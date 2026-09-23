# SIMRAS Repository Audit Report
**Date:** September 23, 2026  
**System:** SIMRAS — Smart Infrastructure Monitoring & Risk Assistance System (Andhra Pradesh, India)  
**Lead Architect & Implementation Engineer:** Antigravity  

---

## 1. Executive Summary

This audit assesses the state of the SIMRAS repository to establish a verified baseline before executing the 15-phase end-to-end implementation plan. SIMRAS is an existing, advanced infrastructure intelligence and digital-twin platform combining:
1. **PostgreSQL/PostGIS** database layer with spatial querying and canonical asset indexing.
2. **FastAPI** backend with source-aware evidence pipelines, deterioration predictions, and report generation.
3. **React/TypeScript** frontend with Three.js realistic Digital Twins, Leaflet GIS, and multi-workspace architecture.
4. **Machine Learning** artifacts trained on National Bridge Inventory transfer data with strict provenance tracking.
5. **Government Datasets** (NWDP, WRIS, CWC NRLD, AAI aerodrome charts, AP Tourism) grounding 194 canonical infrastructure assets.

The repository contains extensive, highly valuable domain implementations that must be preserved, repaired, and unified into an authoritative end-to-end system.

---

## 2. Inventory of Repository Assets

### 2.1 File System Structure
- `backend/`: FastAPI application (`app/`), database models (`app/models/`), API routes (`app/api/routes/`), domain services (`app/services/`), Alembic migrations (`alembic/`), maintenance and import scripts (`scripts/`), data cache (`data/`), and test suite (`tests/`).
- `frontend/`: React 19 + TypeScript + Vite application with Three.js (`three`), Cesium (`@cesium/engine`), Leaflet, Recharts, and Tailwind CSS.
- `etl/`: Data extraction and normalization pipelines (`simras_etl/`) for WRIS, NASA POWER, NWDP telemetry, and OpenStreetMap statewide layers.
- `data/`:
  - `canonical_assets_194.json`: Authoritative canonical asset registry containing 194 assets across 5 categories (167 Dams, 10 Barrages, 2 Bridges, 8 Airports, 7 Temples).
  - `reality_twin/`: Reality twin queue, airport alias reviews, coordinate truth.
  - `official/evidence_manifests/`: Government evidence manifests (e.g., Sir Arthur Cotton Barrage).
  - `seed/assets.csv`: Small 17-record demonstration seed file.
- `artifacts/`:
  - `artifacts/bridge_nbi/`: Trained ML deterioration models (`health.joblib`, `risk.joblib`, `risk_calibrator.joblib`, `rul_lower.joblib`, `rul_median.joblib`, `rul_upper.joblib`, `manifest.json`).
  - `artifacts/bridge_nbi_sparse/`, `artifacts/validation/`: Validation run outputs and candidate models.
- `docs/`: Comprehensive design specifications, implementation runbooks, architecture diagrams, and superpower specs (`docs/superpowers/`).
- `root/`:
  - `compose.yml`, `compose.production.yml`: Docker Compose specifications.
  - `server.ts` & `server/`: Standalone Express/Node gateway previously used for demo/Vercel hosting.
  - `src/`: Root-level React source containing rich officer workflows (Add Asset Wizard, Inspections Manager, Maintenance Planner, Review Queue, Notification Modal, AI Assistant Drawer).
  - Backup directories (`frontend_backup_*`, `frontend_failed_merge_*`): Historic backups created during previous merge operations.

---

## 3. Database & Migrations Audit

### 3.1 Database Engine & Tables
- **Running Instance:** PostgreSQL 17.10 with PostGIS 3.5 on `localhost:5432` (`user=simras`, `db=simras`).
- **Public Tables (27):**
  - Core Registry: `assets`, `asset_identifiers`, `asset_components`, `asset_geometries`, `asset_models`
  - Provenance & Telemetry: `data_sources`, `source_documents`, `official_evidence`, `sensors`, `observations`, `environment_observations`, `remote_sensing_observations`, `state_snapshots`
  - Operational Workflows: `inspections`, `defects`, `maintenance`, `alerts`, `dam_inspection_events`, `dam_inspection_findings`
  - Intelligence: `model_registry`, `predictions`, `map_features`, `ingestion_runs`
  - System: `alembic_version`, `spatial_ref_sys`, `geometry_columns`, `geography_columns`

### 3.2 Alembic Migration Architecture & The "Fresh DB" Issue
- Current head: `0006_expand_string_lengths`
- Migration chain:
  - `0001_initial`: Calls `Base.metadata.create_all()`.
  - `0002_statewide_map_features`: Adds `map_features` table.
  - `0003_asset_twin_metadata`: Modifies `asset_models` columns.
  - `0004_government_evidence`: Adds `source_documents` and `official_evidence`.
  - `0005_dam_inspection_ground_truth`: Adds `dam_inspection_events` and `findings`.
  - `0006_expand_string_lengths`: Expands column character lengths.
