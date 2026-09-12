import os
import re
import json
import math
import asyncio
import pandas as pd

from pathlib import Path
from difflib import SequenceMatcher
from collections import defaultdict
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


ROOT = Path("/app")

MATCH_FILE = (
    ROOT
    / "data"
    / "processed"
    / "dam_barrage"
    / "AP_HYDROLOGY_ASSET_MATCHES.csv"
)

OUT_FILE = (
    ROOT
    / "data"
    / "processed"
    / "dam_barrage"
    / "AP_HYDROLOGY_MATCH_RECOVERY.csv"
)

REPORT_FILE = (
    ROOT
    / "reports"
    / "STEP2B_MATCH_RECOVERY.txt"
)


def norm(x):
    if x is None:
        return ""

    s = str(x).lower()

    s = re.sub(
        r"\b("
        r"dam|reservoir|barrage|project|scheme|"
        r"anicut|anicut|tank|lake|major|medium"
        r")\b",
        " ",
        s,
    )

    s = s.replace("&", " and ")

    s = re.sub(
        r"[^a-z0-9]+",
        " ",
        s
    )

    return re.sub(
        r"\s+",
        " ",
        s
    ).strip()


def sim(a, b):
    a = norm(a)
    b = norm(b)

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


def haversine(lat1, lon1, lat2, lon2):

    try:
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)
    except Exception:
        return None

    r = 6371.0088

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dp = math.radians(
        lat2 - lat1
    )

    dl = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(dp / 2) ** 2
        +
        math.cos(p1)
        * math.cos(p2)
        * math.sin(dl / 2) ** 2
    )

    return (
        2
        * r
        * math.atan2(
            math.sqrt(a),
            math.sqrt(1-a)
        )
    )


