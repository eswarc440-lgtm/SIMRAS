from __future__ import annotations


def build_recommendations(
    *,
    condition_rating: float | None,
    risk_score: float | None,
    rul_years: float | None,
    confidence: float | None,
    model_validated: bool,
) -> list[str]:
    """Return controlled, reviewable actions rather than generated safety advice."""

    recommendations: list[str] = []
    if condition_rating is None:
        recommendations.append("Record an approved structural inspection before assessing health")
    elif condition_rating <= 4:
        recommendations.append("Prioritise a qualified engineering inspection and load review")
    elif condition_rating <= 6:
        recommendations.append("Plan a detailed condition inspection and review identified components")
    else:
        recommendations.append("Continue the documented inspection and preventive-maintenance cycle")

    if risk_score is not None and risk_score >= 70:
        recommendations.append("Escalate for engineering review; do not rely on the model alone")
    elif risk_score is not None and risk_score >= 40:
        recommendations.append("Increase monitoring frequency and verify the main risk factors")

    if rul_years is not None and rul_years <= 5:
        rul_is_actionable = (
            model_validated
            and confidence is not None
            and confidence >= 0.7
            and risk_score is not None
            and risk_score >= 40
        )
        if rul_is_actionable:
            recommendations.append(
                "Prepare a rehabilitation options assessment within the planning cycle"
            )
        else:
            recommendations.append(
                "Do not use the conditional RUL proxy to schedule rehabilitation until local validation and sufficient inputs are available"
            )
    if confidence is not None and confidence < 0.7:
        recommendations.append("Collect missing local evidence before making a maintenance decision")
    if not model_validated:
        recommendations.append("Treat this as research decision support pending Andhra Pradesh validation")
    return list(dict.fromkeys(recommendations))