- **Root Cause of Fresh DB Failure:** Because `0001_initial` invoked `Base.metadata.create_all()` against the current SQLAlchemy ORM schema, all tables and columns are created immediately on a clean database. When subsequent migrations (`0002` through `0006`) run, they attempt to create tables or columns that already exist, causing fatal errors unless suppressed.
- **Permanent Solution:** Implement three-state detection in `db_preflight.py`:
  - `PRISTINE_DATABASE`: Run `create_all()`, validate schema, stamp Alembic head directly, import canonical registry idempotently.
  - `EXISTING_DATABASE`: Run `alembic upgrade head`, validate schema.
  - `PARTIAL_SCHEMA_DETECTED`: Abort startup immediately and output discrepancy diagnostics without stamping.

### 3.3 Current Data Population
- Database currently contains **17 assets**:
  - `bridge`: 2 (Godavari Arch Bridge, Kanaka Durga Flyover)
  - `airport`: 6 (AAI Operational Airports)
  - `temple`: 7 (Statewide Pilgrimage Centres)
  - `dam`: 1 (Prakasam Barrage stored as dam/barrage)
  - `barrage`: 1
- **Target Population:** Ingest the complete 194-asset canonical registry from `data/canonical_assets_194.json` (167 Dams, 10 Barrages, 2 Bridges, 8 Airports, 7 Temples) preserving existing officer records and linkages.

---

## 4. Machine Learning & Deterioration Models

### 4.1 Artifact Inventory (`artifacts/bridge_nbi/`)
- Model Name: `simras_nbi_bridge_deterioration`
- Version: `nbi_transfer_20260831_203056`
- Stage: `RESEARCH_TRANSFER` (transparently documented as FHWA NBI transfer model, not locally validated in AP)
- Tasks:
  - Health Score: Regression (`health.joblib`, MAE: 0.134 rating units)
  - Risk Score & Level: Calibrated classification (`risk.joblib`, `risk_calibrator.joblib`, ROC-AUC: 0.972, Brier: 0.026)
  - Remaining Useful Life (RUL): Quantile interval regression (`rul_lower.joblib`, `rul_median.joblib`, `rul_upper.joblib`)
- Integrity: All SHA-256 artifact checksums in `manifest.json` match the binary files.
- Policy: Frontend and Reports must display `RESEARCH_TRANSFER` or `ESTIMATED_PROXY` status and must NEVER fallback to hardcoded `Health=100` or `Risk=0`.

---

## 5. Digital Twin Inventory & Showcase Assets

### 5.1 Showcase Digital Twins
The repository contains high-fidelity, evidence-backed procedural 3D models rather than generic boxes:
1. **Godavari Arch Bridge (`AP_BR_00001`):**
   - Implemented in: `frontend/src/features/digital-twin/BridgeEngineeringViewer.tsx` (1834 lines).
   - Features: Multi-span bowstring steel-concrete arches, 28 span bays, suspension hangers, pier shafts, abutments, river water plane.
2. **Kanaka Durga Flyover (`AP_BR_00002`):**
   - Implemented in: `BridgeEngineeringViewer.tsx`.
   - Features: Curved elevated spine deck, post-tensioned box girder segments, single-pier supports, Krishna River embankment context.
3. **Prakasam Barrage (`AP_DAM_00001`):**
   - Implemented in: `frontend/src/features/digital-twin/RealityTwinAssetViewer.tsx` and `damBarrageTwinRegistry.ts`.
   - Features: 1232.92m crest length, 70 regulator gates, left/right scouring sluices, road deck, upstream/downstream water levels.
4. **Polavaram Project (`AP_DAM_00002`):**
   - Implemented in: `RealityTwinAssetViewer.tsx`.
   - Features: Earth-cum-Rockfill (ECRF) dam body, 1118.4m spillway, 48 radial gates, 960 MW powerhouse context.
5. **Sir Arthur Cotton Barrage (`AP_BAR_WRIS_B00131`):**
   - Implemented in: `RealityTwinAssetViewer.tsx`.
   - Features: 4 separate arms (Dowleswaram, Ralli, Maddur, Vijjeswaram), 175 regulator vents, road deck.
6. **Srisailam Dam (`AP_DAM_NWDP_AP01VH0059`):**
   - Features: 512m length, 145m height, 12 radial crest gates, deep gorge terrain.
7. **Airports (`AP_AIR_VOBZ`, `AP_AIR_VOTP`, etc.):**
   - Features: Source-accurate runways (length, width, orientation heading angle), runway strips, taxiway layout, apron, terminal, control tower.
8. **Temples (`AP_TEMPLE_KANAKA_DURGA`, `AP_TEMPLE_TIRUMALA`, `AP_TEMPLE_SRIKALAHASTI`):**
   - Features: Multi-tiered gopurams (source-reported height and tiers), mandapa, sanctum sanctorum (vimana/kalasam), plinth, compound walls.

### 5.2 Dynamic Source-Backed Dimensions
- Dimensions are dynamically calculated using Three.js bounding box geometry and attached via sprite labels (`addDimensions()`).
- All measurements display source provenance and remain anchored to geometry during rotation, panning, and zoom.

---

## 6. API & Backend Services Audit

