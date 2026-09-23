# SIMRAS Digital Twin

SIMRAS is a source-aware infrastructure digital twin for Andhra Pradesh bridges,
dams and barrages. It combines PostGIS asset identity, environmental state,
inspection history, explainable health/risk analytics, 2D GIS and web 3D.

## What works in this repository

- Dockerized React/Vite, FastAPI and PostGIS stack.
- Versioned PostGIS schema with spatial indexes and provenance tables.
- Asset list, GeoJSON, high-risk, full twin-state and freshness APIs.
- Rule-based risk scoring that returns factors and confidence.
- Seeded bridge/dam records explicitly marked as unverified demonstration data.
- Leaflet GIS, risk filters, source badges and a Three.js procedural twin.
- Cesium viewer component for WGS84 terrain placement when a token is supplied.
- CSV ETL validation, ingestion audit design, tests and GitHub Actions.

The seed records make the application testable. They are **not engineering
truth**. Replace them through the ETL pipeline and retain their source,
timestamp, quality and confidence fields.

## Repository layout

```text
backend/     FastAPI, SQLAlchemy/GeoAlchemy, Alembic, risk/twin services
frontend/    React, Leaflet, Three.js and Cesium user interface
etl/         Source-aware ingestion and validation package
ml/          Leakage-aware XGBoost/MLflow training package
data/seed/   Clearly labelled bootstrapping records
docs/        Architecture, data contract, implementation and AWS deployment
infra/       Nginx and operational configuration
```

## Start locally

Requirements: Git, Docker Desktop and Docker Compose.

### PowerShell

```powershell
git clone <your-repository-url> simras-digital-twin
Set-Location simras-digital-twin
Copy-Item .env.example .env
docker compose up --build
```

### Bash

```bash
git clone <your-repository-url> simras-digital-twin
cd simras-digital-twin
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: http://localhost:5173
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

The backend automatically runs migrations and idempotently inserts seed data.

## First verification

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/v1/assets
Invoke-RestMethod http://localhost:8000/api/v1/assets/AP_DAM_00001/twin
Invoke-RestMethod http://localhost:8000/api/v1/assets/high-risk
```

## Add verified data

1. Copy `data/seed/assets.csv` to a working CSV.
2. Replace approximate records with verified source values.
3. Set `identity_status=VERIFIED` only after independent identity and coordinate checks.
4. Keep `source_name`, `external_id`, `retrieved_at`, `confidence_score` and licence.
5. Run the ETL validation before ingestion.

```bash
docker compose --profile etl run --rm etl \
  python -m simras_etl.validate_assets /data/verified/assets.csv
```

Detailed instructions are in [docs/implementation-phases.md](docs/implementation-phases.md)
and [docs/data-contract.md](docs/data-contract.md).

To publish the repository, follow [docs/git-setup.md](docs/git-setup.md).

## Reality contract

Every displayed value should identify whether it is observed, a government
record, satellite-derived, modelled/reanalysis, AI-predicted, estimated or
synthetic. Missing sensors remain `NOT_AVAILABLE`; unreliable RUL remains null.

## Reused open-source foundations

The structure follows proven patterns from the FastAPI full-stack template.
CesiumJS supplies geospatial 3D, GDAL/GeoPandas support ETL, and Martin is an
optional PostGIS vector-tile service. See [docs/repository-reuse.md](docs/repository-reuse.md).

## License

MIT. External datasets, models and 3D content retain their own licences and
must be registered in `data_sources`.
