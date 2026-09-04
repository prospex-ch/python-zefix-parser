"""SPARQL queries and result parsing for the Zefix dataset on LINDAS.

LINDAS is the Swiss federal linked-data service, and it publishes the whole
commercial register as RDF at ``https://ld.admin.ch/query``. No credentials
are needed. Nothing in this module opens a network connection: build a query,
send it however you like, hand the bytes back here.

The dataset has no modification-date predicate, so a server-side delta fetch
is impossible. Pagination runs by keyset over the entity URI, which is what
:func:`build_combined_page_query` builds.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace

from ._labels import normalize_whitespace, pick_label, pick_label_with_language
from .identifiers import normalize_uid
from .schemas import ParserError, RegistryEntity

#: Bumped whenever a query template changes in a way that alters output.
QUERY_VERSION = "1"

PREFIXES = """\
PREFIX schema: <http://schema.org/>
PREFIX admin: <https://schema.ld.admin.ch/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

_ENTITY_FIELDS = """\
SELECT ?entity ?legalName ?name ?uid ?chid ?ehraId
       ?legalFormUri ?legalFormLabel
       ?municipalityUri ?municipalityLabel
       ?canton
       ?streetAddress ?postalCode ?locality
       ?purpose
"""

_ENTITY_PATTERN = """\
  ?entity schema:legalName ?legalName .

  OPTIONAL {{ ?entity schema:name ?name . }}

  OPTIONAL {{
    ?entity schema:identifier ?uidNode .
    ?uidNode schema:name "CompanyUID" ;
             schema:value ?uid .
  }}

  OPTIONAL {{
    ?entity schema:identifier ?chidNode .
    ?chidNode schema:name "CompanyCHID" ;
              schema:value ?chid .
  }}

  OPTIONAL {{
    ?entity schema:identifier ?ehraIdNode .
    ?ehraIdNode schema:name "CompanyEHRAID" ;
                schema:value ?ehraId .
  }}

  OPTIONAL {{
    ?entity schema:additionalType ?legalFormUri .
    OPTIONAL {{ ?legalFormUri (schema:name|rdfs:label) ?legalFormLabel . }}
  }}

  OPTIONAL {{
    ?entity admin:municipality ?municipalityUri .
    ?municipalityUri schema:name ?municipalityLabel .
  }}

  OPTIONAL {{ ?entity schema:address/schema:addressRegion ?canton . }}
  OPTIONAL {{ ?entity schema:address/schema:streetAddress ?streetAddress . }}
  OPTIONAL {{ ?entity schema:address/schema:postalCode ?postalCode . }}
  OPTIONAL {{ ?entity schema:address/schema:addressLocality ?locality . }}

  OPTIONAL {{ ?entity schema:description ?purpose . }}
"""

COUNT_QUERY = """\
{prefixes}
SELECT (COUNT(DISTINCT ?entity) AS ?count) WHERE {{
  ?entity a admin:ZefixOrganisation .
}}
"""

URI_PAGE_QUERY = """\
{prefixes}
SELECT DISTINCT ?entity WHERE {{
  ?entity a admin:ZefixOrganisation .
  {cursor_filter}
}}
ORDER BY STR(?entity)
LIMIT {limit}
"""

DETAIL_QUERY = """\
{prefixes}
{fields}WHERE {{
  VALUES ?entity {{ {entity_uris} }}

  ?entity a admin:ZefixOrganisation .
{pattern}}}
"""

DETAIL_BY_UID_QUERY = """\
{prefixes}
{fields}WHERE {{
  VALUES ?uid {{ {uid_values} }}

  ?uidNode schema:name "CompanyUID" ;
           schema:value ?uid .

  ?entity schema:identifier ?uidNode ;
          a admin:ZefixOrganisation .
{pattern}}}
"""

COMBINED_PAGE_QUERY = """\
{prefixes}
{fields}WHERE {{
  {{
    SELECT DISTINCT ?entity WHERE {{
      ?entity a admin:ZefixOrganisation .
      {cursor_filter}
    }}
    ORDER BY STR(?entity)
    LIMIT {limit}
  }}

{pattern}}}
"""

_LEGAL_FORM_CODE = re.compile(r"/([^/]+)$")
_MUNICIPALITY_ID = re.compile(r"/(\d+)$")


def build_count_query() -> str:
    """A query returning the number of companies in the dataset."""
    return COUNT_QUERY.format(prefixes=PREFIXES)


