---
name: stock-explain
description: Plain-English walkthrough of a stock's valuation model output. Invoked as `/stock-explain TICKER`. Reads the latest cached report from `reports/TICKER_YYYYMMDD.json` and produces a friendly narrative covering five questions — what the number says, how it was built, what drives it, what could break it, and how much to trust it. No live data fetches; no file writes. Use whenever the user wants to understand what a valuation number means, how it was derived, or why the model says what it says — even if they just ask "what does this mean?", "walk me through the model", "explain the number", or "how does the valuation work". Designed for a reader with zero finance background.
---

# Explain — Plain-English Valuation Walkthrough

**Command:** `/stock-explain TICKER`
**Purpose:** Turn a cached model report into a friendly narrative that any reader can follow — no finance knowledge required.

---

## 1. Identity

- **Skill name:** stock-explain
- **Command:** `/stock-explain TICKER`
- **Purpose:** Read the latest `reports/TICKER_YYYYMMDD.json` and produce a plain-English walkthrough of the valuation. Read-only — no MCP calls, no file writes.

---

## 2. Methodology

This skill is a translator, not a calculator. All numbers come from the cached report; nothing is recomputed except one specific anchor (implied year-5 free cash flow — see Section 6). The job is to render the model's inputs, outputs, and uncertainties in language that a smart non-investor can read in three minutes and actually understand.

The output answers five questions a thoughtful reader naturally asks:

1. *What does the number say?* — the bottom line
2. *How did we get there?* — model inputs and mechanics
3. *What's really driving it?* — sensitivity and the bet being made
4. *What could break it?* — failure modes
5. *How much should I trust it?* — confidence with qualitative context

Use these as your skeleton. Choose section headings that fit the ticker rather than reusing the same five phrases every time — a generic template reads like boilerplate, and the goal is something a friend wrote, not something a form produced.

---

## 3. Input Schema

All inputs come from `reports/TICKER_YYYYMMDD.json`. No MCP calls. No internet access.

| Field path | Used for |
|---|---|
| `stages.signal.verdict` | Direction of the signal (buy / watch / caution) |
| `stages.signal.profit_stage` | Whether the company is established (profitable) or pre-profit |
| `stages.signal.ai_layer` | Company's relationship to AI (infrastructure, application, etc.) |
| `stages.signal.qualitative_note` | Any flags from the signal phase |
| `stages.model.current_price` | Today's market price at the time of the model run |
| `stages.model.fcf_ttm` | Trailing free cash flow (SBC-stripped) used as the model's starting point |
| `stages.model.fcf_ttm_reported` | Reported free cash flow (before removing stock comp) — for comparison |
| `stages.model.sbc_ttm` | Stock-based compensation removed from FCF |
| `stages.model.fcf_margin_ttm` | Free cash flow as a percentage of revenue |
| `stages.model.growth_rate` | Object: applied rate, whether it was capped, and the source of the cap |
| `stages.model.base_wacc` | Discount rate used in the base scenario |
| `stages.model.base_wacc_source` | Where the discount rate came from (playbook / generic / user) |
| `stages.model.scenarios.bear/base/bull` | Three scenarios, each with IV per share, upside %, growth rate, WACC, terminal growth, narrative |
| `stages.model.intrinsic_value_range` | Convenience object: bear / base / bull IV in dollars |
| `stages.model.sensitivity` | Which input moves the IV most, and by how much |
| `stages.model.playbook.loaded` | Whether ticker-specific assumptions were loaded |
| `stages.model.playbook.failure_modes` | Company-specific downside scenarios (if playbook loaded) |
| `meta.confidence` | HIGH / MEDIUM / LOW |

---

## 4. Execution Phases

### Phase 1 — LOCATE

Find the most recent report file for the requested ticker:

```
reports/TICKER_*.json  →  sort by date descending  →  take the first
```

If no file is found, stop and say:

> No report found for [TICKER]. Run `/stock-signal [TICKER]` first, then `/stock-model [TICKER]`, and try again.

Show the report date near the top of the output so the reader knows how fresh the data is.

### Phase 2 — VALIDATE

Check that both `stages.signal` and `stages.model` are present in the report.

- If `stages.signal` is missing: "The signal phase hasn't been run yet — run `/stock-signal [TICKER]` first."
- If `stages.model` is missing: "The model phase hasn't been run yet — run `/stock-model [TICKER]` first."

