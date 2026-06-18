import sys
import time
from datetime import date
from typing import Optional

import re

import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup
from curl_cffi import requests as creq
from curl_cffi.requests.exceptions import RequestException


class YFNoDataError(Exception):
    """yfinance returned no usable data for this ticker."""


class FXNoDataError(Exception):
    """yfinance returned no usable FX rate for this currency pair."""


class _ScrapeError(Exception):
    """Yahoo HTML page was unreachable or unparseable."""


def get_fx_rate(base: str, quote: str) -> dict:
    """Return the latest close FX rate for base→quote via yfinance.

    Uses the standard yfinance FX symbol convention `{BASE}{QUOTE}=X`
    (e.g. USDKZT=X). Returns the most recent daily close.
    """
    base = (base or "").upper()
    quote = (quote or "").upper()
    if len(base) != 3 or len(quote) != 3 or not base.isalpha() or not quote.isalpha():
        raise FXNoDataError(
            f"Invalid FX pair {base!r}/{quote!r}. "
            "Both base and quote must be 3-letter ISO currency codes."
        )

    symbol = f"{base}{quote}=X"
    start = time.monotonic()
    hist = yf.Ticker(symbol).history(period="1d")
    print(f"[yf] get_fx_rate({base},{quote}) → {time.monotonic() - start:.2f}s", file=sys.stderr)

    if hist is None or hist.empty or "Close" not in hist.columns:
        raise FXNoDataError(
            f"yfinance returned no FX data for {symbol}. "
            "Currency pair may be unsupported or mistyped."
        )

    last = hist["Close"].dropna()
    if last.empty:
        raise FXNoDataError(
            f"yfinance returned no FX close for {symbol}. "
            "Currency pair may be unsupported or mistyped."
        )

    ts = last.index[-1]
    return {
        "base": base,
        "quote": quote,
        "rate": float(last.iloc[-1]),
        "date": ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else date.today().isoformat(),
        "source": "yfinance",
    }


def get_total_return_cagr(ticker: str, years: int = 5) -> dict:
    """Return trailing total-return CAGR over `years` for a ticker.

    Uses yfinance's auto-adjusted Close (default), which folds dividends and
    splits into the price series — so the start/end ratio is the total return,
    not just price appreciation. Intended for benchmark comparators (SPY / QQQ)
    and any "what did this actually return over N years" question.

    Args:
        ticker: Symbol — equity or ETF (e.g. SPY, QQQ).
        years: Lookback window in whole years. Must be ≥ 1.

    Returns:
        {
            "ticker": str,
            "years_requested": int,
            "years_actual": float,        # actual span end−start in years (365.25-day calendar)
            "start_date": "YYYY-MM-DD",
            "end_date":   "YYYY-MM-DD",
            "start_close": float,
            "end_close":   float,
            "cagr": float,                # e.g. 0.143 → 14.3 % annualised total return
            "source": "yfinance",
        }
    """
    if not isinstance(years, int) or years < 1:
        raise YFNoDataError(
            f"Invalid years {years!r}. Must be a positive integer ≥ 1."
        )

    start = time.monotonic()
    # Request a slightly wider window than `years` so the trimming below
    # always has full years of data to work with even if the very oldest
    # row is a partial day or a holiday cluster.
    period = f"{years}y"
    hist = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    print(f"[yf] get_total_return_cagr({ticker},{years}) → {time.monotonic() - start:.2f}s", file=sys.stderr)

    if hist is None or hist.empty or "Close" not in hist.columns:
        raise YFNoDataError(
            f"yfinance returned no price history for {ticker} over {years}y. "
            "Ticker may be delisted, mistyped, or younger than the window."
        )

    closes = hist["Close"].dropna()
    if len(closes) < 2:
        raise YFNoDataError(
            f"yfinance returned fewer than 2 valid closes for {ticker} over {years}y. "
            "Cannot compute CAGR."
        )

    start_ts = closes.index[0]
    end_ts = closes.index[-1]
    start_close = float(closes.iloc[0])
    end_close = float(closes.iloc[-1])

    span_days = (end_ts - start_ts).days
    if span_days <= 0:
        raise YFNoDataError(
            f"yfinance returned a zero-or-negative span for {ticker} over {years}y."
        )
    years_actual = span_days / 365.25
    cagr = (end_close / start_close) ** (1 / years_actual) - 1

    return {
        "ticker": ticker,
        "years_requested": years,
        "years_actual": round(years_actual, 3),
        "start_date": start_ts.strftime("%Y-%m-%d") if hasattr(start_ts, "strftime") else str(start_ts)[:10],
        "end_date": end_ts.strftime("%Y-%m-%d") if hasattr(end_ts, "strftime") else str(end_ts)[:10],
        "start_close": start_close,
        "end_close": end_close,
        "cagr": cagr,
        "source": "yfinance",
    }