def build_uri_page_query(*, cursor_after: str | None = None, limit: int = 500) -> str:
    """A query for one keyset page of entity URIs.

    Pass the last URI of the previous page as *cursor_after* to get the next
    page. Omit it for the first page.
    """
    return URI_PAGE_QUERY.format(
        prefixes=PREFIXES,
        cursor_filter=_cursor_filter(cursor_after),
        limit=_limit(limit),
    )


def build_detail_query(entity_uris: list[str]) -> str:
    """A query for the full record of each URI in *entity_uris*."""
    values = " ".join(f"<{_escape_uri(uri)}>" for uri in entity_uris)
    return DETAIL_QUERY.format(
        prefixes=PREFIXES,
        fields=_ENTITY_FIELDS,
        entity_uris=values,
        pattern=_ENTITY_PATTERN.format(),
    )


def build_detail_query_by_uids(uids: list[str]) -> str:
    """A query for the full record of each UID in *uids*.

    LINDAS stores UIDs unpunctuated, so the values are normalized for you.
    ``"CHE-123.456.789"`` and ``"CHE123456789"`` both match.
    """
    values = " ".join(f'"{_escape_literal(normalize_uid(uid))}"' for uid in uids)
    return DETAIL_BY_UID_QUERY.format(
        prefixes=PREFIXES,
        fields=_ENTITY_FIELDS,
        uid_values=values,
        pattern=_ENTITY_PATTERN.format(),
    )


def build_combined_page_query(
    *, cursor_after: str | None = None, limit: int = 500
) -> str:
    """A query for one keyset page of full records, URIs and details in one round trip."""
    return COMBINED_PAGE_QUERY.format(
        prefixes=PREFIXES,
        fields=_ENTITY_FIELDS,
        cursor_filter=_cursor_filter(cursor_after),
        limit=_limit(limit),
        pattern=_ENTITY_PATTERN.format(),
    )


