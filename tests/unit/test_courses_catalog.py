import csv

from navigator.infrastructure.data.seed import repo_data_dir


def test_courses_catalog_has_real_official_free_courses() -> None:
    with (repo_data_dir() / "courses.current.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        rows = list(csv.DictReader(file))

    assert len(rows) >= 5
    assert {row["is_free"] for row in rows} == {"true"}
    assert all(row["is_active"] == "true" for row in rows)
    assert all("example.com" not in row["url"] for row in rows)
    assert all(not row["name"].startswith("DEMO") for row in rows)
    assert {row["source_name"] for row in rows} == {"АО «Корпорация МСП»"}
