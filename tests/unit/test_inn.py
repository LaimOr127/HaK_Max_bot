import pytest

from navigator.domain.errors import InvalidInn
from navigator.domain.inn import normalize_inn


@pytest.mark.parametrize("value", ["7707083893", "500100732259", " 7707 083 893 "])
def test_valid_inn(value: str) -> None:
    assert normalize_inn(value).isdigit()


@pytest.mark.parametrize("value", ["7707083894", "500100732258", "123", "abcdefghij"])
def test_invalid_inn(value: str) -> None:
    with pytest.raises(InvalidInn):
        normalize_inn(value)
