\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    verified_count integer;
BEGIN
    SELECT count(*)
    INTO verified_count
    FROM staging.nwdp_dam_registry
    WHERE asset_code IN (
        'AP_DAM_NWDP_AP01HH0040',
        'AP_DAM_NWDP_AP01HH0049',
        'AP_DAM_NWDP_AP01MH0011',
        'AP_DAM_NWDP_AP01MH0074',
        'AP_DAM_NWDP_AP01MH0135'
    )
      AND verification_status = 'cross_source_exact_id'
      AND verification_confidence = 1.0
      AND nwdp_pic IS NOT NULL
      AND cwc_nrld_no IS NOT NULL
      AND geom IS NOT NULL
      AND ST_IsValid(geom);

    IF verified_count <> 5 THEN
        RAISE EXCEPTION 'Expected 5 verified hydrology assets, found %', verified_count;
    END IF;
END
$$;

INSERT INTO data_sources (
    code, name, organisation, source_type, url, licence,
    refresh_policy, is_authoritative
)
VALUES
    (
        'NWDP_NWIC_2025',
        'National Dam Inventory 2025',
        'National Water Informatics Centre',
        'OFFICIAL_REGISTRY',
        'https://www.nwdp.nwic.gov.in/',
        NULL,
        'Official snapshot verification',
        true
    ),
    (
        'CWC_WRIS_2024',
        'CWC WRIS Dams 2024',
        'Central Water Commission',
        'PROCESSED_GIS_SNAPSHOT',
        'https://bharatlas.com/view/wris_dams',
        'CC0-1.0 per redistribution page',
        'Cross-source geometry verification',
        false
    )
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    organisation = EXCLUDED.organisation,
    source_type = EXCLUDED.source_type,
    url = EXCLUDED.url,
    licence = EXCLUDED.licence,
    refresh_policy = EXCLUDED.refresh_policy,
    is_authoritative = EXCLUDED.is_authoritative,
    updated_at = now();

INSERT INTO assets (
    asset_code,
    name,
    asset_type,
    subtype,
    district,
    owner,
    status,
    identity_status,
    built_year,
    design_life_years,
    material,
    condition,
    representative_geometry,
    source_id,
    confidence_score,
    is_estimated
)
SELECT staged.asset_code,
       staged.name,
       'dam',
       'reservoir_dam',
       NULLIF(staged.district, ''),
       NULL,
       'ACTIVE',
       'VERIFIED',
       NULLIF(staged.built_year, '')::integer,
       NULL,
       NULL,
       NULL,
       staged.geom,
       source.id,
       staged.verification_confidence,
       false
FROM staging.nwdp_dam_registry AS staged
CROSS JOIN data_sources AS source
WHERE staged.asset_code IN (
        'AP_DAM_NWDP_AP01HH0040',
        'AP_DAM_NWDP_AP01HH0049',
        'AP_DAM_NWDP_AP01MH0011',
        'AP_DAM_NWDP_AP01MH0074',
        'AP_DAM_NWDP_AP01MH0135'
    )
  AND source.code = 'NWDP_NWIC_2025'
ON CONFLICT (asset_code) DO UPDATE
SET name = EXCLUDED.name,
    asset_type = EXCLUDED.asset_type,
    subtype = EXCLUDED.subtype,
    district = EXCLUDED.district,
    status = EXCLUDED.status,
    identity_status = EXCLUDED.identity_status,
    built_year = EXCLUDED.built_year,
    design_life_years = EXCLUDED.design_life_years,
    material = EXCLUDED.material,
    condition = EXCLUDED.condition,
    representative_geometry = EXCLUDED.representative_geometry,
    source_id = EXCLUDED.source_id,
    confidence_score = EXCLUDED.confidence_score,
    is_estimated = EXCLUDED.is_estimated,
    updated_at = now();

DELETE FROM asset_geometries AS geometry
USING assets AS asset,
      data_sources AS source
WHERE geometry.asset_id = asset.id
  AND geometry.source_id = source.id
  AND source.code = 'CWC_WRIS_2024'
  AND asset.asset_code IN (
      'AP_DAM_NWDP_AP01HH0040',
      'AP_DAM_NWDP_AP01HH0049',
      'AP_DAM_NWDP_AP01MH0011',
      'AP_DAM_NWDP_AP01MH0074',
      'AP_DAM_NWDP_AP01MH0135'
  );

