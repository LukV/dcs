import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from dcs.ingest.cleaner import clean_all
from dcs.ingest.fetcher import fetch
from dcs.lexicalsearch.es_client import get_client
from dcs.lexicalsearch.index import drop_index, index_all
from dcs.lexicalsearch.search import search_diensten

console = Console()
app = typer.Typer(help="📥 Dienstencatalogus CLI")


@app.command()
def say(word: str) -> None:
    """Echo the word you say."""
    typer.echo(f"{word} you say?")


@app.command("fetch")
def fetcher(max_pages: int = 50, per_page: int = 100, start_at: int = 1) -> None:
    """Download raw Dienstencatalogus data to disk."""
    fetch(max_pages, per_page, start_at)


@app.command()
def clean(
    output_file: Path = typer.Argument(  # noqa: B008
        ...,
        help="Pad naar het uitvoerbestand waarin de opgeschoonde JSON-data wordt weggeschreven.",  # noqa: E501
    ),
) -> None:
    """Clean downloaded Dienstencatalogus data."""
    clean_all(output_file=output_file)


@app.command()
def index(
    index_name: str = typer.Argument(
        ..., help="Naam van de Elasticsearch-index (verplicht)"
    ),
    file_path: Path = typer.Argument(  # noqa: B008
        ...,
        exists=True,
        readable=True,
        help="Pad naar het JSON-bestand met te indexeren records",
    ),
) -> None:
    """Indexeert records uit een JSON-bestand in de opgegeven Elasticsearch-index."""
    typer.echo(f"📥 Indexeren van bestand: {file_path}")
    typer.echo(f"📦 Doelindex: {index_name}")

    index_all(index_name=index_name, file_path=file_path)


@app.command()
def drop(
    index: str = typer.Argument(
        help="Te verwijderen index",
    ),
) -> None:
    """Drop the Elasticsearch index."""
    client = get_client()
    drop_index(client, ix=index)


@app.command()
def search(  # noqa: PLR0913
    ix: str = typer.Option(
        "diensten",
        help="Te doorzoeken index (standaard: diensten)",
    ),
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
        ix=ix,
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
