from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from collections import deque
from datetime import datetime
from io import StringIO
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

# ============================================================
# SIMRAS OFFICIAL BRIDGE EVIDENCE ACQUISITION
# Andhra Pradesh + Government of India
# ============================================================

ROOT = Path("backend/data")
OUT = ROOT / "official/bridge_evidence_20260927"
RAW = OUT / "raw"
DOCS = OUT / "documents"
TEXT = OUT / "extracted_text"

for p in [OUT, RAW, DOCS, TEXT]:
    p.mkdir(parents=True, exist_ok=True)

BRIDGE_FILES = [
    ROOT / "processed/bridge/AP_ALL_BRIDGES_ENVIRONMENT_ENRICHED.csv",
    ROOT / "processed/bridge/AP_ALL_BRIDGES_NUMERIC_PREDICTIONS.csv",
    ROOT / "processed/bridge/AP_ALL_BRIDGES_PRODUCTION_READY.csv",
]

bridge_file = next((p for p in BRIDGE_FILES if p.exists()), None)

if not bridge_file:
    raise SystemExit("No canonical SIMRAS bridge file found.")

bridges = pd.read_csv(bridge_file)

print("\n======================================================")
print(" SIMRAS OFFICIAL GOVERNMENT BRIDGE EVIDENCE PIPELINE")
print("======================================================")
print("Bridge file :", bridge_file)
print("Bridge rows :", len(bridges))


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent":
        "SIMRAS-Academic-Research/1.0 "
        "(public government data acquisition)"
})

TIMEOUT = 35


def fetch(url, **kwargs):
    last = None

    for attempt in range(3):
        try:
            r = session.get(
                url,
                timeout=TIMEOUT,
                allow_redirects=True,
                **kwargs
            )

            r.raise_for_status()
            return r

        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))

    print("FAILED:", url, "-", last)
    return None


# ============================================================
# OFFICIAL SOURCE MANIFEST
# ============================================================

sources = [
    {
        "authority": "Government of Andhra Pradesh",
        "portal": "APWRIMS",
        "role": "rainfall_hydrology",
        "url": "https://apwrims.ap.gov.in/",
        "priority": "HIGH",
    },

    {
        "authority": "Government of Andhra Pradesh",
        "portal": "APWRIMS Rainfall",
        "role": "rainfall",
        "url":
        "https://apwrims.ap.gov.in/mis/rainfall/summary"
        "?cType=DISTRICT"
        "&endDate=20260927"
        "&hierarchyId=RAINFALL_APSDPS_ADMIN"
        "&location=AP%23%236f86292b-dd9a-4987-bb8f-c3940263b349"
        "&locationHierarchy=ADMIN"
        "&locationLevel=STATE"
        "&pType=STATE"
        "&sourceOfData=AWS"
        "&startDate=20260601"
        "&timePeriod=monsoon"
        "&viewType=ADMIN",
        "priority": "HIGH",
    },

    {
        "authority": "Government of Andhra Pradesh",
        "portal": "APSAC APSSDI",
        "role": "official_gis",
        "url": "https://apsac.ap.gov.in/?page_id=6966",
        "priority": "HIGH",
    },

    {
        "authority": "Government of Andhra Pradesh",
        "portal": "APSAC PM GatiShakti",
        "role": "official_gis",
        "url": "https://apsac.ap.gov.in/?page_id=1075",
        "priority": "HIGH",
    },

    {
        "authority": "Government of Andhra Pradesh",
        "portal": "APRDC",
        "role": "engineering_inspection_project_documents",
        "url": "https://aprdc.ap.gov.in/",
        "priority": "HIGH",
    },

    {
        "authority": "Government of Andhra Pradesh",
        "portal": "APRDC Administration",
        "role": "roads_buildings_documents",
        "url": "https://aprdc.ap.gov.in/UI/Administration.aspx",
        "priority": "HIGH",
    },

    {
        "authority": "Government of India",
        "portal": "NHAI Andhra Pradesh",
        "role": "nh_project_dpr_agreements",
        "url": "https://nhai.gov.in/nhai/taxonomy/term/304",
        "priority": "HIGH",
    },

    {
        "authority": "Government of India",
        "portal": "MoRTH IBMS",
        "role": "bridge_condition",
        "url": "https://morth.gov.in/search/node/ibms",
        "priority": "CRITICAL",
    },

    {
        "authority": "Government of India",
        "portal": "MoRTH RAMS",
        "role": "road_asset_management",
        "url": "https://morth.gov.in/search/node/rams",
        "priority": "HIGH",
    },

    {
        "authority": "Government of India",
        "portal": "MoRTH Traffic Census",
        "role": "traffic_aadt",
        "url": "https://morth.gov.in/search/node/traffic%20census",
        "priority": "HIGH",
    },

    {
        "authority": "Government of India",
        "portal": "MoRTH Bridge Inspection",
        "role": "inspection_condition",
        "url": "https://morth.gov.in/search/node/bridge%20inspection",
        "priority": "CRITICAL",
    },
]

