import asyncio
import hashlib
from pathlib import Path

import httpx
import pytest

from simras_etl.nwdp_download import (
    LEVEL_RESOURCE_ID,
    RESOURCE_API_URL,
    STORAGE_RESOURCE_ID,
    refresh_nwdp_sources,
)
from simras_etl.nwdp_reservoir import LEVEL_COLUMN, STORAGE_COLUMN


def _csv(measurement_column: str) -> bytes:
    return (
        "Station,Data Acquisition Time,Latitude,Longitude,"
        f"{measurement_column}\n"
        "SRI SAILAM PROJECT,31-07-2026 08:00,16.083056,78.899722,253.2\n"
    ).encode()


def _metadata(resource_id: str, content: bytes) -> dict:
    return {
        "success": True,
        "result": {
            "id": resource_id,
            "state": "active",
            "format": "CSV",
            "size": len(content),
            "hash": hashlib.md5(content, usedforsecurity=False).hexdigest(),
            "last_modified": "2026-08-27T00:10:00",
            "url": f"https://nwdp.nwic.gov.in/download/{resource_id}.csv",
        },
    }


def test_refresh_nwdp_sources_validates_and_replaces_both_files(tmp_path: Path) -> None:
    level = _csv(LEVEL_COLUMN)
    storage = _csv(STORAGE_COLUMN)

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).startswith(RESOURCE_API_URL):
            resource_id = request.url.params["id"]
            content = level if resource_id == LEVEL_RESOURCE_ID else storage
            return httpx.Response(200, json=_metadata(resource_id, content))
        content = level if LEVEL_RESOURCE_ID in str(request.url) else storage
        return httpx.Response(200, content=content, request=request)

    async def run() -> dict:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=True
        ) as client:
            return await refresh_nwdp_sources(
                level_path=tmp_path / "level.csv",
                storage_path=tmp_path / "storage.csv",
                client=client,
            )

    result = asyncio.run(run())
    assert (tmp_path / "level.csv").read_bytes() == level
    assert (tmp_path / "storage.csv").read_bytes() == storage
    assert result["level"]["resource_id"] == LEVEL_RESOURCE_ID


def test_checksum_failure_preserves_existing_files(tmp_path: Path) -> None:
    level_path = tmp_path / "level.csv"
    storage_path = tmp_path / "storage.csv"
    level_path.write_text("existing level")
    storage_path.write_text("existing storage")
    level = _csv(LEVEL_COLUMN)
    storage = _csv(STORAGE_COLUMN)

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).startswith(RESOURCE_API_URL):
            resource_id = request.url.params["id"]
            content = level if resource_id == LEVEL_RESOURCE_ID else storage
            metadata = _metadata(resource_id, content)
            if resource_id == STORAGE_RESOURCE_ID:
                metadata["result"]["hash"] = "0" * 32
            return httpx.Response(200, json=metadata)
        content = level if LEVEL_RESOURCE_ID in str(request.url) else storage
        return httpx.Response(200, content=content, request=request)

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=True
        ) as client:
            await refresh_nwdp_sources(
                level_path=level_path,
                storage_path=storage_path,
                client=client,
            )

    with pytest.raises(ValueError, match="checksum mismatch"):
        asyncio.run(run())
    assert level_path.read_text() == "existing level"
    assert storage_path.read_text() == "existing storage"
