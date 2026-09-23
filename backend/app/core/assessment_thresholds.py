"""Centralized assessment thresholds for all SIMRAS services.

Single source of truth for all threshold values to ensure consistency across
health, risk, and RUL assessment logic.
"""

# Risk Thresholds (0-100 scale)
RISK_SCORE_LOW_MIN = 0
RISK_SCORE_LOW_MAX = 40
RISK_SCORE_MEDIUM_MIN = 40
RISK_SCORE_MEDIUM_MAX = 70
RISK_SCORE_HIGH_MIN = 70
RISK_SCORE_HIGH_MAX = 100

# Risk Level Classification
RISK_LEVEL_THRESHOLDS = {
    "LOW": (RISK_SCORE_LOW_MIN, RISK_SCORE_LOW_MAX),
    "MEDIUM": (RISK_SCORE_MEDIUM_MIN, RISK_SCORE_MEDIUM_MAX),
    "HIGH": (RISK_SCORE_HIGH_MIN, RISK_SCORE_HIGH_MAX),
}

# Health Score Categories
HEALTH_SCORE_EXCELLENT_MIN = 85
HEALTH_SCORE_EXCELLENT_MAX = 100
HEALTH_SCORE_GOOD_MIN = 70
HEALTH_SCORE_GOOD_MAX = 85
HEALTH_SCORE_FAIR_MIN = 50
HEALTH_SCORE_FAIR_MAX = 70
HEALTH_SCORE_POOR_MIN = 0
HEALTH_SCORE_POOR_MAX = 50

HEALTH_SCORE_THRESHOLDS = {
    "EXCELLENT": (HEALTH_SCORE_EXCELLENT_MIN, HEALTH_SCORE_EXCELLENT_MAX),
    "GOOD": (HEALTH_SCORE_GOOD_MIN, HEALTH_SCORE_GOOD_MAX),
    "FAIR": (HEALTH_SCORE_FAIR_MIN, HEALTH_SCORE_FAIR_MAX),
    "POOR": (HEALTH_SCORE_POOR_MIN, HEALTH_SCORE_POOR_MAX),
}

# Reference Service Life Years (by asset type)
REFERENCE_SERVICE_LIFE_YEARS = {
    "dam": 100,
    "barrage": 80,
    "bridge": 75,
    "airport": 50,
    "temple": 200,
}


def get_risk_level(risk_score: float | None) -> str | None:
    """Classify risk score into risk level.
    
    Args:
        risk_score: Risk score 0-100, or None if unavailable
        
    Returns:
        Risk level string (LOW, MEDIUM, HIGH) or None if score is None
    """
    if risk_score is None:
        return None
    if risk_score >= RISK_SCORE_HIGH_MIN:
        return "HIGH"
    if risk_score >= RISK_SCORE_MEDIUM_MIN:
        return "MEDIUM"
    return "LOW"


def get_health_category(health_score: float | None) -> str | None:
    """Classify health score into category.
    
    Args:
        health_score: Health score 0-100, or None if unavailable
        
    Returns:
        Health category string (EXCELLENT, GOOD, FAIR, POOR) or None if score is None
    """
    if health_score is None:
        return None
    if health_score >= HEALTH_SCORE_EXCELLENT_MIN:
        return "EXCELLENT"
    if health_score >= HEALTH_SCORE_GOOD_MIN:
        return "GOOD"
    if health_score >= HEALTH_SCORE_FAIR_MIN:
        return "FAIR"
    return "POOR"
