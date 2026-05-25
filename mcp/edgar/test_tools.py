"""Tests for EDGAR MCP tools."""
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "/Users/anton/src/stock-review/mcp/edgar")
from tools import EDGARNoDataError, get_filing_facts, get_filing_text, get_revenue_segments, get_sbc, search_filings


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


# ---------------------------------------------------------------------------
# get_revenue_segments fixtures
# ---------------------------------------------------------------------------

_MSFT_CIK = 789019
_MSFT_SEGMENT_AXIS = "srt:StatementBusinessSegmentsAxis"

_MSFT_FACTS_WITH_SEGMENTS = {
    "cik": _MSFT_CIK,
    "entityName": "Microsoft Corp.",
    "facts": {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "label": "Revenue from Contract with Customer",
                "units": {
                    "USD": [
                        # Consolidated total — no segment tag, should be ignored
                        {
                            "accn": "0000789019-24-000001",
                            "end": "2024-06-30",
                            "val": 245_122_000_000,
                            "form": "10-K",
                            "filed": "2024-07-30",
                        },
                        # Segment: Intelligent Cloud
                        {
                            "accn": "0000789019-24-000001",
                            "end": "2024-06-30",
                            "val": 87_907_000_000,
                            "form": "10-K",
                            "filed": "2024-07-30",
                            "segment": {
                                "dimension": _MSFT_SEGMENT_AXIS,
                                "value": "msft:IntelligentCloudMember",
                            },
                        },
                        # Segment: More Personal Computing
                        {
                            "accn": "0000789019-24-000001",
                            "end": "2024-06-30",
                            "val": 59_655_000_000,
                            "form": "10-K",
                            "filed": "2024-07-30",
                            "segment": {
                                "dimension": _MSFT_SEGMENT_AXIS,
                                "value": "msft:MorePersonalComputingMember",
                            },
                        },
                        # Segment: Productivity and Business Processes
                        {
                            "accn": "0000789019-24-000001",
                            "end": "2024-06-30",
                            "val": 97_560_000_000,
                            "form": "10-K",
                            "filed": "2024-07-30",
                            "segment": {
                                "dimension": _MSFT_SEGMENT_AXIS,
                                "value": "msft:ProductivityAndBusinessProcessesMember",
                            },
                        },
                        # Prior year segment — should be excluded (older end date)
                        {
                            "accn": "0000789019-23-000001",
                            "end": "2023-06-30",
                            "val": 60_000_000_000,
                            "form": "10-K",
                            "filed": "2023-07-27",
                            "segment": {
                                "dimension": _MSFT_SEGMENT_AXIS,
                                "value": "msft:IntelligentCloudMember",
                            },
                        },
                        # 10-Q segment entry — must be excluded
                        {
                            "accn": "0000789019-24-000099",
                            "end": "2024-09-30",
                            "val": 25_000_000_000,
                            "form": "10-Q",
                            "filed": "2024-10-30",
                            "segment": {
                                "dimension": _MSFT_SEGMENT_AXIS,
                                "value": "msft:IntelligentCloudMember",
                            },
                        },
                    ]
                },
            }
        }
    },
}

_RDDT_CIK = 1713445
_RDDT_FACTS_NO_SEGMENTS = {
    "cik": _RDDT_CIK,
    "entityName": "Reddit Inc.",
    "facts": {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "label": "Revenue from Contract with Customer",
                "units": {
                    "USD": [
                        # Only consolidated total, no segment breakdown
                        {
                            "accn": "0001713445-24-000001",
                            "end": "2023-12-31",
                            "val": 804_000_000,
                            "form": "10-K",
                            "filed": "2024-03-01",
                        },
                    ]
                },
            }
        }
    },
}

_SEGMENT_COMPANY_TICKERS = {
    "0": {"cik_str": _MSFT_CIK, "ticker": "MSFT", "title": "Microsoft Corp."},
    "1": {"cik_str": _RDDT_CIK, "ticker": "RDDT", "title": "Reddit Inc."},
}


