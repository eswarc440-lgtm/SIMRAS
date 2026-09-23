# Data and reality contract

## Non-negotiable rule

Every value displayed in SIMRAS must carry enough metadata for a user to know
what it is and when it was valid.

```json
{
  "value": 31.4,
  "unit": "degC",
  "source": "IMD",
  "source_type": "OBSERVED",
  "observed_at": "2026-08-26T10:00:00Z",
  "ingested_at": "2026-08-26T10:05:00Z",
  "quality_flag": "VALID",
  "confidence": 1.0,
  "is_estimated": false
}
```

## Source types

- `OBSERVED`: current measurement from an identified observation system.
- `GOVERNMENT_RECORD`: static or periodically published official record.
- `SENSOR`: actual instrument observation.
- `SATELLITE_DERIVED`: processed remote-sensing metric.
- `REANALYSIS`: historical model/reanalysis such as ERA5; never labelled live.
- `AI_PREDICTED`: versioned model output.
- `ESTIMATED`: explicitly derived/assumed value.
- `SYNTHETIC_DEMO`: test-only value.
- `UNAVAILABLE`: no responsible value exists.

## Asset identity

Do not join assets only by name. Create one `assets.asset_code`, then attach
source-specific identifiers in `asset_identifiers`. A match stores method and
confidence. Names, coordinates, asset types and administrative location should
all be compared before marking identity `VERIFIED`.

## Required verification before public pilot

1. Canonical asset code exists.
2. Identity is supported by at least one authoritative or independently checked source.
3. Coordinates have been independently verified.
4. Geometry source and horizontal accuracy are known.
5. 3D fidelity and provenance are visible.
6. Environment observations show source type and time.
7. Synthetic inspection/maintenance records are removed or clearly labelled.
8. RUL remains null until longitudinal evaluation succeeds.

## Quarantine policy

ETL records with invalid CRS, coordinates, identifiers, timestamps or units
must be rejected into a quarantine result with an ingestion-run reference.
They must not be silently coerced into the production registry.

