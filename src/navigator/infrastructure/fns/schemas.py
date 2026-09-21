from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CompanyStatus = Literal["found", "not_found", "unavailable"]


@dataclass(frozen=True)
class CompanySnapshot:
    inn: str
    name: str
    ogrn: str | None = None
    okved: str | None = None
    region: str | None = None
    is_sme: bool | None = None
    sme_category: str | None = None


@dataclass(frozen=True)
class CompanyLookupResult:
    status: CompanyStatus
    company: CompanySnapshot | None = None
    reason: str | None = None
    source: str = "unknown"

    @classmethod
    def found(cls, company: CompanySnapshot, *, source: str) -> CompanyLookupResult:
        return cls(status="found", company=company, source=source)

    @classmethod
    def not_found(cls, *, source: str, reason: str | None = None) -> CompanyLookupResult:
        return cls(status="not_found", reason=reason, source=source)

    @classmethod
    def unavailable(cls, *, source: str, reason: str) -> CompanyLookupResult:
        return cls(status="unavailable", reason=reason, source=source)


def normalize_inn(inn: str) -> str:
    digits = "".join(ch for ch in inn if ch.isdigit())
    if len(digits) not in {10, 12}:
        raise ValueError("INN must contain 10 or 12 digits")
    return digits
