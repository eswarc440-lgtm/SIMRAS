from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader


# ============================================================
# SIMRAS AP BRIDGE OFFICIAL / PUBLIC DATA IMPORTER
# DOES NOT MODIFY FRONTEND
# DOES NOT MODIFY EXISTING PREDICTIONS
# ============================================================

PROJECT = Path.cwd()

ROOT = PROJECT / "backend" / "data"
OUT = ROOT / "external_bridge_sources"

RAW = OUT / "raw"
PDF = OUT / "pdf"
TEXT = OUT / "extracted_text"
NORMALIZED = OUT / "normalized"
REPOS = PROJECT / "external_repos"

for d in [
    OUT,
    RAW,
    PDF,
    TEXT,
    NORMALIZED,
    REPOS,
]:
    d.mkdir(parents=True, exist_ok=True)


session = requests.Session()
session.headers.update({
    "User-Agent":
        "SIMRAS Academic Bridge Research/1.0"
})


def get(url, timeout=60):

    try:

        r = session.get(
            url,
            timeout=timeout,
            allow_redirects=True
        )

        r.raise_for_status()

        return r

    except Exception as e:

        print("FAILED:", url)
        print("       ", e)

        return None


def download(url, path):

    r = get(url)

    if r is None:
        return False

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_bytes(r.content)

    print(
        "DOWNLOADED:",
        path,
        f"({len(r.content):,} bytes)"
    )

    return True


manifest = []


def register(
    source,
    authority,
    role,
    url,
    local,
    evidence_type,
    authoritative=True,
):

    manifest.append({
        "source": source,
        "authority": authority,
        "role": role,
        "url": url,
        "local_path": str(local),
        "evidence_type": evidence_type,
        "authoritative": authoritative,
        "imported_at": datetime.now().isoformat(),
    })


# ============================================================
# 1. APWRIMS
# ============================================================

print("\n================================================")
print("1. APWRIMS RAINFALL")
print("================================================")

today = datetime.now().strftime("%Y%m%d")

apwrims_url = (
    "https://apwrims.ap.gov.in/mis/rainfall/summary"
    "?cType=DISTRICT"
    f"&endDate={today}"
    "&hierarchyId=RAINFALL_APSDPS_ADMIN"
    "&location=AP%23%236f86292b-dd9a-4987-bb8f-c3940263b349"
    "&locationHierarchy=ADMIN"
    "&locationLevel=STATE"
    "&pType=STATE"
    "&sourceOfData=AWS"
    "&startDate=20260601"
    "&timePeriod=monsoon"
    "&viewType=ADMIN"
)

r = get(apwrims_url)

if r is not None:

    ap_html = RAW / "APWRIMS_RAINFALL.html"
    ap_html.write_bytes(r.content)

    register(
        "APWRIMS Rainfall",
        "Government of Andhra Pradesh",
        "rainfall",
        apwrims_url,
        ap_html,
        "OFFICIAL_DYNAMIC_DATA",
    )

    try:

        tables = pd.read_html(
            StringIO(r.text)
        )

        print(
            "APWRIMS tables:",
            len(tables)
        )

        for i, df in enumerate(tables):

            path = (
                NORMALIZED /
                f"APWRIMS_RAINFALL_TABLE_{i:02d}.csv"
            )

            df.to_csv(
                path,
                index=False
            )

    except Exception as e:

        print(
            "APWRIMS table parsing:",
            e
        )


# ============================================================
# 2. APSAC / APSSDI
# ============================================================

print("\n================================================")
print("2. APSAC / APSSDI")
print("================================================")

apsac_pages = {
    "APSAC_APSSDI":
        "https://apsac.ap.gov.in/?page_id=6966",

    "APSAC_GATISHAKTI":
        "https://apsac.ap.gov.in/?page_id=1075",

    "APSAC_WMS":
        (
            "https://apsac.ap.gov.in/"
            "geoserver/gatishakti/wms"
            "?service=WMS"
            "&version=1.3.0"
            "&request=GetCapabilities"
        ),
}