def _mock_get_segments(url, **kwargs):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "company_tickers.json" in url:
        resp.json.return_value = _SEGMENT_COMPANY_TICKERS
    elif f"CIK{str(_MSFT_CIK).zfill(10)}" in url:
        resp.json.return_value = _MSFT_FACTS_WITH_SEGMENTS
    elif f"CIK{str(_RDDT_CIK).zfill(10)}" in url:
        resp.json.return_value = _RDDT_FACTS_NO_SEGMENTS
    else:
        resp.json.return_value = {}
    return resp


# ---------------------------------------------------------------------------
# get_revenue_segments tests
# ---------------------------------------------------------------------------


class TestGetRevenueSegments:
    def test_msft_returns_list(self):
        with patch("tools.requests.get", side_effect=_mock_get_segments):
            result = get_revenue_segments("MSFT")
        assert isinstance(result, list)

    def test_msft_each_entry_has_name_and_revenue(self):
        with patch("tools.requests.get", side_effect=_mock_get_segments):
            result = get_revenue_segments("MSFT")
        assert len(result) > 0
        for entry in result:
            assert "name" in entry
            assert "revenue" in entry

    def test_msft_correct_segment_count(self):
        """Should return exactly 3 segments for the latest fiscal year."""
        with patch("tools.requests.get", side_effect=_mock_get_segments):
            result = get_revenue_segments("MSFT")
        assert len(result) == 3

    def test_msft_excludes_consolidated_total(self):
        """Entries without a segment tag (consolidated total) must not appear."""
        with patch("tools.requests.get", side_effect=_mock_get_segments):
            result = get_revenue_segments("MSFT")
        revenues = [e["revenue"] for e in result]
        assert 245_122_000_000 not in revenues

    def test_msft_uses_latest_annual_period(self):
        """Prior-year segment values must not appear in results."""
        with patch("tools.requests.get", side_effect=_mock_get_segments):
            result = get_revenue_segments("MSFT")
        revenues = [e["revenue"] for e in result]
        assert 60_000_000_000 not in revenues

    def test_msft_excludes_10q_entries(self):
        """Quarterly filings must be excluded."""
        with patch("tools.requests.get", side_effect=_mock_get_segments):
            result = get_revenue_segments("MSFT")
        revenues = [e["revenue"] for e in result]
        assert 25_000_000_000 not in revenues

    def test_msft_segment_revenues_sum_correctly(self):
        with patch("tools.requests.get", side_effect=_mock_get_segments):
            result = get_revenue_segments("MSFT")
        total = sum(e["revenue"] for e in result)
        assert total == pytest.approx(87_907_000_000 + 59_655_000_000 + 97_560_000_000)

    def test_msft_segment_names_are_readable(self):
        """Names should be human-readable, not raw XBRL member strings."""
        with patch("tools.requests.get", side_effect=_mock_get_segments):
            result = get_revenue_segments("MSFT")
        names = [e["name"] for e in result]
        for name in names:
            assert "Member" not in name
            assert "msft:" not in name

    def test_rddt_returns_empty_list(self):
        """Tickers with no segment breakdown should return [] not raise."""
        with patch("tools.requests.get", side_effect=_mock_get_segments):
            result = get_revenue_segments("RDDT")
        assert result == []

    def test_raises_on_unknown_ticker(self):
        with patch("tools.requests.get", side_effect=_mock_get_segments):
            with pytest.raises(EDGARNoDataError, match="ticker"):
                get_revenue_segments("ZZZZNOTREAL")


# ---------------------------------------------------------------------------
# get_sbc fixtures
# ---------------------------------------------------------------------------

_SBC_NVDA_CIK = 1045810
_SBC_KSPI_CIK = 1985487
_SBC_NONE_CIK = 9999999

_SBC_DUAL_CIK = 7777777
_SBC_QUARTERLY_ONLY_CIK = 8888888
_SBC_MULTI_CCY_CIK = 6666666

