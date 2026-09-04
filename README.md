# zefix-parser

[![PyPI](https://img.shields.io/pypi/v/zefix-parser)](https://pypi.org/project/zefix-parser/)
[![Documentation](https://readthedocs.org/projects/zefix-parser/badge/?version=latest)](https://zefix-parser.readthedocs.io/en/latest/)

Typed Python client for Zefix, the Swiss Central Business Name Index (Zentraler Firmenindex).

Covers both ways into the register: the open [LINDAS](https://lindas.admin.ch) SPARQL
dataset, which carries every company in Switzerland and needs no credentials, and the
[Zefix PublicREST API](https://www.zefix.admin.ch), which adds share capital, legal status,
auditors and corporate relations. Responses parse into plain dataclasses.

Built and maintained by [Prospex](https://prospex.ch), a Swiss B2B sales intelligence platform.

## Install

```bash
pip install zefix-parser
```

To use the HTTP clients (for fetching from the live endpoints):

```bash
pip install zefix-parser[http]
```

## Quick start

### Read the register from LINDAS

No credentials needed.

```python
from zefix_parser.client import LindasClient

with LindasClient() as client:
    print(client.count())  # 812,000 or so

    for entity in client.iter_entities():
        print(entity.legal_name, entity.uid, entity.canton, entity.legal_form_code)
```

Or look up companies you already have UIDs for, in one request:

```python
from zefix_parser.client import LindasClient

with LindasClient() as client:
    entities = client.fetch_by_uids(["CHE-105.215.703", "CHE-411.462.297"])

for entity in entities:
    print(entity.legal_name)   # "Alpenblick Handel AG"
    print(entity.purpose)      # "Handel mit Waren aller Art"
    print(entity.municipality_name, entity.canton)
```

### Fetch details from the PublicREST API

The REST API is gated behind HTTP Basic auth. Credentials are issued on request by
`zefix@bj.admin.ch`.

```python
from zefix_parser.client import ZefixRestClient

with ZefixRestClient(username="...", password="...") as client:
    company = client.get_by_uid("CHE-105.215.703")

print(company.name)             # "Alpenblick Handel AG"
print(company.capital_nominal)  # Decimal("250000.00")
print(company.status)           # "ACTIVE"

for auditor in company.audit_companies:
    print(auditor.name, auditor.legal_seat)
```

Both clients rate-limit themselves to one request every half second and retry transient
failures with exponential backoff.

### Parse responses you already have

Every parser is importable without the `http` extra, so you can point them at recorded
responses or use your own HTTP library:

```python
from zefix_parser import parse_company, parse_entity_page

company = parse_company(rest_json)          # a dict from the REST API
entities = parse_entity_page(sparql_bytes)  # a SPARQL JSON results document
```

## The two access paths

|  | LINDAS | PublicREST |
|---|---|---|
| Endpoint | `https://ld.admin.ch/query` | `https://www.zefix.admin.ch/ZefixPublicREST/api/v1` |
| Credentials | none | HTTP Basic |
| Shape | the whole register, keyset-paginated | one company per request |
| Carries | name, legal form, address, canton, purpose | the above plus capital, status, auditors, branches, mergers, former names |
| Class | `RegistryEntity` | `Company` |

LINDAS has no modification-date predicate, so a server-side delta fetch is impossible: you
either walk the whole register or drive updates from another change feed, such as
[SHAB publications](https://shab-parser.readthedocs.io).

## Data model

`parse_entity_page()` returns `RegistryEntity` objects:

```python
@dataclass(frozen=True)
class RegistryEntity:
    zefix_uri: str
    uid: str                     # CHE123456789, unpunctuated
    chid: str
    ehra_id: str
    legal_name: str
    alternate_names: list[str]   # the other language variants
    legal_form_code: str         # eCH-0097, e.g. "0106"
    legal_form_name: str
    municipality_id: str         # federal municipality number
    municipality_name: str
    canton: str
    street_address: str
    postal_code: str
    locality: str
    purpose: str
    purpose_language: str
    fingerprint: str             # SHA-256 over the identity fields
```

`parse_company()` returns `Company` objects:

```python
@dataclass(frozen=True)
class Company:
    name: str
    ehraid: int
    uid: str
    chid: str
    canton: str
    status: str                  # "ACTIVE", "IN_LIQUIDATION", "DELETED"
    capital_nominal: Decimal | None
    capital_currency: str
    deletion_date: date | None
    cantonal_excerpt_web: str
    head_offices: list[RelatedEntity]
    further_head_offices: list[RelatedEntity]
    branch_offices: list[RelatedEntity]
    has_taken_over: list[RelatedEntity]
    was_taken_over_by: list[RelatedEntity]
    audit_companies: list[RelatedEntity]
    old_names: list[OldName]
```

## Identifiers

The same UID appears in three forms depending on where you read it, so the library
converts between them:

```python
from zefix_parser import clean_uid, format_uid, is_valid_uid, normalize_uid

normalize_uid("CHE-105.215.703")            # "CHE105215703"  (LINDAS form)
format_uid("CHE105215703")                  # "CHE-105.215.703"  (REST form)
clean_uid("VAT: CHE-109.807.630 MWST")      # "CHE109807630"
is_valid_uid("CHE123456789")                # False - the check digit fails
```

`is_valid_uid()` runs the ISO 7064 mod 11-10 check digit. It is worth calling before you
spend a request: a mistyped UID can never match the register, and the register's own
placeholder `CHE123456789` fails it.

## Legal forms

Both registers identify a legal form by its four-digit eCH-0097 code, and the name differs
by language:

```python
from zefix_parser import LegalForm, legal_form_abbreviation, legal_form_name

LegalForm.CORPORATION                    # "0106"
legal_form_name("0106", "de")            # "Aktiengesellschaft"
legal_form_name("0106", "fr")            # "Société anonyme"
legal_form_name("0106", "it")            # "Società anonima"
legal_form_abbreviation("0107", "fr")    # "Sàrl"
```

The full table is in the [legal forms reference](https://zefix-parser.readthedocs.io/en/latest/legal-forms.html).

## Former names

The register re-typesets a company's name whenever anything else about it changes, so
`company.old_names` fills up with entries that differ from the current name only in casing
or spacing: "QualiCasa AG" against "Qualicasa AG". Apply them and you retire the company's
live name. `meaningful_old_names()` drops them:

```python
from zefix_parser import meaningful_old_names

for old in meaningful_old_names(company):
    print(old.sequence_nr, old.name)   # only the genuine renames, oldest first
```

## API reference

### `zefix_parser.parse_entity_page(content: bytes) -> list[RegistryEntity]`

Parse a SPARQL JSON results document into companies. One company spans several rows, one
per language-tagged literal; rows are grouped by entity URI and folded down to a single
deterministic value per field.

### `zefix_parser.parse_company(data: dict | list) -> Company`

Parse one `/company/...` response. The API is inconsistent about whether a single company
comes back as an object or a one-element list; both work.

### `zefix_parser.build_combined_page_query(*, cursor_after=None, limit=500) -> str`

Build the SPARQL query for one keyset page of full records. Use this to run the crawl
yourself, outside `LindasClient`.

### `zefix_parser.client.LindasClient`

SPARQL client. `count()`, `iter_entities()`, `iter_pages()` (which yields `RawPage` objects
carrying the cursor, so a crawl can be resumed), `fetch_by_uids()`, `query()`.

### `zefix_parser.client.ZefixRestClient`

PublicREST client. `get_by_uid()`, `get_by_ehraid()`, `get_by_chid()`, `search()`,
`sogc_by_date()`, `sogc()`.

## Background

Zefix (the Zentraler Firmenindex, *index central des raisons de commerce*, *indice centrale
delle ditte*, officially the Swiss Central Business Name Index) is the federal index over
the 26 cantonal commercial registers: Handelsregister, registre du commerce, registro di
commercio. Every company registered in Switzerland appears in it, identified by a UID
(`CHE-123.456.789`), a CHID and an EHRAID.

The Federal Office of Justice publishes the index twice. LINDAS carries every company as
linked data, open to anyone, holding each company's current state. The PublicREST API holds
more per company, behind credentials, and answers one lookup at a time. Neither publishes a
change feed; for that you need the gazette, which is what
[shab-parser](https://shab-parser.readthedocs.io) reads.

## License

MIT
