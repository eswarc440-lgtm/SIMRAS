from __future__ import annotations

import os
import csv
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


ROOT = Path("/app")

REPORT = (
    ROOT
    / "reports"
    / "STEP6C1_BRIDGE_CATALOG_DISCOVERY.txt"
)

REPORT_JSON = (
    ROOT
    / "reports"
    / "STEP6C1_BRIDGE_CATALOG_DISCOVERY.json"
)


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def qident(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def candidate_score(table_name: str, columns: list[str]) -> int:

    t = table_name.lower()
    cols = {c.lower() for c in columns}

    score = 0

    if "bridge" in t:
        score += 10

    if "osm" in t:
        score += 4

    if "map" in t:
        score += 2

    if "feature" in t:
        score += 2

    if "way" in t:
        score += 2

    strong_cols = {
        "bridge",
        "bridge_type",
        "asset_type",
        "infrastructure_type",
        "osm_id",
        "osm_way_id",
        "highway",
        "railway",
        "geometry",
        "geom",
        "name",
    }

    score += len(
        cols.intersection(strong_cols)
    )

    return score


async def get_columns(conn, schema, table):

    result = await conn.execute(
        text("""
            SELECT
                column_name,
                data_type
            FROM information_schema.columns
            WHERE table_schema=:schema
              AND table_name=:table
            ORDER BY ordinal_position
        """),
        {
            "schema": schema,
            "table": table,
        }
    )

    return [
        {
            "name": r["column_name"],
            "type": r["data_type"],
        }
        for r in result.mappings()
    ]


async def estimated_rows(conn, schema, table):

    try:

        result = await conn.execute(
            text("""
                SELECT
                    COALESCE(c.reltuples,0)::BIGINT
                FROM pg_class c
                JOIN pg_namespace n
                  ON n.oid=c.relnamespace
                WHERE n.nspname=:schema
                  AND c.relname=:table
                LIMIT 1
            """),
            {
                "schema": schema,
                "table": table,
            }
        )

        value = result.scalar()

        return int(value or 0)

    except Exception:
        return None


async def exact_count(conn, schema, table):

    try:

        sql = (
            f"SELECT COUNT(*) "
            f"FROM {qident(schema)}.{qident(table)}"
        )

        result = await conn.execute(
            text(sql)
        )

        return int(
            result.scalar()
            or 0
        )

    except Exception:
        return None


async def sample_rows(conn, schema, table, columns):

    safe_columns = [
        c["name"]
        for c in columns
        if c["type"] not in {
            "USER-DEFINED"
        }
    ][:15]

    if not safe_columns:
        return []

    col_sql = ", ".join(
        qident(c)
        for c in safe_columns
    )

    sql = (
        f"SELECT {col_sql} "
        f"FROM {qident(schema)}.{qident(table)} "
        f"LIMIT 3"
    )

    try:

        result = await conn.execute(
            text(sql)
        )

        rows = []

        for r in result.mappings():

            clean = {}

            for k, v in dict(r).items():

                if v is None:
                    clean[k] = None

                elif isinstance(
                    v,
                    (
                        str,
                        int,
                        float,
                        bool
                    )
                ):
                    clean[k] = v

                else:
                    clean[k] = str(v)[:300]

            rows.append(clean)

        return rows

    except Exception:
        return []


def scan_bridge_files():

    roots = [
        ROOT / "data",
        ROOT / "reports",
    ]

    found = []

    for base in roots:

        if not base.exists():
            continue

        for path in base.rglob("*"):

            if not path.is_file():
                continue

            relative = str(
                path.relative_to(ROOT)
            )

            lower = relative.lower()

            if "bridge" not in lower:
                continue

            try:
                size = path.stat().st_size
            except Exception:
                size = 0

            record = {
                "path": relative,
                "size_mb": round(
                    size / 1024 / 1024,
                    3
                ),
                "suffix": path.suffix.lower(),
                "header": None,
            }

            if (
                path.suffix.lower() == ".csv"
                and size > 0
            ):

                try:

                    with path.open(
                        "r",
                        encoding="utf-8-sig",
                        errors="ignore",
                        newline=""
                    ) as f:

                        reader = csv.reader(f)

                        header = next(
                            reader,
                            []
                        )

                        record["header"] = header[
                            :40
                        ]

                except Exception:
                    pass

            found.append(
                record
            )

    return sorted(
        found,
        key=lambda x: (
            -x["size_mb"],
            x["path"]
        )
    )


async def main():

    db_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("POSTGRES_URL")
    )

    if not db_url:

        raise RuntimeError(
            "DATABASE_URL unavailable"
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

        # ----------------------------------------------------
        # Current canonical bridge count
        # ----------------------------------------------------

        asset_cols_result = await conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name='assets'
            """)
        )

        asset_cols = {
            r[0]
            for r in asset_cols_result
        }

        type_col = next(
            (
                c
                for c in [
                    "asset_type",
                    "type",
                    "infrastructure_type"
                ]
                if c in asset_cols
            ),
            None
        )

        if not type_col:
            raise RuntimeError(
                "assets type column not found"
            )

        canonical_result = await conn.execute(
            text(f"""
                SELECT COUNT(*)
                FROM public.assets
                WHERE UPPER(
                    CAST(
                        "{type_col}"
                        AS TEXT
                    )
                )='BRIDGE'
            """)
        )

        canonical_bridge_count = int(
            canonical_result.scalar()
            or 0
        )

        # ----------------------------------------------------
        # Discover public tables/views
        # ----------------------------------------------------

        table_result = await conn.execute(
            text("""
                SELECT
                    table_schema,
                    table_name,
                    table_type
                FROM information_schema.tables
                WHERE table_schema='public'
                ORDER BY table_name
            """)
        )

        tables = [
            dict(r)
            for r in table_result.mappings()
        ]

        candidates = []

        excluded = {
            "bridge_engineering_evidence_verified",
            "bridge_engineering_features_verified",
        }

        for info in tables:

            schema = info[
                "table_schema"
            ]

            table = info[
                "table_name"
            ]

            if table in excluded:
                continue

            columns_meta = await get_columns(
                conn,
                schema,
                table
            )

            column_names = [
                x["name"]
                for x in columns_meta
            ]

            score = candidate_score(
                table,
                column_names
            )

            # Keep likely ETL/GIS/catalog sources.
            interesting = (
                score >= 5
                or "bridge" in table.lower()
                or any(
                    x.lower() in {
                        "bridge",
                        "bridge_type",
                        "osm_id",
                        "osm_way_id"
                    }
                    for x in column_names
                )
            )

            if not interesting:
                continue

            estimate = await estimated_rows(
                conn,
                schema,
                table
            )

            # Exact count only for candidate tables.
            count = await exact_count(
                conn,
                schema,
                table
            )

            samples = await sample_rows(
                conn,
                schema,
                table,
                columns_meta
            )

            candidates.append({

                "schema":
                    schema,

                "table":
                    table,

                "table_type":
                    info["table_type"],

                "score":
                    score,

                "estimated_rows":
                    estimate,

                "exact_rows":
                    count,

                "columns":
                    columns_meta,

                "sample_rows":
                    samples,
            })

    await engine.dispose()

    candidates = sorted(
        candidates,
        key=lambda x: (
            -x["score"],
            -(
                x["exact_rows"]
                or 0
            ),
            x["table"]
        )
    )

    files = scan_bridge_files()

    # --------------------------------------------------------
    # Select likely promotion candidates
    # --------------------------------------------------------

    likely = []

    for c in candidates:

        table_lower = c[
            "table"
        ].lower()

        cols = {
            x["name"].lower()
            for x in c[
                "columns"
            ]
        }

        has_identity = bool(
            cols.intersection(
                {
                    "osm_id",
                    "osm_way_id",
                    "id",
                    "asset_id",
                    "feature_id",
                }
            )
        )

        has_geometry = bool(
            cols.intersection(
                {
                    "geom",
                    "geometry",
                    "latitude",
                    "longitude",
                    "lat",
                    "lon",
                }
            )
        )

        has_bridge_signal = (
            "bridge" in table_lower
            or "bridge" in cols
            or "bridge_type" in cols
        )

        if (
            has_bridge_signal
            and has_identity
            and (
                has_geometry
                or "name" in cols
            )
        ):
            likely.append(
                c["table"]
            )

    summary = {

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "canonical_bridge_assets":
            canonical_bridge_count,

        "candidate_database_sources":
            len(candidates),

        "likely_promotion_sources":
            likely,

        "bridge_related_files":
            len(files),

        "database_candidates":
            candidates,

        "files":
            files,
    }

    REPORT_JSON.write_text(
        json.dumps(
            summary,
            indent=2,
            default=str
        ),
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # Human-readable report
    # --------------------------------------------------------

    lines = [
        "=" * 115,
        "SIMRAS STEP 6C.1 - STATEWIDE BRIDGE CATALOG DISCOVERY RESULT",
        "=" * 115,
        "",
        f"Current canonical bridge assets : {canonical_bridge_count}",
        f"Candidate DB source tables      : {len(candidates)}",
        f"Likely promotion source tables  : {len(likely)}",
        f"Bridge-related repository files : {len(files)}",
        "",
    ]

    if likely:

        lines.append(
            "LIKELY PROMOTION SOURCES:"
        )

        for table in likely:
            lines.append(
                f"  - public.{table}"
            )

        lines.append("")

    lines.append(
        "DATABASE CANDIDATES:"
    )

    for c in candidates:

        names = [
            x["name"]
            for x in c[
                "columns"
            ]
        ]

        lines.append("")

        lines.append(
            f"public.{c['table']} | "
            f"score={c['score']} | "
            f"rows={c['exact_rows']} | "
            f"type={c['table_type']}"
        )

        lines.append(
            "  columns: "
            + ", ".join(
                names[:30]
            )
        )

        for index, sample in enumerate(
            c["sample_rows"],
            start=1
        ):

            preview = json.dumps(
                sample,
                default=str
            )

            if len(preview) > 900:
                preview = preview[:900] + "..."

            lines.append(
                f"  sample{index}: {preview}"
            )

    lines += [
        "",
        "BRIDGE-RELATED FILES:",
    ]

    for f in files[:60]:

        line = (
            f"  {f['path']} | "
            f"{f['size_mb']} MB"
        )

        if f.get(
            "header"
        ):

            line += (
                " | columns="
                + ",".join(
                    f["header"][:20]
                )
            )

        lines.append(
            line
        )

    lines += [
        "",
        "NEXT DECISION:",
        "  No bridge rows have been promoted in this step.",
        "  The highest-quality statewide ETL source will be selected",
        "  from the database/files above and reconciled against the",
        "  two verified anchor bridges before canonical promotion.",
        "",
        "IMPORTANT:",
        "  Do not train statewide AP bridge ML until the canonical",
        "  bridge catalog and real validation-label strategy are locked.",
        "=" * 115,
    ]

    REPORT.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    print(
        "\n".join(lines)
    )


asyncio.run(main())
