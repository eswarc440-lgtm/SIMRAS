from __future__ import annotations

import pytest

from simras_etl.nasa_power import build_observation_rows


def test_build_observation_rows_and_seven_day_rainfall() -> None:
    dates = [f"2026070{day}" for day in range(1, 8)]
    rain = [0.63, 1.60, 2.59, 14.75, 35.91, 0.0, 0.2]
    payload = {
        "properties": {
            "parameter": {
                "T2M": dict.fromkeys(dates, 30.0),
                "PRECTOTCORR": dict(zip(dates, rain, strict=True)),
                "RH2M": dict.fromkeys(dates, 65.0),
                "WS10M": dict.fromkeys(dates, 6.0),
            }
        }
    }

    rows = build_observation_rows(payload, asset_code="AP_DAM_00001")
    assert len(rows) == 29
    latest_daily = [row for row in rows if row["variable"] == "rainfall_24h"][-1]
    weekly = [row for row in rows if row["variable"] == "rainfall_7d"]
    assert latest_daily["value"] == pytest.approx(0.2)
    assert len(weekly) == 1
    assert weekly[0]["value"] == pytest.approx(55.68)
    assert weekly[0]["source_type"] == "REANALYSIS"
    assert weekly[0]["is_estimated"] is True


def test_fill_values_are_excluded() -> None:
    payload = {
        "properties": {
            "parameter": {
                "T2M": {"20260701": -999.0},
                "PRECTOTCORR": {"20260701": 1.0},
                "RH2M": {"20260701": 60.0},
                "WS10M": {"20260701": 5.0},
            }
        }
    }
    rows = build_observation_rows(payload, asset_code="AP_DAM_00001")
    assert not any(row["variable"] == "temperature_2m" for row in rows)
