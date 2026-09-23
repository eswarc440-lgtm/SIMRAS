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
# API FUNCTION
# ============================================================

api = api_path.read_text(
    encoding="utf-8"
)


api_marker = (
    "export const damBarrageProfile"
)


if api_marker not in api:

    addition = '''

export const damBarrageProfile = (
  assetCode: string,
) =>
  request<any>(
    `/assets/${encodeURIComponent(assetCode)}/dam-barrage-profile`,
  );
'''

    api = api.rstrip() + addition + "\n"


if api.count(api_marker) != 1:
    raise RuntimeError(
        "damBarrageProfile export count must equal 1"
    )


api_path.write_text(
    api,
    encoding="utf-8",
    newline="\n",
)


print(
    "DAM_BARRAGE_API_EXPORT=PASS"
)


# ============================================================
# REPORT IMPORT
# ============================================================

report = report_path.read_text(
    encoding="utf-8"
)


import_line = (
    'import DamBarrageOfficialEvidence '
    'from "./DamBarrageOfficialEvidence";'
)


if import_line not in report:

    imports = list(
        re.finditer(
            r"^import .*?;\s*$",
            report,
            flags=re.MULTILINE,
        )
    )

    if not imports:
        raise RuntimeError(
            "Could not find report import block"
        )

    position = imports[-1].end()

    report = (
        report[:position]
        + "\n"
        + import_line
        + report[position:]
    )


# ============================================================
# DETECT CURRENT SELECTED ASSET-CODE EXPRESSION
#
# Reuse the expression already used by working bridge ML-6D.
# ============================================================

risk = re.search(
    r"reportsApi\s*\.\s*riskPrediction\s*"
    r"\(\s*([^)]+?)\s*\)",
    report,
    flags=re.DOTALL,
)


if risk is None:
    raise RuntimeError(
        "Could not detect selected asset code from "
        "reportsApi.riskPrediction(...)"
    )


asset_expression = (
    risk.group(1).strip()
)


if "\n" in asset_expression:
    asset_expression = re.sub(
        r"\s+",
        " ",
        asset_expression,
    )


print(
    "SELECTED_ASSET_EXPRESSION =",
    asset_expression,
)


# ============================================================
# INSERT COMPONENT BEFORE EXISTING EVIDENCE/PROVENANCE CARD
# ============================================================

marker = (
    "ML7C3B_OFFICIAL_DAM_EVIDENCE"
)


if marker not in report:

    headings = [
        "Evidence & Provenance",
        "Prediction Evidence Status",
        "Infrastructure Specifications",
        "Asset Identity",
    ]

    heading_position = None
    chosen_heading = None


    for heading in headings:

        position = report.find(
            heading
        )

        if position >= 0:

            heading_position = position
            chosen_heading = heading
            break


    if heading_position is None:
        raise RuntimeError(
            "Could not find safe report insertion heading"
        )


    # Find the nearest actual <Card ...> before the heading.
    card_matches = list(
        re.finditer(
            r"<Card(?:\s|>)",
            report[:heading_position],
        )
    )


    if card_matches:

        insertion = card_matches[-1].start()

        line_start = report.rfind(
            "\n",
            0,
            insertion,
        )

        if line_start >= 0:
            insertion = line_start + 1

    else:

        insertion = report.rfind(
            "\n",
            0,
            heading_position,
        )

        if insertion < 0:
            insertion = heading_position
        else:
            insertion += 1


    line_end = report.find(
        "\n",
        insertion,
    )

    if line_end < 0:
        line_end = insertion


    line = report[
        insertion:
        line_end
    ]


    indent_match = re.match(
        r"\s*",
        line,
    )


    indent = (
        indent_match.group(0)
        if indent_match
        else ""
    )


    block = (
        indent
        + "{/* "
        + marker
        + " */}\n"
        + indent
        + "<DamBarrageOfficialEvidence\n"
        + indent
        + "  assetCode={"
        + asset_expression
        + "}\n"
        + indent
        + "/>\n\n"
    )


    report = (
        report[:insertion]
        + block
        + report[insertion:]
    )


    print(
        "INSERTED_BEFORE =",
        chosen_heading,
    )


if report.count(marker) != 1:
    raise RuntimeError(
        "Official dam evidence marker count must equal 1"
    )


if report.count(import_line) != 1:
    raise RuntimeError(
        "Official evidence import count must equal 1"
    )


report_path.write_text(
    report,
    encoding="utf-8",
    newline="\n",
)


print(
    "REPORT_IMPORT=PASS"
)

print(
    "REPORT_COMPONENT=PASS"
)