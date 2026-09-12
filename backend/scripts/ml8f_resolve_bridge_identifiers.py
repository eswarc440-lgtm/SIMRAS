import csv
import json
import os
import re
import asyncio
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


INPUT = Path(
    "/tmp/ml8f/input.csv"
)

OUTDIR = Path(
    "/tmp/ml8f/output"
)

OUTDIR.mkdir(
    parents=True,
    exist_ok=True,
)


def normalize(value):
    if value is None:
        return ""

    value = str(value).upper()

    value = re.sub(
        r"[^A-Z0-9]+",
        " ",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def split_values(value):
    if not value:
        return []

    return [
        item.strip()
        for item in str(value).split(";")
        if item.strip()
    ]


def async_url(value):
    if value.startswith(
        "postgresql://"
    ):
        return value.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1,
        )

    return value


async def main():

    with INPUT.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        rows = list(
            csv.DictReader(handle)
        )


    print(
        "IDENTIFIER_CANDIDATES =",
        len(rows),
    )


    engine = create_async_engine(
        async_url(
            os.environ[
                "DATABASE_URL"
            ]
        )
    )


    resolved = []


    async with engine.connect() as conn:

        catalog_exists = await conn.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema='public'
                    AND table_name='bridge_osm_catalog'
                )
                """
            )
        )


        profile_exists = await conn.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema='public'
                    AND table_name='bridge_digital_twin_profiles'
                )
                """
            )
        )


        print(
            "BRIDGE_OSM_CATALOG =",
            catalog_exists,
        )

        print(
            "BRIDGE_TWIN_PROFILES =",
            profile_exists,
        )


        for index, row in enumerate(
            rows,
            start=1,
        ):

            identifiers = split_values(
                row.get(
                    "bridge_identifiers"
                )
            )

            excerpt = (
                row.get(
                    "page_text_excerpt"
                )
                or ""
            )

            normalized_excerpt = normalize(
                excerpt
            )


            print()
            print(
                "================================================"
            )

            print(
                "CANDIDATE",
                index,
            )

            print(
                "DOCUMENT =",
                row.get(
                    "document"
                ),
            )

            print(
                "PAGE =",
                row.get(
                    "page"
                ),
            )

            print(
                "IDENTIFIERS =",
                identifiers,
            )

            print(
                "CONDITION =",
                row.get(
                    "condition_words"
                ),
            )

            print(
                "RATING =",
                row.get(
                    "rating_values"
                ),
            )

            print(
                "DEFECTS =",
                row.get(
                    "defect_words"
                ),
            )


            matches = []


            # ================================================
            # Exact / conservative search in canonical assets
            # ================================================

            for identifier in identifiers:

                token = normalize(
                    identifier
                )

                if not token:
                    continue


                asset_rows = (
                    await conn.execute(
                        text(
                            """
                            SELECT
                                id,
                                asset_code,
                                name,
                                district,
                                built_year,
                                identity_status
                            FROM public.assets
                            WHERE
                                LOWER(
                                    CAST(asset_type AS TEXT)
                                )='bridge'
                                AND asset_code LIKE 'AP_BR_%'
                                AND (
                                    UPPER(name) LIKE :needle
                                    OR UPPER(asset_code) LIKE :needle
                                )
                            LIMIT 25
                            """
                        ),
                        {
                            "needle":
                                "%"
                                + token.replace(
                                    " ",
                                    "%"
                                )
                                + "%",
                        },
                    )
                ).mappings().all()


                for asset in asset_rows:

                    matches.append(
                        {
                            "method":
                                "CANONICAL_ASSET_TEXT",

                            "identifier":
                                identifier,

                            "asset_id":
                                asset[
                                    "id"
                                ],

                            "asset_code":
                                asset[
                                    "asset_code"
                                ],

                            "name":
                                asset[
                                    "name"
                                ],

                            "district":
                                asset[
                                    "district"
                                ],

                            "identity_status":
                                str(
                                    asset[
                                        "identity_status"
                                    ]
                                ),
                        }
                    )


                if catalog_exists:

                    catalog_rows = (
                        await conn.execute(
                            text(
                                """
                                SELECT
                                    canonical_asset_id,
                                    asset_code,
                                    display_name,
                                    source_name,
                                    ref,
                                    highway,
                                    railway,
                                    latitude,
                                    longitude,
                                    identity_status
                                FROM public.bridge_osm_catalog
                                WHERE
                                    UPPER(
                                        COALESCE(
                                            ref,
                                            ''
                                        )
                                    ) LIKE :needle
                                    OR UPPER(
                                        COALESCE(
                                            display_name,
                                            ''
                                        )
                                    ) LIKE :needle
                                    OR UPPER(
                                        COALESCE(
                                            source_name,
                                            ''
                                        )
                                    ) LIKE :needle
                                LIMIT 25
                                """
                            ),
                            {
                                "needle":
                                    "%"
                                    + token.replace(
                                        " ",
                                        "%"
                                    )
                                    + "%",
                            },
                        )
                    ).mappings().all()


                    for item in catalog_rows:

                        matches.append(
                            {
                                "method":
                                    "OSM_CATALOG_TEXT",

                                "identifier":
                                    identifier,

                                "asset_id":
                                    item[
                                        "canonical_asset_id"
                                    ],

                                "asset_code":
                                    item[
                                        "asset_code"
                                    ],

                                "name":
                                    item[
                                        "display_name"
                                    ]
                                    or item[
                                        "source_name"
                                    ],

                                "district":
                                    None,

                                "identity_status":
                                    str(
                                        item[
                                            "identity_status"
                                        ]
                                    ),

                                "ref":
                                    item[
                                        "ref"
                                    ],

                                "highway":
                                    item[
                                        "highway"
                                    ],

                                "railway":
                                    item[
                                        "railway"
                                    ],

                                "latitude":
                                    item[
                                        "latitude"
                                    ],

                                "longitude":
                                    item[
                                        "longitude"
                                    ],
                            }
                        )


            # ================================================
            # Remove duplicate proposed matches
            # ================================================

            unique_matches = []

            seen = set()

            for item in matches:

                key = (
                    item.get(
                        "asset_code"
                    ),
                    item.get(
                        "method"
                    ),
                    item.get(
                        "identifier"
                    ),
                )

                if key in seen:
                    continue

                seen.add(key)

                unique_matches.append(
                    item
                )


            # ================================================
            # Conservative status
            # ================================================

            asset_codes = sorted(
                {
                    item.get(
                        "asset_code"
                    )
                    for item
                    in unique_matches
                    if item.get(
                        "asset_code"
                    )
                }
            )


            if len(
                asset_codes
            ) == 1:

                resolution_status = (
                    "SINGLE_TEXT_MATCH_REQUIRES_REVIEW"
                )

            elif len(
                asset_codes
            ) > 1:

                resolution_status = (
                    "AMBIGUOUS_MULTIPLE_MATCHES"
                )

            else:

                resolution_status = (
                    "NO_CANONICAL_MATCH"
                )


            print(
                "MATCHED_ASSET_CODES =",
                asset_codes,
            )

            print(
                "RESOLUTION_STATUS =",
                resolution_status,
            )


            for item in unique_matches[:15]:

                print(
                    "  ",
                    item.get(
                        "asset_code"
                    ),
                    "|",
                    item.get(
                        "name"
                    ),
                    "|",
                    item.get(
                        "method"
                    ),
                )


            resolved.append(
                {
                    "document":
                        row.get(
                            "document"
                        ),

                    "page":
                        row.get(
                            "page"
                        ),

                    "bridge_identifiers":
                        row.get(
                            "bridge_identifiers"
                        ),

                    "condition_words":
                        row.get(
                            "condition_words"
                        ),

                    "rating_values":
                        row.get(
                            "rating_values"
                        ),

                    "defect_words":
                        row.get(
                            "defect_words"
                        ),

                    "resolution_status":
                        resolution_status,

                    "matched_asset_codes":
                        "; ".join(
                            asset_codes
                        ),

                    "match_count":
                        len(
                            asset_codes
                        ),

                    "candidate_training_label":
                        False,

                    "verified_for_ml":
                        False,

                    "database_modified":
                        False,

                    "matches_json":
                        json.dumps(
                            unique_matches,
                            default=str,
                        ),

                    "page_text_excerpt":
                        excerpt,
                }
            )


    await engine.dispose()


    output_csv = (
        OUTDIR
        / "ml8f_identifier_resolution.csv"
    )

    if resolved:

        with output_csv.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as handle:

            writer = csv.DictWriter(
                handle,
                fieldnames=list(
                    resolved[0].keys()
                ),
            )

            writer.writeheader()

            writer.writerows(
                resolved
            )


    single = sum(
        1
        for row in resolved
        if row[
            "resolution_status"
        ]
        == "SINGLE_TEXT_MATCH_REQUIRES_REVIEW"
    )


    ambiguous = sum(
        1
        for row in resolved
        if row[
            "resolution_status"
        ]
        == "AMBIGUOUS_MULTIPLE_MATCHES"
    )


    unmatched = sum(
        1
        for row in resolved
        if row[
            "resolution_status"
        ]
        == "NO_CANONICAL_MATCH"
    )


    summary = {
        "identifier_candidates":
            len(
                resolved
            ),

        "single_match_requires_review":
            single,

        "ambiguous_matches":
            ambiguous,

        "no_match":
            unmatched,

        "training_labels_created":
            0,

        "database_modified":
            False,
    }


    (
        OUTDIR
        / "ml8f_summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )


    print()
    print(
        "================================================"
    )

    print(
        "ML-8F IDENTIFIER RESOLUTION SUMMARY"
    )

    print(
        "================================================"
    )

    print(
        "IDENTIFIER_CANDIDATES =",
        len(
            resolved
        ),
    )

    print(
        "SINGLE_MATCH_REQUIRES_REVIEW =",
        single,
    )

    print(
        "AMBIGUOUS_MATCHES =",
        ambiguous,
    )

    print(
        "NO_CANONICAL_MATCH =",
        unmatched,
    )

    print(
        "TRAINING_LABELS_CREATED = 0"
    )

    print(
        "DATABASE_MODIFIED = NO"
    )

    print()
    print(
        "ML8F_IDENTIFIER_RESOLUTION=PASS"
    )


asyncio.run(
    main()
)