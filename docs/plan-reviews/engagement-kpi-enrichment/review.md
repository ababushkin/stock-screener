# Plan review: engagement-kpi-enrichment

## Plan reference

`docs/design-docs/engagement-kpi-enrichment/design-doc.md` — Linear ABA-66.

## Inputs

- **Appetite**: not stated in plan (B7 SUSTAINED). Inferred: 3–4 weeks (1 week walking skeleton + 2–3 weeks KPI map + ticker extension + tests + UI). Owner must fix this as a cap before approval.
- **Cynefin domain**: Complex — LLM extraction quality and YoY-threshold calibration are emergent; cannot be deduced upfront, must be measured.
- **Tier**: Full — selected by (a) implied appetite >1 week, (b) ≥3 external dependencies, (c) user-facing output contract touched.

## B0 — Cynefin

Complex. The doc already concedes this implicitly by demanding a walking skeleton. The implication for review: kill-switches and feedback loops matter more than milestone checkpoints. Verify B8 names specific failure-detection conditions, not generic ones.

## B1 — Problem framing

| Check | Verdict | Falsifying condition |
|---|---|---|
| Opens with problem, not solution | OVERTURNED | Plan's first section names affected user, current behaviour, desired behaviour — no stack language until Recommended Approach. |
| Measurable target named | PARTIAL | The plan names *what changes* (Y1 anchor moves by bounded amount) but not *how we'll know the change was an improvement* — see B6. |

## B2 — Scope clarity

| Item | Verdict | Falsifying condition |
|---|---|---|
| Touches report UI conditional render — boundary undefined ("Coordinate with the UI work in CLAUDE.md") | SUSTAINED | A UI sub-task with owner + acceptance criteria exists at approval time. |
| Touches AI-layer classification produced by `/stock:signal` — no fallback if `stages.signal.ai_layer` is missing/wrong | PARTIAL | Plan states "GATHER step skipped → status: no_kpi_mapping" — but doesn't define behaviour when ai_layer is *present but wrong* (e.g. NVDA misclassified as APPLICATION). |
| KPI-map maintenance process touches a versioning + drift-detection mechanism that isn't specified | SUSTAINED | OQ4 is closed with a concrete cadence and a CI check before approval. |
| "Web-search the latest earnings press release" — vendor not named | SUSTAINED | Plan names the specific search API (e.g. Brave, Tavily, native WebSearch tool) with documented cost-per-call. |
| "LLM extraction" — model not named, prompt-engineering scope undefined | SUSTAINED | Plan names the extractor model and commits to a versioned prompt in `skills/_shared/`. |
| "Versioned reference table" at `engagement_kpi_map.json` — versioning mechanism (semver? changelog? schema version field?) not specified | PARTIAL | Schema and changelog convention named. |

**Net:** 4 SUSTAINED, 2 PARTIAL. Scope is wider than the doc admits, in ways that materially affect cost and timeline.

## B3 — Assumptions + evidence quality

| Assumption | Confidence (Gilad) | 5-min test or owner | Verdict |
|---|---|---|---|
| LLM extraction can hit ≥80% precision on press releases across PDF (META) / HTML (RDDT) / mixed (NFLX) surfaces | 0.5 — anecdotal; no prior measurement on this corpus | Walking skeleton on META Q1 2026 (named in plan); extend to NFLX + RDDT before scoping full build | PARTIAL — test named for META only; PDF surface is the riskiest and untested |
| YoY engagement trend is a leading indicator of NTM-revenue *revision direction* (i.e. the modifier moves toward what consensus *will become*, not just toward truth) | 2 — industry consensus, no measurement on this skill | Backtest on 4 tickers × 8 quarters: compare modifier direction vs. analyst-consensus revision direction in the 6 weeks after each print. NOT NAMED in plan. | SUSTAINED |
| ±4% base-IV cap is the right magnitude — neither too small to matter nor too large to disrupt range integrity | 0.1 — pure assertion | No test named. Could be derived from the backtest above (cap = observed median revision magnitude × confidence haircut). | SUSTAINED |
| Web-search results are reproducible-enough that two runs on the same day produce the same modifier (within the `--no-engagement-modifier` reproducibility contract the plan implies) | 0.5 | Run skill 5× on META on same day, log URL + extraction; verify modifier value identical. NOT NAMED. | SUSTAINED |
| MIP gate catches bad extractions because the user will actually verify the source URL each run | 0.5 — assumes attentive user; failure mode is rubber-stamping | Not testable pre-launch. Observable: track `user_confirmed=true` rate vs. extraction-correctness sample. | PARTIAL |

