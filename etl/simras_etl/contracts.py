from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class SourceType(StrEnum):
    OBSERVED = "OBSERVED"
    GOVERNMENT_RECORD = "GOVERNMENT_RECORD"
    SENSOR = "SENSOR"
    SATELLITE_DERIVED = "SATELLITE_DERIVED"
    REANALYSIS = "REANALYSIS"
    AI_PREDICTED = "AI_PREDICTED"
    ESTIMATED = "ESTIMATED"
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(slots=True)
class Provenance:
    source_code: str
    source_type: SourceType
    source_record_id: str | None
    retrieved_at: datetime
    licence: str | None
    checksum: str | None = None
    quality_flag: str = "UNVERIFIED"
    confidence_score: float | None = None
    processing_method: str | None = None


@dataclass(slots=True)
class CanonicalAssetRecord:
    asset_code: str
    name: str
    asset_type: str
    longitude: float
    latitude: float
    district: str | None
    external_identifiers: dict[str, str] = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)
    provenance: Provenance | None = None

