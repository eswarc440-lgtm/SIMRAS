from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.risk_engine import RiskInput, score_risk


# ============================================================
# SIMRAS Evidence-State Service
#
# Rules:
# 1. Structural condition comes only from A1/A2 evidence.
# 2. Synthetic/demo environmental values are excluded.
# 3. NWDP government telemetry contributes to hazard only.
# 4. Raw water level is NOT classified as dangerous unless an
#    official warning/danger/reference threshold is available.
# 5. Health score and RUL remain unavailable until validated.
# ============================================================


RISK_ORDER = {
    "UNKNOWN": -1,
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}


TRUSTED_ENVIRONMENT_SOURCE_CODES = {
    "NWDP_AP_SW",
}


TRUSTED_ENVIRONMENT_SOURCE_TYPES = {
    "GOVERNMENT_TELEMETRY",
}


TRUSTED_ENVIRONMENT_QUALITY_FLAGS = {
    "OFFICIAL_DIRECT",
    "OFFICIAL_SPATIAL_TRANSFER",
    "OFFICIAL_DERIVED_SPATIAL",
    "OFFICIAL_SOURCE",
}


# ============================================================
# Normalization helpers
# ============================================================


def _norm(
    value: str | None,
) -> str:

    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .upper()
        .replace("_", " ")
        .split()
    )


# ============================================================
# Structural condition mapping
# ============================================================


def _condition_from_crn(
    value: Any,
) -> tuple[str, str]:

    try:
        crn = int(
            float(value)
        )

    except (
        TypeError,
        ValueError,
    ):
        return (
            "UNKNOWN",
            "UNKNOWN",
        )

    # Indian Railways Bridge Manual CRN interpretation.
    mapping = {
        5: (
            "HEALTHY",
            "LOW",
        ),
        4: (
            "MONITOR",
            "LOW",
        ),
        3: (
            "WEAK",
            "MEDIUM",
        ),
        2: (
            "HIGH_PRIORITY",
            "HIGH",
        ),
        1: (
            "CRITICAL",
            "CRITICAL",
        ),
        0: (
            "UNKNOWN",
            "UNKNOWN",
        ),
        6: (
            "UNKNOWN",
            "UNKNOWN",
        ),
    }

    return mapping.get(
        crn,
        (
            "UNKNOWN",
            "UNKNOWN",
        ),
    )


def _condition_from_dam_category(
    value: str | None,
) -> tuple[str, str]:

    category = _norm(
        value
    )

    if category in {
        "I",
        "CATEGORY I",
        "CATEGORY 1",
        "1",
    }:
        return (
            "CRITICAL",
            "CRITICAL",
        )

    if category in {
        "II",
        "CATEGORY II",
        "CATEGORY 2",
        "2",
    }:
        return (
            "HIGH_PRIORITY",
            "HIGH",
        )

    if category in {
        "III",
        "CATEGORY III",
        "CATEGORY 3",
        "3",
    }:
        return (
            "HEALTHY",
            "LOW",
        )

    return (
        "UNKNOWN",
        "UNKNOWN",
    )


def _condition_from_text(
    value: str | None,
) -> tuple[str, str]:

    condition = _norm(
        value
    )

    healthy = {
        "GOOD",
        "SATISFACTORY",
        "SOUND",
        "SAFE",
        "HEALTHY",
        "NORMAL",
    }

    monitor = {
        "FAIR",
        "MONITOR",
        "NEEDS MONITORING",
        "MINOR DEFICIENCY",
        "MINOR DEFICIENCIES",
    }

    weak = {
        "POOR",
        "WEAK",
        "MAJOR REPAIR",
        "MAJOR REPAIRS",
        "SPECIAL REPAIR",
        "SPECIAL REPAIRS",
    }

    high = {
        "HIGH PRIORITY",
        "REHABILITATION REQUIRED",
        "REQUIRES REHABILITATION",
        "PROGRAMMED REHABILITATION",
    }

    critical = {
        "CRITICAL",
        "UNSAFE",
        "IMMEDIATE REHABILITATION",
        "IMMEDIATE REBUILDING",
        "REBUILD IMMEDIATELY",
    }

    if condition in healthy:
        return (
            "HEALTHY",
            "LOW",
        )

    if condition in monitor:
        return (
            "MONITOR",
            "LOW",
        )

    if condition in weak:
        return (
            "WEAK",
            "MEDIUM",
        )

    if condition in high:
        return (
            "HIGH_PRIORITY",
            "HIGH",
        )

    if condition in critical:
        return (
            "CRITICAL",
            "CRITICAL",
        )

    return (
        "UNKNOWN",
        "UNKNOWN",
    )


