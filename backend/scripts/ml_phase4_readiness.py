from __future__ import annotations

import asyncio
import csv
import json
import os
from pathlib import Path

import asyncpg


ASSET_TYPES = [
    "dam",
    "barrage",
    "bridge",
    "road",
    "airport",
    "temple",
]

ENGINEERING_FIELDS = [
    "built_year",
    "design_life_years",
    "material",
    "length_m",
    "width_m",
    "height_m",
    "span_count",
    "pier_count",
    "capacity",
]

LOCATION_FIELDS = [
    "latitude",
    "longitude",
]

TABLE_KEYWORDS = {
    "dam": [
        "dam",
        "reservoir",
        "hydrology",
        "water_level",
        "storage",
    ],

    "barrage": [
        "barrage",
        "hydrology",
        "discharge",
        "velocity",
        "gate",
    ],

    "bridge": [
        "bridge",
        "inspection",
        "nbi",
        "shm",
        "vibration",
        "strain",
    ],

    "road": [
        "road",
        "highway",
        "pavement",
        "pci",
        "iri",
        "traffic",
    ],

    "airport": [
        "airport",
        "runway",
        "pavement",
        "pci",
    ],

    "temple": [
        "temple",
        "heritage",
        "crack",
        "inspection",
    ],

    "climate": [
        "weather",
        "climate",
        "rain",
        "rainfall",
        "temperature",
        "humidity",
        "wind",
        "era5",
        "nasa",
        "power",
        "imd",
    ],
}


CLIMATE_FEATURES = [
    "rain_1d",
    "rain_7d",
    "rain_30d",
    "rain_90d",
    "annual_rainfall",
    "temperature_mean",
    "temperature_max",
    "temperature_range",
    "relative_humidity",
    "wind_mean",
    "wind_max",
    "flood_exposure",
    "cyclone_exposure",
    "coastal_exposure",
]


MODEL_PLAN = {
    "dam": {
        "health": "XGBoost structural/engineering condition model",
        "risk": "XGBoost hydrology + climate operational risk model",
        "rul": "XGBoost AFT when longitudinal deterioration labels exist",
    },

    "barrage": {
        "health": "XGBoost gate/pier/foundation condition model",
        "risk": "XGBoost discharge/level/velocity/climate risk model",
        "rul": "XGBoost AFT when longitudinal condition history exists",
    },

    "bridge": {
        "health": "Bridge-specific XGBoost / existing NBI transfer pipeline",
        "risk": "XGBoost poor-condition probability + climate/SHM features",
        "rul": "XGBoost AFT when longitudinal deterioration evidence exists",
    },

    "road": {
        "health": "XGBoost PCI/IRI/distress health model",
        "risk": "XGBoost pavement deterioration risk model",
        "rul": "XGBoost AFT to resurfacing/rehabilitation threshold",
    },

    "airport": {
        "health": "XGBoost runway/taxiway pavement health model",
        "risk": "XGBoost pavement/drainage/climate deterioration model",
        "rul": "XGBoost AFT to rehabilitation threshold",
    },

    "temple": {
        "health": "XGBoost structural condition + crack/image-derived features",
        "risk": "XGBoost moisture/crack/climate deterioration risk",
        "rul": "WITHHOLD until longitudinal engineering labels exist",
    },
}


def has_value(row: dict, field: str) -> bool:
    value = row.get(field)

    return value not in (
        None,
        "",
        [],
        {},
    )


