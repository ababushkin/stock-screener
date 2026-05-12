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

#### ESTABLISHED path: Magic Formula + Piotroski F-Score

For ESTABLISHED tickers, replace the simple P/E and P/S rules with a two-factor quality screen. Both factors draw on `get_financials` data (balance sheet, income statement, cash flow) plus `get_ratios`.

##### Step 1 — Magic Formula (Greenblatt)

**Earnings Yield** = EBIT / Enterprise Value
- EBIT: from income statement, most recent annual period
- EV: from `get_ratios` response field `enterprise_value`. If null, derive as `market_cap + total_debt − cash_and_equivalents` from balance sheet.

**ROIC** = EBIT / (Net Working Capital + Net Fixed Assets)
- Net Working Capital = Current Assets − Current Liabilities
- Net Fixed Assets = Total Assets − Current Assets − Intangible Assets (use 0 if intangibles not reported)

**Magic Formula flag:**
- **Multi-ticker batch** (≥2 ESTABLISHED tickers): rank each ticker by combined rank (Earnings Yield rank + ROIC rank, lower combined rank = better). Top 25% of batch → flag = `PASS`; remainder → flag = `WATCH`.
- **Single ESTABLISHED ticker**: use absolute thresholds — Earnings Yield > 5% AND ROIC > 15% → flag = `PASS`; otherwise flag = `WATCH`.

If EBIT or EV cannot be computed (missing data), set flag = `WATCH` and note the data gap in the rationale.

##### Step 2 — Piotroski F-Score (9 binary signals, score 0–9)

Each signal is 1 if true, 0 if false. Sum all signals for the score. YoY = year-over-year change comparing the most recent annual period to the prior annual period.

**Profitability (4 signals):**
| Signal | Condition |
|--------|-----------|
| F1 `f1_roa_positive` | Net Income / Total Assets > 0 (most recent year) |
| F2 `f2_ocf_positive` | Operating Cash Flow > 0 (most recent year) |
| F3 `f3_roa_improving` | ROA increased YoY |
| F4 `f4_accruals_negative` | (Operating Cash Flow / Total Assets) − ROA < 0 → cash earnings quality |

**Leverage / Liquidity (3 signals):**
| Signal | Condition |
|--------|-----------|
| F5 `f5_leverage_decreasing` | Long-term debt / Total Assets ratio decreased YoY |
| F6 `f6_current_ratio_improving` | Current Assets / Current Liabilities increased YoY |
| F7 `f7_no_new_shares` | Shares outstanding did not increase YoY |

**Efficiency (2 signals):**
| Signal | Condition |
|--------|-----------|
| F8 `f8_gross_margin_improving` | Gross Profit / Revenue increased YoY |
| F9 `f9_asset_turnover_improving` | Revenue / Total Assets increased YoY |

If a signal cannot be computed due to missing data, score it as 0 and note it.

##### Step 3 — Combine into verdict

| Verdict | Condition |
|---------|-----------|
| PASS    | Piotroski ≥ 7 AND Magic Formula flag = PASS |
| WATCH   | Piotroski 5–6, OR Magic Formula flag = WATCH (and Piotroski ≥ 5) |
| SKIP    | Piotroski ≤ 4 (regardless of Magic Formula) |

Compose a one-sentence rationale citing the Piotroski score, which signals drove it, the Magic Formula flag, and the decisive threshold.

---

#### EMERGING path: Rule of 40 + Gross Margin Gate + EV/NTM Revenue

P/E is invalid for pre-profit companies — never apply it to EMERGING tickers.

For EMERGING tickers, call **three** yfinance MCP tools:
- `mcp__yf__get_ratios` — for `ev_revenue` and valuation context
- `mcp__yf__get_financials` — for TTM/annual revenue, gross profit, operating income, free cash flow
- `mcp__yf__get_estimates` — for `ntm_revenue` (NTM consensus revenue estimate)

##### Step 1 — Gross Margin Gate (hard gate, runs first)

