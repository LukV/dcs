from typing import TypedDict

from pydantic import BaseModel, Field


class Partner(BaseModel):
    """Model representing a partner in the Dienstencatalogus."""

    naam: str


class Voorwaarde(BaseModel):
    """Model representing a condition in the Dienstencatalogus."""

    tekst: str = ""


class Thema(BaseModel):
    """Model representing a theme in the Dienstencatalogus."""

    naam: str


class Metadata(BaseModel):
    """Model representing metadata for a product in the Dienstencatalogus."""

    laatsteWijzigingsdatum: str = ""  # noqa: N815


class Product(BaseModel):
    """Model representing a product in the Dienstencatalogus."""

    id: str
    naam: str
    type: str
    omschrijving: str = ""
    metadata: Metadata
    voorwaarden: dict[str, Voorwaarde] = {}
    partners: list[Partner] = []
    themas: dict[str, Thema] = {}


class DienstRecord(BaseModel):
    """Model representing a Dienstencatalogus record."""

    product: Product


class RegioVoorwaarde(TypedDict):
    """Type for a condition based on region."""

    regio: list[str]


class ThemaVoorwaarde(TypedDict):
    """Type for a condition based on theme."""

    thema: list[str]


class VormVoorwaarde(TypedDict):
    """Type for a condition based on form."""

    vorm: list[str]


class VerenigingVoorwaarde(TypedDict):
    """Type for a condition based on association."""

    vereniging: list[str]


VoorwaardeType = (
    RegioVoorwaarde | ThemaVoorwaarde | VormVoorwaarde | VerenigingVoorwaarde
)


class CleanedProduct(BaseModel):
    """Model for a cleaned product with normalized fields."""

    id: str
    naam: str
    type: str | None = None
    omschrijving: str | None = None
    voorwaarden: list[VoorwaardeType] = Field(default_factory=list)
    omschrijving_clean: str | None = None
    voorwaarden_clean: str | None = None
    themas: list[str] = Field(default_factory=list)
    gemeente: str | None = None
    laatste_wijzigingsdatum: str | None = None
    keywords: list[str] = Field(default_factory=list)
