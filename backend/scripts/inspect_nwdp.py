from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "nwdp"


for path in sorted(DATA.glob("*.csv")):
    print()
    print("=" * 80)
    print(path.name)
    print("=" * 80)

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:

        reader = csv.reader(handle)

        try:
            header = next(reader)
        except StopIteration:
            print("EMPTY FILE")
            continue

        print("HEADERS:")
        for index, column in enumerate(header):
            print(f"{index:02d}: {column}")

        print("\nFIRST RECORD:")

        try:
            row = next(reader)

            for column, value in zip(header, row):
                print(f"{column} = {value}")

        except StopIteration:
            print("NO DATA ROW")