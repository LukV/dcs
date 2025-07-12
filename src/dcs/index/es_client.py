import os

import dotenv
from elasticsearch import Elasticsearch

# Load environment
dotenv.load_dotenv(override=True)

# Database connection URL
ELASTIC_URL = os.getenv("ELASTIC_URL")


def get_client() -> Elasticsearch:
    """Get Elastic Search client."""
    return Elasticsearch(ELASTIC_URL)
