from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


SOURCE = Path(
    "/app/data/raw/osm/"
    "andhra_pradesh_bridges.geojsonseq"
)


def clean_record(raw: str) -> str:
    # RFC 8142 GeoJSON text sequences may begin with
    # ASCII Record Separator 0x1E.
    return raw.lstrip("\x1e").strip()


def extract_way_id(feature, properties):

    candidates = [
        feature.get("id"),
        properties.get("@id"),
        properties.get("id"),
        properties.get("osm_id"),
    ]

    for candidate in candidates:

        if candidate is None:
            continue

        value = str(candidate).strip()

        # osmium --add-unique-id=type_id:
        # w12345678
        match = re.fullmatch(
            r"w(\d+)",
            value,
            flags=re.IGNORECASE
        )

        if match:
            return int(match.group(1))

        # Possible OSM-style alternative.
        match = re.search(
            r"(?:way/|way:)(\d+)$",
            value,
            flags=re.IGNORECASE
        )

        if match:
            return int(match.group(1))

    return None


def main():

    if not SOURCE.exists():
        raise RuntimeError(
            f"Missing source: {SOURCE}"
        )

    total = 0

    geometry_counts = Counter()
    id_prefix_counts = Counter()

    line_features = 0
    line_way_ids = 0
    line_without_way_id = 0

    named_line_features = 0

    bridge_tagged_line_features = 0

    samples = []

    with SOURCE.open(
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as handle:

        for raw in handle:

            raw = clean_record(
                raw
            )

            if not raw:
                continue

            feature = json.loads(
                raw
            )

            total += 1

            geometry = (
                feature.get("geometry")
                or {}
            )

            geometry_type = (
                geometry.get("type")
                or "NULL"
            )

            geometry_counts[
                geometry_type
            ] += 1

            feature_id = feature.get(
                "id"
            )

            if feature_id:

                prefix = str(
                    feature_id
                )[0].lower()

                id_prefix_counts[
                    prefix
                ] += 1

            if geometry_type not in {
                "LineString",
                "MultiLineString",
            }:
                continue

            line_features += 1

            properties = (
                feature.get("properties")
                or {}
            )

            way_id = extract_way_id(
                feature,
                properties
            )

            if way_id is None:

                line_without_way_id += 1
                continue

            line_way_ids += 1

            if properties.get("name"):
                named_line_features += 1

            if properties.get("bridge") is not None:
                bridge_tagged_line_features += 1

            if len(samples) < 10:

                samples.append(
                    {
                        "way_id":
                            way_id,

                        "name":
                            properties.get(
                                "name"
                            ),

                        "bridge":
                            properties.get(
                                "bridge"
                            ),

                        "highway":
                            properties.get(
                                "highway"
                            ),

                        "railway":
                            properties.get(
                                "railway"
                            ),

                        "geometry":
                            geometry_type,
                    }
                )

    print(
        "=" * 100
    )

    print(
        "SIMRAS STEP 6C.2B - BRIDGE PARSER PREFLIGHT"
    )

    print(
        "=" * 100
    )

    print()

    print(
        f"Total exported features       : {total:,}"
    )

    print(
        f"Line/MultiLine features       : {line_features:,}"
    )

    print(
        f"Line features with WAY IDs    : {line_way_ids:,}"
    )

    print(
        f"Line features missing WAY ID  : {line_without_way_id:,}"
    )

    print(
        f"Named line bridge features    : {named_line_features:,}"
    )

    print(
        f"bridge-tagged line features   : {bridge_tagged_line_features:,}"
    )

    print()

    print(
        "GEOMETRY TYPES:"
    )

    for key, value in sorted(
        geometry_counts.items()
    ):

        print(
            f"  {key:<20} {value:,}"
        )

    print()

    print(
        "OSM ID PREFIXES:"
    )

    for key, value in sorted(
        id_prefix_counts.items()
    ):

        label = {
            "n": "node",
            "w": "way",
            "r": "relation",
        }.get(
            key,
            key
        )

        print(
            f"  {label:<20} {value:,}"
        )

    print()

    print(
        "SAMPLE USABLE BRIDGE WAYS:"
    )

    for row in samples:

        print(
            f"  w{row['way_id']} | "
            f"name={row['name']} | "
            f"bridge={row['bridge']} | "
            f"highway={row['highway']} | "
            f"railway={row['railway']} | "
            f"geometry={row['geometry']}"
        )

    print()

    # --------------------------------------------------------
    # SAFETY GATES
    # --------------------------------------------------------

    if total < 100:

        raise RuntimeError(
            "Export contains too few features."
        )

    if line_features < 100:

        raise RuntimeError(
            "Too few bridge line geometries."
        )

    if line_way_ids < 100:

        raise RuntimeError(
            "OSM way IDs are still unavailable "
            "for bridge line geometries."
        )

    coverage = (
        line_way_ids
        / line_features
        if line_features
        else 0
    )

    print(
        f"WAY-ID coverage of line features: "
        f"{coverage * 100:.2f}%"
    )

    if coverage < 0.95:

        raise RuntimeError(
            "Less than 95% of line features have OSM way IDs."
        )

    print()
    print(
        "[PASS] STATEWIDE BRIDGE PARSER INPUT VERIFIED"
    )

    print(
        "=" * 100
    )


if __name__ == "__main__":
    main()
