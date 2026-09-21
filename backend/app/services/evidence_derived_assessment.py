"""
Evidence-Derived Assessment Service

Provides deterministic decision-support values when ML models are not validated.
This is NOT ML prediction - it is transparent rule-based assessment using
available engineering evidence.

Priority:
1. ML_VALIDATED - Use validated ML when available
2. ML_TRANSFER - Use RESEARCH_TRANSFER ML when explicitly allowed
3. EVIDENCE_DERIVED - Use transparent rule engine on available evidence
4. ESTIMATED_PROXY - Use deterministic proxy from real evidence only

NO RANDOM VALUES, NO HARDCODED ASSET SCORES, NO FABRICATED INSPECTIONS.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _num(value: Any) -> float | None:
    """Safe numeric conversion."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _text(value: Any) -> str | None:
    """Safe text conversion."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _current_year() -> int:
    """Get current year."""
    return datetime.now(UTC).year


def _age_score(built_year: int | None, design_life_years: int | None) -> tuple[float | None, str]:
    """
    Calculate age-based health score.
    
    Returns:
        (health_score, basis)
    
    Logic:
    - If built_year and design_life_years are available:
      - Age ratio = age / design_life
      - Health starts at 100 and declines with age
      - New assets: 80-100
      - Mid-life: 60-80
      - Near end of design life: 40-60
      - Past design life: 0-40
    - If only built_year available: use default 100-year design life
    - If neither available: return None
    """
    current = _current_year()
    
    if built_year is None:
        return None, "BUILT_YEAR_UNAVAILABLE"
    
    age = current - built_year
    if age < 0:
        age = 0
    
    design_life = _num(design_life_years) or 100.0
    
    if design_life <= 0:
        design_life = 100.0
    
    age_ratio = age / design_life
    
    # Health declines with age but never goes below 20 without evidence
    if age_ratio <= 0.2:
        health = 85.0
    elif age_ratio <= 0.4:
        health = 75.0
    elif age_ratio <= 0.6:
        health = 65.0
    elif age_ratio <= 0.8:
        health = 55.0
    elif age_ratio <= 1.0:
        health = 45.0
    else:
        health = 35.0
    
    basis = f"EVIDENCE_DERIVED_AGE: age={age} years, design_life={design_life} years, ratio={age_ratio:.2f}"
    
    return health, basis


def _material_health_adjustment(material: str | None, base_health: float) -> tuple[float, str]:
    """
    Adjust health score based on material characteristics.
    
    Steel/concrete bridges typically have better durability than
    unreinforced masonry or timber.
    """
    if material is None:
        return base_health, "MATERIAL_UNAVAILABLE"
    
    material_lower = _text(material).lower()
    
    # Steel and concrete generally have good durability
    if any(m in material_lower for m in ["steel", "concrete", "rc", "prestressed"]):
        adjustment = 5.0
        adjusted = min(100.0, base_health + adjustment)
        basis = f"EVIDENCE_DERIVED_MATERIAL: {material} has good durability characteristics"
        return adjusted, basis
    
    # Masonry and timber may degrade faster
    if any(m in material_lower for m in ["masonry", "stone", "brick", "timber", "wood"]):
        adjustment = -5.0
        adjusted = max(20.0, base_health + adjustment)
        basis = f"EVIDENCE_DERIVED_MATERIAL: {material} may require more frequent inspection"
        return adjusted, basis
    
    # Unknown material - no adjustment
    return base_health, f"MATERIAL_UNKNOWN: {material}"


def _risk_from_health(health_score: float | None) -> tuple[float | None, str]:
    """
    Derive risk score from health score.
    
    Logic:
    - Health 80-100 -> Risk 0-20
    - Health 60-79.99 -> Risk 20-40
    - Health 40-59.99 -> Risk 40-60
    - Health 0-39.99 -> Risk 60-100
    
    This is INVERSE relationship - lower health = higher risk.
    """
    if health_score is None:
        return None, "HEALTH_UNAVAILABLE"
    
    if health_score >= 80:
        risk = 15.0
    elif health_score >= 60:
        risk = 30.0
    elif health_score >= 40:
        risk = 50.0
    else:
        risk = 75.0
    
    basis = f"EVIDENCE_DERIVED_RISK: inverse of health_score={health_score:.1f}"
    
    return risk, basis


def _risk_level_from_score(risk_score: float | None) -> str:
    """
    Convert risk score to risk level.
    
    < 40: LOW
    40-69.99: MEDIUM
    >= 70: HIGH
    """
    if risk_score is None:
        return "NOT_AVAILABLE"
    
    if risk_score >= 70:
        return "HIGH"
    if risk_score >= 40:
        return "MEDIUM"
    return "LOW"


def _rul_from_age(
    built_year: int | None,
    design_life_years: int | None,
    health_score: float | None
) -> tuple[float | None, str]:
    """
    Derive RUL from age and design life.
    
    Logic:
    - RUL = remaining design life adjusted by health
    - If health is high, assume full remaining design life
    - If health is low, reduce RUL proportionally
    - Never return negative RUL
    """
    current = _current_year()
    
    if built_year is None:
        return None, "BUILT_YEAR_UNAVAILABLE"
    
    age = current - built_year
    if age < 0:
        age = 0
    
    design_life = _num(design_life_years) or 100.0
    
    if design_life <= 0:
        design_life = 100.0
    
    remaining_design_life = max(0.0, design_life - age)
    
    if health_score is None:
        # No health adjustment - use raw remaining design life
        rul = remaining_design_life
        basis = f"EVIDENCE_DERIVED_RUL: remaining_design_life={rul:.1f} years (no health adjustment)"
        return rul, basis
    
    # Adjust RUL based on health
    # Health 100 -> 100% of remaining design life
    # Health 50 -> 50% of remaining design life
    # Health 20 -> 20% of remaining design life
    health_factor = max(0.2, health_score / 100.0)
    rul = remaining_design_life * health_factor
    
    basis = (
        f"EVIDENCE_DERIVED_RUL: remaining_design_life={remaining_design_life:.1f} years, "
        f"health_factor={health_factor:.2f}, adjusted_rul={rul:.1f} years"
    )
    
    return rul, basis


def assess_bridge_from_evidence(asset: dict[str, Any]) -> dict[str, Any]:
    """
    Generate evidence-derived assessment for a bridge.
    
    This is NOT ML prediction. It is transparent rule-based assessment
    using available engineering evidence.
    
    Args:
        asset: Asset dictionary with fields like built_year, material, design_life_years
    
    Returns:
        Assessment dictionary with health_score, risk_score, risk_level, rul_years,
        and explicit basis/metadata for each value.
    """
    built_year = _num(asset.get("built_year"))
    design_life_years = _num(asset.get("design_life_years"))
    material = _text(asset.get("material"))
    
    # Step 1: Calculate health from age
    health_score, health_basis = _age_score(built_year, design_life_years)
    
    # Step 2: Adjust health based on material
    if health_score is not None:
        health_score, material_basis = _material_health_adjustment(material, health_score)
        health_basis = f"{health_basis}; {material_basis}"
    
    # Step 3: Derive risk from health
    risk_score, risk_basis = _risk_from_health(health_score)
    
    # Step 4: Calculate risk level
    risk_level = _risk_level_from_score(risk_score)
    
    # Step 5: Derive RUL from age and health
    rul_years, rul_basis = _rul_from_age(built_year, design_life_years, health_score)
    
    # Compile assessment
    assessment = {
        "health_score": health_score,
        "health_status": _health_status(health_score),
        "health_basis": health_basis,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_basis": risk_basis,
        "rul_years": rul_years,
        "rul_basis": rul_basis,
        "assessment_method": "EVIDENCE_DERIVED",
        "assessment_basis": "Transparent rule-based assessment using available engineering evidence",
        "features_used": [],
        "features_missing": [],
        "limitations": [
            "No structural inspection condition rating available",
            "No traffic/load evidence available",
            "No maintenance history available",
            "No geometry dimensions available",
            "Assessment based only on age, material, and design life",
            "This is NOT ML prediction - it is a planning proxy",
        ],
    }
    
    # Track features used
    if built_year is not None:
        assessment["features_used"].append("built_year")
    else:
        assessment["features_missing"].append("built_year")
    
    if design_life_years is not None:
        assessment["features_used"].append("design_life_years")
    else:
        assessment["features_missing"].append("design_life_years")
    
    if material is not None:
        assessment["features_used"].append("material")
    else:
        assessment["features_missing"].append("material")
    
    # Always missing structural evidence
    assessment["features_missing"].extend([
        "structural_inspection_condition",
        "traffic_load",
        "maintenance_history",
        "geometry_dimensions",
        "scour_waterway_evidence",
    ])
    
    return assessment


def _health_status(score: float | None) -> str:
    """Convert health score to status category."""
    if score is None:
        return "NOT_AVAILABLE"
    if score >= 80:
        return "GOOD"
    if score >= 60:
        return "FAIR"
    if score >= 40:
        return "DEGRADED"
    return "POOR"
