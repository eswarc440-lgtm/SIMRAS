# SIMRAS Bridge Confidence, RUL and Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every registered SIMRAS asset produce a selected-asset report from one trustworthy assessment payload, wire verified traffic/load evidence into predictions, persist RUL consistently, expand named bridge coverage, and permit confidence above 90% only when evidence completeness and calibrated model validation justify it.

**Architecture:** Introduce a backend assessment contract that owns feature provenance, confidence decomposition, health/risk, RUL, and evidence status. Digital Twin and Reports consume the same assessment object. Bridge import/eligibility and AP-local calibration are separate services so adding more bridges never bypasses model-governance rules.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy asyncio, PostgreSQL/PostGIS, Pydantic, scikit-learn/joblib, React 19, TypeScript, Vite, pytest, pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-09-19-bridge-confidence-rul-reports-design.md`

## Global Constraints

- Do not fabricate government evidence, traffic values, inspection values, confidence, health, risk, or RUL.
- Do not hard-code a 90% minimum confidence. `final_confidence >= 0.90` is allowed only when an evidence/model eligibility gate passes.
- Every selected asset must return a report payload even when one or more AI values are withheld.
- Digital Twin, report UI, JSON, CSV, and PDF must use the same assessment payload and assessment timestamp.
- Every reportable field must use one of `USED_BY_MODEL`, `CONTEXT_ONLY`, `NOT_USED`, or `WITHHELD`.
- RUL from a planning-life proxy must be labelled `EXPERIMENTAL_PROXY`; it must never be presented as official structural remaining life.
- Existing bridge NBI metrics are transfer-model metrics, not Andhra Pradesh local accuracy.
- Bridge identities may appear in the API before model eligibility, but model predictions remain fail-closed when governance requirements are not met.

---

## File Structure

Create focused files rather than adding more responsibilities to `twin_service.py`:

- `backend/app/schemas/assessment.py` — Pydantic contract for feature use, confidence, RUL and selected-asset assessment.
- `backend/app/services/feature_usage_service.py` — source-aware feature extraction and usage manifest.
- `backend/app/services/confidence_service.py` — confidence component calculation and 0.90+ eligibility rule.
- `backend/app/services/assessment_service.py` — single orchestration path for selected-asset assessment.
- `backend/app/services/report_service.py` — JSON/CSV/PDF serialization from `AssetAssessment` only.
- `backend/app/services/bridge_catalog_service.py` — promote named bridge map features into canonical `assets` without inventing engineering values.
- `backend/app/api/routes/reports.py` — selected-asset report/export API.
- `backend/scripts/promote_named_bridges.py` — controlled named-bridge promotion CLI.
- `backend/tests/test_feature_usage_service.py`
- `backend/tests/test_confidence_service.py`
- `backend/tests/test_assessment_service.py`
- `backend/tests/test_report_service.py`
- `backend/tests/test_bridge_catalog_service.py`
- `frontend/src/types/assessment.ts`
- `frontend/src/features/reports/SelectedAssetReport.tsx`

Modify:

- `backend/app/services/twin_service.py` — delegate prediction assembly to assessment service and persist actual RUL.
- `backend/app/services/risk_engine.py` — consume verified traffic/flood features but keep confidence truthful.
- `backend/app/api/router.py` — register report routes.
- `backend/app/api/routes/assets.py` — optional report-link metadata and bridge filtering remain canonical.
- `backend/app/schemas/twin.py` — remove duplicate RUL fields and map AI fields from assessment contract.
- `backend/pyproject.toml` — add a PDF library only when Task 5 lands.
- `frontend/src/services/api.ts` — report fetch/export methods.
- `frontend/src/App.tsx` — add Reports view without changing existing Digital Twin behavior.

---

### Task 1: Assessment, Feature-Usage, Confidence and RUL Schemas

**Files:**
- Create: `backend/app/schemas/assessment.py`
- Modify: `backend/app/schemas/twin.py`
- Test: `backend/tests/test_assessment_schema.py`

**Interfaces:**
- Produces: `ModelUsage`, `FeatureEvidence`, `ConfidenceBreakdown`, `RULAssessment`, `PredictionAssessment`, `AssetAssessment`.
- Later tasks consume these types directly; do not redefine equivalent dict shapes elsewhere.

- [ ] **Step 1: Write the failing schema test**

```python
from datetime import UTC, datetime

from app.schemas.assessment import AssetAssessment, FeatureEvidence


def test_feature_usage_is_explicit_and_assessment_serializes() -> None:
    feature = FeatureEvidence(
        name="Average Daily Traffic",
        feature_name="average_daily_traffic",
        value=32000,
        unit="vehicles/day",
        source_name="Test authoritative source",
        source_url="https://example.gov/traffic",
        evidence_date=None,
        verification_status="VERIFIED",
        model_usage="USED_BY_MODEL",
        reason_if_not_used=None,
    )
    payload = AssetAssessment(
        assessment_id="SIMRAS-AP_BR_00002-20260919T000000Z",
        asset_code="AP_BR_00002",
        asset_name="Kanaka Durga Flyover",
        asset_type="bridge",
        district="NTR",
        generated_at=datetime(2026, 9, 19, tzinfo=UTC),
        status="ACTIVE",
        feature_evidence=[feature],
    )
    assert payload.feature_evidence[0].model_usage == "USED_BY_MODEL"
    assert payload.model_dump(mode="json")["asset_code"] == "AP_BR_00002"
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
cd backend
pytest tests/test_assessment_schema.py -v
```

Expected: import failure because `app.schemas.assessment` does not yet exist.

- [ ] **Step 3: Implement the schema contract**

Create `backend/app/schemas/assessment.py` with these exact core types:

```python
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ModelUsage = Literal["USED_BY_MODEL", "CONTEXT_ONLY", "NOT_USED", "WITHHELD"]


