from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from simras_ml.nbi import build_panel, download_year
from simras_ml.nbi_train import train_models


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="SIMRAS gated NBI bridge-model pipeline")
    sub = root.add_subparsers(dest="command", required=True)

    download = sub.add_parser("download", help="Download official FHWA NBI archives")
    download.add_argument("--years", nargs="+", type=int, required=True)
    download.add_argument("--output-dir", type=Path, default=Path("/data/ml/nbi"))
    download.add_argument("--accept-fhwa-disclaimer", action="store_true")

    prepare = sub.add_parser("prepare", help="Build a deterministic bridge-year panel")
    prepare.add_argument("--years", nargs="+", type=int, required=True)
    prepare.add_argument("--input-dir", type=Path, default=Path("/data/ml/nbi"))
    prepare.add_argument("--output", type=Path, default=Path("/data/ml/nbi_panel.csv.gz"))
    prepare.add_argument("--max-records-per-year", type=int, default=75_000)

    train = sub.add_parser("train", help="Train and evaluate gated research-transfer models")
    train.add_argument("--panel", type=Path, default=Path("/data/ml/nbi_panel.csv.gz"))
    train.add_argument("--artifact-dir", type=Path, default=Path("/artifacts/bridge_nbi"))
    train.add_argument("--min-rows", type=int, default=100_000)
    train.add_argument("--min-bridges", type=int, default=20_000)
    train.add_argument("--min-years", type=int, default=5)
    train.add_argument("--horizon-years", type=int, default=3)
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "download":
        for year in args.years:
            path = download_year(
                year,
                args.output_dir,
                accept_disclaimer=args.accept_fhwa_disclaimer,
            )
            print(path)
        return 0
    if args.command == "prepare":
        archives = [(year, args.input_dir / f"nbi_{year}.zip") for year in args.years]
        missing = [str(path) for _, path in archives if not path.exists()]
        if missing:
            raise FileNotFoundError(f"Missing NBI archives: {', '.join(missing)}")
        panel = build_panel(archives, max_records_per_year=args.max_records_per_year)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        panel.to_csv(args.output, index=False, compression="gzip")
        print(json.dumps({"rows": len(panel), "bridges": panel.bridge_key.nunique(), "output": str(args.output)}))
        return 0
    panel = pd.read_csv(args.panel)
    manifest = train_models(
        panel,
        args.artifact_dir,
        min_rows=args.min_rows,
        min_bridges=args.min_bridges,
        min_years=args.min_years,
        horizon_years=args.horizon_years,
    )
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["stage"] != "REJECTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
