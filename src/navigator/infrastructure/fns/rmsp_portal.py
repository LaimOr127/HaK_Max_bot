from __future__ import annotations

from typing import Any

import httpx

from .schemas import CompanyLookupResult, CompanySnapshot, normalize_inn

RMSP_SEARCH_URL = "https://rmsp.nalog.ru/search-proc.json"


class RmspPortalCompanyLookup:
    def __init__(
        self,
        *,
        search_url: str = RMSP_SEARCH_URL,
        timeout_seconds: float = 4.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._search_url = search_url
        self._own_client = client is None
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds))

    async def aclose(self) -> None:
        if self._own_client:
            await self._client.aclose()

    async def lookup_by_inn(self, inn: str) -> CompanyLookupResult:
        normalized = normalize_inn(inn)
        try:
            response = await self._client.post(
                self._search_url,
                data={"mode": "quick", "query": normalized},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return CompanyLookupResult.unavailable(
                source="rmsp_portal",
                reason=exc.__class__.__name__,
            )

        company = _extract_company(payload, normalized)
        if company is None:
            if _has_search_results(payload):
                return CompanyLookupResult.unavailable(source="rmsp_portal", reason="schema_drift")
            return CompanyLookupResult.not_found(source="rmsp_portal")
        return CompanyLookupResult.found(company, source="rmsp_portal")


def _extract_company(payload: Any, inn: str) -> CompanySnapshot | None:
    for row in _iter_dicts(payload):
        row_inn = row.get("inn") or row.get("innUl") or row.get("innfl") or row.get("ИНН")
        try:
            row_matches = row_inn is not None and normalize_inn(str(row_inn)) == inn
        except ValueError:
            row_matches = False
        if not row_matches:
            continue
        name = (
            row.get("name")
            or row.get("name_ex")
            or row.get("namep")
            or row.get("fullName")
            or row.get("Наименование")
        )
        if not name:
            return None
        return CompanySnapshot(
            inn=inn,
            name=str(name),
            ogrn=_as_str(row.get("ogrn") or row.get("ogrnip") or row.get("ОГРН")),
            okved=_as_str(row.get("okved") or row.get("okved1") or row.get("ОКВЭД")),
            region=_as_str(
                row.get("region")
                or row.get("regioncode")
                or row.get("regionName")
                or row.get("Регион")
            ),
            is_sme=True,
            sme_category=_category(row.get("category") or row.get("smeCategory")),
        )
    return None


def _iter_dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        rows: list[dict[str, Any]] = []
        for key in ("data", "rows", "items", "results"):
            rows.extend(_iter_dicts(value.get(key)))
        if not rows and any(key in value for key in ("inn", "innUl", "innfl", "ИНН")):
            rows.append(value)
        return rows
    if isinstance(value, list):
        rows = []
        for item in value:
            rows.extend(_iter_dicts(item))
        return rows
    return []


def _has_search_results(payload: Any) -> bool:
    return bool(_iter_dicts(payload))


def _as_str(value: Any) -> str | None:
    return None if value in (None, "") else str(value)


def _category(value: Any) -> str | None:
    return {"1": "micro", "2": "small", "3": "medium"}.get(str(value), _as_str(value))
