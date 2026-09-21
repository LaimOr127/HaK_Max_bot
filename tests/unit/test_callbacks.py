from uuid import UUID

import pytest

from navigator.presentation.maxbot.callbacks import InvalidCallback, parse_callback


def test_parse_known_callbacks() -> None:
    assert parse_callback("nav:start").action == "nav:start"
    assert parse_callback("employees:2_15").values == ("2_15",)


def test_parse_callback_uuid() -> None:
    value = "12345678-1234-5678-1234-567812345678"
    assert parse_callback(f"measure:add:{value}").uuid() == UUID(value)


@pytest.mark.parametrize(
    "payload",
    ["unknown:value", "measure:add:not-a-uuid", "employees:500", "compare:a:b"],
)
def test_reject_invalid_callbacks(payload: str) -> None:
    with pytest.raises(InvalidCallback):
        parse_callback(payload)
