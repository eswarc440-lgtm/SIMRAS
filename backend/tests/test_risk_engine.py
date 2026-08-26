from app.services.risk_engine import RiskInput, score_risk


def test_well_maintained_asset_is_lower_risk() -> None:
    low = score_risk(
        RiskInput(
            built_year=2015,
            design_life_years=100,
            condition="GOOD",
            inspection_score=90,
            days_since_inspection=90,
            days_since_maintenance=180,
            rainfall_mm_24h=10,
            rainfall_mm_7d=35,
            water_level_anomaly_m=0.1,
            flood_exposure=0.15,
            traffic_load_ratio=0.5,
            source_confidence=0.9,
        ),
        current_year=2026,
    )
    high = score_risk(
        RiskInput(
            built_year=1955,
            design_life_years=80,
            condition="POOR",
            inspection_score=42,
            days_since_inspection=700,
            days_since_maintenance=1600,
            rainfall_mm_24h=180,
            rainfall_mm_7d=390,
            water_level_anomaly_m=2.2,
            flood_exposure=0.9,
            traffic_load_ratio=1.2,
            source_confidence=0.8,
        ),
        current_year=2026,
    )
    assert low.risk_score < high.risk_score
    assert high.risk_level == "HIGH"
    assert high.remaining_life_years is None


def test_missing_data_lowers_confidence_without_inventing_rul() -> None:
    result = score_risk(RiskInput(condition="FAIR"), current_year=2026)
    assert result.confidence < 0.6
    assert result.remaining_life_years is None
    assert any("missing" in factor.lower() for factor in result.factors)

