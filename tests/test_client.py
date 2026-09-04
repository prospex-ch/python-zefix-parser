import json
from datetime import date
from urllib.parse import parse_qs
from pathlib import Path

import httpx
import pytest

from zefix_parser import AuthenticationError, RetryableError, TransportError
from zefix_parser.client import LindasClient, ZefixRestClient

FIXTURES = Path(__file__).parent / "fixtures"


def _rest_client(handler, **kwargs):
    """A REST client whose requests are answered by *handler*, with no throttling."""
    kwargs.setdefault("username", "user")
    kwargs.setdefault("password", "pass")
    client = ZefixRestClient(min_interval=0.0, **kwargs)
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    client._sleep = lambda seconds: None
    return client


def _lindas_client(handler, **kwargs):
    client = LindasClient(min_interval=0.0, **kwargs)
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    client._sleep = lambda seconds: None
    return client


def _sent_query(request):
    """The SPARQL text of a form-encoded request body."""
    return parse_qs(request.content.decode())["query"][0]


def _sparql(bindings):
    return json.dumps({"results": {"bindings": bindings}}).encode()


def _entity_binding(number):
    uri = f"https://register.ld.admin.ch/zefix/company/{number}"
    return {
        "entity": {"type": "uri", "value": uri},
        "legalName": {"type": "literal", "value": f"Firma {number} AG", "xml:lang": "de"},
        "uid": {"type": "literal", "value": f"CHE{number:09d}"},
    }


class TestRestClient:
    def test_get_by_uid_punctuates_the_uid(self, company_full):
        """The API 404s on an unpunctuated UID, so the client punctuates for you."""
        seen = []

        def handler(request):
            seen.append(request.url.path)
            return httpx.Response(200, json=company_full)

        with _rest_client(handler) as client:
            company = client.get_by_uid("CHE105215703")

        assert seen == ["/ZefixPublicREST/api/v1/company/uid/CHE-105.215.703"]
        assert company.name == "Alpenblick Handel AG"

    def test_unknown_company_is_none(self):
        with _rest_client(lambda request: httpx.Response(404)) as client:
            assert client.get_by_uid("CHE-105.215.703") is None

    def test_get_by_ehraid(self, company_full):
        seen = []

        def handler(request):
            seen.append(request.url.path)
            return httpx.Response(200, json=company_full)

        with _rest_client(handler) as client:
            client.get_by_ehraid(1102345)

        assert seen == ["/ZefixPublicREST/api/v1/company/ehraid/1102345"]

    def test_get_by_chid_normalizes(self, company_full):
        seen = []

        def handler(request):
            seen.append(request.url.path)
            return httpx.Response(200, json=company_full)

        with _rest_client(handler) as client:
            client.get_by_chid("CH-020.3.926.264-8")

        assert seen == ["/ZefixPublicREST/api/v1/company/chid/CH02039262648"]

    def test_search_posts_the_prefix(self, company_full):
        seen = []

        def handler(request):
            seen.append(json.loads(request.content))
            return httpx.Response(200, json=[company_full])

        with _rest_client(handler) as client:
            results = client.search("Alpenblick", max_entries=5)

        assert seen == [
            {"name": "Alpenblick", "activeOnly": True, "maxEntries": 5, "offset": 0}
        ]
        assert len(results) == 1

    def test_sogc_by_date(self, sogc_bydate):
        seen = []

        def handler(request):
            seen.append(request.url.path)
            return httpx.Response(200, json=sogc_bydate)

        with _rest_client(handler) as client:
            publications = client.sogc_by_date(date(2026, 6, 15))

        assert seen == ["/ZefixPublicREST/api/v1/sogc/bydate/2026-06-15"]
        assert len(publications) == 2

    def test_missing_credentials_are_named_in_the_error(self):
        with _rest_client(lambda request: httpx.Response(401)) as client:
            with pytest.raises(AuthenticationError, match="zefix@bj.admin.ch"):
                client.get_by_uid("CHE-105.215.703")

    def test_no_auth_header_without_credentials(self, company_full):
        seen = []

        def handler(request):
            seen.append("authorization" in request.headers)
            return httpx.Response(200, json=company_full)

        with _rest_client(handler, username="", password="") as client:
            client.get_by_uid("CHE-105.215.703")

        assert seen == [False]

    def test_retries_a_server_error_then_succeeds(self, company_full):
        attempts = []

        def handler(request):
            attempts.append(request)
            if len(attempts) < 3:
                return httpx.Response(503)
            return httpx.Response(200, json=company_full)

        with _rest_client(handler, max_retries=3) as client:
            company = client.get_by_uid("CHE-105.215.703")

        assert len(attempts) == 3
        assert company.ehraid == 1102345

    def test_gives_up_after_max_retries(self):
        attempts = []

        def handler(request):
            attempts.append(request)
            return httpx.Response(429)

        with _rest_client(handler, max_retries=2) as client:
            with pytest.raises(RetryableError, match="429"):
                client.get_by_uid("CHE-105.215.703")

        assert len(attempts) == 2

    def test_transport_failures_are_retried(self, company_full):
        attempts = []

        def handler(request):
            attempts.append(request)
            if len(attempts) == 1:
                raise httpx.ConnectError("connection refused")
            return httpx.Response(200, json=company_full)

        with _rest_client(handler, max_retries=2) as client:
            assert client.get_by_uid("CHE-105.215.703") is not None

    def test_a_client_error_is_permanent(self):
        with _rest_client(lambda request: httpx.Response(400)) as client:
            with pytest.raises(TransportError, match="400"):
                client.get_by_uid("CHE-105.215.703")

    def test_rejects_a_zero_retry_budget(self):
        with pytest.raises(ValueError, match="at least 1"):
            ZefixRestClient(max_retries=0)


