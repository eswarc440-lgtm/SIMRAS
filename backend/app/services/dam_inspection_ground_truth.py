from __future__ import annotations

from datetime import date
from typing import Any


# Public authoritative sources used to define the inspection schema and seed
# candidate labels. These records are metadata only; SIMRAS does not promote
# a row to training ground truth until an asset-specific inspection event with
# traceable date/report context is available.
_PUBLIC_SOURCES: tuple[dict[str, Any], ...] = (
    {
        "source_key": "cwc_safety_inspection_guidelines_2018",
        "agency": "Central Water Commission",
        "title": "Guidelines for Safety Inspection of Dams",
        "document_type": "INSPECTION_GUIDELINE",
        "url": "https://damsafety.cwc.gov.in/ecm-includes/PDFs/Guidelines_for_Safety_Inspection_of_Dams.pdf",
        "is_authoritative": True,
        "use": "Inspection workflow, components, observations and reporting structure",
    },
    {
        "source_key": "drip_dsrp_standard_format",
        "agency": "Central Water Commission / DRIP",
        "title": "DSRP Inspection Standard Format",
        "document_type": "INSPECTION_TEMPLATE",
        "url": "https://damsafety.cwc.gov.in/index.php?origin=front-end&page=Dashboard&tp=1",
        "is_authoritative": True,
        "use": "Dam Safety Review Panel inspection structure",
    },
    {
        "source_key": "drip_tc3_category_register_2024",
        "agency": "Central Water Commission / DRIP",
        "title": "Agenda Item of 3rd Meeting of Technical Committee of DRIP II",
        "document_type": "TECHNICAL_COMMITTEE_AGENDA",
        "url": "https://drip.cwc.gov.in/ecm-includes/Detailed_Agenda_3rd_TC_meeting.pdf",
        "is_authoritative": True,
        "use": "Historical AP dam/barrage Category-II candidate labels; not direct inspection-event ground truth",
    },
    {
        "source_key": "drip_ap_dsrp_constitution",
        "agency": "Andhra Pradesh Water Resources Department / CWC DRIP",
        "title": "DSRP Andhra Pradesh",
        "document_type": "DSRP_CONSTITUTION",
        "url": "https://damsafety.cwc.gov.in/ecm-includes/PDFs/DRIP_II/dsrp/AP-WRd-DSRP.pdf",
        "is_authoritative": True,
        "use": "Authority/provenance for Andhra Pradesh DSRP reviews",
    },
    {
        "source_key": "drip_dashboard",
        "agency": "Central Water Commission / DRIP",
        "title": "DRIP Dam Safety Dashboard",
        "document_type": "OFFICIAL_PORTAL",
        "url": "https://damsafety.cwc.gov.in/index.php?origin=front-end&page=Dashboard&tp=1",
        "is_authoritative": True,
        "use": "Official DRIP project, guidance and inspection-resource registry",
    },
    {
        "source_key": "cwc_kgbo",
        "agency": "Central Water Commission - Krishna Godavari Basin Organisation",
        "title": "Krishna Godavari Basin Organisation",
        "document_type": "OFFICIAL_ORGANISATION_PAGE",
        "url": "https://cwc.gov.in/en/kgbo/about",
        "is_authoritative": True,
        "use": "AP hydrology and basin-monitoring provenance",
    },
    {
        "source_key": "cwc_gundlakamma_monitoring_2023",
        "agency": "Central Water Commission - Krishna and Godavari Basin Organisation",
        "title": "Monitoring Report on Kandula Obula Reddy Gundlakamma Reservoir Project, Andhra Pradesh",
        "document_type": "CWC_PROJECT_MONITORING_REPORT",
        "url": "https://pmksy.mowr.gov.in/cadwm/VisitReport/2024214-1059-CWC_28_1_24-08-2023_PartII_D_4131_1688733757259.pdf",
        "is_authoritative": True,
        "use": "Dated field visit with source-reported component condition findings",
    },
    {
        "source_key": "ndsa_cwc_srisailam_safety_inspection_2024",
        "agency": "NDSA / Central Water Commission / Andhra Pradesh",
        "title": "Department of Water Resources Annual Report 2024-25 - Srisailam safety inspection record",
        "document_type": "OFFICIAL_ANNUAL_REPORT_INSPECTION_RECORD",
        "url": "https://www.jalshakti-dowr.gov.in/static/uploads/2024/05/fc00cd887135cf39b2005ccf1539e0e5.pdf",
        "is_authoritative": True,
        "use": "Confirms dated Srisailam safety inspection; public component findings not present in this source",
    },
)


# Annexure-IV of the official DRIP technical-committee agenda lists these
# Andhra Pradesh assets as Category II with rehabilitation proposed. This is
# useful historical evidence, but it is deliberately NOT marked training
# eligible because the agenda does not itself give an asset-specific physical
# inspection date and component-level officer findings for each row.
_AP_CATEGORY_II_CANDIDATES: tuple[str, ...] = (
    "Srisailam Project – PART - A",
    "Sir Arthur Cotton Barrage",
    "Raiwada Reservoir",
    "Gundlakamma Reservoir",
    "Velugodu Balancing Reservoir",
    "Alaganur Balancing Reservoir",
    "Gotta Barrage",
    "Owk Reservoir complex",
    "Gajuladinne Project",
    "Somasila Reservoir",
    "Chitravathi Balancing Reservoir",
    "Mid Pennar Stage-I",
)


