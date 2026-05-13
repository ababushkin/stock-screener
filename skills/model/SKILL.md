---
name: stock:model
description: DCF/valuation model for a tech stock. Invoked as `/stock:model TICKER [--confirm]`. Reads MODEL_READY from the upstream `/stock:signal` (conversation context preferred, same-day `reports/TICKER_YYYYMMDD.json` fallback) and branches: YES → run two-stage DCF (ESTABLISHED) and emit a bear/base/bull intrinsic-value range; CONDITIONAL → halt and surface `condition` (or proceed when `--confirm` is passed); NO → refuse and surface `qualitative_note`. Pre-profit (EMERGING) variant — revenue-multiple exit + FCF inflection — lands in ABA-34. Use whenever the user asks for an intrinsic value, fair-value range, DCF, or "what's it worth" on a ticker.
---

# Model — DCF & Intrinsic Value

**Command:** `/stock:model TICKER [--confirm]`
**Purpose:** Run a two-stage DCF for ESTABLISHED profitable tech and emit a bear/base/bull intrinsic-value range, after enforcing the upstream-context contract from `/stock:signal`. EMERGING (pre-profit) variant lands in ABA-34.

---

## 1. Identity

- **Skill name:** stock:model
- **Command:** `/stock:model TICKER [--confirm]`
- **Purpose:** Gate on the upstream Signal, then compute a two-stage DCF (5y explicit FCF projection + Gordon terminal) under three demonstrably-different scenario sets. Output a per-share intrinsic-value range (bear/base/bull) with each scenario's assumptions and narrative fully disclosed, and merge into `reports/TICKER_YYYYMMDD.json` under `stages.model`. EMERGING (pre-profit) ticker variant is handled by ABA-34.

---

## 2. Why a context gate

