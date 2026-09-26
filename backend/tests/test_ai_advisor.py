from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.routes.ai import gateway_only
from app.services.ai_advisor import AmbiguousAssetError, _prediction, build_ai_context


def test_untimestamped_prediction_is_withheld():
    row = SimpleNamespace(
        value=59.9, status="VALIDATED_ML", prediction_time=None,
        predicted_class="MEDIUM", factors=[], model_version="test",
    )
    assert _prediction(row)["value"] is None
    assert _prediction(row)["status"] == "WITHHELD"


def test_timestamped_validated_prediction_keeps_provenance():
    when = datetime(2026, 9, 25, tzinfo=timezone.utc)
    row = SimpleNamespace(
        value=59.9, status="VALIDATED_ML", prediction_time=when,
        predicted_class="MEDIUM", factors=["inspection"], model_version="test-v1",
    )
    result = _prediction(row)
    assert result["value"] == 59.9
    assert result["model_version"] == "test-v1"
    assert result["prediction_time"] == str(when)


def test_locally_validated_ml_prediction_keeps_value_and_method():
    row = SimpleNamespace(value=72.5, status="VALIDATED_LOCAL",
                          prediction_time=datetime(2026, 9, 25, tzinfo=timezone.utc),
                          predicted_class="LOW", factors=[], model_version="local-ml-v1")
    result = _prediction(row)
    assert result["value"] == 72.5
    assert result["status"] == "VALIDATED_LOCAL"
    assert result["method"] == "ML_DERIVED"
    assert result["model_version"] == "local-ml-v1"


@pytest.mark.asyncio
async def test_duplicate_asset_names_require_an_explicit_code():
    assets = [
        SimpleNamespace(id=1, asset_code="A", name="Prakasam Barrage", district="Krishna"),
        SimpleNamespace(id=2, asset_code="B", name="Prakasam Barrage", district="NTR"),
    ]
    session = SimpleNamespace(scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: assets)))
    with pytest.raises(AmbiguousAssetError) as error:
        await build_ai_context(session, "A", "Tell me about Prakasam Barrage")
    assert [choice["asset_code"] for choice in error.value.choices] == ["A", "B"]


@pytest.mark.asyncio
async def test_python_advisor_route_directs_callers_to_gateway():
    with pytest.raises(HTTPException) as error:
        await gateway_only()
    assert error.value.status_code == 410
