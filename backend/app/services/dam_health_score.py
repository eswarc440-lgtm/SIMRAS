from __future__ import annotations

from typing import Any


_METHOD = "simras_cwc_condition_index_v1"
_CONDITION_INDEX = {
    "SATISFACTORY": 100.0,
    "FAIR": 100.0 * (2.0 / 3.0),
    "POOR": 100.0 * (1.0 / 3.0),
    "UNSATISFACTORY": 0.0,
}


def cwc_condition_index(condition: str | None) -> float | None:
    """Map an official CWC-style ordinal condition class to a transparent index.

    CWC condition classes are ordinal. The numeric values below are a SIMRAS
    evenly-spaced normalization for modelling/reporting; they are not official
    CWC numeric scores.
    """

    if condition is None:
        return None
    key = str(condition).strip().upper()
    return _CONDITION_INDEX.get(key)


def build_health_score_target(
    findings: list[dict[str, Any]],
    *,
    applicable_components: list[str],
    minimum_coverage: float = 0.70,
) -> dict[str, Any]:
    """Build an auditable whole-asset health target from official findings.

    Only official, non-synthetic findings with a recognized CWC-style condition
    class count toward component coverage. A whole-asset target is withheld when
    the configured evidence-coverage gate is not met.
    """

    if not 0.0 <= minimum_coverage <= 1.0:
        raise ValueError("minimum_coverage must be between 0 and 1")

    expected = [str(component).strip() for component in applicable_components if str(component).strip()]
    expected_unique = list(dict.fromkeys(expected))
    expected_set = set(expected_unique)

    component_scores: dict[str, float] = {}

    for finding in findings:
        if not bool(finding.get("is_official", False)):
            continue
        if bool(finding.get("is_synthetic", False)):
            continue

        component = str(finding.get("component_name") or "").strip()
        if not component or component not in expected_set:
            continue

        score = cwc_condition_index(finding.get("condition_state"))
        if score is None:
            continue

        component_scores[component] = score

    components_expected = len(expected_unique)
    components_scored = len(component_scores)
    coverage = (
        components_scored / components_expected
        if components_expected
        else 0.0
    )

    health_score: float | None = None
    status = "INSUFFICIENT_COMPONENT_COVERAGE"

    if components_expected and coverage >= minimum_coverage:
        health_score = sum(component_scores.values()) / components_scored
        status = "DERIVED_FROM_OFFICIAL_CWC_CONDITIONS"

    return {
        "health_score_target": health_score,
        "health_target_status": status,
        "component_coverage": coverage,
        "components_scored": components_scored,
        "components_expected": components_expected,
        "component_scores": component_scores,
        "score_method": _METHOD,
        "official_numeric_score": False,
    }
