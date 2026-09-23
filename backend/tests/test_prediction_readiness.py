from app.services.risk_engine import RiskInput, score_risk


def test_environmental_hazard_is_separate_from_structural_health():
    result = score_risk(
        RiskInput(
            rainfall_mm_24h=120,
            rainfall_mm_7d=280,
            source_confidence=1,
        ),
        current_year=2026,
    )

    assert result.health_score is None
    assert result.risk_score is None
    assert result.hazard_score is not None
    assert result.hazard_score > 0
    assert result.hazard_level in {"LOW", "MEDIUM", "HIGH"}
    assert result.status == "INSUFFICIENT_DATA"
    assert result.model_validated is False


def test_inspection_enables_engineering_decision_support():
    result = score_risk(
        RiskInput(
            built_year=1997,
            design_life_years=100,
            condition="GOOD",
            inspection_score=82,
            rainfall_mm_24h=28.3,
            source_confidence=0.9,
        ),
        current_year=2026,
    )

    assert result.health_score is not None
    assert result.risk_score is not None
    assert result.status == "DECISION_SUPPORT"
    assert result.prediction_method == "transparent_engineering_rules"
    assert result.model_validated is False