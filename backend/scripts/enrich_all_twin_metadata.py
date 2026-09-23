from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from sqlalchemy import text

from app.db.session import SessionLocal


SOURCE_OVERRIDES: list[dict[str, Any]] = [
    {
        "matches": ["srisailam"],
        "template": "gravity_dam",
        "source_name": "Krishna River Management Board",
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
        },
    },
    {
        "matches": ["prakasam barrage", "prakasham barrage"],
        "template": "gated_barrage",
        "source_name": "Krishna River Management Board",
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
        },
    },
    {
        "matches": ["kanaka durga", "kanakadurga"],
        "template": "curved_flyover",
        "source_name": "MoRTH/PIB project record + Tata Steel engineering project record",
        "source_url": (
            "https://www.pib.gov.in/PressReleasePage.aspx"
            "?PRID=1664791&lang=2&reg=48"
        ),
        "dimensions": {
            "length_m": 2600.0,
            "project_corridor_length_m": 5122.0,
            "lane_count": 6,
            "typical_span_m": 45.0,
            "deck_width_ft": 78.0,
            "curve_count": 6,
            "major_turn_count": 2,
            "alignment_status": "parametric_curve_from_published_project_characteristics",
        },
    },
    {
        "matches": ["vijayawada airport", "gannavaram airport"],
        "template": "airport_runway",
        "source_name": "Airports Authority of India eAIP - VOBZ",
        "source_url": (
            "https://aim-india.aai.aero/eAIP_Archive/19-05-2022/"
            "eAIP/IN-AD%202.1VOBZ-en-GB.html"
        ),
        "dimensions": {
            "runway_length_m": 3360.0,
            "runway_width_m": 45.0,
            "runway_designation": "08/26",
            "surface": "asphalt",
        },
    },
    {
        "matches": ["rajahmundry airport", "rajahmundry", "rajamahendravaram airport"],
        "template": "airport_runway",
        "source_name": "Airports Authority of India eAIP - VORY",
        "source_url": (
            "https://aim-india.aai.aero/eaip-v2-6-2023/"
            "eAIP/IN-AD%202.1VORY-en-GB.html"
        ),
        "dimensions": {
            "runway_length_m": 3165.0,
            "runway_width_m": 45.0,
            "runway_designation": "05/23",
            "runway_true_bearing_deg": 53.25,
            "surface": "asphalt",
        },
    },
    {
        "matches": ["tirupati airport"],
        "template": "airport_runway",
        "source_name": "Airports Authority of India eAIP - VOTP",
        "source_url": (
            "https://aim-india.aai.aero/eAIP_Archive/01-07-2019/"
            "eAIP/IN-AD%202.1VOTP-en-GB.html"
        ),
        "dimensions": {
            "runway_length_m": 2286.0,
            "runway_width_m": 45.0,
            "runway_designation": "08/26",
            "surface": "asphalt",
            "source_date_note": "published eAIP archive value; verify against latest amendment before engineering use",
        },
    },
]


ALIASES: dict[str, list[str]] = {
    "length_m": [
        "length_m",
        "dm_length",
        "dam_length",
        "length",
        "structure_length",
        "bridge_length",
        "total_length",
    ],
    "height_m": [
        "height_m",
        "dm_height",
        "dam_height",
        "height",
        "max_height",
    ],
    "crest_width_m": [
        "crest_width_m",
        "crest_width",
        "top_width",
        "top_width_m",
    ],
    "gate_count": [
        "gate_count",
        "no_of_gates",
        "number_of_gates",
        "gates",
    ],
    "gate_width_m": [
        "gate_width_m",
        "gate_width",
    ],
    "gate_height_m": [
        "gate_height_m",
        "gate_height",
    ],
    "spillway_length_m": [
        "spillway_length_m",
        "spillway_length",
    ],
    "runway_length_m": [
        "runway_length_m",
        "runway_length",
    ],
    "runway_width_m": [
        "runway_width_m",
        "runway_width",
    ],
    "berth_length_m": [
        "berth_length_m",
        "berth_length",
        "quay_length_m",
        "quay_length",
    ],
    "permissible_draft_m": [
        "permissible_draft_m",
        "draft_m",
        "draft",
    ],
    "lane_count": [
        "lane_count",
        "lanes",
        "number_of_lanes",
    ],
    "span_count": [
        "span_count",
        "number_of_spans",
        "no_of_spans",
    ],
    "typical_span_m": [
        "typical_span_m",
        "main_span_m",
        "span_m",
        "max_span_m",
    ],
    "gopuram_height_m": [
        "gopuram_height_m",
        "tower_height_m",
    ],
}


