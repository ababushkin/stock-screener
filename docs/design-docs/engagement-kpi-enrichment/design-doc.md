---
name: engagement-kpi-enrichment
status: accepted
authors: Anton Babushkin
created: 2026-05-14
last_updated: 2026-05-17
supersedes: none
linear: ABA-66
appetite: 3 weeks (fixed cap, not range) — see Sequencing
plan_review: docs/plan-reviews/engagement-kpi-enrichment/review.md (REVISE, six conditions; this revision addresses)
spike_decision: docs/design-docs/engagement-kpi-enrichment/spike-decision.md (RESHAPE → PROCEED; supersedes the "lead-prediction" framing — see Acceptance note below)
---

# Engagement-KPI enrichment for `/stock-model` (APPLICATION / INCUMBENT tickers)

> **Acceptance note (2026-05-17).** Accepted with the spike-decision pivot in
> force. The doc body below frames the modifier as a **lead** signal —
> engagement-direction *predicts* the consensus revision before it lands, and
> NFR7's backtest is the gate. The Task 7 spike (see `spike-decision.md`)
> showed the wayback data source needed for that gate is not viable, and
> reshaped the philosophy to **confirm/lag**: engagement-direction agrees with
> (or contradicts) the revision that has already started, measured against
> Yahoo Finance's live `/analysis/` EPS Trend "Current vs 30 Days Ago" table.
> The NFR7 backtest is replaced by a flag-gated advisory plus forward-log
> accumulation toward n≥24 ticker-quarters; the kill-criterion value (60%
> direction agreement) is unchanged. Where the body below says "lead",
> "predict", or "consensus revision direction" in the context of NFR7 /
> backtest gating, read it as superseded by `spike-decision.md`. All other
> design choices — EDGAR-anchored KPI extraction, pre-registered constants,
> two-cap audit trail, base-scenario-only application, KPI-map versioning —
> survive the pivot unchanged and were built in Tasks 1, 3–13.

## Problem

When `/stock-model` runs for ad-driven and subscription companies (APPLICATION and INCUMBENT layers in the existing AI-layer taxonomy — e.g. META, NFLX, RDDT, GOOGL), the DCF's Year-1 revenue and FCF-margin inputs are anchored on `ntm_revenue` from `yfinance.get_estimates`. That figure is a single consensus number compiled by sell-side analysts. By the time it lands in yfinance it is already 1–8 weeks stale relative to the latest earnings release.

For these business models, the most recent quarter's engagement metrics (DAU, ARPU, paid-sub net adds, impressions, CPM) are the *leading* indicator of next-quarter and next-year revenue. The current skill is structurally blind to them — it can see what the analyst median was last week, but not the post-print engagement trajectory the analyst median will be updated *to* over the coming weeks.

**Affected user:** the user running `/stock-model META` (or similar) within ~6 weeks of an earnings release.

**Current behaviour:** Year-1 revenue is anchored exactly on stale consensus; bear/base/bull scenarios are perturbations around that anchor with no signal about whether the trajectory is accelerating or decelerating versus what the consensus assumes.

**Desired behaviour:** When the upstream Signal classified the ticker as APPLICATION or INCUMBENT, the skill incorporates the most recent quarter's engagement-KPI trajectory as a directional modifier on the Year-1 anchor, with the modification disclosed in the output. The user can see *which* engagement metric moved, by how much, and how the modifier was applied.

## Context

### Prior work and skill structure

- `/stock-model` is the v1.6 skill specified in `skills/stock-model/SKILL.md`. Year-1 revenue/FCF math is reconciled across two paths (ESTABLISHED two-stage DCF, EMERGING pre-profit variant); both use `ntm_revenue` as the anchor.
- The Manual Input Protocol (`skills/_shared/MANUAL_INPUT_PROTOCOL.md`) is the established pattern for inputs that cannot be derived from MCP data. Web-search results (e.g. comp multiples in the pre-profit variant) flow through this protocol — they are presented to the user for confirmation, never silently committed.
- The AI-layer classification (INFRASTRUCTURE / FOUNDATION / APPLICATION / INCUMBENT / NONE) is produced upstream by `/stock-signal` and lives in `stages.signal.ai_layer` of the report JSON.
- Confidence caps already exist (HIGH / MEDIUM / LOW) and cascade across stages. Any EDGAR-anchored modifier (with WebSearch as last-resort fallback) should integrate into this rather than introduce a new dimension.

### Constraints inherited from the existing skill

- **No silent substitution.** Every user-visible number must be derivable from documented inputs (MCP calls or user-confirmed paste-ins).
- **Range integrity (`bear_iv < base_iv < bull_iv`) is mandatory.** Any new modifier must not collapse scenarios or invert their order.
- **Demonstrably different assumption sets per scenario.** The modifier must perturb scenarios on an independent axis from the existing Y1 perturbation — not piggyback on it.
- **Audit trail is load-bearing.** The OUTPUT block must show which KPI was read, the source URL, the trend value, and how the modifier was applied. No paraphrasing.

