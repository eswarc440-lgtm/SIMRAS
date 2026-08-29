from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import ModelRegistry


async def register() -> None:
    artifact_dir = Path(os.getenv("SIMRAS_ML_ARTIFACT_DIR", "/artifacts/bridge_nbi"))
    manifest_path = artifact_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["stage"] not in {"RESEARCH_TRANSFER", "VALIDATED_LOCAL"}:
        raise RuntimeError(f"Refusing to register model stage {manifest['stage']}")
    async with SessionLocal() as session:
        existing = await session.scalar(
            select(ModelRegistry).where(
                ModelRegistry.model_name == manifest["model_name"],
                ModelRegistry.version == manifest["version"],
            )
        )
        if existing:
            print(f"Model already registered: {manifest['version']}")
            return
        session.add(
            ModelRegistry(
                model_name=manifest["model_name"],
                version=manifest["version"],
                training_dataset=manifest["data_source"],
                feature_version=manifest["feature_version"],
                metrics={
                    **manifest["metrics"],
                    "gates": manifest["gates"],
                    "training_scope": manifest["training_scope"],
                    "model_validated": manifest["model_validated"],
                    "limitations": manifest["limitations"],
                },
                stage=manifest["stage"],
                artifact_uri=str(artifact_dir),
                checksum=manifest["artifact_checksums"].get("health.joblib"),
            )
        )
        await session.commit()
        print(f"Registered {manifest['version']} as {manifest['stage']}")


if __name__ == "__main__":
    asyncio.run(register())
