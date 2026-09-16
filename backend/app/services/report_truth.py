from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


_UNAVAILABLE_EXACT = {
    "",
    "N/A",
    "NA",
    "NULL",
    "NONE",
    "UNKNOWN",
    "NOT AVAILABLE",
    "NOT_AVAILABLE",
    "NOT VERIFIED",
    "NOT_VERIFIED",
    "WITHHELD",
    "MISSING",
    "UNAVAILABLE",
}

_UNAVAILABLE_PREFIXES = (
    "INSUFFICIENT",
    "WITHHELD_",
    "MISSING_",
    "NOT_AVAILABLE_",
    "UNAVAILABLE_",
)


def _normalise_text(value: str) -> str:
    return " ".join(value.strip().upper().replace("-", " ").split())


def is_report_value_present(value: Any) -> bool:
    """Return True only when a value is meaningful enough to display.

    Zero and False are legitimate evidence values and therefore remain present.
    Sentinel text used by evidence/model gates is intentionally hidden from the
    public-facing report instead of being rendered as an empty-looking row.
    """

    if value is None:
        return False

    if isinstance(value, bool):
        return True

    if isinstance(value, (int, float)):
        return True

    if isinstance(value, str):
        normalised = _normalise_text(value)
        canonical = normalised.replace(" ", "_")
        if normalised in _UNAVAILABLE_EXACT or canonical in _UNAVAILABLE_EXACT:
            return False
        return not canonical.startswith(_UNAVAILABLE_PREFIXES)

    if isinstance(value, Mapping):
        return bool(compact_report_mapping(dict(value)))

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return any(is_report_value_present(item) for item in value)

    return True


def compact_report_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return compact_report_mapping(dict(value))

    if isinstance(value, list):
        compacted = [compact_report_value(item) for item in value]
        return [item for item in compacted if is_report_value_present(item)]

    if isinstance(value, tuple):
        compacted = [compact_report_value(item) for item in value]
        return [item for item in compacted if is_report_value_present(item)]

    return value


def compact_report_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    """Recursively remove unavailable/insufficient report fields.

    This function does not invent replacement values.  It only removes fields
    whose values are explicitly absent or evidence-gated as unavailable.
    """

    result: dict[str, Any] = {}

    for key, raw_value in mapping.items():
        value = compact_report_value(raw_value)
        if not is_report_value_present(value):
            continue
        result[str(key)] = value

    return result
