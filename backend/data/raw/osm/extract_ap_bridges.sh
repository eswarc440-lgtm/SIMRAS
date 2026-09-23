#!/usr/bin/env bash

set -euo pipefail

echo "============================================================"
echo " SIMRAS OSMIUM - ANDHRA PRADESH BRIDGE EXTRACTION"
echo "============================================================"

echo ""
echo "[A] Installing osmium-tool + jq..."

export DEBIAN_FRONTEND=noninteractive

apt-get update -qq

apt-get install -y -qq \
    osmium-tool \
    jq \
    ca-certificates \
    >/dev/null

echo "[PASS] osmium version:"
osmium --version | head -n 1

echo ""
echo "[B] Validating Andhra Pradesh boundary response..."

jq -e '
    type == "array"
    and length > 0
    and .[0].geojson != null
' /work/andhra_pradesh_lookup.json >/dev/null

echo "[PASS] Nominatim response contains polygon geometry."

jq '.[0].geojson' \
    /work/andhra_pradesh_lookup.json \
    > /work/andhra_pradesh_boundary.geojson

test -s /work/andhra_pradesh_boundary.geojson

echo ""
echo "[C] Boundary geometry type:"

jq -r '.type' \
    /work/andhra_pradesh_boundary.geojson

echo ""
echo "[D] Checking Southern Zone PBF..."

test -s /work/southern-zone-latest.osm.pbf

osmium fileinfo \
    /work/southern-zone-latest.osm.pbf \
    | head -n 12

echo ""
echo "[E] Clipping Southern Zone to exact Andhra Pradesh boundary..."
echo "This can take several minutes."

osmium extract \
    --strategy=complete_ways \
    --polygon=/work/andhra_pradesh_boundary.geojson \
    /work/southern-zone-latest.osm.pbf \
    --output=/work/andhra_pradesh.osm.pbf \
    --overwrite

test -s /work/andhra_pradesh.osm.pbf

echo ""
echo "[PASS] Andhra Pradesh PBF created."

echo ""
echo "[F] Extracting all mapped bridge ways..."

osmium tags-filter \
    /work/andhra_pradesh.osm.pbf \
    w/bridge \
    --output=/work/andhra_pradesh_bridges.osm.pbf \
    --overwrite

test -s /work/andhra_pradesh_bridges.osm.pbf

echo ""
echo "[G] Bridge PBF statistics..."

osmium fileinfo \
    --extended \
    /work/andhra_pradesh_bridges.osm.pbf \
    | grep -E \
        'Number of objects|Number of nodes|Number of ways|Number of relations' \
    || true

echo ""
echo "[H] Exporting bridge geometries to GeoJSON sequence..."

osmium export \
    /work/andhra_pradesh_bridges.osm.pbf \
    --output-format=geojsonseq \
    --output=/work/andhra_pradesh_bridges.geojsonseq \
    --overwrite

test -s /work/andhra_pradesh_bridges.geojsonseq

echo ""
echo "[I] Counting exported bridge features..."

LINES=$(wc -l < /work/andhra_pradesh_bridges.geojsonseq)

echo "GeoJSON bridge features: ${LINES}"

if [ "${LINES}" -lt 100 ]; then
    echo "ERROR: Unexpectedly low bridge feature count."
    exit 50
fi

echo ""
echo "============================================================"
echo " OSMIUM AP BRIDGE EXTRACTION VERIFIED SUCCESS"
echo "============================================================"