class TestLindasClient:
    def test_count(self):
        def handler(request):
            body = _sparql([{"count": {"type": "literal", "value": "817234"}}])
            return httpx.Response(200, content=body)

        with _lindas_client(handler) as client:
            assert client.count() == 817234

    def test_query_is_form_encoded(self):
        seen = []

        def handler(request):
            seen.append(_sent_query(request))
            return httpx.Response(200, content=_sparql([]))

        with _lindas_client(handler) as client:
            client.query("SELECT * WHERE { ?s ?p ?o }")

        assert seen == ["SELECT * WHERE { ?s ?p ?o }"]

    def test_iter_entities_walks_every_page(self):
        pages = [
            _sparql([_entity_binding(1), _entity_binding(2)]),
            _sparql([_entity_binding(3)]),
            _sparql([]),
        ]
        cursors = []

        def handler(request):
            cursors.append("FILTER" in _sent_query(request))
            return httpx.Response(200, content=pages[len(cursors) - 1])

        with _lindas_client(handler, page_size=2) as client:
            entities = list(client.iter_entities())

        assert [e.legal_name for e in entities] == [
            "Firma 1 AG",
            "Firma 2 AG",
            "Firma 3 AG",
        ]
        assert cursors == [False, True, True]

    def test_iter_pages_reports_the_cursor_it_used(self):
        pages = [_sparql([_entity_binding(1)]), _sparql([])]
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(200, content=pages[len(calls) - 1])

        with _lindas_client(handler) as client:
            collected = list(client.iter_pages())

        assert [p.page_number for p in collected] == [0, 1]
        assert collected[0].cursor_after == ""
        assert collected[1].cursor_after == "https://register.ld.admin.ch/zefix/company/1"
        assert collected[0].row_count == 1

    def test_a_page_of_only_dropped_entities_still_advances(self):
        """An entity with no identifier is dropped, but the cursor must move past it."""
        unusable = {
            "entity": {
                "type": "uri",
                "value": "https://register.ld.admin.ch/zefix/company/9",
            },
            "legalName": {"type": "literal", "value": "Invalid Entity"},
        }
        pages = [_sparql([unusable]), _sparql([])]
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(200, content=pages[len(calls) - 1])

        with _lindas_client(handler) as client:
            assert list(client.iter_entities()) == []

        assert len(calls) == 2
        assert "company/9" in _sent_query(calls[1])

    def test_resumes_from_a_cursor(self):
        seen = []

        def handler(request):
            seen.append(_sent_query(request))
            return httpx.Response(200, content=_sparql([]))

        with _lindas_client(handler) as client:
            list(client.iter_entities(cursor_after="https://example.org/500"))

        assert "https://example.org/500" in seen[0]

    def test_fetch_by_uids(self):
        seen = []

        def handler(request):
            seen.append(_sent_query(request))
            return httpx.Response(200, content=_sparql([_entity_binding(1)]))

        with _lindas_client(handler) as client:
            entities = client.fetch_by_uids(["CHE-000.000.001"])

        assert "CHE000000001" in seen[0]
        assert len(entities) == 1

    def test_no_uids_means_no_request(self):
        def handler(request):  # pragma: no cover - must never run
            raise AssertionError("should not have been called")

        with _lindas_client(handler) as client:
            assert client.fetch_by_uids([]) == []

    def test_a_malformed_query_is_permanent(self):
        with _lindas_client(lambda request: httpx.Response(400, text="parse error")) as client:
            with pytest.raises(TransportError, match="parse error"):
                client.query("SELECT nonsense")

    def test_rejects_an_out_of_range_page_size(self):
        with pytest.raises(ValueError, match="between 1 and 2000"):
            LindasClient(page_size=5000)
