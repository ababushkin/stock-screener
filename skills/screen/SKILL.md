---
name: screen
description: Fast go/no-go valuation screen for tech stocks. Invoked as `/screen TICKER` or `/screen TICKER1, TICKER2`. Fetches ratios from the yfinance MCP, classifies profit stage, applies threshold rules, and writes a structured JSON report to reports/. Use whenever asked to screen a stock, evaluate whether a ticker is worth deeper analysis, or produce a reports/ JSON for the UI. Also use when the user mentions a ticker and asks if it's cheap, overvalued, worth looking at, or whether to buy or investigate it — even if they don't say "screen."
---

# Screen — Fast Valuation Screen

**Command:** `/screen TICKER [, TICKER2 ...]`
**Purpose:** Fast go/no-go screen. Classifies a tech stock as PASS / WATCH / SKIP using valuation ratios and financial quality signals from the yfinance MCP. Writes output to `reports/TICKER_YYYYMMDD.json`.

---

## Execution Phases

### GATHER

1. Parse the ticker from the command argument. Uppercase it (e.g. `nvda` → `NVDA`). If multiple tickers are provided (comma-separated), collect the full list before processing — you need all tickers upfront for Magic Formula ranking.
2. For **each ticker**, call two yfinance MCP tools:

   **a. Ratios** — `mcp__yf__get_ratios`:
   - Input: `{ "ticker": "META" }`
   - Returns: `pe_ratio`, `ps_ratio`, `ev_ebitda`, `pfcf`, `ev_revenue`, `enterprise_value`, `market_cap`, `period`, `date`

   **b. Financials** (ESTABLISHED tickers only — skip for EMERGING) — `mcp__yf__get_financials`:
   - Input: `{ "ticker": "META" }`
   - Returns multi-year income statement, balance sheet, and cash flow statement. You need at least 2 years of annual data for YoY Piotroski signals.

3. If either tool call fails:
   - **YFNoDataError**: yfinance returned an empty payload — the ticker may be delisted, mistyped, or Yahoo's endpoint changed. Report the failure for this ticker.
   - **Other failures (network, server not connected)**: report the failure for this ticker.
   - In all cases: do not write a partial report, and continue processing any remaining tickers in the list.

### VALIDATE

Confirm ratios were retrieved. At minimum, `ps_ratio` must be non-null and greater than 0 for the screen to proceed — P/S is the one ratio available for both profitable and pre-profit companies, so without it there's no basis for any verdict. If `ps_ratio` is null or zero, stop and report that yfinance returned no usable data for this ticker. (Note: the MCP server raises `YFNoDataError` itself when `ps_ratio` is missing, so this path mainly guards against an unexpected zero.)

### COMPUTE — Infer profit stage and track

- **ESTABLISHED**: `pe_ratio` is not null and greater than 0
- **EMERGING**: `pe_ratio` is null, zero, or negative
- **Track**: Always GROWTH for tech. The YIELD track is dormant — do not apply it unless the user explicitly requests it.

### THRESHOLD — Apply screening rules

---

#### ESTABLISHED path: Magic Formula (capped) + Quality Signals (MCP-constrained Piotroski analogue)

For ESTABLISHED tickers, run a two-factor quality screen using only fields the yf MCP actually exposes. **The canonical Piotroski F-Score and the canonical Magic Formula ROIC are NOT computable from the current `get_financials` surface** — the MCP returns only `revenue`, `operating_income`, `net_income`, `free_cash_flow`, `stock_based_compensation`, `total_debt`, `cash` per year (plus `marketCap`, `sharesOutstanding`, `eps_ttm` from `get_ratios`). It does NOT return total_assets, current_assets/liabilities, long-term debt split, gross_profit, operating_cash_flow, intangibles, or historical share counts.

