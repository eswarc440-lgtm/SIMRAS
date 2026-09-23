from __future__ import annotations

import csv
import hashlib
import io
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from simras_etl.nwdp_reservoir import (
    LATITUDE_COLUMN,
    LEVEL_COLUMN,
    LONGITUDE_COLUMN,
    STATION_COLUMN,
    STORAGE_COLUMN,
    TIME_COLUMN,
)

RESOURCE_API_URL = "https://www.nwdp.nwic.gov.in/api/3/action/resource_show"
LEVEL_RESOURCE_ID = "6b4a1ebf-413c-4503-ba59-59518e97471b"
STORAGE_RESOURCE_ID = "576f26ce-eb63-4de7-9ddd-aebcc60202c2"
ALLOWED_HOSTS = {"nwdp.nwic.gov.in", "www.nwdp.nwic.gov.in"}
MD5_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")


def _validate_download_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Unsafe NWDP download URL: {url}")


def _validate_csv(content: bytes, required_columns: set[str], label: str) -> None:
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} resource is not UTF-8 CSV") from exc
    reader = csv.DictReader(io.StringIO(decoded))
    columns = set(reader.fieldnames or [])
    missing = required_columns.difference(columns)
    if missing:
        raise ValueError(f"{label} CSV is missing columns: {sorted(missing)}")
    if next(reader, None) is None:
        raise ValueError(f"{label} CSV contains no records")


async def _fetch_resource(
    client: httpx.AsyncClient,
    *,
    resource_id: str,
    required_columns: set[str],
    label: str,
) -> tuple[bytes, dict[str, Any]]:
    metadata_response = await client.get(RESOURCE_API_URL, params={"id": resource_id})
    metadata_response.raise_for_status()
    payload = metadata_response.json()
    if payload.get("success") is not True:
        raise ValueError(f"NWDP metadata request failed for {label}")
    metadata = payload.get("result", {})
    if metadata.get("id") != resource_id or metadata.get("state") != "active":
        raise ValueError(f"NWDP returned invalid metadata for {label}")
    if str(metadata.get("format", "")).upper() != "CSV":
        raise ValueError(f"NWDP {label} resource is not CSV")

    download_url = str(metadata.get("url", ""))
    _validate_download_url(download_url)
    response = await client.get(download_url)
    response.raise_for_status()
    _validate_download_url(str(response.url))
    content = response.content

    expected_size = metadata.get("size")
    if expected_size is not None and len(content) != int(expected_size):
        raise ValueError(
            f"NWDP {label} size mismatch: expected {expected_size}, got {len(content)}"
        )
    expected_hash = str(metadata.get("hash", ""))
    if not MD5_PATTERN.fullmatch(expected_hash):
        raise ValueError(f"NWDP {label} metadata does not contain a valid MD5 hash")
    actual_hash = hashlib.md5(content, usedforsecurity=False).hexdigest()
    if actual_hash.casefold() != expected_hash.casefold():
        raise ValueError(f"NWDP {label} checksum mismatch")

    _validate_csv(content, required_columns, label)
    return content, metadata


async def refresh_nwdp_sources(
    *,
    level_path: str | Path,
    storage_path: str | Path,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Download and atomically replace both verified NWDP reservoir resources."""
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=120, follow_redirects=True)
    common_columns = {
        STATION_COLUMN,
        TIME_COLUMN,
        LATITUDE_COLUMN,
        LONGITUDE_COLUMN,
    }
    try:
        level_content, level_metadata = await _fetch_resource(
            client,
            resource_id=LEVEL_RESOURCE_ID,
            required_columns=common_columns | {LEVEL_COLUMN},
            label="reservoir level",
        )
        storage_content, storage_metadata = await _fetch_resource(
            client,
            resource_id=STORAGE_RESOURCE_ID,
            required_columns=common_columns | {STORAGE_COLUMN},
            label="reservoir storage",
        )
    finally:
        if owns_client:
            await client.aclose()

    destinations = (
        (Path(level_path), level_content),
        (Path(storage_path), storage_content),
    )
    temporary_paths: list[Path] = []
    try:
        for destination, content in destinations:
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(destination.suffix + ".tmp")
            temporary.write_bytes(content)
            temporary_paths.append(temporary)
        for (destination, _), temporary in zip(destinations, temporary_paths, strict=True):
            temporary.replace(destination)
    finally:
        for temporary in temporary_paths:
            temporary.unlink(missing_ok=True)

    return {
        "level": {
            "resource_id": LEVEL_RESOURCE_ID,
            "last_modified": level_metadata.get("last_modified"),
            "size": len(level_content),
            "checksum": level_metadata.get("hash"),
            "path": str(Path(level_path)),
        },
        "storage": {
            "resource_id": STORAGE_RESOURCE_ID,
            "last_modified": storage_metadata.get("last_modified"),
            "size": len(storage_content),
            "checksum": storage_metadata.get("hash"),
            "path": str(Path(storage_path)),
        },
    }
