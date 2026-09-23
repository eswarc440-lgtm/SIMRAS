from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.report_truth import compact_report_mapping, is_report_value_present

GOVERNMENT_ENGINEERING: dict[str, dict[str, Any]] = {
    "AP_DAM_00001": {
        "asset_name": "Prakasam Barrage",
        "structural_type": "gated barrage",
        "barrage_length_m": 1232.92,
        "regulator_gate_count": 70,
        "regulator_gate_width_m": 12.19,
        "regulator_gate_height_m": 3.66,
        "left_scour_sluice_count": 6,
        "right_scour_sluice_count": 8,
        "scour_sluice_count": 14,
        "scour_sluice_width_m": 5.18,
        "scour_sluice_height_m": 3.66,
        "completion_year": 1957,
        "source_name": "Government of Andhra Pradesh Water Resources / KRMB project record",
        "source_url": "https://irrigation.ap.gov.in/wrd/home/projects/51",
        "verification_status": "GOVERNMENT_VERIFIED",
    },
    "AP_DAM_00002": {
        "asset_name": "Polavaram Irrigation Project",
        "structural_type": "earth-cum-rock-fill dam plus gated concrete spillway",
        "dam_system_length_m": 2454.0,
        "maximum_dam_height_m": 50.0,
        "spillway_length_m": 1118.4,
        "radial_gate_count": 48,
        "radial_gate_width_m": 16.0,
        "radial_gate_height_m": 20.0,
        "powerhouse_installed_capacity_mw": 960,
        "power_unit_count": 12,
        "power_unit_capacity_mw": 80,
        "live_reservoir_capacity_tmc": 75.2,
        "spillway_design_discharge_cumec": 141435,
        "source_name": "Polavaram Project Authority",
        "source_url": "https://ppa.gov.in/WPSCore/Common/WebPages/Home/AboutProject.aspx",
        "verification_status": "GOVERNMENT_VERIFIED",
    },
    "AP_DAM_NWDP_AP01VH0059": {
        "asset_name": "Srisailam Project",
        "structural_type": "concrete gravity dam",
        "dam_length_m": 512.0,
        "dam_height_m": 145.0,
        "radial_crest_gate_count": 12,
        "radial_gate_width_m": 18.3,
        "radial_gate_height_m": 16.7,
        "river_sluice_count": 2,
        "river_sluice_width_m": 3.65,
        "river_sluice_height_m": 9.14,
        "gross_storage_mcm": 6110.9,
        "live_storage_mcm": 6014.17,
        "designed_spillway_capacity_m3s": 38369,
        "source_name": "Central Water Commission / official project engineering record",
        "verification_status": "GOVERNMENT_VERIFIED",
    },
    "AP_DAM_WRIS_AP01HH0062": {
        "asset_name": "Somasila Reservoir",
        "structural_type": "concrete gravity dam",
        "dam_length_m": 760.0,
        "dam_height_m": 39.0,
        "gross_storage_mcm": 2208.37,
        "live_storage_mcm": 1994.1,
        "designed_spillway_capacity_m3s": 22375,
        "source_name": "Central Water Commission / official static engineering record",
        "verification_status": "GOVERNMENT_VERIFIED",
    },
    "AP_BAR_WRIS_B00131": {
        "asset_name": "Sir Arthur Cotton Barrage",
        "structural_type": "four-arm gated barrage on RCC raft",
        "total_length_m": 3592.67,
        "height_m": 10.6,
        "gate_count": 175,
        "gate_width_m": 18.29,
        "gate_height_m": 3.34,
        "road_width_m": 7.50,
        "dowleswaram_arm_length_m": 1437.92,
        "dowleswaram_arm_vent_count": 70,
        "ralli_arm_length_m": 884.45,
        "ralli_arm_vent_count": 43,
        "madduru_arm_length_m": 469.66,
        "madduru_arm_vent_count": 23,
        "vijjeswaram_arm_length_m": 800.64,
        "vijjeswaram_arm_vent_count": 39,
        "source_name": "ICID technical paper + Government of Andhra Pradesh expert committee",
        "verification_status": "VERIFIED_SOURCE_BACKED",
    },
    "AP_AIR_VOBZ": {
        "asset_name": "Vijayawada Airport",
        "icao_code": "VOBZ",
        "runway_designation": "08/26",
        "runway_length_m": 3360,
        "runway_width_m": 45,
        "runway_strip_length_m": 3480,
        "runway_strip_width_m": 280,
        "runway_surface": "asphalt",
        "heading_deg": 77.75,
        "source_name": "Airports Authority of India eAIP",
        "source_url": "https://aim-india.aai.aero/",
        "verification_status": "GOVERNMENT_VERIFIED",
    },
    "AP_AIR_VOTP": {
        "asset_name": "Tirupati Airport",
        "icao_code": "VOTP",
        "runway_designation": "08/26",
        "runway_length_m": 2285,
        "runway_width_m": 45,
        "runway_strip_length_m": 2405,
        "runway_strip_width_m": 150,
        "runway_surface": "asphalt",
        "heading_deg": 81.5,
        "source_name": "Airports Authority of India eAIP",
        "source_url": "https://aim-india.aai.aero/",
        "verification_status": "GOVERNMENT_VERIFIED",
    },
    "AP_TEMPLE_SRIKALAHASTI": {
        "asset_name": "Sri Kalahasteeswara Swamy Temple",
        "main_gopuram_height_m": 36.5,
        "main_gopuram_height_ft": 120,
        "pathala_ganapathi_depth_ft": 20,
        "source_name": "Sri Kalahasti Temple official site",
        "source_url": "https://srikalahasthitemple.com/history/",
        "verification_status": "SOURCE_REPORTED",
    },
    "AP_TEMPLE_TIRUMALA": {
        "asset_name": "Sri Venkateswara Swamy Temple, Tirumala",
        "complex_area_acres": 16.2,
        "main_entrance_height_ft": 50,
        "gopuram_tiers": 7,
        "source_name": "Tirumala Tirupati Devasthanams published temple profile",
        "source_url": "https://www.tirumala.org/TTDTempleHistory.aspx",
        "verification_status": "SOURCE_REPORTED",
    },
}


