\set ON_ERROR_STOP on

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM staging.nasa_power_observations) THEN
        RAISE EXCEPTION 'NASA POWER staging table is empty';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM staging.nasa_power_observations
        WHERE source_type <> 'REANALYSIS'
           OR quality_flag <> 'MODELLED_REANALYSIS'
           OR is_estimated IS NOT TRUE
    ) THEN
        RAISE EXCEPTION 'NASA POWER staging provenance is invalid';
    END IF;
END
$$;

INSERT INTO data_sources (
    code,
    name,
    organisation,
    source_type,
    url,
    refresh_policy,
    is_authoritative
)
VALUES (
    'NASA_POWER_DAILY',
    'NASA POWER Daily Meteorology',
    'NASA Langley Research Center',
    'REANALYSIS',
    'https://power.larc.nasa.gov/',
    'Daily point refresh; retain modelled-data label',
    true
)
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    organisation = EXCLUDED.organisation,
    source_type = EXCLUDED.source_type,
    url = EXCLUDED.url,
    refresh_policy = EXCLUDED.refresh_policy,
    is_authoritative = EXCLUDED.is_authoritative,
    updated_at = now();

DELETE FROM environment_observations AS observation
USING assets AS asset
WHERE observation.asset_id = asset.id
  AND asset.asset_code IN (SELECT DISTINCT asset_code FROM staging.nasa_power_observations)
  AND observation.source_type = 'SYNTHETIC_DEMO'
  AND observation.variable IN ('rainfall_24h', 'rainfall_7d');

DELETE FROM environment_observations AS observation
USING assets AS asset,
      data_sources AS source,
      staging.nasa_power_observations AS staged
WHERE observation.asset_id = asset.id
  AND observation.source_id = source.id
  AND source.code = 'NASA_POWER_DAILY'
  AND asset.asset_code = staged.asset_code
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
SELECT asset.id,
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
FROM staging.nasa_power_observations AS staged
JOIN assets AS asset ON asset.asset_code = staged.asset_code
CROSS JOIN data_sources AS source
WHERE source.code = 'NASA_POWER_DAILY';

COMMIT;

SELECT asset.asset_code,
       observation.variable,
       count(*) AS records,
       min(observation.observed_at) AS first_observation,
       max(observation.observed_at) AS latest_observation,
       source.code AS source,
       observation.source_type,
       observation.quality_flag,
       observation.is_estimated
FROM environment_observations AS observation
JOIN assets AS asset ON asset.id = observation.asset_id
JOIN data_sources AS source ON source.id = observation.source_id
WHERE source.code = 'NASA_POWER_DAILY'
GROUP BY asset.asset_code,
         observation.variable,
         source.code,
         observation.source_type,
         observation.quality_flag,
         observation.is_estimated
ORDER BY observation.variable;
