from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from shapely.geometry import shape
from shapely.ops import unary_union


MAJOR_ROADS = {"motorway", "trunk", "primary", "secondary"}


class DisjointSet:
    def __init__(self, values: list[str]) -> None:
        self.parent = {value: value for value in values}
        self.rank = {value: 0 for value in values}

    def find(self, value: str) -> str:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1


def property_value(properties: dict[str, Any], key: str) -> Any:
    for candidate in (f"@{key}", key):
        value = properties.get(candidate)
        if value not in (None, ""):
            return value
    return None


def normalise_id(value: Any) -> str:
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def node_ids(value: Any) -> list[str]:
    if isinstance(value, list):
        return [normalise_id(item) for item in value]
    if value in (None, ""):
        return []
    text = str(value)
    try:
        decoded = json.loads(text)
        if isinstance(decoded, list):
            return [normalise_id(item) for item in decoded]
    except json.JSONDecodeError:
        pass
    return re.findall(r"\d+", text)


def geometry_rank(feature: dict[str, Any]) -> int:
    geometry_type = (feature.get("geometry") or {}).get("type", "")
    if geometry_type in {"LineString", "MultiLineString"}:
        return 2
    if geometry_type in {"Polygon", "MultiPolygon"}:
        return 1
    return 0


def most_common(values: list[str]) -> str:
    usable = [value for value in values if value]
    return Counter(usable).most_common(1)[0][0] if usable else ""


def joined_values(features: list[dict[str, Any]], key: str) -> str:
    values = {
        str(property_value(feature.get("properties", {}), key)).strip()
        for feature in features
        if property_value(feature.get("properties", {}), key) not in (None, "")
    }
    return ";".join(sorted(values))


def classify(features: list[dict[str, Any]]) -> str:
    highways = set(joined_values(features, "highway").split(";")) - {""}
    railways = set(joined_values(features, "railway").split(";")) - {""}
    if highways and railways:
        return "mixed_transport_bridge"
    if railways:
        return "rail_bridge"
    if highways & MAJOR_ROADS:
        return "major_road_bridge"
    if highways:
        return "road_bridge"
    return "other_bridge"


def load_unique_features(path: Path) -> tuple[dict[str, dict[str, Any]], int]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    features = payload.get("features", [])
    unique: dict[str, dict[str, Any]] = {}
    duplicate_geometries = 0
    for feature in features:
        properties = feature.get("properties", {})
        raw_id = property_value(properties, "id")
        if raw_id is None:
            continue
        osm_id = normalise_id(raw_id)
        existing = unique.get(osm_id)
        if existing is not None:
            duplicate_geometries += 1
            if geometry_rank(feature) <= geometry_rank(existing):
                continue
        unique[osm_id] = feature
    return unique, duplicate_geometries


def build_groups(features: dict[str, dict[str, Any]]) -> list[list[str]]:
    disjoint_set = DisjointSet(list(features))
    first_way_by_node: dict[str, str] = {}
    missing_node_lists = 0
    for osm_id, feature in features.items():
        nodes = node_ids(property_value(feature.get("properties", {}), "way_nodes"))
        if not nodes:
            missing_node_lists += 1
            continue
        for node_id in nodes:
            first_way = first_way_by_node.setdefault(node_id, osm_id)
            disjoint_set.union(osm_id, first_way)
    if missing_node_lists:
        raise ValueError(
            f"{missing_node_lists} features have no way-node list. Re-export with "
            "--attributes=type,id,version,timestamp,way_nodes."
        )
    grouped: dict[str, list[str]] = defaultdict(list)
    for osm_id in features:
        grouped[disjoint_set.find(osm_id)].append(osm_id)
    return list(grouped.values())


def write_outputs(
    features: dict[str, dict[str, Any]],
    groups: list[list[str]],
    registry_path: Path,
    crosswalk_path: Path,
) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_fields = [
        "asset_code",
        "name",
        "asset_type",
        "subtype",
        "longitude",
        "latitude",
        "osm_way_ids",
        "segment_count",
        "osm_name",
        "bridge_tag",
        "highway",
        "railway",
        "road_ref",
        "operator",
        "identity_status",
        "match_method",
        "match_confidence",
        "source_code",
        "quality_flag",
    ]
    crosswalk_fields = ["asset_code", "osm_type", "osm_way_id"]
    with registry_path.open("w", newline="", encoding="utf-8") as registry_handle, crosswalk_path.open(
        "w", newline="", encoding="utf-8"
    ) as crosswalk_handle:
        registry_writer = csv.DictWriter(registry_handle, fieldnames=registry_fields)
        crosswalk_writer = csv.DictWriter(crosswalk_handle, fieldnames=crosswalk_fields)
        registry_writer.writeheader()
        crosswalk_writer.writeheader()
        for member_ids in sorted(groups, key=lambda values: min(int(value) for value in values)):
            ordered_ids = sorted(member_ids, key=int)
            members = [features[osm_id] for osm_id in ordered_ids]
            geometries = [shape(member["geometry"]) for member in members if member.get("geometry")]
            merged = unary_union(geometries)
            point = merged.representative_point()
            names = [
                str(property_value(member.get("properties", {}), "name") or "").strip()
                for member in members
            ]
            osm_name = most_common(names)
            group_id = ordered_ids[0]
            asset_code = f"AP_BR_OSM_G_{group_id}"
            registry_writer.writerow(
                {
                    "asset_code": asset_code,
                    "name": osm_name or f"Unnamed OSM bridge group {group_id}",
                    "asset_type": "bridge",
                    "subtype": classify(members),
                    "longitude": round(point.x, 7),
                    "latitude": round(point.y, 7),
                    "osm_way_ids": ";".join(ordered_ids),
                    "segment_count": len(ordered_ids),
                    "osm_name": osm_name,
                    "bridge_tag": joined_values(members, "bridge"),
                    "highway": joined_values(members, "highway"),
                    "railway": joined_values(members, "railway"),
                    "road_ref": joined_values(members, "ref"),
                    "operator": joined_values(members, "operator"),
                    "identity_status": "NEEDS_VERIFICATION",
                    "match_method": "SHARED_OSM_NODE",
                    "match_confidence": 0.65 if len(ordered_ids) > 1 else 0.50,
                    "source_code": "OSM_GEOFABRIK",
                    "quality_flag": "UNVERIFIED_OSM_GROUP",
                }
            )
            for osm_id in ordered_ids:
                crosswalk_writer.writerow(
                    {"asset_code": asset_code, "osm_type": "way", "osm_way_id": osm_id}
                )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Conservatively group OSM bridge ways that share OSM nodes."
    )
    parser.add_argument("input_geojson", type=Path)
    parser.add_argument("output_registry_csv", type=Path)
    parser.add_argument("output_crosswalk_csv", type=Path)
    args = parser.parse_args()

    features, duplicate_geometries = load_unique_features(args.input_geojson)
    groups = build_groups(features)
    write_outputs(features, groups, args.output_registry_csv, args.output_crosswalk_csv)

    grouped_segments = sum(len(group) for group in groups if len(group) > 1)
    largest_group = max((len(group) for group in groups), default=0)
    print(f"UNIQUE OSM WAYS: {len(features)}")
    print(f"DUPLICATE GEOMETRIES REMOVED: {duplicate_geometries}")
    print(f"CONNECTED BRIDGE CANDIDATES: {len(groups)}")
    print(f"SEGMENTS IN MULTI-WAY GROUPS: {grouped_segments}")
    print(f"LARGEST GROUP: {largest_group}")
    print(f"REGISTRY: {args.output_registry_csv}")
    print(f"CROSSWALK: {args.output_crosswalk_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
