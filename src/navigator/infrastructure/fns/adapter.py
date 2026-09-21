from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from navigator.domain.enums import BusinessForm, CompanyLookupStatus, MspCategory
from navigator.ports.company_lookup import CompanyLookupResult

from .schemas import CompanyLookupResult as RawLookupResult


class RawCompanyLookup(Protocol):
    async def lookup_by_inn(self, inn: str) -> RawLookupResult: ...


class CompanyLookupAdapter:
    """Adapts the intentionally best-effort FNS sources to the application port."""

    def __init__(self, lookup: RawCompanyLookup) -> None:
        self._lookup = lookup

    async def find_by_inn(self, inn: str) -> CompanyLookupResult:
        result = await self._lookup.lookup_by_inn(inn)
        if result.status == "not_found":
            return CompanyLookupResult(CompanyLookupStatus.NOT_FOUND, inn)
        if result.status != "found" or result.company is None:
            return CompanyLookupResult(CompanyLookupStatus.TEMPORARILY_UNAVAILABLE, inn)

        company = result.company
        return CompanyLookupResult(
            status=CompanyLookupStatus.FOUND,
            inn=company.inn,
            company_name=company.name,
            ogrn=company.ogrn,
            business_form=BusinessForm.OOO if len(company.inn) == 10 else BusinessForm.IP,
            region_code=_region_code(company.region),
            primary_okved=company.okved,
            msp_category=_msp_category(company.sme_category),
            source_checked_at=datetime.now(UTC),
        )


def _region_code(value: str | None) -> str | None:
    if value and value.isdigit() and len(value) <= 3:
        return value.zfill(2)
    return None


def _msp_category(value: str | None) -> MspCategory | None:
    if not value:
        return None
    normalized = value.strip().lower()
    aliases = {
        "micro": MspCategory.MICRO,
        "микро": MspCategory.MICRO,
        "small": MspCategory.SMALL,
        "малое": MspCategory.SMALL,
        "medium": MspCategory.MEDIUM,
        "среднее": MspCategory.MEDIUM,
    }
    return aliases.get(normalized)
