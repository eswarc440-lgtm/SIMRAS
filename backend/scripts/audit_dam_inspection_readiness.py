from __future__ import annotations

import asyncio
import csv
import re
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import Asset
from app.services.dam_inspection_ground_truth import load_candidate_labels


OUTPUT = Path("/data/ml/ap_dam_inspection_label_readiness.csv")


def normalize(value: str) -> str:
    value = value.lower()
    value = value.replace("–", "-").replace("—", "-")
    value = re.sub(r"\b(project|reservoir|barrage|dam|complex|part|stage)\b", " ", value)
    value = re.sub(r"\b[ivx]+\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def score_match(source_name: str, asset_name: str) -> float:
    a = normalize(source_name)
    b = normalize(asset_name)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.95
    aset = set(a.split())
    bset = set(b.split())
    union = aset | bset
    return len(aset & bset) / len(union) if union else 0.0


async def main() -> None:
    labels = load_candidate_labels()

    async with SessionLocal() as session:
        assets = (
            await session.scalars(
                select(Asset).where(Asset.asset_type.in_(["dam", "barrage"]))
            )
        ).all()

    rows: list[dict] = []
    matched_asset_ids: set[int] = set()

    for label in labels:
        ranked = sorted(
            ((score_match(label["asset_name_reported"], asset.name), asset) for asset in assets),
            key=lambda item: item[0],
            reverse=True,
        )
        score, asset = ranked[0] if ranked else (0.0, None)
        matched = asset is not None and score >= 0.55
        if matched:
            matched_asset_ids.add(asset.id)

        rows.append(
            {
                "source_asset_name": label["asset_name_reported"],
                "inspection_category": label["inspection_category"],
                "matched": matched,
                "match_score": round(score, 3),
                "asset_code": asset.asset_code if matched else "",
                "registry_name": asset.name if matched else "",
                "asset_type": asset.asset_type if matched else "",
                "district": asset.district if matched else "",
                "training_eligible": label["training_eligible"],
                "reason_not_training_eligible": label["reason_not_training_eligible"],
                "source_url": label["source_url"],
                "source_page": label["source_page"],
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    trainable = [row for row in rows if row["matched"] and row["training_eligible"]]
    matched = [row for row in rows if row["matched"]]

    print("=== AP DAM/BARRAGE INSPECTION GROUND-TRUTH READINESS ===")
    print(f"Registry dams/barrages       : {len(assets)}")
    print(f"Public category candidates   : {len(rows)}")
    print(f"Candidates matched to assets : {len(matched)}")
    print(f"Unique matched assets        : {len(matched_asset_ids)}")
    print(f"Training-eligible labels     : {len(trainable)}")
    print(f"Output                       : {OUTPUT}")
    print()
    print("IMPORTANT:")
    print("Category-register rows are historical official evidence, not yet")
    print("dated physical-inspection ground truth. Training remains gated until")
    print("the underlying inspection/DSRP reports and component findings are linked.")


if __name__ == "__main__":
    asyncio.run(main())
