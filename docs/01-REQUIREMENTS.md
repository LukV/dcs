# Gepersonaliseerde zoekmachine voor de IDPC Dienstencatalogus


Dit document beschrijft de vereisten voor een geavanceerde, Nederlandstalige gepersonaliseerde zoekmachine voor de IDPC Dienstencatalogus. Het doel is om relevante en transparante zoekresultaten aan te bieden die afgestemd zijn op het profiel van de aangemelde vereniging, met behoud van essentiële zoekfunctionaliteiten zoals filtering en paginering.

---

## 🔗 Wat is er al gerealiseerd?

### Zoekinterface voor Aanbod op verenigingsloket.be

Gebruikers voeren zoekopdrachten uit via een interface met:
- Vrije zoektekst
- Filters (zoals thema, type aanvraag)

Daarnaast is er contextuele informatie beschikbaar voor aangemelde gebruikers:
- Het profiel van de vereniging gelinkt aan de gebruiker (bv. type, werkdomein, gemeente)

### Datavoorziening & synchronisatie

Bronnen:
- Externe databronnen:
  - Aanbod: IDPC – diensten van de Vlaamse Overheid voor o.m. verenigingen (bv. subsidies, vergunningen, uitleendiensten), verrijkt met voorwaarden voor afname.
  - Verenigingsinfo: Verenigingsregister + historiek op basis van Subsidieregister en DOSIS.
- CMS: Drupal – hierin worden diensten beheerd.

Proces:
- Data uit Drupal worden aangeleverd aan de zoekmachine, verrijkt met locatiegegevens: NUTS LAU-codes en -velden (TBD).


## Functionele vereisten

### 1. Behoud van bestaande zoekfunctionaliteit
- **Vrije zoektekst**: Flexibele zoekopdrachten over alle dienstbeschrijvingen heen.
- **Facetten**: Filteren op kernattributen zoals thema, regio, doelgroepen.
- **Sorteren**: Mogelijkheid tot sorteren op datum, alfabetisch of relevantie.
- **Paginering**: Resultaten worden gepagineerd weergegeven voor gebruiksgemak en schaalbaarheid.

### 2. Gepersonaliseerde relevantieranking

Resultaten worden gerangschikt op basis van de mate waarin een dienst overeenkomt met het profiel van de aangemelde vereniging.

#### a. Gewogen, dynamische attributenmatching

Boost-logica moet instelbaar zijn door beheerders. Gewicht per attribuut:
- `type` (bv. jeugdvereniging, cultuurvereniging), `locatie` → **hoogste gewicht**
- `doelgroep` (bv. leeftijdscategorie) → **gemiddeld gewicht**
- `thema` (bv. sport, cultuur, jeugdwerk) → **laagste gewicht**
- …

Gebruik het verenigingprofiel om:
- Extra queryvoorwaarden toe te voegen (bv. type, regio, doelgroep).
- Boosting parameters dynamisch aan te passen.
  - Bv: als type = jeugdvereniging, verhoog de relevantie van diensten die dat als voorwaarde hebben.

Deze gewichten bepalen het relatieve belang van verschillende voorwaarden bij de relevantiescore.



#### b. Ad nominatum-diensten

Sommige diensten richten zich expliciet op specifieke verenigingen:
- Indien de aangemelde vereniging expliciet vermeld wordt → **sterke positieve boost**
- Indien niet vermeld → **uitsluiten** uit de zoekresultaten

#### c. Toekomst: Gebruikssignalen

In latere releases willen we ook rekening houden met effectief gebruik:
- Historiek van reeds afgenomen diensten
- Goedgekeurde dossiers of subsidieaanvragen

Deze gedragscontext verhoogt de relevantie van zoekresultaten.

#### Volwaardige ondersteuning voor de Nederlandse taal

- Ondersteuning voor Nederlandse **lemmatisatie en stemming**
- **Samenstellingen** correct behandelen (bv. “cultuurbeleid” vs. “cultuur”)
- **Typotolerantie** bij veelvoorkomende spellingfouten
- Tools met **native ondersteuning voor Nederlands** genieten de voorkeur (bv. Elasticsearch’s Dutch analyzer of alternatieven)

### 4. Geavanceerde full-text search

Om zoekervaring en relevantie te verbeteren:
- **Synoniemen**: Onderkenning van semantisch gelijkaardige termen
- **Stemming & lemmatisatie**: Begrip van woordstammen en vervoegingen
- **Typotolerantie**: Foutenmarge bij spelling
- **Vector search**: Zoekresultaten rangschikken op basis van semantische gelijkenis via embeddings

⚠️ *Vector search heeft prioriteit boven synoniemen*, gezien het beter scoort op het interpreteren van vage of complexe zoekvragen.

### 5. Fijnmazige rankinglogica

- Relevantie wordt bepaald op veldniveau:
  - Boost bij match in sterk informatieve velden (bv. titel, samenvatting)
  - Lager gewicht voor minder doorslaggevende velden
  - Specifieke boostregels, bv. “voorwaarden” die exact overeenkomen met type vereniging → hogere score

## ⚙️ Niet-functionele vereisten

### 1. Onderhoudbaarheid en operationele eenvoud

Het team heeft beperkte expertise rond infrastructuur en DevOps. De focus ligt op frontend en CMS (Drupal). Daarom:

- De infrastructuur moet **zo weinig mogelijk operationele overhead** vragen.
- Technologieën die complexe infrastructuur vereisen (zoals Elasticsearch clusters) zijn **zorgpunten**.
- Er is een voorkeur voor:
  - **Beheerde diensten** (indien betaalbaar en betrouwbaar)
  - **Serverless** of **zero-maintenance** oplossingen
  - **Eenvoudige integratie** met Drupal of andere headless CMS-systemen

➡️ *Onderhoudbaarheid is de belangrijkste niet-functionele vereiste.*

---

### 2. Licenties en onafhankelijkheid

Ondanks de focus op eenvoud wil het team:
- **Heldere, voorspelbare licentievoorwaarden**
- **Geen vendor lock-in** of op z’n minst een **duidelijke migratie-optie**
- **Open source-componenten** zijn gewenst waar mogelijk, of anders goed gedocumenteerde API’s en exportmechanismen

---

### 3. Toekomstbestendigheid en AI-readiness

Hoewel dit geen prioriteit is in de eerste release, moet de architectuur toekomstige innovaties ondersteunen zoals:

- AI-ondersteunde ranking (bv. via LLMs)
- Embedding-gebaseerde zoekopdrachten (vector search)
- Machine learning voor persoonlijke aanbevelingen gebaseerd op gebruikersgedrag

➡️ Dit zorgt ervoor dat de oplossing mee kan evolueren met moderne zoek- en aanbevelingstechnologie, zonder ingrijpende herbouw.

---

## 🌱 Toekomstige uitbreidingen

- Weergave van gepersonaliseerde labels zoals “Reeds gebruikt” of “Specifiek voor jouw vereniging”
- Feedbackmechanisme voor gebruikers om de ranking te verfijnen
- Gebruik van historiek uit Subsidieregister en DOSIS om resultaten verder te personaliseren
- Samenvatting van zoekresultaten + belangrijkste opportuniteiten in één duidelijke zin
