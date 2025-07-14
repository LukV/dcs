import json
from typing import Any

from elastic_transport import ApiError
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from rich.console import Console

from dcs.index.es_client import get_client
from dcs.index.mapper import product_to_es_doc
from dcs.models.product import CleanedProduct
from dcs.utils.config import CLEANED_FILE

console = Console()

INDEX_NAME = "diensten"

MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "dutch_analyzer": {
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "dutch_stop",
                        "dutch_stemmer",
                        "dutch_synonyms",
                    ],
                }
            },
            "filter": {
                "dutch_stop": {"type": "stop", "stopwords": "_dutch_"},
                "dutch_stemmer": {"type": "stemmer", "language": "dutch"},
                "dutch_synonyms": {
                    "type": "synonym_graph",
                    "synonyms": ["toelating, vergunning", "subsidie, toelage"],
                },
            },
        }
    },
    "mappings": {
        "properties": {
            "naam": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                "analyzer": "dutch_analyzer",
            },
            "omschrijving": {"type": "tcext"},
            "themas": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "type": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "gemeente": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "voorwaarden_vorm": {"type": "keyword"},
            "voorwaarden_regio": {"type": "keyword"},
            "voorwaarden_vereniging": {"type": "keyword"},
            "keywords": {"type": "text"},
            "laatste_wijzigingsdatum": {
                "type": "date",
                "format": "strict_date_optional_time||yyyy-MM-dd",
            },
        }
    },
}


def drop_index(client: Elasticsearch) -> None:
    """Drop the Elasticsearch index if it exists."""
    try:
        if client.indices.exists(index=INDEX_NAME):
            client.indices.delete(index=INDEX_NAME)
            console.print(f"🗑️ Dropped index '{INDEX_NAME}'.")
        else:
            console.print(f"⚠️ Index '{INDEX_NAME}' does not exist.")
    except Exception as e:
        console.print(f"🔥 Failed to delete index '{INDEX_NAME}': {e}")
        raise


def create_index(client: Elasticsearch) -> None:
    """Create the Elasticsearch index with the defined mapping."""
    try:
        if INDEX_NAME in client.indices.get_alias():
            console.print(f"Index '{INDEX_NAME}' already exists.")
            return

        client.indices.create(index=INDEX_NAME, body=MAPPING)
        console.print(f"✅ Created index '{INDEX_NAME}'.")

    except Exception as e:
        console.print(f"🔥 Failed to create index '{INDEX_NAME}': {e}")
        if isinstance(e, ApiError) and e.body:
            console.print(e.body)
        raise


def index_all() -> None:
    """Index all cleaned Dienstencatalogus records into Elasticsearch."""
    client = get_client()
    create_index(client)

    with CLEANED_FILE.open(encoding="utf-8") as f:
        raw_items = json.load(f)

    products = [CleanedProduct(**item) for item in raw_items]
    actions = [{**product_to_es_doc(p), "_index": INDEX_NAME} for p in products]

    bulk(client, actions)
    console.print(f"✅ Indexed {len(actions)} producten")


def search_diensten(  # noqa: PLR0913
    client: Elasticsearch,
    query: str | None = None,
    themas: list[str] | None = None,
    gemeente: str | None = None,
    sort_by: str = "naam",
    sort_order: str = "asc",
    from_: int = 0,
    size: int = 10,
    vereniging_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Search the diensten index with optional filters and sorting."""
    must_clauses = []

    if query:
        must_clauses.append(
            {
                "multi_match": {
                    "query": query,
                    "fields": ["naam^3", "omschrijving_clean", "themas", "gemeente"],
                    "fuzziness": "AUTO",
                }
            }
        )

    if themas:
        must_clauses.append({"terms": {"themas.keyword": themas}})

    if gemeente:
        must_clauses.append({"match_phrase": {"gemeente": gemeente}})

    base_query = {
        "bool": {"must": must_clauses if must_clauses else [{"match_all": {}}]}
    }

    if vereniging_profile:
        query_block = {
            "script_score": {
                "query": base_query,
                "script": {
                    "source": """
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
        """,
                    "params": {
                        "gemeentes": vereniging_profile.get("werkingsgebieden", []),
                        "vorm": vereniging_profile.get("type_vereniging", []),
                        "themas": vereniging_profile.get("hoofdactiviteiten", []),
                        "allowed_verenigingen": list(
                            vereniging_profile.get("namen", {}).values()
                        ),
                    },
                },
            }
        }
    else:
        query_block = base_query  # type: ignore  # noqa: PGH003

    body = {
        "from": from_,
        "size": size,
        "query": query_block,
        "aggs": {
            "themas": {"terms": {"field": "themas.keyword"}},
            "gemeentes": {"terms": {"field": "gemeente.keyword"}},
            "types": {"terms": {"field": "type.keyword"}},
        },
    }

    if sort_by == "relevance":
        body["sort"] = [{"_score": {"order": "desc"}}]
    elif sort_by:
        sort_field = (
            f"{sort_by}.keyword"
            if sort_by in ["naam", "laatste_wijzigingsdatum"]
            else sort_by
        )
        body["sort"] = [{sort_field: {"order": sort_order}}]

    console.log(f"🔎 Search body: {body}")
    return dict(client.search(index=INDEX_NAME, body=body).body)
