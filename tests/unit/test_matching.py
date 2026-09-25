from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from navigator.domain.entities import BusinessProfile, Measure
from navigator.domain.enums import (
    BusinessForm,
    BusinessStage,
    EmployeeBucket,
    MatchStatus,
    SphereCategory,
    SupportLevel,
)
from navigator.domain.matching import match_measure, recommend

TODAY = date(2026, 9, 21)


def make_measure(index: int = 1, **changes: object) -> Measure:
    values: dict[str, object] = {
        "id": UUID(f"00000000-0000-0000-0000-{index:012d}"),
        "external_code": f"DEMO-{index}",
        "name": f"DEMO — Мера {index}",
        "support_level": SupportLevel.FEDERAL,
        "amount_display": "До 1 ₽",
        "what_is_it": "Описание",
        "who_can_receive": "МСП",
        "where_to_apply": "Портал",
        "source_name": "DEMO",
        "source_url": "https://example.com",
        "source_checked_at": TODAY,
    }
    values.update(changes)
    return Measure(**values)  # type: ignore[arg-type]


def profile(**changes: object) -> BusinessProfile:
    values: dict[str, object] = {
        "max_user_id": 1,
        "region_code": "77",
        "sphere": SphereCategory.IT_DIGITAL,
        "business_stage": BusinessStage.LT1,
        "business_form": BusinessForm.OOO,
        "employee_bucket": EmployeeBucket.TWO_TO_FIFTEEN,
    }
    values.update(changes)
    return BusinessProfile(**values)  # type: ignore[arg-type]


def test_unrestricted_measure_is_eligible() -> None:
    assert match_measure(profile(), make_measure(), TODAY).status == MatchStatus.ELIGIBLE


def test_matching_and_mismatching_hard_criteria() -> None:
    matching = make_measure(
        regions=frozenset({"77"}),
        spheres=frozenset({SphereCategory.IT_DIGITAL}),
        business_forms=frozenset({BusinessForm.OOO}),
        business_stages=frozenset({BusinessStage.LT1}),
    )
    assert match_measure(profile(), matching, TODAY).status == MatchStatus.ELIGIBLE
    assert (
        match_measure(profile(region_code="78"), matching, TODAY).status == MatchStatus.INELIGIBLE
    )


def test_missing_required_criterion_needs_info() -> None:
    measure = make_measure(regions=frozenset({"77"}))
    result = match_measure(profile(region_code=None), measure, TODAY)
    assert result.status == MatchStatus.NEEDS_MORE_INFO
    assert result.missing == ("region",)


def test_dates_and_active_filter() -> None:
    assert (
        match_measure(profile(), make_measure(is_active=False), TODAY).status
        == MatchStatus.INELIGIBLE
    )
    assert (
        match_measure(profile(), make_measure(valid_from=TODAY + timedelta(days=1)), TODAY).status
        == MatchStatus.INELIGIBLE
    )
    assert (
        match_measure(
            profile(), make_measure(application_deadline=TODAY - timedelta(days=1)), TODAY
        ).status
        == MatchStatus.INELIGIBLE
    )


def test_employee_bounds() -> None:
    assert (
        match_measure(
            profile(employee_count=7), make_measure(employee_min=2, employee_max=15), TODAY
        ).status
        == MatchStatus.ELIGIBLE
    )
    assert (
        match_measure(profile(employee_count=16), make_measure(employee_max=15), TODAY).status
        == MatchStatus.INELIGIBLE
    )
    assert (
        match_measure(
            profile(employee_count=None, employee_bucket=None), make_measure(employee_min=2), TODAY
        ).status
        == MatchStatus.NEEDS_MORE_INFO
    )


def test_sorting_and_limit() -> None:
    measures = [
        make_measure(1, priority=1, amount_max_rub=Decimal("100")),
        make_measure(2, priority=2, amount_max_rub=Decimal("10")),
        make_measure(3, priority=1, amount_max_rub=Decimal("200")),
        make_measure(4, priority=0, amount_max_rub=Decimal("999")),
    ]
    assert [result.measure.external_code for result in recommend(profile(), measures, TODAY)] == [
        "DEMO-3",
        "DEMO-1",
        "DEMO-2",
    ]
