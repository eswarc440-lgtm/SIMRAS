from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import Point

from simras_etl.india_wris import dms_to_decimal, normalize_identifier


def test_normalize_identifier() -> None:
    assert normalize_identifier(" AP-01 MH 0009 ") == "AP01MH0009"
    assert normalize_identifier(None) == ""


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ('16° 30\' 27.000" N', 16.5075),
        ('80° 36\' 19.000" E', 80.6052777778),
        ('12° 30\' 0" S', -12.5),
    ],
)
def test_dms_to_decimal(value: str, expected: float) -> None:
    assert dms_to_decimal(value) == pytest.approx(expected)


def test_geopandas_dependency_supports_point_geometry() -> None:
    frame = gpd.GeoDataFrame(
        [{"asset_code": "AP_DAM_NWDP_AP01MH0009"}],
        geometry=[Point(80.605277778, 16.5075)],
        crs="EPSG:4326",
    )
    assert frame.geometry.is_valid.all()
