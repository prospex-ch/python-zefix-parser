Quick start
===========

Installation
------------

.. code-block:: bash

   pip install zefix-parser

To use the HTTP clients, for fetching from the live endpoints:

.. code-block:: bash

   pip install zefix-parser[http]

The parsers themselves have no dependencies at all, so you can install the
package without the extra and point them at responses you fetched yourself.

Read the register from LINDAS
-----------------------------

No credentials needed.

.. code-block:: python

   from zefix_parser.client import LindasClient

   with LindasClient() as client:
       print(client.count())  # 800000-ish

       for entity in client.iter_entities():
           print(entity.legal_name, entity.uid, entity.canton, entity.legal_form_code)

Or look up companies you already have UIDs for, in one request:

.. code-block:: python

   from zefix_parser.client import LindasClient

   with LindasClient() as client:
       entities = client.fetch_by_uids(["CHE-105.215.703", "CHE-411.462.297"])

   for entity in entities:
       print(entity.legal_name)   # "Alpenblick Handel AG"
       print(entity.purpose)      # "Handel mit Waren aller Art"
       print(entity.municipality_name, entity.canton)

Fetch details from the PublicREST API
-------------------------------------

The REST API is gated behind HTTP Basic auth. Credentials are issued on request
by ``zefix@bj.admin.ch``.

.. code-block:: python

   from zefix_parser.client import ZefixRestClient

   with ZefixRestClient(username="...", password="...") as client:
       company = client.get_by_uid("CHE-105.215.703")

   print(company.name)             # "Alpenblick Handel AG"
   print(company.capital_nominal)  # Decimal("250000.00")
   print(company.status)           # "ACTIVE"

   for auditor in company.audit_companies:
       print(auditor.name, auditor.legal_seat)

Both clients rate-limit themselves to one request every half second and retry
transient failures with exponential backoff. Neither is thread-safe: give each
thread its own client.

Parse responses you already have
--------------------------------

.. code-block:: python

   from zefix_parser import parse_company, parse_entity_page

   company = parse_company(rest_json)          # a dict from the REST API
   entities = parse_entity_page(sparql_bytes)  # a SPARQL JSON results document

Identifiers
-----------

The same UID appears in three forms depending on where you read it, so the
library converts between them:

.. code-block:: python

   from zefix_parser import clean_uid, format_uid, is_valid_uid, normalize_uid

   normalize_uid("CHE-105.215.703")         # "CHE105215703"  (LINDAS form)
   format_uid("CHE105215703")               # "CHE-105.215.703"  (REST form)
   clean_uid("VAT: CHE-109.807.630 MWST")   # "CHE109807630"
   is_valid_uid("CHE123456789")             # False - the check digit fails

:func:`~zefix_parser.is_valid_uid` runs the ISO 7064 mod 11-10 check digit. It
is worth calling before you spend a request: a mistyped UID can never match the
register, and the register's own placeholder ``CHE123456789`` fails it.

Background
----------

Zefix -- the Zentraler Firmenindex, *index central des raisons de commerce*,
*indice centrale delle ditte*, officially the Swiss Central Business Name Index
-- is the federal index over the 26 cantonal commercial registers
(Handelsregister, registre du commerce, registro di commercio). Every company
registered in Switzerland appears in it, identified by a UID
(``CHE-123.456.789``), a CHID and an EHRAID.

The Federal Office of Justice publishes the index twice: as a linked-data
dataset on LINDAS, which is open and complete but state-only, and as the
PublicREST API, which is richer but needs credentials and answers one company at
a time. Neither publishes a change feed; for that you need the gazette, which is
what `shab-parser <https://shab-parser.readthedocs.io>`_ reads.
