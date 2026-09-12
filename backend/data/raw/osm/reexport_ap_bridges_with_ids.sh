#!/usr/bin/env bash

set -euo pipefail

echo "============================================================"
echo " RE-EXPORT AP BRIDGES WITH OSM OBJECT IDs"
echo "============================================================"

export DEBIAN_FRONTEND=noninteractive

apt-get update -qq

apt-get install -y -qq \
    osmium-tool \
    jq \
    ca-certificates \
    >/dev/null

test -s /work/andhra_pradesh_bridges.osm.pbf

echo ""
echo "[1] Existing bridge PBF statistics"

osmium fileinfo \
    --extended \
    /work/andhra_pradesh_bridges.osm.pbf \
    | grep -E \
        'Number of nodes|Number of ways|Number of relations' \
    || true


echo ""
echo "[2] Re-exporting with unique OSM IDs..."

rm -f \
    /work/andhra_pradesh_bridges.geojsonseq

osmium export \
    /work/andhra_pradesh_bridges.osm.pbf \
    --output-format=geojsonseq \
    --add-unique-id=type_id \
    --output=/work/andhra_pradesh_bridges.geojsonseq \
    --overwrite

test -s \
    /work/andhra_pradesh_bridges.geojsonseq


echo ""
echo "[3] Exported feature count"

COUNT=$(
    wc -l \
    < /work/andhra_pradesh_bridges.geojsonseq
)

echo "GeoJSON features : ${COUNT}"


echo ""
echo "[4] Verifying IDs in first features..."

python3 - <<'PY'
import json

path = "/work/andhra_pradesh_bridges.geojsonseq"

checked = 0
with_ids = 0
line_features = 0

with open(
    path,
    "r",
    encoding="utf-8",
    errors="ignore"
) as f:

    for raw in f:

        # RFC8142 GeoJSON sequence begins each record with RS 0x1e.
        raw = raw.lstrip("\x1e").strip()

        if not raw:
            continue

        obj = json.loads(raw)

        checked += 1

        geometry = obj.get("geometry") or {}

        if geometry.get("type") in {
            "LineString",
            "MultiLineString"
        }:
            line_features += 1

        feature_id = obj.get("id")

        print(
            "sample",
            checked,
            "| id=",
            feature_id,
            "| geometry=",
            geometry.get("type")
        )

        if feature_id:
            with_ids += 1

        if checked >= 5:
            break


if checked == 0:
    raise SystemExit(
        "ERROR: no GeoJSON records"
    )

if with_ids == 0:
    raise SystemExit(
        "ERROR: unique IDs were not exported"
    )

print()
print(
    f"[PASS] IDs present in "
    f"{with_ids}/{checked} sampled features"
)
PY


echo ""
echo "============================================================"
echo " RE-EXPORT WITH OSM IDs SUCCESS"
echo "============================================================"