pd.DataFrame(sources).to_csv(
    OUT / "OFFICIAL_SOURCE_MANIFEST.csv",
    index=False
)


# ============================================================
# SAVE LANDING PAGES
# ============================================================

print("\n[1/8] Downloading official portal pages...")

portal_records = []

for i, src in enumerate(sources, 1):

    r = fetch(src["url"])

    record = dict(src)
    record["fetch_time"] = datetime.now().isoformat()
    record["status"] = "FAILED"

    if r is not None:

        ext = ".html"

        content_type = r.headers.get("Content-Type", "").lower()

        if "xml" in content_type:
            ext = ".xml"

        path = RAW / f"portal_{i:02d}_{src['portal'].replace(' ','_')}{ext}"

        path.write_bytes(r.content)

        record["status"] = "DOWNLOADED"
        record["http_status"] = r.status_code
        record["bytes"] = len(r.content)
        record["local_file"] = str(path)

    portal_records.append(record)

pd.DataFrame(portal_records).to_csv(
    OUT / "PORTAL_FETCH_RESULTS.csv",
    index=False
)


# ============================================================
# APWRIMS TABLE EXTRACTION
# ============================================================

print("\n[2/8] Extracting APWRIMS rainfall tables...")

apwrims = next(
    x for x in sources
    if x["portal"] == "APWRIMS Rainfall"
)

r = fetch(apwrims["url"])

if r is not None:

    try:

        tables = pd.read_html(StringIO(r.text))

        for i, table in enumerate(tables):
            table.to_csv(
                OUT / f"APWRIMS_RAINFALL_TABLE_{i:02d}.csv",
                index=False
            )

        print("APWRIMS tables:", len(tables))

    except Exception as e:
        print("APWRIMS table extraction:", e)


# ============================================================
# APSAC OFFICIAL WMS CAPABILITIES
# ============================================================

print("\n[3/8] Downloading APSAC official GIS capabilities...")

apsac_layers = [
    "Andhra-RoadNetwork",
    "Andhra-NationalHighway",
    "Andhra-StateHighway",
    "Andhra-MajorRiver",
    "Andhra-River",
    "Andhra-AutomaticRainGauges",
    "Andhra-AutomaticWeatherStations",
    "Andhra-RiverWaterLevelRecorders",
    "Andhra-ClimaticZones",
    "Andhra-Geology250K",
    "Andhra-Soil250k",
]

apsac_rows = []

for layer in apsac_layers:

    url = (
        f"https://apsac.ap.gov.in/geoserver/{layer}/wms"
        "?service=WMS&request=GetCapabilities&version=1.3.0"
    )

    r = fetch(url)

    row = {
        "layer": layer,
        "url": url,
        "authority": "APSAC / Government of Andhra Pradesh",
        "status": "FAILED",
    }

    if r is not None:

        f = RAW / f"APSAC_{layer}_GetCapabilities.xml"
        f.write_bytes(r.content)

        row["status"] = "AVAILABLE"
        row["bytes"] = len(r.content)
        row["local_file"] = str(f)

    apsac_rows.append(row)

