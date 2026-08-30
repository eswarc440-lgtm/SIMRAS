from dataclasses import asdict, dataclass
from datetime import date


@dataclass(slots=True)
class RiskInput:
    asset_type: str | None = None
    built_year: int | None = None
    design_life_years: int | None = None
    condition: str | None = None
    inspection_score: float | None = None
    days_since_inspection: int | None = None
    days_since_maintenance: int | None = None
    rainfall_mm_24h: float | None = None
    rainfall_mm_7d: float | None = None
    water_level_anomaly_m: float | None = None
    flood_exposure: float | None = None
    traffic_load_ratio: float | None = None
    source_confidence: float | None = None


@dataclass(slots=True)
class RiskResult:
    health_score: float | None
    risk_score: float | None
    risk_level: str | None
    hazard_score: float | None
    hazard_level: str | None
    confidence: float | None
    remaining_life_years: None
    model_version: str
    feature_version: str
    status: str
    prediction_method: str
    model_validated: bool
    factors: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:
    return max(minimum, min(maximum, value))


def _condition_health(condition: str | None) -> float | None:
    mapping = {
        "EXCELLENT": 96.0,
        "HEALTHY": 92.0,
        "GOOD": 90.0,
        "SOUND": 90.0,
        "SATISFACTORY": 86.0,
        "NORMAL": 85.0,
        "MONITOR": 75.0,
        "FAIR": 70.0,
        "WEAK": 55.0,
        "POOR": 45.0,
        "HIGH_PRIORITY": 35.0,
        "HIGH PRIORITY": 35.0,
        "CRITICAL": 18.0,
        "UNSAFE": 12.0,
    }
    return mapping.get((condition or "").strip().upper())


def _typical_design_life(asset_type: str | None) -> int:
    asset_type = (asset_type or "").lower()
    if asset_type == "barrage":
        return 80
    if asset_type in {"bridge", "dam"}:
        return 100
    return 80


