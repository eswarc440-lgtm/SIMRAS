import pytest

from app.api.routes.map_features import parse_bbox


def test_parse_bbox_accepts_valid_bounds() -> None:
    assert parse_bbox("76.7,12.6,84.8,19.2") == (
        76.7,
        12.6,
        84.8,
        19.2,
    )


def test_parse_bbox_accepts_none() -> None:
    assert parse_bbox(None) is None


@pytest.mark.parametrize(
    "value",
    [
        "76.7,12.6,84.8",
        "invalid,12.6,84.8,19.2",
        "84.8,12.6,76.7,19.2",
        "76.7,19.2,84.8,12.6",
    ],
)
def test_parse_bbox_rejects_invalid_bounds(value: str) -> None:
    with pytest.raises(ValueError):
        parse_bbox(value)