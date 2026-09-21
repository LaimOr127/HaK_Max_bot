from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from navigator.domain.enums import BusinessForm, CompanyLookupStatus, MspCategory


@dataclass(frozen=True, slots=True)
class CompanyLookupResult:
    status: CompanyLookupStatus
    inn: str
    company_name: str | None = None
    ogrn: str | None = None
    business_form: BusinessForm | None = None
    region_code: str | None = None
    region_name: str | None = None
    primary_okved: str | None = None
    msp_category: MspCategory | None = None
    registration_date: date | None = None
    employee_count: int | None = None
    source_checked_at: datetime | None = None


class CompanyLookup(Protocol):
    async def find_by_inn(self, inn: str) -> CompanyLookupResult: ...
