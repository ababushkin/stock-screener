"""Tests for EDGAR MCP tools."""
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "/Users/anton/src/stock-review/mcp/edgar")
from tools import EDGARNoDataError, get_filing_facts, get_filing_text, search_filings


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


# ---------------------------------------------------------------------------
# get_filing_text fixtures
# ---------------------------------------------------------------------------

_ACCESSION = "0001045810-24-000010"
_FT_CIK = "1045810"
_FT_ACCN_NODASH = "000104581024000010"
_FT_DOC = "nvda-20240128.htm"

_INDEX_JSON = {
    "directory": {
        "name": _FT_ACCN_NODASH,
        "parent-dir": f"/Archives/edgar/data/{_FT_CIK}/",
        "item": [
            {"name": _FT_DOC, "type": "10-K", "size": "27000000"},
            {"name": "R1.htm", "type": "", "size": "100"},
        ],
    }
}

# Realistic 10-K HTML: short TOC entries followed by long section bodies.
# The TOC MD&A entry is < 200 bytes from the next Item marker.
# The actual MD&A body is > 5 000 bytes from the next Item marker.
_FILING_HTML = """<html><body>
<p><b>Table of Contents</b></p>
<p>Item 1. Business .......... 5</p>
<p>Item 1A. Risk Factors .......... 15</p>
<p>Item 7. Management&#8217;s Discussion and Analysis .......... 42</p>
<p>Item 7A. Quantitative and Qualitative .......... 78</p>
<p>Item 8. Financial Statements .......... 80</p>

<h2>Item 1. BUSINESS</h2>
<p>We design, develop, and market graphics processing units (GPUs) and system-on-chip units.</p>

<h2>Item 1A. RISK FACTORS</h2>
<p>Our business faces many risks including competition and regulatory changes.
Additional risk details follow in this section covering all material risks.</p>

<h2>Item 7. MANAGEMENT&#8217;S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION
AND RESULTS OF OPERATIONS</h2>
<p>The following discussion and analysis provides information which management believes
is relevant to an assessment of our consolidated results of operations and financial
condition. This discussion should be read in conjunction with our consolidated
financial statements and notes thereto.</p>
<p>Revenue for fiscal year 2024 was $60.9 billion, an increase of 122% compared to
fiscal year 2023 revenue of $26.9 billion. Data Center revenue increased 217%
year-over-year, driven by strong demand for our Hopper GPU computing platform.</p>
<p>Operating income was $32.9 billion for fiscal year 2024, compared to $4.2 billion
for fiscal year 2023. Net income was $29.8 billion, or $11.93 per diluted share,
compared to $4.4 billion, or $1.74 per diluted share, for fiscal year 2023.</p>
<p>We continue to see strong demand across all segments as hyperscale cloud providers
and enterprise customers accelerate AI infrastructure investments.</p>

<h2>Item 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK</h2>
<p>We are exposed to market risk in the ordinary course of business, including interest
rate risk and foreign currency exchange rate risk.</p>

<h2>Item 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA</h2>
<p>See consolidated financial statements beginning on page 80.</p>
</body></html>"""


def _mock_get_filing(url, **kwargs):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "company_tickers.json" in url:
        resp.json.return_value = _COMPANY_TICKERS
    elif "/submissions/" in url:
        resp.json.return_value = _SUBMISSIONS
    elif "/companyfacts/" in url:
        resp.json.return_value = _COMPANY_FACTS
    elif "index.json" in url:
        resp.json.return_value = _INDEX_JSON
    elif url.endswith(".htm"):
        resp.text = _FILING_HTML
    else:
        resp.json.return_value = {}
    return resp


# ---------------------------------------------------------------------------
# get_filing_text tests
# ---------------------------------------------------------------------------


class TestGetFilingText:
    def test_returns_nonempty_string(self):
        with patch("tools.requests.get", side_effect=_mock_get_filing):
            result = get_filing_text(_ACCESSION, "MD&A")
        assert isinstance(result, str) and len(result) > 0

    def test_mda_contains_recognizable_prose(self):
        with patch("tools.requests.get", side_effect=_mock_get_filing):
            result = get_filing_text(_ACCESSION, "MD&A")
        assert "revenue" in result.lower() or "discussion" in result.lower()

    def test_case_insensitive_section_name(self):
        with patch("tools.requests.get", side_effect=_mock_get_filing):
            lower = get_filing_text(_ACCESSION, "md&a")
            upper = get_filing_text(_ACCESSION, "MD&A")
        assert lower == upper

    def test_does_not_include_next_section(self):
        with patch("tools.requests.get", side_effect=_mock_get_filing):
            result = get_filing_text(_ACCESSION, "MD&A")
        assert "market risk" not in result.lower()

    def test_risk_factors_section(self):
        with patch("tools.requests.get", side_effect=_mock_get_filing):
            result = get_filing_text(_ACCESSION, "Risk Factors")
        assert "risk" in result.lower()

    def test_raises_for_unknown_section(self):
        with patch("tools.requests.get", side_effect=_mock_get_filing):
            with pytest.raises(EDGARNoDataError):
                get_filing_text(_ACCESSION, "Nonexistent Section XYZ123")

    def test_uses_primary_document_from_index(self):
        """Primary document must be fetched from the filing index, not hardcoded."""
        fetched_urls = []

        def tracking_mock(url, **kwargs):
            fetched_urls.append(url)
            return _mock_get_filing(url, **kwargs)

        with patch("tools.requests.get", side_effect=tracking_mock):
            get_filing_text(_ACCESSION, "MD&A")

        doc_urls = [u for u in fetched_urls if u.endswith(".htm")]
        assert any(_FT_DOC in u for u in doc_urls)
