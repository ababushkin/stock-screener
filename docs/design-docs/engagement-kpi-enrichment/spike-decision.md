# Spike decision — Task 7 (ABA-66)

**Date:** 2026-05-14
**Branch:** `anton/aba-66-eng-kpi-spike`
**Decision:** **RESHAPE → PROCEED.** Pivot the revision signal from wayback-Yahoo NTM-revenue history to **Yahoo Finance live EPS Trend / EPS Revisions**. Ship the modifier production-wired to the new signal; defer NFR7's backtest gate to forward-accumulated samples, with the modifier flag-gated advisory until n≥24.

---

## What the spike found

Tasks 1, 3, 4, 5, 6a–b produced:

- **Mechanically correct extraction pipeline.** EDGAR-direct 8-K Ex 99.1 → regex → derivation works deterministically across META, RDDT, PINS (22/23 quarters extracted clean on Slice B; Task 3 reproducibility harness shows zero drift across 5× trials).
- **Pre-registered constants** (ADR `engagement-modifier-constants.md`): deadband ±2%, strong threshold 8%, input cap ±4%, output cap ≤5%, base-scenario-only application, kill-criterion 60% on n≥24.
- **A data-source blocker** (`backtest-data-source-blocker.md`): wayback's coverage of `finance.yahoo.com/quote/<T>/analysis/` is sparse — only 2/23 ticker-quarters cleared the ±7d/±14d drift gates needed for clean revenue-revision measurement. NFR7's historical backtest is **not viable** on the originally-proposed wayback data source.
- **A live-page discovery** (this turn): Yahoo Finance's live `/analysis/` page exposes an **EPS Trend** table with built-in 7/30/60/90-day revision history, plus an **EPS Revisions** table with up-vs-down analyst-action counts at 7d and 30d windows. Coverage verified across META (58 analysts), RDDT (31), PINS (34), SNAP (40) — all four return complete, well-populated tables.

## The reshape

### What changes in the signal

| | Original design | Pivot |
|---|---|---|
| Source | Wayback snapshots of Yahoo `/analysis/` Revenue Estimate "Next Year" column at T0 (print+1d) and T1 (print+28d) | **Live** Yahoo `/analysis/` EPS Trend "Current" vs "30 Days Ago" (Next Year column) |
| Metric measured | NTM revenue consensus % revision | NTM EPS consensus % revision over trailing 30 days |
| Philosophy | **Lead** — engagement-direction predicts consensus revision before it lands | **Confirm/lag** — engagement-direction agrees with (or contradicts) the revision that has already started |
| Cost | 2 wayback fetches per ticker-quarter; coverage attrition >90% | 1 live fetch per `/stock:model` run; coverage attrition ~0% on seed set |

### What doesn't change

- The KPI-extraction leg (EDGAR 8-K Ex 99.1 → regex → YoY direction × magnitude) is unchanged.
- The pre-registered constants (deadband, magnitude bands, input cap, output cap, base-only) are unchanged.
- The two-cap audit trail (`stages.model.engagement_modifier` JSON with input and output bounds) is unchanged.
- The kill-criterion target (60% direction agreement on n≥24) is unchanged in *value* — what changes is *when* we evaluate it.

### Why EPS instead of revenue

The live page exposes revision history for EPS, not revenue. EPS and revenue revisions move together for analyst-update events (a sell-side analyst updating a model revises both lines in the same publication). Directional correlation between revenue-revision and EPS-revision is therefore high. **For NFR7's purpose (direction agreement only, not magnitude prediction), EPS is a defensible proxy.** The substitution is recorded explicitly so a future post-launch review can audit whether revenue-revision would have produced a different verdict, if/when historical revenue data becomes accessible.

### Lead vs confirm — design implication

The original modifier was framed as a *predictor*: engagement-direction precedes consensus revision; the modifier nudges base IV before the revision lands. The live-data pivot reframes it as a *confirmer*: when engagement direction and 30-day revision direction agree, the modifier activates with full force; when they disagree, it suppresses to neutral.

- **Agree (both +, or both −):** apply the modifier per the C3/C4 caps.
- **Disagree:** suppress the modifier to neutral (multiplier = 1.00) and emit `status: "direction_disagreement"` in the audit trail.
- **Revision-data unavailable:** apply the modifier per C3/C4 (legacy fall-through — preserves modifier function when Yahoo is unreachable).

This is a stronger guardrail than the lead-only design: an engagement print that the market has already disagreed with via post-print revisions doesn't get to push the IV further. The modifier becomes most active in the regime it has the best signal in.

## NFR7 — deferred, not deleted

NFR7 (≥60% direction agreement on n≥24 valid samples) cannot be evaluated *now* with free historical data. Three sub-options were considered:

- **A. Pay for FMP API to backfill historical estimates.** ~$15/mo or free-tier-feasible. Rejected for v1: cost-and-vendor surface for a personal skill-pack is out of proportion to the validation it buys, and the live-page signal gives us most of the practical value without it.
- **B. Use stock-price-change as a revision proxy.** Rejected: too noisy, would degrade NFR7's signal quality.
- **C. (Adopted) Forward-accumulate.** Each `/stock:model` run on an engagement-mapped ticker logs `(engagement_direction, revision_direction, agreement)` into a JSONL file (`tests/fixtures/engagement_kpi/forward_log.jsonl`). When n≥24 unique ticker-quarter samples accumulate, the backtest gate is re-evaluated. Until then, the modifier ships **advisory-mode** (flag-gated, off by default).

