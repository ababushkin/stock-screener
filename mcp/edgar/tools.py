import html as _html_mod
import re
import sys
from datetime import date

import requests

EDGAR_BASE = "https://data.sec.gov"
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_HEADERS = {"User-Agent": "stock-review babushkin.anton@gmail.com"}
_ANNUAL_FORMS = {"10-K", "10-K/A"}

# Annual forms including the 20-F foreign private issuer report. Used only by
# get_sbc — the other tools stay 10-K-only to preserve their existing behaviour.
_ANNUAL_FORMS_FPI = _ANNUAL_FORMS | {"20-F", "20-F/A"}

# SBC concept candidates, tried in order. US filers tag the cash-flow add-back
# under us-gaap; IFRS filers (20-F foreign private issuers like KSPI) tag the
# employee share-based payment expense under ifrs-full. Only concepts verified
# against live companyfacts are listed — adding unverified element names risks
# silently matching the wrong fact.
_SBC_CONCEPTS = [
    ("us-gaap", "ShareBasedCompensation"),
    ("ifrs-full", "ExpenseFromSharebasedPaymentTransactionsWithEmployees"),
]


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


def get_sbc(ticker: str, periods: int = 4) -> dict:
    """Return up to `periods` years of stock-based compensation from XBRL facts.

    Reads the SBC line straight from the companyfacts cash-flow / income facts,
    covering both US filers (10-K, us-gaap:ShareBasedCompensation) and foreign
    private issuers (20-F, ifrs-full:ExpenseFromSharebasedPaymentTransactions-
    WithEmployees). This is the fallback /stock-signal uses when yfinance returns
    null SBC — common for non-US filers whose 20-F cash-flow line Yahoo doesn't
    normalise.

    The two concepts are close but not definitionally identical: the us-gaap one
    is the cash-flow-statement non-cash add-back; the ifrs-full one is the
    income-statement employee share-based-payment expense (which excludes
    non-employee/supplier awards and any capitalised amounts). For EPS stripping
    they are a sound proxy for each other, but they are not a like-for-like
    substitute — treat the ifrs-full figure as an approximation of the cash-flow
    SBC, not an exact equal.

    Candidates are tried us-gaap first, then ifrs-full: the us-gaap cash-flow
    figure is the closest match to the yfinance value being replaced, so a filer
    that tags both resolves to us-gaap. A namespace whose concept carries no
    annual-form entries (only quarterly) is skipped, so an FPI lacking real
    us-gaap annual data falls through to ifrs-full.

    SBC is a flow (duration) fact, so the same fiscal year appears once per
    filing that restates it; entries are deduplicated by period-end, keeping the
    most recently filed value.

    Returns:
        {
            "ticker": str,
            "filing_type": str,       # "10-K" or "20-F" — the form the values came from
            "currency": str,          # reporting currency, e.g. "USD" or "KZT"
            "periods": [              # newest first, up to `periods` entries
                {"fiscal_year": "YYYY-MM-DD", "sbc": int, "source": "edgar_xbrl"},
                ...
            ],
        }

    Raises:
        EDGARNoDataError: ticker unknown, or no SBC concept present in any annual
            filing — the caller should treat this as "SBC line not present in
            filing" (some issuers genuinely report $0 / no SBC).
    """
    if periods < 1:
        raise ValueError(f"periods must be >= 1, got {periods}")

    cik = _get_cik(ticker)
    url = f"{EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik}.json"
    resp = requests.get(url, headers=_HEADERS)
    resp.raise_for_status()
    facts = resp.json().get("facts", {})

    for namespace, concept in _SBC_CONCEPTS:
        concept_data = facts.get(namespace, {}).get(concept)
        if not concept_data:
            continue

        units = concept_data.get("units", {})
        # Group annual-form entries by reporting currency, dropping currencies
        # with no annual data.
        annual_by_unit = {
            unit: annual
            for unit, entries in units.items()
            if (annual := [e for e in entries if e.get("form") in _ANNUAL_FORMS_FPI])
        }
        if not annual_by_unit:
            continue

        # Prefer USD; otherwise pick deterministically — the currency with the
        # most annual entries (the filer's primary reporting currency), breaking
        # ties on the currency code so the result never depends on dict ordering.
        if "USD" in annual_by_unit:
            unit_key = "USD"
        else:
            unit_key = sorted(
                annual_by_unit, key=lambda u: (-len(annual_by_unit[u]), u)
            )[0]
        annual = annual_by_unit[unit_key]

        # Dedupe by period-end; keep the most recently filed value on collision.
        by_end: dict[str, dict] = {}
        for e in annual:
            end = e["end"]
            if end not in by_end or e["filed"] > by_end[end]["filed"]:
                by_end[end] = e

        selected = sorted(by_end.values(), key=lambda e: e["end"], reverse=True)[
            :periods
        ]
        filing_type = selected[0]["form"]

        return {
            "ticker": ticker,
            "filing_type": filing_type,
            "currency": unit_key,
            "periods": [
                {
                    "fiscal_year": e["end"],
                    "sbc": e["val"],
                    "source": "edgar_xbrl",
                }
                for e in selected
            ],
        }

    raise EDGARNoDataError(
        f"no stock-based-compensation concept present in any annual filing for "
        f"{ticker}; tried {', '.join(f'{ns}:{c}' for ns, c in _SBC_CONCEPTS)}. "
        f"SBC line not present in filing (issuer may genuinely have $0 SBC)."
    )


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
    "segment information": [
        r"segment\s+information(?:\s+and\s+geographic\s+data)?",
        r"note\s+\w+\s*.{0,10}segment",
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


def _primary_doc_url(accession_number: str, cik: str | None = None) -> str:
    """Return the URL of the primary document for a given accession number.

    Uses the EDGAR submissions endpoint (same source as search_filings) so
    the primaryDocument field is always correct. Falls back to the directory
    index filtered to skip index headers, XBRL viewer, and exhibit files.
    """
    accn_nodash = accession_number.replace("-", "")
    # cik_path is the unpadded CIK used in EDGAR archive URLs.
    # When cik is provided (zero-padded 10-digit string from _get_cik), strip
    # leading zeros; otherwise derive from the accession's first segment.
    cik_padded = cik if cik is not None else accession_number.split("-")[0].zfill(10)
    cik_path = str(int(cik_padded))  # strip leading zeros for URL path

    # Primary path: look up the accession number in the submissions feed.
    sub_url = f"{EDGAR_BASE}/submissions/CIK{cik_padded}.json"
    resp = requests.get(sub_url, headers=_HEADERS)
    resp.raise_for_status()
    recent = resp.json().get("filings", {}).get("recent", {})
    for accn, doc in zip(recent.get("accessionNumber", []), recent.get("primaryDocument", [])):
        if accn.replace("-", "") == accn_nodash:
            return (
                f"https://www.sec.gov/Archives/edgar/data/{cik_path}"
                f"/{accn_nodash}/{doc}"
            )

    # Fallback: directory index, skipping non-primary files.
    index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_path}/{accn_nodash}/index.json"
    resp2 = requests.get(index_url, headers=_HEADERS)
    resp2.raise_for_status()
    items = resp2.json().get("directory", {}).get("item", [])
    for item in items:
        name = item["name"]
        name_l = name.lower()
        if (name_l.startswith(accn_nodash.lower()[:10])   # accession-prefixed index
                or re.match(r"^r\d+\.html?$", name_l)     # XBRL viewer R*.htm
                or re.search(r"ex\d", name_l)):            # exhibit files
            continue
        if name_l.endswith((".htm", ".html")):
            return f"https://www.sec.gov/Archives/edgar/data/{cik_path}/{accn_nodash}/{name}"

    raise EDGARNoDataError(f"no primary document found for {accession_number}")


