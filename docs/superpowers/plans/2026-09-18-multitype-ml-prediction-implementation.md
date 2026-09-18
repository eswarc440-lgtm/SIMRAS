# SIMRAS Multi-Type ML Prediction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend SIMRAS from bridge-only ML inference to a reproducible, evidence-aware prediction system for BRIDGE, DAM, BARRAGE, AIRPORT, and TEMPLE, with persisted Health/Risk/RUL outputs and consistent report integration.

**Architecture:** Keep category-specific feature builders and predictors behind one routing layer. Reuse the current NBI bridge artifact path, current `Prediction` persistence, and current selected-asset report path. Use ML only where legitimate labels exist; otherwise expose an explicit engineering baseline with provenance rather than fabricated model output.

**Tech Stack:** Python 3.12, scikit-learn, pandas, numpy, joblib, FastAPI, SQLAlchemy async, PostgreSQL/PostGIS, pytest, Docker Compose, React/Vite frontend.

**Spec:** `docs/superpowers/specs/2026-09-18-multitype-ml-prediction-design.md`

## Global Constraints

- Risk classification targets ROC-AUC >= 0.97 only when an untouched held-out test genuinely supports it.
- Health and RUL are evaluated as regression problems using MAE/RMSE/R2 where appropriate; do not fabricate a single accuracy percentage.
- Transfer predictions may be displayed only with explicit provenance: `RESEARCH_TRANSFER`, model version, feature version, training scope, confidence, and local-validation status.
- Missing evidence is omitted; do not synthesize structural measurements, inspection scores, or model labels.
- Dam/barrage/airport/temple RUL may use `ENGINEERING_RUL_BASELINE` until sufficient longitudinal deterioration labels exist.
- Dam/barrage operational hydrologic risk remains separate from structural Health/Risk.
- Airports and temples must never be routed through the bridge NBI model.
- Reports, PDF/JSON/CSV, and Digital Twin views consume the same persisted prediction records rather than recalculating conflicting values.

---

## File Structure / Responsibilities

- `ml/simras_ml/nbi.py` — NBI ingestion, feature normalization, target construction, deterministic bridge identity.
- `ml/simras_ml/nbi_train.py` — bridge Health/Risk/RUL training and evaluation.
- `ml/simras_ml/cli.py` — reproducible download/prepare/train/evaluate CLI.
- `ml/simras_ml/temporal_eval.py` — new 2025 temporal-holdout evaluation utilities.
- `ml/tests/test_temporal_eval.py` — new temporal split/leakage and metric tests.
- `backend/app/services/ml_predictor.py` — unified prediction dataclasses, category routing, artifact inference, engineering baselines.
- `backend/app/services/twin_service.py` — build category inputs, refresh/persist current predictions.
- `backend/app/services/real_report_service.py` — expose accepted transfer predictions and baseline provenance.
- `backend/app/api/routes/real_reports.py` — report/PDF labels and consistent ML section.
- `backend/tests/test_ml_predictor.py` — category router and baseline behavior tests.
- `backend/tests/test_real_report_service.py` — report provenance and visibility tests.
- `backend/tests/test_prediction_readiness.py` — category support/readiness tests.
- `backend/app/services/dam_hydrology_risk.py` — keep operational hydrologic risk separate; do not convert it to structural risk.
- `artifacts/bridge_nbi/manifest.json` — promoted bridge artifact metadata and metrics.
- `artifacts/<category>/manifest.json` — future category artifact metadata only after a defensible training pipeline exists.

---

### Task 0: Preserve and verify the local first slice

**Files:**
- Modify (already changed locally): `backend/app/services/ml_predictor.py`
- Modify (already changed locally): `backend/app/services/twin_service.py`
- Test (already changed locally): `backend/tests/test_ml_predictor.py`

**Interfaces:**
- Consumes: existing `MLInput`, `MLResult`, `refresh_ml_prediction()` and `Prediction` persistence.
- Produces: category routing for BRIDGE/DAM/BARRAGE/AIRPORT/TEMPLE and explicit engineering RUL baseline objects for non-bridge categories.

- [ ] **Step 1: Inspect exactly what is modified locally**

Run from the repo root in Windows PowerShell:

