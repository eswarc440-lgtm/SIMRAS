from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    Asset,
    AssetModel,
    DataSource,
    EnvironmentObservation,
    Inspection,
    Maintenance,
    Prediction,
    Sensor,
)
from app.services.recommendation_engine import build_recommendations
from app.services.risk_engine import RiskInput, RiskResult, score_risk


OFFICIAL_ENVIRONMENT_QUALITY_FLAGS = {
    "OFFICIAL_DIRECT",
    "OFFICIAL_SPATIAL_TRANSFER",
    "OFFICIAL_DERIVED_SPATIAL",
    "OFFICIAL_DERIVED",
    "OFFICIAL_SOURCE",
}


def _freshness(observed_at: datetime | None) -> str:
    if observed_at is None:
        return "NOT_AVAILABLE"
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=UTC)

    hours = (datetime.now(UTC) - observed_at).total_seconds() / 3600.0
    if hours <= 24:
        return "CURRENT"
    if hours <= 24 * 7:
        return f"{int(hours // 24)}_DAYS_OLD"
    return f"{int(hours // (24 * 7))}_WEEKS_OLD"


def _condition_to_rating(
    condition: str | None,
    score: float | None,
) -> float | None:
    if score is not None:
        return max(0.0, min(9.0, float(score) * 9.0 / 100.0))

    return {
        "EXCELLENT": 8.5,
        "HEALTHY": 8.0,
        "GOOD": 7.5,
        "SOUND": 7.5,
        "SATISFACTORY": 7.0,
        "MONITOR": 6.0,
        "FAIR": 5.5,
        "WEAK": 4.0,
        "POOR": 3.5,
        "HIGH_PRIORITY": 2.5,
        "CRITICAL": 1.5,
        "UNSAFE": 1.0,
    }.get((condition or "").strip().upper())


async def get_asset_row(session: AsyncSession, asset_code: str):
    statement = (
        select(
            Asset,
            func.ST_X(Asset.representative_geometry).label("longitude"),
            func.ST_Y(Asset.representative_geometry).label("latitude"),
        )
        .where(Asset.asset_code == asset_code)
        .limit(1)
    )
    row = (await session.execute(statement)).first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Asset {asset_code} was not found",
        )

    return row


async def latest_predictions(
    session: AsyncSession,
    asset_id: int,
) -> dict[str, Prediction]:
    rows = (
        await session.execute(
            select(Prediction)
            .where(Prediction.asset_id == asset_id)
            .order_by(
                Prediction.target,
                desc(Prediction.prediction_time),
                desc(Prediction.id),
            )
        )
    ).scalars()

    latest: dict[str, Prediction] = {}
    for prediction in rows:
        if prediction.target not in latest:
            latest[prediction.target] = prediction

    return latest


async def _active_asset_model(
    session: AsyncSession,
    asset_id: int,
) -> AssetModel | None:
    return (
        await session.execute(
            select(AssetModel)
            .where(
                AssetModel.asset_id == asset_id,
                AssetModel.is_active.is_(True),
            )
            .order_by(
                desc(AssetModel.updated_at),
                desc(AssetModel.id),
            )
            .limit(1)
        )
    ).scalar_one_or_none()


async def _latest_inspection(
    session: AsyncSession,
    asset_id: int,
) -> Inspection | None:
    return (
        await session.execute(
            select(Inspection)
            .where(Inspection.asset_id == asset_id)
            .order_by(
                desc(Inspection.inspection_date),
                desc(Inspection.id),
            )
            .limit(1)
        )
    ).scalar_one_or_none()


async def _latest_maintenance(
    session: AsyncSession,
    asset_id: int,
) -> Maintenance | None:
    return (
        await session.execute(
            select(Maintenance)
            .where(Maintenance.asset_id == asset_id)
            .order_by(
                desc(Maintenance.maintenance_date),
                desc(Maintenance.id),
            )
            .limit(1)
        )
    ).scalar_one_or_none()


async def _trusted_environment(
    session: AsyncSession,
    asset_id: int,
) -> tuple[dict[str, dict[str, Any]], datetime | None]:
    rows = (
        await session.execute(
            select(EnvironmentObservation, DataSource)
            .join(
                DataSource,
                DataSource.id == EnvironmentObservation.source_id,
            )
            .where(
                EnvironmentObservation.asset_id == asset_id,
                EnvironmentObservation.source_type == "GOVERNMENT_TELEMETRY",
            )
            .order_by(
                EnvironmentObservation.variable,
                desc(EnvironmentObservation.observed_at),
                desc(EnvironmentObservation.id),
            )
        )
    ).all()

    environment: dict[str, dict[str, Any]] = {}
    latest_time: datetime | None = None

    for observation, source in rows:
        if observation.quality_flag not in OFFICIAL_ENVIRONMENT_QUALITY_FLAGS:
            continue
        if observation.variable in environment:
            continue

        environment[observation.variable] = {
            "value": observation.value,
            "unit": observation.unit,
            "source": source.name,
            "source_type": observation.source_type,
            "observed_at": observation.observed_at,
            "ingested_at": observation.ingested_at,
            "quality_flag": observation.quality_flag,
            "confidence": observation.confidence_score,
            "is_estimated": observation.is_estimated,
        }

        if latest_time is None or observation.observed_at > latest_time:
            latest_time = observation.observed_at

    return environment, latest_time


