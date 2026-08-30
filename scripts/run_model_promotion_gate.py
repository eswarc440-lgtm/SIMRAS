import json
from pathlib import Path

from simras_ml.promotion import (
    write_promotion_report,
)

artifact_dir = Path(
    "artifacts/bridge_nbi"
)

result = write_promotion_report(
    artifact_dir
)

print()
print("=" * 68)
print("SIMRAS MODEL PRODUCTION PROMOTION GATE")
print("=" * 68)

print(
    "Model:",
    result["model_name"]
)

print(
    "Version:",
    result["model_version"]
)

print(
    "Current stage:",
    result["current_stage"]
)

print(
    "Requested target:",
    "PRODUCTION_DECISION_SUPPORT"
)

print()

for name, passed in result[
    "checks"
].items():
    state = "PASS" if passed else "FAIL"
    print(
        f"[{state}] {name}"
    )

print()
print("-" * 68)

print(
    "DECISION:",
    result["promotion_decision"]
)

print(
    "RESULTING STAGE:",
    result["target_stage"]
)

if result["blockers"]:
    print()
    print("PROMOTION BLOCKERS:")

    for blocker in result["blockers"]:
        print(
            " -",
            blocker
        )

print()
print("AP VALIDATION:")
print(
    json.dumps(
        result["ap_validation"],
        indent=2,
    )
)

print()
print(
    "Report:",
    artifact_dir
    / "promotion_report.json"
)
