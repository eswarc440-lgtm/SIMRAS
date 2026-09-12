from __future__ import annotations

from pathlib import Path

import pandas as pd

from simras_ml.nbi import FEATURE_COLUMNS
from simras_ml.nbi_train import train_models


def _panel() -> pd.DataFrame:
    rows = []
    for bridge in range(240):
        starting = 8 - (bridge % 3)
        for offset, year in enumerate(range(2018, 2026)):
            deterioration = offset // (2 + bridge % 2)
            condition = max(3, starting - deterioration)
            row = {
                "bridge_key": f"B{bridge:04d}",
                "report_year": year,
                "age_years": 20 + bridge % 70 + offset,
                "condition_rating": condition,
                "material_code": 1 + bridge % 4,
                "design_type_code": 1 + bridge % 15,
                "average_daily_traffic": 1000 + bridge * 20,
                "truck_traffic_percent": 5 + bridge % 25,
                "skew_deg": bridge % 45,
                "span_count": 1 + bridge % 10,
                "max_span_m": 10 + bridge % 90,
                "structure_length_m": 30 + bridge % 500,
                "inventory_rating": 20 + bridge % 40,
                "scour_rating": 4 + bridge % 5,
                "waterway_rating": 4 + bridge % 5,
            }
            rows.append(row)
    frame = pd.DataFrame(rows)
    assert set(FEATURE_COLUMNS).issubset(frame.columns)
    return frame


def test_training_writes_a_governed_manifest(tmp_path: Path) -> None:
    manifest = train_models(
        _panel(),
        tmp_path,
        min_rows=500,
        min_bridges=100,
        min_years=5,
    )
    assert manifest["model_validated"] is False
    assert manifest["stage"] in {"RESEARCH_TRANSFER", "REJECTED"}
    assert manifest["training_scope"] == "FHWA_NBI_US_BRIDGES_RESEARCH_TRANSFER"
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "health.joblib").exists()
    assert (tmp_path / "risk.joblib").exists()
