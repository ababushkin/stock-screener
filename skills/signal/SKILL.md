---
name: stock:signal
description: GARP signal analysis for a tech stock. Invoked as `/stock:signal TICKER`. Fetches live financials and estimates from the yfinance MCP, strips SBC, computes PEG/P/S, classifies AI layer, and outputs a structured SIGNAL OUTPUT block with a MODEL_READY flag. Use whenever the user asks to analyse a stock more deeply, investigate a ticker, check whether it passes GARP criteria, or after a `/stock:screen` PASS or WATCH result — even if they don't say "signal" or "GARP".
---

# Signal — GARP Signal Analysis

**Command:** `/stock:signal TICKER`
**Purpose:** GARP signal analysis. Fetches valuation ratios and financials from the yfinance MCP, classifies profit stage and AI layer, strips SBC from EPS, and emits a structured SIGNAL OUTPUT block with a MODEL_READY flag for downstream use by `/stock:model`.

---


## 1. Identity

- **Skill name:** stock:signal
- **Command:** `/stock:signal TICKER`
- **Purpose:** Produce a GARP signal verdict (BUY / WATCH / CAUTION) and a MODEL_READY flag for a single ticker, using yfinance data and a structured qualitative overlay.

---

## 2. Methodology

Growth at a Reasonable Price (GARP) — a combination of:

- **Clean EPS** (earnings after SBC removal) — SBC stripping is step zero, always
- **PEG ratio** (P/E ÷ forward EPS growth rate) — primary GARP metric for ESTABLISHED companies
- **P/S ratio** — primary metric for EMERGING companies where PEG is undefined
- **Rule of 40** (revenue growth % + FCF margin %) — supplementary filter for ESTABLISHED SaaS/software; N/A for hardware/semis
- **AI layer classification** — qualitative modifier applied to INFRASTRUCTURE / APPLICATION / MODEL / INCUMBENT companies

Source references: Peter Lynch (One Up on Wall Street) for PEG; Brad Feld/Fred Wilson for Rule of 40; Cagan/GARP corpus for valuation discipline.

---

## 3. Input Schema

| Input | Source | Data-gap handling |
|---|---|---|
| Ticker | Command argument | Uppercase; fail immediately if blank |
| P/E ratio (TTM) | `get_ratios(ticker)` | Null → classify EMERGING; never use for pre-profit |
| P/S ratio (TTM) | `get_ratios(ticker)` | Null → stop; report gap to user |
| EV/EBITDA (TTM) | `get_ratios(ticker)` | Null → note as missing; not blocking |
| P/FCF (TTM) | `get_ratios(ticker)` | Null → note as missing; not blocking |
| EV/Revenue (TTM) | `get_ratios(ticker)` | Null → note as missing; not blocking |
| SBC (TTM) — **required** | `get_financials(ticker)` — `Stock Based Compensation` row from cashflow | Null → `Clean EPS: N/A — SBC not returned by yfinance`; `SBC stripped: N/A` |
| Shares outstanding — **required for SBC stripping** | `get_ratios(ticker)` — `sharesOutstanding`; fallback: market cap ÷ current price | Null → same N/A treatment as missing SBC |
| Diluted EPS (TTM) — **required for SBC stripping** | `get_ratios(ticker)` — `eps_ttm`; fallback: price ÷ `pe_ratio` | Null → same N/A treatment |
| NTM EPS consensus | `get_estimates(ticker)` — `ntm_eps` field | Null → PEG = N/A — reason: no consensus; required for PEG computation |
| 5-year EPS CAGR | `get_estimates(ticker)` — `eps_growth_5y` field if available | Null → fall back to derived estimate: `(ntm_eps / clean_ttm_eps)^(1/5) − 1`; if that is also unavailable or ≤ 0, PEG = N/A with reason |
| NTM revenue estimate | `get_estimates(ticker)` | Null → Rule of 40 degrades; note in output |
| Company name | `get_ratios` response or inference | Use ticker if name unavailable |

---

## 4. Execution Phases

### GATHER

1. Parse the ticker from the command argument. Uppercase it (e.g. `nvda` → `NVDA`).
2. Call the yfinance MCP `get_ratios` tool:
   - Server: `yf`, Tool: `get_ratios`
   - Input: `{ "ticker": "NVDA" }`
   - Returns: `pe_ratio`, `ps_ratio`, `ev_ebitda`, `pfcf`, `ev_revenue`, `period` (always `"TTM"`), `date`
3. Call the yfinance MCP `get_financials` tool to retrieve SBC line:
   - Server: `yf`, Tool: `get_financials`
   - Input: `{ "ticker": "NVDA" }`
   - Used for: `Stock Based Compensation` row from cashflow statement
