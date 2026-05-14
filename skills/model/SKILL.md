---
name: stock:model
description: DCF/valuation model for a tech stock. Invoked as `/stock:model TICKER [--confirm] [--pre-profit]`. Reads MODEL_READY from the upstream `/stock:signal` (conversation context preferred, same-day `reports/TICKER_YYYYMMDD.json` fallback) and branches: YES → run DCF and emit a bear/base/bull intrinsic-value range; CONDITIONAL → halt and surface `condition` (or proceed when `--confirm` is passed); NO → refuse and surface `qualitative_note`. ESTABLISHED profile uses two-stage DCF (5y FCF + Gordon terminal). EMERGING profile (or any ticker invoked with `--pre-profit`) uses revenue-multiple exit + FCF inflection + SBC dilution schedule. Use whenever the user asks for an intrinsic value, fair-value range, DCF, or "what's it worth" on a ticker.
---

# Model — DCF & Intrinsic Value

**Command:** `/stock:model TICKER [--confirm] [--pre-profit]`
**Purpose:** Run a DCF for a tech stock and emit a bear/base/bull intrinsic-value range, after enforcing the upstream-context contract from `/stock:signal`. ESTABLISHED → two-stage DCF (5y FCF + Gordon terminal). EMERGING (or any ticker forced with `--pre-profit`) → revenue-multiple exit + FCF inflection year + SBC dilution schedule.

---

## 1. Identity

- **Skill name:** stock:model
- **Command:** `/stock:model TICKER [--confirm] [--pre-profit]`
- **Purpose:** Gate on the upstream Signal, then compute a DCF under three demonstrably-different scenario sets. ESTABLISHED profile → two-stage DCF (5y explicit FCF + Gordon terminal). EMERGING profile (or any ticker forced with `--pre-profit`) → revenue-multiple exit + FCF inflection + SBC dilution. Output a per-share intrinsic-value range (bear/base/bull) with each scenario's assumptions and narrative fully disclosed, and merge into `reports/TICKER_YYYYMMDD.json` under `stages.model`.

---

## 2. Why a context gate

