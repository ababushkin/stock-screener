"""Fitness functions for `get_ratios` — one test per NFR in the design doc.

Tests are split into hermetic (every-commit) and `@pytest.mark.nightly` (live
Yahoo network calls). Run hermetic only: `pytest -m "not nightly"`.

The Slice 2 retry-policy tests for `_fetch_with_retry` live in `test_tools.py`
(TestFetchWithRetry) — they are pure unit tests on the helper and stay there.
"""
import statistics
import time
from unittest.mock import MagicMock, patch

import pytest

from tools import YFNoDataError, get_ratios


# ---------------------------------------------------------------------------
# Hermetic tests — run on every commit
# ---------------------------------------------------------------------------


_MALFORMED_HTML = """
<html><body>
<section data-testid="qsp-statistics">
  <div class="table-container">
    <table>
      <tr><th></th><th>Current</th><th>3/31/2025</th></tr>
      <tr><td>Trailing PER</td><td>7.15</td><td>6.50</td></tr>
      <tr><td>Price-to-Sales</td><td>1.91</td><td>1.85</td></tr>
      <tr><td>Mkt Capitalisation</td><td>16.24B</td><td>15.0B</td></tr>
    </table>
  </div>
</section>
</body></html>
"""


def _info_missing_ps():
    return {
        "longName": "Test Co.",
        "currentPrice": 90.0,
        "marketCap": 17_000_000_000,
        "financialCurrency": "KZT",
    }


def test_get_ratios_html_malformed_raises():
    """Yahoo renaming table labels must fail loudly, not silently return all-None.

    Fitness for NFR 6 (loud failure on structural drift). Stub HTML has the
    valuation section present but every row label renamed — both `Trailing P/E`
    and `Price/Sales` are absent, so `_ratios_from_html` raises `_ScrapeError`
    which `get_ratios` translates to `YFNoDataError`.
    """
    mock_ticker = MagicMock()
    mock_ticker.info = _info_missing_ps()
    with patch("tools.yf.Ticker", return_value=mock_ticker), \
         patch("tools._fetch_yahoo_html", return_value=_MALFORMED_HTML):
        with pytest.raises(YFNoDataError):
            get_ratios("FAKE")


def test_get_ratios_html_retry_budget():
    """Three transient HTTP failures stay inside the documented retry budget.

    Fitness for NFR 3 (retry-exhaustion bounded). With `time.sleep` patched out
    we verify the *policy*: 3 attempts fired, backoff schedule [0.5, 1.0]
    (no sleep after the final attempt), total sleep budget < 12s.
    """
    mock_ticker = MagicMock()
    mock_ticker.info = _info_missing_ps()

    fake_resp = MagicMock()
    fake_resp.status_code = 503
    fake_resp.text = ""

    with patch("tools.yf.Ticker", return_value=mock_ticker), \
         patch("tools.creq.get", return_value=fake_resp) as get_mock, \
         patch("tools.time.sleep") as sleep_mock:
        with pytest.raises(YFNoDataError):
            get_ratios("KSPI")

    assert get_mock.call_count == 3, "should make exactly `attempts` HTTP attempts"
    sleeps = [c.args[0] for c in sleep_mock.call_args_list]
    assert sleeps == [0.5, 1.0], f"backoff schedule drifted: {sleeps}"
    assert sum(sleeps) < 12.0


# ---------------------------------------------------------------------------
# Nightly tests — hit live Yahoo, skipped on hermetic runs
# ---------------------------------------------------------------------------


# Recorded smoke snapshot from 2026-05-13. Values drift with the market — the
# fitness test below uses generous tolerances and only fails on structural
# breakage, not normal price movement. Refresh when Yahoo's table changes.
KSPI_FIXTURE = {
    "pe_ratio": 7.15,
    "ps_ratio": 1.91,
    "marketCap": 16.24e9,
    "currentPrice": 86.38,
    "reporting_currency": "KZT",
}

US_MEGACAP_GOLDEN = {
    "AAPL": {"source": "yahoo_api", "reporting_currency": "USD"},
    "MSFT": {"source": "yahoo_api", "reporting_currency": "USD"},
    "NVDA": {"source": "yahoo_api", "reporting_currency": "USD"},
}


def _median_latency(fn, runs: int = 5) -> float:
    samples = []
    for _ in range(runs):
        t0 = time.monotonic()
        fn()
        samples.append(time.monotonic() - t0)
    return statistics.median(samples)


@pytest.mark.nightly
def test_get_ratios_latency():
    """AAPL happy path: median of 5 calls < 1.0s.

    Fitness for NFR 1 (API-path latency). Median dampens single-shot noise.
    """
    median = _median_latency(lambda: get_ratios("AAPL"), runs=5)
    assert median < 1.0, f"AAPL get_ratios median latency {median:.2f}s exceeds 1.0s budget"


@pytest.mark.nightly
def test_get_ratios_html_fallback_latency():
    """KSPI fallback path: single call < 3.0s when first HTTP attempt succeeds.

    Fitness for NFR 2 (HTML-path latency).
    """
    t0 = time.monotonic()
    get_ratios("KSPI")
    elapsed = time.monotonic() - t0
    assert elapsed < 3.0, f"KSPI HTML fallback took {elapsed:.2f}s, exceeds 3.0s budget"


@pytest.mark.nightly
def test_get_ratios_kspi_fallback_values():
    """KSPI fallback returns populated, in-range numerics.

    Fitness for NFR 4 (fallback correctness). Uses ±50% tolerance against the
    recorded fixture — wide enough to absorb market movement, tight enough to
    catch a parser regression (which would zero or N/A the fields).
    """
    r = get_ratios("KSPI")
    assert r["source"] == "yahoo_html"
    assert r["reporting_currency"] == KSPI_FIXTURE["reporting_currency"]
    for field in ("pe_ratio", "ps_ratio", "marketCap", "currentPrice"):
        v = r[field]
        expected = KSPI_FIXTURE[field]
        assert v is not None, f"{field} is None — parser likely regressed"
        assert expected * 0.5 <= v <= expected * 1.5, (
            f"{field}={v} drifted >50% from fixture {expected} — "
            f"either Yahoo labels changed or KSPI moved hard; investigate"
        )


@pytest.mark.nightly
@pytest.mark.parametrize("ticker", list(US_MEGACAP_GOLDEN.keys()))
def test_get_ratios_us_megacap_unchanged(ticker):
    """US mega-caps stay on the API path with populated valuation fields.

    Fitness for NFR 5 (no regression on the happy path). Asserts source and
    currency only; numeric values drift daily and are not the regression
    signal — the regression signal is the path taken.
    """
    r = get_ratios(ticker)
    expected = US_MEGACAP_GOLDEN[ticker]
    assert r["source"] == expected["source"]
    assert r["reporting_currency"] == expected["reporting_currency"]
    assert r["pe_ratio"] is not None, f"{ticker} pe_ratio missing on API path"
    assert r["ps_ratio"] is not None, f"{ticker} ps_ratio missing on API path"
    assert r["marketCap"] is not None