4. Call the yfinance MCP `get_estimates` tool to retrieve forward consensus:
   - Server: `yf`, Tool: `get_estimates`
   - Input: `{ "ticker": "NVDA" }`
   - Used for: NTM EPS consensus (PEG denominator)
5. If `get_ratios` fails:
   - **YFNoDataError**: ticker may be delisted, mistyped, or Yahoo's endpoint changed. Report failure and stop.
   - **Other failures (network, server not connected)**: report failure and stop.
   - In all cases: do not write a partial report.

### VALIDATE

- `ps_ratio` must be non-null and greater than 0. **If missing, fire the Manual Input Protocol** (see `skills/_shared/MANUAL_INPUT_PROTOCOL.md`) before stopping — ask the user to paste P/S, current price, EPS TTM, shares outstanding, and SBC TTM as a grouped paste-in. Only stop if the user replies `abort`.
- The protocol also fires when `get_ratios` raised `YFNoDataError` (the common case for non-US filers), or when `get_financials` returned null for `stock_based_compensation` on the most recent year.
- Any field accepted via paste-in is tagged `source: "user_paste"` and added to `meta.manual_inputs`; overall `meta.confidence` caps at MEDIUM (LOW if every required field came from paste-in).
- State what was retrieved and what gaps exist before proceeding.

### COMPUTE

Execute these steps in order. Each step may produce inputs required by later steps.

**Step 1 — Profit stage inference:**
- **ESTABLISHED**: `pe_ratio` is not null and greater than 0
- **EMERGING**: `pe_ratio` is null, zero, or negative
- **Track**: Always GROWTH for tech. YIELD track is dormant — do not apply unless user explicitly requests it.

**Step 2 — AI layer classification (pure qualitative reasoning):**
No MCP tool call required. Reason from the company's primary revenue source and public AI investment posture.

Classification decision tree:
1. Does the company's primary revenue come from AI chips, cloud compute, or data centre hardware? → INFRASTRUCTURE
2. Is AI embedded in SaaS products as a core differentiator, with subscription-based revenue? → APPLICATION
3. Is the primary product a foundation model or model API? → MODEL
4. Is this a large profitable tech company using AI as optionality/defence rather than as a primary product? → INCUMBENT
5. None of the above / AI is not material to the investment thesis → N/A

Output: one-line rationale explaining the primary reason for the classification.

Examples:
- NVDA → INFRASTRUCTURE — primary revenue from data centre GPUs that power AI training and inference workloads
- META → INCUMBENT — core revenue from ad targeting; AI (LLaMA, Reels ranking) is an optionality layer, not the product
- AAPL → N/A — AI features (Apple Intelligence) are product polish, not a revenue driver or investment thesis
- MSFT → INFRASTRUCTURE — Azure AI and Copilot integration make AI a primary revenue driver across cloud and productivity

**Step 3 — TAM penetration check (INFRASTRUCTURE companies only):**

Fires when AI layer = INFRASTRUCTURE. This is a qualitative estimate — state all assumptions explicitly; never assert precision.

Steps:
1. Retrieve the company's data centre / AI hardware revenue run-rate from `get_financials(ticker)`. If a segment breakdown is unavailable, use the most recent publicly reported data centre revenue figure from training knowledge and flag it as an estimate.
2. Annualise if needed: if the most recent period is a single quarter, multiply by 4.
3. Estimate data centre GPU TAM from training knowledge. Use the range $150–400B for 2025–2026 and pick a point estimate appropriate to the current year (e.g. ~$250B for mid-2025 as a central estimate). State the source assumption.
4. Compute implied TAM penetration = annualised DC/AI revenue run-rate ÷ estimated TAM × 100.
5. Classify and output:
   - Penetration > 50%: flag as **TAM ceiling risk** — significant ceiling risk at current growth trajectory; contributes FAIL to Qualitative if the primary signal lens is already CAUTION, otherwise FLAG.
   - Penetration 30–50%: neutral note — approaching ceiling; monitor trajectory.
   - Penetration < 30%: positive note — meaningful runway remains.
6. Output a TAM penetration note in the TAM/Optionality line (see OUTPUT section).

Example note: "Data centre GPU TAM: ~$250B est.; NVDA at ~$115B annualised DC revenue = ~46% penetration — approaching ceiling, monitor trajectory."

**Step 4 — AI optionality flag (INCUMBENT companies only):**

Fires when AI layer = INCUMBENT. This is a qualitative estimate — state all assumptions explicitly; the percentage must always be a number in the output, never omitted or written as N/A.

