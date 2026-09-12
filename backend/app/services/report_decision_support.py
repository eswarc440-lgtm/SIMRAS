from __future__ import annotations

from typing import Any, Iterable


CWC_SAFETY_INSPECTION = {
    "authority": "Central Water Commission / Central Dam Safety Organisation",
    "title": "Guidelines for Safety Inspection of Dams",
    "url": "https://damsafety.cwc.gov.in/ecm-includes/PDFs/Guidelines_for_Safety_Inspection_of_Dams.pdf",
    "role": "Inspection, deficiency identification, monitoring and remedial-action guidance",
}
CWC_RISK = {
    "authority": "Central Water Commission / Central Dam Safety Organisation",
    "title": "Guidelines for Assessing and Managing Risks Associated with Dams",
    "url": "https://damsafety.cwc.gov.in/ecm-includes/PDFs/Guidelines_on_Risk_Analysis.pdf",
    "role": "Dam-risk assessment and risk-management guidance",
}
CWC_STRUCTURAL = {
    "authority": "Central Water Commission / Central Dam Safety Organisation",
    "title": "Manual for Assessing Structural Safety of Existing Dams",
    "url": "https://damsafety.cwc.gov.in/ecm-includes/PDFs/Manual_for_Assessing_Structural_Safety.pdf",
    "role": "Structural-safety investigation and assessment guidance",
}
NWDP_AP_RESERVOIR = {
    "authority": "National Water Informatics Centre / Andhra Pradesh Surface Water",
    "title": "Reservoir Storage and Water Level (Manual - Daily), Andhra Pradesh",
    "url": "https://www.nwdp.nwic.gov.in/en/dataset/reservoir-water-level-manual-daily-andhra-pradesh-surface-water-department",
    "role": "Official reservoir level/storage observations used when linked to the selected asset",
}
NWDP_AP_RIVER = {
    "authority": "National Water Informatics Centre / Andhra Pradesh Surface Water",
    "title": "River Water Level (Telemetry - Hourly), Andhra Pradesh",
    "url": "https://www.nwdp.nwic.gov.in/dataset/river-water-level-telemetry-hourly-andhra-pradesh-surface-water-department",
    "role": "Official river-level observations used when linked to the selected asset",
}
NWDP_AP_DISCHARGE = {
    "authority": "National Water Informatics Centre / Andhra Pradesh Surface Water",
    "title": "River Discharge (Manual - Daily), Andhra Pradesh",
    "url": "https://www.nwdp.nwic.gov.in/dataset/river-discharge-manual-dailly-andhra-pradesh-surface-water-department",
    "role": "Official river-discharge observations used when linked to the selected asset",
}
NWDP_AP_RAINFALL = {
    "authority": "National Water Informatics Centre / Andhra Pradesh Surface Water",
    "title": "Rainfall (Telemetry - Hourly), Andhra Pradesh",
    "url": "https://www.nwdp.nwic.gov.in/en/dataset/rainfall-andhra-pradesh-surface-water-telemetry-hourly",
    "role": "Official rainfall observations used when linked to the selected asset",
}
MORTH_BRIDGE_INSPECTION = {
    "authority": "Ministry of Road Transport and Highways",
    "title": "Inspection and Maintenance of Bridges / Structures falling on National Highways and Expressways",
    "url": "https://morth.nic.in/technical_circulars",
    "role": "Bridge inspection and maintenance guidance",
}
MORTH_IBMS = {
    "authority": "Ministry of Road Transport and Highways",
    "title": "Indian Bridge Management System (IBMS)",
    "url": "https://morth.nic.in/search/node/ibms",
    "role": "National bridge inventory / condition-management context",
}


GOVERNMENT_KEYWORDS = (
    "CWC",
    "CENTRAL WATER COMMISSION",
    "CDSO",
    "DRIP",
    "NWDP",
    "NWIC",
    "INDIA-WRIS",
    "INDIA WRIS",
    "WRIS",
    "ANDHRA PRADESH SW",
    "AP SW",
    "WATER RESOURCES DEPARTMENT",
    "MORTH",
    "MINISTRY OF ROAD TRANSPORT",
    "NHAI",
    "INDIAN RAILWAYS",
    "RDSO",
    "AAI",
    "AIRPORTS AUTHORITY OF INDIA",
    "GOVERNMENT OF INDIA",
)

