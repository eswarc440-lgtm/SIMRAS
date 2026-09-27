from pathlib import Path
import re
import pandas as pd

ROOT = Path("backend/data/official/bridge_evidence_20260927")
TEXT = ROOT / "extracted_text"

bridge_file = Path(
    "backend/data/processed/bridge/AP_ALL_BRIDGES_ENVIRONMENT_ENRICHED.csv"
)

if not bridge_file.exists():
    bridge_file = Path(
        "backend/data/processed/bridge/AP_ALL_BRIDGES_NUMERIC_PREDICTIONS.csv"
    )

bridges = pd.read_csv(bridge_file)

name_col = next(
    c for c in [
        "bridge_name",
        "asset_name",
        "display_name",
        "name"
    ]
    if c in bridges.columns
)

def norm(x):
    return re.sub(r"[^a-z0-9]+", " ", str(x).lower()).strip()

def value(patterns, text, flags=re.I):
    for p in patterns:
        m = re.search(p, text, flags)
        if m:
            return m.group(1).strip()
    return None


# ============================================================
# FIELD PATTERNS
# ============================================================

patterns = {

    "length_m": [
        r"(?:bridge\s+)?length\s*[:=-]?\s*([\d,.]+)\s*m\b",
        r"total\s+length\s*[:=-]?\s*([\d,.]+)\s*m\b",
    ],

    "width_m": [
        r"(?:bridge\s+)?width\s*[:=-]?\s*([\d,.]+)\s*m\b",
        r"carriageway\s+width\s*[:=-]?\s*([\d,.]+)\s*m\b",
        r"deck\s+width\s*[:=-]?\s*([\d,.]+)\s*m\b",
    ],

    "lanes": [
        r"(\d+)\s*[- ]?lane\b",
        r"number\s+of\s+lanes\s*[:=-]?\s*(\d+)",
    ],

    "span_count": [
        r"(?:no\.?\s*of\s*)?spans?\s*[:=-]?\s*(\d+)",
        r"(\d+)\s+spans?\b",
    ],

    "pier_count": [
        r"(?:no\.?\s*of\s*)?piers?\s*[:=-]?\s*(\d+)",
        r"(\d+)\s+piers?\b",
    ],

    "built_year": [
        r"(?:completed|completion|commissioned|constructed)\s+(?:in\s+)?((?:19|20)\d{2})",
        r"(?:year\s+of\s+construction|construction\s+year)\s*[:=-]?\s*((?:19|20)\d{2})",
    ],

    "traffic_pcu_day": [
        r"(?:traffic|aadt|adt)\s*(?:volume)?\s*[:=-]?\s*([\d,]+)\s*(?:pcu/?day|pcu/day)",
        r"([\d,]+)\s*pcu/?day",
    ],

    "aadt": [
        r"\bAADT\b\s*[:=-]?\s*([\d,]+)",
        r"annual\s+average\s+daily\s+traffic\s*[:=-]?\s*([\d,]+)",
    ],
}

material_terms = [
    "prestressed concrete",
    "prestressed rcc",
    "reinforced cement concrete",
    "reinforced concrete",
    "rcc",
    "steel",
    "composite",
    "masonry",
    "psc",
]

condition_terms = [
    "crack",
    "corrosion",
    "spalling",
    "settlement",
    "scour",
    "damaged bearing",
    "bearing damage",
    "expansion joint",
    "deck distress",
    "structural distress",
    "defect",
]

maintenance_terms = [
    "rehabilitation",
    "repair",
    "maintenance",
    "strengthening",
    "replacement",
    "retrofit",
]

inspection_terms = [
    "bridge inspection",
    "condition survey",
    "visual inspection",
    "structural inspection",
    "inspection report",
    "condition rating",
]


# ============================================================
# LOAD GOVERNMENT DOCUMENT TEXT
# ============================================================

documents = []

for txt in TEXT.glob("*.txt"):
    try:
        content = txt.read_text(
            encoding="utf-8",
            errors="ignore"
        )
        if len(content.strip()) > 100:
            documents.append((txt, content))
    except Exception:
        pass

print("Government text documents:", len(documents))


