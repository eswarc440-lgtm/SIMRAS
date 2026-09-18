from __future__ import annotations

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
