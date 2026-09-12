import argparse
import json
from dataclasses import asdict

from simras_etl.validation import validate_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a SIMRAS asset CSV")
    parser.add_argument("csv_path")
    args = parser.parse_args()
    report = validate_csv(args.csv_path)
    print(json.dumps(asdict(report), indent=2))
    return 1 if report.rejected or report.issues else 0


if __name__ == "__main__":
    raise SystemExit(main())

