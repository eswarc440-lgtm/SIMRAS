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
from app.services.ml_predictor import (
    MLInput,
    condition_to_rating,
    predict_bridge,
)
from app.services.recommendation_engine import build_recommendations
from app.services.risk_engine import RiskInput, score_risk


# ============================================================
# Freshness helper
# ============================================================


def _freshness(observed_at: datetime | None) -> str:
    if observed_at is None:
        return "NOT_AVAILABLE"

    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=UTC)

    hours = (datetime.now(UTC) - observed_at).total_seconds() / 3600

    if hours <= 24:
        return "CURRENT"

    if hours <= 24 * 7:
        return f"{int(hours // 24)}_DAYS_OLD"

    return f"{int(hours // (24 * 7))}_WEEKS_OLD"


# ============================================================
# Asset lookup
# ============================================================


async def get_asset_row(
    session: AsyncSession,
    asset_code: str,
):
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


# ============================================================
# Prediction retrieval
# ============================================================


async def latest_predictions(
    session: AsyncSession,
    asset_id: int,
) -> dict[str, Prediction]:
    """
    Return the newest database prediction for every target.

    Example:
        health -> latest health row
        risk   -> latest risk row
        rul    -> latest RUL row
    """

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


# ============================================================
# ML prediction persistence
# ============================================================


async def persist_ml_prediction(
    session: AsyncSession,
    asset_id: int,
    prediction,
) -> list[Prediction]:
    """
    Persist one bridge ML inference as three prediction rows:

        health
        risk
        rul

    Historical predictions are intentionally preserved.
    """

    prediction_time = datetime.now(UTC)

    common_fields = {
        "asset_id": asset_id,
        "prediction_time": prediction_time,
        "confidence_score": prediction.confidence,
        "model_version": prediction.model_version,
        "feature_version": prediction.feature_version,
        "status": prediction.status,
        "factors": prediction.factors,
    }

    health_prediction = Prediction(
        **common_fields,
        target="health",
        value=prediction.health_score,
        predicted_class=None,
        lower_bound=prediction.health_lower_bound,
        upper_bound=prediction.health_upper_bound,
    )

    risk_prediction = Prediction(
        **common_fields,
        target="risk",
        value=prediction.risk_score,
        predicted_class=prediction.risk_level,
        lower_bound=None,
        upper_bound=None,
    )

    rul_prediction = Prediction(
        **common_fields,
        target="rul",
        value=prediction.remaining_life_years,
        predicted_class=(
            "VALIDATED"
            if prediction.model_validated
            else "EXPERIMENTAL"
        ),
        lower_bound=prediction.rul_lower_bound,
        upper_bound=prediction.rul_upper_bound,
    )

    rows = [
        health_prediction,
        risk_prediction,
        rul_prediction,
    ]

    session.add_all(rows)

    # Send INSERTs to PostgreSQL without committing yet.
    await session.flush()

    return rows


# ============================================================
# Explicit ML refresh
# ============================================================