# These are stronger than category-register candidates because each row has a
# real date and an authoritative source. Training eligibility is task-specific:
# Gundlakamma supplies a directly observed/reported gate-condition label, while
# Srisailam only confirms that a safety inspection occurred and therefore stays
# non-trainable until the component findings/report are linked.
_DATED_PUBLIC_INSPECTION_EVENTS: tuple[dict[str, Any], ...] = (
    {
        "source_key": "cwc_gundlakamma_monitoring_2023",
        "asset_name_reported": "Kandula Obula Reddy Gundlakamma Reservoir Project",
        "inspection_date": date(2023, 6, 20),
        "inspection_type": "CWC_PROJECT_MONITORING_FIELD_VISIT",
        "inspection_category": None,
        "overall_condition": None,
        "inspector_agency": "Central Water Commission / Andhra Pradesh Water Resources Department",
        "authority_level": "CWC_KGBO_FIELD_MONITORING",
        "quality_flag": "SOURCE_REPORTED_COMPONENT_FINDING",
        "is_official": True,
        "is_synthetic": False,
        "training_eligible": True,
        "label_scope": "COMPONENT_MONITORING_FINDING",
        "reason_not_training_eligible": None,
        "recommended_action": "Restore washed-out spillway gate components and complete required gate repairs.",
        "source_page": "9",
        "findings": [
            {
                "component_name": "gates",
                "condition_state": "RESTORATION_REQUIRED",
                "deficiency_type": "WASHED_OUT_GATES",
                "severity": "MAJOR",
                "finding_text": "Structures (gates) were reported completed but under restoration of washed-out gates.",
                "recommended_action": "Restore damaged/washed-out gate components before relying on normal reservoir operation.",
                "source_page": "9",
                "quality_flag": "SOURCE_REPORTED_COMPONENT_FINDING",
                "is_official": True,
                "is_synthetic": False,
            }
        ],
    },
    {
        "source_key": "ndsa_cwc_srisailam_safety_inspection_2024",
        "asset_name_reported": "Srisailam Project",
        "inspection_date": date(2024, 2, 7),
        "inspection_type": "NDSA_CWC_SAFETY_INSPECTION",
        "inspection_category": None,
        "overall_condition": None,
        "inspector_agency": "NDSA / CWC / CSMRS / KRMB / Governments of Telangana and Andhra Pradesh",
        "authority_level": "NDSA_CWC_SAFETY_INSPECTION",
        "quality_flag": "OFFICIAL_INSPECTION_EVENT_CONFIRMED",
        "is_official": True,
        "is_synthetic": False,
        "training_eligible": False,
        "label_scope": "INSPECTION_EVENT_ONLY",
        "reason_not_training_eligible": (
            "The official annual report confirms the 7-9 February 2024 safety inspection, "
            "but public component-level findings from that inspection are not linked in this source."
        ),
        "recommended_action": None,
        "source_page": "69",
        "findings": [],
    },
)


def load_public_source_registry() -> list[dict[str, Any]]:
    """Return public authoritative sources used by the inspection pipeline."""

    return [dict(source) for source in _PUBLIC_SOURCES]


def load_candidate_labels() -> list[dict[str, Any]]:
    """Return public AP candidate labels without overstating them as training GT.

    The DRIP technical-committee category register is useful for asset matching
    and historical validation. It is not equivalent to a dated physical
    inspection report, so every row remains ``training_eligible=False`` until
    the underlying inspection/DSRP report is obtained and linked.
    """

    source = next(
        source
        for source in _PUBLIC_SOURCES
        if source["source_key"] == "drip_tc3_category_register_2024"
    )

    return [
        {
            "asset_name_reported": name,
            "inspection_category": "II",
            "label_scope": "DRIP_REHABILITATION_CATEGORY_REGISTER",
            "source_key": source["source_key"],
            "source_url": source["url"],
            "source_page": "Annexure-IV / page 22",
            "authority_level": "CWC_DRIP_TECHNICAL_COMMITTEE",
            "quality_flag": "SOURCE_REPORTED_CATEGORY",
            "is_official": True,
            "is_synthetic": False,
            "training_eligible": False,
            "reason_not_training_eligible": (
                "Official category-register evidence is available, but a dated "
                "asset-specific physical inspection report with component-level "
                "findings has not yet been linked."
            ),
        }
        for name in _AP_CATEGORY_II_CANDIDATES
    ]


def load_dated_public_inspection_events() -> list[dict[str, Any]]:
    """Return dated authoritative inspection/monitoring events.

    ``training_eligible`` is deliberately scoped to the label actually observed.
    A component-level monitoring finding may train a component-condition model,
    but it does not become an overall dam-safety category or structural-health
    label unless the source explicitly reports that outcome.
    """

    sources = {source["source_key"]: source for source in _PUBLIC_SOURCES}
    rows: list[dict[str, Any]] = []

    for event in _DATED_PUBLIC_INSPECTION_EVENTS:
        row = dict(event)
        source = sources[row["source_key"]]
        row["source_url"] = source["url"]
        row["source_title"] = source["title"]
        row["findings"] = [dict(finding) for finding in event["findings"]]
        rows.append(row)

    return rows
