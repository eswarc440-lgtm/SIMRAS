from app.services.asset_health_assessment_report import (
    _health_category,
    _risk_level,
    _trend,
)


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
