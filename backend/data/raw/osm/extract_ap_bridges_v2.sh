#!/usr/bin/env bash

set -euo pipefail

echo "============================================================"
echo " SIMRAS OSMIUM - AP BRIDGE EXTRACTION V2"
echo "============================================================"

export DEBIAN_FRONTEND=noninteractive

echo ""
echo "[A] Installing osmium-tool and jq..."

apt-get update -qq

apt-get install -y -qq \
    osmium-tool \
    jq \
    ca-certificates \
    >/dev/null

echo "[PASS] $(osmium --version | head -n 1)"


echo ""
echo "[B] Building valid GeoJSON Feature boundary..."

# IMPORTANT:
# Nominatim returns .geojson as a bare geometry:
#
# {
#   "type": "MultiPolygon",
#   "coordinates": [...]
# }
#
# Osmium expects:
#
# {
#   "type": "Feature",
#   "properties": {...},
#   "geometry": {
#       "type": "MultiPolygon",
#       "coordinates": [...]
#   }
# }

jq '
{
  "type": "Feature",
  "properties": {
      "name": (.[0].display_name // "Andhra Pradesh"),
      "osm_relation": 2022095
  },
  "geometry": .[0].geojson
}
' \
/work/andhra_pradesh_lookup.json \
> /work/andhra_pradesh_boundary.geojson


echo ""
echo "[C] Validating boundary..."

jq -e '
    .type == "Feature"
    and .geometry != null
    and (
        .geometry.type == "Polygon"
        or
        .geometry.type == "MultiPolygon"
    )
' \
/work/andhra_pradesh_boundary.geojson \
>/dev/null

echo "[PASS] Boundary root type:"
jq -r '.type' \
    /work/andhra_pradesh_boundary.geojson

echo "[PASS] Boundary geometry type:"
jq -r '.geometry.type' \
    /work/andhra_pradesh_boundary.geojson


echo ""
echo "[D] Checking source PBF..."

test -s \
    /work/southern-zone-latest.osm.pbf

echo "[PASS] Southern Zone PBF available."


echo ""
echo "============================================================"
echo "[E] CLIPPING SOUTHERN ZONE TO ANDHRA PRADESH"
echo "============================================================"
echo "This may take several minutes."
echo ""

osmium extract \
    --strategy=complete_ways \
    --polygon=/work/andhra_pradesh_boundary.geojson \
    /work/southern-zone-latest.osm.pbf \
    --output=/work/andhra_pradesh.osm.pbf \
    --overwrite

test -s \
    /work/andhra_pradesh.osm.pbf

echo ""
echo "[PASS] Andhra Pradesh PBF generated."

ls -lh \
    /work/andhra_pradesh.osm.pbf


echo ""
echo "============================================================"
echo "[F] FILTERING BRIDGE WAYS"
echo "============================================================"

osmium tags-filter \
    /work/andhra_pradesh.osm.pbf \
    w/bridge \
    --output=/work/andhra_pradesh_bridges.osm.pbf \
    --overwrite

test -s \
    /work/andhra_pradesh_bridges.osm.pbf

echo ""
echo "[PASS] AP bridge PBF generated."

ls -lh \
    /work/andhra_pradesh_bridges.osm.pbf


echo ""
echo "============================================================"
echo "[G] BRIDGE OBJECT STATISTICS"
echo "============================================================"

osmium fileinfo \
    --extended \
    /work/andhra_pradesh_bridges.osm.pbf \
    | grep -E \
        'Number of objects|Number of nodes|Number of ways|Number of relations' \
    || true


echo ""
echo "============================================================"
echo "[H] EXPORTING REAL BRIDGE GEOMETRY"
echo "============================================================"

osmium export \
    /work/andhra_pradesh_bridges.osm.pbf \
    --output-format=geojsonseq \
    --output=/work/andhra_pradesh_bridges.geojsonseq \
    --overwrite

test -s \
    /work/andhra_pradesh_bridges.geojsonseq


echo ""
echo "============================================================"
echo "[I] FINAL FEATURE COUNT"
echo "============================================================"

COUNT=$(wc -l < \
    /work/andhra_pradesh_bridges.geojsonseq)

echo "Exported bridge features : ${COUNT}"

if [ "${COUNT}" -lt 100 ]; then

    echo ""
    echo "ERROR:"
    echo "Bridge count is unexpectedly low."
    echo "Import will NOT continue."

    exit 50
fi


echo ""
echo "============================================================"
echo " AP BRIDGE EXTRACTION SUCCESS"
echo "============================================================"
echo "Exported bridge features : ${COUNT}"
echo "============================================================"