for name, url in apsac_pages.items():

    path = RAW / f"{name}.xml"

    if download(url, path):

        register(
            name,
            "APSAC / Government of Andhra Pradesh",
            "official_gis",
            url,
            path,
            "OFFICIAL_GIS_REFERENCE",
        )


# ============================================================
# 3. APRDC OFFICIAL REPORTS
# ============================================================

print("\n================================================")
print("3. APRDC REPORTS / DPR MATERIAL")
print("================================================")

aprdc = {
    "APRDC_KAKINADA_RAJAHMUNDRY":
        (
            "https://aprdc.ap.gov.in/Documents/"
            "DISCLOSURES/ENVIRONMENT/Rajamundry.pdf"
        ),

    "APRDC_ANAKAPALLE_ATCHUTAPURAM":
        (
            "https://aprdc.ap.gov.in/Documents/"
            "DISCLOSURES/ENVIRONMENT/"
            "Draft_AA_Road_Env.pdf"
        ),
}

for name, url in aprdc.items():

    path = PDF / f"{name}.pdf"

    if download(url, path):

        register(
            name,
            "APRDC / Government of Andhra Pradesh",
            "engineering_traffic_hydrology",
            url,
            path,
            "OFFICIAL_DPR_REPORT",
        )


aprdc_dashboards = {
    "APRDC_GREENFIELD":
        (
            "https://aprdc.ap.gov.in/"
            "CMDASHBOARDREPORTS/"
            "GreenFieldExpressReport.aspx"
        ),

    "APRDC_NH_DPR_STATUS":
        (
            "https://aprdc.ap.gov.in/"
            "CMDASHBOARDREPORTS/"
            "In_PrincipleReport.aspx"
        ),
}

for name, url in aprdc_dashboards.items():

    path = RAW / f"{name}.html"

    if download(url, path):

        register(
            name,
            "APRDC / Government of Andhra Pradesh",
            "project_traffic_metadata",
            url,
            path,
            "OFFICIAL_PROJECT_DATA",
        )


# ============================================================
# 4. NHAI
# ============================================================

print("\n================================================")
print("4. NHAI PROJECT / MAINTENANCE DATA")
print("================================================")

nhai_completed = (
    "https://nhai.gov.in/nhai/sites/default/"
    "files/mix_file/"
    "Completed_PCC_PCOD_04-2025.pdf"
)

path = PDF / "NHAI_COMPLETED_PROJECTS_AP.pdf"

if download(
    nhai_completed,
    path
):

    register(
        "NHAI Completed Projects",
        "National Highways Authority of India",
        "bridge_projects_maintenance",
        nhai_completed,
        path,
        "OFFICIAL_NHAI_PROJECT_RECORD",
    )


nhai_ap_page = (
    "https://nhai.gov.in/nhai/"
    "taxonomy/term/304"
)

path = RAW / "NHAI_ANDHRA_PRADESH.html"

if download(
    nhai_ap_page,
    path
):

    register(
        "NHAI Andhra Pradesh",
        "National Highways Authority of India",
        "ap_national_highway_projects",
        nhai_ap_page,
        path,
        "OFFICIAL_NHAI_PORTAL",
    )


# ============================================================
# 5. NHTIS TRAFFIC / PCU
# ============================================================

print("\n================================================")
print("5. NHAI TOLL / TRAFFIC DATA")
print("================================================")

# Known AP / nearby AP-corridor toll IDs.
# More can be appended without changing importer.

toll_ids = [
    203,
    228,
    246,
    247,
    376,
    451,
    4557,
    6633,
    6659,
]

traffic_rows = []

