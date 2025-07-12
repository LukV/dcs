# Elasticsearch Proof of Concept voor Dienstencatalogus

Dit document beschrijft de proof of concept om diensten uit de dienstencatalogus te indexeren en te doorzoeken via Elasticsearch.

## 1. Index en Mapping

Bij het aanmaken van de index `diensten` voorzien we een **expliciete** mapping. Dit bepaalt hoe Elasticsearch de gegevens opslaat en doorzoekbaar maakt.

### Mapping (samenvatting)

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

## 2. Voorbeeld zoekopdracht

Een typische zoekopdracht combineert:
- Full-text queries
- Filters op themas, gemeente…
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

## 3. Verbeteringen voor zoekkwaliteit

Om zoekresultaten robuuster te maken voor eindgebruikers, hebben we volgende technieken toegepast:

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

## 4. Analyzer-definitie

De analyzer dutch_analyzer combineert stopwoorden, stemming en synoniemen:

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

## 5. 🚨 **Afspraken rond dataformaat**
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
