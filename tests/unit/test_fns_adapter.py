from navigator.domain.enums import CompanyLookupStatus, MspCategory
from navigator.infrastructure.fns.adapter import CompanyLookupAdapter
from navigator.infrastructure.fns.schemas import CompanyLookupResult, CompanySnapshot


class Lookup:
    def __init__(self, result: CompanyLookupResult) -> None:
        self.result = result

    async def lookup_by_inn(self, _inn: str) -> CompanyLookupResult:
        return self.result


async def test_adapter_maps_found_company_to_application_contract() -> None:
    result = await CompanyLookupAdapter(
        Lookup(
            CompanyLookupResult.found(
                CompanySnapshot("7712345678", "Demo", region="77", sme_category="small"),
                source="test",
            )
        )
    ).find_by_inn("7712345678")

    assert result.status is CompanyLookupStatus.FOUND
    assert result.region_code == "77"
    assert result.msp_category is MspCategory.SMALL


async def test_adapter_preserves_not_found_and_degrades_other_failures() -> None:
    missing = await CompanyLookupAdapter(
        Lookup(CompanyLookupResult.not_found(source="test"))
    ).find_by_inn("7712345678")
    unavailable = await CompanyLookupAdapter(
        Lookup(CompanyLookupResult.unavailable(source="test", reason="timeout"))
    ).find_by_inn("7712345678")

    assert missing.status is CompanyLookupStatus.NOT_FOUND
    assert unavailable.status is CompanyLookupStatus.TEMPORARILY_UNAVAILABLE
