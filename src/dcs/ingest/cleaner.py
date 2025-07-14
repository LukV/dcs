import json
import random
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import track

from dcs.models.product import Product, VoorwaardeType
from dcs.utils.config import CLEANED_DIR, RAW_DIR
from dcs.utils.string_utils import strip_html

console = Console()


def clean_item(raw: dict[str, Any], index: int) -> Product:
    """Clean a single raw Dienstencatalogus record into a normalized Product."""
    product = raw.get("product", {})
    ipdc = product.get("ipdcProduct", {})

    id_ = product.get("id")
    naam = product.get("naam")
    type_ = product.get("type")
    omschrijving = product.get("omschrijving", "")
    omschrijving_clean = strip_html(omschrijving)

    # Thema
    themas_raw = product.get("themas", {}).get("elementen", [])
    themas = [t["naam"] for t in themas_raw if isinstance(t, dict) and "naam" in t]

    # Toepassingsgebied
    geo = ipdc.get("geografischeToepassingsgebieden", {}).get("elementen", [])
    toepassingsgebied = geo[0]["label"] if geo else None

    # Datum
    metadata = product.get("metadata", {})
    laatste_wijzigingsdatum = metadata.get("laatsteWijzigingsdatum", "")[:10]

    # Voorwaarden
    voorwaarden: list[VoorwaardeType] = []

    if toepassingsgebied:
        voorwaarden.append({"regio": [toepassingsgebied]})

    if themas:
        voorwaarden.append({"thema": themas})

    vorm_options = [["VZW"], ["Vereniging"], ["Vereniging", "VZW"]]
    voorwaarden.append({"vorm": random.choice(vorm_options)})  # noqa: S311

    # Extra filters for test cases
    if (index - 10) % 500 == 0:
        voorwaarden.append({"vereniging": ["LIGHT MODELS AERO CLUB"]})

    if (index - 15) % 200 == 0:
        voorwaarden.append({"vereniging": ["Joris Zwanzeleer"]})

    return Product(
        id=id_,
        naam=naam,
        type=type_,
        omschrijving=omschrijving,
        omschrijving_clean=omschrijving_clean,
        themas=themas,
        toepassingsgebied=toepassingsgebied,
        laatste_wijzigingsdatum=laatste_wijzigingsdatum,
        voorwaarden=voorwaarden,
        match=compute_match(voorwaarden),
    )


def clean_all(output_file: Path) -> None:
    """Clean all raw Dienstencatalogus records into a single JSON file."""
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    raw_files = sorted(RAW_DIR.glob("aangeboden-producten__*.json"))
    if not raw_files:
        console.print("[red]❌ No raw files found[/red]")
        return

    all_items = []
    i = 0
    for path in track(raw_files, description="Cleaning..."):
        with path.open(encoding="utf-8") as f:
            raw_records = json.load(f)
            for record in raw_records:
                item = clean_item(record, i)
                all_items.append(item.model_dump())
                i += 1

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)

    console.print(f"✅ Saved {len(all_items)} cleaned records to {output_file}")


def compute_match(voorwaarden: list[VoorwaardeType]) -> str:
    """Compute a match string based on the provided conditions."""
    match = ["0"] * 4

    for voorwaarde in voorwaarden:
        if "vereniging" in voorwaarde:
            if any(
                v in {"LIGHT MODELS AERO CLUB", "L.M.A.C."}
                for v in voorwaarde["vereniging"]
            ):
                match[0] = "1"
            elif match[0] == "0":  # Only upgrade to 2 if not already 1
                match[0] = "2"

        elif "regio" in voorwaarde:
            if any(r in {"Leuven", "Vlaams-Brabant"} for r in voorwaarde["regio"]):
                match[1] = "1"

        elif "vorm" in voorwaarde:
            if "VZW" in voorwaarde["vorm"]:
                match[2] = "1"

        elif "thema" in voorwaarde and any(
            t in {"Economie en Werk", "Technologie en Wetenschap"}
            for t in voorwaarde["thema"]
        ):
            match[3] = "1"

    return "".join(match)
