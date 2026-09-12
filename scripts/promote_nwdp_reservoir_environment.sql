\set ON_ERROR_STOP on

BEGIN;

INSERT INTO data_sources (
    code,
    name,
    organisation,
    source_type,
    url,
    licence,
    refresh_policy,
    is_authoritative
)
VALUES (
    'NWDP_AP_RESERVOIR_DAILY',
    'AP Reservoir Level and Storage (Manual Daily)',
    'Andhra Pradesh Surface Water Department / NWIC',
    'OFFICIAL_TIME_SERIES',
    'https://www.nwdp.nwic.gov.in/dataset/reservoir-water-level-manual-daily-andhra-pradesh-surface-water-department',
    NULL,
    'Refresh from published NWDP CSV/API snapshot',
    true
)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    organisation = EXCLUDED.organisation,
    source_type = EXCLUDED.source_type,
    url = EXCLUDED.url,
    licence = EXCLUDED.licence,
    refresh_policy = EXCLUDED.refresh_policy,
    is_authoritative = EXCLUDED.is_authoritative,
    updated_at = now();

DELETE FROM environment_observations observation
USING staging.nwdp_reservoir_observations staged,
      assets asset,
      data_sources source
WHERE asset.asset_code = staged.asset_code
  AND source.code = staged.source_code
  AND observation.asset_id = asset.id
  AND observation.source_id = source.id
  AND observation.variable = staged.variable
  AND observation.observed_at = staged.observed_at;

INSERT INTO environment_observations (
    asset_id,
    variable,
    value,
    unit,
    observed_at,
    ingested_at,
    source_id,
    source_type,
    spatial_method,
    quality_flag,
    confidence_score,
    is_estimated
)
SELECT
    asset.id,
    staged.variable,
    staged.value,
    staged.unit,
    staged.observed_at,
    now(),
    source.id,
    staged.source_type,
    staged.spatial_method,
    staged.quality_flag,
    staged.confidence_score,
    staged.is_estimated
FROM staging.nwdp_reservoir_observations staged
JOIN assets asset ON asset.asset_code = staged.asset_code
JOIN data_sources source ON source.code = staged.source_code;

COMMIT;

SELECT
    asset.asset_code,
    observation.variable,
    observation.unit,
    COUNT(*) AS records,
    MIN(observation.observed_at) AS earliest,
    MAX(observation.observed_at) AS latest,
    MIN(observation.value) AS minimum,
    MAX(observation.value) AS maximum,
    BOOL_AND(observation.source_type = 'OBSERVED') AS all_observed,
    BOOL_AND(observation.is_estimated = false) AS none_estimated
FROM environment_observations observation
JOIN assets asset ON asset.id = observation.asset_id
JOIN data_sources source ON source.id = observation.source_id
WHERE source.code = 'NWDP_AP_RESERVOIR_DAILY'
GROUP BY asset.asset_code, observation.variable, observation.unit
ORDER BY asset.asset_code, observation.variable;