def _environment_value(
    environment: dict[str, dict[str, Any]],
    variable: str,
) -> float | None:
    value = environment.get(variable, {}).get("value")
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _prediction_input(
    *,
    asset: Asset,
    inspection: Inspection | None,
    latest_maintenance: Maintenance | None,
    environment: dict[str, dict[str, Any]],
) -> RiskInput:
    condition = inspection.condition if inspection is not None else asset.condition
    inspection_score = inspection.score if inspection is not None else None

    return RiskInput(
        asset_type=asset.asset_type,
        built_year=asset.built_year,
        design_life_years=asset.design_life_years,
        condition=condition,
        inspection_score=inspection_score,
        days_since_inspection=(
            (date.today() - inspection.inspection_date).days
            if inspection is not None
            else None
        ),
        days_since_maintenance=(
            (date.today() - latest_maintenance.maintenance_date).days
            if latest_maintenance is not None
            else None
        ),
        rainfall_mm_24h=_environment_value(environment, "rainfall_24h"),
        rainfall_mm_7d=_environment_value(environment, "rainfall_7d"),
        water_level_anomaly_m=_environment_value(
            environment,
            "water_level_anomaly",
        ),
        source_confidence=asset.confidence_score,
    )


def _default_dimensions(asset_type: str | None) -> dict[str, Any]:
    """Return metadata only for an L0 illustrative twin.

    Numeric fallback proportions live only in the renderer. They are never
    returned as engineering dimensions unless a source-backed AssetModel exists.
    """
    return {
        "representation": "illustrative_type_model_not_measured",
    }


def _effective_dimensions(
    asset: Asset,
    model: AssetModel | None,
) -> dict[str, Any]:
    if model is not None and model.dimensions:
        dimensions = dict(model.dimensions)
        representation = str(
            dimensions.get("representation") or ""
        ).lower()

        if representation == "illustrative_default_not_measured":
            return _default_dimensions(asset.asset_type)

        return dimensions

    return _default_dimensions(asset.asset_type)


async def persist_ml_prediction(
    session: AsyncSession,
    asset_id: int,
    prediction: RiskResult,
) -> list[Prediction]:
    """Persist the current transparent SIMRAS health/risk prediction."""

    prediction_time = datetime.now(UTC)

    common = {
        "asset_id": asset_id,
        "prediction_time": prediction_time,
        "confidence_score": prediction.confidence,
        "model_version": prediction.model_version,
        "feature_version": prediction.feature_version,
        "status": prediction.status,
        "factors": prediction.factors,
    }

    rows = [
        Prediction(
            **common,
            target="health",
            value=prediction.health_score,
            predicted_class=None,
            lower_bound=None,
            upper_bound=None,
        ),
        Prediction(
            **common,
            target="risk",
            value=prediction.risk_score,
            predicted_class=prediction.risk_level,
            lower_bound=None,
            upper_bound=None,
        ),
        Prediction(
            **common,
            target="rul",
            value=None,
            predicted_class="DISABLED",
            lower_bound=None,
            upper_bound=None,
        ),
    ]

    session.add_all(rows)
    await session.flush()
    return rows


