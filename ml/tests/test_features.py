from simras_ml.features import HEALTH_TARGET, required_columns


def test_health_contract_contains_identity_and_target() -> None:
    columns = required_columns("health")
    assert {"asset_code", "state_time", HEALTH_TARGET} <= columns
    assert "source_confidence" in columns

