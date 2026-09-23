from pathlib import Path

import pandas as pd
import pytest

from simras_etl.nwdp_reservoir import build_reservoir_observations


def _row(value_column: str, value: float, latitude: float = 16.083056) -> dict:
    return {
        "Station": "SRI SAILAM PROJECT",
        "Latitude": latitude,
        "Longitude": 78.899722,
        "Data Acquisition Time": "31-07-2026 08:00",
        value_column: value,
    }


def test_build_reservoir_observations(tmp_path: Path) -> None:
    level = tmp_path / "level.csv"
    storage = tmp_path / "storage.csv"
    output = tmp_path / "output.csv"
    pd.DataFrame([_row("Manual Daily Reservoir water level (m)", 253.197364)]).to_csv(
        level, index=False
    )
    pd.DataFrame([_row("Manual Daily Reservoir storage (mcm)", 1407.4424)]).to_csv(
        storage, index=False
    )
    result = build_reservoir_observations(level, storage, output)
    generated = pd.read_csv(output)
    assert result["records"] == 2
    assert set(generated["variable"]) == {"reservoir_level", "reservoir_storage"}
    assert set(generated["observed_at"]) == {"2026-07-31T02:30:00Z"}
    assert not generated["is_estimated"].any()


def test_rejects_station_outside_distance_gate(tmp_path: Path) -> None:
    level = tmp_path / "level.csv"
    storage = tmp_path / "storage.csv"
    output = tmp_path / "output.csv"
    pd.DataFrame(
        [_row("Manual Daily Reservoir water level (m)", 253.197364, latitude=17.0)]
    ).to_csv(level, index=False)
    pd.DataFrame(
        [_row("Manual Daily Reservoir storage (mcm)", 1407.4424, latitude=17.0)]
    ).to_csv(storage, index=False)
    with pytest.raises(ValueError, match="maximum"):
        build_reservoir_observations(level, storage, output)