Model is downstream of Signal: it consumes the profit-stage classification, clean EPS, AI layer, and MODEL_READY flag that Signal produces. Running `/stock:model` without first running `/stock:signal` would force this skill to either re-derive those inputs (duplicating Signal's MCP calls and methodology) or fabricate them (silently wrong). The gate enforces the contract — Signal first, Model second.

The gate also routes on `model_ready`. Signal's classification is the authoritative call on whether a DCF is sensible right now:

- `YES` — proceed past the gate; downstream DCF logic runs.
- `CONDITIONAL` — a specific user-confirmable risk exists. Halt and surface the `condition` string; require `--confirm` on re-invocation before continuing.
- `NO` — Signal has already ruled the DCF out (pre-profit, qualitative FAIL, or hard CAUTION). Refuse and point back to Signal.

v1.2 (ABA-31) lands the standard two-stage DCF for ESTABLISHED profile. EMERGING (pre-profit) variant — revenue-multiple exit + FCF inflection — lands in ABA-34.

---

## 3. Execution Phases

### GATHER

1. Parse the ticker from the command argument. Uppercase it (e.g. `nvda` → `NVDA`). If blank, refuse immediately with: "Usage: `/stock:model TICKER [--confirm]`".
2. Parse the optional `--confirm` flag. Its only effect is to allow a CONDITIONAL Signal to pass through (see GATE step 3 below).

### GATE — Resolve upstream Signal, then branch on MODEL_READY

**Step 1 — Locate the upstream Signal.** Two sources, in this precedence order:

1. **Conversation context (preferred).** Scan the messages above this invocation for a `SIGNAL OUTPUT` block whose `Ticker:` line matches the requested ticker (uppercase comparison). If multiple are present, use the most recent.
2. **Filesystem fallback.** If no in-context block is found, look for `reports/TICKER_YYYYMMDD.json` where `YYYYMMDD` is **today's date** (the same date format Signal writes). Read it and use `stages.signal` as the upstream payload. **Reject any file not dated today** — stale on-disk Signal data is fabrication risk; require the user to re-run `/stock:signal` instead.

If both sources are present, conversation context wins (it reflects the current session's reasoning).

**If neither source yields a valid upstream Signal for the requested ticker**, refuse with exactly this message (substituting the requested ticker):

> `/stock:model TICKER` requires a SIGNAL OUTPUT block in context. Please run `/stock:signal TICKER` first, then re-run `/stock:model TICKER` in the same session.

The literal phrase **"run `/stock:signal TICKER` first"** (with TICKER substituted) MUST appear in the refusal — it is verified by the ABA-30 smoke check.

Do not proceed past this step. Do not call any MCP tool. Do not write any file.

**Step 2 — Extract routing fields from the upstream Signal:**

- `model_ready` — `YES`, `CONDITIONAL`, or `NO`. Required.
- `condition` — string, only meaningful when `model_ready = CONDITIONAL`.
- `qualitative_note` — string, surfaced when `model_ready = NO`.
- `verdict` (or `signal`) — `BUY` / `WATCH` / `CAUTION`. Used in the YES acknowledgement.

From the in-context SIGNAL OUTPUT block, read by line label (`MODEL_READY:`, `Condition:`, `Qualitative:`, `Signal:`). From the JSON fallback, read `stages.signal.model_ready`, `stages.signal.condition`, `stages.signal.qualitative_note`, `stages.signal.verdict`.

**Step 3 — Branch on `model_ready`:**

**`YES`:** Gate passed. Emit:

> Gate passed: SIGNAL OUTPUT for TICKER found (source=SOURCE, verdict=VERDICT, MODEL_READY=YES). Proceeding to DCF.

Then continue to **ROUTE** below. Substitute SOURCE as `context` or `reports/TICKER_YYYYMMDD.json`, VERDICT from upstream, and TICKER throughout.

**`CONDITIONAL` — without `--confirm`:** Halt. Emit:

> Model is CONDITIONAL on Signal — confirm: `<condition>`. Re-invoke `/stock:model TICKER --confirm` to proceed.

Surface the `<condition>` string from the upstream Signal **verbatim** (no paraphrasing). Do not proceed.

**`CONDITIONAL` — with `--confirm`:** Treat as YES for routing purposes. Emit:

> Gate passed (confirmed): SIGNAL OUTPUT for TICKER MODEL_READY=CONDITIONAL, user confirmed `<condition>`. Proceeding to DCF.

Then continue to **ROUTE** below.

**`NO`:** Refuse. Emit:

> Signal for TICKER is MODEL_READY=NO — Model will not run. Reason: `<qualitative_note>`. Re-run `/stock:signal TICKER` if conditions have changed.

Surface the `qualitative_note` from the upstream Signal verbatim. Do not proceed; do not call any MCP tool; do not write any file.

**Ticker mismatch** (SIGNAL OUTPUT in context is for a different ticker, AND no same-day JSON for the requested ticker exists) is treated as "no upstream Signal" — use the Step 1 refusal message.

### ROUTE — Branch on `profit_stage`

After the gate passes (`model_ready = YES` or `CONDITIONAL` with `--confirm`):

- **`profit_stage = ESTABLISHED`** → continue to the standard two-stage DCF below (this skill).
- **`profit_stage = EMERGING`** → this path is handled by the pre-profit variant in ABA-34 (revenue-multiple exit + FCF inflection). If reached in v1.2 before ABA-34 lands, refuse with: `EMERGING profile — pre-profit DCF variant (ABA-34) is not yet implemented. /stock:model standard DCF requires ESTABLISHED stage.`

### GATHER — DCF inputs (ESTABLISHED path)

Run these MCP calls in this order. Every retrieved figure is held with its raw value; never round during gather. State which calls succeeded and which fell back before COMPUTE.

1. **`get_ratios(ticker)`** — fields used: `currentPrice`, `marketCap`, `sharesOutstanding` (fallback when diluted shares missing), `eps_ttm`.
2. **`get_financials(ticker)`** — used for:
   - `years[].free_cash_flow` (4y usable per ABA-47 — accept 4y base; 5th column is dropped server-side)
   - `years[].revenue` (for FCF margin derivation)
   - `years[].shares_outstanding_diluted` (latest year — primary shares figure for per-share IV)
   - `years[0].total_debt` and `years[0].cash` (net debt for EV→equity bridge)
3. **`get_estimates(ticker)`** — fields used: `ntm_revenue`, `ntm_eps`. NTM revenue anchors Year-1 FCF projection; NTM EPS is used only for sanity-check.

**Manual Input Protocol (`skills/_shared/MANUAL_INPUT_PROTOCOL.md`) fires when:**

- `currentPrice` is null (cannot compute upside/downside)
- Fewer than 3 historical years of `free_cash_flow` are usable (trailing CAGR cannot be derived)
- `years[0].total_debt`, `years[0].cash`, or `shares_outstanding_diluted` is null
- **Always** for **base WACC** — yfinance does not expose risk-free rate, beta, or capital structure inputs that would let the skill derive WACC honestly. Ask the user once via grouped paste-in: `base WACC %` (single number, e.g. `9.0`). Never default this value.

Any field accepted via paste-in is tagged `source: "user_paste"` and added to `meta.manual_inputs`; overall `meta.confidence` caps at MEDIUM.

### COMPUTE — Two-stage DCF

Execute in order. Show the working — every scenario must be reproducible from the printed assumptions.

**Step 1 — Derive trailing FCF base and margin.**

- `fcf_ttm` = `years[0].free_cash_flow` (latest reported FY; if quarterly TTM is unavailable, accept the latest annual figure).
- `fcf_margin_ttm` = `fcf_ttm / years[0].revenue`.
- `fcf_cagr_3y` = `(years[0].free_cash_flow / years[3].free_cash_flow) ^ (1/3) − 1` when 4y of FCF is available; if only 3y is available use `^(1/2)` with the oldest available year as the base; if only 2y is available, set `fcf_cagr_3y = (latest / prior) − 1` and flag confidence = MEDIUM. State which formulation was used.

**Step 2 — Year-1 FCF anchor under each scenario.**

Year-1 FCF is anchored on NTM consensus, then perturbed per scenario. Compute `fcf_y1_consensus = ntm_revenue × fcf_margin_ttm` as the consensus anchor.

| Scenario | Y1 FCF |
|---|---|
| Bear | `fcf_y1_consensus × 0.85` — revenue miss + 200 bps margin compression |
| Base | `fcf_y1_consensus` — NTM consensus delivers, margin stable |
| Bull | `fcf_y1_consensus × 1.10` — revenue beat + operating leverage |

**Step 3 — Years 2–5 FCF growth per scenario.**

Each scenario uses its own growth axis — **not** a percentage haircut of the base growth rate.

| Scenario | Y2–Y5 CAGR | Narrative |
|---|---|---|
| Bear | `max(fcf_cagr_3y × 0.50, 0.02)` | Secular deceleration; growth halves and floors at GDP |
| Base | `fcf_cagr_3y` | Trailing 3y CAGR persists; consensus extrapolated |
| Bull | `fcf_cagr_3y × 1.20 + 0.02` | Operating leverage extends runway; 200 bps uplift |

Project: `fcf_y_n = fcf_y_(n−1) × (1 + cagr)` for n = 2, 3, 4, 5.

**Step 4 — Terminal value (Gordon Growth) per scenario.**

| Scenario | Terminal growth `g` | WACC | Narrative |
|---|---|---|---|
| Bear | 1.5% | `base_wacc + 1.0pp` | Recession tail; cost of capital widens |
| Base | 2.5% | `base_wacc` | Long-run growth normalises to GDP+; current rates |
| Bull | 3.5% | `base_wacc − 1.0pp` | Above-GDP terminal; rate-easing tailwind |

Terminal value at end of Year 5: `TV = fcf_y5 × (1 + g) / (wacc − g)`. Require `wacc > g` — if violated (sensitivity edge), narrow the WACC adjustment for that scenario and state the override in the output.

**Step 5 — Discount to present.**

For each scenario, the enterprise value is the sum of discounted explicit FCFs and the discounted terminal value:

```
EV = Σ_{n=1..5} fcf_y_n / (1 + wacc)^n  +  TV / (1 + wacc)^5
```

**Step 6 — Equity bridge and per-share intrinsic value.**

- `net_debt = years[0].total_debt − years[0].cash`
- `equity_value = EV − net_debt`
- `shares = years[0].shares_outstanding_diluted` (fallback to `get_ratios.sharesOutstanding` only if the diluted figure is null — note the fallback)
- `intrinsic_value_per_share = equity_value / shares`
- `upside_pct = (intrinsic_value_per_share / currentPrice − 1) × 100`

**Step 7 — Range integrity check.**

Compute all three scenarios. The acceptance contract requires `bear_iv < base_iv < bull_iv`. If the inequality fails, the assumption sets have collided — stop, print the three scenario inputs and outputs, and ask the user to widen the WACC or growth deltas. Never silently re-order or hand-tune. (This is the "demonstrably different assumption sets" guardrail in executable form.)

**Step 8 — Sensitivity note.**

Vary one assumption at a time around the base scenario and observe which produces the largest swing in base IV:

- WACC ± 100 bps
- Terminal growth ± 100 bps
- Y2–Y5 CAGR ± 300 bps

Report the dominant driver as a one-line note (e.g. `Sensitivity: WACC dominates — ±100 bps WACC moves base IV by ±18%`). The numbers shown are the percentage change in base IV, not raw IVs.

### THRESHOLD — Range vs price

After IVs are computed, classify where `currentPrice` sits in the bear–bull range:

| Position | Label | Interpretation |
|---|---|---|
| `currentPrice < bear_iv` | **MARGIN OF SAFETY** | Even the bear case clears the current price — implied undervaluation. |
| `bear_iv ≤ currentPrice ≤ base_iv` | **WITHIN BEAR–BASE** | Trading in the lower half of the modelled range. |
| `base_iv < currentPrice ≤ bull_iv` | **WITHIN BASE–BULL** | Trading in the upper half; bull-case assumptions implied. |
| `currentPrice > bull_iv` | **PRICE EXCEEDS RANGE** | Even the bull case does not justify the price — implied overvaluation. |

This is a descriptive label, not a buy/sell instruction. The Signal verdict is the buy/sell call; Model reports where price sits in the modelled value range.

### OUTPUT — MODEL OUTPUT block + JSON merge

Emit the MODEL OUTPUT block. All fields must appear every run; never omit.

```
MODEL OUTPUT
  Ticker:          [TICKER]
  Method:          Two-stage DCF (5y explicit + Gordon terminal)
  Profit stage:    ESTABLISHED
  Upstream:        SIGNAL OUTPUT (source=context|reports/TICKER_YYYYMMDD.json, verdict=..., MODEL_READY=...)

  Current price:   $X.XX
  Shares (dil.):   XXX.X M (source: get_financials.years[0].shares_outstanding_diluted | get_ratios.sharesOutstanding fallback)
  Net debt:        $X.X B (total_debt $X.X B − cash $X.X B, FY ending YYYY-MM-DD)
  FCF (TTM):       $X.X B  |  margin: XX%  |  3y CAGR: XX%
  NTM revenue:     $X.X B (consensus, n=N analysts)
  Base WACC:       X.X% (source: user_paste)

  Bear: $X.XX / share — [N]% [up|down]side
    Y1 FCF: $X.XB (NTM × 0.85)  |  Y2-5 CAGR: X%  |  g: 1.5%  |  WACC: X%
    Narrative: revenue miss, decelerating growth, tighter cost of capital

  Base: $X.XX / share — [N]% [up|down]side
    Y1 FCF: $X.XB (NTM consensus)  |  Y2-5 CAGR: X%  |  g: 2.5%  |  WACC: X%
    Narrative: consensus delivers, growth normalises to GDP+

  Bull: $X.XX / share — [N]% [up|down]side
    Y1 FCF: $X.XB (NTM × 1.10)  |  Y2-5 CAGR: X%  |  g: 3.5%  |  WACC: X%
    Narrative: revenue beat, operating leverage, rate-easing tailwind

  Range vs price: [MARGIN OF SAFETY | WITHIN BEAR–BASE | WITHIN BASE–BULL | PRICE EXCEEDS RANGE]
  Sensitivity:    [one-line dominant-driver note]
```

**JSON merge into `reports/TICKER_YYYYMMDD.json` under `stages.model`:**

Run `mkdir -p reports` and read-modify-write the existing file (it already contains `stages.signal` and may contain `stages.screen`). Do not overwrite other stages.

```json
"model": {
  "method": "two-stage DCF",
  "profit_stage": "ESTABLISHED",
  "current_price": <number>,
  "shares_diluted": <number>,
  "net_debt": <number>,
  "fcf_ttm": <number>,
  "fcf_margin_ttm": <number>,
  "fcf_cagr_3y": <number>,
  "ntm_revenue": <number>,
  "base_wacc": <number>,
  "scenarios": {
    "bear": {
      "y1_fcf": <number>, "y2_5_cagr": <number>, "terminal_growth": 0.015, "wacc": <number>,
      "intrinsic_value_per_share": <number>, "upside_pct": <number>,
      "narrative": "revenue miss, decelerating growth, tighter cost of capital"
    },
    "base": { /* same shape */ },
    "bull": { /* same shape */ }
  },
  "range_vs_price": "MARGIN OF SAFETY | WITHIN BEAR-BASE | WITHIN BASE-BULL | PRICE EXCEEDS RANGE",
  "sensitivity": {
    "dominant_driver": "WACC | terminal_growth | y2_5_cagr",
    "note": "WACC dominates — ±100 bps WACC moves base IV by ±18%"
  }
}
```

After writing, print:

```
Wrote: reports/META_20260513.json  ← stages.model
META — DCF bear/base/bull = $X / $Y / $Z (price $P, WITHIN BEAR–BASE)
```

**Confidence rules (`meta.confidence`):**

- HIGH: 4y of FCF history, no manual inputs other than base WACC, scenario range check passed first time.
- MEDIUM: 2–3y of FCF history, or any of net_debt / shares paste-in fired, or range integrity check required user re-input.
- LOW: <2y FCF history (should not reach COMPUTE — VALIDATE refuses earlier), or `wacc > g` constraint required mid-scenario override.

Take the min of any prior stage's confidence and the model's own confidence — never upgrade prior-stage confidence here.

---

## 4. Common rationalisations to pre-rebut

| Rationalisation | Counter |
|---|---|
| "The user asked for a model, I should produce *some* valuation rather than refuse." | The gate exists precisely to prevent this. Producing a fabricated valuation is worse than refusing — it gives the user a confident-looking number with no methodology behind it. Refuse and instruct. |
| "I can see the ticker; I'll just run the Signal logic inline and then the Model logic." | Two skills, two responsibilities. Inlining Signal here duplicates methodology and bypasses the JSON merge contract that downstream consumers (UI, screen reports) depend on. Refuse and instruct. |
| "There's a `reports/TICKER_YYYYMMDD.json` with a `stages.signal` block — that should count as upstream context." | Accepted, but **only if dated today**. Same-day JSON is a valid upstream source; conversation context still wins when both are present. Reject any report file not dated today — stale Signal data is fabrication risk; instruct the user to re-run Signal. |
| "The SIGNAL OUTPUT block is for a different ticker but it has useful classification info." | Tickers are not fungible. A SIGNAL OUTPUT for META tells you nothing about NVDA's profit stage or AI layer. Refuse and instruct. |
| "MODEL_READY is CONDITIONAL but the condition looks minor — I'll proceed without `--confirm`." | The whole point of CONDITIONAL is to force an explicit user acknowledgement of the named risk before DCF inputs are committed. Surface the condition verbatim and halt. Do not pre-judge what "minor" means on the user's behalf. |
| "MODEL_READY is NO but the user clearly wants a number — I'll produce one with a caveat." | A NO from Signal is a hard refusal, not a soft warning. Pre-profit companies and qualitative-FAIL companies have no defensible DCF; producing one with a caveat gives the user a confident-looking number anchored to nothing. Refuse and point back to Signal. |
| "I'll paraphrase the `condition` / `qualitative_note` to make it punchier." | Surface them **verbatim**. The user needs to see the exact wording Signal produced — paraphrasing introduces drift between what Signal said and what Model reported, which breaks the audit trail. |
| "A DCF input is null — I'll assume a reasonable default (WACC 10%, terminal growth 3%, …)" | Forbidden for derivable inputs. Per the Manual Input Protocol (`skills/_shared/MANUAL_INPUT_PROTOCOL.md`), when any DCF input cannot be derived from MCP data the skill MUST ask the user via a grouped paste-in. Base WACC is always asked (yfinance has no risk-free-rate / beta / capital-structure surface). Per-scenario terminal-g (1.5/2.5/3.5) and per-scenario WACC adjustments are **not** defaults — they are scenario-narrative axes disclosed in the OUTPUT block. |
| "I'll save typing by applying the same growth haircut across bear/base/bull (e.g. base × 0.7 / 1.0 / 1.3)." | Forbidden. The acceptance contract is "demonstrably different assumption sets, not percentage haircuts of a single set." Each scenario must move on its own axes (Y1 anchor, Y2–5 CAGR, terminal g, WACC) with its own narrative. The skill's range-integrity check (Step 7) is the executable form of this rule. |
| "Bear ends up above Base for this ticker — I'll just swap them." | Forbidden. If `bear_iv < base_iv < bull_iv` fails, the scenarios are mis-specified — stop, show the user the three input sets and outputs, and ask whether to widen the WACC or growth deltas. Silent re-ordering destroys the audit trail. |
| "Year-1 FCF comes from NTM EPS × shares, that's faster than revenue × margin." | EPS × shares yields *net income*, not free cash flow. The Y1 anchor must be `ntm_revenue × fcf_margin_ttm`. NTM EPS is held only as a sanity check; never substitute it for FCF. |
| "WACC > g failed in the bull scenario; I'll just use g = WACC − 0.001 to keep the formula valid." | Forbidden. If `wacc ≤ g`, narrow the WACC adjustment (e.g. reduce the bull WACC discount from −1.0 pp to −0.5 pp) and **state the override in the OUTPUT block** so the user can see why bull discount narrowed. Numerical tricks that hide a broken scenario from the reader are exactly what the rationalisations table exists to prevent. |
| "The user just wants a number — I'll skip the sensitivity note." | The sensitivity note is required output. It tells the user which assumption their valuation is most fragile to; omitting it gives a confident-looking point estimate with no fragility disclosure. |
| "Net debt is negative (net cash) so I'll set it to zero." | Forbidden. Net debt of −X means equity = EV + X; keep the sign. Net-cash tech companies are common and the equity bridge must reflect it. |

---

## 5. Acceptance criteria

### v1 — ABA-30 (still in force)

1. **No upstream Signal in context or on disk →** invoking `/stock:model NVDA` returns a refusal message containing the literal phrase **`run /stock:signal NVDA first`** (with the requested ticker substituted).
2. **Valid SIGNAL OUTPUT block in context for the requested ticker (MODEL_READY=YES) →** invoking `/stock:model NVDA` proceeds past the gate and emits the "Gate passed" acknowledgement, naming the verdict and MODEL_READY value from the upstream block.
3. **Mismatched ticker** (SIGNAL OUTPUT for META, request for NVDA, no same-day NVDA report on disk) → treated as "no upstream Signal" — same refusal message, substituting the requested ticker (NVDA).

### v1.1 — ABA-93 (MODEL_READY branching)

4. **Filesystem fallback — same-day `reports/TICKER_YYYYMMDD.json` exists, no in-context block →** the gate reads `stages.signal.model_ready` from the JSON and branches accordingly.
5. **Stale on-disk Signal** (date in filename is not today) → ignored; treated as if no upstream Signal exists; standard refusal.
6. **`model_ready = YES` →** gate passes; "Ready for DCF" acknowledgement emitted; DCF body still stubbed.
7. **`model_ready = CONDITIONAL`, no `--confirm` flag →** gate halts with: `Model is CONDITIONAL on Signal — confirm: <condition>. Re-invoke /stock:model TICKER --confirm to proceed.` The `<condition>` string appears verbatim from the upstream Signal.
8. **`model_ready = CONDITIONAL`, `--confirm` passed →** gate passes (treated as YES); acknowledgement notes the confirmation and surfaces the confirmed condition.
9. **`model_ready = NO` →** gate refuses with: `Signal for TICKER is MODEL_READY=NO — Model will not run. Reason: <qualitative_note>. Re-run /stock:signal TICKER if conditions have changed.` The `<qualitative_note>` string appears verbatim.
10. **Context precedence:** when both an in-context SIGNAL OUTPUT and a same-day JSON exist for the same ticker, the in-context block is the source of truth.

### v1.2 — ABA-31 (standard two-stage DCF, ESTABLISHED path)

11. **ESTABLISHED + MODEL_READY=YES →** invoking `/stock:model META` after a META Signal output produces a MODEL OUTPUT block with three intrinsic-value scenarios and writes `stages.model` into `reports/META_YYYYMMDD.json` (merging with existing `stages.signal` / `stages.screen` — no overwrite).
12. **Bear < Base < Bull (range integrity) →** the three scenarios satisfy `bear_iv < base_iv < bull_iv`. If the inequality fails, the skill stops and surfaces the three scenario inputs/outputs without silently re-ordering.
13. **Demonstrably different assumption sets →** each scenario's Y1 anchor, Y2–5 CAGR, terminal growth, and WACC are each set by an independent axis (not a single percentage haircut applied to a base case). Each scenario carries its own one-line narrative.
14. **EMERGING + MODEL_READY=YES (edge case) →** the route step refuses with the ABA-34 message; no DCF math is run, no `stages.model` is written.
15. **Base WACC always asked →** the Manual Input Protocol fires for base WACC on every ESTABLISHED run; the value is recorded in `meta.manual_inputs` and the confidence caps at MEDIUM.
16. **Sensitivity note present →** the OUTPUT block names exactly one dominant driver (WACC / terminal growth / Y2–5 CAGR) with a one-line magnitude statement.
17. **`wacc ≤ g` override is disclosed →** if a scenario required narrowing the WACC adjustment to keep `wacc > g`, the OUTPUT block states the override explicitly; the user never sees a silently re-tuned scenario.

EMERGING-path math (revenue-multiple exit + FCF inflection) is tracked in ABA-34.
