import json
from pathlib import Path

from simras_ml.promotion import (
    evaluate_promotion,
)


def test_current_transfer_model_cannot_promote_without_local_validation(
    tmp_path: Path,
):
    (tmp_path / "health.joblib").write_bytes(
        b"health-test"
    )

    import hashlib

    checksum = hashlib.sha256(
        b"health-test"
    ).hexdigest()

    manifest = {
        "model_name": "test-model",
        "version": "test-v1",
        "stage": "RESEARCH_TRANSFER",
        "feature_version": "test-features",
        "training_scope":
            "FHWA_NBI_US_BRIDGES_RESEARCH_TRANSFER",
        "gates": {
            "health_mae_le_1_0": True,
            "risk_auc_ge_0_70": True,
            "risk_brier_le_0_20": True,
            "risk_ece_le_0_10": True,
            "rul_mae_le_5_years": True,
        },
        "artifact_checksums": {
            "health.joblib": checksum,
        },
        "limitations": [
            "Not locally validated for Andhra Pradesh"
        ],
    }

    ap = {
        "stage": "AP_COMPATIBILITY_CHECKED",
        "total_bridge_candidates": 22795,
        "prediction_eligible": 0,
        "prediction_withheld": 22795,
        "verified_identities": 1,
        "average_feature_coverage": 0.07,
        "max_feature_coverage": 0.15,
        "local_engineering_validation": False,
    }

    (tmp_path / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    (
        tmp_path
        / "ap_validation_report.json"
    ).write_text(
        json.dumps(ap),
        encoding="utf-8",
    )

    result = evaluate_promotion(tmp_path)

    assert (
        result["promotion_approved"]
        is False
    )

    assert (
        result["promotion_decision"]
        == "PROMOTION_BLOCKED"
    )

    assert (
        "AP_LOCAL_LABELLED_VALIDATION_REQUIRED"
        in result["blockers"]
    )


def test_checksum_failure_blocks_promotion(
    tmp_path: Path,
):
    (tmp_path / "health.joblib").write_bytes(
        b"actual-data"
    )

    manifest = {
        "model_name": "test-model",
        "version": "test-v2",
        "stage": "RESEARCH_TRANSFER",
        "feature_version": "v1",
        "training_scope":
            "FHWA_NBI_US_BRIDGES_RESEARCH_TRANSFER",
        "gates": {
            "health_mae_le_1_0": True,
            "risk_auc_ge_0_70": True,
            "risk_brier_le_0_20": True,
            "risk_ece_le_0_10": True,
            "rul_mae_le_5_years": True,
        },
        "artifact_checksums": {
            "health.joblib": "invalid"
        },
        "limitations": [
            "Not locally validated for Andhra Pradesh"
        ],
    }

    ap = {
        "stage": "AP_COMPATIBILITY_CHECKED",
        "total_bridge_candidates": 100,
        "prediction_eligible": 50,
        "prediction_withheld": 50,
        "verified_identities": 50,
        "local_engineering_validation": True,
    }

    (tmp_path / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    (
        tmp_path
        / "ap_validation_report.json"
    ).write_text(
        json.dumps(ap),
        encoding="utf-8",
    )

    result = evaluate_promotion(tmp_path)

    assert result["promotion_approved"] is False

    assert any(
        x.startswith(
            "ARTIFACT_CHECKSUM_MISMATCH"
        )
        for x in result["blockers"]
    )
