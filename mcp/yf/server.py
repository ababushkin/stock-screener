import sys

print("[yf] yfinance MCP server ready", file=sys.stderr)

from mcp.server.fastmcp import FastMCP
from tools import YFNoDataError, get_estimates as _get_estimates, get_ratios as _get_ratios

mcp = FastMCP("yf")


@mcp.tool()
def get_ratios(ticker: str) -> dict:
    """Valuation ratios for a ticker: pe_ratio, ps_ratio, ev_ebitda, pfcf, ev_revenue."""
    return _get_ratios(ticker)


@mcp.tool()
def get_estimates(ticker: str) -> dict:
    """NTM consensus estimates: ntm_eps, ntm_revenue, analyst_count."""
    return _get_estimates(ticker)


if __name__ == "__main__":
    mcp.run()
