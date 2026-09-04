from zefix_parser import (
    LEGAL_FORM_LABELS,
    LegalForm,
    legal_form_abbreviation,
    legal_form_name,
)


class TestLegalForm:
    def test_compares_equal_to_its_code(self):
        assert LegalForm.CORPORATION == "0106"

    def test_every_member_has_labels(self):
        assert {form.value for form in LegalForm} == set(LEGAL_FORM_LABELS)

    def test_every_entry_has_four_languages(self):
        for code, labels in LEGAL_FORM_LABELS.items():
            assert set(labels) == {"de", "fr", "it", "en"}, code


class TestLegalFormName:
    def test_per_language(self):
        assert legal_form_name("0106", "de") == "Aktiengesellschaft"
        assert legal_form_name("0106", "fr") == "Société anonyme"
        assert legal_form_name("0106", "it") == "Società anonima"

    def test_defaults_to_german(self):
        assert legal_form_name("0107") == "Gesellschaft mit beschränkter Haftung"

    def test_unknown_language_falls_back_to_german(self):
        assert legal_form_name("0107", "rm") == "Gesellschaft mit beschränkter Haftung"

    def test_unknown_code(self):
        assert legal_form_name("9999") == ""


class TestLegalFormAbbreviation:
    def test_per_language(self):
        assert legal_form_abbreviation("0107", "de") == "GmbH"
        assert legal_form_abbreviation("0107", "fr") == "Sàrl"
        assert legal_form_abbreviation("0107", "it") == "Sagl"

    def test_forms_without_one(self):
        assert legal_form_abbreviation("0110") == ""
