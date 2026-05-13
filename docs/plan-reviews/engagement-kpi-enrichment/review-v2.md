# Plan review v2: engagement-kpi-enrichment (post-revision)

Re-review of `docs/design-docs/engagement-kpi-enrichment/design-doc.md` after the owner addressed the six conditions in `review.md`. Focus: whether the revisions hold and whether the revisions themselves introduce new defects.

## Inputs

- **Appetite**: 3 weeks (now stated, fixed cap).
- **Cynefin domain**: Complex (unchanged).
- **Tier**: Full (unchanged — still touches user-facing output contract).

## Conditions from review v1 — disposition

| # | Condition | Disposition |
|---|---|---|
| 1 | B6 outcome metric | **CLOSED.** NFR7 names revision-agreement ≥ 60% on 32 ticker-quarter backtest with a hard floor and CI fitness function. |
| 2 | B7 appetite cap | **CLOSED.** 3 weeks fixed, weekly gates with explicit slip behaviour. Critical path of OQ resolution sequenced. |
| 3 | B3/B4 vendor naming | **CLOSED in an unexpected way.** FR8 collapses the search + extractor stack to Claude Code's native `WebSearch` + same-Claude extraction. Eliminates two external dependencies entirely. Cost reframed from $/invocation to in-session tokens (≤ 8k). |
| 4 | B3/B8 backtest plan | **CLOSED.** 32 ticker-quarters, ≥ 60% pass condition, ship-disabled-by-default if fails. Fixture-frozen so future changes can re-evaluate. |
| 5 | B5 ADR commitments | **CLOSED.** Two named ADRs, both blocking merge: `engagement-modifier-constants.md` and `engagement-kpi-map-versioning.md`. |
| 6 | B2 scope tightening | **CLOSED on 4/4 prior SUSTAINEDs** (UI ownership + sequencing, AI-layer wrong behaviour, search vendor, extractor model, KPI-map versioning). |

All six prior conditions are addressed. New B2 / B3 / B8 hits surface from the revisions themselves below.

## B2 — New scope items introduced by the revision

| Item | Verdict | Falsifying condition |
|---|---|---|
| FR8 couples the skill to running inside Claude Code specifically — if invoked from a different harness (e.g. a future scheduled cron context, or an alternative MCP host), the extraction stack is no longer available | PARTIAL | Skill explicitly documents the runtime requirement and emits `status: "unavailable"` outside Claude Code, OR confirms the skill is only ever invoked from Claude Code in this project. |
| Backtest data source — "yfinance historical estimates if available, otherwise hand-collected from archived analyst notes" — "hand-collected" is a scope landmine that could swallow Week 2 | SUSTAINED | Week 1 spike includes a feasibility check on the data source: pull one historical ticker-quarter end-to-end (estimate-revision direction over 4 weeks) and confirm yfinance returns enough granularity. If not, name the substitute source before Week 2 begins. |
| GH Actions weekly drift-CI check — repo doesn't currently have GH Actions infrastructure documented; setup is implicit scope | PARTIAL | Either confirm existing GH Actions workflow exists in this repo, or budget the workflow setup as a named Week 3 task. |

## B3 — New assumptions introduced by the revision

| Assumption | Confidence (Gilad) | 5-min test or owner | Verdict |
|---|---|---|---|
| The 60% backtest pass threshold itself is well-calibrated (not too lax, not too strict) | 0.1 — pure assertion | Justify in the constants ADR alongside the other constants. Anchor against a baseline: e.g. "naive coin-flip = 50%; an analyst's median over the same window hits N%; we require 10pp above coin-flip." | SUSTAINED |
| Constants (±2%/±4%/8%) are pre-registered in the ADR *before* the backtest is run — not tuned post-hoc to hit 60% on the 32-quarter sample | 0.5 — implied by the doc but not explicit | Add an explicit ordering rule to Week 2: ADR constants are committed first, backtest runs against them blind, only one revision allowed if the result fails. | SUSTAINED |
| Web search + extraction reproducibility (carried from v1 — not addressed by the revision) | 0.5 | Run skill 5× on same ticker same day; log URL + extraction; verify modifier value identical | SUSTAINED (carried from v1) |

## B4 — Dependencies (delta)

All prior SUSTAINEDs cleared. New dependency surface: GH Actions infra (PARTIAL above). Historical-estimate data for backtest (PARTIAL above). No new external vendor.

## B5 — Reversibility + ADR pairing (delta)

