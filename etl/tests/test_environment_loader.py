from datetime import UTC, datetime

import pytest

from simras_etl.environment_loader import asyncpg_dsn, validate_observations


def test_asyncpg_dsn_removes_sqlalchemy_driver() -> None:
    assert asyncpg_dsn("postgresql+asyncpg://user:pass@db:5432/simras") == (
        "postgresql://user:pass@db:5432/simras"
    )


def test_validate_nasa_power_observation() -> None:
    rows = validate_observations(
        [
            {
                "asset_code": "AP_DAM_00001",
                "variable": "rainfall_24h",
                "value": "11.49",
                "unit": "mm",
                "observed_at": "2026-08-23T00:00:00Z",
                "source_type": "REANALYSIS",
                "spatial_method": "NASA_POWER_POINT_GRID_0.5x0.625_DEG",
                "quality_flag": "MODELLED_REANALYSIS",
                "confidence_score": "0.75",
                "is_estimated": "true",
            }
        ],
        "NASA_POWER_DAILY",
    )
    assert rows[0]["observed_at"] == datetime(2026, 8, 23, tzinfo=UTC)
    assert rows[0]["is_estimated"] is True


def test_validate_rejects_false_observed_provenance() -> None:
    with pytest.raises(ValueError, match="invalid provenance"):
        validate_observations(
            [
                {
                    "asset_code": "AP_DAM_NWDP_AP01VH0059",
                    "variable": "reservoir_level",
                    "value": 253.2,
                    "unit": "m",
                    "observed_at": "2026-07-31T02:30:00Z",
                    "source_type": "OBSERVED",
                    "spatial_method": "exact_station_name_and_coordinate_match",
                    "quality_flag": "MANUAL_GOVERNMENT_OBSERVATION",
                    "confidence_score": 0.9,
                    "is_estimated": True,
                }
            ],
            "NWDP_AP_RESERVOIR_DAILY",
        )
