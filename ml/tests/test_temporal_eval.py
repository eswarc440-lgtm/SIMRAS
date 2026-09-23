from __future__ import annotations

import pandas as pd

from simras_ml.nbi import stable_partition
from simras_ml.temporal_eval import build_temporal_holdouts


def _key_in_partition(*, minimum: int, maximum: int = 99) -> str:
    for index in range(100_000):
        key = f"TEST:{index:06d}"
        value = stable_partition(key)
        if minimum <= value <= maximum:
            return key
    raise AssertionError("Unable to find deterministic bridge key in requested partition")


def _panel_for(key: str, ratings: dict[int, float]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "bridge_key": key,
                "report_year": year,
                "condition_rating": rating,
            }
            for year, rating in sorted(ratings.items())
        ]
    )


def test_health_holdout_uses_2024_features_and_2025_outcome_for_heldout_bridges():
    heldout_key = _key_in_partition(minimum=85)
    training_key = _key_in_partition(minimum=0, maximum=69)
    panel = pd.concat(
        [
            _panel_for(heldout_key, {2023: 7.0, 2024: 6.0, 2025: 5.0}),
            _panel_for(training_key, {2023: 8.0, 2024: 7.0, 2025: 6.0}),
        ],
        ignore_index=True,
    )

    holdouts = build_temporal_holdouts(panel, outcome_year=2025, horizon_years=3)
    health = holdouts["health"]

    assert health["bridge_key"].tolist() == [heldout_key]
    assert health["report_year"].tolist() == [2024]
    assert health["next_condition_rating"].tolist() == [5.0]


def test_risk_holdout_uses_2022_features_and_outcomes_through_2025():
    poor_key = _key_in_partition(minimum=85)
    second_heldout_key = None
    for index in range(100_000, 200_000):
        candidate = f"TEST:{index:06d}"
        if stable_partition(candidate) >= 85 and candidate != poor_key:
            second_heldout_key = candidate
            break
    assert second_heldout_key is not None

    panel = pd.concat(
        [
            _panel_for(poor_key, {2022: 7.0, 2023: 6.0, 2024: 5.0, 2025: 4.0}),
            _panel_for(second_heldout_key, {2022: 7.0, 2023: 7.0, 2024: 6.0, 2025: 6.0}),
        ],
        ignore_index=True,
    )

    holdouts = build_temporal_holdouts(panel, outcome_year=2025, horizon_years=3)
    risk = holdouts["risk"].set_index("bridge_key")

    assert set(risk["report_year"]) == {2022}
    assert risk.loc[poor_key, "poor_within_horizon"] == 1.0
    assert risk.loc[second_heldout_key, "poor_within_horizon"] == 0.0


def test_rul_holdout_contains_only_deterioration_events_observed_in_2025():
    event_key = _key_in_partition(minimum=85)
    panel = _panel_for(event_key, {2021: 7.0, 2022: 6.0, 2023: 6.0, 2024: 5.0, 2025: 4.0})

    holdouts = build_temporal_holdouts(panel, outcome_year=2025, horizon_years=3)
    rul = holdouts["rul"]

    assert not rul.empty
    assert set(rul["bridge_key"]) == {event_key}
    assert set(rul["report_year"] + rul["rul_years"]) == {2025.0}


def test_temporal_holdouts_reject_panel_without_outcome_year():
    key = _key_in_partition(minimum=85)
    panel = _panel_for(key, {2022: 7.0, 2023: 6.0, 2024: 5.0})

    try:
        build_temporal_holdouts(panel, outcome_year=2025, horizon_years=3)
    except ValueError as exc:
        assert "2025" in str(exc)
    else:
        raise AssertionError("Expected missing outcome year to be rejected")