Two ADRs now committed (✓). The formula-constants ADR has the right scope to absorb the two new B3 SUSTAINEDs above — just needs to explicitly cover the 60% threshold justification and the pre-registration ordering rule. No new one-way doors introduced by the revision.

## B6 — Operability + success metrics (delta)

NFR7 added as outcome metric (✓). Two new metrics added (`extraction_tokens`, `revision_agreement_rate`). All operability sub-fields populated for a personal-tool context. **CLOSED.**

## B7 — Sequencing + capacity (delta)

Appetite is fixed at 3 weeks with named weekly gates and slip behaviour. Critical path of OQ resolution sequenced. **CLOSED.** One minor note: Week 2 carries both backtest execution AND two-ADR authoring; if the data-source feasibility check (new B2 PARTIAL above) fails, both backtest and ADRs slip. Worth naming as the Week 2 single point of failure.

## B8 — Pre-mortem (revised)

The three original failure modes now have kill-switches:
1. Extraction precision fails on PDF/letter → Week 1 gate stops at end of Week 1.
2. YoY signal doesn't lead consensus revision → Week 2 backtest gate; modifier ships disabled-by-default.
3. KPI map drift → weekly drift-CI check fires within ~2 weeks.

Two new failure modes the revision creates:

4. **Backtest passes via overfit.** Constants are silently tuned (or selected with hindsight) to hit 60% on the 32-quarter sample. Out-of-sample (next 4 quarters) hit rate is 50% — pure noise — but the feature ships because the in-sample test passed.
   **Kill-switch:** Pre-registration ordering rule baked into Week 2 — constants committed in ADR before backtest runs. Plus a rolling out-of-sample monitor (`engagement_modifier_revision_agreement_rate` metric, already named) with a hard floor that auto-disables the feature if it drops below 55% over the next 4 real quarters.

5. **Backtest data is unobtainable in Week 2.** yfinance doesn't expose snapshot-dated historical estimates (only current rolling NTM). Hand-collection from archived analyst notes for 32 ticker-quarters is infeasible in one week. Backtest becomes nominal — the team runs whatever data it has, with hit rate undefined; the NFR7 fitness function becomes ceremony.
   **Kill-switch:** Week 1 data-source feasibility check (new B2 item above). If yfinance is insufficient and no alternative source is available within 2 days, the backtest is dropped and the modifier ships disabled-by-default by construction (not as a fallback) — re-enable only after manual evidence accumulates over 2+ quarters.

## Recommendation

**REVISE** — but only narrowly. The revision addressed all six prior conditions cleanly and substantively. Two new SUSTAINED items emerge — both of which can be absorbed into the already-committed constants ADR by expanding its scope; no further design-doc rewriting is needed.

### Conditions (narrow, scope into existing ADR / Week 1)

1. **(B3) Pre-register backtest constants and the 60% threshold in the constants ADR before Week 2 backtest runs.** ADR records: deadband, magnitude threshold, ±4% cap, base-only application, AND the 60% pass threshold with its justification (e.g. ≥ 10pp above coin-flip). Only one constant revision allowed post-result; further iterations require a new ADR.
2. **(B2) Add a Week 1 data-source feasibility check** for the backtest's historical analyst-consensus revisions. If yfinance is insufficient, name the substitute source before Week 2 starts, OR ship the modifier disabled-by-default by construction with the rolling-out-of-sample monitor as the only re-enable path.
3. **(B2 / B7) Confirm or budget GH Actions infrastructure** for the weekly drift-CI check — single line in Week 3 sequencing, no further design work needed.
4. **(B3 carried)** Reproducibility test for web-search + extraction — fold into Week 1 skeleton acceptance criteria: same-day same-ticker repeat run must produce identical modifier values.

None of these require structural redesign. All four can be absorbed in <30 minutes of editing the design doc + ADR scope notes.

### What is genuinely good about the revision

- FR8 (collapsing the search + extractor stack to in-runtime Claude Code) is the right kind of simplification — removes two external dependencies, eliminates the cost-per-invocation question, and reduces failure modes.
- NFR7 with a hard kill-switch (ship disabled-by-default if backtest fails) honestly addresses the load-bearing assumption rather than papering over it.
- Sequencing has explicit slip behaviour per gate — Universal Rule C1 ("appetite is a cap, not a target") in operational form.
- Two named ADRs is appropriate scope; not over-architected.
- The "what we resolved by adding scope" framing under Integration risks is honest about which earlier hand-waves got real treatment.

The plan is one focused editing pass from APPROVE.