### Phase 3 — EXPLAIN

Draft the narrative according to the writing principles in Section 5 and the content requirements in Section 6.

### Phase 4 — EMIT

Print the output to the terminal. Do not write any files.

---

## 5. Writing Principles

These shape the *craft* of the explanation. Read them before drafting, not after.

**Define every acronym and abbreviation on first use.** Put a plain-English gloss in parentheses. Case doesn't matter — what matters is that a smart non-investor never hits a term they can't decode. Common ones to define:

- free cash flow (FCF) — the money the business generates after paying to keep itself running and grow
- discounted cash flow (DCF) — a method for estimating what a business is worth based on the cash it will generate in the future
- weighted-average cost of capital (WACC) — roughly, the annual return investors require to take on the risk of owning this stock
- stock-based compensation (SBC) — shares or options given to employees as pay, which dilute existing shareholders
- intrinsic value (IV) — our model's estimate of what the stock is actually worth per share
- trailing twelve months (TTM) — the most recent full year of data

**Sound like a knowledgeable friend, not a form.** Mix flowing prose with bullets, short tables, and per-scenario callouts where each works best. Use prose when the logic has to connect ("we capped growth at 25% because…"); use bullets when items are genuinely parallel (failure modes, scenario takeaways). Avoid analyst-report mannerisms ("the company demonstrated robust free cash flow generation").

**Choose headings that fit the ticker.** Suggested phrasings — "The bottom line", "How we got here", "What's driving the number most", "What could go wrong", "How much to trust this" — are fine but not mandatory. If a different phrasing serves the specific story better, use it. The five *questions* in Section 2 are what's load-bearing, not the exact words.

**Quantify every assumption claim.** Don't say "WACC is a key driver." Say "Dropping the discount rate by 1 percentage point would push the base estimate from $207 to roughly $240" — pull the dollar impact from `stages.model.sensitivity` or compute it from the scenario spread. The reader should always be able to see what would change the answer and by how much.

**Honour the bear/base/bull spread.** A wide spread is a fact about the uncertainty in the bet, not a flaw to hide. State it honestly and explain *why* it's wide (usually: the growth rate or WACC has high uncertainty).

**Refer to the report date.** Never imply the data is live. If the report is more than a few weeks old, note it.

---

## 6. Content Requirements

These are the elements the output must contain. The order is flexible; the elements are not.

### A. Bottom line (1–2 sentences near the top)

Current price, base intrinsic value, and the gap as a percentage. Translate the signal verdict to plain language ("the model sees it as a buy" rather than "BUY"). Show the report date here or in the heading area.

### B. How the number was built

Walk through the inputs in the order they enter the model:

1. **Starting cash flow** — name the cleaned-up FCF figure, briefly explain why it differs from the reported number (SBC is subtracted because it's a real cost even though it doesn't show up as a cash payment).
2. **Growth assumption** — state the 5-year rate, where it came from (analyst consensus, ticker-specific playbook ceiling, or a generic fallback), and any cap that was applied. Explain *why* caps exist when relevant ("raw historical rates often overstate what's sustainable").
3. **Discount rate (WACC)** — name it, explain it in plain terms, note whether it's company-specific or generic.
4. **The mechanics** — one sentence: "We project five years of free cash flow, add a terminal value (an estimate of what the business is worth from year six onward at a slower steady state), and discount everything back to today's dollars."

### C. What's driving the number — including two REQUIRED elements

**Required: WACC sensitivity with the interest-rate angle.** Use `stages.model.sensitivity` to anchor a quantified statement of how much a 1 percentage point change in WACC moves the per-share value. Then connect it to the macro lens the reader actually cares about: "If long-term interest rates rise, WACC rises with them — and the model's estimate would compress accordingly." This is the single most-asked question from non-finance readers; never skip it.

**Required: implied year-5 free cash flow.** After explaining the sensitivity, compute and state what the base scenario's growth rate implies for the company's free cash flow in five years. This is the only number you compute yourself — everything else comes straight from the report.

- Use `scenarios.base.y1_fcf × (1 + scenarios.base.y2_5_cagr)^4`.
- Fall back to `fcf_ttm × (1 + growth_rate.applied_base_cagr)^5` if `y1_fcf` is missing.
- State it with a future year ("by 2031, ~$691 billion in free cash flow") and a comparison to today ("roughly 7.5× the $90 billion the business generates now").
- Frame it as a reality check the reader can sanity-test against industry size or comparable companies. This anchor is what makes the growth assumption *concrete*.

