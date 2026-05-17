---
name: stock-portfolio
description: Portfolio-level snapshot across the seven covered tickers. Invoked as `/stock-portfolio`. Reads the latest cached screen / signal / model outputs from `reports/` for each ticker in `COVERAGE.md` and emits a ranked table (ticker / current price / our IV / margin of safety / verdict / last updated) so the operator can answer "where should I add" in one invocation. Does NOT re-run the model. Use whenever the user asks a portfolio-level question — "which of the seven is most undervalued right now", "where should I add", "what's the gap across the portfolio", "rank the covered tickers" — even if they don't say "portfolio".
---

# Portfolio — Cross-Ticker Snapshot

**Command:** `/stock-portfolio`
**Purpose:** Single-invocation portfolio view across all seven covered tickers. Reads the latest cached `/stock-screen`, `/stock-signal`, and `/stock-model` outputs from `reports/`, computes margin-of-safety vs the freshest available price per ticker, and prints a verdict-ranked table plus a JSON snapshot at `reports/PORTFOLIO_YYYYMMDD.json`.

This skill is a **read-only aggregator**. It never re-runs `/stock-screen`, `/stock-signal`, or `/stock-model`. If a ticker is missing fresh inputs, the row still appears and the gap is flagged — the operator decides whether to re-run the upstream skill.

---

## 1. Identity

- **Skill name:** stock-portfolio
- **Command:** `/stock-portfolio` (no ticker arguments — the universe is fixed by `COVERAGE.md`)
- **Purpose:** Produce a portfolio-level ranked snapshot across the seven covered tickers using only cached reports.

---

## 2. Methodology

The portfolio view answers one question: **across the seven covered names, where is the largest gap between our base-case intrinsic value and the market price right now, and what does the model's range-vs-price label say about that gap?**

Vocabulary and bands are **inherited** from `/stock-model`, not re-invented:

- **Margin of safety (MoS %)** — `(base_iv / current_price − 1) × 100`. Positive = upside to base IV; negative = price already exceeds base IV. This is the same formula used in `skills/stock-model/SKILL.md` POSITION SIZING block. See it for the canonical definition.
- **Verdict** — the existing `stages.model.range_vs_price` label written by `/stock-model`: `MARGIN OF SAFETY` / `WITHIN BEAR-BASE` / `WITHIN BASE-BULL` / `PRICE EXCEEDS RANGE`. This skill does **not** define its own verdict bands; it surfaces the upstream label so the portfolio view stays consistent with per-ticker model output. Two additional labels exist only for this skill: `NO_MODEL` (no cached model on disk) and `STALE_MODEL` (newest model > 14 days old; surfaced alongside the original `range_vs_price` so the operator can see both the label and the staleness).
- **Sort order** — descending by MoS %. `NO_MODEL` rows sort to the bottom. Within `NO_MODEL`, sort alphabetically by ticker.

**Why no new MoS thresholds?** A search of the repo found the established `range_vs_price` 4-band convention already used by `/stock-model`'s POSITION SIZING block. Inventing a second set of bands (e.g. ADD/HOLD/TRIM/AVOID at ±25/±10) would fork the vocabulary and silently disagree with per-ticker model output at the margins. v1 uses the existing labels as-is.

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

**Note on price-on-file.** Not every stage's JSON guarantees a `current_price` field. `stages.model.current_price` is canonical (DESIGN.md). `stages.signal` and `stages.screen` may carry a price implicitly via ratios but do not always serialise an explicit `current_price`. If the freshest stage with an explicit price is older than the newest stage on file, that's acceptable for v1 — the price is what the model was scored against at the time it ran. Surface the price's date alongside it so the operator can judge staleness directly. (Follow-up — fetching a live price from yfinance to refresh the price column without re-running the model — is out of scope for v1.)

### VALIDATE

- Confirm the covered-ticker list has exactly seven entries. If `COVERAGE.md` parsing yields a different count, halt and surface the discrepancy — do not guess.
- For each ticker, if `stages.model.intrinsic_value_range.base` is present but null/zero, treat it as missing and set verdict to `NO_MODEL` with a gap note ("model present but base IV null").
- If `current_price` is null but a model exists, MoS is not computable. Surface as `mos_pct: null` and verdict `STALE_MODEL` (or `NO_MODEL` if the model itself is missing).

### COMPUTE

For each ticker:

