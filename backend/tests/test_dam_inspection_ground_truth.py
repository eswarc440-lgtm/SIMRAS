from __future__ import annotations

from app.models.entities import DamInspectionEvent, DamInspectionFinding
from app.services.dam_inspection_ground_truth import (
    load_candidate_labels,
    load_public_source_registry,
)


def test_dam_inspection_event_has_government_ground_truth_fields() -> None:
    columns = set(DamInspectionEvent.__table__.columns.keys())

    assert {
        "asset_id",
        "asset_name_reported",
        "document_id",
        "source_id",
        "inspection_date",
        "inspection_type",
        "inspection_category",
        "overall_condition",
        "inspector_agency",
        "recommended_action",
        "source_page",
        "authority_level",
        "quality_flag",
        "is_official",
        "is_synthetic",
        "training_eligible",
        "label_scope",
        "metadata_json",
    }.issubset(columns)


def test_component_findings_are_linked_to_inspection_event() -> None:
    columns = set(DamInspectionFinding.__table__.columns.keys())

    assert {
        "inspection_id",
        "component_name",
        "condition_state",
        "deficiency_type",
        "severity",
        "finding_text",
        "recommended_action",
        "source_page",
        "quality_flag",
        "is_official",
        "is_synthetic",
    }.issubset(columns)


def test_public_source_registry_contains_only_authoritative_sources() -> None:
    sources = load_public_source_registry()

    assert len(sources) >= 6
    assert all(source["is_authoritative"] is True for source in sources)
    assert any(source["source_key"] == "cwc_safety_inspection_guidelines_2018" for source in sources)
    assert any(source["source_key"] == "drip_tc3_category_register_2024" for source in sources)


def test_candidate_labels_are_historical_and_not_training_eligible_without_report_date() -> None:
    labels = load_candidate_labels()

    assert len(labels) >= 10
    assert any("Sir Arthur Cotton" in row["asset_name_reported"] for row in labels)
    assert all(row["inspection_category"] in {"I", "II", "III"} for row in labels)
    assert all(row["training_eligible"] is False for row in labels)
    assert all(row["reason_not_training_eligible"] for row in labels)
