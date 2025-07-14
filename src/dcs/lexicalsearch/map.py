from dcs.models.product import Product


def product_to_es_doc(product: Product) -> dict[str, object]:
    """Convert a Product to a flat Elasticsearch document."""

    def flatten(label: str) -> list[str]:
        return [
            v
            for item in product.voorwaarden
            for k, vs in item.items()
            if k == label
            for v in vs  # type: ignore  # noqa: PGH003
        ]

    return {
        "id": product.id,
        "naam": product.naam,
        "omschrijving": product.omschrijving_clean,
        "type": product.type,
        "themas": product.themas,
        "toepassingsgebied": product.toepassingsgebied,
        "voorwaarden_vorm": flatten("vorm"),
        "voorwaarden_regio": flatten("regio"),
        "voorwaarden_vereniging": flatten("vereniging"),
        "voorwaarden_thema": flatten("thema"),
        "match": product.match,
    }
