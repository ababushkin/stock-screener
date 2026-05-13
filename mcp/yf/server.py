import sys

print("[yf] yfinance MCP server ready", file=sys.stderr)

from mcp.server.fastmcp import FastMCP
from tools import YFNoDataError, FXNoDataError, get_analyst_targets as _get_analyst_targets, get_earnings_history as _get_earnings_history, get_estimates as _get_estimates, get_financials as _get_financials, get_fx_rate as _get_fx_rate, get_ratios as _get_ratios

mcp = FastMCP("yf")


@mcp.tool()
def get_earnings_history(ticker: str, n: int = 4) -> list:
    """Last n quarters of EPS history: quarter, reported_eps, estimated_eps, surprise_pct. Max 4q (yfinance cap)."""
    return _get_earnings_history(ticker, n)


@mcp.tool()
def get_analyst_targets(ticker: str) -> dict:
    """Analyst price targets and buy/hold/sell counts: avg_target, high_target, low_target, buy_count, hold_count, sell_count."""
    return _get_analyst_targets(ticker)


@mcp.tool()
def get_ratios(ticker: str) -> dict:
    """Valuation ratios for a ticker: pe_ratio, ps_ratio, ev_ebitda, pfcf, ev_revenue."""
    return _get_ratios(ticker)


@mcp.tool()
def get_estimates(ticker: str) -> dict:
    """NTM consensus estimates: ntm_eps, ntm_revenue, analyst_count."""
    return _get_estimates(ticker)


@mcp.tool()
def get_fx_rate(base: str, quote: str) -> dict:
    """Latest daily close FX rate for base→quote (e.g. USD→KZT): base, quote, rate, date, source."""
    return _get_fx_rate(base, quote)


@mcp.tool()
def get_financials(ticker: str, period: str = "annual") -> dict:
    """Multi-year financials: revenue, operating_income, net_income, free_cash_flow, stock_based_compensation, total_debt, cash."""
    return _get_financials(ticker, period)


if __name__ == "__main__":
    mcp.run()