for toll_id in toll_ids:

    url = (
        "https://tis.nhai.gov.in/"
        "TollInformation.aspx?"
        f"TollPlazaID={toll_id}"
    )

    r = get(url)

    if r is None:
        continue

    local = (
        RAW /
        f"NHTIS_TOLL_{toll_id}.html"
    )

    local.write_bytes(r.content)

    soup = BeautifulSoup(
        r.text,
        "html.parser"
    )

    text = " ".join(
        soup.stripped_strings
    )

    traffic = re.search(
        r"Traffic\s*\(PCU/day\)"
        r"\s*[:\-]?\s*([\d,]+)",
        text,
        re.I
    )

    target = re.search(
        r"Target\s+Traffic"
        r".{0,30}?([\d,]+)",
        text,
        re.I
    )

    nh = re.search(
        r"\bNH[- ]?(\d+[A-Z]?)\b",
        text,
        re.I
    )

    traffic_rows.append({
        "toll_plaza_id": toll_id,

        "nh_number":
            nh.group(1)
            if nh else None,

        "traffic_pcu_day":
            traffic.group(1).replace(",", "")
            if traffic else None,

        "target_traffic_pcu_day":
            target.group(1).replace(",", "")
            if target else None,

        "source_url": url,

        "evidence_role":
            "CORRIDOR_TRAFFIC_NOT_BRIDGE_SPECIFIC",
    })

    register(
        f"NHTIS Toll {toll_id}",
        "NHAI",
        "corridor_traffic",
        url,
        local,
        "OFFICIAL_CORRIDOR_TRAFFIC",
    )


pd.DataFrame(
    traffic_rows
).to_csv(
    NORMALIZED /
    "NHTIS_AP_TRAFFIC.csv",
    index=False
)


# ============================================================
# 6. MORTH / IBMS / RAMS
# ============================================================

print("\n================================================")
print("6. MORTH IBMS / RAMS PORTALS")
print("================================================")

morth = {
    "MORTH_IBMS":
        "https://morth.nic.in/search/node/ibms",

    "MORTH_RAMS":
        "https://morth.nic.in/search/node/rams",

    "MORTH_BRIDGE_INSPECTION":
        (
            "https://morth.nic.in/search/"
            "node/bridge%20inspection"
        ),

    "MORTH_TRAFFIC_CENSUS":
        (
            "https://morth.nic.in/search/"
            "node/traffic%20census"
        ),
}

for name, url in morth.items():

    path = RAW / f"{name}.html"

    if download(url, path):

        register(
            name,
            "Ministry of Road Transport and Highways",
            "inspection_condition_traffic",
            url,
            path,
            "OFFICIAL_PORTAL_INDEX",
        )


# ============================================================
# 7. EXISTING NWDP / AP WATER DATA IN SIMRAS
# ============================================================

print("\n================================================")
print("7. EXISTING NWDP / AP HYDROLOGY DATA")
print("================================================")

local_sources = [
    (
        ROOT /
        "official/dam/hydrology/river/"
        "ap_river_discharge_2001_2025.csv",
        "river_discharge"
    ),

    (
        ROOT /
        "official/dam/hydrology/river/"
        "ap_river_velocity_discharge_2021_2025.csv",
        "river_velocity_discharge"
    ),

    (
        ROOT /
        "raw/nwdp/"
        "ap_rainfall_hourly_2026_2030.csv",
        "rainfall_station"
    ),

    (
        ROOT /
        "raw/nwdp/"
        "godavari_river_level_hourly_2026_2030.csv",
        "river_level"
    ),

    (
        ROOT /
        "raw/nwdp/"
        "pennar_river_level_hourly_2026_2030.csv",
        "river_level"
    ),
]

for source, role in local_sources:

    if not source.exists():
        print(
            "MISSING LOCAL:",
            source
        )
        continue

    destination = (
        NORMALIZED /
        source.name
    )

    shutil.copy2(
        source,
        destination
    )

    print(
        "IMPORTED:",
        source.name
    )

    register(
        source.name,
        "NWDP / Andhra Pradesh Surface Water",
        role,
        "LOCAL_EXISTING_GOVERNMENT_DATA",
        destination,
        "OFFICIAL_HYDROLOGY_DATA",
    )


