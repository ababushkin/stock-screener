import sys
import time
from datetime import date
from typing import Optional

import pandas as pd
import yfinance as yf


class YFNoDataError(Exception):
    """yfinance returned no usable data for this ticker."""


def get_estimates(ticker: str) -> dict:
    """Return NTM consensus EPS, revenue, and analyst count for a ticker.

    Uses the +1y row from yfinance earnings_estimate / revenue_estimate as the
    NTM proxy (next fiscal year is the standard analyst convention).
    """
    t = yf.Ticker(ticker)
    ee = t.earnings_estimate
    re = t.revenue_estimate

    if ee is None or ee.empty or "+1y" not in ee.index:
        raise YFNoDataError(
            f"yfinance returned no estimates for {ticker}. "
            "Ticker may be delisted, mistyped, or lack analyst coverage."
        )

    ntm_eps = float(ee.loc["+1y", "avg"])
    analyst_count = int(ee.loc["+1y", "numberOfAnalysts"])
    ntm_revenue = float(re.loc["+1y", "avg"]) if (re is not None and not re.empty and "+1y" in re.index) else None

    return {
        "ticker": ticker,
        "ntm_eps": ntm_eps,
        "ntm_revenue": ntm_revenue,
        "analyst_count": analyst_count,
        "period": "NTM",
        "date": date.today().isoformat(),
    }


def _row(df: pd.DataFrame, name: str, col) -> Optional[float]:
    """Safely extract a scalar from a DataFrame row, returning None if missing/NaN."""
    try:
        v = df.loc[name, col]
        return float(v) if pd.notna(v) else None
    except KeyError:
        return None


def get_financials(ticker: str, period: str = "annual") -> dict:
    """Return multi-year income statement, balance sheet, and cash flow data.

    Pulls from yfinance annual statements. yfinance returns 5 columns but the
    oldest column is NaN on all tested tickers; it is dropped automatically.

    Args:
        ticker: Stock ticker symbol.
        period: Must be "annual". Other values raise ValueError.

    Returns:
        {
            "ticker": str,
            "period": str,
            "years": [  # newest first, up to 4 years
                {
                    "fiscal_year": "YYYY-MM-DD",
                    "revenue": float | None,
                    "operating_income": float | None,
                    "net_income": float | None,
                    "free_cash_flow": float | None,
                    "stock_based_compensation": float | None,
                    "total_debt": float | None,
                    "cash": float | None,
                }
            ]
        }
    """
    if period != "annual":
        raise ValueError(f"Unsupported period {period!r}. Only 'annual' is supported in v1.")

    t = yf.Ticker(ticker)
    fin = t.financials
    cf = t.cashflow
    bs = t.balance_sheet

    if fin is None or fin.empty:
        raise YFNoDataError(
            f"yfinance returned no financial statements for {ticker}. "
            "Ticker may be delisted or mistyped."
        )

    # Drop columns where every value is NaN (the phantom 5th year)
    valid_cols = [c for c in fin.columns if not fin[c].isna().all()]

    years = []
    for col in sorted(valid_cols, reverse=True):  # newest first
        fy = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)[:10]
        years.append({
            "fiscal_year": fy,
            "revenue": _row(fin, "Total Revenue", col),
            "operating_income": _row(fin, "Operating Income", col),
            "net_income": _row(fin, "Net Income", col),
            "free_cash_flow": _row(cf, "Free Cash Flow", col) if cf is not None else None,
            "stock_based_compensation": _row(cf, "Stock Based Compensation", col) if cf is not None else None,
            "total_debt": _row(bs, "Total Debt", col) if bs is not None else None,
            "cash": _row(bs, "Cash And Cash Equivalents", col) if bs is not None else None,
        })

    return {"ticker": ticker, "period": period, "years": years}


def get_ratios(ticker: str) -> dict:
    """Return valuation ratios for a ticker from Yahoo Finance (TTM).

    Returns the same dict shape the FMP server returned, so callers don't care
    which backend produced the numbers. P/FCF is computed from market cap and
    free cash flow since yfinance doesn't expose it pre-computed.
    """
    start = time.monotonic()
    info = yf.Ticker(ticker).info or {}
    elapsed = time.monotonic() - start
    print(f"[yf] Ticker({ticker}).info → {len(info)} keys in {elapsed:.2f}s", file=sys.stderr)

    ps_ratio = info.get("priceToSalesTrailing12Months")
    if not ps_ratio:
        raise YFNoDataError(
            f"yfinance returned no usable data for {ticker}. "
            f"Ticker may be delisted, mistyped, or Yahoo's endpoint changed."
        )

    market_cap = info.get("marketCap")
    fcf = info.get("freeCashflow")
    pfcf = market_cap / fcf if market_cap and fcf and fcf > 0 else None

    return {
        "ticker": ticker,
        "pe_ratio": info.get("trailingPE"),
        "ps_ratio": ps_ratio,
        "ev_ebitda": info.get("enterpriseToEbitda"),
        "pfcf": pfcf,
        "ev_revenue": info.get("enterpriseToRevenue"),
        "period": "TTM",
        "date": date.today().isoformat(),
    }
