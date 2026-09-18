from __future__ import annotations

import math

import pandas as pd

from simras_ml.nbi import stable_partition


def _heldout_bridge_keys(panel: pd.DataFrame) -> set[str]:
    return {
        str(key)
        for key in panel["bridge_key"].dropna().astype(str).unique()
        if stable_partition(str(key)) >= 85
    }


def build_temporal_holdouts(
    panel: pd.DataFrame,
    *,
    outcome_year: int = 2025,
    horizon_years: int = 3,
) -> dict[str, pd.DataFrame]:
    """Build strict temporal holdouts from held-out bridge identities.

    Health uses the observation immediately before ``outcome_year`` as the
    feature row and the ``outcome_year`` condition as the target.

    Risk uses the feature row at ``outcome_year - horizon_years`` and labels
    whether the bridge reaches poor condition (rating <= 4) at any later
    observation through ``outcome_year``.

    RUL contains only rows whose first later poor-condition event is observed
    exactly in ``outcome_year``. This is an observed-event deterioration
    horizon, not a structural failure-time forecast.
    """

    required = {"bridge_key", "report_year", "condition_rating"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"Panel is missing required columns: {sorted(missing)}")

    if outcome_year not in set(panel["report_year"].dropna().astype(int)):
        raise ValueError(f"Outcome year {outcome_year} is not present in the panel")
    if horizon_years <= 0:
        raise ValueError("horizon_years must be positive")

    heldout_keys = _heldout_bridge_keys(panel)
    heldout = panel[panel["bridge_key"].astype(str).isin(heldout_keys)].copy()
    heldout = heldout.sort_values(["bridge_key", "report_year"]).reset_index(drop=True)

    health_rows: list[dict] = []
    risk_rows: list[dict] = []
    rul_rows: list[dict] = []

    risk_feature_year = outcome_year - horizon_years

    for bridge_key, group in heldout.groupby("bridge_key", sort=True):
        rows = group.sort_values("report_year").to_dict("records")
        by_year = {int(row["report_year"]): row for row in rows}

        outcome = by_year.get(outcome_year)
        previous = by_year.get(outcome_year - 1)
        if outcome is not None and previous is not None:
            record = dict(previous)
            record["next_condition_rating"] = float(outcome["condition_rating"])
            health_rows.append(record)

        risk_feature = by_year.get(risk_feature_year)
        if risk_feature is not None and outcome is not None:
            future = [
                row
                for row in rows
                if risk_feature_year < int(row["report_year"]) <= outcome_year
            ]
            poor_within_horizon = float(
                any(float(row["condition_rating"]) <= 4.0 for row in future)
            )
            record = dict(risk_feature)
            record["poor_within_horizon"] = poor_within_horizon
            risk_rows.append(record)

        for index, current in enumerate(rows[:-1]):
            current_year = int(current["report_year"])
            future = [
                row
                for row in rows[index + 1 :]
                if int(row["report_year"]) <= outcome_year
            ]
            event = next(
                (
                    row
                    for row in future
                    if float(row["condition_rating"]) <= 4.0
                    and int(row["report_year"]) > current_year
                ),
                None,
            )
            if event is None or int(event["report_year"]) != outcome_year:
                continue
            record = dict(current)
            record["rul_years"] = float(outcome_year - current_year)
            rul_rows.append(record)

    return {
        "health": pd.DataFrame(health_rows),
        "risk": pd.DataFrame(risk_rows),
        "rul": pd.DataFrame(rul_rows),
    }
