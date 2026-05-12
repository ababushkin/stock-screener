"""Tests for yfinance MCP tools."""
import math
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, "/Users/anton/src/stock-review/mcp/yf")
from tools import YFNoDataError, get_analyst_targets, get_earnings_history, get_estimates, get_financials


def _make_earnings_estimate(avg, analysts):
    """Build a minimal earnings_estimate DataFrame matching yfinance shape."""
    return pd.DataFrame(
        {"avg": [1.0, 1.2, 4.0, avg], "numberOfAnalysts": [30, 29, 40, analysts]},
        index=pd.Index(["0q", "+1q", "0y", "+1y"], name="period"),
    )


def _make_revenue_estimate(avg, analysts):
    return pd.DataFrame(
        {"avg": [10e9, 12e9, 45e9, avg], "numberOfAnalysts": [28, 28, 40, analysts]},
        index=pd.Index(["0q", "+1q", "0y", "+1y"], name="period"),
    )


class TestGetEstimates:
    def test_returns_required_keys(self):
        ee = _make_earnings_estimate(avg=11.28, analysts=46)
        re = _make_revenue_estimate(avg=485e9, analysts=54)

        mock_ticker = MagicMock()
        mock_ticker.earnings_estimate = ee
        mock_ticker.revenue_estimate = re

        with patch("tools.yf.Ticker", return_value=mock_ticker):
            result = get_estimates("NVDA")

        assert set(result.keys()) >= {"ticker", "ntm_eps", "ntm_revenue", "analyst_count"}

    def test_values_populated_from_plus1y_row(self):
        ee = _make_earnings_estimate(avg=11.28, analysts=46)
        re = _make_revenue_estimate(avg=485_834_707_830, analysts=54)

        mock_ticker = MagicMock()
        mock_ticker.earnings_estimate = ee
        mock_ticker.revenue_estimate = re

        with patch("tools.yf.Ticker", return_value=mock_ticker):
            result = get_estimates("NVDA")

        assert result["ntm_eps"] == pytest.approx(11.28, rel=1e-4)
        assert result["ntm_revenue"] == pytest.approx(485_834_707_830, rel=1e-4)
        assert result["analyst_count"] == 46

    def test_raises_when_estimates_empty(self):
        mock_ticker = MagicMock()
        mock_ticker.earnings_estimate = pd.DataFrame()
        mock_ticker.revenue_estimate = pd.DataFrame()

        with patch("tools.yf.Ticker", return_value=mock_ticker):
            with pytest.raises(YFNoDataError):
                get_estimates("FAKE")

    def test_ticker_passed_through(self):
        ee = _make_earnings_estimate(avg=5.0, analysts=20)
        re = _make_revenue_estimate(avg=10e9, analysts=20)

        mock_ticker = MagicMock()
        mock_ticker.earnings_estimate = ee
        mock_ticker.revenue_estimate = re

        with patch("tools.yf.Ticker", return_value=mock_ticker):
            result = get_estimates("META")

        assert result["ticker"] == "META"


# ---------------------------------------------------------------------------
# Helpers for get_financials tests
# ---------------------------------------------------------------------------

_DATES_4Y = pd.to_datetime(["2025-12-31", "2024-12-31", "2023-12-31", "2022-12-31"])
_DATES_5Y = pd.to_datetime(
    ["2025-12-31", "2024-12-31", "2023-12-31", "2022-12-31", "2021-12-31"]
)


def _make_financials_df(with_nan_col: bool = False):
    """Income statement DataFrame (rows=metrics, cols=dates, newest first)."""
    dates = _DATES_5Y if with_nan_col else _DATES_4Y
    data = {
        "Total Revenue":    [163e9, 140e9, 134e9, 116e9] + ([float("nan")] if with_nan_col else []),
        "Operating Income": [69e9,  59e9,  46e9,  28e9]  + ([float("nan")] if with_nan_col else []),
        "Net Income":       [62e9,  50e9,  39e9,  23e9]  + ([float("nan")] if with_nan_col else []),
    }
    return pd.DataFrame(data, index=dates).T


