NUMERIC_FEATURES = [
    "age_years",
    "design_life_years",
    "age_design_life_ratio",
    "inspection_score",
    "defect_count",
    "max_defect_severity",
    "days_since_inspection",
    "days_since_maintenance",
    "rainfall_24h",
    "rainfall_7d",
    "rainfall_30d",
    "water_level",
    "water_level_anomaly",
    "flood_exposure",
    "elevation_m",
    "slope_deg",
    "traffic_load_ratio",
    "source_confidence",
    "missing_feature_ratio",
]

CATEGORICAL_FEATURES = [
    "asset_type",
    "subtype",
    "material",
    "condition",
    "district",
    "season",
]

IDENTITY_COLUMNS = ["asset_code", "state_time"]
HEALTH_TARGET = "target_health_score"
RISK_TARGET = "target_risk_class"


def required_columns(task: str) -> set[str]:
    target = HEALTH_TARGET if task == "health" else RISK_TARGET
    return set(IDENTITY_COLUMNS + NUMERIC_FEATURES + CATEGORICAL_FEATURES + [target])