### What the ticket gets wrong, that this doc reconciles

The ticket frames the modifier as "positive momentum → use upper range of NTM estimate." The skill does not currently expose a high/low consensus band — `get_estimates` returns a single `ntm_revenue` mean. So either (a) the modifier perturbs the existing single NTM number, (b) the skill grows a high/low band, or (c) the modifier operates on a different lever entirely (FCF margin, scenario weights). This is resolved in **Alternatives** below.

### Engagement-KPI reality check (per-ticker)

A quick reality check of the ticket's KPI table against current (2026) disclosures:

| Company | Ticket's primary KPI | Actually disclosed in press release? |
|---|---|---|
| META | DAU/MAU, impressions | DAP ("Daily Active People") — replaced DAU/MAU in 2023 |
| NFLX | Paid-sub net adds | Stopped quarterly disclosure in Q1 2025 — only annual now |
| RDDT | DAU | DAUq ("Daily Active Uniques") — yes, quarterly |
| GOOGL | Search CPM / impression vol. | Not disclosed; "paid clicks" + "cost-per-click" YoY % only |
| XYZ (Block) | Cash App MAUs, inflows-per-active | Cash App MAUs + Cash App gross profit per active disclosed quarterly in shareholder letter / 10-Q |

The takeaway: the KPI map needs to be authored as part of this work and verified against current 10-Q / press-release language, not lifted from the ticket as gospel.

## Constraints

### Functional

- FR1: Modifier fires only when `upstream_signal.ai_layer ∈ {APPLICATION, INCUMBENT}`. If `ai_layer` is missing OR the user believes upstream classification is wrong, the skill does not second-guess `/stock-signal` — the user re-runs Signal. The modifier honours the upstream truth and is not a side-channel for re-classification.
- FR2: Extracted KPIs and source URL are surfaced to the user via the existing Manual Input Protocol — never silently applied.
- FR3: Modifier produces a single direction value `∈ {+1, 0, −1}` (accelerating / neutral / decelerating) and a magnitude band (`mild` / `strong`) derived from the trend.
- FR4: The modifier is bounded by **two** caps. **(a) Input multiplier cap: ±4% on the Year-1 anchor** (`base_y1_anchor_multiplier ∈ [0.96, 1.04]`) — applied to the base scenario only; bear/bull unaffected to preserve scenario-axis independence. **(b) Output IV impact cap: ≤5% on base IV** — computed post-application, asserted by NFR4. If the input multiplier is at its ±4% bound but the resulting base IV moves >5% from the unmodified IV (possible under leveraged DCF sensitivities), the modifier is clamped further so the output cap holds, OR marked `status: "clamped"` with the reduction recorded. The specific caps, deadband, and magnitude thresholds are recorded in `docs/adrs/engagement-modifier-constants.md` (see Consequences).
- FR5: When the modifier cannot be computed (no recent earnings release, web search fails, user rejects the extracted KPIs), the skill proceeds *without* the modifier and records `engagement_modifier.status: "unavailable"` in the JSON — never fabricates a direction.
- FR6: The modifier never triggers on EMERGING/`--pre-profit` runs where the company has no meaningful engagement KPI yet (e.g. enterprise-software pre-IPO comps).
- FR7: The KPI map (which metrics matter for which ticker / business model) is authored as a versioned reference table at `skills/_shared/engagement_kpi_map.json` with a top-level `schema_version` field (integer, starts at 1) and a sibling `CHANGELOG.md` recording every ticker/KPI change with date and source-link evidence. Tickers not in the map skip the modifier with `status: "no_kpi_mapping"`. Schema version is emitted in every `engagement_modifier` JSON block so report-replay can reconstruct map state.
- FR8: **Source anchoring — EDGAR 8-K Exhibit 99.1 is the primary source.** The earnings press release filed as Exhibit 99.1 to the 8-K is the same document the IR page hosts, but on a deterministic SEC URL with a time-stamped filing date and a consistent surface across all US-listed seed tickers (META, NFLX, RDDT, GOOGL). Source resolution order:
  1. **EDGAR MCP `get_8k_exhibit(ticker, latest=true)`** — preferred; the planned EDGAR MCP server (per CLAUDE.md) is the right home for this. Returns Exhibit 99.1 content + filing date + accession number.
  2. **Direct EDGAR HTTP fetch** — fallback if the EDGAR MCP server is not yet built when this skill ships. Use `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=<cik>&type=8-K&dateb=&owner=include` to find the latest 8-K, then resolve to the Exhibit 99.1 document.
  3. **`WebSearch` fallback** — only when the ticker has no 8-K with a Q-end exhibit in the last 90 days (e.g. mid-quarter run before the next earnings). Marked in the JSON with `source_type: "websearch_fallback"` so the audit trail records the lower-reliability path.

  **Extraction** uses the same Claude model already running the skill (no separate API call, no cross-vendor LLM). Cost is in-session tokens (see NFR6). **Runtime coupling:** if neither EDGAR nor `WebSearch` is reachable, the step emits `status: "unavailable"` and the skill proceeds without the modifier — no fabrication, no third fallback.

  **Why EDGAR over web search:** (a) deterministic URL → reproducibility test (Week 1) becomes a tautology rather than a real risk; (b) time-stamped filing date → no risk of pulling the previous quarter's release; (c) one consistent surface format across the seed set rather than three; (d) audit trail anchors on an SEC accession number, which never changes.

