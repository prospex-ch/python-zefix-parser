"""Swiss company identifiers: the UID, the CHID and the EHRAID.

Every Swiss company carries a UID (Unternehmens-Identifikationsnummer,
``CHE-123.456.789``), and Zefix stores it three different ways depending on
where you read it: LINDAS returns it unpunctuated, the PublicREST API requires
it punctuated, and free-text sources hide it inside a longer string. These
helpers convert between the forms and validate the check digit.
"""

from __future__ import annotations

import re

_NON_ALPHANUMERIC = re.compile(r"[^A-Za-z0-9]")
_UID = re.compile(r"^CHE(\d{3})(\d{3})(\d{3})$")
_UID_IN_TEXT = re.compile(r"CHE\d{9}")
_CHID = re.compile(r"^CH(\d{3})(\d{1})(\d{3})(\d{3})(\d{1})$")

#: Weights of the UID check digit, ISO 7064 mod 11-10 as the Federal
#: Statistical Office specifies it.
UID_WEIGHTS = (5, 4, 3, 2, 7, 6, 5, 4)


def normalize_uid(uid: str) -> str:
    """*uid* with punctuation removed and uppercased: ``"CHE123456789"``.

    Does not validate. Use this as an index key, and :func:`is_valid_uid` to
    decide whether the value is a real UID.
    """
    return _NON_ALPHANUMERIC.sub("", uid or "").upper()


def format_uid(uid: str) -> str:
    """*uid* in the punctuated form ``"CHE-123.456.789"``.

    This is the form the PublicREST API expects in its path; passing the
    unpunctuated form returns 404. Values that are not nine digits behind a
    ``CHE`` prefix are returned normalized but unchanged.
    """
    normalized = normalize_uid(uid)
    match = _UID.match(normalized)
    if not match:
        return normalized
    return f"CHE-{match.group(1)}.{match.group(2)}.{match.group(3)}"


def clean_uid(value: str) -> str:
    """The first UID embedded anywhere in *value*, or ``""``.

    For free-text fields that wrap the UID in other content, such as
    ``"VAT: CHE-109.807.630 MWST"``.
    """
    match = _UID_IN_TEXT.search(normalize_uid(value))
    return match.group(0) if match else ""


def is_valid_uid(uid: str) -> bool:
    """Whether *uid* is a ``CHE`` number with a valid check digit.

    A mistyped UID can never match the register, so it is worth rejecting
    before you spend a request on it. Placeholders such as ``CHE123456789``
    fail this check, which is usually what you want.
    """
    normalized = normalize_uid(uid)
    if not _UID.match(normalized):
        return False
    return uid_check_digit_ok(normalized[3:])


def uid_check_digit_ok(digits: str) -> bool:
    """Whether nine digits carry a valid UID check digit."""
    if len(digits) != 9 or not digits.isdigit():
        return False
    total = sum(int(digit) * weight for digit, weight in zip(digits, UID_WEIGHTS))
    check = 11 - (total % 11)
    if check == 10:
        return False
    return int(digits[8]) == (0 if check == 11 else check)


def normalize_chid(chid: str) -> str:
    """*chid* with punctuation removed and uppercased: ``"CH12345678901"``."""
    return _NON_ALPHANUMERIC.sub("", chid or "").upper()


def format_chid(chid: str) -> str:
    """*chid* in the punctuated form ``"CH-123.4.567.890-1"``.

    The CHID is the older cantonal register number that Zefix still returns
    alongside the UID. Values that are not eleven digits behind a ``CH``
    prefix are returned normalized but unchanged.
    """
    normalized = normalize_chid(chid)
    match = _CHID.match(normalized)
    if not match:
        return normalized
    register, office, first, second, check = match.groups()
    return f"CH-{register}.{office}.{first}.{second}-{check}"
