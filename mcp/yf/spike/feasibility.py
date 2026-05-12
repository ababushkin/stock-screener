"""ABA-47 throwaway spike. Probe yfinance coverage for 10 data surfaces × 3 tickers."""
import json
import sys
import warnings
import yfinance as yf

warnings.filterwarnings("ignore")

TICKERS = ["NVDA", "META", "RDDT"]


def probe(t: yf.Ticker, label: str, fn):
    try:
        r = fn(t)
        if r is None:
            return ("MISSING", "returned None")
        if hasattr(r, "empty") and r.empty:
            return ("MISSING", "empty DataFrame")
        if isinstance(r, (list, dict)) and not r:
            return ("MISSING", "empty container")
        return ("OK", r)
    except Exception as e:
        return ("MISSING", f"{type(e).__name__}: {e}")


def show(label, status, val, *, max_rows=4):
    print(f"\n--- {label} :: {status}")
    if status != "OK":
        print(f"    {val}")
        return
    try:
        import pandas as pd
        if isinstance(val, pd.DataFrame):
            print(f"    shape={val.shape} cols={list(val.columns)[:6]}")
            print(f"    index={list(val.index)[:8]}")
            print(val.head(max_rows).to_string()[:2000])
        elif isinstance(val, pd.Series):
            print(f"    series len={len(val)}")
            print(val.head(max_rows).to_string()[:1000])
        elif isinstance(val, dict):
            keys = list(val.keys())
            print(f"    dict keys={keys[:20]}")
            for k in keys[:6]:
                print(f"      {k}: {str(val[k])[:200]}")
        else:
            print(f"    type={type(val).__name__} value={str(val)[:500]}")
    except Exception as e:
        print(f"    [print error: {e}]")


def run(ticker: str):
    print("\n" + "=" * 70)
    print(f"TICKER: {ticker}")
    print("=" * 70)
    t = yf.Ticker(ticker)

    surfaces = [
        ("1. SBC (cashflow)",        lambda x: x.cashflow),
        ("1b. SBC (financials)",     lambda x: x.financials),
        ("2. earnings_estimate",     lambda x: x.earnings_estimate),
        ("3. revenue_estimate",      lambda x: x.revenue_estimate),
        ("4. earnings_history",      lambda x: x.earnings_history),
        ("5. eps_revisions",         lambda x: x.eps_revisions),
        ("5b. upgrades_downgrades",  lambda x: x.upgrades_downgrades),
        ("6. analyst_price_targets", lambda x: x.analyst_price_targets),
        ("6b. recommendations_summary", lambda x: x.recommendations_summary),
        ("7. revenue segments",      lambda x: x.get_isin()),  # placeholder; real check below
        ("8. balance_sheet",         lambda x: x.balance_sheet),
        ("8b. cashflow (multi-yr)",  lambda x: x.cashflow),
        ("9. 5y cashflow FCF",       lambda x: x.cashflow),
        ("10. info.longBusinessSummary (guidance proxy)", lambda x: t.info.get("longBusinessSummary")),
    ]

    for label, fn in surfaces:
        status, val = probe(t, label, fn)
        show(label, status, val)

    # specific deep checks
    try:
        cf = t.cashflow
        sbc_rows = [r for r in cf.index if "stock" in r.lower() or "compensation" in r.lower()]
        print(f"\n>> SBC candidate rows in cashflow: {sbc_rows}")
        capex_rows = [r for r in cf.index if "capital" in r.lower() or "purchase" in r.lower()]
        print(f">> Capex candidate rows: {capex_rows}")
    except Exception as e:
        print(f">> cashflow row inspect failed: {e}")


if __name__ == "__main__":
    for tk in TICKERS:
        run(tk)