Steps:
1. From `get_financials(ticker)` retrieve the TTM capital expenditure figure (capital expenditures line from the cashflow statement). This is total capex; qualitatively estimate the AI-attributed portion from context (e.g. for META in 2025, a large fraction of capex is publicly attributed to AI infrastructure — state the assumed fraction and its basis).
2. Estimate AI capex run-rate = total TTM capex × estimated AI fraction. State both figures and the fraction assumption.
3. Apply a 5× revenue multiple on AI capex as a conservative premium proxy to estimate the implied AI optionality premium in dollar terms. State assumption: "Assumption: 5× AI capex as a rough AI revenue premium proxy (conservative)."
4. Get market cap from `get_ratios(ticker)` — derive as price × sharesOutstanding if not directly available.
5. AI optionality premium % = (AI capex run-rate × 5) ÷ market cap × 100.
6. Classify and output:
   - Premium > 20%: flag — "AI capex implies a significant unverified optionality premium; buyer should verify AI monetisation path." Contributes FLAG to Qualitative (not FAIL — this is a risk, not a disqualifier).
   - Premium ≤ 20%: note — "AI investment appears proportionate to core business value."
7. Output: `AI optionality premium: XX%` in the TAM/Optionality line (see OUTPUT section). XX must be a computed number — never omit, never write N/A.

Example note: "AI optionality premium: 23% — AI capex implies a significant unverified optionality premium; buyer should verify AI monetisation path. (Assumption: ~60% of $38B TTM capex attributed to AI; 5× proxy multiple.)"

**Step 5 — SBC stripping:**
1. From `get_financials(ticker)` response, extract the TTM `Stock Based Compensation` value from the cashflow statement.
2. Calculate shares outstanding: use `sharesOutstanding` from `get_ratios` response (or derive from market cap ÷ current price if not directly available).
3. Per-share SBC = TTM SBC ÷ shares outstanding
4. Reported diluted EPS (TTM) = from `get_ratios` response, field `eps_ttm` (or derive: price ÷ `pe_ratio` if `eps_ttm` not available)
5. Clean EPS (TTM) = Reported diluted EPS − per-share SBC
6. SBC stripped = YES; note the dollar adjustment: "SBC adjustment: $X.XX per share"

**Data gap handling:**
- If SBC line is missing from cashflow: output `Clean EPS (TTM): N/A — SBC not returned by yfinance`; `SBC stripped: N/A`
- If shares outstanding cannot be determined: same N/A treatment
- Never skip or estimate SBC — only two states: computed (YES) or not available (N/A with reason)

**Step 6 — PEG ratio computation:**

Pre-conditions:
- Only compute for ESTABLISHED companies (positive clean TTM EPS). For EMERGING: PEG = N/A — pre-profit.
- Requires NTM EPS from `get_estimates`.

Steps:
1. Clean forward P/E = current price ÷ (NTM EPS − per-share SBC)
   - current price: derive as `pe_ratio × reported_diluted_eps` from ratios if not directly available
   - If NTM EPS ≤ 0 or unavailable: PEG = N/A — forward earnings negative or unavailable
2. 5-year EPS growth rate (g):
   a. Use yfinance 5-year growth estimate from `get_estimates` if present (field: `eps_growth_5y` or similar)
   b. Fallback: derive `g = (ntm_eps / clean_ttm_eps)^(1/5) − 1` (1-year bridge × compounding approximation)
   c. If g ≤ 0: PEG = N/A — negative/zero growth makes PEG undefined
3. PEG ratio = clean forward P/E ÷ (g × 100)  [g expressed as whole number, e.g. 15 not 0.15]
4. State the computation: "PEG = [clean fwd P/E] ÷ [g]% = [result]"

**P/S as primary fallback:**
- For EMERGING companies: P/S is the primary metric. State explicitly: "P/E and PEG are undefined for pre-profit companies; using P/S as primary valuation metric."
- For ESTABLISHED companies where PEG = N/A: fall back to P/S as primary signal driver with a note explaining why PEG is unavailable.

**Step 7 — P/S ratio:**
- Read directly from `get_ratios` response. Output the value.

**Step 8 — Rule of 40 (not implemented — dormant):**
- Output `N/A — not implemented`.
- Rule of 40 = revenue growth % + FCF margin %; will be added in a future iteration.

### THRESHOLD

Always state which lens is active and why.

**ESTABLISHED — PEG available (primary lens):**

| Signal  | Condition |
|---------|-----------|
| BUY     | PEG ≤ 1.0 |
| WATCH   | PEG ≤ 2.0 |
| CAUTION | PEG > 2.0 |

**ESTABLISHED — PEG = N/A, fall back to P/S:**

| Signal  | Condition |
|---------|-----------|
| BUY     | P/S ≤ 8   |
| WATCH   | P/S ≤ 25  |
| CAUTION | P/S > 25  |

**EMERGING — P/S only (PEG never applies):**

| Signal  | Condition |
|---------|-----------|
| BUY     | P/S ≤ 8   |
| WATCH   | P/S ≤ 20  |
| CAUTION | P/S > 20  |

