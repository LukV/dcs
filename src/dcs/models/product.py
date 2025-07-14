from pydantic import BaseModel, Field

VoorwaardeType = dict[str, list[str]]


class Product(BaseModel):
    """Normalized, ES-ready Dienstencatalogus product."""

    id: str
    naam: str
    type: str | None = None
    omschrijving: str | None = None
    omschrijving_clean: str | None = None
    themas: list[str] = Field(default_factory=list)
    toepassingsgebied: str | None = None
    laatste_wijzigingsdatum: str | None = None
    voorwaarden: list[VoorwaardeType] = Field(default_factory=list)
    match: str = "0000"
    """Derived 4-digit keyword used for filtering and boosting in search.

    Meaning of each digit:
    - [0] Vereniging:
        '1' if includes 'LIGHT MODELS AERO CLUB' or 'L.M.A.C.'
        '2' if vereniging is present but different
        '0' if no vereniging
    - [1] Regio: '1' if regio includes 'Leuven' or 'Vlaams-Brabant'
    - [2] Vorm: '1' if vorm includes 'VZW'
    - [3] Thema: '1' if thema includes 'Economie en Werk' or 'Technologie en Wetenschap'
    """
