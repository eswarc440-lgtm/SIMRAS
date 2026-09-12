from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class OperationalRiskResult:
    operational_risk_score: float | None
    operational_risk_level: str | None
    operational_confidence: float | None
    operational_method: str
    operational_status: str
    operational_factors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _number(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _obs(environment: dict[str, dict[str, Any]], key: str) -> dict[str, Any] | None:
    row = environment.get(key)
    if not isinstance(row, dict):
        return None
    value = _number(row.get("value"))
    if value is None:
        return None

    observed_at = row.get("observed_at")
    if isinstance(observed_at, str):
        try:
            observed_at = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        except ValueError:
            observed_at = None

    if isinstance(observed_at, datetime):
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=UTC)
        if observed_at > datetime.now(UTC):
            return None

    return row


def _piecewise(value: float, low: float, medium: float, high: float) -> float:
    value = max(0.0, value)
    if value <= low:
        return 0.15 * (value / low) if low > 0 else 0.0
    if value <= medium:
        return 0.15 + 0.35 * ((value - low) / (medium - low))
    if value <= high:
        return 0.50 + 0.50 * ((value - medium) / (high - medium))
    return 1.0


def _ratio_piecewise(ratio: float) -> float:
    ratio = max(0.0, ratio)
    if ratio <= 0.70:
        return 0.10 * (ratio / 0.70)
    if ratio <= 0.90:
        return 0.10 + 0.35 * ((ratio - 0.70) / 0.20)
    if ratio <= 1.00:
        return 0.45 + 0.45 * ((ratio - 0.90) / 0.10)
    return min(1.0, 0.90 + (ratio - 1.00) * 0.50)


def _dimension(dimensions: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _number(dimensions.get(key))
        if value is not None and value > 0:
            return value
    return None


def score_dam_barrage_operational_risk(
    *,
    asset_type: str | None,
    environment: dict[str, dict[str, Any]],
    dimensions: dict[str, Any] | None = None,
) -> OperationalRiskResult | None:
    if str(asset_type or "").lower() not in {"dam", "barrage"}:
        return None

    dimensions = dimensions or {}
    components: list[tuple[str, float, float, dict[str, Any]]] = []
    factors: list[str] = []

    def add(name: str, severity: float, weight: float, row: dict[str, Any], detail: str) -> None:
        severity = max(0.0, min(1.0, severity))
        components.append((name, severity, weight, row))
        factors.append(detail)

    row = _obs(environment, "rainfall_24h")
    if row:
        value = float(row["value"])
        add("rainfall_24h", _piecewise(value, 25.0, 75.0, 150.0), 0.25, row,
            f"24 h rainfall exposure: {value:.1f} mm")

    row = _obs(environment, "rainfall_7d")
    if row:
        value = float(row["value"])
        add("rainfall_7d", _piecewise(value, 100.0, 250.0, 500.0), 0.15, row,
            f"7 d rainfall exposure: {value:.1f} mm")

    row = _obs(environment, "water_level_anomaly")
    if row:
        value = max(0.0, float(row["value"]))
        add("water_level_anomaly", _piecewise(value, 0.25, 1.0, 2.0), 0.20, row,
            f"Water-level anomaly exposure: {value:.2f} m")

    row = _obs(environment, "river_velocity")
    if row:
        value = max(0.0, float(row["value"]))
        add("river_velocity", _piecewise(value, 0.5, 1.5, 3.0), 0.15, row,
            f"River velocity exposure: {value:.2f} m/s")

    storage = _obs(environment, "reservoir_storage")
    capacity = _dimension(
        dimensions, "gross_storage_mcm", "storage_capacity_mcm",
        "reservoir_capacity_mcm", "capacity_mcm", "live_storage_mcm"
    )
    if storage and capacity:
        value = max(0.0, float(storage["value"]))
        ratio = value / capacity
        add("reservoir_storage_ratio", _ratio_piecewise(ratio), 0.20, storage,
            f"Reservoir storage utilisation: {ratio * 100:.1f}% of linked capacity")

    level = _obs(environment, "reservoir_level")
    reference_level = _dimension(
        dimensions, "full_reservoir_level_m", "frl_m",
        "maximum_water_level_m", "max_water_level_m"
    )
    if level and reference_level:
        value = max(0.0, float(level["value"]))
        ratio = value / reference_level
        add("reservoir_level_ratio", _ratio_piecewise(ratio), 0.20, level,
            f"Reservoir level: {ratio * 100:.1f}% of linked reference level")

    discharge = _obs(environment, "river_discharge")
    discharge_capacity = _dimension(
        dimensions, "spillway_capacity_m3s", "design_discharge_m3s",
        "discharge_capacity_m3s"
    )
    if discharge and discharge_capacity:
        value = max(0.0, float(discharge["value"]))
        ratio = value / discharge_capacity
        add("discharge_ratio", _ratio_piecewise(ratio), 0.25, discharge,
            f"River discharge: {ratio * 100:.1f}% of linked discharge capacity")

    if not components:
        return OperationalRiskResult(
            operational_risk_score=None,
            operational_risk_level=None,
            operational_confidence=None,
            operational_method="dam_barrage_hydrologic_rules_v1",
            operational_status="INSUFFICIENT_HYDROLOGY_DATA",
            operational_factors=[
                "No usable current dam/barrage hydrologic exposure inputs were available.",
                "Structural health and structural risk remain separate and require structural evidence.",
            ],
        )

    weight_sum = sum(weight for _, _, weight, _ in components)
    weighted_mean = sum(severity * weight for _, severity, weight, _ in components) / weight_sum
    peak = max(severity for _, severity, _, _ in components)
    score = round(max(0.0, min(100.0, 100.0 * (0.65 * weighted_mean + 0.35 * peak))), 1)

    level_name = "HIGH" if score >= 70 else "MEDIUM" if score >= 40 else "LOW"

    confidences: list[float] = []
    directness: list[float] = []
    for _, _, _, row in components:
        conf = _number(row.get("confidence"))
        if conf is not None:
            confidences.append(max(0.0, min(1.0, conf)))
        directness.append(0.80 if bool(row.get("is_estimated")) else 1.0)

    source_conf = sum(confidences) / len(confidences) if confidences else 0.50
    direct_conf = sum(directness) / len(directness) if directness else 0.80
    coverage = min(1.0, weight_sum)

    confidence = round(
        min(0.70, max(0.20, 0.15 + 0.30 * coverage + 0.20 * source_conf + 0.15 * direct_conf)),
        2,
    )

    factors.append(
        "Operational-hydrologic score is transparent decision support, not a structural-health or official dam-safety rating."
    )
    factors.append(
        "Absolute reservoir/river values contribute only when a linked asset-specific reference/capacity is available."
    )

    return OperationalRiskResult(
        operational_risk_score=score,
        operational_risk_level=level_name,
        operational_confidence=confidence,
        operational_method="dam_barrage_hydrologic_rules_v1",
        operational_status="DECISION_SUPPORT",
        operational_factors=factors,
    )
