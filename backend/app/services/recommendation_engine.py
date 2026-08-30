from __future__ import annotations


def _legacy_recommendations(
    *,
    condition_rating: float | None,
    risk_score: float | None,
    rul_years: float | None,
    confidence: float | None,
    model_validated: bool,
) -> list[str]:
    recommendations: list[str] = []

    if condition_rating is None:
        recommendations.append(
            "Record an approved structural inspection before assessing health"
        )
    elif condition_rating <= 4:
        recommendations.append(
            "Prioritise a qualified engineering inspection and load review"
        )
    elif condition_rating <= 6:
        recommendations.append(
            "Plan a detailed condition inspection and review identified components"
        )
    else:
        recommendations.append(
            "Continue the documented inspection and preventive-maintenance cycle"
        )

    if risk_score is not None and risk_score >= 70:
        recommendations.append(
            "Escalate for engineering review; do not rely on the model alone"
        )
    elif risk_score is not None and risk_score >= 40:
        recommendations.append(
            "Increase monitoring frequency and verify the main risk factors"
        )

    if rul_years is not None and rul_years <= 5:
        recommendations.append(
            "Prepare a rehabilitation options assessment within the planning cycle"
        )

    if confidence is not None and confidence < 0.7:
        recommendations.append(
            "Collect missing local evidence before making a maintenance decision"
        )

    if not model_validated:
        recommendations.append(
            "Treat this as research decision support pending Andhra Pradesh validation"
        )

    return list(dict.fromkeys(recommendations))


def build_recommendations(
    *,
    condition_rating: float | None,
    risk_score: float | None,
    rul_years: float | None,
    confidence: float | None,
    model_validated: bool,
    health_score: float | None = None,
    risk_level: str | None = None,
    hazard_level: str | None = None,
    asset_type: str | None = None,
    has_structural_evidence: bool | None = None,
    factors: list[str] | None = None,
) -> list[str]:
    """Build controlled, explainable decision-support actions.

    With only the legacy five arguments this preserves the previous output.
    The Digital Twin supplies the enhanced fields below.
    """

    enhanced = any(
        value is not None
        for value in (
            health_score,
            risk_level,
            hazard_level,
            asset_type,
            has_structural_evidence,
            factors,
        )
    )

    if not enhanced:
        return _legacy_recommendations(
            condition_rating=condition_rating,
            risk_score=risk_score,
            rul_years=rul_years,
            confidence=confidence,
            model_validated=model_validated,
        )

    recommendations: list[str] = []
    kind = (asset_type or "asset").lower()
    risk_level = (risk_level or "").upper()
    hazard_level = (hazard_level or "").upper()

    if has_structural_evidence is False:
        recommendations.append(
            "[HIGH] Obtain or link an approved structural inspection to improve the health prediction"
        )

    if health_score is not None:
        if health_score < 40:
            recommendations.append(
                "[HIGH] Prioritise qualified engineering inspection and rehabilitation assessment"
            )
        elif health_score < 55:
            recommendations.append(
                "[HIGH] Plan a detailed condition inspection and component-level review"
            )
        elif health_score < 70:
            recommendations.append(
                "[MEDIUM] Increase inspection attention and verify the main deterioration drivers"
            )
        else:
            recommendations.append(
                "[ROUTINE] Continue documented inspection and preventive-maintenance activities"
            )

    if risk_score is not None:
        if risk_score >= 70 or risk_level == "HIGH":
            recommendations.append(
                "[HIGH] Escalate the asset for engineering review and verify the dominant risk factors"
            )
        elif risk_score >= 40 or risk_level == "MEDIUM":
            recommendations.append(
                "[MEDIUM] Increase monitoring frequency until the main risk factors are verified"
            )

    if hazard_level == "HIGH":
        recommendations.append(
            "[HIGH] Review the asset after the current environmental event and verify flood/drainage exposure"
        )
    elif hazard_level == "MEDIUM":
        recommendations.append(
            "[MEDIUM] Continue enhanced environmental monitoring until exposure returns to normal"
        )

    if kind in {"dam", "barrage"}:
        recommendations.append(
            "[ROUTINE] Continue reservoir, rainfall, gate/spillway and downstream-condition monitoring"
        )
    elif kind == "bridge":
        recommendations.append(
            "[ROUTINE] Continue deck, bearing, pier, scour and loading inspections according to the approved cycle"
        )

    if confidence is not None and confidence < 0.60:
        recommendations.append(
            "[HIGH] Collect missing local engineering evidence before using the prediction for maintenance decisions"
        )
    elif confidence is not None and confidence < 0.75:
        recommendations.append(
            "[MEDIUM] Improve prediction confidence with newer inspection and maintenance records"
        )

    if rul_years is not None and rul_years <= 5:
        recommendations.append(
            "[HIGH] Prepare rehabilitation options for engineering review"
        )

    if not model_validated:
        recommendations.append(
            "[NOTICE] Treat SIMRAS scores as research decision support until Andhra Pradesh validation is completed"
        )

    return list(dict.fromkeys(recommendations))
