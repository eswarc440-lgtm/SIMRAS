from __future__ import annotations

from pathlib import Path

from simras_ml.cli import parser


def test_parser_accepts_evaluate_temporal_command():
    args = parser().parse_args(
        [
            "evaluate-temporal",
            "--panel",
            "/data/ml/nbi_panel_2020_2025.csv.gz",
            "--artifact-dir",
            "/artifacts/bridge_nbi",
            "--outcome-year",
            "2025",
            "--horizon-years",
            "3",
        ]
    )

    assert args.command == "evaluate-temporal"
    assert args.panel == Path("/data/ml/nbi_panel_2020_2025.csv.gz")
    assert args.artifact_dir == Path("/artifacts/bridge_nbi")
    assert args.outcome_year == 2025
    assert args.horizon_years == 3