class FeatureEvidence(BaseModel):
    name: str
    feature_name: str
    value: float | int | str | None = None
    unit: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    evidence_date: date | datetime | None = None
    verification_status: str
    model_usage: ModelUsage
    reason_if_not_used: str | None = None


class ConfidenceBreakdown(BaseModel):
    evidence_completeness: float = Field(ge=0, le=1)
    source_quality: float = Field(ge=0, le=1)
    domain_compatibility: float = Field(ge=0, le=1)
    model_calibration_quality: float = Field(ge=0, le=1)
    structural_evidence_quality: float = Field(ge=0, le=1)
    final_confidence: float = Field(ge=0, le=1)
    eligible_for_high_confidence: bool = False
    reason_codes: list[str] = Field(default_factory=list)


class RULAssessment(BaseModel):
    value_years: float | None = None
    lower_bound_years: float | None = None
    upper_bound_years: float | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    status: str = "WITHHELD"
    method: str = "UNAVAILABLE"
    basis: str | None = None
    basis_url: str | None = None
    model_version: str | None = None
    feature_version: str | None = None


class PredictionAssessment(BaseModel):
    health_score: float | None = Field(default=None, ge=0, le=100)
    risk_score: float | None = Field(default=None, ge=0, le=100)
    risk_level: str | None = None
    hazard_score: float | None = Field(default=None, ge=0, le=100)
    hazard_level: str | None = None
    confidence: ConfidenceBreakdown | None = None
    rul: RULAssessment = Field(default_factory=RULAssessment)
    status: str = "WITHHELD"
    prediction_method: str = "UNAVAILABLE"
    model_version: str | None = None
    feature_version: str | None = None
    factors: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class AssetAssessment(BaseModel):
    assessment_id: str
    asset_code: str
    asset_name: str
    asset_type: str
    district: str | None = None
    generated_at: datetime
    status: str
    static: dict[str, Any] = Field(default_factory=dict)
    dimensions: dict[str, Any] = Field(default_factory=dict)
    government_evidence: list[FeatureEvidence] = Field(default_factory=list)
    feature_evidence: list[FeatureEvidence] = Field(default_factory=list)
    environment: dict[str, Any] = Field(default_factory=dict)
    inspection: dict[str, Any] = Field(default_factory=dict)
    maintenance: list[dict[str, Any]] = Field(default_factory=list)
    prediction: PredictionAssessment = Field(default_factory=PredictionAssessment)
    limitations: list[str] = Field(default_factory=list)
```

In `backend/app/schemas/twin.py`, remove the duplicate `rul_lower_bound` and `rul_upper_bound` declarations from `PredictionState`; keep one declaration of each.

- [ ] **Step 4: Run schema tests**

```bash
cd backend
pytest tests/test_assessment_schema.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/assessment.py backend/app/schemas/twin.py backend/tests/test_assessment_schema.py
git commit -m "feat: add unified asset assessment schema"
```

---

### Task 2: Wire Verified Traffic/Flood Features and Produce a Feature-Usage Manifest

**Files:**
- Create: `backend/app/services/feature_usage_service.py`
- Modify: `backend/app/services/twin_service.py`
- Modify: `backend/app/services/risk_engine.py`
- Test: `backend/tests/test_feature_usage_service.py`
- Test: `backend/tests/test_risk_engine.py`

**Interfaces:**
- Produces: `build_feature_evidence(asset, environment, inspection, maintenance) -> list[FeatureEvidence]`.
- Produces: `feature_value(items, feature_name) -> float | None` only for `USED_BY_MODEL` features.
- `twin_service._prediction_input()` consumes those values for `flood_exposure` and `traffic_load_ratio`.

- [ ] **Step 1: Write failing feature-usage tests**

```python
from app.services.feature_usage_service import feature_value
from app.schemas.assessment import FeatureEvidence


def test_feature_value_returns_only_verified_model_input() -> None:
    rows = [
        FeatureEvidence(
            name="Traffic load ratio",
            feature_name="traffic_load_ratio",
            value=0.82,
            unit="ratio",
            source_name="Authority",
            source_url=None,
            verification_status="VERIFIED",
            model_usage="USED_BY_MODEL",
        )
    ]
    assert feature_value(rows, "traffic_load_ratio") == 0.82