Model is downstream of Signal: it consumes the profit-stage classification, clean EPS, AI layer, and MODEL_READY flag that Signal produces. Running `/stock:model` without first running `/stock:signal` would force this skill to either re-derive those inputs (duplicating Signal's MCP calls and methodology) or fabricate them (silently wrong). The gate enforces the contract — Signal first, Model second.

The gate also routes on `model_ready`. Signal's classification is the authoritative call on whether a DCF is sensible right now:

- `YES` — proceed past the gate; downstream DCF logic runs.
- `CONDITIONAL` — a specific user-confirmable risk exists. Halt and surface the `condition` string; require `--confirm` on re-invocation before continuing.
- `NO` — Signal has already ruled the DCF out (pre-profit, qualitative FAIL, or hard CAUTION). Refuse and point back to Signal.

v1.2 (ABA-31) lands the standard two-stage DCF for ESTABLISHED profile. v1.3 (ABA-34) lands the pre-profit variant — revenue-multiple exit, explicit FCF inflection year per scenario, and SBC-driven dilution schedule. The `--pre-profit` flag forces the pre-profit variant even on an ESTABLISHED upstream classification (useful for transition-year tickers like RDDT whose recent profitability does not yet support a stable terminal-value calculation).

---

## 3. Execution Phases

### GATHER

1. Parse the ticker from the command argument. Uppercase it (e.g. `nvda` → `NVDA`). If blank, refuse immediately with: "Usage: `/stock:model TICKER [--confirm] [--pre-profit]`".
2. Parse the optional `--confirm` flag. Its only effect is to allow a CONDITIONAL Signal to pass through (see GATE step 3 below).
3. Parse the optional `--pre-profit` flag. Its effect is to force the pre-profit variant in ROUTE regardless of the upstream `profit_stage`. Accepted spellings: `--pre-profit`, `-- pre-profit` (separator tolerant). When set, record `route_override = "pre-profit"` for the OUTPUT block.
4. Parse the optional `--engagement-modifier` flag. **Default: off.** When absent, the engagement-modifier GATHER sub-step is skipped entirely and the `engagement_modifier` JSON block is omitted (FR6 / spike-decision: advisory + flag-gated default-off until n≥24 forward samples accumulate; see `docs/design-docs/engagement-kpi-enrichment/spike-decision.md`). When present, the sub-step runs per the rules in **GATHER — Engagement modifier** below (ESTABLISHED path only — EMERGING path always skips per FR6). Accepted spellings: `--engagement-modifier`, `-- engagement-modifier` (separator tolerant).

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

### ROUTE — Branch on `profit_stage` (with `--pre-profit` override)

After the gate passes (`model_ready = YES` or `CONDITIONAL` with `--confirm`), pick a variant:

| `profit_stage` | `--pre-profit` flag | Variant |
|---|---|---|
| ESTABLISHED | absent | **Standard two-stage DCF** (GATHER → COMPUTE — ESTABLISHED below) |
| ESTABLISHED | present | **Pre-profit variant** (GATHER → COMPUTE — EMERGING below). Emit: `Forcing pre-profit variant on ESTABLISHED ticker — terminal-value DCF skipped, revenue-multiple exit + FCF inflection used instead.` |
| EMERGING | absent or present | **Pre-profit variant** (GATHER → COMPUTE — EMERGING below) |

The `--pre-profit` override exists for transition-year companies (e.g. RDDT, recently profitable) where the trailing-FCF base is too thin for stable Gordon-growth terminal math, but where revenue trajectory + comp multiples + dilution schedule still produce a defensible range.

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

### GATHER — Engagement modifier (ESTABLISHED path, opt-in)

**Runs only when `--engagement-modifier` was passed.** When the flag is absent, skip this entire sub-section and proceed directly to COMPUTE; the `engagement_modifier` JSON block is omitted from output and no OUTPUT line is emitted.

When the flag is present, execute the steps below. Every terminal state writes a `stages.model.engagement_modifier` block per the JSON contract in OUTPUT below — `status ∈ {applied, unavailable, no_kpi_mapping, user_skipped}`. Non-applied states must populate `status_reason` from the enum `{missing_ai_layer, no_recent_print, source_unreachable, extraction_failed, non_interactive}` (FR5, NFR3).

**Step 1 — AI-layer gate (FR1).**

Read `upstream_signal.ai_layer` (from the SIGNAL OUTPUT block resolved in GATE, or `stages.signal.ai_layer` in the on-disk fallback).

- `ai_layer ∈ {APPLICATION, INCUMBENT}` → continue to Step 2.
- `ai_layer ∈ {INFRASTRUCTURE, FOUNDATION, NONE}` → emit `status: "unavailable", status_reason: "missing_ai_layer"` (ai_layer doesn't qualify, not strictly missing — but the enum's `missing_ai_layer` covers both "absent" and "present-but-non-qualifying" per spike-decision linkage; the audit trail records the actual value in `ai_layer_observed`). Skip to COMPUTE.
- `ai_layer` absent (upstream Signal predates AI-layer field) → emit `status: "unavailable", status_reason: "missing_ai_layer"`, with `ai_layer_observed: null`. Skip to COMPUTE. **Do not second-guess the upstream classification — re-run `/stock:signal` if the user believes it's wrong.**

**Step 2 — KPI-map lookup (FR7).**

Read `skills/_shared/engagement_kpi_map.json`. Record `kpi_map_schema_version` from the top-level field for the audit trail (Task 8 ADR D5).

- Ticker is in `tickers` → take the `primary_kpi` (and `evidence.exhibit_url` as a starting hint) and continue to Step 3.
- Ticker is in `excluded_tickers` → emit `status: "no_kpi_mapping"`, with `excluded_reason` copied from the map's `reason` field. Skip to COMPUTE.
- Ticker is absent from both → emit `status: "no_kpi_mapping"`, `status_reason: null` (the enum doesn't cover "ticker not mapped" because that's a `status`, not a reason). Skip to COMPUTE.

**Step 3 — Locate the latest 8-K Ex 99.1 (FR8 source resolution order).**

1. Try EDGAR MCP `get_8k_exhibit(ticker, latest=true)` if the server is reachable. Returns the Exhibit 99.1 content + filing date + accession.
2. Fallback: direct EDGAR HTTP. Resolve the latest 8-K via the submissions API (`https://data.sec.gov/submissions/CIK<10digit>.json`), traverse `recent.accessionNumber` + `recent.primaryDocument` to find the Ex 99.1 URL. SEC requires a custom User-Agent header (`Stock Review Skill-Pack <email>`); use it on every request.
3. If both the EDGAR MCP and the direct HTTP path fail (network error, 5xx persisting past one retry with 2 s backoff per design doc §316) → emit `status: "unavailable", status_reason: "source_unreachable"`. Skip to COMPUTE.
4. If the latest 8-K is older than 90 days (mid-quarter run between earnings) → fall through to `WebSearch` for the most recent earnings press release. Mark the audit trail with `source_type: "websearch_fallback"`. If the WebSearch returns no plausible recent release → `status: "unavailable", status_reason: "no_recent_print"`.

**Step 4 — Extract the KPI value and YoY.**

Use the `primary_kpi.source_phrase` from the map as the regex anchor. Pull the latest-period value AND the YoY-prior-period value from the Ex 99.1 document (most press releases disclose both in the same sentence: *"DAP increased 6% year over year to 3.43 billion"*). Compute `yoy_change = (current / prior_year) - 1` from the two raw numbers — do not trust a stated "%" without numerical cross-check.

If extraction fails (regex doesn't match, or numbers are non-numeric, or YoY can't be derived) → emit `status: "unavailable", status_reason: "extraction_failed"`. Skip to COMPUTE.

**Step 5 — Classify direction × magnitude per pre-registered constants** (ADR `engagement-modifier-constants.md`, C1/C2):

- `abs(yoy_change) < 0.02` → `direction = 0`, `magnitude = "neutral"`. The modifier is a no-op (`base_anchor_multiplier = 1.00`). Status is still `applied` — the audit trail records that the modifier ran and concluded "no signal."
- `abs(yoy_change) >= 0.02 AND abs(yoy_change) < 0.08` → `direction = sign(yoy_change)`, `magnitude = "mild"`.
- `abs(yoy_change) >= 0.08` → `direction = sign(yoy_change)`, `magnitude = "strong"`.

**Step 5b — Revision-direction agreement guardrail** (spike-decision §"Lead vs confirm").

Fetch Yahoo Finance's live `/analysis/` page to read the trailing 30-day EPS revision direction. The modifier is reframed as a **confirmer** (not a predictor): when engagement direction agrees with the post-print revision direction the market has already begun to record, the modifier applies; when they strictly disagree, the modifier suppresses to neutral.

1. **Fetch.** `WebFetch https://finance.yahoo.com/quote/<TICKER>/analysis/`. One retry with 2 s backoff on transient 5xx / network error (mirrors design-doc §316).

2. **Extract EPS Trend.** Locate the "EPS Trend" table. Read the **Next Year** column's "Current Estimate" and "30 Days Ago" rows. Compute `revision_pct = (current - thirty_days_ago) / thirty_days_ago`. Direction: `+1` if `revision_pct > 0`, `-1` if `< 0`, `0` if exactly zero.

3. **Fetch / parse failure** (HTTP error after retry, page DOM changed, regex miss, non-numeric values) → set `revision: {metric: "eps_ntm_30d", revision_pct: null, direction: null, source_url: "<attempted URL>"}` and `agreement: null`. Apply the modifier per C3/C4 unchanged — this is the legacy "revision-data unavailable" fall-through. Proceed to Step 6.

4. **Compute agreement.** `agreement = (revision.direction == direction) OR (revision.direction == 0) OR (direction == 0)`. A neutral side (KPI deadband or zero revision) is treated as compatible — there's no signal to disagree with.

5. **`agreement == false` (strict disagreement).** Emit `status: "direction_disagreement"`, `base_anchor_multiplier = 1.00`, `clamped_from = null`, `user_confirmed: false`. Populate the audit trail fully (kpi block, revision block, `agreement: false`). **Skip Step 6 (MIP)** — there is no modifier to confirm. Proceed to COMPUTE; the base scenario is unperturbed (Step 2b becomes a no-op; Step 6b does not run).

6. **`agreement == true`** (or revision unavailable per case 3) → preserve `base_anchor_multiplier` from Step 5 and continue to Step 6 (MIP).

7. **Forward-log emission (Task 10b).** Whether the modifier applies, suppresses, or falls through, append one line to `tests/fixtures/engagement_kpi/forward_log.jsonl` (create the file with mode 0644 if absent):

   ```jsonl
   {"ticker": "<T>", "period": "<Q1 2026>", "engagement_direction": -1|0|1, "revision_direction_30d": -1|0|1|null, "agreement": true|false|null, "run_ts": "<ISO8601 UTC>"}
   ```

   Append-only. Never edited, rotated, or culled. This is the dataset NFR7 (≥60% direction agreement on n≥24) is evaluated against once enough forward samples accumulate. Per spike-decision §"NFR7 — deferred, not deleted", the log records the pre-suppression decision too — `engagement_direction` is the Step-5 KPI direction, not the post-guardrail multiplier sign — so the accumulated dataset preserves the engagement-only direction-agreement evidence for the eventual NFR7 evaluation. Emission failures (disk full, permission denied) **never** block the model run — log a warning and proceed; the forward log is telemetry, not a contract artefact.

**Step 6 — Manual Input Protocol confirmation (FR2, NFR5).**

Skip this step entirely when Step 5b emitted `status: "direction_disagreement"` (modifier already suppressed).

Present the extracted values to the user via the grouped paste-in pattern:

```
ENGAGEMENT MODIFIER — confirm before applying:
  Ticker:        META
  KPI:           DAP (Family Daily Active People)
  Latest period: Q1 2026 (filed 2026-04-29, accession 0001628280-26-028364)
  Value:         3.43 billion (prior-year period: 3.23 billion)
  YoY change:    +6.2%
  Direction:     +1 (positive)
  Magnitude:     mild (|YoY| in [2%, 8%))
  Source:        https://www.sec.gov/Archives/edgar/data/1326801/...
  Will apply:    base_anchor_multiplier = 1.02 (+2% on Y1 base anchor, base scenario only)

Confirm? (y / n / paste a corrected value)
```

- User confirms (`y`) → `user_confirmed: true`, proceed to COMPUTE with the applied multiplier.
- User skips (`n`) → emit `status: "user_skipped", status_reason: null`. Skip to COMPUTE.
- User pastes a correction (e.g. `kpi_value=3.41, yoy_change=0.054`) → re-run Step 5 with the corrected values, then loop back to Step 6 once. A second correction is treated as `user_skipped` to avoid an infinite confirmation loop.

**Non-interactive runs** (e.g. CI / batch mode where stdin is closed): the MIP gate cannot be satisfied. Emit `status: "user_skipped", status_reason: "non_interactive"`. Skip to COMPUTE. Per design-doc §309 this is the correct behaviour — silent application without user confirmation violates FR2.

**Confidence cap (NFR5).** Any run that emits `status: "applied"` caps `meta.confidence` at MEDIUM (LLM-extracted-and-user-confirmed is not a structured-data source). Do not raise prior-stage confidence; the modifier cap is one-way.

**Step 7 — Hand off to COMPUTE.**

When `status = "applied"`, COMPUTE Step 2 (Year-1 FCF anchor) uses `base_anchor_multiplier` from this sub-section on the **base** scenario only. The output cap (Step 6b in COMPUTE) may further clamp the multiplier; `clamped_from` records the pre-clamp value. When `status ∈ {unavailable, no_kpi_mapping, user_skipped, direction_disagreement}`, `base_anchor_multiplier = 1.00` and COMPUTE Step 2b is a no-op.

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
| Base | `fcf_y1_consensus × base_anchor_multiplier` — NTM consensus, perturbed by the engagement modifier (see Step 2b) |
| Bull | `fcf_y1_consensus × 1.10` — revenue beat + operating leverage |

**Step 2b — Engagement modifier on base scenario (FR3/FR4, C3/C4/C5).**

When the engagement-modifier GATHER sub-step emitted `status: "applied"`, the base scenario's Y1 FCF anchor is perturbed by `base_anchor_multiplier ∈ [0.96, 1.04]` from that sub-step. When `status ∈ {unavailable, no_kpi_mapping, user_skipped, direction_disagreement}` OR when the `--engagement-modifier` flag was absent, `base_anchor_multiplier = 1.00` and this step is a no-op (the base scenario's Y1 anchor equals `fcf_y1_consensus` unchanged).

