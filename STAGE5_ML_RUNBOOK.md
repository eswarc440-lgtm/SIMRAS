# SIMRAS Stage 5 — Gated ML Runbook

This stage adds a real training pipeline without fabricating Andhra Pradesh labels.
It trains bridge deterioration models on official annual FHWA NBI histories and
publishes them only as `RESEARCH_TRANSFER`. A future local validation job is required
before `model_validated=true` is permitted. Dams and barrages continue using the
inspection-based engineering fallback.

Official source: <https://www.fhwa.dot.gov/bridge/nbi/ascii.cfm>

## 1. Build and test the ML image

```powershell
docker compose --profile ml build ml
docker compose --profile ml run --rm ml --help
docker compose --profile ml run --rm --entrypoint pytest ml -q
```

## 2. Download six annual official archives

Review the FHWA disclaimer presented from its download page before running this.
The command records acceptance explicitly.

```powershell
docker compose --profile ml run --rm ml download `
  --years 2020 2021 2022 2023 2024 2025 `
  --output-dir /data/ml/nbi `
  --accept-fhwa-disclaimer
```

## 3. Build a deterministic bridge-year panel

The same hash-selected bridges are retained across years. The default below limits
memory while retaining up to 75,000 bridges per year.

```powershell
docker compose --profile ml run --rm ml prepare `
  --years 2020 2021 2022 2023 2024 2025 `
  --input-dir /data/ml/nbi `
  --output /data/ml/nbi_panel.csv.gz `
  --max-records-per-year 75000
```

## 4. Train and enforce the gates

```powershell
docker compose --profile ml run --rm ml train `
  --panel /data/ml/nbi_panel.csv.gz `
  --artifact-dir /artifacts/bridge_nbi `
  --min-rows 100000 `
  --min-bridges 20000 `
  --min-years 5 `
  --horizon-years 3
```

Exit code `2` or manifest stage `REJECTED` means the backend will refuse the model.
Do not change thresholds merely to force acceptance.

## 5. Inspect, register, rebuild and verify

```powershell
Get-Content .\artifacts\bridge_nbi\manifest.json

docker compose build backend frontend
docker compose run --rm backend python -m scripts.register_model
docker compose run --rm backend pytest -q
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm run lint
docker compose run --rm frontend npm test
docker compose up -d --force-recreate backend frontend

curl.exe "http://127.0.0.1:8000/api/v1/analytics/models/status"
curl.exe "http://127.0.0.1:8000/api/v1/assets/AP_BR_00001/twin"
```

Expected bridge status is `RESEARCH_TRANSFER`, never `VALIDATED_LOCAL`. The UI must
show uncertainty, training scope, recommendations and the human-review warning.
Prakasam Barrage must continue to show `INSUFFICIENT_DATA` until a verified dam
inspection is entered.

## Data and Git safety

- Do not commit `data/ml/`, `artifacts/`, `.env`, tokens or the source-review ZIP.
- Preserve model manifests and metrics for the project report.
- An AP model may be promoted to `VALIDATED_LOCAL` only after asset/time-separated
  evaluation on approved AP inspection history and documented domain review.
