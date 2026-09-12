import os
import re
import csv
import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


ROOT = Path("/app")

OUT = (
    ROOT
    / "data"
    / "processed"
    / "airport"
    / "AP_AIRPORT_SOURCE_PLAN.csv"
)

REPORT = (
    ROOT
    / "reports"
    / "STEP4A_AP_AIRPORT_INVENTORY.txt"
)


ICAO_RULES = [

    (
        [
            "vijayawada",
            "gannavaram"
        ],
        "VOBZ",
        "Vijayawada Airport"
    ),

    (
        [
            "visakhapatnam",
            "vizag",
            "visakhapatnam airport"
        ],
        "VOVZ",
        "Visakhapatnam Airport"
    ),

    (
        [
            "rajahmundry",
            "rajamahendravaram",
            "rajahmundry airport"
        ],
        "VORY",
        "Rajahmundry Airport"
    ),

    (
        [
            "tirupati",
            "renigunta"
        ],
        "VOTP",
        "Tirupati Airport"
    ),

    (
        [
            "kadapa",
            "cuddapah"
        ],
        "VOCP",
        "Kadapa Airport"
    ),

    (
        [
            "kurnool",
            "orvakal",
            "orvakallu"
        ],
        "VOKU",
        "Kurnool Airport"
    ),

    (
        [
            "puttaparthi",
            "puttaparthy",
            "sri sathya sai",
            "sathya sai airport"
        ],
        "VOPN",
        "Sri Sathya Sai Airport"
    ),

    (
        [
            "bhogapuram",
            "bhogapuram international"
        ],
        "VOVI",
        "Bhogapuram International Airport"
    ),
]


def norm(value):

    value = str(
        value or ""
    ).lower()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


def identify(name):

    n = norm(name)

    for aliases, code, canonical in ICAO_RULES:

        for alias in aliases:

            if norm(alias) in n:

                return (
                    code,
                    canonical,
                    "AUTO_NAME_MATCH"
                )

    return (
        None,
        None,
        "UNRESOLVED"
    )


async def main():

    db_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("POSTGRES_URL")
    )

    if not db_url:
        raise RuntimeError(
            "DATABASE_URL not found"
        )

    if db_url.startswith(
        "postgresql://"
    ):

        db_url = db_url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1
        )

    engine = create_async_engine(
        db_url,
        pool_pre_ping=True
    )

    async with engine.connect() as conn:

        cols = {
            r[0]
            for r in (
                await conn.execute(
                    text("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema='public'
                          AND table_name='assets'
                    """)
                )
            )
        }

        type_col = next(
            (
                x
                for x in [
                    "asset_type",
                    "type",
                    "infrastructure_type"
                ]
                if x in cols
            ),
            None
        )

        if not type_col:
            raise RuntimeError(
                "Asset type column not found"
            )

        select_cols = [
            c
            for c in [
                "id",
                "asset_code",
                "name",
                type_col,
                "district",
                "latitude",
                "longitude",
                "built_year"
            ]
            if c in cols
        ]

        qcols = ",".join(
            f'"{c}"'
            for c in select_cols
        )

        result = await conn.execute(
            text(f"""
                SELECT {qcols}
                FROM public.assets
                WHERE UPPER(
                    CAST(
                        "{type_col}"
                        AS TEXT
                    )
                ) = 'AIRPORT'
                ORDER BY name
            """)
        )

        assets = [
            dict(row)
            for row in result.mappings().all()
        ]

    rows = []

    for asset in assets:

        code, canonical, status = identify(
            asset.get("name")
        )

        rows.append({

            "asset_id":
                asset.get("id"),

            "asset_code":
                asset.get("asset_code"),

            "asset_name":
                asset.get("name"),

            "district":
                asset.get("district"),

            "latitude":
                asset.get("latitude"),

            "longitude":
                asset.get("longitude"),

            "built_year":
                asset.get("built_year"),

            "icao_code":
                code,

            "aai_canonical_name":
                canonical,

            "mapping_status":
                status,

            "source_authority":
                "Airports Authority of India",

            "source_system":
                "AIM India / eAIP",

            "eaip_required":
                "YES" if code else "REVIEW",
        })

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUT.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=rows[0].keys()
            if rows
            else [
                "asset_id",
                "asset_code",
                "asset_name",
                "icao_code"
            ]
        )

        writer.writeheader()

        writer.writerows(
            rows
        )

    matched = sum(
        1
        for r in rows
        if r[
            "mapping_status"
        ] == "AUTO_NAME_MATCH"
    )

    unresolved = len(rows) - matched

    lines = [
        "=" * 95,
        "SIMRAS STEP 4A - ANDHRA PRADESH AIRPORT INVENTORY",
        "=" * 95,
        "",
        f"Airport assets found       : {len(rows)}",
        f"ICAO automatically matched : {matched}",
        f"Unresolved                 : {unresolved}",
        "",
    ]

    for r in rows:

        lines.append(
            f"{r['asset_code']} | "
            f"{r['asset_name']} | "
            f"{r['icao_code']} | "
            f"{r['mapping_status']}"
        )

    lines += [
        "",
        f"Source plan: {OUT}",
        "=" * 95
    ]

    print(
        "\n".join(lines)
    )

    REPORT.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    await engine.dispose()


asyncio.run(main())