def _legacy_score(
    data: RiskInput,
    *,
    current_year: int,
) -> RiskResult:
    """Preserve the previous evidence-only contract for old tests/callers."""

    penalty = 0.0
    structural_hazard = 0.0
    environmental_hazard = 0.0
    hazard_inputs = 0
    factors: list[str] = []
    known = 0
    expected = 10

    if data.built_year and data.design_life_years and data.design_life_years > 0:
        known += 1
        age = max(0, current_year - data.built_year)
        ratio = age / data.design_life_years
        penalty += clamp(ratio * 24, 0, 30)
        if ratio >= 0.75:
            factors.append(f"Age is {ratio:.0%} of stated design life")

    condition_penalty = {
        "GOOD": 3,
        "FAIR": 13,
        "POOR": 28,
        "CRITICAL": 45,
    }
    if data.condition:
        known += 1
        normalized = data.condition.upper()
        penalty += condition_penalty.get(normalized, 12)
        if normalized in {"POOR", "CRITICAL"}:
            factors.append(f"Recorded condition is {normalized.lower()}")

    if data.inspection_score is not None:
        known += 1
        score = clamp(data.inspection_score)
        penalty += (100 - score) * 0.25
        if score < 60:
            factors.append("Latest inspection score is below 60")

    if data.days_since_inspection is not None:
        known += 1
        if data.days_since_inspection > 365:
            penalty += min(
                15,
                (data.days_since_inspection - 365) / 90 * 2,
            )
            factors.append("Inspection is more than one year old")

    if data.days_since_maintenance is not None:
        known += 1
        if data.days_since_maintenance > 730:
            penalty += min(
                10,
                (data.days_since_maintenance - 730) / 365 * 2,
            )
            factors.append("No recorded maintenance within two years")

    if data.rainfall_mm_24h is not None:
        known += 1
        hazard_inputs += 1
        rain = max(0.0, data.rainfall_mm_24h)
        structural_hazard += clamp((rain - 50) / 8, 0, 12)
        environmental_hazard += clamp(rain / 150 * 30, 0, 30)
        if rain >= 100:
            factors.append("Very heavy 24-hour rainfall exposure")

    if data.rainfall_mm_7d is not None:
        known += 1
        hazard_inputs += 1
        rain = max(0.0, data.rainfall_mm_7d)
        structural_hazard += clamp((rain - 150) / 25, 0, 8)
        environmental_hazard += clamp(rain / 400 * 20, 0, 20)
        if rain >= 250:
            factors.append("High cumulative seven-day rainfall")

    if data.water_level_anomaly_m is not None:
        known += 1
        hazard_inputs += 1
        anomaly = max(0.0, data.water_level_anomaly_m)
        structural_hazard += clamp(anomaly * 6, 0, 18)
        environmental_hazard += clamp(anomaly / 3 * 25, 0, 25)
        if anomaly >= 1.5:
            factors.append("Water level is materially above baseline")

    if data.flood_exposure is not None:
        known += 1
        hazard_inputs += 1
        exposure = max(0.0, min(1.0, data.flood_exposure))
        structural_hazard += exposure * 15
        environmental_hazard += exposure * 20
        if exposure >= 0.7:
            factors.append("High mapped flood exposure")

    if data.traffic_load_ratio is not None:
        known += 1
        hazard_inputs += 1
        ratio = max(0.0, data.traffic_load_ratio)
        structural_hazard += clamp((ratio - 0.7) * 20, 0, 10)
        environmental_hazard += clamp((ratio - 0.7) * 10, 0, 5)
        if ratio > 1:
            factors.append("Estimated traffic/load exceeds reference capacity")

    hazard_score = (
        round(clamp(environmental_hazard), 1)
        if hazard_inputs
        else None
    )
    if hazard_score is None:
        hazard_level = None
    elif hazard_score >= 70:
        hazard_level = "HIGH"
    elif hazard_score >= 40:
        hazard_level = "MEDIUM"
    else:
        hazard_level = "LOW"

    has_structural_evidence = (
        bool(data.condition)
        or data.inspection_score is not None
    )

    if has_structural_evidence:
        health = round(clamp(100 - penalty), 1)
        risk = round(
            clamp((100 - health) * 0.72 + structural_hazard),
            1,
        )
        risk_level = (
            "HIGH"
            if risk >= 70
            else "MEDIUM"
            if risk >= 40
            else "LOW"
        )
    else:
        health = None
        risk = None
        risk_level = None

    completeness = known / expected
    source_confidence = (
        0.5
        if data.source_confidence is None
        else data.source_confidence
    )
    confidence = (
        round(
            max(
                0.1,
                min(
                    1.0,
                    completeness * 0.7
                    + source_confidence * 0.3,
                ),
            ),
            2,
        )
        if has_structural_evidence
        else None
    )

    if not has_structural_evidence:
        factors.insert(
            0,
            "Health and structural risk require a condition assessment or inspection",
        )
        factors.append(
            "Environmental hazard does not prove structural condition"
        )
        factors.append(
            "Verified identity and location do not verify structural condition"
        )
    elif not factors:
        factors.append(
            "No major threshold exceedance in available features"
        )

    if hazard_score is not None:
        factors.append(
            f"Available environmental exposure gives a {hazard_level.lower()} hazard index"
        )

    if completeness < 0.6:
        factors.append(
            "Result confidence reduced by missing input data"
        )

    factors.append(
        "RUL disabled until longitudinal deterioration data are validated"
    )

    return RiskResult(
        health_score=health,
        risk_score=risk,
        risk_level=risk_level,
        hazard_score=hazard_score,
        hazard_level=hazard_level,
        confidence=confidence,
        remaining_life_years=None,
        model_version="transparent_rules_v2",
        feature_version="asset_state_v1",
        status=(
            "DECISION_SUPPORT"
            if has_structural_evidence
            else "INSUFFICIENT_DATA"
        ),
        prediction_method="transparent_engineering_rules",
        model_validated=False,
        factors=factors,
    )


