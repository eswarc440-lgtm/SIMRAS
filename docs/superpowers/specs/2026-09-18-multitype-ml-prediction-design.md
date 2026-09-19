# SIMRAS Multi-Type ML Prediction Design

Date: 2026-09-18
Branch: `feature/ml-multitype-predictions-20260918`

## Goal

Extend SIMRAS from bridge-only ML inference to a truthful, auditable prediction system for BRIDGE, DAM, BARRAGE, AIRPORT, and TEMPLE assets while preserving evidence provenance. Predictions must support new input rows without retraining for every inference and must integrate with the existing prediction history, Digital Twin, Reports page, PDF, CSV, and JSON outputs.

## Core Principles

1. Use a category-specific model or evidence-backed baseline for each asset type rather than one pooled model across incompatible structures.
2. Risk classification targets 0.97+ ROC-AUC only when a held-out test supports it. Accuracy, F1, PR-AUC, Brier score, and calibration are also reported.
3. Health and RUL are regression tasks and are evaluated using MAE, RMSE, and R2 where appropriate rather than fabricated accuracy percentages.
4. Transfer-model outputs may be shown in reports when clearly labeled `RESEARCH_TRANSFER`, with model version, training scope, confidence, and local-validation status.
5. Missing evidence must not be replaced with invented engineering values.
6. Dam/barrage/airport/temple RUL may use an explicitly labeled engineering service-life baseline until legitimate longitudinal deterioration labels are sufficient for ML.

## Existing SIMRAS Assets to Reuse

- Existing bridge NBI training pipeline and artifacts.
- Existing `POST /assets/{asset_code}/predictions/refresh` endpoint.
- Existing `Prediction` persistence and history.
- Existing real-report pipeline and PDF generation.
- Existing dam/barrage engineering and hydrology tables and operational hydrologic risk engine.
- Existing airport engineering and maintenance evidence.
- Existing temple engineering/identity evidence.

## Model Architecture

### Bridge

Training source: FHWA National Bridge Inventory, extended through 2025 where compatible.

Candidate models:
- existing HistGradientBoosting pipeline
- XGBoost challenger if dependency/runtime cost is acceptable
- LightGBM challenger if dependency/runtime cost is acceptable
- Random Forest baseline
- Logistic/linear baseline where applicable

Outputs:
- Health: regression
- Risk: calibrated classification
- RUL: lower/median/upper regression where observed deterioration events support it

Promotion gates:
- grouped bridge-identity split or temporal holdout with no identity leakage
- final 2025 temporal holdout where feasible
- risk ROC-AUC target >= 0.97 if genuinely achieved
- acceptable calibration/Brier score
- health model must beat a simple persistence baseline

### Dam

Training sources:
- USACE National Inventory of Dams transfer data where target semantics are defensible
- India-WRIS/CWC/AP engineering and hydrology evidence for feature mapping and local context

Features may include:
- age, dam type, height, length, storage capacity, spillway capacity
- gate/spillway properties
- reservoir level/storage behavior
- rainfall, discharge, water-level anomalies, river velocity
- inspection/maintenance evidence where available
- evidence-quality indicators

Outputs:
- Health: transfer regression/classification only if defensible labels exist
- Risk: calibrated transfer classifier using legitimate safety/condition targets
- RUL: `ENGINEERING_RUL_BASELINE` until longitudinal labels are sufficient

The existing hydrologic rule engine remains a separate operational-risk feature and must not be renamed structural risk.

### Barrage

Use a barrage-specific feature builder rather than blindly reusing the dam feature map.

Features may include:
- age, total length, gate count and dimensions, scour sluices
- flow/discharge/velocity, water-level exposure, rainfall
- maintenance and inspection evidence
- material/structural type where available

Outputs:
- Health: transfer model if label quality is sufficient
- Risk: calibrated transfer classifier if label quality is sufficient
- RUL: `ENGINEERING_RUL_BASELINE` initially

### Airport

Model scope: pavement/engineering condition, not generic airport safety.

Features may include:
- runway age, length, width, surface type, pavement strength
- maintenance/rehabilitation history
- traffic/load where available
- rainfall/temperature exposure
- engineering evidence quality

Outputs:
- Health: pavement/engineering condition model if valid labels are found
- Risk: deterioration/maintenance-risk classifier if valid labels are found
- RUL: pavement/service-life baseline until longitudinal labels support ML

