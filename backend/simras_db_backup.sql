--
-- PostgreSQL database dump
--

\restrict IcyNbedXGPcebLVx3zas8hiqFmJx5n6Gpf9CYgwEHYoCG9pXX7hD0nzcJEw9Ync

-- Dumped from database version 17.10
-- Dumped by pg_dump version 17.10

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: alerts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alerts (
    id integer NOT NULL,
    alert_id character varying(80) NOT NULL,
    asset_id character varying(50) NOT NULL,
    alert_type character varying(100) NOT NULL,
    severity character varying(50) NOT NULL,
    title character varying(255) NOT NULL,
    description text NOT NULL,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    source_data json,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.alerts OWNER TO postgres;

--
-- Name: alerts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.alerts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.alerts_id_seq OWNER TO postgres;

--
-- Name: alerts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.alerts_id_seq OWNED BY public.alerts.id;


--
-- Name: asset_inspections; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.asset_inspections (
    id integer NOT NULL,
    asset_id character varying(50) NOT NULL,
    inspection_date timestamp without time zone NOT NULL,
    inspector character varying(255),
    condition character varying(50),
    inspection_score double precision,
    notes text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    inspection_type character varying(100),
    severity character varying(50),
    crack_severity character varying(50),
    corrosion_level character varying(50),
    structural_defect_level character varying(50),
    inspection_status character varying(50),
    data_source character varying(100),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.asset_inspections OWNER TO postgres;

--
-- Name: COLUMN asset_inspections.inspection_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_inspections.inspection_type IS 'Type of inspection: Visual, Structural, NDT, Routine, etc.';


--
-- Name: COLUMN asset_inspections.severity; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_inspections.severity IS 'Severity: None, Minor, Moderate, Major, Critical';


--
-- Name: COLUMN asset_inspections.crack_severity; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_inspections.crack_severity IS 'Crack assessment: None, Hairline, Moderate, Severe';


--
-- Name: COLUMN asset_inspections.corrosion_level; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_inspections.corrosion_level IS 'Corrosion assessment: None, Minor, Moderate, Severe';


--
-- Name: COLUMN asset_inspections.structural_defect_level; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_inspections.structural_defect_level IS 'Structural defects: None, Minor, Moderate, Severe';


--
-- Name: COLUMN asset_inspections.inspection_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_inspections.inspection_status IS 'Status: Draft, Submitted, Approved, Rejected';


--
-- Name: COLUMN asset_inspections.data_source; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_inspections.data_source IS 'Data source: REAL, SYNTHETIC_DEMO, IMPORTED, SIMULATED';


--
-- Name: COLUMN asset_inspections.updated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_inspections.updated_at IS 'Last update timestamp';


--
-- Name: asset_inspections_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.asset_inspections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.asset_inspections_id_seq OWNER TO postgres;

--
-- Name: asset_inspections_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.asset_inspections_id_seq OWNED BY public.asset_inspections.id;


--
-- Name: asset_maintenance; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.asset_maintenance (
    id integer NOT NULL,
    asset_id character varying(50) NOT NULL,
    maintenance_date timestamp without time zone NOT NULL,
    maintenance_type character varying(100),
    description text,
    status character varying(50),
    cost numeric(12,2),
    performed_by character varying(255),
    next_maintenance_date timestamp without time zone,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    data_source character varying(100),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.asset_maintenance OWNER TO postgres;

--
-- Name: COLUMN asset_maintenance.data_source; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_maintenance.data_source IS 'Data source: REAL, SYNTHETIC_DEMO, IMPORTED, SIMULATED';


--
-- Name: COLUMN asset_maintenance.updated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_maintenance.updated_at IS 'Last update timestamp';


--
-- Name: asset_maintenance_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.asset_maintenance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.asset_maintenance_id_seq OWNER TO postgres;

--
-- Name: asset_maintenance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.asset_maintenance_id_seq OWNED BY public.asset_maintenance.id;


--
-- Name: asset_measurements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.asset_measurements (
    id integer NOT NULL,
    asset_id character varying(50) NOT NULL,
    measurement_time timestamp without time zone NOT NULL,
    measurement_type character varying(100) NOT NULL,
    value numeric(16,6) NOT NULL,
    unit character varying(50),
    source character varying(100),
    quality_flag character varying(50),
    data_source character varying(100),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.asset_measurements OWNER TO postgres;

--
-- Name: COLUMN asset_measurements.asset_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_measurements.asset_id IS 'Foreign key to assets.asset_id';


--
-- Name: COLUMN asset_measurements.measurement_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_measurements.measurement_time IS 'When measurement was taken';


--
-- Name: COLUMN asset_measurements.measurement_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_measurements.measurement_type IS 'Type: water_level, temperature, vibration, crack_width, displacement, rainfall, etc.';


--
-- Name: COLUMN asset_measurements.value; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_measurements.value IS 'Measured value';


--
-- Name: COLUMN asset_measurements.unit; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_measurements.unit IS 'Measurement unit: m, °C, mm, g, etc.';


--
-- Name: COLUMN asset_measurements.source; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_measurements.source IS 'Measurement source: sensor, manual, instrument, etc.';


--
-- Name: COLUMN asset_measurements.quality_flag; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_measurements.quality_flag IS 'Data quality: good, suspect, invalid, etc.';


--
-- Name: COLUMN asset_measurements.data_source; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_measurements.data_source IS 'Data source: REAL, SYNTHETIC_DEMO, IMPORTED, SIMULATED';


--
-- Name: asset_measurements_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.asset_measurements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.asset_measurements_id_seq OWNER TO postgres;

--
-- Name: asset_measurements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.asset_measurements_id_seq OWNED BY public.asset_measurements.id;


--
-- Name: asset_models; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.asset_models (
    id integer NOT NULL,
    asset_id character varying(50) NOT NULL,
    model_name character varying(100) NOT NULL,
    model_version character varying(50),
    model_type character varying(100),
    model_reliability double precision,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    model_url character varying(500),
    model_source character varying(100)
);


ALTER TABLE public.asset_models OWNER TO postgres;

--
-- Name: COLUMN asset_models.model_url; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_models.model_url IS 'URL to model file (e.g., /models/asset.glb)';


--
-- Name: COLUMN asset_models.model_source; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_models.model_source IS 'Model source: Blender, CAD, Scanned, AI-generated, etc.';


--
-- Name: asset_models_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.asset_models_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.asset_models_id_seq OWNER TO postgres;

--
-- Name: asset_models_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.asset_models_id_seq OWNED BY public.asset_models.id;


--
-- Name: asset_predictions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.asset_predictions (
    id integer NOT NULL,
    asset_id character varying(50) NOT NULL,
    model_id integer,
    health_score double precision,
    risk_score double precision,
    remaining_life double precision,
    ai_health double precision,
    ai_risk double precision,
    ai_rul double precision,
    ai_maintenance character varying(255),
    prediction_confidence double precision,
    prediction_timestamp timestamp without time zone NOT NULL,
    prediction_horizon integer,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    model_version character varying(100),
    feature_version character varying(100),
    data_source character varying(100),
    health_score_lower double precision,
    health_score_upper double precision,
    risk_score_lower double precision,
    risk_score_upper double precision,
    rul_lower double precision,
    rul_upper double precision,
    uncertainty_method character varying(50),
    prediction_status character varying(50),
    prediction_error character varying(500)
);


ALTER TABLE public.asset_predictions OWNER TO postgres;

--
-- Name: COLUMN asset_predictions.model_version; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_predictions.model_version IS 'Model version used: e.g., ''random_forest_20260817_182132''';


--
-- Name: COLUMN asset_predictions.feature_version; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_predictions.feature_version IS 'Feature engineering version: e.g., ''v1_20260817''';


--
-- Name: COLUMN asset_predictions.data_source; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_predictions.data_source IS 'Data source: ''REAL'', ''SYNTHETIC_DEMO'', ''IMPORTED_CSV''';


--
-- Name: COLUMN asset_predictions.health_score_lower; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_predictions.health_score_lower IS 'Health score lower bound (95% CI)';


--
-- Name: COLUMN asset_predictions.health_score_upper; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_predictions.health_score_upper IS 'Health score upper bound (95% CI)';


--
-- Name: COLUMN asset_predictions.risk_score_lower; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_predictions.risk_score_lower IS 'Risk score lower bound (95% CI)';


--
-- Name: COLUMN asset_predictions.risk_score_upper; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_predictions.risk_score_upper IS 'Risk score upper bound (95% CI)';


--
-- Name: COLUMN asset_predictions.rul_lower; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_predictions.rul_lower IS 'RUL lower bound (95% CI, years)';


--
-- Name: COLUMN asset_predictions.rul_upper; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_predictions.rul_upper IS 'RUL upper bound (95% CI, years)';


--
-- Name: COLUMN asset_predictions.uncertainty_method; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_predictions.uncertainty_method IS 'Method used: ''oob'', ''residual'', ''bootstrap'', ''none''';


--
-- Name: COLUMN asset_predictions.prediction_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_predictions.prediction_status IS 'Status: ''SUCCESS'', ''FAILED'', ''PARTIAL''';


--
-- Name: COLUMN asset_predictions.prediction_error; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.asset_predictions.prediction_error IS 'Error message if prediction failed';


--
-- Name: asset_predictions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.asset_predictions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.asset_predictions_id_seq OWNER TO postgres;

--
-- Name: asset_predictions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.asset_predictions_id_seq OWNED BY public.asset_predictions.id;


--
-- Name: assets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.assets (
    id integer NOT NULL,
    asset_id character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    type character varying(50) NOT NULL,
    district character varying(100) NOT NULL,
    location character varying(255),
    latitude numeric(10,8),
    longitude numeric(11,8),
    geometry public.geometry(Point,4326),
    age integer,
    design_life integer,
    material character varying(100),
    condition character varying(50),
    status character varying(50),
    owner character varying(255),
    description text,
    data_source character varying(100),
    source_record_id character varying(100),
    import_batch character varying(100),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.assets OWNER TO postgres;

--
-- Name: assets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.assets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.assets_id_seq OWNER TO postgres;

--
-- Name: assets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.assets_id_seq OWNED BY public.assets.id;


--
-- Name: citizen_reports; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.citizen_reports (
    id integer NOT NULL,
    report_id character varying(50) NOT NULL,
    asset_id character varying(50),
    category character varying(100) NOT NULL,
    description text NOT NULL,
    severity character varying(50) DEFAULT 'medium'::character varying NOT NULL,
    status character varying(50) DEFAULT 'open'::character varying NOT NULL,
    latitude numeric(10,8) NOT NULL,
    longitude numeric(11,8) NOT NULL,
    geometry public.geometry(Point,4326),
    images json,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.citizen_reports OWNER TO postgres;

--
-- Name: citizen_reports_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.citizen_reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.citizen_reports_id_seq OWNER TO postgres;

--
-- Name: citizen_reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.citizen_reports_id_seq OWNED BY public.citizen_reports.id;


--
-- Name: health_scores; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.health_scores (
    id integer NOT NULL,
    asset_id character varying(50) NOT NULL,
    score double precision NOT NULL,
    category character varying(50) NOT NULL,
    confidence double precision,
    factors json,
    calculated_at timestamp without time zone DEFAULT now() NOT NULL,
    data_source character varying(100) DEFAULT 'CALCULATED_BASELINE'::character varying NOT NULL
);


ALTER TABLE public.health_scores OWNER TO postgres;

--
-- Name: health_scores_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.health_scores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.health_scores_id_seq OWNER TO postgres;

--
-- Name: health_scores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.health_scores_id_seq OWNED BY public.health_scores.id;


--
-- Name: infrastructure_assets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.infrastructure_assets (
    id integer NOT NULL,
    asset_id character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    asset_type character varying(50) NOT NULL,
    description text,
    latitude character varying(50),
    longitude character varying(50),
    location character varying(255),
    geometry public.geometry(Point,4326),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.infrastructure_assets OWNER TO postgres;

--
-- Name: infrastructure_assets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.infrastructure_assets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.infrastructure_assets_id_seq OWNER TO postgres;

--
-- Name: infrastructure_assets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.infrastructure_assets_id_seq OWNED BY public.infrastructure_assets.id;


--
-- Name: risk_scores; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.risk_scores (
    id integer NOT NULL,
    asset_id character varying(50) NOT NULL,
    score double precision NOT NULL,
    risk_level character varying(50) NOT NULL,
    hazard character varying(100),
    confidence double precision,
    factors json,
    calculated_at timestamp without time zone DEFAULT now() NOT NULL,
    data_source character varying(100) DEFAULT 'CALCULATED_BASELINE'::character varying NOT NULL
);


ALTER TABLE public.risk_scores OWNER TO postgres;

--
-- Name: risk_scores_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.risk_scores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.risk_scores_id_seq OWNER TO postgres;

--
-- Name: risk_scores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.risk_scores_id_seq OWNED BY public.risk_scores.id;


--
-- Name: roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    description text,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.roles OWNER TO postgres;

--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.roles_id_seq OWNER TO postgres;

--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: satellite_observations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.satellite_observations (
    id integer NOT NULL,
    provider character varying(100) NOT NULL,
    asset_id character varying(50),
    observation_type character varying(100) NOT NULL,
    observed_at timestamp without time zone NOT NULL,
    geometry public.geometry(Geometry,4326),
    status character varying(50) DEFAULT 'metadata_only'::character varying NOT NULL,
    metadata_json json,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.satellite_observations OWNER TO postgres;

--
-- Name: satellite_observations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.satellite_observations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.satellite_observations_id_seq OWNER TO postgres;

--
-- Name: satellite_observations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.satellite_observations_id_seq OWNED BY public.satellite_observations.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    full_name character varying(255) NOT NULL,
    organization character varying(255),
    role character varying(50) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: weather_forecasts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.weather_forecasts (
    id integer NOT NULL,
    provider character varying(100) NOT NULL,
    latitude numeric(10,8) NOT NULL,
    longitude numeric(11,8) NOT NULL,
    geometry public.geometry(Point,4326),
    forecast_for timestamp without time zone NOT NULL,
    fetched_at timestamp without time zone DEFAULT now() NOT NULL,
    horizon_hours integer DEFAULT 24 NOT NULL,
    payload json NOT NULL,
    data_source character varying(100) DEFAULT 'OPEN_METEO'::character varying NOT NULL
);


ALTER TABLE public.weather_forecasts OWNER TO postgres;

--
-- Name: weather_forecasts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.weather_forecasts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.weather_forecasts_id_seq OWNER TO postgres;

--
-- Name: weather_forecasts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.weather_forecasts_id_seq OWNED BY public.weather_forecasts.id;


--
-- Name: weather_observations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.weather_observations (
    id integer NOT NULL,
    provider character varying(100) NOT NULL,
    latitude numeric(10,8) NOT NULL,
    longitude numeric(11,8) NOT NULL,
    geometry public.geometry(Point,4326),
    observed_at timestamp without time zone NOT NULL,
    temperature_c double precision,
    precipitation_mm double precision,
    rainfall_mm double precision,
    humidity_percent double precision,
    wind_speed_kmh double precision,
    wind_direction_deg double precision,
    pressure_hpa double precision,
    weather_code integer,
    data_source character varying(100) DEFAULT 'OPEN_METEO'::character varying NOT NULL,
    raw_payload json,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.weather_observations OWNER TO postgres;

--
-- Name: weather_observations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.weather_observations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.weather_observations_id_seq OWNER TO postgres;

--
-- Name: weather_observations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.weather_observations_id_seq OWNED BY public.weather_observations.id;


--
-- Name: alerts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts ALTER COLUMN id SET DEFAULT nextval('public.alerts_id_seq'::regclass);


--
-- Name: asset_inspections id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_inspections ALTER COLUMN id SET DEFAULT nextval('public.asset_inspections_id_seq'::regclass);


--
-- Name: asset_maintenance id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_maintenance ALTER COLUMN id SET DEFAULT nextval('public.asset_maintenance_id_seq'::regclass);


--
-- Name: asset_measurements id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_measurements ALTER COLUMN id SET DEFAULT nextval('public.asset_measurements_id_seq'::regclass);


--
-- Name: asset_models id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_models ALTER COLUMN id SET DEFAULT nextval('public.asset_models_id_seq'::regclass);


--
-- Name: asset_predictions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_predictions ALTER COLUMN id SET DEFAULT nextval('public.asset_predictions_id_seq'::regclass);


--
-- Name: assets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assets ALTER COLUMN id SET DEFAULT nextval('public.assets_id_seq'::regclass);


--
-- Name: citizen_reports id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.citizen_reports ALTER COLUMN id SET DEFAULT nextval('public.citizen_reports_id_seq'::regclass);


--
-- Name: health_scores id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.health_scores ALTER COLUMN id SET DEFAULT nextval('public.health_scores_id_seq'::regclass);


--
-- Name: infrastructure_assets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.infrastructure_assets ALTER COLUMN id SET DEFAULT nextval('public.infrastructure_assets_id_seq'::regclass);


--
-- Name: risk_scores id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.risk_scores ALTER COLUMN id SET DEFAULT nextval('public.risk_scores_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: satellite_observations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.satellite_observations ALTER COLUMN id SET DEFAULT nextval('public.satellite_observations_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: weather_forecasts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.weather_forecasts ALTER COLUMN id SET DEFAULT nextval('public.weather_forecasts_id_seq'::regclass);


--
-- Name: weather_observations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.weather_observations ALTER COLUMN id SET DEFAULT nextval('public.weather_observations_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
006
\.


--
-- Data for Name: alerts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alerts (id, alert_id, asset_id, alert_type, severity, title, description, status, source_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: asset_inspections; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.asset_inspections (id, asset_id, inspection_date, inspector, condition, inspection_score, notes, created_at, inspection_type, severity, crack_severity, corrosion_level, structural_defect_level, inspection_status, data_source, updated_at) FROM stdin;
1	AP-VIJ-DAM-001	2026-08-18 10:30:00	\N	\N	\N	\N	2026-08-18 07:36:54.299875	\N	\N	\N	\N	\N	\N	REAL	2026-08-18 07:36:54.299875
\.


--
-- Data for Name: asset_maintenance; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.asset_maintenance (id, asset_id, maintenance_date, maintenance_type, description, status, cost, performed_by, next_maintenance_date, created_at, data_source, updated_at) FROM stdin;
1	AP-VIJ-DAM-001	2026-08-18 08:00:00	Preventive	Annual preventive maintenance - dam structural inspection	Scheduled	25000.00	AP Irrigation Dept	2026-11-16 02:10:41.246416	2026-08-18 07:40:41.320608	REAL	2026-08-18 07:40:41.320608
\.


--
-- Data for Name: asset_measurements; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.asset_measurements (id, asset_id, measurement_time, measurement_type, value, unit, source, quality_flag, data_source, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: asset_models; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.asset_models (id, asset_id, model_name, model_version, model_type, model_reliability, created_at, updated_at, model_url, model_source) FROM stdin;
\.


--
-- Data for Name: asset_predictions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.asset_predictions (id, asset_id, model_id, health_score, risk_score, remaining_life, ai_health, ai_risk, ai_rul, ai_maintenance, prediction_confidence, prediction_timestamp, prediction_horizon, created_at, model_version, feature_version, data_source, health_score_lower, health_score_upper, risk_score_lower, risk_score_upper, rul_lower, rul_upper, uncertainty_method, prediction_status, prediction_error) FROM stdin;
1	AP-VIJ-DAM-001	\N	73.77	28.85	28.88	\N	\N	\N	\N	\N	2026-08-18 02:29:31.627551	\N	2026-08-18 07:59:26.707532	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
2	AP-VIJ-DAM-001	\N	73.77	28.85	28.88	\N	\N	\N	\N	\N	2026-08-18 02:29:36.772072	\N	2026-08-18 07:59:31.889582	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
3	AP-VIJ-BRG-001	\N	74.57	25.07	47.6	\N	\N	\N	\N	\N	2026-08-18 02:29:42.1576	\N	2026-08-18 07:59:36.839466	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
4	AP-KRS-RD-001	\N	78.22	22.5	21.64	\N	\N	\N	\N	\N	2026-08-18 02:29:46.938495	\N	2026-08-18 07:59:42.230263	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
5	AP-VIJ-DAM-001	\N	73.77	28.85	28.88	\N	\N	\N	\N	\N	2026-08-18 02:31:21.298291	\N	2026-08-18 08:01:21.174388	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
6	AP-VIJ-BRG-001	\N	74.57	25.07	47.6	\N	\N	\N	\N	\N	2026-08-18 02:31:21.569006	\N	2026-08-18 08:01:21.45094	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
7	AP-ELU-DAM-001	\N	58.15	48.45	20.46	\N	\N	\N	\N	\N	2026-08-18 02:31:21.84361	\N	2026-08-18 08:01:21.723324	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
8	AP-KRS-RD-001	\N	78.22	22.5	21.64	\N	\N	\N	\N	\N	2026-08-18 02:31:22.132163	\N	2026-08-18 08:01:22.01366	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
9	AP-GNT-SCH-001	\N	77.23	22.41	31.59	\N	\N	\N	\N	\N	2026-08-18 02:31:22.398275	\N	2026-08-18 08:01:22.288384	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
10	AP-VIJ-DAM-001	\N	73.77	28.85	28.88	\N	\N	\N	\N	\N	2026-08-18 02:32:58.615877	\N	2026-08-18 08:02:53.818042	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
11	AP-VIJ-DAM-001	\N	73.77	28.85	28.88	\N	\N	\N	\N	\N	2026-08-18 02:32:58.889316	\N	2026-08-18 08:02:58.774654	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
12	AP-VIJ-BRG-001	\N	74.57	25.07	47.6	\N	\N	\N	\N	\N	2026-08-18 02:32:59.081233	\N	2026-08-18 08:02:58.960364	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
13	AP-VIJ-BRG-002	\N	85.1	14.97	56	\N	\N	\N	\N	\N	2026-08-18 02:32:59.268877	\N	2026-08-18 08:02:59.156925	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
14	AP-ELU-DAM-001	\N	58.15	48.45	20.46	\N	\N	\N	\N	\N	2026-08-18 02:32:59.450415	\N	2026-08-18 08:02:59.344734	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
15	AP-ELU-DAM-002	\N	79.61	21.97	62.88	\N	\N	\N	\N	\N	2026-08-18 02:32:59.636602	\N	2026-08-18 08:02:59.518999	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: assets; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.assets (id, asset_id, name, type, district, location, latitude, longitude, geometry, age, design_life, material, condition, status, owner, description, data_source, source_record_id, import_batch, created_at, updated_at) FROM stdin;
15	AP-VIJ-DAM-001	Vijayawada Main Dam	dam	NTR	Vijayawada	16.52040000	80.64690000	0101000020E610000013F241CF66295440A1D634EF38853040	45	50	Concrete	Good	Operational	AP Irrigation Department	\N	CSV	AP-VIJ-DAM-001	phase3_import	2026-08-18 07:13:49.385524	2026-08-18 07:13:49.385524
16	AP-VIJ-BRG-001	Krishna River Bridge	bridge	NTR	Vijayawada	16.51000000	80.65000000	0101000020E61000009A99999999295440C3F5285C8F823040	30	75	Steel-RCC	Fair	Operational	NHAI	\N	CSV	AP-VIJ-BRG-001	phase3_import	2026-08-18 07:13:49.385524	2026-08-18 07:13:49.385524
17	AP-VIJ-BRG-002	NH44 Bypass Bridge	bridge	NTR	Vijayawada	16.49000000	80.63000000	0101000020E6100000B81E85EB512854403D0AD7A3707D3040	15	75	RCC	Good	Operational	NHAI	\N	CSV	AP-VIJ-BRG-002	phase3_import	2026-08-18 07:13:49.385524	2026-08-18 07:13:49.385524
18	AP-ELU-DAM-001	Eluru Tank	dam	Eluru	Eluru	16.70500000	82.07750000	0101000020E6100000295C8FC2F584544014AE47E17AB43040	60	75	Masonry	Poor	Operational	AP Irrigation Department	\N	CSV	AP-ELU-DAM-001	phase3_import	2026-08-18 07:13:49.385524	2026-08-18 07:13:49.385524
19	AP-ELU-DAM-002	Polavaram Project	dam	Eluru	Polavaram	16.64500000	81.67000000	0101000020E61000007B14AE47E16A544085EB51B81EA53040	8	100	Concrete	Excellent	Under Construction	NTPC	\N	CSV	AP-ELU-DAM-002	phase3_import	2026-08-18 07:13:49.385524	2026-08-18 07:13:49.385524
20	AP-KRS-RD-001	Krishna National Highway	road	Krishna	Machilipatnam	15.79420000	81.12610000	0101000020E6100000A301BC051248544066F7E461A1962F40	20	30	Asphalt	Good	Operational	National Highways Authority	\N	CSV	AP-KRS-RD-001	phase3_import	2026-08-18 07:13:49.385524	2026-08-18 07:13:49.385524
21	AP-KRS-RD-002	State Highway 5	road	Krishna	Vijayawada-Machilipatnam	15.82000000	81.15000000	0101000020E61000009A99999999495440A4703D0AD7A32F40	12	30	Asphalt	Fair	Operational	AP PWD	\N	CSV	AP-KRS-RD-002	phase3_import	2026-08-18 07:13:49.385524	2026-08-18 07:13:49.385524
22	AP-KRS-BRG-001	Pulicat Bridge	bridge	Krishna	Pulicat	14.14500000	79.83000000	0101000020E610000085EB51B81EF553400AD7A3703D4A2C40	25	75	RCC	Fair	Operational	NHAI	\N	CSV	AP-KRS-BRG-001	phase3_import	2026-08-18 07:13:49.385524	2026-08-18 07:13:49.385524
23	AP-GNT-SCH-001	Government School Guntur	school	Guntur	Guntur City	16.30670000	80.43650000	0101000020E61000000E2DB29DEF1B5440E6AE25E4834E3040	25	60	RCC	Good	Operational	AP Government	\N	CSV	AP-GNT-SCH-001	phase3_import	2026-08-18 07:13:49.385524	2026-08-18 07:13:49.385524
24	AP-GNT-BLD-001	Municipal Corporation Office	building	Guntur	Guntur City	16.31000000	80.44000000	0101000020E61000005C8FC2F5281C54408FC2F5285C4F3040	35	75	RCC	Fair	Operational	Guntur Municipality	\N	CSV	AP-GNT-BLD-001	phase3_import	2026-08-18 07:13:49.385524	2026-08-18 07:13:49.385524
25	AP-GNT-DAM-001	Uppaleru Dam	dam	Guntur	Uppaleru	16.20000000	80.20000000	0101000020E6100000CDCCCCCCCC0C54403333333333333040	70	100	Masonry	Fair	Operational	AP Irrigation Department	\N	CSV	AP-GNT-DAM-001	phase3_import	2026-08-18 07:13:49.385524	2026-08-18 07:13:49.385524
26	AP-NTR-APT-001	Vijayawada Airport Terminal	building	NTR	Vijayawada	16.52800000	80.79500000	0101000020E61000007B14AE47E1325440BA490C022B873040	20	75	RCC-Steel	Good	Operational	Airports Authority	\N	CSV	AP-NTR-APT-001	phase3_import	2026-08-18 07:13:49.385524	2026-08-18 07:13:49.385524
\.


--
-- Data for Name: citizen_reports; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.citizen_reports (id, report_id, asset_id, category, description, severity, status, latitude, longitude, geometry, images, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: health_scores; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.health_scores (id, asset_id, score, category, confidence, factors, calculated_at, data_source) FROM stdin;
\.


--
-- Data for Name: infrastructure_assets; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.infrastructure_assets (id, asset_id, name, asset_type, description, latitude, longitude, location, geometry, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: risk_scores; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.risk_scores (id, asset_id, score, risk_level, hazard, confidence, factors, calculated_at, data_source) FROM stdin;
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.roles (id, name, description, created_at) FROM stdin;
1	ADMIN	System administrator	2026-08-18 22:24:50.934569
2	ENGINEER	Infrastructure engineer	2026-08-18 22:24:50.934569
3	URBAN_PLANNER	Urban planning analyst	2026-08-18 22:24:50.934569
4	DISASTER_OFFICER	Disaster response officer	2026-08-18 22:24:50.934569
5	CITIZEN	Citizen reporter	2026-08-18 22:24:50.934569
\.


--
-- Data for Name: satellite_observations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.satellite_observations (id, provider, asset_id, observation_type, observed_at, geometry, status, metadata_json, created_at) FROM stdin;
\.


--
-- Data for Name: spatial_ref_sys; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, email, password_hash, full_name, organization, role, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: weather_forecasts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.weather_forecasts (id, provider, latitude, longitude, geometry, forecast_for, fetched_at, horizon_hours, payload, data_source) FROM stdin;
\.


--
-- Data for Name: weather_observations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.weather_observations (id, provider, latitude, longitude, geometry, observed_at, temperature_c, precipitation_mm, rainfall_mm, humidity_percent, wind_speed_kmh, wind_direction_deg, pressure_hpa, weather_code, data_source, raw_payload, created_at) FROM stdin;
\.


--
-- Name: alerts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.alerts_id_seq', 1, false);


--
-- Name: asset_inspections_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.asset_inspections_id_seq', 2, true);


--
-- Name: asset_maintenance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.asset_maintenance_id_seq', 5, true);


--
-- Name: asset_measurements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.asset_measurements_id_seq', 1, false);


--
-- Name: asset_models_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.asset_models_id_seq', 3, true);


--
-- Name: asset_predictions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.asset_predictions_id_seq', 15, true);


--
-- Name: assets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.assets_id_seq', 26, true);


--
-- Name: citizen_reports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.citizen_reports_id_seq', 1, false);


--
-- Name: health_scores_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.health_scores_id_seq', 1, false);


--
-- Name: infrastructure_assets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.infrastructure_assets_id_seq', 1, false);


--
-- Name: risk_scores_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.risk_scores_id_seq', 1, false);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.roles_id_seq', 5, true);


--
-- Name: satellite_observations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.satellite_observations_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 1, false);


--
-- Name: weather_forecasts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.weather_forecasts_id_seq', 1, false);


--
-- Name: weather_observations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.weather_observations_id_seq', 1, false);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: alerts alerts_alert_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_alert_id_key UNIQUE (alert_id);


--
-- Name: alerts alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_pkey PRIMARY KEY (id);


--
-- Name: asset_inspections asset_inspections_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_inspections
    ADD CONSTRAINT asset_inspections_pkey PRIMARY KEY (id);


--
-- Name: asset_maintenance asset_maintenance_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_maintenance
    ADD CONSTRAINT asset_maintenance_pkey PRIMARY KEY (id);


--
-- Name: asset_measurements asset_measurements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_measurements
    ADD CONSTRAINT asset_measurements_pkey PRIMARY KEY (id);


--
-- Name: asset_models asset_models_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_models
    ADD CONSTRAINT asset_models_pkey PRIMARY KEY (id);


--
-- Name: asset_predictions asset_predictions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_predictions
    ADD CONSTRAINT asset_predictions_pkey PRIMARY KEY (id);


--
-- Name: assets assets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT assets_pkey PRIMARY KEY (id);


--
-- Name: citizen_reports citizen_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.citizen_reports
    ADD CONSTRAINT citizen_reports_pkey PRIMARY KEY (id);


--
-- Name: citizen_reports citizen_reports_report_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.citizen_reports
    ADD CONSTRAINT citizen_reports_report_id_key UNIQUE (report_id);


--
-- Name: health_scores health_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.health_scores
    ADD CONSTRAINT health_scores_pkey PRIMARY KEY (id);


--
-- Name: infrastructure_assets infrastructure_assets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.infrastructure_assets
    ADD CONSTRAINT infrastructure_assets_pkey PRIMARY KEY (id);


--
-- Name: risk_scores risk_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.risk_scores
    ADD CONSTRAINT risk_scores_pkey PRIMARY KEY (id);


--
-- Name: roles roles_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_name_key UNIQUE (name);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: satellite_observations satellite_observations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.satellite_observations
    ADD CONSTRAINT satellite_observations_pkey PRIMARY KEY (id);


--
-- Name: assets uq_asset_asset_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT uq_asset_asset_id UNIQUE (asset_id);


--
-- Name: infrastructure_assets uq_infrastructure_asset_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.infrastructure_assets
    ADD CONSTRAINT uq_infrastructure_asset_id UNIQUE (asset_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: weather_forecasts weather_forecasts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.weather_forecasts
    ADD CONSTRAINT weather_forecasts_pkey PRIMARY KEY (id);


--
-- Name: weather_observations weather_observations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.weather_observations
    ADD CONSTRAINT weather_observations_pkey PRIMARY KEY (id);


--
-- Name: idx_asset_condition; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_asset_condition ON public.assets USING btree (condition);


--
-- Name: idx_asset_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_asset_created_at ON public.assets USING btree (created_at);


--
-- Name: idx_asset_district; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_asset_district ON public.assets USING btree (district);


--
-- Name: idx_asset_geometry; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_asset_geometry ON public.assets USING gist (geometry);


--
-- Name: idx_asset_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_asset_id ON public.assets USING btree (asset_id);


--
-- Name: idx_asset_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_asset_status ON public.assets USING btree (status);


--
-- Name: idx_asset_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_asset_type ON public.assets USING btree (type);


--
-- Name: idx_assets_geometry; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_assets_geometry ON public.assets USING gist (geometry);


--
-- Name: idx_citizen_report_geometry; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_citizen_report_geometry ON public.citizen_reports USING gist (geometry);


--
-- Name: idx_citizen_reports_geometry; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_citizen_reports_geometry ON public.citizen_reports USING gist (geometry);


--
-- Name: idx_infrastructure_asset_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_infrastructure_asset_id ON public.infrastructure_assets USING btree (asset_id);


--
-- Name: idx_infrastructure_asset_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_infrastructure_asset_type ON public.infrastructure_assets USING btree (asset_type);


--
-- Name: idx_infrastructure_assets_geometry; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_infrastructure_assets_geometry ON public.infrastructure_assets USING gist (geometry);


--
-- Name: idx_infrastructure_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_infrastructure_created_at ON public.infrastructure_assets USING btree (created_at);


--
-- Name: idx_infrastructure_geometry; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_infrastructure_geometry ON public.infrastructure_assets USING gist (geometry);


--
-- Name: idx_inspection_asset_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_inspection_asset_id ON public.asset_inspections USING btree (asset_id);


--
-- Name: idx_inspection_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_inspection_date ON public.asset_inspections USING btree (inspection_date);


--
-- Name: idx_maintenance_asset_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_maintenance_asset_id ON public.asset_maintenance USING btree (asset_id);


--
-- Name: idx_maintenance_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_maintenance_date ON public.asset_maintenance USING btree (maintenance_date);


--
-- Name: idx_measurement_asset_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_measurement_asset_id ON public.asset_measurements USING btree (asset_id);


--
-- Name: idx_measurement_asset_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_measurement_asset_time ON public.asset_measurements USING btree (asset_id, measurement_time);


--
-- Name: idx_measurement_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_measurement_time ON public.asset_measurements USING btree (measurement_time);


--
-- Name: idx_measurement_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_measurement_type ON public.asset_measurements USING btree (measurement_type);


--
-- Name: idx_model_asset_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_model_asset_id ON public.asset_models USING btree (asset_id);


--
-- Name: idx_model_source; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_model_source ON public.asset_models USING btree (model_source);


--
-- Name: idx_model_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_model_type ON public.asset_models USING btree (model_type);


--
-- Name: idx_model_version; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_model_version ON public.asset_models USING btree (model_version);


--
-- Name: idx_prediction_asset_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_prediction_asset_id ON public.asset_predictions USING btree (asset_id);


--
-- Name: idx_prediction_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_prediction_timestamp ON public.asset_predictions USING btree (prediction_timestamp);


--
-- Name: idx_satellite_observation_geometry; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_satellite_observation_geometry ON public.satellite_observations USING gist (geometry);


--
-- Name: idx_satellite_observations_geometry; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_satellite_observations_geometry ON public.satellite_observations USING gist (geometry);


--
-- Name: idx_weather_forecast_location_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_weather_forecast_location_time ON public.weather_forecasts USING btree (latitude, longitude, forecast_for);


--
-- Name: idx_weather_forecast_point; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_weather_forecast_point ON public.weather_forecasts USING gist (geometry);


--
-- Name: idx_weather_forecasts_geometry; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_weather_forecasts_geometry ON public.weather_forecasts USING gist (geometry);


--
-- Name: idx_weather_observation_location_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_weather_observation_location_time ON public.weather_observations USING btree (latitude, longitude, observed_at);


--
-- Name: idx_weather_observation_point; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_weather_observation_point ON public.weather_observations USING gist (geometry);


--
-- Name: idx_weather_observations_geometry; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_weather_observations_geometry ON public.weather_observations USING gist (geometry);


--
-- Name: ix_alerts_alert_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_alerts_alert_id ON public.alerts USING btree (alert_id);


--
-- Name: ix_alerts_alert_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_alerts_alert_type ON public.alerts USING btree (alert_type);


--
-- Name: ix_alerts_asset_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_alerts_asset_id ON public.alerts USING btree (asset_id);


--
-- Name: ix_alerts_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_alerts_id ON public.alerts USING btree (id);


--
-- Name: ix_alerts_severity; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_alerts_severity ON public.alerts USING btree (severity);


--
-- Name: ix_alerts_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_alerts_status ON public.alerts USING btree (status);


--
-- Name: ix_asset_measurements_measurement_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_asset_measurements_measurement_time ON public.asset_measurements USING btree (measurement_time);


--
-- Name: ix_citizen_reports_asset_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_citizen_reports_asset_id ON public.citizen_reports USING btree (asset_id);


--
-- Name: ix_citizen_reports_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_citizen_reports_category ON public.citizen_reports USING btree (category);


--
-- Name: ix_citizen_reports_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_citizen_reports_id ON public.citizen_reports USING btree (id);


--
-- Name: ix_citizen_reports_report_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_citizen_reports_report_id ON public.citizen_reports USING btree (report_id);


--
-- Name: ix_citizen_reports_severity; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_citizen_reports_severity ON public.citizen_reports USING btree (severity);


--
-- Name: ix_citizen_reports_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_citizen_reports_status ON public.citizen_reports USING btree (status);


--
-- Name: ix_health_scores_asset_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_health_scores_asset_id ON public.health_scores USING btree (asset_id);


--
-- Name: ix_health_scores_calculated_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_health_scores_calculated_at ON public.health_scores USING btree (calculated_at);


--
-- Name: ix_health_scores_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_health_scores_id ON public.health_scores USING btree (id);


--
-- Name: ix_risk_scores_asset_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_risk_scores_asset_id ON public.risk_scores USING btree (asset_id);


--
-- Name: ix_risk_scores_calculated_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_risk_scores_calculated_at ON public.risk_scores USING btree (calculated_at);


--
-- Name: ix_risk_scores_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_risk_scores_id ON public.risk_scores USING btree (id);


--
-- Name: ix_roles_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_roles_id ON public.roles USING btree (id);


--
-- Name: ix_roles_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_roles_name ON public.roles USING btree (name);


--
-- Name: ix_satellite_observations_asset_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_satellite_observations_asset_id ON public.satellite_observations USING btree (asset_id);


--
-- Name: ix_satellite_observations_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_satellite_observations_id ON public.satellite_observations USING btree (id);


--
-- Name: ix_satellite_observations_observed_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_satellite_observations_observed_at ON public.satellite_observations USING btree (observed_at);


--
-- Name: ix_satellite_observations_provider; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_satellite_observations_provider ON public.satellite_observations USING btree (provider);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_role ON public.users USING btree (role);


--
-- Name: ix_weather_forecasts_forecast_for; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_weather_forecasts_forecast_for ON public.weather_forecasts USING btree (forecast_for);


--
-- Name: ix_weather_forecasts_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_weather_forecasts_id ON public.weather_forecasts USING btree (id);


--
-- Name: ix_weather_forecasts_provider; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_weather_forecasts_provider ON public.weather_forecasts USING btree (provider);


--
-- Name: ix_weather_observations_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_weather_observations_id ON public.weather_observations USING btree (id);


--
-- Name: ix_weather_observations_observed_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_weather_observations_observed_at ON public.weather_observations USING btree (observed_at);


--
-- Name: ix_weather_observations_provider; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_weather_observations_provider ON public.weather_observations USING btree (provider);


--
-- Name: alerts alerts_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(asset_id) ON DELETE CASCADE;


--
-- Name: asset_inspections asset_inspections_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_inspections
    ADD CONSTRAINT asset_inspections_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(asset_id) ON DELETE CASCADE;


--
-- Name: asset_maintenance asset_maintenance_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_maintenance
    ADD CONSTRAINT asset_maintenance_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(asset_id) ON DELETE CASCADE;


--
-- Name: asset_measurements asset_measurements_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_measurements
    ADD CONSTRAINT asset_measurements_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(asset_id) ON DELETE CASCADE;


--
-- Name: asset_models asset_models_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_models
    ADD CONSTRAINT asset_models_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(asset_id) ON DELETE CASCADE;


--
-- Name: asset_predictions asset_predictions_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_predictions
    ADD CONSTRAINT asset_predictions_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(asset_id) ON DELETE CASCADE;


--
-- Name: asset_predictions asset_predictions_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asset_predictions
    ADD CONSTRAINT asset_predictions_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.asset_models(id) ON DELETE SET NULL;


--
-- Name: citizen_reports citizen_reports_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.citizen_reports
    ADD CONSTRAINT citizen_reports_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(asset_id) ON DELETE SET NULL;


--
-- Name: health_scores health_scores_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.health_scores
    ADD CONSTRAINT health_scores_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(asset_id) ON DELETE CASCADE;


--
-- Name: risk_scores risk_scores_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.risk_scores
    ADD CONSTRAINT risk_scores_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(asset_id) ON DELETE CASCADE;


--
-- Name: satellite_observations satellite_observations_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.satellite_observations
    ADD CONSTRAINT satellite_observations_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(asset_id) ON DELETE SET NULL;


--
-- Name: users users_role_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_role_fkey FOREIGN KEY (role) REFERENCES public.roles(name) ON DELETE RESTRICT;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO simras;


--
-- PostgreSQL database dump complete
--

\unrestrict IcyNbedXGPcebLVx3zas8hiqFmJx5n6Gpf9CYgwEHYoCG9pXX7hD0nzcJEw9Ync

