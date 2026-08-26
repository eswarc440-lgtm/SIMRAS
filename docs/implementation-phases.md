# Implementation phases

The repository contains the foundation and local vertical slice. The checklists
below define the order for turning it into a verified public pilot.

## Phase 0 - Git and environment

- [x] Monorepo created with `main` branch.
- [x] Example environment and Docker Compose added.
- [x] CI workflow added.
- [ ] Create your GitHub repository and push `main`.
- [ ] Replace all development secrets.

Exit gate: a clean clone starts the frontend, API and PostGIS.

## Phase 1 - Canonical schema

- [x] PostGIS asset, provenance, geometry, inspection, observation, prediction and alert tables.
- [x] GiST indexes and Alembic migration.
- [x] Aggregate twin-state API contract.
- [ ] Add authenticated write routes only when user roles are defined.

Exit gate: migrations build an empty database without manual SQL.

## Phase 2 - Verified asset registry

- [x] OSM bridge and India-WRIS dam extractors.
- [x] CSV validation and AP coordinate bounds.
- [ ] Run official extracts and retain raw checksums.
- [ ] Match OSM, WRIS, CWC/NHAI identifiers without name-only joins.
- [ ] Independently verify pilot coordinates.
- [ ] Replace `DEMO_SEED` records.

Exit gate: one bridge and one dam/barrage have canonical IDs and verified coordinates.

## Phase 3 - Environmental and hydrological state

- [x] Provenance-aware environment storage and API.
- [ ] Integrate approved IMD current-weather access.
- [ ] Import CWC reservoir bulletins or approved API output.
- [ ] Backfill ERA5/ERA5-Land as historical reanalysis.
- [ ] Add Copernicus DEM elevation/slope.
- [ ] Add source-specific refresh/failure alerts.

Exit gate: current and historical data are distinguishable and freshness is visible.

## Phase 4 - First asset-specific 3D twins

- [x] L0 procedural fallback and fidelity badge.
- [x] Three.js close-up and Cesium WGS84 viewers.
- [ ] Validate or rebuild one bridge GLB and one dam/barrage GLB.
- [ ] Establish scale, heading, elevation, capture source and checksum.
- [ ] Register models in `asset_models` as L1/L2/L3 only with evidence.

Exit gate: selecting an asset loads its correct, provenance-labelled model.

## Phase 5 - Unified user experience

- [x] GIS registry, risk colours, search and type filters.
- [x] Highest-risk-first selection and aggregate twin endpoint.
- [x] Health/risk, environment, freshness and provenance panels.
- [ ] Add inspection/maintenance timeline and approved write workflows.
- [ ] Add alert acknowledgement and reports.

Exit gate: a user can move from the AP map to one complete asset state without hard-coded data.

## Phase 6 - AI health and risk

- [x] Transparent, tested rules baseline with factors and confidence.
- [x] RUL disabled when evidence is insufficient.
- [ ] Build asset-state-time training rows from real inspections.
- [ ] Split evaluation by asset and time.
- [ ] Compare linear/RF baseline with XGBoost and LightGBM.
- [ ] Record calibration, recall, MAE/RMSE/R2 and immutable model versions.
- [ ] Deploy only a model that beats the transparent baseline.

Exit gate: web predictions are reproducible decision support, not arbitrary numbers.

## Phase 7 - Satellite, defects and sensors

- [ ] Query Sentinel scenes and calculate source-labelled water/change metrics.
- [ ] Build inspection-photo upload and human verification.
- [ ] Evaluate crack detector on local inspection conditions.
- [ ] Add FROST/MQTT only after actual hardware exists.

Exit gate: machine detections remain candidates until human/engineering verification.

## Phase 8 - Production and AWS

- [x] Production container targets and Nginx routing.
- [x] CI test/build gates.
- [ ] Provision RDS PostgreSQL/PostGIS or protected EC2 PostGIS.
- [ ] Store GLB/3D Tiles and rasters in S3 with CloudFront.
- [ ] Configure HTTPS, authentication, backups and restore test.
- [ ] Add CloudWatch/OpenTelemetry monitoring and stale-data alerts.
- [ ] Run the go-live checklist.

Exit gate: production is reproducible from a clean commit and its backup is restorable.

