from pathlib import Path

import pandas as pd

from simras_etl.nwdp_station_match import (
    build_station_match_report,
    normalize_name,
)
from simras_etl.nwdp_reservoir import LEVEL_COLUMN, STORAGE_COLUMN


def test_normalize_name_removes_generic_asset_words() -> None:
    assert normalize_name("Srisailam Project (N.S.R.S.P) Dam") == "srisailam n s r s p"


def test_station_report_auto_matches_srisailam(tmp_path: Path) -> None:
    common = {
        "Station": "SRI SAILAM PROJECT",
        "Data Acquisition Time": "31-07-2026 08:00",
        "Latitude": 16.083056,
        "Longitude": 78.899722,
    }
    level = tmp_path / "level.csv"
    storage = tmp_path / "storage.csv"
    registry = tmp_path / "registry.csv"
    output = tmp_path / "matches.csv"
    pd.DataFrame([{**common, LEVEL_COLUMN: 253.2}]).to_csv(level, index=False)
    pd.DataFrame([{**common, STORAGE_COLUMN: 1407.4}]).to_csv(storage, index=False)
    pd.DataFrame(
        [
            {
                "asset_code": "AP_DAM_NWDP_AP01VH0059",
                "name": "Srisailam Project (N.S.R.S.P)",
                "latitude": 16.0866523,
                "longitude": 78.8967766,
            }
        ]
    ).to_csv(registry, index=False)

    result = build_station_match_report(level, storage, registry, output)
    row = pd.read_csv(output).iloc[0]
    assert result["status_counts"] == {"AUTO_MATCH": 1}
    assert row["asset_code"] == "AP_DAM_NWDP_AP01VH0059"
    assert row["distance_km"] < 1


def test_station_report_rejects_distant_asset(tmp_path: Path) -> None:
    common = {
        "Station": "EXAMPLE DAM",
        "Data Acquisition Time": "31-07-2026 08:00",
        "Latitude": 16.0,
        "Longitude": 79.0,
    }
    level = tmp_path / "level.csv"
    storage = tmp_path / "storage.csv"
    registry = tmp_path / "registry.csv"
    output = tmp_path / "matches.csv"
    pd.DataFrame([{**common, LEVEL_COLUMN: 10}]).to_csv(level, index=False)
    pd.DataFrame([{**common, STORAGE_COLUMN: 20}]).to_csv(storage, index=False)
    pd.DataFrame(
        [
            {
                "asset_code": "AP_DAM_FAR",
                "name": "Example Dam",
                "latitude": 14.0,
                "longitude": 77.0,
            }
        ]
    ).to_csv(registry, index=False)

    build_station_match_report(level, storage, registry, output)
    row = pd.read_csv(output).iloc[0]
    assert row["match_status"] == "REVIEW"