### Non-functional (each with fitness function)

- NFR1 — **Web-search latency at p95 ≤ 12 s per ticker.** Fitness function: smoke test in `tests/smoke/engagement_kpi_latency.py` times the search step on a 5-ticker rotation and fails CI above the bound.
- NFR2 — **Extraction precision ≥ 80% on the seed ticker set (META, NFLX, RDDT, GOOGL, XYZ).** Defined as: for each of the five tickers, the extracted KPI value and YoY % match what a human verifies from the linked 8-K Exhibit 99.1. Fitness function: `tests/golden/engagement_kpi_extraction.py` runs against frozen press-release fixtures and asserts extracted values match the fixture's hand-verified expected values within ±2% (numerical) and exact-match (direction).
- NFR3 — **Zero silent application + status-reason discipline.** Every modifier application must produce an entry in `stages.model.engagement_modifier` with `kpi_name`, `kpi_value`, `kpi_period`, `yoy_change`, `direction`, `magnitude`, `source_url`, `user_confirmed: true|false`. Every non-applied entry (`status ∈ {unavailable, no_kpi_mapping, user_skipped}`) must populate `status_reason` from the documented enum. Fitness function: JSON-schema test — applied entries have all eight applied-fields populated; non-applied entries have a non-null `status_reason` matching the enum.
- NFR4 — **Modifier impact bounded.** No scenario IV moves more than 5% from its pre-modifier value due to the engagement modifier alone. Fitness function: unit test asserts `abs(iv_with_modifier / iv_without_modifier - 1) ≤ 0.05` across the seed set.
- NFR5 — **Confidence cap honoured.** Any run with `engagement_modifier.status == "applied"` caps `meta.confidence` at MEDIUM (web search is not a structured-data source). Fitness function: unit test on the confidence-resolution logic.
- NFR6 — **Cost envelope: in-session tokens only.** Because FR8 fixes the search + extraction stack to the Claude Code runtime, there is no separate API line item. The budget collapses to "extraction prompt + press-release excerpt token count per invocation ≤ 8k tokens." Fitness function: smoke-test asserts the GATHER step's net token consumption against a frozen extraction prompt + a representative press-release fixture per surface type (PDF/HTML/letter).

- NFR7 — **Outcome metric (load-bearing).** Over a rolling 8-quarter backtest on the seed-ticker set, the modifier's direction (computed retroactively from each quarter's engagement KPI) agrees with the *actual* analyst-consensus revision direction over the 4-week post-print window on **≥ 60% of ticker-quarters**. Below this threshold the modifier is signal-dressed noise and must not ship. Fitness function: `tests/backtest/engagement_kpi_revision_agreement.py` — runs against frozen historical engagement-KPI + consensus-revision fixtures, asserts hit rate ≥ 60% with at least 24 ticker-quarter samples. This NFR is the kill-switch for the load-bearing assumption named in B3 of the plan review.

## Alternatives considered

### Alt A — Do nothing (status quo)

`/stock-model` continues to anchor Year-1 inputs on stale consensus only.

- **Blast radius if wrong:** Continued loss of leading-indicator signal on the four highest-traffic tickers in the user's universe.
- **Reversal cost:** None — this is the current state.
- **Why rejected:** Concedes the most valuable enrichment for the most-used skill on the most-watched tickers.

### Alt B — EDGAR-anchored KPI extraction with WebSearch fallback (recommended)

Add an optional GATHER step for APPLICATION/INCUMBENT tickers. Fetch the latest 8-K Exhibit 99.1 from EDGAR (per FR8 — deterministic URL, time-stamped filing); fall back to WebSearch only when no Q-end exhibit exists in the last 90 days. Extract the engagement KPI(s) mapped to the ticker, compute YoY trend, and apply a bounded multiplicative modifier to Year-1 revenue (or FCF margin — see open question OQ1) in the **base** scenario only. Bear/bull are unmodified to preserve scenario-axis independence. Modifier is surfaced via MIP before commitment.

