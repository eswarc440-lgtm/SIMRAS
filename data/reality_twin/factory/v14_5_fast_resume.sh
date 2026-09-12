#!/usr/bin/env bash
set -u
O2W='/work/tools/osm2world/current/osm2world.sh'
JOBS='/work/data/reality_twin/factory/v14_5_pending_jobs.txt'
STATUS='/work/data/reality_twin/factory/v14_4_model_status.txt'
INPUT_DIR='/work/data/reality_twin/factory/osm_extracts'
MODEL_DIR='/work/frontend/public/reality-twin/models'
LOG_DIR='/work/data/reality_twin/factory/v14_5_logs'
MAX_WORKERS=3
mkdir -p "$MODEL_DIR" "$LOG_DIR"

run_o2w(){ bash "$O2W" "$@"; }

one(){
  code="$1"
  input="$INPUT_DIR/$code.osm.pbf"
  out="$MODEL_DIR/$code"
  glb="$out/$code.glb"
  gltf="$out/$code.gltf"
  log="$LOG_DIR/$code.log"
  mkdir -p "$out"

  if [ -s "$glb" ]; then
    echo "$code|SUCCESS_GLB|/reality-twin/models/$code/$code.glb" >> "$STATUS"
    echo "[EXISTS] $code"; return
  fi
  if [ -s "$gltf" ]; then
    echo "$code|SUCCESS_GLTF|/reality-twin/models/$code/$code.gltf" >> "$STATUS"
    echo "[EXISTS] $code"; return
  fi
  if [ ! -s "$input" ]; then
    echo "$code|SKIP_EMPTY_EXTRACT|" >> "$STATUS"
    echo "[EMPTY] $code"; return
  fi

  if run_o2w convert -i "$input" -o "$glb" >"$log" 2>&1 && [ -s "$glb" ]; then
    echo "$code|SUCCESS_GLB|/reality-twin/models/$code/$code.glb" >> "$STATUS"
    echo "[DONE] $code"; return
  fi
  rm -f "$glb"

  if run_o2w convert -i "$input" -o "$gltf" >>"$log" 2>&1 && [ -s "$gltf" ]; then
    echo "$code|SUCCESS_GLTF|/reality-twin/models/$code/$code.gltf" >> "$STATUS"
    echo "[DONE] $code"; return
  fi
  echo "$code|FAILED|$log" >> "$STATUS"
  echo "[FAILED] $code"
}

running(){ jobs -rp|wc -l; }

while IFS= read -r code; do
  [ -z "$code" ] && continue
  one "$code" &
  while [ "$(running)" -ge "$MAX_WORKERS" ]; do wait -n || true; done
done < "$JOBS"
wait || true
echo "FAST_RESUME_COMPLETE"