### OVERRIDE

**Qualitative field contributions from TAM/optionality checks:**

The `Qualitative` field (PASS / FLAG / FAIL) is computed after the primary signal lens, then adjusted by the TAM/optionality checks:

- **TAM ceiling risk (INFRASTRUCTURE, penetration > 50%):** If primary signal is CAUTION → Qualitative = FAIL. If primary signal is BUY or WATCH → Qualitative = FLAG. Include the TAM note in the one-line reason.
- **TAM approaching ceiling (INFRASTRUCTURE, penetration 30–50%):** Qualitative unchanged from primary lens result; include a neutral note in the reason.
- **TAM runway (INFRASTRUCTURE, penetration < 30%):** Qualitative unchanged; include a positive note.
- **AI optionality premium > 20% (INCUMBENT):** Qualitative = FLAG regardless of primary lens (never FAIL — optionality premium is a risk, not a disqualifier). Include the premium percentage in the reason.
- **AI optionality premium ≤ 20% (INCUMBENT):** Qualitative unchanged from primary lens result; note that investment appears proportionate.
- **All other AI layers (APPLICATION / MODEL / N/A):** TAM/optionality checks do not fire; Qualitative is determined solely by the primary signal lens thresholds.

**Override 1 — Pre-profit base effect (EMERGING companies):**

Fires for every EMERGING company — no exceptions.

```
IF profit_stage = EMERGING:
  Signal = CAUTION  (regardless of P/S threshold verdict above)
  MODEL_READY = NO
  Reason: "Pre-profit base effect — Signal CAUTION overrides P/S threshold; PEG undefined."
  Qualitative = FAIL if not already FAIL
```

**Override 2 — Transition year (first or second profitable year):**

Fires when the company has only recently turned profitable — earnings history is too short for reliable DCF inputs.

```
IF profit_stage = ESTABLISHED AND this is the company's first or second year of positive EPS:
  MODEL_READY = CONDITIONAL
  Condition: "Confirm [N]th profitable year before running Model — earnings history too short for reliable DCF inputs."
  Signal is NOT overridden by this rule; it stays at whatever the threshold produced.
```

Detection heuristic: if `eps_growth_5y` is unavailable (no 5-year history) AND `pe_ratio` is positive but very high (>100), flag as a potential transition year. Also apply if training knowledge or web search indicates the company first turned profitable within the last 2 years.

Known transition-year companies — apply automatically without needing to detect:
- **RDDT** — turned profitable late 2024; apply transition-year override

**Override 2.5 — SBC-distorted earnings (clean EPS negative because SBC absorbs reported EPS):**

Fires when the company is GAAP-profitable and FCF-positive, but stock-based compensation is large enough that clean (SBC-stripped) TTM EPS goes negative. Standard two-stage DCF cannot anchor here — there is no positive clean earnings base — but the company is too operationally mature for the pre-profit lens to fire naturally. The honest move is to route the user to the pre-profit `/stock:model` variant, which explicitly schedules dilution into year-5 share count and values the company on revenue / FCF rather than earnings. Reserve Override 3 (FAIL → NO) for governance, accounting, or going-concern problems where price-cheapness doesn't fix the thesis; SBC-driven dilution is a *valuation* problem the pre-profit lens is built to handle.

```
IF profit_stage = ESTABLISHED
   AND clean_eps_ttm < 0
   AND reported_diluted_eps > 0
   AND fcf_ttm > 0
   AND (sbc_per_share / reported_diluted_eps) >= 1.0:
  Qualitative = FLAG  (NOT FAIL — pre-empts Override 3; SBC is dilution overhang, not quality failure)
  Signal = min(threshold_verdict, WATCH)  (cap at WATCH; never upgrade — never report BUY when clean EPS is negative)
  MODEL_READY = CONDITIONAL
  Condition: "Clean TTM EPS is negative ($X.XX) because SBC ($Y.YY/sh) exceeds reported EPS ($Z.ZZ/sh).
              Standard DCF cannot anchor. Re-invoke with `/stock:model TICKER --pre-profit --confirm`
              to value via revenue/FCF multiple with explicit dilution schedule."
```

Evaluation order: this override is evaluated **after** Override 2 (transition year) and **before** Override 3 (qualitative FAIL). When it fires, Qualitative is set to FLAG before Override 3 sees the record, so Override 3 does not subsequently fire. If both Override 2 (transition year) and Override 2.5 fire on the same ticker, the conditions are merged into a single CONDITIONAL message naming both.

**Override 3 — Qualitative failure:**

```
IF Qualitative = FAIL:
  Signal = CAUTION  (unless already CAUTION from Override 1)
  MODEL_READY = NO
  Reason: state the specific qualitative failure
```

**Override 4 — Yield trap (dormant for most tech):**