def _make_cashflow_df(with_nan_col: bool = False):
    dates = _DATES_5Y if with_nan_col else _DATES_4Y
    data = {
        "Free Cash Flow":            [52e9, 43e9, 19e9, 6e9]  + ([float("nan")] if with_nan_col else []),
        "Stock Based Compensation":  [20e9, 17e9, 14e9, 12e9] + ([float("nan")] if with_nan_col else []),
    }
    return pd.DataFrame(data, index=dates).T


def _make_balance_sheet_df(with_nan_col: bool = False):
    dates = _DATES_5Y if with_nan_col else _DATES_4Y
    data = {
        "Total Debt":                [28e9, 18e9, 18e9, 18e9] + ([float("nan")] if with_nan_col else []),
        "Cash And Cash Equivalents": [77e9, 43e9, 42e9, 14e9] + ([float("nan")] if with_nan_col else []),
    }
    return pd.DataFrame(data, index=dates).T


def _mock_ticker(with_nan_col: bool = False):
    m = MagicMock()
    m.financials = _make_financials_df(with_nan_col)
    m.cashflow = _make_cashflow_df(with_nan_col)
    m.balance_sheet = _make_balance_sheet_df(with_nan_col)
    return m


class TestGetFinancials:
    def test_outer_dict_has_required_keys(self):
        with patch("tools.yf.Ticker", return_value=_mock_ticker()):
            result = get_financials("META", "annual")

        assert set(result.keys()) >= {"ticker", "period", "years"}

    def test_ticker_and_period_passed_through(self):
        with patch("tools.yf.Ticker", return_value=_mock_ticker()):
            result = get_financials("META", "annual")

        assert result["ticker"] == "META"
        assert result["period"] == "annual"

    def test_at_least_two_years_returned(self):
        with patch("tools.yf.Ticker", return_value=_mock_ticker()):
            result = get_financials("META", "annual")

        assert len(result["years"]) >= 2

    def test_each_year_has_required_fields(self):
        required = {
            "fiscal_year",
            "revenue",
            "operating_income",
            "net_income",
            "free_cash_flow",
            "stock_based_compensation",
            "total_debt",
            "cash",
        }
        with patch("tools.yf.Ticker", return_value=_mock_ticker()):
            result = get_financials("META", "annual")

        for year in result["years"]:
            assert set(year.keys()) >= required, f"Missing keys in {year}"

    def test_income_statement_values_correct(self):
        with patch("tools.yf.Ticker", return_value=_mock_ticker()):
            result = get_financials("META", "annual")

        newest = result["years"][0]
        assert newest["revenue"] == pytest.approx(163e9, rel=1e-4)
        assert newest["operating_income"] == pytest.approx(69e9, rel=1e-4)
        assert newest["net_income"] == pytest.approx(62e9, rel=1e-4)

    def test_cashflow_values_correct(self):
        with patch("tools.yf.Ticker", return_value=_mock_ticker()):
            result = get_financials("META", "annual")

        newest = result["years"][0]
        assert newest["free_cash_flow"] == pytest.approx(52e9, rel=1e-4)
        assert newest["stock_based_compensation"] == pytest.approx(20e9, rel=1e-4)

    def test_balance_sheet_values_correct(self):
        with patch("tools.yf.Ticker", return_value=_mock_ticker()):
            result = get_financials("META", "annual")

        newest = result["years"][0]
        assert newest["total_debt"] == pytest.approx(28e9, rel=1e-4)
        assert newest["cash"] == pytest.approx(77e9, rel=1e-4)

    def test_nan_column_dropped(self):
        """The 5th column (all NaN) must not appear in results."""
        with patch("tools.yf.Ticker", return_value=_mock_ticker(with_nan_col=True)):
            result = get_financials("META", "annual")

        fiscal_years = [y["fiscal_year"] for y in result["years"]]
        assert "2021-12-31" not in fiscal_years

    def test_years_ordered_newest_first(self):
        with patch("tools.yf.Ticker", return_value=_mock_ticker()):
            result = get_financials("META", "annual")

        years = [y["fiscal_year"] for y in result["years"]]
        assert years == sorted(years, reverse=True)

    def test_raises_on_empty_financials(self):
        m = MagicMock()
        m.financials = pd.DataFrame()
        m.cashflow = _make_cashflow_df()
        m.balance_sheet = _make_balance_sheet_df()

        with patch("tools.yf.Ticker", return_value=m):
            with pytest.raises(YFNoDataError):
                get_financials("FAKE", "annual")

    def test_raises_on_unsupported_period(self):
        with patch("tools.yf.Ticker", return_value=_mock_ticker()):
            with pytest.raises(ValueError, match="period"):
                get_financials("META", "quarterly")


