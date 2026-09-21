from __future__ import annotations

from .errors import InvalidInn


def normalize_inn(value: str) -> str:
    inn = "".join(value.split())
    if not inn.isdigit() or len(inn) not in (10, 12):
        raise InvalidInn("INN must contain 10 or 12 digits")
    if not has_valid_checksum(inn):
        raise InvalidInn("INN checksum is invalid")
    return inn


def has_valid_checksum(inn: str) -> bool:
    if len(inn) == 10:
        return _control_digit(inn, (2, 4, 10, 3, 5, 9, 4, 6, 8)) == int(inn[9])
    if len(inn) == 12:
        n11 = _control_digit(inn, (7, 2, 4, 10, 3, 5, 9, 4, 6, 8))
        n12 = _control_digit(inn, (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8))
        return n11 == int(inn[10]) and n12 == int(inn[11])
    return False


def _control_digit(inn: str, coefficients: tuple[int, ...]) -> int:
    return (
        sum(int(digit) * coefficient for digit, coefficient in zip(inn, coefficients, strict=False))
        % 11
        % 10
    )
