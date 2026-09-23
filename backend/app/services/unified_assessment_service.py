"""Unified Assessment Service for all SIMRAS asset types.

This service provides a single entry point for health/risk/RUL assessment,
replacing scattered type-specific logic with evidence-based evaluation.

Key principles:
- Evidence-based assessment (no 100/0 defaults)
- Asset type-aware feature extraction
- Transparent assessment basis (ML_VALIDATED, ML_TRANSFER, EVIDENCE_DERIVED, NOT_AVAILABLE)
- Consistent thresholds across all asset types
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.services.risk_engine import RiskInput, score_risk
from app.core.assessment_thresholds import (
    REFERENCE_SERVICE_LIFE_YEARS,
    RISK_LEVEL_THRESHOLDS,
    get_risk_level,
)


# ============================================================
# ASSESSMENT RESULT CONTRACT
# ============================================================

@dataclass(slots=True)
class UnifiedAssessmentResult:
    """Single contract for all asset assessment results."""

    asset_code: str
    asset_type: str

    # Primary scores
    health_score: float | None
    risk_score: float | None
    risk_level: str | None
    remaining_useful_life: float | None

    # Assessment metadata
    health_basis: str  # ML_VALIDATED, ML_TRANSFER, EVIDENCE_DERIVED, NOT_AVAILABLE
    risk_basis: str
    rul_basis: str
    assessment_basis: str  # Overall basis (priority: ML_VALIDATED > ML_TRANSFER > EVIDENCE_DERIVED > NOT_AVAILABLE)
    confidence: float | None

    # Evidence tracking
    features_used: list[str]
    features_missing: list[str]
    factors: list[str]  # Human-readable explanation

    # Model information
    model_name: str | None
    model_version: str | None
    feature_version: str | None
    model_is_validated: bool

    # Limitations
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "asset_code": self.asset_code,
            "asset_type": self.asset_type,
            "health_score": self.health_score,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "remaining_useful_life": self.remaining_useful_life,
            "health_basis": self.health_basis,
            "risk_basis": self.risk_basis,
            "rul_basis": self.rul_basis,
            "assessment_basis": self.assessment_basis,
            "confidence": self.confidence,
            "features_used": self.features_used,
            "features_missing": self.features_missing,
            "factors": self.factors,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "feature_version": self.feature_version,
            "model_is_validated": self.model_is_validated,
            "limitations": self.limitations,
        }


# ============================================================
# EVIDENCE EXTRACTION
# ============================================================

def _extract_airport_features(asset: dict[str, Any], inspection_history: list[dict[str, Any]],
                               maintenance_history: list[dict[str, Any]], environment: dict[str, float]) -> dict[str, Any]:
    """Extract airport-specific features for assessment."""

    features = {}
    used = []
    missing = []

    # Identity features
    features["asset_code"] = asset.get("asset_code")
    features["name"] = asset.get("name")

    # Built year and age
    current_year = datetime.now(UTC).year
    built_year = asset.get("built_year")
    if built_year is not None:
        features["built_year"] = built_year
        features["age_years"] = max(0, current_year - built_year)
        used.append("built_year")
    else:
        missing.append("built_year")

    # Runway characteristics (from asset components if available)
    runway_data = asset.get("runway_data", {})
    if runway_data:
        features["runway_length_m"] = runway_data.get("length")
        features["runway_width_m"] = runway_data.get("width")
        features["runway_count"] = runway_data.get("count")
        if any(v is not None for v in [runway_data.get("length"), runway_data.get("width")]):
            used.append("runway_dimensions")
    else:
        missing.append("runway_dimensions")

    # Pavement condition (from latest inspection if available)
    latest_inspection = inspection_history[0] if inspection_history else None
    if latest_inspection:
        inspection_condition = latest_inspection.get("condition", "").upper()
        features["pavement_condition"] = inspection_condition
        if inspection_condition:
            used.append("pavement_condition")
        inspection_score = latest_inspection.get("score")
        if inspection_score is not None:
            features["inspection_score"] = inspection_score
            used.append("inspection_score")
    else:
        missing.append("pavement_condition")
        missing.append("inspection_score")

    # Maintenance history
    if maintenance_history:
        features["maintenance_records"] = len(maintenance_history)
        recent_maintenance = maintenance_history[0] if maintenance_history else None
        if recent_maintenance and recent_maintenance.get("date"):
            try:
                days_since = max(0, (datetime.now(UTC).date() - 
                                  datetime.fromisoformat(str(recent_maintenance["date"]).replace("Z", "+00:00")).date()).days)
                features["days_since_maintenance"] = days_since
                used.append("maintenance_recency")
            except ValueError:
                missing.append("maintenance_date_parse")
    else:
        missing.append("maintenance_history")

    # Environmental factors
    if environment.get("rainfall_24h"):
        features["rainfall_24h_mm"] = environment["rainfall_24h"]
        used.append("rainfall_24h")
    else:
        missing.append("rainfall_24h")

    if environment.get("rainfall_7d"):
        features["rainfall_7d_mm"] = environment["rainfall_7d"]
        used.append("rainfall_7d")
    else:
        missing.append("rainfall_7d")

    features["_used"] = used
    features["_missing"] = missing

    return features


def _extract_temple_features(asset: dict[str, Any], inspection_history: list[dict[str, Any]],
                              maintenance_history: list[dict[str, Any]], environment: dict[str, float]) -> dict[str, Any]:
    """Extract temple-specific features for assessment."""

    features = {}
    used = []
    missing = []

    # Identity features
    features["asset_code"] = asset.get("asset_code")
    features["name"] = asset.get("name")

    # Heritage age and construction
    current_year = datetime.now(UTC).year
    built_year = asset.get("built_year")
    if built_year is not None:
        features["built_year"] = built_year
        features["age_years"] = max(0, current_year - built_year)
        used.append("heritage_age")
    else:
        missing.append("heritage_age")

    # Structural dimensions (if verified)
    dimensions = asset.get("dimensions", {})
    if dimensions:
        features["height_m"] = dimensions.get("height")
        features["length_m"] = dimensions.get("length")
        features["width_m"] = dimensions.get("width")
        if any(v is not None for v in dimensions.values()):
            used.append("structural_dimensions")
    else:
        missing.append("structural_dimensions")

    # Condition (from inspection history)
    latest_inspection = inspection_history[0] if inspection_history else None
    if latest_inspection:
        inspection_condition = latest_inspection.get("condition", "").upper()
        features["structural_condition"] = inspection_condition
        if inspection_condition:
            used.append("structural_condition")
        inspection_score = latest_inspection.get("score")
        if inspection_score is not None:
            features["inspection_score"] = inspection_score
            used.append("inspection_score")
    else:
        missing.append("structural_condition")
        missing.append("inspection_score")

    # Restoration/maintenance history
    if maintenance_history:
        features["restoration_records"] = len(maintenance_history)
        recent_restoration = maintenance_history[0] if maintenance_history else None
        if recent_restoration and recent_restoration.get("date"):
            try:
                days_since = max(0, (datetime.now(UTC).date() - 
                                  datetime.fromisoformat(str(recent_restoration["date"]).replace("Z", "+00:00")).date()).days)
                features["days_since_restoration"] = days_since
                used.append("restoration_recency")
            except ValueError:
                missing.append("restoration_date_parse")
    else:
        missing.append("restoration_history")

    # Environmental factors (humidity, rainfall)
    if environment.get("humidity_percent"):
        features["humidity_percent"] = environment["humidity_percent"]
        used.append("humidity")
    else:
        missing.append("humidity")

    if environment.get("rainfall_24h"):
        features["rainfall_24h_mm"] = environment["rainfall_24h"]
        used.append("rainfall_24h")
    else:
        missing.append("rainfall_24h")

    features["_used"] = used
    features["_missing"] = missing

    return features


# ============================================================
# ASSESSMENT LOGIC
# ============================================================

def _assess_airport(features: dict[str, Any]) -> UnifiedAssessmentResult:
    """Assess airport using runway, pavement, and maintenance evidence."""

    asset_code = features.get("asset_code", "UNKNOWN")
    used = features.get("_used", [])
    missing = features.get("_missing", [])

    health_score = None
    risk_score = None
    rul_years = None
    factors = []

    # Evidence-based health assessment
    if len(used) >= 2:  # At least 2 evidence inputs required
        health_components = []

        # Age-based component
        age_years = features.get("age_years")
        design_life = features.get("design_life_years") or REFERENCE_SERVICE_LIFE_YEARS.get("airport", 50)
        if age_years is not None:
            age_ratio = min(1.0, max(0.0, age_years / design_life))
            age_health = 100 - (age_ratio * 40)  # Age penalty: 0-40 points
            health_components.append(age_health)
            if age_ratio > 0.75:
                factors.append(f"Age is {age_ratio:.0%} of reference design life ({design_life} years)")

        # Pavement condition component
        pavement_condition = features.get("pavement_condition", "").upper()
        condition_map = {
            "EXCELLENT": 95,
            "GOOD": 85,
            "FAIR": 65,
            "POOR": 40,
            "CRITICAL": 15,
        }
        condition_health = condition_map.get(pavement_condition)
        if condition_health is not None:
            health_components.append(condition_health)
            if pavement_condition in ("POOR", "CRITICAL"):
                factors.append(f"Pavement condition: {pavement_condition}")

        # Inspection score component
        inspection_score = features.get("inspection_score")
        if inspection_score is not None:
            health_components.append(inspection_score)
            if inspection_score < 50:
                factors.append("Latest inspection score below 50")

        # Maintenance recency
        days_since_maintenance = features.get("days_since_maintenance")
        if days_since_maintenance is not None:
            if days_since_maintenance > 1095:  # 3 years
                factors.append("No recent maintenance (>3 years)")
                health_components.append(max(30, 100 - (days_since_maintenance - 1095) / 365 * 5))
            else:
                health_components.append(min(100, 85 + (1095 - days_since_maintenance) / 1095 * 15))

        # Calculate average health
        if health_components:
            health_score = sum(health_components) / len(health_components)
            health_score = max(0.0, min(100.0, health_score))

        # Risk is inverse of health with environmental factors
        environmental_penalty = 0.0
        if features.get("rainfall_24h_mm", 0) > 100:
            environmental_penalty += 15
            factors.append("Heavy 24h rainfall exposure")
        if features.get("rainfall_7d_mm", 0) > 250:
            environmental_penalty += 10
            factors.append("Sustained high rainfall")

        risk_score = max(0.0, min(100.0, (100 - health_score) + environmental_penalty))

    # RUL calculation
    if features.get("age_years") is not None and (features.get("design_life_years") or REFERENCE_SERVICE_LIFE_YEARS.get("airport")):
        design_life = features.get("design_life_years") or REFERENCE_SERVICE_LIFE_YEARS.get("airport", 50)
        age_years = features.get("age_years", 0)
        remaining = max(0.0, design_life - age_years)
        if health_score is not None:
            # Adjust RUL by health condition
            health_factor = max(0.2, health_score / 100.0)
            rul_years = remaining * health_factor
        else:
            rul_years = remaining

    # Determine basis
    if len(used) >= 3:
        health_basis = "EVIDENCE_DERIVED"
        risk_basis = "EVIDENCE_DERIVED"
        rul_basis = "EVIDENCE_DERIVED" if rul_years is not None else "NOT_AVAILABLE"
    else:
        health_basis = "NOT_AVAILABLE"
        risk_basis = "NOT_AVAILABLE"
        rul_basis = "NOT_AVAILABLE"

    risk_level = None
    if risk_score is not None:
        risk_level = get_risk_level(risk_score)

    return UnifiedAssessmentResult(
        asset_code=asset_code,
        asset_type="AIRPORT",
        health_score=round(health_score, 1) if health_score is not None else None,
        risk_score=round(risk_score, 1) if risk_score is not None else None,
        risk_level=risk_level,
        remaining_useful_life=round(rul_years, 1) if rul_years is not None else None,
        health_basis=health_basis,
        risk_basis=risk_basis,
        rul_basis=rul_basis,
        assessment_basis=health_basis,  # Use health basis as overall
        confidence=80.0 if len(used) >= 3 else 50.0 if len(used) >= 2 else 0.0,
        features_used=used,
        features_missing=missing,
        factors=factors,
        model_name=None,
        model_version=None,
        feature_version="airport_evidence_v1",
        model_is_validated=False,
        limitations=[
            "Assessment based on available evidence, not ML validation",
            "Missing evidence reduces confidence and is listed in features_missing",
            "This is decision support only, not an engineering certificate",
        ],
    )


def _assess_temple(features: dict[str, Any]) -> UnifiedAssessmentResult:
    """Assess temple using heritage age, structure, and maintenance evidence."""

    asset_code = features.get("asset_code", "UNKNOWN")
    used = features.get("_used", [])
    missing = features.get("_missing", [])

    health_score = None
    risk_score = None
    rul_years = None
    factors = []

    # Evidence-based health assessment
    if len(used) >= 2:  # At least 2 evidence inputs required
        health_components = []

        # Heritage age component (temples don't deteriorate proportionally with age)
        age_years = features.get("age_years")
        if age_years is not None:
            # For heritage structures, age is less directly linked to deterioration
            # if properly maintained. Use a gentler curve.
            age_ratio = min(1.0, max(0.0, age_years / 200.0))  # 200-year reference
            age_health = 100 - (age_ratio * 25)  # Gentler penalty: 0-25 points
            health_components.append(age_health)
            if age_years > 100:
                factors.append(f"Heritage structure age: {age_years} years")

        # Structural condition component
        condition = features.get("structural_condition", "").upper()
        condition_map = {
            "EXCELLENT": 95,
            "GOOD": 85,
            "FAIR": 70,
            "POOR": 45,
            "CRITICAL": 20,
        }
        condition_health = condition_map.get(condition)
        if condition_health is not None:
            health_components.append(condition_health)
            if condition in ("POOR", "CRITICAL"):
                factors.append(f"Structural condition: {condition}")

        # Inspection evidence
        inspection_score = features.get("inspection_score")
        if inspection_score is not None:
            health_components.append(inspection_score)
            if inspection_score < 50:
                factors.append("Structural inspection score below 50")

        # Restoration/maintenance recency (crucial for heritage)
        days_since_restoration = features.get("days_since_restoration")
        if days_since_restoration is not None:
            if days_since_restoration > 2555:  # 7 years
                factors.append("No recent restoration (>7 years)")
                health_components.append(max(40, 100 - (days_since_restoration - 2555) / 365 * 3))
            else:
                health_components.append(min(100, 80 + (2555 - days_since_restoration) / 2555 * 20))

        # Calculate average health
        if health_components:
            health_score = sum(health_components) / len(health_components)
            health_score = max(0.0, min(100.0, health_score))

        # Risk is inverse of health with environmental factors
        environmental_penalty = 0.0
        if features.get("humidity_percent", 0) > 80:
            environmental_penalty += 12
            factors.append("High humidity exposure (structural risk)")
        if features.get("rainfall_24h_mm", 0) > 80:
            environmental_penalty += 10
            factors.append("High rainfall exposure")

        risk_score = max(0.0, min(100.0, (100 - health_score) + environmental_penalty))

    # RUL calculation (for heritage structures)
    if features.get("age_years") is not None:
        # Heritage structures with proper maintenance can exceed original design life
        design_life = 200  # Reference life for temple heritage
        age_years = features.get("age_years", 0)
        # Don't force RUL to zero even if age exceeds design life
        remaining = max(0.0, design_life - age_years)
        if health_score is not None and health_score > 50:
            # Well-maintained heritage can continue indefinitely
            rul_years = remaining if remaining > 0 else 50  # Assume another 50 years if well-maintained
        else:
            rul_years = remaining

    # Determine basis
    if len(used) >= 3:
        health_basis = "EVIDENCE_DERIVED"
        risk_basis = "EVIDENCE_DERIVED"
        rul_basis = "EVIDENCE_DERIVED" if rul_years is not None else "NOT_AVAILABLE"
    else:
        health_basis = "NOT_AVAILABLE"
        risk_basis = "NOT_AVAILABLE"
        rul_basis = "NOT_AVAILABLE"

    risk_level = None
    if risk_score is not None:
        risk_level = get_risk_level(risk_score)

    return UnifiedAssessmentResult(
        asset_code=asset_code,
        asset_type="TEMPLE",
        health_score=round(health_score, 1) if health_score is not None else None,
        risk_score=round(risk_score, 1) if risk_score is not None else None,
        risk_level=risk_level,
        remaining_useful_life=round(rul_years, 1) if rul_years is not None else None,
        health_basis=health_basis,
        risk_basis=risk_basis,
        rul_basis=rul_basis,
        assessment_basis=health_basis,  # Use health basis as overall
        confidence=80.0 if len(used) >= 3 else 50.0 if len(used) >= 2 else 0.0,
        features_used=used,
        features_missing=missing,
        factors=factors,
        model_name=None,
        model_version=None,
        feature_version="temple_evidence_v1",
        model_is_validated=False,
        limitations=[
            "Assessment based on available evidence, not ML validation",
            "Missing evidence reduces confidence and is listed in features_missing",
            "This is decision support only, not an engineering certificate",
            "Heritage structures may continue beyond original design life if well-maintained",
        ],
    )


def build_unified_assessment(
    asset_type: str,
    asset: dict[str, Any],
    inspection_history: list[dict[str, Any]] | None = None,
    maintenance_history: list[dict[str, Any]] | None = None,
    environment: dict[str, float] | None = None,
) -> UnifiedAssessmentResult:
    """Build a unified assessment for any asset type.

    Args:
        asset_type: Asset category (AIRPORT, TEMPLE, etc.)
        asset: Asset record with identity info
        inspection_history: Inspection records (most recent first)
        maintenance_history: Maintenance records (most recent first)
        environment: Environmental sensor readings (rainfall_24h, humidity, etc.)

    Returns:
        UnifiedAssessmentResult with health/risk/RUL and full metadata
    """

    asset_type = str(asset_type or "").upper()
    inspection_history = inspection_history or []
    maintenance_history = maintenance_history or []
    environment = environment or {}

    if asset_type == "AIRPORT":
        features = _extract_airport_features(asset, inspection_history, maintenance_history, environment)
        return _assess_airport(features)

    elif asset_type == "TEMPLE":
        features = _extract_temple_features(asset, inspection_history, maintenance_history, environment)
        return _assess_temple(features)

    else:
        # For other asset types, return NOT_AVAILABLE for now
        # (Bridge, Dam, etc. use their specialized assessments)
        return UnifiedAssessmentResult(
            asset_code=asset.get("asset_code", "UNKNOWN"),
            asset_type=asset_type,
            health_score=None,
            risk_score=None,
            risk_level=None,
            remaining_useful_life=None,
            health_basis="NOT_AVAILABLE",
            risk_basis="NOT_AVAILABLE",
            rul_basis="NOT_AVAILABLE",
            assessment_basis="NOT_AVAILABLE",
            confidence=0.0,
            features_used=[],
            features_missing=["asset_type_unsupported"],
            factors=[f"Assessment not available for {asset_type} (use specialized service)"],
            model_name=None,
            model_version=None,
            feature_version=None,
            model_is_validated=False,
            limitations=["This asset type requires specialized assessment service"],
        )
