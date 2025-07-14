import json
from pathlib import Path

from elastic_transport import ApiError
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from rich.console import Console

from dcs.lexicalsearch.es_client import get_client
from dcs.lexicalsearch.map import product_to_es_doc
from dcs.models.product import Product

console = Console()

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


def drop_index(client: Elasticsearch, ix: str) -> None:
    """Drop the Elasticsearch index if it exists."""
    try:
        if client.indices.exists(index=ix):
            client.indices.delete(index=ix)
            console.print(f"🗑️ Dropped index '{ix}'.")
        else:
            console.print(f"⚠️ Index '{ix}' does not exist.")
    except Exception as e:
        console.print(f"🔥 Failed to delete index '{ix}': {e}")
        raise


def create_index(client: Elasticsearch, index_name: str) -> None:
    """Create the Elasticsearch index with the defined mapping."""
    try:
        if index_name in client.indices.get_alias():
            console.print(f"Index '{index_name}' already exists.")
            return

        client.indices.create(index=index_name, body=MAPPING)
        console.print(f"✅ Created index '{index_name}'.")

    except Exception as e:
        console.print(f"🔥 Failed to create index '{index_name}': {e}")
        if isinstance(e, ApiError) and e.body:
            console.print(e.body)
        raise


def index_all(index_name: str, file_path: Path) -> None:
    """Index all cleaned Dienstencatalogus records into Elasticsearch."""
    client = get_client()
    create_index(client, index_name=index_name)

    with file_path.open(encoding="utf-8") as f:
        raw_items = json.load(f)

    products = [Product(**item) for item in raw_items]
    actions = [{**product_to_es_doc(p), "_index": index_name} for p in products]

    bulk(client, actions)
    console.print(f"✅ Indexed {len(actions)} producten into index '{index_name}'")