async def refresh_ml_prediction(
    session: AsyncSession,
    asset_code: str,
) -> dict[str, Any]:
    """Refresh and persist the SIMRAS multifactor prediction.

    The old function name is retained for API compatibility.
    """

    row = await get_asset_row(session, asset_code)
    asset, _, _ = row

    inspection = await _latest_inspection(session, asset.id)
    maintenance = await _latest_maintenance(session, asset.id)
    environment, _ = await _trusted_environment(session, asset.id)

    risk_input = _prediction_input(
        asset=asset,
        inspection=inspection,
        latest_maintenance=maintenance,
        environment=environment,
    )
    prediction = score_risk(risk_input, allow_estimated_health=True)

    rows = await persist_ml_prediction(
        session,
        asset.id,
        prediction,
    )
    await session.commit()

    for item in rows:
        await session.refresh(item)

    condition_rating = _condition_to_rating(
        risk_input.condition,
        risk_input.inspection_score,
    )

    recommendations = build_recommendations(
        condition_rating=condition_rating,
        health_score=prediction.health_score,
        risk_score=prediction.risk_score,
        risk_level=prediction.risk_level,
        hazard_level=prediction.hazard_level,
        rul_years=None,
        confidence=prediction.confidence,
        model_validated=False,
        asset_type=asset.asset_type,
        has_structural_evidence=(
            bool(risk_input.condition)
            or risk_input.inspection_score is not None
        ),
        factors=prediction.factors,
    )

    return {
        "status": "saved",
        "asset": {
            "id": asset.id,
            "asset_code": asset.asset_code,
            "name": asset.name,
            "asset_type": asset.asset_type,
        },
        "model": {
            "model_name": "simras_multifactor_health",
            "version": prediction.model_version,
            "feature_version": prediction.feature_version,
            "stage": prediction.status,
            "model_validated": False,
            "training_scope": "ANDHRA_PRADESH_TRANSPARENT_DECISION_SUPPORT",
        },
        "prediction": {
            "health_score": prediction.health_score,
            "health_lower_bound": None,
            "health_upper_bound": None,
            "risk_score": prediction.risk_score,
            "risk_level": prediction.risk_level,
            "hazard_score": prediction.hazard_score,
            "hazard_level": prediction.hazard_level,
            "remaining_life_years": None,
            "rul_lower_bound": None,
            "rul_upper_bound": None,
            "confidence": prediction.confidence,
            "prediction_method": prediction.prediction_method,
            "forecast_horizon_years": None,
        },
        "database_rows": [
            {
                "id": item.id,
                "target": item.target,
                "value": item.value,
                "predicted_class": item.predicted_class,
                "confidence": item.confidence_score,
                "model_version": item.model_version,
                "status": item.status,
                "prediction_time": item.prediction_time,
            }
            for item in rows
        ],
        "factors": prediction.factors,
        "recommendations": recommendations,
        "warning": (
            "Research decision support only; not an official structural rating."
        ),
    }


async def build_asset_summary(
    session: AsyncSession,
    row,
) -> dict[str, Any]:
    asset, longitude, latitude = row

    # Fast registry ranking. Full twin adds environment/inspection/maintenance.
    prediction = score_risk(
        RiskInput(
            asset_type=asset.asset_type,
            built_year=asset.built_year,
            design_life_years=asset.design_life_years,
            condition=asset.condition,
            source_confidence=asset.confidence_score,
        ),
        allow_estimated_health=True,
    )

    return {
        "asset_code": asset.asset_code,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "subtype": asset.subtype,
        "district": asset.district,
        "identity_status": asset.identity_status,
        "condition": asset.condition,
        "geometry": {
            "type": "Point",
            "coordinates": (longitude, latitude),
        },
        "risk_score": prediction.risk_score,
        "risk_level": prediction.risk_level,
        "data_confidence": asset.confidence_score,
    }


