from datetime import datetime

from app.api.v1.search import _parse_eis_result_date


def test_parse_eis_result_date_supports_iso_and_russian_formats():
    iso_value = _parse_eis_result_date("2026-07-15T10:30:00Z")
    ru_datetime_value = _parse_eis_result_date("15.07.2026 10:30")
    ru_date_value = _parse_eis_result_date("15.07.2026")

    assert iso_value == datetime(2026, 7, 15, 10, 30, tzinfo=iso_value.tzinfo)
    assert ru_datetime_value == datetime(2026, 7, 15, 10, 30)
    assert ru_date_value == datetime(2026, 7, 15)


def test_parse_eis_result_date_returns_none_for_unknown_format():
    assert _parse_eis_result_date("15/07/2026") is None
