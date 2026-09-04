zefix-parser
============

Typed Python client for Zefix, the Swiss Central Business Name Index
(Zentraler Firmenindex).

Covers both ways into the register: the open `LINDAS <https://lindas.admin.ch>`_
SPARQL dataset, which carries every company in Switzerland and needs no
credentials, and the `Zefix PublicREST API <https://www.zefix.admin.ch>`_, which
adds share capital, legal status, auditors and corporate relations. Responses
parse into plain dataclasses.

Built and maintained by `Prospex <https://prospex.ch>`_.

.. toctree::
   :maxdepth: 2

   quickstart
   lindas
   rest
   legal-forms
   api
   changelog