_SBC_TICKERS = {
    "0": {"cik_str": _SBC_NVDA_CIK, "ticker": "NVDA", "title": "NVIDIA Corp."},
    "1": {"cik_str": _SBC_KSPI_CIK, "ticker": "KSPI", "title": "Joint Stock Co Kaspi.kz"},
    "2": {"cik_str": _SBC_NONE_CIK, "ticker": "NOSBC", "title": "No SBC Co."},
    "3": {"cik_str": _SBC_DUAL_CIK, "ticker": "DUAL", "title": "Dual Tagged Co."},
    "4": {"cik_str": _SBC_QUARTERLY_ONLY_CIK, "ticker": "QONLY", "title": "Quarterly Only Co."},
    "5": {"cik_str": _SBC_MULTI_CCY_CIK, "ticker": "MULTICCY", "title": "Multi Currency Co."},
}

# US 10-K filer: us-gaap, USD. The 2024-01-28 period is reported in two filings
# with different values (a restatement); the later-filed value must win. A 10-Q
# entry is present and must be excluded.
_SBC_NVDA_FACTS = {
    "facts": {
        "us-gaap": {
            "ShareBasedCompensation": {
                "units": {
                    "USD": [
                        {"start": "2022-01-31", "end": "2023-01-29", "val": 2_709_000_000, "form": "10-K", "filed": "2025-02-26"},
                        {"start": "2023-01-30", "end": "2024-01-28", "val": 3_500_000_000, "form": "10-K", "filed": "2024-02-21"},
                        {"start": "2023-01-30", "end": "2024-01-28", "val": 3_549_000_000, "form": "10-K", "filed": "2026-02-25"},
                        {"start": "2024-01-29", "end": "2025-01-26", "val": 4_737_000_000, "form": "10-K", "filed": "2026-02-25"},
                        {"start": "2025-01-27", "end": "2026-01-25", "val": 6_386_000_000, "form": "10-K", "filed": "2026-02-25"},
                        {"start": "2025-01-27", "end": "2025-04-30", "val": 1_500_000_000, "form": "10-Q", "filed": "2025-05-28"},
                    ]
                }
            }
        }
    }
}

# Foreign private issuer (20-F, IFRS, KZT). No us-gaap SBC concept — the lookup
# must fall through to ifrs-full. Restating filings repeat prior years.
_SBC_KSPI_FACTS = {
    "facts": {
        "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": []}}},
        "us-gaap": {},
        "ifrs-full": {
            "ExpenseFromSharebasedPaymentTransactionsWithEmployees": {
                "units": {
                    "KZT": [
                        {"start": "2022-01-01", "end": "2022-12-31", "val": 19_984_000_000, "form": "20-F", "filed": "2024-04-29"},
                        {"start": "2022-01-01", "end": "2022-12-31", "val": 19_984_000_000, "form": "20-F", "filed": "2025-03-10"},
                        {"start": "2023-01-01", "end": "2023-12-31", "val": 20_859_000_000, "form": "20-F", "filed": "2025-03-10"},
                        {"start": "2024-01-01", "end": "2024-12-31", "val": 16_963_000_000, "form": "20-F", "filed": "2025-03-10"},
                        {"start": "2025-01-01", "end": "2025-12-31", "val": 15_476_000_000, "form": "20-F", "filed": "2026-03-16"},
                    ]
                }
            }
        },
    }
}

# Filer with no SBC concept in any namespace.
_SBC_NONE_FACTS = {
    "facts": {
        "us-gaap": {"Revenues": {"units": {"USD": [{"end": "2024-12-31", "val": 1_000, "form": "10-K", "filed": "2025-02-01"}]}}},
        "ifrs-full": {},
    }
}