```powershell
git status --short
git diff -- backend/app/services/ml_predictor.py backend/app/services/twin_service.py backend/tests/test_ml_predictor.py
```

Expected: only intentional changes in the three files above (plus any plan/spec files from this branch).

- [ ] **Step 2: Run the focused backend tests**

```powershell
docker compose run --rm backend pytest -q backend/tests/test_ml_predictor.py backend/tests/test_prediction_readiness.py
```

Expected: PASS; no skipped category-routing failures.

If the backend image uses `/app` as workdir and paths are mounted without the `backend/` prefix, run instead:

```powershell
docker compose run --rm backend pytest -q tests/test_ml_predictor.py tests/test_prediction_readiness.py
```

- [ ] **Step 3: Run the current backend unit suite used by the local agent**

```powershell
docker compose run --rm backend pytest -q backend/tests
```

If `/app` maps directly to `backend`, use:

```powershell
docker compose run --rm backend pytest -q tests
```

Expected: the same or better than the locally reported `32 passed`; record any unrelated legacy failures separately rather than masking them.

- [ ] **Step 4: Commit the first slice**

```powershell
git add backend/app/services/ml_predictor.py backend/app/services/twin_service.py backend/tests/test_ml_predictor.py
git commit -m "feat: add multitype prediction routing and RUL baselines"
git push -u origin feature/ml-multitype-predictions-20260918
```

Expected: clean working tree for these files and remote branch updated.

---

### Task 1: Add a leakage-safe 2025 temporal holdout for the bridge model

**Files:**
- Create: `ml/simras_ml/temporal_eval.py`
- Modify: `ml/simras_ml/cli.py`
- Test: `ml/tests/test_temporal_eval.py`

**Interfaces:**
- Consumes: panel columns produced by `simras_ml.nbi.build_panel()` and targets produced by `add_targets()`.
- Produces: `temporal_split(panel, test_year=2025)` and `evaluate_bridge_temporal_holdout(...)` returning a serializable metrics dictionary.

- [ ] **Step 1: Write the failing split tests**

Create `ml/tests/test_temporal_eval.py` with tests equivalent to:

```python
import pandas as pd

from simras_ml.temporal_eval import temporal_split


def test_temporal_split_holds_out_2025_and_prevents_bridge_overlap():
    frame = pd.DataFrame(
        {
            "bridge_key": ["A", "A", "B", "C", "D"],
            "report_year": [2024, 2025, 2024, 2025, 2023],
        }
    )

    train, test = temporal_split(frame, test_year=2025)

    assert set(test["report_year"]) == {2025}
    assert not (set(train["bridge_key"]) & set(test["bridge_key"]))
    assert "A" not in set(train["bridge_key"])
```

- [ ] **Step 2: Run the new test and confirm RED**

```powershell
docker compose run --rm ml pytest -q tests/test_temporal_eval.py
```

Expected: FAIL because `simras_ml.temporal_eval` does not yet exist.

- [ ] **Step 3: Implement the split**

Create `ml/simras_ml/temporal_eval.py` with this contract:

```python
from __future__ import annotations

import pandas as pd


def temporal_split(frame: pd.DataFrame, *, test_year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    test = frame[frame["report_year"] == test_year].copy()
    test_keys = set(test["bridge_key"].astype(str))
    train = frame[
        (frame["report_year"] < test_year)
        & (~frame["bridge_key"].astype(str).isin(test_keys))
    ].copy()
    if train.empty or test.empty:
        raise ValueError("Temporal split produced an empty train or test partition")
    return train, test
```

This deliberately excludes from training any bridge that appears in the 2025 test set, which prevents identity leakage while preserving a strict temporal holdout.

- [ ] **Step 4: Re-run the split tests**

```powershell
docker compose run --rm ml pytest -q tests/test_temporal_eval.py
```

Expected: PASS.

- [ ] **Step 5: Add an `evaluate-temporal` CLI command**

Modify `ml/simras_ml/cli.py` to add:

```python
evaluate = sub.add_parser("evaluate-temporal", help="Evaluate bridge models on a strict temporal holdout")
evaluate.add_argument("--panel", type=Path, default=Path("/data/ml/nbi_panel.csv.gz"))
evaluate.add_argument("--test-year", type=int, default=2025)
evaluate.add_argument("--artifact-dir", type=Path, default=Path("/artifacts/bridge_nbi"))
```

