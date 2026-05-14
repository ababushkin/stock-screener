---
id: ADR-engagement-modifier-constants
status: accepted
date: 2026-05-14
authors: Anton Babushkin
linear: ABA-66
supersedes: none
---

# ADR — Engagement-modifier constants (pre-registered)

## Status

**Accepted.** Pre-registered before the Task 6 backtest is run, so the backtest cannot be tuned to its own answer. One in-sample revision is permitted (recorded as a superseding ADR with explicit "in-sample retune" rationale); a second failure ships the modifier disabled-by-default per the design-doc Week-2 → Week-3 gate.

## Context

`/stock:model` is being extended with an engagement-KPI–driven base-IV modifier (design doc: `docs/design-docs/engagement-kpi-enrichment/design-doc.md`, ABA-66). The modifier reads the latest as-published engagement KPI (e.g. META DAP, RDDT DAUq) from EDGAR 8-K Ex 99.1, classifies the YoY trend into a direction × magnitude band, and perturbs the Year-1 revenue anchor by a small bounded multiplier. The full effect is then clamped against an output cap on base IV.

The numerical constants that govern this pipeline have to be fixed **before** the Task 6 backtest runs. Otherwise the backtest's hit rate becomes a function of constant tuning, and NFR7 (≥60% revision-direction agreement) collapses into circular validation. This ADR records each constant, the alternative considered, and the data point that would prompt a revision.

Tasks 1, 3, and 4 (walking-skeleton spike, reproducibility harness, backtest data-source feasibility) are complete and inform the choices below.

## Decision

The following constants are pre-registered for the Task 6 backtest and for the eventual production wiring (Tasks 8–14):

### C1 — Deadband: ±2% YoY

If `abs(yoy_change) < 0.02`, set `direction = 0`, `magnitude = "neutral"`, `base_anchor_multiplier = 1.00` (no-op).

**Reasoning.** Reported YoY KPI deltas in the seed-ticker set cluster tightly around their long-run trend (META DAP YoY oscillates 3–8% quarter-over-quarter; RDDT DAUq 15–25%). A 2% deadband filters reporting-noise-tier changes (rounding in stated KPI, mix-shift artefacts) without absorbing meaningful inflections. The two spike samples (META +4%, RDDT +17%) both sit well outside the deadband, confirming the threshold doesn't reject the actual signal.

**Alternative considered.** ±1% (tighter; risks reading rounding as signal) and ±3% (looser; risks absorbing the bottom edge of meaningful META decel). Both rejected as worse on the seed set.

**Revision trigger.** If backtest direction-agreement is <60% AND ≥30% of misses occur on |YoY|<3% samples, the deadband may be widened to ±3% as the single permitted in-sample retune.

### C2 — Strong-magnitude threshold: 8% YoY

If `abs(yoy_change) >= 0.08`, `magnitude = "strong"`; otherwise `magnitude = "mild"`.

**Reasoning.** 8% separates META's normal DAP cadence (mid-single-digit YoY) from clearly out-of-trend prints (≥8% accel or decel signals a regime change). RDDT's print cadence is structurally higher (mid-teens to mid-twenties), so RDDT prints land in `strong` by default — which matches the intuition: a high-growth app's signal is louder per unit of YoY-change. Spike samples (META 4% → mild; RDDT 17% → strong) match the intended classification.

