import csv

from simras_etl.validation import validate_csv


def test_valid_asset_csv(tmp_path) -> None:
    path = tmp_path / "assets.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["asset_code", "name", "asset_type", "longitude", "latitude"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "asset_code": "AP_BR_TEST",
                "name": "Test Bridge",
                "asset_type": "bridge",
                "longitude": "80.6",
                "latitude": "16.5",
            }
        )
    report = validate_csv(path)
    assert report.accepted == 1
    assert report.rejected == 0

