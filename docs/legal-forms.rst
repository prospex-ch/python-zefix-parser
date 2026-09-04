Legal forms
===========

Zefix and SHAB both identify a company's legal form by its four-digit eCH-0097
code. The name depends on the language the company is registered in: code
``0106`` is an *Aktiengesellschaft* in Zurich, a *Société anonyme* in Geneva and
a *Società anonima* in Ticino, all of them the same legal form.

.. code-block:: python

   from zefix_parser import LegalForm, legal_form_abbreviation, legal_form_name

   LegalForm.CORPORATION                    # "0106"
   legal_form_name("0106", "de")            # "Aktiengesellschaft"
   legal_form_name("0106", "fr")            # "Société anonyme"
   legal_form_name("0106", "it")            # "Società anonima"
   legal_form_abbreviation("0107", "fr")    # "Sàrl"

An unknown language falls back to German; an unknown code returns ``""``.

The codes
---------

.. list-table::
   :header-rows: 1
   :widths: 8 14 20 20 20 18

   * - Code
     - Member
     - German
     - French
     - Italian
     - English
   * - ``0101``
     - ``SOLE_PROPRIETORSHIP``
     - Einzelunternehmen
     - Entreprise individuelle
     - Impresa individuale
     - Sole proprietorship
   * - ``0103``
     - ``GENERAL_PARTNERSHIP``
     - Kollektivgesellschaft
     - Société en nom collectif
     - Società in nome collettivo
     - General partnership
   * - ``0104``
     - ``LIMITED_PARTNERSHIP``
     - Kommanditgesellschaft
     - Société en commandite
     - Società in accomandita
     - Limited partnership
   * - ``0105``
     - ``PARTNERSHIP_LIMITED_BY_SHARES``
     - Kommanditaktiengesellschaft
     - Société en commandite par actions
     - Società in accomandita per azioni
     - Partnership limited by shares
   * - ``0106``
     - ``CORPORATION``
     - Aktiengesellschaft
     - Société anonyme
     - Società anonima
     - Corporation
   * - ``0107``
     - ``LIMITED_LIABILITY_COMPANY``
     - Gesellschaft mit beschränkter Haftung
     - Société à responsabilité limitée
     - Società a garanzia limitata
     - Limited liability company
   * - ``0108``
     - ``COOPERATIVE``
     - Genossenschaft
     - Société coopérative
     - Società cooperativa
     - Cooperative
   * - ``0109``
     - ``ASSOCIATION``
     - Verein
     - Association
     - Associazione
     - Association
   * - ``0110``
     - ``FOUNDATION``
     - Stiftung
     - Fondation
     - Fondazione
     - Foundation
   * - ``0111``
     - ``FOREIGN_BRANCH``
     - Zweigniederlassung ausländischer Gesellschaft
     - Succursale étrangère inscrite au registre du commerce
     - Succursale estera iscritta nel registro di commercio
     - Branch of a foreign company
   * - ``0114``
     - ``COLLECTIVE_INVESTMENT_LIMITED_PARTNERSHIP``
     - Kommanditgesellschaft für kollektive Kapitalanlagen
     - Société en commandite de placements collectifs
     - Società in accomandita per investimenti collettivi di capitale
     - Limited partnership for collective investment
   * - ``0115``
     - ``SICAV``
     - Investmentgesellschaft mit variablem Kapital (SICAV)
     - Société d'investissement à capital variable (SICAV)
     - Società di investimento a capitale variabile (SICAV)
     - Investment company with variable capital (SICAV)
   * - ``0117``
     - ``PUBLIC_LAW_INSTITUTE``
     - Institut des öffentlichen Rechts
     - Institut de droit public
     - Istituto di diritto pubblico
     - Public-law institute
   * - ``0119``
     - ``UNDIVIDED_ESTATE_REPRESENTATIVE``
     - Gemeinderschaft
     - Responsable d'indivision
     - Rappresentante dell'indivisione
     - Undivided-estate representative
   * - ``0151``
     - ``SWISS_BRANCH``
     - Zweigniederlassung schweizerischer Gesellschaft
     - Succursale suisse inscrite au registre du commerce
     - Succursale svizzera iscritta nel registro di commercio
     - Branch of a Swiss company

Abbreviations
-------------

These are the forms a company carries in its name. Every other code returns
``""``.

.. list-table::
   :header-rows: 1
   :widths: 20 27 27 26

   * - Code
     - German
     - French
     - Italian
   * - ``0103`` General partnership
     - KlG
     - SNC
     - SNC
   * - ``0104`` Limited partnership
     - KmG
     - SC
     - SAc
   * - ``0105`` Partnership limited by shares
     - KmAG
     - SCA
     - SAcA
   * - ``0106`` Corporation
     - AG
     - SA
     - SA
   * - ``0107`` Limited liability company
     - GmbH
     - Sàrl
     - Sagl
   * - ``0115`` Investment company with variable capital (SICAV)
     - SICAV
     - SICAV
     - SICAV

Codes outside the register
--------------------------

eCH-0097 reserves codes the commercial register leaves alone: ``0102`` covers
the simple partnership, which stays unregistered, and ``0220`` and above cover
public-law bodies that keep their own registers. Zefix emits the fifteen codes
above and nothing else, so anything outside that set points to a data error
upstream or a change to the standard.