def test_withheld_traffic_is_not_returned_to_model() -> None:
    rows = [
        FeatureEvidence(
            name="Traffic load ratio",
            feature_name="traffic_load_ratio",
            value=None,
            unit="ratio",
            source_name=None,
            source_url=None,
            verification_status="NO_VERIFIED_DATA",
            model_usage="WITHHELD",
            reason_if_not_used="No verified traffic evidence",
        )
    ]
    assert feature_value(rows, "traffic_load_ratio") is None
```

- [ ] **Step 2: Run tests and verify failure**

```bash
cd backend
pytest tests/test_feature_usage_service.py -v
```

Expected: import failure for the new service.

- [ ] **Step 3: Implement explicit usage filtering**

```python
from app.schemas.assessment import FeatureEvidence


def feature_value(items: list[FeatureEvidence], feature_name: str) -> float | None:
    for item in items:
        if item.feature_name != feature_name or item.model_usage != "USED_BY_MODEL":
            continue
        if isinstance(item.value, (int, float)):
            return float(item.value)
    return None
```

`build_feature_evidence()` must create rows from trusted runtime fields. Use these environment variable mappings initially:

```python
ENV_FEATURES = {
    "rainfall_24h": ("Rainfall 24h", "rainfall_mm_24h"),
    "rainfall_7d": ("Rainfall 7d", "rainfall_mm_7d"),
    "water_level_anomaly": ("Water level anomaly", "water_level_anomaly_m"),
    "flood_exposure": ("Flood exposure", "flood_exposure"),
    "traffic_load_ratio": ("Traffic load ratio", "traffic_load_ratio"),
}
```

Only mark a row `USED_BY_MODEL` when the source value already passed the project's trusted-environment filtering and has a usable numeric value. Otherwise emit a `WITHHELD` row with a reason.

- [ ] **Step 4: Wire values into `_prediction_input()`**

Change the current `RiskInput(...)` construction so these two currently omitted fields are present:

```python
        flood_exposure=_environment_value(environment, "flood_exposure"),
        traffic_load_ratio=_environment_value(environment, "traffic_load_ratio"),
```

Do not insert fallback numbers.

- [ ] **Step 5: Add a regression test showing traffic changes risk only when supplied**

Append to `backend/tests/test_risk_engine.py`:

```python
def test_verified_traffic_load_can_increase_hazard() -> None:
    base = RiskInput(
        built_year=2010,
        design_life_years=100,
        condition="GOOD",
        inspection_score=90,
        source_confidence=0.95,
    )
    without_traffic = score_risk(base, current_year=2026, allow_estimated_health=True)
    with_traffic = score_risk(
        RiskInput(**{**base.__dict__, "traffic_load_ratio": 1.2}),
        current_year=2026,
        allow_estimated_health=True,
    )
    assert with_traffic.hazard_score > (without_traffic.hazard_score or 0)
```

If `slots=True` prevents `__dict__`, construct the second `RiskInput` explicitly with the same fields and `traffic_load_ratio=1.2`.

- [ ] **Step 6: Run targeted tests**

```bash
cd backend
pytest tests/test_feature_usage_service.py tests/test_risk_engine.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/feature_usage_service.py backend/app/services/twin_service.py backend/app/services/risk_engine.py backend/tests/test_feature_usage_service.py backend/tests/test_risk_engine.py
git commit -m "feat: wire verified traffic and flood evidence into predictions"
```

---

### Task 3: Confidence Decomposition and Honest 90%+ Eligibility

**Files:**
- Create: `backend/app/services/confidence_service.py`
- Test: `backend/tests/test_confidence_service.py`

**Interfaces:**
- Produces: `calculate_confidence(...) -> ConfidenceBreakdown`.
- Assessment service will pass evidence completeness, source quality, domain compatibility, calibration quality, and structural evidence quality.

- [ ] **Step 1: Write failing confidence tests**

```python
from app.services.confidence_service import calculate_confidence


def test_missing_structural_evidence_cannot_reach_90_percent() -> None:
    result = calculate_confidence(
        evidence_completeness=1.0,
        source_quality=1.0,
        domain_compatibility=1.0,
        model_calibration_quality=1.0,
        structural_evidence_quality=0.0,
        locally_validated=True,
    )
    assert result.final_confidence < 0.90
    assert result.eligible_for_high_confidence is False


def test_complete_locally_validated_assessment_may_exceed_90_percent() -> None:
    result = calculate_confidence(
        evidence_completeness=0.98,
        source_quality=0.98,
        domain_compatibility=0.96,
        model_calibration_quality=0.97,
        structural_evidence_quality=0.98,
        locally_validated=True,
    )
    assert result.final_confidence >= 0.90
    assert result.eligible_for_high_confidence is True


def test_transfer_model_without_local_validation_is_capped() -> None:
    result = calculate_confidence(
        evidence_completeness=1.0,
        source_quality=1.0,
        domain_compatibility=0.75,
        model_calibration_quality=0.95,
        structural_evidence_quality=1.0,
        locally_validated=False,
    )
    assert result.final_confidence <= 0.80
```

- [ ] **Step 2: Verify failure**

```bash
cd backend
pytest tests/test_confidence_service.py -v
```

- [ ] **Step 3: Implement deterministic confidence decomposition**

```python
from app.schemas.assessment import ConfidenceBreakdown


