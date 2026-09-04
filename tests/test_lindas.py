import pytest

from zefix_parser import (
    ParserError,
    build_combined_page_query,
    build_count_query,
    build_detail_query,
    build_detail_query_by_uids,
    build_uri_page_query,
    compute_fingerprint,
    parse_count,
    parse_entity_page,
    parse_sparql_json,
    parse_uri_page,
)


class TestQueryBuilders:
    def test_count_query(self):
        query = build_count_query()
        assert "COUNT(DISTINCT ?entity)" in query
        assert "admin:ZefixOrganisation" in query

    def test_first_page_has_no_cursor_filter(self):
        assert "FILTER" not in build_uri_page_query(limit=10)

    def test_later_page_filters_on_the_cursor(self):
        query = build_uri_page_query(cursor_after="https://example.org/1", limit=10)
        assert 'FILTER (STR(?entity) > "https://example.org/1")' in query

    def test_cursor_quotes_are_escaped(self):
        """A cursor is interpolated into a SPARQL literal, so it must be escaped."""
        query = build_uri_page_query(cursor_after='x" ) || (1=1) FILTER ("')
        assert 'FILTER (STR(?entity) > "x\\" ) || (1=1) FILTER (\\"")' in query

    def test_rejects_zero_limit(self):
        with pytest.raises(ValueError, match="at least 1"):
            build_uri_page_query(limit=0)

    def test_detail_query_lists_the_uris(self):
        query = build_detail_query(["https://example.org/1", "https://example.org/2"])
        assert "VALUES ?entity { <https://example.org/1> <https://example.org/2> }" in query

    def test_detail_query_rejects_a_broken_uri(self):
        with pytest.raises(ValueError, match="illegal character"):
            build_detail_query(["https://example.org/a b"])

    def test_uid_query_normalizes(self):
        """LINDAS stores UIDs unpunctuated, so punctuated input has to be cleaned."""
        query = build_detail_query_by_uids(["CHE-105.215.703"])
        assert 'VALUES ?uid { "CHE105215703" }' in query

    def test_combined_page_query_is_one_round_trip(self):
        query = build_combined_page_query(limit=50)
        assert "SELECT DISTINCT ?entity" in query
        assert "?legalName" in query
        assert "LIMIT 50" in query


class TestParseSparqlJson:
    def test_returns_bindings(self, count_json):
        assert len(parse_sparql_json(count_json)) == 1

    def test_rejects_non_json(self):
        with pytest.raises(ParserError, match="invalid SPARQL JSON"):
            parse_sparql_json(b"<html>nope</html>")

    def test_rejects_a_json_array(self):
        with pytest.raises(ParserError, match="not an object"):
            parse_sparql_json(b"[]")

    def test_rejects_a_document_without_results(self):
        with pytest.raises(ParserError, match="no 'results' object"):
            parse_sparql_json(b'{"head": {}}')

    def test_rejects_results_without_bindings(self):
        with pytest.raises(ParserError, match="no 'bindings' list"):
            parse_sparql_json(b'{"results": {}}')


class TestParseCount:
    def test_reads_the_typed_literal(self, count_json):
        assert parse_count(count_json) == 5

    def test_empty_result(self):
        assert parse_count(b'{"results": {"bindings": []}}') is None


class TestParseUriPage:
    def test_lists_the_uris(self, uris_page_1_json):
        uris = parse_uri_page(uris_page_1_json)
        assert len(uris) == 5
        assert uris[0] == "https://register.ld.admin.ch/zefix/company/1"

    def test_exhausted_page(self, uris_page_2_json):
        assert parse_uri_page(uris_page_2_json) == []


class TestParseEntityPage:
    def test_drops_the_entity_with_no_identifier(self, entities_json):
        """An entity with neither a UID nor an EHRAID cannot be matched to anything."""
        entities = parse_entity_page(entities_json)
        assert len(entities) == 4
        assert "Invalid Entity" not in {e.legal_name for e in entities}

    def test_prefers_the_german_legal_name(self, entities_json):
        entity = self._by_uid(entities_json, "CHE123456789")
        assert entity.legal_name == "Müller & Söhne AG"

    def test_other_language_variants_become_alternate_names(self, entities_json):
        entity = self._by_uid(entities_json, "CHE123456789")
        assert entity.alternate_names == ["Müller et Fils SA"]

    def test_falls_back_to_french_when_there_is_no_german(self, entities_json):
        entity = self._by_uid(entities_json, "CHE987654321")
        assert entity.legal_name == "Boulangerie du Lac Sàrl"
        assert entity.legal_form_name == "Société à responsabilité limitée"

    def test_legal_form_code_comes_from_the_uri_tail(self, entities_json):
        assert self._by_uid(entities_json, "CHE123456789").legal_form_code == "0106"
        assert self._by_uid(entities_json, "CHE987654321").legal_form_code == "0107"

    def test_address_and_municipality(self, entities_json):
        entity = self._by_uid(entities_json, "CHE123456789")
        assert entity.canton == "ZH"
        assert entity.street_address == "Bahnhofstrasse 10"
        assert entity.postal_code == "8001"
        assert entity.municipality_id == "261"
        assert entity.municipality_name == "Zürich"

    def test_purpose_keeps_its_language(self, entities_json):
        entity = self._by_uid(entities_json, "CHE123456789")
        assert entity.purpose == "Handel mit Waren aller Art"
        assert entity.purpose_language == "de"

    def test_an_entity_with_only_an_ehraid_survives(self, entities_json):
        entities = {e.legal_name: e for e in parse_entity_page(entities_json)}
        cooperative = entities["Genossenschaft Alpkäse"]
        assert cooperative.uid == ""
        assert cooperative.ehra_id == "400004"

    def test_parsing_is_deterministic(self, entities_json):
        first = parse_entity_page(entities_json)
        second = parse_entity_page(entities_json)
        assert [e.fingerprint for e in first] == [e.fingerprint for e in second]

    def test_empty_page(self, uris_page_2_json):
        assert parse_entity_page(uris_page_2_json) == []

    def _by_uid(self, content, uid):
        return next(e for e in parse_entity_page(content) if e.uid == uid)


class TestFingerprint:
    def test_changes_when_the_company_does(self, entities_json):
        from dataclasses import replace

        entity = parse_entity_page(entities_json)[0]
        moved = replace(entity, street_address="Seestrasse 1")
        assert compute_fingerprint(moved) != compute_fingerprint(entity)

    def test_ignores_alternate_names(self, entities_json):
        """Alternate names are not part of the company's identity."""
        from dataclasses import replace

        entity = parse_entity_page(entities_json)[0]
        renamed = replace(entity, alternate_names=["Something Else SA"])
        assert compute_fingerprint(renamed) == compute_fingerprint(entity)

    def test_uid_punctuation_does_not_matter(self, entities_json):
        from dataclasses import replace

        entity = parse_entity_page(entities_json)[0]
        punctuated = replace(entity, uid="CHE-123.456.789")
        assert compute_fingerprint(punctuated) == compute_fingerprint(entity)
