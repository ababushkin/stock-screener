import html as _html_mod
import re
import sys
from datetime import date

import requests

EDGAR_BASE = "https://data.sec.gov"
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_HEADERS = {"User-Agent": "stock-review babushkin.anton@gmail.com"}
_ANNUAL_FORMS = {"10-K", "10-K/A"}


class EDGARNoDataError(Exception):
    """EDGAR returned no usable data for this ticker or concept."""


def _get_cik(ticker: str) -> str:
    """Return zero-padded 10-digit CIK for ticker, or raise EDGARNoDataError."""
    resp = requests.get(_TICKERS_URL, headers=_HEADERS)
    resp.raise_for_status()
    data = resp.json()
    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry["ticker"].upper() == ticker_upper:
            return str(entry["cik_str"]).zfill(10)
    raise EDGARNoDataError(
        f"ticker {ticker!r} not found in EDGAR company tickers list"
    )


def search_filings(ticker: str, form_type: str) -> list[dict]:
    """Return recent filings of form_type for ticker.

    Each entry has: accession_number, filing_date, form, primary_document.
    """
    cik = _get_cik(ticker)
    url = f"{EDGAR_BASE}/submissions/CIK{cik}.json"
    resp = requests.get(url, headers=_HEADERS)
    resp.raise_for_status()
    data = resp.json()

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])
    docs = recent.get("primaryDocument", [])

    results = []
    for form, accn, filed, doc in zip(forms, accessions, dates, docs):
        if form == form_type:
            results.append({
                "accession_number": accn,
                "filing_date": filed,
                "form": form,
                "primary_document": doc,
            })
    return results


def get_filing_facts(ticker: str, concept: str) -> dict:
    """Return the most recent annual (10-K) value for an XBRL concept.

    Searches us-gaap namespace. concept is the bare concept name,
    e.g. "ShareBasedCompensation".

    Returns dict with: ticker, concept, value, unit, period_end, form, filed.
    """
    cik = _get_cik(ticker)
    url = f"{EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik}.json"
    resp = requests.get(url, headers=_HEADERS)
    resp.raise_for_status()
    data = resp.json()

    facts = data.get("facts", {})
    us_gaap = facts.get("us-gaap", {})

    if concept not in us_gaap:
        raise EDGARNoDataError(
            f"concept {concept!r} not found in us-gaap facts for {ticker}"
        )

    concept_data = us_gaap[concept]
    units = concept_data.get("units", {})

    # Prefer USD; fall back to first available unit
    unit_key = "USD" if "USD" in units else (next(iter(units), None))
    if unit_key is None:
        raise EDGARNoDataError(
            f"concept {concept!r} for {ticker} has no unit data"
        )

    entries = units[unit_key]

    # Keep only annual filings, then pick the one with the latest period end.
    # On tie, pick the most recently filed.
    annual = [e for e in entries if e.get("form") in _ANNUAL_FORMS]
    if not annual:
        raise EDGARNoDataError(
            f"concept {concept!r} for {ticker} has no 10-K entries"
        )

    best = max(annual, key=lambda e: (e["end"], e["filed"]))

    return {
        "ticker": ticker,
        "concept": concept,
        "value": best["val"],
        "unit": unit_key,
        "period_end": best["end"],
        "form": best["form"],
        "filed": best["filed"],
    }


# ---------------------------------------------------------------------------
# get_filing_text
# ---------------------------------------------------------------------------

# Common section name aliases → regex patterns searched against raw HTML text.
_SECTION_ALIASES: dict[str, list[str]] = {
    "md&a": [
        r"management.{0,20}s?\s+discussion.{0,50}analysis",
    ],
    "risk factors": [
        r"item\s+1a\b.{0,30}risk\s+factors",
        r"risk\s+factors",
    ],
    "business": [
        r"item\s+1\b(?![ab]).{0,20}business",
    ],
    "financial statements": [
        r"item\s+8\b.{0,30}financial\s+statements",
    ],
}

# Pattern that marks the start of ANY numbered item — used to find the end of a section.
_ITEM_BOUNDARY_RE = re.compile(r"\bitem\s+\d+[a-z]?\b", re.IGNORECASE)

_MAX_SECTION_CHARS = 50_000


def _html_to_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = _html_mod.unescape(text)
    return re.sub(r"[ \t]+", " ", text)


def _extract_section(html_text: str, section: str) -> str:
    """Find the named section in filing HTML; return stripped plain text.

    Disambiguation between TOC entries and actual section body: the TOC entry
    has very little content before the next Item marker; the actual body has
    thousands of characters.  We pick the match with the longest span.
    """
    key = section.strip().lower()
    patterns = _SECTION_ALIASES.get(key, [re.escape(section)])

    best_start: int | None = None
    best_end: int = 0
    best_span: int = -1

    for pattern in patterns:
        for m in re.finditer(pattern, html_text, re.IGNORECASE):
            # Look for the NEXT item boundary, skipping a small offset so we
            # don't immediately re-match the same item number.
            next_b = _ITEM_BOUNDARY_RE.search(html_text, m.end() + 200)
            end = next_b.start() if next_b else m.start() + _MAX_SECTION_CHARS
            span = end - m.start()
            if span > best_span:
                best_span = span
                best_start = m.start()
                best_end = end

    if best_start is None:
        raise EDGARNoDataError(f"section {section!r} not found in filing")

    raw = html_text[best_start : min(best_end, best_start + _MAX_SECTION_CHARS)]
    return re.sub(r"\s+", " ", _html_to_text(raw)).strip()


def _primary_doc_url(accession_number: str) -> str:
    """Return the URL of the primary document for a given accession number.

    Extracts CIK from the accession number (first numeric segment) and fetches
    the EDGAR directory index.json to locate the 10-K primary document.
    """
    cik = str(int(accession_number.split("-")[0]))
    accn_nodash = accession_number.replace("-", "")
    index_url = (
        f"https://www.sec.gov/Archives/edgar/data/{cik}/{accn_nodash}/index.json"
    )
    resp = requests.get(index_url, headers=_HEADERS)
    resp.raise_for_status()
    items = resp.json().get("directory", {}).get("item", [])

    # Prefer item explicitly typed as 10-K/10-K/A; fall back to first .htm file.
    for item in items:
        if item.get("type") in ("10-K", "10-K/A"):
            return (
                f"https://www.sec.gov/Archives/edgar/data/{cik}"
                f"/{accn_nodash}/{item['name']}"
            )
    for item in items:
        if item["name"].lower().endswith((".htm", ".html")):
            return (
                f"https://www.sec.gov/Archives/edgar/data/{cik}"
                f"/{accn_nodash}/{item['name']}"
            )
    raise EDGARNoDataError(f"no primary document found for {accession_number}")


def get_filing_text(accession_number: str, section: str) -> str:
    """Return plain text of a named section from an EDGAR filing.

    accession_number: EDGAR accession number, e.g. "0001045810-24-000010".
    section: section name — "MD&A", "Risk Factors", "Business", etc.
    """
    doc_url = _primary_doc_url(accession_number)
    resp = requests.get(doc_url, headers=_HEADERS)
    resp.raise_for_status()
    return _extract_section(resp.text, section)
