# Open-source repository reuse

SIMRAS integrates focused projects instead of copying an unrelated digital-twin
demo and inheriting unverifiable data.

| Priority | Repository | SIMRAS use | Decision |
|---|---|---|---|
| P0 | [FastAPI full-stack template](https://github.com/fastapi/full-stack-fastapi-template) | Docker, React/FastAPI/PostgreSQL, tests and CI patterns | Architecture patterns only |
| P0 | [CesiumJS](https://github.com/CesiumGS/cesium) | WGS84 geospatial 3D and 3D Tiles | Integrated in frontend |
| P0 | [PostGIS](https://github.com/postgis/postgis) | Spatial system of record | Integrated |
| P0 | [GDAL](https://github.com/OSGeo/gdal) | Raster/vector conversion | ETL runtime dependency for raster phase |
| P0 | [GeoPandas](https://github.com/geopandas/geopandas) | Spatial cleaning and joins | ETL dependency |
| P0 | [Prefect](https://github.com/PrefectHQ/prefect) | Schedules, retries and audit | ETL flows included |
| P1 | [Martin](https://github.com/maplibre/martin) | PostGIS vector tiles | Optional Compose profile |
| P1 | [XGBoost](https://github.com/dmlc/xgboost) | Health/risk model | Add after labelled dataset gate |
| P1 | [MLflow](https://github.com/mlflow/mlflow) | Model registry and experiments | Planned ML profile |
| P1 | [FROST Server](https://github.com/FraunhoferIOSB/FROST-Server) | OGC SensorThings API | Add when real sensors exist |
| P1 | [Mosquitto](https://github.com/eclipse-mosquitto/mosquitto) | MQTT transport | Add with sensors |

## Why no large digital-twin repository was copied

The differentiating work is AP asset identity, source provenance, temporal
state and engineering validation. A generic city-twin UI cannot supply those.
The selected repositories provide maintained infrastructure without pretending
to provide Andhra Pradesh engineering truth.

## Licence practice

Repository code and datasets have independent licences. Record dataset and 3D
content licences in `data_sources`; do not assume the SIMRAS MIT licence changes
the licence of OSM, government data, imagery or model files.

