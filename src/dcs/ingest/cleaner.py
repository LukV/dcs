import json
from typing import Any

from rich.console import Console
from rich.progress import track

from dcs.models.product import CleanedProduct, DienstRecord
from dcs.utils.config import CLEANED_DIR, CLEANED_FILE, RAW_DIR
from dcs.utils.string_utils import extract_keywords, strip_html

console = Console()


def clean_item(raw: dict[str, Any]) -> CleanedProduct:
    """Clean a single Dienstencatalogus record into a normalized format."""
    record = DienstRecord(**raw)
    product = record.product
    voorwaarden_raw = product.voorwaarden.get("elementen", [])  # type: ignore  # noqa: PGH003
    themas_raw = product.themas.get("elementen", [])  # type: ignore  # noqa: PGH003

    voorwaarden_text = " ".join(v.get("tekst", "") for v in voorwaarden_raw)  # type: ignore  # noqa: PGH003
    gemeente = next((p.naam for p in product.partners if p.naam), None)

    return CleanedProduct(
        id=product.id,
        naam=product.naam,
        type=product.type,
        omschrijving=product.omschrijving,
        omschrijving_clean=strip_html(product.omschrijving),
        voorwaarden_clean=strip_html(voorwaarden_text),
        themas=[t.get("naam") for t in themas_raw if "naam" in t],  # type: ignore  # noqa: PGH003
        gemeente=gemeente,
        laatste_wijzigingsdatum=product.metadata.laatsteWijzigingsdatum[:10],
        keywords=extract_keywords(product.omschrijving + " " + voorwaarden_text),
    )


def clean_all() -> None:
    """Clean all raw Dienstencatalogus JSON files into a single normalized output."""
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    raw_files = sorted(RAW_DIR.glob("aangeboden-producten__*.json"))
    if not raw_files:
        console.print("[red]❌ No raw files found[/red]")
        return

    all_items = []
    for path in track(raw_files, description="Cleaning..."):
        with path.open(encoding="utf-8") as f:
            raw_records = json.load(f)
            all_items.extend([clean_item(r).dict() for r in raw_records])

    with CLEANED_FILE.open("w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)

    console.print(f"✅ Saved {len(all_items)} cleaned records to {CLEANED_FILE}")