# ============================================================
# Risk helpers
# ============================================================


def _worse_risk(
    first: str,
    second: str,
) -> str:

    return max(
        (
            first,
            second,
        ),
        key=lambda value: (
            RISK_ORDER.get(
                value,
                -1,
            )
        ),
    )


# ============================================================
# Observation freshness
# ============================================================


def _freshness(
    observed_at: datetime | None,
) -> str:

    if observed_at is None:
        return "NOT_AVAILABLE"

    if observed_at.tzinfo is None:
        observed_at = (
            observed_at.replace(
                tzinfo=UTC,
            )
        )

    hours = max(
        0.0,
        (
            datetime.now(
                UTC
            )
            - observed_at
        ).total_seconds()
        / 3600.0,
    )

    if hours <= 24:
        return "CURRENT"

    if hours <= (
        24 * 7
    ):
        return (
            f"{int(hours // 24)}"
            "_DAYS_OLD"
        )

    return (
        f"{int(hours // (24 * 7))}"
        "_WEEKS_OLD"
    )


# ============================================================
# Asset loader
# ============================================================


async def _asset(
    session: AsyncSession,
    asset_code: str,
) -> dict[str, Any]:

    result = await session.execute(
        text(
            """
            SELECT
                id,
                asset_code,
                name,
                asset_type,
                subtype,
                district,
                owner,
                built_year,
                design_life_years,
                material,
                identity_status,
                confidence_score,
                is_estimated,
                ST_Y(
                    representative_geometry
                ) AS latitude,
                ST_X(
                    representative_geometry
                ) AS longitude
            FROM assets
            WHERE asset_code =
                  CAST(
                      :asset_code
                      AS VARCHAR
                  )
            LIMIT 1
            """
        ),
        {
            "asset_code": (
                asset_code
            ),
        },
    )

    row = (
        result
        .mappings()
        .first()
    )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Asset "
                f"{asset_code} "
                "was not found"
            ),
        )

    return dict(
        row
    )


# ============================================================
# Trusted government environmental observations
# ============================================================


async def _latest_environment(
    session: AsyncSession,
    asset_id: int,
) -> dict[
    str,
    dict[str, Any],
]:

    # IMPORTANT:
    #
    # We deliberately select ONLY NWDP government telemetry.
    #
    # This prevents:
    # - SIMRAS demonstration seed
    # - synthetic environment data
    # - unverified environmental values
    #
    # from overriding genuine NWDP observations simply because
    # they have a newer timestamp.

    result = await session.execute(
        text(
            """
            SELECT DISTINCT ON (
                eo.variable
            )
                eo.variable,
                eo.value,
                eo.unit,
                eo.observed_at,
                eo.ingested_at,
                eo.source_type,
                eo.spatial_method,
                eo.quality_flag,
                eo.confidence_score,
                eo.is_estimated,

                ds.code
                    AS source_code,

                ds.name
                    AS source_name

            FROM environment_observations eo

            JOIN data_sources ds
              ON ds.id =
                 eo.source_id

            WHERE
                eo.asset_id =
                CAST(
                    :asset_id
                    AS INTEGER
                )

                AND ds.code =
                    'NWDP_AP_SW'

                AND eo.source_type =
                    'GOVERNMENT_TELEMETRY'

                AND eo.quality_flag
                    IN (
                        'OFFICIAL_DIRECT',
                        'OFFICIAL_SPATIAL_TRANSFER',
                        'OFFICIAL_DERIVED_SPATIAL',
                        'OFFICIAL_SOURCE'
                    )

            ORDER BY
                eo.variable,
                eo.observed_at DESC,
                eo.ingested_at DESC,
                eo.id DESC
            """
        ),
        {
            "asset_id": int(
                asset_id
            ),
        },
    )

    environment: dict[
        str,
        dict[str, Any],
    ] = {}

    for row in (
        result.mappings()
    ):

        variable = (
            row[
                "variable"
            ]
        )

        environment[
            variable
        ] = {
            "value": (
                row[
                    "value"
                ]
            ),

            "unit": (
                row[
                    "unit"
                ]
            ),

            "observed_at": (
                row[
                    "observed_at"
                ]
            ),

            "ingested_at": (
                row[
                    "ingested_at"
                ]
            ),

            "source_code": (
                row[
                    "source_code"
                ]
            ),

            "source": (
                row[
                    "source_name"
                ]
            ),

            "source_type": (
                row[
                    "source_type"
                ]
            ),

            "spatial_method": (
                row[
                    "spatial_method"
                ]
            ),

            "quality_flag": (
                row[
                    "quality_flag"
                ]
            ),

            "confidence": (
                row[
                    "confidence_score"
                ]
            ),

            "is_estimated": (
                row[
                    "is_estimated"
                ]
            ),

            "freshness": (
                _freshness(
                    row[
                        "observed_at"
                    ]
                )
            ),
        }

    return environment


