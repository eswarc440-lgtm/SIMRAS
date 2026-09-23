from pathlib import Path
import re


root = Path.cwd()

api_path = (
    root
    / "frontend/src/services/simrasTwinApi.ts"
)

report_path = (
    root
    / "frontend/src/features/reports/SelectedAssetReports.tsx"
)


# ============================================================
# API EXPORT
# ============================================================

api = api_path.read_text(
    encoding="utf-8"
)

marker = "export const bridgeReportProfile"

if marker not in api:

    addition = '''

export const bridgeReportProfile = (
  assetCode: string,
) =>
  request<any>(
    `/assets/${encodeURIComponent(assetCode)}/bridge-report-profile`,
  );
'''

    api = api.rstrip() + addition + "\n"


if api.count(marker) != 1:
    raise RuntimeError(
        "bridgeReportProfile export count != 1"
    )


api_path.write_text(
    api,
    encoding="utf-8",
    newline="\n",
)


# ============================================================
# REPORT IMPORT
# ============================================================

report = report_path.read_text(
    encoding="utf-8"
)

bridge_import = (
    'import BridgeEngineeringEvidence '
    'from "./BridgeEngineeringEvidence";'
)


if bridge_import not in report:

    imports = list(
        re.finditer(
            r"^import .*?;\s*$",
            report,
            flags=re.MULTILINE,
        )
    )

    if not imports:
        raise RuntimeError(
            "Could not locate imports"
        )

    position = imports[-1].end()

    report = (
        report[:position]
        + "\n"
        + bridge_import
        + report[position:]
    )


# ============================================================
# FIX DAM COMPONENT PLACEMENT
# ============================================================

dam_block_pattern = re.compile(
    r"\s*\{/\*\s*ML7C3B_OFFICIAL_DAM_EVIDENCE\s*\*/\}\s*"
    r"<DamBarrageOfficialEvidence\s*"
    r"assetCode=\{reportAssetCodeForRisk\}\s*/>\s*",
    flags=re.MULTILINE,
)

report = dam_block_pattern.sub(
    "\n",
    report,
)


dam_marker = (
    "ML7C3B_DAM_EVIDENCE_CORRECT_POSITION"
)


if dam_marker not in report:

    heading_position = report.find(
        "Evidence & Provenance"
    )

    if heading_position < 0:
        raise RuntimeError(
            "Evidence & Provenance heading not found"
        )

    section_start = report.rfind(
        "<section",
        0,
        heading_position,
    )

    if section_start < 0:
        raise RuntimeError(
            "Evidence section start not found"
        )

    dam_block = '''
      {/* ML7C3B_DAM_EVIDENCE_CORRECT_POSITION */}
      {(reportAssetType === "dam" ||
        reportAssetType === "barrage") && (
        <DamBarrageOfficialEvidence
          assetCode={reportAssetCodeForRisk}
        />
      )}

'''

    report = (
        report[:section_start]
        + dam_block
        + report[section_start:]
    )


# ============================================================
# INSERT BRIDGE ENGINEERING COMPONENT
# ============================================================

bridge_marker = (
    "BRIDGE_REAL_ENGINEERING_REPORT"
)


if bridge_marker not in report:

    heading_position = report.find(
        "Asset-Specific Engineering Evidence"
    )

    if heading_position < 0:
        raise RuntimeError(
            "Asset-Specific Engineering Evidence heading missing"
        )

    section_start = report.rfind(
        "<section",
        0,
        heading_position,
    )

    if section_start < 0:
        raise RuntimeError(
            "Asset-specific section start missing"
        )


    bridge_block = '''
      {/* BRIDGE_REAL_ENGINEERING_REPORT */}
      {reportAssetType === "bridge" && (
        <BridgeEngineeringEvidence
          assetCode={reportAssetCodeForRisk}
        />
      )}

'''

    report = (
        report[:section_start]
        + bridge_block
        + report[section_start:]
    )


# ============================================================
# HIDE GENERIC INFRASTRUCTURE SPECIFICATIONS FOR BRIDGES
#
# The new bridge card replaces the generic UNKNOWN fields.
# ============================================================

