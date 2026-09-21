from __future__ import annotations

import argparse
import asyncio
import csv
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from navigator.config import get_settings
from navigator.domain.enums import (
    BusinessForm,
    BusinessStage,
    MspCategory,
    SphereCategory,
    SupportLevel,
)
from navigator.infrastructure.db import models
from navigator.infrastructure.db.session import create_session_factory

ARRAY_SEP = "|"
REQUIRED_COLUMNS = (
    "external_code",
    "name",
    "support_level",
    "regions",
    "spheres",
    "business_forms",
    "business_stages",
    "msp_categories",
    "employee_min",
    "employee_max",
    "amount_display",
    "amount_min_rub",
    "amount_max_rub",
    "benefit_detail",
    "what_is_it",
    "who_can_receive",
    "documents",
    "where_to_apply",
    "review_days",
    "valid_from",
    "application_deadline",
    "source_name",
    "source_url",
    "source_checked_at",
    "is_active",
    "priority",
)
RU_REGION_CODES = {f"{index:02d}" for index in range(1, 100)}


@dataclass(frozen=True, slots=True)
class CsvError:
    row: int
    column: str
    message: str

    def __str__(self) -> str:
        return f"row {self.row}, column {self.column}: {self.message}"


@dataclass(frozen=True, slots=True)
class MeasureRow:
    external_code: str
    name: str
    support_level: str
    regions: tuple[str, ...]
    spheres: tuple[str, ...]
    business_forms: tuple[str, ...]
    business_stages: tuple[str, ...]
    msp_categories: tuple[str, ...]
    employee_min: int | None
    employee_max: int | None
    amount_display: str
    amount_min_rub: Decimal | None
    amount_max_rub: Decimal | None
    benefit_detail: str | None
    what_is_it: str
    who_can_receive: str
    documents: tuple[str, ...]
    where_to_apply: str
    review_days: int | None
    valid_from: date | None
    application_deadline: date | None
    source_name: str
    source_url: str
    source_checked_at: date
    is_active: bool
    priority: int


def load_csv(path: Path) -> tuple[list[MeasureRow], list[CsvError]]:
    if not path.is_file():
        return [], [CsvError(0, "file", f"not a file: {path}")]
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            return [], [CsvError(1, "header", f"missing columns: {', '.join(missing)}")]
        return parse_rows(reader)


def parse_rows(rows: Iterable[dict[str, str]]) -> tuple[list[MeasureRow], list[CsvError]]:
    parsed: list[MeasureRow] = []
    errors: list[CsvError] = []
    seen_codes: set[str] = set()
    for row_number, raw in enumerate(rows, start=2):
        row, row_errors = _parse_row(row_number, raw)
        code = raw.get("external_code", "").strip()
        if code and code in seen_codes:
            row_errors.append(CsvError(row_number, "external_code", "duplicate value in file"))
        if code:
            seen_codes.add(code)
        if row:
            parsed.append(row)
        errors.extend(row_errors)
    return parsed, errors


