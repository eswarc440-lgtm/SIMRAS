from app.services.dam_hydrology_risk import score_dam_barrage_operational_risk


def row(value, confidence=0.9, estimated=False):
    return {
        "value": value,
        "confidence": confidence,
        "is_estimated": estimated,
        "observed_at": "2026-08-31T10:00:00+00:00",
    }


def test_non_dam_is_not_scored():
    assert score_dam_barrage_operational_risk(
        asset_type="bridge", environment={}, dimensions={}
    ) is None


def test_missing_hydrology_abstains():
    result = score_dam_barrage_operational_risk(
        asset_type="dam", environment={}, dimensions={}
    )
    assert result is not None
    assert result.operational_risk_score is None
    assert result.operational_status == "INSUFFICIENT_HYDROLOGY_DATA"


def test_heavier_rainfall_scores_higher():
    low = score_dam_barrage_operational_risk(
        asset_type="barrage",
        environment={"rainfall_24h": row(10), "rainfall_7d": row(40)},
        dimensions={},
    )
    high = score_dam_barrage_operational_risk(
        asset_type="barrage",
        environment={"rainfall_24h": row(140), "rainfall_7d": row(450)},
        dimensions={},
    )
    assert low and high
    assert low.operational_risk_score is not None
    assert high.operational_risk_score is not None
    assert high.operational_risk_score > low.operational_risk_score


def test_storage_uses_asset_specific_capacity():
    result = score_dam_barrage_operational_risk(
        asset_type="dam",
        environment={"reservoir_storage": row(950)},
        dimensions={"gross_storage_mcm": 1000},
    )
    assert result is not None
    assert result.operational_risk_score is not None
    assert result.operational_risk_score > 40
