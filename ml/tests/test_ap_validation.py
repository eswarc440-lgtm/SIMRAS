from simras_ml.ap_validation import assess_record


def test_incomplete_osm_bridge_is_withheld():
    result = assess_record({
        "asset_code": "AP_TEST_1",
        "identity_status": "NEEDS_VERIFICATION",
        "segment_count": 1,
        "osm_group_length_m": 50.0,
        "subtype": "road_bridge",
    })

    assert result["prediction_eligible"] is False
    assert "IDENTITY_NOT_VERIFIED" in result["blockers"]


def test_verified_but_incomplete_bridge_is_withheld():
    result = assess_record({
        "asset_code": "AP_TEST_2",
        "canonical_identity_status": "VERIFIED",
        "canonical_built_year": 2010,
        "segment_count": 1,
        "osm_group_length_m": 120.0,
        "subtype": "road_bridge",
    })

    assert result["prediction_eligible"] is False
    assert result["available_features"] >= 2


def test_complete_verified_engineering_record_can_pass():
    result = assess_record({
        "asset_code": "AP_TEST_3",
        "canonical_identity_status": "VERIFIED",
        "age_years": 20,
        "condition_rating": 7,
        "material_code": 3,
        "design_type_code": 10,
        "average_daily_traffic": 15000,
        "truck_traffic_percent": 8,
        "skew_deg": 5,
        "span_count": 4,
        "max_span_m": 35,
        "structure_length_m": 140,
        "inventory_rating": 30,
        "scour_rating": 7,
        "waterway_rating": 8,
    })

    assert result["prediction_eligible"] is True
    assert result["available_features"] == 13
    assert result["feature_coverage"] == 1.0


def test_multiway_geometry_requires_review():
    result = assess_record({
        "asset_code": "AP_TEST_4",
        "canonical_identity_status": "VERIFIED",
        "segment_count": 4,
        "osm_group_length_m": 250.0,
    })

    assert result["prediction_eligible"] is False
    assert "DERIVED_REVIEW_REQUIRED" in result["feature_status"]
