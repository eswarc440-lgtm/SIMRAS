from datetime import UTC, datetime

from simras_etl.osm_statewide import (
    classify_subtype,
    element_geometry,
    transform_layer,
)


def test_road_geometry_is_linestring() -> None:
    geometry = element_geometry(
        "road",
        {
            "geometry": [
                {"lon": 80.0, "lat": 16.0},
                {"lon": 80.2, "lat": 16.1},
            ]
        },
    )
    assert geometry is not None
    assert geometry.geom_type == "LineString"


def test_point_feature_uses_overpass_center() -> None:
    geometry = element_geometry(
        "airport",
        {"center": {"lon": 80.8, "lat": 16.5}},
    )
    assert geometry is not None
    assert geometry.x == 80.8
    assert geometry.y == 16.5


def test_temple_with_wikidata_is_landmark() -> None:
    assert (
        classify_subtype("temple", {"wikidata": "Q123", "name": "Example Temple"})
        == "landmark_temple"
    )


def test_transform_labels_osm_as_source_reported() -> None:
    retrieved_at = datetime(2026, 8, 28, tzinfo=UTC)
    rows = transform_layer(
        "bridge",
        {
            "elements": [
                {
                    "type": "way",
                    "id": 42,
                    "center": {"lon": 80.5, "lat": 16.5},
                    "tags": {
                        "name": "Example Bridge",
                        "bridge": "yes",
                        "highway": "primary",
                    },
                }
            ]
        },
        retrieved_at,
    )
    assert len(rows) == 1
    assert rows[0].external_id == "way/42"
    assert rows[0].identity_status == "SOURCE_REPORTED"
    assert rows[0].subtype == "major_road_bridge"
    assert rows[0].confidence_score == 0.75


def test_transform_deduplicates_same_osm_element() -> None:
    retrieved_at = datetime(2026, 8, 28, tzinfo=UTC)
    element = {
        "type": "node",
        "id": 99,
        "lat": 16.5,
        "lon": 80.5,
        "tags": {"name": "Example Airport", "aeroway": "aerodrome"},
    }
    rows = transform_layer(
        "airport",
        {"elements": [element, element]},
        retrieved_at,
    )
    assert len(rows) == 1
