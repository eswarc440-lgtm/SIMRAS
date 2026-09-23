from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import EnvironmentObservation, Prediction
from app.services.dam_hydrology_risk import score_dam_barrage_operational_risk


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _risk_level(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def resolve_current_risk_snapshot(
    *,
    asset_type: str | None,
    persisted_risk: Prediction | Any | None,
    environment: dict[str, dict[str, Any]] | None,
    dimensions: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve the reportable current risk without fabricating missing values.

    DAM/BARRAGE operational hydrologic decision support takes precedence when
    current usable hydrologic evidence exists. Other categories use the latest
    persisted category prediction when available. An unavailable risk remains
    explicitly NOT_AVAILABLE rather than being converted to zero/LOW.
    """

    category = str(asset_type or "").strip().lower()
    environment = environment or {}
    dimensions = dimensions or {}

    if category in {"dam", "barrage"}:
        operational = score_dam_barrage_operational_risk(
            asset_type=category,
            environment=environment,
            dimensions=dimensions,
        )
        if operational is not None and operational.operational_risk_score is not None:
            observed_times = [
                row.get("observed_at")
                for row in environment.values()
                if isinstance(row, dict) and row.get("observed_at") is not None
            ]
            source_time = max(observed_times) if observed_times else None
            return {
                "available": True,
                "risk_score": float(operational.operational_risk_score),
                "risk_level": operational.operational_risk_level,
                "confidence": operational.operational_confidence,
                "risk_method": operational.operational_method,
                "risk_scope": "OPERATIONAL_HYDROLOGIC",
                "source_timestamp": _iso(source_time),
                "status": operational.operational_status,
            }

    value = getattr(persisted_risk, "value", None) if persisted_risk is not None else None
    if value is not None:
        score = float(value)
        predicted_class = getattr(persisted_risk, "predicted_class", None)
        status = str(getattr(persisted_risk, "status", None) or "PERSISTED")
        model_version = getattr(persisted_risk, "model_version", None)
        return {
            "available": True,
            "risk_score": score,
            "risk_level": predicted_class or _risk_level(score),
            "confidence": getattr(persisted_risk, "confidence_score", None),
            "risk_method": model_version or "persisted_category_prediction",
            "risk_scope": "STRUCTURAL_MODEL" if category == "bridge" else "CATEGORY_MODEL",
            "source_timestamp": _iso(getattr(persisted_risk, "prediction_time", None)),
            "status": status,
        }

    return {
        "available": False,
        "risk_score": None,
        "risk_level": "NOT_AVAILABLE",
        "confidence": None,
        "risk_method": None,
        "risk_scope": "STRUCTURAL" if category in {"airport", "temple"} else "CURRENT_RISK",
        "source_timestamp": None,
        "status": "NOT_AVAILABLE",
    }


async def load_latest_environment(
    *,
    session: AsyncSession,
    asset_id: int,
) -> dict[str, dict[str, Any]]:
    """Load the newest non-future observation for every variable of one asset."""

    rows = (
        await session.execute(
            select(EnvironmentObservation)
            .where(EnvironmentObservation.asset_id == asset_id)
            .order_by(
                EnvironmentObservation.variable,
                desc(EnvironmentObservation.observed_at),
                desc(EnvironmentObservation.id),
            )
        )
    ).scalars().all()

    latest: dict[str, dict[str, Any]] = {}
    now = datetime.now(UTC)

    for observation in rows:
        observed_at = observation.observed_at
        if observed_at is not None:
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=UTC)
            if observed_at > now:
                continue

        variable = str(observation.variable)
        if variable in latest:
            continue

        latest[variable] = {
            "value": observation.value,
            "unit": observation.unit,
            "observed_at": observed_at,
            "ingested_at": observation.ingested_at,
            "quality_flag": observation.quality_flag,
            "confidence": observation.confidence_score,
            "is_estimated": observation.is_estimated,
            "source_type": observation.source_type,
        }

    return latest