def normalise_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if match:
            return float(match.group(0))

    return None


def walk(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield normalise_key(str(key)), item
            yield from walk(item)

    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def extract_dimensions(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    flattened = list(walk(evidence))
    output: dict[str, Any] = {}

    for canonical, aliases in ALIASES.items():
        wanted = {normalise_key(alias) for alias in aliases}

        for key, raw in flattened:
            if key not in wanted:
                continue

            value = number(raw)

            if value is not None and value > 0:
                output[canonical] = (
                    int(value)
                    if canonical in {"gate_count", "lane_count", "span_count"}
                    else round(value, 4)
                )
                break

    # Preserve common dam/bridge structural classification strings.
    for key, raw in flattened:
        if key in {"dm_type", "dam_type", "structure_type", "bridge_type"}:
            if isinstance(raw, str) and raw.strip():
                output["structural_form"] = raw.strip()
                break

    return output


def template_for(asset: dict[str, Any], dimensions: dict[str, Any]) -> str:
    explicit = str(dimensions.get("template") or "").strip().lower()
    if explicit:
        return explicit

    name = str(asset["name"] or "").lower()
    asset_type = str(asset["asset_type"] or "").lower()
    subtype = str(asset["subtype"] or "").lower()

    if "flyover" in name or "flyover" in subtype or "viaduct" in subtype:
        return "curved_flyover"

    if "arch" in name or "arch" in subtype:
        return "arch_bridge"

    if asset_type == "bridge":
        return "girder_bridge"

    if asset_type == "barrage" or "barrage" in name:
        return "gated_barrage"

    if asset_type == "dam":
        return "gravity_dam"

    if asset_type == "airport":
        return "airport_runway"

    if asset_type == "port":
        return "port_berth"

    if asset_type == "temple":
        return "temple_complex"

    return "generic"


def find_override(name: str) -> dict[str, Any] | None:
    lowered = name.lower()

    for record in SOURCE_OVERRIDES:
        if any(token in lowered for token in record["matches"]):
            return record

    return None


async def evidence_json(session, asset_id: int) -> list[dict[str, Any]]:
    try:
        value = (
            await session.execute(
                text(
                    """
                    SELECT COALESCE(
                        jsonb_agg(to_jsonb(oe)),
                        '[]'::jsonb
                    )
                    FROM official_evidence oe
                    WHERE oe.asset_id = CAST(:asset_id AS INTEGER)
                    """
                ),
                {"asset_id": asset_id},
            )
        ).scalar_one()

        return value or []

    except Exception:
        return []


async def active_model(session, asset_id: int):
    return (
        await session.execute(
            text(
                """
                SELECT
                    id,
                    model_uri,
                    format,
                    version,
                    fidelity_level,
                    model_source,
                    source_url,
                    dimensions,
                    is_asset_specific
                FROM asset_models
                WHERE asset_id = CAST(:asset_id AS INTEGER)
                  AND is_active = TRUE
                ORDER BY updated_at DESC NULLS LAST, id DESC
                LIMIT 1
                """
            ),
            {"asset_id": asset_id},
        )
    ).mappings().first()


async def save_profile(
    session,
    asset: dict[str, Any],
    profile: dict[str, Any],
    source_name: str,
    source_url: str | None,
    source_backed_count: int,
) -> None:
    asset_id = int(asset["id"])
    identity = str(asset["identity_status"] or "").upper()
    current = await active_model(session, asset_id)

    has_real_model = bool(current and current["model_uri"])

    if has_real_model:
        fidelity = str(current["fidelity_level"] or "L2")
        is_specific = True
        model_source = str(current["model_source"] or source_name)
        url = current["source_url"] or source_url
    elif identity == "VERIFIED" and source_backed_count >= 1:
        fidelity = "L1"
        is_specific = True
        model_source = source_name
        url = source_url
    else:
        fidelity = "L0"
        is_specific = False
        model_source = (
            "SIMRAS illustrative type model; "
            "source-backed engineering geometry not yet linked"
        )
        url = None

        # Do not expose unverified numeric dimensions as measured truth.
        profile = {
            "template": profile["template"],
            "representation": "illustrative_type_model_not_measured",
        }

    profile.setdefault(
        "representation",
        (
            "source_backed_parametric_model"
            if fidelity != "L0"
            else "illustrative_type_model_not_measured"
        ),
    )

    if current:
        await session.execute(
            text(
                """
                UPDATE asset_models
                SET
                    version = CAST(:version AS VARCHAR),
                    fidelity_level = CAST(:fidelity AS VARCHAR),
                    model_source = CAST(:model_source AS VARCHAR),
                    source_url = CAST(:source_url AS TEXT),
                    dimensions = CAST(:dimensions AS JSONB),
                    is_asset_specific = CAST(:specific AS BOOLEAN),
                    updated_at = NOW()
                WHERE id = CAST(:model_id AS INTEGER)
                """
            ),
            {
                "model_id": int(current["id"]),
                "version": "real-twin-v1",
                "fidelity": fidelity,
                "model_source": model_source,
                "source_url": url,
                "dimensions": json.dumps(profile),
                "specific": is_specific,
            },
        )
    else:
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
                    'procedural',
                    'real-twin-v1',
                    CAST(:fidelity AS VARCHAR),
                    CAST(:model_source AS VARCHAR),
                    CAST(:source_url AS TEXT),
                    CAST(:dimensions AS JSONB),
                    CAST(:specific AS BOOLEAN),
                    TRUE,
                    NOW(),
                    NOW()
                )
                """
            ),
            {
                "asset_id": asset_id,
                "fidelity": fidelity,
                "model_source": model_source,
                "source_url": url,
                "dimensions": json.dumps(profile),
                "specific": is_specific,
            },
        )


async def main() -> None:
    async with SessionLocal() as session:
        assets = (
            await session.execute(
                text(
                    """
                    SELECT
                        id,
                        asset_code,
                        name,
                        asset_type,
                        subtype,
                        identity_status,
                        built_year,
                        material
                    FROM assets
                    ORDER BY id
                    """
                )
            )
        ).mappings().all()

        counts = {
            "assets": 0,
            "source_backed": 0,
            "l0": 0,
            "override": 0,
            "evidence_extracted": 0,
        }

        for row in assets:
            asset = dict(row)
            counts["assets"] += 1

            evidence = await evidence_json(session, int(asset["id"]))
            extracted = extract_dimensions(evidence)
            source_name = "Existing asset registry / official evidence"
            source_url: str | None = None

            override = find_override(str(asset["name"]))

            if override:
                extracted.update(override["dimensions"])
                source_name = override["source_name"]
                source_url = override["source_url"]
                extracted["template"] = override["template"]
                counts["override"] += 1

            if extracted:
                counts["evidence_extracted"] += 1

            extracted["template"] = template_for(asset, extracted)

            source_count = len(
                [
                    key
                    for key in extracted.keys()
                    if key
                    not in {
                        "template",
                        "representation",
                        "structural_form",
                        "alignment_status",
                    }
                ]
            )

            if (
                str(asset["identity_status"] or "").upper() == "VERIFIED"
                and source_count >= 1
            ):
                counts["source_backed"] += 1
            else:
                counts["l0"] += 1

            await save_profile(
                session=session,
                asset=asset,
                profile=extracted,
                source_name=source_name,
                source_url=source_url,
                source_backed_count=source_count,
            )

        await session.commit()

        print("=" * 72)
        print("SIMRAS REAL-TWIN ENRICHMENT COMPLETE")
        print("=" * 72)
        for key, value in counts.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())