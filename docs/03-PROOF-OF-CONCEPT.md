# Proof of Concept voor Dienstencatalogus

De Proof-Of-Concept indexeert het aanbode uit de dienstencatalogus maakt die doorzoekbaar via Elasticsearch.

## 1. Indexering en Mapping

Bij het aanmaken van de index `diensten` voorzien we een **expliciete** mapping. Dit bepaalt hoe Elasticsearch de gegevens opslaat en doorzoekbaar maakt.

### Mapping (vereenvoudigd)

```json
"naam": {
  "type": "text",
  "fields": {
    "keyword": {
      "type": "keyword",
      "ignore_above": 256
    }
  }
},
"omschrijving": { "type": "text" },
"themas": { "type": "keyword" },
"type": { "type": "keyword" },
"gemeente": { "type": "keyword" },
"laatste_wijzigingsdatum": { "type": "date" }
```

Waarom deze mapping?
- Velden van het type `text` worden opgesplitst in *tokens*, ideaal voor full-text search.
- `keyword` velden (zoals themas, gemeente) zijn niet opgesplitst, en dus bruikbaar voor facet search, filtering en sortering.
- Velden zoals naam hebben zowel een text- als keyword-versie zodat je ze kan doorzoeken én sorteren.
- ignore_above: 256 voorkomt dat erg lange strings als keyword worden geïndexeerd (besparing op geheugen).

Demo
```bash
curl -X GET "elasticsearch:9200/diensten" -H 'Content-Type: application/json' | jq
```

## 2. Zoekopdracht (`query`) samenstellen en lanceren

Een typische zoekopdracht - zoals nu ook bestaat op https://vereningsloket.be/aanbod - combineert:
- Full-text queries
- Facetten (aggregaties)
- Sortering
- Paginering

### Voorbeeld Elasticsearch query DSL (Vereenvoudigd)

```json
{
  "from": 0,
  "size": 10,
  "query": {
    "bool": {
      "must": [
        {
          "multi_match": {
            "query": "vergunning",
            "fields": ["naam^3", "omschrijving_clean", "themas", "gemeente"]
          }
        },
        {
          "terms": {
            "themas": ["Economie en Werk"]
          }
        }
      ]
    }
  },
  "aggs": {
    "themas": { "terms": { "field": "themas" } },
    "gemeentes": { "terms": { "field": "gemeente" } },
    "types": { "terms": { "field": "type" } }
  },
  "sort": [
    { "naam.keyword": { "order": "asc" } }
  ]
}
```

Bovenstaande query:
- Doet een vrije zoekopdracht op `vergunning`
- Binnen het thema `Economie en Werk`
- Vraagt groepering per `themas`, `gemeentes`, `types`.
- Sorteert op `naam`

Demo

```bash
dcs search --sort-by naam --thema "Economie en Werk"
```

## 3. Vrije tekst termen tolerantie

Om zoekresultaten robuuster te maken voor eindgebruikers, kunnen we een aantal technieken toepassen:

### ✅ 1. Typo-tolerantie

We gebruiken `"fuzziness": "AUTO"` in onze multi_match query. Dit maakt kleine typfouten of spellingvarianten (bv. toelatign i.p.v. toelating) alsnog doorzoekbaar.

### ✅ 2. Nederlandse stemming

Via de dutch_stemmer filter worden woorden herleid tot hun stam. Hierdoor vindt subsidie ook subsidies, en toelating ook toelatingen.

### ✅ 3. Synoniemen

We voorzien een synoniemfilter met woorden zoals:

```json
"synonyms": [
  "toelating, vergunning",
  "subsidie, toelage"
]
```

Zo vindt een zoekopdracht naar toelage ook documenten met enkel het woord subsidie.

> Deze filters werken enkel indien de velden een aangepaste analyzer gebruiken (zoals dutch_analyzer hieronder).

### Analyzer-definitie

De analyzer `dutch_analyzer` combineert stopwoorden, stemming en synoniemen:

