from __future__ import annotations

import argparse
import asyncio
import csv
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from navigator.config import get_settings
from navigator.infrastructure.data.import_measures import import_rows, load_csv
from navigator.infrastructure.db import models
from navigator.infrastructure.db.session import create_session_factory


def repo_data_dir() -> Path:
    working_copy = Path.cwd() / "data"
    if working_copy.is_dir():
        return working_copy
    return Path(__file__).resolve().parents[4] / "data"


async def seed_demo(data_dir: Path | None = None) -> None:
    data_dir = data_dir or repo_data_dir()
    measures, errors = load_csv(data_dir / "measures.example.csv")
    if errors:
        raise ValueError("\n".join(str(error) for error in errors))

    session_factory = create_session_factory(get_settings())
    async with session_factory() as session:
        async with session.begin():
            await _seed_spheres(session, data_dir / "sphere_categories.csv")
            await _seed_okved(session, data_dir / "okved_mapping.csv")
            await import_rows(session, measures, is_demo=True)
            await _seed_courses(session, data_dir / "courses.example.csv")


async def _seed_spheres(session: AsyncSession, path: Path) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            sphere = await session.scalar(
                select(models.SphereCategory).where(models.SphereCategory.code == row["code"])
            )
            if sphere is None:
                sphere = models.SphereCategory(code=row["code"])
                session.add(sphere)
            sphere.name = row["name"]
            sphere.is_active = row["is_active"].strip().lower() == "true"


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
        for row in csv.DictReader(file):
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
