import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import typer
from rich.console import Console
from rich.progress import Progress

app = typer.Typer(help="📥 Dienstencatalogus CLI")
console = Console()

BASE_URL = "https://cms.verenigingsloket.be/api/aangeboden-producten-pagina"
RAW_DIR = Path("data/raw")
RAW_FILE = RAW_DIR / "aangeboden-producten.json"


@app.command()
def say(word: str) -> None:
    """Echo a word back in a friendly way."""
    typer.echo(f"{word} you say?")


async def fetch_page(
    client: httpx.AsyncClient, page: int, per_page: int = 100
) -> list[dict[str, Any]]:
    """Fetch a single paginated page of records from the Dienstencatalogus API."""
    params: dict[str, str | int] = {
        "index": page,
        "limiet": per_page,
        "sorteeroptie": "last-changed",
        "_format": "json",
    }
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Referer": "https://www.verenigingsloket.be/",
        "User-Agent": "Mozilla/5.0 (compatible; DataCollector/1.0)",
    }

    response = await client.get(BASE_URL, params=params, headers=headers)
    console.print()
    console.print(f"🔍 Request URL: {response.url}")
    console.print(f"🔍 Status code: {response.status_code}")

    try:
        data: dict[str, Any] = response.json()
        items = data.get("inhoud", {}).get("elementen", [])
        console.print(f"📦 Page {page}: {len(items)} items")
        return list(items) if isinstance(items, list) else []
    except (json.JSONDecodeError, KeyError) as e:
        console.print(f"❌ JSON decode error on page {page}: {e}")
        console.print(f"🧾 Raw response:\n{response.text}")
        return []


@app.command()
def ingest(max_pages: int = 50, per_page: int = 100, start_at: int = 1) -> None:
    """Fetch Dienstencatalogus data and save to /data/raw as JSON.

    Args:
        max_pages (int): Maximum number of pages to fetch.
        per_page (int): Number of items per page.
        start_at (int): Starting index (1-based).

    """

    async def run() -> None:
        """Run the asynchronous data fetching."""
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        all_items = []

        console.print(
            f"📥 Fetching Dienstencatalogus data into [bold]{RAW_FILE}[/bold]"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            with Progress() as progress:
                task = progress.add_task("Fetching pages...", total=max_pages)
                for i in range(max_pages):
                    page = start_at + i
                    try:
                        items = await fetch_page(client, page, per_page)
                        if not items:
                            console.print(
                                f"✅ No more items at index {page}, stopping early."
                            )
                            break
                        all_items.extend(items)
                        progress.update(task, advance=1)
                    except (httpx.HTTPError, json.JSONDecodeError) as e:
                        console.print(f"[red]⚠️ Failed on index {page}: {e}[/red]")
                        break

        with RAW_FILE.open("w", encoding="utf-8") as f:
            json.dump(all_items, f, indent=2, ensure_ascii=False)

        console.print(f"✅ Saved [bold]{len(all_items)}[/bold] records to {RAW_FILE}")

    asyncio.run(run())
