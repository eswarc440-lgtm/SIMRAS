from __future__ import annotations

from pathlib import Path

import pandas as pd

from simras_ml.nbi import FEATURE_COLUMNS
from simras_ml.nbi_challenger import train_challenger_models


def _panel() -> pd.DataFrame:
    rows: list[dict] = []
    for bridge in range(240):
        starting = 8 - (bridge % 3)
        for offset, year in enumerate(range(2020, 2026)):
            deterioration = offset // (2 + bridge % 2)
            condition = max(3, starting - deterioration)
            row = {
                "bridge_key": f"C{bridge:04d}",
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


def test_challenger_excludes_2025_and_marks_health_as_persistence(tmp_path: Path) -> None:
    champion_dir = tmp_path / "champion"
    challenger_dir = tmp_path / "challenger"
    champion_dir.mkdir()

    # RUL artifacts are copied from the accepted champion bundle by the challenger trainer.
    for name in ("rul_lower.joblib", "rul_median.joblib", "rul_upper.joblib"):
        (champion_dir / name).write_bytes(b"placeholder")

    manifest = train_challenger_models(
        _panel(),
        challenger_dir,
        champion_dir=champion_dir,
        max_training_year=2024,
        min_rows=500,
        min_bridges=100,
        min_years=4,
    )

    assert max(manifest["training_years"]) <= 2024
    assert 2025 not in manifest["training_years"]
    assert manifest["health_method"] == "PERSISTENCE_BASELINE"
    assert manifest["risk_algorithm"] == "XGBoostClassifier"
    assert manifest["champion_preserved"] is True
    assert (challenger_dir / "health.joblib").exists()
    assert (challenger_dir / "risk.joblib").exists()
    assert (challenger_dir / "risk_calibrator.joblib").exists()
    assert (challenger_dir / "rul_lower.joblib").exists()
    assert (challenger_dir / "rul_median.joblib").exists()
    assert (challenger_dir / "rul_upper.joblib").exists()
    assert (challenger_dir / "manifest.json").exists()