def _universal_prediction(
    data: RiskInput,
    *,
    current_year: int,
) -> RiskResult:
    """Produce a 0-100 SIMRAS research prediction for registry-wide ranking.

    Missing structural evidence reduces confidence. The output is explicitly
    not an official condition rating and not a locally validated ML model.
    """

    factors: list[str] = []
    known = 0
    expected = 9

    health = 70.0
    used_neutral_prior = True

    if data.built_year is not None:
        known += 1
        age = max(0, current_year - int(data.built_year))

        if data.design_life_years and data.design_life_years > 0:
            design_life = float(data.design_life_years)
            known += 1
        else:
            design_life = float(_typical_design_life(data.asset_type))
            factors.append(
                "Official design life is unavailable; an asset-type planning prior is used"
            )

        ratio = age / design_life
        health = clamp(
            100.0 - ratio * 45.0,
            42.0,
            98.0,
        )
        used_neutral_prior = False
        factors.append(
            f"Asset age is approximately {age} years ({ratio:.0%} of the design-life basis)"
        )

    condition_health = _condition_health(data.condition)
    if condition_health is not None:
        known += 1
        health = (
            condition_health
            if used_neutral_prior
            else 0.45 * health + 0.55 * condition_health
        )
        used_neutral_prior = False
        factors.append(
            f"Recorded condition contributes to predicted health ({data.condition})"
        )

    if data.inspection_score is not None:
        known += 1
        inspection_health = clamp(float(data.inspection_score))
        health = (
            inspection_health
            if used_neutral_prior
            else 0.35 * health + 0.65 * inspection_health
        )
        used_neutral_prior = False
        factors.append(
            f"Latest inspection score contributes {inspection_health:.0f}/100"
        )

    if data.days_since_inspection is not None:
        known += 1
        if data.days_since_inspection > 365:
            health -= min(
                10.0,
                (data.days_since_inspection - 365) / 365.0 * 4.0,
            )
            factors.append(
                "Structural inspection is older than one year"
            )

    if data.days_since_maintenance is not None:
        known += 1
        if data.days_since_maintenance > 730:
            health -= min(
                7.0,
                (data.days_since_maintenance - 730) / 365.0 * 2.0,
            )
            factors.append(
                "No recent maintenance is recorded within the last two years"
            )

    environmental_hazard = 0.0
    hazard_inputs = 0

    if data.rainfall_mm_24h is not None:
        known += 1
        hazard_inputs += 1
        rainfall = max(0.0, float(data.rainfall_mm_24h))
        environmental_hazard += clamp(
            rainfall / 150.0 * 40.0,
            0.0,
            40.0,
        )
        if rainfall >= 100:
            factors.append(
                "Very heavy 24-hour rainfall increases environmental exposure"
            )

    if data.rainfall_mm_7d is not None:
        known += 1
        hazard_inputs += 1
        rainfall = max(0.0, float(data.rainfall_mm_7d))
        environmental_hazard += clamp(
            rainfall / 400.0 * 25.0,
            0.0,
            25.0,
        )
        if rainfall >= 250:
            factors.append(
                "High cumulative seven-day rainfall increases environmental exposure"
            )

    if data.water_level_anomaly_m is not None:
        known += 1
        hazard_inputs += 1
        anomaly = max(0.0, float(data.water_level_anomaly_m))
        environmental_hazard += clamp(
            anomaly / 3.0 * 20.0,
            0.0,
            20.0,
        )
        if anomaly >= 1.5:
            factors.append(
                "Water level is materially above the available baseline"
            )

    if data.flood_exposure is not None:
        known += 1
        hazard_inputs += 1
        exposure = max(
            0.0,
            min(1.0, float(data.flood_exposure)),
        )
        environmental_hazard += exposure * 25.0
        if exposure >= 0.7:
            factors.append("Mapped flood exposure is high")

    if data.traffic_load_ratio is not None:
        known += 1
        hazard_inputs += 1
        load_ratio = max(0.0, float(data.traffic_load_ratio))
        environmental_hazard += clamp(
            (load_ratio - 0.7) * 20.0,
            0.0,
            10.0,
        )
        if load_ratio > 1.0:
            factors.append(
                "Estimated load exceeds the available reference capacity"
            )

    hazard_score = (
        round(clamp(environmental_hazard), 1)
        if hazard_inputs
        else None
    )

    if hazard_score is None:
        hazard_level = None
    elif hazard_score >= 70:
        hazard_level = "HIGH"
    elif hazard_score >= 40:
        hazard_level = "MEDIUM"
    else:
        hazard_level = "LOW"

    if hazard_score is not None:
        health -= hazard_score * 0.10

    health = round(clamp(health, 10.0, 98.0), 1)

    hazard_component = (
        hazard_score
        if hazard_score is not None
        else 20.0
    )
    risk = clamp(
        (100.0 - health) * 0.72
        + hazard_component * 0.28
    )

    has_structural_evidence = (
        condition_health is not None
        or data.inspection_score is not None
    )

    if not has_structural_evidence:
        risk += 4.0
        factors.append(
            "No approved structural condition/inspection is available; prediction confidence is capped"
        )

    risk = round(clamp(risk), 1)

    risk_level = (
        "HIGH"
        if risk >= 70
        else "MEDIUM"
        if risk >= 40
        else "LOW"
    )

    completeness = min(1.0, known / expected)
    source_confidence = (
        0.50
        if data.source_confidence is None
        else max(
            0.0,
            min(1.0, float(data.source_confidence)),
        )
    )

    confidence = (
        0.22
        + completeness * 0.48
        + source_confidence * 0.20
        + (0.10 if has_structural_evidence else 0.0)
    )

    if not has_structural_evidence:
        confidence = min(confidence, 0.60)

    confidence = round(
        max(0.20, min(0.92, confidence)),
        2,
    )

    if used_neutral_prior:
        factors.insert(
            0,
            "Predicted health uses a neutral research prior because asset age/condition evidence is unavailable",
        )

    if hazard_score is not None:
        factors.append(
            f"Available government/environment data produces a {hazard_level.lower()} environmental hazard index"
        )
    else:
        factors.append(
            "No usable environmental hazard input is available for this asset"
        )

    if confidence < 0.60:
        factors.append(
            "Prediction confidence is reduced by missing local engineering evidence"
        )

    factors.append(
        "Health and risk are SIMRAS research predictions, not official engineering ratings"
    )
    factors.append(
        "RUL remains disabled until longitudinal Andhra Pradesh deterioration data are validated"
    )

    return RiskResult(
        health_score=health,
        risk_score=risk,
        risk_level=risk_level,
        hazard_score=hazard_score,
        hazard_level=hazard_level,
        confidence=confidence,
        remaining_life_years=None,
        model_version="simras_multifactor_health_v1",
        feature_version="ap_asset_state_v2",
        status=(
            "SIMRAS_PREDICTION"
            if confidence >= 0.60
            else "SIMRAS_PREDICTION_LOW_CONFIDENCE"
        ),
        prediction_method="transparent_multifactor_prediction",
        model_validated=False,
        factors=list(dict.fromkeys(factors)),
    )


def score_risk(
    data: RiskInput,
    *,
    current_year: int | None = None,
    allow_estimated_health: bool = False,
) -> RiskResult:
    """Score an asset.

    Default behaviour preserves the previous evidence-only contract.
    The Digital Twin calls with allow_estimated_health=True to obtain the
    clearly labelled SIMRAS 0-100 research prediction requested by the UI.
    """

    year = current_year or date.today().year

    if allow_estimated_health:
        return _universal_prediction(
            data,
            current_year=year,
        )

    return _legacy_score(
        data,
        current_year=year,
    )