- **Blast radius if wrong:** A bad extraction propagates into base IV by ≤ 5% (per NFR4). The MIP gate means the user has a chance to reject the extraction before it commits.
- **Reversal cost:** Low — the modifier is additive and disable-able per-run via a `--no-engagement-modifier` flag (proposed). Removing the feature entirely is a single skill-version revert.

### Alt C — Grow `get_estimates` to expose high/low consensus band, then shift within it

The ticket's literal framing: yfinance's `recommendationKey` / analyst-range fields could be surfaced and the modifier picks high vs. low end.

- **Blast radius if wrong:** Touches the yf MCP server, not just the skill. Requires a new field across `get_estimates` consumers (signal, model, UI).
- **Reversal cost:** High — once exposed, downstream consumers depend on it.
- **Why rejected:** (a) The analyst high/low range is itself stale and slow-to-update — it doesn't solve the post-print freshness problem. (b) Expands the yf MCP surface area for marginal benefit. (c) Doesn't actually use the engagement-KPI signal the ticket calls out — just shifts within a band that doesn't reflect it. Wrong layer.

### Alt D — Subscribe to a structured engagement-data feed (Visible Alpha, AlphaSense, Bloomberg)

Buy structured KPI data rather than scraping press releases.

- **Blast radius if wrong:** Adds a paid vendor dependency, account/contract overhead, and an additional MCP server.
- **Reversal cost:** Medium-high — vendor lock-in once integrated.
- **Why rejected:** Boring-technology principle inverted — this is a personal research tool. The user-base is one. A $500/month feed is the wrong shape; web search costs cents per invocation and the failure mode (occasional bad extraction) is bounded by NFR4 and the MIP gate.

## Recommended approach

**Alt B** with the following concrete shape:

1. **KPI mapping table** lives at `skills/_shared/engagement_kpi_map.json`. Authored manually for the v1 seed set (META, NFLX, RDDT, GOOGL); extension to other tickers is a future task. Each entry names: primary KPI, secondary KPI, comparison basis (YoY or QoQ), and whether the metric is a "growth signal" (higher is better) or a "monetisation signal" (higher is better, but interpretation differs).

2. **GATHER step inserted into both paths** — runs after `get_estimates` and before COMPUTE, conditional on `ai_layer ∈ {APPLICATION, INCUMBENT}` AND ticker present in the KPI map. The step:
   - Fetches the latest 8-K Exhibit 99.1 from EDGAR per FR8 resolution order (EDGAR MCP → direct HTTP → WebSearch fallback).
   - Extracts the mapped KPIs via the in-runtime Claude model with the filing accession + URL captured.
   - Computes the YoY trend.
   - Surfaces the extraction to the user via MIP: KPI name, value, period, YoY %, source filing — for confirm/override/skip.

3. **Modifier application** (only after user confirms):
   - `direction ∈ {+1, 0, −1}` based on YoY trend thresholds (deadband ±2% YoY → 0; otherwise sign of YoY).
   - `magnitude ∈ {mild, strong}` based on `abs(YoY) < 8%` vs `≥ 8%`.
   - Effect: `base_y1_anchor_multiplier = 1 + direction × (0.02 if mild else 0.04)` — i.e. ±2% or ±4% on the Y1 anchor (input cap, FR4a).
   - Applied to `fcf_y1_consensus` (ESTABLISHED) or `revenue_y1` (EMERGING) in the **base scenario only**.
   - Post-application, if `abs(base_iv_after / base_iv_before − 1) > 0.05` (output cap, FR4b / NFR4), the multiplier is clamped further to bring the IV impact under 5%, and the JSON records `clamped_from` alongside the applied multiplier.
   - Bear and bull unmodified.

4. **JSON contract** — new optional block `stages.model.engagement_modifier`:
   ```json
   "engagement_modifier": {
     "status": "applied | unavailable | no_kpi_mapping | user_skipped",
     "status_reason": "missing_ai_layer | no_recent_print | source_unreachable | extraction_failed | non_interactive | null",
     "kpi_name": "DAP",
     "kpi_value": 3.43,
     "kpi_unit": "billion",
     "kpi_period": "Q1 2026",
     "yoy_change": 0.061,
     "direction": 1,
     "magnitude": "mild",
     "base_anchor_multiplier": 1.02,
     "source_url": "https://investor.fb.com/...",
     "user_confirmed": true
   }
   ```

5. **OUTPUT block addition** — a single line under the base-scenario block:
   ```
   Engagement modifier (base only): DAP +6.1% YoY (Q1 2026) → +2% anchor uplift (mild positive, user-confirmed)
     Source: https://investor.fb.com/...
   ```

