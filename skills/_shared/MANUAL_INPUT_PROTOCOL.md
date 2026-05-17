# Manual Input Protocol (shared across /stock-signal, /stock-screen, /stock-timing, /stock-model)

When an MCP tool returns null (or raises `YFNoDataError`) on a field a skill needs, the skill MUST NOT silently degrade to N/A and MUST NOT fabricate the value. It MUST offer the user a structured paste-in fallback.

## Trigger

Any required field is `null` after the MCP call, OR the MCP call raised `YFNoDataError`, AND a sensible user-supplied value would unblock the computation. Examples (from ABA-72 / KSPI run):

| Missing field | Paste format | Source |
|---|---|---|
| Current price | `Price = 86.38 USD` | any quote page |
| P/S ratio | `P/S = 2.14` | StockAnalysis.com, finbox.com, or computed manually |
| FX rate | `USD/KZT = 521.34` | xe.com, google.com/finance |
| Stock-based compensation (TTM or annual) | `SBC = 12.5B KZT` (or `SBC = 0`) | 20-F / 10-K cash flow statement |
| Gross profit (annual) | `Gross profit FY2024 = 850B KZT` | filings or earnings press release |
| Organic revenue growth | `FY25 ex-acquisition revenue = 3,000B KZT` | earnings press release segment breakout |

The trigger does NOT fire when:
- The field is genuinely not needed for the verdict path being taken (e.g. PEG inputs for an EMERGING ticker).
- The MCP returned a valid `null` that the skill already handles via documented fallback (e.g. canonical Piotroski signal falling back to its MCP-constrained Q substitute — see `skills/stock-screen/SKILL.md` Step 2).

## Question template

When firing, the skill emits a single grouped question — never one paste-in question per field. Format:

> The yfinance MCP returned no `<field>` for `<TICKER>` (reason: `<YFNoDataError message | "field missing from response">`). To proceed I need the following — paste each on its own line, or reply `N/A` on a line to skip that field and accept reduced confidence:
>
> 1. `<field-1>` (units, source hint)
> 2. `<field-2>` (units, source hint)
> ...
>
> Or reply `abort` to stop the run.

State explicitly **why** each field is required (which downstream step uses it). Quote the source hint so the user knows where to find it.

## Parsing rules

- Accept lines of the shape `key = value [unit]` or `key: value [unit]` (case-insensitive on key, whitespace tolerant).
- Numeric values may use `B` / `M` / `K` suffixes (billions / millions / thousands) — expand to plain numbers.
- Currency suffix (`USD`, `KZT`, `EUR`, etc.) MUST be preserved alongside the numeric value when the field is monetary.
- Reject lines that don't parse — re-ask only the failed lines with a one-line error pointing at the parse failure. Do not silently drop them.
- `N/A` (case-insensitive, alone on a line) is a valid response and skips that field — the skill proceeds with its documented null-handling path for that field, and confidence is reduced (see below).
- `abort` (case-insensitive, alone on a line) halts the skill with a one-line acknowledgement.

## Provenance contract

Every field accepted via manual paste is tagged in the output JSON. The skill MUST:

1. Add a `meta.manual_inputs` array (or merge into an existing one) listing each field, value, and source:
   ```json
   "meta": {
     "manual_inputs": [
       { "field": "ps_ratio", "value": 2.14, "source": "user_paste", "note": "user pasted from StockAnalysis.com" },
       { "field": "current_price", "value": 86.38, "unit": "USD", "source": "user_paste", "note": null }
     ]
   }
   ```
2. For any computed downstream metric that consumed a manual input, tag it in the relevant `stages.<stage>` block with `source: "derived_from_manual"` so downstream consumers can trace provenance.
3. Never overwrite an existing MCP-sourced value with a manual one — manual fills only the null slots.

## Confidence rules

When `meta.manual_inputs` is non-empty:

- Cap overall `meta.confidence` at **MEDIUM** regardless of what the per-stage confidence logic would otherwise produce.
- If every required field is manual (i.e. the MCP failed entirely and the user pasted everything), cap at **LOW**.
- Per-stage `verdict` and `signal` fields still emit normally — confidence reflects provenance, not the verdict itself.

## Common rationalisations (pre-rebut — every skill includes these)

| Rationalisation | Counter |
|---|---|
| "I'll assume P/S ≈ 8 since that's typical for the sector." | Forbidden. Assumed values are indistinguishable from fabricated ones at read time. Ask, don't assume. |
| "yfinance returned null so I'll skip this field and proceed." | Only acceptable if the field has a documented null-handling path. Otherwise, fire the Manual Input Protocol. |
| "The user is busy; I'll just use last year's value." | Forbidden. Stale ≠ current. The Manual Input Protocol exists precisely so we don't silently substitute. |
| "I have the value from training data / web search — I'll use that." | Acceptable ONLY if you cite the source URL and date and tag it `source: "research"` (not `"mcp"` and not `"user_paste"`). Confidence still caps at MEDIUM. Prefer asking the user when the gap is small. |
| "I'll fire one question per missing field — that's clearer." | Forbidden. Group all questions in one prompt. Each round-trip costs the user time. |

## Skill-specific entry points

Each skill references this protocol from inside its GATHER / VALIDATE phase. The Common Rationalisations table at the bottom of each skill includes "ask, don't assume" as a row.

- `/stock-signal` — fires when `get_ratios` raises or returns null on `ps_ratio` / `currentPrice` / `eps_ttm` / `sharesOutstanding`, or when `get_financials` returns null on `stock_based_compensation` for the most recent year.
- `/stock-screen` — fires when `get_ratios` raises, or `get_financials` returns null on a field needed for the verdict path (e.g. `gross_profit` on EMERGING SKIP gate, `total_assets` on ESTABLISHED Piotroski canonical).
- `/stock-timing` — fires when `get_earnings_history` raises or returns no data, OR `get_analyst_targets` returns null on `avg_target`.
- `/stock-model` — fires post-gate; DCF inputs (currently stubbed — see ABA-31/34) will fire this when a required CF / discount-rate / terminal-rate input cannot be derived.
