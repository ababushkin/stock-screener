---
name: stock-portfolio
description: Portfolio-level snapshot across the seven covered tickers. Invoked as `/stock-portfolio`. Reads the latest cached screen / signal / model outputs from `reports/` for each ticker in `COVERAGE.md` and emits a ranked table (ticker / current price / our IV / margin of safety / verdict / last updated) so the operator can answer "where should I add" in one invocation. Does NOT re-run the model. Use whenever the user asks a portfolio-level question — "which of the seven is most undervalued right now", "where should I add", "what's the gap across the portfolio", "rank the covered tickers" — even if they don't say "portfolio".
---

# Portfolio — Cross-Ticker Snapshot

**Command:** `/stock-portfolio`
**Purpose:** Single-invocation portfolio view across all seven covered tickers. Reads the latest cached `/stock-screen`, `/stock-signal`, and `/stock-model` outputs from `reports/`, computes margin-of-safety vs the freshest available price per ticker, layers an SPY/QQQ benchmark overlay (ABA-125) so each row carries an opportunity-cost verdict, and prints a verdict-ranked table plus a JSON snapshot at `reports/PORTFOLIO_YYYYMMDD.json`.

This skill is a **read-only aggregator** over the per-ticker pipeline — it never re-runs `/stock-screen`, `/stock-signal`, or `/stock-model`. The single network dependency is one yfinance call each for SPY and QQQ to fetch trailing total-return CAGR over the model horizon; the per-ticker rows themselves are entirely cache-driven. If a ticker is missing fresh inputs, the row still appears and the gap is flagged — the operator decides whether to re-run the upstream skill.

---

## 1. Identity

- **Skill name:** stock-portfolio
- **Command:** `/stock-portfolio` (no ticker arguments — the universe is fixed by `COVERAGE.md`)
- **Purpose:** Produce a portfolio-level ranked snapshot across the seven covered tickers using only cached reports.

---

## 2. Methodology

The portfolio view answers two questions in one invocation:

1. **Across the seven covered names, where is the largest gap between our base-case intrinsic value and the market price right now, and what does the model's range-vs-price label say about that gap?** (Original v1 question.)
2. **Should I buy this stock or just buy the better of SPY/QQQ?** (ABA-125 — the operator's actual decision: opportunity cost against the passive benchmark.)

Vocabulary and bands for the IV / MoS layer are **inherited** from `/stock-model`, not re-invented. The opportunity-cost layer is local to this skill but its convergence assumption is deliberately the model's explicit horizon, not a free parameter.

- **Margin of safety (MoS %)** — `(base_iv / current_price − 1) × 100`. Positive = upside to base IV; negative = price already exceeds base IV. This is the same formula used in `skills/stock-model/SKILL.md` POSITION SIZING block. See it for the canonical definition.
- **Range-vs-price label** — the existing `stages.model.range_vs_price` label written by `/stock-model`: `MARGIN OF SAFETY` / `WITHIN BEAR-BASE` / `WITHIN BASE-BULL` / `PRICE EXCEEDS RANGE`. This skill does **not** define its own bands; it surfaces the upstream label so the portfolio view stays consistent with per-ticker model output. Two additional values exist only for this skill: `NO_MODEL` (no cached model on disk) and `STALE_MODEL` (newest model > 14 days old; surfaced alongside the original `range_vs_price`).

### Benchmark overlay (ABA-125)

- **Horizon** — `horizon_years = 5`. This is the explicit-projection horizon of `/stock-model`'s two-stage DCF on the ESTABLISHED path (5y FCF + Gordon terminal); pre-profit uses the same 5y window for revenue-multiple exit. Using the model's own horizon as the convergence assumption is the deliberate choice — it asks the operator's question on the same timeframe the model is actually projecting on, not a free knob.
- **Implied annualised return** — for each ticker with a non-null `base_iv` and `current_price`, `implied_AR = (base_iv / current_price) ^ (1 / horizon_years) − 1`. The assumption: price converges to base IV over `horizon_years`. This is a deliberate simplification — IV is a *present* discounted value, not a future endpoint, so the implied AR is bounded above by the model's WACC for a stock currently trading at IV. The skill surfaces the number anyway because the operator cares about the comparative ranking against SPY / QQQ, not the absolute precision.
- **Benchmark CAGR** — `SPY` and `QQQ` trailing total-return CAGR over `horizon_years`, fetched once per invocation via `mcp__yf__get_total_return_cagr(ticker, years=5)`. The yfinance auto-adjusted Close (default) folds dividends and splits into the price series, so endpoint-to-endpoint ratio is the total return. Single network dependency for the whole skill.
- **Opportunity-cost verdict** — per ticker, the chat-table `Verdict` column is reframed as `implied_AR` minus the better of the two benchmarks (`max(spy_cagr, qqq_cagr)`):
  - `BEATS INDEX` — implied AR exceeds the better benchmark by **> +200 bps**.
  - `MATCHES INDEX` — within ±200 bps of the better benchmark.
  - `BUY INDEX INSTEAD` — implied AR falls short by **> 200 bps**.
  - `NO_MODEL`, `STALE_MODEL`, or `NO_BENCHMARK` — propagated from upstream gaps (see Override Rules §10).
  The `200 bps` threshold is a v1 default; it filters the noise that comes from using trailing-CAGR-as-forward-proxy on a 5y window. Open to revision after operator usage.
- **"Better of the two"** — `max(spy_cagr, qqq_cagr)`. Using the better benchmark is intentional: the operator's actual alternative is buying whichever passive vehicle has the higher recent total return, not an average. The JSON records both so the operator can see if the choice mattered.
- **Sort order** — descending by `implied_AR` (the operator's actual ranking question is "where is the highest expected return", not "where is the largest IV gap"). `NO_MODEL` and `NO_BENCHMARK` rows sort to the bottom, then alphabetical by ticker. Note this is a v1.1 change from v1.0/v1.1 (which sorted by MoS %); MoS % remains in the table so the original mental model is still visible.

**Why no new MoS thresholds?** A search of the repo found the established `range_vs_price` 4-band convention already used by `/stock-model`'s POSITION SIZING block. Inventing a second set of bands (e.g. ADD/HOLD/TRIM/AVOID at ±25/±10) would fork the vocabulary and silently disagree with per-ticker model output at the margins. v1 uses the existing labels as-is.

**Why trailing — not forward — benchmark CAGR?** Forward expected return for SPY / QQQ is a model output of its own (CAPE-based, factor-based, sell-side strategist consensus). Any choice introduces silent assumptions the operator hasn't been told. Trailing total return is what the index *actually* delivered over the window we're projecting against, sourced directly from yfinance — verifiable, no embedded model. Treat the trailing number as "this is what the index has been doing"; if the operator wants to override, the JSON has the raw inputs.

**Staleness threshold.** v1 default: a model is `STALE_MODEL` if its report file is more than **14 days** older than today. This is a v1 default — the appetite is one week and the staleness number is open to revision based on operator usage. Documented in the output footer and in this skill so future tuning is auditable.

---

## 3. Input Schema

| Input | Source | Data-gap handling |
|---|---|---|
| Covered-ticker universe | `COVERAGE.md` "Currently supported" table | If COVERAGE.md is unreadable, fail loudly — do not fall back to a hardcoded list |
| Latest screen output per ticker | `reports/{TICKER}_*.json` → `stages.screen` (newest by filename date) | Missing → row still emitted; `screen_verdict: null`, `gaps` notes "no screen on file" |
| Latest signal output per ticker | `reports/{TICKER}_*.json` → `stages.signal` (newest by filename date) | Missing → row still emitted; `signal_verdict: null`, `gaps` notes "no signal on file" |
| Latest model output per ticker | `reports/{TICKER}_*.json` → `stages.model` (newest by filename date) | Missing → row still emitted with verdict `NO_MODEL`; `iv_base: null`, `mos_pct: null` |
| Current price per ticker | Freshest non-null price across all stages of all reports for that ticker, with fallback order **signal → screen → model** | None of the three present → `current_price: null`; MoS not computable; verdict `NO_MODEL` (or `STALE_MODEL` if model exists but price doesn't) |
| SPY trailing total-return CAGR | `mcp__yf__get_total_return_cagr("SPY", years=5)` — one call per invocation | yf MCP unreachable or returns an error → benchmark overlay row records `error`, per-ticker `vs_spy_bps` is null, opp-cost verdict falls through to `NO_BENCHMARK`. The IV / MoS / range-vs-price layer still produces output |
| QQQ trailing total-return CAGR | `mcp__yf__get_total_return_cagr("QQQ", years=5)` — one call per invocation | Same as SPY |

**Ticker resolution.**

- The seven canonical tickers (per `COVERAGE.md`): `GOOG`, `META`, `AMZN`, `NVDA`, `ASML`, `NFLX`, `ADYEN.AS`.
- `GOOGL` reports on disk are treated as aliases for `GOOG` (Alphabet share-class; same underlying business) — when scanning `reports/`, look for both `GOOG_*.json` and `GOOGL_*.json` and merge by newest. The output row uses the canonical `GOOG` ticker; the JSON records `alias_used: "GOOGL"` if that was the source.
- Period-suffixed exchange codes are preserved verbatim — `reports/ADYEN.AS_*.json`, not `reports/ADYEN_*.json`.

**"Latest" rule.** Filename pattern is `TICKER_YYYYMMDD.json`. Sort by the date portion descending. Newest file wins per-stage. If a stage is null in the newest file but present in an older file, scan backwards through the ticker's files and take the most recent non-null occurrence of that stage. Record the source filename per stage in the JSON output so the QA agent can audit.

**Price source recording.** The JSON output records `price_source: "signal" | "screen" | "model"` and `price_source_file: "META_20260517.json"` for each ticker, so the operator can see which stage the displayed price came from. Fallback order is signal → screen → model (the model snapshot is taken at model-run time and can lag the freshest signal/screen on the same ticker).

---

## 4. Execution Phases

### GATHER

1. Read `COVERAGE.md` and extract the seven tickers from the "Currently supported" table. The set is fixed and not configurable from the command line — adding a ticker is a `COVERAGE.md` edit (see `COVERAGE.md` → *Contributing new coverage*).
2. List `reports/*.json`. Group files by canonical ticker (resolving the GOOG/GOOGL alias). For each canonical ticker, sort that ticker's files by the `YYYYMMDD` portion of the filename, descending.
3. For each ticker, walk the sorted file list:
   - Initialise `screen = null`, `signal = null`, `model = null`, `price_candidates = []`.
   - For each file from newest to oldest: if `stages.screen` is present and `screen` is still null, capture it (and its filename). Same for `stages.signal` and `stages.model`. If `stages.signal.current_price` or `stages.screen.current_price` or `stages.model.current_price` is present, append it to `price_candidates` tagged with `{stage, file, date}`.
   - Stop walking once `screen`, `signal`, and `model` are all populated **or** the file list is exhausted.
4. Resolve the displayed current price by fallback order: take the first non-null price from a `signal` candidate; if none, the first non-null from a `screen` candidate; if none, the first non-null from a `model` candidate. Record `price_source` and `price_source_file`.
5. Fetch the benchmark overlay: call `mcp__yf__get_total_return_cagr("SPY", years=5)` and `mcp__yf__get_total_return_cagr("QQQ", years=5)`. Each call returns `{cagr, start_date, end_date, start_close, end_close, years_actual, source}` — store both. On either call failing (MCP unreachable, ticker error, network error), record `{ticker, error: "<reason>"}` for that benchmark, leave the other intact, and proceed; per-ticker opp-cost columns degrade to `NO_BENCHMARK` (see THRESHOLD / Override Rules).

**Note on price-on-file.** Not every stage's JSON guarantees a `current_price` field. `stages.model.current_price` is canonical (DESIGN.md). `stages.signal` and `stages.screen` may carry a price implicitly via ratios but do not always serialise an explicit `current_price`. If the freshest stage with an explicit price is older than the newest stage on file, that's acceptable for v1 — the price is what the model was scored against at the time it ran. Surface the price's date alongside it so the operator can judge staleness directly. (Follow-up — fetching a live price from yfinance to refresh the price column without re-running the model — is out of scope for v1.)

### VALIDATE

- Confirm the covered-ticker list has exactly seven entries. If `COVERAGE.md` parsing yields a different count, halt and surface the discrepancy — do not guess.
- For each ticker, if `stages.model.intrinsic_value_range.base` is present but null/zero, treat it as missing and set verdict to `NO_MODEL` with a gap note ("model present but base IV null").
- If `current_price` is null but a model exists, MoS is not computable. Surface as `mos_pct: null` and verdict `STALE_MODEL` (or `NO_MODEL` if the model itself is missing).

### COMPUTE

**Per-ticker IV / MoS layer.** For each ticker:

1. **Base IV** = `stages.model.intrinsic_value_range.base` (from the latest model report on file).
2. **MoS %** = `(base_iv / current_price − 1) × 100`. Round to one decimal. Null if either input is null.
3. **Range-vs-price label** = `stages.model.range_vs_price` from the same model file. If absent (older model report without the field), fall back to deriving it from the bear / base / bull values vs `current_price` using the exact rules from `skills/stock-model/SKILL.md` THRESHOLD section:
   - `current_price < bear_iv` → `MARGIN OF SAFETY`
   - `bear_iv ≤ current_price < base_iv` → `WITHIN BEAR-BASE`
   - `base_iv ≤ current_price ≤ bull_iv` → `WITHIN BASE-BULL`
   - `current_price > bull_iv` → `PRICE EXCEEDS RANGE`
4. **Last updated** = the filename date of the model report (`YYYY-MM-DD`).
5. **Days stale** = today − last updated.
6. **Staleness flag** = days stale > 14 → `STALE_MODEL` annotation applied alongside the `range_vs_price` value.

**Benchmark overlay layer (ABA-125).** Once per invocation, then per ticker:

7. **Implied annualised return** (per ticker, where both `base_iv` and `current_price` are non-null):
   - `implied_AR = (base_iv / current_price) ^ (1 / horizon_years) − 1` with `horizon_years = 5`.
   - Round display to one decimal place (e.g. `+12.3 %`); JSON stores three decimals of the raw rate.
   - Null if either `base_iv` or `current_price` is null.
8. **Excess return vs each benchmark** (per ticker):
   - `vs_spy_bps = round((implied_AR − spy_cagr) × 10_000)` — integer basis points.
   - `vs_qqq_bps = round((implied_AR − qqq_cagr) × 10_000)`.
   - Null on either side if `implied_AR` is null OR the corresponding benchmark CAGR is unavailable.
9. **Better benchmark and excess vs better** (per ticker):
   - `better_benchmark = "SPY"` if `spy_cagr ≥ qqq_cagr`, else `"QQQ"`. If only one is available, that one is the better. If neither is available, `better_benchmark = null`.
   - `vs_better_bps = round((implied_AR − better_benchmark_cagr) × 10_000)`. Null if `implied_AR` is null or no benchmark is available.

### THRESHOLD

Two verdict layers are computed per ticker. The chat-table `Verdict` column shows the **opportunity-cost verdict** (item 2 below) because that's the operator's actual decision. The IV / range-vs-price label remains in the JSON (`range_vs_price` field) so the per-ticker model context is not lost.

**1. Range-vs-price label.** The upstream `range_vs_price` label — no new threshold logic. Two derived values are applied here only:

- `NO_MODEL` — no model report exists for this ticker, or model is present but `base IV` is null.
- `STALE_MODEL` — model exists but the report date is > 14 days old. Surfaced as a suffix to the underlying label, e.g. `WITHIN BEAR-BASE (STALE)`. Days-stale shown numerically in the JSON.

**2. Opportunity-cost verdict (ABA-125 — chat-table `Verdict` column).** Derived from `vs_better_bps` per the bands below:

| `vs_better_bps` (implied AR − better benchmark CAGR, basis points) | Opp-cost verdict |
|---|---|
| `> +200` | `BEATS INDEX` |
| `−200 ≤ vs_better_bps ≤ +200` | `MATCHES INDEX` |
| `< −200` | `BUY INDEX INSTEAD` |
| `null` because `implied_AR` is null | `NO_MODEL` or `STALE_MODEL` (whichever applies from layer 1) |
| `null` because both benchmark CAGRs failed to fetch | `NO_BENCHMARK` (footer surfaces the underlying yf MCP failure) |

The `200 bps` threshold is a v1 default that filters noise when comparing a 5y implied AR (a forward assumption) against a 5y trailing total-return CAGR (a backward number). Open to revision after operator usage. Surface the raw `vs_better_bps` value alongside the band so the operator can override the verdict on judgement.

### OUTPUT

Two deliverables per invocation:

**(a) Chat output.** A markdown table sorted by `implied_AR` descending (`NO_MODEL`, `STALE_MODEL`, and `NO_BENCHMARK` rows last, alphabetical among themselves), plus a footer block. Columns:

| # | Ticker | Current price | Base IV | MoS % | Implied AR (5y) | vs SPY (5y) | vs QQQ (5y) | Verdict | Last updated |

Per-column conventions:

- `Implied AR (5y)` — implied annualised return assuming price converges to base IV over 5y. Display as `+12.3 %`, `−4.1 %`, or `—` when null. (5y window is also surfaced in the column header.)
- `vs SPY (5y)` / `vs QQQ (5y)` — implied AR minus the benchmark's 5y trailing total-return CAGR, in basis points. Display as `+520 bps`, `−180 bps`, or `—`. The 5y window is also surfaced in the column header.
- `Verdict` — the opportunity-cost verdict from THRESHOLD §2 (`BEATS INDEX` / `MATCHES INDEX` / `BUY INDEX INSTEAD` / `NO_MODEL` / `STALE_MODEL` / `NO_BENCHMARK`).

Directly above the table, print a one-line benchmark banner like:

```
Benchmark overlay (5y trailing total return): SPY +14.2 % CAGR · QQQ +18.3 % CAGR · better = QQQ
```

If a benchmark fetch failed, replace its number with `—` and a short reason in the footer.

The footer block contains:
- Today's date.
- Source `COVERAGE.md` version note (the seven tickers as discovered).
- Per-ticker `price_source` map.
- Any gaps (e.g. "AMZN: no model on file — run `/stock-model AMZN`").
- The v1 verdict bands disclaimer (see below).
- The benchmark-overlay v1 caveats (horizon assumption, trailing-not-forward CAGR, ±200 bps band).

**(b) JSON snapshot** at `reports/PORTFOLIO_YYYYMMDD.json`, schema below. Overwrite any existing file with the same date stamp — one snapshot per day is the v1 contract.

---

## 5. Output Schema

```json
{
  "type": "portfolio_snapshot",
  "date": "2026-05-17",
  "universe": ["GOOG", "META", "AMZN", "NVDA", "ASML", "NFLX", "ADYEN.AS"],
  "tickers": [
    {
      "ticker": "META",
      "company": "Meta Platforms, Inc.",
      "current_price": 614.23,
      "price_source": "model",
      "price_source_file": "META_20260517.json",
      "price_as_of": "2026-05-17",
      "iv_base": 1154.78,
      "iv_bear": 444.36,
      "iv_bull": 2439.51,
      "mos_pct": 88.0,
      "range_vs_price": "WITHIN BEAR-BASE",
      "implied_annualised_return": 0.135,
      "vs_spy_bps": -70,
      "vs_qqq_bps": -480,
      "vs_better_bps": -480,
      "better_benchmark": "QQQ",
      "verdict": "BUY INDEX INSTEAD",
      "model_date": "2026-05-17",
      "days_stale": 0,
      "stale": false,
      "alias_used": null,
      "sources": {
        "screen_file": null,
        "signal_file": "META_20260517.json",
        "model_file": "META_20260517.json"
      },
      "gaps": []
    },
    {
      "ticker": "AMZN",
      "company": "Amazon.com, Inc.",
      "current_price": null,
      "price_source": null,
      "price_source_file": null,
      "price_as_of": null,
      "iv_base": null,
      "iv_bear": null,
      "iv_bull": null,
      "mos_pct": null,
      "range_vs_price": null,
      "implied_annualised_return": null,
      "vs_spy_bps": null,
      "vs_qqq_bps": null,
      "vs_better_bps": null,
      "better_benchmark": "QQQ",
      "verdict": "NO_MODEL",
      "model_date": null,
      "days_stale": null,
      "stale": null,
      "alias_used": null,
      "sources": {
        "screen_file": null,
        "signal_file": "AMZN_20260517.json",
        "model_file": null
      },
      "gaps": ["no model report on file — run /stock-model AMZN"]
    }
  ],
  "thresholds": {
    "stale_days": 14,
    "mos_formula": "(iv_base / current_price - 1) * 100",
    "range_vs_price_source": "stages.model.range_vs_price (inherited from /stock-model)",
    "opp_cost_bps_threshold": 200,
    "implied_ar_formula": "(iv_base / current_price) ^ (1 / horizon_years) - 1",
    "v1_notes": "Range-vs-price labels and MoS formula inherited unchanged from /stock-model. Opportunity-cost verdict bands (±200 bps) are this skill's defaults, open to revision. Implied-AR assumes price converges to base IV over horizon_years (the model's explicit-projection horizon)."
  },
  "benchmark_overlay": {
    "horizon_years": 5,
    "benchmarks": [
      {
        "ticker": "SPY",
        "trailing_cagr": 0.142,
        "start_date": "2021-05-17",
        "end_date": "2026-05-17",
        "start_close": 412.18,
        "end_close": 807.55,
        "years_actual": 5.0,
        "source": "yfinance"
      },
      {
        "ticker": "QQQ",
        "trailing_cagr": 0.183,
        "start_date": "2021-05-17",
        "end_date": "2026-05-17",
        "start_close": 335.51,
        "end_close": 779.04,
        "years_actual": 5.0,
        "source": "yfinance"
      }
    ],
    "better_benchmark": "QQQ",
    "better_benchmark_cagr": 0.183,
    "computed_at": "2026-05-17"
  },
  "meta": {
    "skill": "stock-portfolio",
    "skill_version": "v1.1",
    "coverage_source": "COVERAGE.md",
    "generated_at": "2026-05-17"
  }
}
```

**Schema notes:**

- `verdict` is the user-facing opportunity-cost label (from THRESHOLD §2). `range_vs_price` carries the raw upstream IV / price-band label even when the row is stale, so the operator can see both layers.
- `implied_annualised_return` is the raw rate (e.g. `0.135` = 13.5 % CAGR), three decimals. The chat table renders it as `+13.5 %`.
- `vs_spy_bps` / `vs_qqq_bps` / `vs_better_bps` are integer basis-point excess returns (e.g. `-480` = stock implied AR is 480 bps below QQQ). Null when implied AR or the corresponding benchmark CAGR is unavailable.
- `better_benchmark` is `"SPY"` or `"QQQ"` (whichever has the higher trailing CAGR). Populated even when the per-ticker implied AR is null, so the operator can see which index the universe is being measured against.
- `sources` records which `reports/*.json` file each stage was read from. This is the audit trail.
- `benchmark_overlay.benchmarks[].cagr` is the raw rate (e.g. `0.142` = 14.2 %), three decimals. The chat banner renders it as `+14.2 %`.
- On a benchmark fetch failure, the corresponding `benchmarks[]` row carries `{"ticker": "<sym>", "error": "<short reason>"}` in place of the price fields; `better_benchmark` resolves to the surviving benchmark, or `null` if both failed.

---

## 6. Data Fetching Behaviour

**Per-ticker rows are cache-only.** The IV / MoS / range-vs-price layer reads only from the local `reports/` directory — no network calls, no live yfinance fetches for the per-ticker rows. If `reports/` is empty or unreadable, the skill emits an empty snapshot with all seven tickers flagged `NO_MODEL` and a top-level gap note recommending the operator runs `/stock-screen` + `/stock-signal` + `/stock-model` across the universe.

**Benchmark overlay is the only network dependency.** Two `mcp__yf__get_total_return_cagr` calls per invocation — one for SPY, one for QQQ — return the 5y trailing total-return CAGRs. These are the only network calls this skill makes. If the `yf` MCP server is not connected or both calls fail, the per-ticker rows still render; the chat-table verdict column degrades to `NO_BENCHMARK` and the footer surfaces the underlying failure.

**Why per-ticker is cache-only.** The point of the portfolio view is to make the existing per-ticker outputs comparable in one place — not to silently rerun expensive computations the operator may have specific reasons to defer. v1 surfaces gaps; the operator chooses what to refresh.

**Why benchmarks are fetched live.** Trailing 5y CAGR for SPY / QQQ is cheap (one yfinance call each, sub-second), not playbook-tunable, and a stale cached value would silently mislead the opportunity-cost verdict. A live fetch is the simpler and more honest path than introducing a benchmark-cache file.

---

## 7. Invocation Patterns

```
/stock-portfolio
```

That's the only supported form. No ticker arguments — universe is fixed by `COVERAGE.md`. No `--refresh`, no `--rerun-model`, no `--ticker-filter`, no `--benchmark` flag. The SPY/QQQ overlay is always on (ABA-125); there is no operator-visible flag to disable it. If the `yf` MCP is unavailable the overlay degrades gracefully (`NO_BENCHMARK` verdicts) — the operator does not need to opt out.

---

## 8. Dependencies

- `COVERAGE.md` for the canonical ticker list.
- `reports/*.json` files written by `/stock-screen`, `/stock-signal`, `/stock-model`.
- `mcp__yf__get_total_return_cagr` (added in ABA-125) for the SPY/QQQ benchmark overlay. The skill degrades gracefully if the MCP is unavailable — per-ticker rows still render with `NO_BENCHMARK` in the verdict column.
- No new third-party libraries required.

---

## 9. Tech-Specific Rules

None unique to this skill. All upstream conventions (SBC stripping, AI layer classification, base IV definition) are inherited via the cached reports — this skill is a pure aggregator.

---

## 10. Override Rules

- **IF** `COVERAGE.md` listed tickers ≠ 7 → halt, surface the discrepancy, do not produce an output.
- **IF** all seven tickers have `NO_MODEL` → still produce the snapshot; flag the universe-wide gap; suggest the operator run `/stock-model` across the seven before relying on the portfolio view.
- **IF** the GOOG/GOOGL alias resolves to two ambiguous sources (a `GOOG_*.json` and a `GOOGL_*.json` with the same date) → prefer the GOOG file (matches the canonical ticker in `COVERAGE.md`); record both in `sources` for audit; surface the duplication in `gaps`.
- **IF** a model file has `intrinsic_value_range.base` present but `current_price` null → verdict is `STALE_MODEL` (model on file but no price to score against), not `NO_MODEL`. Gap note: "model on file but no current_price across any stage".
- **IF** the `yf` MCP is unavailable or both SPY and QQQ `get_total_return_cagr` calls fail → set `benchmark_overlay.benchmarks` rows to `{"ticker": "<sym>", "error": "<reason>"}`, set `better_benchmark` to `null`, set per-ticker `vs_spy_bps` / `vs_qqq_bps` / `vs_better_bps` to null, set the per-ticker opp-cost `verdict` to `NO_BENCHMARK` (only when the upstream IV layer would otherwise have produced a verdict — `NO_MODEL` / `STALE_MODEL` rows keep their existing labels). Surface "benchmark fetch failed — opportunity-cost layer unavailable" in the footer.
- **IF** one of SPY / QQQ fetches succeeds and the other fails → `better_benchmark` is the surviving one; per-ticker `vs_<failed>_bps` is null, `vs_better_bps` is computed against the survivor, opp-cost verdict computes normally. Surface the partial failure in the footer.

---

## 11. Common Rationalisations (pre-rebut)

| Rationalisation | Counter |
|---|---|
| "I'll just call yfinance to fetch a fresh **per-ticker** price — the price column will be more useful." | Out of scope. The per-ticker rows stay cache-only. Introducing a per-ticker fetch path changes the failure modes (rate limits, MCP not connected, stale fallbacks). Note the freshest cached price's date instead. The SPY/QQQ benchmark overlay is the only exception — it's two calls per invocation, not seven, and is justified by the freshness requirement on the comparator (see §2 / §6). |
| "While I'm computing the benchmark overlay, I'll use SPY/QQQ's `forward` expected return instead of trailing CAGR — that's more theoretically right." | Forbidden. Forward expected return for an index is itself a model output (CAPE-based, factor-based, strategist consensus); choosing one embeds a silent assumption. Trailing total return is what the index *actually* delivered over the window we're projecting against, sourced directly from yfinance and verifiable. The JSON exposes the raw inputs so the operator can override on judgement. |
| "The implied AR formula assumes price converges to base IV in 5 years — that's strong. Let me skip the column rather than mislead." | Forbidden. The simplification is documented (§2). The point of the column is the *comparative ranking* against SPY/QQQ, not absolute precision. Surface the number plus the caveats in the footer — silently dropping the column defeats the whole skill. |
| "Let me invent a richer opportunity-cost label like STRONG BEAT / WEAK BEAT / NEAR-MATCH / UNDERPERFORM." | Forbidden. Three bands (`BEATS INDEX` / `MATCHES INDEX` / `BUY INDEX INSTEAD`) is the minimum that gives the operator a decision; finer gradations are noise on a 5y trailing-vs-implied comparison. The raw `vs_better_bps` is in the JSON for the operator to override. |
| "Let me invent ADD / HOLD / TRIM / AVOID bands — they're easier to read than 'WITHIN BEAR-BASE'." | Forbidden. The `/stock-model` skill already owns the verdict vocabulary. A second set of labels in this skill silently disagrees at the margins and forks the operator's mental model. Reuse the upstream labels; if a more compact display is needed, it's a UI concern, not a skill-output concern. |
| "AMZN has no model — I'll just drop it from the table to keep things clean." | Forbidden. Silently dropping tickers hides the gap that the operator needs to see. Every covered ticker gets a row; missing inputs are flagged in the verdict column and the gaps list. |
| "The newest report for GOOG is GOOGL — I'll just show GOOGL as the ticker." | The output uses the canonical `COVERAGE.md` ticker. Record `alias_used: "GOOGL"` in the JSON for audit, but display `GOOG` in the table — the canonical name is what the operator sees in `COVERAGE.md` and in playbooks. |
| "I'll re-run `/stock-model` for the stale tickers as part of this skill — it's only a few calls." | Forbidden. v1 scope says read-only. Re-running model is expensive (manual inputs, WACC confirmations) and would defeat the "one invocation" contract. The skill surfaces staleness; the operator decides what to refresh. |
| "There's no `range_vs_price` in the older META report — I'll just leave the verdict blank." | Forbidden. The fallback in COMPUTE step 3 derives the label from bear / base / bull / current_price using the documented `/stock-model` THRESHOLD rules. Blank verdict is silent failure. |
| "Today is 2026-05-17 and the META model is from 2026-05-17 — `days_stale` is 0 and I don't need a date column." | The table always shows `Last updated` per ticker, even at zero days. Half the value of this skill is making freshness comparable across the seven; suppressing the column at zero defeats that. |

---

## 12. Self-check (acceptance criteria)

A `/stock-portfolio` run is correct when:

1. The output table contains exactly seven rows — one per ticker in `COVERAGE.md` — with no silent drops.
2. Each row carries: ticker, current price (or `—` if null), base IV (or `—` if null), MoS % (or `—` if null), Implied AR (5y) (or `—`), vs SPY (5y) (or `—`), vs QQQ (5y) (or `—`), Verdict, last updated date.
3. Rows are sorted by implied annualised return descending; `NO_MODEL`, `STALE_MODEL`, and `NO_BENCHMARK`-only rows sort to the bottom alphabetically among themselves.
4. The JSON snapshot at `reports/PORTFOLIO_YYYYMMDD.json` is valid JSON, schema-conformant, and overwrites the same-day file if present.
5. Every non-null price has `price_source` recorded in the JSON (`signal` | `screen` | `model`) with the source filename.
6. `range_vs_price` (JSON) is drawn from `{MARGIN OF SAFETY, WITHIN BEAR-BASE, WITHIN BASE-BULL, PRICE EXCEEDS RANGE, null}` only — no new bands. The user-facing `verdict` is drawn from `{BEATS INDEX, MATCHES INDEX, BUY INDEX INSTEAD, NO_MODEL, STALE_MODEL, NO_BENCHMARK}`.
7. The footer carries the v1 disclaimer about the range-vs-price-source provenance, the staleness threshold, and the benchmark-overlay caveats (horizon, trailing-not-forward CAGR, ±200 bps band).
8. `benchmark_overlay` is populated with `{horizon_years, benchmarks[], better_benchmark, better_benchmark_cagr, computed_at}`; SPY and QQQ rows each carry trailing CAGR + the dates the CAGR was measured between, or an `error` field if the fetch failed.
9. Each ticker row carries `implied_annualised_return`, `vs_spy_bps`, `vs_qqq_bps`, `vs_better_bps`, and `better_benchmark` (the latter populated even when the per-ticker fields are null, so the operator can see the universe-level comparison frame).
10. The skill made exactly two yf MCP calls (SPY + QQQ) and no other network calls; the per-ticker rows are still cache-only.

---

## 13. Output Footer (template)

```
Notes
- The range-vs-price label and MoS formula are inherited from /stock-model —
  no new IV thresholds were introduced in this skill. See
  skills/stock-model/SKILL.md POSITION SIZING for the source.
- A model is flagged STALE if its report file is more than 14 days old
  (v1 default — open to revision based on operator usage).
- Current price per ticker is taken from the freshest report stage in
  fallback order: signal → screen → model. The per-ticker price_source
  is recorded in reports/PORTFOLIO_YYYYMMDD.json.
- Benchmark overlay (ABA-125): Implied annualised return assumes price
  converges to /stock-model's base IV over the model's explicit 5-year
  horizon. SPY and QQQ CAGRs are trailing 5-year total returns from
  yfinance (auto-adjusted close folds in dividends + splits) — not a
  forward expected-return model. The opportunity-cost verdict bands are
  ±200 bps around the better of SPY/QQQ; raw vs_better_bps is in the
  JSON so the operator can override on judgement.
- The per-ticker rows are read-only — this skill does not re-run
  /stock-screen, /stock-signal, or /stock-model. Gaps in the table mean
  the operator should run the upstream skill for that ticker. The only
  network calls are two yfinance fetches (SPY + QQQ) for the benchmark
  overlay.
```
