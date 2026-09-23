from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from app.services.dam_health_score import build_health_score_target
from app.services.dam_inspection_targets import build_inspection_targets


def _event_is_eligible(event: dict[str, Any]) -> bool:
    return (
        bool(event.get("is_official"))
        and not bool(event.get("is_synthetic"))
        and bool(event.get("training_eligible"))
        and event.get("asset_id") is not None
        and isinstance(event.get("inspection_date"), date)
    )


def _finding_is_eligible(finding: dict[str, Any]) -> bool:
    return (
        bool(finding.get("is_official"))
        and not bool(finding.get("is_synthetic"))
        and finding.get("inspection_id") is not None
    )


def _observation_before(observation: dict[str, Any], cutoff: date) -> bool:
    observed_at = observation.get("observed_at")
    if not isinstance(observed_at, datetime):
        return False
    return observed_at.date() <= cutoff


def _is_major_finding(finding: dict[str, Any]) -> bool:
    return str(finding.get("severity") or "").strip().upper() in {
        "MAJOR",
        "CRITICAL",
        "SEVERE",
    }


def _future_targets(
    event: dict[str, Any],
    events: list[dict[str, Any]],
    findings_by_inspection: dict[int, list[dict[str, Any]]],
    horizon_years: int,
) -> dict[str, Any]:
    current_date = event["inspection_date"]
    future = [
        candidate
        for candidate in events
        if candidate["asset_id"] == event["asset_id"]
        and candidate["inspection_date"] > current_date
        and (candidate["inspection_date"] - current_date).days / 365.25 <= horizon_years
    ]
    future.sort(key=lambda candidate: candidate["inspection_date"])

    first_major = None
    for candidate in future:
        condition = str(candidate.get("overall_condition") or "").upper()
        category = str(candidate.get("inspection_category") or "").upper()
        findings = findings_by_inspection.get(int(candidate["id"]), [])
        if category in {"I", "II"} or condition in {"MAJOR_DEFICIENCY", "CRITICAL_DEFICIENCY", "UNSAFE", "POOR", "CRITICAL"} or any(_is_major_finding(item) for item in findings):
            first_major = candidate
            break

    return {
        "risk_event_within_horizon": None if not future else int(first_major is not None),
        "risk_target_status": "NO_FUTURE_INSPECTION" if not future else "OBSERVED_FUTURE_OUTCOME",
        "risk_horizon_years": horizon_years,
        "rul_event_years": (
            (first_major["inspection_date"] - current_date).days / 365.25
            if first_major is not None
            else None
        ),
        "rul_event_observed": first_major is not None,
    }


def build_dam_training_rows(
    *,
    events: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    environment: list[dict[str, Any]],
    engineering_by_asset: dict[int, dict[str, Any]],
    applicable_components: list[str],
    minimum_health_coverage: float = 0.70,
    risk_horizon_years: int = 3,
) -> list[dict[str, Any]]:
    """Build leakage-safe dam/barrage training rows from dated evidence.

    Current inspection findings are targets. Only earlier inspections and
    environment observations at or before the inspection date become features.
    """
    if risk_horizon_years <= 0:
        raise ValueError("risk_horizon_years must be positive")

    eligible_events = sorted(
        [event for event in events if _event_is_eligible(event)],
        key=lambda event: (int(event["asset_id"]), event["inspection_date"], int(event.get("id") or 0)),
    )
    eligible_findings = [finding for finding in findings if _finding_is_eligible(finding)]
    findings_by_inspection: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for finding in eligible_findings:
        findings_by_inspection[int(finding["inspection_id"])].append(finding)

    environment_by_asset: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for observation in environment:
        if observation.get("asset_id") is not None and not bool(observation.get("is_estimated")):
            environment_by_asset[int(observation["asset_id"])].append(observation)

    rows: list[dict[str, Any]] = []
    for event in eligible_events:
        asset_id = int(event["asset_id"])
        inspection_date = event["inspection_date"]
        prior = [
            candidate
            for candidate in eligible_events
            if int(candidate["asset_id"]) == asset_id
            and candidate["inspection_date"] < inspection_date
        ]
        prior.sort(key=lambda candidate: candidate["inspection_date"], reverse=True)
        prior_findings = [
            finding
            for candidate in prior
            for finding in findings_by_inspection.get(int(candidate["id"]), [])
        ]

        features = dict(engineering_by_asset.get(asset_id, {}))
        features.update(
            {
                "previous_inspection_count": len(prior),
                "previous_major_deficiency_count": sum(1 for finding in prior_findings if _is_major_finding(finding)),
            }
        )
        if prior:
            features["days_since_previous_inspection"] = (inspection_date - prior[0]["inspection_date"]).days

        for observation in environment_by_asset.get(asset_id, []):
            if _observation_before(observation, inspection_date):
                variable = str(observation.get("variable") or "").strip()
                if variable:
                    existing = features.get(variable)
                    observed_at = observation.get("observed_at")
                    if existing is None or not isinstance(existing, tuple) or observed_at > existing[1]:
                        features[variable] = (observation.get("value"), observed_at)

        for key, value in list(features.items()):
            if isinstance(value, tuple) and len(value) == 2:
                features[key] = value[0]

        current_findings = findings_by_inspection.get(int(event["id"]), [])
        health_target = build_health_score_target(
            current_findings,
            applicable_components=applicable_components,
            minimum_coverage=minimum_health_coverage,
        )
        future_target = _future_targets(
            event,
            eligible_events,
            findings_by_inspection,
            risk_horizon_years,
        )
        rows.append(
            {
                "asset_id": asset_id,
                "inspection_id": int(event["id"]),
                "inspection_date": inspection_date,
                "features": features,
                "targets": {**health_target, **future_target},
            }
        )

    return rows
