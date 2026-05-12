import sys
import time
from datetime import date

import yfinance as yf


class YFNoDataError(Exception):
    """yfinance returned no usable data for this ticker."""


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
