"""Parse responses from the Zefix PublicREST API.

The API returns JSON with camelCase keys; these functions turn it into the
dataclasses in :mod:`zefix_parser.schemas`. Nothing here opens a network
connection, so you can use it with any HTTP library, or with a recorded
response.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from ._labels import normalize_whitespace
from .schemas import Company, OldName, ParserError, RelatedEntity, SogcPublication

PARSER_VERSION = "zefix-parser/0.1.0"

_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)


def parse_company(data: dict | list) -> Company:
    """Parse one ``/company/...`` response into a :class:`~zefix_parser.Company`.

    The API returns a single company as an object from some endpoints and as
    a one-element list from others. Both are accepted.

    Raises:
        ParserError: if *data* is neither of those shapes.
    """
    record = _single(data)
    return Company(
        name=record.get("name", "") or "",
        ehraid=_to_int(record.get("ehraid")),
        uid=record.get("uid", "") or "",
        chid=record.get("chid", "") or "",
        canton=record.get("canton", "") or "",
        status=record.get("status", "") or "",
        capital_nominal=_to_decimal(record.get("capitalNominal")),
        capital_currency=record.get("capitalCurrency") or "CHF",
        deletion_date=_to_date(record.get("deletionDate")),
        cantonal_excerpt_web=record.get("cantonalExcerptWeb", "") or "",
        head_offices=_parse_relations(record.get("headOffices")),
        further_head_offices=_parse_relations(record.get("furtherHeadOffices")),
        branch_offices=_parse_relations(record.get("branchOffices")),
        has_taken_over=_parse_relations(record.get("hasTakenOver")),
        was_taken_over_by=_parse_relations(record.get("wasTakenOverBy")),
        audit_companies=_parse_relations(record.get("auditCompanies")),
        old_names=_parse_old_names(record.get("oldNames")),
    )


def parse_companies(data: list | dict) -> list[Company]:
    """Parse a ``/company/search`` response into a list of companies."""
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ParserError(f"expected a list of companies, got {type(data).__name__}")
    return [parse_company(item) for item in data if isinstance(item, dict)]


def parse_sogc(data: dict | list) -> SogcPublication:
    """Parse one ``/sogc/...`` response into a :class:`~zefix_parser.SogcPublication`."""
    record = _single(data)
    return SogcPublication(
        sogc_id=_to_int(record.get("sogcId") or record.get("id")),
        publication_date=_to_date(record.get("sogcDate") or record.get("publicationDate")),
        name=record.get("name", "") or "",
        uid=record.get("uid", "") or "",
        ehraid=_to_int(record.get("ehraid")),
        canton=record.get("canton", "") or "",
        mutation_type_id=_to_int(record.get("mutationTypeId")),
        mutation_type=record.get("mutationTypeText") or record.get("mutationType") or "",
        message=record.get("message", "") or "",
    )


def parse_sogc_list(data: list | dict) -> list[SogcPublication]:
    """Parse a ``/sogc/bydate/...`` response into a list of publications."""
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ParserError(f"expected a list of publications, got {type(data).__name__}")
    return [parse_sogc(item) for item in data if isinstance(item, dict)]


def meaningful_old_names(company: Company) -> list[OldName]:
    """The entries of ``company.old_names`` that are real former names.

    The register re-typesets a name whenever anything else about the company
    changes, so ``oldNames`` fills up with entries that differ from the current
    name only in casing, punctuation or spacing: "QualiCasa AG" against
    "Qualicasa AG". Apply those and you retire the company's live name. This
    drops them, along with duplicates, and returns the rest oldest first.
    """
    current = normalize_name(company.name)
    seen: set[str] = set()
    kept = []
    for old_name in sorted(company.old_names, key=lambda n: n.sequence_nr):
        normalized = normalize_name(old_name.name)
        if not normalized or normalized == current or normalized in seen:
            continue
        seen.add(normalized)
        kept.append(old_name)
    return kept


def normalize_name(name: str) -> str:
    """*name* casefolded with punctuation and extra whitespace removed.

    The comparison key behind :func:`meaningful_old_names`.
    """
    stripped = _PUNCTUATION.sub(" ", name or "")
    return normalize_whitespace(stripped).casefold()


def _single(data: dict | list) -> dict:
    if isinstance(data, list):
        if not data:
            raise ParserError("expected a record, got an empty list")
        data = data[0]
    if not isinstance(data, dict):
        raise ParserError(f"expected a record, got {type(data).__name__}")
    return data


def _parse_relations(items: list | None) -> list[RelatedEntity]:
    if not items:
        return []
    relations = []
    for item in items:
        if not isinstance(item, dict):
            continue
        ehraid = _to_int(item.get("ehraid"))
        if not ehraid:
            continue
        relations.append(
            RelatedEntity(
                name=item.get("name", "") or "",
                ehraid=ehraid,
                uid=item.get("uid", "") or "",
                chid=item.get("chid", "") or "",
                legal_seat=item.get("legalSeat", "") or "",
                status=item.get("status", "") or "",
            )
        )
    return relations


def _parse_old_names(items: list | None) -> list[OldName]:
    if not items:
        return []
    return [
        OldName(
            name=normalize_whitespace(item["name"]),
            sequence_nr=_to_int(item.get("sequenceNr")),
        )
        for item in items
        if isinstance(item, dict) and item.get("name")
    ]


def _to_int(value: object) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _to_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _to_date(value: object) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