6. **CLI flag** — `--no-engagement-modifier` skips the GATHER step entirely. Useful for reproducibility and for cases where the user wants the unmodified DCF.

**Why this wins on the constraints:**

- **FR1–FR7 all met by construction.** The skill gates on AI layer, surfaces to MIP, caps the effect, and emits a structured audit trail.
- **NFR4 honoured by the two-cap structure.** Input multiplier capped at ±4% on the Y1 anchor; output base IV impact additionally clamped at ≤5% if the input cap alone is insufficient.
- **Bear/bull preserved unmodified** — scenario-axis independence is protected (the existing range-integrity rule still holds, and the modifier can only narrow the bear-base gap or widen the base-bull gap, never invert them).
- **Boring tech:** EDGAR-anchored extraction reuses the existing EDGAR MCP surface; WebSearch fallback reuses the pre-profit comp-set pattern.
- **Reversible:** flag-disable per run, version-revert in aggregate.

## Consequences

### Positive

- Post-earnings runs of `/stock-model` on the seed tickers reflect the latest engagement trajectory rather than stale consensus.
- The audit trail (source URL + user confirmation in the JSON) lets the user verify or replay the call.
- Pattern is generalisable — the segment-revenue ticket (mentioned in ABA-66 alongside RDDT) can re-use the GATHER-step infrastructure.

### Negative

- EDGAR-anchoring largely removes the source-URL non-determinism that earlier drafts worried about (deterministic accession numbers; time-stamped filings). The residual risk is on the WebSearch fallback path (used only when no Q-end 8-K exists in the last 90 days) — that path is marked in the JSON as `source_type: "websearch_fallback"` and carries the lower-reliability tag in the audit trail.
- LLM extraction will sometimes fail — typically silently producing a plausible-but-wrong number. NFR2 + the MIP gate are the two-tier defence; both are required.
- The KPI map is a maintenance burden: when META rebrands DAP to a new metric (which they will), the map must be updated. Open question OQ4 below.

### Walking-skeleton requirement

**Yes — required.** Before scoping the full implementation, build an end-to-end spike across **three surface types** (not one):
- **META Q1 2026** — PDF earnings release surface (the riskiest extraction surface)
- **RDDT Q1 2026** — HTML press-release surface
- **NFLX Q1 2026** — quarterly shareholder-letter surface (mixed; metric cadence changed in 2025)

One ticker each, one mapped KPI each, one extraction prompt iteration allowed, modifier application + MIP confirmation + JSON write end-to-end.

Goals:
- Validate ≥ 80% extraction precision (NFR2) on *each of the three surfaces*. Failing any one surface stops the project — pivot to Alt D or reshape KPI map.
- Validate ±4% base-IV cap holds (NFR4).
- Bound the in-session token cost (NFR6).

This skeleton is the single biggest risk-reducer in the design. Pre-skeleton, the entire approach is a hypothesis about extraction quality on heterogeneous surfaces. Post-skeleton, it is measured.

### Backtest gate (precondition to merge)

Independent of the walking skeleton, the modifier's load-bearing assumption — "YoY engagement leads analyst consensus revision direction" — must be backtested before the feature ships to the user. Plan:

- **Sample:** up to **40 candidate ticker-quarters** (5 seed tickers × 8 historical quarters). Some will be unmappable (e.g. NFLX post-Q1 2025 sub-disclosure change). **Minimum valid sample to count as a pass: 32 ticker-quarters.** NFR7's hard floor is **24 samples** — if usable data falls below that, the backtest is moot and the modifier ships disabled-by-default by construction. Where a quarter is unmappable, substitute the next-best mapped quarter from the same ticker and document the substitution; otherwise drop the quarter and note it.
- **For each ticker-quarter:** compute what the modifier direction *would have been* using the engagement KPI as it was published at the time. Compare against the actual sign of the consensus NTM-revenue revision over the 4 weeks following the print (data source: yfinance historical estimates if available, otherwise hand-collected from archived analyst notes).
- **Pass condition:** hit rate ≥ 60% (NFR7). Below this the modifier ships disabled by default — flag becomes `--engagement-modifier` (opt-in) rather than `--no-engagement-modifier` (opt-out).
- **Fixture-frozen:** the backtest is committed as test data, so future map / formula changes can be re-evaluated against the same baseline.

### ADR commitments

Two ADRs to be authored in the same sequence as the implementation, both before merge:

1. **`docs/adrs/engagement-modifier-constants.md`** — records the deadband (±2% YoY), strong-magnitude threshold (8% YoY), base-only application choice (vs. all three scenarios), ±4% cap on base IV, AND the **60% backtest-pass threshold** with its justification (coin-flip baseline + ≥10pp lift). Each constant carries reasoning + the alternative considered + the data point that would prompt a revision. The ADR is **pre-registered** — committed before the Week 2 backtest is run, so the backtest cannot be tuned to its own answer. One in-sample revision allowed (documented as supersession); further revisions require fresh data.
2. **`docs/adrs/engagement-kpi-map-versioning.md`** — records the schema-versioning convention (integer monotonic), the changelog format, and the drift-detection CI check.

### Integration risks (known and unknown)

- **Known:** Confidence-cap interaction with existing MEDIUM caps from manual-input pasteins (pre-profit variant already caps at MEDIUM by construction — no incremental cap). Resolution: the engagement modifier never *raises* confidence; it can only cap MEDIUM if not already capped.
- **Known:** Report-UI consumers need a new conditional render for the `engagement_modifier` block. A UI sub-issue must be filed under ABA-66 before the feature ships, with acceptance criteria covering all four `status` values (applied / unavailable / no_kpi_mapping / user_skipped). Owner: Anton (UI is solo-maintained). Sequenced after the implementation lands the JSON contract.
- **Resolved by walking-skeleton scope expansion:** Extraction reliability on PDF (META) / HTML (RDDT) / shareholder-letter (NFLX) surfaces — all three are now in-scope for the skeleton, not just META.
- **Resolved by backtest gate:** YoY threshold calibration. The backtest's 40 ticker-quarter sample is the dataset against which the per-ticker vs. global threshold question (OQ2) gets resolved before merge — not after.

## Sequencing & appetite

**This work is structured as a spike-then-build, not a single committed build.** Weeks 1 + 2 are a time-boxed spike whose deliverable is a PROCEED / KILL / RESHAPE decision. Week 3 (the actual implementation, KPI map authoring, UI sub-issue, drift CI) only runs if Weeks 1–2 produce evidence that the approach works. This explicitly applies Universal Rule C5 (time-box every spike; produce a written decision when the box expires) — the design doc is not a commitment to ship; it is a commitment to investigate, with a named bar for what would justify shipping.

**Why spike first:** the load-bearing assumption (YoY engagement leads consensus revision direction) and the load-bearing technical risk (extraction reliability across EDGAR 8-K surfaces, even with deterministic URLs) are both currently at Confidence ≤ 0.5. Spending Week 3's implementation budget before measuring either is the build-trap failure mode. The 8-K-anchoring decision (FR8) removes one form of risk from the spike (URL non-determinism); it does not remove the YoY-leads-revision risk or the extraction-quality risk.

**Total appetite cap: 3 weeks from approval.** Fixed cap, not range. If a gate slips, the plan reshapes (cut scope, simplify, or kill) — it does not extend. The Week 2 → Week 3 transition is the explicit go/no-go.

| Week | Gate | Output | Slip behaviour |
|---|---|---|---|
| **Week 1 — Walking skeleton + feasibility checks** | (a) Three-surface skeleton (META PDF, RDDT HTML, NFLX letter) passes ≥ 80% extraction precision (NFR2) and ±4% cap (NFR4); (b) **reproducibility check** — same-day same-ticker repeat invocation produces identical modifier values across 5 trials per ticker; (c) **backtest data-source feasibility check** — pull one historical ticker-quarter end-to-end (engagement KPI as-published at print date + consensus NTM revenue 4 weeks later); confirm yfinance / alternative source supports this for 40 ticker-quarters | Spike branch with working GATHER step on three tickers; precision + reproducibility fixtures committed; data-source decision documented | If any surface fails after one prompt-iteration round → STOP. If reproducibility fails (modifier value drifts run-to-run) → STOP, this defeats the audit-trail contract. If no viable data source for the backtest → modifier ships disabled-by-default by construction (re-enable path is rolling out-of-sample evidence over 2+ real quarters, not the Week 2 backtest). |
| **Week 2 — ADR pre-registration, then backtest, then ADR finalisation** | (a) **Constants ADR pre-registered** — deadband (±2% YoY), magnitude threshold (8% YoY), ±4% Y1-anchor multiplier cap, base-only application, AND the 60% pass threshold with its justification (anchored against coin-flip baseline: ≥10pp above 50%), all committed **before** the backtest is run; (b) backtest runs blind against pre-registered constants on the 40-candidate / 32-minimum-valid / 24-floor sample; (c) ≥60% revision-direction agreement (NFR7); (d) map-versioning ADR finalised | Backtest test suite green; `docs/adrs/engagement-modifier-constants.md` + `docs/adrs/engagement-kpi-map-versioning.md` merged | If backtest hit rate <60% → **one** constant revision allowed (documented as ADR supersession with explicit "in-sample retune"); a second failure ships the modifier disabled-by-default. Multiple revisions are tuning to noise and require a new ADR with fresh data. |
| **Spike → Build gate (end of Week 2)** | **PROCEED** if: all three extraction surfaces hit ≥80% precision; reproducibility passes; backtest hits ≥60%; both ADRs merged. **KILL** if: precision fails on multiple surfaces with no obvious fix; backtest is materially below 60%; data source is unobtainable. **RESHAPE** if: only one surface fails (drop that ticker from seed); or backtest passes only with a different lever (revenue vs. margin) — re-author the constants ADR and shift Week 3 scope accordingly. | Written go/no-go memo in `docs/design-docs/engagement-kpi-enrichment/spike-decision.md` summarising what was learned, what the evidence shows, and the recommended path. Linked from ABA-66. | KILL closes ABA-66 with the memo as deliverable; the spike's learnings (especially what doesn't work) feed back into the idea bank. PROCEED unlocks Week 3. |
| **Week 3 — Implementation + KPI map + tests + UI sub-issue + drift CI** (only if PROCEED) | Full skill changes merged; KPI-map v1 with schema_version + changelog; smoke + golden + backtest tests green in CI; UI sub-issue filed with acceptance criteria; **weekly drift-CI workflow** authored (confirm existing GH Actions infra or budget setup as named sub-task) | Feature ready to ship to user; ABA-66 closed | If week 3 slips, the half-built feature does not ship — revert the skeleton branch and re-scope. |