SYNTHETIC_MARKERS = (
    "SYNTHETIC",
    "DEMO",
    "DEMONSTRATION",
    "MOCK",
    "SIMULATED",
)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _upper(value: Any) -> str:
    return (_text(value) or "").upper()


def _first(mapping: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = mapping.get(name)
        if value is not None and value != "":
            return value
    return None


def _nested(root: dict[str, Any], *path: str) -> Any:
    current: Any = root
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item)


def _contains_marker(value: Any, markers: tuple[str, ...]) -> bool:
    try:
        text = str(value).upper()
    except Exception:
        return False
    return any(marker in text for marker in markers)


def _has_any_key(value: Any, names: set[str]) -> bool:
    for item in _walk(value):
        for key, raw in item.items():
            if str(key).lower() in names and raw not in (None, "", [], {}):
                return True
    return False


def _government_source_records(report: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    output: list[dict[str, Any]] = []
    ignored_synthetic = 0
    seen: set[tuple[str, str, str]] = set()

    for item in _walk(report):
        relevant_keys = {
            "source",
            "source_name",
            "source_code",
            "agency",
            "document_title",
            "title",
            "document_url",
            "source_url",
            "source_record_id",
            "observed_at",
            "ingested_at",
            "quality_flag",
            "spatial_method",
            "processing_method",
            "confidence",
            "confidence_score",
            "is_estimated",
            "is_official",
        }

        if not relevant_keys.intersection(item.keys()):
            continue

        if _contains_marker(item, SYNTHETIC_MARKERS):
            ignored_synthetic += 1
            continue

        source_code = _text(_first(item, "source_code", "code")) or ""
        source_name = _text(_first(item, "source_name", "source", "agency")) or ""
        document_title = _text(_first(item, "document_title", "title")) or ""
        document_url = _text(_first(item, "document_url", "source_url", "url")) or ""
        joined = " | ".join((source_code, source_name, document_title, document_url)).upper()

        if not any(keyword in joined for keyword in GOVERNMENT_KEYWORDS):
            continue

        key = (source_code, document_url, document_title or source_name)
        if key in seen:
            continue
        seen.add(key)

        output.append(
            {
                "source_code": source_code or None,
                "source_name": source_name or None,
                "document_title": document_title or None,
                "document_url": document_url or None,
                "source_record_id": _text(item.get("source_record_id")),
                "observed_at": _text(item.get("observed_at")),
                "ingested_at": _text(item.get("ingested_at")),
                "quality_flag": _text(item.get("quality_flag")),
                "spatial_method": _text(_first(item, "spatial_method", "processing_method")),
                "confidence": _num(_first(item, "confidence", "confidence_score")),
                "is_estimated": item.get("is_estimated"),
                "is_official": item.get("is_official"),
            }
        )

    output.sort(
        key=lambda row: (
            row.get("source_code") or "",
            row.get("source_name") or "",
            row.get("document_title") or "",
        )
    )
    return output, ignored_synthetic


def _model_info(report: dict[str, Any], ai: dict[str, Any]) -> dict[str, Any]:
    governance = _mapping(report.get("model_governance"))
    stage = _text(
        _first(
            ai,
            "status",
            "stage",
        )
    ) or _text(_first(governance, "stage", "status")) or "NOT_AVAILABLE"

    method = _text(
        _first(
            ai,
            "prediction_method",
            "method",
            "operational_method",
        )
    ) or _text(_first(governance, "prediction_method", "method"))

    version = _text(
        _first(
            ai,
            "model_version",
            "version",
        )
    ) or _text(_first(governance, "model_version", "version"))

    validated = bool(
        ai.get("model_validated") is True
        or governance.get("model_validated") is True
        or stage.upper() == "VALIDATED_LOCAL"
    )

    return {
        "prediction_method": method,
        "model_version": version,
        "stage": stage,
        "locally_validated": validated,
        "training_scope": _text(_first(ai, "training_scope")) or _text(_first(governance, "training_scope")),
        "feature_version": _text(_first(ai, "feature_version")) or _text(_first(governance, "feature_version")),
    }


def _is_bridge_ml(method: str | None) -> bool:
    text = (method or "").lower()
    return "nbi_bridge" in text or "bridge_ml" in text or "calibrated_nbi" in text


def _confidence(ai: dict[str, Any], model: dict[str, Any], asset_type: str) -> float | None:
    value = _num(ai.get("confidence"))
    if value is None and asset_type in {"dam", "barrage"}:
        value = _num(ai.get("operational_confidence"))
    if value is None:
        return None
    return max(0.0, min(1.0, value))


def _rul_summary(ai: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    value = _num(ai.get("remaining_life_years"))
    lower = _num(ai.get("rul_lower_bound"))
    upper = _num(ai.get("rul_upper_bound"))
    method = _text(_first(ai, "rul_method", "prediction_method")) or ""
    method_upper = method.upper()
    stage = _upper(model.get("stage"))
    training_scope = _upper(model.get("training_scope"))

    confidence = _num(ai.get("rul_confidence"))
    if confidence is None:
        confidence = _num(ai.get("confidence"))

    if value is None:
        return {
            "status": "WITHHELD",
            "estimate_years": None,
            "lower_bound_years": None,
            "upper_bound_years": None,
            "confidence": confidence,
            "mode": "NO_ELIGIBLE_RUL_OUTPUT",
            "reason": (
                _text(ai.get("rul_basis"))
                or "No eligible longitudinal deterioration output is available for this asset."
            ),
        }

    is_nbi_bridge = (
        "NBI" in method_upper
        or "CALIBRATED_NBI_BRIDGE_ML" in method_upper
        or "FHWA_NBI" in training_scope
    )

    if is_nbi_bridge and stage == "RESEARCH_TRANSFER":
        return {
            "status": "RESEARCH_TRANSFER",
            "estimate_years": round(value, 2),
            "lower_bound_years": round(lower, 2) if lower is not None else None,
            "upper_bound_years": round(upper, 2) if upper is not None else None,
            "confidence": confidence,
            "mode": "CONDITIONAL_DETERIORATION_HORIZON",
            "reason": (
                "FHWA/NBI longitudinal bridge model output. This is a conditional "
                "deterioration horizon derived from U.S. bridge histories and is "
                "RESEARCH_TRANSFER for Andhra Pradesh; it is not a locally validated "
                "structural failure-time forecast."
            ),
        }

    if bool(model.get("locally_validated")) or stage == "VALIDATED_LOCAL":
        return {
            "status": "AVAILABLE",
            "estimate_years": round(value, 2),
            "lower_bound_years": round(lower, 2) if lower is not None else None,
            "upper_bound_years": round(upper, 2) if upper is not None else None,
            "confidence": confidence,
            "mode": "STRUCTURAL_RUL",
            "reason": "Locally validated longitudinal model output.",
        }

    return {
        "status": "WITHHELD",
        "estimate_years": None,
        "lower_bound_years": None,
        "upper_bound_years": None,
        "confidence": confidence,
        "mode": "UNVALIDATED_OR_PLANNING_PROXY",
        "reason": (
            "A numeric planning/experimental value exists in the source state, but "
            "it is intentionally excluded from structural RUL because local "
            "longitudinal validation is not established."
        ),
    }

def _risk_level(score: float | None, supplied: Any = None) -> str:
    supplied_text = _upper(supplied)
    if supplied_text and supplied_text not in {"N/A", "NA", "NONE", "UNKNOWN"}:
        return supplied_text
    if score is None:
        return "NOT_AVAILABLE"
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def _guidance(asset_type: str) -> list[dict[str, str]]:
    if asset_type in {"dam", "barrage"}:
        return [
            CWC_SAFETY_INSPECTION,
            CWC_RISK,
            CWC_STRUCTURAL,
            NWDP_AP_RESERVOIR,
            NWDP_AP_RIVER,
            NWDP_AP_DISCHARGE,
            NWDP_AP_RAINFALL,
        ]
    if asset_type == "bridge":
        return [MORTH_BRIDGE_INSPECTION, MORTH_IBMS, NWDP_AP_RIVER, NWDP_AP_RAINFALL]
    return []


def _required_evidence(report: dict[str, Any], asset_type: str) -> list[dict[str, str]]:
    if asset_type == "bridge":
        requirements = [
            ("Current structural inspection / condition rating", {"condition_rating", "inspection_score", "inspection_date", "inspected_at"}),
            ("Defect inventory / severity", {"defect_count", "defects", "max_defect_severity", "defect_severity"}),
            ("Bridge geometry / span evidence", {"span_count", "max_span_m", "typical_span_m", "structure_length_m", "length_m"}),
            ("Material / structural type", {"material", "structural_form", "structure_type", "bridge_type"}),
            ("Traffic / loading evidence", {"average_daily_traffic", "traffic_load_ratio", "truck_traffic_percent"}),
            ("Scour / waterway evidence", {"scour_rating", "waterway_rating", "scour", "river_level", "river_discharge"}),
            ("Maintenance history", {"maintenance", "maintenance_records", "days_since_maintenance", "last_maintenance"}),
        ]
    elif asset_type in {"dam", "barrage"}:
        requirements = [
            ("Current dam/barrage safety inspection", {"inspection_date", "inspected_at", "dam_safety_category", "official_condition", "structural_condition"}),
            ("Gate / spillway operational condition", {"gate_condition", "spillway_condition", "gate_count", "spillway_capacity", "designed_spillway_capacity"}),
            ("Reservoir level / storage", {"reservoir_level", "reservoir_storage", "water_level", "storage"}),
            ("River discharge / velocity", {"river_discharge", "discharge", "river_velocity", "water_velocity"}),
            ("Seepage / uplift / instrumentation where applicable", {"seepage", "uplift_pressure", "piezometer", "instrumentation"}),
            ("Maintenance / repair history", {"maintenance", "maintenance_records", "last_maintenance", "repair_history"}),
            ("Emergency action / operating evidence", {"eap", "emergency_action_plan", "operating_rule", "operation_manual"}),
        ]
    else:
        requirements = [
            ("Current approved inspection", {"inspection_date", "inspected_at", "condition_rating"}),
            ("Maintenance history", {"maintenance", "maintenance_records", "last_maintenance"}),
        ]

    return [
        {
            "item": label,
            "status": "AVAILABLE" if _has_any_key(report, names) else "REQUIRED_OR_NOT_LINKED",
        }
        for label, names in requirements
    ]


def _actions(
    report: dict[str, Any],
    *,
    asset_type: str,
    health: float | None,
    structural_risk: float | None,
    operational_risk: float | None,
    hazard: float | None,
    confidence: float | None,
    structural_available: bool,
    government_sources: list[dict[str, Any]],
    rul: dict[str, Any],
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    evidence = _required_evidence(report, asset_type)
    missing = [item["item"] for item in evidence if item["status"] != "AVAILABLE"]

    def add(priority: str, action: str, reason: str, basis: str) -> None:
        key = (priority, action)
        if any((row["priority"], row["action"]) == key for row in actions):
            return
        actions.append(
            {
                "priority": priority,
                "action": action,
                "reason": reason,
                "basis": basis,
            }
        )

    if not government_sources:
        add(
            "P1",
            "Link an authoritative government/owner record to this asset before treating the report as evidence-backed.",
            "No qualifying government source record was discoverable in the selected-asset report payload.",
            "SIMRAS provenance requirement",
        )

    if asset_type == "bridge":
        if not structural_available:
            add(
                "P1",
                "Obtain and attach a current competent-authority bridge condition inspection with component ratings and defects.",
                "A structural ML result is not eligible from the currently linked evidence.",
                "MoRTH bridge inspection / maintenance guidance",
            )
        if structural_risk is not None and structural_risk >= 70 or health is not None and health <= 40:
            add(
                "P1",
                "Prioritise a detailed engineering inspection and authority review of critical bridge components before maintenance decisions.",
                "SIMRAS structural decision-support output is in a high-concern range.",
                "Model output + MoRTH inspection framework; human engineering review required",
            )
            add(
                "P1",
                "Verify load, scour/waterway and component-condition evidence; consider restrictions only through the responsible authority.",
                "High structural concern should be checked against physical condition and loading evidence.",
                "MoRTH bridge inspection / maintenance practice",
            )
        elif structural_risk is not None and structural_risk >= 40 or health is not None and health < 70:
            add(
                "P2",
                "Schedule a focused condition inspection and close the missing high-value evidence fields.",
                "The decision-support output is not low-concern or has reduced health.",
                "SIMRAS model + MoRTH inspection framework",
            )
        else:
            add(
                "P3",
                "Continue the documented inspection and preventive-maintenance cycle and retain the next approved condition record for local validation.",
                "No high structural concern is indicated by the eligible decision-support layer.",
                "MoRTH inspection / maintenance framework",
            )

    elif asset_type in {"dam", "barrage"}:
        if not structural_available:
            add(
                "P1",
                "Obtain/attach a current qualified dam-safety structural and operational inspection; keep structural health and RUL withheld until then.",
                "Hydrology alone does not establish structural safety.",
                "CWC Guidelines for Safety Inspection of Dams",
            )

        operating_score = operational_risk if operational_risk is not None else hazard
        if operating_score is not None and operating_score >= 70:
            add(
                "P1",
                "Verify current reservoir/river observations directly, inspect gates/spillway readiness, and review the applicable emergency/operating procedures.",
                "Operational/hydrologic decision support is in a high-concern range.",
                "NWDP observations + CWC dam risk/inspection guidance",
            )
        elif operating_score is not None and operating_score >= 40:
            add(
                "P2",
                "Review gate/spillway operation and validate reservoir, rainfall and discharge observations against direct station records.",
                "Operational/hydrologic concern is moderate.",
                "NWDP observations + CWC dam risk/inspection guidance",
            )
        else:
            add(
                "P3",
                "Continue surveillance and refresh reservoir, rainfall and river observations at the source publication cadence.",
                "No high operational/hydrologic concern is indicated by the current source-backed state.",
                "NWDP observations + CWC inspection guidance",
            )

        if any(
            "SPATIAL" in _upper(row.get("quality_flag"))
            or "NEAREST" in _upper(row.get("spatial_method"))
            or row.get("is_estimated") is True
            for row in government_sources
        ):
            add(
                "P2",
                "Use a direct asset/station observation before any operational decision that depends on a spatially transferred hydrology value.",
                "At least one government input is spatially transferred/estimated rather than a direct asset observation.",
                "SIMRAS provenance rule",
            )

    if confidence is not None and confidence < 0.65:
        add(
            "P2",
            "Collect the missing high-value evidence and re-run the model before escalating a model-only recommendation.",
            f"Current model/input confidence is {confidence:.0%}.",
            "SIMRAS model-governance rule",
        )

    if rul.get("status") == "WITHHELD":
        add(
            "P2",
            "Build longitudinal approved inspection/maintenance history before publishing a structural remaining-useful-life estimate.",
            rul.get("reason") or "RUL evidence is insufficient.",
            "SIMRAS RUL governance + longitudinal validation requirement",
        )

    if missing:
        add(
            "P2",
            "Close the report's missing-evidence items in priority order: " + "; ".join(missing[:5]) + ".",
            "These inputs are absent or not linked in the selected-asset evidence payload.",
            "SIMRAS evidence completeness check",
        )

    order = {"P1": 0, "P2": 1, "P3": 2}
    actions.sort(key=lambda row: (order.get(row["priority"], 9), row["action"]))
    return actions


def enrich_report_decision_support(report: dict[str, Any]) -> dict[str, Any]:
    """Add an evidence-backed decision-support section to one selected-asset report.

    This function never invents missing structural measurements and never upgrades
    a research-transfer model into a locally validated model. Government records
    are treated as inputs/provenance; SIMRAS outputs remain SIMRAS decision support.
    """

    if not isinstance(report, dict):
        return report

    twin = _mapping(report.get("twin"))
    asset = _mapping(twin.get("asset"))
    if not asset:
        asset = _mapping(report.get("asset"))

    ai = _mapping(twin.get("ai"))
    if not ai:
        ai = _mapping(report.get("ai"))

    asset_type = (_text(_first(asset, "asset_type", "type")) or "unknown").lower()
    model = _model_info(report, ai)
    method = model.get("prediction_method")

    health_raw = _num(ai.get("health_score"))
    risk_raw = _num(ai.get("risk_score"))
    hazard = _num(ai.get("hazard_score"))
    operational_risk = _num(ai.get("operational_risk_score"))
    operational_confidence = _num(ai.get("operational_confidence"))
    confidence = _confidence(ai, model, asset_type)

    bridge_method_on_nonbridge = asset_type != "bridge" and _is_bridge_ml(method)

    if asset_type == "bridge":
        structural_available = (
            health_raw is not None
            and risk_raw is not None
            and _is_bridge_ml(method)
        )
    else:
        structural_available = (
            health_raw is not None
            and risk_raw is not None
            and bool(model.get("locally_validated"))
            and not bridge_method_on_nonbridge
        )

    health = health_raw if structural_available else None
    structural_risk = risk_raw if structural_available else None

    government_sources, ignored_synthetic = _government_source_records(report)
    rul = _rul_summary(ai, model)

    evidence_requirements = _required_evidence(report, asset_type)
    actions = _actions(
        report,
        asset_type=asset_type,
        health=health,
        structural_risk=structural_risk,
        operational_risk=operational_risk,
        hazard=hazard,
        confidence=confidence,
        structural_available=structural_available,
        government_sources=government_sources,
        rul=rul,
    )

    if bridge_method_on_nonbridge:
        model = {
            **model,
            "prediction_method": method,
            "applicability": "BLOCKED_WRONG_ASSET_CLASS",
        }
    elif structural_available:
        model = {
            **model,
            "applicability": (
                "LOCALLY_VALIDATED"
                if model.get("locally_validated")
                else "RESEARCH_TRANSFER_REAL_INPUTS"
            ),
        }
    elif asset_type in {"dam", "barrage"} and operational_risk is not None:
        model = {
            **model,
            "applicability": "OPERATIONAL_HYDROLOGIC_DECISION_SUPPORT_ONLY",
        }
    else:
        model = {
            **model,
            "applicability": "STRUCTURAL_PREDICTION_WITHHELD",
        }

    report["decision_support"] = {
        "contract_version": "simras-real-evidence-report-v1",
        "asset_code": _text(_first(asset, "asset_code", "id")) or _text(report.get("asset_code")),
        "asset_name": _text(asset.get("name")),
        "asset_type": asset_type,
        "prediction": {
            "structural": {
                "available": structural_available,
                "health_score": round(health, 2) if health is not None else None,
                "risk_score": round(structural_risk, 2) if structural_risk is not None else None,
                "risk_level": _risk_level(structural_risk, ai.get("risk_level")) if structural_available else "WITHHELD",
                "reason": (
                    "Eligible structural model result from linked source-backed inputs."
                    if structural_available
                    else (
                        "Bridge NBI-family ML is not applicable to dams/barrages."
                        if bridge_method_on_nonbridge
                        else "Eligible structural evidence/model validation is insufficient; no structural score is published in this report section."
                    )
                ),
            },
            "operational_hydrologic": {
                "available": operational_risk is not None,
                "risk_score": round(operational_risk, 2) if operational_risk is not None else None,
                "risk_level": _risk_level(operational_risk, ai.get("operational_risk_level")),
                "confidence": (
                    round(max(0.0, min(1.0, operational_confidence)), 3)
                    if operational_confidence is not None
                    else None
                ),
                "method": _text(ai.get("operational_method")),
                "status": _text(ai.get("operational_status")),
            },
            "environmental_hazard": {
                "available": hazard is not None,
                "score": round(hazard, 2) if hazard is not None else None,
                "level": _risk_level(hazard, ai.get("hazard_level")),
            },
            "prediction_confidence": round(confidence, 3) if confidence is not None else None,
            "remaining_useful_life": rul,
        },
        "model": model,
        "government_evidence": {
            "records": government_sources,
            "record_count": len(government_sources),
            "synthetic_or_demo_records_ignored": ignored_synthetic,
            "note": (
                "Only source metadata already linked to the selected asset is treated as asset evidence. "
                "Government guidance links below are references, not measurements for this asset."
            ),
        },
        "required_evidence": evidence_requirements,
        "recommended_actions": actions,
        "government_guidance": _guidance(asset_type),
        "quality": {
            "uses_selected_asset_only": True,
            "missing_values_are_not_fabricated": True,
            "bridge_model_blocked_for_dam_barrage": True,
            "rul_requires_local_longitudinal_validation": True,
            "government_record_is_not_government_prediction": True,
        },
        "disclaimer": (
            "Government/owner records and observations are evidence inputs. "
            "SIMRAS predictions, risk scores and recommendations are decision-support outputs, "
            "not government-issued safety ratings and not a substitute for inspection or a competent engineer's decision."
        ),
    }

    return report
