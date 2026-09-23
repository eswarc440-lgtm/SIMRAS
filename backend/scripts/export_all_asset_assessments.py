from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import Asset
from app.services.asset_health_assessment_report import apply_numeric_assessment, build_asset_health_assessment
from app.services.prediction_report_overlay import overlay_assessment_with_latest_predictions


FIELDS = [
    "asset_code",
    "name",
    "category",
    "health_score",
    "risk_score",
    "risk_level",
    "confidence",
    "rul_years",
    "prediction_basis",
    "health_basis",
    "risk_basis",
    "rul_basis",
    "features_used_count",
    "features_missing_count",
]


async def export(path: Path) -> int:
    async with SessionLocal() as session:
        assets = (
            await session.execute(select(Asset).order_by(Asset.asset_code.asc()))
        ).scalars().all()
        rows: list[dict[str, object]] = []
        for asset in assets:
            report = await build_asset_health_assessment(session, asset.asset_code)
            report = await overlay_assessment_with_latest_predictions(session, asset.asset_code, report)
            public = apply_numeric_assessment(report)
            rows.append(
                {
                    "asset_code": asset.asset_code,
                    "name": asset.name,
                    "category": asset.asset_type,
                    "health_score": public["health_score"],
                    "risk_score": public["risk_score"],
                    "risk_level": public["risk_level"],
                    "confidence": public["confidence"],
                    "rul_years": public["rul_years"],
                    "prediction_basis": public["prediction_basis"],
                    "health_basis": public["health_basis"],
                    "risk_basis": public["risk_basis"],
                    "rul_basis": public["rul_basis"],
                    "features_used_count": len(public["features_used"]),
                    "features_missing_count": len(public["features_missing"]),
                }
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/reports/SIMRAS_ALL_ASSET_ASSESSMENTS.csv"),
    )
    args = parser.parse_args()
    count = asyncio.run(export(args.output))
    print(f"exported={count} path={args.output}")


if __name__ == "__main__":
    main()
