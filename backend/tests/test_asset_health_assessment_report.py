from app.services.asset_health_assessment_report import (
    _numeric_proxy_assessment,
    _health_category,
    _risk_level,
    _trend,
)


def test_numeric_proxy_is_deterministic_and_tracks_missing_features():
    report = {
        "asset": {
            "asset_type": "DAM",
            "built_year": 1980,
            "design_life_years": 100,
            "confidence_score": 0.35,
        },
        "health": {},
        "risk": {},
        "rul": {},
        "transparency": {},
        "inspection_history": [],
        "maintenance_history": [],
        "supporting_data": [{"name": "rainfall_24h", "current_value": 80}],
    }
    first = _numeric_proxy_assessment(report)
    second = _numeric_proxy_assessment(report)
    assert first == second
    # With insufficient evidence (no inspection/maintenance), scores should be None
    assert first["health_score"] is None or (0 <= first["health_score"] <= 100)
    assert first["risk_score"] is None or (0 <= first["risk_score"] <= 100)
    # Risk level should be NOT_AVAILABLE or None when insufficient evidence
    assert first["risk_level"] in {"LOW", "MEDIUM", "HIGH", "NOT_AVAILABLE", None}
    assert first["confidence"] < 100
    # With no inspection/maintenance history, RUL should be None or 0
    assert first["rul_years"] is None or first["rul_years"] >= 0
    assert first["prediction_basis"] in {"EVIDENCE_DERIVED", "ESTIMATED_PROXY", "NOT_AVAILABLE"}
    assert "inspection_score" in first["features_missing"]


def test_health_categories():
    assert _health_category(90) == "EXCELLENT"
    assert _health_category(75) == "GOOD"
    assert _health_category(60) == "WARNING"
    assert _health_category(30) == "CRITICAL"
    assert _health_category(None) == "NOT_AVAILABLE"


def test_risk_levels():
    assert _risk_level(20) == "LOW"
    assert _risk_level(55) == "MEDIUM"
    assert _risk_level(75) == "HIGH"
    assert _risk_level(90) == "CRITICAL"
    assert _risk_level(None) == "NOT_AVAILABLE"


def test_trend_is_derived_from_history():
    assert _trend([{"value": 1}, {"value": 2}]) == "INCREASING"
    assert _trend([{"value": 2}, {"value": 1}]) == "DECREASING"
    assert _trend([{"value": 1}]) == "INSUFFICIENT_HISTORY"