def _unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def calculate_confidence(
    *,
    evidence_completeness: float,
    source_quality: float,
    domain_compatibility: float,
    model_calibration_quality: float,
    structural_evidence_quality: float,
    locally_validated: bool,
) -> ConfidenceBreakdown:
    parts = {
        "evidence_completeness": _unit(evidence_completeness),
        "source_quality": _unit(source_quality),
        "domain_compatibility": _unit(domain_compatibility),
        "model_calibration_quality": _unit(model_calibration_quality),
        "structural_evidence_quality": _unit(structural_evidence_quality),
    }
    raw = (
        parts["evidence_completeness"] * 0.25
        + parts["source_quality"] * 0.20
        + parts["domain_compatibility"] * 0.20
        + parts["model_calibration_quality"] * 0.20
        + parts["structural_evidence_quality"] * 0.15
    )
    reason_codes: list[str] = []
    if parts["structural_evidence_quality"] < 0.80:
        raw = min(raw, 0.75)
        reason_codes.append("STRUCTURAL_EVIDENCE_INCOMPLETE")
    if not locally_validated:
        raw = min(raw, 0.80)
        reason_codes.append("MODEL_NOT_LOCALLY_VALIDATED")
    eligible = (
        locally_validated
        and parts["evidence_completeness"] >= 0.90
        and parts["source_quality"] >= 0.90
        and parts["domain_compatibility"] >= 0.90
        and parts["model_calibration_quality"] >= 0.90
        and parts["structural_evidence_quality"] >= 0.90
    )
    if not eligible:
        raw = min(raw, 0.899)
    return ConfidenceBreakdown(
        **parts,
        final_confidence=round(raw, 3),
        eligible_for_high_confidence=eligible,
        reason_codes=reason_codes,
    )
```

This is a quality aggregation rule, not a claim that the model is 90% accurate. Local calibration metrics must feed `model_calibration_quality` in Task 7.

- [ ] **Step 4: Run tests**

```bash
cd backend
pytest tests/test_confidence_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/confidence_service.py backend/tests/test_confidence_service.py
git commit -m "feat: add evidence-calibrated confidence breakdown"
```

---

### Task 4: Repair RUL Persistence and Make API/Database/Twin Consistent

**Files:**
- Modify: `backend/app/services/twin_service.py`
- Test: `backend/tests/test_rul_persistence.py`

**Interfaces:**
- `persist_ml_prediction(..., rul: RULAssessment)` persists the same RUL shown to clients.
- The `rul` prediction row uses `value`, `lower_bound`, `upper_bound`, `confidence_score`, and `predicted_class` from the RUL assessment.

- [ ] **Step 1: Write the failing persistence-construction test**

Extract row construction into a pure helper so it can be unit-tested without PostgreSQL:

```python
from app.schemas.assessment import RULAssessment
from app.services.twin_service import build_prediction_rows


def test_rul_row_matches_assessment() -> None:
    rul = RULAssessment(
        value_years=18.4,
        lower_bound_years=12.0,
        upper_bound_years=24.8,
        confidence=0.72,
        status="EXPERIMENTAL_PROXY",
        method="AGE_HEALTH_HAZARD",
    )
    rows = build_prediction_rows(
        asset_id=2,
        health_score=84.0,
        risk_score=21.0,
        risk_level="LOW",
        confidence=0.72,
        model_version="simras_multifactor_health_v1",
        feature_version="ap_asset_state_v2",
        status="SIMRAS_PREDICTION",
        factors=[],
        rul=rul,
    )
    rul_row = next(row for row in rows if row.target == "rul")
    assert rul_row.value == 18.4
    assert rul_row.lower_bound == 12.0
    assert rul_row.upper_bound == 24.8
    assert rul_row.predicted_class == "EXPERIMENTAL_PROXY"
```

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
pytest tests/test_rul_persistence.py -v
```

- [ ] **Step 3: Refactor persistence**

Replace the existing hard-coded RUL row:

```python
Prediction(
    **common,
    target="rul",
    value=None,
    predicted_class="DISABLED",
    lower_bound=None,
    upper_bound=None,
)
```

with construction from `RULAssessment`:

```python
Prediction(
    **common,
    target="rul",
    value=rul.value_years,
    predicted_class=rul.status,
    lower_bound=rul.lower_bound_years,
    upper_bound=rul.upper_bound_years,
    confidence_score=rul.confidence,
)
```

Because `common` currently contains `confidence_score`, do not pass the key twice. Build the RUL row with an RUL-specific dict or exclude `confidence_score` from `common` for that row.

- [ ] **Step 4: Compute RUL before persistence**

Move the existing `estimate_rul_proxy(...)` call so `refresh_ml_prediction()` computes the RUL object before `persist_ml_prediction()`. The returned API object must use exactly that object rather than returning `remaining_life_years=None`.

- [ ] **Step 5: Run RUL and risk tests**

```bash
cd backend
pytest tests/test_rul_persistence.py tests/test_risk_engine.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/twin_service.py backend/tests/test_rul_persistence.py
git commit -m "fix: persist and return calculated RUL consistently"
```

---

### Task 5: Unified Selected-Asset Assessment Service

