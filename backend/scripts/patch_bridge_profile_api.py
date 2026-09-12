from pathlib import Path
import re

path = Path("/repo/backend/app/api/routes/assets.py")
src = path.read_text(encoding="utf-8-sig")


# ------------------------------------------------------------
# HTTPException
# ------------------------------------------------------------

src = src.replace(
    "from fastapi import APIRouter, Depends, Query",
    "from fastapi import APIRouter, Depends, HTTPException, Query",
)


# ------------------------------------------------------------
# sqlalchemy text()
# ------------------------------------------------------------

match = re.search(
    r"from sqlalchemy import ([^\n]+)",
    src,
)

if not match:
    raise RuntimeError(
        "SQLAlchemy import line not found"
    )

parts = [
    p.strip()
    for p in match.group(1).split(",")
]

if "text" not in parts:
    parts.append("text")

replacement = (
    "from sqlalchemy import "
    + ", ".join(parts)
)

src = (
    src[:match.start()]
    + replacement
    + src[match.end():]
)


# ------------------------------------------------------------
# Bridge profile endpoint
# ------------------------------------------------------------

if '("/{asset_code}/bridge-profile")' not in src:

    marker = (
        '@router.get("/{asset_code}", '
        'response_model=AssetSummary)'
    )

    if marker not in src:
        raise RuntimeError(
            "Asset detail route marker not found"
        )

    endpoint = r'''
@router.get("/{asset_code}/bridge-profile")
async def get_bridge_profile(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
):
    asset = (
        await session.execute(
            select(Asset).where(
                Asset.asset_code == asset_code
            )
        )
    ).scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail="Asset not found",
        )

    if str(asset.asset_type).lower() != "bridge":
        raise HTTPException(
            status_code=400,
            detail="Asset is not a bridge",
        )

    profile = await session.scalar(
        text("""
            SELECT
                row_to_json(p)::text
            FROM
                public.bridge_digital_twin_profiles p
            WHERE
                p.asset_id = :asset_id
            LIMIT 1
        """),
        {
            "asset_id": asset.id
        },
    )

    engineering = await session.scalar(
        text("""
            SELECT
                row_to_json(e)::text
            FROM
                public.bridge_engineering_features_verified e
            WHERE
                e.asset_id = :asset_id
            LIMIT 1
        """),
        {
            "asset_id": asset.id
        },
    )

    report = await session.scalar(
        text("""
            SELECT
                row_to_json(r)::text
            FROM
                public.bridge_report_readiness r
            WHERE
                r.asset_id = :asset_id
            LIMIT 1
        """),
        {
            "asset_id": asset.id
        },
    )

    return {
        "asset": {
            "id": asset.id,
            "asset_code": asset.asset_code,
            "name": asset.name,
            "district": asset.district,
            "asset_type": asset.asset_type,
            "identity_status": asset.identity_status,
            "is_estimated": asset.is_estimated,
        },
        "profile": profile,
        "engineering": engineering,
        "report": report,
    }


'''

    src = src.replace(
        marker,
        endpoint + marker,
        1,
    )

path.write_text(
    src,
    encoding="utf-8",
    newline="\n",
)

print(
    "[PATCHED] /assets/{asset_code}/bridge-profile"
)