async def build_twin(
    session: AsyncSession,
    asset_code: str,
) -> dict[str, Any]:
    row = await get_asset_row(session, asset_code)
    asset, _, _ = row

    summary = await build_asset_summary(session, row)
    model = await _active_asset_model(session, asset.id)
    inspection = await _latest_inspection(session, asset.id)
    latest_maintenance = await _latest_maintenance(session, asset.id)

    maintenance_rows = (
        await session.execute(
            select(Maintenance)
            .where(Maintenance.asset_id == asset.id)
            .order_by(
                desc(Maintenance.maintenance_date),
                desc(Maintenance.id),
            )
            .limit(10)
        )
    ).scalars().all()

    environment, latest_env_time = await _trusted_environment(
        session,
        asset.id,
    )

    risk_input = _prediction_input(
        asset=asset,
        inspection=inspection,
        latest_maintenance=latest_maintenance,
        environment=environment,
    )
    prediction = score_risk(risk_input, allow_estimated_health=True)

    condition_rating = _condition_to_rating(
        risk_input.condition,
        risk_input.inspection_score,
    )

    recommendations = build_recommendations(
        condition_rating=condition_rating,
        health_score=prediction.health_score,
        risk_score=prediction.risk_score,
        risk_level=prediction.risk_level,
        hazard_level=prediction.hazard_level,
        rul_years=None,
        confidence=prediction.confidence,
        model_validated=False,
        asset_type=asset.asset_type,
        has_structural_evidence=(
            bool(risk_input.condition)
            or risk_input.inspection_score is not None
        ),
        factors=prediction.factors,
    )

    dimensions = _effective_dimensions(asset, model)

    sensor_count = await session.scalar(
        select(func.count())
        .select_from(Sensor)
        .where(Sensor.asset_id == asset.id)
    )

    ai = {
        **prediction.to_dict(),
        "health_lower_bound": None,
        "health_upper_bound": None,
        "rul_lower_bound": None,
        "rul_upper_bound": None,
        "training_scope": "ANDHRA_PRADESH_TRANSPARENT_MULTIFACTOR_DECISION_SUPPORT",
        "forecast_horizon_years": None,
        "recommendations": recommendations,
        "prediction_time": datetime.now(UTC),
    }

    # SIMRAS_FINAL_RUL_PROXY
    # Transparent planning-life proxy. Not an official structural-life rating.
    if ai.get("remaining_life_years") is None:
        rul_horizon = None
        rul_basis = None
        rul_basis_url = None
        rul_confidence = None
        rul_status = "INSUFFICIENT_INPUTS"

        if asset.built_year is not None:
            if asset.design_life_years is not None and asset.design_life_years > 0:
                rul_horizon = float(asset.design_life_years)
                rul_basis = "Asset-stated design life"
                rul_confidence = 0.55
                rul_status = "EXPERIMENTAL_ASSET_DESIGN_LIFE"
            elif str(asset.asset_type or "").lower() in {"dam", "barrage"}:
                # CWC general guidance: planned useful life is 100 years for
                # irrigation/multipurpose projects. This is a generic planning
                # horizon, not an asset-specific certified design life.
                rul_horizon = 100.0
                rul_basis = (
                    "CWC general planning guidance: 100-year useful-life "
                    "horizon for irrigation/multipurpose projects"
                )
                rul_basis_url = "https://cwc.gov.in/sites/default/files/nwauser/chap5.pdf"
                rul_confidence = 0.35
                rul_status = "EXPERIMENTAL_CWC_PLANNING_HORIZON"

        if rul_horizon is not None and asset.built_year is not None:
            age = max(0.0, float(datetime.now(UTC).year - asset.built_year))
            rul_value = max(0.0, rul_horizon - age)
            uncertainty = 0.25 if rul_status == "EXPERIMENTAL_ASSET_DESIGN_LIFE" else 0.30
            ai["remaining_life_years"] = round(rul_value, 1)
            ai["rul_lower_bound"] = round(max(0.0, rul_value * (1.0 - uncertainty)), 1)
            ai["rul_upper_bound"] = round(min(rul_horizon, rul_value * (1.0 + uncertainty)), 1)
        else:
            ai["remaining_life_years"] = None
            ai["rul_lower_bound"] = None
            ai["rul_upper_bound"] = None

        ai["rul_status"] = rul_status
        ai["rul_basis"] = rul_basis or "Built year and design-life basis are required"
        ai["rul_basis_url"] = rul_basis_url
        ai["rul_confidence"] = rul_confidence


    return {
        "asset": summary,
        "static": {
            "owner": asset.owner,
            "built_year": asset.built_year,
            "design_life_years": asset.design_life_years,
            "material": asset.material,
            "status": asset.status,
            "is_estimated": asset.is_estimated,
        },
        "twin": {
            "format": model.format if model is not None else "procedural",
            "uri": model.model_uri if model is not None else None,
            "version": model.version if model is not None else "procedural-v1",
            "fidelity_level": model.fidelity_level if model is not None else "L0",
            "model_source": (
                model.model_source
                if model is not None
                else "SIMRAS procedural illustration - not measured geometry"
            ),
            "source_url": model.source_url if model is not None else None,
            "dimensions": dimensions,
            "is_asset_specific": (
                bool(model.is_asset_specific)
                if model is not None
                else False
            ),
            "heading_deg": model.heading_deg if model is not None else None,
            "elevation_m": model.elevation_m if model is not None else None,
            "horizontal_accuracy_m": (
                model.horizontal_accuracy_m
                if model is not None
                else None
            ),
        },
        "environment": environment,
        "inspection": {
            "inspection_date": (
                inspection.inspection_date
                if inspection is not None
                else None
            ),
            "condition": (
                inspection.condition
                if inspection is not None
                else asset.condition
            ),
            "score": inspection.score if inspection is not None else None,
            "quality_flag": (
                inspection.quality_flag
                if inspection is not None
                else "NOT_AVAILABLE"
            ),
            "is_synthetic": (
                inspection.is_synthetic
                if inspection is not None
                else False
            ),
        },
        "maintenance": [
            {
                "date": item.maintenance_date,
                "action": item.action,
                "status": item.status,
                "next_due": item.next_due,
                "is_synthetic": item.is_synthetic,
            }
            for item in maintenance_rows
        ],
        "sensors_status": "CONNECTED" if sensor_count else "NOT_INSTRUMENTED",
        "ai": ai,
        "freshness": {
            "asset_metadata": _freshness(asset.updated_at),
            "environment": _freshness(latest_env_time),
            "inspection": _freshness(
                datetime.combine(
                    inspection.inspection_date,
                    datetime.min.time(),
                    tzinfo=UTC,
                )
                if inspection is not None
                else None
            ),
            "sensors": "CURRENT" if sensor_count else "NOT_AVAILABLE",
        },
        "generated_at": datetime.now(UTC),
    }