**Files:**
- Create: `backend/app/services/assessment_service.py`
- Modify: `backend/app/services/twin_service.py`
- Test: `backend/tests/test_assessment_service.py`

**Interfaces:**
- Produces: `async build_asset_assessment(session, asset_code) -> AssetAssessment`.
- Digital Twin and Reports both call this function.

- [ ] **Step 1: Write a failing orchestration test with monkeypatched dependencies**

```python
import pytest

from app.services import assessment_service


@pytest.mark.asyncio
async def test_assessment_contains_one_prediction_contract(monkeypatch) -> None:
    async def fake_row(session, asset_code):
        return (type("Asset", (), {
            "id": 2,
            "asset_code": asset_code,
            "name": "Kanaka Durga Flyover",
            "asset_type": "bridge",
            "subtype": "flyover",
            "district": "NTR",
            "status": "ACTIVE",
            "owner": None,
            "built_year": 2016,
            "design_life_years": 100,
            "material": "concrete",
            "condition": "GOOD",
            "confidence_score": 0.95,
            "is_estimated": False,
        })(), 80.62, 16.51)

    monkeypatch.setattr(assessment_service, "get_asset_row", fake_row)
    result = await assessment_service.build_asset_assessment(object(), "AP_BR_00002")
    assert result.asset_code == "AP_BR_00002"
    assert result.prediction.rul.status
```

During implementation, inject or monkeypatch the remaining loaders so this test stays database-independent.

- [ ] **Step 2: Verify failure**

```bash
cd backend
pytest tests/test_assessment_service.py -v
```

- [ ] **Step 3: Implement `build_asset_assessment()`**

The service must perform this exact flow:

```python
async def build_asset_assessment(session: AsyncSession, asset_code: str) -> AssetAssessment:
    row = await get_asset_row(session, asset_code)
    asset, _, _ = row
    model = await _active_asset_model(session, asset.id)
    inspection = await _latest_inspection(session, asset.id)
    maintenance = await _latest_maintenance(session, asset.id)
    environment, _ = await _trusted_environment(session, asset.id)

    feature_evidence = build_feature_evidence(
        asset=asset,
        environment=environment,
        inspection=inspection,
        maintenance=maintenance,
    )

    risk_input = _prediction_input(
        asset=asset,
        inspection=inspection,
        latest_maintenance=maintenance,
        environment=environment,
    )
    prediction = score_risk(risk_input, allow_estimated_health=True)

    # Governance metadata determines local-validation status and confidence caps.
    locally_validated = False
    domain_compatibility = 0.80 if asset.asset_type != "bridge" else 0.60

    confidence = calculate_confidence(
        evidence_completeness=_model_feature_completeness(feature_evidence),
        source_quality=_source_quality(feature_evidence),
        domain_compatibility=domain_compatibility,
        model_calibration_quality=0.80 if asset.asset_type != "bridge" else 0.70,
        structural_evidence_quality=_structural_evidence_quality(inspection, asset),
        locally_validated=locally_validated,
    )

    rul = build_rul_assessment(...)
    return AssetAssessment(...)
```

The placeholder-looking `...` above is not an implementation instruction: define and call a concrete local helper `build_rul_assessment(asset, model, prediction, current_year)` in this same task. It wraps the existing `estimate_rul_proxy()` and returns a fully populated `RULAssessment` with `status="EXPERIMENTAL_PROXY"` when a proxy value exists, otherwise `WITHHELD`.

- [ ] **Step 4: Make `build_twin()` consume the assessment prediction**

`build_twin()` may continue returning the existing `TwinResponse`, but its `ai` section must be mapped from `assessment.prediction` rather than running a second independent scoring path.

- [ ] **Step 5: Run assessment, RUL and existing twin tests**

```bash
cd backend
pytest tests/test_assessment_service.py tests/test_rul_persistence.py tests/test_risk_engine.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/assessment_service.py backend/app/services/twin_service.py backend/tests/test_assessment_service.py
git commit -m "refactor: unify selected asset assessment pipeline"
```

---

### Task 6: Selected-Asset Reports and JSON/CSV/PDF Exports

**Files:**
- Create: `backend/app/services/report_service.py`
- Create: `backend/app/api/routes/reports.py`
- Modify: `backend/app/api/router.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/test_report_service.py`

**Interfaces:**
- `render_report_json(assessment) -> bytes`
- `render_report_csv(assessment) -> bytes`
- `render_report_pdf(assessment) -> bytes`
- Endpoints: `GET /reports/{asset_code}`, `/reports/{asset_code}.json`, `.csv`, `.pdf`.

- [ ] **Step 1: Add failing JSON/CSV serialization tests**

```python
from datetime import UTC, datetime

from app.schemas.assessment import AssetAssessment
from app.services.report_service import render_report_csv, render_report_json


def sample() -> AssetAssessment:
    return AssetAssessment(
        assessment_id="A1",
        asset_code="AP_BR_00002",
        asset_name="Kanaka Durga Flyover",
        asset_type="bridge",
        district="NTR",
        generated_at=datetime(2026, 9, 19, tzinfo=UTC),
        status="ACTIVE",
    )


def test_json_report_contains_selected_asset_only() -> None:
    data = render_report_json(sample()).decode()
    assert '"asset_code":"AP_BR_00002"' in data.replace(" ", "")


def test_csv_report_contains_asset_and_section_rows() -> None:
    data = render_report_csv(sample()).decode()
    assert "AP_BR_00002" in data
    assert "assessment" in data.lower()
```

