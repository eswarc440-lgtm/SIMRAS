#!/usr/bin/env bash
set -u

code="$1"
O2W='/work/tools/osm2world/current/osm2world.sh'
INPUT_DIR='/work/data/reality_twin/factory/osm_extracts'
MODEL_DIR='/work/frontend/public/reality-twin/models'
LOG_DIR='/work/data/reality_twin/factory/v14_6_logs'
STATUS_DIR='/work/data/reality_twin/factory/v14_6_attempt_status'

outdir="$MODEL_DIR/$code"
input="$INPUT_DIR/$code.osm.pbf"
glb="$outdir/$code.glb"
gltf="$outdir/$code.gltf"
log="$LOG_DIR/$code.log"
status="$STATUS_DIR/$code.status"

mkdir -p "$outdir" "$LOG_DIR" "$STATUS_DIR"

run_o2w() {
  bash "$O2W" "$@"
}

if [ -s "$glb" ]; then
  printf '%s|SUCCESS_GLB|/reality-twin/models/%s/%s.glb\n' "$code" "$code" "$code" > "$status"
  echo "[EXISTS] $code"
  exit 0
fi

if [ -s "$gltf" ]; then
  printf '%s|SUCCESS_GLTF|/reality-twin/models/%s/%s.gltf\n' "$code" "$code" "$code" > "$status"
  echo "[EXISTS] $code"
  exit 0
fi

if [ ! -s "$input" ]; then
  printf '%s|EMPTY_EXTRACT|\n' "$code" > "$status"
  echo "[EMPTY] $code"
  exit 0
fi

rm -f "$glb" "$gltf"

if run_o2w convert -i "$input" -o "$glb" >"$log" 2>&1; then
  if [ -s "$glb" ]; then
    printf '%s|SUCCESS_GLB|/reality-twin/models/%s/%s.glb\n' "$code" "$code" "$code" > "$status"
    echo "[DONE GLB] $code"
    exit 0
  fi
fi

rm -f "$glb"

if run_o2w convert -i "$input" -o "$gltf" >>"$log" 2>&1; then
  if [ -s "$gltf" ]; then
    printf '%s|SUCCESS_GLTF|/reality-twin/models/%s/%s.gltf\n' "$code" "$code" "$code" > "$status"
    echo "[DONE GLTF] $code"
    exit 0
  fi
fi

printf '%s|FAILED|%s\n' "$code" "$log" > "$status"
echo "[FAILED] $code"
exit 0
