from __future__ import annotations

from datetime import date

from app.services.dam_inspection_targets import build_inspection_targets


def _event(
    event_id: int,
    asset_id: int,
    when: date,
    *,
    category: str | None = None,
    overall_condition: str | None = None,
) -> dict:
    return {
        "id": event_id,
        "asset_id": asset_id,
        "inspection_date": when,
        "inspection_category": category,
        "overall_condition": overall_condition,
        "is_official": True,
        "is_synthetic": False,
        "training_eligible": True,
    }


def _finding(
    inspection_id: int,
    component: str,
    *,
    state: str | None,
    severity: str | None,
) -> dict:
    return {
        "inspection_id": inspection_id,
        "component_name": component,
        "condition_state": state,
        "severity": severity,
        "is_official": True,
        "is_synthetic": False,
    }


def test_single_component_finding_does_not_fabricate_whole_asset_health_score() -> None:
    events = [_event(1, 10, date(2023, 6, 20))]
    findings = [
        _finding(
            1,
            "gates",
            state="RESTORATION_REQUIRED",
            severity="MAJOR",
        )
    ]

    targets = build_inspection_targets(events, findings, horizon_years=3)
    row = targets[0]

    assert row["component_targets"] == {
        "gates": {
            "condition_state": "RESTORATION_REQUIRED",
            "severity": "MAJOR",
        }
    }
    assert row["health_score_target"] is None
    assert row["health_target_status"] == "INSUFFICIENT_COMPONENT_COVERAGE"
    assert row["risk_event_within_horizon"] is None
    assert row["risk_target_status"] == "NO_FUTURE_INSPECTION"
    assert row["rul_event_years"] is None
    assert row["rul_event_observed"] is False


def test_later_major_deficiency_creates_real_risk_and_rul_targets() -> None:
    events = [
        _event(1, 20, date(2021, 6, 1), overall_condition="SATISFACTORY"),
        _event(2, 20, date(2023, 6, 1), overall_condition="MAJOR_DEFICIENCY"),
    ]
    findings = [
        _finding(1, "gates", state="SATISFACTORY", severity="MINOR"),
        _finding(1, "spillway", state="SATISFACTORY", severity="NONE"),
        _finding(1, "drainage", state="SATISFACTORY", severity="NONE"),
        _finding(2, "gates", state="RESTORATION_REQUIRED", severity="MAJOR"),
    ]

    targets = build_inspection_targets(events, findings, horizon_years=3)
    first = next(row for row in targets if row["inspection_id"] == 1)

    assert first["risk_event_within_horizon"] == 1
    assert first["risk_target_status"] == "OBSERVED_FUTURE_OUTCOME"
    assert first["rul_event_observed"] is True
    assert 1.99 <= first["rul_event_years"] <= 2.01


def test_future_satisfactory_inspection_creates_negative_risk_target() -> None:
    events = [
        _event(1, 30, date(2021, 7, 1), overall_condition="SATISFACTORY"),
        _event(2, 30, date(2023, 7, 1), overall_condition="SATISFACTORY"),
    ]
    findings = [
        _finding(1, "gates", state="SATISFACTORY", severity="NONE"),
        _finding(2, "gates", state="SATISFACTORY", severity="NONE"),
    ]

    targets = build_inspection_targets(events, findings, horizon_years=3)
    first = next(row for row in targets if row["inspection_id"] == 1)

    assert first["risk_event_within_horizon"] == 0
    assert first["risk_target_status"] == "OBSERVED_FUTURE_OUTCOME"
    assert first["rul_event_observed"] is False
    assert first["rul_event_years"] is None


def test_category_i_or_ii_counts_as_major_future_deficiency() -> None:
    events = [
        _event(1, 40, date(2020, 1, 1), category="III"),
        _event(2, 40, date(2022, 1, 1), category="II"),
    ]

    targets = build_inspection_targets(events, [], horizon_years=3)
    first = next(row for row in targets if row["inspection_id"] == 1)

    assert first["risk_event_within_horizon"] == 1
    assert first["rul_event_observed"] is True
