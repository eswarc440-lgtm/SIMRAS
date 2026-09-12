\set ON_ERROR_STOP on

CREATE SCHEMA IF NOT EXISTS staging;
DROP TABLE IF EXISTS staging.nasa_power_observations;
CREATE TABLE staging.nasa_power_observations (
    asset_code text NOT NULL,
    variable text NOT NULL,
    value double precision NOT NULL,
    unit text NOT NULL,
    observed_at timestamptz NOT NULL,
    source_record_id text NOT NULL,
    source_type text NOT NULL,
    spatial_method text,
    quality_flag text NOT NULL,
    confidence_score double precision,
    is_estimated boolean NOT NULL,
    PRIMARY KEY (source_record_id)
);