Bear and bull are **never** modifier-perturbed — scenario-axis independence (C5) and the range-integrity invariant `bear_iv < base_iv < bull_iv` both depend on the modifier touching base alone.

**Output cap (C4 / FR4b / NFR4 — applied AFTER Step 6 produces base IV.)** Per the ADR, the modifier's effect on the base scenario's per-share intrinsic value is additionally capped at ≤5%. This cap is evaluated post-COMPUTE in **Step 6b** below (after the equity bridge produces `intrinsic_value_per_share`), because the input multiplier alone cannot predict the IV impact — DCF leverage means a 4% Y1 nudge can translate to anywhere from 2% to 9% on per-share IV depending on the WACC / terminal-growth regime.

**Revision-direction agreement guardrail** (spike-decision §"Lead vs confirm", wired in GATHER Step 5b). When engagement direction and the trailing 30-day EPS revision direction strictly disagree, GATHER emits `status: "direction_disagreement"` with `base_anchor_multiplier = 1.00`, and this step is a no-op. When they agree (or revision data is unavailable — legacy fall-through), the modifier applies per C3/C4 and the audit trail records `agreement: true | null` respectively.

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

**Step 6b — Engagement modifier output-cap clamp (FR4b / NFR4).**

Runs only when the engagement modifier emitted `status: "applied"` AND `base_anchor_multiplier ≠ 1.00`. When the modifier was a no-op (deadband / not applied), skip this step.

1. Recompute the **base scenario only** with `base_anchor_multiplier = 1.00` (i.e. unperturbed `fcf_y1_consensus`) using Steps 2–6 with all other inputs held constant. Call the result `base_iv_unmodified`.
2. Compute `iv_impact_pct = abs(scenarios.base.intrinsic_value_per_share / base_iv_unmodified − 1)`.
3. If `iv_impact_pct ≤ 0.05` → cap holds, no clamp needed. Record `engagement_modifier.clamped_from = null` in the JSON.
4. If `iv_impact_pct > 0.05` → bisect on `base_anchor_multiplier` between `1.00` and the original applied multiplier to find the largest multiplier such that `iv_impact_pct ≤ 0.05`. Apply that clamped multiplier and re-run Steps 2–6 for the base scenario. Record `engagement_modifier.clamped_from = <original_multiplier>` (the pre-clamp value) and set `engagement_modifier.base_anchor_multiplier = <clamped_value>` in the JSON. Bear and bull are not recomputed (they were never modifier-perturbed).

Bisection tolerance: 0.001 on the multiplier or 0.001 on `iv_impact_pct`, whichever is reached first. Three iterations is usually sufficient.

The cap defends against DCF-leverage edge cases where a 4% Y1 anchor nudge translates to a >5% per-share IV swing — input bound (C3) and output bound (C4) work in concert, neither alone is sufficient (ADR §C3/C4 alternative-considered).

**Step 7 — Range integrity check.**

Compute all three scenarios. The acceptance contract requires `bear_iv < base_iv < bull_iv`. If the inequality fails, the assumption sets have collided — stop, print the three scenario inputs and outputs, and ask the user to widen the WACC or growth deltas. Never silently re-order or hand-tune. (This is the "demonstrably different assumption sets" guardrail in executable form.)

The engagement modifier (Step 6b) can narrow the bear–base gap (negative direction) or widen the base–bull gap (positive direction). It cannot, by construction, invert the ordering: the input cap C3 is ±4% on Y1 anchor and the output cap C4 is ≤5% on base IV; bear and bull are unperturbed; the smallest gaps in the seed set are wider than 5%. If a future ticker has tighter scenarios and the modifier *does* threaten inversion, Step 7's existing refusal path catches it — the user widens scenario deltas or disables the modifier with `--engagement-modifier` absent.

**Step 8 — Sensitivity note (dominant driver).**

Vary one assumption at a time around the base scenario and observe which produces the largest swing in base IV:

- WACC ± 100 bps
- Terminal growth ± 100 bps
- Y2–Y5 CAGR ± 300 bps

Report the dominant driver as a one-line note (e.g. `Sensitivity: WACC dominates — ±100 bps WACC moves base IV by ±18%`). The numbers shown are the percentage change in base IV, not raw IVs.

**Step 9 — Sensitivity grid (5×5 WACC × terminal growth).**

Produce a 5×5 grid of per-share intrinsic values around the **base** scenario by sweeping WACC and terminal growth jointly. All other base-case inputs (`fcf_y1`, `y2_5_cagr`, `shares`, `net_debt`) are held constant — only WACC and terminal `g` move.

- **WACC axis (rows):** `base_wacc − 1.0pp, −0.5pp, base_wacc, +0.5pp, +1.0pp` — five values, 0.5 pp steps.
- **Terminal-growth axis (columns):** `1.5%, 2.0%, 2.5%, 3.0%, 3.5%` — five values centred on the base scenario's 2.5% g, 0.5 pp steps.

For each `(wacc, g)` cell, repeat COMPUTE Steps 4–6 (terminal value → discount → equity bridge → per-share IV) using the base-scenario explicit FCFs (Y1–Y5 from Step 2 base + Step 3 base CAGR projection). The cell at the middle of both axes — `(row=2, col=2)` in 0-indexed terms (`base_wacc`, `g=2.5%`) — is the **base cell** and must equal `scenarios.base.intrinsic_value_per_share` from Step 6 — within $0.50 / share of rounding tolerance. The JSON `base_cell` field uses the same 0-indexed convention: `{"row": 2, "col": 2}`. If the two diverge by more than that, the grid math has drifted from the base scenario math; stop and reconcile before emitting.

