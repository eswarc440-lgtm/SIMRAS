# SIMRAS Bridge Confidence, RUL, Traffic and Reports Design

Date: 2026-09-19
Branch: `simras-bridge-confidence-rul-reports`

## Goal

Make SIMRAS produce trustworthy selected-asset reports for every registered DAM, BARRAGE, BRIDGE, AIRPORT and TEMPLE while improving bridge prediction coverage, integrating traffic/load evidence, enabling RUL outputs, and allowing confidence above 90% only when evidence and model calibration justify it.

The design explicitly forbids hard-coding confidence, health, risk, or RUL values. A report must always be generated for the selected asset even when one or more AI fields remain withheld.

## Current problems

1. Bridge inference is fail-closed and the current AP transfer-validation artifact reports zero prediction-eligible bridge candidates because local AP engineering coverage is insufficient.
2. `traffic_load_ratio` exists in the feature definitions and risk engine, but the runtime prediction input currently does not consistently pass traffic/flood inputs from trusted evidence.
3. The Digital Twin path can calculate an experimental RUL proxy, but persisted prediction rows and the refresh API still write/return RUL as disabled/null.
4. Confidence is currently capped when structural evidence is missing. Raising the UI number would be misleading; confidence must increase through better evidence completeness and model calibration.
5. Reports and Digital Twin can consume different assessment paths, which can produce inconsistent output such as RUL visible in one location but withheld in another.
6. Not every registered asset currently has a complete selected-asset report containing evidence provenance and model-use status.

## Design principles

- No fabricated government evidence.
- No hard-coded 90% confidence.
- Confidence is a calibrated quality statement, not a cosmetic score.
- Government evidence remains visible even when not used by a model.
- Every report explicitly labels each field as `USED_BY_MODEL`, `CONTEXT_ONLY`, `NOT_USED`, or `WITHHELD`.
- Unsupported structural predictions remain withheld rather than inferred from identity/location alone.
- Digital Twin, report UI, PDF, CSV and JSON consume the same backend assessment object.
- RUL distinguishes validated ML RUL from experimental planning-life proxy RUL.

## Architecture

### 1. Unified assessment service

Introduce a single selected-asset assessment service in the backend. It will assemble:

- asset identity and metadata;
- trusted government/authoritative evidence;
- latest inspection and maintenance records;
- environmental/hydrology evidence;
- traffic/load evidence;
- feature-usage manifest;
- health/risk prediction;
- confidence decomposition;
- RUL prediction or proxy;
- recommendations;
- evidence provenance.

Both Digital Twin and Reports must call this service. Existing `build_twin()` and refresh/report code should delegate to it instead of independently rebuilding prediction logic.

### 2. Bridge API coverage

Use the existing AP bridge registry as the source of candidate bridges, but expose named bridges only when identity and coordinates are sufficiently resolved. Do not create fake duplicate bridge assets.

For each bridge, keep an eligibility state such as:

- `IDENTITY_VERIFIED`
- `EVIDENCE_PARTIAL`
- `MODEL_READY`
- `MODEL_WITHHELD`

The API should return the bridge even if prediction is withheld, so every selected bridge can still generate a report.

### 3. Bridge feature contract

Bridge feature construction will map verified local evidence into the NBI-compatible feature set where defensible:

- age_years
- condition_rating / inspection_score
- material_code
- design_type_code
- average_daily_traffic
- truck_traffic_percent
- skew_deg
- span_count
- max_span_m
- structure_length_m
- inventory/load rating
- scour rating
- waterway rating
- rainfall/flood exposure
- source confidence
- missing feature ratio

A mapping record must carry source, retrieval/observation date, verification status and model-use status.

### 4. Traffic/load evidence

Traffic/load is asset-specific:

- BRIDGE: AADT, truck percentage, axle/load or inventory-rating evidence when available.
- BARRAGE carrying road traffic: AADT/load evidence where applicable.
- DAM: road traffic is context only unless structurally relevant; hydrological loading is primary.
- AIRPORT: aircraft movements, pavement/load classification, runway cycles.
- TEMPLE: visitor/footfall evidence only when authoritative and relevant.

The prediction runtime must pass verified traffic/load features into the model input. If no authoritative traffic value exists, the field is `WITHHELD`; it must not be replaced with a guessed category such as HIGH/MEDIUM/LOW.

### 5. Confidence model

Replace a single opaque confidence calculation with a decomposed assessment:

- `evidence_completeness`
- `source_quality`
- `domain_compatibility`
- `model_calibration_quality`
- `structural_evidence_quality`
- `final_confidence`

Final confidence must be calibrated against held-out/local validation results. A result may exceed 0.90 only if the required evidence gate passes and the applicable model has sufficient local validation/calibration support.

For assets without structural evidence, confidence remains capped and the structural health/risk result may remain withheld. There is no forced minimum confidence.

### 6. Bridge model adaptation

Retain the existing NBI model artifacts as the transfer-learning/research base. Build an AP compatibility layer rather than retraining blindly.

The pipeline will:

1. assemble AP bridge feature rows;
2. calculate coverage for required features;
3. exclude rows that require fabricated values;
4. validate against any available AP inspection/condition labels;
5. calibrate probability outputs where enough local labels exist;
6. promote only if validation gates pass;
7. otherwise expose research-transfer output only with an explicit status and appropriate confidence ceiling.

A strong NBI held-out metric does not count as AP-local accuracy.

