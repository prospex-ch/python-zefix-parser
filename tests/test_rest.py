from datetime import date
from decimal import Decimal

import pytest

from zefix_parser import (
    Company,
    ParserError,
    meaningful_old_names,
    normalize_name,
    parse_companies,
    parse_company,
    parse_sogc,
    parse_sogc_list,
)


class TestParseCompany:
    def test_scalar_fields(self, company_full):
        company = parse_company(company_full)
        assert company.name == "Alpenblick Handel AG"
        assert company.ehraid == 1102345
        assert company.uid == "CHE-105.215.703"
        assert company.canton == "ZH"
        assert company.status == "ACTIVE"

    def test_capital(self, company_full):
        company = parse_company(company_full)
        assert company.capital_nominal == Decimal("250000.00")
        assert company.capital_currency == "CHF"

    def test_relations(self, company_full):
        company = parse_company(company_full)
        assert [b.name for b in company.branch_offices] == [
            "Alpenblick Handel AG, succursale de Lausanne"
        ]
        assert company.branch_offices[0].legal_seat == "Lausanne"
        assert company.audit_companies[0].name == "Limmat Revisions AG"
        assert company.has_taken_over[0].status == "DELETED"
        assert company.was_taken_over_by == []

    def test_old_names(self, company_full):
        company = parse_company(company_full)
        assert len(company.old_names) == 3
        assert company.old_names[0].sequence_nr == 1

    def test_accepts_a_single_element_list(self, company_minimal):
        """The API returns an object for some endpoints and a list for others."""
        company = parse_company(company_minimal)
        assert company.name == "Léman Services Sàrl"

    def test_missing_fields_get_defaults(self, company_minimal):
        company = parse_company(company_minimal)
        assert company.chid == ""
        assert company.capital_currency == "CHF"
        assert company.branch_offices == []

    def test_unparseable_capital_is_dropped(self, company_minimal):
        assert parse_company(company_minimal).capital_nominal is None

    def test_deletion_date(self, company_minimal):
        assert parse_company(company_minimal).deletion_date == date(2026, 3, 15)

    def test_null_deletion_date(self, company_full):
        assert parse_company(company_full).deletion_date is None

    def test_rejects_an_empty_list(self):
        with pytest.raises(ParserError, match="empty list"):
            parse_company([])

    def test_rejects_a_string(self):
        with pytest.raises(ParserError, match="got str"):
            parse_company("Alpenblick Handel AG")


class TestParseCompanies:
    def test_list(self, company_full, company_minimal):
        companies = parse_companies([company_full, company_minimal[0]])
        assert [c.ehraid for c in companies] == [1102345, 1204488]

    def test_wraps_a_single_object(self, company_full):
        assert len(parse_companies(company_full)) == 1

    def test_rejects_a_string(self):
        with pytest.raises(ParserError, match="got str"):
            parse_companies("nope")


class TestParseSogc:
    def test_list(self, sogc_bydate):
        publications = parse_sogc_list(sogc_bydate)
        assert len(publications) == 2
        assert publications[0].sogc_id == 1234567
        assert publications[0].publication_date == date(2026, 6, 15)
        assert publications[0].mutation_type == "Neueintragung"

    def test_missing_message(self, sogc_bydate):
        assert parse_sogc(sogc_bydate[1]).message == ""


class TestNormalizeName:
    def test_ignores_case_and_punctuation(self):
        assert normalize_name("QualiCasa AG") == normalize_name("Qualicasa  AG.")

    def test_keeps_genuinely_different_names(self):
        assert normalize_name("Alpenblick Import GmbH") != normalize_name(
            "Alpenblick Handel AG"
        )


class TestMeaningfulOldNames:
    def test_drops_retypeset_variants_of_the_current_name(self, company_full):
        """Only the real rename survives; the other two are the live name re-typeset."""
        company = parse_company(company_full)
        assert [n.name for n in meaningful_old_names(company)] == [
            "Alpenblick Import GmbH"
        ]

    def test_deduplicates(self):
        company = parse_company(
            {
                "name": "Zürisee Tech AG",
                "ehraid": 1,
                "oldNames": [
                    {"name": "Seetech GmbH", "sequenceNr": 2},
                    {"name": "SEETECH GMBH", "sequenceNr": 1},
                ],
            }
        )
        kept = meaningful_old_names(company)
        assert [n.sequence_nr for n in kept] == [1]

    def test_no_old_names(self):
        assert meaningful_old_names(Company(name="Zürisee Tech AG", ehraid=1)) == []
