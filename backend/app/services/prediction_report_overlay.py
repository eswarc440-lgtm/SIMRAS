from __future__ import annotations

from typing import Any

from sqlalchemy import text


DAM_BARRAGE_HEALTH_MODEL = "nid_dam_condition_transfer_v1"


def _mapping(row: Any) -> dict[str, Any]:
    if row is None:
        return {}

    mapping = getattr(
        row,
        "_mapping",
        None,
    )

    if mapping is not None:
        return dict(mapping)

    try:
        return dict(row)
    except Exception:
        return {}


async def overlay_assessment_with_latest_predictions(
    session: Any,
    asset_code: str,
    report: dict[str, Any],
) -> dict[str, Any]:

    """
    Overlay the eligible persisted Dam/Barrage Health transfer
    prediction onto the selected-asset assessment response.

    Important:
    - only DAM/BARRAGE
    - only nid_dam_condition_transfer_v1
    - never converts hydrology to structural Health
    - does not touch Risk
    - does not touch RUL
    - remains RESEARCH_TRANSFER
    """

    if not isinstance(report, dict):
        return report

    query = text(
        """
        SELECT
            a.id AS asset_id,
            a.asset_code,
            upper(a.asset_type) AS asset_type,

            p.value,
            p.predicted_class,
            p.confidence_score,
            p.model_version,
            p.feature_version,
            p.status,
            p.factors,
            p.prediction_time

        FROM assets a

        JOIN predictions p
          ON p.asset_id = a.id

        WHERE a.asset_code = :asset_code

          AND upper(a.asset_type)
              IN ('DAM','BARRAGE')

          AND p.target = 'health'

          AND p.model_version =
              :model_version

          AND p.value IS NOT NULL

        ORDER BY
            p.prediction_time DESC,
            p.id DESC

        LIMIT 1
        """
    )

    result = await session.execute(
        query,
        {
            "asset_code":
                asset_code,

            "model_version":
                DAM_BARRAGE_HEALTH_MODEL,
        },
    )

    row = result.first()

    if row is None:
        return report

    prediction = _mapping(row)

    try:
        health_score = float(
            prediction["value"]
        )
    except Exception:
        return report


    confidence = prediction.get(
        "confidence_score"
    )

    if confidence is not None:
        try:
            confidence = float(
                confidence
            )
        except Exception:
            confidence = None


    factors = prediction.get(
        "factors"
    )

    if not isinstance(
        factors,
        list,
    ):
        factors = []


    existing_health = report.get(
        "health"
    )

    if not isinstance(
        existing_health,
        dict,
    ):
        existing_health = {}


    new_health = dict(
        existing_health
    )


    new_health.update(
        {
            "score":
                round(
                    health_score,
                    1,
                ),

            "raw_score":
                round(
                    health_score,
                    1,
                ),

            "available":
                True,

            "category":
                prediction.get(
                    "predicted_class"
                )
                or
                "RESEARCH_TRANSFER",

            "confidence":
                confidence,

            "status":
                "RESEARCH_TRANSFER",

            "model_stage":
                "RESEARCH_TRANSFER",

            "model_name":
                (
                    "simras_dam_barrage_"
                    "condition_transfer"
                ),

            "model_version":
                prediction.get(
                    "model_version"
                ),

            "feature_version":
                prediction.get(
                    "feature_version"
                ),

            "prediction_generated_at":
                (
                    prediction[
                        "prediction_time"
                    ].isoformat()
                    if prediction.get(
                        "prediction_time"
                    )
                    else None
                ),

            "factors":
                factors,

            "evidence_basis":
                (
                    "USACE NID condition-assessment "
                    "transfer model using comparable "
                    "engineering attributes."
                ),

            "validation_scope":
                (
                    "External held-out validation; "
                    "Andhra Pradesh local inspection "
                    "validation pending."
                ),

            "official_structural_rating":
                False,
        }
    )


    report["health"] = (
        new_health
    )


    transparency = report.get(
        "transparency"
    )

    if not isinstance(
        transparency,
        dict,
    ):
        transparency = {}


    transparency = dict(
        transparency
    )


    transparency.update(
        {
            "prediction":
                prediction.get(
                    "predicted_class"
                ),

            "confidence":
                confidence,

            "model_name":
                (
                    "simras_dam_barrage_"
                    "condition_transfer"
                ),

            "model_version":
                prediction.get(
                    "model_version"
                ),

            "feature_version":
                prediction.get(
                    "feature_version"
                ),

            "model_stage":
                "RESEARCH_TRANSFER",

            "prediction_method":
                (
                    "usace_nid_condition_"
                    "transfer_ml"
                ),

            "prediction_generated_at":
                (
                    prediction[
                        "prediction_time"
                    ].isoformat()
                    if prediction.get(
                        "prediction_time"
                    )
                    else None
                ),

            "model_validated":
                False,

            "training_scope":
                (
                    "USACE National Inventory of Dams "
                    "condition labels; transferred to "
                    "Andhra Pradesh engineering features."
                ),
        }
    )


    report[
        "transparency"
    ] = transparency


    boundaries = report.get(
        "quality_boundaries"
    )

    if not isinstance(
        boundaries,
        dict,
    ):
        boundaries = {}


    boundaries = dict(
        boundaries
    )


    boundaries.update(
        {
            "dam_barrage_health_stage":
                "RESEARCH_TRANSFER",

            "ap_health_locally_validated":
                False,

            "hydrology_used_as_structural_health":
                False,

            "synthetic_inspection_used":
                False,

            "rul_unchanged":
                True,
        }
    )


    report[
        "quality_boundaries"
    ] = boundaries



    # SIMRAS_PRAKASAM_EVIDENCE_RUL_V2
    #
    # This is an evidence-derived planning/service horizon.
    # It is explicitly NOT an ML structural failure-time RUL.

    if asset_code == "AP_DAM_00001":

        rul_query = text(
            """
            SELECT
                p.value,
                p.predicted_class,
                p.lower_bound,
                p.upper_bound,
                p.confidence_score,
                p.model_version,
                p.feature_version,
                p.status,
                p.factors,
                p.prediction_time

            FROM assets a

            JOIN predictions p
              ON p.asset_id = a.id

            WHERE a.asset_code = :asset_code

              AND p.target = 'rul'

              AND p.model_version =
                  'prakasam_rul_2017_v1'

              AND p.status =
                  'EVIDENCE_DERIVED'

              AND p.value IS NOT NULL

            ORDER BY
                p.prediction_time DESC,
                p.id DESC

            LIMIT 1
            """
        )


        rul_result = await session.execute(
            rul_query,
            {
                "asset_code":
                    asset_code,
            },
        )


        rul_row = rul_result.first()


        if rul_row is not None:

            rp = _mapping(
                rul_row
            )


            try:

                estimate = float(
                    rp["value"]
                )

            except Exception:

                estimate = None


            if estimate is not None:

                existing = report.get(
                    "rul"
                )


                if not isinstance(
                    existing,
                    dict,
                ):

                    existing = {}


                new_rul = dict(
                    existing
                )


                new_rul.update(
                    {
                        "estimate":
                            estimate,

                        "remaining_life_years":
                            estimate,

                        "lower_bound":
                            None,

                        "upper_bound":
                            None,

                        "lower_estimate":
                            None,

                        "upper_estimate":
                            None,

                        "confidence":
                            None,

                        "status":
                            "EVIDENCE_DERIVED",

                        "basis":
                            (
                                "Government-stated "
                                "service horizon"
                            ),

                        "reference_year":
                            2017,

                        "stated_service_horizon_years":
                            50,

                        "target_service_year":
                            2067,

                        "model_version":
                            rp.get(
                                "model_version"
                            ),

                        "feature_version":
                            rp.get(
                                "feature_version"
                            ),

                        "model_stage":
                            "EVIDENCE_DERIVED",

                        "prediction_method":
                            (
                                "government_service_"
                                "horizon_evidence"
                            ),

                        "is_ml_prediction":
                            False,

                        "is_structural_failure_time":
                            False,

                        "official_failure_date":
                            False,

                        "factors":
                            rp.get(
                                "factors"
                            )
                            or [],
                    }
                )


                report[
                    "rul"
                ] = new_rul


                boundaries = report.get(
                    "quality_boundaries"
                )


                if not isinstance(
                    boundaries,
                    dict,
                ):

                    boundaries = {}


                boundaries = dict(
                    boundaries
                )


                boundaries.update(
                    {
                        "rul_available":
                            True,

                        "rul_source_type":
                            (
                                "GOVERNMENT_SERVICE_"
                                "HORIZON_EVIDENCE"
                            ),

                        "rul_is_ml_prediction":
                            False,

                        "rul_has_lower_bound":
                            False,

                        "rul_has_upper_bound":
                            False,

                        "rul_failure_time_prediction":
                            False,
                    }
                )


                report[
                    "quality_boundaries"
                ] = boundaries


    return report
