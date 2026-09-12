#!/usr/bin/env bash
set -euo pipefail

JOBS='/work/data/reality_twin/factory/v14_6_pending_jobs.txt'
WORKER='/work/data/reality_twin/factory/v14_6_worker.sh'
P=3

echo "Pending jobs: $(grep -cve '^[[:space:]]*$' "$JOBS")"
echo "Parallel workers: $P"

if command -v xargs >/dev/null 2>&1; then
  grep -ve '^[[:space:]]*$' "$JOBS" | xargs -n 1 -P "$P" bash "$WORKER"
else
  echo "xargs unavailable; using Bash parallel fallback."
  while IFS= read -r code; do
    [ -z "$code" ] && continue
    bash "$WORKER" "$code" &
    while [ "$(jobs -rp | wc -l)" -ge "$P" ]; do
      sleep 1
    done
  done < "$JOBS"
  wait
fi

echo "V14_6_BATCH_DONE"
