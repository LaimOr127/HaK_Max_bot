from __future__ import annotations

from dataclasses import dataclass

from .inn import normalize_inn


@dataclass(frozen=True, slots=True)
class Inn:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", normalize_inn(self.value))


@dataclass(frozen=True, slots=True)
class Region:
    code: str
    name: str

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.name.strip():
            raise ValueError("region code and name are required")
