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
    ModelRegistry,
    Prediction,
    Sensor,
)
from app.services.ml_predictor import (
    MLInput,
    condition_to_rating,
    predict_asset,
    predict_bridge,
    predict_bridge_sparse,
)
from app.services.recommendation_engine import build_recommendations
from app.services.risk_engine import RiskInput, score_risk
from app.services.dam_hydrology_risk import score_dam_barrage_operational_risk
from app.services.current_risk_service import (
    load_latest_environment,
    resolve_current_risk_snapshot,
)


BRIDGE_MODEL_NAME = "simras_nbi_bridge_deterioration"


# ============================================================
# Freshness
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
# Latest predictions
# ============================================================


async def latest_predictions(
    session: AsyncSession,
    asset_id: int,
) -> dict[str, Prediction]:
    """
    Return the newest persisted prediction for every target.

    Example:
        health -> latest health prediction
        risk   -> latest risk prediction
        rul    -> latest RUL prediction
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
# Persist ML prediction
# ============================================================


async def persist_ml_prediction(
    session: AsyncSession,
    asset_id: int,
    prediction,
) -> list[Prediction]:
    """
    Persist one bridge ML inference.

    Three independent records are created:
        health
        risk
        rul

    Existing prediction history is never deleted.
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

    health_row = Prediction(
        **common_fields,
        target="health",
        value=prediction.health_score,
        predicted_class=None,
        lower_bound=prediction.health_lower_bound,
        upper_bound=prediction.health_upper_bound,
    )

    risk_row = Prediction(
        **common_fields,
        target="risk",
        value=prediction.risk_score,
        predicted_class=prediction.risk_level,
        lower_bound=None,
        upper_bound=None,
    )

    rul_row = Prediction(
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
        health_row,
        risk_row,
        rul_row,
    ]

    session.add_all(rows)

    # Execute INSERTs, but leave commit responsibility
    # with the caller.
    await session.flush()

    return rows


# ============================================================
# Active asset model
# ============================================================


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


def twin_quality_metadata(
    model: AssetModel | None,
    asset_type: str,
) -> dict[str, Any]:
    """Return an auditable presentation rank for an active twin model.

    The score ranks source-backed, asset-specific geometry ahead of generic
    L0 illustrations. It is a visualization-readiness score, not structural
    condition, safety, or engineering-certification evidence.
    """

    if model is None:
        return {
            "twin_quality_score": 0,
            "twin_quality": "BASIC",
            "twin_group": "BASIC",
            "twin_quality_label": "No active 3D model",
            "twin_fidelity": "L0",
            "twin_source_backed": False,
            "twin_dimension_count": 0,
            "twin_template": asset_type or "generic",
        }

    fidelity = (model.fidelity_level or "L0").upper()
    dimensions = model.dimensions or {}
    dimension_count = len(
        [value for value in dimensions.values() if value not in (None, "")]
    )
    source_backed = bool(
        model.source_url
        and model.model_source
        and "procedural illustration" not in model.model_source.lower()
    )

    score = {
        "L0": 10,
        "L1": 55,
        "L2": 75,
        "L3": 90,
        "L4": 95,
    }.get(fidelity, 10)
    score += 15 if model.is_asset_specific else 0
    score += 8 if source_backed else 0
    score += min(dimension_count * 2, 12)
    score = min(score, 100)

    if score >= 80:
        quality = "EXCELLENT"
        group = "BEST"
        label = "Source-backed asset-specific twin"
    elif score >= 60:
        quality = "READY"
        group = "BEST"
        label = "Asset-specific twin with usable dimensions"
    elif score >= 35:
        quality = "PARTIAL"
        group = "IMPROVING"
        label = "Partial geometry; additional evidence required"
    else:
        quality = "BASIC"
        group = "BASIC"
        label = "Generic L0 visualization fallback"

    representation = str(dimensions.get("representation") or asset_type or "generic")

    return {
        "twin_quality_score": score,
        "twin_quality": quality,
        "twin_group": group,
        "twin_quality_label": label,
        "twin_fidelity": fidelity,
        "twin_source_backed": source_backed,
        "twin_dimension_count": dimension_count,
        "twin_template": representation,
    }


# ============================================================
# Latest inspection
# ============================================================


async def _latest_inspection(
    session: AsyncSession,
    asset_id: int,
) -> Inspection | None:
    # Return newest source-backed inspection eligible for structural ML.
    # Synthetic/demo rows remain in PostgreSQL for audit/history but cannot
    # establish the structural state used by ML inference.
    rows = (
        await session.execute(
            select(Inspection)
            .where(Inspection.asset_id == asset_id)
            .order_by(
                desc(Inspection.inspection_date),
                desc(Inspection.id),
            )
            .limit(100)
        )
    ).scalars().all()

    for inspection in rows:
        quality = str(inspection.quality_flag or "").upper()
        if bool(inspection.is_synthetic):
            continue
        if any(
            marker in quality
            for marker in ("SYNTHETIC", "DEMO", "DEMONSTRATION")
        ):
            continue
        return inspection

    return None


