from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import ModelRegistry


BRIDGE_MODEL_NAME = "simras_nbi_bridge_deterioration"

PRODUCTION_STAGES = {
    "PRODUCTION_DECISION_SUPPORT",
    "VALIDATED_LOCAL",
}


async def bridge_prediction_gate(
    session: AsyncSession,
    asset,
) -> dict[str, Any]:
    """
    Decide whether the governed NBI bridge model may run for an AP asset.

    This function is fail-closed:
    missing registry, unverified identity, blocked promotion, or an
    unapproved stage all result in prediction withholding.
    """

    if str(asset.asset_type or "").lower() != "bridge":
        return {
            "allowed": True,
            "reason_code": "NOT_BRIDGE_MODEL_SCOPE",
            "model": None,
        }

    registry = (
        await session.execute(
            select(ModelRegistry)
            .where(
                ModelRegistry.model_name == BRIDGE_MODEL_NAME
            )
            .order_by(
                ModelRegistry.created_at.desc(),
                ModelRegistry.id.desc(),
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    if registry is None:
        return {
            "allowed": False,
            "reason_code": "MODEL_NOT_REGISTERED",
            "model": {
                "model_name": BRIDGE_MODEL_NAME,
            },
        }

    metrics = registry.metrics or {}
    promotion = metrics.get("promotion") or {}
    ap_validation = promotion.get("ap_validation") or {}

    promotion_approved = (
        promotion.get("approved") is True
    )

    identity_status = str(
        getattr(asset, "identity_status", "") or ""
    ).upper()

    model = {
        "model_name": registry.model_name,
        "version": registry.version,
        "feature_version": registry.feature_version,
        "stage": registry.stage,
        "promotion_decision": promotion.get("decision"),
        "promotion_approved": promotion_approved,
        "training_dataset": registry.training_dataset,
    }

    governance = {
        "identity_status": identity_status,
        "promotion_blockers": promotion.get(
            "blockers",
            [],
        ),
        "ap_validation": ap_validation,
    }

    if identity_status != "VERIFIED":
        return {
            "allowed": False,
            "reason_code": "ASSET_IDENTITY_NOT_VERIFIED",
            "model": model,
            "governance": governance,
        }

    if not promotion_approved:
        return {
            "allowed": False,
            "reason_code": "MODEL_NOT_AP_LOCALLY_VALIDATED",
            "model": model,
            "governance": governance,
        }

    if registry.stage not in PRODUCTION_STAGES:
        return {
            "allowed": False,
            "reason_code": "MODEL_STAGE_NOT_PRODUCTION_ALLOWED",
            "model": model,
            "governance": governance,
        }

    if int(ap_validation.get("prediction_eligible", 0) or 0) <= 0:
        return {
            "allowed": False,
            "reason_code": "NO_AP_ASSETS_MEET_INFERENCE_ELIGIBILITY",
            "model": model,
            "governance": governance,
        }

    return {
        "allowed": True,
        "reason_code": "MODEL_GOVERNANCE_APPROVED",
        "model": model,
        "governance": governance,
    }
