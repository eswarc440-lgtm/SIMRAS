from dataclasses import asdict, dataclass
from datetime import date


@dataclass(slots=True)
class RiskInput:
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
    confidence: float | None
    remaining_life_years: None
    model_version: str
    feature_version: str
    status: str
    factors: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def score_risk(data: RiskInput, *, current_year: int | None = None) -> RiskResult:
    """Return a transparent decision-support baseline.

    This is deliberately not called a trained AI model. It ensures the complete
    application works while labelled inspection history is collected.
    """

    year = current_year or date.today().year
    penalty = 0.0
    hazard = 0.0
    factors: list[str] = []
    known = 0
    expected = 10

    if data.built_year and data.design_life_years and data.design_life_years > 0:
        known += 1
        age = max(0, year - data.built_year)
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
            penalty += min(15, (data.days_since_inspection - 365) / 90 * 2)
            factors.append("Inspection is more than one year old")

    if data.days_since_maintenance is not None:
        known += 1
        if data.days_since_maintenance > 730:
            penalty += min(10, (data.days_since_maintenance - 730) / 365 * 2)
            factors.append("No recorded maintenance within two years")

    if data.rainfall_mm_24h is not None:
        known += 1
        rain_penalty = clamp((data.rainfall_mm_24h - 50) / 8, 0, 12)
        hazard += rain_penalty
        if data.rainfall_mm_24h >= 100:
            factors.append("Very heavy 24-hour rainfall exposure")

    if data.rainfall_mm_7d is not None:
        known += 1
        hazard += clamp((data.rainfall_mm_7d - 150) / 25, 0, 8)
        if data.rainfall_mm_7d >= 250:
            factors.append("High cumulative seven-day rainfall")

    if data.water_level_anomaly_m is not None:
        known += 1
        hazard += clamp(data.water_level_anomaly_m * 6, 0, 18)
        if data.water_level_anomaly_m >= 1.5:
            factors.append("Water level is materially above baseline")

    if data.flood_exposure is not None:
        known += 1
        exposure = max(0, min(1, data.flood_exposure))
        hazard += exposure * 15
        if exposure >= 0.7:
            factors.append("High mapped flood exposure")

    if data.traffic_load_ratio is not None:
        known += 1
        ratio = max(0, data.traffic_load_ratio)
        hazard += clamp((ratio - 0.7) * 20, 0, 10)
        if ratio > 1:
            factors.append("Estimated traffic/load exceeds reference capacity")

    # Age, identity and location do not establish structural condition. A
    # health/risk score is only defensible once a condition assessment or an
    # inspection score exists. This prevents missing data from appearing as
    # perfect health (100) and zero risk.
    has_structural_evidence = bool(data.condition) or data.inspection_score is not None
    if has_structural_evidence:
        health = round(clamp(100 - penalty), 1)
        risk = round(clamp((100 - health) * 0.72 + hazard), 1)
        risk_level = "HIGH" if risk >= 70 else "MEDIUM" if risk >= 40 else "LOW"
    else:
        health = None
        risk = None
        risk_level = None

    completeness = known / expected
    source_confidence = 0.5 if data.source_confidence is None else data.source_confidence
    confidence = (
        round(max(0.1, min(1.0, completeness * 0.7 + source_confidence * 0.3)), 2)
        if has_structural_evidence
        else None
    )

    if not has_structural_evidence:
        factors.insert(0, "Health and risk unavailable until a condition assessment or inspection is recorded")
        factors.append("Verified identity and location do not verify structural condition")
    elif not factors:
        factors.append("No major threshold exceedance in available features")
    if completeness < 0.6:
        factors.append("Result confidence reduced by missing input data")
    factors.append("RUL disabled until longitudinal deterioration data are validated")

    return RiskResult(
        health_score=health,
        risk_score=risk,
        risk_level=risk_level,
        confidence=confidence,
        remaining_life_years=None,
        model_version="transparent_rules_v2",
        feature_version="asset_state_v1",
        status="DECISION_SUPPORT" if has_structural_evidence else "INSUFFICIENT_DATA",
        factors=factors,
    )