# ============================================================
# Model Registry metadata
# ============================================================


async def _registered_model(
    session: AsyncSession,
    version: str | None,
) -> ModelRegistry | None:
    if not version:
        return None

    return (
        await session.execute(
            select(ModelRegistry)
            .where(
                ModelRegistry.model_name == BRIDGE_MODEL_NAME,
                ModelRegistry.version == version,
            )
            .limit(1)
        )
    ).scalar_one_or_none()


# ============================================================
# ML input builder
# ============================================================


def _build_bridge_ml_input(
    *,
    asset: Asset,
    model: AssetModel | None,
    inspection: Inspection | None,
) -> MLInput:
    dimensions = (
        model.dimensions
        if model is not None and model.dimensions
        else {}
    )

    # IMPORTANT: generic asset.condition is NOT an NBI-compatible inspection.
    # The full NBI model receives a condition rating only from an eligible,
    # non-synthetic inspection returned by _latest_inspection().
    inspection_condition = (
        inspection.condition
        if inspection is not None
        else None
    )
    inspection_score = (
        inspection.score
        if inspection is not None
        else None
    )

    condition_rating = condition_to_rating(
        inspection_condition,
        inspection_score,
    )

    age_years = (
        datetime.now(UTC).year - asset.built_year
        if asset.built_year is not None
        else None
    )

    return MLInput(
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


# ============================================================
# Explicit prediction refresh
# ============================================================


async def refresh_ml_prediction(
    session: AsyncSession,
    asset_code: str,
) -> dict[str, Any]:
    """
    Explicitly execute the accepted bridge ML model
    and persist the result.

    This function is used by the POST prediction-refresh endpoint.

    GET /twin must NOT call this function.
    """

    row = await get_asset_row(
        session=session,
        asset_code=asset_code,
    )

    asset, _, _ = row

    supported_types = {"bridge", "dam", "barrage", "airport", "temple"}
    asset_type = (asset.asset_type or "").lower()
    if asset_type not in supported_types:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "UNSUPPORTED_ASSET_TYPE",
                "asset_code": asset.asset_code,
                "asset_type": asset.asset_type,
                "message": (
                    "No category-specific predictor supports this asset type."
                ),
            },
        )

    model = await _active_asset_model(
        session=session,
        asset_id=asset.id,
    )

    inspection = await _latest_inspection(
        session=session,
        asset_id=asset.id,
    )

    if asset_type == "bridge":
        ml_input = _build_bridge_ml_input(
            asset=asset,
            model=model,
            inspection=inspection,
        )
    else:
        ml_input = MLInput(
            asset_type=asset.asset_type,
            age_years=(
                datetime.now(UTC).year - asset.built_year
                if asset.built_year is not None
                else None
            ),
            condition_rating=condition_to_rating(
                inspection.condition if inspection is not None else None,
                inspection.score if inspection is not None else None,
            ),
            material=asset.material,
            built_year=asset.built_year,
            design_life_years=asset.design_life_years,
            evidence_confidence=asset.confidence_score,
        )

    ml_prediction = predict_asset(ml_input)

    if ml_prediction is None:
        missing_fields: list[str] = []

        if ml_input.age_years is None:
            missing_fields.append("built_year")

        if ml_input.condition_rating is None:
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
                    "The category-specific predictor could not produce a "
                    "prediction using the currently available evidence."
                ),
            },
        )

    rows = await persist_ml_prediction(
        session=session,
        asset_id=asset.id,
        prediction=ml_prediction,
    )

    await session.commit()

    for row_item in rows:
        await session.refresh(row_item)

    return {
        "status": "saved",

        "asset": {
            "id": asset.id,
            "asset_code": asset.asset_code,
            "name": asset.name,
            "asset_type": asset.asset_type,
        },

        "model": {
            "model_name": ml_prediction.prediction_method,
            "version": ml_prediction.model_version,
            "feature_version": ml_prediction.feature_version,
            "stage": ml_prediction.status,
            "model_validated": ml_prediction.model_validated,
            "training_scope": ml_prediction.training_scope,
            "rul_method": ml_prediction.rul_method,
        },

        "prediction": {
            "health_score": ml_prediction.health_score,
            "health_lower_bound": ml_prediction.health_lower_bound,
            "health_upper_bound": ml_prediction.health_upper_bound,

            "risk_score": ml_prediction.risk_score,
            "risk_level": ml_prediction.risk_level,

            "remaining_life_years": (
                ml_prediction.remaining_life_years
            ),
            "rul_lower_bound": ml_prediction.rul_lower_bound,
            "rul_upper_bound": ml_prediction.rul_upper_bound,

            "confidence": ml_prediction.confidence,
            "prediction_method": ml_prediction.prediction_method,
            "rul_method": ml_prediction.rul_method,
            "forecast_horizon_years": (
                ml_prediction.forecast_horizon_years
            ),
        },

        "database_rows": [
            {
                "id": item.id,
                "target": item.target,
                "value": item.value,
                "predicted_class": item.predicted_class,
                "lower_bound": item.lower_bound,
                "upper_bound": item.upper_bound,
                "confidence": item.confidence_score,
                "model_version": item.model_version,
                "feature_version": item.feature_version,
                "status": item.status,
                "prediction_time": item.prediction_time,
            }
            for item in rows
        ],

        "factors": ml_prediction.factors,

        "recommendations": ml_prediction.recommendations,

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
    model = await _active_asset_model(
        session=session,
        asset_id=asset.id,
    )
    quality = twin_quality_metadata(model, asset.asset_type)

    environment: dict[str, dict[str, Any]] = {}
    if str(asset.asset_type or "").lower() in {"dam", "barrage"}:
        environment = await load_latest_environment(
            session=session,
            asset_id=asset.id,
        )

    current_risk = resolve_current_risk_snapshot(
        asset_type=asset.asset_type,
        persisted_risk=risk,
        environment=environment,
        dimensions=(
            model.dimensions
            if model is not None and model.dimensions
            else {}
        ),
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
            "coordinates": (
                longitude,
                latitude,
            ),
        },

        "risk_score": current_risk["risk_score"],

        "risk_level": current_risk["risk_level"],

        "data_confidence": asset.confidence_score,
        **quality,
    }


