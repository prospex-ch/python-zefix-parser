"""Data contracts for parsed Zefix records.

Plain dataclasses with no external dependencies. The two access paths return
different shapes: LINDAS yields :class:`RegistryEntity` (the open baseline
record) and the PublicREST API yields :class:`Company` (the authenticated
detail record, which adds capital, status and corporate relations).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class CompanyStatus(str, Enum):
    """Legal status as reported by the PublicREST API."""

    ACTIVE = "ACTIVE"
    IN_LIQUIDATION = "IN_LIQUIDATION"
    DELETED = "DELETED"


class RelationType(str, Enum):
    """Kinds of corporate relation the REST detail record carries."""

    HEAD_OFFICE = "head_office"
    FURTHER_HEAD_OFFICE = "further_head_office"
    BRANCH_OFFICE = "branch_office"
    HAS_TAKEN_OVER = "has_taken_over"
    WAS_TAKEN_OVER_BY = "was_taken_over_by"
    AUDITOR = "auditor"


class Language(str, Enum):
    """Languages the register publishes labels in."""

    DE = "de"
    FR = "fr"
    IT = "it"
    EN = "en"


@dataclass(frozen=True)
class RegistryEntity:
    """One company as published on LINDAS.

    Multi-valued and language-tagged predicates are already folded down to a
    single deterministic value per field; see :func:`zefix_parser.parse_entity_page`.
    """

    zefix_uri: str
    uid: str
    chid: str
    ehra_id: str
    legal_name: str
    alternate_names: list[str] = field(default_factory=list)
    legal_form_code: str = ""
    legal_form_name: str = ""
    municipality_id: str = ""
    municipality_name: str = ""
    canton: str = ""
    street_address: str = ""
    postal_code: str = ""
    locality: str = ""
    purpose: str = ""
    purpose_language: str = ""
    fingerprint: str = ""


@dataclass(frozen=True)
class RelatedEntity:
    """A company reference inside a relationship field (auditor, branch, ...)."""

    name: str
    ehraid: int
    uid: str = ""
    chid: str = ""
    legal_seat: str = ""
    status: str = ""


@dataclass(frozen=True)
class OldName:
    """A superseded company name, oldest first by ``sequence_nr``."""

    name: str
    sequence_nr: int


@dataclass(frozen=True)
class Company:
    """One company as returned by the Zefix PublicREST API."""

    name: str
    ehraid: int
    uid: str = ""
    chid: str = ""
    canton: str = ""
    status: str = ""
    capital_nominal: Decimal | None = None
    capital_currency: str = "CHF"
    deletion_date: date | None = None
    cantonal_excerpt_web: str = ""
    head_offices: list[RelatedEntity] = field(default_factory=list)
    further_head_offices: list[RelatedEntity] = field(default_factory=list)
    branch_offices: list[RelatedEntity] = field(default_factory=list)
    has_taken_over: list[RelatedEntity] = field(default_factory=list)
    was_taken_over_by: list[RelatedEntity] = field(default_factory=list)
    audit_companies: list[RelatedEntity] = field(default_factory=list)
    old_names: list[OldName] = field(default_factory=list)


@dataclass(frozen=True)
class SogcPublication:
    """A SOGC/SHAB publication reference as returned by the ``/sogc`` endpoints."""

    sogc_id: int
    publication_date: date | None = None
    name: str = ""
    uid: str = ""
    ehraid: int = 0
    canton: str = ""
    mutation_type_id: int = 0
    mutation_type: str = ""
    message: str = ""


@dataclass(frozen=True)
class RawPage:
    """One SPARQL response with the provenance needed to replay it."""

    page_number: int
    cursor_after: str
    content: bytes
    content_type: str
    fetched_at: datetime
    row_count: int


class ZefixError(Exception):
    """Base class for every error this library raises."""


class ParserError(ZefixError):
    """A response could not be parsed into the expected shape."""


class TransportError(ZefixError):
    """An HTTP request failed and will not succeed on retry."""


class RetryableError(TransportError):
    """An HTTP request failed transiently and may succeed on retry."""


class AuthenticationError(TransportError):
    """The PublicREST API rejected the credentials, or none were supplied."""
