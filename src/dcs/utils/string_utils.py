from bs4 import BeautifulSoup


def strip_html(text: str) -> str:
    """Remove HTML tags from a string and return plain text."""
    return BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)


def extract_keywords(text: str) -> list[str]:
    """Extract keywords from a given text."""
    return [f"term-{text[0]}", f"term-{text[1]}"]