### 6.1 Working Backend Endpoints
- `GET /api/v1/assets`: Query filters (asset_type, district, search, limit, offset), PostGIS geometry formatting.
- `GET /api/v1/assets/{asset_code}/twin`: Twin geometry mode, dimensions, components, and inspection/maintenance state.
- `GET /api/v1/assets/{asset_code}/bridge-profile`: Specific bridge engineering profile.
- `GET /api/v1/reports/assets/{asset_code}/json`: Asset report JSON payload.
- `GET /api/v1/reports/assets/{asset_code}/csv`: Asset report CSV export.
- `GET /api/v1/map/features`: PostGIS GIS features.

### 6.2 Missing / Disconnected Backend Endpoints
FastAPI backend currently lacks endpoints that must be implemented:
1. **Authentication:**
   - `POST /api/v1/auth/login`: Issue secure JWT token for roles `PUBLIC`, `OFFICER`, `REVIEWER`, `ADMIN`. Passwords hashed with bcrypt.
   - `GET /api/v1/auth/me`: Validate JWT and return current user profile.
2. **Inspections Workflow:**
   - `GET /api/v1/inspections`: Officer inspection queue (SCHEDULED, DUE_SOON, OVERDUE, IN_PROGRESS, COMPLETED).
   - `POST /api/v1/inspections`: Schedule or create inspection.
   - `PATCH /api/v1/inspections/{id}`: Update condition, enter defect findings, upload evidence.
   - `POST /api/v1/inspections/{id}/submit`: Submit for reviewer approval.
3. **Maintenance Workflow:**
   - `GET /api/v1/maintenance`: Maintenance records and scheduled tasks.
   - `POST /api/v1/maintenance`: Propose maintenance plan.
   - `PATCH /api/v1/maintenance/{id}`: Record maintenance progress and completion.
4. **Reviews Workflow:**
   - `GET /api/v1/reviews/queue`: Unified reviewer queue for pending submissions.
   - `POST /api/v1/reviews/{id}/action`: Approve, request revision, or reject (enforcing that an officer cannot approve their own submission).
5. **Event-Driven Notifications:**
   - `GET /api/v1/notifications`: User-specific notifications with unread counts.
   - `PATCH /api/v1/notifications/{id}/read`: Mark notification as read.
6. **Environmental Time Series:**
   - `GET /api/v1/assets/{asset_code}/environment/timeseries`: Timeseries data (rainfall, humidity, wind, traffic, water level, storage, inflow, outflow).
7. **Gemini AI Assistant:**
   - `POST /api/v1/ai/assistant`: Grounded Gemini proxy utilizing backend evidence context.

---

## 7. Frontend Integration & Architecture Analysis

### 7.1 Frontend Duality
- Root `src/`: Contains complete, highly styled components for the entire government platform (`PublicHeader`, `OfficerHeader`, `OfficerSidebar`, `PublicHome`, `GISCommandView`, `DigitalTwinPage`, `PublicReportsPage`, `OfficerDashboard`, `OfficerAssetTable`, `OfficerLoginPage`, `AddAssetWizard`, `InspectionsManager`, `MaintenancePlanner`, `ReviewQueue`, `NotificationModal`, `AiAssistantDrawer`).
- `frontend/src/`: Contains the containerized SPA with Three.js viewers, Cesium, and TanStack Router artifacts.
- **Action Plan:** Consolidate the rich UI components from `src/` into `frontend/src/` to create a unified, production-ready React application that natively communicates with FastAPI at `/api/v1/`.

### 7.2 Selected Asset Synchronization
- Asset selection must be unified across GIS, Digital Twin, Reports, Inspections, Maintenance, and AI Assistant via URL query parameter `?asset={asset_code}` and local storage backup.

---

## 8. Test Suite Baseline

- **Backend Pytest:** 52 tests passing. 1 test (`test_dam_training_table.py`) failed due to missing module `app.services.dam_training_table`.
- **Frontend Build:** `tsc -b && vite build` in `frontend/` succeeds with exit code 0.
- **Linting:** 175 ESLint errors and 155 warnings in `frontend/`, primarily loose `any` types and unused variables from previous merges.

---

## 9. Risk & Technical Debt Register

| ID | Issue | Impact | Mitigation Strategy |
|---|---|---|---|
| TD-01 | Alembic fresh DB failure | Fresh Docker/CI deployment fails | Replace naive upgrade with three-state `db_preflight.py` |
| TD-02 | Incomplete database population | Only 17 of 194 canonical assets in local DB | Idempotent canonical registry import from `data/canonical_assets_194.json` |
| TD-03 | Missing FastAPI backend routes | Officer workflows only exist in mock `server.ts` | Implement production FastAPI routes backed by PostgreSQL models |
| TD-04 | Missing Dockerfiles | `docker compose up --build` fails | Create multi-stage production Dockerfiles for `backend` and `frontend` |
| TD-05 | Shallow `/health` check | Degraded DB or missing tables return OK | Implement deep schema and table readiness checks |
| TD-06 | Missing PDF generation | Report download lacks multi-page charts | Implement ReportLab multi-page PDF generation engine |

---

**Audit Sign-off:** Complete. Backups will be established prior to commencing execution phases.