```
IF track = YIELD AND dividend yield > 6% AND revenue growth < 0:
  Signal = CAUTION
  MODEL_READY = NO
  Reason: "Yield trap risk — high yield combined with negative growth."
```

This override is dormant for all GROWTH-track companies (i.e. virtually all tech). Included for completeness and for when YIELD track is enabled.

### OUTPUT

Emit the SIGNAL OUTPUT block. **All fields must appear every run.** Unimplemented fields show a placeholder — they are never omitted.

```
SIGNAL OUTPUT
  Ticker:          [TICKER]
  Company:         [Name or ticker if unavailable]
  Profit stage:    [ESTABLISHED | EMERGING]
  Track:           [GROWTH | YIELD]
  AI layer:        [INFRASTRUCTURE | APPLICATION | MODEL | INCUMBENT | N/A] — [one-line rationale]

  Clean EPS (TTM): [$X.XX | N/A — reason]
  SBC stripped:    [YES — SBC adjustment: $X.XX/share | N/A — reason]
  PEG ratio:       [x.x (active lens) | N/A — reason (pre-profit / no consensus / negative growth / forward earnings negative)]
  P/S ratio:       [x.x]
  Rule of 40:      [N/A — not implemented]

  Qualitative:     [PASS | FLAG | FAIL] — [one-line reason including TAM/optionality note if applicable]
  TAM/Optionality: [note — only present when AI layer = INFRASTRUCTURE or INCUMBENT; omit line for all other layers]
                   INFRASTRUCTURE example: "Data centre GPU TAM: ~$250B est.; NVDA at ~$115B annualised DC revenue = ~46% penetration — approaching ceiling, monitor trajectory."
                   INCUMBENT example: "AI optionality premium: 23% — AI capex implies a significant unverified optionality premium; buyer should verify AI monetisation path."

  Signal:          [BUY | WATCH | CAUTION]
  MODEL_READY:     [YES | CONDITIONAL | NO]
  Condition:       [if CONDITIONAL — what the user must confirm; omit line if YES or NO]
```

**MODEL_READY final logic:**

Evaluate after all four override rules have been applied. Precedence: NO > CONDITIONAL > YES — a CAUTION always produces NO, even if other conditions would point to CONDITIONAL.

| MODEL_READY | Condition |
|---|---|
| YES | Signal = BUY or WATCH, AND Qualitative ≠ FAIL, AND no transition-year flag, AND Override 2.5 did not fire, AND profit_stage = ESTABLISHED |
| CONDITIONAL | Signal = WATCH, AND (transition-year flag is set OR Override 2.5 fired OR one or more stub fields are still pending) |
| NO | Signal = CAUTION, OR Qualitative = FAIL, OR profit_stage = EMERGING |

If MODEL_READY = CONDITIONAL, the `Condition` line MUST state what the user needs to confirm before running `/stock:model`. Never leave Condition blank on a CONDITIONAL result.

**Report JSON write:**
Run `mkdir -p reports` before writing.
Write to `reports/TICKER_YYYYMMDD.json` where YYYYMMDD is today's date.

Merge behaviour:
- If the file already exists (e.g. written by `/stock:screen` earlier), READ it first, then merge — add/update `stages.signal` and `meta` fields. Do NOT overwrite `stages.screen` or other stages.
- If the file does not exist, create it with the full outer structure.

**Required JSON structure for a new file:**

```json
{
  "ticker": "[TICKER]",
  "company": "[company name or ticker if unavailable]",
  "date": "[YYYY-MM-DD]",
  "stages": {
    "signal": {
      "verdict": "[BUY | WATCH | CAUTION]",
      "profit_stage": "[ESTABLISHED | EMERGING]",
      "track": "[GROWTH | YIELD]",
      "ai_layer": "[INFRASTRUCTURE | APPLICATION | MODEL | INCUMBENT | N/A | null]",
      "clean_eps_ttm": "[number or null]",
      "sbc_stripped": "[true | false | null]",
      "sbc_adjustment_per_share": "[number or null]",
      "peg_ratio": "[number or null]",
      "ps_ratio": "[number]",
      "rule_of_40": null,
      "qualitative": "[PASS | FLAG | FAIL]",
      "qualitative_note": "[one-line reason]",
      "signal": "[BUY | WATCH | CAUTION]",
      "model_ready": "[YES | CONDITIONAL | NO]",
      "condition": "[string or null]"
    }
  },
  "meta": {
    "profit_stage": "[ESTABLISHED | EMERGING]",
    "track": "[GROWTH | YIELD]",
    "ai_layer": "[classification or null]",
    "confidence": "[HIGH | MEDIUM | LOW]"
  }
}
```