### Temple

No fake transfer from bridge or airport models.

Features may include:
- structure age, material, structural type
- gopuram/building dimensions
- maintenance/renovation history
- inspection/crack/damage observations
- rainfall/humidity/environmental exposure

Outputs:
- Health/Risk only when legitimate labeled structural-condition data can be sourced and mapped
- otherwise report verified engineering evidence plus `ENGINEERING_RUL_BASELINE`

## Unified Prediction Contract

All supported predictors return a common structure:

```json
{
  "asset_code": "...",
  "category": "BRIDGE|DAM|BARRAGE|AIRPORT|TEMPLE",
  "health_score": 0.0,
  "risk_score": 0.0,
  "risk_level": "LOW|MEDIUM|HIGH",
  "confidence": 0.0,
  "remaining_life_years": 0.0,
  "rul_method": "ML_PREDICTED|ENGINEERING_RUL_BASELINE",
  "model_name": "...",
  "model_version": "...",
  "feature_version": "...",
  "training_scope": "...",
  "validation_status": "RESEARCH_TRANSFER|VALIDATED_LOCAL|ENGINEERING_BASELINE",
  "prediction_time": "..."
}
```

Fields unsupported by evidence may be omitted rather than replaced with sentinel display values.

## New-Data Inference Flow

1. User/API adds or updates evidence for an asset.
2. SIMRAS validates schema and source quality.
3. Category-specific feature builder maps the row to the saved feature contract.
4. Saved preprocessing pipeline applies the exact training-time transformations.
5. Category model or approved engineering baseline returns the unified prediction contract.
6. Health/risk/RUL rows are persisted in `Prediction` history.
7. Digital Twin and Reports read the persisted prediction; they do not recalculate a conflicting value independently.

Retraining is required only when the training dataset/model is intentionally updated, not for every new inference row.

## Report Policy

Transfer predictions are visible when the model artifact is accepted for research-transfer use. Reports must show:

- Health Score
- Risk Score and Risk Level
- Confidence
- RUL and RUL method
- Model Name and Version
- Feature Version
- Training Scope
- Validation Status
- Local AP Validation: Yes/No
- Prediction Time

PDF/CSV/JSON and frontend cards must use the same persisted prediction payload.

Report language must distinguish:
- `RESEARCH_TRANSFER`
- `VALIDATED_LOCAL`
- `ENGINEERING_RUL_BASELINE`

Reports must not call transfer predictions government ground truth.

## RUL Baseline

For categories without sufficient longitudinal deterioration labels:

```text
age_years = current_year - built_year
baseline_rul = max(0, reference_service_life - age_years)
```

The reference service life must be explicit and category-specific. Any adjustment from verified condition/environment evidence must be documented and deterministic. This value is not to be presented as an ML forecast.

## Testing Strategy

- Unit tests for each feature builder and missing-data behavior.
- Unit tests for prediction contract and provenance fields.
- Bridge temporal/group leakage tests.
- Model promotion tests against baselines.
- API tests for each supported asset category.
- Report tests ensuring transfer predictions are shown with research-transfer labeling.
- Tests ensuring unsupported/missing values are omitted instead of fabricated.
- Docker/CI smoke test for model loading and one-row inference.

## Implementation Order

1. Bridge model evaluation/retraining and 2025 temporal holdout.
2. Unified predictor interface and persistence integration.
3. Report policy change for research-transfer predictions.
4. Dam feature/target audit and model/baseline implementation.
5. Barrage feature/target audit and model/baseline implementation.
6. Airport feature/target audit and model/baseline implementation.
7. Temple label audit; train only if defensible labels exist, otherwise evidence + baseline path.
8. Frontend/report integration and end-to-end verification.

## Success Criteria for Final Review

- Every bridge/dam/barrage can return a current prediction or an explicitly labeled engineering baseline according to evidence availability.
- New valid input rows can be passed through the saved pipeline without retraining.
- Bridge risk evaluation is reproducible and leakage-controlled; 0.97+ ROC-AUC is reported only if the final holdout actually achieves it.
- Dam/barrage operational hydrologic risk remains separate from structural Health/Risk.
- Airports and temples are routed through their own category logic and are never scored using the bridge model.
- Reports, PDF, CSV, JSON, and Digital Twin use the same persisted prediction records and display provenance clearly.