def _real_observations(environment: dict[str, Any] | None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, raw in (environment or {}).items():
        if not isinstance(raw, dict):
            if is_report_value_present(raw):
                result[key] = raw
            continue
        if raw.get("is_estimated") is True:
            continue
        quality = str(raw.get("quality_flag") or "").upper()
        source_type = str(raw.get("source_type") or "").upper()
        if "SYNTHETIC" in quality or "SYNTHETIC" in source_type:
            continue
        compacted = compact_report_mapping(raw)
        if compacted:
            result[key] = compacted
    return result


def _real_inspection(inspection: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(inspection, dict) or inspection.get("is_synthetic") is True:
        return {}
    return compact_report_mapping(inspection)


def _real_maintenance(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict) or row.get("is_synthetic") is True:
            continue
        compacted = compact_report_mapping(row)
        if compacted:
            result.append(compacted)
    return result


def _eligible_ml(ai: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(ai, dict):
        return {}

    # Public reports must not turn a transfer model or transparent engineering
    # rules into a locally validated condition assessment. A prediction is
    # published here only after the runtime explicitly marks local validation.
    if ai.get("model_validated") is not True:
        return {}
    if str(ai.get("training_scope") or "") != "LOCAL_ANDHRA_PRADESH_VALIDATION":
        return {}

    keys = (
        "health_score",
        "health_lower_bound",
        "health_upper_bound",
        "risk_score",
        "risk_level",
        "confidence",
        "remaining_life_years",
        "rul_lower_bound",
        "rul_upper_bound",
        "model_name",
        "model_version",
        "feature_version",
        "training_scope",
        "prediction_method",
        "prediction_time",
        "forecast_horizon_years",
    )
    return compact_report_mapping({key: ai.get(key) for key in keys})


def build_real_report_payload(
    asset_code: str,
    twin: dict[str, Any],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a selected-asset report containing only displayable real evidence.

    Absence is represented by omission, never by a fabricated replacement or
    a public-facing 'not available' row.
    """

    asset = compact_report_mapping(deepcopy(twin.get("asset") or {}))
    static = compact_report_mapping(deepcopy(twin.get("static") or {}))
    engineering = compact_report_mapping(deepcopy(GOVERNMENT_ENGINEERING.get(asset_code, {})))
    inspection = _real_inspection(twin.get("inspection"))
    maintenance = _real_maintenance(twin.get("maintenance"))
    environment = _real_observations(twin.get("environment"))
    ml_prediction = _eligible_ml(twin.get("ai"))
    twin_state = compact_report_mapping(deepcopy(twin.get("twin") or {}))
    evidence_state = compact_report_mapping(deepcopy(evidence or {}))

    payload: dict[str, Any] = {
        "asset_code": asset_code,
        "asset": asset,
        "official_asset_facts": static,
        "government_engineering": engineering,
        "digital_twin": twin_state,
        "real_environment_observations": environment,
        "real_inspection": inspection,
        "real_maintenance": maintenance,
        "evidence": evidence_state,
        "generated_at": twin.get("generated_at"),
    }

    if ml_prediction:
        payload["ml_prediction"] = ml_prediction

    return compact_report_mapping(payload)