def _parse_row(row_number: int, raw: dict[str, str]) -> tuple[MeasureRow | None, list[CsvError]]:
    errors: list[CsvError] = []

    external_code = _required(raw, row_number, "external_code", errors)
    name = _required(raw, row_number, "name", errors)
    support_level = _enum(raw, row_number, "support_level", SupportLevel, errors)
    regions = _regions(raw, row_number, errors)
    spheres = _enum_list(raw, row_number, "spheres", SphereCategory, errors)
    business_forms = _enum_list(raw, row_number, "business_forms", BusinessForm, errors)
    business_stages = _enum_list(raw, row_number, "business_stages", BusinessStage, errors)
    msp_categories = _enum_list(raw, row_number, "msp_categories", MspCategory, errors)
    employee_min = _int(raw, row_number, "employee_min", errors)
    employee_max = _int(raw, row_number, "employee_max", errors)
    amount_min = _decimal(raw, row_number, "amount_min_rub", errors)
    amount_max = _decimal(raw, row_number, "amount_max_rub", errors)
    valid_from = _date(raw, row_number, "valid_from", errors)
    deadline = _date(raw, row_number, "application_deadline", errors)
    source_checked_at = _date(raw, row_number, "source_checked_at", errors)
    source_url = _url(raw, row_number, "source_url", errors)
    review_days = _int(raw, row_number, "review_days", errors)
    priority = _int(raw, row_number, "priority", errors)
    is_active = _bool(raw, row_number, "is_active", errors)

    amount_display = _required(raw, row_number, "amount_display", errors)
    what_is_it = _required(raw, row_number, "what_is_it", errors)
    who_can_receive = _required(raw, row_number, "who_can_receive", errors)
    where_to_apply = _required(raw, row_number, "where_to_apply", errors)
    source_name = _required(raw, row_number, "source_name", errors)
    documents = _split(raw.get("documents", ""))
    if not documents:
        errors.append(CsvError(row_number, "documents", "empty value"))

    if employee_min is not None and employee_max is not None and employee_min > employee_max:
        errors.append(CsvError(row_number, "employee_min", "must be <= employee_max"))
    if amount_min is not None and amount_max is not None and amount_min > amount_max:
        errors.append(CsvError(row_number, "amount_min_rub", "must be <= amount_max_rub"))
    if valid_from is not None and deadline is not None and deadline < valid_from:
        errors.append(CsvError(row_number, "application_deadline", "must be >= valid_from"))

    if errors or source_checked_at is None or priority is None or is_active is None:
        return None, errors

    return (
        MeasureRow(
            external_code=external_code,
            name=name,
            support_level=support_level,
            regions=regions,
            spheres=spheres,
            business_forms=business_forms,
            business_stages=business_stages,
            msp_categories=msp_categories,
            employee_min=employee_min,
            employee_max=employee_max,
            amount_display=amount_display,
            amount_min_rub=amount_min,
            amount_max_rub=amount_max,
            benefit_detail=_optional(raw, "benefit_detail"),
            what_is_it=what_is_it,
            who_can_receive=who_can_receive,
            documents=documents,
            where_to_apply=where_to_apply,
            review_days=review_days,
            valid_from=valid_from,
            application_deadline=deadline,
            source_name=source_name,
            source_url=source_url,
            source_checked_at=source_checked_at,
            is_active=is_active,
            priority=priority,
        ),
        [],
    )


async def import_rows(
    session: AsyncSession, rows: Sequence[MeasureRow], *, is_demo: bool = False
) -> None:
    sphere_ids = await _ensure_spheres(session)
    await _ensure_regions(session, {region for row in rows for region in row.regions})
    for row in rows:
        measure = await session.scalar(
            select(models.Measure).where(models.Measure.external_code == row.external_code)
        )
        if measure is None:
            measure = models.Measure(external_code=row.external_code)
            session.add(measure)

        measure.name = row.name
        measure.support_level = row.support_level
        measure.amount_display = row.amount_display
        measure.amount_min_rub = row.amount_min_rub
        measure.amount_max_rub = row.amount_max_rub
        measure.benefit_detail = row.benefit_detail
        measure.what_is_it = row.what_is_it
        measure.who_can_receive = row.who_can_receive
        measure.where_to_apply = row.where_to_apply
        measure.review_days = row.review_days
        measure.source_name = row.source_name
        measure.source_url = row.source_url
        measure.source_checked_at = row.source_checked_at
        measure.valid_from = row.valid_from
        measure.application_deadline = row.application_deadline
        measure.employee_min = row.employee_min
        measure.employee_max = row.employee_max
        measure.is_active = row.is_active
        measure.is_demo = is_demo
        measure.priority = row.priority
        await session.flush()

        await _replace_measure_children(session, measure.id, row, sphere_ids)


async def import_file(path: Path, *, validate_only: bool, is_demo: bool = False) -> list[CsvError]:
    rows, errors = load_csv(path)
    if errors or validate_only:
        return errors

    session_factory = create_session_factory(get_settings())
    async with session_factory() as session:
        async with session.begin():
            await import_rows(session, rows, is_demo=is_demo)
    return []


async def _ensure_spheres(session: AsyncSession) -> dict[str, UUID]:
    existing = {
        sphere.code: sphere.id for sphere in await session.scalars(select(models.SphereCategory))
    }
    missing = [sphere for sphere in SphereCategory if sphere.value not in existing]
    for sphere in missing:
        obj = models.SphereCategory(code=sphere.value, name=sphere.value.replace("_", " ").title())
        session.add(obj)
        await session.flush()
        existing[sphere.value] = obj.id
    return existing


async def _ensure_regions(session: AsyncSession, codes: set[str]) -> None:
    if not codes:
        return
    existing = set(
        await session.scalars(select(models.Region.code).where(models.Region.code.in_(codes)))
    )
    for code in sorted(codes - existing):
        session.add(models.Region(code=code, name=f"Region {code}", aliases=[]))