_REVENUE_CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
]

_SEGMENT_AXIS = "srt:StatementBusinessSegmentsAxis"


def _clean_segment_name(raw: str) -> str:
    """Convert XBRL member string to human-readable segment name."""
    if ":" in raw:
        raw = raw.split(":", 1)[1]
    for suffix in ("Member", "Segment"):
        if raw.endswith(suffix):
            raw = raw[: -len(suffix)]
    return re.sub(r"([A-Z])", r" \1", raw).strip()


def _parse_segment_revenues(text: str) -> list[dict]:
    """Extract segment revenues from the plain-text segment note.

    Looks for patterns of the form:
      <Segment Name> ... Revenue $ AMOUNT1 $ AMOUNT2 ...
    where AMOUNT1 is the most-recent year's figure (in millions).
    Skips the "Total" consolidated row.

    Returns [] if no segment revenue pattern is found.
    """
    # Match: (segment label)(optional text)(Revenue $ AMOUNT) on the same run of text.
    # The segment label is a multi-word title-cased phrase without $ or digits.
    pattern = re.compile(
        r"([A-Z][A-Za-z &,()'-]{4,80}?)\s+"
        r"Revenue\s+\$\s*([\d,]+)",
    )
    results = []
    for m in pattern.finditer(text):
        label = m.group(1).strip().rstrip()
        # Skip "Total" rows, header artifacts, and percentage-change context rows
        if re.search(
            r"\bTotal\b|\bYear\b|\bIn millions\b|\bJun\b|^\s*\d"
            r"|\bPercent|\bChange\b|\bConsolidat|\bCorporat|\bElimin",
            label, re.IGNORECASE,
        ):
            continue
        # Clean residual whitespace/punctuation
        label = re.sub(r"\s+", " ", label).strip(" .")
        if len(label) < 3:
            continue
        revenue_str = m.group(2).replace(",", "")
        try:
            revenue = int(revenue_str) * 1_000_000  # note: values are in millions
        except ValueError:
            continue
        results.append({"name": label, "revenue": revenue})

    # Deduplicate by name (keep highest revenue, i.e., most recent year typically)
    seen: dict[str, dict] = {}
    for r in results:
        if r["name"] not in seen or r["revenue"] > seen[r["name"]]["revenue"]:
            seen[r["name"]] = r

    return sorted(seen.values(), key=lambda x: -x["revenue"])


