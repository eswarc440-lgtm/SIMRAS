from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timezone
from typing import Any

from app.services.dam_health_score import build_health_score_target
from app.services.dam_inspection_targets import _eligible_event, _eligible_finding, _is_major_outcome, build_inspection_targets

UTC = timezone.utc


def build_dam_training_rows(
    events: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    environment: list[dict[str, Any]],
    engineering_by_asset: dict[int, dict[str, Any]],
    applicable_components: list[str],
    minimum_health_coverage: float = 0.70,
    risk_horizon_years: int = 3,
) -> list[dict[str, Any]]:
    """Build leakage-safe dam training rows combining engineering features,
    prior inspection history, cutoff-bounded environment telemetry, and official
    CWC health/risk/RUL targets.
    """
    eligible_events = [e for e in events if _eligible_event(e)]
    if not eligible_events:
        return []

    # Target calculation
    target_records = build_inspection_targets(
        eligible_events,
        findings,
        horizon_years=risk_horizon_years,
    )
    targets_by_inspection_id = {t["inspection_id"]: t for t in target_records}

    findings_by_event: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for f in findings:
        if _eligible_finding(f):
            findings_by_event[int(f["inspection_id"])].append(f)

    # Group events by asset to compute historical lag features
    events_by_asset: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for e in eligible_events:
        events_by_asset[int(e["asset_id"])].append(e)

    for asset_id in events_by_asset:
        events_by_asset[asset_id].sort(
            key=lambda x: (x["inspection_date"], int(x.get("id") or 0))
        )

    # Index environment observations by asset_id
    env_by_asset: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for obs in environment:
        aid = obs.get("asset_id")
        if aid is not None:
            env_by_asset[int(aid)].append(obs)

    rows: list[dict[str, Any]] = []

    for event in eligible_events:
        insp_id = int(event["id"])
        asset_id = int(event["asset_id"])
        insp_date: date = event["inspection_date"]

        # Health target
        current_findings = findings_by_event.get(insp_id, [])
        health_res = build_health_score_target(
            current_findings,
            applicable_components=applicable_components,
            minimum_coverage=minimum_health_coverage,
        )

        target_info = targets_by_inspection_id.get(insp_id, {})

        targets = {
            "health_score_target": health_res.get("health_score_target"),
            "health_target_status": "DERIVED_FROM_OFFICIAL_CWC_CONDITIONS",
            "risk_event_within_horizon": target_info.get("risk_event_within_horizon", 0),
            "rul_event_observed": target_info.get("rul_event_observed", False),
            "rul_event_years": target_info.get("rul_event_years"),
        }

        # 1. Engineering features
        eng = engineering_by_asset.get(asset_id, {})
        features: dict[str, Any] = dict(eng)

        # 2. Environment observations strictly BEFORE or ON cutoff date
        # Convert date to end of day UTC
        cutoff_dt = datetime.combine(insp_date, time.max, tzinfo=UTC)
        candidate_env = [
            o for o in env_by_asset.get(asset_id, [])
            if o.get("observed_at") is not None and o["observed_at"] <= cutoff_dt
        ]
        # Sort by observed_at to take latest for each variable
        candidate_env.sort(key=lambda x: x["observed_at"])
        latest_env_by_var: dict[str, float] = {}
        for o in candidate_env:
            var = o.get("variable")
            val = o.get("value")
            if var and val is not None:
                latest_env_by_var[var] = float(val)

        features.update(latest_env_by_var)

        # 3. Prior inspection history (strictly before current event)
        all_asset_events = events_by_asset.get(asset_id, [])
        prior_events = [
            e for e in all_asset_events
            if (e["inspection_date"] < insp_date)
            or (e["inspection_date"] == insp_date and int(e["id"]) < insp_id)
        ]

        features["previous_inspection_count"] = len(prior_events)

        prior_major_count = sum(
            1 for pe in prior_events
            if _is_major_outcome(pe, findings_by_event.get(int(pe["id"]), []))
        )
        features["previous_major_deficiency_count"] = prior_major_count

        if prior_events:
            prev_event = prior_events[-1]
            days_diff = (insp_date - prev_event["inspection_date"]).days
            features["days_since_previous_inspection"] = days_diff

        # Ensure no target leakage into features
        features.pop("current_gates_condition", None)
        features.pop("current_health_score", None)

        rows.append({
            "inspection_id": insp_id,
            "asset_id": asset_id,
            "features": features,
            "targets": targets,
        })

    return rows
