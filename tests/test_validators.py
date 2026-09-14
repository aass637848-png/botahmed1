import pytest
from datetime import datetime
from bot.utils.validators import (
    validate_target_identifier,
    clean_target_identifier,
    validate_positive_int,
    validate_float_range,
    parse_schedule_datetime,
)


def test_clean_target_identifier():
    assert clean_target_identifier("https://t.me/my_channel") == "@my_channel"
    assert clean_target_identifier("t.me/test_group/") == "@test_group"
    assert clean_target_identifier("-1001234567890") == "-1001234567890"


def test_validate_target_identifier_valid():
    # Valid username
    is_valid, cleaned, err = validate_target_identifier("@channel123")
    assert is_valid is True
    assert cleaned == "@channel123"
    assert err is None

    # Missing @ but valid username
    is_valid, cleaned, err = validate_target_identifier("channel123")
    assert is_valid is True
    assert cleaned == "@channel123"

    # Numeric chat_id
    is_valid, cleaned, err = validate_target_identifier("-1001987654321")
    assert is_valid is True
    assert cleaned == "-1001987654321"


def test_validate_target_identifier_invalid():
    is_valid, cleaned, err = validate_target_identifier("")
    assert is_valid is False

    is_valid, cleaned, err = validate_target_identifier("!!!")
    assert is_valid is False


def test_validate_positive_int():
    is_valid, val, err = validate_positive_int("5", min_val=1, max_val=10)
    assert is_valid is True
    assert val == 5

    is_valid, val, err = validate_positive_int("0", min_val=1, max_val=10)
    assert is_valid is False

    is_valid, val, err = validate_positive_int("abc")
    assert is_valid is False


def test_validate_float_range():
    is_valid, val, err = validate_float_range("1.5", min_val=0.1, max_val=5.0)
    assert is_valid is True
    assert val == 1.5

    is_valid, val, err = validate_float_range("10.0", min_val=0.1, max_val=5.0)
    assert is_valid is False

    is_valid, val, err = validate_float_range("invalid")
    assert is_valid is False


def test_parse_schedule_datetime():
    # Test valid HH:MM
    is_valid, dt, err = parse_schedule_datetime("23:59")
    assert is_valid is True
    assert isinstance(dt, datetime)

    # Test invalid string
    is_valid, dt, err = parse_schedule_datetime("not-a-date")
    assert is_valid is False
