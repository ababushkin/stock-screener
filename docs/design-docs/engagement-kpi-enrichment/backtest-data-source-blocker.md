# Backtest data-source blocker — Task 6 Slice B finding (ABA-66)

**Run date:** 2026-05-14
**Branch:** `anton/aba-66-eng-kpi-spike`
**Status:** ⛔ **Blocker raised — Task 4 feasibility assumption invalidated.**

## TL;DR

Slice B collection across 23 ticker-quarters (META 8 + RDDT 9 + PINS 6) finds only **2 samples** clear both T0 (±7d drift) and T1 (±14d drift) wayback gates. The remaining 21 attrit on wayback coverage gaps, not on harness bugs.

The Task 4 feasibility note's "viable for 40 ticker-quarters" verdict was based on a single validated sample (META Q1 2025). Population-level wayback coverage of `finance.yahoo.com/quote/<TICKER>/analysis/` is materially sparser than that sample implied.

NFR7 (≥60% revision-direction agreement on ≥24 valid samples) cannot be evaluated with this data source at any tolerance that preserves signal meaning. **The spike is in Task 7 PROCEED/RESHAPE/KILL territory.**

## Evidence

### Collection harness

`tests/spike/collect_backtest_fixtures.py` (committed). Per ticker-quarter:
1. Find 8-K Ex 99.1 URL via EDGAR submissions API.
2. Extract KPI YoY via per-ticker regex (META/RDDT/PINS).
3. Hit wayback redirect-resolution for T0 (print+1d) and T1 (print+28d), parse "Next Year" avg estimate.

Retry-on-5xx (3 attempts, exponential backoff), 1-second wayback politeness sleep, drift-tolerance gates (T0 ±7d, T1 ±14d).

### Attrition tally (23 ticker-quarters)

| Status | T0 count | T1 count |
|---|---|---|
| ok | 5 | 2 |
| drift_too_large | 15 | 15 |
| no_snapshot | 2 | 3 |
| fetch_failed (post-retry) | 1 | 3 |

### Drift histogram (days from target)

**T0** (target = print + 1d):
`[0, 0, 0, 0, 2, 8, 14, 24, 25, 33, 40, 50, 66, 92, 105, 157, 178, 267, 351, 448]`

**T1** (target = print + 28d):
`[3, 7, 19, 22, 24, 24, 41, 50, 65, 93, 114, 132, 163, 205, 294, 378, 475]`

The 100+ day drifts indicate wayback has multi-month gaps in coverage of Yahoo Finance analyst pages for these tickers. Even loosening T1 tolerance to ±30d only adds 4 samples (still <24 floor).

### Pattern by ticker

KPI extraction (leg 1) succeeded 22/23 — single PINS Q4-2025 miss likely a regex edge case, fixable. Leg 1 is not the blocker.

Wayback (leg 2) coverage is asymmetric: META Q1 2025 (the Task 4 sample) sits in a relatively well-covered window. Older quarters and RDDT/PINS generally have sparser coverage.

## Why this happened

The Task 4 verdict was reached on N=1. The single sample (META Q1 2025) happened to fall in a high-coverage window — META is one of the most-archived tickers and Q1 2025 was a high-attention earnings cycle (post-AI-capex announcements). Generalizing from this sample to "viable for 40" did not survive population contact.

This is a Universal-P4 failure (named assumptions; test the risky ones before committing). The implicit assumption was "wayback coverage at the validated sample generalizes to the seed-ticker set." The validation needed a coverage survey across ≥5 ticker-quarters, not one end-to-end pull.

## Options for Task 7

The spike-decision memo (Task 7) must now choose among:

### A. RESHAPE — alternative revision-data source
Switch from wayback-Yahoo to a paid historical-estimates source:
- **FMP API** (~$15/mo, free tier of 250 calls/day) — `/v3/analyst-estimates/<ticker>` returns historical EPS+revenue estimates by date. Plausible fit. **Pros**: reliable historical access. **Cons**: subscription cost, API key management, external dependency.
- **Visible Alpha / Bloomberg / Refinitiv** — institutional, prohibitive for a personal skill-pack.

Estimated cost to validate: 1–2 days to integrate FMP and re-run Slice B.

### B. RESHAPE — different signal proxy
Replace consensus-revenue revision with a free directional proxy:
- **Stock-price change T0 → T1** as proxy for sentiment shift (weak signal, but free). NFR7 becomes "engagement-direction predicts 4-week post-print price direction," which is a much noisier target — likely lower hit rate, but defensible if the spike rebrand admits it.
- **Yahoo "Recommendation Trend"** (analyst rating count changes) via yfinance — currently no historical access, but archived in 13D/G occasionally. Likely not viable at scale.

### C. RESHAPE — drop NFR7 entirely, ship advisory
The modifier ships with a disclaimer ("directional heuristic, not statistically validated") and flag-gated default-off (`--engagement-modifier` opt-in). No backtest, no claim of predictive validity. This is the Task 4 "ship disabled-by-default" fallback path.

### D. KILL
ABA-66 cannot meet the design-doc NFR7 with available free data sources, and the cost of fixing it (Option A) is out of scope for a personal skill-pack. Mothball the modifier; close ABA-66 with the spike findings preserved.

## Recommendation

**Option C (ship advisory) is the smallest correct response.** The modifier's mechanical correctness is validated by Tasks 1, 3, 5 (extraction is deterministic; constants are explainable; effect is bounded). What's not validated is whether the *signal predicts consensus revisions*. Shipping advisory + flag-gated honestly communicates that gap to the future user (me) without burning subscription budget on Option A or noisy-signal-chasing on Option B.

If the user later finds the modifier subjectively useful in real research workflows, Option A is the natural next investment (validate post-hoc with paid data when there's a usage signal).

If subjective use shows the modifier is irrelevant, the spike is in fact a KILL (Option D) and the advisory-shipped artefact gets removed cleanly because it was flag-gated from day one.

## Linkage

- Supersedes the "PROCEED" verdict of `backtest-data-source.md` for the Wayback-Yahoo path.
- Surfaces to Task 7 (`spike-decision.md`) as the primary input.
- Fixtures and harness committed for audit: `tests/fixtures/engagement_kpi/` and `tests/spike/collect_backtest_fixtures.py`.
