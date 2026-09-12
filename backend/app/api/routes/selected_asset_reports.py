from __future__ import annotations

import csv
import json
import math
import textwrap
from datetime import UTC, date, datetime
from io import StringIO
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.entities import ModelRegistry
from app.services.evidence_state_service import build_evidence_state
from app.services.twin_service import build_twin
from app.services.report_decision_support import enrich_report_decision_support
from app.services.asset_health_assessment_report import assessment_docx_bytes, assessment_pdf_bytes, build_asset_health_assessment
from app.services.prediction_report_overlay import overlay_assessment_with_latest_predictions

router = APIRouter(prefix="/reports/assets", tags=["selected-asset-reports"])
REPORT_SCOPE = "SELECTED_ASSET_ONLY"
SCHEMA_VERSION = "simras-selected-asset-report-v1"


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())
    return str(value)


def _clean(value: Any, default: str = "NOT AVAILABLE") -> Any:
    if value is None or value == "":
        return default
    return value


def _nested(mapping: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def _contains_non_operational_marker(value: Any) -> bool:
    try:
        text = json.dumps(_jsonable(value), ensure_ascii=False).upper()
    except Exception:
        text = str(value).upper()
    return any(
        marker in text
        for marker in (
            "SYNTHETIC",
            "DEMONSTRATION",
            "SIMRAS_DEMO",
            "DEMO_SEED",
        )
    )


def _environment_items(evidence_state: dict[str, Any]) -> list[dict[str, Any]]:
    raw = evidence_state.get("environment", {})
    if isinstance(raw, dict):
        items: list[dict[str, Any]] = []
        for variable, payload in raw.items():
            item = dict(payload) if isinstance(payload, dict) else {"value": payload}
            item.setdefault("variable", variable)
            items.append(item)
        return items
    if isinstance(raw, list):
        return [dict(item) for item in raw if isinstance(item, dict)]
    return []


async def _latest_model(session: AsyncSession) -> dict[str, Any] | None:
    row = await session.scalar(
        select(ModelRegistry)
        .order_by(desc(ModelRegistry.created_at), desc(ModelRegistry.id))
        .limit(1)
    )
    if row is None:
        return None

    metrics = _jsonable(row.metrics or {})
    promotion = metrics.get("promotion", {}) if isinstance(metrics, dict) else {}
    ap_validation = (
        promotion.get("ap_validation", {}) if isinstance(promotion, dict) else {}
    )
    safety_policy = (
        promotion.get("safety_policy", {}) if isinstance(promotion, dict) else {}
    )
    training_metrics = metrics.get("training_metrics") if isinstance(metrics, dict) else None
    if training_metrics is None and isinstance(metrics, dict):
        training_metrics = metrics.get("metrics")
    if training_metrics is None and isinstance(metrics, dict):
        direct_metric_keys = {
            "health_mae_rating",
            "health_rmse_rating",
            "health_persistence_mae_rating",
            "risk_roc_auc",
            "risk_brier",
            "risk_f1_at_0_5",
            "risk_ece",
            "rul_mae_years_observed_events",
            "rul_interval_80_coverage_observed_events",
        }
        direct_metrics = {
            key: metrics[key]
            for key in direct_metric_keys
            if key in metrics
        }
        training_metrics = direct_metrics or None
    training_gates = metrics.get("training_gates") if isinstance(metrics, dict) else None
    if training_gates is None and isinstance(metrics, dict):
        training_gates = metrics.get("gates")

    evaluation_protocol = (
        metrics.get("evaluation_protocol") if isinstance(metrics, dict) else None
    )
    evaluation_counts = (
        metrics.get("evaluation_counts") if isinstance(metrics, dict) else None
    )

    return {
        "model_name": row.model_name,
        "version": row.version,
        "stage": row.stage,
        "training_dataset": row.training_dataset,
        "feature_version": row.feature_version,
        "artifact_uri": row.artifact_uri,
        "checksum": row.checksum,
        "created_at": _jsonable(row.created_at),
        "training_rows": metrics.get("training_rows") if isinstance(metrics, dict) else None,
        "unique_bridges": metrics.get("unique_bridges") if isinstance(metrics, dict) else None,
        "training_years": metrics.get("training_years") if isinstance(metrics, dict) else None,
        "prediction_horizon_years": metrics.get("prediction_horizon_years") if isinstance(metrics, dict) else None,
        "training_metrics": training_metrics or {},
        "training_gates": training_gates or {},
        "evaluation_protocol": evaluation_protocol or {
            "status": "NOT_RECORDED_IN_REGISTERED_ARTIFACT"
        },
        "evaluation_counts": evaluation_counts or {
            "status": "NOT_RECORDED_IN_REGISTERED_ARTIFACT"
        },
        "persistence_baseline": {
            "health_persistence_mae_rating": (
                (training_metrics or {}).get("health_persistence_mae_rating")
                if isinstance(training_metrics, dict)
                else None
            ),
            "status": (
                "RECORDED"
                if isinstance(training_metrics, dict)
                and training_metrics.get("health_persistence_mae_rating") is not None
                else "NOT_RECORDED_IN_REGISTERED_ARTIFACT"
            ),
        },
        "promotion": promotion,
        "ap_validation": ap_validation,
        "safety_policy": safety_policy,
        "limitations": metrics.get("limitations", []) if isinstance(metrics, dict) else [],
        "raw_metrics": metrics,
    }


def _governance_for_asset(
    model: dict[str, Any] | None,
    twin: dict[str, Any],
) -> dict[str, Any]:
    asset = twin.get("asset", {}) if isinstance(twin, dict) else {}
    ai = twin.get("ai", {}) if isinstance(twin, dict) else {}
    asset_type = str(asset.get("asset_type") or "UNKNOWN").lower()

    if model is None:
        return {
            "registry_status": "NOT_AVAILABLE",
            "selected_asset_type": asset_type,
            "applicable_to_selected_asset": False,
            "validation_status": "NOT_AVAILABLE",
            "decision_use": "WITHHELD_WHERE_EVIDENCE_OR_MODEL_SCOPE_IS_INSUFFICIENT",
        }

    model_name = str(model.get("model_name") or "")
    training_dataset = str(model.get("training_dataset") or "")
    bridge_only = "bridge" in model_name.lower() or "nbi" in training_dataset.lower()
    local_validation = bool(
        (model.get("ap_validation") or {}).get("local_engineering_validation", False)
    )
    twin_validated = bool(ai.get("model_validated", False))
    applicable = asset_type == "bridge" if bridge_only else True

    validation_status = (
        "AP_VALIDATED"
        if applicable and local_validation and twin_validated
        else "NOT_AP_VALIDATED"
    )

    return {
        **model,
        "registry_status": "AVAILABLE",
        "selected_asset_type": asset_type,
        "bridge_only_model": bridge_only,
        "applicable_to_selected_asset": applicable,
        "local_engineering_validation": local_validation,
        "twin_model_validated": twin_validated,
        "validation_status": validation_status,
        "decision_use": "DECISION_SUPPORT_ONLY",
        "scope_statement": (
            "Bridge research-transfer model; not applicable to this selected asset type."
            if bridge_only and not applicable
            else "Model output remains research decision support until Andhra Pradesh validation is recorded."
        ),
    }


async def _build_report_core_real_evidence_v1(
    session: AsyncSession,
    asset_code: str,
) -> dict[str, Any]:
    twin = _jsonable(await build_twin(session, asset_code))
    evidence_state = _jsonable(await build_evidence_state(session, asset_code))
    model = await _latest_model(session)
    governance = _governance_for_asset(model, twin)

    evidence_rows = evidence_state.get("evidence", []) if isinstance(evidence_state, dict) else []
    environment_rows = evidence_state.get("environment", []) if isinstance(evidence_state, dict) else []
    condition = evidence_state.get("condition", {}) if isinstance(evidence_state, dict) else {}
    risk = evidence_state.get("risk", {}) if isinstance(evidence_state, dict) else {}

    environment_items = _environment_items(evidence_state if isinstance(evidence_state, dict) else {})
    non_operational_environment = [
        item for item in environment_items if _contains_non_operational_marker(item)
    ]
    source_labelled_environment = [
        item for item in environment_items if not _contains_non_operational_marker(item)
    ]
    inspection_state = twin.get("inspection", {}) if isinstance(twin, dict) else {}
    inspection_non_operational = _contains_non_operational_marker(inspection_state)
    prediction_input_non_operational = bool(non_operational_environment) or inspection_non_operational

    return {
        "schema_version": SCHEMA_VERSION,
        "scope": REPORT_SCOPE,
        "selected_asset_only": True,
        "generated_at": datetime.now(UTC).isoformat(),
        "asset_code": asset_code,
        "asset": twin.get("asset", {}),
        "report_integrity": {
            "canonical_twin_service": "app.services.twin_service.build_twin",
            "canonical_evidence_service": "app.services.evidence_state_service.build_evidence_state",
            "portfolio_aggregation": False,
            "cross_asset_mixing": False,
            "missing_values_policy": "NOT_AVAILABLE_OR_WITHHELD; NEVER_SYNTHESIZE_ENGINEERING_TRUTH",
            "synthetic_demo_policy": (
                "Synthetic/demo values are never counted as real official evidence. "
                "They remain visible only as explicitly labelled audit context and are excluded from operational environment rows."
            ),
        },
        "evidence_quality": {
            "evidence_strength": evidence_state.get("evidence_strength"),
            "official_evidence_rows": len(evidence_rows) if isinstance(evidence_rows, list) else 0,
            "environment_rows": len(environment_items),
            "source_labelled_environment_rows": len(source_labelled_environment),
            "synthetic_or_demo_environment_rows": len(non_operational_environment),
            "structural_condition": condition.get("condition") if isinstance(condition, dict) else None,
            "official_structural_risk": (
                condition.get("risk") if isinstance(condition, dict) else None
            ),
            "structural_state_origin": condition.get("origin") if isinstance(condition, dict) else None,
            "structural_state_message": condition.get("message") if isinstance(condition, dict) else None,
            "structural_state_source": condition.get("source") if isinstance(condition, dict) else None,
            "structural_state_observed_at": condition.get("observed_at") if isinstance(condition, dict) else None,
            "overall_evidence_risk": risk.get("value") if isinstance(risk, dict) else None,
            "completeness_is_not_health_or_safety": True,
            "statement": "Evidence completeness and model validation status are separate from structural health and safety.",
        },
        "prediction_input_quality": {
            "status": (
                "SYNTHETIC_OR_DEMO_INPUTS_PRESENT"
                if prediction_input_non_operational
                else "SOURCE_LABELLED_INPUTS"
            ),
            "synthetic_or_demo_environment_rows": len(non_operational_environment),
            "inspection_synthetic_or_demo": inspection_non_operational,
            "operational_interpretation": (
                "Prediction is displayable only as research/demo decision support; do not present it as a real-world validated prediction."
                if prediction_input_non_operational
                else "No synthetic/demo marker was detected in the current environment/inspection input payload; source and validation limitations still apply."
            ),
        },
        "twin": twin,
        "evidence_state": evidence_state,
        "model_governance": governance,
        "disclaimer": (
            "SIMRAS is engineering decision support. This selected-asset report is not an official "
            "condition certificate, dam-safety rating, bridge fitness certificate, or maintenance authorization."
        ),
    }


async def _build_report(
    session: AsyncSession,
    asset_code: str,
) -> dict[str, Any]:
    report = await _build_report_core_real_evidence_v1(session, asset_code)
    return enrich_report_decision_support(report)


def _prediction_kind(ai: dict[str, Any]) -> str:
    method = str(ai.get("prediction_method") or ai.get("prediction_source") or "").lower()
    if "bridge" in method and "ml" in method:
        return "RESEARCH_TRANSFER_BRIDGE_ML"
    if "transparent" in method or "rule" in method:
        return "TRANSPARENT_DECISION_SUPPORT"
    return "DECISION_SUPPORT"


async def _prediction_row_count(session: AsyncSession) -> int:
    value = await session.scalar(text("SELECT COUNT(*)::bigint FROM public.predictions"))
    return int(value or 0)


async def _build_prediction_preview(
    session: AsyncSession,
    asset_code: str,
) -> dict[str, Any]:
    # The no-write guard is evaluated inside the backend's own SQLAlchemy session.
    # This avoids Docker/PowerShell stdout parsing and directly verifies that the
    # canonical live preview did not change the predictions table.
    count_before = await _prediction_row_count(session)
    report = await _build_report(session, asset_code)
    count_after = await _prediction_row_count(session)
    twin = report.get("twin", {}) if isinstance(report, dict) else {}
    ai = twin.get("ai", {}) if isinstance(twin, dict) else {}
    if not isinstance(ai, dict):
        ai = {}
    governance = report.get("model_governance", {})
    quality = report.get("evidence_quality", {})

    prediction_available = any(
        ai.get(key) is not None
        for key in (
            "health_score",
            "risk_score",
            "hazard_score",
            "remaining_life_years",
        )
    )

    return {
        "scope": REPORT_SCOPE,
        "selected_asset_only": True,
        "asset_code": asset_code,
        "generated_at": datetime.now(UTC).isoformat(),
        "prediction_available": prediction_available,
        "prediction_kind": _prediction_kind(ai),
        "prediction": ai if ai else None,
        "model_governance": governance,
        "input_quality": report.get("prediction_input_quality", {}),
        "official_structural_state": {
            "condition": quality.get("structural_condition"),
            "risk": quality.get("official_structural_risk"),
            "origin": quality.get("structural_state_origin"),
            "message": quality.get("structural_state_message"),
        },
        "persistence": {
            "persisted": False,
            "database_write": False,
            "prediction_table_write": False,
            "db_write_guard": {
                "prediction_rows_before": count_before,
                "prediction_rows_after": count_after,
                "unchanged": count_before == count_after,
                "verification": "BACKEND_SQLALCHEMY_SAME_SESSION",
            },
        },
        "statement": (
            "This is a live selected-asset decision-support evaluation from the canonical twin service. "
            "It is not an official structural condition or safety rating and this preview does not persist a prediction row."
        ),
    }


def _display(value: Any) -> str:
    if value is None or value == "":
        return "NOT AVAILABLE"
    if isinstance(value, bool):
        return "YES" if value else "NO"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if isinstance(value, (dict, list)):
        return json.dumps(_jsonable(value), ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _official_display(value: Any, origin: Any) -> str:
    label = str(value or "").strip().upper()
    if not label or label == "UNKNOWN":
        return "NOT AVAILABLE"
    return str(value).replace("_", " ")


def _audit_summary(value: Any) -> str:
    if isinstance(value, dict):
        status = value.get("status")
        if status == "NOT_RECORDED_IN_REGISTERED_ARTIFACT":
            return "NOT RECORDED IN CURRENT REGISTERED ARTIFACT"
        parts = []
        for key, item in list(value.items())[:8]:
            if item is None or item == "":
                continue
            parts.append(f"{str(key).replace('_', ' ')}={_display(item)}")
        return "; ".join(parts) if parts else "NOT AVAILABLE"
    return _display(value)


def _prediction_line(value: Any, suffix: str = "") -> str:
    if value is None:
        return "NOT AVAILABLE"
    if isinstance(value, (int, float)):
        return f"{float(value):.1f}{suffix}"
    return f"{value}{suffix}"


def _csv_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    asset = report.get("asset", {})
    twin = report.get("twin", {})
    evidence_state = report.get("evidence_state", {})
    governance = report.get("model_governance", {})
    rows: list[dict[str, Any]] = []

    def add(
        section: str,
        field: str,
        value: Any,
        *,
        unit: Any = None,
        observed_at: Any = None,
        source: Any = None,
        source_type: Any = None,
        authority_level: Any = None,
        origin: Any = None,
        quality_flag: Any = None,
        confidence: Any = None,
        document: Any = None,
        document_url: Any = None,
        note: Any = None,
    ) -> None:
        rows.append(
            {
                "scope": REPORT_SCOPE,
                "asset_code": report.get("asset_code"),
                "asset_name": asset.get("name"),
                "asset_type": asset.get("asset_type"),
                "section": section,
                "field": field,
                "value": _display(value),
                "unit": _display(unit) if unit is not None else "",
                "observed_at": _display(observed_at) if observed_at is not None else "",
                "source": _display(source) if source is not None else "",
                "source_type": _display(source_type) if source_type is not None else "",
                "authority_level": _display(authority_level) if authority_level is not None else "",
                "origin": _display(origin) if origin is not None else "",
                "quality_flag": _display(quality_flag) if quality_flag is not None else "",
                "confidence": _display(confidence) if confidence is not None else "",
                "document": _display(document) if document is not None else "",
                "document_url": _display(document_url) if document_url is not None else "",
                "note": _display(note) if note is not None else "",
            }
        )

    for field in (
        "asset_code",
        "name",
        "asset_type",
        "subtype",
        "district",
        "owner",
        "built_year",
        "design_life_years",
        "material",
        "identity_status",
        "confidence_score",
    ):
        add("ASSET_IDENTITY", field, asset.get(field))

    state_asset = evidence_state.get("asset", {}) if isinstance(evidence_state, dict) else {}
    for field in ("latitude", "longitude"):
        if field not in asset or asset.get(field) is None:
            add("ASSET_IDENTITY", field, state_asset.get(field))

    quality = report.get("evidence_quality", {})
    add(
        "OFFICIAL_STRUCTURAL_STATE",
        "condition",
        _official_display(quality.get("structural_condition"), quality.get("structural_state_origin")),
        observed_at=quality.get("structural_state_observed_at"),
        source=quality.get("structural_state_source"),
        origin=quality.get("structural_state_origin"),
        note=quality.get("structural_state_message"),
    )
    add(
        "OFFICIAL_STRUCTURAL_STATE",
        "risk",
        _official_display(quality.get("official_structural_risk"), quality.get("structural_state_origin")),
        observed_at=quality.get("structural_state_observed_at"),
        source=quality.get("structural_state_source"),
        origin=quality.get("structural_state_origin"),
        note="Official evidence state is kept separate from AI decision-support output.",
    )

    for item in evidence_state.get("evidence", []) if isinstance(evidence_state, dict) else []:
        value = item.get("numeric_value")
        if value is None:
            value = item.get("text_value")
        add(
            "OFFICIAL_EVIDENCE",
            item.get("field_name") or item.get("evidence_type") or "evidence",
            value,
            unit=item.get("unit"),
            observed_at=item.get("observed_at") or item.get("valid_from"),
            source=item.get("source_name") or item.get("agency"),
            source_type=item.get("source_code"),
            authority_level=item.get("authority_level"),
            origin=item.get("origin"),
            quality_flag=item.get("quality_flag"),
            confidence=item.get("confidence_score"),
            document=item.get("document_title"),
            document_url=item.get("document_url"),
        )

    environment_items = _environment_items(evidence_state if isinstance(evidence_state, dict) else {})

    for item in environment_items:
        non_operational = _contains_non_operational_marker(item)
        add(
            "EXCLUDED_DEMO_OR_SYNTHETIC" if non_operational else "ENVIRONMENT",
            item.get("variable") or "observation",
            item.get("value"),
            unit=item.get("unit"),
            observed_at=item.get("observed_at"),
            source=item.get("source_name") or item.get("source_code") or item.get("source"),
            source_type=item.get("source_type"),
            origin=item.get("spatial_method"),
            quality_flag=item.get("quality_flag"),
            confidence=item.get("confidence_score") or item.get("confidence"),
            note=(
                "Excluded from operational/real evidence because source or quality metadata is synthetic/demo."
                if non_operational
                else ("Estimated/spatially transferred" if item.get("is_estimated") else None)
            ),
        )

    twin_model = twin.get("twin", {}) if isinstance(twin, dict) else {}
    for key, value in (twin_model.get("dimensions") or {}).items():
        add(
            "TWIN_DIMENSION",
            key,
            value,
            source=twin_model.get("model_source"),
            document_url=twin_model.get("source_url"),
            note=twin_model.get("fidelity_level"),
        )

    ai = twin.get("ai", {}) if isinstance(twin, dict) else {}
    for field in (
        "health_score",
        "risk_score",
        "risk_level",
        "hazard_score",
        "hazard_level",
        "remaining_life_years",
        "rul_lower_bound",
        "rul_upper_bound",
        "confidence",
        "status",
        "prediction_method",
        "model_version",
        "feature_version",
        "model_validated",
    ):
        add(
            "ML_DECISION_SUPPORT",
            field,
            ai.get(field),
            note="Not an official engineering condition or safety rating",
        )

    for field in (
        "model_name",
        "version",
        "stage",
        "training_dataset",
        "feature_version",
        "training_rows",
        "unique_bridges",
        "training_years",
        "prediction_horizon_years",
        "validation_status",
        "applicable_to_selected_asset",
        "evaluation_protocol",
        "evaluation_counts",
        "persistence_baseline",
        "training_metrics",
        "training_gates",
        "limitations",
    ):
        add("MODEL_GOVERNANCE", field, governance.get(field))

    input_quality = report.get("prediction_input_quality", {})
    add(
        "REPORT_INTEGRITY",
        "prediction_input_quality",
        input_quality.get("status"),
        note=input_quality.get("operational_interpretation"),
    )
    add(
        "REPORT_INTEGRITY",
        "source_labelled_environment_rows",
        report.get("evidence_quality", {}).get("source_labelled_environment_rows"),
    )
    add(
        "REPORT_INTEGRITY",
        "synthetic_or_demo_environment_rows",
        report.get("evidence_quality", {}).get("synthetic_or_demo_environment_rows"),
    )

    add(
        "REPORT_INTEGRITY",
        "completeness_is_not_health_or_safety",
        True,
        note=report.get("evidence_quality", {}).get("statement"),
    )
    return rows


def _csv_bytes(report: dict[str, Any]) -> bytes:
    rows = _csv_rows(report)
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


def _pdf_escape(text: str) -> str:
    return (
        text.encode("latin-1", errors="replace")
        .decode("latin-1")
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _pdf_text(x: int, y: int, font: str, size: float, text: str, rgb: str = "0 0 0") -> str:
    return f"BT /{font} {size} Tf {rgb} rg {x} {y} Td ({_pdf_escape(text)}) Tj ET"


def _pdf_bytes(report: dict[str, Any]) -> bytes:
    asset = report.get("asset", {})
    quality = report.get("evidence_quality", {})
    twin = report.get("twin", {})
    ai = twin.get("ai", {}) if isinstance(twin, dict) else {}
    twin_model = twin.get("twin", {}) if isinstance(twin, dict) else {}
    governance = report.get("model_governance", {})

    content: list[str] = [
        "0.06 0.13 0.20 rg 0 786 595 56 re f",
        "0.90 0.94 0.97 rg 0 748 595 38 re f",
        _pdf_text(36, 818, "F2", 15, "GOVERNMENT OF ANDHRA PRADESH - SIMRAS", "1 1 1"),
        _pdf_text(36, 800, "F1", 9, "Smart Infrastructure Monitoring and Risk Assistance System", "1 1 1"),
        _pdf_text(36, 770, "F2", 11, "SELECTED ASSET REPORT", "0.06 0.13 0.20"),
        _pdf_text(385, 770, "F2", 9, REPORT_SCOPE, "0.06 0.13 0.20"),
    ]

    y = 727

    def heading(text: str) -> None:
        nonlocal y
        content.append("0.78 0.84 0.88 RG 36 %d m 559 %d l S" % (y + 8, y + 8))
        content.append(_pdf_text(36, y, "F2", 10.2, text, "0.06 0.13 0.20"))
        y -= 16

    def line(label: str, value: Any, *, small: bool = False) -> None:
        nonlocal y
        value_text = _display(value)
        width = 86 if small else 78
        chunks = textwrap.wrap(f"{label}: {value_text}", width=width) or [f"{label}: NOT AVAILABLE"]
        for chunk in chunks[:3]:
            content.append(_pdf_text(44, y, "F1", 7.4 if small else 8.3, chunk, "0.08 0.10 0.13"))
            y -= 10 if small else 11

    heading("1. Asset identity")
    line("Asset", f"{asset.get('name') or 'NOT AVAILABLE'} ({report.get('asset_code')})")
    line("Type / district", f"{_clean(asset.get('asset_type'))} / {_clean(asset.get('district'))}")
    line("Identity status", asset.get("identity_status"))

    heading("2. Official evidence state")
    line("Evidence strength", quality.get("evidence_strength"))
    line("Official evidence rows", quality.get("official_evidence_rows"))
    line(
        "Official structural condition",
        _official_display(quality.get("structural_condition"), quality.get("structural_state_origin")),
    )
    line(
        "Official structural risk",
        _official_display(quality.get("official_structural_risk"), quality.get("structural_state_origin")),
    )
    line("Evidence reason", quality.get("structural_state_message"), small=True)
    line(
        "Source-labelled environment / synthetic-demo excluded",
        f"{_display(quality.get('source_labelled_environment_rows'))} / {_display(quality.get('synthetic_or_demo_environment_rows'))}",
    )

    heading("3. Current AI / decision-support prediction")
    validation = governance.get("validation_status") or "NOT_AP_VALIDATED"
    line("Validation", validation)
    health = _prediction_line(ai.get("health_score"), "/100")
    health_range = (
        f"{_prediction_line(ai.get('health_lower_bound'), '/100')} - {_prediction_line(ai.get('health_upper_bound'), '/100')}"
        if ai.get("health_lower_bound") is not None and ai.get("health_upper_bound") is not None
        else "NOT AVAILABLE"
    )
    line("Health estimate / interval", f"{health} / {health_range}")
    line("Poor-condition probability", f"{_prediction_line(ai.get('risk_score'), '%')} / {_display(ai.get('risk_level'))}")
    line("Environment hazard", f"{_prediction_line(ai.get('hazard_score'), '/100')} / {_display(ai.get('hazard_level'))}")
    conf = ai.get("confidence")
    conf_text = "NOT AVAILABLE" if conf is None else f"{(float(conf) * 100 if float(conf) <= 1 else float(conf)):.0f}%"
    line("Prediction confidence", conf_text)
    rul = _prediction_line(ai.get("remaining_life_years"), " years")
    if ai.get("rul_lower_bound") is not None and ai.get("rul_upper_bound") is not None:
        rul += f" ({_prediction_line(ai.get('rul_lower_bound'))}-{_prediction_line(ai.get('rul_upper_bound'))})"
    line("Conditional RUL / planning proxy", rul)
    line("Method", ai.get("prediction_method") or ai.get("prediction_source"), small=True)
    line("Model version / status", f"{_display(ai.get('model_version') or governance.get('version'))} / {_display(ai.get('status') or governance.get('stage'))}", small=True)
    input_quality = report.get("prediction_input_quality", {})
    line("Input quality", input_quality.get("status"))
    line("Input-quality interpretation", input_quality.get("operational_interpretation"), small=True)
    line("Prediction use", "Research decision support only; AI does not replace the official structural state.", small=True)

    heading("4. Digital twin provenance")
    line("Fidelity", twin_model.get("fidelity_level"))
    line("Model source", twin_model.get("model_source"), small=True)
    line("Asset-specific", twin_model.get("is_asset_specific"))

    heading("5. Model governance and held-out metrics")
    line("Registry model", f"{_display(governance.get('model_name'))} / {_display(governance.get('version'))}", small=True)
    line("Stage / AP validation", f"{_display(governance.get('stage'))} / {_display(governance.get('validation_status'))}")
    line("Selected-asset applicability", governance.get("applicable_to_selected_asset"))
    training_metrics = governance.get("training_metrics") or {}
    line("Risk ROC-AUC / Brier / ECE", f"{_display(training_metrics.get('risk_roc_auc'))} / {_display(training_metrics.get('risk_brier'))} / {_display(training_metrics.get('risk_ece'))}")
    line("Health MAE / RMSE", f"{_display(training_metrics.get('health_mae_rating'))} / {_display(training_metrics.get('health_rmse_rating'))}")
    line("Training rows / bridges", f"{_display(governance.get('training_rows'))} / {_display(governance.get('unique_bridges'))}")
    line("Evaluation protocol", _audit_summary(governance.get("evaluation_protocol")), small=True)
    line("Partition counts", _audit_summary(governance.get("evaluation_counts")), small=True)

    heading("6. Use limitation")
    disclaimer = report.get("disclaimer") or "Decision support only."
    for wrapped in textwrap.wrap(disclaimer, width=92)[:4]:
        content.append(_pdf_text(44, y, "F1", 7.3, wrapped, "0.32 0.10 0.10"))
        y -= 9

    content.extend(
        [
            "0.78 0.84 0.88 RG 36 32 m 559 32 l S",
            _pdf_text(36, 18, "F1", 6.8, f"Generated {_display(report.get('generated_at'))} | Scope: {REPORT_SCOPE}", "0.35 0.38 0.42"),
        ]
    )

    stream = "\n".join(content).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out.extend(f"{index} 0 obj\n".encode())
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode())
    out.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(out)


def _headers(filename: str) -> dict[str, str]:
    return {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-SIMRAS-Report-Scope": REPORT_SCOPE,
        "Cache-Control": "no-store",
    }


@router.get("/{asset_code}")
async def selected_asset_report(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await _build_report(session, asset_code)


@router.post("/{asset_code}/prediction-preview")
async def selected_asset_prediction_preview(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await _build_prediction_preview(session, asset_code)


@router.get("/{asset_code}/json")
async def selected_asset_json(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> Response:
    report = await _build_report(session, asset_code)
    body = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
    return Response(
        body,
        media_type="application/json",
        headers=_headers(f"{asset_code}-SIMRAS-selected-asset.json"),
    )


@router.get("/{asset_code}/csv")
async def selected_asset_csv(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> Response:
    report = await _build_report(session, asset_code)
    return Response(
        _csv_bytes(report),
        media_type="text/csv; charset=utf-8",
        headers=_headers(f"{asset_code}-SIMRAS-selected-asset-evidence.csv"),
    )


@router.get("/{asset_code}/pdf")
async def selected_asset_pdf(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> Response:
    report = await _build_report(session, asset_code)
    return Response(
        _pdf_bytes(report),
        media_type="application/pdf",
        headers=_headers(f"{asset_code}-SIMRAS-selected-asset-report.pdf"),
    )

# SIMRAS_ASSET_HEALTH_ASSESSMENT_ROUTES_V1
@router.get("/{asset_code}/assessment")
async def selected_asset_health_assessment(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await overlay_assessment_with_latest_predictions(session, asset_code, await build_asset_health_assessment(session, asset_code))


@router.get("/{asset_code}/assessment/pdf")
async def selected_asset_health_assessment_pdf(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> Response:
    report = await build_asset_health_assessment(session, asset_code)
    payload = assessment_pdf_bytes(report)
    filename = f"{asset_code}-SIMRAS-Asset-Health-Assessment.pdf"
    return Response(
        payload,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-SIMRAS-Report-ID": report["report_id"],
        },
    )


@router.get("/{asset_code}/assessment/docx")
async def selected_asset_health_assessment_docx(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> Response:
    report = await build_asset_health_assessment(session, asset_code)
    payload = assessment_docx_bytes(report)
    filename = f"{asset_code}-SIMRAS-Asset-Health-Assessment.docx"
    return Response(
        payload,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-SIMRAS-Report-ID": report["report_id"],
        },
    )