**Optional but encouraged: per-scenario narratives.** Each scenario in the report has its own narrative field. Surface them with framing like "what has to go right" / "what has to go wrong" / "what the base case assumes" — this makes the bear/base/bull range mean something rather than being three numbers in a row.

### D. What could go wrong

If `stages.model.playbook.loaded` is true, use `playbook.failure_modes` as the primary source. If not, synthesise 2–3 risks from the bear scenario narrative and the sensitivity dominant driver.

Format as short bullets or short bolded paragraphs — one risk per item. Each risk should name (1) what event happens, and (2) why it breaks the model's specific growth assumption.

**Example (playbook loaded):**
- **AI capex slowdown:** If cloud providers cut GPU spending — as happened briefly in 2022 — NVIDIA's revenue could plateau and the 35% annual growth the base case assumes would quickly look too optimistic.
- **Custom-chip displacement:** ASIC chips built by Google, Amazon, and others are already taking share in AI inference. If they exceed 25% of AI workloads by 2027, it removes one of the main tailwinds behind NVIDIA's pricing power.
- **Export controls:** If the US government tightens rules to cover NVIDIA's next-generation China chips, it eliminates residual China revenue and signals that further restrictions are politically viable.

### E. How much to trust this — with qualitative context

Translate `meta.confidence` (HIGH / MEDIUM / LOW) to plain language, and *then* go further than the report does. The numerical confidence answers "how much did the model have to guess?" but the more useful question for the reader is "what kind of bet is this, in business terms?" Add 2–4 sentences of qualitative context drawn from the report's qualitative fields (signal `ai_layer`, `qualitative_note`, scenario narratives, playbook content):

- Where is the company in its market lifecycle? (Early share gains, mature with expansion bets, defending a moat?)
- What kind of future is the base case implicitly betting on? (Continued AI infrastructure buildout? Successful pivot? Regulatory stability?)
- What's the most important thing the reader should be watching that the model can't measure?

**Example (NVDA, qualitative context):**

> A company already at roughly 90% share of data-centre AI accelerators has limited room to grow from share gains. Future growth requires the AI compute market itself to keep expanding — a bet on continued hyperscaler capex, sovereign-AI buildouts, and the emergence of new workloads like physical AI. These are real opportunities, but they sit further out and are harder to forecast than the share-gain story of the past three years.

This kind of context is what separates a useful explanation from a recitation of the model.

---

## 7. Invocation Patterns

```
/stock-explain NVDA
/stock-explain META
/stock-explain AAPL
/stock-explain MSFT
```

---

## 8. Dependencies

- `reports/TICKER_YYYYMMDD.json` with both `stages.signal` and `stages.model` populated
- No MCP tools
- No external network access

---

## 9. Common Rationalisations

| What you might want to do | Why not to do it |
|---|---|
| Fetch live prices to make the output "current" | The skill explains the model that was run — live prices would mismatch the report's assumptions. If the report is stale, tell the user to re-run `/stock-signal` and `/stock-model`. |
| Add technical terms back in for completeness | If a term needs a parenthetical explanation, just use the parenthetical. The goal is comprehension, not precision theatre. |
| Emit a JSON block for the audit trail | The audit trail is the report JSON file itself. This output is for human reading only. |
| Skip the FCF/SBC explanation because the user already ran `/stock-model` | The whole point of `/stock-explain` is to build understanding from scratch. Always explain the inputs, regardless of what the user has already run. |
| Skip the WACC sensitivity / interest rate connection | This is the single most-asked question from non-finance readers. Always quantify a 1pp WACC move and connect it to interest rates. |
| Skip the implied year-5 FCF calculation | This is the most concrete way to sanity-check the growth assumption. Always compute and state it with a future-year reference. |
| Reuse the same five literal section headers on every ticker | Headings should fit the company's story. The five *questions* are required; the exact phrasing is not. |
| Hedge every sentence ("this may be", "it's possible that") | The model has already handled uncertainty through the bear/base/bull range. Don't pile on additional verbal hedging — it reads as evasive rather than honest. State clearly what the model says, and clearly what the known risks are. |
