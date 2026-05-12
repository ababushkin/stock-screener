import sys
import time

import httpx

BASE_URL = "https://financialmodelingprep.com/stable"


class FMPNoDataError(Exception):
    """FMP returned an empty response for this ticker/endpoint."""


class FMPPremiumError(Exception):
    """FMP endpoint requires a premium subscription."""


def _get(endpoint: str, params: dict) -> list | dict:
    url = f"{BASE_URL}/{endpoint}"
    log_url = f"{url}?apikey=[redacted]"
    for k, v in params.items():
        if k != "apikey":
            log_url += f"&{k}={v}"

    start = time.monotonic()
    resp = httpx.get(url, params=params, timeout=10.0)
    elapsed = time.monotonic() - start

    print(f"[fmp] GET {log_url} → HTTP {resp.status_code} in {elapsed:.2f}s", file=sys.stderr)

    if resp.status_code == 402:
        symbol = params.get("symbol", "?")
        raise FMPPremiumError(
            f"FMP free tier does not serve {symbol} on /{endpoint} (HTTP 402). "
            f"This is a per-ticker restriction, not an account-wide one — most tickers work. "
            f"For dual-class shares, try the sibling class (e.g. GOOG → GOOGL)."
        )
    resp.raise_for_status()

    return resp.json()


def get_ratios(ticker: str, api_key: str) -> dict:
    """Return valuation ratios for a ticker.

    Calls stable/ratios (pe, ps, ev/ebitda, pfcf) and stable/key-metrics (ev/revenue).
    """
    ratios_data = _get("ratios", {"symbol": ticker, "apikey": api_key, "period": "annual", "limit": 1})
    if not ratios_data:
        raise FMPNoDataError(ticker, "ratios")
    r = ratios_data[0] if isinstance(ratios_data, list) else ratios_data

    metrics_data = _get("key-metrics", {"symbol": ticker, "apikey": api_key, "period": "annual", "limit": 1})
    m = (metrics_data[0] if isinstance(metrics_data, list) else metrics_data) if metrics_data else {}

    return {
        "ticker": ticker,
        "pe_ratio": r.get("priceToEarningsRatio"),
        "ps_ratio": r.get("priceToSalesRatio"),
        "ev_ebitda": r.get("enterpriseValueMultiple"),
        "pfcf": r.get("priceToFreeCashFlowRatio"),
        "ev_revenue": m.get("evToSales"),
        "period": r.get("period"),
        "date": r.get("date"),
    }
