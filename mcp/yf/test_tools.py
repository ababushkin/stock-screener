"""Tests for yfinance MCP tools."""
import math
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, "/Users/anton/src/stock-review/mcp/yf")
from tools import YFNoDataError, get_estimates, get_financials


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