### 7. RUL design

RUL has two allowed modes:

#### A. Validated ML RUL

For eligible bridges, use the existing lower/median/upper RUL artifacts when a complete compatible feature vector exists and governance permits the model. Persist:

- remaining_life_years
- rul_lower_bound
- rul_upper_bound
- rul_confidence
- rul_method=`ML`
- model version
- feature version

#### B. Evidence-derived planning-life proxy

For DAM/BARRAGE/AIRPORT/TEMPLE and bridges that cannot run ML RUL, the existing planning-life proxy may be shown only as `EXPERIMENTAL_PROXY`, together with basis, source URL, uncertainty interval and proxy confidence.

The report must never present proxy RUL as official remaining structural life.

If neither mode has enough inputs, RUL is withheld with an explicit reason code.

### 8. Persistence

Update prediction persistence so the RUL row is not always written as disabled. The persisted row must match the exact RUL object returned by the assessment service.

Persist enough metadata to reproduce the assessment:

- model version
- feature version
- prediction timestamp
- confidence
- lower/upper bounds
- status
- factors/reason codes
- feature-usage manifest reference or snapshot

### 9. Reports

Every selected asset gets a report even when prediction values are withheld.

The report contains:

1. Asset identity
2. Infrastructure specifications/dimensions
3. Health score
4. Risk score and risk level
5. Confidence and confidence components
6. RUL / RUL interval / RUL status
7. Government/authoritative evidence table
8. Traffic or operational-load evidence where relevant
9. Feature usage table
10. Environmental/hydrology evidence
11. Inspection and maintenance evidence
12. Prediction factors and recommendations
13. Model/version/status
14. Limitations and withholding reasons
15. Source references and evidence dates

PDF, CSV and JSON exports must use the same assessment payload.

### 10. Feature usage contract

Each reportable evidence field has:

```text
name
value
unit
source_name
source_url
evidence_date
verification_status
model_usage
feature_name
reason_if_not_used
```

`model_usage` is one of:

- `USED_BY_MODEL`
- `CONTEXT_ONLY`
- `NOT_USED`
- `WITHHELD`

This removes ambiguous labels such as simply “Not used by model” without explaining why.

## Data flow

1. User selects an asset.
2. Backend resolves canonical asset identity.
3. Evidence service loads verified government/authoritative records.
4. Asset-type feature builder creates a typed feature vector.
5. Feature gate computes completeness and eligibility.
6. Applicable model or transparent fallback runs.
7. Confidence service calculates decomposed confidence.
8. RUL service returns ML RUL, experimental proxy, or withheld status.
9. Unified assessment object is persisted.
10. Digital Twin and Reports render the same assessment object.
11. PDF/CSV/JSON export serializes the same object.

## Error and withholding behavior

The API should not fail merely because predictions are unavailable. It returns a valid assessment payload with explicit field statuses.

Examples:

- `MODEL_NOT_AP_LOCALLY_VALIDATED`
- `INSUFFICIENT_STRUCTURAL_EVIDENCE`
- `INSUFFICIENT_TRAFFIC_EVIDENCE`
- `INSUFFICIENT_RUL_FEATURES`
- `RUL_PROXY_ONLY`
- `MODEL_READY`

No endpoint should silently substitute guessed values for missing engineering evidence.

## Tests

### Backend unit tests

- traffic evidence reaches `RiskInput` when verified;
- absent traffic remains null/withheld;
- confidence cannot exceed configured eligibility ceiling when structural evidence is missing;
- confidence may exceed 0.90 only when the calibrated gate passes;
- RUL persistence stores value and interval when available;
- RUL proxy is clearly labelled experimental;
- report assessment and twin assessment are identical for common prediction fields.

### Integration tests

For representative assets in each class:

- asset appears in API;
- selected-asset assessment returns 200;
- report returns even if prediction is withheld;
- PDF/CSV/JSON payloads contain the same asset code and assessment timestamp/version;
- government evidence table contains source/verification fields;
- feature usage is explicit;
- RUL status is consistent across Twin and Report.

### Bridge acceptance tests

- multiple named AP bridges are visible in the API;
- no duplicate canonical bridge is created;
- every visible bridge has a report;
- model eligibility is evidence-driven;
- traffic is consumed when available;
- 90%+ confidence is never achieved solely by changing a constant;
- RUL is displayed only from ML or clearly labelled proxy logic.

## Implementation sequence

1. Add unified assessment schema/service.
2. Wire traffic/flood inputs into runtime feature construction.
3. Add feature-usage manifest and confidence decomposition.
4. Repair RUL persistence and response contract.
5. Route Digital Twin through unified assessment.
6. Route Reports and exports through unified assessment.
7. Expand named bridge API coverage without fabricating evidence.
8. Build AP bridge compatibility/validation pipeline.
9. Add local calibration/promotion gate.
10. Run all acceptance tests and audit every registered asset report.

## Definition of done

- Every registered asset can open a selected-asset report.
- Every report exposes evidence provenance and feature-usage status.
- Traffic/operational load is used for the appropriate asset classes when verified.
- Multiple bridges are available in the API.
- Bridge prediction eligibility is no longer limited by a UI-only special case.
- RUL is consistent between database, API, Digital Twin and Reports.
- Confidence above 90% appears only for qualifying, calibrated assessments.
- No fake prediction, confidence, RUL, traffic or government evidence is introduced.