# ============================================================
# Convert persisted prediction into Twin AI state
# ============================================================


async def _persisted_ai_state(
    *,
    session: AsyncSession,
    asset: Asset,
    predictions: dict[str, Prediction],
    baseline,
    condition_rating: float | None,
) -> dict[str, Any] | None:
    health = predictions.get("health")
    risk = predictions.get("risk")
    rul = predictions.get("rul")

    if health is None or risk is None:
        return None


    # SIMRAS_REAL_EVIDENCE_PERSISTED_GUARD
    if (
        condition_rating is None
        and str(health.model_version or "").startswith("nbi_transfer_")
    ):
        return None
    # Health and risk must belong to the same model run/model
    # before they are combined into one AI state.
    if health.model_version != risk.model_version:
        return None

    if health.feature_version != risk.feature_version:
        return None

    # Do not accidentally interpret an older rule model
    # as the current NBI bridge ML model.
    is_bridge_ml = (
        health.model_version.startswith("nbi_transfer_")
        or health.status in {
            "RESEARCH_TRANSFER",
            "VALIDATED_LOCAL",
        }
    )

    if not is_bridge_ml:
        return None

    # RUL is used only if it came from the same model version.
    if (
        rul is not None
        and rul.model_version != health.model_version
    ):
        rul = None

    registry = await _registered_model(
        session=session,
        version=health.model_version,
    )

    metrics = (
        registry.metrics
        if registry is not None and registry.metrics
        else {}
    )

    training_scope = metrics.get(
        "training_scope",
        (
            "FHWA_NBI_US_BRIDGES_RESEARCH_TRANSFER"
            if health.status == "RESEARCH_TRANSFER"
            else "LOCAL_ANDHRA_PRADESH_VALIDATION"
        ),
    )

    model_validated = (
        health.status == "VALIDATED_LOCAL"
    )

    factors = health.factors or risk.factors or []

    confidence_values = [
        value
        for value in [
            health.confidence_score,
            risk.confidence_score,
            rul.confidence_score if rul is not None else None,
        ]
        if value is not None
    ]

    confidence = (
        min(confidence_values)
        if confidence_values
        else None
    )

    recommendations = build_recommendations(
        condition_rating=condition_rating,
        risk_score=risk.value,
        rul_years=(
            rul.value
            if rul is not None
            else None
        ),
        confidence=confidence,
        model_validated=model_validated,
    )

    return {
        "health_score": health.value,
        "health_lower_bound": health.lower_bound,
        "health_upper_bound": health.upper_bound,

        "risk_score": risk.value,
        "risk_level": risk.predicted_class,

        "hazard_score": baseline.hazard_score,
        "hazard_level": baseline.hazard_level,

        "remaining_life_years": (
            rul.value
            if rul is not None
            else None
        ),

        "rul_lower_bound": (
            rul.lower_bound
            if rul is not None
            else None
        ),

        "rul_upper_bound": (
            rul.upper_bound
            if rul is not None
            else None
        ),

        "confidence": confidence,

        "model_version": health.model_version,
        "feature_version": health.feature_version,

        # Critical:
        # this is the persisted DB prediction timestamp.
        "prediction_time": health.prediction_time,

        "status": health.status,

        "prediction_method": "persisted_bridge_ml",

        "model_validated": model_validated,

        "training_scope": training_scope,

        "forecast_horizon_years": 3,

        "factors": factors,

        "recommendations": recommendations,
    }