# ============================================================
# Official structural evidence
# ============================================================


async def _official_evidence(
    session: AsyncSession,
    asset_id: int,
) -> list[
    dict[str, Any]
]:

    result = await session.execute(
        text(
            """
            SELECT
                oe.id,
                oe.evidence_type,
                oe.field_name,
                oe.numeric_value,
                oe.text_value,
                oe.unit,
                oe.rating_system,
                oe.observed_at,
                oe.valid_from,
                oe.valid_to,
                oe.authority_level,
                oe.origin,
                oe.quality_flag,
                oe.confidence_score,
                oe.is_official,
                oe.is_derived,
                oe.is_synthetic,
                oe.processing_method,

                sd.agency,

                sd.title
                    AS document_title,

                sd.document_type,

                sd.document_url,

                sd.source_record_id,

                sd.published_at,

                ds.code
                    AS source_code,

                ds.name
                    AS source_name

            FROM official_evidence oe

            JOIN source_documents sd
              ON sd.id =
                 oe.document_id

            JOIN data_sources ds
              ON ds.id =
                 oe.source_id

            WHERE
                oe.asset_id =
                CAST(
                    :asset_id
                    AS INTEGER
                )

                AND COALESCE(
                    oe.is_synthetic,
                    FALSE
                ) = FALSE

            ORDER BY
                oe.observed_at
                    DESC NULLS LAST,

                oe.valid_from
                    DESC NULLS LAST,

                oe.id DESC
            """
        ),
        {
            "asset_id": int(
                asset_id
            ),
        },
    )

    return [
        dict(
            row
        )
        for row
        in result.mappings()
    ]


# ============================================================
# Structural evidence interpretation
# ============================================================