# ---------------------------------------------------------------------------
# Helpers for get_analyst_targets tests
# ---------------------------------------------------------------------------

def _make_recommendations_summary():
    """4-month rolling recommendations DataFrame matching yfinance shape."""
    return pd.DataFrame(
        {
            "period":    ["0m", "-1m", "-2m", "-3m"],
            "strongBuy": [9,    9,     9,     12],
            "buy":       [48,   48,    48,    48],
            "hold":      [2,    2,     2,     2],
            "sell":      [1,    1,     1,     1],
            "strongSell":[0,    0,     0,     0],
        }
    )


def _make_analyst_price_targets():
    """analyst_price_targets dict matching yfinance shape."""
    return {
        "current": 219.44,
        "high": 380.0,
        "low": 140.0,
        "mean": 269.16544,
        "median": 265.0,
    }


def _mock_targets_ticker():
    m = MagicMock()
    m.analyst_price_targets = _make_analyst_price_targets()
    m.recommendations_summary = _make_recommendations_summary()
    return m


class TestGetAnalystTargets:
    def test_returns_required_keys(self):
        with patch("tools.yf.Ticker", return_value=_mock_targets_ticker()):
            result = get_analyst_targets("META")

        required = {"ticker", "avg_target", "median_target", "high_target", "low_target", "buy_count", "hold_count", "sell_count"}
        assert required <= set(result.keys())

    def test_price_target_values(self):
        with patch("tools.yf.Ticker", return_value=_mock_targets_ticker()):
            result = get_analyst_targets("META")

        assert result["avg_target"] == pytest.approx(269.16544, rel=1e-4)
        assert result["median_target"] == pytest.approx(265.0, rel=1e-4)
        assert result["high_target"] == pytest.approx(380.0, rel=1e-4)
        assert result["low_target"] == pytest.approx(140.0, rel=1e-4)

    def test_buy_count_merges_strong_buy(self):
        """buy_count = strongBuy + buy from the 0m period row."""
        with patch("tools.yf.Ticker", return_value=_mock_targets_ticker()):
            result = get_analyst_targets("META")

        assert result["buy_count"] == 57  # 9 strongBuy + 48 buy

    def test_sell_count_merges_strong_sell(self):
        """sell_count = sell + strongSell from the 0m period row."""
        with patch("tools.yf.Ticker", return_value=_mock_targets_ticker()):
            result = get_analyst_targets("META")

        assert result["sell_count"] == 1  # 1 sell + 0 strongSell

    def test_hold_count(self):
        with patch("tools.yf.Ticker", return_value=_mock_targets_ticker()):
            result = get_analyst_targets("META")

        assert result["hold_count"] == 2

    def test_ticker_passed_through(self):
        with patch("tools.yf.Ticker", return_value=_mock_targets_ticker()):
            result = get_analyst_targets("META")

        assert result["ticker"] == "META"

    def test_raises_when_price_targets_missing(self):
        m = MagicMock()
        m.analyst_price_targets = {}
        m.recommendations_summary = _make_recommendations_summary()

        with patch("tools.yf.Ticker", return_value=m):
            with pytest.raises(YFNoDataError):
                get_analyst_targets("FAKE")

    def test_raises_when_recommendations_empty(self):
        m = MagicMock()
        m.analyst_price_targets = _make_analyst_price_targets()
        m.recommendations_summary = pd.DataFrame()

        with patch("tools.yf.Ticker", return_value=m):
            with pytest.raises(YFNoDataError):
                get_analyst_targets("FAKE")