def parse_sparql_json(content: bytes) -> list[dict]:
    """The ``results.bindings`` list of a SPARQL JSON response.

    Raises:
        ParserError: if *content* is not a SPARQL JSON results document.
    """
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as exc:
        raise ParserError(f"invalid SPARQL JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ParserError("SPARQL response is not an object")

    results = data.get("results")
    if not isinstance(results, dict):
        raise ParserError("SPARQL response has no 'results' object")

    bindings = results.get("bindings")
    if not isinstance(bindings, list):
        raise ParserError("SPARQL results have no 'bindings' list")

    return bindings


def parse_count(content: bytes) -> int | None:
    """The integer answer to :func:`build_count_query`, or ``None``."""
    bindings = parse_sparql_json(content)
    if not bindings:
        return None
    value = _binding_value(bindings[0].get("count"))
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_uri_page(content: bytes) -> list[str]:
    """The entity URIs of a :func:`build_uri_page_query` response, deduplicated."""
    uris: list[str] = []
    seen: set[str] = set()
    for row in parse_sparql_json(content):
        uri = _binding_value(row.get("entity"))
        if uri and uri not in seen:
            uris.append(uri)
            seen.add(uri)
    return uris


def parse_entity_page(content: bytes) -> list[RegistryEntity]:
    """The companies in a detail or combined-page response.

    One company spans several rows, one per language-tagged literal, so rows
    are grouped by entity URI and folded down. Entities lacking a legal name,
    or carrying neither a UID nor an EHRAID, are dropped: there is nothing to
    match them against, and the register emits a few.
    """
    grouped: dict[str, list[dict]] = {}
    for row in parse_sparql_json(content):
        uri = _binding_value(row.get("entity"))
        if uri:
            grouped.setdefault(uri, []).append(row)

    entities = []
    for uri, rows in grouped.items():
        entity = _group_entity(uri, rows)
        if entity is not None:
            entities.append(entity)
    return entities


def _cursor_filter(cursor_after: str | None) -> str:
    if not cursor_after:
        return ""
    return f'FILTER (STR(?entity) > "{_escape_literal(cursor_after)}")'


def _limit(limit: int) -> int:
    if limit < 1:
        raise ValueError(f"limit must be at least 1, got {limit!r}")
    return int(limit)


def _escape_literal(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def _escape_uri(uri: str) -> str:
    if any(char in uri for char in '<>"{}|^`\\ \n\r'):
        raise ValueError(f"entity URI contains an illegal character: {uri!r}")
    return uri


def _binding_value(binding: dict | None) -> str | None:
    if not binding:
        return None
    value = binding.get("value")
    if value is None or value == "":
        return None
    return str(value)


def _binding_language(binding: dict | None) -> str:
    if not binding:
        return ""
    return binding.get("xml:lang", "")


def _group_entity(uri: str, rows: list[dict]) -> RegistryEntity | None:
    uid = chid = ehra_id = ""
    legal_names: dict[str, str] = {}
    legal_form_labels: dict[str, str] = {}
    municipality_labels: dict[str, str] = {}
    purposes: dict[str, str] = {}
    alternate_names: set[str] = set()
    legal_form_codes: set[str] = set()
    municipality_ids: set[str] = set()
    cantons: set[str] = set()
    street_addresses: set[str] = set()
    postal_codes: set[str] = set()
    localities: set[str] = set()

    for row in rows:
        uid = uid or _binding_value(row.get("uid")) or ""
        chid = chid or _binding_value(row.get("chid")) or ""
        ehra_id = ehra_id or _binding_value(row.get("ehraId")) or ""

        legal_name = _binding_value(row.get("legalName"))
        if legal_name:
            legal_names[_binding_language(row.get("legalName"))] = normalize_whitespace(
                legal_name
            )

        name = _binding_value(row.get("name"))
        if name:
            alternate_names.add(normalize_whitespace(name))

        legal_form_uri = _binding_value(row.get("legalFormUri"))
        if legal_form_uri:
            code = _code_from_uri(legal_form_uri, _LEGAL_FORM_CODE)
            if code:
                legal_form_codes.add(code)
            label = _binding_value(row.get("legalFormLabel"))
            if label:
                legal_form_labels[_binding_language(row.get("legalFormLabel"))] = label

        municipality_uri = _binding_value(row.get("municipalityUri"))
        if municipality_uri:
            municipality_id = _code_from_uri(municipality_uri, _MUNICIPALITY_ID)
            if municipality_id:
                municipality_ids.add(municipality_id)
            label = _binding_value(row.get("municipalityLabel"))
            if label:
                municipality_labels[_binding_language(row.get("municipalityLabel"))] = (
                    label
                )

        canton = _binding_value(row.get("canton"))
        if canton:
            cantons.add(canton.strip().upper()[:2])

        street_address = _binding_value(row.get("streetAddress"))
        if street_address:
            street_addresses.add(normalize_whitespace(street_address))

        postal_code = _binding_value(row.get("postalCode"))
        if postal_code:
            postal_codes.add(postal_code.strip())

        locality = _binding_value(row.get("locality"))
        if locality:
            localities.add(normalize_whitespace(locality))

        purpose = _binding_value(row.get("purpose"))
        if purpose:
            purposes[_binding_language(row.get("purpose"))] = normalize_whitespace(
                purpose
            )

    legal_name = pick_label(legal_names)
    if not legal_name:
        return None
    if not uid and not ehra_id:
        return None

    every_name = set(legal_names.values()) | alternate_names
    every_name.discard(legal_name)

    purpose, purpose_language = pick_label_with_language(purposes)
    entity = RegistryEntity(
        zefix_uri=uri,
        uid=uid,
        chid=chid,
        ehra_id=ehra_id,
        legal_name=legal_name,
        alternate_names=sorted(every_name),
        legal_form_code=_first(legal_form_codes),
        legal_form_name=pick_label(legal_form_labels),
        municipality_id=_first(municipality_ids),
        municipality_name=pick_label(municipality_labels),
        canton=_first(cantons),
        street_address=_first(street_addresses),
        postal_code=_first(postal_codes),
        locality=_first(localities),
        purpose=purpose,
        purpose_language=purpose_language,
    )
    return replace(entity, fingerprint=compute_fingerprint(entity))


def compute_fingerprint(entity: RegistryEntity) -> str:
    """A stable digest of the fields that describe *entity* itself.

    Two fetches of an unchanged company produce the same value, so you can
    skip the write. The digest covers the descriptive fields only: ``chid``,
    ``ehra_id`` and ``alternate_names`` sit outside it.
    """
    identity = {
        "uri": entity.zefix_uri,
        "uid": normalize_uid(entity.uid) if entity.uid else "",
        "legal_name": entity.legal_name,
        "legal_form_code": entity.legal_form_code,
        "legal_form_name": entity.legal_form_name,
        "municipality_id": entity.municipality_id,
        "canton": entity.canton,
        "street_address": entity.street_address,
        "postal_code": entity.postal_code,
        "locality": entity.locality,
        "purpose": entity.purpose,
    }
    canonical = json.dumps(identity, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _code_from_uri(uri: str, pattern: re.Pattern) -> str:
    match = pattern.search(uri)
    return match.group(1) if match else ""


def _first(values: set[str]) -> str:
    return sorted(values)[0] if values else ""
