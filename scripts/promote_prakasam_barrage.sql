\set ON_ERROR_STOP on

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM staging.nwdp_dam_registry
        WHERE nwdp_pic = 'AP01MH0009'
          AND verification_status = 'authoritative_registry_corroborated'
          AND verification_confidence >= 0.95
          AND geom IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'Verified Prakasam Barrage staging record is missing';
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
    'NWDP_NWIC_2025',
    'National Dam Inventory 2025',
    'National Water Informatics Centre',
    'OFFICIAL_REGISTRY',
    'https://www.nwdp.nwic.gov.in/',
    'Official snapshot verification',
    true
)
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    organisation = EXCLUDED.organisation,
    source_type = EXCLUDED.source_type,
    url = EXCLUDED.url,
    refresh_policy = EXCLUDED.refresh_policy,
    is_authoritative = true,
    updated_at = now();

UPDATE assets AS asset
SET name = staged.name,
    asset_type = 'barrage',
    subtype = 'river_barrage',
    district = NULLIF(staged.district, ''),
    owner = 'Water Resources Department, Government of Andhra Pradesh',
    status = 'ACTIVE',
    identity_status = 'VERIFIED',
    built_year = NULLIF(staged.built_year, '')::integer,
    design_life_years = NULL,
    material = NULL,
    condition = NULL,
    representative_geometry = staged.geom,
    source_id = source.id,
    confidence_score = staged.verification_confidence,
    is_estimated = false,
    updated_at = now()
FROM staging.nwdp_dam_registry AS staged,
     data_sources AS source
WHERE asset.asset_code = 'AP_DAM_00001'
  AND staged.nwdp_pic = 'AP01MH0009'
  AND source.code = 'NWDP_NWIC_2025';

DELETE FROM inspections
WHERE asset_id = (SELECT id FROM assets WHERE asset_code = 'AP_DAM_00001')
  AND is_synthetic = true;

DELETE FROM maintenance
WHERE asset_id = (SELECT id FROM assets WHERE asset_code = 'AP_DAM_00001')
  AND is_synthetic = true;

DELETE FROM environment_observations
WHERE asset_id = (SELECT id FROM assets WHERE asset_code = 'AP_DAM_00001')
  AND is_estimated = true;

DELETE FROM predictions
WHERE asset_id = (SELECT id FROM assets WHERE asset_code = 'AP_DAM_00001')
  AND model_version IN ('transparent_rules_v1', 'transparent_rules_v2');

DELETE FROM asset_geometries
WHERE asset_id = (SELECT id FROM assets WHERE asset_code = 'AP_DAM_00001');

INSERT INTO asset_geometries (
    asset_id,
    geometry,
    geometry_type,
    source_id,
    accuracy_m
)
SELECT asset.id,
       staged.geom,
       'POINT',
       source.id,
       NULL
FROM assets AS asset
JOIN staging.nwdp_dam_registry AS staged
  ON staged.nwdp_pic = 'AP01MH0009'
CROSS JOIN data_sources AS source
WHERE asset.asset_code = 'AP_DAM_00001'
  AND source.code = 'NWDP_NWIC_2025';

INSERT INTO asset_identifiers (
    asset_id,
    source_id,
    external_id,
    external_name,
    match_method,
    match_confidence
)
SELECT asset.id,
       source.id,
       staged.nwdp_pic,
       staged.name,
       'EXACT_ID',
       staged.verification_confidence
FROM assets AS asset
JOIN staging.nwdp_dam_registry AS staged
  ON staged.nwdp_pic = 'AP01MH0009'
CROSS JOIN data_sources AS source
WHERE asset.asset_code = 'AP_DAM_00001'
  AND source.code = 'NWDP_NWIC_2025'
ON CONFLICT (source_id, external_id) DO UPDATE
SET asset_id = EXCLUDED.asset_id,
    external_name = EXCLUDED.external_name,
    match_method = EXCLUDED.match_method,
    match_confidence = EXCLUDED.match_confidence;

COMMIT;

SELECT asset.asset_code,
       asset.name,
       asset.identity_status,
       asset.is_estimated,
       asset.confidence_score,
       round(ST_Y(asset.representative_geometry)::numeric, 6) AS latitude,
       round(ST_X(asset.representative_geometry)::numeric, 6) AS longitude,
       (SELECT count(*) FROM predictions WHERE asset_id = asset.id) AS predictions,
       (SELECT count(*) FROM inspections WHERE asset_id = asset.id AND is_synthetic) AS synthetic_inspections,
       (SELECT count(*) FROM environment_observations WHERE asset_id = asset.id AND is_estimated) AS estimated_environment
FROM assets AS asset
WHERE asset.asset_code = 'AP_DAM_00001';