pd.DataFrame(apsac_rows).to_csv(
    OUT / "APSAC_LAYER_AVAILABILITY.csv",
    index=False
)


# ============================================================
# GOVERNMENT DOCUMENT CRAWLER
# ============================================================

KEYWORDS = re.compile(
    r"bridge|flyover|rob|rub|traffic|aadt|adt|pcu|"
    r"inspection|condition|rehabil|repair|maintenance|"
    r"dpr|feasibility|structure|structural|bearing|"
    r"expansion.?joint|pier|span|deck|crack|corrosion|"
    r"scour|nh[- ]?\d+",
    re.I
)

DOWNLOAD_EXT = (
    ".pdf", ".csv", ".xlsx", ".xls", ".zip", ".doc", ".docx"
)


def safe_name(text):
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    return text[:170]


document_index = []


def crawl(seed, portal, max_pages=70, max_depth=2, max_docs=180):

    allowed = urlparse(seed).netloc.lower()

    q = deque([(seed, 0)])
    visited = set()
    documents = 0

    while q and len(visited) < max_pages and documents < max_docs:

        url, depth = q.popleft()

        if url in visited:
            continue

        visited.add(url)

        r = fetch(url)

        if r is None:
            continue

        content_type = r.headers.get("Content-Type", "").lower()

        if "text/html" not in content_type:
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.find_all("a", href=True):

            href = urljoin(url, a["href"])
            parsed = urlparse(href)

            if parsed.netloc.lower() != allowed:
                continue

            label = " ".join(a.stripped_strings)

            candidate = f"{label} {href}"

            clean_path = parsed.path.lower()

            is_document = (
                clean_path.endswith(DOWNLOAD_EXT)
                or "sites/default/files" in clean_path
                or "/documents/" in clean_path
            )

            if is_document and KEYWORDS.search(candidate):

                dr = fetch(href)

                if dr is None:
                    continue

                ctype = dr.headers.get("Content-Type", "").lower()

                if (
                    len(dr.content) > 30_000_000
                    or len(dr.content) < 100
                ):
                    continue

                ext = Path(parsed.path).suffix

                if not ext:
                    ext = ".pdf" if "pdf" in ctype else ".bin"

                digest = hashlib.sha1(
                    href.encode("utf-8")
                ).hexdigest()[:10]

                filename = (
                    safe_name(
                        portal + "_" +
                        (label or Path(parsed.path).stem)
                    )
                    + "_" + digest + ext
                )

                dest = DOCS / filename

                if not dest.exists():
                    dest.write_bytes(dr.content)

                document_index.append({
                    "portal": portal,
                    "authority_url": seed,
                    "source_page": url,
                    "document_url": href,
                    "link_text": label,
                    "local_file": str(dest),
                    "bytes": len(dr.content),
                    "content_type": ctype,
                })

                documents += 1

                if documents >= max_docs:
                    break

            elif depth < max_depth:

                # Follow only relevant government pages.
                if KEYWORDS.search(candidate):
                    q.append((href, depth + 1))

    print(
        f"{portal}: pages={len(visited)} documents={documents}"
    )


print("\n[4/8] Crawling APRDC/NHAI/MoRTH documents...")

crawl(
    "https://aprdc.ap.gov.in/",
    "APRDC",
    max_pages=80,
    max_depth=3,
    max_docs=200,
)

crawl(
    "https://nhai.gov.in/nhai/taxonomy/term/304",
    "NHAI_AP",
    max_pages=120,
    max_depth=2,
    max_docs=250,
)