# ---------------------------------------------------------------------------
# Helpers for get_earnings_history tests
# ---------------------------------------------------------------------------

_EH_DATES = pd.to_datetime(["2025-04-30", "2025-07-31", "2025-10-31", "2026-01-31"])


def _make_earnings_history_df():
    """earnings_history DataFrame matching yfinance shape (4 rows × 4 cols)."""
    df = pd.DataFrame(
        {
            "epsActual":       [0.81, 1.05, 1.30, 1.62],
            "epsEstimate":     [0.74988, 1.00867, 1.25647, 1.53812],
            "epsDifference":   [0.06, 0.04, 0.04, 0.08],
            "surprisePercent": [0.0802, 0.0410, 0.0346, 0.0532],
        },
        index=pd.DatetimeIndex(_EH_DATES, name="quarter"),
    )
    return df


def _mock_eh_ticker():
    m = MagicMock()
    m.earnings_history = _make_earnings_history_df()
    return m


class TestGetEarningsHistory:
    def test_returns_list_of_four_dicts(self):
        with patch("tools.yf.Ticker", return_value=_mock_eh_ticker()):
            result = get_earnings_history("AAPL", 4)

        assert isinstance(result, list)
        assert len(result) == 4

    def test_each_dict_has_required_keys(self):
        required = {"quarter", "reported_eps", "estimated_eps", "surprise_pct"}
        with patch("tools.yf.Ticker", return_value=_mock_eh_ticker()):
            result = get_earnings_history("AAPL", 4)

        for row in result:
            assert required <= set(row.keys()), f"Missing keys in {row}"

    def test_no_null_values(self):
        with patch("tools.yf.Ticker", return_value=_mock_eh_ticker()):
            result = get_earnings_history("AAPL", 4)

        for row in result:
            for k, v in row.items():
                assert v is not None, f"Null value for key {k!r} in {row}"

    def test_values_match_source_data(self):
        with patch("tools.yf.Ticker", return_value=_mock_eh_ticker()):
            result = get_earnings_history("AAPL", 4)

        first = result[0]
        assert first["quarter"] == "2025-04-30"
        assert first["reported_eps"] == pytest.approx(0.81, rel=1e-4)
        assert first["estimated_eps"] == pytest.approx(0.74988, rel=1e-4)
        assert first["surprise_pct"] == pytest.approx(0.0802, rel=1e-4)

    def test_n_limits_rows_returned(self):
        with patch("tools.yf.Ticker", return_value=_mock_eh_ticker()):
            result = get_earnings_history("AAPL", 2)

        assert len(result) == 2

    def test_rows_ordered_oldest_to_newest(self):
        with patch("tools.yf.Ticker", return_value=_mock_eh_ticker()):
            result = get_earnings_history("AAPL", 4)

        quarters = [r["quarter"] for r in result]
        assert quarters == sorted(quarters)

    def test_raises_when_earnings_history_none(self):
        m = MagicMock()
        m.earnings_history = None

        with patch("tools.yf.Ticker", return_value=m):
            with pytest.raises(YFNoDataError):
                get_earnings_history("FAKE", 4)

    def test_raises_when_earnings_history_empty(self):
        m = MagicMock()
        m.earnings_history = pd.DataFrame()

        with patch("tools.yf.Ticker", return_value=m):
            with pytest.raises(YFNoDataError):
                get_earnings_history("FAKE", 4)