- [ ] **Step 2: Verify failure**

```bash
cd backend
pytest tests/test_report_service.py -v
```

- [ ] **Step 3: Implement JSON/CSV from `AssetAssessment` only**

Use standard `json` and `csv` modules. CSV is a long-form table with columns:

```text
section,name,value,unit,source_name,verification_status,model_usage,reason
```

Include identity/prediction rows first, then every `FeatureEvidence` row. Never query the database from `report_service.py`.

- [ ] **Step 4: Add PDF dependency and renderer**

Add to `backend/pyproject.toml`:

```toml
"reportlab>=4.2,<5",
```

Create a ReportLab PDF with title, asset identity, Health/Risk/Confidence/RUL summary, evidence table, feature-usage table, and limitations. It must render `WITHHELD` literally when a value is absent.

- [ ] **Step 5: Add FastAPI routes**

```python
from fastapi import APIRouter, Depends, Response

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/{asset_code}")
async def get_report(asset_code: str, session=Depends(get_db)):
    return await build_asset_assessment(session, asset_code)
```

For `.json`, `.csv`, and `.pdf`, call `build_asset_assessment()` exactly once and return the corresponding bytes with correct content type and `Content-Disposition` filename containing only the selected asset code.

- [ ] **Step 6: Register `reports.router`**

Update `backend/app/api/router.py` to import and include the reports router.

- [ ] **Step 7: Run report tests and backend test suite**

```bash
cd backend
pytest tests/test_report_service.py -v
pytest -q
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/report_service.py backend/app/api/routes/reports.py backend/app/api/router.py backend/pyproject.toml backend/tests/test_report_service.py
git commit -m "feat: add selected asset report exports"
```

---

### Task 7: Promote More Named Bridges Into the Canonical Asset API Without Fabricating Engineering Data

**Files:**
- Create: `backend/app/services/bridge_catalog_service.py`
- Create: `backend/scripts/promote_named_bridges.py`
- Test: `backend/tests/test_bridge_catalog_service.py`

**Interfaces:**
- `async promote_named_bridge_features(session, limit: int) -> PromotionSummary`.
- Reads `map_features` where `feature_type='bridge'` and `name IS NOT NULL`.
- Creates `Asset` and `AssetIdentifier` rows only when a matching external identifier is not already linked.

- [ ] **Step 1: Write failing normalization/deduplication tests**

Keep SQL/database writes thin by first testing pure code-generation helpers:

```python
from app.services.bridge_catalog_service import bridge_asset_code, is_promotable_bridge


def test_bridge_asset_code_is_stable() -> None:
    assert bridge_asset_code("OSM", "way/12345") == bridge_asset_code("OSM", "way/12345")
    assert bridge_asset_code("OSM", "way/12345").startswith("AP_BR_")


def test_unnamed_feature_is_not_promotable() -> None:
    assert is_promotable_bridge(name=None, identity_status="SOURCE_REPORTED") is False


def test_named_source_reported_bridge_can_be_catalogued_but_not_verified() -> None:
    assert is_promotable_bridge(name="Example Bridge", identity_status="SOURCE_REPORTED") is True
```

- [ ] **Step 2: Verify failure**

```bash
cd backend
pytest tests/test_bridge_catalog_service.py -v
```

- [ ] **Step 3: Implement stable codes and promotion rules**

```python
import hashlib


def bridge_asset_code(source_code: str, external_id: str) -> str:
    digest = hashlib.sha1(f"{source_code}:{external_id}".encode()).hexdigest()[:10].upper()
    return f"AP_BR_{digest}"


def is_promotable_bridge(*, name: str | None, identity_status: str | None) -> bool:
    return bool(name and name.strip()) and str(identity_status or "").upper() not in {"REJECTED", "INVALID"}
```

Promotion rules:

- use `ST_PointOnSurface(mf.geometry)` for `representative_geometry`;
- preserve the original `data_sources.id` as `Asset.source_id`;
- copy name/subtype;
- set `asset_type="bridge"`;
- preserve source identity status; do not change `SOURCE_REPORTED` to `VERIFIED`;
- set `built_year`, `design_life_years`, `material`, and `condition` to `None` unless they already exist in a verified authoritative source mapping;
- create `AssetIdentifier(source_id, external_id, external_name, match_method="SOURCE_PROMOTION", match_confidence=mf.confidence_score)`;
- deduplicate via existing `AssetIdentifier(source_id, external_id)` unique constraint.

- [ ] **Step 4: Add a CLI script**

`backend/scripts/promote_named_bridges.py` must accept `--limit` and `--dry-run`. Dry-run prints candidate count and sample names and performs no commit.

- [ ] **Step 5: Run unit tests**

```bash
cd backend
pytest tests/test_bridge_catalog_service.py -v
```

