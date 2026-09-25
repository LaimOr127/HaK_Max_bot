from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .schemas import CompanyLookupResult, CompanySnapshot, normalize_inn

RMSP_SEARCH_URL = "https://rmsp.nalog.ru/search-proc.json"
TRANSPARENT_BUSINESS_SEARCH_URL = "https://pb.nalog.ru/search-proc.json"


class RmspPortalCompanyLookup:
    def __init__(
        self,
        *,
        search_url: str = RMSP_SEARCH_URL,
        transparent_business_url: str = TRANSPARENT_BUSINESS_SEARCH_URL,
        timeout_seconds: float = 4.0,
        client: httpx.AsyncClient | None = None,
        poll_delays: tuple[float, ...] = (1.0, 2.0, 4.0),
    ) -> None:
        self._search_url = search_url
        self._transparent_business_url = transparent_business_url
        self._own_client = client is None
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds))
        self._poll_delays = poll_delays

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
        except (httpx.HTTPError, ValueError):
            return await self._lookup_transparent_business(normalized)

        company = _extract_company(payload, normalized)
        if company is None:
            if _has_search_results(payload):
                return CompanyLookupResult.unavailable(source="rmsp_portal", reason="schema_drift")
            return await self._lookup_transparent_business(normalized)
        return CompanyLookupResult.found(company, source="rmsp_portal")

    async def _lookup_transparent_business(self, inn: str) -> CompanyLookupResult:
        """Best-effort fallback for legal entities absent from the SME register."""
        try:
            response = await self._client.post(
                self._transparent_business_url,
                data={"mode": "search-all", "queryAll": inn, "page": "1", "pageSize": "10"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            initial_payload = response.json()
            request_id = (
                _as_str(initial_payload.get("id")) if isinstance(initial_payload, dict) else None
            )
            if request_id is None:
                return CompanyLookupResult.unavailable(
                    source="transparent_business", reason="schema_drift"
                )

            for delay in self._poll_delays:
                await asyncio.sleep(delay)
                response = await self._client.post(
                    self._transparent_business_url,
                    data={"id": request_id, "method": "get-response"},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                payload = response.json()
                if not _transparent_response_ready(payload):
                    continue
                company = _extract_transparent_business_company(payload, inn)
                if company is None:
                    return CompanyLookupResult.not_found(source="transparent_business")
                return CompanyLookupResult.found(company, source="transparent_business")
        except (httpx.HTTPError, ValueError) as exc:
            return CompanyLookupResult.unavailable(
                source="transparent_business", reason=exc.__class__.__name__
            )
        return CompanyLookupResult.unavailable(
            source="transparent_business", reason="search_timeout"
        )


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


def _transparent_response_ready(payload: Any) -> bool:
    return isinstance(payload, dict) and ("ul" in payload or "ip" in payload)


def _extract_transparent_business_company(payload: Any, inn: str) -> CompanySnapshot | None:
    if not isinstance(payload, dict):
        return None
    for section_name in ("ul", "ip"):
        section = payload.get(section_name)
        if not isinstance(section, dict):
            continue
        for row in _iter_dicts(section.get("data")):
            try:
                matches = normalize_inn(str(row.get("inn", ""))) == inn
            except ValueError:
                matches = False
            if not matches:
                continue
            name = row.get("namep") or row.get("name") or row.get("name_ex")
            if not name:
                return None
            return CompanySnapshot(
                inn=inn,
                name=str(name),
                ogrn=_as_str(row.get("ogrn") or row.get("ogrnip")),
                okved=_as_str(row.get("okved2main") or row.get("okved1")),
                region=_as_str(row.get("regioncode")) or inn[:2],
                is_sme=None,
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