**Alternative considered.** Per-ticker thresholds (calibrated to each ticker's baseline volatility). Rejected for v1 because (a) it doubles the surface area to tune without backtest evidence supporting the lift, and (b) the global threshold's failure mode is well-defined — it under-weights large-cap signals and over-weights high-growth signals. OQ2 in the design doc explicitly defers per-ticker calibration to post-backtest evidence.

**Revision trigger.** If backtest shows direction-agreement is materially asymmetric between mild and strong samples (e.g. strong agrees ≥70%, mild agrees ≤50%), this is the prompt to move to per-ticker thresholds — but that revision creates a *new* ADR with fresh data, not an in-sample retune of this one.

### C3 — Input cap: ±4% on Year-1 revenue anchor

`base_anchor_multiplier = 1 + direction × (0.02 if mild else 0.04)` → ∈ [0.96, 1.04].

**Reasoning.** ±4% caps the modifier's input perturbation at a level smaller than the typical quarter-to-quarter analyst-consensus revision (which empirically runs ±2–6% on the seed set). The modifier should nudge the Y1 anchor in the direction of where consensus is *about to revise*, not anticipate the revision's full magnitude. ±4% is the largest input perturbation that, combined with the C4 output cap, holds the design's claim that the modifier is a directional nudge rather than a re-forecast.

**Alternative considered.** ±2% (too small — strong signals get the same nudge as mild ones; loses the magnitude band) and ±6% (too large — under leveraged DCF sensitivities the output cap C4 binds frequently, defeating the input cap's purpose). ±4% is the value where the input cap and the output cap are both occasionally binding, which is the desired regime.

**Revision trigger.** If, post-Task 6, the input cap binds on >40% of samples while the output cap binds on <10%, the input cap is too tight; if the output cap binds on >30% while the input cap is rarely the active constraint, the input cap is too loose. Either case prompts re-authoring (new ADR).

### C4 — Output cap: ≤5% on base IV

Post-application, if `abs(base_iv_after / base_iv_before − 1) > 0.05`, clamp the multiplier downward until the IV impact is ≤5%, and record `status: "clamped"` with `clamped_from: <original_multiplier>` in the JSON.

**Reasoning.** The modifier exists to nudge IV in the direction of expected consensus revision, not to dominate the valuation. A 5% IV ceiling means the modifier can never single-handedly flip a base-case verdict; it can only shade it. Combined with C3, this enforces two-level defense in depth: an input bound that's easy to reason about and an output bound that catches DCF leverage edge cases.

**Alternative considered.** A single output cap with no input cap (simpler, but loses the auditable narrative — "we said the modifier was a ±4% nudge" reads better than "we said it was a ≤5% effect, derived"). Rejected for explainability reasons.

**Revision trigger.** If `engagement_modifier_base_iv_impact_pct` regularly exceeds 5% pre-clamp (>20% of applied runs) the cap is doing real work — that's fine, no revision. If the cap *never* binds, C3 is conservative enough that C4 is dead weight, and a future ADR may simplify.

### C5 — Base-scenario only

The multiplier is applied to the **base** scenario's Y1 anchor only. Bull and bear scenarios are unaffected.

**Reasoning.** Bull and bear scenarios have their own intentional bias by construction (optimistic / pessimistic growth assumptions). Compounding an additional engagement-direction nudge onto them double-counts: a positive engagement print already partially explains why the bull scenario is bull-shaped. The modifier targets the *central* estimate where the analyst-consensus-revision signal it tracks is most directly priced. This also preserves scenario-axis independence — the bull–base–bear spread is unchanged by the modifier (it shifts the central value, not the width).

**Alternative considered.** Apply to all three scenarios (more dramatic, more confusing). Apply only to bear when KPI is negative / only to bull when KPI is positive (asymmetric — risk: looks like cherry-picking to reinforce conclusions). Both rejected. The base-only choice resolves OQ5 in the spike-outputs note.

**Revision trigger.** If post-launch the user reports that bull/bear scenarios feel "stale" relative to base after a strong engagement print, the resolution is more likely a UI clarification (the spread shifts with base, since bull = base × multiplier and bear = base × multiplier) than an ADR change. Revisit only on direct evidence that scenario-axis independence is causing decision-confusion.

### C6 — Backtest-pass threshold: 60% direction agreement on ≥24 valid samples

NFR7 ships only if Task 6's revision-direction agreement is **≥60%** on **≥24 valid ticker-quarter samples**.

**Reasoning.** The null hypothesis for direction agreement is 50% (coin-flip). For the modifier to be load-bearing it must demonstrate a meaningful lift above coin-flip. ≥10pp above 50% is the smallest lift where, on a 24-sample test, the result is unlikely to be noise (binomial p-value ≈ 0.27 for exactly 60% on n=24; tightens fast as n grows toward the 40-sample target). 60% is therefore: high enough to rule out coin-flip-with-noise, low enough that a single calibration miss doesn't sink an otherwise-real signal, and clear enough to be a falsifiable up-front commitment.

**Alternative considered.** 55% (closer to noise floor; not enough lift to claim the modifier is doing work). 65–70% (too aggressive for v1; the seed-set sample is small and even a real signal might not clear it). Both rejected.

**Revision trigger.** The threshold itself is not revisable in-sample. If Task 6 returns 55–59%, the design-doc Week-2 → Week-3 gate fires: one in-sample constant revision (most likely C1 or C2) is permitted, then the backtest re-runs against the same threshold. A second sub-60% result ships the modifier disabled-by-default with `--engagement-modifier` as opt-in.

## Consequences

**Positive.**

- Task 6 backtest runs against fixed constants — its hit rate is an honest test of the underlying signal, not of constant tuning.
- The audit trail (`stages.model.engagement_modifier` JSON) records every constant the run used, so downstream replay produces identical output.
- The two-cap structure (C3 input + C4 output) is explainable to a reader in two sentences without requiring DCF intuition.
- Pre-registering 60% as the kill criterion makes the spike→build gate falsifiable on evidence rather than negotiation.

**Negative.**

- Global thresholds (C1, C2) under-fit the variance between META-class and RDDT-class signals. The design accepts this for v1 in exchange for not double-spending the in-sample revision budget on per-ticker calibration before the backtest has run.
- Base-only application (C5) means a strong engagement print does not visibly perturb the bull or bear scenarios — users who don't read the doc may miss why. Mitigation: the report UI surfaces the modifier in the base column with a tooltip noting the scenario-axis-independence rationale (Task 11/12 scope).
- One-revision budget creates pressure to "spend" it on the first sub-threshold result rather than investigate root cause. Mitigation: a revision requires explaining which constant moved and why, recorded as a superseding ADR.

**Neutral / open.**

- OQ1 (revenue vs. FCF-margin lever) is not resolved by this ADR. The Y1 anchor named throughout is the **revenue** anchor per the design-doc default. If Task 9 (live wiring) surfaces a reason to perturb the FCF-margin path instead, that is a new ADR.

## Linkage

- Design doc: `docs/design-docs/engagement-kpi-enrichment/design-doc.md` §Constraints (FR3, FR4), §Recommended approach §3.
- Spike outputs: `docs/design-docs/engagement-kpi-enrichment/spike-outputs.md` (META and RDDT classification samples).
- Feasibility note: `docs/design-docs/engagement-kpi-enrichment/backtest-data-source.md` (Task 4 — data-source path used by C6's backtest).
- Task plan: `docs/tasks/engagement-kpi-enrichment.md` (Task 5 = this ADR; Task 6 = backtest gated on it).
