import typer

from dcs.index.es_client import get_client
from dcs.index.indexer import drop_index, index_all, search_diensten
from dcs.ingest.cleaner import clean_all
from dcs.ingest.fetcher import ingest

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
        "naam", help="Sorteerveld (bv. naam, laatste_wijzigingsdatum)"
    ),
    sort_order: str = typer.Option("asc", help="asc of desc"),
    from_: int = typer.Option(0, help="Offset"),
    size: int = typer.Option(10, help="Aantal resultaten"),
) -> None:
    """Search the Diensten index."""
    client = get_client()
    result = search_diensten(
        client,
        query=query,
        themas=thema,
        gemeente=gemeente,
        sort_by=sort_by,
        sort_order=sort_order,
        from_=from_,
        size=size,
    )

    hits = result["hits"]["hits"]
    typer.echo(f"\n🔍 Resultaten ({len(hits)}):")
    for hit in hits:
        source = hit["_source"]
        typer.echo(f"- {source['naam']} ({source['type']})")

    typer.echo("\n📊 Facetten:")
    for facet_name in ["themas", "gemeentes", "types"]:
        typer.echo(f"\n{facet_name.capitalize()}:")
        for bucket in result["aggregations"][facet_name]["buckets"]:
            typer.echo(f"  {bucket['key']} ({bucket['doc_count']})")
