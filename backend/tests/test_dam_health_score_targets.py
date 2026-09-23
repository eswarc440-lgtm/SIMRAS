from __future__ import annotations

import pytest

from app.services.dam_health_score import (
    build_health_score_target,
    cwc_condition_index,
)


CORE_COMPONENTS = [
    "dam_body",
    "foundation",
    "spillway",
    "gates",
    "drainage",
    "seepage",
    "instrumentation",
]


def _finding(
    component: str,
    condition: str,
    *,
    official: bool = True,
    synthetic: bool = False,
) -> dict:
    return {
        "component_name": component,
        "condition_state": condition,
        "is_official": official,
        "is_synthetic": synthetic,
    }


def test_cwc_condition_classes_map_to_transparent_evenly_spaced_index() -> None:
    assert cwc_condition_index("SATISFACTORY") == pytest.approx(100.0)
    assert cwc_condition_index("FAIR") == pytest.approx(66.6666667)
    assert cwc_condition_index("POOR") == pytest.approx(33.3333333)
    assert cwc_condition_index("UNSATISFACTORY") == pytest.approx(0.0)


def test_unknown_condition_is_not_converted_to_a_number() -> None:
    assert cwc_condition_index("UNKNOWN") is None
    assert cwc_condition_index(None) is None


def test_sparse_component_coverage_withholds_whole_asset_health_score() -> None:
    result = build_health_score_target(
        [
            _finding("gates", "POOR"),
            _finding("spillway", "FAIR"),
        ],
        applicable_components=CORE_COMPONENTS,
        minimum_coverage=0.70,
    )

    assert result["health_score_target"] is None
    assert result["health_target_status"] == "INSUFFICIENT_COMPONENT_COVERAGE"
    assert result["component_coverage"] == pytest.approx(2 / 7)
    assert result["score_method"] == "simras_cwc_condition_index_v1"
    assert result["official_numeric_score"] is False


def test_sufficient_official_component_coverage_builds_derived_health_target() -> None:
    result = build_health_score_target(
        [
            _finding("dam_body", "SATISFACTORY"),
            _finding("foundation", "SATISFACTORY"),
            _finding("spillway", "FAIR"),
            _finding("gates", "FAIR"),
            _finding("drainage", "POOR"),
            _finding("seepage", "SATISFACTORY"),
        ],
        applicable_components=CORE_COMPONENTS,
        minimum_coverage=0.70,
    )

    assert result["health_target_status"] == "DERIVED_FROM_OFFICIAL_CWC_CONDITIONS"
    assert result["health_score_target"] == pytest.approx(77.8, abs=0.1)
    assert result["component_coverage"] == pytest.approx(6 / 7)
    assert result["components_scored"] == 6
    assert result["components_expected"] == 7
    assert result["official_numeric_score"] is False


def test_unofficial_or_synthetic_findings_cannot_create_health_target() -> None:
    result = build_health_score_target(
        [
            _finding("dam_body", "SATISFACTORY", official=False),
            _finding("foundation", "SATISFACTORY", synthetic=True),
            _finding("spillway", "FAIR", official=False),
            _finding("gates", "POOR", synthetic=True),
            _finding("drainage", "SATISFACTORY", official=False),
            _finding("seepage", "FAIR", synthetic=True),
            _finding("instrumentation", "SATISFACTORY", official=False),
        ],
        applicable_components=CORE_COMPONENTS,
        minimum_coverage=0.70,
    )

    assert result["health_score_target"] is None
    assert result["health_target_status"] == "INSUFFICIENT_COMPONENT_COVERAGE"
    assert result["components_scored"] == 0


def test_health_target_reports_component_scores_for_auditability() -> None:
    result = build_health_score_target(
        [
            _finding("dam_body", "SATISFACTORY"),
            _finding("foundation", "FAIR"),
            _finding("spillway", "POOR"),
            _finding("gates", "UNSATISFACTORY"),
            _finding("drainage", "SATISFACTORY"),
        ],
        applicable_components=[
            "dam_body",
            "foundation",
            "spillway",
            "gates",
            "drainage",
        ],
        minimum_coverage=1.0,
    )

    assert result["component_scores"] == {
        "dam_body": pytest.approx(100.0),
        "foundation": pytest.approx(66.6666667),
        "spillway": pytest.approx(33.3333333),
        "gates": pytest.approx(0.0),
        "drainage": pytest.approx(100.0),
    }
    assert result["health_score_target"] == pytest.approx(60.0, abs=0.1)