The command must load the panel, call the temporal evaluation function, print JSON, and return non-zero only when required evaluation inputs are invalid. It must never rewrite the promoted artifact during evaluation.

- [ ] **Step 6: Commit**

```powershell
git add ml/simras_ml/temporal_eval.py ml/simras_ml/cli.py ml/tests/test_temporal_eval.py
git commit -m "feat: add 2025 bridge temporal holdout evaluation"
```

---

### Task 2: Extend the bridge dataset through 2025 and measure the real result

**Files:**
- Data: `data/ml/nbi/nbi_2025.zip` (local data; do not commit the archive)
- Generated: `data/ml/nbi_panel_2020_2025.csv.gz` (local generated data unless repository policy permits artifacts)
- Read/modify only if parser compatibility requires it: `ml/simras_ml/nbi.py`

**Interfaces:**
- Consumes: official FHWA annual NBI download supported by existing `download_year()`.
- Produces: a reproducible 2020–2025 bridge-year panel and temporal metrics JSON.

- [ ] **Step 1: Download official 2020–2025 NBI archives through the existing CLI**

```powershell
docker compose run --rm ml python -m simras_ml.cli download --years 2020 2021 2022 2023 2024 2025 --output-dir /data/ml/nbi --accept-fhwa-disclaimer
```

Expected: one local archive path printed per year. If 2025 format compatibility fails, stop and update only `nbi.py` with a test fixture that reproduces the exact parser mismatch; do not silently substitute a different source.

- [ ] **Step 2: Build the 2020–2025 panel**

```powershell
docker compose run --rm ml python -m simras_ml.cli prepare --years 2020 2021 2022 2023 2024 2025 --input-dir /data/ml/nbi --output /data/ml/nbi_panel_2020_2025.csv.gz --max-records-per-year 75000
```

Expected: JSON showing row count, unique bridge count, and output path.

- [ ] **Step 3: Run the strict 2025 temporal evaluation**

```powershell
docker compose run --rm ml python -m simras_ml.cli evaluate-temporal --panel /data/ml/nbi_panel_2020_2025.csv.gz --test-year 2025 --artifact-dir /artifacts/bridge_nbi
```

Record at least:
- ROC-AUC
- PR-AUC
- F1 at the declared threshold
- ordinary accuracy
- Brier score
- ECE/calibration
- Health MAE/RMSE
- Health persistence MAE
- RUL MAE on observed deterioration events, with event count

- [ ] **Step 4: Apply the promotion decision exactly**

Promote/retrain only if the final untouched holdout is at least as trustworthy as the existing artifact. The promotion report must explicitly state whether ROC-AUC >= 0.97 was achieved. If it is below 0.97, keep the existing accepted research-transfer artifact and report the new temporal result rather than fabricating a higher score.

- [ ] **Step 5: Commit only code/metadata, not raw FHWA archives**

```powershell
git status --short
```

Verify raw archives/panels are ignored or left untracked. Commit only parser/evaluation code or a compact JSON metrics report if project policy allows it.

---

### Task 3: Make the unified prediction contract explicit and stable

**Files:**
- Modify: `backend/app/services/ml_predictor.py`
- Modify: `backend/app/services/twin_service.py`
- Test: `backend/tests/test_ml_predictor.py`
- Test: `backend/tests/test_prediction_readiness.py`

**Interfaces:**
- Produces a single result shape with these keys: `category`, `health_score`, `risk_score`, `risk_level`, `confidence`, `remaining_life_years`, `rul_method`, `model_name`, `model_version`, `feature_version`, `training_scope`, `validation_status`, `prediction_method`, `prediction_time`.

- [ ] **Step 1: Add tests for provenance and no cross-category model use**

Tests must assert all of the following:

```python
assert bridge_result.training_scope == "FHWA_NBI_US_BRIDGES_RESEARCH_TRANSFER"
assert dam_result.rul_method == "ENGINEERING_RUL_BASELINE"
assert airport_result.prediction_method != "calibrated_nbi_bridge_ml"
assert temple_result.prediction_method != "calibrated_nbi_bridge_ml"
```

