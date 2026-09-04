"""HTTP clients for the two Zefix access paths.

Requires the ``http`` extra::

    pip install zefix-parser[http]

:class:`LindasClient` talks to the open SPARQL endpoint and needs no
credentials. :class:`ZefixRestClient` talks to the PublicREST API, which is
gated behind HTTP Basic auth; credentials are issued on request by
``zefix@bj.admin.ch``.

Both clients rate-limit themselves and retry transient failures with
exponential backoff. Neither of them is thread-safe: give each thread its own
client.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import date, datetime, timezone

from .identifiers import format_uid, normalize_chid
from .lindas import (
    build_combined_page_query,
    build_count_query,
    build_detail_query_by_uids,
    parse_count,
    parse_entity_page,
    parse_uri_page,
)
from .rest import parse_companies, parse_company, parse_sogc, parse_sogc_list
from .schemas import (
    AuthenticationError,
    Company,
    RawPage,
    RegistryEntity,
    RetryableError,
    SogcPublication,
    TransportError,
)

DEFAULT_REST_BASE_URL = "https://www.zefix.admin.ch/ZefixPublicREST/api/v1"
DEFAULT_LINDAS_ENDPOINT = "https://ld.admin.ch/query"
MAX_PAGE_SIZE = 2000
USER_AGENT = "python-zefix-parser/0.1"

_MAX_BACKOFF = 30.0


class _BaseClient:
    """Throttling, retry and lifecycle shared by both clients."""

    def __init__(
        self,
        *,
        timeout: float,
        min_interval: float,
        max_retries: int,
        headers: dict[str, str],
        auth: object | None = None,
        auth_hint: str = "",
    ) -> None:
        httpx = _import_httpx()
        if max_retries < 1:
            raise ValueError(f"max_retries must be at least 1, got {max_retries!r}")
        self._min_interval = max(0.0, min_interval)
        self._max_retries = max_retries
        self._last_request_at = 0.0
        self._sleep = time.sleep
        self._auth_hint = auth_hint
        self._client = httpx.Client(timeout=timeout, headers=headers, auth=auth)

    def close(self) -> None:
        """Close the underlying connection pool."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def _throttle(self) -> None:
        if not self._min_interval:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._min_interval:
            self._sleep(self._min_interval - elapsed)

    def _request(self, method: str, url: str, **kwargs):
        """Send one request, retrying transient failures. Returns the response."""
        httpx = _import_httpx()
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            self._throttle()
            self._last_request_at = time.monotonic()
            try:
                response = self._client.request(method, url, **kwargs)
            except httpx.TransportError as exc:
                last_error = RetryableError(f"{method} {url} failed: {exc}")
                self._back_off(attempt)
                continue

            if response.status_code in (401, 403):
                raise AuthenticationError(
                    f"{method} {url} returned {response.status_code}{self._auth_hint}"
                )
            if response.status_code == 429 or response.status_code >= 500:
                last_error = RetryableError(
                    f"{method} {url} returned {response.status_code}"
                )
                self._back_off(attempt)
                continue
            return response

        raise last_error if last_error else RetryableError(f"{method} {url} failed")

    def _back_off(self, attempt: int) -> None:
        if attempt + 1 < self._max_retries:
            self._sleep(min(2.0**attempt, _MAX_BACKOFF))