[ABA-70](https://linear.app/ababushkin/issue/ABA-70) tracks adding those fields. Until then, the methodology below is the honest, MCP-constrained substitute. Every uncomputable input is marked **N/A** in the JSON — never fabricated, never silently proxied without disclosure.

##### Step 1 — Magic Formula (EY only — ROIC N/A)

**Earnings Yield** = `operating_income` / Enterprise Value
- `operating_income`: from `get_financials.years[0]` (most recent annual period). EBIT proxy — operating income excludes interest and tax, matching Greenblatt's definition.
- Enterprise Value (EV) = `marketCap + total_debt − cash`, all from the most recent year of `get_financials` (for `total_debt` / `cash`) and `get_ratios` (for `marketCap`). Do **not** use `ev_revenue` × revenue to back-derive EV — that path quietly inherits Yahoo's EV definition which we cannot inspect.

**ROIC** = **N/A in v1** — the canonical denominator (Net Working Capital + Net Fixed Assets) requires `total_assets`, `current_assets`, `current_liabilities`, and `intangible_assets`, none of which the MCP returns. Do **not** substitute an undocumented proxy. `roic` is `null` in JSON.

**Magic Formula flag:**
- **Multi-ticker batch** (≥2 ESTABLISHED tickers): rank each ticker by Earnings Yield (higher = better). Top 25% of batch → flag = `PASS`; remainder → flag = `WATCH`. Document that ranking is EY-only (no ROIC tiebreaker) in the rationale.
- **Single ESTABLISHED ticker**: Earnings Yield > 5% → flag = `PASS`; otherwise flag = `WATCH`. Single-dimension threshold — the rationale must note that ROIC is N/A so the bar is lower than the canonical "EY > 5% AND ROIC > 15%".

If `operating_income` or EV cannot be computed (missing data), set flag = `WATCH` and `earnings_yield: null`. Note the gap in the rationale.

##### Step 2 — Quality Signals (MCP-constrained — 9 signals, denominator floats)

This is a *named substitute* for the Piotroski F-Score. Each signal is 1 if true, 0 if false, N/A if the inputs are unavailable. **The denominator is the number of computable signals for this ticker, not 9** — i.e. score is reported as "X of N computable signals". Do not score N/A signals as 0; that would silently penalise tickers with sparse data.

YoY = year-over-year change comparing `get_financials.years[0]` (most recent) to `get_financials.years[1]` (prior year). If `years[1]` is missing, all YoY signals are N/A.

| Signal | Condition | Required fields | Notes |
|--------|-----------|-----------------|-------|
| Q1 `net_income_positive` | `net_income[0] > 0` | net_income | Profitability existence |
| Q2 `fcf_positive` | `free_cash_flow[0] > 0` | free_cash_flow | Cash generation existence |
| Q3 `net_income_improving` | `net_income[0] > net_income[1]` | net_income (2 yrs) | YoY profit trend |
| Q4 `fcf_improving` | `free_cash_flow[0] > free_cash_flow[1]` | free_cash_flow (2 yrs) | YoY cash trend |
| Q5 `revenue_growing` | `revenue[0] > revenue[1]` | revenue (2 yrs) | Top-line trend |
| Q6 `operating_margin_improving` | `op_income[0]/revenue[0] > op_income[1]/revenue[1]` | revenue, operating_income (2 yrs) | Margin trend |
| Q7 `leverage_not_increasing` | `total_debt[0] <= total_debt[1]` (no YoY rise) | total_debt (2 yrs) | Absolute debt — without total_assets denominator, this is the honest substitute for F5 |
| Q8 `cash_buffer_improving` | `cash[0] > cash[1]` | cash (2 yrs) | Liquidity trend (substitute for F6 current-ratio improving) |
| Q9 `sbc_intensity_not_worsening` | `sbc[0]/revenue[0] <= sbc[1]/revenue[1]` | stock_based_compensation, revenue (2 yrs) | Tech-specific quality signal — F-Score has no SBC equivalent because Piotroski (2000) predates the SBC era |

**Mapping to Piotroski (for reviewers familiar with the canonical signals):**
- Q1 ↔ F1 (NI > 0 is a strict substitute since we lack total_assets; profitability existence rather than ROA)
- Q2 substitutes for F2 OCF (FCF > 0 is strictly stronger than OCF > 0 — FCF = OCF − CapEx, so FCF positive implies OCF positive, but the reverse is not true; we err conservative)
- Q3, Q4, Q5, Q6 cover ROA-improving / accruals / efficiency dimensions without requiring TA
- Q7 substitutes for F5 (absolute debt rather than LT-debt / TA)
- Q8 substitutes for F6 (cash buffer rather than current-ratio improving)
- Q9 is NEW — SBC dilution is a tech-specific quality signal not in the original framework
- F7 (no new shares), F8 (gross margin improving), F9 (asset turnover) have **no honest MCP-constrained substitute** — they would require historical shares outstanding, gross_profit, and total_assets respectively, none of which the MCP exposes. They are **not** present in the 9 substitute signals.

If a signal's required field is null for any required year, the signal value is `null` (not `false`). The score is reported as `score: X, denominator: N, signals: {...}` where `N = sum(1 for v in signals.values() if v is not None)`.

##### Step 3 — Combine into verdict

Verdict uses the **normalised quality ratio** = `score / denominator`. This keeps the thresholds stable when some signals are N/A.

| Verdict | Condition |
|---------|-----------|
| PASS    | quality_ratio ≥ 0.75 (i.e. ≥75% of computable signals true) AND Magic Formula flag = PASS |
| WATCH   | quality_ratio ≥ 0.55, OR (quality_ratio ≥ 0.55 AND Magic Formula flag = WATCH) |
| SKIP    | quality_ratio < 0.55 (regardless of Magic Formula) |

The 0.55 / 0.75 cutoffs map to the original F-Score thresholds (5/9 ≈ 0.556 for WATCH; 7/9 ≈ 0.778 for PASS).

If `denominator < 4` (too sparse for a defensible verdict), force verdict = `WATCH` and note in the rationale that the quality dimension is insufficiently sampled — Magic Formula carries the decision.

Compose a one-sentence rationale citing the quality ratio (with score/denominator), which Q-signals drove it, the Magic Formula flag, and **explicitly call out that ROIC is N/A and the Piotroski substitute is MCP-constrained pending [ABA-70](https://linear.app/ababushkin/issue/ABA-70)**.

---

#### EMERGING path: Rule of 40 + Gross Margin Gate + EV/NTM Revenue

P/E is invalid for pre-profit companies — never apply it to EMERGING tickers.

For EMERGING tickers, call **three** yfinance MCP tools:
- `mcp__yf__get_ratios` — for `ev_revenue` and valuation context
- `mcp__yf__get_financials` — for annual `revenue`, `operating_income`, `free_cash_flow`, `total_debt`, `cash` (note: `gross_profit` is NOT returned — see Step 1 caveat)
- `mcp__yf__get_estimates` — for `ntm_revenue` (NTM consensus revenue estimate)

##### Step 1 — Gross Margin Gate (informational in v1)

Canonical gate: Gross Margin = Gross Profit / Revenue, hard SKIP if < 60%.

**v1 status — gate is INFORMATIONAL only.** The yf MCP `get_financials` tool does NOT currently return `gross_profit`. Until [ABA-70](https://linear.app/ababushkin/issue/ABA-70) ships:

- Set `gross_margin: null` and `gross_margin_gate: "N/A"` in JSON.
- Do **not** fabricate gross margin from peer averages, training-data recall, or any undocumented proxy.
- Do **not** fire SKIP on the basis of a missing gate.
- Always proceed to Step 2 (Rule of 40) and Step 3 (EV/NTM Revenue) regardless.
- Note the gate's v1 status in the rationale ("gross margin gate informational only — `gross_profit` not exposed by MCP, see ABA-70").

When `gross_profit` is available (post-ABA-70), restore the canonical behaviour:
- Gross Margin ≥ 60% → `gross_margin_gate: "PASS"`, proceed.
- Gross Margin < 60% → `gross_margin_gate: "FAIL"`, verdict = SKIP immediately, `rule_of_40` and `ev_ntm_revenue` set to `null`. Rationale must include "gross margin gate" explicitly.

##### Step 2 — Rule of 40

Rule of 40 Score = Revenue Growth Rate (%) + FCF Margin (%)

- **Revenue Growth Rate** = (Revenue_y0 − Revenue_y1) / |Revenue_y1| × 100
  - y0 = most recent annual period, y1 = prior annual period (from `get_financials`)
  - If only one year of data: use the `get_estimates` NTM revenue growth as a fallback — set `growth_source: "ntm_estimate"` in the output
- **FCF Margin** = Free Cash Flow / Revenue × 100 (most recent annual period)
  - If FCF is null or unavailable: substitute Operating Income / Revenue × 100 and set `fcf_note: "used operating income as FCF proxy"`

| Rule of 40 Score | Tier |
|-----------------|------|
| ≥ 40 | STRONG |
| 20–39 | ADEQUATE |
| < 20 | WEAK |

##### Step 3 — EV/NTM Revenue Position

EV/NTM Revenue = `ev_revenue` from `get_ratios` (Yahoo computes this as EV / TTM revenue; use it as a proxy for NTM if ntm_revenue unavailable)

Preferred: recompute as EV / ntm_revenue where:
- EV = market_cap + total_debt − cash (from `get_ratios` and `get_financials`)
- ntm_revenue from `get_estimates`

| EV/NTM Rev | Label |
|------------|-------|
| < 5× | CHEAP |
| 5–15× | FAIR |
| > 15× | RICH |

##### Step 4 — Combine into verdict

| Verdict | Condition |
|---------|-----------|
| PASS    | Rule of 40 ≥ 40 AND EV/NTM ≤ 15× |
| WATCH   | Rule of 40 ≥ 20 OR EV/NTM ≤ 15× (but not both PASS conditions met) |
| SKIP    | Rule of 40 < 20 AND EV/NTM > 15×, OR gross margin gate triggered |

Compose a one-sentence rationale citing the gross margin, Rule of 40 score, and EV/NTM Revenue, with the decisive factor.

---

### OVERRIDE

None currently active.

### OUTPUT

Run `mkdir -p reports` before writing. Write the report file at `reports/TICKER_YYYYMMDD.json` where YYYYMMDD is today's date.

**Required JSON structure (ESTABLISHED):**

```json
{
  "ticker": "META",
  "company": null,
  "date": "2026-05-12",
  "stages": {
    "screen": {
      "verdict": "PASS",
      "profit_stage": "ESTABLISHED",
      "ratios": {
        "pe_ratio": 24.1,
        "ps_ratio": 8.3,
        "ev_ebitda": 16.2,
        "pfcf": 28.4,
        "ev_revenue": 7.9
      },
      "quality_signals": {
        "score": 6,
        "denominator": 9,
        "ratio": 0.667,
        "methodology": "mcp_constrained_v1",
        "signals": {
          "q1_net_income_positive": true,
          "q2_fcf_positive": true,
          "q3_net_income_improving": true,
          "q4_fcf_improving": false,
          "q5_revenue_growing": true,
          "q6_operating_margin_improving": false,
          "q7_leverage_not_increasing": true,
          "q8_cash_buffer_improving": true,
          "q9_sbc_intensity_not_worsening": false
        },
        "piotroski_canonical": null,
        "piotroski_note": "Canonical Piotroski F-Score not computable from current yf MCP get_financials surface (missing total_assets, current_assets/liabilities, long-term debt split, gross_profit, operating_cash_flow, historical share counts). See ABA-70."
      },
      "magic_formula": {
        "earnings_yield": 0.062,
        "roic": null,
        "roic_note": "ROIC not computable from current yf MCP surface (canonical denominator requires total_assets, current_assets/liabilities, intangibles). See ABA-70.",
        "flag": "WATCH"
      },
      "rationale": "Quality ratio 6/9 = 67% (above 55% WATCH cutoff, below 75% PASS cutoff) with Magic Formula WATCH (EY 6.2%, ROIC N/A — MCP-constrained per ABA-70); WATCH verdict driven by mixed Q-signals (FCF declining, op-margin contracting, SBC intensity rising) offsetting positive profitability and revenue trend."
    }
  },
  "meta": {
    "profit_stage": "ESTABLISHED",
    "track": "GROWTH",
    "ai_layer": null,
    "confidence": "HIGH"
  }
}
```

**Required JSON structure (EMERGING — full M4 fields):**

```json
{
  "ticker": "CRWV",
  "company": null,
  "date": "2026-05-13",
  "stages": {
    "screen": {
      "verdict": "WATCH",
      "profit_stage": "EMERGING",
      "ratios": {
        "pe_ratio": null,
        "ps_ratio": 12.4,
        "ev_ebitda": null,
        "pfcf": null,
        "ev_revenue": 11.8
      },
      "quality_signals": null,
      "magic_formula": null,
      "gross_margin": 0.72,
      "gross_margin_gate": "PASS",
      "rule_of_40": {
        "revenue_growth_pct": 35.4,
        "fcf_margin_pct": 8.2,
        "score": 43.6,
        "tier": "STRONG",
        "growth_source": "yoy_annual",
        "fcf_note": null
      },
      "ev_ntm_revenue": {
        "value": 11.8,
        "label": "FAIR",
        "source": "get_ratios.ev_revenue"
      },
      "rationale": "Gross margin 72% clears the 60% gate; Rule of 40 score 43.6 (STRONG); EV/NTM Revenue 11.8x in FAIR band; both PASS conditions not jointly met (R40 STRONG but EV/NTM not CHEAP)."
    }
  },
  "meta": {
    "profit_stage": "EMERGING",
    "track": "GROWTH",
    "ai_layer": null,
    "confidence": "HIGH"
  }
}
```

For EMERGING tickers, `quality_signals` and `magic_formula` are always `null` (ESTABLISHED-only). For ESTABLISHED tickers, `gross_margin`, `gross_margin_gate`, `rule_of_40`, and `ev_ntm_revenue` are always `null` (EMERGING-only). If the gross margin gate fires SKIP, `rule_of_40` and `ev_ntm_revenue` are `null` (computation halted at the gate); the `gross_margin_gate` field is set to `"FAIL"` so the gate's effect is auditable.

**Rules:**
- Use JSON `null` for any field not populated — never `""` or `0` as a placeholder
- EMERGING tickers: set `quality_signals` and `magic_formula` to `null`. ESTABLISHED tickers: set `gross_margin`, `gross_margin_gate`, `rule_of_40`, `ev_ntm_revenue` to `null`
- Write valid JSON only — no prose in the file
- `date` is ISO format `YYYY-MM-DD`
- `company` is `null` (profile call not yet implemented)
- `ai_layer` is `null` (AI layer classification is a Signal-phase concern)
- Preserve full yfinance precision in numeric fields — rounding belongs in display layers

After writing each per-ticker file, print a one-line summary:

```
Wrote: reports/META_20260512.json
META — WATCH | ESTABLISHED | Quality 6/9 (67%), MF WATCH (EY 6.2%, ROIC N/A)
```

#### Batch consolidated report (multi-ticker runs only)

When the input contains **two or more tickers**, also write a single consolidated batch file at `reports/SCREEN_YYYYMMDD.json`. This file is what downstream tools and the UI use to read a full screening pass — the per-ticker files remain authoritative for individual ticker drilldown.

**Path:** `reports/SCREEN_YYYYMMDD.json` (uppercase `SCREEN` prefix; same date stamp as the per-ticker files in this run).

**Required JSON structure:**

```json
{
  "date": "2026-05-12",
  "tickers": ["META", "MSFT", "AAPL", "RDDT", "CRWV"],
  "stages": {
    "screen": [
      {
        "ticker": "META",
        "verdict": "PASS",
        "profit_stage": "ESTABLISHED",
        "ratios": {
          "pe_ratio": 24.1,
          "ps_ratio": 8.3,
          "ev_ebitda": 16.2,
          "pfcf": 28.4,
          "ev_revenue": 7.9
        },
        "quality_signals": {
          "score": 6,
          "denominator": 9,
          "ratio": 0.667,
          "methodology": "mcp_constrained_v1",
          "signals": { "q1_net_income_positive": true, "q2_fcf_positive": true, "q3_net_income_improving": true, "q4_fcf_improving": false, "q5_revenue_growing": true, "q6_operating_margin_improving": false, "q7_leverage_not_increasing": true, "q8_cash_buffer_improving": true, "q9_sbc_intensity_not_worsening": false }
        },
        "magic_formula": {
          "earnings_yield": 0.062,
          "roic": null,
          "roic_note": "ROIC not computable from current yf MCP surface (see ABA-70).",
          "flag": "PASS",
          "rank": 1
        },
        "gross_margin": null,
        "gross_margin_gate": null,
        "rule_of_40": null,
        "ev_ntm_revenue": null,
        "rationale": "Quality 6/9 (67%) with Magic Formula PASS (EY 6.2% rank 1 of batch, ROIC N/A); top of batch on EY-only ranking."
      },
      {
        "ticker": "CRWV",
        "verdict": "SKIP",
        "profit_stage": "EMERGING",
        "ratios": {
          "pe_ratio": null,
          "ps_ratio": 12.4,
          "ev_ebitda": null,
          "pfcf": null,
          "ev_revenue": 11.8
        },
        "quality_signals": null,
        "magic_formula": null,
        "gross_margin": 0.54,
        "gross_margin_gate": "FAIL",
        "rule_of_40": null,
        "ev_ntm_revenue": null,
        "rationale": "Gross margin 54% below 60% floor — gross margin gate triggered SKIP; R40 and EV/NTM not computed."
      }
    ]
  },
  "meta": {
    "batch_size": 5,
    "established_count": 3,
    "emerging_count": 2,
    "pass_count": 1,
    "watch_count": 2,
    "skip_count": 2,
    "track": "GROWTH",
    "confidence": "HIGH"
  }
}
```

**Batch JSON rules:**
- The `stages.screen` value is an **array**, one entry per ticker, ordered to match the input order. Each element is the per-ticker payload with the ticker as a sibling field (not a key), so it merges cleanly with the per-ticker `reports/TICKER_YYYYMMDD.json` shape.
- ESTABLISHED entries: populate `quality_signals` and `magic_formula`; leave `gross_margin`, `gross_margin_gate`, `rule_of_40`, `ev_ntm_revenue` as `null`.
- EMERGING entries: populate `gross_margin`, `gross_margin_gate`, `rule_of_40`, `ev_ntm_revenue`; leave `quality_signals` and `magic_formula` as `null`.
- For ESTABLISHED batches with ≥2 tickers, include the Magic Formula `rank` (1 = best) inside `magic_formula` so the UI can render the ranking column without recomputing.
- `meta.confidence` is `HIGH` when every ticker's data was retrieved cleanly; `MEDIUM` when one or more tickers had missing ratios or missing financials that degraded a signal; `LOW` when ≥1 ticker failed entirely.
- If a ticker errored during fetch, include it in the array with `verdict: null`, `rationale: "<error description>"`, and all signal fields `null`. Do not omit failed tickers — preserving the input order keeps row alignment with any UI table.
- Write the batch file **after** all per-ticker files have been written, so a failure during a single-ticker write does not leave a stale batch file referencing it.

#### Inline ranked table (multi-ticker runs only)

After all writes, print a single ranked table to the conversation so the user sees the full batch in one block:

```
SCREEN BATCH — 2026-05-12 (5 tickers)

Rank  Ticker  Stage         Verdict  Score / Signal
----  ------  ------------  -------  -----------------------------------------
  1   META    ESTABLISHED   WATCH    Quality 6/9, MF WATCH (EY 6.2%, ROIC N/A)
  2   MSFT    ESTABLISHED   WATCH    Quality 7/9, MF WATCH (EY 5.8%, ROIC N/A)
  3   AAPL    ESTABLISHED   WATCH    Quality 5/9, MF WATCH (EY 4.1%, ROIC N/A)
  4   RDDT    ESTABLISHED   SKIP     Quality 3/9, MF WATCH (EY 2.2%, ROIC N/A)
  5   CRWV    EMERGING      SKIP     Gross margin 54% < 60% gate — auto SKIP

Batch summary: 2 PASS, 2 WATCH, 1 SKIP
Wrote: reports/SCREEN_20260512.json
```

**Ranking rule:** Sort within the table by verdict (PASS → WATCH → SKIP), then within each verdict by profit stage's primary signal (ESTABLISHED: Earnings Yield descending — ROIC is N/A so no combined rank in v1; EMERGING: Rule of 40 score descending). The `Rank` column reflects the inline display order — it is NOT the Magic Formula rank, which is reported inside the `Score / Signal` cell. This ordering is for display only; the JSON `stages.screen` array preserves input order so downstream consumers can re-sort as they wish.

For single-ticker runs, the inline ranked table is not emitted and the consolidated batch file is not written — only the per-ticker file and its one-line summary appear.

---

## Invocation patterns

```
/screen META
/screen RDDT
/screen META, MSFT, AAPL     ← batch: Magic Formula ranking applies across the batch
```

---

## Common rationalisations

| Rationalisation | Rebuttal |
|---|---|
| "P/E is negative but this company clearly has earnings" | If yfinance returns a negative or null P/E, classify as EMERGING. Don't second-guess the data — a negative P/E signals something unusual and the pre-profit path is the safe default. |
| "The P/E field exists so I'll use it for this EMERGING company" | Pre-profit P/E is mathematically undefined or misleading. Only P/S applies to EMERGING companies. Mixing methods produces nonsense verdicts. |
| "A report file already exists for this ticker today, I'll skip writing" | Always overwrite. The user may be re-running with updated data or correcting a prior run. |
| "I'll round the ratios to 2 decimal places in the JSON" | Preserve full yfinance precision in the file. Rounding belongs in display layers, not in the source data that the report viewer reads. |
| "I'll continue past a null ps_ratio and use other ratios instead" | P/S is the one ratio available for both profitable and pre-profit companies. Without it there's no basis for any verdict. Stop and report. |
| "YFNoDataError means I should retry with a different ticker spelling" | Don't guess at ticker variants. Report the failure with the exact ticker the user supplied and let them re-invoke with a different one. |
| "I'll skip the financial data fetch and use only ratios for ESTABLISHED tickers" | The Quality Signals set requires 2 years of revenue/op_income/net_income/FCF/SBC/debt/cash from `get_financials`. Always call `get_financials` for ESTABLISHED tickers. |
| "All three tickers have the same Quality score" | Check that YoY deltas are computed correctly using two distinct annual periods. META, MSFT, and AAPL have meaningfully different revenue/op-margin/SBC trends — identical scores indicate a data or computation error. |
| "I'll fill in the canonical Piotroski F1–F9 from training data since I roughly know META's balance sheet" | NEVER fabricate signal values. The canonical F-Score requires fields the MCP does not return (total_assets, current_assets/liabilities, gross_profit, etc.). Mark them N/A — that is the spec. Inventing values from training-data recall is exactly the failure mode ABA-58 QA caught. See ABA-70 for the MCP expansion that restores canonical Piotroski. |
| "I'll proxy ROIC with operating_income / (total_debt − cash + marketCap) since I have all those fields" | That proxy collapses to the inverse of EY (operating_income / EV) — it provides no second signal independent from Earnings Yield. ROIC is `null` in v1 per the documented spec. Don't sneak in a proxy that fails the "second factor" criterion the Magic Formula relies on. |
| "I have only one year of get_financials data so I'll score the YoY signals as false" | YoY signals are N/A when only one year is available, NOT false. Scoring them false silently penalises tickers with sparse data. The denominator floats — see Step 2 in the ESTABLISHED path. |
| "Single-ticker run: I'll skip Magic Formula because there's no peer group to rank" | For single-ticker ESTABLISHED runs, use the absolute threshold: Earnings Yield > 5% → flag = PASS (ROIC is N/A in v1). Ranking requires a batch; the EY threshold is the correct fallback for single tickers. |
| "I'll call get_financials for EMERGING tickers too, just in case" | EMERGING tickers do still need `get_financials` for revenue (R40), free_cash_flow (R40 FCF margin), and (when we get gross_profit back from ABA-70) the gross margin gate. **However**, the Quality Signals and Magic Formula sections do NOT run for EMERGING — those are ESTABLISHED-only. Call `get_financials` for every ticker; only apply the ESTABLISHED methodology when the stage classification fires ESTABLISHED. |
| "Gross margin gate is hard but get_financials doesn't return gross_profit so I'll estimate from peer averages" | NEVER estimate gross margin from peers or training data. If gross_profit is unavailable (current MCP state), mark `gross_margin: null` and `gross_margin_gate: "N/A"` — do not fire SKIP, do not fire PASS. Document the data gap in the rationale. ABA-70 tracks adding `gross_profit` to the MCP; until then, the gate is informational only for EMERGING tickers. |
| "One ticker errored, I'll skip writing the batch SCREEN_YYYYMMDD.json entirely" | Write the batch file with the errored ticker present (verdict null, rationale set to the error message). A consumer reading the batch must see every requested ticker in the array — omitting one silently makes failure invisible. |
| "I'll write the batch SCREEN_YYYYMMDD.json before the per-ticker files for speed" | Always write per-ticker files first, then the batch file. If a per-ticker write fails, the batch file would otherwise reference data that doesn't exist on disk. |
| "Single-ticker run: I'll still write a SCREEN_YYYYMMDD.json with one entry" | The batch file is only written for runs with two or more tickers. Single-ticker runs produce only the per-ticker TICKER_YYYYMMDD.json. The batch path is reserved for actual batches. |
| "The batch array should be sorted by verdict so the consumer doesn't have to" | The JSON array preserves input order — that's the contract. Sorting belongs in the inline display table, not the data file. Consumers re-sort as needed. |

---

## Dependencies

- **yfinance MCP server** must be connected. It is registered in `.mcp.json`. If `get_ratios` or `get_financials` is not available as a tool, tell the user to restart the Claude Code session so the MCP server is reloaded.

---

## Boundaries

- Never apply P/E thresholds, Quality Signals, or Magic Formula to EMERGING companies
- Never fabricate or hardcode Q-signal values, gross margin, or any field whose required input is not returned by the current yf MCP — mark as `null` and document the gap (see ABA-70)
- Always write valid JSON — the report viewer reads this file directly
- `company` is `null`; do not guess or hardcode the company name
- Do not add fields not listed in the output schema above
- For multi-ticker batches, collect all ticker data before computing Magic Formula ranks — ranking requires the full batch
- For multi-ticker batches, write both per-ticker `reports/TICKER_YYYYMMDD.json` files AND a consolidated `reports/SCREEN_YYYYMMDD.json` batch file; never one without the other
