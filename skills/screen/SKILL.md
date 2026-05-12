---
name: screen
description: Fast go/no-go valuation screen for tech stocks. Invoked as `/screen TICKER` or `/screen TICKER1, TICKER2`. Fetches ratios from the FMP MCP, classifies profit stage, applies threshold rules, and writes a structured JSON report to reports/. Use whenever asked to screen a stock, evaluate whether a ticker is worth deeper analysis, or produce a reports/ JSON for the UI. Also use when the user mentions a ticker and asks if it's cheap, overvalued, worth looking at, or whether to buy or investigate it — even if they don't say "screen."
---

# Screen — Fast Valuation Screen

**Command:** `/screen TICKER [, TICKER2 ...]`
**Purpose:** Fast go/no-go screen. Classifies a tech stock as PASS / WATCH / SKIP using valuation ratios from the FMP MCP. Writes output to `reports/TICKER_YYYYMMDD.json`.

---

## Walking-Skeleton Scope (M1)

This is the M1 stub. Thresholds are simple ratio-based rules. The M2 full implementation adds Magic Formula + Piotroski for established tech and Rule of 40 + EV/NTM Revenue for emerging tech.

---

## Execution Phases

### GATHER

1. Parse the ticker from the command argument. Uppercase it (e.g. `nvda` → `NVDA`). If multiple tickers are provided (comma-separated), process each one in sequence.
2. Call the FMP MCP `get_ratios` tool with the ticker:
   - Server: `fmp`, Tool: `get_ratios`
   - Input: `{ "ticker": "NVDA" }`
   - Returns: `pe_ratio`, `ps_ratio`, `ev_ebitda`, `pfcf`, `ev_revenue`, `period`, `date`
3. If the tool call fails:
   - **Per-ticker gating (HTTP 402 / "FMP free tier does not serve")**: report the failure for this ticker. If it's a known dual-class share (e.g. `GOOG`/`GOOGL`, `BRK.B`/`BRK.A`), suggest the sibling class to the user as a single-line follow-up — but **do not auto-run it**. The user decides whether the sibling is an acceptable proxy.
   - **Other failures (FMPNoDataError, network)**: report the failure for this ticker.
   - In all cases: do not write a partial report, and continue processing any remaining tickers in the list.

### VALIDATE

Confirm ratios were retrieved. At minimum, `ps_ratio` must be non-null and greater than 0 for the screen to proceed — P/S is the one ratio available for both profitable and pre-profit companies, so without it there's no basis for any verdict. If `ps_ratio` is null or zero, stop and report that FMP returned no usable data for this ticker.

### COMPUTE — Infer profit stage and track

- **ESTABLISHED**: `pe_ratio` is not null and greater than 0
- **EMERGING**: `pe_ratio` is null, zero, or negative
- **Track**: Always GROWTH for tech. The YIELD track is dormant — do not apply it unless the user explicitly requests it. (The dividend yield framework is a separate methodology not yet implemented.)

### THRESHOLD — Apply screening rules

**ESTABLISHED (P/E and P/S available):**

| Verdict | Condition |
|---------|-----------|
| PASS    | P/E ≤ 25 AND P/S ≤ 8 |
| WATCH   | P/E ≤ 45 AND P/S ≤ 25 |
| SKIP    | P/E > 45 OR P/S > 25 |

**EMERGING (P/S only; P/E is invalid for pre-profit companies — never apply it):**

| Verdict | Condition |
|---------|-----------|
| PASS    | P/S ≤ 8 |
| WATCH   | P/S ≤ 20 |
| SKIP    | P/S > 20 |

Compose a one-sentence rationale citing the key ratios and the decisive threshold.

### OVERRIDE

None in M1.

### OUTPUT

Run `mkdir -p reports` before writing. Write the report file at `reports/TICKER_YYYYMMDD.json` where YYYYMMDD is today's date.

**Required JSON structure:**

```json
{
  "ticker": "NVDA",
  "company": null,
  "date": "2026-05-12",
  "stages": {
    "screen": {
      "verdict": "WATCH",
      "profit_stage": "ESTABLISHED",
      "ratios": {
        "pe_ratio": 37.7,
        "ps_ratio": 20.9,
        "ev_ebitda": 25.1,
        "pfcf": 42.3,
        "ev_revenue": 19.8
      },
      "rationale": "P/E of 37.7 exceeds the 25 PASS threshold but sits within the 45 WATCH bound; P/S of 20.9 is within the 25 WATCH bound."
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

**Rules:**
- Use JSON `null` for any field not populated — never `""` or `0` as a placeholder
- Write valid JSON only — no prose in the file
- `date` is ISO format `YYYY-MM-DD`
- `company` is `null` in M1 (profile call not yet implemented)
- `ai_layer` is `null` in M1 (AI layer classification is a Signal-phase concern)

After writing the file, print a one-line summary:

```
Wrote: reports/NVDA_20260512.json
NVDA — WATCH | ESTABLISHED | P/E 37.7, P/S 20.9
```

---

## Invocation patterns

```
/screen NVDA
/screen RDDT
/screen AAPL, NVDA, META     ← screen multiple tickers in sequence
```

---

## Common rationalisations

| Rationalisation | Rebuttal |
|---|---|
| "P/E is negative but this company clearly has earnings" | If FMP returns a negative P/E, classify as EMERGING. Don't second-guess the data — a negative P/E signals something unusual and the pre-profit path is the safe default. |
| "The P/E field exists so I'll use it for this EMERGING company" | Pre-profit P/E is mathematically undefined or misleading. Only P/S applies to EMERGING companies. Mixing methods produces nonsense verdicts. |
| "A report file already exists for this ticker today, I'll skip writing" | Always overwrite. The user may be re-running with updated data or correcting a prior run. |
| "I'll round the ratios to 2 decimal places in the JSON" | Preserve full FMP precision in the file. Rounding belongs in display layers, not in the source data that the report viewer reads. |
| "I'll continue past a null ps_ratio and use other ratios instead" | P/S is the one ratio available for both profitable and pre-profit companies. Without it there's no basis for any verdict. Stop and report. |
| "GOOG failed, GOOGL is basically the same company, I'll just run that and write the report under GOOG" | Don't substitute tickers silently. Class A and Class C trade at different prices so ratios differ marginally. Report the GOOG failure, suggest GOOGL as a follow-up, let the user re-invoke. |

---

## Dependencies

- **FMP MCP server** must be connected. It is registered in `.claude/settings.json`. If `get_ratios` is not available as a tool, tell the user to restart the Claude Code session so the MCP server is reloaded.

---

## Boundaries

- Never apply P/E thresholds to EMERGING companies — P/E is undefined for pre-profit stocks
- Always write valid JSON — the report viewer reads this file directly
- `company` is `null` in M1; do not guess or hardcode the company name
- Do not add fields not listed in the output schema above