class ZefixRestClient(_BaseClient):
    """Client for the Zefix PublicREST API.

    Args:
        base_url: API root. Defaults to :data:`DEFAULT_REST_BASE_URL`.
        username: HTTP Basic username issued by ``zefix@bj.admin.ch``.
        password: HTTP Basic password.
        timeout: Per-request timeout in seconds.
        min_interval: Minimum seconds between requests.
        max_retries: Attempts per request, including the first.
        user_agent: ``User-Agent`` header to send.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_REST_BASE_URL,
        *,
        username: str = "",
        password: str = "",
        timeout: float = 30.0,
        min_interval: float = 0.5,
        max_retries: int = 3,
        user_agent: str = USER_AGENT,
    ) -> None:
        httpx = _import_httpx()
        auth = httpx.BasicAuth(username, password) if username and password else None
        super().__init__(
            timeout=timeout,
            min_interval=min_interval,
            max_retries=max_retries,
            headers={"Accept": "application/json", "User-Agent": user_agent},
            auth=auth,
            auth_hint=(
                "; the Zefix PublicREST API needs credentials, which "
                "zefix@bj.admin.ch issues on request"
            ),
        )
        self._base_url = base_url.rstrip("/")

    def get_by_uid(self, uid: str) -> Company | None:
        """The company with this UID, or ``None`` if the register has none.

        *uid* is punctuated for you, so ``"CHE123456789"`` and
        ``"CHE-123.456.789"`` both work; the API only accepts the latter.
        """
        data = self._get(f"/company/uid/{format_uid(uid)}")
        return parse_company(data) if data else None

    def get_by_ehraid(self, ehraid: int) -> Company | None:
        """The company with this EHRAID, or ``None``."""
        data = self._get(f"/company/ehraid/{int(ehraid)}")
        return parse_company(data) if data else None

    def get_by_chid(self, chid: str) -> Company | None:
        """The company with this CHID, or ``None``."""
        data = self._get(f"/company/chid/{normalize_chid(chid)}")
        return parse_company(data) if data else None

    def search(
        self,
        name: str,
        *,
        active_only: bool = True,
        max_entries: int = 30,
        offset: int = 0,
    ) -> list[Company]:
        """Companies whose name starts with *name*.

        The endpoint is a prefix match, not a full-text search, and it caps
        how much it will return; there is no cursor, so widen the prefix
        rather than paging deeper.
        """
        payload = {
            "name": name,
            "activeOnly": active_only,
            "maxEntries": int(max_entries),
            "offset": int(offset),
        }
        data = self._post("/company/search", payload)
        return parse_companies(data) if data else []

    def sogc_by_date(self, day: date) -> list[SogcPublication]:
        """Every SOGC/SHAB publication issued on *day*."""
        data = self._get(f"/sogc/bydate/{day.isoformat()}")
        return parse_sogc_list(data) if data else []

    def sogc(self, publication_id: int) -> SogcPublication | None:
        """One SOGC/SHAB publication by its id, or ``None``."""
        data = self._get(f"/sogc/{int(publication_id)}")
        return parse_sogc(data) if data else None

    def _get(self, path: str) -> dict | list | None:
        response = self._request("GET", f"{self._base_url}{path}")
        if response.status_code == 404:
            return None
        return _json(response, f"GET {path}")

    def _post(self, path: str, payload: dict) -> dict | list | None:
        response = self._request("POST", f"{self._base_url}{path}", json=payload)
        if response.status_code == 404:
            return None
        return _json(response, f"POST {path}")


class LindasClient(_BaseClient):
    """Client for the Zefix dataset on the LINDAS SPARQL endpoint.

    No credentials are needed. The dataset carries the whole commercial
    register, so :meth:`iter_entities` is a long walk: roughly 800,000
    companies at the default page size.

    Args:
        endpoint: SPARQL endpoint. Defaults to :data:`DEFAULT_LINDAS_ENDPOINT`.
        page_size: Entities per request, at most :data:`MAX_PAGE_SIZE`.
        timeout: Per-request timeout in seconds.
        min_interval: Minimum seconds between requests.
        max_retries: Attempts per request, including the first.
        user_agent: ``User-Agent`` header to send.
    """

    def __init__(
        self,
        endpoint: str = DEFAULT_LINDAS_ENDPOINT,
        *,
        page_size: int = 500,
        timeout: float = 60.0,
        min_interval: float = 0.5,
        max_retries: int = 4,
        user_agent: str = USER_AGENT,
    ) -> None:
        if not 1 <= page_size <= MAX_PAGE_SIZE:
            raise ValueError(
                f"page_size must be between 1 and {MAX_PAGE_SIZE}, got {page_size!r}"
            )
        super().__init__(
            timeout=timeout,
            min_interval=min_interval,
            max_retries=max_retries,
            headers={
                "Accept": "application/sparql-results+json",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": user_agent,
            },
        )
        self._endpoint = endpoint
        self._page_size = page_size

    def count(self) -> int | None:
        """How many companies the dataset holds, or ``None`` if it will not say."""
        return parse_count(self.query(build_count_query()))

    def fetch_by_uids(self, uids: list[str]) -> list[RegistryEntity]:
        """The companies with these UIDs, in one request.

        Keep batches to a few hundred; the endpoint times out on very large
        ``VALUES`` clauses.
        """
        if not uids:
            return []
        return parse_entity_page(self.query(build_detail_query_by_uids(uids)))

    def iter_pages(self, *, cursor_after: str | None = None) -> Iterator[RawPage]:
        """Walk the register one page at a time, yielding raw responses.

        Each :class:`~zefix_parser.RawPage` carries the cursor it was fetched
        with, so you can persist it and resume an interrupted crawl by passing
        it back as *cursor_after*.
        """
        for page, _entities in self._walk(cursor_after):
            yield page

    def iter_entities(
        self, *, cursor_after: str | None = None
    ) -> Iterator[RegistryEntity]:
        """Walk the whole register, yielding one company at a time."""
        for _page, entities in self._walk(cursor_after):
            yield from entities

    def _walk(
        self, cursor_after: str | None
    ) -> Iterator[tuple[RawPage, list[RegistryEntity]]]:
        page_number = 0
        while True:
            query = build_combined_page_query(
                cursor_after=cursor_after, limit=self._page_size
            )
            content = self.query(query)
            entities = parse_entity_page(content)
            page = RawPage(
                page_number=page_number,
                cursor_after=cursor_after or "",
                content=content,
                content_type="application/sparql-results+json",
                fetched_at=datetime.now(timezone.utc),
                row_count=len(entities),
            )
            yield page, entities

            uris = sorted(_page_uris(content))
            if not uris:
                return
            cursor_after = uris[-1]
            page_number += 1

    def query(self, sparql: str) -> bytes:
        """Send *sparql* to the endpoint and return the raw response body.

        Raises:
            TransportError: on a malformed query, which no retry will fix.
        """
        response = self._request("POST", self._endpoint, data={"query": sparql})
        if response.status_code >= 400:
            raise TransportError(
                f"SPARQL query returned {response.status_code}: {response.text[:200]}"
            )
        return response.content


def _page_uris(content: bytes) -> set[str]:
    """Every entity URI in a page, including entities the parser dropped.

    The cursor has to advance past dropped entities too, or a page whose last
    rows are all invalid loops forever.
    """
    return set(parse_uri_page(content))


def _import_httpx():
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - depends on the install
        raise ImportError(
            "the Zefix HTTP clients need httpx: pip install zefix-parser[http]"
        ) from exc
    return httpx


def _json(response, what: str) -> dict | list | None:
    if response.status_code >= 400:
        raise TransportError(f"{what} returned {response.status_code}")
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError as exc:
        raise TransportError(f"{what} returned invalid JSON: {exc}") from exc
