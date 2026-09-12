from app.models.entities import AssetModel
from app.services.twin_service import twin_quality_metadata


def test_source_backed_l1_twin_ranks_ahead_of_l0() -> None:
    l1 = AssetModel(
        fidelity_level="L1",
        model_source="Official published dimensions",
        source_url="https://example.gov/official-record",
        dimensions={
            "length_m": 1000,
            "width_m": 45,
            "representation": "dimension_derived_parametric",
        },
        is_asset_specific=True,
    )
    l0 = AssetModel(
        fidelity_level="L0",
        model_source="SIMRAS procedural illustration",
        dimensions={},
        is_asset_specific=False,
    )

    strong = twin_quality_metadata(l1, "airport")
    fallback = twin_quality_metadata(l0, "airport")

    assert strong["twin_quality_score"] > fallback["twin_quality_score"]
    assert strong["twin_group"] == "BEST"
    assert strong["twin_source_backed"] is True
    assert fallback["twin_group"] == "BASIC"
    assert fallback["twin_fidelity"] == "L0"


def test_missing_model_is_ranked_last() -> None:
    result = twin_quality_metadata(None, "temple")

    assert result["twin_quality_score"] == 0
    assert result["twin_group"] == "BASIC"
    assert result["twin_template"] == "temple"