def get_revenue_segments(ticker: str) -> list[dict]:
    """Return revenue breakdown by business segment.

    First tries the EDGAR companyfacts API (works for companies that tag
    segment revenue with srt:StatementBusinessSegmentsAxis). Falls back to
    parsing the segment note from the 10-K filing HTML.

    Returns [] for single-segment companies — never raises for missing segments.
    """
    cik = _get_cik(ticker)

    # --- Try 1: EDGAR companyfacts API (dimensional XBRL) ---
    try:
        cf_url = f"{EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik}.json"
        resp = requests.get(cf_url, headers=_HEADERS)
        resp.raise_for_status()
        us_gaap = resp.json().get("facts", {}).get("us-gaap", {})

        segmented: list[dict] = []
        for concept in _REVENUE_CONCEPTS:
            if concept not in us_gaap:
                continue
            for entry in us_gaap[concept].get("units", {}).get("USD", []):
                if entry.get("form") not in _ANNUAL_FORMS:
                    continue
                seg = entry.get("segment")
                if seg and seg.get("dimension") == _SEGMENT_AXIS:
                    segmented.append(entry)
            if segmented:
                break

        if segmented:
            latest_end = max(e["end"] for e in segmented)
            latest = [e for e in segmented if e["end"] == latest_end]
            by_seg: dict[str, dict] = {}
            for entry in latest:
                key = entry["segment"]["value"]
                if key not in by_seg or entry["filed"] > by_seg[key]["filed"]:
                    by_seg[key] = entry
            return [
                {"name": _clean_segment_name(v), "revenue": e["val"]}
                for v, e in sorted(by_seg.items(), key=lambda x: -x[1]["val"])
            ]
    except Exception:
        pass

    # --- Try 2: Parse segment revenue table from the full 10-K filing HTML ---
    # _extract_section can pick an MD&A reference instead of the actual note, so
    # we run _parse_segment_revenues on the entire plain-text document instead.
    try:
        filings = search_filings(ticker, "10-K")
        if not filings:
            return []
        accn = filings[0]["accession_number"]
        doc_url = _primary_doc_url(accn, cik)
        resp = requests.get(doc_url, headers=_HEADERS)
        resp.raise_for_status()
        full_text = re.sub(r"\s+", " ", _html_to_text(resp.text))
        results = _parse_segment_revenues(full_text)
        return results
    except Exception:
        return []


def get_filing_text(accession_number: str, section: str) -> str:
    """Return plain text of a named section from an EDGAR filing.

    accession_number: EDGAR accession number, e.g. "0001045810-24-000010".
    section: section name — "MD&A", "Risk Factors", "Business", etc.
    """
    doc_url = _primary_doc_url(accession_number)
    resp = requests.get(doc_url, headers=_HEADERS)
    resp.raise_for_status()
    return _extract_section(resp.text, section)