for seed, name in [
    ("https://morth.gov.in/search/node/ibms", "MORTH_IBMS"),
    ("https://morth.gov.in/search/node/rams", "MORTH_RAMS"),
    (
        "https://morth.gov.in/search/node/traffic%20census",
        "MORTH_TRAFFIC",
    ),
    (
        "https://morth.gov.in/search/node/bridge%20inspection",
        "MORTH_INSPECTION",
    ),
]:

    crawl(
        seed,
        name,
        max_pages=50,
        max_depth=2,
        max_docs=100,
    )

pd.DataFrame(document_index).drop_duplicates(
    subset=["document_url"]
).to_csv(
    OUT / "OFFICIAL_DOCUMENT_INDEX.csv",
    index=False
)


# ============================================================
# NHTIS CORRIDOR TRAFFIC / TOLL EVIDENCE
#
# This is corridor evidence, NOT necessarily bridge-specific.
# ============================================================

print("\n[5/8] Downloading known AP NHTIS corridor evidence...")

# Seed AP plazas relevant to existing SIMRAS corridors.
# Additional plazas can be appended later.
toll_ids = [
    203,    # Laxmipuram NH16
    228,    # Kaza NH16
    246,    # Nathavalasa/Vizianagaram NH16
    247,    # Pottipadu NH16
    376,    # Chillakallu NH65
    451,    # Unguturu NH16
    4557,   # Buchireddypalem
    6633,   # Veeravalli NH16
    6659,   # Mopidevi NH216
]

toll_records = []

for tid in toll_ids:

    url = (
        "https://tis.nhai.gov.in/"
        f"TollInformation.aspx?TollPlazaID={tid}"
    )

    r = fetch(url)

    if r is None:
        continue

    path = RAW / f"NHTIS_{tid}.html"
    path.write_bytes(r.content)

    text = BeautifulSoup(r.text, "html.parser").get_text(
        " ",
        strip=True
    )

    traffic = re.search(
        r"Traffic\s*\(PCU/day\)\s*[:\-]?\s*([\d,]+)",
        text,
        re.I,
    )

    highway = re.search(
        r"\bNH[- ]?(\d+[A-Z]?)\b",
        text,
        re.I,
    )

    toll_records.append({
        "toll_plaza_id": tid,
        "url": url,
        "traffic_pcu_day":
            traffic.group(1).replace(",", "")
            if traffic else None,
        "nh_number":
            highway.group(1)
            if highway else None,
        "evidence_role":
            "CORRIDOR_TRAFFIC_PROXY_NOT_BRIDGE_SPECIFIC",
        "local_file": str(path),
    })

pd.DataFrame(toll_records).to_csv(
    OUT / "NHTIS_AP_CORRIDOR_TRAFFIC.csv",
    index=False
)


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

print("\n[6/8] Extracting searchable PDF text...")

pdf_index = []

for pdf in DOCS.glob("*.pdf"):

    status = "OK"
    page_count = 0
    chars = 0

    try:

        reader = PdfReader(str(pdf))
        page_count = len(reader.pages)

        text_parts = []

        # Enough for indexing while avoiding huge DPR extraction.
        for page in reader.pages[:100]:

            try:
                t = page.extract_text() or ""
                text_parts.append(t)
            except Exception:
                pass

        text = "\n".join(text_parts)

        chars = len(text)

        if chars < 100:
            status = "NO_MACHINE_READABLE_TEXT"

        txtfile = TEXT / (pdf.stem + ".txt")
        txtfile.write_text(
            text,
            encoding="utf-8",
            errors="ignore"
        )

    except Exception as e:

        status = "PDF_READ_ERROR"
        txtfile = None

    pdf_index.append({
        "pdf": str(pdf),
        "pages": page_count,
        "text_characters": chars,
        "text_status": status,
        "text_file": str(txtfile) if txtfile else None,
    })

pd.DataFrame(pdf_index).to_csv(
    OUT / "PDF_TEXT_EXTRACTION_INDEX.csv",
    index=False
)


# ============================================================
# MATCH BRIDGE NAMES AGAINST OFFICIAL DOCUMENTS
# ============================================================

print("\n[7/8] Matching 577 bridges against official documents...")


