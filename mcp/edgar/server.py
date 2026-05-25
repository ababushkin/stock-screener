import sys

print("[edgar] EDGAR MCP server ready", file=sys.stderr)

from mcp.server.fastmcp import FastMCP
from tools import (
    EDGARNoDataError,
    get_filing_facts as _get_filing_facts,
    get_filing_text as _get_filing_text,
    get_revenue_segments as _get_revenue_segments,
    get_sbc as _get_sbc,
    search_filings as _search_filings,
)

mcp = FastMCP("edgar")


@mcp.tool()
def search_filings(ticker: str, form_type: str = "10-K") -> list:
    """Recent EDGAR filings for a ticker. Returns accession_number, filing_date, form."""
    return _search_filings(ticker, form_type)


@mcp.tool()
def get_filing_facts(ticker: str, concept: str) -> dict:
    """Most recent annual 10-K value for an XBRL concept (us-gaap namespace).

    Example: get_filing_facts("CRM", "ShareBasedCompensation") returns SBC in USD.
    """
    return _get_filing_facts(ticker, concept)


@mcp.tool()
def get_sbc(ticker: str, periods: int = 4) -> dict:
    """Multi-year stock-based compensation from EDGAR XBRL facts.

    Fallback for /stock-signal when yfinance returns null SBC. Covers US filers
    (10-K, us-gaap) and foreign private issuers (20-F, ifrs-full — e.g. KSPI).

    Example: get_sbc("KSPI", 4) returns 4 years of SBC in KZT from the 20-F facts.
    Returns {ticker, filing_type, currency, periods:[{fiscal_year, sbc, source}]}.
    Raises EDGARNoDataError when no SBC concept is present in any annual filing
    (treat as "SBC line not present" — the issuer may genuinely report $0 SBC).
    """
    return _get_sbc(ticker, periods)


@mcp.tool()
def get_filing_text(accession_number: str, section: str) -> str:
    """Return plain text of a named section from an EDGAR 10-K filing.

    accession_number: e.g. "0001045810-24-000010" (from search_filings).
    section: "MD&A", "Risk Factors", "Business", or "Financial Statements".
    """
    return _get_filing_text(accession_number, section)


@mcp.tool()
def get_revenue_segments(ticker: str) -> list:
    """Revenue breakdown by business segment from EDGAR XBRL facts.

    Returns a list of {'name': str, 'revenue': int} dicts sorted by revenue
    descending.  Returns [] for single-segment companies — never raises for
    missing segment data.
    """
    return _get_revenue_segments(ticker)


if __name__ == "__main__":
    mcp.run()
