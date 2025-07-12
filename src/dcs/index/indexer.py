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
            "omschrijving": {"type": "text"},
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
    """Delete the Elasticsearch index if it exists."""
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
    """Create the Elasticsearch index if it doesn't exist."""
    try:
        # Use a more robust check via cat indices
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
    """Index all cleaned products into Elasticsearch."""
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
) -> dict[str, Any]:
    """Search for diensten in Elasticsearch."""
    must_clauses = []

    if query:
        must_clauses.append(
            {
                "multi_match": {
                    "query": query,
                    "fields": ["naam^3", "omschrijving_clean", "themas", "gemeente"],
                    "fuzziness": "AUTO",  # 🔍 typo-tolerantie
                }
            }
        )

    if themas:
        must_clauses.append({"terms": {"themas.keyword": themas}})

    if gemeente:
        must_clauses.append({"match_phrase": {"gemeente": gemeente}})

    body = {
        "from": from_,
        "size": size,
        "query": {
            "bool": {"must": must_clauses if must_clauses else {"match_all": {}}}
        },
        "aggs": {
            "themas": {"terms": {"field": "themas.keyword"}},
            "gemeentes": {"terms": {"field": "gemeente.keyword"}},
            "types": {"terms": {"field": "type.keyword"}},
        },
        "sort": [
            {
                f"{sort_by}.keyword"
                if sort_by in ["naam", "gemeente", "type"]
                else sort_by: {"order": sort_order}
            }
        ],
    }

    console.log(f"🔎 Search body: {body}")
    return dict(client.search(index=INDEX_NAME, body=body).body)