# ============================================================
# BRIDGE/DOCUMENT MATCHING + FIELD EXTRACTION
# ============================================================

rows = []

generic = {
    "bridge", "road", "flyover", "bypass", "main",
    "old", "new", "nh", "sh"
}

for _, bridge in bridges.iterrows():

    bridge_name = str(bridge[name_col])
    clean = norm(bridge_name)

    tokens = [
        t for t in clean.split()
        if len(t) >= 4 and t not in generic
    ]

    # Distinctive terms only
    tokens = list(dict.fromkeys(tokens))

    if not tokens:
        continue

    for txt, raw in documents:

        text = raw.lower()

        matched = [t for t in tokens if t in text]

        token_score = (
            len(matched) / len(tokens)
            if tokens else 0
        )

        exact_name = clean in norm(raw)

        if not exact_name and token_score < 0.60:
            continue

        candidate = {
            "asset_code": bridge.get("asset_code", ""),
            "bridge_name": bridge_name,
            "document": txt.name,
            "exact_name_match": exact_name,
            "token_match_ratio": round(token_score, 3),
        }

        # Engineering numeric fields
        for field, pats in patterns.items():
            candidate[field] = value(pats, raw)

        # Material
        found_material = [
            x for x in material_terms
            if x in text
        ]

        candidate["material_candidate"] = (
            ";".join(found_material[:5])
            if found_material else None
        )

        # Condition / maintenance / inspection
        condition = [
            x for x in condition_terms
            if x in text
        ]

        maintenance = [
            x for x in maintenance_terms
            if x in text
        ]

        inspection = [
            x for x in inspection_terms
            if x in text
        ]

        candidate["condition_terms"] = ";".join(condition)
        candidate["maintenance_terms"] = ";".join(maintenance)
        candidate["inspection_terms"] = ";".join(inspection)

        candidate["has_engineering_candidate"] = any(
            candidate.get(x)
            for x in [
                "length_m",
                "width_m",
                "lanes",
                "span_count",
                "pier_count",
                "built_year",
                "material_candidate",
            ]
        )

        candidate["has_traffic_candidate"] = any(
            candidate.get(x)
            for x in [
                "traffic_pcu_day",
                "aadt",
            ]
        )

        candidate["has_condition_candidate"] = bool(condition)
        candidate["has_maintenance_candidate"] = bool(maintenance)
        candidate["has_inspection_candidate"] = bool(inspection)

        # Do NOT auto-verify.
        candidate["evidence_status"] = "REVIEW_REQUIRED"

        rows.append(candidate)


out = pd.DataFrame(rows)

outfile = ROOT / "BRIDGE_DOCUMENT_EVIDENCE_CANDIDATES.csv"

if len(out):
    out = out.sort_values(
        [
            "exact_name_match",
            "token_match_ratio",
            "has_inspection_candidate",
            "has_traffic_candidate",
        ],
        ascending=[False, False, False, False]
    )

out.to_csv(outfile, index=False)


# ============================================================
# SUMMARY
# ============================================================

print("\n====================================================")
print(" GOVERNMENT DOCUMENT EVIDENCE EXTRACTION")
print("====================================================")

print("Candidate rows :", len(out))

if len(out):

    print(
        "Bridges matched :",
        out["bridge_name"].nunique()
    )

    print(
        "Engineering     :",
        int(out["has_engineering_candidate"].sum())
    )

    print(
        "Traffic         :",
        int(out["has_traffic_candidate"].sum())
    )

    print(
        "Maintenance     :",
        int(out["has_maintenance_candidate"].sum())
    )

    print(
        "Inspection      :",
        int(out["has_inspection_candidate"].sum())
    )

    print(
        "Condition       :",
        int(out["has_condition_candidate"].sum())
    )

    print("\n=== TOP CANDIDATES ===")

    show = [
        "bridge_name",
        "document",
        "width_m",
        "lanes",
        "span_count",
        "pier_count",
        "built_year",
        "traffic_pcu_day",
        "aadt",
        "material_candidate",
        "has_inspection_candidate",
        "has_condition_candidate",
    ]

    print(
        out[show]
        .head(30)
        .to_string(index=False)
    )

print("\nSaved:", outfile)
