from pathlib import Path
import re
import shutil

ROOT = Path.cwd()

twin = ROOT / "backend" / "app" / "services" / "twin_service.py"
ml = ROOT / "backend" / "app" / "services" / "ml_predictor.py"
gov = ROOT / "backend" / "app" / "services" / "model_governance.py"

if not twin.exists():
    raise SystemExit(f"Missing: {twin}")

if not ml.exists():
    raise SystemExit(f"Missing: {ml}")

if not gov.exists():
    raise SystemExit(
        "model_governance.py is missing. Create that file before applying this patch."
    )

# ------------------------------------------------------------
# BACKUPS
# ------------------------------------------------------------

shutil.copy2(
    twin,
    twin.with_name("twin_service.before_governance.py"),
)

shutil.copy2(
    ml,
    ml.with_name("ml_predictor.before_governance.py"),
)

print("Backups created.")

# ------------------------------------------------------------
# PATCH twin_service.py
# ------------------------------------------------------------

text = twin.read_text(encoding="utf-8-sig")

if "bridge_prediction_gate(" not in text:

    function_start = text.find(
        "async def refresh_ml_prediction("
    )

    if function_start == -1:
        raise SystemExit(
            "Could not find refresh_ml_prediction()"
        )

    next_function = text.find(
        "\nasync def ",
        function_start + 10,
    )

    if next_function == -1:
        next_function = len(text)

    block = text[
        function_start:next_function
    ]

    marker_pattern = re.compile(
        r"("
        r"\s+row\s*=\s*await\s+get_asset_row"
        r"\(session,\s*asset_code\)"
        r"\s*\n"
        r"\s+asset,\s*_,\s*_\s*=\s*row"
        r"\s*\n"
        r")"
    )

    match = marker_pattern.search(block)

    if not match:
        raise SystemExit(
            "Could not locate asset loading lines "
            "inside refresh_ml_prediction()."
        )

    gate_code = '''
    # --------------------------------------------------------
    # Governed bridge ML inference gate
    # --------------------------------------------------------
    if str(asset.asset_type or "").lower() == "bridge":
        from app.services.model_governance import (
            bridge_prediction_gate,
        )

        gate = await bridge_prediction_gate(
            session=session,
            asset=asset,
        )

        if not gate["allowed"]:
            return {
                "status": "WITHHELD",
                "prediction_available": False,
                "reason_code": gate["reason_code"],
                "asset": {
                    "id": asset.id,
                    "asset_code": asset.asset_code,
                    "name": asset.name,
                    "asset_type": asset.asset_type,
                    "identity_status": asset.identity_status,
                },
                "model": gate.get("model"),
                "governance": gate.get(
                    "governance",
                    {},
                ),
                "prediction": None,
                "database_rows": [],
                "warning": (
                    "Bridge AI prediction withheld because "
                    "the governed AP/NBI production "
                    "requirements are not satisfied."
                ),
            }

'''

    insert_at = match.end()

    block = (
        block[:insert_at]
        + gate_code
        + block[insert_at:]
    )

    text = (
        text[:function_start]
        + block
        + text[next_function:]
    )

    twin.write_text(
        text,
        encoding="utf-8",
    )

    print(
        "PATCHED: twin_service.py governance gate"
    )

else:
    print(
        "SKIP: twin_service.py already contains governance gate"
    )

# ------------------------------------------------------------
# PATCH ml_predictor.py
# ------------------------------------------------------------

text = ml.read_text(encoding="utf-8-sig")

old_stage = (
    'if manifest.get("stage") not in '
    '{"RESEARCH_TRANSFER", "VALIDATED_LOCAL"}:'
)

new_stage = (
    'if manifest.get("stage") not in '
    '{"PRODUCTION_DECISION_SUPPORT", '
    '"VALIDATED_LOCAL"}:'
)

if old_stage in text:
    text = text.replace(
        old_stage,
        new_stage,
        1,
    )
    print(
        "PATCHED: RESEARCH_TRANSFER direct inference disabled"
    )
elif new_stage in text:
    print(
        "SKIP: direct inference stage already hardened"
    )
else:
    raise SystemExit(
        "Could not locate artifact stage check "
        "in ml_predictor.py"
    )

condition_pattern = re.compile(
    r"def condition_to_rating"
    r"\("
    r"condition: str \| None,"
    r"\s*score: float \| None"
    r"\)"
    r"\s*->\s*float \| None:"
    r".*?"
    r"(?=\ndef _checksum)",
    re.DOTALL,
)

safe_condition = '''def condition_to_rating(
    condition: str | None,
    score: float | None,
) -> float | None:
    """
    Generic condition labels and generic inspection scores are
    not automatically equivalent to FHWA/NBI 0-9 ratings.

    An explicitly sourced NBI-compatible engineering rating is
    required before NBI inference.
    """
    return None


'''

if condition_pattern.search(text):
    text = condition_pattern.sub(
        safe_condition,
        text,
        count=1,
    )
    print(
        "PATCHED: unsafe condition-to-NBI mapping disabled"
    )
elif "An explicitly sourced NBI-compatible" in text:
    print(
        "SKIP: condition mapping already hardened"
    )
else:
    raise SystemExit(
        "Could not safely locate condition_to_rating()"
    )

ml.write_text(
    text,
    encoding="utf-8",
)

print()
print("GOVERNANCE PATCH COMPLETE")
