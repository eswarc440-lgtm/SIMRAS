from app.services.real_report_service import build_real_report_payload


def test_prakasam_report_contains_government_engineering_facts_without_placeholders():
    twin = {
        "asset": {
            "asset_code": "AP_DAM_00001",
            "name": "Prakasam Barrage",
            "asset_type": "barrage",
            "district": "NTR",
        },
        "static": {"owner": "Water Resources Department", "built_year": 1957},
        "environment": {},
        "inspection": {"condition": None, "quality_flag": "NOT_AVAILABLE"},
        "maintenance": [],
        "ai": {
            "health_score": None,
            "risk_score": None,
            "remaining_life_years": None,
            "status": "INSUFFICIENT_ENGINEERING_EVIDENCE",
        },
    }
    evidence = {"evidence_strength": "HIGH", "evidence": []}

    report = build_real_report_payload("AP_DAM_00001", twin, evidence)

    engineering = report["government_engineering"]
    assert engineering["barrage_length_m"] == 1232.92
    assert engineering["regulator_gate_count"] == 70
    assert engineering["regulator_gate_width_m"] == 12.19
    assert engineering["regulator_gate_height_m"] == 3.66
    assert engineering["scour_sluice_count"] == 14

    rendered = str(report).upper()
    assert "NOT AVAILABLE" not in rendered
    assert "NOT_AVAILABLE" not in rendered
    assert "INSUFFICIENT" not in rendered


def test_ineligible_ai_section_is_omitted_entirely():
    twin = {
        "asset": {"asset_code": "AP_AIR_VOBZ", "name": "Vijayawada Airport", "asset_type": "airport"},
        "static": {},
        "environment": {},
        "inspection": {},
        "maintenance": [],
        "ai": {
            "health_score": 77,
            "risk_score": 20,
            "model_validated": False,
            "training_scope": "ASSET_SPECIFIC_ENGINEERING_RULES",
            "status": "RESEARCH_TRANSFER",
        },
    }

    report = build_real_report_payload("AP_AIR_VOBZ", twin, {})
    assert "ml_prediction" not in report
    assert report["government_engineering"]["runway_length_m"] == 3360
    assert report["government_engineering"]["runway_width_m"] == 45


def test_real_bridge_ml_can_be_included_when_model_is_locally_validated():
    twin = {
        "asset": {"asset_code": "AP_BR_00001", "name": "Bridge", "asset_type": "bridge"},
        "static": {},
        "environment": {},
        "inspection": {"condition": "GOOD", "is_synthetic": False},
        "maintenance": [],
        "ai": {
            "health_score": 83,
            "risk_score": 12,
            "risk_level": "LOW",
            "confidence": 0.81,
            "model_validated": True,
            "training_scope": "LOCAL_ANDHRA_PRADESH_VALIDATION",
            "model_version": "validated_bridge_v1",
            "prediction_time": "2026-09-16T12:00:00Z",
        },
    }

    report = build_real_report_payload("AP_BR_00001", twin, {})
    assert report["ml_prediction"]["health_score"] == 83
    assert report["ml_prediction"]["risk_score"] == 12



def test_tirumala_report_uses_canonical_asset_code_and_source_backed_structure_facts():
    twin = {
        "asset": {
            "asset_code": "AP_TEMPLE_TIRUMALA",
            "name": "Sri Venkateswara Swamy Temple, Tirumala",
            "asset_type": "temple",
            "district": "Tirupati",
        },
        "static": {},
        "environment": {},
        "inspection": {},
        "maintenance": [],
        "ai": {},
    }

    report = build_real_report_payload("AP_TEMPLE_TIRUMALA", twin, {})
    engineering = report["government_engineering"]

    assert engineering["complex_area_acres"] == 16.2
    assert engineering["main_entrance_height_ft"] == 50
    assert engineering["gopuram_tiers"] == 7



def test_srikalahasti_report_contains_source_backed_gopuram_height():
    twin = {
        "asset": {
            "asset_code": "AP_TEMPLE_SRIKALAHASTI",
            "name": "Sri Kalahasteeswara Swamy Temple",
            "asset_type": "temple",
            "district": "Tirupati",
        },
        "static": {},
        "environment": {},
        "inspection": {},
        "maintenance": [],
        "ai": {},
    }

    report = build_real_report_payload("AP_TEMPLE_SRIKALAHASTI", twin, {})
    engineering = report["government_engineering"]

    assert engineering["main_gopuram_height_m"] == 36.5
    assert engineering["main_gopuram_height_ft"] == 120