Forward accumulation is the smallest correct response: it uses real production runs as the validation dataset, doesn't introduce a paid dependency, and surfaces the NFR7 result on a timescale that matches the user's actual usage cadence rather than a backfill push.

## What ships in Phase 4 (Tasks 8–14)

1. **Task 8** — Versioning ADR for `engagement_kpi_map.json` schema (already in flight; PINS at v2 is the first practical bump).
2. **Task 9** — Wire `/stock:model` to read the latest 8-K Ex 99.1 KPI and apply the modifier per the pre-registered constants.
3. **Task 10** — Wire the Yahoo live `/analysis/` fetch + EPS Trend extraction (deterministic regex against the rendered HTML; no JS execution at read time, same path that worked across all 4 tested tickers).
4. **Task 10b (new)** — Forward-log emission: append `(ticker, period, engagement_direction, revision_direction_30d, agreement, run_ts)` to `forward_log.jsonl` on every applied run.
5. **Task 11** — Audit-trail JSON shape (`stages.model.engagement_modifier` with `kpi`, `revision`, `agreement`, `multiplier`, `clamped_from`, `status`).
6. **Task 12** — Golden fixture tests covering both the KPI extraction and the Yahoo-live extraction paths.
7. **Task 13** — Report UI integration (modifier surfaced in base column with tooltip explaining the lag-confirm framing).
8. **Task 14** — Documentation update: design doc flipped to **accepted** with explicit superseding note over the original lead-prediction framing.

### Flag-gating

- Default state for v1: **off** (`--engagement-modifier` opt-in).
- When opted in, the modifier applies per C1–C5 with the agreement-suppression guardrail from §"Lead vs confirm" above.
- When n≥24 forward samples accumulate and direction-agreement ≥60% on the accumulated set, a follow-up ADR flips the default to **on**. Failing that bar at n=24 → kill the modifier and remove it from `/stock:model`.

## Why this isn't a kill

The kill criterion in the Task 5 ADR was "C6 sub-60% twice in-sample." We are not at that gate — we never *ran* the backtest. The blocker is data availability, not signal failure. The mechanical pipeline works, the constants are defensible, and the live signal substitutes a workable revision-direction observation for the unobtainable historical revision-direction. Killing the spike here would discard a real lever that has 4-ticker live-data coverage validated today, on the grounds that we couldn't validate it against 2-years-ago data we can't access.

The forward-accumulation path makes the eventual NFR7 gate **harder** to game (production runs, not curated fixtures) at the cost of taking longer to fire. That's an acceptable trade for a personal research skill-pack with no external launch pressure.

## Risks taken with this reshape

| Risk | Likelihood | Mitigation |
|---|---|---|
| EPS-revision direction diverges from revenue-revision direction often enough to weaken the signal | Low (analyst updates revise both lines together) | Audit trail records both `revision_pct` (EPS) and the count signal (`up_30d`, `down_30d`); a post-launch review at n=24 compares to revenue-revision direction if FMP-tier data becomes accessible |
| Yahoo restructures the live `/analysis/` page DOM | Low (stable structure across 5+ years per Task 4 spot-check; verified 2026-05 across 4 tickers) | Yahoo-extraction lives behind a single regex bank with structured-failure fallback to "revision_unavailable" → modifier still applies per C3/C4, just without the agreement guardrail |
| Yahoo blocks programmatic access from the runtime IP / requires JS | Currently no — plain GET works; verified across 4 tickers in Playwright session | If it ever requires JS rendering, document fallback to `--engagement-modifier-no-revision` (agreement guardrail off) and flag the gap to user |
| Direction-disagreement suppression masks signal that would otherwise have validated | Moderate but acceptable | The forward log records the **pre-suppression** decision too, so the accumulated dataset preserves the engagement-only direction agreement evidence for the eventual NFR7 evaluation |
| Forward-accumulation takes longer than the user's patience for an NFR7 verdict | High in absolute terms (n=24 may take 6–12 months of real use) | The modifier is advisory-only during that window; nothing about the audit trail or report UI implies validated status before the gate fires |

## Linkage

- Supersedes the wayback path in `backtest-data-source.md` (Task 4) per `backtest-data-source-blocker.md`.
- Preserves the pre-registered constants in ADR `engagement-modifier-constants.md` (Task 5) without revision — this is a data-source pivot, not a constant retune; the one-revision budget remains unspent.
- Modifies the design doc (`design-doc.md`): the revision lever changes from NTM revenue → NTM EPS (live), and the gate from "in-sample backtest" → "forward-accumulated n≥24." Design doc to be updated to **accepted** in Task 14 with this memo cited as the superseding decision.
- Resolves Task 7. Tasks 8–14 begin with the reshape in effect.

## Decision

**RESHAPE → PROCEED.** Tasks 8–14 are unblocked. Modifier ships **advisory + flag-gated default-off**; NFR7 gate deferred to forward-accumulated n≥24 with the same 60% threshold.
