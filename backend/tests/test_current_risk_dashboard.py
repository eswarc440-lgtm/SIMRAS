from types import SimpleNamespace

from app.api.routes.ui_compat import _asset_payload


def _asset(asset_type: str = "barrage"):
    return SimpleNamespace(
        id=42,
        asset_code="AP_BAR_WRIS_B00131",
        name="Sir Arthur Cotton Barrage",
        asset_type=asset_type,
        district="East Godavari",
    )


def test_asset_payload_uses_resolved_operational_risk_when_no_stored_risk():
    payload = _asset_payload(
        _asset(),
        predictions={},
        current_risk={
            "available": True,
            "risk_score": 100.0,
            "risk_level": "HIGH",
            "confidence": 0.55,
            "risk_method": "dam_barrage_hydrologic_rules_v1",
            "risk_scope": "OPERATIONAL_HYDROLOGIC",
            "source_timestamp": "2026-09-18T10:40:03+00:00",
        },
    )

    assert payload["risk_score"] == 100.0
    assert payload["risk_level"] == "HIGH"
    assert payload["prediction_confidence"] == 0.55
    assert payload["risk_method"] == "dam_barrage_hydrologic_rules_v1"
    assert payload["risk_scope"] == "OPERATIONAL_HYDROLOGIC"


def test_asset_payload_keeps_unavailable_risk_unknown_instead_of_zero():
    payload = _asset_payload(
        _asset("airport"),
        predictions={},
        current_risk={
            "available": False,
            "risk_score": None,
            "risk_level": "NOT_AVAILABLE",
            "confidence": None,
            "risk_method": None,
            "risk_scope": "STRUCTURAL",
            "source_timestamp": None,
        },
    )

    assert payload["risk_score"] is None
    assert payload["risk_level"] == "NOT_AVAILABLE"
    assert payload["prediction_confidence"] is None