**Confidence rules:**
- HIGH: SBC stripped successfully + PEG computed (not N/A) + qualitative = PASS
- MEDIUM: any of SBC/PEG are N/A but P/S is available
- LOW: P/S is the only reliable data point

**Field mapping from SIGNAL OUTPUT block to JSON:**
- Ticker → `ticker` (uppercase)
- Company → `company`
- Profit stage → `profit_stage` (and `meta.profit_stage`)
- Track → `track` (and `meta.track`)
- AI layer → `ai_layer` (and `meta.ai_layer`) — strip the rationale note; JSON gets the enum value only (e.g. `"INFRASTRUCTURE"`, not `"INFRASTRUCTURE — primary revenue from data centre GPUs..."`)
- Clean EPS (TTM) → `clean_eps_ttm` (number; `null` if N/A)
- SBC stripped → `sbc_stripped` (`true` if YES; `null` if N/A)
- SBC adjustment dollar value → `sbc_adjustment_per_share` (number; `null` if N/A)
- PEG ratio → `peg_ratio` (number; `null` if N/A)
- P/S ratio → `ps_ratio` (number)
- Rule of 40 → `rule_of_40` (`null` — deferred)
- Qualitative → `qualitative` (PASS/FLAG/FAIL only; rationale goes in `qualitative_note`)
- Signal → `signal` (and `verdict` — both must be the same value)
- MODEL_READY → `model_ready`
- Condition → `condition` (string; `null` if not CONDITIONAL)

**JSON validity rules:**
- Use JSON `null` (not `""` or `0`) for any unavailable field
- No trailing commas, no comments, no NaN values
- `date` is ISO format `YYYY-MM-DD`
- `sbc_stripped` is a boolean (`true`/`false`/`null`) — never the string `"YES"` or `"N/A"`

After writing, print:

```
Wrote: reports/NVDA_20260512.json  ← stages.signal
NVDA — WATCH | ESTABLISHED | PEG 1.8 | P/S 20.9 | MODEL_READY: YES
```

---

## 5. Output Schema

Every run produces the SIGNAL OUTPUT block above and writes `reports/TICKER_YYYYMMDD.json`. Fields 1–13 are always present in both the block and JSON; field 14 is conditional (present in block; `null` in JSON when not CONDITIONAL).

The 14 JSON fields under `stages.signal` are:

1. `verdict` — BUY / WATCH / CAUTION (same value as `signal`)
2. `profit_stage` — ESTABLISHED or EMERGING
3. `track` — GROWTH (always in M1)
4. `ai_layer` — enum value only: INFRASTRUCTURE / APPLICATION / MODEL / INCUMBENT / N/A (rationale is in the SIGNAL OUTPUT block, not in JSON)
5. `clean_eps_ttm` — SBC-stripped EPS as a number; `null` if SBC unavailable
6. `sbc_stripped` — boolean `true` if successfully stripped; `null` if N/A
7. `sbc_adjustment_per_share` — per-share SBC deduction as a number; `null` if N/A
8. `peg_ratio` — computed PEG as a number; `null` if N/A (pre-profit / no consensus / negative growth / forward earnings negative)
9. `ps_ratio` — number (always present if VALIDATE passes)
10. `rule_of_40` — `null` (deferred — not yet implemented)
11. `qualitative` — PASS / FLAG / FAIL only; rationale is in `qualitative_note`
12. `qualitative_note` — one-line reason string (includes TAM/optionality note when applicable)
13. `signal` — BUY / WATCH / CAUTION (same value as `verdict`)
14. `model_ready` — YES / CONDITIONAL / NO; `condition` is a string when CONDITIONAL, `null` otherwise. See MODEL_READY table in the OUTPUT section above.

---

## 6. Data Fetching Behaviour

- Always fetch from yfinance MCP tools — do not use hardcoded values or training-data recall for ratios
- Fetch order: `get_ratios` first (required), then `get_financials` and `get_estimates` (supplementary; failures are noted but not blocking in the stub)
- State what was retrieved, what was missing, and what was assumed before the SIGNAL OUTPUT block

---

## 7. Invocation Patterns

```
/stock:signal NVDA
/stock:signal Meta Platforms        ← resolve to META if unambiguous
/stock:signal RDDT
```

For multiple tickers, direct the user to `/stock:screen TICKER1, TICKER2` then invoke `/stock:signal` on each PASS result individually. Signal is a single-ticker operation.

---

## 8. Dependencies

- **yfinance MCP server** must be connected (`get_ratios`, `get_financials`, `get_estimates`). Registered in `.mcp.json`. If tools are unavailable, tell the user to restart the Claude Code session.
- **`reports/` directory** — created on first write via `mkdir -p reports`.
- **`/stock:model` skill** — reads the SIGNAL OUTPUT block from context. If block is absent, Model cannot proceed.

---

## 9. Tech-Specific Rules