**Monotonicity invariant.** The grid must satisfy:

- IV strictly decreases down each column (WACC ↑ → IV ↓), and
- IV strictly increases across each row (g ↑ → IV ↑).

`wacc > g` holds for every cell in this grid by construction (WACC floor 8% with default base_wacc 9%, g ceiling 3.5%) — but if the user-supplied `base_wacc` is < 4.5%, the lowest-WACC / highest-g corner collapses (`wacc ≤ g`). In that case, refuse the grid for that cell with `n/a (wacc ≤ g)` and surface a one-line note `Sensitivity grid: N cell(s) suppressed because wacc ≤ g at low-WACC corner`. Never floor or fudge.

The grid is a complement to the dominant-driver note, not a replacement — both are required output.

### THRESHOLD — Range vs price

After IVs are computed, classify where `currentPrice` sits in the bear–bull range:

| Position | Label | Interpretation |
|---|---|---|
| `currentPrice < bear_iv` | **MARGIN OF SAFETY** | Even the bear case clears the current price — implied undervaluation. |
| `bear_iv ≤ currentPrice ≤ base_iv` | **WITHIN BEAR–BASE** | Trading in the lower half of the modelled range. |
| `base_iv < currentPrice ≤ bull_iv` | **WITHIN BASE–BULL** | Trading in the upper half; bull-case assumptions implied. |
| `currentPrice > bull_iv` | **PRICE EXCEEDS RANGE** | Even the bull case does not justify the price — implied overvaluation. |

This is a descriptive label, not a buy/sell instruction. The Signal verdict is the buy/sell call; Model reports where price sits in the modelled value range.

### POSITION SIZING — Allocation band from Signal verdict × margin of safety

Applies identically to both ESTABLISHED and EMERGING paths. Run after THRESHOLD, before OUTPUT.

**Step 1 — Margin of safety (MoS) %.** `mos_pct = (scenarios.base.intrinsic_value_per_share / current_price − 1) × 100`. Sign matters: positive = upside to base IV; negative = price already exceeds base IV.

**Step 2 — Look up the allocation band.** Cross signal verdict against `range_vs_price` (the THRESHOLD label, which already integrates where price sits in the bear–bull range — a richer signal than MoS alone):

| Signal verdict ↓ / Range vs price → | MARGIN OF SAFETY | WITHIN BEAR–BASE | WITHIN BASE–BULL | PRICE EXCEEDS RANGE |
|---|---|---|---|---|
| **BUY**     | 4–6% | 3–4% | 2–3% | 0–1% |
| **WATCH**   | 3–4% | 2–3% | 1–2% | 0%   |
| **CAUTION** | 0–1% | 0%   | 0%   | 0%   |

The bands are deliberately conservative for a single-name tech book — bear conviction plus a price already through the bull case is a fully-priced thesis, not a position. CAUTION × MARGIN OF SAFETY is *not* unlocked by cheapness; CAUTION means a qualitative or governance concern that price doesn't fix.

**Step 3 — Confidence cap.** Cap the *upper* band by `meta.confidence`:

- HIGH → no cap (use band as-is).
- MEDIUM → upper bound capped at `min(upper, 4%)`. Lower bound unchanged.
- LOW → upper bound capped at `min(upper, 2%)`. Lower bound unchanged. If the table band starts at 0%, leave at 0%.

The pre-profit variant always caps at MEDIUM (per Confidence rules), so any pre-profit position is `≤ 4%` regardless of MoS.

**Step 4 — Emit the band string.** Format: `"L–U% of portfolio"` (en-dash, no space around digits) where L and U are the (possibly capped) lower and upper bounds. If L = U = 0, emit `"0% of portfolio (no entry)"`.

**Step 5 — Rationale string.** One line referencing all three load-bearing inputs: signal verdict, range_vs_price (with current_price and base_iv), and the resulting band. If a confidence cap fired, name it. Examples:

- `"BUY × WITHIN BEAR–BASE (price $603.00 vs base IV $1050.50, MoS +74.2%) → 3–4% band (HIGH confidence, no cap applied)."`
- `"BUY × MARGIN OF SAFETY (price $42.00 vs base IV $98.00, MoS +133%) → 4–4% band (capped from 4–6% by MEDIUM confidence)."`
- `"WATCH × PRICE EXCEEDS RANGE (price $137.20 vs bull IV $98.00, MoS −60.5%) → 0% of portfolio (no entry)."`

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
    Y1 FCF: $X.XB (NTM consensus × base_anchor_multiplier)  |  Y2-5 CAGR: X%  |  g: 2.5%  |  WACC: X%
    Narrative: consensus delivers, growth normalises to GDP+
    Engagement modifier (base only): [KPI_NAME] [+/-X.X]% YoY ([PERIOD]) → [+/-X]% anchor uplift ([mild|strong] [positive|negative], [user-confirmed|user-skipped|...])
      Source: [URL]
    (Emitted only when `--engagement-modifier` was passed AND `engagement_modifier.status == "applied"`. Other statuses replace with a single line: `Engagement modifier: <status> (<status_reason>)`. Flag absent → line omitted entirely.)

  Bull: $X.XX / share — [N]% [up|down]side
    Y1 FCF: $X.XB (NTM × 1.10)  |  Y2-5 CAGR: X%  |  g: 3.5%  |  WACC: X%
    Narrative: revenue beat, operating leverage, rate-easing tailwind

  Range vs price: [MARGIN OF SAFETY | WITHIN BEAR–BASE | WITHIN BASE–BULL | PRICE EXCEEDS RANGE]
  Sensitivity:    [one-line dominant-driver note]

  Sensitivity grid (base IV, $/share — WACC rows × terminal g columns):
                   g=1.5%    g=2.0%    g=2.5%    g=3.0%    g=3.5%
    WACC=X.X%    $XXXX.X   $XXXX.X   $XXXX.X   $XXXX.X   $XXXX.X
    WACC=X.X%    $XXXX.X   $XXXX.X   $XXXX.X   $XXXX.X   $XXXX.X
    WACC=X.X%    $XXXX.X   $XXXX.X   $XXXX.X*  $XXXX.X   $XXXX.X
    WACC=X.X%    $XXXX.X   $XXXX.X   $XXXX.X   $XXXX.X   $XXXX.X
    WACC=X.X%    $XXXX.X   $XXXX.X   $XXXX.X   $XXXX.X   $XXXX.X
    * = base scenario (matches Base IV above)

  Position sizing: [L–U% of portfolio]
    Signal: [BUY|WATCH|CAUTION] × Range vs price: [...] (MoS [+/-]X.X%)
    Rationale: [one-line — signal × range_vs_price → band; cap if applicable]
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
  "intrinsic_value_range": {
    "bear": <number>,
    "base": <number>,
    "bull": <number>
  },
  "range_vs_price": "MARGIN OF SAFETY | WITHIN BEAR-BASE | WITHIN BASE-BULL | PRICE EXCEEDS RANGE",
  "sensitivity": {
    "dominant_driver": "WACC | terminal_growth | y2_5_cagr",
    "note": "WACC dominates — ±100 bps WACC moves base IV by ±18%"
  },
  "sensitivity_table": {
    "wacc_axis": [<base_wacc-0.01>, <base_wacc-0.005>, <base_wacc>, <base_wacc+0.005>, <base_wacc+0.01>],
    "terminal_growth_axis": [0.015, 0.02, 0.025, 0.03, 0.035],
    "intrinsic_value_per_share": [
      [<iv>, <iv>, <iv>, <iv>, <iv>],
      [<iv>, <iv>, <iv>, <iv>, <iv>],
      [<iv>, <iv>, <iv>, <iv>, <iv>],
      [<iv>, <iv>, <iv>, <iv>, <iv>],
      [<iv>, <iv>, <iv>, <iv>, <iv>]
    ],
    "base_cell": {"row": 2, "col": 2}
  },
  "position_sizing": {
    "band": "L–U% of portfolio",
    "lower_pct": <number>,
    "upper_pct": <number>,
    "signal_verdict": "BUY | WATCH | CAUTION",
    "range_vs_price": "MARGIN OF SAFETY | WITHIN BEAR-BASE | WITHIN BASE-BULL | PRICE EXCEEDS RANGE",
    "margin_of_safety_pct": <number>,
    "confidence_cap_applied": <boolean>,
    "rationale": "..."
  },
  "engagement_modifier": {
    "status": "applied | unavailable | no_kpi_mapping | user_skipped | direction_disagreement",
    "status_reason": "missing_ai_layer | no_recent_print | source_unreachable | extraction_failed | non_interactive | null",
    "kpi_map_schema_version": <integer>,
    "kpi_name": "<e.g. DAP>",
    "kpi_value": <number>,
    "kpi_unit": "<e.g. billion>",
    "kpi_period": "<e.g. Q1 2026>",
    "yoy_change": <number>,
    "direction": -1 | 0 | 1,
    "magnitude": "deadband | mild | strong",
    "base_anchor_multiplier": <number>,
    "clamped_from": <number | null>,
    "revision": {
      "metric": "eps_ntm_30d",
      "revision_pct": <number | null>,
      "direction": -1 | 0 | 1 | null,
      "source_url": "<yahoo /analysis/ URL>"
    },
    "agreement": <boolean | null>,
    "source_url": "<8-K Ex 99.1 URL>",
    "user_confirmed": <boolean>
  }
}
```

The `engagement_modifier` block is emitted only when `--engagement-modifier` was passed. When the flag is absent, omit the block entirely (FR6 / spike-decision). When the flag is present but the modifier was not applied (any non-`applied` status), populate `status` and `status_reason` and emit the remaining fields as `null` — preserving the schema shape for replay diffing. When `status == "applied"`, all populated fields are required (NFR3). `kpi_map_schema_version` mirrors the top-level field of `skills/_shared/engagement_kpi_map.json` at run time per Task 8 ADR D5. `clamped_from` is non-null only when the output-cap clamp fired (Step 6b); otherwise `null`. `revision` and `agreement` are populated by GATHER Step 5b (Yahoo `/analysis/` EPS Trend fetch); when the fetch fails or parsing returns no values, `revision.revision_pct` and `revision.direction` are `null` and `agreement` is `null` (legacy fall-through — modifier still applies per C3/C4). `agreement == false` triggers the `direction_disagreement` status, in which case `base_anchor_multiplier = 1.00` (modifier suppressed per spike-decision guardrail).

`intrinsic_value_range` is a flat extract of `scenarios.{bear,base,bull}.intrinsic_value_per_share` for UI convenience — must reconcile cell-for-cell with the scenarios block.

Rows in `sensitivity_table.intrinsic_value_per_share` are indexed by `wacc_axis` (row 0 = lowest WACC); columns by `terminal_growth_axis` (col 0 = lowest g). `base_cell` names the index that should match `scenarios.base.intrinsic_value_per_share`. Suppressed cells (where `wacc ≤ g`) are emitted as `null`, not numbers.

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

### GATHER — Pre-profit inputs (EMERGING path)

Run these MCP calls in this order. Every retrieved figure is held with its raw value; never round during gather.

1. **`get_ratios(ticker)`** — fields used: `currentPrice`, `marketCap`, `sharesOutstanding`.
2. **`get_financials(ticker)`** — used for:
   - `years[].revenue` (trailing revenue trajectory; minimum 3y required for CAGR)
   - `years[].free_cash_flow` (margin baseline + visibility into how close to inflection the company is today; may be negative)
   - `years[].stock_based_compensation` (SBC dilution input — required, never substituted)
   - `years[].shares_outstanding_diluted` (compute historical dilution rate)
   - `years[0].total_debt`, `years[0].cash` (net debt for EV→equity bridge)
3. **`get_estimates(ticker)`** — fields used: `ntm_revenue` (Year-1 revenue anchor).
4. **Web search for comparable EV/Revenue multiples.** Identify 3–5 public comps matched on (a) sector / business model, (b) revenue scale (within ~0.3×–3×), and (c) growth profile (NTM revenue growth within ~±15 pp). Retrieve current forward (NTM) EV/Revenue from the search results. Surface the comp list and their multiples to the user as part of the Manual Input Protocol below.

**Manual Input Protocol fires (always grouped — one paste-in):**

- **Base WACC** — same rule as ESTABLISHED; yfinance has no risk-free-rate / beta surface. Never default.
- **Exit EV/Revenue multiple — base case.** Present the comp list and ask the user to confirm or override the base multiple. Bear is `base × 0.6`, bull is `base × 1.4` (state these scenario axes; do not ask separately).
- **Terminal FCF margin target.** Industry-anchored. Ask the user for the steady-state margin the company is expected to achieve by Year 5 under the base case. Bear is `target − 5 pp`, bull is `target + 5 pp`. Never default.
- **SBC dilution rate (annual %).** Pre-fill with the trailing 3y dilution rate derived from `shares_outstanding_diluted` history: `dilution_3y = (years[0].shares / years[3].shares) ^ (1/3) − 1`. Surface this number and the historical share-count series, and ask the user to confirm or override. Bear is `confirmed × 1.5`, bull is `confirmed × 0.5` (dilution accelerates in bear, decelerates in bull) — state these axes; do not ask separately.

Manual inputs are tagged `source: "user_paste"`; `meta.confidence` caps at MEDIUM. If the user accepts every pre-filled value with no override, still record `source: "user_confirmed"` — the value is load-bearing on the output.

If `get_financials` returns null `stock_based_compensation` for the latest year: refuse with `Pre-profit variant requires SBC data; yf MCP returned null. Re-run with --confirm only after SBC is verified manually.` Do not proceed without SBC — the dilution schedule is a first-class output.

### COMPUTE — Pre-profit (revenue-multiple exit + FCF inflection)

Execute in order. The math anchors on revenue (not FCF) because pre-profit companies do not yet have a stable FCF base.

**Step 1 — Revenue trajectory per scenario.**

- `rev_cagr_3y = (years[0].revenue / years[3].revenue) ^ (1/3) − 1` (use shorter history with the same degraded formulations as ESTABLISHED Step 1 if 4y is unavailable).
- Year-1 revenue is anchored on NTM consensus, perturbed per scenario:

| Scenario | Y1 revenue | Y2–Y5 CAGR |
|---|---|---|
| Bear | `ntm_revenue × 0.85` | `max(rev_cagr_3y × 0.50, 0.05)` |
| Base | `ntm_revenue` | `rev_cagr_3y` |
| Bull | `ntm_revenue × 1.15` | `rev_cagr_3y × 1.15 + 0.03` |

Project `revenue_y_n = revenue_y_(n−1) × (1 + cagr)` for n = 2..5.

**Step 2 — FCF margin trajectory and inflection year.**

- `margin_ttm = years[0].free_cash_flow / years[0].revenue` (may be negative).
- Target Year-5 margin per scenario: `target − 5pp` (bear) / `target` (base) / `target + 5pp` (bull), where `target` is the user-confirmed terminal margin.
- Linear interpolation across Years 1–5: `margin_y_n = margin_ttm + (target − margin_ttm) × (n / 5)`.
- `fcf_y_n = revenue_y_n × margin_y_n` (negative in early years if the company is still cash-burning).
- **FCF inflection year:** the smallest n ∈ {1..5} such that `fcf_y_n ≥ 0` AND `fcf_y_m ≥ 0` for all m ≥ n in {1..5} (i.e., first year of *sustained* positive FCF — not a one-off blip).
- If no scenario reaches positive FCF by Y5, name it explicitly: `inflection_year = "beyond Y5"`. Do **not** silently assume eventual inflection — surface it as a model limitation in the OUTPUT block.

**Step 3 — Exit enterprise value.**

| Scenario | Exit EV/Revenue multiple | Exit EV at end of Year 5 |
|---|---|---|
| Bear | `base_multiple × 0.6` | `revenue_y5 × bear_multiple` |
| Base | `base_multiple` (user-confirmed) | `revenue_y5 × base_multiple` |
| Bull | `base_multiple × 1.4` | `revenue_y5 × bull_multiple` |

No Gordon-growth terminal — the exit-multiple is the terminal. State that explicitly in the OUTPUT block.

**Step 4 — SBC dilution schedule.**

- `dilution_rate` per scenario: `confirmed_rate × 1.5` (bear) / `confirmed_rate` (base) / `confirmed_rate × 0.5` (bull).
- `shares_y_n = shares_y_(n−1) × (1 + dilution_rate)` for n = 1..5, starting from `years[0].shares_outstanding_diluted`.
- The Year-5 diluted share count is the divisor for per-share IV — using today's share count overstates IV. This is the whole reason dilution is first-class.
- Also report `dilution_pct_5y = (shares_y5 / shares_y0) − 1` for the OUTPUT block.

**Step 5 — Discount to present.**

For each scenario:

```
EV_today = Σ_{n=1..5} fcf_y_n / (1 + wacc)^n   +   exit_ev / (1 + wacc)^5
```

The first sum includes negative FCFs in early years if the company is still burning cash — this is a real present-value drag and must be carried (do not floor at zero).

**Step 6 — Equity bridge and per-share intrinsic value.**

- `net_debt = years[0].total_debt − years[0].cash` (keep the sign; negative means net cash).
- `equity_value = EV_today − net_debt`
- `intrinsic_value_per_share = equity_value / shares_y5`  ← **Year-5 diluted shares**, not today's.
- `upside_pct = (intrinsic_value_per_share / currentPrice − 1) × 100`

**Step 7 — Range integrity check.**

Same rule as ESTABLISHED: require `bear_iv < base_iv < bull_iv`. If violated, stop, surface the three scenario input/output tables, and ask the user to widen the exit-multiple, margin-target, or dilution-rate deltas. Never silently re-order.

**Step 8 — Sensitivity note.**

For the pre-profit variant the dominant drivers are usually exit multiple and terminal margin (not WACC). Vary one assumption at a time around base:

- Exit multiple ± 1.0× (absolute)
- Terminal FCF margin ± 300 bps
- Dilution rate ± 200 bps annual
- WACC ± 100 bps

Report the largest-swing driver as a one-line note. The numbers shown are the percentage change in base IV.

### THRESHOLD — Range vs price

Identical to the ESTABLISHED path (MARGIN OF SAFETY / WITHIN BEAR–BASE / WITHIN BASE–BULL / PRICE EXCEEDS RANGE).

### OUTPUT — Pre-profit MODEL OUTPUT block + JSON merge

```
MODEL OUTPUT
  Ticker:          [TICKER]
  Method:          Revenue-multiple exit + FCF inflection (pre-profit variant)
  Profit stage:    [EMERGING | ESTABLISHED (forced --pre-profit)]
  Upstream:        SIGNAL OUTPUT (source=context|reports/TICKER_YYYYMMDD.json, verdict=..., MODEL_READY=...)

  Current price:   $X.XX
  Shares today:    XXX.X M (diluted)
  Net debt:        $X.X B (total_debt $X.X B − cash $X.X B, FY ending YYYY-MM-DD)
  Revenue (TTM):   $X.X B  |  3y CAGR: XX%  |  TTM FCF margin: -X% (cash-burning)
  NTM revenue:     $X.X B (consensus)
  Base WACC:       X.X% (source: user_paste)
  Comp set:        [TICKER1: NTM EV/Rev X.Xx, TICKER2: X.Xx, ...]  →  base exit multiple: X.Xx (user-confirmed)
  Terminal margin target (base): XX% (user-confirmed)
  SBC dilution (base): X.X% annual (3y trailing: X.X%, user-confirmed)

  Bear: $X.XX / share — [N]% [up|down]side
    Y1 rev: $X.XB (NTM × 0.85)  |  Y2-5 rev CAGR: X%  |  exit mult: X.Xx (base × 0.6)
    Terminal margin: XX% (target − 5pp)  |  Annual dilution: X.X% (base × 1.5)
    FCF inflection: Year N  |  Y5 share count: XXX.X M (+X% vs today)
    Narrative: revenue miss, slower margin path, accelerated dilution, comp multiples compress

  Base: $X.XX / share — [N]% [up|down]side
    Y1 rev: $X.XB (NTM consensus)  |  Y2-5 rev CAGR: X%  |  exit mult: X.Xx (comp median)
    Terminal margin: XX% (industry-anchored)  |  Annual dilution: X.X% (trailing 3y)
    FCF inflection: Year N  |  Y5 share count: XXX.X M (+X% vs today)
    Narrative: consensus revenue + linear margin convergence + historical dilution rate persists

  Bull: $X.XX / share — [N]% [up|down]side
    Y1 rev: $X.XB (NTM × 1.15)  |  Y2-5 rev CAGR: X%  |  exit mult: X.Xx (base × 1.4)
    Terminal margin: XX% (target + 5pp)  |  Annual dilution: X.X% (base × 0.5)
    FCF inflection: Year N  |  Y5 share count: XXX.X M (+X% vs today)
    Narrative: revenue beat, faster operating-leverage, dilution decelerates as SBC grants vest, comp multiples expand

  Range vs price: [MARGIN OF SAFETY | WITHIN BEAR–BASE | WITHIN BASE–BULL | PRICE EXCEEDS RANGE]
  Sensitivity:    [one-line dominant-driver note — usually exit multiple or margin target for pre-profit]

  Position sizing: [L–U% of portfolio]
    Signal: [BUY|WATCH|CAUTION] × Range vs price: [...] (MoS [+/-]X.X%)
    Rationale: [one-line — signal × range_vs_price → band; MEDIUM-confidence cap always applies for pre-profit]
