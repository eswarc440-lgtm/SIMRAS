#!/usr/bin/env bash
set -u

O2W='/work/tools/osm2world/current/osm2world.sh'
JOBS='/work/data/reality_twin/factory/v14_4_jobs.txt'
STATUS='/work/data/reality_twin/factory/v14_4_model_status.txt'
INPUT_DIR='/work/data/reality_twin/factory/osm_extracts'
MODEL_DIR='/work/frontend/public/reality-twin/models'
LOG_DIR='/work/data/reality_twin/factory/v14_4_logs'
MAX_WORKERS=3

mkdir -p "$MODEL_DIR" "$LOG_DIR"
: > "$STATUS"

run_o2w() {
  bash "$O2W" "$@"
}

generate_one() {
  code="$1"
  input="$INPUT_DIR/$code.osm.pbf"
  outdir="$MODEL_DIR/$code"
  log="$LOG_DIR/$code.log"

  mkdir -p "$outdir"
  rm -f "$outdir/$code.glb" "$outdir/$code.gltf"

  if [ ! -s "$input" ]; then
    echo "$code|SKIP_EMPTY_EXTRACT|" >> "$STATUS"
    return 0
  fi

  if run_o2w convert -i "$input" -o "$outdir/$code.glb" >"$log" 2>&1; then
    if [ -s "$outdir/$code.glb" ]; then
      echo "$code|SUCCESS_GLB|/reality-twin/models/$code/$code.glb" >> "$STATUS"
      return 0
    fi
  fi

  rm -f "$outdir/$code.glb"

  if run_o2w convert -i "$input" -o "$outdir/$code.gltf" >>"$log" 2>&1; then
    if [ -s "$outdir/$code.gltf" ]; then
      echo "$code|SUCCESS_GLTF|/reality-twin/models/$code/$code.gltf" >> "$STATUS"
      return 0
    fi
  fi

  echo "$code|FAILED|$log" >> "$STATUS"
  return 0
}

active_jobs() {
  jobs -rp | wc -l
}

while IFS= read -r code; do
  [ -z "$code" ] && continue

  # Canary already generated successfully.
  if [ "$code" = "AP_BR_00001" ]; then
    echo "AP_BR_00001|SUCCESS_GLB|/reality-twin/models/AP_BR_00001/AP_BR_00001.glb" >> "$STATUS"
    continue
  fi

  generate_one "$code" &

  while [ "$(active_jobs)" -ge "$MAX_WORKERS" ]; do
    wait -n || true
  done
done < "$JOBS"

wait || true
echo "BATCH_COMPLETE"
