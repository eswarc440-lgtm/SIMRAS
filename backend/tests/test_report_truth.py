from app.services.report_truth import compact_report_mapping, is_report_value_present


def test_unavailable_and_insufficient_values_are_not_present():
    values = [
        None,
        "",
        "   ",
        "N/A",
        "NA",
        "NOT AVAILABLE",
        "NOT_AVAILABLE",
        "WITHHELD",
        "INSUFFICIENT DATA",
        "INSUFFICIENT_ENGINEERING_EVIDENCE",
        "INSUFFICIENT_LOCATION_EVIDENCE",
    ]
    assert all(is_report_value_present(value) is False for value in values)


def test_real_zero_false_and_government_values_are_present():
    assert is_report_value_present(0) is True
    assert is_report_value_present(False) is True
    assert is_report_value_present(1232.92) is True
    assert is_report_value_present("Central Water Commission") is True


def test_compact_report_mapping_removes_unavailable_recursively():
    payload = {
        "asset": {
            "name": "Prakasam Barrage",
            "length_m": 1232.92,
            "width_m": "NOT AVAILABLE",
            "risk": "INSUFFICIENT_DATA",
        },
        "sources": [
            {"name": "AP Water Resources", "url": "https://irrigation.ap.gov.in/"},
            {"name": "NOT AVAILABLE", "url": None},
        ],
        "zero_value": 0,
    }

    compacted = compact_report_mapping(payload)

    assert compacted["asset"] == {
        "name": "Prakasam Barrage",
        "length_m": 1232.92,
    }
    assert compacted["sources"] == [
        {"name": "AP Water Resources", "url": "https://irrigation.ap.gov.in/"}
    ]
    assert compacted["zero_value"] == 0
