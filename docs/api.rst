API reference
=============

LINDAS
------

.. autofunction:: zefix_parser.parse_entity_page
.. autofunction:: zefix_parser.parse_uri_page
.. autofunction:: zefix_parser.parse_count
.. autofunction:: zefix_parser.parse_sparql_json
.. autofunction:: zefix_parser.compute_fingerprint

.. autofunction:: zefix_parser.build_combined_page_query
.. autofunction:: zefix_parser.build_uri_page_query
.. autofunction:: zefix_parser.build_detail_query
.. autofunction:: zefix_parser.build_detail_query_by_uids
.. autofunction:: zefix_parser.build_count_query

.. py:data:: zefix_parser.QUERY_VERSION

   Version of the SPARQL query templates. Bumped whenever a template changes
   in a way that alters the parsed output, so a stored crawl can be told apart
   from one made under different queries.

PublicREST
----------

.. autofunction:: zefix_parser.parse_company
.. autofunction:: zefix_parser.parse_companies
.. autofunction:: zefix_parser.parse_sogc
.. autofunction:: zefix_parser.parse_sogc_list
.. autofunction:: zefix_parser.meaningful_old_names
.. autofunction:: zefix_parser.normalize_name

.. py:data:: zefix_parser.PARSER_VERSION

   Version string identifying this parser, for recording alongside anything
   you persist.

Data model
----------

.. autoclass:: zefix_parser.RegistryEntity
   :members:

.. autoclass:: zefix_parser.Company
   :members:

.. autoclass:: zefix_parser.RelatedEntity
   :members:

.. autoclass:: zefix_parser.OldName
   :members:

.. autoclass:: zefix_parser.SogcPublication
   :members:

.. autoclass:: zefix_parser.RawPage
   :members:

Enumerations
------------

.. autoclass:: zefix_parser.CompanyStatus
   :members:
   :undoc-members:

.. autoclass:: zefix_parser.RelationType
   :members:
   :undoc-members:

.. autoclass:: zefix_parser.Language
   :members:
   :undoc-members:

Identifiers
-----------

.. autofunction:: zefix_parser.normalize_uid
.. autofunction:: zefix_parser.format_uid
.. autofunction:: zefix_parser.clean_uid
.. autofunction:: zefix_parser.is_valid_uid
.. autofunction:: zefix_parser.uid_check_digit_ok
.. autofunction:: zefix_parser.normalize_chid
.. autofunction:: zefix_parser.format_chid

Legal forms
-----------

.. autoclass:: zefix_parser.LegalForm
   :members:
   :undoc-members:

.. autofunction:: zefix_parser.legal_form_name
.. autofunction:: zefix_parser.legal_form_abbreviation

.. py:data:: zefix_parser.LEGAL_FORM_LABELS

   Legal-form names by eCH-0097 code, then by language tag (``de``, ``fr``,
   ``it``, ``en``). See :doc:`legal-forms` for the rendered table.

.. py:data:: zefix_parser.LEGAL_FORM_ABBREVIATIONS

   Usual abbreviations by code, as a ``(German, French, Italian)`` tuple. Only
   the forms a company carries in its name have one.

HTTP clients
------------

.. autoclass:: zefix_parser.client.LindasClient
   :members: count, iter_entities, iter_pages, fetch_by_uids, query, close

.. autoclass:: zefix_parser.client.ZefixRestClient
   :members: get_by_uid, get_by_ehraid, get_by_chid, search, sogc_by_date, sogc, close

.. py:data:: zefix_parser.client.DEFAULT_LINDAS_ENDPOINT

   ``"https://ld.admin.ch/query"``

.. py:data:: zefix_parser.client.DEFAULT_REST_BASE_URL

   ``"https://www.zefix.admin.ch/ZefixPublicREST/api/v1"``

.. py:data:: zefix_parser.client.MAX_PAGE_SIZE

   Largest page :class:`~zefix_parser.client.LindasClient` will request.

Exceptions
----------

.. autoclass:: zefix_parser.ZefixError
.. autoclass:: zefix_parser.ParserError
.. autoclass:: zefix_parser.TransportError
.. autoclass:: zefix_parser.RetryableError
.. autoclass:: zefix_parser.AuthenticationError