- [ ] **Step 6: Run promotion in dry-run mode against the project database**

```bash
python -m scripts.promote_named_bridges --dry-run --limit 25
```

Expected: named bridge candidates are listed; no database mutation occurs.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/bridge_catalog_service.py backend/scripts/promote_named_bridges.py backend/tests/test_bridge_catalog_service.py
git commit -m "feat: promote named bridge map features into asset catalog"
```

---

### Task 8: AP Bridge Compatibility, Eligibility and Confidence Calibration Gate

**Files:**
- Create: `backend/app/services/bridge_feature_service.py`
- Modify: `backend/app/services/model_governance.py`
- Modify: `ml/simras_ml/ap_validation.py`
- Test: `backend/tests/test_prediction_readiness.py`
- Test: `ml/tests/test_ap_validation.py`

**Interfaces:**
- `build_bridge_feature_vector(...) -> BridgeFeatureVector` with nullable fields and coverage ratio.
- `bridge_prediction_gate()` consumes local coverage/validation output and returns `allowed`, `reason_code`, model metadata, and calibration quality.

- [ ] **Step 1: Add failing eligibility tests**

```python
def test_bridge_with_insufficient_core_features_is_withheld():
    vector = build_bridge_feature_vector(
        age_years=10,
        condition_rating=None,
        average_daily_traffic=None,
        truck_traffic_percent=None,
        span_count=None,
        structure_length_m=None,
    )
    assert vector.coverage < 0.90
    assert vector.model_ready is False


def test_bridge_ready_requires_no_fabricated_core_values():
    vector = build_bridge_feature_vector(
        age_years=10,
        condition_rating=8,
        average_daily_traffic=30000,
        truck_traffic_percent=12,
        span_count=18,
        structure_length_m=1800,
        values_verified=True,
    )
    assert vector.model_ready is True
```

Define `BridgeFeatureVector` in this task with the complete NBI-compatible feature names already present in `artifacts/bridge_nbi/manifest.json`.

- [ ] **Step 2: Verify failure**

```bash
cd backend
pytest tests/test_prediction_readiness.py -v
cd ../ml
pytest tests/test_ap_validation.py -v
```

- [ ] **Step 3: Implement feature coverage without imputation for eligibility**

Compute coverage as present required features divided by required features. It is acceptable for the underlying sklearn pipeline to have model-specific preprocessing, but governance eligibility must not count imputed/guessed values as source evidence.

- [ ] **Step 4: Extend AP validation output**

`ml/simras_ml/ap_validation.py` must emit, at minimum:

```json
{
  "prediction_eligible": 0,
  "average_feature_coverage": 0.0,
  "local_engineering_validation": false,
  "calibration_quality": 0.0,
  "promotion_allowed": false
}
```

When local labelled AP rows are available, calculate calibration quality from held-out local data. If no sufficient local labelled set exists, leave `local_engineering_validation=false`, `promotion_allowed=false`, and do not manufacture a calibration score.

- [ ] **Step 5: Make governance return calibration quality**

Add `calibration_quality` to `governance` returned by `bridge_prediction_gate()`. The confidence service in Task 3 consumes this value. A bridge transfer model not locally validated stays capped below 0.90 even when NBI held-out metrics are strong.

- [ ] **Step 6: Run ML/backend readiness tests**

```bash
cd ml
pytest tests/test_ap_validation.py -v
cd ../backend
pytest tests/test_prediction_readiness.py -v
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/bridge_feature_service.py backend/app/services/model_governance.py backend/tests/test_prediction_readiness.py ml/simras_ml/ap_validation.py ml/tests/test_ap_validation.py
git commit -m "feat: add AP bridge eligibility and calibration gate"
```

---

### Task 9: Frontend Reports View Uses the Unified Assessment API

**Files:**
- Create: `frontend/src/types/assessment.ts`
- Create: `frontend/src/features/reports/SelectedAssetReport.tsx`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- `api.report(assetCode)` loads `/reports/{assetCode}`.
- `api.reportExport(assetCode, format)` returns a browser-downloadable response for `json|csv|pdf`.

- [ ] **Step 1: Add TypeScript assessment types matching backend field names**

```typescript
export type ModelUsage =
  | "USED_BY_MODEL"
  | "CONTEXT_ONLY"
  | "NOT_USED"
  | "WITHHELD";

export interface ConfidenceBreakdown {
  evidence_completeness: number;
  source_quality: number;
  domain_compatibility: number;
  model_calibration_quality: number;
  structural_evidence_quality: number;
  final_confidence: number;
  eligible_for_high_confidence: boolean;
  reason_codes: string[];
}
```

Define the remaining `FeatureEvidence`, `RULAssessment`, `PredictionAssessment`, and `AssetAssessment` interfaces with the exact backend snake_case names.

- [ ] **Step 2: Add API methods**

In `frontend/src/services/api.ts`:

```typescript
report: (assetCode: string) =>
  request<AssetAssessment>(`/reports/${encodeURIComponent(assetCode)}`),
