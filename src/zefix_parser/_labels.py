"""Shared text normalization for language-tagged register literals.

Both LINDAS and the REST API return the same company under several language
tags. These helpers pick one deterministically so a given input always parses
to the same output.
"""

from __future__ import annotations

import re

#: Order in which a language-tagged literal is preferred. The empty string is
#: an untagged literal, which the register uses for language-neutral values.
LANGUAGE_PRIORITY = ("de", "fr", "it", "en", "")

_WHITESPACE = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    """*text* with runs of whitespace collapsed to single spaces and stripped."""
    return _WHITESPACE.sub(" ", text or "").strip()


def pick_label(labels: dict[str, str]) -> str:
    """The best label from a ``{language: value}`` mapping, or ``""``."""
    value, _ = pick_label_with_language(labels)
    return value


def pick_label_with_language(labels: dict[str, str]) -> tuple[str, str]:
    """The best label and the language tag it came from, or ``("", "")``."""
    for lang in LANGUAGE_PRIORITY:
        if lang in labels:
            return labels[lang], lang
    if labels:
        lang, value = next(iter(labels.items()))
        return value, lang
    return "", ""