# Dual-tagged filer: both namespaces carry annual SBC. us-gaap must win.
_SBC_DUAL_FACTS = {
    "facts": {
        "us-gaap": {
            "ShareBasedCompensation": {
                "units": {"USD": [{"start": "2024-01-01", "end": "2024-12-31", "val": 500_000_000, "form": "10-K", "filed": "2025-02-01"}]}
            }
        },
        "ifrs-full": {
            "ExpenseFromSharebasedPaymentTransactionsWithEmployees": {
                "units": {"EUR": [{"start": "2024-01-01", "end": "2024-12-31", "val": 460_000_000, "form": "20-F", "filed": "2025-02-01"}]}
            }
        },
    }
}

# us-gaap SBC concept exists but carries only quarterly entries → must fall
# through to the ifrs-full annual data rather than shadow it.
_SBC_QUARTERLY_ONLY_FACTS = {
    "facts": {
        "us-gaap": {
            "ShareBasedCompensation": {
                "units": {"USD": [{"start": "2024-01-01", "end": "2024-03-31", "val": 100_000_000, "form": "10-Q", "filed": "2024-05-01"}]}
            }
        },
        "ifrs-full": {
            "ExpenseFromSharebasedPaymentTransactionsWithEmployees": {
                "units": {"GBP": [{"start": "2023-01-01", "end": "2023-12-31", "val": 88_000_000, "form": "20-F", "filed": "2024-04-01"}]}
            }
        },
    }
}

# No USD; two non-USD currencies. The one with more annual entries (CHF, 2)
# must win over the single-entry EUR, deterministically.
_SBC_MULTI_CCY_FACTS = {
    "facts": {
        "ifrs-full": {
            "ExpenseFromSharebasedPaymentTransactionsWithEmployees": {
                "units": {
                    "EUR": [{"start": "2024-01-01", "end": "2024-12-31", "val": 10_000_000, "form": "20-F", "filed": "2025-02-01"}],
                    "CHF": [
                        {"start": "2023-01-01", "end": "2023-12-31", "val": 9_000_000, "form": "20-F", "filed": "2024-02-01"},
                        {"start": "2024-01-01", "end": "2024-12-31", "val": 11_000_000, "form": "20-F", "filed": "2025-02-01"},
                    ],
                }
            }
        },
    }
}


def _mock_get_sbc(url, **kwargs):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "company_tickers.json" in url:
        resp.json.return_value = _SBC_TICKERS
    elif f"CIK{str(_SBC_NVDA_CIK).zfill(10)}" in url:
        resp.json.return_value = _SBC_NVDA_FACTS
    elif f"CIK{str(_SBC_KSPI_CIK).zfill(10)}" in url:
        resp.json.return_value = _SBC_KSPI_FACTS
    elif f"CIK{str(_SBC_NONE_CIK).zfill(10)}" in url:
        resp.json.return_value = _SBC_NONE_FACTS
    elif f"CIK{str(_SBC_DUAL_CIK).zfill(10)}" in url:
        resp.json.return_value = _SBC_DUAL_FACTS
    elif f"CIK{str(_SBC_QUARTERLY_ONLY_CIK).zfill(10)}" in url:
        resp.json.return_value = _SBC_QUARTERLY_ONLY_FACTS
    elif f"CIK{str(_SBC_MULTI_CCY_CIK).zfill(10)}" in url:
        resp.json.return_value = _SBC_MULTI_CCY_FACTS
    else:
        resp.json.return_value = {}
    return resp


# ---------------------------------------------------------------------------
# get_sbc tests
# ---------------------------------------------------------------------------


