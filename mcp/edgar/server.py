import sys

print("[edgar] EDGAR MCP server ready", file=sys.stderr)

from mcp.server.fastmcp import FastMCP
from tools import (
    EDGARNoDataError,
    get_filing_facts as _get_filing_facts,
    get_filing_text as _get_filing_text,
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
def get_filing_text(accession_number: str, section: str) -> str:
    """Return plain text of a named section from an EDGAR 10-K filing.

    accession_number: e.g. "0001045810-24-000010" (from search_filings).
    section: "MD&A", "Risk Factors", "Business", or "Financial Statements".
    """
    return _get_filing_text(accession_number, section)


if __name__ == "__main__":
    mcp.run()