INSERT INTO asset_geometries (
    asset_id, geometry, geometry_type, source_id, accuracy_m
)
SELECT asset.id,
       staged.geom,
       'POINT',
       source.id,
       NULL
FROM staging.nwdp_dam_registry AS staged
JOIN assets AS asset ON asset.asset_code = staged.asset_code
CROSS JOIN data_sources AS source
WHERE staged.asset_code IN (
        'AP_DAM_NWDP_AP01HH0040',
        'AP_DAM_NWDP_AP01HH0049',
        'AP_DAM_NWDP_AP01MH0011',
        'AP_DAM_NWDP_AP01MH0074',
        'AP_DAM_NWDP_AP01MH0135'
    )
  AND source.code = 'CWC_WRIS_2024';

INSERT INTO asset_identifiers (
    asset_id, source_id, external_id, external_name, match_method, match_confidence
)
SELECT asset.id,
       source.id,
       staged.nwdp_pic,
       staged.name,
       'EXACT_ID',
       staged.verification_confidence
FROM staging.nwdp_dam_registry AS staged
JOIN assets AS asset ON asset.asset_code = staged.asset_code
CROSS JOIN data_sources AS source
WHERE staged.asset_code IN (
        'AP_DAM_NWDP_AP01HH0040',
        'AP_DAM_NWDP_AP01HH0049',
        'AP_DAM_NWDP_AP01MH0011',
        'AP_DAM_NWDP_AP01MH0074',
        'AP_DAM_NWDP_AP01MH0135'
    )
  AND source.code = 'NWDP_NWIC_2025'
ON CONFLICT (source_id, external_id) DO UPDATE
SET asset_id = EXCLUDED.asset_id,
    external_name = EXCLUDED.external_name,
    match_method = EXCLUDED.match_method,
    match_confidence = EXCLUDED.match_confidence;

INSERT INTO asset_identifiers (
    asset_id, source_id, external_id, external_name, match_method, match_confidence
)
SELECT asset.id,
       source.id,
       staged.cwc_nrld_no,
       staged.name,
       'EXACT_ID',
       staged.verification_confidence
FROM staging.nwdp_dam_registry AS staged
JOIN assets AS asset ON asset.asset_code = staged.asset_code
CROSS JOIN data_sources AS source
WHERE staged.asset_code IN (
        'AP_DAM_NWDP_AP01HH0040',
        'AP_DAM_NWDP_AP01HH0049',
        'AP_DAM_NWDP_AP01MH0011',
        'AP_DAM_NWDP_AP01MH0074',
        'AP_DAM_NWDP_AP01MH0135'
    )
  AND source.code = 'CWC_WRIS_2024'
ON CONFLICT (source_id, external_id) DO UPDATE
SET asset_id = EXCLUDED.asset_id,
    external_name = EXCLUDED.external_name,
    match_method = EXCLUDED.match_method,
    match_confidence = EXCLUDED.match_confidence;

INSERT INTO asset_models (
    asset_id, format, version, fidelity_level, model_source,
    is_asset_specific, is_active
)
SELECT asset.id,
       'procedural',
       '1',
       'L0',
       'SIMRAS procedural illustration',
       false,
       true
FROM assets AS asset
WHERE asset.asset_code IN (
        'AP_DAM_NWDP_AP01HH0040',
        'AP_DAM_NWDP_AP01HH0049',
        'AP_DAM_NWDP_AP01MH0011',
        'AP_DAM_NWDP_AP01MH0074',
        'AP_DAM_NWDP_AP01MH0135'
    )
  AND NOT EXISTS (
      SELECT 1
      FROM asset_models AS model
      WHERE model.asset_id = asset.id
        AND model.is_active = true
  );

COMMIT;

SELECT asset.asset_code,
       asset.name,
       asset.district,
       asset.identity_status,
       asset.confidence_score,
       asset.is_estimated,
       round(ST_Y(asset.representative_geometry)::numeric, 6) AS latitude,
       round(ST_X(asset.representative_geometry)::numeric, 6) AS longitude,
       (SELECT count(*) FROM asset_identifiers WHERE asset_id = asset.id) AS identifiers
FROM assets AS asset
WHERE asset.asset_code IN (
    'AP_DAM_NWDP_AP01HH0040',
    'AP_DAM_NWDP_AP01HH0049',
    'AP_DAM_NWDP_AP01MH0011',
    'AP_DAM_NWDP_AP01MH0074',
    'AP_DAM_NWDP_AP01MH0135'
)
ORDER BY asset.asset_code;