1. **Base IV** = `stages.model.intrinsic_value_range.base` (from the latest model report on file).
2. **MoS %** = `(base_iv / current_price − 1) × 100`. Round to one decimal. Null if either input is null.
3. **Verdict source** = `stages.model.range_vs_price` from the same model file. If absent (older model report without the field), fall back to deriving it from the bear / base / bull values vs `current_price` using the exact rules from `skills/stock-model/SKILL.md` THRESHOLD section:
   - `current_price < bear_iv` → `MARGIN OF SAFETY`
   - `bear_iv ≤ current_price < base_iv` → `WITHIN BEAR–BASE`
   - `base_iv ≤ current_price ≤ bull_iv` → `WITHIN BASE–BULL`
   - `current_price > bull_iv` → `PRICE EXCEEDS RANGE`
4. **Last updated** = the filename date of the model report (`YYYY-MM-DD`).
5. **Days stale** = today − last updated.
6. **Staleness flag** = days stale > 14 → `STALE_MODEL` annotation applied alongside the `range_vs_price` verdict.

### THRESHOLD

The verdict column is the upstream `range_vs_price` label — no new threshold logic. Two derived labels are applied here only:

- `NO_MODEL` — no model report exists for this ticker, or model is present but `base IV` is null.
- `STALE_MODEL` — model exists but the report date is > 14 days old. Surfaced as an annotation suffixed to the underlying verdict, e.g. `WITHIN BEAR–BASE (STALE)`. Days-stale shown numerically in the JSON.

### OUTPUT

Two deliverables per invocation:

**(a) Chat output.** A markdown table sorted by MoS % descending (NO_MODEL rows last, alphabetical among themselves), plus a footer block. Columns:

| # | Ticker | Current price | Base IV | MoS % | Verdict | Last updated |