```

Add a second helper that fetches `${API_BASE_URL}/reports/${encodeURIComponent(assetCode)}.${format}` and returns `response.blob()`.

- [ ] **Step 3: Implement `SelectedAssetReport`**

Render these cards directly from `assessment.prediction`:

- Health Score
- Risk Level
- Risk Score
- Confidence (`final_confidence * 100`)
- Remaining Useful Life

Rules:

- null AI values display `WITHHELD`, not `0`;
- if RUL status is `EXPERIMENTAL_PROXY`, display that label next to the value/interval;
- feature evidence table includes Source, Verification and Model Usage columns;
- confidence component table shows all five components;
- no component is hidden merely because it is low.

- [ ] **Step 4: Add PDF/CSV/JSON buttons**

Buttons call the export endpoint for the currently selected asset only. Use the filename supplied by `Content-Disposition` where available; otherwise use `SIMRAS-${assetCode}.${format}`.

- [ ] **Step 5: Run frontend typecheck/build**

```bash
cd frontend
npm run build
```

Expected: TypeScript and Vite build PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/assessment.ts frontend/src/features/reports/SelectedAssetReport.tsx frontend/src/services/api.ts frontend/src/App.tsx
git commit -m "feat: add evidence-aware selected asset reports UI"
```

---

### Task 10: End-to-End Acceptance Gate for Every Registered Asset

**Files:**
- Create: `backend/scripts/audit_asset_reports.py`
- Create: `backend/tests/test_report_contract.py`

**Interfaces:**
- CLI exits non-zero only for broken API/report contracts, duplicate asset codes, inconsistent Twin/Report prediction fields, or invalid confidence/RUL semantics. It does not fail merely because a legitimate field is withheld.

- [ ] **Step 1: Add report-contract tests**

```python
def test_withheld_is_valid_but_fake_high_confidence_is_not():
    assert validate_prediction_contract(
        confidence=0.55,
        eligible_for_high_confidence=False,
        status="SIMRAS_PREDICTION_LOW_CONFIDENCE",
    ) == []
    errors = validate_prediction_contract(
        confidence=0.95,
        eligible_for_high_confidence=False,
        status="SIMRAS_PREDICTION",
    )
    assert "HIGH_CONFIDENCE_WITHOUT_ELIGIBILITY" in errors
```

Also test:

- RUL proxy with value must have status `EXPERIMENTAL_PROXY`;
- RUL `WITHHELD` may have no value;
- a report must always contain the selected asset code;
- `USED_BY_MODEL` evidence must have a non-null value and a source/verification state.

- [ ] **Step 2: Implement audit script**

The script queries all `Asset.asset_code` values and for each calls `build_asset_assessment(session, code)`. Write one CSV row per asset with:

```text
asset_code,asset_type,report_ok,health_status,risk_status,confidence,rul_status,used_feature_count,withheld_feature_count,error_codes
```

- [ ] **Step 3: Add Twin/Report consistency checks**

For each asset, compare the common fields returned by `build_twin()` and `build_asset_assessment()`:

```text
health_score
risk_score
risk_level
remaining_life_years
rul_lower_bound
rul_upper_bound
confidence
model_version
feature_version
```

Numerical values must match exactly because both should originate from one assessment object after Task 5.

- [ ] **Step 4: Run backend/ML/frontend verification**

```bash
cd backend
pytest -q
python -m scripts.audit_asset_reports
cd ../ml
pytest -q
cd ../frontend
npm run build
```

Expected:

- all test suites PASS;
- audit produces a row for every registered asset;
- no asset fails report generation;
- confidence >= 0.90 appears only when `eligible_for_high_confidence=true`;
- RUL values are either validated ML output or explicitly experimental proxy output;
- withheld fields remain allowed where real evidence is missing.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/audit_asset_reports.py backend/tests/test_report_contract.py
git commit -m "test: add all asset report acceptance gate"
```

---

## Execution Order and Checkpoints

Run Tasks 1-4 first as the backend correctness checkpoint. At that point traffic wiring and RUL persistence are testable without touching Reports UI.

Run Tasks 5-6 second as the selected-asset assessment/report checkpoint. Verify Kanaka Durga Flyover and at least one dam, barrage, airport, and temple report before continuing.

Run Tasks 7-8 third as the bridge-coverage/model-governance checkpoint. More bridges may appear in the API even while predictions remain withheld; this is correct until AP evidence/model eligibility passes.

Run Tasks 9-10 last as the UI/export/full-registry checkpoint.

## Self-Review Results

- **Spec coverage:** All ten design areas are covered: unified assessment, bridge API expansion, bridge feature contract, traffic/load evidence, confidence, NBI/AP adaptation, RUL, persistence, reports, feature-usage contract, and acceptance tests.
- **No fabricated-value path:** Every task preserves null/withheld behavior when authoritative inputs are missing.
- **Confidence consistency:** Only `confidence_service.calculate_confidence()` can authorize >=0.90, and Task 8 supplies real local-validation/calibration state.
- **RUL consistency:** Task 4 removes the current hard-coded `DISABLED` persistence path; Task 5 makes Twin and Report consume one RUL object.
- **Type consistency:** Frontend uses the exact backend snake_case contract and the same four `model_usage` values.
- **Report consistency:** All exports serialize `AssetAssessment`; none computes a second prediction.