# ============================================================
# 8. PUBLIC GITHUB REPOSITORIES
# ============================================================

print("\n================================================")
print("8. PUBLIC REPOSITORIES")
print("================================================")


def clone_or_update(
    url,
    destination
):

    if destination.exists():

        try:

            subprocess.run(
                [
                    "git",
                    "-C",
                    str(destination),
                    "pull",
                    "--ff-only"
                ],
                check=False
            )

        except Exception:
            pass

        return

    subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            url,
            str(destination)
        ],
        check=False
    )


# NHAI-derived traffic dataset
toll_repo = (
    REPOS /
    "toll-plazas-india"
)

clone_or_update(
    "https://github.com/"
    "geohacker/toll-plazas-india.git",
    toll_repo
)


# Bridge ML methodology reference ONLY
risk_repo = (
    REPOS /
    "bridge-risk-xgboost"
)

clone_or_update(
    "https://github.com/"
    "twiese86/bridge-risk-xgboost.git",
    risk_repo
)


# Indian traffic CV reference ONLY
itd_repo = (
    REPOS /
    "ITD-Indian-traffic-dataset"
)

clone_or_update(
    "https://github.com/"
    "teg-iitr/"
    "ITD-Indian-traffic-dataset.git",
    itd_repo
)


# ============================================================
# FIND NEWEST NON-EMPTY NHAI TRAFFIC REPO SNAPSHOT
# ============================================================

print("\nScanning NHAI-derived toll repository...")

traffic_candidates = []

if toll_repo.exists():

    for csv_file in (
        toll_repo /
        "data"
    ).glob(
        "*/tolls-with-metadata.csv"
    ):

        if csv_file.stat().st_size > 100:

            try:

                folder_date = datetime.strptime(
                    csv_file.parent.name,
                    "%d-%m-%Y"
                )

                traffic_candidates.append(
                    (
                        folder_date,
                        csv_file
                    )
                )

            except Exception:
                pass


if traffic_candidates:

    traffic_candidates.sort(
        reverse=True,
        key=lambda x: x[0]
    )

    newest_date, newest_file = (
        traffic_candidates[0]
    )

    print(
        "Newest usable toll snapshot:",
        newest_file
    )

    try:

        df = pd.read_csv(
            newest_file
        )

        # Find AP using every textual column rather
        # than assuming one exact schema.
        text = (
            df.astype(str)
            .agg(
                " ".join,
                axis=1
            )
        )

        mask = text.str.contains(
            r"Andhra\s*Pradesh|\bAP\b",
            case=False,
            regex=True,
            na=False
        )

        ap = df[mask].copy()

        out_file = (
            NORMALIZED /
            "PUBLIC_REPO_NHAI_AP_TOLL_TRAFFIC.csv"
        )

        ap.to_csv(
            out_file,
            index=False
        )

        print(
            "AP rows from public NHAI-derived repo:",
            len(ap)
        )

        register(
            "geohacker/toll-plazas-india",
            "Public repo derived from NHAI TIS",
            "traffic_reference",
            (
                "https://github.com/"
                "geohacker/toll-plazas-india"
            ),
            out_file,
            "SECONDARY_NHAI_DERIVED_DATA",
            authoritative=False,
        )

    except Exception as e:

        print(
            "Traffic repo parsing failed:",
            e
        )

else:

    print(
        "No non-empty toll CSV snapshot found."
    )


# ============================================================
# 9. EXTRACT TEXT FROM GOVERNMENT PDFS
# ============================================================

print("\n================================================")
print("9. PDF TEXT EXTRACTION")
print("================================================")

pdf_summary = []

