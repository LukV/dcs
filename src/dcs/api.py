from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="👀 Dienstencatalogus Search API", version="0.1.0")


class VerenigingProfile(BaseModel):
    """Profile for a Vereniging (Association) in the Dienstencatalogus."""

    gemeente: str | None = None
    regio: str | None = None
    doelgroep: list[str] | None = []
    sector: str | None = None


class SearchRequest(BaseModel):
    """Request model for searching the Dienstencatalogus."""

    query: str | None = None
    filters: dict[str, object] | None = {}
    profile: VerenigingProfile | None = None
    sort: str | None = "relevance"  # or "date"
    page: int | None = 1
    size: int | None = 10


@app.post("/search")
def search(request: SearchRequest) -> dict[str, object]:
    """Handle search requests."""
    return {
        "message": "Search endpoint is live",
        "received": request.model_dump(),
    }
