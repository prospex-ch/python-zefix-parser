Changelog
=========

0.1.1 (2026-10-16)
------------------

* ``ZefixRestClient.get_by_uid`` sends the unpunctuated UID. The PublicREST API
  now answers the punctuated form with an empty list, so 0.1.0 returned
  ``None`` for every company. When the unpunctuated form comes back empty, the
  client asks again with the punctuated one.
* The docstrings of ``format_uid`` and ``normalize_uid`` name the form the API
  expects.

0.1.0 (2026-09-04)
------------------

Initial release.

* LINDAS SPARQL query builders and result parsing into ``RegistryEntity``,
  with language folding, content fingerprints and keyset pagination.
* Zefix PublicREST parsing into ``Company``, covering capital, status,
  corporate relations and former names.
* ``LindasClient`` and ``ZefixRestClient``, both self-throttling and retrying.
* UID and CHID normalization, formatting and ISO 7064 check-digit validation.
* The eCH-0097 legal-form codes with German, French, Italian and English names.
