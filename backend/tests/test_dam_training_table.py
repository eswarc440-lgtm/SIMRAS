from __future__ import annotations

from datetime import date, datetime, timezone

from app.services.dam_training_table import build_dam_training_rows


UTC = timezone.utc


def _event(
    event_id: int,
    asset_id: int,
    when: date,
    *,
    condition: str | None = None,
    category: str | None = None,
) -> dict:
    return {
        "id": event_id,
        "asset_id": asset_id,
        "inspection_date": when,
        "inspection_category": category,
        "overall_condition": condition,
        "is_official": True,
        "is_synthetic": False,
        "training_eligible": True,
    }


def _finding(
    inspection_id: int,
    component: str,
    condition: str,
    *,
    severity: str = "NONE",
) -> dict:
    return {
        "inspection_id": inspection_id,
        "component_name": component,
        "condition_state": condition,
        "severity": severity,
        "is_official": True,
        "is_synthetic": False,
    }


def _env(asset_id: int, variable: str, value: float, when: datetime) -> dict:
    return {
        "asset_id": asset_id,
        "variable": variable,
        "value": value,
        "observed_at": when,
        "quality_flag": "VALID",
        "is_estimated": False,
    }


def test_training_row_never_uses_environment_observation_after_inspection_cutoff() -> None:
    events = [_event(1, 10, date(2024, 6, 15), condition="SATISFACTORY")]
    findings = [
        _finding(1, "dam_body", "SATISFACTORY"),
        _finding(1, "foundation", "SATISFACTORY"),
        _finding(1, "spillway", "FAIR"),
        _finding(1, "gates", "FAIR"),
        _finding(1, "drainage", "POOR"),
        _finding(1, "seepage", "SATISFACTORY"),
    ]
    environment = [
        _env(10, "rainfall_24h", 42.0, datetime(2024, 6, 14, 12, tzinfo=UTC)),
        _env(10, "rainfall_24h", 999.0, datetime(2024, 6, 16, 12, tzinfo=UTC)),
    ]

    rows = build_dam_training_rows(
        events=events,
        findings=findings,
        environment=environment,
        engineering_by_asset={10: {"built_year": 1984, "height_m": 31.0}},
        applicable_components=[
            "dam_body",
            "foundation",
            "spillway",
            "gates",
            "drainage",
            "seepage",
            "instrumentation",
        ],
        minimum_health_coverage=0.70,
        risk_horizon_years=3,
    )

    row = rows[0]
    assert row["features"]["rainfall_24h"] == 42.0
    assert row["features"]["built_year"] == 1984
    assert row["features"]["height_m"] == 31.0
    assert 999.0 not in row["features"].values()


def test_current_inspection_findings_are_labels_not_same_row_predictor_features() -> None:
    events = [_event(1, 20, date(2024, 7, 1), condition="SATISFACTORY")]
    findings = [
        _finding(1, "dam_body", "SATISFACTORY"),
        _finding(1, "foundation", "SATISFACTORY"),
        _finding(1, "spillway", "FAIR"),
        _finding(1, "gates", "FAIR"),
        _finding(1, "drainage", "POOR"),
        _finding(1, "seepage", "SATISFACTORY"),
    ]

    rows = build_dam_training_rows(
        events=events,
        findings=findings,
        environment=[],
        engineering_by_asset={20: {"built_year": 1990}},
        applicable_components=[
            "dam_body",
            "foundation",
            "spillway",
            "gates",
            "drainage",
            "seepage",
            "instrumentation",
        ],
        minimum_health_coverage=0.70,
        risk_horizon_years=3,
    )

    row = rows[0]
    assert row["targets"]["health_score_target"] is not None
    assert row["targets"]["health_target_status"] == "DERIVED_FROM_OFFICIAL_CWC_CONDITIONS"
    assert "current_gates_condition" not in row["features"]
    assert "current_health_score" not in row["features"]


def test_only_prior_inspection_summary_can_be_used_as_history_feature() -> None:
    events = [
        _event(1, 30, date(2022, 6, 1), condition="SATISFACTORY"),
        _event(2, 30, date(2024, 6, 1), condition="MAJOR_DEFICIENCY"),
    ]
    findings = [
        _finding(1, "gates", "SATISFACTORY", severity="NONE"),
        _finding(2, "gates", "UNSATISFACTORY", severity="MAJOR"),
    ]

    rows = build_dam_training_rows(
        events=events,
        findings=findings,
        environment=[],
        engineering_by_asset={30: {"built_year": 1978}},
        applicable_components=["gates"],
        minimum_health_coverage=1.0,
        risk_horizon_years=3,
    )

    second = next(row for row in rows if row["inspection_id"] == 2)
    assert second["features"]["previous_inspection_count"] == 1
    assert second["features"]["previous_major_deficiency_count"] == 0
    assert second["features"]["days_since_previous_inspection"] in {730, 731}


def test_future_inspection_creates_risk_and_rul_target_but_not_future_features() -> None:
    events = [
        _event(1, 40, date(2021, 1, 1), condition="SATISFACTORY"),
        _event(2, 40, date(2023, 1, 1), condition="MAJOR_DEFICIENCY"),
    ]
    findings = [
        _finding(1, "gates", "SATISFACTORY", severity="NONE"),
        _finding(2, "gates", "UNSATISFACTORY", severity="MAJOR"),
    ]
    environment = [
        _env(40, "rainfall_24h", 10.0, datetime(2020, 12, 31, 6, tzinfo=UTC)),
        _env(40, "rainfall_24h", 777.0, datetime(2022, 12, 31, 6, tzinfo=UTC)),
    ]

    rows = build_dam_training_rows(
        events=events,
        findings=findings,
        environment=environment,
        engineering_by_asset={40: {"built_year": 1965}},
        applicable_components=["gates"],
        minimum_health_coverage=1.0,
        risk_horizon_years=3,
    )

    first = next(row for row in rows if row["inspection_id"] == 1)
    assert first["targets"]["risk_event_within_horizon"] == 1
    assert first["targets"]["rul_event_observed"] is True
    assert 1.99 <= first["targets"]["rul_event_years"] <= 2.01
    assert first["features"]["rainfall_24h"] == 10.0
    assert 777.0 not in first["features"].values()
