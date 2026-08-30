from __future__ import annotations

import asyncio
import json
from typing import Any

from sqlalchemy import text

from app.db.session import SessionLocal


SOURCE_MODELS: dict[str, dict[str, Any]] = {
    "AP_DAM_00001": {
        "asset_type": "barrage",
        "subtype": "gated_barrage",
        "model_source": (
            "Krishna River Management Board - Prakasam Barrage salient features"
        ),
        "source_url": "https://krmb.gov.in/html/project37.html",
        "dimensions": {
            "length_m": 1232.92,
            "gate_count": 70,
            "gate_width_m": 12.19,
            "gate_height_m": 3.66,
            "left_scour_sluice_count": 6,
            "right_scour_sluice_count": 8,
            "constructed_year": 1957,
            "structural_form": "gated_barrage",
            "representation": "source_backed_dimension_model",
            "source_basis": "KRMB salient features",
        },
    },
    "AP_DAM_NWDP_AP01VH0059": {
        "asset_type": "dam",
        "subtype": "reservoir_dam",
        "model_source": (
            "Krishna River Management Board - Srisailam salient features"
        ),
        "source_url": "https://krmb.gov.in/html/project19.html",
        "dimensions": {
            "length_m": 512.0,
            "height_m": 143.26,
            "spillway_length_m": 266.39,
            "gate_count": 12,
            "gate_width_m": 18.3,
            "gate_height_m": 16.7,
            "deep_river_bed_level_m": 152.4,
            "full_reservoir_level_m": 269.75,
            "maximum_water_level_m": 271.88,
            "spillway_crest_level_m": 252.98,
            "designed_total_spillway_capacity_m3s": 38365.0,
            "dam_type": "gravity_dam",
            "representation": "source_backed_dimension_model",
            "source_basis": "KRMB salient features",
        },
    },
}


async def get_asset(session, code: str) -> dict[str, Any] | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, asset_code, name, asset_type, subtype, identity_status
                FROM assets
                WHERE asset_code = CAST(:code AS VARCHAR)
                LIMIT 1
                """
            ),
            {"code": code},
        )
    ).mappings().first()
    return dict(row) if row else None


async def active_model_id(session, asset_id: int) -> int | None:
    value = (
        await session.execute(
            text(
                """
                SELECT id
                FROM asset_models
                WHERE asset_id = CAST(:asset_id AS INTEGER)
                  AND is_active = TRUE
                ORDER BY updated_at DESC NULLS LAST, id DESC
                LIMIT 1
                """
            ),
            {"asset_id": asset_id},
        )
    ).scalar_one_or_none()
    return int(value) if value is not None else None


async def upsert_source_model(
    session,
    asset: dict[str, Any],
    metadata: dict[str, Any],
) -> None:
    asset_id = int(asset["id"])

    await session.execute(
        text(
            """
            UPDATE assets
            SET
                asset_type = CAST(:asset_type AS VARCHAR),
                subtype = CAST(:subtype AS VARCHAR),
                updated_at = NOW()
            WHERE id = CAST(:asset_id AS INTEGER)
            """
        ),
        {
            "asset_id": asset_id,
            "asset_type": metadata["asset_type"],
            "subtype": metadata["subtype"],
        },
    )

    model_id = await active_model_id(session, asset_id)

    params = {
        "asset_id": asset_id,
        "version": "2.0-source-backed",
        "fidelity": "L1",
        "model_source": metadata["model_source"],
        "source_url": metadata["source_url"],
        "dimensions": json.dumps(metadata["dimensions"]),
    }

    if model_id is None:
        model_id = int(
            (
                await session.execute(
                    text(
                        """
                        INSERT INTO asset_models (
                            asset_id,
                            model_uri,
                            format,
                            version,
                            fidelity_level,
                            model_source,
                            source_url,
                            dimensions,
                            is_asset_specific,
                            is_active,
                            created_at,
                            updated_at
                        )
                        VALUES (
                            CAST(:asset_id AS INTEGER),
                            NULL,
                            'parametric',
                            CAST(:version AS VARCHAR),
                            CAST(:fidelity AS VARCHAR),
                            CAST(:model_source AS VARCHAR),
                            CAST(:source_url AS TEXT),
                            CAST(:dimensions AS JSONB),
                            TRUE,
                            TRUE,
                            NOW(),
                            NOW()
                        )
                        RETURNING id
                        """
                    ),
                    params,
                )
            ).scalar_one()
        )
        print("INSERTED", asset["asset_code"], "model", model_id)
    else:
        params["model_id"] = model_id
        await session.execute(
            text(
                """
                UPDATE asset_models
                SET
                    model_uri = NULL,
                    format = 'parametric',
                    version = CAST(:version AS VARCHAR),
                    fidelity_level = CAST(:fidelity AS VARCHAR),
                    model_source = CAST(:model_source AS VARCHAR),
                    source_url = CAST(:source_url AS TEXT),
                    dimensions = CAST(:dimensions AS JSONB),
                    is_asset_specific = TRUE,
                    is_active = TRUE,
                    updated_at = NOW()
                WHERE id = CAST(:model_id AS INTEGER)
                """
            ),
            params,
        )
        print("UPDATED", asset["asset_code"], "model", model_id)

    await session.execute(
        text(
            """
            UPDATE asset_models
            SET is_active = FALSE, updated_at = NOW()
            WHERE asset_id = CAST(:asset_id AS INTEGER)
              AND id <> CAST(:model_id AS INTEGER)
              AND is_active = TRUE
            """
        ),
        {"asset_id": asset_id, "model_id": model_id},
    )


async def demote_unverified_godavari(session) -> None:
    asset = await get_asset(session, "AP_BR_00001")
    if asset is None:
        return

    if str(asset["identity_status"]).upper() == "VERIFIED":
        print(
            "AP_BR_00001 is VERIFIED; keeping current fidelity. "
            "Do not attach railway evidence unless the exact bridge identity matches."
        )
        return

    await session.execute(
        text(
            """
            UPDATE asset_models
            SET
                model_uri = NULL,
                format = 'procedural',
                version = 'identity-unverified-l0',
                fidelity_level = 'L0',
                model_source = 'Identity not yet verified; illustrative type model only',
                source_url = NULL,
                dimensions =
                    '{"representation":"illustrative_type_model_not_measured"}'::jsonb,
                is_asset_specific = FALSE,
                updated_at = NOW()
            WHERE asset_id = CAST(:asset_id AS INTEGER)
              AND is_active = TRUE
            """
        ),
        {"asset_id": int(asset["id"])},
    )

    print(
        "DEMOTED AP_BR_00001 to L0 because identity_status =",
        asset["identity_status"],
    )


async def main() -> None:
    async with SessionLocal() as session:
        for code, metadata in SOURCE_MODELS.items():
            asset = await get_asset(session, code)

            if asset is None:
                print("SKIP", code, "- asset not found")
                continue

            if str(asset["identity_status"]).upper() != "VERIFIED":
                print(
                    "SKIP",
                    code,
                    "- identity is not VERIFIED:",
                    asset["identity_status"],
                )
                continue

            await upsert_source_model(session, asset, metadata)

        await demote_unverified_godavari(session)
        await session.commit()

        print("REAL-WORLD TWIN METADATA COMMIT COMPLETE")


if __name__ == "__main__":
    asyncio.run(main())