async def _replace_measure_children(
    session: AsyncSession,
    measure_id: object,
    row: MeasureRow,
    sphere_ids: Mapping[str, UUID],
) -> None:
    child_models = (
        models.MeasureRegion,
        models.MeasureSphere,
        models.MeasureBusinessForm,
        models.MeasureBusinessStage,
        models.MeasureMspCategory,
        models.MeasureDocument,
    )
    for child_model in child_models:
        await session.execute(delete(child_model).where(child_model.measure_id == measure_id))

    session.add_all(
        models.MeasureRegion(measure_id=measure_id, region_code=code) for code in row.regions
    )
    session.add_all(
        models.MeasureSphere(measure_id=measure_id, sphere_category_id=sphere_ids[code])
        for code in row.spheres
    )
    session.add_all(
        models.MeasureBusinessForm(measure_id=measure_id, business_form=value)
        for value in row.business_forms
    )
    session.add_all(
        models.MeasureBusinessStage(measure_id=measure_id, business_stage=value)
        for value in row.business_stages
    )
    session.add_all(
        models.MeasureMspCategory(measure_id=measure_id, msp_category=value)
        for value in row.msp_categories
    )
    session.add_all(
        models.MeasureDocument(
            measure_id=measure_id,
            code=_document_code(title),
            title=title,
            sort_order=index,
        )
        for index, title in enumerate(row.documents, start=1)
    )


def _required(raw: dict[str, str], row: int, column: str, errors: list[CsvError]) -> str:
    value = raw.get(column, "").strip()
    if not value:
        errors.append(CsvError(row, column, "empty value"))
    return value


def _optional(raw: dict[str, str], column: str) -> str | None:
    return raw.get(column, "").strip() or None


def _split(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(ARRAY_SEP) if part.strip())


def _enum(
    raw: dict[str, str],
    row: int,
    column: str,
    enum: type[SupportLevel],
    errors: list[CsvError],
) -> str:
    value = _required(raw, row, column, errors)
    if value and value not in enum:
        errors.append(CsvError(row, column, f"unknown value {value!r}"))
    return value


def _enum_list(
    raw: dict[str, str],
    row: int,
    column: str,
    enum: type[BusinessForm] | type[BusinessStage] | type[MspCategory] | type[SphereCategory],
    errors: list[CsvError],
) -> tuple[str, ...]:
    values = _split(raw.get(column, ""))
    for value in values:
        if value not in enum:
            errors.append(CsvError(row, column, f"unknown value {value!r}"))
    return values


def _regions(raw: dict[str, str], row: int, errors: list[CsvError]) -> tuple[str, ...]:
    values = _split(raw.get("regions", ""))
    for value in values:
        if value not in RU_REGION_CODES:
            errors.append(CsvError(row, "regions", f"unknown value {value!r}"))
    return values


def _int(raw: dict[str, str], row: int, column: str, errors: list[CsvError]) -> int | None:
    value = raw.get(column, "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        errors.append(CsvError(row, column, f"invalid integer {value!r}"))
        return None


def _decimal(raw: dict[str, str], row: int, column: str, errors: list[CsvError]) -> Decimal | None:
    value = raw.get(column, "").strip()
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        errors.append(CsvError(row, column, f"invalid monetary number {value!r}"))
        return None


def _date(raw: dict[str, str], row: int, column: str, errors: list[CsvError]) -> date | None:
    value = raw.get(column, "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(CsvError(row, column, f"invalid date {value!r}"))
        return None


def _bool(raw: dict[str, str], row: int, column: str, errors: list[CsvError]) -> bool | None:
    value = raw.get(column, "").strip().lower()
    if value in {"true", "1", "yes"}:
        return True
    if value in {"false", "0", "no"}:
        return False
    errors.append(CsvError(row, column, f"invalid boolean {value!r}"))
    return None


def _url(raw: dict[str, str], row: int, column: str, errors: list[CsvError]) -> str:
    value = _required(raw, row, column, errors)
    parsed = urlparse(value)
    if value and (parsed.scheme not in {"http", "https"} or not parsed.netloc):
        errors.append(CsvError(row, column, f"invalid URL {value!r}"))
    return value


def _document_code(title: str) -> str:
    code = "".join(char.lower() if char.isalnum() else "_" for char in title).strip("_")
    return code[:120] or "document"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    errors = asyncio.run(import_file(args.file, validate_only=args.validate_only))
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
