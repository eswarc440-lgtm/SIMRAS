from types import SimpleNamespace

from app.services.current_risk_service import resolve_current_risk_snapshot


def _prediction(*, value=82.0, level="HIGH", confidence=0.77):
    return SimpleNamespace(
        value=value,
        predicted_class=level,
        confidence_score=confidence,
        prediction_time=None,
        model_version="nbi_transfer_test",
        feature_version="nbi_bridge_state_v1",
        status="RESEARCH_TRANSFER",
    )


def test_dam_barrage_operational_risk_overrides_missing_persisted_risk():
    snapshot = resolve_current_risk_snapshot(
        asset_type="barrage",
        persisted_risk=None,
        environment={
            "rainfall_24h": {"value": 180.0},
            "rainfall_7d": {"value": 420.0},
            "river_velocity": {"value": 3.8},
        },
        dimensions={},
    )

    assert snapshot["available"] is True
    assert snapshot["risk_score"] is not None
    assert snapshot["risk_level"] in {"LOW", "MEDIUM", "HIGH"}
    assert snapshot["risk_method"] == "dam_barrage_hydrologic_rules_v1"
    assert snapshot["risk_scope"] == "OPERATIONAL_HYDROLOGIC"


def test_bridge_uses_latest_persisted_model_risk():
    snapshot = resolve_current_risk_snapshot(
        asset_type="bridge",
        persisted_risk=_prediction(),
        environment={},
        dimensions={},
    )

    assert snapshot["available"] is True
    assert snapshot["risk_score"] == 82.0
    assert snapshot["risk_level"] == "HIGH"
    assert snapshot["confidence"] == 0.77
    assert snapshot["risk_scope"] == "STRUCTURAL_MODEL"


def test_airport_without_supported_risk_stays_not_available():
    snapshot = resolve_current_risk_snapshot(
        asset_type="airport",
        persisted_risk=None,
        environment={},
        dimensions={},
    )

    assert snapshot["available"] is False
    assert snapshot["risk_score"] is None
    assert snapshot["risk_level"] == "NOT_AVAILABLE"
    assert snapshot["confidence"] is None
