from __future__ import annotations

from navigator.domain.entities import BusinessProfile
from navigator.domain.enums import (
    BusinessForm,
    BusinessStage,
    EmployeeBucket,
    ProfileSource,
    SphereCategory,
)
from navigator.domain.inn import normalize_inn
from navigator.ports.repositories import ProfileRepository

from .dto import ProfileInput


class ProfileService:
    def __init__(self, profiles: ProfileRepository) -> None:
        self._profiles = profiles

    async def get_profile(self, max_user_id: int) -> BusinessProfile | None:
        return await self._profiles.get_by_user(max_user_id)

    async def save_manual_profile(self, data: ProfileInput) -> BusinessProfile:
        profile = BusinessProfile(
            max_user_id=data.max_user_id,
            region_code=data.region_code,
            business_form=BusinessForm(data.business_form),
            sphere=SphereCategory(data.sphere),
            business_stage=BusinessStage(data.business_stage),
            employee_bucket=EmployeeBucket(data.employee_bucket),
            inn=normalize_inn(data.inn) if data.inn else None,
            company_name=data.company_name,
            source=ProfileSource.MANUAL,
        )
        await self._profiles.save(profile)
        return profile

    async def delete_profile(self, max_user_id: int) -> None:
        await self._profiles.delete_by_user(max_user_id)
