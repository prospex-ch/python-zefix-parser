"""The eCH-0097 legal-form codes Zefix and SHAB publish, with their names.

Both Swiss registers identify a company's legal form by a four-digit eCH-0097
code rather than by name, and the name itself differs per language: code
``0106`` is an *Aktiengesellschaft*, a *Société anonyme* and a *Società
anonima* depending on where the company is seated. This module is the lookup
table.
"""

from __future__ import annotations

from enum import Enum


class LegalForm(str, Enum):
    """eCH-0097 legal-form codes used by Zefix and SHAB."""

    SOLE_PROPRIETORSHIP = "0101"
    GENERAL_PARTNERSHIP = "0103"
    LIMITED_PARTNERSHIP = "0104"
    PARTNERSHIP_LIMITED_BY_SHARES = "0105"
    CORPORATION = "0106"
    LIMITED_LIABILITY_COMPANY = "0107"
    COOPERATIVE = "0108"
    ASSOCIATION = "0109"
    FOUNDATION = "0110"
    FOREIGN_BRANCH = "0111"
    COLLECTIVE_INVESTMENT_LIMITED_PARTNERSHIP = "0114"
    SICAV = "0115"
    PUBLIC_LAW_INSTITUTE = "0117"
    UNDIVIDED_ESTATE_REPRESENTATIVE = "0119"
    SWISS_BRANCH = "0151"


#: Legal-form names by code, then by language tag.
LEGAL_FORM_LABELS: dict[str, dict[str, str]] = {
    "0101": {
        "de": "Einzelunternehmen",
        "fr": "Entreprise individuelle",
        "it": "Impresa individuale",
        "en": "Sole proprietorship",
    },
    "0103": {
        "de": "Kollektivgesellschaft",
        "fr": "Société en nom collectif",
        "it": "Società in nome collettivo",
        "en": "General partnership",
    },
    "0104": {
        "de": "Kommanditgesellschaft",
        "fr": "Société en commandite",
        "it": "Società in accomandita",
        "en": "Limited partnership",
    },
    "0105": {
        "de": "Kommanditaktiengesellschaft",
        "fr": "Société en commandite par actions",
        "it": "Società in accomandita per azioni",
        "en": "Partnership limited by shares",
    },
    "0106": {
        "de": "Aktiengesellschaft",
        "fr": "Société anonyme",
        "it": "Società anonima",
        "en": "Corporation",
    },
    "0107": {
        "de": "Gesellschaft mit beschränkter Haftung",
        "fr": "Société à responsabilité limitée",
        "it": "Società a garanzia limitata",
        "en": "Limited liability company",
    },
    "0108": {
        "de": "Genossenschaft",
        "fr": "Société coopérative",
        "it": "Società cooperativa",
        "en": "Cooperative",
    },
    "0109": {
        "de": "Verein",
        "fr": "Association",
        "it": "Associazione",
        "en": "Association",
    },
    "0110": {
        "de": "Stiftung",
        "fr": "Fondation",
        "it": "Fondazione",
        "en": "Foundation",
    },
    "0111": {
        "de": "Zweigniederlassung ausländischer Gesellschaft",
        "fr": "Succursale étrangère inscrite au registre du commerce",
        "it": "Succursale estera iscritta nel registro di commercio",
        "en": "Branch of a foreign company",
    },
    "0114": {
        "de": "Kommanditgesellschaft für kollektive Kapitalanlagen",
        "fr": "Société en commandite de placements collectifs",
        "it": "Società in accomandita per investimenti collettivi di capitale",
        "en": "Limited partnership for collective investment",
    },
    "0115": {
        "de": "Investmentgesellschaft mit variablem Kapital (SICAV)",
        "fr": "Société d'investissement à capital variable (SICAV)",
        "it": "Società di investimento a capitale variabile (SICAV)",
        "en": "Investment company with variable capital (SICAV)",
    },
    "0117": {
        "de": "Institut des öffentlichen Rechts",
        "fr": "Institut de droit public",
        "it": "Istituto di diritto pubblico",
        "en": "Public-law institute",
    },
    "0119": {
        "de": "Gemeinderschaft",
        "fr": "Responsable d'indivision",
        "it": "Rappresentante dell'indivisione",
        "en": "Undivided-estate representative",
    },
    "0151": {
        "de": "Zweigniederlassung schweizerischer Gesellschaft",
        "fr": "Succursale suisse inscrite au registre du commerce",
        "it": "Succursale svizzera iscritta nel registro di commercio",
        "en": "Branch of a Swiss company",
    },
}

#: Common abbreviations by code, in the order German / French / Italian.
LEGAL_FORM_ABBREVIATIONS: dict[str, tuple[str, ...]] = {
    "0103": ("KlG", "SNC", "SNC"),
    "0104": ("KmG", "SC", "SAc"),
    "0105": ("KmAG", "SCA", "SAcA"),
    "0106": ("AG", "SA", "SA"),
    "0107": ("GmbH", "Sàrl", "Sagl"),
    "0115": ("SICAV", "SICAV", "SICAV"),
}


def legal_form_name(code: str, lang: str = "de") -> str:
    """The name of legal-form *code* in *lang*, falling back to German.

    Returns ``""`` for a code that is not part of eCH-0097.
    """
    labels = LEGAL_FORM_LABELS.get(str(code).strip())
    if not labels:
        return ""
    return labels.get(lang) or labels["de"]


def legal_form_abbreviation(code: str, lang: str = "de") -> str:
    """The usual abbreviation for *code* in *lang*, or ``""``.

    Only the forms that companies actually carry in their name have one, so
    a foundation or an association returns ``""``.
    """
    abbreviations = LEGAL_FORM_ABBREVIATIONS.get(str(code).strip())
    if not abbreviations:
        return ""
    index = {"de": 0, "fr": 1, "it": 2}.get(lang, 0)
    return abbreviations[index]
