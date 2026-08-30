from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pandas as pd

from simras_ml.ap_validation import write_report


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "bridge_nbi"


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


user = docker_env("POSTGRES_USER")
database = docker_env("POSTGRES_DB")

query = """
SELECT *
FROM staging.osm_bridge_group_features
ORDER BY asset_code
"""

result = subprocess.run(
    [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        user,
        "-d",
        database,
        "--csv",
        "-P",
        "footer=off",
        "-c",
        query,
    ],
    cwd=ROOT,
    text=True,
    capture_output=True,
    check=True,
)

frame = pd.read_csv(io.StringIO(result.stdout), low_memory=False)

print("AP bridge candidates loaded:", len(frame))

summary = write_report(frame, OUTPUT)

print()
print("SIMRAS AP/NBI COMPATIBILITY REPORT")
print("=" * 50)
print(json.dumps(summary, indent=2))
print()
print("Reports:")
print(OUTPUT / "ap_compatibility.csv")
print(OUTPUT / "ap_validation_report.json")
