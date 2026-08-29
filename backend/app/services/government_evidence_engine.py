from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum


MODEL_VERSION = "ap_government_evidence_v1"
FEATURE_VERSION = "ap_official_evidence_v1"


class ConditionState(StrEnum):
    HEALTHY = "HEALTHY"
    MONITOR = "MONITOR"
    WEAK = "WEAK"
    HIGH_PRIORITY = "HIGH_PRIORITY"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class RiskBand(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class EvidenceStrength(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


class ResultOrigin(StrEnum):
    OBSERVED = "OBSERVED"
    DERIVED_FROM_OFFICIAL = "DERIVED_FROM_OFFICIAL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(slots=True)
class GovernmentEvidenceInput:
    asset_type: str

    # --------------------------------------------------------
    # Indian Railways bridge evidence
    # --------------------------------------------------------
    railway_crn: int | None = None

    # --------------------------------------------------------
    # Dam / barrage official evidence
    # --------------------------------------------------------
    dam_overall_condition: str | None = None
    dam_safety_category: str | None = None

    # --------------------------------------------------------
    # Generic official inspection
    # --------------------------------------------------------
    official_condition: str | None = None
    official_inspection_date: date | None = None

    # --------------------------------------------------------
    # Maintenance / rehabilitation
    # --------------------------------------------------------
    official_maintenance_recorded: bool = False
    official_rehabilitation_active: bool = False

    # --------------------------------------------------------
    # Hazard
    #
    # Important:
    # This should come from an official threshold/rating such as
    # CWC/AP-WRD warning level logic.
    #
    # We intentionally DO NOT convert rainfall directly into
    # structural health.
    # --------------------------------------------------------
    official_hazard_level: str | None = None

    # --------------------------------------------------------
    # Provenance
    # --------------------------------------------------------
    official_source_count: int = 0
    verified_inspection_count: int = 0
    synthetic_source_count: int = 0

    source_agencies: tuple[str, ...] = ()
    source_urls: tuple[str, ...] = ()


@dataclass(slots=True)
class GovernmentEvidenceResult:
    condition_state: str
    structural_risk_band: str
    hazard_band: str | None

    evidence_strength: str
    origin: str

    model_version: str
    feature_version: str

    # We intentionally do not invent these.
    health_score: None
    risk_score: None
    remaining_life_years: None

    forecast_ready: bool

    factors: list[str]
    source_agencies: list[str]
    source_urls: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# Helpers
# ============================================================


def _normalize_text(
    value: str | None,
) -> str | None:
    if not value:
        return None

    return (
        value.strip()
        .upper()
        .replace("-", "_")
        .replace(" ", "_")
    )


# ============================================================
# Indian Railways bridge condition
# ============================================================


def _railway_crn_state(
    crn: int | None,
) -> tuple[
    ConditionState,
    RiskBand,
    list[str],
]:
    if crn is None:
        return (
            ConditionState.UNKNOWN,
            RiskBand.UNKNOWN,
            [],
        )

    factors: list[str] = [
        (
            "Structural state derived from the "
            f"Indian Railways Condition Rating Number CRN={crn}"
        )
    ]

    if crn == 5:
        return (
            ConditionState.HEALTHY,
            RiskBand.LOW,
            factors,
        )

    if crn == 4:
        return (
            ConditionState.MONITOR,
            RiskBand.LOW,
            factors,
        )

    if crn == 3:
        return (
            ConditionState.WEAK,
            RiskBand.MEDIUM,
            factors,
        )

    if crn == 2:
        return (
            ConditionState.HIGH_PRIORITY,
            RiskBand.HIGH,
            factors,
        )

    if crn == 1:
        return (
            ConditionState.CRITICAL,
            RiskBand.CRITICAL,
            factors,
        )

    if crn == 0:
        factors.append(
            "Indian Railways CRN 0 means the component was not inspected"
        )

    elif crn == 6:
        factors.append(
            "Indian Railways CRN 6 means the component is not applicable"
        )

    else:
        factors.append(
            "CRN is outside the supported Indian Railways rating range"
        )

    return (
        ConditionState.UNKNOWN,
        RiskBand.UNKNOWN,
        factors,
    )


# ============================================================
# CWC / NDSA dam condition
# ============================================================


def _dam_condition_state(
    condition: str | None,
) -> tuple[
    ConditionState,
    RiskBand,
    list[str],
]:
    normalized = _normalize_text(
        condition
    )

    if normalized is None:
        return (
            ConditionState.UNKNOWN,
            RiskBand.UNKNOWN,
            [],
        )

    factors = [
        (
            "Dam state derived from the official "
            f"inspection condition '{condition}'"
        )
    ]

    if normalized in {
        "SATISFACTORY",
        "GOOD",
        "SOUND",
    }:
        return (
            ConditionState.HEALTHY,
            RiskBand.LOW,
            factors,
        )

    if normalized in {
        "FAIR",
    }:
        return (
            ConditionState.MONITOR,
            RiskBand.MEDIUM,
            factors,
        )

    if normalized in {
        "POOR",
    }:
        return (
            ConditionState.WEAK,
            RiskBand.HIGH,
            factors,
        )

    if normalized in {
        "UNSATISFACTORY",
        "CRITICAL",
    }:
        return (
            ConditionState.CRITICAL,
            RiskBand.CRITICAL,
            factors,
        )

    factors.append(
        "Official dam condition text is present but not mapped"
    )

    return (
        ConditionState.UNKNOWN,
        RiskBand.UNKNOWN,
        factors,
    )


# ============================================================
# NDSA safety category
# ============================================================


def _dam_safety_category(
    category: str | None,
) -> tuple[
    RiskBand,
    list[str],
]:
    normalized = _normalize_text(
        category
    )

    if normalized is None:
        return (
            RiskBand.UNKNOWN,
            [],
        )

    normalized = (
        normalized
        .replace("CATEGORY_", "")
        .replace("CAT_", "")
    )

    factors = [
        (
            "Structural risk incorporates the "
            f"official dam safety category {category}"
        )
    ]

    if normalized in {
        "I",
        "1",
    }:
        return (
            RiskBand.CRITICAL,
            factors,
        )

    if normalized in {
        "II",
        "2",
    }:
        return (
            RiskBand.HIGH,
            factors,
        )

    if normalized in {
        "III",
        "3",
    }:
        return (
            RiskBand.LOW,
            factors,
        )

    factors.append(
        "Official dam safety category could not be normalized"
    )

    return (
        RiskBand.UNKNOWN,
        factors,
    )


# ============================================================
# Generic government inspection
# ============================================================


def _generic_condition_state(
    condition: str | None,
) -> tuple[
    ConditionState,
    RiskBand,
    list[str],
]:
    normalized = _normalize_text(
        condition
    )

    if normalized is None:
        return (
            ConditionState.UNKNOWN,
            RiskBand.UNKNOWN,
            [],
        )

    factors = [
        (
            "State derived from an official "
            f"inspection condition '{condition}'"
        )
    ]

    if normalized in {
        "GOOD",
        "VERY_GOOD",
        "EXCELLENT",
        "SATISFACTORY",
        "SOUND",
    }:
        return (
            ConditionState.HEALTHY,
            RiskBand.LOW,
            factors,
        )

    if normalized in {
        "FAIR",
        "AVERAGE",
        "ROUTINE_MAINTENANCE",
    }:
        return (
            ConditionState.MONITOR,
            RiskBand.MEDIUM,
            factors,
        )

    if normalized in {
        "POOR",
        "UNSATISFACTORY",
        "WEAK",
        "MAJOR_REPAIR_REQUIRED",
    }:
        return (
            ConditionState.WEAK,
            RiskBand.HIGH,
            factors,
        )

    if normalized in {
        "CRITICAL",
        "UNSAFE",
        "IMMEDIATE_REHABILITATION",
    }:
        return (
            ConditionState.CRITICAL,
            RiskBand.CRITICAL,
            factors,
        )

    return (
        ConditionState.UNKNOWN,
        RiskBand.UNKNOWN,
        factors,
    )


# ============================================================
# Risk ordering
# ============================================================


_RISK_ORDER = {
    RiskBand.UNKNOWN: 0,
    RiskBand.LOW: 1,
    RiskBand.MEDIUM: 2,
    RiskBand.HIGH: 3,
    RiskBand.CRITICAL: 4,
}


def _worst_risk(
    first: RiskBand,
    second: RiskBand,
) -> RiskBand:
    if _RISK_ORDER[second] > _RISK_ORDER[first]:
        return second

    return first


# ============================================================
# Evidence strength
# ============================================================


def _evidence_strength(
    data: GovernmentEvidenceInput,
) -> EvidenceStrength:
    if data.synthetic_source_count > 0:
        # Synthetic data may remain visible in the system,
        # but it cannot increase government evidence strength.
        pass

    if (
        data.verified_inspection_count >= 1
        and data.official_source_count >= 1
    ):
        return EvidenceStrength.HIGH

    if data.official_source_count >= 1:
        return EvidenceStrength.MEDIUM

    return EvidenceStrength.INSUFFICIENT


# ============================================================
# Forecast eligibility
# ============================================================


def _forecast_ready(
    data: GovernmentEvidenceInput,
) -> bool:
    """
    Future deterioration forecasting requires longitudinal
    official observations.

    This is an internal SIMRAS evidence gate, not a government
    standard.

    A future ML pipeline can tighten this requirement further.
    """

    return (
        data.verified_inspection_count >= 3
        and data.synthetic_source_count == 0
    )


# ============================================================
# Main state engine
# ============================================================


def evaluate_government_evidence(
    data: GovernmentEvidenceInput,
) -> GovernmentEvidenceResult:
    asset_type = (
        data.asset_type
        .strip()
        .lower()
    )

    factors: list[str] = []

    condition_state = (
        ConditionState.UNKNOWN
    )

    structural_risk = (
        RiskBand.UNKNOWN
    )

    # --------------------------------------------------------
    # Railway bridge
    # --------------------------------------------------------

    if (
        asset_type == "bridge"
        and data.railway_crn is not None
    ):
        (
            condition_state,
            structural_risk,
            bridge_factors,
        ) = _railway_crn_state(
            data.railway_crn
        )

        factors.extend(
            bridge_factors
        )

    # --------------------------------------------------------
    # Dam / barrage
    # --------------------------------------------------------

    elif asset_type in {
        "dam",
        "barrage",
    }:
        (
            condition_state,
            structural_risk,
            dam_factors,
        ) = _dam_condition_state(
            data.dam_overall_condition
            or data.official_condition
        )

        factors.extend(
            dam_factors
        )

        (
            category_risk,
            category_factors,
        ) = _dam_safety_category(
            data.dam_safety_category
        )

        structural_risk = (
            _worst_risk(
                structural_risk,
                category_risk,
            )
        )

        factors.extend(
            category_factors
        )

    # --------------------------------------------------------
    # Other asset categories
    # --------------------------------------------------------

    else:
        (
            condition_state,
            structural_risk,
            generic_factors,
        ) = _generic_condition_state(
            data.official_condition
        )

        factors.extend(
            generic_factors
        )

    # --------------------------------------------------------
    # Maintenance evidence
    #
    # Maintenance is disclosed but does NOT automatically
    # convert a weak asset into a healthy asset.
    # --------------------------------------------------------

    if (
        data.official_maintenance_recorded
    ):
        factors.append(
            "Official maintenance evidence is recorded for the asset"
        )

    if (
        data.official_rehabilitation_active
    ):
        factors.append(
            "Official rehabilitation activity is recorded; condition should be reassessed after completion"
        )

    # --------------------------------------------------------
    # Hazard
    # --------------------------------------------------------

    hazard_band: str | None = None

    if data.official_hazard_level:
        hazard = _normalize_text(
            data.official_hazard_level
        )

        if hazard in {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }:
            hazard_band = hazard

            factors.append(
                (
                    "Environmental/hydraulic hazard "
                    "comes from an official or officially-derived threshold"
                )
            )

    # --------------------------------------------------------
    # Evidence strength
    # --------------------------------------------------------

    strength = _evidence_strength(
        data
    )

    forecast_ready = _forecast_ready(
        data
    )

    if (
        condition_state
        == ConditionState.UNKNOWN
    ):
        origin = (
            ResultOrigin.INSUFFICIENT_EVIDENCE
        )

        factors.insert(
            0,
            (
                "No supported government structural "
                "condition rating has been matched to this asset"
            ),
        )

    else:
        origin = (
            ResultOrigin.DERIVED_FROM_OFFICIAL
        )

    if (
        data.synthetic_source_count > 0
    ):
        factors.append(
            (
                "Synthetic/demo records are excluded "
                "from authoritative structural-state determination"
            ),
        )

    if not forecast_ready:
        factors.append(
            (
                "Future deterioration prediction is disabled "
                "until sufficient longitudinal official inspections exist"
            ),
        )

    factors.append(
        (
            "No FHWA/NBI or other foreign deterioration "
            "model contributes to this operational result"
        ),
    )

    return GovernmentEvidenceResult(
        condition_state=(
            condition_state.value
        ),

        structural_risk_band=(
            structural_risk.value
        ),

        hazard_band=hazard_band,

        evidence_strength=(
            strength.value
        ),

        origin=origin.value,

        model_version=MODEL_VERSION,

        feature_version=FEATURE_VERSION,

        health_score=None,

        risk_score=None,

        remaining_life_years=None,

        forecast_ready=forecast_ready,

        factors=list(
            dict.fromkeys(
                factors
            )
        ),

        source_agencies=list(
            dict.fromkeys(
                data.source_agencies
            )
        ),

        source_urls=list(
            dict.fromkeys(
                data.source_urls
            )
        ),
    )