generic_marker = (
    "BRIDGE_HIDE_GENERIC_SPECIFICATIONS"
)


if generic_marker not in report:

    heading_position = report.find(
        "Infrastructure Specifications"
    )

    if heading_position < 0:
        raise RuntimeError(
            "Infrastructure Specifications heading missing"
        )


    article_start = report.rfind(
        "<article",
        0,
        heading_position,
    )

    article_end = report.find(
        "</article>",
        heading_position,
    )


    if article_start < 0 or article_end < 0:
        raise RuntimeError(
            "Could not isolate Infrastructure Specifications article"
        )


    article_end += len(
        "</article>"
    )


    original = report[
        article_start:
        article_end
    ]


    wrapped = (
        "{/* "
        + generic_marker
        + " */}\n"
        + '        {reportAssetType !== "bridge" && (\n'
        + original
        + "\n"
        + "        )}"
    )


    report = (
        report[:article_start]
        + wrapped
        + report[article_end:]
    )


# ============================================================
# HIDE OLD ASSET-SPECIFIC SECTION FOR BRIDGES
# ============================================================

old_bridge_marker = (
    "BRIDGE_HIDE_OLD_ASSET_SPECIFIC"
)


if old_bridge_marker not in report:

    heading_position = report.find(
        "Asset-Specific Engineering Evidence"
    )

    section_start = report.rfind(
        "<section",
        0,
        heading_position,
    )

    section_end = report.find(
        "</section>",
        heading_position,
    )


    if section_start < 0 or section_end < 0:
        raise RuntimeError(
            "Could not isolate old asset-specific section"
        )


    section_end += len(
        "</section>"
    )


    original = report[
        section_start:
        section_end
    ]


    wrapped = (
        "{/* "
        + old_bridge_marker
        + " */}\n"
        + '      {reportAssetType !== "bridge" && (\n'
        + original
        + "\n"
        + "      )}"
    )


    report = (
        report[:section_start]
        + wrapped
        + report[section_end:]
    )


# ============================================================
# HIDE GENERIC UNKNOWN PROVENANCE FOR BRIDGES
#
# Bridge component now displays engineering/evidence status.
# ============================================================

provenance_marker = (
    "BRIDGE_HIDE_GENERIC_PROVENANCE"
)


if provenance_marker not in report:

    heading_position = report.find(
        "Evidence & Provenance"
    )

    if heading_position < 0:
        raise RuntimeError(
            "Evidence & Provenance heading missing"
        )


    section_start = report.rfind(
        "<section",
        0,
        heading_position,
    )

    section_end = report.find(
        "</section>",
        heading_position,
    )


    if section_start < 0 or section_end < 0:
        raise RuntimeError(
            "Could not isolate Evidence & Provenance section"
        )


    section_end += len(
        "</section>"
    )


    original = report[
        section_start:
        section_end
    ]


    wrapped = (
        "{/* "
        + provenance_marker
        + " */}\n"
        + '      {reportAssetType !== "bridge" && (\n'
        + original
        + "\n"
        + "      )}"
    )


    report = (
        report[:section_start]
        + wrapped
        + report[section_end:]
    )


# ============================================================
# FINAL VALIDATION
# ============================================================

required = [
    "BRIDGE_REAL_ENGINEERING_REPORT",
    "BRIDGE_HIDE_GENERIC_SPECIFICATIONS",
    "BRIDGE_HIDE_OLD_ASSET_SPECIFIC",
    "BRIDGE_HIDE_GENERIC_PROVENANCE",
    "ML7C3B_DAM_EVIDENCE_CORRECT_POSITION",
]


for value in required:

    if report.count(value) != 1:

        raise RuntimeError(
            value
            + " marker count != 1"
        )


if report.count(bridge_import) != 1:
    raise RuntimeError(
        "Bridge import count != 1"
    )


report_path.write_text(
    report,
    encoding="utf-8",
    newline="\n",
)


print("BRIDGE_API_EXPORT=PASS")
print("DAM_COMPONENT_POSITION=PASS")
print("BRIDGE_REPORT_COMPONENT=PASS")
print("BRIDGE_UNKNOWN_DUPLICATES_HIDDEN=PASS")