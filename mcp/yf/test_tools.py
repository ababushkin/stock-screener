"""Tests for yfinance MCP tools."""
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, "/Users/anton/src/stock-review/mcp/yf")
from tools import YFNoDataError, get_estimates


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