for pdf in PDF.glob("*.pdf"):

    try:

        reader = PdfReader(
            str(pdf)
        )

        chunks = []

        for page_no, page in enumerate(
            reader.pages
        ):

            try:

                chunks.append(
                    page.extract_text() or ""
                )

            except Exception:
                pass

        text = "\n".join(
            chunks
        )

        textfile = (
            TEXT /
            f"{pdf.stem}.txt"
        )

        textfile.write_text(
            text,
            encoding="utf-8",
            errors="ignore"
        )

        pdf_summary.append({
            "pdf": pdf.name,
            "pages": len(reader.pages),
            "characters": len(text),
            "text_file": str(textfile),
        })

        print(
            "EXTRACTED:",
            pdf.name,
            "pages=",
            len(reader.pages)
        )

    except Exception as e:

        print(
            "PDF ERROR:",
            pdf.name,
            e
        )


pd.DataFrame(
    pdf_summary
).to_csv(
    OUT /
    "PDF_EXTRACTION_SUMMARY.csv",
    index=False
)


# ============================================================
# 10. SEARCH EXTRACTED GOVERNMENT TEXT FOR BRIDGE DATA TERMS
# ============================================================

keywords = {
    "traffic":
        r"\bAADT\b|\bADT\b|PCU|traffic volume|axle load",

    "bridge_geometry":
        r"bridge|span|pier|abutment|carriageway|width",

    "material":
        r"\bRCC\b|\bPSC\b|prestressed|steel|concrete",

    "condition":
        r"crack|spall|corrosion|distress|damage|scour|settlement",

    "maintenance":
        r"maintenance|repair|rehabilitation|strengthening|replacement",

    "inspection":
        r"inspection|condition survey|visual survey",
}


search_rows = []

for text_file in TEXT.glob("*.txt"):

    content = text_file.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    for category, pattern in keywords.items():

        matches = list(
            re.finditer(
                pattern,
                content,
                re.I
            )
        )

        if not matches:
            continue

        search_rows.append({
            "document": text_file.name,
            "category": category,
            "match_count": len(matches),
        })


pd.DataFrame(
    search_rows
).to_csv(
    OUT /
    "GOVERNMENT_DOCUMENT_DATA_INDEX.csv",
    index=False
)


# ============================================================
# 11. SOURCE MANIFEST
# ============================================================

manifest_df = pd.DataFrame(
    manifest
)

manifest_df.to_csv(
    OUT /
    "SOURCE_MANIFEST.csv",
    index=False
)


# ============================================================
# 12. IMPORT INVENTORY
# ============================================================

inventory = []

for file in OUT.rglob("*"):

    if file.is_file():

        inventory.append({
            "file":
                str(
                    file.relative_to(PROJECT)
                ),

            "bytes":
                file.stat().st_size,

            "extension":
                file.suffix.lower(),
        })


pd.DataFrame(
    inventory
).to_csv(
    OUT /
    "IMPORT_INVENTORY.csv",
    index=False
)


print("\n================================================")
print(" SIMRAS BRIDGE SOURCE IMPORT COMPLETE")
print("================================================")

print(
    "Output:",
    OUT
)

print(
    "Sources registered:",
    len(manifest_df)
)

print(
    "Files imported:",
    len(inventory)
)

print("\nImportant files:")

for f in [
    "SOURCE_MANIFEST.csv",
    "IMPORT_INVENTORY.csv",
    "GOVERNMENT_DOCUMENT_DATA_INDEX.csv",
    "PDF_EXTRACTION_SUMMARY.csv",
    "normalized/NHTIS_AP_TRAFFIC.csv",
    "normalized/PUBLIC_REPO_NHAI_AP_TOLL_TRAFFIC.csv",
]:

    print(
        " ",
        OUT / f
    )

print("\nNOTE:")
print(
    "Public repository data is staged as secondary evidence."
)

print(
    "No prediction confidence has been modified."
)

