from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .entities import BusinessProfile, Measure
from .enums import MatchStatus


@dataclass(frozen=True, slots=True)
class MatchResult:
    measure: Measure
    status: MatchStatus
    reasons: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()


def recommend(
    profile: BusinessProfile, measures: list[Measure], today: date, limit: int = 3
) -> list[MatchResult]:
    results = [match_measure(profile, measure, today) for measure in measures]
    eligible = sorted(
        (result for result in results if result.status == MatchStatus.ELIGIBLE),
        key=_sort_key,
    )
    uncertain = sorted(
        (result for result in results if result.status == MatchStatus.NEEDS_MORE_INFO),
        key=_sort_key,
    )
    return (eligible + uncertain)[:limit]


def needs_more_info(
    profile: BusinessProfile, measures: list[Measure], today: date
) -> list[MatchResult]:
    return [
        result
        for result in (match_measure(profile, measure, today) for measure in measures)
        if result.status == MatchStatus.NEEDS_MORE_INFO
    ]


def match_measure(profile: BusinessProfile, measure: Measure, today: date) -> MatchResult:
    if not _is_available(measure, today):
        return MatchResult(measure, MatchStatus.INELIGIBLE)

    reasons: list[str] = []
    missing: list[str] = []

    for ok in (
        _check_set(
            profile.region_code, measure.regions, "region", "Регион подходит", missing, reasons
        ),
        _check_set(
            profile.sphere, measure.spheres, "sphere", "Сфера бизнеса подходит", missing, reasons
        ),
        _check_set(
            profile.business_form,
            measure.business_forms,
            "business_form",
            "Форма бизнеса подходит",
            missing,
            reasons,
        ),
        _check_set(
            profile.business_stage,
            measure.business_stages,
            "business_stage",
            "Этап бизнеса подходит",
            missing,
            reasons,
        ),
        _check_set(
            profile.msp_category,
            measure.msp_categories,
            "msp_category",
            "Статус МСП подходит",
            missing,
            reasons,
        ),
    ):
        if not ok:
            return MatchResult(measure, MatchStatus.INELIGIBLE)

    if measure.employee_min is not None or measure.employee_max is not None:
        employee_range = _employee_range(profile)
        if employee_range is None:
            missing.append("employees")
        elif _employee_range_conflicts(employee_range, measure.employee_min, measure.employee_max):
            return MatchResult(measure, MatchStatus.INELIGIBLE)
        elif _employee_range_fits(employee_range, measure.employee_min, measure.employee_max):
            reasons.append("Количество сотрудников подходит")
        else:
            missing.append("employees")

    if missing:
        return MatchResult(measure, MatchStatus.NEEDS_MORE_INFO, tuple(reasons), tuple(missing))
    return MatchResult(measure, MatchStatus.ELIGIBLE, tuple(reasons[:3]), ())


def _check_set(
    value: object | None,
    allowed: frozenset[object],
    missing_name: str,
    reason: str,
    missing: list[str],
    reasons: list[str],
) -> bool:
    if not allowed:
        return True
    if value is None:
        missing.append(missing_name)
        return True
    if value not in allowed:
        return False
    reasons.append(reason)
    return True


def _is_available(measure: Measure, today: date) -> bool:
    if not measure.is_active:
        return False
    if measure.valid_from is not None and measure.valid_from > today:
        return False
    return measure.application_deadline is None or measure.application_deadline >= today


def _sort_key(result: MatchResult) -> tuple[bool, int, int, date, str]:
    measure = result.measure
    amount = int(measure.amount_max_rub or -1)
    deadline = measure.application_deadline or date.max
    return (
        measure.priority <= 0,
        -amount,
        -measure.priority,
        deadline,
        measure.name or str(measure.id),
    )


def _employee_range(profile: BusinessProfile) -> tuple[int, int | None] | None:
    if profile.employee_count is not None:
        return (profile.employee_count, profile.employee_count)
    bucket = profile.employee_bucket
    if bucket is None:
        return None
    return {
        "1": (1, 1),
        "2_15": (2, 15),
        "16_100": (16, 100),
        "100_plus": (101, None),
    }.get(str(bucket))


def _employee_range_conflicts(
    employee_range: tuple[int, int | None], employee_min: int | None, employee_max: int | None
) -> bool:
    low, high = employee_range
    if employee_max is not None and low > employee_max:
        return True
    return employee_min is not None and high is not None and high < employee_min


def _employee_range_fits(
    employee_range: tuple[int, int | None], employee_min: int | None, employee_max: int | None
) -> bool:
    low, high = employee_range
    if employee_min is not None and low < employee_min:
        return False
    if employee_max is not None and (high is None or high > employee_max):
        return False
    return True
