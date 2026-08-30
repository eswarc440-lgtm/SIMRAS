from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "artifacts" / "bridge_nbi"

MANIFEST = ARTIFACT_DIR / "manifest.json"
PROMOTION = ARTIFACT_DIR / "promotion_report.json"


def read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def docker_env(name: str) -> str:
    return subprocess.check_output(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "db",
            "printenv",
            name,
        ],
        cwd=ROOT,
        text=True,
    ).strip()


def sql_text(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


manifest = read_json(MANIFEST)
promotion = read_json(PROMOTION)

# Never promote simply because this registration script ran.
if promotion.get("promotion_approved"):
    registry_stage = promotion.get(
        "target_stage",
        manifest.get("stage", "RESEARCH_TRANSFER"),
    )
else:
    registry_stage = manifest.get(
        "stage",
        "RESEARCH_TRANSFER",
    )

metrics_payload = {
    "training_metrics": manifest.get("metrics", {}),
    "training_gates": manifest.get("gates", {}),
    "training_rows": manifest.get("training_rows"),
    "unique_bridges": manifest.get("unique_bridges"),
    "training_years": manifest.get("training_years"),
    "prediction_horizon_years": manifest.get(
        "prediction_horizon_years"
    ),
    "artifact_checksums": manifest.get(
        "artifact_checksums",
        {},
    ),
    "limitations": manifest.get("limitations", []),
    "promotion": {
        "decision": promotion.get(
            "promotion_decision"
        ),
        "approved": promotion.get(
            "promotion_approved"
        ),
        "target_stage": promotion.get(
            "target_stage"
        ),
        "blockers": promotion.get(
            "blockers",
            [],
        ),
        "ap_validation": promotion.get(
            "ap_validation",
            {},
        ),
        "safety_policy": promotion.get(
            "safety_policy",
            {},
        ),
    },
}

model_name = manifest["model_name"]
version = manifest["version"]
feature_version = manifest["feature_version"]

training_dataset = (
    manifest.get("data_source")
    or manifest.get("training_scope")
)

artifact_uri = "repo://artifacts/bridge_nbi"

# Registry checksum represents the immutable model manifest.
manifest_checksum = sha256(MANIFEST)

metrics_json = json.dumps(
    metrics_payload,
    separators=(",", ":"),
)

sql = f"""
WITH updated AS (
    UPDATE model_registry
    SET
        training_dataset = {sql_text(training_dataset)},
        feature_version = {sql_text(feature_version)},
        metrics = {sql_text(metrics_json)}::jsonb,
        stage = {sql_text(registry_stage)},
        artifact_uri = {sql_text(artifact_uri)},
        checksum = {sql_text(manifest_checksum)},
        updated_at = NOW()
    WHERE
        model_name = {sql_text(model_name)}
        AND version = {sql_text(version)}
    RETURNING id
)
INSERT INTO model_registry (
    model_name,
    version,
    training_dataset,
    feature_version,
    metrics,
    stage,
    artifact_uri,
    checksum,
    created_at,
    updated_at
)
SELECT
    {sql_text(model_name)},
    {sql_text(version)},
    {sql_text(training_dataset)},
    {sql_text(feature_version)},
    {sql_text(metrics_json)}::jsonb,
    {sql_text(registry_stage)},
    {sql_text(artifact_uri)},
    {sql_text(manifest_checksum)},
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM updated
);
"""

db_user = docker_env("POSTGRES_USER")
db_name = docker_env("POSTGRES_DB")

result = subprocess.run(
    [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        db_user,
        "-d",
        db_name,
        "-v",
        "ON_ERROR_STOP=1",
    ],
    cwd=ROOT,
    input=sql,
    text=True,
    capture_output=True,
)

if result.returncode != 0:
    print(result.stdout)
    print(result.stderr)
    raise SystemExit(result.returncode)

print(result.stdout)

print("=" * 65)
print("SIMRAS MODEL REGISTRY UPDATE")
print("=" * 65)
print("Model:", model_name)
print("Version:", version)
print("Stage:", registry_stage)
print(
    "Promotion:",
    promotion.get("promotion_decision"),
)
print(
    "Promotion approved:",
    promotion.get("promotion_approved"),
)
print("Artifact URI:", artifact_uri)
print("Manifest SHA256:", manifest_checksum)