OQ resolution sequencing (load-bearing OQs only):
- OQ1 (revenue vs. margin lever) resolves at end of Week 1 from skeleton observations.
- OQ2 (per-ticker vs. global thresholds) resolves at end of Week 2 from backtest data.
- OQ3 (NFLX substitute KPI) resolves at start of Week 1 as part of KPI-map authoring; if no substitute can be authored, NFLX drops from the seed set.
- OQ5 (base-only vs. all-three scenarios) resolves at end of Week 1 and is locked into the constants ADR.
- OQ6 (GOOGL fallback KPI) resolves at start of Week 1; same drop rule as NFLX.

## Operability plan

### Metrics (load-bearing only — this is a personal skill-pack)

Five metrics tied directly to fitness functions; everything else is nice-to-have and can be added if a real question shows up:

- `engagement_modifier_extraction_precision` — golden-fixture pass rate (NFR2). Floor: 80%.
- `engagement_modifier_extraction_tokens{ticker}` — per-invocation in-session token count (NFR6). Cap: 8k.
- `engagement_modifier_base_iv_impact_pct{ticker}` — `(iv_with − iv_without) / iv_without` per applied run (NFR4). Cap: 5%.
- `engagement_modifier_revision_agreement_rate` — rolling-8-quarter outcome metric (NFR7). Floor: 60%; OOS floor 55%.
- `engagement_modifier_kpi_map_drift_check` — weekly dry-run pass/fail per seed ticker (see Alerts).

Nice-to-have (add when a question surfaces): per-ticker invocation counters, YoY-delta distribution, extraction-latency histogram, span-level traces. Skipped in v1 because no one is reading them.

### Structured logs

Each invocation emits one log line at GATHER end. Fields are precisely the ones above plus identifying context:
```
{"event": "engagement_modifier", "ticker": "META", "ai_layer": "INCUMBENT",
 "status": "applied", "kpi_name": "DAP", "yoy": 0.061, "direction": 1,
 "magnitude": "mild", "y1_anchor_multiplier": 1.02,
 "base_iv_impact_pct": 0.018, "extraction_tokens": 5_200,
 "source_accession": "0000-...", "source_type": "edgar_8k_exh99"}
```

### Alerts (thresholds and routing)

This is a personal research tool — no on-call. "Alerts" here means CI fitness functions that block merge:

