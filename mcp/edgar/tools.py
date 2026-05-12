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
