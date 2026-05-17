"""Dry-run driver for the engagement-KPI drift CI gate (ABA-66 Task 13 / ADR D4).

For each ticker in `skills/_shared/engagement_kpi_map.json` (`tickers` block), runs
the source-phrase extractor against the most-recent committed fixture in
`tests/fixtures/engagement_kpi/press_release_snippets.json` and emits a per-ticker
status. CI invokes this in a hermetic mode (fixtures only); the same driver can
later be pointed at a live EDGAR fetch by swapping the snippet source.

State is read from / written to a JSON file (`--state-file`) carrying the
`consecutive_failures` count per ticker. The CI workflow restores prior state
via actions/cache and persists it back, so two consecutive non-applied runs
trip the gate per ADR D4.

Exit codes
----------
0  — all tickers `applied` (or below the 2-consecutive-failure threshold)
1  — at least one ticker has hit the threshold
2  — driver-level error (missing map, malformed fixtures)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAP_PATH = REPO_ROOT / "skills" / "_shared" / "engagement_kpi_map.json"
FIXTURES_PATH = REPO_ROOT / "tests" / "fixtures" / "engagement_kpi" / "press_release_snippets.json"

CONSECUTIVE_FAILURE_THRESHOLD = 2

sys.path.insert(0, str(REPO_ROOT / "tests" / "golden"))
from test_engagement_kpi_extraction import extract_pr, normalize  # noqa: E402


def latest_snippet(fixtures: dict, ticker: str) -> dict | None:
    rows = fixtures.get(ticker)
    if not rows:
        return None
    # Fixtures are committed newest-first per ticker (Q1 2026 → Q1 2025).
    return rows[0]


def dry_run_ticker(ticker: str, snippet_row: dict) -> dict:
    try:
        actual = extract_pr(ticker, normalize(snippet_row["snippet"]))
    except Exception as exc:
        return {"status": "unavailable", "reason": f"extraction_failed: {exc}"}

    expected = snippet_row["expected"]
    direction_ok = actual["direction"] == expected["direction"]
    tol = max(abs(expected["kpi_value"]) * 0.02, 1e-6)
    value_ok = abs(actual["kpi_value"] - expected["kpi_value"]) <= tol

    if direction_ok and value_ok:
        return {"status": "applied", "kpi_value": actual["kpi_value"], "direction": actual["direction"]}
    return {"status": "unavailable", "reason": "extraction_drift", "actual": actual, "expected": expected}


def run(state_path: Path, force_unavailable: list[str]) -> int:
    if not MAP_PATH.exists():
        print(f"ERROR: KPI map missing at {MAP_PATH}", file=sys.stderr)
        return 2
    if not FIXTURES_PATH.exists():
        print(f"ERROR: PR fixtures missing at {FIXTURES_PATH}", file=sys.stderr)
        return 2

    kpi_map = json.loads(MAP_PATH.read_text())
    fixtures = json.loads(FIXTURES_PATH.read_text())
    seed_tickers = sorted(kpi_map.get("tickers", {}).keys())

    if state_path.exists():
        state = json.loads(state_path.read_text())
    else:
        state = {"consecutive_failures": {}}
    counts = state.setdefault("consecutive_failures", {})

    per_ticker = {}
    tripped = []
    for ticker in seed_tickers:
        snippet = latest_snippet(fixtures, ticker)
        if snippet is None:
            result = {"status": "unavailable", "reason": "no_fixture"}
        elif ticker in force_unavailable:
            result = {"status": "unavailable", "reason": "forced_by_dispatch"}
        else:
            result = dry_run_ticker(ticker, snippet)

        if result["status"] == "applied":
            counts[ticker] = 0
        else:
            counts[ticker] = counts.get(ticker, 0) + 1

        per_ticker[ticker] = {**result, "consecutive_failures": counts[ticker]}
        if counts[ticker] >= CONSECUTIVE_FAILURE_THRESHOLD:
            tripped.append(ticker)

    state["last_results"] = per_ticker
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")

    print(json.dumps({"seed_tickers": seed_tickers, "per_ticker": per_ticker, "tripped": tripped}, indent=2))

    if tripped:
        print(
            f"\nDRIFT GATE TRIPPED: {', '.join(tripped)} non-applied for "
            f"≥{CONSECUTIVE_FAILURE_THRESHOLD} consecutive runs (ADR D4).",
            file=sys.stderr,
        )
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state-file",
        type=Path,
        default=REPO_ROOT / ".github" / "drift-state" / "engagement_kpi.json",
        help="JSON file holding consecutive_failures across runs (cached in CI).",
    )
    parser.add_argument(
        "--force-unavailable",
        default="",
        help="Comma-separated tickers to force to status=unavailable (manual-dispatch failure test).",
    )
    args = parser.parse_args()
    forced = [t.strip() for t in args.force_unavailable.split(",") if t.strip()]
    return run(args.state_file, forced)


if __name__ == "__main__":
    sys.exit(main())