def norm(s):
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        str(s).lower()
    ).strip()


name_col = next(
    (
        c for c in [
            "bridge_name",
            "asset_name",
            "display_name",
            "name",
        ]
        if c in bridges.columns
    ),
    None,
)

if not name_col:
    raise SystemExit("No bridge name column found.")


texts = []

for txt in TEXT.glob("*.txt"):

    try:
        content = txt.read_text(
            encoding="utf-8",
            errors="ignore"
        ).lower()

        texts.append((txt, content))

    except Exception:
        pass


matches = []

for _, row in bridges.iterrows():

    bridge_name = str(row[name_col])

    n = norm(bridge_name)

    # Ignore generic one-word names.
    tokens = [
        x for x in n.split()
        if x not in {
            "bridge",
            "road",
            "flyover",
            "bypass",
            "main",
        }
        and len(x) >= 4
    ]

    if not tokens:
        continue

    # Prefer distinctive 2-4 word sequences.
    phrase = " ".join(tokens[:4])

    for txt, content in texts:

        score = 0

        if phrase and phrase in content:
            score = 100

        else:
            found = sum(
                1 for token in set(tokens)
                if token in content
            )

            if len(set(tokens)):
                score = round(
                    100 * found / len(set(tokens))
                )

        if score >= 60:

            matches.append({
                "bridge_name": bridge_name,
                "asset_code":
                    row.get("asset_code", ""),
                "document":
                    txt.name,
                "name_match_score": score,
                "review_required": True,
            })


pd.DataFrame(matches).to_csv(
    OUT / "BRIDGE_TO_OFFICIAL_DOCUMENT_CANDIDATES.csv",
    index=False
)


# ============================================================
# EVIDENCE COVERAGE / 0.90 TARGET AUDIT
# ============================================================

print("\n[8/8] Building evidence coverage audit...")


def first_nonempty(row, candidates):

    for c in candidates:

        if c not in row.index:
            continue

        v = row[c]

        if pd.notna(v) and str(v).strip().lower() not in {
            "",
            "nan",
            "none",
            "unknown",
            "withheld",
        }:
            return v

    return None


aliases = {

    "built_year": [
        "built_year",
        "completion_year",
        "year_built",
        "construction_year",
    ],

    "material": [
        "material",
        "material_reported",
        "structural_material",
    ],

    "length": [
        "official_length_m",
        "model_length_m",
        "length_m",
        "length_m_derived",
    ],

    "width": [
        "official_width_m",
        "width_m",
        "width_m_reported",
    ],

    "lanes": [
        "lanes",
        "lane_count",
        "lanes_reported",
    ],

    "spans": [
        "span_count",
        "spans",
        "verified_span_count",
    ],

    "piers": [
        "pier_count",
        "verified_pier_count",
    ],

    "traffic": [
        "aadt",
        "aadt_pcu",
        "traffic_pcu_day",
        "traffic_load",
    ],

    "rainfall": [
        "rainfall_ytd_mm",
        "rainfall_mm",
    ],

    "flood": [
        "flood_risk",
        "flood_exposure",
        "flood_zone",
    ],

    "discharge": [
        "river_discharge_mean_m3s",
        "river_discharge_max_m3s",
    ],

    "velocity": [
        "water_velocity_mean_ms",
        "water_velocity_max_ms",
    ],

    "maintenance": [
        "maintenance_status",
        "last_repair_date",
        "repair_count",
        "maintenance_history",
    ],

    "inspection": [
        "inspection_date",
        "latest_inspection_date",
        "inspection_ready",
        "structural_inspection",
    ],

    "condition_history": [
        "condition_history",
        "inspection_history",
        "condition_rating",
        "defect_history",
    ],
}


coverage_rows = []