**SBC stripping (mandatory):**
- SBC is step zero before any earnings calculation. Always retrieve `Stock Based Compensation` from `get_financials` and compute per-share SBC before applying any multiple.
- Never list SBC alongside other one-offs. It is its own line item in the output.
- Never skip SBC stripping on grounds that SBC is "immaterial" — always check, always compute or report N/A with reason.

**AI layer classification:**
See decision tree and examples in Section 4, Step 2. Classification is pure qualitative reasoning — no MCP call required.

**TAM penetration and AI optionality:**

TAM penetration check fires only for INFRASTRUCTURE companies. AI optionality flag fires only for INCUMBENT companies. Neither fires for APPLICATION, MODEL, or N/A layers.

TAM penetration rules:
- Use the company's annualised data centre / AI hardware revenue as the numerator. If segment detail is unavailable from `get_financials`, use the most recent publicly reported figure and flag it as an estimate.
- Use $150–400B as the 2025–2026 data centre GPU TAM range; pick a stated point estimate and state it explicitly. Do not assert precision — this is a qualitative estimate.
- Penetration > 50%: Qualitative = FLAG (or FAIL if primary lens = CAUTION). State "TAM ceiling risk."
- Penetration 30–50%: Qualitative unchanged; note "approaching ceiling."
- Penetration < 30%: Qualitative unchanged; note "meaningful runway."
- Always output the TAM/Optionality line for INFRASTRUCTURE companies.

AI optionality rules:
- Use TTM capex from `get_financials` as the base. Qualitatively estimate the AI-attributed fraction; state the fraction and its basis explicitly.
- Apply a 5× revenue multiple on AI capex as the premium proxy. Always state this assumption.
- AI optionality premium % = (AI capex × 5) ÷ market cap × 100.
- The percentage must always be a computed number in the output. Never omit it, never write N/A, never write "not applicable."
- Premium > 20%: Qualitative = FLAG. State "AI capex implies a significant unverified optionality premium; buyer should verify AI monetisation path."
- Premium ≤ 20%: Qualitative unchanged. Note "AI investment appears proportionate to core business value."
- Always output the TAM/Optionality line for INCUMBENT companies.

**Three-lens valuation hierarchy:**
- For ESTABLISHED companies: use PEG as the primary signal lens when available. Fall back to P/S if PEG = N/A. Never silently switch lenses — always state which lens is active and why.
- For EMERGING companies: P/S is always the primary lens. PEG is never applicable. P/E is never applicable. State this explicitly in the output.
- The fallback chain is: PEG → P/S. There is no P/E-only lens — P/E only appears as an intermediate step in computing clean forward P/E for the PEG numerator.

**Pre-profit / EMERGING rules:**
- Never apply P/E or PEG to EMERGING companies — mathematically undefined or misleading.
- Rule of 40 is the primary supplementary filter for EMERGING SaaS (not yet implemented).
- P/S is the primary ratio for EMERGING at all times.

**Track:**
- Growth track is the default for all tech companies.
- Yield track is dormant. Do not apply it unless the user explicitly requests it and the thesis is genuinely income-oriented.

---

## 10. Override Rules

All four active override rules and the qualitative overrides from TAM/optionality checks are defined in the OVERRIDE section of Section 4. This section lists only planned future overrides not yet implemented:
- AI infrastructure premium: INFRASTRUCTURE companies may sustain higher P/S multiples — lift WATCH threshold from P/S ≤ 25 to P/S ≤ 40 if Rule of 40 ≥ 60 and revenue growth > 30%
- Rule of 40 excellence: score ≥ 60 may lift CAUTION to WATCH for EMERGING companies
- Earnings revision momentum: strong upward revision trend may lift WATCH to BUY

---

## Common Rationalisations