def get_estimates(ticker: str) -> dict:
    """Return NTM consensus EPS, revenue, and analyst count for a ticker.

    Uses the +1y row from yfinance earnings_estimate / revenue_estimate as the
    NTM proxy (next fiscal year is the standard analyst convention).
    """
    start = time.monotonic()
    t = yf.Ticker(ticker)
    ee = t.earnings_estimate
    re = t.revenue_estimate
    print(f"[yf] get_estimates({ticker}) → {time.monotonic() - start:.2f}s", file=sys.stderr)

    if ee is None or ee.empty or "+1y" not in ee.index:
        raise YFNoDataError(
            f"yfinance returned no estimates for {ticker}. "
            "Ticker may be delisted, mistyped, or lack analyst coverage."
        )

    ntm_eps = float(ee.loc["+1y", "avg"])
    analyst_count = int(ee.loc["+1y", "numberOfAnalysts"])
    ntm_revenue = float(re.loc["+1y", "avg"]) if (re is not None and not re.empty and "+1y" in re.index) else None

    # LTG (Long-Term Growth) from growth_estimates — 5-year EPS CAGR proxy
    eps_growth_5y = None
    try:
        ge = t.growth_estimates
        if ge is not None and not ge.empty and "LTG" in ge.index:
            v = ge.loc["LTG", "stockTrend"]
            eps_growth_5y = float(v) if pd.notna(v) else None
    except Exception:
        pass

    return {
        "ticker": ticker,
        "ntm_eps": ntm_eps,
        "ntm_revenue": ntm_revenue,
        "analyst_count": analyst_count,
        "eps_growth_5y": eps_growth_5y,
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
                    "gross_profit": float | None,
                    "cost_of_revenue": float | None,
                    "operating_income": float | None,
                    "net_income": float | None,
                    "free_cash_flow": float | None,
                    "operating_cash_flow": float | None,
                    "capital_expenditures": float | None,
                    "stock_based_compensation": float | None,
                    "total_debt": float | None,
                    "long_term_debt": float | None,
                    "cash": float | None,
                    "total_assets": float | None,
                    "current_assets": float | None,
                    "current_liabilities": float | None,
                    "intangible_assets": float | None,
                    "shares_outstanding_diluted": float | None,
                }
            ]
        }

    Notes on yfinance row mapping:
        - intangible_assets uses "Goodwill And Other Intangible Assets" (goodwill + other intangibles).
          Falls back to summing "Goodwill" + "Other Intangible Assets" when the combined row is absent.
        - shares_outstanding_diluted uses "Diluted Average Shares" from the income statement (annual avg).
        - capital_expenditures is reported negative by yfinance; we return the raw signed value.
    """
    if period != "annual":
        raise ValueError(f"Unsupported period {period!r}. Only 'annual' is supported in v1.")

    start = time.monotonic()
    t = yf.Ticker(ticker)
    fin = t.financials
    cf = t.cashflow
    bs = t.balance_sheet
    print(f"[yf] get_financials({ticker}) → {time.monotonic() - start:.2f}s", file=sys.stderr)

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
        # Intangibles: prefer the combined "Goodwill And Other Intangible Assets" row;
        # fall back to summing "Goodwill" + "Other Intangible Assets" when only those exist.
        if bs is not None:
            intangibles = _row(bs, "Goodwill And Other Intangible Assets", col)
            if intangibles is None:
                gw = _row(bs, "Goodwill", col)
                oi = _row(bs, "Other Intangible Assets", col)
                intangibles = (gw or 0) + (oi or 0) if (gw is not None or oi is not None) else None
        else:
            intangibles = None

        year_data = {
            "fiscal_year": fy,
            "revenue": _row(fin, "Total Revenue", col),
            "gross_profit": _row(fin, "Gross Profit", col),
            "cost_of_revenue": _row(fin, "Cost Of Revenue", col),
            "operating_income": _row(fin, "Operating Income", col),
            "net_income": _row(fin, "Net Income", col),
            "free_cash_flow": _row(cf, "Free Cash Flow", col) if cf is not None else None,
            "operating_cash_flow": _row(cf, "Operating Cash Flow", col) if cf is not None else None,
            "capital_expenditures": _row(cf, "Capital Expenditure", col) if cf is not None else None,
            "stock_based_compensation": _row(cf, "Stock Based Compensation", col) if cf is not None else None,
            "total_debt": _row(bs, "Total Debt", col) if bs is not None else None,
            "long_term_debt": _row(bs, "Long Term Debt", col) if bs is not None else None,
            "cash": _row(bs, "Cash And Cash Equivalents", col) if bs is not None else None,
            "total_assets": _row(bs, "Total Assets", col) if bs is not None else None,
            "current_assets": _row(bs, "Current Assets", col) if bs is not None else None,
            "current_liabilities": _row(bs, "Current Liabilities", col) if bs is not None else None,
            "intangible_assets": intangibles,
            "shares_outstanding_diluted": _row(fin, "Diluted Average Shares", col),
        }
        # Drop years where every financial field is None (partial NaN columns)
        if any(v is not None for k, v in year_data.items() if k != "fiscal_year"):
            years.append(year_data)

    return {"ticker": ticker, "period": period, "years": years}


def get_earnings_history(ticker: str, n: int = 4) -> list[dict]:
    """Return the last n quarters of EPS actuals, estimates, and surprise.

    Args:
        ticker: Stock ticker symbol.
        n: Number of quarters to return (max 4; yfinance caps at 4).

    Returns:
        List of dicts ordered oldest-to-newest, each with:
            quarter (YYYY-MM-DD), reported_eps, estimated_eps, surprise_pct.
        surprise_pct is the raw yfinance fraction (e.g. 0.08 = 8% surprise).
    """
    t = yf.Ticker(ticker)
    eh = t.earnings_history

    if eh is None or (hasattr(eh, "empty") and eh.empty):
        raise YFNoDataError(
            f"yfinance returned no earnings history for {ticker}. "
            "Ticker may be delisted, mistyped, or lack reported earnings."
        )

    rows = []
    for ts, row in eh.sort_index().iterrows():
        quarter = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
        rows.append({
            "quarter": quarter,
            "reported_eps": float(row["epsActual"]),
            "estimated_eps": float(row["epsEstimate"]),
            "surprise_pct": float(row["surprisePercent"]),
        })

    return rows[-n:] if n < len(rows) else rows


def get_analyst_targets(ticker: str) -> dict:
    """Return analyst price targets and buy/hold/sell recommendation counts.

    Uses Ticker.analyst_price_targets for price target distribution and
    Ticker.recommendations_summary for the current-month (0m) counts.
    strongBuy+buy → buy_count; sell+strongSell → sell_count.
    """
    t = yf.Ticker(ticker)
    targets = t.analyst_price_targets or {}
    recs = t.recommendations_summary

    if not targets.get("mean"):
        raise YFNoDataError(
            f"yfinance returned no analyst price targets for {ticker}. "
            "Ticker may be delisted, mistyped, or lack analyst coverage."
        )
    if recs is None or (hasattr(recs, "empty") and recs.empty):
        raise YFNoDataError(
            f"yfinance returned no recommendations summary for {ticker}. "
            "Ticker may be delisted, mistyped, or lack analyst coverage."
        )

    # Use the 0m (current month) row — first row in the DataFrame
    row = recs.iloc[0]
    buy_count = int(row.get("strongBuy", 0)) + int(row.get("buy", 0))
    hold_count = int(row.get("hold", 0))
    sell_count = int(row.get("sell", 0)) + int(row.get("strongSell", 0))

    return {
        "ticker": ticker,
        "avg_target": float(targets["mean"]),
        "median_target": float(targets["median"]) if targets.get("median") else None,
        "high_target": float(targets["high"]),
        "low_target": float(targets["low"]),
        "buy_count": buy_count,
        "hold_count": hold_count,
        "sell_count": sell_count,
        "date": date.today().isoformat(),
    }


_SI_SUFFIX = {"T": 1e12, "B": 1e9, "M": 1e6, "k": 1e3, "K": 1e3}
_DATE_CELL = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")


def _parse_si_number(s: str) -> Optional[float]:
    """Parse Yahoo's "16.24B" / "189.88M" / "2.42T" / "7.15" / "--" strings.

    Returns None when the value is a Yahoo placeholder (`--`, empty) or
    unparseable. Strips commas and percent signs.
    """
    if s is None:
        return None
    s = s.strip().replace(",", "")
    if not s or s in ("--", "N/A"):
        return None
    pct = s.endswith("%")
    if pct:
        s = s[:-1]
    mult = 1.0
    if s and s[-1] in _SI_SUFFIX:
        mult = _SI_SUFFIX[s[-1]]
        s = s[:-1]
    try:
        v = float(s) * mult
    except ValueError:
        return None
    return v / 100.0 if pct else v


def _parse_valuation_table(soup: BeautifulSoup) -> dict:
    """Extract the Valuation Measures `{label: current_value}` from a Yahoo
    key-statistics page.

    The table lives at `<section data-testid="qsp-statistics">` → first
    `<table>` inside. Each `<tr>` has cells: label, Current, 5 historical
    quarters. We take the "Current" cell (index 1).

    Returns an empty dict if the section is absent or empty — caller decides
    whether that is fatal.
    """
    section = soup.find("section", attrs={"data-testid": "qsp-statistics"})
    if section is None:
        return {}
    table = section.find("table")
    if table is None:
        return {}
    out: dict[str, Optional[float]] = {}
    for tr in table.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        label = cells[0]
        current = cells[1]
        if not label or _DATE_CELL.match(current) or current == "Current":
            continue
        out[label] = _parse_si_number(current)
    return out


_RETRY_BACKOFF = (0.5, 1.0, 2.0)


def _fetch_with_retry(url: str, attempts: int = 3, timeout: float = 5.0):
    """Fetch `url` with Chrome TLS impersonation, retrying transient failures.

    Retries on curl_cffi network errors, HTTP 5xx, and HTTP 429.
    Does NOT retry on other 4xx — those are treated as permanent.
    Backoff between attempts: 0.5s, 1.0s, 2.0s (no sleep after final attempt).

    Returns the curl_cffi response on success. Raises `_ScrapeError` after
    exhausting all attempts or on a non-retryable HTTP status.
    """
    last_err = "unknown"
    for i in range(attempts):
        try:
            r = creq.get(url, impersonate="chrome", timeout=timeout)
        except RequestException as e:
            last_err = f"network error: {e}"
            if i < attempts - 1:
                time.sleep(_RETRY_BACKOFF[i])
                continue
            raise _ScrapeError(f"{url}: {last_err} after {attempts} attempts") from e

        if r.status_code == 200:
            return r

        if r.status_code >= 500 or r.status_code == 429:
            last_err = f"HTTP {r.status_code}"
            if i < attempts - 1:
                time.sleep(_RETRY_BACKOFF[i])
                continue
            raise _ScrapeError(f"{url}: {last_err} after {attempts} attempts")

        raise _ScrapeError(f"{url}: HTTP {r.status_code} (non-retryable)")

    raise _ScrapeError(f"{url}: exhausted {attempts} attempts ({last_err})")


def _fetch_yahoo_html(url: str, timeout: float = 5.0) -> str:
    """Fetch a Yahoo HTML page with retry. Returns response body text."""
    return _fetch_with_retry(url, timeout=timeout).text


def _ratios_from_html(ticker: str) -> dict:
    """Fetch and parse Yahoo's key-statistics page for `ticker`.

    Returns a dict with the same valuation fields the API path returns,
    sourced from the Valuation Measures "Current" column. Raises
    `_ScrapeError` if the page is unreachable or the valuation section is
    missing/empty.

    `reporting_currency` is NOT set here — the HTML page does not surface
    `financialCurrency`. Caller layers it on from `Ticker.info`.
    """
    start = time.monotonic()
    url = f"https://finance.yahoo.com/quote/{ticker}/key-statistics/"
    html = _fetch_yahoo_html(url)
    elapsed = time.monotonic() - start
    print(f"[yf] _ratios_from_html({ticker}) fetched in {elapsed:.2f}s", file=sys.stderr)

    soup = BeautifulSoup(html, "html.parser")
    vm = _parse_valuation_table(soup)
    if not vm:
        raise _ScrapeError(
            f"Yahoo key-statistics page for {ticker} has no Valuation Measures table"
        )

    pe = vm.get("Trailing P/E")
    ps = vm.get("Price/Sales")
    if pe is None and ps is None:
        raise _ScrapeError(
            f"Yahoo key-statistics page for {ticker} has no P/E and no P/S. "
            f"Either the ticker is too new/delisted, or Yahoo's table labels changed."
        )

    return {
        "pe_ratio": pe,
        "ps_ratio": ps,
        "ev_ebitda": vm.get("Enterprise Value/EBITDA"),
        "ev_revenue": vm.get("Enterprise Value/Revenue"),
        "marketCap": vm.get("Market Cap"),
        "enterpriseValue": vm.get("Enterprise Value"),
    }


def _ratios_from_info(ticker: str, info: dict) -> dict:
    """Build the standard ratios dict from a populated `Ticker.info`. Happy path."""
    market_cap = info.get("marketCap")
    fcf = info.get("freeCashflow")
    pfcf = market_cap / fcf if market_cap and fcf and fcf > 0 else None
    return {
        "ticker": ticker,
        "company_name": info.get("longName") or info.get("shortName"),
        "pe_ratio": info.get("trailingPE"),
        "ps_ratio": info.get("priceToSalesTrailing12Months"),
        "ev_ebitda": info.get("enterpriseToEbitda"),
        "pfcf": pfcf,
        "ev_revenue": info.get("enterpriseToRevenue"),
        "eps_ttm": info.get("trailingEps"),
        "sharesOutstanding": info.get("sharesOutstanding"),
        "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
        "marketCap": market_cap,
        "source": "yahoo_api",
        "reporting_currency": info.get("financialCurrency"),
        "period": "TTM",
        "date": date.today().isoformat(),
    }


def get_ratios(ticker: str) -> dict:
    """Return valuation ratios for a ticker from Yahoo Finance (TTM).

    Happy path reads from `Ticker.info` (`source: "yahoo_api"`). When
    `priceToSalesTrailing12Months` is missing (typical for non-US ADRs such as
    KSPI), falls back to scraping the public key-statistics HTML page
    (`source: "yahoo_html"`). Raises `YFNoDataError` if the fallback also
    fails — loud failure preserved.
    """
    start = time.monotonic()
    info = yf.Ticker(ticker).info or {}
    elapsed = time.monotonic() - start
    print(f"[yf] get_ratios({ticker}).info → {len(info)} keys in {elapsed:.2f}s", file=sys.stderr)

    if info.get("priceToSalesTrailing12Months"):
        return _ratios_from_info(ticker, info)

    html_start = time.monotonic()
    try:
        html_ratios = _ratios_from_html(ticker)
    except _ScrapeError as e:
        html_elapsed = time.monotonic() - html_start
        print(
            f"[yf] get_ratios({ticker}).html FAILED in {html_elapsed:.2f}s reason={e}",
            file=sys.stderr,
        )
        raise YFNoDataError(
            f"yfinance returned no usable data for {ticker} and HTML fallback failed: {e}. "
            f"Ticker may be delisted, mistyped, or Yahoo's endpoint changed."
        ) from e

    html_elapsed = time.monotonic() - html_start
    n_fields = sum(1 for v in html_ratios.values() if v is not None)
    print(
        f"[yf] get_ratios({ticker}).html → {n_fields} fields in {html_elapsed:.2f}s source=yahoo_html",
        file=sys.stderr,
    )

    market_cap = html_ratios.get("marketCap") or info.get("marketCap")
    return {
        "ticker": ticker,
        "company_name": info.get("longName") or info.get("shortName"),
        "pe_ratio": html_ratios.get("pe_ratio"),
        "ps_ratio": html_ratios.get("ps_ratio"),
        "ev_ebitda": html_ratios.get("ev_ebitda"),
        "pfcf": None,
        "ev_revenue": html_ratios.get("ev_revenue"),
        "eps_ttm": info.get("trailingEps"),
        "sharesOutstanding": info.get("sharesOutstanding"),
        "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
        "marketCap": market_cap,
        "source": "yahoo_html",
        "reporting_currency": info.get("financialCurrency"),
        "period": "TTM",
        "date": date.today().isoformat(),
    }