Unsupported Health/Risk values for categories without a trained accepted model must be `None`/omitted rather than copied from bridge inference.

- [ ] **Step 2: Run the tests and confirm any missing behavior fails**

```powershell
docker compose run --rm backend pytest -q tests/test_ml_predictor.py tests/test_prediction_readiness.py
```

- [ ] **Step 3: Implement the smallest routing/provenance changes needed**

Keep the router explicit:

```python
category = str(data.asset_type or "").upper()
if category == "BRIDGE":
    return predict_bridge(...)
if category in {"DAM", "BARRAGE", "AIRPORT", "TEMPLE"}:
    return predict_engineering_baseline(...)
return None
```

Do not add a generic fallback that silently scores unknown categories.

- [ ] **Step 4: Re-run focused tests and commit**

```powershell
docker compose run --rm backend pytest -q tests/test_ml_predictor.py tests/test_prediction_readiness.py
git add backend/app/services/ml_predictor.py backend/app/services/twin_service.py backend/tests/test_ml_predictor.py backend/tests/test_prediction_readiness.py
git commit -m "feat: stabilize multitype prediction contract"
```

---

### Task 4: Show accepted research-transfer predictions in real reports

**Files:**
- Modify: `backend/app/services/real_report_service.py`
- Modify: `backend/app/api/routes/real_reports.py`
- Test: `backend/tests/test_real_report_service.py`
- Test: `backend/tests/test_report_truth.py`

**Interfaces:**
- Consumes: persisted/current `ai` prediction payload from `build_twin()`.
- Produces: `ml_prediction` when status is `RESEARCH_TRANSFER`, `VALIDATED_LOCAL`, or `ENGINEERING_BASELINE`, provided provenance is complete.

- [ ] **Step 1: Write tests that fail under the old local-only gate**

Add assertions equivalent to:

```python
payload = build_real_report_payload("AP_BR_00001", twin_with_research_transfer, {})
assert payload["ml_prediction"]["validation_status"] == "RESEARCH_TRANSFER"
assert payload["ml_prediction"]["training_scope"]
assert payload["ml_prediction"]["model_version"]
```

Also assert that a payload missing training scope/model version is not promoted as a model prediction.

- [ ] **Step 2: Replace the local-only report gate**

In `real_report_service.py`, accept explicit research-transfer and engineering-baseline statuses instead of requiring `LOCAL_ANDHRA_PRADESH_VALIDATION`. Keep synthetic/demo values excluded.

- [ ] **Step 3: Rename the PDF section**

Change the report section title from:

```text
Eligible locally validated ML prediction
```

to:

```text
ML / Engineering Decision-Support Prediction
```

Also adjust the introductory copy so it does not claim all displayed ML is locally validated.

- [ ] **Step 4: Run report tests and commit**

```powershell
docker compose run --rm backend pytest -q tests/test_real_report_service.py tests/test_report_truth.py
git add backend/app/services/real_report_service.py backend/app/api/routes/real_reports.py backend/tests/test_real_report_service.py backend/tests/test_report_truth.py
git commit -m "feat: expose provenance-labeled transfer predictions in reports"
```

---

### Task 5: Dam and barrage structural-model readiness audit plus RUL baseline

**Files:**
- Create: `ml/simras_ml/dam_barrage_features.py`
- Create: `ml/tests/test_dam_barrage_features.py`
- Modify: `backend/app/services/ml_predictor.py`
- Modify: `backend/app/api/routes/dam_barrage_profile.py`

**Interfaces:**
- Produces normalized dam/barrage feature dictionaries from verified evidence.
- Keeps `score_dam_barrage_operational_risk()` as operational risk only.

- [ ] **Step 1: Add feature-builder tests**

Use explicit source-backed input fields such as:

```python
source = {
    "built_year": 1957,
    "height_m": 10.6,
    "total_length_m": 3592.67,
    "gate_count": 175,
    "gate_width_m": 18.29,
    "gate_height_m": 3.34,
}
```

Assert the builder returns age plus available dimensions and does not invent missing inspection condition.

