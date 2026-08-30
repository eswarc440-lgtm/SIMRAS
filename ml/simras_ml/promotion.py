from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


REQUIRED_MODEL_GATES = [
    "health_mae_le_1_0",
    "risk_auc_ge_0_70",
    "risk_brier_le_0_20",
    "risk_ece_le_0_10",
    "rul_mae_le_5_years",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def evaluate_promotion(
    artifact_dir: Path,
    *,
    require_local_validation: bool = True,
) -> dict:
    manifest_path = artifact_dir / "manifest.json"
    ap_report_path = artifact_dir / "ap_validation_report.json"

    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)

    if not ap_report_path.exists():
        raise FileNotFoundError(ap_report_path)

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    ap_report = json.loads(
        ap_report_path.read_text(encoding="utf-8")
    )

    checks = {}
    blockers = []

    # ---------------------------------------------------------
    # Original NBI research-transfer training gates
    # ---------------------------------------------------------

    model_gates = manifest.get("gates", {})

    for gate in REQUIRED_MODEL_GATES:
        passed = bool(model_gates.get(gate, False))
        checks[f"model_gate:{gate}"] = passed

        if not passed:
            blockers.append(f"FAILED_MODEL_GATE:{gate}")

    # ---------------------------------------------------------
    # Artifact integrity
    # ---------------------------------------------------------

    expected_checksums = manifest.get(
        "artifact_checksums",
        {}
    )

    checks["artifact_manifest_present"] = (
        len(expected_checksums) > 0
    )

    if not expected_checksums:
        blockers.append("NO_ARTIFACT_CHECKSUMS")

    for filename, expected in expected_checksums.items():
        path = artifact_dir / filename

        exists = path.exists()
        checks[f"artifact_exists:{filename}"] = exists

        if not exists:
            blockers.append(
                f"MISSING_ARTIFACT:{filename}"
            )
            continue

        actual = sha256(path)

        valid = actual == expected

        checks[
            f"artifact_checksum:{filename}"
        ] = valid

        if not valid:
            blockers.append(
                f"ARTIFACT_CHECKSUM_MISMATCH:{filename}"
            )

    # ---------------------------------------------------------
    # AP compatibility
    # ---------------------------------------------------------

    compatibility_checked = (
        ap_report.get("stage")
        == "AP_COMPATIBILITY_CHECKED"
    )

    checks[
        "ap_compatibility_checked"
    ] = compatibility_checked

    if not compatibility_checked:
        blockers.append(
            "AP_COMPATIBILITY_NOT_COMPLETED"
        )

    total_candidates = int(
        ap_report.get(
            "total_bridge_candidates",
            0,
        )
    )

    checks[
        "ap_candidates_evaluated"
    ] = total_candidates > 0

    if total_candidates <= 0:
        blockers.append(
            "NO_AP_BRIDGE_CANDIDATES_EVALUATED"
        )

    # ---------------------------------------------------------
    # Local engineering validation
    # ---------------------------------------------------------

    local_validation = bool(
        ap_report.get(
            "local_engineering_validation",
            False,
        )
    )

    checks[
        "ap_local_engineering_validation"
    ] = local_validation

    if require_local_validation and not local_validation:
        blockers.append(
            "AP_LOCAL_LABELLED_VALIDATION_REQUIRED"
        )

    prediction_eligible = int(
        ap_report.get(
            "prediction_eligible",
            0,
        )
    )

    checks[
        "ap_has_eligible_prediction_records"
    ] = prediction_eligible > 0

    if prediction_eligible == 0:
        blockers.append(
            "NO_AP_ASSETS_MEET_INFERENCE_ELIGIBILITY"
        )

    # ---------------------------------------------------------
    # Governance constraints
    # ---------------------------------------------------------

    correct_scope = (
        manifest.get("training_scope")
        == "FHWA_NBI_US_BRIDGES_RESEARCH_TRANSFER"
    )

    checks[
        "training_scope_declared"
    ] = correct_scope

    if not correct_scope:
        blockers.append(
            "UNEXPECTED_TRAINING_SCOPE"
        )

    limitations = manifest.get(
        "limitations",
        []
    )

    limitation_text = " ".join(
        str(item) for item in limitations
    ).lower()

    ap_limitation_declared = (
        "andhra pradesh" in limitation_text
    )

    checks[
        "ap_transfer_limitation_declared"
    ] = ap_limitation_declared

    if not ap_limitation_declared:
        blockers.append(
            "AP_TRANSFER_LIMITATION_NOT_DECLARED"
        )

    # ---------------------------------------------------------
    # Decision
    # ---------------------------------------------------------

    approved = len(blockers) == 0

    if approved:
        decision = "PROMOTION_APPROVED"
        target_stage = (
            "PRODUCTION_DECISION_SUPPORT"
        )
    else:
        decision = "PROMOTION_BLOCKED"
        target_stage = "RESEARCH_TRANSFER"

    return {
        "model_name": manifest.get(
            "model_name"
        ),
        "model_version": manifest.get(
            "version"
        ),
        "feature_version": manifest.get(
            "feature_version"
        ),
        "training_scope": manifest.get(
            "training_scope"
        ),
        "current_stage": manifest.get(
            "stage"
        ),
        "target_stage": target_stage,
        "promotion_decision": decision,
        "promotion_approved": approved,
        "checks": checks,
        "blockers": blockers,
        "ap_validation": {
            "total_candidates": total_candidates,
            "prediction_eligible": prediction_eligible,
            "prediction_withheld": int(
                ap_report.get(
                    "prediction_withheld",
                    0,
                )
            ),
            "verified_identities": int(
                ap_report.get(
                    "verified_identities",
                    0,
                )
            ),
            "average_feature_coverage": float(
                ap_report.get(
                    "average_feature_coverage",
                    0.0,
                )
            ),
            "max_feature_coverage": float(
                ap_report.get(
                    "max_feature_coverage",
                    0.0,
                )
            ),
            "local_engineering_validation": (
                local_validation
            ),
        },
        "safety_policy": {
            "allow_unverified_asset_prediction": False,
            "allow_missing_core_feature_prediction": False,
            "allow_fake_engineering_features": False,
            "rul_authoritative_for_ap": False,
            "intended_use": "DECISION_SUPPORT_ONLY",
        },
        "evaluated_at": datetime.now(
            UTC
        ).isoformat(),
    }


def write_promotion_report(
    artifact_dir: Path,
) -> dict:
    result = evaluate_promotion(
        artifact_dir
    )

    output = (
        artifact_dir
        / "promotion_report.json"
    )

    output.write_text(
        json.dumps(
            result,
            indent=2,
        ),
        encoding="utf-8",
    )

    return result
