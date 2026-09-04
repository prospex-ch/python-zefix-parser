import pytest

from zefix_parser import (
    clean_uid,
    format_chid,
    format_uid,
    is_valid_uid,
    normalize_chid,
    normalize_uid,
    uid_check_digit_ok,
)


class TestNormalizeUid:
    def test_strips_punctuation(self):
        assert normalize_uid("CHE-105.215.703") == "CHE105215703"

    def test_uppercases(self):
        assert normalize_uid("che-105.215.703") == "CHE105215703"

    def test_empty(self):
        assert normalize_uid("") == ""


class TestFormatUid:
    def test_punctuates(self):
        assert format_uid("CHE105215703") == "CHE-105.215.703"

    def test_idempotent(self):
        assert format_uid("CHE-105.215.703") == "CHE-105.215.703"

    def test_leaves_non_uid_alone(self):
        """Anything that is not CHE plus nine digits comes back normalized only."""
        assert format_uid("CHE-105.215") == "CHE105215"


class TestCleanUid:
    def test_extracts_from_free_text(self):
        assert clean_uid("VAT: CHE-109.807.630 MWST") == "CHE109807630"

    def test_no_uid(self):
        assert clean_uid("+41 44 273 16 38") == ""


class TestIsValidUid:
    def test_real_uid(self):
        assert is_valid_uid("CHE-105.215.703")

    def test_placeholder_fails(self):
        """CHE123456789 is the placeholder the register itself emits."""
        assert not is_valid_uid("CHE123456789")

    def test_too_short(self):
        assert not is_valid_uid("CHE10521570")

    def test_check_digit_directly(self):
        assert uid_check_digit_ok("105215703")
        assert not uid_check_digit_ok("105215704")
        assert not uid_check_digit_ok("abcdefghi")


class TestChid:
    def test_normalize(self):
        assert normalize_chid("CH-020.3.926.264-8") == "CH02039262648"

    def test_format(self):
        assert format_chid("CH02039262648") == "CH-020.3.926.264-8"

    def test_format_leaves_non_chid_alone(self):
        assert format_chid("CH123") == "CH123"
