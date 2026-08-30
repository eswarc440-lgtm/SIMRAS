from __future__ import annotations

from dataclasses import dataclass


CWC_URL = "https://cwc.gov.in/sites/default/files/nwauser/chap5.pdf"
IRC_URL = "https://irc.nic.in/admnis/admin/showimg.aspx?ID=818"
AIRPORT_URL = (
    "https://aim-india.aai.aero/eaip-v2-01-2023/pdf/"
    "Official%20AIC/AIC2021/AIC_2021_17.pdf"
)
BUILDING_URL = (
    "https://www.cochinport.gov.in/sites/default/files/2021-08/"
    "8-%20VOL-IV-Amended%20-Employers%20Requirement%2CMilestone.pdf"
)


@dataclass(slots=True)
class RULProxy:
    estimate_years: float | None
    lower_bound: float | None
    upper_bound: float | None
    confidence: float | None
    status: str
    basis: str
    basis_url: str | None
    method: str


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _class_horizon(
    asset_type: str | None,
    subtype: str | None,
) -> tuple[float, str, str | None, float]:
    kind = str(asset_type or "").strip().lower()
    sub = str(subtype or "").strip().lower()

    if kind in {"dam", "barrage"} or "reservoir" in sub:
        return (
            100.0,
            (
                "CWC general planning guidance: 100-year useful-life "
                "horizon for irrigation/multipurpose projects"
            ),
            CWC_URL,
            0.40,
        )

    if kind == "bridge" or "flyover" in sub or "viaduct" in sub:
        return (
            100.0,
            "IRC bridge design-life planning reference: 100 years",
            IRC_URL,
            0.40,
        )

    if kind == "airport" or "runway" in sub:
        return (
            20.0,
            (
                "Airport pavement planning proxy: 20-year runway/"
                "taxiway useful-life reference"
            ),
            AIRPORT_URL,
            0.30,
        )

    if kind == "temple":
        return (
            50.0,
            (
                "Heritage civil-maintenance proxy using a 50-year "
                "general permanent-building planning horizon; this is "
                "not the historical/heritage life of the temple"
            ),
            BUILDING_URL,
            0.20,
        )

    return (
        50.0,
        (
            "Generic civil-structure maintenance proxy using a "
            "50-year permanent-works planning horizon"
        ),
        BUILDING_URL,
        0.20,
    )


def estimate_rul_proxy(
    *,
    asset_type: str | None,
    subtype: str | None,
    built_year: int | None,
    design_life_years: int | None,
    current_year: int,
    health_score: float | None,
    hazard_score: float | None,
) -> RULProxy:
    kind = str(asset_type or "").strip().lower()

    class_horizon, class_basis, class_url, class_confidence = (
        _class_horizon(asset_type, subtype)
    )

    if design_life_years is not None and design_life_years > 0:
        horizon = float(design_life_years)
        basis = "Asset-stated design life"
        basis_url = None
        basis_confidence = 0.55
        use_age = built_year is not None
        status_base = "ASSET_DESIGN_LIFE"
    else:
        horizon = class_horizon
        basis = class_basis
        basis_url = class_url
        basis_confidence = class_confidence
        use_age = built_year is not None and kind not in {"airport", "temple"}
        status_base = "CLASS_PLANNING_HORIZON"

    health = (
        None
        if health_score is None
        else _clamp(float(health_score), 0.0, 100.0)
    )

    hazard = (
        20.0
        if hazard_score is None
        else _clamp(float(hazard_score), 0.0, 100.0)
    )

    hazard_factor = 1.0 - 0.20 * (hazard / 100.0)

    if use_age:
        age = max(0.0, float(current_year - int(built_year)))
        nominal = max(0.0, horizon - age)

        if health is None:
            estimate = nominal * hazard_factor
            confidence = min(basis_confidence, 0.30)
            uncertainty = 0.40
            method = "AGE_PLUS_CLASS_HAZARD"
        else:
            health_factor = 0.70 + 0.30 * (health / 100.0)
            estimate = nominal * health_factor * hazard_factor
            confidence = basis_confidence
            uncertainty = 0.30
            method = "AGE_HEALTH_HAZARD"

        status = f"EXPERIMENTAL_{status_base}"

    elif health is not None:
        estimate = (
            horizon
            * (health / 100.0)
            * hazard_factor
        )
        confidence = min(basis_confidence, 0.25)
        uncertainty = 0.45
        status = "EXPERIMENTAL_HEALTH_ONLY_CLASS_HORIZON"
        method = "HEALTH_HAZARD_CLASS_HORIZON"

    else:
        return RULProxy(
            estimate_years=None,
            lower_bound=None,
            upper_bound=None,
            confidence=None,
            status="INSUFFICIENT_INPUTS",
            basis=basis,
            basis_url=basis_url,
            method="UNAVAILABLE",
        )

    estimate = _clamp(estimate, 0.0, horizon)

    lower = max(
        0.0,
        estimate * (1.0 - uncertainty),
    )

    upper = min(
        horizon,
        estimate * (1.0 + uncertainty),
    )

    return RULProxy(
        estimate_years=round(estimate, 1),
        lower_bound=round(lower, 1),
        upper_bound=round(upper, 1),
        confidence=round(confidence, 2),
        status=status,
        basis=basis,
        basis_url=basis_url,
        method=method,
    )