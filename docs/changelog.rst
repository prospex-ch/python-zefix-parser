Changelog
=========

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
