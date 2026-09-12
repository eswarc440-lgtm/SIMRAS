from __future__ import annotations

import asyncio
import csv
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import (
    Asset,
    AssetModel,
    DataSource,
    EnvironmentObservation,
    Inspection,
    Prediction,
)
from app.services.risk_engine import RiskInput, score_risk


def optional_int(value: str) -> int | None:
    return int(value) if value.strip() else None


def optional_float(value: str) -> float | None:
    return float(value) if value.strip() else None


def seed_path() -> Path:
    configured = os.getenv("SIMRAS_SEED_FILE")
    if configured:
        return Path(configured)
    docker_path = Path("/data/seed/assets.csv")
    if docker_path.exists():
        return docker_path
    return Path(__file__).resolve().parents[2] / "data" / "seed" / "assets.csv"


async def ensure_source(session) -> DataSource:
    source = await session.scalar(select(DataSource).where(DataSource.code == "DEMO_SEED"))
    if source:
        return source
    source = DataSource(
        code="DEMO_SEED",
        name="SIMRAS demonstration seed",
        organisation="SIMRAS",
        source_type="SYNTHETIC_DEMO",
        licence="Project test data only",
        refresh_policy="Never; replace with verified records",
        is_authoritative=False,
    )
    session.add(source)
    await session.flush()
    return source


async def seed() -> None:
    path = seed_path()
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {path}")

    async with SessionLocal() as session:
        source = await ensure_source(session)
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        for record in rows:
            existing = await session.scalar(
                select(Asset).where(Asset.asset_code == record["asset_code"])
            )
            if existing:
                continue

            longitude = float(record["longitude"])
            latitude = float(record["latitude"])
            asset = Asset(
                asset_code=record["asset_code"],
                name=record["name"],
                asset_type=record["asset_type"],
                subtype=record["subtype"] or None,
                district=record["district"] or None,
                owner=record["owner"] or None,
                identity_status=record["identity_status"],
                built_year=optional_int(record["built_year"]),
                design_life_years=optional_int(record["design_life_years"]),
                material=record["material"] or None,
                condition=record["condition"] or None,
                representative_geometry=WKTElement(
                    f"POINT({longitude} {latitude})", srid=4326
                ),
                source_id=source.id,
                confidence_score=optional_float(record["confidence_score"]),
                is_estimated=record["is_estimated"].lower() == "true",
            )
            session.add(asset)
            await session.flush()

            session.add(
                AssetModel(
                    asset_id=asset.id,
                    format="procedural",
                    fidelity_level="L0",
                    model_source="SIMRAS procedural illustration",
                    is_asset_specific=False,
                    heading_deg=0,
                )
            )

            observed_at = datetime.now(UTC) - timedelta(hours=2)
            rainfall_24h = optional_float(record["rainfall_24h"])
            rainfall_7d = optional_float(record["rainfall_7d"])
            water_anomaly = optional_float(record["water_level_anomaly"])
            for variable, value, unit in [
                ("rainfall_24h", rainfall_24h, "mm"),
                ("rainfall_7d", rainfall_7d, "mm"),
                ("water_level_anomaly", water_anomaly, "m"),
            ]:
                if value is None:
                    continue
                session.add(
                    EnvironmentObservation(
                        asset_id=asset.id,
                        variable=variable,
                        value=value,
                        unit=unit,
                        observed_at=observed_at,
                        ingested_at=datetime.now(UTC),
                        source_id=source.id,
                        source_type="SYNTHETIC_DEMO",
                        spatial_method="seed record",
                        quality_flag="UNVERIFIED",
                        confidence_score=0.3,
                        is_estimated=True,
                    )
                )

            inspection_score = optional_float(record["inspection_score"])
            if inspection_score is not None:
                session.add(
                    Inspection(
                        asset_id=asset.id,
                        inspection_date=date.today() - timedelta(days=180),
                        inspection_type="DEMONSTRATION",
                        condition=record["condition"],
                        score=inspection_score,
                        inspector="Synthetic seed",
                        notes="Replace with an approved inspection record.",
                        source_id=source.id,
                        quality_flag="SYNTHETIC",
                        is_synthetic=True,
                    )
                )

            result = score_risk(
                RiskInput(
                    built_year=asset.built_year,
                    design_life_years=asset.design_life_years,
                    condition=asset.condition,
                    inspection_score=inspection_score,
                    days_since_inspection=180 if inspection_score is not None else None,
                    rainfall_mm_24h=rainfall_24h,
                    rainfall_mm_7d=rainfall_7d,
                    water_level_anomaly_m=water_anomaly,
                    flood_exposure=optional_float(record["flood_exposure"]),
                    traffic_load_ratio=optional_float(record["traffic_load_ratio"]),
                    source_confidence=asset.confidence_score,
                )
            )
            now = datetime.now(UTC)
            for target, value, predicted_class in [
                ("health", result.health_score, None),
                ("risk", result.risk_score, result.risk_level),
            ]:
                session.add(
                    Prediction(
                        asset_id=asset.id,
                        prediction_time=now,
                        target=target,
                        value=value,
                        predicted_class=predicted_class,
                        confidence_score=result.confidence,
                        model_version=result.model_version,
                        feature_version=result.feature_version,
                        status=result.status,
                        factors=result.factors,
                    )
                )

        await session.commit()
        print(f"Seed complete: {len(rows)} source-labelled demonstration assets checked")


if __name__ == "__main__":
    asyncio.run(seed())