```json
"settings": {
  "analysis": {
    "analyzer": {
      "dutch_analyzer": {
        "tokenizer": "standard",
        "filter": [
          "lowercase",
          "dutch_stop",
          "dutch_stemmer",
          "dutch_synonyms"
        ]
      }
    },
    "filter": {
      "dutch_stop": { "type": "stop", "stopwords": "_dutch_" },
      "dutch_stemmer": { "type": "stemmer", "language": "dutch" },
      "dutch_synonyms": {
        "type": "synonym_graph",
        "synonyms": [
          "toelating, vergunning",
          "subsidie, toelage"
        ]
      }
    }
  }
}
```

Demo
```bash
dcs search --sort-by naam --thema "Economie en Werk" --query "Ik zoek De Subsiedies of toelatings"
```

## 4. Ranking op basis van profielovereenkomst

Demo
```bash
dcs search --sort-by relevance --thema "Economie en Werk" --query "Ik zoek De Subsiedies of toelatings" --profile data/vereniging.json
```

### Logica in het script

1. **Initialisatie van statusvlaggen**
   - `hasRegio`, `hasVorm`, `hasThema`: controleren of een dienst overeenkomt met respectievelijk de regio, rechtsvorm of thema's van de vereniging
   - `adNominatumMatched`, `adNominatumOther`: controleren of een dienst expliciet gericht is op een bepaalde vereniging (via `voorwaarden_vereniging`)

2. **Ad nominatum uitsluiting en voorkeursbehandeling**
   - Als een dienst **expliciet een andere** vereniging noemt → score = `0.0`
   - Als een dienst **expliciet deze** vereniging noemt → score = `100.0`

3. **Controle op regiovoorwaarden**
   - Match tussen `voorwaarden_regio` en de werkingsgebieden van de vereniging → `hasRegio = true`

4. **Controle op rechtsvorm**
   - Match tussen `voorwaarden_vorm` en de rechtsvorm (bv. "VZW") → `hasVorm = true`

5. **Controle op thema's**
   - Match tussen `themas.keyword` en de hoofdactiviteiten van de vereniging → `hasThema = true`

6. **Score-matrix**

| Regio | Vorm | Thema | Score |
|-------|------|--------|-------|
| ✅    | ✅   | ✅     | 90.0  |
| ✅    | ✅   | ❌     | 80.0  |
| ✅    | ❌   | ✅     | 70.0  |
| ❌    | ✅   | ✅     | 70.0  |
| ✅    | ❌   | ❌     | 60.0  |
| ❌    | ✅   | ❌     | 60.0  |
| ❌    | ❌   | ✅     | 20.0  |
| ❌    | ❌   | ❌     | 10.0  |

### We gebruiken Elasticsearch `script_score`?

`script_score` is een Elasticsearch-functie die toelaat om volledige controle te nemen over de berekening van de relevantiescore (`_score`) van zoekresultaten door gebruik te maken van een **Painless-script**.

We gebruiken `script_score` onze businesslogica te complex is voor `function_score`. Denk aan:
- Diensten die expliciet gericht zijn op een bepaalde vereniging (ad nominatum) → hard scoren (100) of uitsluiten (0)
- Diensten met geen voorwaarden → mild scoren (open voor iedereen)
- Diensten met voorwaarden op regio, vorm of thema → conditionele bonuspunten
- Een matrix van combinaties → bijvoorbeeld “Regio + Vorm + Thema = 90”

`script_score` implementatie:

```json
"query": {
  "script_score": {
    "query": { "bool": { "must": [...] }},
    "script": {
      "source": "... Painless code ...",
      "params": {
        "vorm": "VZW",
        "gemeentes": [...],
        "themas": [...],
        "allowed_verenigingen": [...]
      }
    }
  }
}
```

Script zoals opgenomen in de POC:

```javascript
// 1. Init
boolean hasRegio = false;
boolean hasVorm = false;
boolean hasThema = false;
boolean adNominatumMatched = false;
boolean adNominatumOther = false;

// 2. Vereniging name check
boolean verenigingFieldExists = doc.containsKey('voorwaarden_vereniging');
if (verenigingFieldExists && doc['voorwaarden_vereniging'].size() > 0) {
  def vs = doc['voorwaarden_vereniging'];
  boolean anyMatch = false;
  for (int i = 0; i < vs.length; i++) {
    if (params.allowed_verenigingen.contains(vs[i])) {
      anyMatch = true;
      break;
    }
  }
  if (anyMatch) {
    adNominatumMatched = true;
  } else {
    adNominatumOther = true;
  }
}

// 3. Ad nominatum logic
if (adNominatumOther) {
  return 0.0;
}
if (adNominatumMatched) {
  return 100.0;
}

// 4. Regio match (voorwaarden_regio vs werkingsgebieden)
if (doc.containsKey('voorwaarden_regio') && doc['voorwaarden_regio'].size() > 0) {
  def regio = doc['voorwaarden_regio'];
  for (int i = 0; i < regio.length; i++) {
    if (params.gemeentes.contains(regio[i])) {
      hasRegio = true;
      break;
    }
  }
}

// 5. Vorm match (voorwaarden_vorm vs type_vereniging)
if (doc.containsKey('voorwaarden_vorm') && doc['voorwaarden_vorm'].size() > 0) {
  def vormen = doc['voorwaarden_vorm'];
  for (int i = 0; i < vormen.length; i++) {
    if (params.vorm.contains(vormen[i])) {
      hasVorm = true;
      break;
    }
  }
}

// 6. Thema match (themas.keyword vs hoofdactiviteiten)
if (doc.containsKey('themas.keyword') && doc['themas.keyword'].size() > 0) {
  def themas = doc['themas.keyword'];
  for (int i = 0; i < themas.length; i++) {
    if (params.themas.contains(themas[i])) {
      hasThema = true;
      break;
    }
  }
}

// 7. Scoring matrix
if (hasRegio && hasVorm && hasThema) {
  return 90.0;
} else if (hasRegio && hasVorm) {
  return 80.0;
} else if ((hasRegio && hasThema) || (hasVorm && hasThema)) {
  return 70.0;
} else if (hasRegio || hasVorm) {
  return 60.0;
} else if (hasThema) {
  return 20.0;
} else {
  return 10.0;
}
```
Demo
```bash
dcs search --sort-by relevance --size 20 --profile data/vereniging.json
```


### 5. 🚨 **Afspraken rond dataformaat**
Voor een goede werking van filtering en facetten moet het uitwisselingsformaat goed afgesproken worden, en bevroren worden. De zoekmachine ontvangt tekst, correct geformatteerd en volledig.

Bijvoorbeeld, voor facet-analyse op gemeente, regio en provincie, volgens NUTS/LAU code wordt volgende serializatie aangeleverd, zowel in het Vereniging profiel als in de Dienst. Er kan niet uitgegaan worden van mappings en cleaning in de search engine logica:

```json
"provincie": "Provincie Vlaams-Brabant",
"regio": "Regio Leuven",
"gemeente": "Gemeente Leuven"
```

Op deze manier kunnen we aparte filters en facetten voorzien voor elk niveau:
- Gemeente
- Regio
- Provincie

Alsook worden voorwaarden structureel aangeleverd, bijvoorbeeld...

```json
{
    "naam": "Terrasvergunning - Inname openbaar domein",
    "type": "Toelating",
    "themas": [
        "Economie en Werk"
    ],
    "gemeente": "Provincie Vlaams-Brabant > Regio Leuven > Gemeente Leuven",
    "laatste_wijzigingsdatum": "2024-10-01",
    "voorwaarden": [
        {
        "regio": [
            "Vlaams-Brabant",
            "Leuven"
        ]
        },
        {
        "vorm": [
            "VZW"
        ]
        },
        {
        "thema": [
            "Economie en Werk"
        ]
        }
    ]
}
```