async def main():

    conn = await asyncpg.connect(
        host=os.environ.get(
            "SIMRAS_DB_HOST",
            "db",
        ),
        port=int(
            os.environ.get(
                "SIMRAS_DB_PORT",
                "5432",
            )
        ),
        user=os.environ["SIMRAS_DB_USER"],
        password=os.environ.get(
            "SIMRAS_DB_PASSWORD",
            "",
        ),
        database=os.environ["SIMRAS_DB_NAME"],
    )

    try:

        table_records = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
            ORDER BY table_name
            """
        )

        tables = [
            record["table_name"]
            for record in table_records
        ]

        asset_records = await conn.fetch(
            """
            SELECT to_jsonb(a)::text AS asset_json
            FROM public.assets a
            WHERE LOWER(
                COALESCE(asset_type,'')
            ) IN (
                'dam',
                'barrage',
                'bridge',
                'road',
                'airport',
                'temple'
            )
            """
        )

    finally:
        await conn.close()


    assets = []

    for record in asset_records:

        raw = record["asset_json"]

        if isinstance(raw, str):
            assets.append(
                json.loads(raw)
            )
        elif isinstance(raw, dict):
            assets.append(raw)


    readiness = []


    for asset_type in ASSET_TYPES:

        rows = [
            row
            for row in assets
            if str(
                row.get(
                    "asset_type",
                    "",
                )
            ).lower()
            == asset_type
        ]

        total = len(rows)

        verified = sum(
            1
            for row in rows
            if str(
                row.get(
                    "identity_status",
                    "",
                )
            ).upper()
            == "VERIFIED"
        )


        location_ready = sum(
            1
            for row in rows
            if any(
                has_value(row, field)
                for field in LOCATION_FIELDS
            )
        )


        engineering_ready = sum(
            1
            for row in rows
            if any(
                has_value(row, field)
                for field in ENGINEERING_FIELDS
            )
        )


        built_year_ready = sum(
            1
            for row in rows
            if has_value(
                row,
                "built_year",
            )
        )


        material_ready = sum(
            1
            for row in rows
            if has_value(
                row,
                "material",
            )
        )


        relevant_tables = [
            table
            for table in tables
            if any(
                keyword
                in table.lower()
                for keyword
                in TABLE_KEYWORDS[
                    asset_type
                ]
            )
        ]


        climate_tables = [
            table
            for table in tables
            if any(
                keyword
                in table.lower()
                for keyword
                in TABLE_KEYWORDS[
                    "climate"
                ]
            )
        ]


        if total == 0:

            health_status = (
                "NO_CANONICAL_ASSETS"
            )

            risk_status = (
                "NO_CANONICAL_ASSETS"
            )

            rul_status = (
                "NO_CANONICAL_ASSETS"
            )

        else:

            if engineering_ready > 0:
                health_status = (
                    "FEATURE_BUILD_REQUIRED"
                )
            else:
                health_status = (
                    "INSUFFICIENT_ENGINEERING_EVIDENCE"
                )


            if location_ready > 0:
                risk_status = (
                    "CLIMATE_FEATURE_BUILD_REQUIRED"
                )
            else:
                risk_status = (
                    "INSUFFICIENT_LOCATION_EVIDENCE"
                )


            rul_status = (
                "LONGITUDINAL_LABELS_REQUIRED"
            )


        readiness.append(
            {
                "asset_type":
                    asset_type,

                "assets":
                    total,

                "verified_identity_assets":
                    verified,

                "location_ready_assets":
                    location_ready,

                "engineering_ready_assets":
                    engineering_ready,

                "built_year_assets":
                    built_year_ready,

                "material_assets":
                    material_ready,

                "relevant_tables":
                    ";".join(
                        relevant_tables
                    ),

                "climate_tables":
                    ";".join(
                        climate_tables
                    ),

                "health_readiness":
                    health_status,

                "risk_readiness":
                    risk_status,

                "rul_readiness":
                    rul_status,

                "health_model_plan":
                    MODEL_PLAN[
                        asset_type
                    ]["health"],

                "risk_model_plan":
                    MODEL_PLAN[
                        asset_type
                    ]["risk"],

                "rul_model_plan":
                    MODEL_PLAN[
                        asset_type
                    ]["rul"],
            }
        )


    output = Path(
        "/app/data/processed/ml_phase4"
    )

    output.mkdir(
        parents=True,
        exist_ok=True,
    )


    csv_path = (
        output
        / "SIMRAS_ML_READINESS.csv"
    )

    json_path = (
        output
        / "SIMRAS_ML_READINESS.json"
    )

    contract_path = (
        output
        / "SIMRAS_FEATURE_CONTRACT.json"
    )


    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=
                readiness[0].keys(),
        )

        writer.writeheader()
        writer.writerows(readiness)


    json_path.write_text(
        json.dumps(
            readiness,
            indent=2,
        ),
        encoding="utf-8",
    )


    contract = {
        "feature_version":
            "simras_common_state_v1",

        "asset_types":
            ASSET_TYPES,

        "shared_climate_features":
            CLIMATE_FEATURES,

        "target_architecture": {
            "health":
                "category-specific model",

            "risk":
                "category-specific model with climate features",

            "rul":
                "XGBoost AFT survival model when eligible",
        },

        "rules": [
            "No synthetic production predictions.",
            "No RUL without longitudinal labels.",
            "Health Risk and RUL are separate targets.",
            "External transfer models remain RESEARCH_TRANSFER until AP validation.",
            "Climate variables are direct model features.",
            "Asset/year leakage between train and test is prohibited.",
        ],

        "category_models":
            MODEL_PLAN,
    }


    contract_path.write_text(
        json.dumps(
            contract,
            indent=2,
        ),
        encoding="utf-8",
    )


    print()
    print("=" * 118)
    print(
        "SIMRAS ML PHASE 4 READINESS"
    )
    print("=" * 118)

    print(
        f"{'TYPE':10}"
        f"{'ASSETS':>9}"
        f"{'VERIFIED':>11}"
        f"{'LOCATION':>11}"
        f"{'ENGINEERING':>14}"
        f"{'BUILT_YEAR':>12}"
        f"{'MATERIAL':>10}"
    )

    print("-" * 118)

    for row in readiness:

        print(
            f"{row['asset_type'].upper():10}"
            f"{row['assets']:>9}"
            f"{row['verified_identity_assets']:>11}"
            f"{row['location_ready_assets']:>11}"
            f"{row['engineering_ready_assets']:>14}"
            f"{row['built_year_assets']:>12}"
            f"{row['material_assets']:>10}"
        )


    print()
    print("READINESS")

    for row in readiness:

        print()
        print(
            row["asset_type"].upper()
        )

        print(
            "  HEALTH:",
            row[
                "health_readiness"
            ],
        )

        print(
            "  RISK  :",
            row[
                "risk_readiness"
            ],
        )

        print(
            "  RUL   :",
            row[
                "rul_readiness"
            ],
        )


    print()

    print(
        "CSV      :",
        csv_path,
    )

    print(
        "JSON     :",
        json_path,
    )

    print(
        "CONTRACT :",
        contract_path,
    )


    try:
        import xgboost

        print(
            "XGBOOST  :",
            xgboost.__version__,
        )

    except Exception as exc:

        print(
            "XGBOOST  : NOT INSTALLED",
            exc,
        )


    try:
        import lightgbm

        print(
            "LIGHTGBM :",
            lightgbm.__version__,
        )

    except Exception:

        print(
            "LIGHTGBM : NOT INSTALLED"
        )


    print("=" * 118)


asyncio.run(main())
