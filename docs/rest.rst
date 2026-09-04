The PublicREST API
==================

The Zefix PublicREST API lives at
``https://www.zefix.admin.ch/ZefixPublicREST/api/v1`` and answers one company at
a time. Every endpoint requires HTTP Basic auth; without an ``Authorization``
header you get a 401. Credentials are issued on request by ``zefix@bj.admin.ch``.

What it adds over LINDAS
------------------------

The register's own detail record, which LINDAS keeps to itself:

* ``capital_nominal`` and ``capital_currency``: the share capital
* ``status``: ``ACTIVE``, ``IN_LIQUIDATION`` or ``DELETED``, plus
  ``deletion_date`` where it applies
* ``audit_companies``: the statutory auditor
* ``head_offices``, ``further_head_offices``, ``branch_offices``: the
  head-office and branch tree
* ``has_taken_over``, ``was_taken_over_by``: mergers, from both sides
* ``old_names``: every name the company has carried
* ``cantonal_excerpt_web``: a link to the cantonal register's own excerpt

Endpoints
---------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Method
     - Endpoint
   * - :meth:`~zefix_parser.client.ZefixRestClient.get_by_uid`
     - ``GET /company/uid/{uid}``
   * - :meth:`~zefix_parser.client.ZefixRestClient.get_by_ehraid`
     - ``GET /company/ehraid/{ehraid}``
   * - :meth:`~zefix_parser.client.ZefixRestClient.get_by_chid`
     - ``GET /company/chid/{chid}``
   * - :meth:`~zefix_parser.client.ZefixRestClient.search`
     - ``POST /company/search``
   * - :meth:`~zefix_parser.client.ZefixRestClient.sogc_by_date`
     - ``GET /sogc/bydate/{date}``
   * - :meth:`~zefix_parser.client.ZefixRestClient.sogc`
     - ``GET /sogc/{id}``

A lookup that finds nothing returns ``None``. The register answers 404 for a UID
it has no record of, so treat that as an answer and carry on.

The UID has to be punctuated
----------------------------

``GET /company/uid/CHE105215703`` returns 404;
``GET /company/uid/CHE-105.215.703`` returns the company. LINDAS stores the
unpunctuated form, so anything you carry across from a crawl needs converting.
:meth:`~zefix_parser.client.ZefixRestClient.get_by_uid` calls
:func:`~zefix_parser.format_uid` for you, and you can call it yourself if you
are driving the API by hand.

Search is a prefix match
------------------------

``/company/search`` matches the start of the name and caps how much it returns.
There is no cursor and no total, so shorten the prefix when you need more
results and lengthen it when you get too many.

Most former names are re-typesettings
-------------------------------------

The register re-typesets a company's name whenever anything else about it
changes, so ``old_names`` fills up with entries that differ from the current
name only in casing, punctuation or spacing: "QualiCasa AG" against
"Qualicasa AG". In one corpus of Swiss companies, thousands of ``oldNames`` rows
were of exactly this kind. Apply them and you retire the company's live name.

:func:`~zefix_parser.meaningful_old_names` compares each entry against the
current name under :func:`~zefix_parser.normalize_name` (casefolded, stripped of
punctuation and extra whitespace) and returns the genuine former names,
deduplicated, oldest first:

.. code-block:: python

   from zefix_parser import meaningful_old_names

   for old in meaningful_old_names(company):
       print(old.sequence_nr, old.name)

Rate limiting
-------------

:class:`~zefix_parser.client.ZefixRestClient` waits half a second between
requests and retries 429 and 5xx responses with exponential backoff. For more
throughput, run several clients in separate threads. Each one throttles itself
independently, and a single client is unsafe to share between threads.
