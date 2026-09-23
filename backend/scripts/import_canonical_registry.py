"""SIMRAS Canonical Asset Registry Importer.

Imports or synchronizes the authoritative 194-asset baseline from
data/canonical_assets_194.json into public.assets and related tables.
Idempotent: safe to run repeatedly without creating duplicate assets.
Preserves existing officer-added assets and user modifications.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import create_async_engine

backend_root = Path(__file__).resolve().parents[1]
repo_root = backend_root.parent

import sys
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.entities import Asset, AssetModel, DataSource, Prediction

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("canonical_import")


def find_canonical_file() -> Path:
    candidates = [
        repo_root / "data" / "canonical_assets_194.json",
        Path("/data/canonical_assets_194.json"),
        backend_root / "data" / "canonical_assets_194.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"Could not find canonical_assets_194.json in {candidates}")


async def ensure_canonical_source(session) -> DataSource:
    source = await session.scalar(
        select(DataSource).where(DataSource.code == "CANONICAL_AP_REGISTRY")
    )
    if source:
        return source
    source = DataSource(
        code="CANONICAL_AP_REGISTRY",
        name="Andhra Pradesh Canonical Infrastructure Registry",
        organisation="Government of Andhra Pradesh / Central Authorities",
        source_type="OFFICIAL_REGISTRY",
        url="https://simras.ap.gov.in",
        licence="Government of Andhra Pradesh Open Data",
        refresh_policy="Authoritative baseline",
        is_authoritative=True,
    )
    session.add(source)
    await session.flush()
    return source


async def import_canonical_registry() -> int:
    path = find_canonical_file()
    logger.info("Reading canonical assets from %s...", path)
    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)

    logger.info("Found %d canonical records to ingest/reconcile.", len(records))

    async with SessionLocal() as session:
        source = await ensure_canonical_source(session)

        # Existing assets in DB
        res = await session.execute(select(Asset.asset_code, Asset.id))
        existing_assets = {row[0]: row[1] for row in res.fetchall()}

        inserted = 0
        updated = 0

        now = datetime.now(UTC)

        for rec in records:
            code = rec["asset_code"]
            name = rec.get("name") or code
            asset_type = rec.get("asset_type", "other").lower()
            subtype = rec.get("subtype")
            district = rec.get("district")
            built_year = rec.get("built_year")
            material = rec.get("material")
            condition = rec.get("condition") or "UNKNOWN"
            lat = rec.get("latitude")
            lon = rec.get("longitude")
            identity_status = rec.get("identity_status") or "VERIFIED"
            dimensions = rec.get("dimensions") or {}

            if lat is None or lon is None:
                continue

            geom = WKTElement(f"POINT({lon} {lat})", srid=4326)

            if code in existing_assets:
                asset_id = existing_assets[code]
                # Update existing asset non-destructively
                await session.execute(
                    text("""
                        UPDATE public.assets
                        SET
                            name = COALESCE(name, :name),
                            asset_type = :asset_type,
                            subtype = COALESCE(subtype, :subtype),
                            district = COALESCE(district, :district),
                            built_year = COALESCE(built_year, :built_year),
                            material = COALESCE(material, :material),
                            condition = COALESCE(condition, :condition),
                            representative_geometry = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                            identity_status = COALESCE(identity_status, :identity_status)
                        WHERE id = :id
                    """),
                    {
                        "id": asset_id,
                        "name": name,
                        "asset_type": asset_type,
                        "subtype": subtype,
                        "district": district,
                        "built_year": built_year,
                        "material": material,
                        "condition": condition,
                        "lon": lon,
                        "lat": lat,
                        "identity_status": identity_status,
                    }
                )
                updated += 1
            else:
                asset = Asset(
                    asset_code=code,
                    name=name,
                    asset_type=asset_type,
                    subtype=subtype,
                    district=district,
                    owner="Government of Andhra Pradesh",
                    status="ACTIVE",
                    identity_status=identity_status,
                    built_year=built_year,
                    material=material,
                    condition=condition,
                    representative_geometry=geom,
                    source_id=source.id,
                    confidence_score=0.95,
                    is_estimated=False,
                )
                session.add(asset)
                await session.flush()
                asset_id = asset.id
                existing_assets[code] = asset_id
                inserted += 1

            # Ensure AssetModel
            m_res = await session.execute(
                select(AssetModel).where(AssetModel.asset_id == asset_id).limit(1)
            )
            model = m_res.scalar_one_or_none()
            fidelity = rec.get("fidelity_status") or "L2"
            if not model:
                session.add(
                    AssetModel(
                        asset_id=asset_id,
                        format="parametric",
                        fidelity_level=fidelity,
                        model_source=rec.get("visual_strategy") or "SIMRAS Evidence Twin",
                        is_asset_specific=True,
                        dimensions=dimensions,
                    )
                )

            # Ensure Prediction (health / risk / rul baseline if provided)
            p_res = await session.execute(
                select(Prediction).where(Prediction.asset_id == asset_id).limit(1)
            )
            existing_pred = p_res.scalar_one_or_none()
            if not existing_pred and rec.get("health_score") is not None:
                health = float(rec["health_score"])
                risk = float(rec.get("risk_score", 0.0))
                risk_lvl = rec.get("risk_level") or ("HIGH" if risk >= 70 else "MEDIUM" if risk >= 40 else "LOW")
                raw_basis = rec.get("assessment_basis") or "EVIDENCE_DERIVED"
                prefix = raw_basis.split(":")[0].strip()
                allowed_statuses = {"ML_VALIDATED", "ML_TRANSFER", "INSPECTION_DERIVED", "EVIDENCE_DERIVED", "ESTIMATED_PROXY", "WITHHELD"}
                status = prefix if prefix in allowed_statuses else "EVIDENCE_DERIVED"
                factors = [raw_basis]

                session.add(
                    Prediction(
                        asset_id=asset_id,
                        prediction_time=now,
                        target="health",
                        value=health,
                        predicted_class=None,
                        confidence_score=0.9,
                        model_version="simras_baseline_v1",
                        feature_version="v1",
                        status=status,
                        factors=factors,
                    )
                )
                session.add(
                    Prediction(
                        asset_id=asset_id,
                        prediction_time=now,
                        target="risk",
                        value=risk,
                        predicted_class=risk_lvl,
                        confidence_score=0.9,
                        model_version="simras_baseline_v1",
                        feature_version="v1",
                        status=status,
                        factors=factors,
                    )
                )
                if rec.get("rul_years") is not None:
                    session.add(
                        Prediction(
                            asset_id=asset_id,
                            prediction_time=now,
                            target="rul",
                            value=float(rec["rul_years"]),
                            predicted_class=None,
                            confidence_score=0.85,
                            model_version="simras_baseline_v1",
                            feature_version="v1",
                            status=status,
                            factors=factors,
                        )
                    )

        await session.commit()
        logger.info(
            "Canonical registry import complete: %d inserted, %d updated. Total in database: %d.",
            inserted,
            updated,
            len(existing_assets),
        )

        # Output category summary
        summary_res = await session.execute(
            text("""
                SELECT UPPER(CAST(asset_type AS TEXT)) as cat, count(*)
                FROM public.assets
                GROUP BY UPPER(CAST(asset_type AS TEXT))
                ORDER BY count(*) DESC
            """)
        )
        logger.info("Assets by category in database:")
        for cat, cnt in summary_res.fetchall():
            logger.info("  %s: %d", cat, cnt)

    return 0


if __name__ == "__main__":
    asyncio.run(import_canonical_registry())
