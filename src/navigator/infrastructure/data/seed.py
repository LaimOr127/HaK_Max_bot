from __future__ import annotations

import argparse
import asyncio
import csv
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from navigator.config import get_settings
from navigator.infrastructure.data.import_measures import (
    import_rows,
    load_csv,
    load_sphere_catalog,
)
from navigator.infrastructure.db import models
from navigator.infrastructure.db.session import create_session_factory


def repo_data_dir() -> Path:
    working_copy = Path.cwd() / "data"
    if working_copy.is_dir():
        return working_copy
    return Path(__file__).resolve().parents[4] / "data"


async def seed_demo(data_dir: Path | None = None) -> None:
    data_dir = data_dir or repo_data_dir()
    production = get_settings().app_env == "production"
    category_catalog, catalog_errors = load_sphere_catalog(data_dir / "spravochnik.xlsx")
    if catalog_errors:
        raise ValueError("\n".join(str(error) for error in catalog_errors))
    measures, errors = (
        load_csv(data_dir / "measures.example.csv", category_catalog=category_catalog)
        if not production
        else ([], [])
    )
    if errors:
        raise ValueError("\n".join(str(error) for error in errors))

    session_factory = create_session_factory(get_settings())
    async with session_factory() as session:
        async with session.begin():
            await _seed_spheres(session, category_catalog)
            await _seed_okved(session, data_dir / "okved_mapping.csv")
            if measures:
                await import_rows(session, measures, is_demo=True)
                await session.execute(
                    update(models.Measure)
                    .where(models.Measure.is_demo.is_(True))
                    .where(
                        models.Measure.external_code.not_in([row.external_code for row in measures])
                    )
                    .values(is_active=False)
                )
            else:
                await session.execute(
                    update(models.Measure)
                    .where(models.Measure.is_demo.is_(True))
                    .values(is_active=False)
                )
            current_measures, current_errors = load_csv(
                data_dir / "measures.current.csv", category_catalog=category_catalog
            )
            if current_errors:
                raise ValueError("\n".join(str(error) for error in current_errors))
            await import_rows(session, current_measures)
            await _seed_courses(session, data_dir / "courses.current.csv")


async def _seed_spheres(session: AsyncSession, catalog: dict[str, str]) -> None:
    legacy_codes = {
        "foodservice": "food",
        "household_services": "household",
        "it_digital": "it",
        "construction_repair": "construction",
        "beauty_health": "beauty",
        "transport_logistics": "transport",
    }
    for name, code in catalog.items():
        if code == "any":
            continue
        sphere = await session.scalar(
            select(models.SphereCategory).where(models.SphereCategory.code == code)
        )
        if sphere is None:
            legacy_code = next((old for old, new in legacy_codes.items() if new == code), None)
            if legacy_code is not None:
                sphere = await session.scalar(
                    select(models.SphereCategory).where(models.SphereCategory.code == legacy_code)
                )
        if sphere is None:
            sphere = models.SphereCategory(code=code)
            session.add(sphere)
        sphere.code = code
        sphere.name = name
        sphere.is_active = True


async def _seed_okved(session: AsyncSession, path: Path) -> None:
    sphere_ids = {
        sphere.code: sphere.id for sphere in await session.scalars(select(models.SphereCategory))
    }
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            for okved_class in _expand_okved(row["okved_class"]):
                mapping = await session.get(models.OkvedMapping, okved_class)
                if mapping is None:
                    mapping = models.OkvedMapping(okved_class=okved_class)
                    session.add(mapping)
                mapping.sphere_category_id = sphere_ids[row["sphere"]]
                mapping.note = row.get("note") or None


async def _seed_courses(session: AsyncSession, path: Path) -> None:
    sphere_ids = {
        sphere.code: sphere.id for sphere in await session.scalars(select(models.SphereCategory))
    }
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
        for row in rows:
            course = await session.scalar(
                select(models.Course).where(models.Course.name == row["name"])
            )
            if course is None:
                course = models.Course(name=row["name"])
                session.add(course)
            course.is_free = row["is_free"].strip().lower() == "true"
            course.description = row["description"]
            course.url = row["url"]
            course.source_name = row["source_name"]
            course.sphere_category_id = sphere_ids.get(row["sphere"])
            course.is_active = row["is_active"].strip().lower() == "true"
    await session.execute(
        update(models.Course)
        .where(models.Course.name.not_in([row["name"] for row in rows]))
        .values(is_active=False)
    )


def _expand_okved(value: str) -> tuple[str, ...]:
    value = value.strip()
    if "-" not in value:
        return (value.zfill(2),)
    start_raw, end_raw = value.split("-", maxsplit=1)
    start = int(start_raw)
    end = int(end_raw)
    return tuple(f"{item:02d}" for item in range(start, end + 1))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args(argv)
    asyncio.run(seed_demo(args.data_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
