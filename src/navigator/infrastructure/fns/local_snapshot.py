from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .schemas import CompanyLookupResult, CompanySnapshot, normalize_inn


class LocalSnapshotCompanyLookup:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._companies: dict[str, CompanySnapshot] | None = None

    async def lookup_by_inn(self, inn: str) -> CompanyLookupResult:
        normalized = normalize_inn(inn)
        if self._companies is None:
            self._companies = self._load()
        company = self._companies.get(normalized)
        if company is None:
            return CompanyLookupResult.not_found(source="local_snapshot")
        return CompanyLookupResult.found(company, source="local_snapshot")

    def _load(self) -> dict[str, CompanySnapshot]:
        if not self._path.exists():
            return {}
        if self._path.suffix.lower() == ".json":
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            rows = raw.values() if isinstance(raw, dict) else raw
        else:
            with self._path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        companies: dict[str, CompanySnapshot] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            company = _snapshot_from_row(row)
            if company is not None:
                companies[company.inn] = company
        return companies


def _snapshot_from_row(row: dict[str, Any]) -> CompanySnapshot | None:
    inn_raw = row.get("inn") or row.get("ИНН") or row.get("innUl") or row.get("innfl")
    name = row.get("name") or row.get("Наименование") or row.get("namep") or row.get("full_name")
    if not inn_raw or not name:
        return None
    try:
        inn = normalize_inn(str(inn_raw))
    except ValueError:
        return None
    return CompanySnapshot(
        inn=inn,
        name=str(name),
        ogrn=_optional_str(row.get("ogrn") or row.get("ОГРН") or row.get("ogrnip")),
        okved=_optional_str(row.get("okved") or row.get("ОКВЭД")),
        region=_optional_str(row.get("region") or row.get("Регион")),
        is_sme=_optional_bool(row.get("is_sme") or row.get("sme") or row.get("isSme")),
        sme_category=_optional_str(
            row.get("sme_category") or row.get("category") or row.get("Категория")
        ),
    )


def _optional_str(value: Any) -> str | None:
    return None if value in (None, "") else str(value)


def _optional_bool(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "да", "y"}