async def main():

    if not MATCH_FILE.exists():
        raise RuntimeError(
            f"Missing previous Step 2 file: {MATCH_FILE}"
        )

    df = pd.read_csv(
        MATCH_FILE,
        low_memory=False
    )

    unmatched = df[
        df["match_status"]
        == "UNMATCHED"
    ].copy()

    url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("POSTGRES_URL")
    )

    if url.startswith("postgresql://"):
        url = url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1
        )

    engine = create_async_engine(
        url,
        pool_pre_ping=True
    )

    aliases = defaultdict(set)
    rivers = defaultdict(set)

    async with engine.connect() as c:

        cols = {
            r[0]
            for r in (
                await c.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema='public'
                      AND table_name='assets'
                """))
            )
        }

        type_col = next(
            x for x in [
                "asset_type",
                "type",
                "infrastructure_type"
            ]
            if x in cols
        )

        select_cols = [
            x for x in [
                "id",
                "asset_code",
                "name",
                type_col,
                "latitude",
                "longitude",
                "district"
            ]
            if x in cols
        ]

        qcols = ",".join(
            f'"{x}"'
            for x in select_cols
        )

        assets = [
            dict(r)
            for r in (
                await c.execute(
                    text(f"""
                        SELECT {qcols}
                        FROM public.assets
                        WHERE UPPER(
                            CAST("{type_col}" AS TEXT)
                        ) IN ('DAM','BARRAGE')
                    """)
                )
            ).mappings()
        ]

        asset_ids = {
            a["id"]
            for a in assets
        }

        for a in assets:
            aliases[a["id"]].add(
                str(a.get("name") or "")
            )

            aliases[a["id"]].add(
                str(a.get("asset_code") or "")
            )

        tables = {
            r[0]
            for r in (
                await c.execute(text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema='public'
                """))
            )
        }

        if "official_evidence" in tables:

            rows = (
                await c.execute(text("""
                    SELECT
                        asset_id,
                        text_value,
                        extraction_metadata
                    FROM public.official_evidence
                    WHERE asset_id IS NOT NULL
                """))
            ).mappings()

            for row in rows:

                aid = row["asset_id"]

                if aid not in asset_ids:
                    continue

                if row.get("text_value"):
                    aliases[aid].add(
                        str(row["text_value"])
                    )

                meta = row.get(
                    "extraction_metadata"
                )

                if not isinstance(meta, dict):
                    continue

                props = meta.get(
                    "properties",
                    {}
                )

                if not isinstance(props, dict):
                    continue

                for key in [
                    "dm_name",
                    "strucode",
                    "nrld_no",
                    "dm_ncity"
                ]:

                    val = props.get(key)

                    if val:
                        aliases[aid].add(
                            str(val)
                        )

                river = props.get(
                    "rivcode"
                )

                if river:
                    rivers[aid].add(
                        str(river)
                    )

    recovery = []

    for _, src in unmatched.iterrows():

        best = None

        source_name = str(
            src.get("source_name") or ""
        )

        slat = src.get(
            "latitude"
        )

        slon = src.get(
            "longitude"
        )

        for asset in assets:

            aid = asset["id"]

            alias_score = max(
                [
                    sim(
                        source_name,
                        x
                    )
                    for x in aliases[aid]
                    if x
                ]
                or [0]
            )

            river_score = max(
                [
                    sim(
                        source_name,
                        r
                    )
                    for r in rivers[aid]
                    if r
                ]
                or [0]
            )

            dist = haversine(
                slat,
                slon,
                asset.get("latitude"),
                asset.get("longitude"),
            )

            spatial = 0

            if dist is not None:

                if dist <= 0.5:
                    spatial = 1.00

                elif dist <= 1:
                    spatial = 0.98

                elif dist <= 2:
                    spatial = 0.95

                elif dist <= 5:
                    spatial = 0.90

                elif dist <= 10:
                    spatial = 0.75

                elif dist <= 20:
                    spatial = 0.55

            # Prefer spatial + reasonable name evidence.
            if (
                spatial >= 0.90
                and alias_score >= 0.50
            ):
                score = (
                    0.55 * spatial
                    + 0.45 * alias_score
                )

                method = "COORDINATE_PLUS_ALIAS"

            elif alias_score >= 0.92:
                score = alias_score

                method = "STRONG_ALIAS"

            elif (
                spatial >= 0.95
                and river_score >= 0.50
            ):
                score = (
                    0.70 * spatial
                    + 0.30 * river_score
                )

                method = "COORDINATE_PLUS_RIVER"

            else:
                score = max(
                    alias_score,
                    0.65 * spatial
                    + 0.35 * alias_score
                )

                method = "REVIEW"

            candidate = {
                "score": score,
                "alias_score": alias_score,
                "river_score": river_score,
                "distance_km": dist,
                "method": method,
                "asset": asset
            }

            if (
                best is None
                or candidate["score"]
                > best["score"]
            ):
                best = candidate

        if best is None:
            continue

        if best["score"] >= 0.90:
            status = "RECOVER_HIGH"

        elif best["score"] >= 0.82:
            status = "RECOVER_REVIEW"

        else:
            status = "STILL_UNMATCHED"

        recovery.append({
            "dataset":
                src.get("dataset"),

            "source_name":
                source_name,

            "source_code":
                src.get("source_code"),

            "latitude":
                slat,

            "longitude":
                slon,

            "candidate_asset_id":
                best["asset"]["id"],

            "candidate_asset_code":
                best["asset"].get(
                    "asset_code"
                ),

            "candidate_asset_name":
                best["asset"].get(
                    "name"
                ),

            "match_score":
                round(
                    best["score"],
                    4
                ),

            "alias_score":
                round(
                    best["alias_score"],
                    4
                ),

            "river_score":
                round(
                    best["river_score"],
                    4
                ),

            "distance_km":
                (
                    round(
                        best["distance_km"],
                        3
                    )
                    if best[
                        "distance_km"
                    ] is not None
                    else None
                ),

            "method":
                best["method"],

            "recovery_status":
                status
        })

    result = pd.DataFrame(
        recovery
    )

    result.to_csv(
        OUT_FILE,
        index=False
    )

    high = int(
        (
            result[
                "recovery_status"
            ]
            == "RECOVER_HIGH"
        ).sum()
    )

    review = int(
        (
            result[
                "recovery_status"
            ]
            == "RECOVER_REVIEW"
        ).sum()
    )

    still = int(
        (
            result[
                "recovery_status"
            ]
            == "STILL_UNMATCHED"
        ).sum()
    )

    recovered_assets = set(
        result.loc[
            result[
                "recovery_status"
            ].isin([
                "RECOVER_HIGH",
                "RECOVER_REVIEW"
            ]),
            "candidate_asset_id"
        ].dropna()
    )

    previous_assets = set(
        df.loc[
            df[
                "match_status"
            ] != "UNMATCHED",
            "asset_id"
        ].dropna()
    )

    combined = (
        previous_assets
        | recovered_assets
    )

    lines = [
        "=" * 90,
        "SIMRAS STEP 2B - HYDROLOGY MATCH RECOVERY",
        "=" * 90,
        f"Previous unmatched entities : {len(unmatched)}",
        f"High recoverable            : {high}",
        f"Review recoverable          : {review}",
        f"Still unmatched             : {still}",
        "",
        f"Previous matched assets     : {len(previous_assets)}",
        f"Potential combined assets   : {len(combined)}",
        f"Potential asset coverage    : {len(combined)/177*100:.2f}%",
        "",
        f"Report CSV                  : {OUT_FILE}",
        "=" * 90,
    ]

    print(
        "\n".join(lines)
    )

    REPORT_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    await engine.dispose()


asyncio.run(main())