**Net:** 3 SUSTAINED, 2 PARTIAL. The backtest assumption is the load-bearing one — if YoY engagement does NOT lead consensus revision direction, the entire modifier is noise dressed up as signal.

## B4 — Dependencies

| Dependency | Owner confirmed? | Capacity confirmed? | Verdict |
|---|---|---|---|
| Web-search API (vendor unnamed) | No | No (cost not validated on a named vendor) | SUSTAINED |
| LLM extraction model (unnamed) | No | No | SUSTAINED |
| `/stock:signal` AI-layer field | Yes (in code) | Yes | OVERTURNED |
| Report UI consumer | No — "coordinate" is hand-wavy; no Linear sub-issue, no UI owner named | No | SUSTAINED |
| KPI-map maintainer (implicitly Anton) | Implicit | Cadence undefined (OQ4) | PARTIAL |
| Press-release publishers (META IR, NFLX IR, RDDT IR, GOOGL IR) — these are external, format-changing parties | No (not a confirmable owner) | N/A | Documented limitation — acceptable, but the KPI-drift kill-switch (B8 #3) must address it |

## B5 — Reversibility + ADR pairing

| One-way door | Alternatives in plan? | ADR exists / committed? | Verdict |
|---|---|---|---|
| JSON schema addition (`stages.model.engagement_modifier` block) — once consumers depend on it, renaming/removing is breaking | Yes (Alt A/B/C/D with blast radius + reversal cost — well-done) | No ADR committed | PARTIAL |
| Modifier formula — direction/magnitude bands, ±4% cap, base-only application | Partial — Alt B is the chosen approach, but the specific formula constants are not justified against alternatives (why ±2%/±4%? why 8% strong threshold? why base-only vs. all three scenarios?) | No ADR committed | SUSTAINED |
| KPI map v1 ticker set — once written into a production JSON contract, downstream replay/audit depends on the v1 names | Not framed as alternatives | No ADR committed | PARTIAL |
| Decision to use web-search instead of paid feed (Alt B vs Alt D) | Yes, well-justified in doc | The doc itself substitutes for the ADR here — acceptable if cross-linked | OVERTURNED with note: link the design doc as the ADR-equivalent for this decision |

**Net:** The big alternatives discussion (A vs B vs C vs D) is well done — the design doc passes B5 at the architectural level. But the *formula-level* one-way doors (the constants) aren't paired with reasoning, and no ADR is committed for them. SUSTAINED on formula choice.

## B6 — Operability + success metrics

- Metrics: **named** (5 metrics — invocations, YoY delta, latency, base-IV impact, cost)
- Alerts: **named as CI fitness functions** — acceptable for personal-tool context; no on-call exists, so CI red == "alert"
- Rollback path: **named** (`--no-engagement-modifier` flag + single-commit revert)
- Runbook: not named — acceptable given no on-call, marginal
- Capacity headroom: **addressed** (no shared infra)
- **User-visible outcome metric: NOT NAMED.** ← SUSTAINED

This is the load-bearing operability gap. The plan names *input* metrics (extraction precision, latency, cost) and *bounded-effect* metrics (base-IV impact magnitude). It does NOT name an outcome metric — i.e. a measurable answer to "did this modifier actually make the DCF more useful to the user?" Candidates:

- Post-print analyst-revision-direction agreement rate (does the modifier's direction match the direction consensus moves over the following 4–6 weeks?)
- User retention of the modifier value (`user_confirmed=true` rate ≥ X% on the seed set; rubber-stamp rate is a counter-signal)
- Reduction in absolute base-IV vs. post-print consensus drift over 4 weeks (with vs. without modifier)

Without an outcome metric the modifier can be shipped, look correct, and silently fail to move the user's decisions — exactly the build-trap failure mode (Product P1: outcomes, not outputs).

## B7 — Sequencing + capacity

- **Critical path surfaced?** Partially. The doc sequences walking-skeleton → extension, but doesn't name the OQ-resolution → KPI-map authoring → skeleton → extension → ship critical path. OQ1 (lever choice) and OQ2 (thresholds) gate the skeleton; OQ3/OQ6 (KPI map decisions for NFLX/GOOGL) gate the extension.
- **Appetite fixed?** NO — total appetite cap not stated. Open questions have individual deadlines (+3 days, +1 week, +2 weeks) but no total cap. This is the form Universal Rule C1 specifically calls out: "an appetite of '2–4 weeks' is not an appetite; it is a hope" — and a missing total cap is worse than a range.
- **FTE consistent?** N/A — solo.

Verdict: SUSTAINED on appetite cap. The critical path can be derived from the OQ deadlines but should be explicit.

## B8 — Pre-mortem (Full: top 3 + kill-switches for top 2)

**Top failure modes (assume the plan shipped and failed within appetite):**

1. **LLM extraction precision is < 80% on PDF earnings releases (META) and on NFLX's quarterly shareholder-letter format.** Walking skeleton reveals it; project pivots to Alt D (paid feed) or kills the feature; 1–2 weeks of work sunk into the extractor that doesn't ship.
   **Kill-switch:** Walking-skeleton precision measurement on META Q1 2026 + RDDT (HTML) + NFLX (mixed) before scoping ticker 4. If precision < 80% on any of the three after one round of prompt iteration, stop. The doc names META only — extend skeleton coverage to the three surface types.

2. **YoY engagement signal does NOT lead analyst consensus revision direction at the magnitudes/thresholds chosen (B3 assumption).** Modifier ships, runs on every APPLICATION/INCUMBENT call, and silently shifts base IVs in directions uncorrelated with where consensus actually moves. User can't easily tell — the modifier looks plausible per run, but its decision-impact is noise.
   **Kill-switch:** Backtest on 4 tickers × 8 quarters before ship. If hit rate on revision-direction prediction < 60%, kill the feature or pivot to a different lever (e.g. modify FCF margin instead of revenue; or change deadband). The doc does not name this backtest — it must be added as a precondition to merge.

3. **KPI map drifts faster than maintenance cadence.** META renames DAP again, NFLX moves to annual cadence, RDDT splits DAUq. Within 6 months, three of four seed tickers route to `status: "no_kpi_mapping"`; modifier silently never fires; user doesn't notice because the absence is silent.
   **No kill-switch in the plan.** Doc names this only as OQ4. Needs an active CI check: weekly run of the modifier against each seed ticker; if `status != "applied"` for >2 consecutive runs on a ticker, fail loudly so map maintenance is triggered.

## Recommendation

**REVISE** — design-level structure is solid (clear problem framing, well-considered alternatives, bounded blast radius, honest about LLM-extraction risk), but five SUSTAINED conditions must be addressed before approval. None are fatal; all are concrete.

### Conditions (must be resolved before APPROVE)

1. **(B6) Name a user-visible outcome metric.** Recommend: "post-modifier base IV agrees with analyst-consensus revision direction over the 4-week post-print window on ≥ 60% of the seed-ticker quarters in the backtest." This becomes the kill-switch for B8 #2.

2. **(B7) Fix a total appetite cap.** Recommend: 3 weeks from approval, with hard intermediate gates: walking skeleton (week 1), backtest result + threshold calibration (week 2), full implementation + KPI map + tests (week 3). If any gate slips, the plan is reshaped — not extended.

3. **(B3, B4) Name the web-search vendor and the LLM extractor.** Validate the $0.10/invocation cost envelope on the chosen vendor pair, not generic "web search + LLM."

4. **(B3 + B8 #2) Add the backtest plan.** 4 tickers × 8 historical quarters, comparing modifier direction (computed retroactively from past engagement KPIs) against actual analyst-consensus revision direction over the 4-week post-print window. This is the load-bearing test the design currently relies on hope for.

5. **(B5) Commit to a short ADR for the modifier-formula constants** (deadband, magnitude thresholds, base-only application, ±4% cap). Doesn't need to be long — a paragraph each — but the constants are one-way doors once data is written under them, and they currently have no recorded reasoning.

6. **(B2) Tighten three of the four scope-SUSTAINED items:** name the search vendor + extractor model (covers two), define behaviour when upstream AI-layer is wrong (not just missing), and commit to a KPI-map versioning + drift-CI mechanism (which doubles as the kill-switch for B8 #3).

### What is genuinely good in the plan (worth preserving on REVISE)

- Problem statement is concrete, names the user, and avoids solution language.
- Alternatives section with blast-radius + reversal-cost is well done (Alt A/B/C/D).
- Walking-skeleton requirement is explicit and non-negotiable in the consequences section.
- The "what the ticket gets wrong, that this doc reconciles" passage is exactly the kind of honest scope-correction that Agentic P3 demands.
- Bounded effect (±5% on base IV) plus base-only application preserves the existing range-integrity contract.
- Open questions are named with owners and deadlines (rare; most docs omit deadlines).

The doc is closer to APPROVE than to KILL. The five concrete conditions above turn it into APPROVE.