class TestGetSBC:
    def test_us_returns_required_keys(self):
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            result = get_sbc("NVDA", 4)
        assert set(result.keys()) >= {"ticker", "filing_type", "currency", "periods"}

    def test_us_filing_type_and_currency(self):
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            result = get_sbc("NVDA", 4)
        assert result["filing_type"] == "10-K"
        assert result["currency"] == "USD"

    def test_us_returns_requested_period_count(self):
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            result = get_sbc("NVDA", 4)
        assert len(result["periods"]) == 4

    def test_us_periods_newest_first(self):
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            result = get_sbc("NVDA", 4)
        ends = [p["fiscal_year"] for p in result["periods"]]
        assert ends == sorted(ends, reverse=True)
        assert result["periods"][0]["fiscal_year"] == "2026-01-25"
        assert result["periods"][0]["sbc"] == 6_386_000_000

    def test_us_dedupes_keeping_latest_filed(self):
        """The restated 2024-01-28 value (filed 2026) must win over the 2024 one."""
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            result = get_sbc("NVDA", 4)
        period = next(p for p in result["periods"] if p["fiscal_year"] == "2024-01-28")
        assert period["sbc"] == 3_549_000_000

    def test_us_excludes_quarterly_filings(self):
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            result = get_sbc("NVDA", 4)
        ends = [p["fiscal_year"] for p in result["periods"]]
        sbcs = [p["sbc"] for p in result["periods"]]
        assert "2025-04-30" not in ends
        assert 1_500_000_000 not in sbcs

    def test_each_period_tagged_edgar_xbrl(self):
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            result = get_sbc("NVDA", 4)
        assert all(p["source"] == "edgar_xbrl" for p in result["periods"])

    def test_periods_argument_limits_results(self):
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            result = get_sbc("NVDA", 2)
        assert len(result["periods"]) == 2
        assert [p["fiscal_year"] for p in result["periods"]] == ["2026-01-25", "2025-01-26"]

    def test_ifrs_foreign_filer_falls_through_to_ifrs_full(self):
        """KSPI has no us-gaap SBC; must read ifrs-full and report 20-F / KZT."""
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            result = get_sbc("KSPI", 4)
        assert result["filing_type"] == "20-F"
        assert result["currency"] == "KZT"
        assert len(result["periods"]) == 4

    def test_ifrs_returns_non_null_sbc_values(self):
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            result = get_sbc("KSPI", 4)
        assert all(isinstance(p["sbc"], int) and p["sbc"] > 0 for p in result["periods"])
        assert result["periods"][0]["fiscal_year"] == "2025-12-31"
        assert result["periods"][0]["sbc"] == 15_476_000_000

    def test_raises_when_sbc_concept_absent(self):
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            with pytest.raises(EDGARNoDataError, match="not present in filing"):
                get_sbc("NOSBC", 4)

    def test_raises_on_unknown_ticker(self):
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            with pytest.raises(EDGARNoDataError, match="ticker"):
                get_sbc("ZZZZNOTREAL", 4)

    def test_rejects_non_positive_periods(self):
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            with pytest.raises(ValueError, match="periods"):
                get_sbc("NVDA", 0)

    def test_dual_tagged_filer_prefers_us_gaap(self):
        """When both namespaces carry annual SBC, us-gaap wins (closest to yfinance)."""
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            result = get_sbc("DUAL", 4)
        assert result["currency"] == "USD"
        assert result["filing_type"] == "10-K"
        assert result["periods"][0]["sbc"] == 500_000_000

    def test_falls_through_when_us_gaap_has_only_quarterly(self):
        """A us-gaap concept with no annual entries must not shadow ifrs-full."""
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            result = get_sbc("QONLY", 4)
        assert result["currency"] == "GBP"
        assert result["filing_type"] == "20-F"
        assert result["periods"][0]["sbc"] == 88_000_000

    def test_non_usd_unit_selection_is_deterministic(self):
        """With no USD and multiple currencies, the one with most annual entries wins."""
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            result = get_sbc("MULTICCY", 4)
        assert result["currency"] == "CHF"
        assert len(result["periods"]) == 2
        assert result["periods"][0]["sbc"] == 11_000_000

    def test_periods_larger_than_available_returns_all(self):
        with patch("tools.requests.get", side_effect=_mock_get_sbc):
            result = get_sbc("KSPI", 99)
        assert len(result["periods"]) == 4