- [ ] **Step 2: Implement deterministic feature normalization**

The builder must return `None` for absent evidence. It must not convert hydrologic operational risk into a structural-health label.

- [ ] **Step 3: Implement category-specific engineering RUL baselines**

Use this explicit contract:

```python
remaining = max(0.0, reference_service_life_years - age_years)
```

The result must include `rul_method="ENGINEERING_RUL_BASELINE"`, the chosen reference service life, and its provenance/assumption text. Do not call this ML.

- [ ] **Step 4: Remove public `WITHHELD` sentinels from the dam/barrage profile response when a legitimate baseline exists**

Return structured `prediction_policy` metadata describing what is ML, what is operational risk, and what is an engineering baseline.

- [ ] **Step 5: Run tests and commit**

```powershell
docker compose run --rm ml pytest -q tests/test_dam_barrage_features.py
docker compose run --rm backend pytest -q tests/test_ml_predictor.py tests/test_dam_hydrology_risk.py
git add ml/simras_ml/dam_barrage_features.py ml/tests/test_dam_barrage_features.py backend/app/services/ml_predictor.py backend/app/api/routes/dam_barrage_profile.py
git commit -m "feat: add dam and barrage evidence features and RUL baseline"
```

---

### Task 6: Airport prediction readiness and pavement/service-life baseline

**Files:**
- Create: `ml/simras_ml/airport_features.py`
- Create: `ml/tests/test_airport_features.py`
- Modify: `backend/app/services/ml_predictor.py`
- Test: `backend/tests/test_ml_predictor.py`

**Interfaces:**
- Consumes runway dimensions, surface/pavement strength, built/commissioning year if verified, maintenance/rehabilitation records, and environmental exposure.
- Produces an airport feature dictionary and engineering RUL baseline; Health/Risk remain absent until a defensible labeled pavement dataset is trained and accepted.

- [ ] **Step 1: Write tests using verified AAI-style runway evidence**

Example test input:

```python
source = {
    "runway_length_m": 3360,
    "runway_width_m": 45,
    "runway_surface": "asphalt",
    "pavement_strength": "PCN",
}
```

Assert no bridge-only fields are required and no bridge model method is returned.

- [ ] **Step 2: Implement the airport feature builder and baseline routing**

Keep unsupported Health/Risk as absent. Return confidence based on evidence completeness, not a hard-coded high confidence.

- [ ] **Step 3: Run tests and commit**

```powershell
docker compose run --rm ml pytest -q tests/test_airport_features.py
docker compose run --rm backend pytest -q tests/test_ml_predictor.py
git add ml/simras_ml/airport_features.py ml/tests/test_airport_features.py backend/app/services/ml_predictor.py backend/tests/test_ml_predictor.py
git commit -m "feat: add airport evidence features and service-life baseline"
```

---

### Task 7: Temple prediction readiness and structural evidence baseline

**Files:**
- Create: `ml/simras_ml/temple_features.py`
- Create: `ml/tests/test_temple_features.py`
- Modify: `backend/app/services/ml_predictor.py`
- Test: `backend/tests/test_ml_predictor.py`

**Interfaces:**
- Consumes verified temple identity/architecture dimensions and maintenance/inspection evidence.
- Produces a structural evidence feature dictionary and engineering baseline only when built-year/reference-life inputs are supported.

- [ ] **Step 1: Write tests using verified temple engineering evidence**

Example input:

```python
source = {
    "main_gopuram_height_m": 36.5,
    "pathala_ganapathi_depth_ft": 20,
}
```

Assert that absence of built year means no fabricated RUL and absence of labeled damage means no fabricated Health/Risk.

- [ ] **Step 2: Implement the temple feature builder**

Do not infer condition from architectural height, temple age, or religious importance. Condition labels must come from actual structural/inspection evidence.

- [ ] **Step 3: Run tests and commit**

```powershell
docker compose run --rm ml pytest -q tests/test_temple_features.py
docker compose run --rm backend pytest -q tests/test_ml_predictor.py
git add ml/simras_ml/temple_features.py ml/tests/test_temple_features.py backend/app/services/ml_predictor.py backend/tests/test_ml_predictor.py
git commit -m "feat: add temple structural evidence feature path"
```

