from __future__ import annotations

import asyncio
import json
from typing import Any

from sqlalchemy import text
from app.db.session import SessionLocal


RECORDS: list[dict[str, Any]] = [
    {
        "asset_code": "AP_AIR_AAI_VIJAYAWADA",
        "tokens": ["vijayawada airport"],
        "template": "airport_vijayawada",
        "fidelity": "L1",
        "model_source": "AAI India eAIP / Vijayawada Aerodrome Chart",
        "source_url": "https://aim-india.aai.aero/eaip/eaip-v2-04-2026/eAIP/IN-AD%202.1VOBZ-en-GB.html",
        "dimensions": {
            "runway_designation": "08/26",
            "runway_length_m": 3360.0, "runway_width_m": 45.0,
            "runway_strip_length_m": 3480.0, "runway_strip_width_m": 280.0,
            "runway_true_bearing_deg": 77.75, "opposite_true_bearing_deg": 257.75,
            "resa_08_length_m": 240.0, "resa_08_width_m": 90.0,
            "resa_26_length_m": 150.0, "resa_26_width_m": 90.0,
            "layout_epoch": "2025-04-28",
            "layout_features": ["Apron I", "Apron II", "Apron III", "ATC tower", "cargo complex", "terminal building"],
            "representation": "source_backed_airport_complex",
            "geometry_scope": "runway_strip_resa_plus_chart_context",
            "source_references": ["AAI eAIP VOBZ AD 2.12", "AAI VOBZ Aerodrome Chart AAI/55-AC/2024"]
        },
    },
    {
        "asset_code": "AP_AIR_AAI_TIRUPATI",
        "tokens": ["tirupati airport"],
        "template": "airport_tirupati",
        "fidelity": "L1",
        "model_source": "AAI India eAIP + AAI Integrated Terminal release",
        "source_url": "https://aim-india.aai.aero/eAIP_Archive/06-08-2026/eAIP/IN-AD%202.1VOTP-en-GB.html",
        "dimensions": {
            "runway_designation": "08/26",
            "runway_length_m": 3810.0, "runway_width_m": 45.0,
            "runway_strip_length_m": 3930.0, "runway_strip_width_m": 280.0,
            "runway_true_bearing_deg": 81.50, "opposite_true_bearing_deg": 261.50,
            "resa_length_m": 240.0, "resa_width_m": 90.0,
            "terminal_area_sqm": 16500.0,
            "terminal_peak_hour_capacity": 700, "apron_aircraft_stands": 3,
            "terminal_geometry_status": "area_scaled_massing_not_survey_footprint",
            "representation": "source_backed_airport_complex",
            "source_references": ["AAI eAIP VOTP AD 2.12", "AAI New Integrated Terminal Building Tirupati Airport"]
        },
    },
    {
        "asset_code": "AP_AIR_AAI_RAJAHMUNDRY",
        "tokens": ["rajahmundry airport", "rajamahendravaram airport"],
        "template": "airport_rajahmundry",
        "fidelity": "L1",
        "model_source": "AAI India eAIP / Rajahmundry Airport",
        "source_url": "https://aim-india.aai.aero/eAIP_Archive/12-06-2025/eAIP/IN-AD%202.1VORY-en-GB.html",
        "dimensions": {
            "runway_designation": "05/23",
            "runway_length_m": 3165.0, "runway_width_m": 45.0,
            "runway_strip_length_m": 3285.0, "runway_strip_width_m": 280.0,
            "runway_true_bearing_deg": 53.25, "opposite_true_bearing_deg": 233.25,
            "resa_length_m": 90.0, "resa_width_m": 90.0,
            "taxiway_c_length_m": 257.5, "taxiway_c_width_m": 23.0,
            "isolation_bay_length_m": 91.0, "isolation_bay_width_m": 76.0,
            "land_area_status": "not_used_for_geometry_due_to_conflicting_AAI_pages",
            "representation": "source_backed_airport_complex",
            "source_references": ["AAI eAIP VORY AD 2.8", "AAI eAIP VORY AD 2.12"]
        },
    },
    {
        "asset_code": "AP_AIR_AAI_KADAPA",
        "tokens": ["kadapa airport", "cuddapah airport"],
        "template": "airport_kadapa",
        "fidelity": "L1",
        "model_source": "AAI India eAIP / Kadapa Airport",
        "source_url": "https://aim-india.aai.aero/eaip/eaip-v2-01-2026/eAIP/IN-AD%202.1VOCP-en-GB.html",
        "dimensions": {
            "runway_designation": "11/29",
            "runway_length_m": 1719.0, "runway_width_m": 30.0,
            "runway_strip_length_m": 1839.0, "runway_strip_width_m": 150.0,
            "runway_true_bearing_deg": 108.31, "opposite_true_bearing_deg": 288.31,
            "terminal_status": "new_domestic_terminal_project",
            "terminal_dimensions_status": "not_published_in_linked_source",
            "representation": "source_backed_airport_complex",
            "source_references": ["AAI eAIP VOCP AD 2.12", "AAI New Domestic Terminal Building project"]
        },
    },
    {
        "asset_code": "AP_AIR_AAI_KURNOOL",
        "tokens": ["kurnool airport", "orvakal airport", "uyyalawada narasimha reddy airport"],
        "template": "airport_kurnool",
        "fidelity": "L1",
        "model_source": "AAI India eAIP + APADCL official project documents",
        "source_url": "https://aim-india.aai.aero/eAIP_Archive/02-11-2023/eAIP/IN-AD%202.1VOKU-en-GB.html",
        "dimensions": {
            "runway_designation": "10/28",
            "runway_length_m": 2000.0, "runway_width_m": 30.0,
            "runway_strip_length_m": 2120.0, "runway_strip_width_m": 150.0,
            "runway_true_bearing_deg": 98.84, "opposite_true_bearing_deg": 278.84,
            "terminal_area_sqm": 1350.0, "apron_atr_stands": 4,
            "land_area_acres": 1008.75, "aero_zone_acres": 135.0,
            "terminal_geometry_status": "area_scaled_massing_not_survey_footprint",
            "representation": "source_backed_airport_complex",
            "source_references": ["AAI eAIP VOKU AD 2.12", "APADCL Kurnool Airport RFP", "APADCL 2025 O&M/development EOI"]
        },
    },
    {
        "asset_code": "AP_AIR_AAI_VISAKHAPATNAM",
        "tokens": ["visakhapatnam airport", "vizag airport"],
        "template": "airport_visakhapatnam",
        "fidelity": "L1",
        "model_source": "AAI Visakhapatnam Airport fact sheet / status",
        "source_url": "https://www.aai.aero/en/node/2856",
        "dimensions": {
            "runway_designation": "10/28",
            "runway_length_m": 3048.0, "runway_width_m": 45.0, "runway_axis_deg": 100.0,
            "secondary_runway_designation": "05/23",
            "secondary_runway_length_m": 1829.0, "secondary_runway_width_m": 45.0,
            "secondary_runway_true_bearing_deg": 47.81,
            "terminal_area_sqm": 20400.0, "land_area_acres": 350.31,
            "apron_length_m": 350.0, "apron_width_m": 135.0,
            "old_apron_length_m": 90.0, "old_apron_width_m": 75.0,
            "parking_contact_stands": 8, "parking_remote_stands": 3, "parking_cargo_stands": 3,
            "terminal_geometry_status": "area_scaled_massing_not_survey_footprint",
            "representation": "source_backed_airport_complex",
            "source_references": ["AAI Visakhapatnam Airport fact sheet", "AAI Visakhapatnam present-status publication"]
        },
    },

    {
        "asset_code": "AP_TEMPLE_TIRUMALA",
        "tokens": ["venkateswara swamy temple, tirumala", "tirumala"],
        "template": "temple_tirumala",
        "fidelity": "L1",
        "model_source": "Tirumala Tirupati Devasthanams official publications",
        "source_url": "https://www.tirumala.org/TTDTempleHistory.aspx",
        "dimensions": {
            "complex_land_area_acres": 16.2,
            "main_platform_length_m": 126.492, "main_platform_width_m": 80.1624,
            "main_platform_length_ft": 415.0, "main_platform_width_ft": 263.0,
            "ananda_nilaya_total_height_m": 19.8628, "ananda_nilaya_total_height_ft": 65.1667,
            "vimanam_upper_height_ft": 37.6667, "vimanam_storeys": 3,
            "outer_gopuram_base_ns_ft": 38.0, "outer_gopuram_base_ew_ft": 32.0,
            "outer_gopuram_height_ft": 50.0, "outer_gopuram_storeys": 5,
            "architectural_style": "Dravidian",
            "representation": "source_backed_temple_complex",
            "source_references": ["TTD Temple History", "TTD Ananda Nilayam", "TTD Sanctorum of Lord Venkateswara", "TTD The Tirumala Temple"]
        },
    },
    {
        "asset_code": "AP_TEMPLE_SRIKALAHASTI",
        "tokens": ["kalahasteeswara", "srikalahasti", "sri kalahasti"],
        "template": "temple_srikalahasti",
        "fidelity": "L1",
        "model_source": "Sri Kalahasti Temple official site",
        "source_url": "https://srikalahasthitemple.com/history/",
        "dimensions": {
            "main_gopuram_height_m": 36.5, "main_gopuram_height_ft": 120.0,
            "pathala_ganapathi_depth_ft": 20.0,
            "architectural_context": "west_facing_temple_adjoining_hill",
            "river_context": "Swarnamukhi",
            "representation": "source_backed_partial_temple_geometry",
            "source_references": ["Sri Kalahasti Temple official History", "Sri Kalahasti Temple official About Temple"]
        },
    },
    {
        "asset_code": "AP_TEMPLE_KANAKA_DURGA",
        "tokens": ["durga malleswara", "kanaka durga"],
        "template": "temple_kanaka_durga",
        "fidelity": "L1",
        "model_source": "AP Government identity/style + public rajagopuram dimension",
        "source_url": "https://ntr.ap.gov.in/tourist-place/kanaka-durga-temple-vijayawada/",
        "dimensions": {
            "rajagopuram_storeys": 9, "rajagopuram_height_ft": 82.6, "rajagopuram_height_m": 25.1765,
            "architectural_style": "Dravidian", "site_context": "Indrakeeladri_hill",
            "source_grade_height": "SECONDARY_PUBLIC_NEW_INDIAN_EXPRESS_2015",
            "representation": "source_backed_partial_temple_geometry",
            "source_references": ["NTR/Krishna District Government", "New Indian Express 2015 rajagopuram report"]
        },
    },
    {
        "asset_code": "AP_TEMPLE_SRISAILAM",
        "tokens": ["mallikarjuna swamy temple", "mallikarjuna", "srisailam temple"],
        "template": "temple_srisailam",
        "fidelity": "L1",
        "model_source": "Census of India historical official dimensional description",
        "source_url": "https://censusindia.gov.in/nada/index.php/catalog/30154/download/33335/22180_1961_KUR.pdf",
        "dimensions": {
            "enclosure_length_m": 201.168, "enclosure_width_m": 155.448,
            "enclosure_length_ft": 660.0, "enclosure_width_ft": 510.0,
            "wall_height_min_m": 6.096, "wall_height_max_m": 7.9248,
            "wall_height_min_ft": 20.0, "wall_height_max_ft": 26.0,
            "central_gopuram_height_ft": 30.0,
            "dimension_epoch": "historical_reference_not_current_survey",
            "representation": "source_backed_historical_temple_envelope",
            "source_references": ["Census of India Fairs and Festivals, Kurnool, Vol II"]
        },
    },
    {
        "asset_code": "AP_TEMPLE_SIMHACHALAM",
        "tokens": ["simhachalam", "varaha lakshmi narasimha"],
        "template": "temple_simhachalam",
        "fidelity": "L0",
        "model_source": "Visakhapatnam District Government architectural description",
        "source_url": "https://visakhapatnam.ap.gov.in/religion/",
        "dimensions": {
            "site_elevation_m_asl": 244.0, "shrine_form": "square", "mandapam_pillar_count": 16,
            "material": "dark_granite",
            "representation": "source_described_form_not_measured",
            "geometry_scope": "architectural_form_only_no_measured_building_dimensions"
        },
    },
    {
        "asset_code": "AP_TEMPLE_ANNAVARAM",
        "tokens": ["annavaram", "satyanarayana swamy"],
        "template": "temple_annavaram",
        "fidelity": "L0",
        "model_source": "East Godavari / Kakinada District Government",
        "source_url": "https://eastgodavari.ap.gov.in/lord-sri-veera-venkata-satya-narayana-swamy-vari-devasthanam-annavaram/",
        "dimensions": {
            "storey_count": 2, "deity_height_m": 4.0, "site_context": "Ratnagiri_hill",
            "architectural_style": "Dravidian",
            "representation": "source_described_form_not_measured",
            "geometry_scope": "two_storey_form_no_measured_building_envelope"
        },
    },
    {
        "asset_code": "AP_TEMPLE_DWARAKA_TIRUMALA",
        "tokens": ["dwaraka tirumala"],
        "template": "temple_dwaraka_tirumala",
        "fidelity": "L0",
        "model_source": "Census of India + Ministry of Tourism Utsav record",
        "source_url": "https://censusindia.gov.in/nada/index.php/catalog/30161/download/33342/22186_1961_WES.pdf",
        "dimensions": {
            "main_gopuram_storeys": 5, "temple_site_height_ft": 120.0, "temple_site_height_m": 36.576,
            "site_context": "portion_of_temple_carved_out_of_hill",
            "representation": "source_described_form_not_measured",
            "geometry_scope": "architectural_form_no_measured_building_envelope"
        },
    },
]