- Smoke test fails (NFR1 latency, NFR2 precision, NFR4 cap violation) → CI red → cannot merge.
- Golden-fixture extraction precision drops below 80% on the seed set → CI red.
- Token consumption exceeds 8k per invocation in the smoke suite → CI red.
- **Backtest revision-agreement (NFR7) drops below 60%** on the rolling 8-quarter sample → CI red; modifier auto-disables until investigated.
- **Rolling out-of-sample monitor:** after Week-3 launch, every new ticker-quarter outcome (modifier-direction vs. actual consensus revision at 4 weeks post-print) accumulates in a running tally. Floor: **55%** over the trailing 8 fresh ticker-quarters (i.e. excluding the in-sample backtest set). Below the floor → modifier auto-disables and surfaces a one-line notice on next invocation. This is the kill-switch for the "passed in-sample by overfit" failure mode (B8 #4).
- **KPI-map drift CI check** (runs weekly via scheduled GH Action): invokes the modifier in dry-run mode against each seed ticker; if `status != "applied"` for any ticker for >2 consecutive runs, the check fails loudly. Surfaces map staleness within ~2 weeks of a publisher format change.

### Rollback plan

- Per-run: `/stock-model META --no-engagement-modifier` disables the GATHER step entirely.
- Skill-level: a single-commit revert to the skill version preceding the enrichment. Time estimate: ~5 minutes.
- JSON contract: the `engagement_modifier` block is optional with `status: "unavailable"` fallback. Removing the field does not break the report-JSON schema for prior reports.

### Capacity headroom

EDGAR fetch and in-runtime extraction are call-per-invocation; no shared infrastructure to size. Cost is bounded by NFR6 (in-session tokens only).

### Known failure modes with mitigations

| Failure mode | Mitigation |
|---|---|
| Earnings release not yet published (mid-quarter run) | GATHER step finds no fresh release; sets `status: "unavailable"`; skill proceeds without modifier. |
| Web search returns wrong URL (e.g. competitor's press release) | LLM extraction step verifies the ticker name appears in the source. If not, sets `status: "unavailable"`. |
| LLM extracts wrong number (extraction failure) | MIP gate surfaces the number + source URL to the user for confirmation. User rejects → `status: "user_skipped"`. |
| KPI definition changed between quarters (META DAU → DAP) | KPI-map maintenance task; until updated, extraction will likely fail-soft (no KPI value found) and route to `status: "unavailable"`. |
| YoY data unavailable (first-quarter disclosure of a new metric) | Computes QoQ instead if `comparison_basis: "QoQ_fallback"` is set in the KPI map; otherwise `status: "unavailable"`. |
| User runs `/stock-model` non-interactively in CI / batch mode | MIP gate is interactive — for non-interactive runs, the skill emits `status: "unavailable"` and proceeds. (Same behaviour as existing MIP fields in non-interactive contexts.) |

### Upstream / downstream dependency failure modes

- **Upstream — `/stock-signal`:** If `ai_layer` is missing from upstream Signal output, the GATHER step is skipped with `status: "unavailable"`, `status_reason: "missing_ai_layer"`. (Distinct from `no_kpi_mapping`, which means "ai_layer is known but the ticker isn't in `engagement_kpi_map.json`.") No fabrication of AI layer here.
- **Upstream — web-search API:** Transient failures → retry once with 2 s backoff; on second failure, `status: "unavailable"`.
- **Upstream — LLM extraction:** Same retry / unavailable pattern.
- **Downstream — report JSON consumers:** `engagement_modifier` is optional; existing consumers that don't read the field continue to work.
- **Downstream — report UI:** New optional render. UI must handle the four `status` values; missing field treated as `status: "unavailable"`.

## Open questions

| # | Question | Owner | Resolution by |
|---|---|---|---|
| OQ1 | Which lever does the modifier perturb — Year-1 revenue, FCF margin, or both? Revenue is the more direct link to engagement; margin captures monetisation. | Anton | End of Week 1 (walking-skeleton output) |
| OQ2 | YoY thresholds (±2% deadband, 8% strong) — calibrate per-ticker or use single global thresholds? RDDT and META have very different baseline growth rates. | Anton | End of Week 2 (backtest data) |
| OQ3 | NFLX stopped publishing quarterly net-adds in Q1 2025 — what's the substitute KPI? Drop NFLX from seed set if no substitute can be authored. | Anton | Start of Week 1 (KPI-map authoring) |
| OQ4 | KPI-map maintenance cadence — resolved: weekly drift-CI check (see Alerts) plus on-print ad-hoc review the Monday after each seed ticker's earnings date. Authored into `docs/adrs/engagement-kpi-map-versioning.md`. | Anton | RESOLVED in this revision |
| OQ5 | Should the modifier apply to bear/bull scenarios as well, or remain base-only? | Anton | End of Week 1; locked into constants ADR |
| OQ6 | INCUMBENT tickers without disclosed engagement KPIs (e.g. GOOGL) — fall back to "paid clicks YoY %" or skip? Same drop rule as NFLX if no defensible mapping. | Anton | Start of Week 1 (KPI-map authoring) |
| OQ7 | **KPI-discovery skill as v2 follow-on** — hard-coded map is right for v1's 4-ticker seed set, but if the monitored universe grows past ~8 tickers, manual map maintenance becomes the bottleneck. A separate skill (`/stock-kpi-discover TICKER`) could classify the ticker's business model and auto-propose a KPI mapping for human confirmation, writing the result into `engagement_kpi_map.json`. Filed as a separate Linear issue rather than absorbed into ABA-66 — scope is "later" by Now-Next-Later, contingent on v1 succeeding and the universe expanding. | Anton | Filed as separate Linear issue; not v1 scope |
