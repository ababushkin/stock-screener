"""Reproducibility check for engagement-KPI extraction pipeline (ABA-66 Task 3).

Walking-skeleton harness. For each ticker in the seed engagement_kpi_map.json,
fetch the locked EDGAR 8-K Exhibit 99.1 URL, run the deterministic text-extraction
pipeline 5x, and assert identical derivation across trials. Locks in the regression
behaviour the Task 12 golden-fixture test will subsume once we hit PROCEED.

Scope: deterministic pipeline only (HTML fetch + regex + derivation). The
Claude-runtime LLM extraction layer is out of scope here — Task 12 covers it.

Run: python tests/spike/engagement_kpi_reproducibility.py
"""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MAP_PATH = REPO / "skills" / "_shared" / "engagement_kpi_map.json"

UA = "Stock Review Skill-Pack babushkin.anton@gmail.com"
TRIALS = 5
DEADBAND = 0.02
STRONG = 0.08

# Locked expected values from spike-outputs.md (Task 1).
EXPECTED = {
    "META": {
        "kpi_value": 3.56,
        "yoy_change": 0.04,
        "direction": 1,
        "magnitude": "mild",
        "base_anchor_multiplier": 1.02,
    },
    "RDDT": {
        "kpi_value": 126.8,
        "yoy_change": 0.17,
        "direction": 1,
        "magnitude": "strong",
        "base_anchor_multiplier": 1.04,
    },
}

# Per-ticker extraction patterns. Group 1 = kpi_value, Group 2 = yoy %.
PATTERNS = {
    "META": re.compile(
        r"DAP was\s+([0-9]+\.[0-9]+)\s+billion[^.]*?increase of\s+([0-9]+)%\s+year-over-year",
        re.IGNORECASE,
    ),
    "RDDT": re.compile(
        r'Daily Active Uniques.*?increased\s+([0-9]+)%\s+year-over-year to\s+([0-9]+\.[0-9]+)\s+million',
        re.IGNORECASE | re.DOTALL,
    ),
}


def fetch(url: str) -> str:
    """Fetch HTML with SEC-compliant UA. Errors out loud if non-200."""
    result = subprocess.run(
        ["curl", "-sS", "-f", "-A", UA, url],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: {result.stderr}")
    return result.stdout


def normalize(raw_html: str) -> str:
    """Strip tags, decode entities, collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text


def derive(yoy: float) -> tuple[int, str, float]:
    """Apply deadband + magnitude thresholds → (direction, magnitude, multiplier)."""
    if abs(yoy) < DEADBAND:
        return 0, "neutral", 1.00
    direction = 1 if yoy > 0 else -1
    magnitude = "strong" if abs(yoy) >= STRONG else "mild"
    step = 0.04 if magnitude == "strong" else 0.02
    return direction, magnitude, round(1 + direction * step, 4)


def extract(ticker: str, text: str) -> dict:
    pattern = PATTERNS[ticker]
    match = pattern.search(text)
    if not match:
        raise RuntimeError(f"{ticker}: source-phrase pattern did not match")

    if ticker == "META":
        kpi_value = float(match.group(1))
        yoy = float(match.group(2)) / 100
    elif ticker == "RDDT":
        yoy = float(match.group(1)) / 100
        kpi_value = float(match.group(2))
    else:
        raise RuntimeError(f"Unknown ticker {ticker}")

    direction, magnitude, multiplier = derive(yoy)
    return {
        "kpi_value": kpi_value,
        "yoy_change": round(yoy, 4),
        "direction": direction,
        "magnitude": magnitude,
        "base_anchor_multiplier": multiplier,
    }


def main() -> int:
    seed_map = json.loads(MAP_PATH.read_text())
    failures: list[str] = []

    for ticker, expected in EXPECTED.items():
        url = seed_map["tickers"][ticker]["evidence"]["exhibit_url"]
        raw = fetch(url)
        text = normalize(raw)

        trials = [extract(ticker, text) for _ in range(TRIALS)]

        # Reproducibility: every trial identical.
        for i, trial in enumerate(trials[1:], start=2):
            if trial != trials[0]:
                failures.append(f"{ticker} trial {i} drifted from trial 1: {trial} != {trials[0]}")

        # Correctness: trial 1 matches locked spike values.
        if trials[0] != expected:
            failures.append(f"{ticker} extraction != locked spike values: {trials[0]} != {expected}")

        print(f"  {ticker}: {trials[0]}  ({TRIALS}/{TRIALS} identical)")

    if failures:
        print("\nFAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"\nOK: {len(EXPECTED)} tickers, {TRIALS} trials each, zero drift")
    return 0


if __name__ == "__main__":
    sys.exit(main())