# ============================================================
# Complete Digital Twin
# ============================================================


def _integerize_public_prediction_values(ai: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(ai, dict):
        return ai

    integer_keys = {
        "health_score",
        "health_lower_bound",
        "health_upper_bound",
        "risk_score",
        "hazard_score",
        "operational_risk_score",
        "remaining_life_years",
        "rul_lower_bound",
        "rul_upper_bound",
    }

    out = dict(ai)
    for key in integer_keys:
        value = out.get(key)
        if value is None or isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            out[key] = int(round(float(value)))
    return out


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
    # 3D / parametric asset model
    # --------------------------------------------------------

    model = await _active_asset_model(
        session=session,
        asset_id=asset.id,
    )

    # --------------------------------------------------------
    # Inspection
    # --------------------------------------------------------

    inspection = await _latest_inspection(
        session=session,
        asset_id=asset.id,
    )

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
    # Environment
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
                desc(EnvironmentObservation.observed_at),
            )
        )
    ).all()

    environment: dict[str, dict[str, Any]] = {}

    latest_env_time: datetime | None = None

    for observation, source in env_rows:

        # SIMRAS_IGNORE_FUTURE_ENVIRONMENT_OBSERVATIONS

        if observation.observed_at is not None and observation.observed_at > datetime.now(UTC):

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

        if (
            latest_env_time is None
            or observation.observed_at > latest_env_time
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
    # Structural condition
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

    # ML/persisted-NBI eligibility must come from a real inspection only.
    ml_condition = (
        inspection.condition
        if inspection is not None
        else None
    )
    condition_rating = condition_to_rating(
        ml_condition,
        inspection_score,
    )

    # --------------------------------------------------------
    # Engineering/environment baseline
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

            source_confidence=asset.confidence_score,
        )
    )

    # --------------------------------------------------------
    # First preference:
    # persisted prediction state
    # --------------------------------------------------------

    persisted_predictions = await latest_predictions(
        session=session,
        asset_id=asset.id,
    )

    ai = await _persisted_ai_state(
        session=session,
        asset=asset,
        predictions=persisted_predictions,
        baseline=baseline,
        condition_rating=condition_rating,
    )

    # --------------------------------------------------------
    # Second preference:
    # live ML inference when no persisted ML result exists.
    #
    # IMPORTANT:
    # this does NOT write anything to PostgreSQL.
    # --------------------------------------------------------

    if ai is None and asset.asset_type.lower() == "bridge":
        ml_input = _build_bridge_ml_input(
            asset=asset,
            model=model,
            inspection=inspection,
        )

        live_prediction = predict_bridge(ml_input)
        if live_prediction is None:
            live_prediction = predict_bridge_sparse(ml_input)

        if live_prediction is not None:
            ai = {
                **live_prediction.to_dict(),

                "hazard_score": baseline.hazard_score,

                "hazard_level": baseline.hazard_level,

                "prediction_time": datetime.now(UTC),

                "prediction_method": live_prediction.prediction_method,
            }

    # --------------------------------------------------------
    # Final fallback:
    # transparent engineering/risk rules
    # --------------------------------------------------------

    if ai is None:
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
    # Sensors
    # --------------------------------------------------------

    # SIMRAS_DAM_BARRAGE_OPERATIONAL_HYDROLOGIC_RISK_V1

    if str(asset.asset_type or "").lower() in {"dam", "barrage"}:

        operational = score_dam_barrage_operational_risk(

            asset_type=asset.asset_type,

            environment=environment,

            dimensions=(model.dimensions if model is not None and model.dimensions else {}),

        )

        if operational is not None:

            op = operational.to_dict()

            ai["operational_risk_score"] = op["operational_risk_score"]

            ai["operational_risk_level"] = op["operational_risk_level"]

            ai["operational_confidence"] = op["operational_confidence"]

            ai["operational_method"] = op["operational_method"]

            ai["operational_status"] = op["operational_status"]

            ai.setdefault("factors", []).extend(op["operational_factors"])

            if op["operational_risk_score"] is not None:

                ai.setdefault("recommendations", []).append(

                    "Review hydrologic/operational exposure alongside current reservoir, rainfall and river observations."

                )


    sensor_count = await session.scalar(
        select(func.count())
        .select_from(Sensor)
        .where(Sensor.asset_id == asset.id)
    )

    # --------------------------------------------------------
    # Final Twin response
    # --------------------------------------------------------

    ai = _integerize_public_prediction_values(ai)

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
