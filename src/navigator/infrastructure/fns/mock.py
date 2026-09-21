from __future__ import annotations

from collections.abc import Mapping

from .schemas import CompanyLookupResult, CompanySnapshot, normalize_inn


class MockCompanyLookup:
    def __init__(self, companies: Mapping[str, CompanySnapshot]) -> None:
        self._companies = {normalize_inn(inn): company for inn, company in companies.items()}

    async def lookup_by_inn(self, inn: str) -> CompanyLookupResult:
        normalized = normalize_inn(inn)
        company = self._companies.get(normalized)
        if company is None:
            return CompanyLookupResult.not_found(source="mock")
        return CompanyLookupResult.found(company, source="mock")