async def find_asset(session, record):
    row = (await session.execute(
        text("SELECT id,asset_code,name,asset_type,identity_status FROM assets WHERE asset_code=:code LIMIT 1"),
        {"code": record["asset_code"]},
    )).mappings().first()
    if row:
        return row

    for token in record["tokens"]:
        row = (await session.execute(
            text("""
                SELECT id,asset_code,name,asset_type,identity_status
                FROM assets
                WHERE lower(name) LIKE :token
                ORDER BY id LIMIT 1
            """),
            {"token": f"%{token.lower()}%"},
        )).mappings().first()
        if row:
            return row
    return None


async def active_model(session, asset_id):
    return (await session.execute(
        text("""
            SELECT id,model_uri,fidelity_level,dimensions
            FROM asset_models
            WHERE asset_id=:asset_id AND is_active=TRUE
            ORDER BY updated_at DESC NULLS LAST,id DESC
            LIMIT 1
        """),
        {"asset_id": asset_id},
    )).mappings().first()


async def save(session, asset, record):
    current = await active_model(session, int(asset["id"]))
    dims = dict(record["dimensions"])
    dims.update({
        "template": record["template"],
        "research_date": "2026-08-30",
        "provenance_policy": "missing_dimensions_not_invented",
    })

    fidelity = record["fidelity"]
    specific = fidelity != "L0"

    if fidelity != "L0" and str(asset["identity_status"] or "").upper() != "VERIFIED":
        fidelity = "L0"
        specific = False
        dims["representation"] = "source_record_unlinked_identity_not_measured"

    if current and current["model_uri"]:
        fidelity = current["fidelity_level"] if current["fidelity_level"] not in (None, "L0") else "L2"
        specific = True

    if current:
        existing = current["dimensions"] if isinstance(current["dimensions"], dict) else {}
        merged = {**existing, **dims}
        await session.execute(text("""
            UPDATE asset_models
            SET version='airport-temple-real-twin-v1',
                fidelity_level=:fidelity,
                model_source=:model_source,
                source_url=:source_url,
                dimensions=CAST(:dimensions AS JSONB),
                is_asset_specific=:specific,
                updated_at=NOW()
            WHERE id=:id
        """), {
            "id": int(current["id"]), "fidelity": fidelity,
            "model_source": record["model_source"], "source_url": record["source_url"],
            "dimensions": json.dumps(merged), "specific": specific,
        })
    else:
        await session.execute(text("""
            INSERT INTO asset_models(
                asset_id,model_uri,format,version,fidelity_level,
                model_source,source_url,dimensions,is_asset_specific,
                is_active,created_at,updated_at
            )
            VALUES(
                :asset_id,NULL,'parametric','airport-temple-real-twin-v1',
                :fidelity,:model_source,:source_url,CAST(:dimensions AS JSONB),
                :specific,TRUE,NOW(),NOW()
            )
        """), {
            "asset_id": int(asset["id"]), "fidelity": fidelity,
            "model_source": record["model_source"], "source_url": record["source_url"],
            "dimensions": json.dumps(dims), "specific": specific,
        })

    return fidelity


async def main():
    async with SessionLocal() as session:
        matched = l1 = l0 = 0
        missing = []

        for record in RECORDS:
            asset = await find_asset(session, record)
            if not asset:
                missing.append(record["asset_code"])
                print("MISSING:", record["asset_code"])
                continue

            fidelity = await save(session, asset, record)
            matched += 1
            if fidelity == "L0":
                l0 += 1
            else:
                l1 += 1
            print(asset["asset_code"], "|", asset["name"], "|", fidelity, "|", record["template"])

        await session.commit()

        print("=" * 72)
        print("AIRPORT + TEMPLE TWIN ENRICHMENT")
        print("matched:", matched)
        print("L1_or_better:", l1)
        print("contextual_L0:", l0)
        print("missing:", len(missing))
        for code in missing:
            print(" -", code)


if __name__ == "__main__":
    asyncio.run(main())