Gross Margin = Gross Profit / Revenue (most recent annual period from `get_financials`)

**If Gross Margin < 60%: verdict = SKIP immediately.**
- Do not compute Rule of 40 or EV/NTM Revenue.
- Rationale must include "gross margin gate" explicitly.
- This is a hard gate — no exceptions.

If Gross Margin ≥ 60%: proceed to Step 2.

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
      "piotroski": {
        "score": 7,
        "signals": {
          "f1_roa_positive": true,
          "f2_ocf_positive": true,
          "f3_roa_improving": true,
          "f4_accruals_negative": true,
          "f5_leverage_decreasing": false,
          "f6_current_ratio_improving": true,
          "f7_no_new_shares": false,
          "f8_gross_margin_improving": true,
          "f9_asset_turnover_improving": true
        }
      },
      "magic_formula": {
        "earnings_yield": 0.062,
        "roic": 0.28,
        "flag": "PASS"
      },
      "rationale": "Piotroski F-Score of 7 (≥7 threshold met) with Magic Formula PASS (EY 6.2%, ROIC 28%); strong profitability and efficiency signals drive the PASS verdict."
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

**Required JSON structure (EMERGING — unchanged):**

```json
{
  "ticker": "RDDT",
  "company": null,
  "date": "2026-05-12",
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
      "piotroski": null,
      "magic_formula": null,
      "rationale": "P/S of 12.4 falls within the WATCH band (8–20) for EMERGING stage."
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

**Rules:**
- Use JSON `null` for any field not populated — never `""` or `0` as a placeholder
- EMERGING tickers: set `piotroski` and `magic_formula` to `null`
- Write valid JSON only — no prose in the file
- `date` is ISO format `YYYY-MM-DD`
- `company` is `null` (profile call not yet implemented)
- `ai_layer` is `null` (AI layer classification is a Signal-phase concern)
- Preserve full yfinance precision in numeric fields — rounding belongs in display layers

After writing each per-ticker file, print a one-line summary:

```
Wrote: reports/META_20260512.json
META — PASS | ESTABLISHED | Piotroski 7, MF PASS (EY 6.2%, ROIC 28%)
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
        "piotroski": {
          "score": 7,
          "signals": { "f1_roa_positive": true, "f2_ocf_positive": true, "f3_roa_improving": true, "f4_accruals_negative": true, "f5_leverage_decreasing": false, "f6_current_ratio_improving": true, "f7_no_new_shares": false, "f8_gross_margin_improving": true, "f9_asset_turnover_improving": true }
        },
        "magic_formula": {
          "earnings_yield": 0.062,
          "roic": 0.28,
          "flag": "PASS",
          "rank": 1
        },
        "rule_of_40": null,
        "gross_margin": null,
        "ev_ntm_revenue": null,
        "rationale": "Piotroski 7 with Magic Formula PASS (EY 6.2%, ROIC 28%); top of batch on combined rank."
      },
      {
        "ticker": "RDDT",
        "verdict": "SKIP",
        "profit_stage": "EMERGING",
        "ratios": {
          "pe_ratio": null,
          "ps_ratio": 12.4,
          "ev_ebitda": null,
          "pfcf": null,
          "ev_revenue": 11.8
        },
        "piotroski": null,
        "magic_formula": null,
        "rule_of_40": { "score": 18, "tier": "WEAK", "revenue_growth_pct": 22.0, "fcf_margin_pct": -4.0 },
        "gross_margin": 0.54,
        "ev_ntm_revenue": { "value": 9.2, "label": "FAIR" },
        "rationale": "Gross margin 54% below 60% floor — gross margin gate triggered."
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
- ESTABLISHED entries: populate `piotroski` and `magic_formula`; leave `rule_of_40`, `gross_margin`, `ev_ntm_revenue` as `null`.
- EMERGING entries: populate `rule_of_40`, `gross_margin`, `ev_ntm_revenue`; leave `piotroski` and `magic_formula` as `null`.
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
  1   META    ESTABLISHED   PASS     Piotroski 7, MF PASS (EY 6.2%, ROIC 28%)
  2   MSFT    ESTABLISHED   PASS     Piotroski 7, MF PASS (EY 5.8%, ROIC 26%)
  3   AAPL    ESTABLISHED   WATCH    Piotroski 6, MF WATCH (EY 4.1%, ROIC 35%)
  4   CRWV    EMERGING      WATCH    R40 42 STRONG, EV/NTM 13.1× FAIR, GM 72%
  5   RDDT    EMERGING      SKIP     Gross margin 54% < 60% gate — auto SKIP

Batch summary: 2 PASS, 2 WATCH, 1 SKIP
Wrote: reports/SCREEN_20260512.json
```

**Ranking rule:** Sort within the table by verdict (PASS → WATCH → SKIP), then within each verdict by profit stage's primary signal (ESTABLISHED: Magic Formula combined rank; EMERGING: Rule of 40 score descending). The `Rank` column reflects the inline display order — it is NOT the Magic Formula rank, which is reported inside the `Score / Signal` cell. This ordering is for display only; the JSON `stages.screen` array preserves input order so downstream consumers can re-sort as they wish.

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
| "I'll skip the financial data fetch and use only ratios for ESTABLISHED tickers" | Piotroski requires balance sheet and cash flow data across 2 years; `get_ratios` alone cannot supply F1–F9. Always call `get_financials` for ESTABLISHED tickers. |
| "All three tickers have the same Piotroski score" | Check that YoY deltas are computed correctly using two distinct annual periods. META, MSFT, and AAPL have meaningfully different capital structures and efficiency trends — identical scores indicate a data or computation error. |
| "Single-ticker run: I'll skip Magic Formula because there's no peer group to rank" | For single-ticker ESTABLISHED runs, use absolute thresholds: Earnings Yield > 5% AND ROIC > 15% → flag = PASS. Ranking requires a batch; thresholds are the correct fallback for single tickers. |
| "I'll call get_financials for EMERGING tickers too, just in case" | EMERGING tickers skip the financials fetch entirely — Piotroski and Magic Formula are undefined for pre-profit companies. Only call get_financials for ESTABLISHED tickers. |
| "One ticker errored, I'll skip writing the batch SCREEN_YYYYMMDD.json entirely" | Write the batch file with the errored ticker present (verdict null, rationale set to the error message). A consumer reading the batch must see every requested ticker in the array — omitting one silently makes failure invisible. |
| "I'll write the batch SCREEN_YYYYMMDD.json before the per-ticker files for speed" | Always write per-ticker files first, then the batch file. If a per-ticker write fails, the batch file would otherwise reference data that doesn't exist on disk. |
| "Single-ticker run: I'll still write a SCREEN_YYYYMMDD.json with one entry" | The batch file is only written for runs with two or more tickers. Single-ticker runs produce only the per-ticker TICKER_YYYYMMDD.json. The batch path is reserved for actual batches. |
| "The batch array should be sorted by verdict so the consumer doesn't have to" | The JSON array preserves input order — that's the contract. Sorting belongs in the inline display table, not the data file. Consumers re-sort as needed. |

---

## Dependencies

- **yfinance MCP server** must be connected. It is registered in `.mcp.json`. If `get_ratios` or `get_financials` is not available as a tool, tell the user to restart the Claude Code session so the MCP server is reloaded.

---

## Boundaries

- Never apply P/E thresholds or Piotroski/Magic Formula to EMERGING companies
- Always write valid JSON — the report viewer reads this file directly
- `company` is `null`; do not guess or hardcode the company name
- Do not add fields not listed in the output schema above
- For multi-ticker batches, collect all ticker data before computing Magic Formula ranks — ranking requires the full batch
- For multi-ticker batches, write both per-ticker `reports/TICKER_YYYYMMDD.json` files AND a consolidated `reports/SCREEN_YYYYMMDD.json` batch file; never one without the other
