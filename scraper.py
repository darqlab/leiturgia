import requests
from bs4 import BeautifulSoup
import re
from hymnal import get_by_number, get_by_title

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SabbathProgram/1.0)"}


def fetch_hymn_lyrics(hymn_number: int) -> list[dict]:
    """
    Return stanzas for a hymn number.
    Tries local SQLite DB first (instant, offline), then falls back to web scraping.
    Stanzas: [{"number": N, "type": "verse"|"refrain", "lines": [...]}]
    """
    # 1. Local DB (fast, reliable, offline)
    result = get_by_number(hymn_number)
    if result and result.get("stanzas"):
        return result["stanzas"]

    # 2. Web fallback
    try:
        stanzas = _scrape_sdahymnal(hymn_number)
        if stanzas:
            return stanzas
    except Exception:
        pass
    return _scrape_hymnary(hymn_number)


def _scrape_sdahymnal(hymn_number: int) -> list[dict]:
    """Scrape from sdahymnals.com"""
    # The site uses slugs, so we search first
    search_url = f"https://sdahymnals.com/?s={hymn_number}"
    r = requests.get(search_url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    
    # Find first result link matching the hymn number
    link = None
    for a in soup.select("a[href*='/Hymnal/']"):
        href = a.get("href", "")
        slug_num = href.split("/Hymnal/")[1].split("-")[0] if "/Hymnal/" in href else ""
        if slug_num.lstrip("0") == str(hymn_number) or slug_num == str(hymn_number).zfill(3):
            link = href
            break
    
    if not link:
        return []
    
    r = requests.get(link, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    
    # Extract verse blocks
    stanzas = []
    verse_blocks = soup.select(".verse, .stanza, p")
    
    raw_text = ""
    content = soup.find("div", class_=re.compile(r"entry|content|post|lyrics", re.I))
    if content:
        raw_text = content.get_text("\n")
    
    return _parse_lyrics_text(raw_text)


def _scrape_hymnary(hymn_number: int) -> list[dict]:
    """Fallback: scrape hymnary.org"""
    # Try Trinity Hymnal (SDA equivalent numbering close enough)
    url = f"https://hymnary.org/hymn/TH1990/{hymn_number}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    
    text_div = soup.find("div", class_=re.compile(r"text|lyrics|hymn-text", re.I))
    if not text_div:
        # Try getting the full page text
        text_div = soup.find("div", {"id": re.compile(r"text|lyrics", re.I)})
    
    if text_div:
        return _parse_lyrics_text(text_div.get_text("\n"))
    
    return []


def _parse_lyrics_text(raw: str) -> list[dict]:
    """
    Parse raw multiline text into stanzas.
    Splits on blank lines or numbered verse markers.
    """
    stanzas = []
    lines = [l.strip() for l in raw.splitlines()]
    
    current_lines = []
    stanza_num = 1
    
    for line in lines:
        # Skip empty lines as stanza separators
        if not line:
            if len(current_lines) >= 2:
                stanzas.append({
                    "number": stanza_num,
                    "lines": current_lines[:]
                })
                stanza_num += 1
                current_lines = []
        else:
            # Strip leading verse numbers like "1.", "2.", "Verse 1"
            clean = re.sub(r"^(\d+\.?\s+|verse\s+\d+[.:]\s*)", "", line, flags=re.I)
            if clean:
                current_lines.append(clean)
    
    # Catch last stanza
    if len(current_lines) >= 2:
        stanzas.append({"number": stanza_num, "lines": current_lines})
    
    return stanzas


def fetch_lyrics_by_title(title: str) -> list[dict]:
    """
    Return stanzas for a hymn/song by title.
    Tries local SQLite DB first, then falls back to web scraping.
    """
    # 1. Local DB
    result = get_by_title(title)
    if result and result.get("stanzas"):
        return result["stanzas"]

    # 2. Web fallback
    try:
        stanzas = _search_sdahymnal_by_title(title)
        if stanzas:
            return stanzas
    except Exception:
        pass
    try:
        return _search_hymnary_by_title(title)
    except Exception:
        return []


def _search_sdahymnal_by_title(title: str) -> list[dict]:
    from urllib.parse import quote
    search_url = f"https://sdahymnals.com/?s={quote(title)}"
    r = requests.get(search_url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    link = None
    for a in soup.select("a[href*='/Hymnal/']"):
        link = a.get("href")
        break

    if not link:
        return []

    r = requests.get(link, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    content = soup.find("div", class_=re.compile(r"entry|content|post|lyrics", re.I))
    if content:
        return _parse_lyrics_text(content.get_text("\n"))
    return []


def _search_hymnary_by_title(title: str) -> list[dict]:
    from urllib.parse import quote
    search_url = f"https://hymnary.org/search?qu=text&q={quote(title)}"
    r = requests.get(search_url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    link = None
    for a in soup.select("a[href*='/hymn/']"):
        href = a.get("href", "")
        if href.startswith("/hymn/"):
            link = "https://hymnary.org" + href
            break

    if not link:
        return []

    r = requests.get(link, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    text_div = (soup.find("div", class_=re.compile(r"text|lyrics|hymn-text", re.I))
                or soup.find("div", {"id": re.compile(r"text|lyrics", re.I)}))
    if text_div:
        return _parse_lyrics_text(text_div.get_text("\n"))
    return []


def fetch_program(url: str) -> dict:
    """Fetch program data from a Google Sites URL (future use)."""
    r = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    # Placeholder — returns raw text for now
    return {"raw": soup.get_text("\n")}
