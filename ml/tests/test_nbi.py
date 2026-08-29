from __future__ import annotations

import math

import pandas as pd

from simras_ml.nbi import add_targets, parse_fixed_width_record


def _record() -> str:
    chars = [" "] * 445

    def put(start: int, end: int, value: str) -> None:
        chars[start:end] = list(value.ljust(end - start)[: end - start])

    put(0, 3, "001")
    put(3, 18, "BRIDGE-0001")
    put(156, 160, "1990")
    put(164, 170, "012500")
    put(201, 202, "3")
    put(202, 204, "10")
    put(207, 210, "004")
    put(217, 222, "00975")
    put(222, 228, "027450")
    put(258, 259, "7")
    put(259, 260, "6")
    put(260, 261, "8")
    put(268, 271, "450")
    put(369, 371, "12")
    put(374, 375, "6")
    put(275, 276, "7")
    return "".join(chars)


def test_parse_official_fixed_width_positions() -> None:
    result = parse_fixed_width_record(_record(), 2025)
    assert result is not None
    assert result["bridge_key"] == "001:BRIDGE-0001"
    assert result["age_years"] == 35
    assert result["condition_rating"] == 6
    assert result["span_count"] == 4
    assert result["max_span_m"] == 97.5
    assert result["structure_length_m"] == 2745


def test_targets_respect_horizon_and_censoring() -> None:
    rows = []
    for bridge, conditions in {"A": [8, 7, 6, 4, 4], "B": [8, 8, 7, 7, 7]}.items():
        for year, condition in zip(range(2021, 2026), conditions, strict=True):
            rows.append(
                {
                    "bridge_key": bridge,
                    "report_year": year,
                    "condition_rating": condition,
                }
            )
    labelled = add_targets(pd.DataFrame(rows), horizon_years=3)
    a2021 = labelled[(labelled.bridge_key == "A") & (labelled.report_year == 2021)].iloc[0]
    b2021 = labelled[(labelled.bridge_key == "B") & (labelled.report_year == 2021)].iloc[0]
    b2024 = labelled[(labelled.bridge_key == "B") & (labelled.report_year == 2024)].iloc[0]
    assert a2021.poor_within_horizon == 1
    assert a2021.rul_years == 3
    assert b2021.poor_within_horizon == 0
    assert math.isnan(b2024.poor_within_horizon)