async def refresh_ml_prediction(
    session: AsyncSession,
    asset_code: str,
) -> dict[str, Any]:
    """
    Run the accepted bridge deterioration ML model for one asset
    and persist health, risk and experimental RUL predictions.

    This function is intended for an explicit POST refresh endpoint.
    It is NOT automatically called whenever the twin GET endpoint
    is opened.
    """

    row = await get_asset_row(
        session=session,
        asset_code=asset_code,
    )

    asset, _, _ = row

    # --------------------------------------------------------
    # Current ML artifact is bridge-only
    # --------------------------------------------------------

    if not asset.asset_type or asset.asset_type.lower() != "bridge":
        raise HTTPException(
            status_code=400,
            detail={
                "status": "UNSUPPORTED_ASSET_TYPE",
                "asset_code": asset.asset_code,
                "asset_type": asset.asset_type,
                "message": (
                    "The currently registered deterioration ML model "
                    "supports bridges only."
                ),
            },
        )

    # --------------------------------------------------------
    # Active asset-specific / procedural model
    # --------------------------------------------------------

    model = (
        await session.execute(
            select(AssetModel)
            .where(
                AssetModel.asset_id == asset.id,
                AssetModel.is_active.is_(True),
            )
            .order_by(
                desc(AssetModel.updated_at),
                desc(AssetModel.id),
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    dimensions = (
        model.dimensions
        if model is not None and model.dimensions
        else {}
    )

    # --------------------------------------------------------
    # Latest inspection
    # --------------------------------------------------------

    inspection = (
        await session.execute(
            select(Inspection)
            .where(Inspection.asset_id == asset.id)
            .order_by(
                desc(Inspection.inspection_date),
                desc(Inspection.id),
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    condition = (
        inspection.condition
        if inspection is not None
        else asset.condition
    )

    inspection_score = (
        inspection.score
        if inspection is not None
        else None
    )

    condition_rating = condition_to_rating(
        condition,
        inspection_score,
    )

    age_years = (
        datetime.now(UTC).year - asset.built_year
        if asset.built_year is not None
        else None
    )

    # --------------------------------------------------------
    # ML feature assembly
    # --------------------------------------------------------

    ml_input = MLInput(
        asset_type=asset.asset_type,
        age_years=age_years,
        condition_rating=condition_rating,
        material=asset.material,
        span_count=dimensions.get("span_count"),
        max_span_m=(
            dimensions.get("main_span_m")
            or dimensions.get("max_span_m")
        ),
        structure_length_m=dimensions.get("length_m"),
    )

    # --------------------------------------------------------
    # Run bridge ML artifact
    # --------------------------------------------------------

    ml_prediction = predict_bridge(ml_input)

    # --------------------------------------------------------
    # Insufficient-data protection
    # --------------------------------------------------------

    if ml_prediction is None:
        missing_fields: list[str] = []

        if age_years is None:
            missing_fields.append("built_year")

        if condition_rating is None:
            missing_fields.append(
                "condition_or_inspection_score"
            )

        raise HTTPException(
            status_code=422,
            detail={
                "status": "INSUFFICIENT_DATA",
                "asset_code": asset.asset_code,
                "asset_name": asset.name,
                "missing_fields": missing_fields,
                "message": (
                    "The bridge ML model could not produce a prediction "
                    "using the currently available evidence."
                ),
            },
        )

    # --------------------------------------------------------
    # Persist prediction
    # --------------------------------------------------------

    rows = await persist_ml_prediction(
        session=session,
        asset_id=asset.id,
        prediction=ml_prediction,
    )

    await session.commit()

    # Reload generated IDs and persisted database values.
    for prediction_row in rows:
        await session.refresh(prediction_row)

    # --------------------------------------------------------
    # API response
    # --------------------------------------------------------

    return {
        "status": "saved",
        "asset": {
            "id": asset.id,
            "asset_code": asset.asset_code,
            "name": asset.name,
            "asset_type": asset.asset_type,
        },
        "model": {
            "model_name": "simras_nbi_bridge_deterioration",
            "version": ml_prediction.model_version,
            "feature_version": ml_prediction.feature_version,
            "stage": ml_prediction.status,
            "model_validated": ml_prediction.model_validated,
            "training_scope": ml_prediction.training_scope,
        },
        "prediction": {
            "health_score": ml_prediction.health_score,
            "health_lower_bound": (
                ml_prediction.health_lower_bound
            ),
            "health_upper_bound": (
                ml_prediction.health_upper_bound
            ),
            "risk_score": ml_prediction.risk_score,
            "risk_level": ml_prediction.risk_level,
            "remaining_life_years": (
                ml_prediction.remaining_life_years
            ),
            "rul_lower_bound": (
                ml_prediction.rul_lower_bound
            ),
            "rul_upper_bound": (
                ml_prediction.rul_upper_bound
            ),
            "confidence": ml_prediction.confidence,
            "prediction_method": (
                ml_prediction.prediction_method
            ),
            "forecast_horizon_years": (
                ml_prediction.forecast_horizon_years
            ),
        },
        "database_rows": [
            {
                "id": prediction_row.id,
                "target": prediction_row.target,
                "value": prediction_row.value,
                "predicted_class": (
                    prediction_row.predicted_class
                ),
                "lower_bound": (
                    prediction_row.lower_bound
                ),
                "upper_bound": (
                    prediction_row.upper_bound
                ),
                "confidence": (
                    prediction_row.confidence_score
                ),
                "model_version": (
                    prediction_row.model_version
                ),
                "feature_version": (
                    prediction_row.feature_version
                ),
                "status": prediction_row.status,
                "prediction_time": (
                    prediction_row.prediction_time
                ),
            }
            for prediction_row in rows
        ],
        "factors": ml_prediction.factors,
        "recommendations": (
            ml_prediction.recommendations
        ),
        "warning": (
            "Research decision support only. "
            "Model has not been locally validated for Andhra Pradesh."
            if not ml_prediction.model_validated
            else None
        ),
    }


# ============================================================
# Asset summary
# ============================================================


async def build_asset_summary(
    session: AsyncSession,
    row,
) -> dict[str, Any]:
    asset, longitude, latitude = row

    predictions = await latest_predictions(
        session=session,
        asset_id=asset.id,
    )

    risk = predictions.get("risk")

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
            "coordinates": (
                longitude,
                latitude,
            ),
        },
        "risk_score": (
            risk.value
            if risk is not None
            else None
        ),
        "risk_level": (
            risk.predicted_class
            if risk is not None
            else None
        ),
        "data_confidence": asset.confidence_score,
    }


# ============================================================
# Complete Digital Twin
# ============================================================


async def build_twin(
    session: AsyncSession,
    asset_code: str,
) -> dict[str, Any]:
    row = await get_asset_row(
        session=session,
        asset_code=asset_code,
    )

    asset, _, _ = row

    summary = await build_asset_summary(
        session=session,
        row=row,
    )

    # --------------------------------------------------------
    # Active 3D model
    # --------------------------------------------------------

    model = (
        await session.execute(
            select(AssetModel)
            .where(
                AssetModel.asset_id == asset.id,
                AssetModel.is_active.is_(True),
            )
            .order_by(
                desc(AssetModel.updated_at),
                desc(AssetModel.id),
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    # --------------------------------------------------------
    # Latest inspection
    # --------------------------------------------------------

    inspection = (
        await session.execute(
            select(Inspection)
            .where(Inspection.asset_id == asset.id)
            .order_by(
                desc(Inspection.inspection_date),
                desc(Inspection.id),
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    # --------------------------------------------------------
    # Maintenance
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Environmental observations
    # --------------------------------------------------------

    env_rows = (
        await session.execute(
            select(
                EnvironmentObservation,
                DataSource,
            )
            .join(
                DataSource,
                DataSource.id
                == EnvironmentObservation.source_id,
            )
            .where(
                EnvironmentObservation.asset_id
                == asset.id
            )
            .order_by(
                EnvironmentObservation.variable,
                desc(
                    EnvironmentObservation.observed_at
                ),
            )
        )
    ).all()

    environment: dict[str, dict[str, Any]] = {}

    latest_env_time: datetime | None = None

    for observation, source in env_rows:
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

        if (
            latest_env_time is None
            or observation.observed_at
            > latest_env_time
        ):
            latest_env_time = observation.observed_at

    rainfall_24h = environment.get(
        "rainfall_24h",
        {},
    ).get("value")

    rainfall_7d = environment.get(
        "rainfall_7d",
        {},
    ).get("value")

    water_anomaly = environment.get(
        "water_level_anomaly",
        {},
    ).get("value")

    # --------------------------------------------------------
    # Structural state
    # --------------------------------------------------------

    condition = (
        inspection.condition
        if inspection is not None
        else asset.condition
    )

    inspection_score = (
        inspection.score
        if inspection is not None
        else None
    )

    # --------------------------------------------------------
    # Engineering baseline
    # --------------------------------------------------------

    baseline = score_risk(
        RiskInput(
            built_year=asset.built_year,
            design_life_years=(
                asset.design_life_years
            ),
            condition=condition,
            inspection_score=inspection_score,
            days_since_inspection=(
                (
                    date.today()
                    - inspection.inspection_date
                ).days
                if inspection is not None
                else None
            ),
            rainfall_mm_24h=rainfall_24h,
            rainfall_mm_7d=rainfall_7d,
            water_level_anomaly_m=water_anomaly,
            source_confidence=(
                asset.confidence_score
            ),
        )
    )

    # --------------------------------------------------------
    # ML feature construction
    # --------------------------------------------------------

    dimensions = (
        model.dimensions
        if model is not None and model.dimensions
        else {}
    )

    condition_rating = condition_to_rating(
        condition,
        inspection_score,
    )

    age_years = (
        datetime.now(UTC).year - asset.built_year
        if asset.built_year is not None
        else None
    )

    # --------------------------------------------------------
    # Live inference for the Twin display
    #
    # IMPORTANT:
    # This does NOT persist another DB row.
    # Persistence happens only through refresh_ml_prediction().
    # --------------------------------------------------------

    ml_prediction = predict_bridge(
        MLInput(
            asset_type=asset.asset_type,
            age_years=age_years,
            condition_rating=condition_rating,
            material=asset.material,
            span_count=dimensions.get("span_count"),
            max_span_m=(
                dimensions.get("main_span_m")
                or dimensions.get("max_span_m")
            ),
            structure_length_m=(
                dimensions.get("length_m")
            ),
        )
    )

    # --------------------------------------------------------
    # AI state
    # --------------------------------------------------------

    if ml_prediction is not None:
        ai = {
            **ml_prediction.to_dict(),
            "hazard_score": baseline.hazard_score,
            "hazard_level": baseline.hazard_level,
            "prediction_time": datetime.now(UTC),
        }

    else:
        recommendations = build_recommendations(
            condition_rating=condition_rating,
            risk_score=baseline.risk_score,
            rul_years=None,
            confidence=baseline.confidence,
            model_validated=False,
        )

        ai = {
            **baseline.to_dict(),
            "health_lower_bound": None,
            "health_upper_bound": None,
            "rul_lower_bound": None,
            "rul_upper_bound": None,
            "training_scope": (
                "ASSET_SPECIFIC_ENGINEERING_RULES"
            ),
            "forecast_horizon_years": None,
            "recommendations": recommendations,
            "prediction_time": datetime.now(UTC),
        }

    # --------------------------------------------------------
    # Sensor status
    # --------------------------------------------------------

    sensor_count = await session.scalar(
        select(func.count())
        .select_from(Sensor)
        .where(Sensor.asset_id == asset.id)
    )

    # --------------------------------------------------------
    # Final Twin payload
    # --------------------------------------------------------

    return {
        "asset": summary,

        "static": {
            "owner": asset.owner,
            "built_year": asset.built_year,
            "design_life_years": (
                asset.design_life_years
            ),
            "material": asset.material,
            "status": asset.status,
            "is_estimated": asset.is_estimated,
        },

        "twin": {
            "format": (
                model.format
                if model is not None
                else "procedural"
            ),
            "uri": (
                model.model_uri
                if model is not None
                else None
            ),
            "version": (
                model.version
                if model is not None
                else "1"
            ),
            "fidelity_level": (
                model.fidelity_level
                if model is not None
                else "L0"
            ),
            "model_source": (
                model.model_source
                if model is not None
                else "procedural illustration"
            ),
            "source_url": (
                model.source_url
                if model is not None
                else None
            ),
            "dimensions": (
                model.dimensions
                if model is not None
                else {}
            ),
            "is_asset_specific": (
                model.is_asset_specific
                if model is not None
                else False
            ),
            "heading_deg": (
                model.heading_deg
                if model is not None
                else None
            ),
            "elevation_m": (
                model.elevation_m
                if model is not None
                else None
            ),
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
            "score": (
                inspection.score
                if inspection is not None
                else None
            ),
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

        "sensors_status": (
            "CONNECTED"
            if sensor_count
            else "NOT_INSTRUMENTED"
        ),

        "ai": ai,

        "freshness": {
            "asset_metadata": _freshness(
                asset.updated_at
            ),
            "environment": _freshness(
                latest_env_time
            ),
            "inspection": _freshness(
                datetime.combine(
                    inspection.inspection_date,
                    datetime.min.time(),
                    tzinfo=UTC,
                )
                if inspection is not None
                else None
            ),
            "sensors": (
                "CURRENT"
                if sensor_count
                else "NOT_AVAILABLE"
            ),
        },

        "generated_at": datetime.now(UTC),
    }