| Rationalisation | Rebuttal |
|---|---|
| "SBC is small for this company so I'll skip stripping it" | SBC stripping is mandatory step zero in every run. The amount is always noted. Skipping it silently is the exact failure mode the rule exists to prevent. |
| "P/E is negative but this company clearly has earnings" | If yfinance returns a negative or null P/E, classify as EMERGING. A negative P/E signals something unusual — the pre-profit path is the safe default. |
| "I'll apply PEG to this pre-profit company because it has a useful forward estimate" | PEG requires positive trailing earnings. For EMERGING companies PEG is undefined. Use P/S only. |
| "The stub fields are not computed so I'll just omit them from the SIGNAL OUTPUT block" | Every field must appear every run. Omitting a field breaks the output contract that `/stock:model` depends on. Use the placeholder text. |
| "MODEL_READY = YES because the signal looks good even though stub fields are pending" | If any of Clean EPS, Rule of 40, or AI layer are pending, MODEL_READY is at most CONDITIONAL. The condition line must explain what needs confirming. |
| "PEG is available so I can skip P/S entirely" | P/S must always be fetched and reported. P/S is the fallback lens and is always present in the output block regardless of whether PEG is computed. |
| "I'll use a raw P/E from yfinance as my PEG numerator" | The PEG numerator is clean forward P/E — computed from NTM EPS minus per-share SBC. Never use reported P/E directly as the PEG numerator. |
| "g is small so I'll round up to avoid a very high PEG" | Compute g exactly and report the result honestly. A very high PEG is a valid signal — do not adjust it. |
| "I'll infer the AI layer from my training data rather than computing it" | AI layer classification is a qualitative filter requiring current context. In the stub, output the placeholder. Do not hallucinate a classification. |
| "I'll look up AI layer from a hardcoded table" | Classification is qualitative reasoning, not a lookup. Apply the decision tree and state your reasoning. The output is only as good as the argument you make. |
| "A report file already exists for this ticker today, I'll skip writing" | Always write. The user may be re-running with updated data or correcting a prior run. Read-modify-write if the file exists. |
| "yfinance returned null for P/S — I'll estimate from sector average" | Forbidden. Fire the Manual Input Protocol (`skills/_shared/MANUAL_INPUT_PROTOCOL.md`) and ask the user to paste the value. Ask, don't assume. |
| "I'll fire one question per missing field — that's cleaner" | Forbidden. Group every missing field into a single paste-in prompt. Round-trips cost the user time. |
| "The user is busy, I'll use last quarter's value" | Forbidden. Stale ≠ current. The Manual Input Protocol exists so we don't silently substitute. |
| "I'll skip merging and just overwrite the whole file" | If `/stock:screen` was run first, the file has `stages.screen`. Overwriting it loses the screen data the UI needs. Always read-modify-write when the file already exists. |
| "I'll use my training knowledge for ratio values instead of calling the MCP" | Always fetch live data from the yfinance MCP. Training data ratios are stale by definition. |
| "SBC per share looks tiny — probably a unit mismatch but I'll proceed anyway" | yfinance returns SBC in raw dollars (not thousands or millions) and shares outstanding in units. Verify the magnitude before dividing — if per-share SBC exceeds $10 for a sub-$500 stock, a unit mismatch is almost certain. Report the raw figures so the user can sanity-check. |
| "I'll skip the TAM/optionality check since it's qualitative anyway" | These checks are required for INFRASTRUCTURE and INCUMBENT companies respectively. The AI optionality premium percentage must be present and non-null for every INCUMBENT. Skipping a qualitative check because it's qualitative is the exact failure mode it was designed to prevent. |
| "The AI optionality premium percentage is hard to estimate so I'll write N/A" | The percentage must always be a computed number. Estimate AI capex fraction from context, apply the stated 5× proxy, divide by market cap. State your assumptions. N/A is never acceptable for this field on INCUMBENT companies. |
| "The TAM estimate is uncertain so I'll omit the TAM/Optionality line" | Uncertainty is exactly why this is a qualitative note rather than a precise metric. State the range ($150–400B), pick a point estimate, state your assumption, and compute the penetration. The output must include the line. |
| "RDDT has a positive P/E so I'll mark MODEL_READY: YES" | RDDT is in its first profitable year (transition year). Override 2 applies: MODEL_READY = CONDITIONAL with condition stating to confirm 2nd profitable year. The positive P/E establishes ESTABLISHED stage and allows Signal to remain at the threshold verdict — but MODEL_READY is capped at CONDITIONAL until a second profitable year is confirmed. |
| "C3.ai shows a WATCH or BUY result from the P/S threshold so I'll give WATCH or BUY" | Override 1 fires for all EMERGING companies regardless of P/S threshold verdict. AI (C3.ai) is pre-profit (EMERGING), so Signal = CAUTION and MODEL_READY = NO unconditionally. The P/S threshold is computed and shown for transparency but is overridden. |
| "Clean EPS is negative so Qualitative must be FAIL and MODEL_READY = NO" | Not when SBC is the sole cause and the company is GAAP-profitable + FCF-positive. Override 2.5 routes this case to Qualitative = FLAG and MODEL_READY = CONDITIONAL so the pre-profit `/stock:model` variant can value the company via revenue/FCF multiple with explicit dilution scheduling. Reserve FAIL for governance / accounting / going-concern issues where price-cheapness doesn't fix the thesis. |
| "Adding Override 2.5 just lets users bypass SBC discipline" | The opposite. The pre-profit variant is the *only* DCF lens that explicitly schedules SBC dilution into year-5 share count. The current NO refusal lets users argue away the dilution by retreating to reported EPS; Override 2.5 channels them into a model that confronts dilution head-on. The verdict cap at WATCH also prevents the threshold lens from producing a BUY signal while clean economics are underwater. |
