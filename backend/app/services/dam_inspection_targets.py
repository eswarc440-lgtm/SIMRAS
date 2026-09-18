from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any


_MAJOR_CATEGORIES = {"I", "II"}
_MAJOR_CONDITIONS = {
    "MAJOR_DEFICIENCY",
    "CRITICAL_DEFICIENCY",
    "UNSAFE",
    "POOR",
    "CRITICAL",
}
_MAJOR_SEVERITIES = {"MAJOR", "CRITICAL", "SEVERE"}


def _eligible_event(event: dict[str, Any]) -> bool:
    return (
        bool(event.get("is_official", False))
        and not bool(event.get("is_synthetic", False))
        and bool(event.get("training_eligible", False))
        and event.get("asset_id") is not None
        and isinstance(event.get("inspection_date"), date)
    )


def _eligible_finding(finding: dict[str, Any]) -> bool:
    return (
        bool(finding.get("is_official", False))
        and not bool(finding.get("is_synthetic", False))
        and finding.get("inspection_id") is not None
    )


def _is_major_outcome(
    event: dict[str, Any],
    findings: list[dict[str, Any]],
) -> bool:
    category = str(event.get("inspection_category") or "").strip().upper()
    if category in _MAJOR_CATEGORIES:
        return True

    condition = str(event.get("overall_condition") or "").strip().upper()
    if condition in _MAJOR_CONDITIONS:
        return True

    return any(
        str(finding.get("severity") or "").strip().upper() in _MAJOR_SEVERITIES
        for finding in findings
    )


def _years_between(start: date, end: date) -> float:
    return (end - start).days / 365.25


def build_inspection_targets(
    events: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    *,
    horizon_years: int = 3,
) -> list[dict[str, Any]]:
    """Build leakage-safe labels from real, dated inspection outcomes.

    This function deliberately does not manufacture a whole-asset Health Score
    from sparse component evidence. Health remains withheld until a separately
    tested component-coverage/scoring contract is defined.

    Risk is a binary observed future-outcome target. RUL is the observed time
    from the current inspection to the first later major deterioration event.
    """

    if horizon_years <= 0:
        raise ValueError("horizon_years must be positive")

    eligible_events = [event for event in events if _eligible_event(event)]

    findings_by_event: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        if _eligible_finding(finding):
            findings_by_event[int(finding["inspection_id"])].append(finding)

    events_by_asset: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for event in eligible_events:
        events_by_asset[int(event["asset_id"])].append(event)

    for asset_events in events_by_asset.values():
        asset_events.sort(
            key=lambda event: (
                event["inspection_date"],
                int(event.get("id") or 0),
            )
        )

    output: list[dict[str, Any]] = []

    for event in sorted(
        eligible_events,
        key=lambda row: (
            int(row["asset_id"]),
            row["inspection_date"],
            int(row.get("id") or 0),
        ),
    ):
        inspection_id = int(event["id"])
        inspection_date = event["inspection_date"]
        current_findings = findings_by_event.get(inspection_id, [])

        component_targets: dict[str, dict[str, Any]] = {}
        for finding in current_findings:
            component = str(finding.get("component_name") or "").strip()
            if not component:
                continue
            component_targets[component] = {
                "condition_state": finding.get("condition_state"),
                "severity": finding.get("severity"),
            }

        future_events = [
            candidate
            for candidate in events_by_asset[int(event["asset_id"])]
            if candidate["inspection_date"] > inspection_date
            and _years_between(inspection_date, candidate["inspection_date"])
            <= float(horizon_years)
        ]

        risk_event: int | None
        risk_status: str
        rul_years: float | None = None
        rul_observed = False

        if not future_events:
            risk_event = None
            risk_status = "NO_FUTURE_INSPECTION"
        else:
            risk_status = "OBSERVED_FUTURE_OUTCOME"
            first_major: dict[str, Any] | None = None

            for candidate in future_events:
                candidate_findings = findings_by_event.get(int(candidate["id"]), [])
                if _is_major_outcome(candidate, candidate_findings):
                    first_major = candidate
                    break

            if first_major is None:
                risk_event = 0
            else:
                risk_event = 1
                rul_observed = True
                rul_years = _years_between(
                    inspection_date,
                    first_major["inspection_date"],
                )

        output.append(
            {
                "inspection_id": inspection_id,
                "asset_id": int(event["asset_id"]),
                "inspection_date": inspection_date,
                "component_targets": component_targets,
                "health_score_target": None,
                "health_target_status": "INSUFFICIENT_COMPONENT_COVERAGE",
                "risk_event_within_horizon": risk_event,
                "risk_target_status": risk_status,
                "risk_horizon_years": horizon_years,
                "rul_event_years": rul_years,
                "rul_event_observed": rul_observed,
            }
        )

    return output
