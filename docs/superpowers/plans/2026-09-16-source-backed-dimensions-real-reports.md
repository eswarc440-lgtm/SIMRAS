# Source-Backed Dimensions and Real Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make source-backed engineering dimensions visibly render on SIMRAS digital twins and make selected-asset reports show only available real/government evidence and eligible ML outputs.

**Architecture:** Keep authoritative engineering evidence separate from Three.js viewer normalization. The viewer consumes verified metrics from the existing topology/evidence registries and renders both moving 3D annotations and a compact visible engineering summary. Reports use a truth-filter that omits unavailable/insufficient fields entirely while preserving provenance and ML evidence gates.

**Tech Stack:** React 19, TypeScript, Three.js, FastAPI, SQLAlchemy, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-16-source-backed-l2-l3-digital-twins-design.md`

## Global Constraints

- Never fabricate engineering dimensions, condition, risk, RUL, inspection, maintenance, or environmental values.
- `L2` requires authoritative component topology/dimensions and verified real-world scale; no seed-generated engineering measurements.
- Dimension annotations display source values, never normalized Three.js extents.
- Missing/unavailable/insufficient values are omitted from report presentation instead of rendered as `NOT AVAILABLE`, `N/A`, or `INSUFFICIENT DATA`.
- ML output is shown only when the existing category/evidence/model-scope gate permits it.
- Government/source provenance remains visible for every presented engineering fact.

---

### Task 1: Report truth filter

**Files:**
- Create: `backend/app/services/report_truth.py`
- Create: `backend/tests/test_report_truth.py`
- Modify: `backend/app/api/routes/selected_asset_reports.py`

**Interfaces:**
- Produces: `is_report_value_present(value: Any) -> bool`
- Produces: `compact_report_mapping(mapping: dict[str, Any]) -> dict[str, Any]`
- Consumes: existing selected-asset report payloads.

- [ ] **Step 1: Write failing tests** for `None`, blank, `N/A`, `NOT AVAILABLE`, `WITHHELD`, and `INSUFFICIENT_*` values, plus valid numeric/string/government-source values.
- [ ] **Step 2: Run** `cd backend && pytest -q tests/test_report_truth.py` and verify failure before implementation.
- [ ] **Step 3: Implement** `report_truth.py` with recursive mapping/list compaction. Treat zero/false as valid values; drop only unavailable/insufficient sentinels.
- [ ] **Step 4: Integrate** the helper into selected-asset PDF/report presentation so `line()` skips absent values instead of printing unavailable placeholders. Keep source/evidence and explicit real values.
- [ ] **Step 5: Run** `cd backend && pytest -q tests/test_report_truth.py` and the existing report-related tests.

### Task 2: Always-visible real engineering dimensions

**Files:**
- Modify: `frontend/src/features/digital-twin/RealityTwinAssetViewer.tsx`
- Test/verify: `frontend` TypeScript build and source-contract checks.

**Interfaces:**
- Consumes: `dimensionOverlayMetrics: EngineeringMetric[]` where metrics are verified/source-backed.
- Produces: moving Three.js world annotations plus a compact HTML summary sourced from the same metrics.

- [ ] **Step 1: Add a regression assertion** in the repository patch/acceptance script that the viewer keeps `createWorldDimensionAnnotations(...)`, defaults dimensions visible, and renders verified dimension summary data.
- [ ] **Step 2: Ensure Prakasam** renders source values `1232.92 m`, `70` regulator gates, `12.19 m` gate width and `3.66 m` gate height through `getVerifiedWaterEngineeringValues`.
- [ ] **Step 3: Make dimension labels robust** by keeping `SpriteMaterial.depthTest=false`, moving the annotation group with the twin, and rendering a small verified-dimension strip inside the viewer so dimensions remain readable even at extreme camera angles.
- [ ] **Step 4: Hide unavailable engineering cards** from the engineering specification panel; do not display `UNAVAILABLE`/`NOT VERIFIED` cards.
- [ ] **Step 5: Run** `cd frontend && npm install && npm run test && npm run build`.

### Task 3: Source-backed fidelity and priority presentation

**Files:**
- Modify: `frontend/src/features/digital-twin/RealityTwinAssetViewer.tsx`
- Modify or extend: `frontend/src/features/digital-twin/verifiedWaterTopologyTwin.ts`

**Interfaces:**
- Consumes: existing verified water topology manifest.
- Produces: source-backed fidelity copy and priority-ready metadata without upgrading unsupported assets.

- [ ] **Step 1: Promote only supported water twins** (Prakasam, Polavaram, Srisailam, Somasila, Sir Arthur Cotton) to source-backed display copy based on their existing topology status.
- [ ] **Step 2: Keep detailed-survey geometry false** where drawings/survey are unavailable; label such assets `L2 SOURCE-MATCHED ENGINEERING TWIN`, never `L3`.
- [ ] **Step 3: Keep approximate fallback geometry** only for assets lacking source topology; never use its seed-derived dimensions as report truth.
- [ ] **Step 4: Verify** exact source-backed component counts (Prakasam 70 regulator gates + 14 scour sluices; Polavaram 48 radial gates) remain encoded in the source-backed builder.

### Task 4: End-to-end verification and PR

**Files:**
- Add/update only test/automation files required to run the patch safely.

**Interfaces:**
- Produces: passing backend tests, frontend tests/build, and an auditable GitHub PR against `simras-source-20260912-124514`.

- [ ] **Step 1: Run backend quality gates:** `cd backend && pip install -e '.[dev]' && ruff check . && pytest -q`.
- [ ] **Step 2: Run frontend quality gates:** `cd frontend && npm install && npm run test && npm run build`.
- [ ] **Step 3: Run source-truth assertions** confirming no unavailable/insufficient placeholder is deliberately emitted by selected-asset PDF lines and dimension overlay consumes verified values.
- [ ] **Step 4: Commit** implementation changes on `feature/source-backed-l2-l3-twins-20260916`.
- [ ] **Step 5: Open PR** to `simras-source-20260912-124514` with exact verification results and remaining evidence limitations.
