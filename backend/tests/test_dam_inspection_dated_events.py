from __future__ import annotations

from datetime import date

from app.services.dam_inspection_ground_truth import load_dated_public_inspection_events


def test_gundlakamma_has_dated_component_level_official_finding() -> None:
    events = load_dated_public_inspection_events()
    event = next(row for row in events if row["source_key"] == "cwc_gundlakamma_monitoring_2023")

    assert event["asset_name_reported"] == "Kandula Obula Reddy Gundlakamma Reservoir Project"
    assert event["inspection_date"] == date(2023, 6, 20)
    assert event["inspection_type"] == "CWC_PROJECT_MONITORING_FIELD_VISIT"
    assert event["inspection_category"] is None
    assert event["is_official"] is True
    assert event["training_eligible"] is True
    assert event["label_scope"] == "COMPONENT_MONITORING_FINDING"

    assert len(event["findings"]) >= 1
    gate = next(row for row in event["findings"] if row["component_name"] == "gates")
    assert gate["condition_state"] == "RESTORATION_REQUIRED"
    assert gate["deficiency_type"] == "WASHED_OUT_GATES"
    assert gate["source_page"] == "9"


def test_srisailam_2024_safety_visit_stays_non_trainable_without_public_findings() -> None:
    events = load_dated_public_inspection_events()
    event = next(row for row in events if row["source_key"] == "ndsa_cwc_srisailam_safety_inspection_2024")

    assert event["asset_name_reported"] == "Srisailam Project"
    assert event["inspection_date"] == date(2024, 2, 7)
    assert event["inspection_type"] == "NDSA_CWC_SAFETY_INSPECTION"
    assert event["inspection_category"] is None
    assert event["training_eligible"] is False
    assert event["findings"] == []
    assert "public component-level findings" in event["reason_not_training_eligible"].lower()


def test_no_dated_event_invents_inspection_category() -> None:
    events = load_dated_public_inspection_events()

    assert events
    assert all(row["inspection_category"] is None for row in events)
