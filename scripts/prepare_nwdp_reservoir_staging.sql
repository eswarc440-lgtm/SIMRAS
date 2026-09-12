\set ON_ERROR_STOP on

CREATE SCHEMA IF NOT EXISTS staging;
DROP TABLE IF EXISTS staging.nwdp_reservoir_observations;
CREATE TABLE staging.nwdp_reservoir_observations (
    asset_code text NOT NULL,
    variable text NOT NULL,
    value double precision NOT NULL,
    unit text NOT NULL,
    observed_at timestamptz NOT NULL,
    source_code text NOT NULL,
    source_type text NOT NULL,
    spatial_method text NOT NULL,
    quality_flag text NOT NULL,
    confidence_score double precision NOT NULL,
    is_estimated boolean NOT NULL,
    station_name text NOT NULL,
    station_latitude double precision NOT NULL,
    station_longitude double precision NOT NULL,
    PRIMARY KEY (asset_code, variable, observed_at)
);

CREATE INDEX nwdp_reservoir_observed_at_idx
    ON staging.nwdp_reservoir_observations (observed_at);
