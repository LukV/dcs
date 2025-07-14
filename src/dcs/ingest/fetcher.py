import asyncio
import json
from typing import Any

import httpx
from rich.console import Console
from rich.progress import Progress

from dcs.utils.config import BASE_URL, RAW_DIR, RAW_FILE

console = Console()


async def fetch_page(
    client: httpx.AsyncClient, page: int, per_page: int
) -> list[dict[str, Any]]:
    """Fetch a single paginated page of records from Verenigingsloket CMS."""
    params = {
        "index": str(page),
        "limiet": str(per_page),
        "sorteeroptie": "last-changed",
        "_format": "json",
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Referer": "https://www.verenigingsloket.be/",
        "User-Agent": "Mozilla/5.0 (compatible; DataCollector/1.0)",
    }

    response = await client.get(BASE_URL, params=params, headers=headers)
    console.print(f"🔍 Page {page} → Status {response.status_code}")
    data = response.json()
    return data.get("inhoud", {}).get("elementen", [])  # type: ignore  # noqa: PGH003


async def fetch_all(
    max_pages: int, per_page: int, start_at: int
) -> list[dict[str, Any]]:
    """Fetch multiple pages of records from Verenigingsloket CMS."""
    all_items = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        with Progress() as progress:
            task = progress.add_task("Fetching pages...", total=max_pages)
            for i in range(max_pages):
                page = start_at + i
                items = await fetch_page(client, page, per_page)
                if not items:
                    console.print(f"✅ No more items at page {page}")
                    break
                all_items.extend(items)
                progress.update(task, advance=1)
    return all_items


def fetch(max_pages: int, per_page: int, start_at: int) -> None:
    """Fetch Dienstencatalogus data and save to /data/raw as JSON."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    all_items = asyncio.run(fetch_all(max_pages, per_page, start_at))
    with RAW_FILE.open("w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)
    console.print(f"✅ Saved {len(all_items)} items to {RAW_FILE}")
