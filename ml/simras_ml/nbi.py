from __future__ import annotations

import hashlib
import heapq
import math
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

FHWA_URL = "https://www.fhwa.dot.gov/bridge/nbi/{year}hwybronefilenodel.zip"

FEATURE_COLUMNS = [
    "age_years",
    "condition_rating",
    "material_code",
    "design_type_code",
    "average_daily_traffic",
    "truck_traffic_percent",
    "skew_deg",
    "span_count",
    "max_span_m",
    "structure_length_m",
    "inventory_rating",
    "scour_rating",
    "waterway_rating",
]


def _text(line: str, start: int, end: int) -> str:
    return line[start:end].strip()


def _number(line: str, start: int, end: int, *, scale: float = 1.0) -> float:
    value = _text(line, start, end)
    if not value or not value.replace(".", "", 1).isdigit():
        return math.nan
    return float(value) * scale


def _rating(line: str, index: int) -> float:
    value = _text(line, index, index + 1)
    return float(value) if value.isdigit() and 0 <= int(value) <= 9 else math.nan


def parse_fixed_width_record(line: str, report_year: int) -> dict | None:
    """Parse the stable legacy NBI download fields used by SIMRAS.

    Field positions follow FHWA's published 445-character NBI download format.
    Only traceable inspection/inventory fields are retained.
    """

    line = line.rstrip("\r\n")
    if len(line) < 375:
        return None
    state_code = _text(line, 0, 3)
    structure_number = _text(line, 3, 18)
    if not state_code or not structure_number:
        return None

    built_year_raw = _number(line, 156, 160)
    built_year = int(built_year_raw) if not math.isnan(built_year_raw) else None
    ratings = [_rating(line, 258), _rating(line, 259), _rating(line, 260)]
    culvert = _rating(line, 262)
    valid_ratings = [value for value in ratings if not math.isnan(value)]
    if not math.isnan(culvert):
        valid_ratings.append(culvert)
    if not valid_ratings:
        return None

    return {
        "bridge_key": f"{state_code}:{structure_number}",
        "report_year": report_year,
        "age_years": max(0, report_year - built_year) if built_year else math.nan,
        "condition_rating": min(valid_ratings),
        "material_code": _number(line, 201, 202),
        "design_type_code": _number(line, 202, 204),
        "average_daily_traffic": _number(line, 164, 170),
        "truck_traffic_percent": _number(line, 369, 371),
        "skew_deg": _number(line, 180, 182),
        "span_count": _number(line, 207, 210),
        "max_span_m": _number(line, 217, 222, scale=0.1),
        "structure_length_m": _number(line, 222, 228, scale=0.1),
        "inventory_rating": _number(line, 268, 271, scale=0.1),
        "scour_rating": _rating(line, 374),
        "waterway_rating": _rating(line, 275),
    }


def stable_partition(key: str) -> int:
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % 100


def download_year(year: int, output_dir: Path, *, accept_disclaimer: bool) -> Path:
    if not accept_disclaimer:
        raise ValueError("FHWA disclaimer acceptance is required before downloading NBI data")
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"nbi_{year}.zip"
    if destination.exists() and destination.stat().st_size > 1_000_000:
        return destination
    request = urllib.request.Request(
        FHWA_URL.format(year=year),
        headers={"User-Agent": "SIMRAS-Academic-Research/0.1"},
    )
    with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as fh:
        while block := response.read(1024 * 1024):
            fh.write(block)
    return destination


def load_year_archive(path: Path, year: int, max_records: int | None = None) -> pd.DataFrame:
    """Read one FHWA archive with deterministic bridge-level sampling."""

    heap: list[tuple[int, int, dict]] = []
    sequence = 0
    with zipfile.ZipFile(path) as archive:
        members = [m for m in archive.infolist() if not m.is_dir()]
        if not members:
            raise ValueError(f"No records found in {path}")
        member = max(members, key=lambda item: item.file_size)
        with archive.open(member) as raw:
            for raw_line in raw:
                record = parse_fixed_width_record(raw_line.decode("latin-1"), year)
                if record is None:
                    continue
                priority = int(
                    hashlib.sha256(record["bridge_key"].encode()).hexdigest()[:12], 16
                )
                sequence += 1
                if max_records is None:
                    heap.append((0, sequence, record))
                elif len(heap) < max_records:
                    heapq.heappush(heap, (-priority, sequence, record))
                elif priority < -heap[0][0]:
                    heapq.heapreplace(heap, (-priority, sequence, record))
    return pd.DataFrame(item[2] for item in heap)


def build_panel(
    archives: list[tuple[int, Path]],
    *,
    max_records_per_year: int | None = 75_000,
) -> pd.DataFrame:
    frames = [
        load_year_archive(path, year, max_records=max_records_per_year)
        for year, path in archives
    ]
    if not frames:
        raise ValueError("At least one NBI archive is required")
    panel = pd.concat(frames, ignore_index=True)
    panel = panel.drop_duplicates(["bridge_key", "report_year"], keep="last")
    return panel.sort_values(["bridge_key", "report_year"]).reset_index(drop=True)


def add_targets(panel: pd.DataFrame, horizon_years: int = 3) -> pd.DataFrame:
    """Create leakage-safe future condition, risk, and observed-event RUL labels."""

    labelled: list[dict] = []
    for _, group in panel.groupby("bridge_key", sort=False):
        rows = group.sort_values("report_year").to_dict("records")
        last_year = int(rows[-1]["report_year"])
        for index, current in enumerate(rows[:-1]):
            year = int(current["report_year"])
            future = rows[index + 1 :]
            next_row = future[0]
            poor_events = [
                row
                for row in future
                if row["condition_rating"] <= 4 and int(row["report_year"]) > year
            ]
            event = poor_events[0] if poor_events else None
            record = dict(current)
            record["next_condition_rating"] = float(next_row["condition_rating"])
            if event and int(event["report_year"]) - year <= horizon_years:
                record["poor_within_horizon"] = 1.0
            elif last_year - year >= horizon_years:
                record["poor_within_horizon"] = 0.0
            else:
                record["poor_within_horizon"] = math.nan
            record["rul_years"] = (
                float(int(event["report_year"]) - year) if event is not None else math.nan
            )
            labelled.append(record)
    return pd.DataFrame(labelled)