---

### Task 8: End-to-end persistence and report verification for new data

**Files:**
- Modify if needed: `backend/app/services/twin_service.py`
- Modify if needed: `backend/app/api/routes/records.py`
- Test: `backend/tests/test_ml_predictor.py`
- Test: `backend/tests/test_real_report_service.py`

**Interfaces:**
- Consumes: `POST /assets/{asset_code}/predictions/refresh`.
- Produces: persisted prediction history and selected-asset real-report output using the same records.

- [ ] **Step 1: Verify a bridge refresh persists Health/Risk/RUL**

```powershell
$headers = @{ "X-Admin-Key" = $env:SIMRAS_ADMIN_KEY }
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/assets/AP_BR_00001/predictions/refresh" -Headers $headers
```

Expected: model metadata plus Health/Risk/RUL from the accepted bridge artifact.

- [ ] **Step 2: Verify a dam/barrage refresh returns a baseline/provenance path rather than bridge inference**

Use one known dam/barrage asset code from the database and confirm `rul_method=ENGINEERING_RUL_BASELINE` when required inputs are present.

- [ ] **Step 3: Verify prediction history**

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/assets/AP_BR_00001/predictions/history"
```

Expected: latest persisted records include model/feature version, confidence, status, and timestamp.

- [ ] **Step 4: Verify real report consumes the same provenance**

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/real-reports/AP_BR_00001"
```

Expected: report ML section contains the same model version/training scope/status as the persisted prediction.

- [ ] **Step 5: Commit any required integration fix**

```powershell
git add backend/app/services/twin_service.py backend/app/api/routes/records.py backend/tests/test_ml_predictor.py backend/tests/test_real_report_service.py
git commit -m "test: verify multitype prediction persistence and reports"
```

---

### Task 9: Docker and final-review acceptance gate

**Files:**
- No code changes unless a real failure is found.

**Interfaces:**
- Validates the complete VS Code + Docker workflow.

- [ ] **Step 1: Run ML tests**

```powershell
docker compose run --rm ml pytest -q tests
```

- [ ] **Step 2: Run backend focused acceptance suite**

```powershell
docker compose run --rm backend pytest -q tests/test_ml_predictor.py tests/test_prediction_readiness.py tests/test_real_report_service.py tests/test_report_truth.py tests/test_dam_hydrology_risk.py
```

- [ ] **Step 3: Build backend/frontend images**

```powershell
docker compose build backend frontend
```

- [ ] **Step 4: Start runtime**

```powershell
docker compose up -d db backend frontend
```

- [ ] **Step 5: Verify services**

```powershell
Invoke-WebRequest "http://127.0.0.1:8000/health" -UseBasicParsing
Invoke-WebRequest "http://127.0.0.1:5173" -UseBasicParsing
```

If the backend health endpoint differs in this repository, use the endpoint already configured in Compose healthchecks rather than inventing a new one.

- [ ] **Step 6: Record final model evidence for the review**

Prepare a compact final table containing:
- Bridge risk ROC-AUC, PR-AUC, Accuracy, F1, Brier/ECE
- Bridge Health MAE/RMSE and persistence-baseline MAE
- Bridge RUL MAE/event count
- Dam/Barrage/Airport/Temple status: trained transfer model vs engineering baseline, with exact provenance
- One sample prediction/report per supported category

Do not label a category as ML-trained unless a saved accepted artifact and held-out evaluation actually exist.

- [ ] **Step 7: Push all verified commits**

```powershell
git status
git push origin feature/ml-multitype-predictions-20260918
```

Expected: clean or intentionally documented working tree and all implementation commits on the remote feature branch.

---

## Plan Self-Review

- Spec coverage: Bridge temporal evaluation, new-data inference, category routing, research-transfer report visibility, dam/barrage operational-risk separation, airport/temple non-bridge routing, engineering RUL baselines, persistence, reports, Docker acceptance are all mapped to tasks.
- Placeholder scan: no implementation step relies on TBD/TODO values; optional ML training for categories without defensible labels is intentionally not fabricated.
- Type consistency: the plan preserves existing `MLInput`/`MLResult` patterns and introduces only explicit category/provenance fields described in the spec.