def _structural_state(
    evidence_rows: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:

    # Only A1/A2 evidence may establish structural condition.
    #
    # Direct official evidence:
    #   is_official = True
    #
    # Or a clearly-labelled SIMRAS derivation from official A1/A2:
    #   is_derived = True
    #   origin = DERIVED_FROM_OFFICIAL

    accepted = [
        row
        for row
        in evidence_rows
        if (
            str(
                row.get(
                    "authority_level"
                )
                or ""
            ).upper()
            in {
                "A1",
                "A2",
            }
        )
        and (
            row.get(
                "is_official"
            )
            is True

            or (
                row.get(
                    "is_derived"
                )
                is True

                and str(
                    row.get(
                        "origin"
                    )
                    or ""
                ).upper()
                ==
                "DERIVED_FROM_OFFICIAL"
            )
        )
    ]

    best_condition = (
        "UNKNOWN"
    )

    best_risk = (
        "UNKNOWN"
    )

    selected: (
        dict[str, Any]
        | None
    ) = None

    for row in accepted:

        field = _norm(
            row.get(
                "field_name"
            )
        )

        rating_system = _norm(
            row.get(
                "rating_system"
            )
        )

        # ----------------------------------------------------
        # Indian Railways CRN
        # ----------------------------------------------------

        if (
            "CRN"
            in rating_system

            or field
            in {
                "RAILWAY CRN",
                "CRN",
                "CONDITION RATING NUMBER",
            }
        ):

            raw = (
                row.get(
                    "numeric_value"
                )
                if row.get(
                    "numeric_value"
                )
                is not None

                else row.get(
                    "text_value"
                )
            )

            (
                condition,
                risk,
            ) = (
                _condition_from_crn(
                    raw
                )
            )

        # ----------------------------------------------------
        # Dam safety category
        # ----------------------------------------------------

        elif field in {
            "DAM SAFETY CATEGORY",
            "SAFETY CATEGORY",
            "DEFICIENCY CATEGORY",
        }:

            (
                condition,
                risk,
            ) = (
                _condition_from_dam_category(
                    row.get(
                        "text_value"
                    )
                )
            )

        # ----------------------------------------------------
        # Explicit structural condition
        # ----------------------------------------------------

        elif field in {
            "DAM OVERALL CONDITION",
            "OVERALL CONDITION",
            "OFFICIAL CONDITION",
            "CONDITION",
            "STRUCTURAL CONDITION",
        }:

            (
                condition,
                risk,
            ) = (
                _condition_from_text(
                    row.get(
                        "text_value"
                    )
                )
            )

        else:
            continue

        if (
            condition
            == "UNKNOWN"
        ):
            continue

        # Use worst qualifying structural state.
        if (
            selected is None

            or RISK_ORDER[
                risk
            ]
            >
            RISK_ORDER[
                best_risk
            ]
        ):

            best_condition = (
                condition
            )

            best_risk = (
                risk
            )

            selected = (
                row
            )

    # --------------------------------------------------------
    # No official structural rating available
    # --------------------------------------------------------

    if selected is None:

        return {
            "condition": (
                "UNKNOWN"
            ),

            "risk": (
                "UNKNOWN"
            ),

            "origin": (
                "INSUFFICIENT_EVIDENCE"
            ),

            "authority_level": (
                None
            ),

            "rating_system": (
                None
            ),

            "observed_at": (
                None
            ),

            "confidence": (
                None
            ),

            "source": (
                None
            ),

            "document": (
                None
            ),

            "document_url": (
                None
            ),

            "field_name": (
                None
            ),

            "evidence_type": (
                None
            ),

            "processing_method": (
                None
            ),

            "message": (
                "No qualifying A1/A2 structural "
                "condition rating is linked to "
                "this asset."
            ),
        }

    # --------------------------------------------------------
    # Qualifying structural result
    # --------------------------------------------------------

    origin = (
        "DERIVED_FROM_OFFICIAL"

        if selected.get(
            "is_derived"
        )

        else "OBSERVED"
    )

    return {
        "condition": (
            best_condition
        ),

        "risk": (
            best_risk
        ),

        "origin": (
            origin
        ),

        "authority_level": (
            selected.get(
                "authority_level"
            )
        ),

        "rating_system": (
            selected.get(
                "rating_system"
            )
        ),

        "observed_at": (
            selected.get(
                "observed_at"
            )
        ),

        "confidence": (
            selected.get(
                "confidence_score"
            )
        ),

        "source": (
            selected.get(
                "source_name"
            )
        ),

        "document": (
            selected.get(
                "document_title"
            )
        ),

        "document_url": (
            selected.get(
                "document_url"
            )
        ),

        "field_name": (
            selected.get(
                "field_name"
            )
        ),

        "evidence_type": (
            selected.get(
                "evidence_type"
            )
        ),

        "processing_method": (
            selected.get(
                "processing_method"
            )
        ),

        "message": (
            "Structural state is derived "
            "from official evidence."

            if origin
            == "DERIVED_FROM_OFFICIAL"

            else (
                "Structural state is directly "
                "reported by official evidence."
            )
        ),
    }


# ============================================================
# Environmental hazard
# ============================================================


def _environment_hazard(
    environment: dict[
        str,
        dict[str, Any],
    ],
) -> dict[str, Any]:

    rainfall_24h = (
        environment
        .get(
            "rainfall_24h",
            {},
        )
        .get(
            "value"
        )
    )

    rainfall_7d = (
        environment
        .get(
            "rainfall_7d",
            {},
        )
        .get(
            "value"
        )
    )

    used: list[
        str
    ] = []

    if (
        rainfall_24h
        is not None
    ):
        used.append(
            "rainfall_24h"
        )

    if (
        rainfall_7d
        is not None
    ):
        used.append(
            "rainfall_7d"
        )

    # --------------------------------------------------------
    # No rainfall exposure available
    # --------------------------------------------------------

    if not used:

        return {
            "value": (
                "UNKNOWN"
            ),

            "score": (
                None
            ),

            "origin": (
                "INSUFFICIENT_EVIDENCE"
            ),

            "inputs_used": (
                []
            ),

            "note": (
                "No trusted government rainfall "
                "observation is matched to this asset. "
                "Reservoir and river levels are displayed "
                "but not converted into a hazard band "
                "without station-specific official thresholds."
            ),
        }

    # --------------------------------------------------------
    # Existing transparent rainfall hazard engine
    # --------------------------------------------------------

    baseline = score_risk(
        RiskInput(
            rainfall_mm_24h=(
                rainfall_24h
            ),

            rainfall_mm_7d=(
                rainfall_7d
            ),
        )
    )

    return {
        "value": (
            baseline.hazard_level
            or "UNKNOWN"
        ),

        "score": (
            baseline.hazard_score
        ),

        "origin": (
            "DERIVED_FROM_OFFICIAL"
        ),

        "inputs_used": (
            used
        ),

        "note": (
            "Hazard band is derived only from "
            "trusted NWDP rainfall observations. "
            "Raw reservoir/river water level is "
            "shown separately and is not labelled "
            "dangerous without an official "
            "station-specific warning/danger/reference "
            "threshold."
        ),
    }


# ============================================================
# Overall risk
# ============================================================


def _overall_risk(
    structural_risk: str,
    hazard_risk: str,
) -> dict[str, Any]:

    # Environmental hazard alone must not be presented as
    # structural infrastructure risk.

    if (
        structural_risk
        == "UNKNOWN"
    ):

        return {
            "value": (
                "UNKNOWN"
            ),

            "origin": (
                "INSUFFICIENT_EVIDENCE"
            ),

            "message": (
                "Environmental hazard does not establish "
                "structural risk. A qualifying official "
                "structural inspection or rating is required."
            ),
        }

    hazard_component = (
        hazard_risk
        if hazard_risk
        in RISK_ORDER

        else "UNKNOWN"
    )

    value = _worse_risk(
        structural_risk,
        hazard_component,
    )

    return {
        "value": (
            value
        ),

        "origin": (
            "DERIVED_FROM_OFFICIAL"
        ),

        "message": (
            "Overall risk band is the worse of "
            "the qualifying structural risk band "
            "and the available environmental hazard band."
        ),
    }


# ============================================================
# Evidence strength
# ============================================================


def _evidence_strength(
    structural: dict[
        str,
        Any,
    ],
    environment: dict[
        str,
        dict[str, Any],
    ],
) -> str:

    # Direct structural evidence is strongest.
    if (
        structural[
            "condition"
        ]
        != "UNKNOWN"
    ):

        if (
            structural.get(
                "origin"
            )
            == "DERIVED_FROM_OFFICIAL"
        ):
            return "MEDIUM"

        confidence = (
            structural.get(
                "confidence"
            )
        )

        if (
            confidence
            is None
            or float(
                confidence
            )
            >= 0.80
        ):
            return "HIGH"

        return "MEDIUM"

    # Government environmental evidence exists,
    # but structural condition is unavailable.
    if environment:
        return "MEDIUM"

    return (
        "INSUFFICIENT"
    )


# ============================================================
# Evidence summary
# ============================================================


def _evidence_summary(
    evidence_rows: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:

    a1 = 0
    a2 = 0
    official = 0
    derived = 0

    for row in evidence_rows:

        authority = str(
            row.get(
                "authority_level"
            )
            or ""
        ).upper()

        if authority == "A1":
            a1 += 1

        if authority == "A2":
            a2 += 1

        if (
            row.get(
                "is_official"
            )
            is True
        ):
            official += 1

        if (
            row.get(
                "is_derived"
            )
            is True
        ):
            derived += 1

    return {
        "total": (
            len(
                evidence_rows
            )
        ),

        "a1": (
            a1
        ),

        "a2": (
            a2
        ),

        "official": (
            official
        ),

        "derived_from_official": (
            derived
        ),
    }


# ============================================================
# Main public service
# ============================================================


async def build_evidence_state(
    session: AsyncSession,
    asset_code: str,
) -> dict[str, Any]:

    # --------------------------------------------------------
    # Canonical asset
    # --------------------------------------------------------

    asset = await _asset(
        session,
        asset_code,
    )

    asset_id = int(
        asset[
            "id"
        ]
    )

    # --------------------------------------------------------
    # Trusted environmental observations
    # --------------------------------------------------------

    environment = (
        await _latest_environment(
            session,
            asset_id,
        )
    )

    # --------------------------------------------------------
    # Official structural evidence
    # --------------------------------------------------------

    evidence_rows = (
        await _official_evidence(
            session,
            asset_id,
        )
    )

    # --------------------------------------------------------
    # Structural state
    # --------------------------------------------------------

    structural = (
        _structural_state(
            evidence_rows
        )
    )

    # --------------------------------------------------------
    # Environmental hazard
    # --------------------------------------------------------

    hazard = (
        _environment_hazard(
            environment
        )
    )

    # --------------------------------------------------------
    # Overall risk
    # --------------------------------------------------------

    risk = (
        _overall_risk(
            structural[
                "risk"
            ],
            hazard[
                "value"
            ],
        )
    )

    # --------------------------------------------------------
    # Evidence strength
    # --------------------------------------------------------

    strength = (
        _evidence_strength(
            structural,
            environment,
        )
    )

    # --------------------------------------------------------
    # Evidence counts
    # --------------------------------------------------------

    summary = (
        _evidence_summary(
            evidence_rows
        )
    )

    # --------------------------------------------------------
    # Final Digital Twin evidence state
    # --------------------------------------------------------

    return {

        # ====================================================
        # Canonical identity
        # ====================================================

        "asset": {

            "asset_code": (
                asset[
                    "asset_code"
                ]
            ),

            "name": (
                asset[
                    "name"
                ]
            ),

            "asset_type": (
                asset[
                    "asset_type"
                ]
            ),

            "subtype": (
                asset[
                    "subtype"
                ]
            ),

            "district": (
                asset[
                    "district"
                ]
            ),

            "owner": (
                asset[
                    "owner"
                ]
            ),

            "built_year": (
                asset[
                    "built_year"
                ]
            ),

            "design_life_years": (
                asset[
                    "design_life_years"
                ]
            ),

            "material": (
                asset[
                    "material"
                ]
            ),

            "identity_status": (
                asset[
                    "identity_status"
                ]
            ),

            "identity_confidence": (
                asset[
                    "confidence_score"
                ]
            ),

            "identity_is_estimated": (
                asset[
                    "is_estimated"
                ]
            ),

            "latitude": (
                asset[
                    "latitude"
                ]
            ),

            "longitude": (
                asset[
                    "longitude"
                ]
            ),
        },

        # ====================================================
        # Structural result
        # ====================================================

        "condition": (
            structural
        ),

        # ====================================================
        # Environmental result
        # ====================================================

        "hazard": (
            hazard
        ),

        # ====================================================
        # Combined result
        # ====================================================

        "risk": (
            risk
        ),

        # ====================================================
        # Unsupported numeric outputs intentionally disabled
        # ====================================================

        "health_score": (
            None
        ),

        "risk_score": (
            None
        ),

        "rul_years": (
            None
        ),

        "forecast_ready": (
            False
        ),

        # ====================================================
        # Evidence confidence
        # ====================================================

        "evidence_strength": (
            strength
        ),

        "evidence_summary": (
            summary
        ),

        # ====================================================
        # Raw trusted government observations
        # ====================================================

        "environment": (
            environment
        ),

        # ====================================================
        # Structural/source evidence
        # ====================================================

        "evidence": (
            evidence_rows
        ),

        # ====================================================
        # Governance disclosure
        # ====================================================

        "governance": {

            "structural_rule": (
                "Only direct A1/A2 official evidence "
                "or explicitly labelled derivations "
                "from A1/A2 evidence may establish "
                "structural condition."
            ),

            "telemetry_rule": (
                "Only trusted government telemetry "
                "is used in this state response. "
                "Synthetic/demo environmental values "
                "are excluded."
            ),

            "hazard_rule": (
                "NWDP rainfall can contribute to "
                "environmental hazard. Raw water level "
                "does not become a danger classification "
                "without an official station-specific "
                "threshold."
            ),

            "health_score_rule": (
                "No arbitrary health percentage is "
                "generated without an official rating "
                "or a locally validated model."
            ),

            "rul_rule": (
                "Remaining useful life is disabled "
                "until sufficient longitudinal Andhra "
                "Pradesh inspection evidence is available "
                "and independently validated."
            ),
        },

        # ====================================================
        # Engine metadata
        # ====================================================

        "engine": {

            "name": (
                "SIMRAS Government "
                "Evidence State"
            ),

            "version": (
                "ap_government_"
                "evidence_state_v3"
            ),

            "environment_policy": (
                "NWDP_GOVERNMENT_ONLY"
            ),

            "generated_at": (
                datetime.now(
                    UTC
                )
            ),
        },
    }