```

If any scenario's inflection year is `beyond Y5`, the line reads `FCF inflection: beyond Y5 — model assumes exit-multiple buyer absorbs continued cash burn`.

**JSON merge into `reports/TICKER_YYYYMMDD.json` under `stages.model`:**

```json
"model": {
  "method": "pre-profit (revenue-multiple exit + FCF inflection)",
  "profit_stage": "EMERGING | ESTABLISHED",
  "route_override": "pre-profit | null",
  "current_price": <number>,
  "shares_today": <number>,
  "net_debt": <number>,
  "revenue_ttm": <number>,
  "rev_cagr_3y": <number>,
  "fcf_margin_ttm": <number>,
  "ntm_revenue": <number>,
  "base_wacc": <number>,
  "comp_set": [{"ticker": "...", "ntm_ev_revenue": <number>}],
  "base_exit_multiple": <number>,
  "terminal_margin_target": <number>,
  "sbc_dilution_base": <number>,
  "sbc_dilution_3y_trailing": <number>,
  "scenarios": {
    "bear": {
      "y1_revenue": <number>, "y2_5_rev_cagr": <number>, "exit_multiple": <number>,
      "terminal_margin": <number>, "dilution_rate": <number>,
      "fcf_inflection_year": <integer | "beyond Y5">,
      "shares_y5": <number>, "dilution_pct_5y": <number>,
      "intrinsic_value_per_share": <number>, "upside_pct": <number>,
      "narrative": "..."
    },
    "base": { /* same shape */ },
    "bull": { /* same shape */ }
  },
  "intrinsic_value_range": {
    "bear": <number>,
    "base": <number>,
    "bull": <number>
  },
  "range_vs_price": "MARGIN OF SAFETY | WITHIN BEAR-BASE | WITHIN BASE-BULL | PRICE EXCEEDS RANGE",
  "sensitivity": {"dominant_driver": "exit_multiple | terminal_margin | dilution_rate | wacc", "note": "..."},
  "sensitivity_table": null,
  "position_sizing": {
    "band": "L–U% of portfolio",
    "lower_pct": <number>,
    "upper_pct": <number>,
    "signal_verdict": "BUY | WATCH | CAUTION",
    "range_vs_price": "MARGIN OF SAFETY | WITHIN BEAR-BASE | WITHIN BASE-BULL | PRICE EXCEEDS RANGE",
    "margin_of_safety_pct": <number>,
    "confidence_cap_applied": true,
    "rationale": "..."
  }
}
```

`sensitivity_table` is `null` for the pre-profit variant — the 5×5 WACC × terminal-g grid is meaningless when there is no Gordon-growth terminal. The per-driver dominant-driver note in `sensitivity` remains the only sensitivity artefact for this path. `intrinsic_value_range` is a flat extract of `scenarios.{bear,base,bull}.intrinsic_value_per_share` — must reconcile.

The `engagement_modifier` block is **never emitted on the EMERGING path** regardless of the `--engagement-modifier` flag (FR6 — pre-profit revenue scaffolding has no incumbent KPI baseline). If the flag is passed alongside an EMERGING ticker, emit a one-line notice to the user: `--engagement-modifier ignored: EMERGING path (FR6)` and proceed without it.

After writing, print:

```
Wrote: reports/RDDT_20260513.json  ← stages.model (pre-profit)
RDDT — pre-profit DCF bear/base/bull = $X / $Y / $Z (price $P, WITHIN BEAR–BASE; FCF inflection base=Y3)
```

**Confidence rules (`meta.confidence`):**

- HIGH: not reachable for pre-profit — by construction, the variant relies on user-confirmed comp multiples and margin targets, so confidence caps at MEDIUM.
- MEDIUM: comp set retrieved from web search with ≥3 matches; all manual inputs user-confirmed; range integrity passed first time; SBC data present.
- LOW: <3 comp matches, or SBC data partial, or range integrity required user re-input, or no scenario reaches FCF inflection by Y5.

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
| "Pre-profit company is cash-burning; I'll just floor early-year FCFs at zero so the DCF doesn't look ugly." | Forbidden. Negative early-year FCFs are real present-value drag and must be discounted as-is. Hiding them inflates the IV and masks the cost of the company's runway to profitability. |
| "Comp multiples vary; I'll just pick a round number like 5× and call it the base." | Forbidden. The base exit multiple must come from a documented comp set (3–5 tickers with their NTM EV/Revenue) surfaced to the user for confirmation. "Pick a round number" is the fabrication path. |
| "The comp tickers I think of off the top of my head are good enough; I'll skip the web search." | Forbidden. Comp multiples drift; using training-cutoff multiples in a 2026 valuation is hallucination. Web-search the current NTM EV/Revenue for each comp at run time, then ask the user to confirm. |
| "FCF inflection year is a soft concept; I'll just write 'eventually profitable' in the narrative." | Forbidden. The acceptance contract requires *naming* the year of first sustained positive FCF per scenario. If no scenario reaches inflection by Y5, write `beyond Y5` explicitly — never paper over with "eventually". |
| "SBC dilution is small; I can just use today's share count for the per-share IV." | Forbidden. Pre-profit tech routinely dilutes 3–8% annually; over 5 years that compounds to 16–47%. Per-share IV must divide by Year-5 diluted shares, not today's. This is the whole reason the dilution schedule is first-class. |
| "I'll set bear dilution = base dilution; the rate doesn't vary that much across scenarios." | The acceptance contract requires demonstrably-different assumption sets. Dilution is one of the four scenario axes (along with revenue, margin, multiple); use `× 1.5 / × 1.0 / × 0.5`. Collapsing axes defeats the bear/base/bull discipline. |
| "The 5×5 sensitivity grid is just decoration — I'll skip it or fudge it from the dominant-driver note." | Forbidden. The grid is a separate required artefact: it shows the full joint shape of IV vs (WACC, g), which the one-line dominant-driver note cannot. The center cell must reconcile to base IV; if it doesn't, the rest of the run is suspect — stop and reconcile, do not paper over. |
| "The center cell of the grid is $5 off the base scenario IV — close enough, I'll round and ship." | Tolerance is ±$0.50 / share. A larger gap means the grid's discounting math has diverged from Step 6's (e.g. using cagr instead of `(1+cagr)`, or off-by-one on the discount exponent). Reconcile before emitting. |
| "Gordon-growth terminal would give a cleaner number than a revenue-multiple exit." | Forbidden for pre-profit. Gordon growth requires a stable FCF base and a defensible long-run growth rate; pre-profit companies have neither. Revenue-multiple exit is the honest call — comp-anchored, scenario-disclosed, and not pretending to a precision the inputs don't support. |
| "Position sizing is just a vibe — I'll write '2-3%' without showing the lookup." | The band must be derivable from the table (Signal verdict × range_vs_price), the MoS %, and the confidence cap. The rationale string names all three load-bearing inputs so the user can audit the call. "Felt right" is not a sizing methodology. |
| "BUY × MARGIN OF SAFETY is rare — I'll bump the band to 6–8% to express conviction." | Forbidden. The bands are fixed by the table and capped by confidence. Single-name tech caps at 6% upper even at maximum conviction; expressing more conviction than the table allows is exactly the discipline failure the table exists to prevent. |
| "CAUTION but the price is far below bear IV — surely a 1–2% starter is justified?" | Forbidden. CAUTION from Signal means a qualitative or governance concern (FAIL or hard-flag), not a price concern. Price-cheapness does not unlock CAUTION; the concern needs to be resolved at the Signal layer first. The table caps CAUTION × MARGIN OF SAFETY at 0–1% for this reason. |
| "Pre-profit run; I should still produce a sensitivity_table by sweeping exit multiple × dilution." | Forbidden in v1. The `sensitivity_table` JSON field is the WACC × terminal-g grid only (ESTABLISHED path). Pre-profit emits `sensitivity_table: null` and relies on the single-driver `sensitivity` note. A second-axis grid for pre-profit is a future-tier concern, not v1. |
| "I'll skip `intrinsic_value_range` — the consumer can read `scenarios.{bear,base,bull}.intrinsic_value_per_share` itself." | Forbidden. `intrinsic_value_range` is a contract field for downstream consumers (UI, router, position-sizing logic) so they don't need to know the scenario-block shape. Drop it and the next change to the scenario shape silently breaks every consumer. |

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
14. **EMERGING + MODEL_READY=YES →** (superseded by v1.3 #18 — EMERGING now routes to the pre-profit variant rather than refusing.)
15. **Base WACC always asked →** the Manual Input Protocol fires for base WACC on every ESTABLISHED run; the value is recorded in `meta.manual_inputs` and the confidence caps at MEDIUM.
16. **Sensitivity note present →** the OUTPUT block names exactly one dominant driver (WACC / terminal growth / Y2–5 CAGR) with a one-line magnitude statement.
17. **`wacc ≤ g` override is disclosed →** if a scenario required narrowing the WACC adjustment to keep `wacc > g`, the OUTPUT block states the override explicitly; the user never sees a silently re-tuned scenario.

### v1.3 — ABA-34 (pre-profit variant)

18. **EMERGING + MODEL_READY=YES →** invoking `/stock:model TICKER` (no flag) routes to the pre-profit variant; output `method` field reads `pre-profit (revenue-multiple exit + FCF inflection)`.
19. **`--pre-profit` flag on ESTABLISHED ticker →** routes to the pre-profit variant, prints the `Forcing pre-profit variant...` acknowledgement, sets `route_override = "pre-profit"` in JSON, and uses revenue-multiple exit instead of Gordon-growth terminal.
20. **Implied EV from revenue multiple →** each scenario's output explicitly shows `revenue_y5 × exit_multiple` as the terminal anchor; no Gordon-growth math runs in this path.
21. **FCF inflection year named per scenario →** every scenario's output line includes `FCF inflection: Year N` or `FCF inflection: beyond Y5`. The skill never paraphrases this to "eventually profitable" or omits it.
22. **SBC dilution schedule first-class →** the OUTPUT block and the JSON both carry `dilution_rate` and `shares_y5` per scenario, with `dilution_pct_5y` reported. Per-share IV divides by Y5 diluted shares, not today's. If SBC data is unavailable, the skill refuses rather than computing a dilution-free IV.
23. **Comp set sourced and confirmed →** the run includes a web-search step that produces ≥3 comparable tickers with their NTM EV/Revenue, surfaced to the user for confirmation via MIP. Confidence caps at MEDIUM for the pre-profit variant by construction.
24. **Bear < Base < Bull holds across the new scenario axes →** Y1 revenue, Y2–5 CAGR, exit multiple, terminal margin, and dilution rate each move on an independent axis; range integrity is enforced the same way as ESTABLISHED.
25. **Acceptance smoke (RDDT) →** running `/stock:signal RDDT` then `/stock:model RDDT --pre-profit` produces a MODEL OUTPUT block with all three scenarios, named FCF inflection years, a comp-anchored exit multiple, and a SBC dilution schedule — and merges into `reports/RDDT_YYYYMMDD.json` without overwriting `stages.signal`.

### v1.4 — ABA-32 (sensitivity grid, ESTABLISHED)

26. **Sensitivity grid present →** the ESTABLISHED OUTPUT block contains a formatted 5×5 grid with rows = WACC axis (`base_wacc ± 1.0 pp` in 0.5 pp steps) and columns = terminal growth axis (`1.5%, 2.0%, 2.5%, 3.0%, 3.5%`). The JSON carries `stages.model.sensitivity_table` (renamed from `sensitivity_grid` in ABA-35) with `wacc_axis`, `terminal_growth_axis`, `intrinsic_value_per_share` (5×5 array of per-share IVs), and `base_cell` index.
27. **Base cell reconciles →** the cell at `base_cell` (`base_wacc`, `g=2.5%`) matches `scenarios.base.intrinsic_value_per_share` within $0.50 / share. A larger gap stops the run.
28. **Monotonicity →** every column is strictly decreasing top-to-bottom (IV ↓ as WACC ↑); every row is strictly increasing left-to-right (IV ↑ as g ↑). If either monotonicity check fails, the grid math is broken — stop, do not silently re-order.
29. **`wacc ≤ g` cells →** if a low-WACC / high-g cell collapses (only possible when user-supplied `base_wacc < 4.5%`), it is emitted as `null` in the JSON and `n/a` in the table, with a one-line note. Never floor, fudge, or silently swap.
30. **Acceptance smoke (META) →** the existing META smoke report `reports/META_YYYYMMDD.json` is updated to include `stages.model.sensitivity_table` (ABA-35 renamed from `sensitivity_grid`); the center cell matches the stored base IV; the printed table satisfies monotonicity.

### v1.5 — ABA-33 (position sizing)

31. **Position-sizing block present →** every MODEL OUTPUT block (both ESTABLISHED and EMERGING paths) includes a `Position sizing` line with an allocation band string and a rationale that references both the upstream Signal verdict (BUY/WATCH/CAUTION) and the margin-of-safety percentage (`(base_iv / current_price − 1) × 100`).
32. **Band derived from the lookup table →** the band must match the Signal × range_vs_price table in the POSITION SIZING section, with the upper bound capped per confidence (HIGH = no cap; MEDIUM ≤ 4%; LOW ≤ 2%). When a cap fires, the rationale names it.
33. **CAUTION → 0–1% maximum →** any CAUTION signal caps total allocation at 0–1% (and only at MARGIN OF SAFETY); CAUTION × any other range is 0%. Cheapness does not unlock CAUTION.
34. **Pre-profit caps at MEDIUM →** because the pre-profit variant always caps `meta.confidence` at MEDIUM, every pre-profit `position_sizing.upper_pct` is `≤ 4`.
35. **No-entry phrasing →** if the band is `0–0%`, the band string reads exactly `"0% of portfolio (no entry)"` — never `"0–0% of portfolio"`.

### v1.6 — ABA-35 (report JSON integration)

36. **`stages.model.intrinsic_value_range` present →** the model JSON contains a flat `{bear, base, bull}` extract of per-share IVs that reconciles cell-for-cell with `scenarios.{bear,base,bull}.intrinsic_value_per_share`. Applies to both ESTABLISHED and EMERGING paths.
37. **`stages.model.scenarios` present →** the full scenario block (each of bear/base/bull with its own assumptions, IV, upside %, narrative) is emitted under `scenarios`.
38. **`stages.model.sensitivity_table` present →** ESTABLISHED emits the 5×5 WACC × terminal-g grid object (renamed from `sensitivity_grid` in v1.4) with `wacc_axis`, `terminal_growth_axis`, `intrinsic_value_per_share` 5×5 array, and `base_cell` index. EMERGING emits `sensitivity_table: null` (the grid is meaningless without a Gordon-growth terminal) and relies on the dominant-driver `sensitivity` note instead.
39. **`stages.model.position_sizing` present →** the sizing block from v1.5 is emitted as a structured object (`band`, `lower_pct`, `upper_pct`, `signal_verdict`, `range_vs_price`, `margin_of_safety_pct`, `confidence_cap_applied`, `rationale`) — not just a string.
40. **JSON validity preserved →** running `/stock:model META` writes a `reports/META_YYYYMMDD.json` that parses as valid JSON, with `stages.model` containing all four required fields and merging cleanly with any pre-existing `stages.signal` / `stages.screen` / `stages.timing` blocks (no overwrite of sibling stages).
