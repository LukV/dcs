import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from dcs.index.es_client import get_client
from dcs.index.indexer import drop_index, index_all, search_diensten
from dcs.ingest.cleaner import clean_all
from dcs.ingest.fetcher import ingest

console = Console()
app = typer.Typer(help="📥 Dienstencatalogus CLI")


@app.command()
def say(word: str) -> None:
    """Echo the word you say."""
    typer.echo(f"{word} you say?")


@app.command()
def fetch(max_pages: int = 50, per_page: int = 100, start_at: int = 1) -> None:
    """Download raw Dienstencatalogus data to disk."""
    ingest(max_pages, per_page, start_at)


@app.command()
def clean() -> None:
    """Clean downloaded Dienstencatalogus data."""
    clean_all()


@app.command()
def index() -> None:
    """Index cleaned Dienstencatalogus records into Elasticsearch."""
    index_all()


@app.command()
def drop() -> None:
    """Drop the Elasticsearch index."""
    client = get_client()
    drop_index(client)


@app.command()
def search(  # noqa: PLR0913
    query: str | None = typer.Option(None, help="Zoekterm"),
    thema: list[str] | None = typer.Option(None, help="Filter op thema"),  # noqa: B008
    gemeente: str | None = typer.Option(None, help="Filter op gemeente"),
    sort_by: str = typer.Option(
        "relevance", help="Sorteerveld (relevance, naam, laatste_wijzigingsdatum)"
    ),
    sort_order: str = typer.Option("asc", help="asc of desc"),
    from_: int = typer.Option(0, help="Offset"),
    size: int = typer.Option(10, help="Aantal resultaten"),
    profile: Path | None = typer.Option(None, help="JSON-pad vereniging profiel"),  # noqa: B008
) -> None:
    """Search the Diensten index."""
    client = get_client()

    vereniging_profile = None
    if profile:
        with Path.open(profile, encoding="utf-8") as f:
            vereniging_profile = json.load(f)

    result = search_diensten(
        client,
        query=query,
        themas=thema,
        gemeente=gemeente,
        sort_by=sort_by,
        sort_order=sort_order,
        from_=from_,
        size=size,
        vereniging_profile=vereniging_profile,
    )

    hits = result["hits"]["hits"]
    table = Table(title="\n🔍 Zoekresultaten", show_lines=True)

    table.add_column("Naam", style="bold")
    table.add_column("ID")
    table.add_column("Score", justify="right", style="dim")

    for hit in hits:
        source = hit["_source"]
        score = hit.get("_score")
        score_display = f"{score:.2f}" if score is not None else "n/a"
        table.add_row(source["naam"], source["id"][:10], score_display)

    console.print(table)

    typer.echo("\n📊 Facetten:")
    for facet_name in ["themas", "gemeentes", "types"]:
        typer.echo(f"\n{facet_name.capitalize()}:")
        for bucket in result["aggregations"][facet_name]["buckets"]:
            typer.echo(f"  {bucket['key']} ({bucket['doc_count']})")
