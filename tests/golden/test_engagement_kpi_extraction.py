"""Golden-fixture extraction tests for the engagement-KPI modifier (ABA-66 Task 12).

Two paths covered:

1. **Press-release KPI extraction** (`tests/fixtures/engagement_kpi/press_release_snippets.json`).
   Per-ticker regex against frozen 8-K Ex 99.1 source-phrase snippets. Asserts
   NFR2's ≥80% precision target with numerical tolerance ±2% on `kpi_value` and
   exact-match on `direction` across the seed set (META, RDDT, PINS × 5 quarters each).

2. **Yahoo `/analysis/` EPS Trend extraction** (`tests/fixtures/engagement_kpi/yahoo_eps_trend_snippets.json`).
   The lag-confirmer revision signal from spike-decision §"Lead vs confirm".
   Asserts the Next-Year Current vs 30-Days-Ago revision_pct + direction extraction
   on frozen DOM snippets.

Hermetic — no network, no live SEC/Yahoo fetches.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import pytest


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "engagement_kpi"
PR_SNIPPETS = FIXTURES / "press_release_snippets.json"
YAHOO_SNIPPETS = FIXTURES / "yahoo_eps_trend_snippets.json"

DEADBAND = 0.02
STRONG = 0.08


# ---------------------------------------------------------------------------
# Press-release extraction — per-ticker regex bank
# ---------------------------------------------------------------------------

PR_PATTERNS = {
    # Group 1 = kpi_value (float), Group 2 = yoy % (int)
    "META": re.compile(
        r"DAP was\s+([0-9]+\.[0-9]+)\s+billion[^.]*?increase of\s+([0-9]+)%\s+year-over-year",
        re.IGNORECASE,
    ),
    # Group 1 = yoy % (int), Group 2 = kpi_value (float)
    "RDDT": re.compile(
        r"Daily Active Uniques.*?increased\s+([0-9]+)%\s+year-over-year to\s+([0-9]+\.[0-9]+)\s+million",
        re.IGNORECASE | re.DOTALL,
    ),
    # Group 1 = yoy % (int), Group 2 = kpi_value (int)
    "PINS": re.compile(
        r'Global Monthly Active Users.*?increased\s+([0-9]+)%\s+year over year to\s+([0-9]+)\s+million',
        re.IGNORECASE | re.DOTALL,
    ),
}


def normalize(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text)


def derive_direction_magnitude(yoy: float) -> tuple[int, str]:
    if abs(yoy) < DEADBAND:
        return 0, "neutral"
    direction = 1 if yoy > 0 else -1
    magnitude = "strong" if abs(yoy) >= STRONG else "mild"
    return direction, magnitude


def extract_pr(ticker: str, text: str) -> dict:
    pattern = PR_PATTERNS[ticker]
    m = pattern.search(text)
    if not m:
        raise ValueError(f"{ticker}: no source-phrase match")

    if ticker == "META":
        kpi_value = float(m.group(1))
        yoy = float(m.group(2)) / 100
    elif ticker == "RDDT":
        yoy = float(m.group(1)) / 100
        kpi_value = float(m.group(2))
    elif ticker == "PINS":
        yoy = float(m.group(1)) / 100
        kpi_value = float(m.group(2))
    else:
        raise ValueError(f"Unknown ticker {ticker}")

    direction, magnitude = derive_direction_magnitude(yoy)
    return {
        "kpi_value": kpi_value,
        "yoy_change": round(yoy, 4),
        "direction": direction,
        "magnitude": magnitude,
    }


# ---------------------------------------------------------------------------
# Press-release fixtures: tabulate & assert ≥80% precision per NFR2
# ---------------------------------------------------------------------------

def _load_pr_fixtures():
    data = json.loads(PR_SNIPPETS.read_text())
    rows = []
    for ticker, entries in data.items():
        if ticker.startswith("_"):
            continue
        for entry in entries:
            rows.append((ticker, entry["period"], entry["snippet"], entry["expected"]))
    return rows


PR_ROWS = _load_pr_fixtures()


@pytest.mark.parametrize(
    "ticker,period,snippet,expected",
    PR_ROWS,
    ids=[f"{t}-{p}" for t, p, _, _ in PR_ROWS],
)
def test_press_release_extraction(ticker, period, snippet, expected):
    text = normalize(snippet)
    actual = extract_pr(ticker, text)

    # Direction is exact-match per NFR2.
    assert actual["direction"] == expected["direction"], (
        f"{ticker} {period}: direction {actual['direction']} != expected {expected['direction']}"
    )
    # Magnitude follows from yoy + thresholds — assert as a derived invariant.
    assert actual["magnitude"] == expected["magnitude"], (
        f"{ticker} {period}: magnitude {actual['magnitude']} != expected {expected['magnitude']}"
    )
    # Numerical kpi_value within ±2% (NFR2 tolerance band).
    expected_kpi = expected["kpi_value"]
    tolerance = max(abs(expected_kpi) * 0.02, 1e-6)
    assert abs(actual["kpi_value"] - expected_kpi) <= tolerance, (
        f"{ticker} {period}: kpi_value {actual['kpi_value']} outside ±2% of {expected_kpi}"
    )


def test_press_release_aggregate_precision_at_least_80pct():
    """NFR2 fleet-level assertion: across the committed fixtures, ≥80% of rows
    must hit both direction (exact) and kpi_value (±2%). Individual rows above
    catch per-quarter regressions; this one catches a fleet drift where
    several quarters slip under tolerance simultaneously."""
    hits = 0
    total = 0
    for ticker, _period, snippet, expected in PR_ROWS:
        total += 1
        try:
            actual = extract_pr(ticker, normalize(snippet))
        except ValueError:
            continue
        direction_ok = actual["direction"] == expected["direction"]
        tol = max(abs(expected["kpi_value"]) * 0.02, 1e-6)
        value_ok = abs(actual["kpi_value"] - expected["kpi_value"]) <= tol
        if direction_ok and value_ok:
            hits += 1

    precision = hits / total
    assert precision >= 0.80, (
        f"Fleet precision {precision:.0%} < 80% target ({hits}/{total} rows)"
    )


# ---------------------------------------------------------------------------
# Yahoo /analysis/ EPS Trend extraction (lag-confirmer revision signal)
# ---------------------------------------------------------------------------

EPS_TREND_HEADER_RE = re.compile(
    r"<th[^>]*>\s*EPS Trend\s*</th>(.*?)</thead>", re.IGNORECASE | re.DOTALL
)
EPS_TREND_BODY_RE = re.compile(r"<tbody>(.*?)</tbody>", re.IGNORECASE | re.DOTALL)
ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)


def extract_eps_trend_next_year(snippet: str) -> dict:
    """Extract the Next-Year EPS Trend Current vs 30 Days Ago revision.

    Returns {"current_ny", "thirty_days_ago_ny", "revision_pct", "direction"}.
    Raises ValueError if structure missing.
    """
    body_match = EPS_TREND_BODY_RE.search(snippet)
    if not body_match:
        raise ValueError("EPS Trend tbody not found")

    rows = ROW_RE.findall(body_match.group(1))
    parsed = {}
    for row in rows:
        cells = [re.sub(r"\s+", " ", c).strip() for c in CELL_RE.findall(row)]
        if not cells:
            continue
        label = cells[0]
        # Next Year is column index 4 (after label): Current Qtr, Next Qtr, Current Year, Next Year
        if len(cells) >= 5:
            try:
                parsed[label] = float(cells[4])
            except ValueError:
                continue

    current = parsed.get("Current Estimate")
    thirty = parsed.get("30 Days Ago")
    if current is None or thirty is None:
        raise ValueError("Current Estimate / 30 Days Ago rows missing")
    if thirty == 0:
        raise ValueError("30 Days Ago is zero — cannot compute revision_pct")

    revision_pct = (current - thirty) / thirty
    if abs(revision_pct) < 1e-6:
        direction = 0
    else:
        direction = 1 if revision_pct > 0 else -1

    return {
        "current_ny": current,
        "thirty_days_ago_ny": thirty,
        "revision_pct": revision_pct,
        "direction": direction,
    }


def _load_yahoo_fixtures():
    data = json.loads(YAHOO_SNIPPETS.read_text())
    return [(e["ticker"], e["snippet"], e["expected"]) for e in data["snippets"]]


YAHOO_ROWS = _load_yahoo_fixtures()


@pytest.mark.parametrize(
    "ticker,snippet,expected",
    YAHOO_ROWS,
    ids=[t for t, _, _ in YAHOO_ROWS],
)
def test_yahoo_eps_trend_extraction(ticker, snippet, expected):
    actual = extract_eps_trend_next_year(snippet)
    assert actual["current_ny"] == expected["current_ny"]
    assert actual["thirty_days_ago_ny"] == expected["thirty_days_ago_ny"]
    assert actual["direction"] == expected["direction"]
    # revision_pct tolerance: 0.001 abs (4 sig-fig fixture values).
    assert abs(actual["revision_pct"] - expected["revision_pct"]) < 1e-3, (
        f"{ticker}: revision_pct {actual['revision_pct']:.4f} != expected {expected['revision_pct']:.4f}"
    )


def test_yahoo_eps_trend_missing_body_raises():
    with pytest.raises(ValueError, match="tbody not found"):
        extract_eps_trend_next_year("<html><body>no table here</body></html>")


def test_yahoo_eps_trend_missing_30d_row_raises():
    incomplete = (
        "<tbody><tr><td>Current Estimate</td><td>7.42</td><td>8.10</td>"
        "<td>32.15</td><td>36.80</td></tr></tbody>"
    )
    with pytest.raises(ValueError, match="Current Estimate / 30 Days Ago rows missing"):
        extract_eps_trend_next_year(incomplete)
