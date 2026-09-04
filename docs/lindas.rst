The LINDAS dataset
==================

LINDAS is the Swiss federal linked-data service. It publishes the whole
commercial register as RDF at ``https://ld.admin.ch/query``, under the class
``admin:ZefixOrganisation``. There is no authentication and no quota beyond
ordinary politeness.

What the dataset carries
------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Field
     - Predicate
     - Notes
   * - ``legal_name``
     - ``schema:legalName``
     - Language-tagged; the same company has one per official language
   * - ``alternate_names``
     - ``schema:name``
     - Plus the legal-name variants the parser set aside
   * - ``uid``
     - ``schema:identifier`` / ``CompanyUID``
     - Unpunctuated, ``CHE123456789``
   * - ``chid``
     - ``schema:identifier`` / ``CompanyCHID``
     - The older cantonal register number
   * - ``ehra_id``
     - ``schema:identifier`` / ``CompanyEHRAID``
     - The register's own key; the only identifier every company has
   * - ``legal_form_code``
     - ``schema:additionalType``
     - The eCH-0097 code, taken from the URI tail
   * - ``municipality_id``
     - ``admin:municipality``
     - The federal municipality number
   * - ``canton``
     - ``schema:address/schema:addressRegion``
     - Two letters
   * - ``street_address``, ``postal_code``, ``locality``
     - ``schema:address/...``
     - Already structured, field by field
   * - ``purpose``
     - ``schema:description``
     - The registered purpose, language-tagged

Folding the language variants
-----------------------------

A single company spans several result rows, one per language-tagged literal.
:func:`~zefix_parser.parse_entity_page` groups rows by entity URI and picks one
value per field, preferring German, then French, Italian, English, and finally
an untagged literal. The remaining variants go to ``alternate_names``, and
``purpose_language`` records which language the purpose came out in.

Where a field holds several values for reasons other than language (two street
addresses, two legal-form codes), the lowest value sorted lexically wins. The
same input always yields the same output, so two fetches of an unchanged company
compare equal.

Two kinds of entity are dropped: those with no legal name, and those carrying
neither a UID nor an EHRAID. The register emits a few of each, and there is
nothing to match them against.

Pagination
----------

The dataset has no modification-date predicate, so there is no way to ask for
what changed. You walk the whole register, paginating by keyset over the entity
URI. Deep ``OFFSET`` values time out on this endpoint:

.. code-block:: python

   from zefix_parser import build_combined_page_query, parse_entity_page

   query = build_combined_page_query(cursor_after=None, limit=500)
   # ... send it, then:
   entities = parse_entity_page(response_body)
   cursor = max(e.zefix_uri for e in entities)
   query = build_combined_page_query(cursor_after=cursor, limit=500)

:meth:`~zefix_parser.client.LindasClient.iter_pages` does this for you and
yields :class:`~zefix_parser.RawPage` objects carrying the cursor each page was
fetched with. A crawl interrupted after six hours resumes where it stopped.

Skipping unchanged companies
----------------------------

Every :class:`~zefix_parser.RegistryEntity` carries a ``fingerprint``: a SHA-256
over the fields that describe the company itself. Two fetches of an unchanged
company produce the same value, so you can compare it against what you stored
last time and skip the write. The digest covers the descriptive fields only:
``chid``, ``ehra_id`` and ``alternate_names`` sit outside it, so a cosmetic
change to a name variant leaves the fingerprint alone.

Detecting deregistrations
-------------------------

A deleted company stops appearing in the dataset. There is no tombstone and no
status field, so the only way to notice is to compare a full crawl against the
previous one. A single failed page can make a company look absent: require the
same company to be missing from two consecutive crawls before you act on it.
