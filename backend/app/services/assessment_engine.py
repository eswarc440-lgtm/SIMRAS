"""SIMRAS Canonical Assessment Engine.

Provides the single authoritative service:
build_asset_assessment(session, asset_code)

Returns:
- health_score (0-100 float or None if withheld/unverified)
- risk_score (0-100 float or None if withheld)
- risk_level ("LOW" | "MEDIUM" | "HIGH" | "CRITICAL")
- rul (remaining useful life in years or None)
- assessment_basis ("ML_VALIDATED" | "ML_TRANSFER" | "INSPECTION_DERIVED" | "EVIDENCE_DERIVED" | "ESTIMATED_PROXY" | "WITHHELD")
- features (dict)
- feature_usage (dict)
- evidence (list of source records)
- limitations (list of explicit warnings)
- model_version (str)

Never falls back to hardcoded Health=100 or Risk=0 when missing.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select, text
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
)
from app.services.twin_service import get_asset_row


ALLOWED_BASIS_VALUES = {
    "ML_VALIDATED",
    "ML_TRANSFER",
    "INSPECTION_DERIVED",
    "EVIDENCE_DERIVED",
    "ESTIMATED_PROXY",
    "WITHHELD",
}


async def build_asset_assessment(
    session: AsyncSession,
    asset_code: str,
) -> dict[str, Any]:
    row = await get_asset_row(session, asset_code)
    asset, longitude, latitude = row

    # Fetch latest predictions
    preds_res = await session.execute(
        select(Prediction)
        .where(Prediction.asset_id == asset.id)
        .order_by(desc(Prediction.prediction_time), desc(Prediction.id))
    )
    all_preds = preds_res.scalars().all()

    latest_preds: dict[str, Prediction] = {}
    for p in all_preds:
        t = str(p.target).lower()
        if t not in latest_preds:
            latest_preds[t] = p

    health_pred = latest_preds.get("health")
    risk_pred = latest_preds.get("risk")
    rul_pred = latest_preds.get("rul") or latest_preds.get("remaining_life")

    health_score = round(float(health_pred.value), 2) if health_pred and health_pred.value is not None else None
    risk_score = round(float(risk_pred.value), 2) if risk_pred and risk_pred.value is not None else None
    rul = round(float(rul_pred.value), 2) if rul_pred and rul_pred.value is not None else None

    # Derive risk level
    if risk_pred and risk_pred.predicted_class:
        risk_level = risk_pred.predicted_class.upper()
    elif risk_score is not None:
        risk_level = "CRITICAL" if risk_score >= 80 else "HIGH" if risk_score >= 60 else "MEDIUM" if risk_score >= 35 else "LOW"
    else:
        risk_level = "UNKNOWN"

    # Assessment basis
    raw_status = None
    if risk_pred and risk_pred.status:
        raw_status = str(risk_pred.status).split(":")[0].strip().upper()
    elif health_pred and health_pred.status:
        raw_status = str(health_pred.status).split(":")[0].strip().upper()

    if raw_status in ALLOWED_BASIS_VALUES:
        assessment_basis = raw_status
    elif raw_status == "RESEARCH_TRANSFER":
        assessment_basis = "ML_TRANSFER"
    elif raw_status == "VALIDATED_ML":
        assessment_basis = "ML_VALIDATED"
    elif asset.identity_status == "VERIFIED":
        assessment_basis = "EVIDENCE_DERIVED"
    elif health_score is not None or risk_score is not None:
        assessment_basis = "ESTIMATED_PROXY"
    else:
        assessment_basis = "WITHHELD"

    # Model metadata
    model_version = (
        (risk_pred.model_version if risk_pred else None)
        or (health_pred.model_version if health_pred else None)
        or "simras_engineering_baseline_v1"
    )

    # Features and feature usage
    features: dict[str, Any] = {
        "asset_code": asset.asset_code,
        "asset_type": asset.asset_type,
        "built_year": asset.built_year,
        "material": asset.material,
        "district": asset.district,
        "condition": asset.condition,
    }

    feature_usage: dict[str, str] = {
        "built_year": "Structural age factor for deterioration baseline",
        "material": "Material vulnerability coefficient",
        "condition": "Recorded baseline physical condition state",
        "district": "Geographic environmental and seismic exposure zone",
    }

    # Fetch latest environment observations
    env_res = await session.execute(
        select(EnvironmentObservation)
        .where(EnvironmentObservation.asset_id == asset.id)
        .order_by(desc(EnvironmentObservation.observed_at))
        .limit(10)
    )
    env_obs = env_res.scalars().all()
    for o in env_obs:
        if o.variable not in features:
            features[o.variable] = o.value
            feature_usage[o.variable] = f"Latest environmental telemetry ({o.unit}) - {o.source_type}"

    # Evidence documents / sources
    evidence: list[dict[str, Any]] = []
    if asset.source_id:
        src = await session.scalar(select(DataSource).where(DataSource.id == asset.source_id))
        if src:
            evidence.append({
                "source_code": src.code,
                "source_name": src.name,
                "organisation": src.organisation,
                "is_authoritative": src.is_authoritative,
                "url": src.url,
            })

    limitations: list[str] = [
        "Risk Score is an evidence-backed deterioration probability index; it does not indicate imminent collapse.",
        "Missing environmental sensor feeds are reported as unavailable and never substituted with fake values.",
    ]
    if assessment_basis == "ML_TRANSFER":
        limitations.append("Transfer deterioration model calibrated on US FHWA NBI; not locally validated on AP bridges.")
    elif assessment_basis == "ESTIMATED_PROXY":
        limitations.append("Proxy estimation based on asset age and material classification; on-site inspection required.")
    elif assessment_basis == "WITHHELD":
        limitations.append("Insufficient authoritative data; health score is withheld to prevent misleading indicators.")

    return {
        "asset_code": asset.asset_code,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "health_score": health_score,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "rul": rul,
        "assessment_basis": assessment_basis,
        "features": features,
        "feature_usage": feature_usage,
        "evidence": evidence,
        "limitations": limitations,
        "model_version": model_version,
        "assessed_at": datetime.now(UTC).isoformat(),
    }
