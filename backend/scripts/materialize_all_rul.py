from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.entities import Asset, Prediction
from app.services.twin_service import build_twin


MODEL_VERSION = "simras_experimental_rul_proxy_v2"
FEATURE_VERSION = "ap_multi_asset_state_v3"



def compact_predicted_class(status: str) -> str:
    mapping = {
        "EXPERIMENTAL_ASSET_DESIGN_LIFE": "ASSET_DESIGN_LIFE",
        "EXPERIMENTAL_CLASS_PLANNING_HORIZON": "CLASS_PLANNING_HORIZON",
        "EXPERIMENTAL_HEALTH_ONLY_CLASS_HORIZON": "HEALTH_ONLY_CLASS_HORIZON",
        "INSUFFICIENT_INPUTS": "INSUFFICIENT_INPUTS",
    }

    value = mapping.get(status)
    if value is not None:
        return value

    cleaned = (
        status
        .replace("EXPERIMENTAL_", "EXP_")
        .replace("PLANNING_", "PLAN_")
    )
    return cleaned[:30]

async def main() -> None:
    async with SessionLocal() as session:
        assets = (
            await session.execute(
                select(Asset).order_by(Asset.id)
            )
        ).scalars().all()

        await session.execute(
            delete(Prediction).where(
                Prediction.target == "rul",
                Prediction.model_version == MODEL_VERSION,
            )
        )

        numeric = 0
        unavailable = 0
        by_type: dict[str, dict[str, int]] = {}

        for index, asset in enumerate(assets, start=1):
            twin = await build_twin(session, asset.asset_code)
            ai = twin["ai"]

            value = ai.get("remaining_life_years")
            status = str(
                ai.get("rul_status")
                or "INSUFFICIENT_INPUTS"
            )

            kind = str(asset.asset_type or "unknown")

            bucket = by_type.setdefault(
                kind,
                {"total": 0, "numeric": 0},
            )
            bucket["total"] += 1

            if value is None:
                unavailable += 1
            else:
                numeric += 1
                bucket["numeric"] += 1

            session.add(
                Prediction(
                    asset_id=asset.id,
                    prediction_time=datetime.now(UTC),
                    target="rul",
                    value=value,
                    predicted_class=compact_predicted_class(status),
                    lower_bound=ai.get("rul_lower_bound"),
                    upper_bound=ai.get("rul_upper_bound"),
                    confidence_score=ai.get("rul_confidence"),
                    model_version=MODEL_VERSION,
                    feature_version=FEATURE_VERSION,
                    status="EXPERIMENTAL_DECISION_SUPPORT",
                    factors=[
                        str(ai.get("rul_basis") or ""),
                        str(ai.get("rul_method") or ""),
                        (
                            "Not an official structural remaining-life "
                            "or safety rating"
                        ),
                    ],
                )
            )

            if index % 25 == 0:
                print(f"processed {index}/{len(assets)}")

        await session.commit()

        print("=" * 72)
        print("ALL-ASSET RUL MATERIALISATION")
        print("=" * 72)
        print("total_assets:", len(assets))
        print("numeric_rul:", numeric)
        print("unavailable:", unavailable)

        for kind in sorted(by_type):
            bucket = by_type[kind]
            print(
                f"{kind}: "
                f"{bucket['numeric']}/{bucket['total']} numeric"
            )


if __name__ == "__main__":
    asyncio.run(main())