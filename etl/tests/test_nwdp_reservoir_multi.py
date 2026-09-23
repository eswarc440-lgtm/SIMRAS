from pathlib import Path

import pandas as pd

from simras_etl.nwdp_reservoir import LEVEL_COLUMN, STORAGE_COLUMN
from simras_etl.nwdp_reservoir_multi import build_matched_reservoir_observations


def test_builds_multiple_assets_and_allows_storage_only_station(tmp_path: Path) -> None:
    level = tmp_path / "level.csv"
    storage = tmp_path / "storage.csv"
    matches = tmp_path / "matches.csv"
    output = tmp_path / "output.csv"
    pd.DataFrame(
        [
            {
                "Station": "SRI SAILAM PROJECT",
                "Data Acquisition Time": "31-07-2026 08:00",
                "Latitude": 16.083056,
                "Longitude": 78.899722,
                LEVEL_COLUMN: 253.2,
            }
        ]
    ).to_csv(level, index=False)
    pd.DataFrame(
        [
            {
                "Station": "SRI SAILAM PROJECT",
                "Data Acquisition Time": "31-07-2026 08:00",
                "Latitude": 16.083056,
                "Longitude": 78.899722,
                STORAGE_COLUMN: 1407.4,
            },
            {
                "Station": "UPPER PENNAR PROJECT",
                "Data Acquisition Time": "31-07-2026 08:00",
                "Latitude": 14.336944,
                "Longitude": 77.355,
                STORAGE_COLUMN: 50.0,
            },
        ]
    ).to_csv(storage, index=False)
    pd.DataFrame(
        [
            {
                "station_name": "SRI SAILAM PROJECT",
                "asset_code": "AP_DAM_NWDP_AP01VH0059",
                "asset_latitude": 16.0866523,
                "asset_longitude": 78.8967766,
                "distance_km": 0.509,
                "level_records": 1,
                "storage_records": 1,
                "match_status": "AUTO_MATCH",
            },
            {
                "station_name": "UPPER PENNAR PROJECT",
                "asset_code": "AP_DAM_NWDP_AP01MH0011",
                "asset_latitude": 14.336717,
                "asset_longitude": 77.354158,
                "distance_km": 0.094,
                "level_records": 0,
                "storage_records": 1,
                "match_status": "AUTO_MATCH",
            },
        ]
    ).to_csv(matches, index=False)

    result = build_matched_reservoir_observations(
        level, storage, matches, output
    )
    rows = pd.read_csv(output)
    assert result["records"] == 3
    assert result["assets"] == 2
    assert set(rows["asset_code"]) == {
        "AP_DAM_NWDP_AP01VH0059",
        "AP_DAM_NWDP_AP01MH0011",
    }
    assert len(rows[rows["variable"].eq("reservoir_level")]) == 1
