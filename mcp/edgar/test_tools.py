"""Tests for EDGAR MCP tools."""
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "/Users/anton/src/stock-review/mcp/edgar")
from tools import EDGARNoDataError, get_filing_facts, search_filings


# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

_CIK = "0001108524"  # Salesforce

_COMPANY_TICKERS = {
    "0": {"cik_str": 1108524, "ticker": "CRM", "title": "Salesforce Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp."},
}

_SUBMISSIONS = {
    "cik": "0001108524",
    "name": "Salesforce Inc.",
    "tickers": ["CRM"],
    "filings": {
        "recent": {
            "accessionNumber": [
                "0001108524-24-000012",
                "0001108524-23-000008",
                "0001108524-22-000005",
            ],
            "filingDate": ["2024-03-15", "2023-03-14", "2022-03-11"],
            "form": ["10-K", "10-K", "10-K"],
            "primaryDocument": ["crm-20240131.htm", "crm-20230131.htm", "crm-20220131.htm"],
        }
    },
}

# Two 10-K filings for the same concept; the one with a later end date should win.
# If tied on end date, the one filed later should win.
_COMPANY_FACTS = {
    "cik": 1108524,
    "entityName": "Salesforce Inc.",
    "facts": {
        "us-gaap": {
            "ShareBasedCompensation": {
                "label": "Share-based Compensation",
                "description": "...",
                "units": {
                    "USD": [
                        {
                            "accn": "0001108524-23-000008",
                            "cik": 1108524,
                            "entityName": "Salesforce Inc.",
                            "end": "2023-01-31",
                            "val": 1_600_000_000,
                            "form": "10-K",
                            "filed": "2023-03-14",
                        },
                        {
                            "accn": "0001108524-24-000012",
                            "cik": 1108524,
                            "entityName": "Salesforce Inc.",
                            "end": "2024-01-31",
                            "val": 2_100_000_000,
                            "form": "10-K",
                            "filed": "2024-03-15",
                        },
                        # 10-Q entry — must be excluded
                        {
                            "accn": "0001108524-24-000099",
                            "cik": 1108524,
                            "entityName": "Salesforce Inc.",
                            "end": "2024-04-30",
                            "val": 500_000_000,
                            "form": "10-Q",
                            "filed": "2024-06-01",
                        },
                    ]
                },
            }
        }
    },
}


def _mock_get(url, **kwargs):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "company_tickers.json" in url:
        resp.json.return_value = _COMPANY_TICKERS
    elif "/submissions/" in url:
        resp.json.return_value = _SUBMISSIONS
    elif "/companyfacts/" in url:
        resp.json.return_value = _COMPANY_FACTS
    else:
        resp.json.return_value = {}
    return resp


# ---------------------------------------------------------------------------
# search_filings tests
# ---------------------------------------------------------------------------


class TestSearchFilings:
    def test_returns_list(self):
        with patch("tools.requests.get", side_effect=_mock_get):
            result = search_filings("CRM", "10-K")
        assert isinstance(result, list)

    def test_each_entry_has_required_keys(self):
        with patch("tools.requests.get", side_effect=_mock_get):
            result = search_filings("CRM", "10-K")
        for entry in result:
            assert "accession_number" in entry
            assert "filing_date" in entry

    def test_filters_to_requested_form_type(self):
        with patch("tools.requests.get", side_effect=_mock_get):
            result = search_filings("CRM", "10-K")
        for entry in result:
            assert entry["form"] == "10-K"

    def test_at_least_one_result(self):
        with patch("tools.requests.get", side_effect=_mock_get):
            result = search_filings("CRM", "10-K")
        assert len(result) >= 1

    def test_raises_on_unknown_ticker(self):
        with patch("tools.requests.get", side_effect=_mock_get):
            with pytest.raises(EDGARNoDataError, match="ticker"):
                search_filings("ZZZZNOTREAL", "10-K")


# ---------------------------------------------------------------------------
# get_filing_facts tests
# ---------------------------------------------------------------------------


class TestGetFilingFacts:
    def test_returns_required_keys(self):
        with patch("tools.requests.get", side_effect=_mock_get):
            result = get_filing_facts("CRM", "ShareBasedCompensation")
        assert set(result.keys()) >= {"ticker", "concept", "value", "unit", "period_end", "form", "filed"}

    def test_returns_most_recent_10k_value(self):
        """Should pick the 10-K with the latest period_end, not the 10-Q."""
        with patch("tools.requests.get", side_effect=_mock_get):
            result = get_filing_facts("CRM", "ShareBasedCompensation")
        assert result["value"] == pytest.approx(2_100_000_000)
        assert result["period_end"] == "2024-01-31"

    def test_excludes_non_annual_forms(self):
        """The 10-Q entry (end=2024-04-30) must not be returned."""
        with patch("tools.requests.get", side_effect=_mock_get):
            result = get_filing_facts("CRM", "ShareBasedCompensation")
        assert result["form"] in ("10-K", "10-K/A")

    def test_unit_is_usd(self):
        with patch("tools.requests.get", side_effect=_mock_get):
            result = get_filing_facts("CRM", "ShareBasedCompensation")
        assert result["unit"] == "USD"

    def test_ticker_and_concept_in_result(self):
        with patch("tools.requests.get", side_effect=_mock_get):
            result = get_filing_facts("CRM", "ShareBasedCompensation")
        assert result["ticker"] == "CRM"
        assert result["concept"] == "ShareBasedCompensation"

    def test_raises_on_unknown_concept(self):
        with patch("tools.requests.get", side_effect=_mock_get):
            with pytest.raises(EDGARNoDataError, match="concept"):
                get_filing_facts("CRM", "NonExistentConceptXYZ")

    def test_raises_on_unknown_ticker(self):
        with patch("tools.requests.get", side_effect=_mock_get):
            with pytest.raises(EDGARNoDataError, match="ticker"):
                get_filing_facts("ZZZZNOTREAL", "ShareBasedCompensation")
