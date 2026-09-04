import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name):
    return (FIXTURES / name).read_bytes()


@pytest.fixture
def entities_json():
    return _load("lindas/entities.json")


@pytest.fixture
def count_json():
    return _load("lindas/count.json")


@pytest.fixture
def uris_page_1_json():
    return _load("lindas/uris_page_1.json")


@pytest.fixture
def uris_page_2_json():
    return _load("lindas/uris_page_2.json")


@pytest.fixture
def company_full():
    return json.loads(_load("rest/company_full.json"))


@pytest.fixture
def company_minimal():
    return json.loads(_load("rest/company_minimal.json"))


@pytest.fixture
def sogc_bydate():
    return json.loads(_load("rest/sogc_bydate.json"))
