#!/usr/bin/env bash
set -u

O2W='/work/tools/osm2world/current/osm2world.sh'
INPUT='/work/data/reality_twin/factory/osm_extracts/AP_BR_00001.osm.pbf'
OUTPUT='/work/frontend/public/reality-twin/models/AP_BR_00001/AP_BR_00001.glb'

run_o2w() {
  bash "$O2W" "$@"
}

echo "Testing OSM2World CLI..."
run_o2w help >/tmp/o2w_help.txt 2>&1 || run_o2w --help >/tmp/o2w_help.txt 2>&1 || true
cat /tmp/o2w_help.txt | head -60 || true

rm -f "$OUTPUT"

echo "Running canary: AP_BR_00001"
if run_o2w convert -i "$INPUT" -o "$OUTPUT"; then
  if [ -s "$OUTPUT" ]; then
    echo "CANARY_OK"
    exit 0
  fi
fi

echo "CANARY_FAILED"
exit 22
