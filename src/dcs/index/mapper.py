from dcs.models.product import CleanedProduct


def product_to_es_doc(product: CleanedProduct) -> dict[str, object]:
    """Convert a CleanedProduct to an Elasticsearch document."""
    voorwaarden_vorm = []
    voorwaarden_regio = []
    voorwaarden_vereniging = []

    for item in product.voorwaarden:
        for key, value in item.items():
            if key.lower() == "vorm":
                voorwaarden_vorm.append(value)
            elif key.lower() == "regio":
                voorwaarden_regio.append(value)
            elif key.lower() == "vereniging":
                voorwaarden_vereniging.append(value)

    return {
        "id": product.id,
        "naam": product.naam,
        "omschrijving": product.omschrijving_clean,
        "type": product.type,
        "themas": product.themas,
        "gemeente": product.gemeente,
        "voorwaarden_vorm": voorwaarden_vorm,
        "voorwaarden_regio": voorwaarden_regio,
        "voorwaarden_vereniging": voorwaarden_vereniging,
        "keywords": product.keywords,
    }


def extract_voorwaarden(voorwaarden: list[dict[str, str]], label: str) -> list[str]:
    """Extract a list of voorwaarden based on the given label."""
    return [v[label] for v in voorwaarden if v.get(label)]