The footer block contains:
- Today's date.
- Source `COVERAGE.md` version note (the seven tickers as discovered).
- Per-ticker `price_source` map.
- Any gaps (e.g. "AMZN: no model on file — run `/stock-model AMZN`").
- The v1 verdict bands disclaimer (see below).

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
      "verdict": "WITHIN BEAR-BASE",
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
    "verdict_source": "stages.model.range_vs_price (inherited from /stock-model)",
    "v1_notes": "Verdict labels and MoS formula inherited unchanged from /stock-model. No new thresholds introduced in this skill. Staleness day-count is a v1 default open to revision."
  },
  "benchmark_overlay": null,
  "benchmark_overlay_note": "SPY/QQQ comparator deferred to ABA-125. Seam reserved; not implemented in v1.",
  "meta": {
    "skill": "stock-portfolio",
    "skill_version": "v1",
    "coverage_source": "COVERAGE.md",
    "generated_at": "2026-05-17"
  }
}
```

**Schema notes:**

- `verdict` carries the user-facing label (which may be `STALE_MODEL` or `NO_MODEL`); `range_vs_price` carries the raw upstream label even when the row is stale, so the operator can see both.
- `sources` records which `reports/*.json` file each stage was read from. This is the audit trail.
- `benchmark_overlay` is reserved for ABA-125 (SPY/QQQ comparator). It stays `null` in v1.

---

## 6. Data Fetching Behaviour

**This skill does not call any MCP server.** It reads only from the local `reports/` directory. The performance contract is "fast" — no network calls, no live yfinance fetches. If `reports/` is empty or unreadable, the skill emits an empty snapshot with all seven tickers flagged `NO_MODEL` and a top-level gap note recommending the operator runs `/stock-screen` + `/stock-signal` + `/stock-model` across the universe.

**Why read-only.** The point of the portfolio view is to make the existing per-ticker outputs comparable in one place — not to silently rerun expensive computations the operator may have specific reasons to defer. v1 surfaces gaps; the operator chooses what to refresh.

---

## 7. Invocation Patterns

```
/stock-portfolio
```

That's the only supported form in v1. No ticker arguments — universe is fixed by `COVERAGE.md`. No `--refresh`, no `--rerun-model`, no `--ticker-filter`. Adding flags is a follow-up issue, not a v1 scope expansion.

**Reserved for ABA-125 (do not implement in v1):**

```
/stock-portfolio --benchmark SPY,QQQ
```

The `--benchmark` flag is the seam for the SPY/QQQ comparator. The `benchmark_overlay` field in the JSON output is the slot it will fill. v1 leaves both reserved and unused.

---

## 8. Dependencies

- `COVERAGE.md` for the canonical ticker list.
- `reports/*.json` files written by `/stock-screen`, `/stock-signal`, `/stock-model`.
- No MCP servers required.
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

---

## 11. Common Rationalisations (pre-rebut)

| Rationalisation | Counter |
|---|---|
| "I'll just call yfinance to fetch a fresh price — the price column will be more useful." | Out of scope for v1. The whole point is read-only aggregation; introducing a fetch path changes the failure modes (rate limits, MCP not connected, stale fallbacks). Note the freshest cached price's date instead. If live-price refresh proves valuable, that's a follow-up issue with its own appetite. |
| "Let me invent ADD / HOLD / TRIM / AVOID bands — they're easier to read than 'WITHIN BEAR–BASE'." | Forbidden. The `/stock-model` skill already owns the verdict vocabulary. A second set of labels in this skill silently disagrees at the margins and forks the operator's mental model. Reuse the upstream labels; if a more compact display is needed, it's a UI concern, not a skill-output concern. |
| "AMZN has no model — I'll just drop it from the table to keep things clean." | Forbidden. Silently dropping tickers hides the gap that the operator needs to see. Every covered ticker gets a row; missing inputs are flagged in the verdict column and the gaps list. |
| "The newest report for GOOG is GOOGL — I'll just show GOOGL as the ticker." | The output uses the canonical `COVERAGE.md` ticker. Record `alias_used: "GOOGL"` in the JSON for audit, but display `GOOG` in the table — the canonical name is what the operator sees in `COVERAGE.md` and in playbooks. |
| "I'll re-run `/stock-model` for the stale tickers as part of this skill — it's only a few calls." | Forbidden. v1 scope says read-only. Re-running model is expensive (manual inputs, WACC confirmations) and would defeat the "one invocation" contract. The skill surfaces staleness; the operator decides what to refresh. |
| "There's no `range_vs_price` in the older META report — I'll just leave the verdict blank." | Forbidden. The fallback in COMPUTE step 3 derives the label from bear / base / bull / current_price using the documented `/stock-model` THRESHOLD rules. Blank verdict is silent failure. |
| "Today is 2026-05-17 and the META model is from 2026-05-17 — `days_stale` is 0 and I don't need a date column." | The table always shows `Last updated` per ticker, even at zero days. Half the value of this skill is making freshness comparable across the seven; suppressing the column at zero defeats that. |

---

## 12. Self-check (acceptance criteria)

A `/stock-portfolio` run is correct when:

1. The output table contains exactly seven rows — one per ticker in `COVERAGE.md` — with no silent drops.
2. Each row carries: ticker, current price (or `—` if null), base IV (or `—` if null), MoS % (or `—` if null), verdict, last updated date.
3. Rows are sorted by MoS % descending; `NO_MODEL` rows sort to the bottom alphabetically.
4. The JSON snapshot at `reports/PORTFOLIO_YYYYMMDD.json` is valid JSON, schema-conformant, and overwrites the same-day file if present.
5. Every non-null price has `price_source` recorded in the JSON (`signal` | `screen` | `model`) with the source filename.
6. Verdict labels are drawn from `{MARGIN OF SAFETY, WITHIN BEAR–BASE, WITHIN BASE–BULL, PRICE EXCEEDS RANGE, NO_MODEL, STALE_MODEL}` only. No new bands.
7. The footer carries the v1 disclaimer about the verdict-source provenance and the staleness threshold.
8. `benchmark_overlay` is `null` and the seam note for ABA-125 is present.
9. The skill made no MCP calls and no network calls.

---

## 13. Output Footer (template)

```
Notes
- Verdict labels and the MoS formula are inherited from /stock-model — no new
  thresholds were introduced in this skill. See skills/stock-model/SKILL.md
  POSITION SIZING for the source.
- A model is flagged STALE if its report file is more than 14 days old
  (v1 default — open to revision based on operator usage).
- Current price per ticker is taken from the freshest report stage in
  fallback order: signal → screen → model. The per-ticker price_source
  is recorded in reports/PORTFOLIO_YYYYMMDD.json.
- Benchmark overlay (SPY/QQQ) is reserved for ABA-125 and is not in v1.
- This skill is read-only — it does not re-run /stock-screen, /stock-signal,
  or /stock-model. Gaps in the table mean the operator should run the
  upstream skill for that ticker.
```
