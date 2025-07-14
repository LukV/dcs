from typing import Any

from elasticsearch import Elasticsearch
from rich.console import Console

console = Console()


def search_diensten(  # noqa: PLR0913
    client: Elasticsearch,
    ix: str = "diensten",
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
    return dict(client.search(index=ix, body=body).body)
