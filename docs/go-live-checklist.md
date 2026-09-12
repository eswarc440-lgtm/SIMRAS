# Go-live acceptance checklist

The application is not production-ready until every applicable item passes.

## Asset and GIS

- [ ] Every public pilot asset has a canonical ID and verified external source.
- [ ] Coordinates are independently verified; no placeholder geometry remains.
- [ ] PostGIS geometry renders in the GIS with road/river context.
- [ ] Source-specific IDs are stored in `asset_identifiers`.
- [ ] Failed ETL records are quarantined and counted.

## Digital twin

- [ ] The selected asset loads the correct 3D model.
- [ ] Model fidelity and provenance are visible.
- [ ] Procedural geometry is labelled illustrative.
- [ ] GLB/3D Tiles checksum, version, scale, heading and position are recorded.
- [ ] Current and historic states can be distinguished.

## Observations

- [ ] Every environment value has source, time, source type and quality.
- [ ] ERA5 is labelled reanalysis, not live.
- [ ] CWC/WRIS data are shown only after legitimate asset matching.
- [ ] Missing sensors say `NOT_INSTRUMENTED` or `NOT_AVAILABLE`.
- [ ] Synthetic inspection and maintenance records are visibly different.
- [ ] Freshness/staleness is returned by the API and visible in the UI.

## AI

- [ ] Training data, feature version and model version are immutable references.
- [ ] Test assets and future time periods are isolated from training.
- [ ] Regression/classification/calibration metrics are recorded.
- [ ] Confidence or prediction intervals are displayed when supported.
- [ ] RUL is disabled or explicitly experimental until validated longitudinally.
- [ ] Computer-vision defects remain candidates until human verification.

## Application and operations

- [ ] No production frontend contains a hard-coded localhost API URL.
- [ ] A clean checkout builds reproducibly.
- [ ] CI gates backend, ETL, frontend, migration and integration tests.
- [ ] Public read APIs and authenticated write/ingestion APIs are separated.
- [ ] CORS, TLS, secrets, rate limits and dependency scans are configured.
- [ ] Database backup restoration has been tested.
- [ ] API errors, ETL failure, stale feeds and prediction failure produce alerts.
- [ ] Dataset, model and 3D-content licences are recorded.