for _, r in bridges.iterrows():

    present = {}

    for key, candidates in aliases.items():

        v = first_nonempty(r, candidates)

        if key == "inspection":

            # A literal false is not inspection evidence.
            present[key] = (
                v is not None
                and str(v).strip().lower()
                not in {"false", "0", "no"}
            )

        else:
            present[key] = v is not None


    # Evidence-completeness score only.
    # NOT model probability/confidence.
    score = 0.0

    # identity / coordinates
    lat = first_nonempty(r, ["latitude", "lat"])
    lon = first_nonempty(r, ["longitude", "lng", "lon"])

    if lat is not None and lon is not None:
        score += 0.05

    engineering_count = sum(
        present[x]
        for x in [
            "length",
            "width",
            "lanes",
            "spans",
            "piers",
        ]
    )

    score += 0.15 * min(
        engineering_count / 4,
        1
    )

    if present["built_year"]:
        score += 0.05

    if present["material"]:
        score += 0.05

    if present["traffic"]:
        score += 0.10

    env_count = sum(
        present[x]
        for x in [
            "rainfall",
            "flood",
            "discharge",
            "velocity",
        ]
    )

    score += 0.10 * min(
        env_count / 3,
        1
    )

    if present["maintenance"]:
        score += 0.10

    # Current structural condition evidence is deliberately heavy.
    if present["inspection"]:
        score += 0.30

    if present["condition_history"]:
        score += 0.10

    score = round(min(score, 1.0), 3)

    missing = [
        k for k, v in present.items()
        if not v
    ]

    target_ready = (
        score >= 0.90
        and present["inspection"]
        and present["traffic"]
        and present["maintenance"]
        and engineering_count >= 4
        and env_count >= 2
    )

    coverage_rows.append({
        "asset_code": r.get("asset_code", ""),
        "bridge_name": r[name_col],

        **{
            f"has_{k}": v
            for k, v in present.items()
        },

        "engineering_feature_count": engineering_count,
        "environment_feature_count": env_count,

        "evidence_coverage_score": score,

        "target_090_evidence_ready": target_ready,

        "missing_for_strong_evidence":
            ";".join(missing),
    })


coverage = pd.DataFrame(coverage_rows)

coverage.to_csv(
    OUT / "BRIDGE_EVIDENCE_COVERAGE.csv",
    index=False
)

coverage[
    ~coverage["target_090_evidence_ready"]
].sort_values(
    "evidence_coverage_score",
    ascending=False
).to_csv(
    OUT / "BRIDGES_BELOW_090_EVIDENCE_TARGET.csv",
    index=False
)


print("\n======================================================")
print(" OFFICIAL EVIDENCE ACQUISITION COMPLETE")
print("======================================================")

print("Output:", OUT)

print("\nTotal bridges:", len(coverage))

print(
    "Evidence >= 0.90:",
    int(
        (
            coverage["evidence_coverage_score"]
            >= 0.90
        ).sum()
    )
)

print(
    "Strict 0.90 evidence-ready:",
    int(
        coverage[
            "target_090_evidence_ready"
        ].sum()
    )
)

print("\n=== EVIDENCE COVERAGE ===")

print(
    coverage["evidence_coverage_score"]
    .describe()
    .round(3)
    .to_string()
)

print("\n=== MOST COMMON MISSING FIELDS ===")

missing_counts = {
    k: int((~coverage[f"has_{k}"]).sum())
    for k in aliases
}

for k, v in sorted(
    missing_counts.items(),
    key=lambda x: -x[1]
):
    print(f"{k:20s} {v}")

print("\nGenerated:")
print(" OFFICIAL_SOURCE_MANIFEST.csv")
print(" PORTAL_FETCH_RESULTS.csv")
print(" OFFICIAL_DOCUMENT_INDEX.csv")
print(" BRIDGE_TO_OFFICIAL_DOCUMENT_CANDIDATES.csv")
print(" BRIDGE_EVIDENCE_COVERAGE.csv")
print(" BRIDGES_BELOW_090_EVIDENCE_TARGET.csv")
print(" NHTIS_AP_CORRIDOR_TRAFFIC.csv")
print(" APSAC_LAYER_AVAILABILITY.csv")

