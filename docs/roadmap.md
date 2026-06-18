# Roadmap

Last updated: 2026-05-17
Cycle: 2026 H1 reshape

This roadmap was reshaped after the operator's M5-era learnings about how the pack is actually being used (portfolio-level decisions, opportunity-cost vs benchmarks, triangulation with external tools, plain-language interpretability). It replaces any prior implicit prioritisation.

## Strategic priorities

1. **Make existing IVs trustworthy.** Without correctness fixes landed, no output is decision-grade. P0.
2. **Deepen coverage on the seven holdings.** Playbooks are how depth-over-breadth becomes real. The covered list = the actual holdings; per-ticker depth is the differentiator.
3. **Make outputs legible.** Plain-language narrative + trajectory visuals + "explain this number" so the operator understands and trusts each output.
4. **Portfolio + opportunity-cost view.** See the seven as a set; compare IV-vs-price gaps and forward returns against SPY / QQQ baselines.
5. **External triangulation discipline.** Codify the AlphaSpread reconciliation pattern as a checklist (no build) so deltas with third-party IVs get reasoned about, not ignored.

## Cycle 1 goal (2026-05-17 → 2026-05-24)

Turn `/stock-model` from a generic intrinsic value calculator into a reliable stock analysis tool that can be used across the portfolio. Fix the remaining trust issues, make the reasoning behind each valuation easy to understand, show deeper company-specific analysis on the first two stocks, and support portfolio-wide comparisons in a single run.

### Outcomes — how we'll know it worked

1. **The model can be trusted.** The remaining free cash flow base-year issue (ABA-104) is either fixed or clearly documented with evidence and a recommended next step. The model output no longer carries major reliability warnings.
2. **The analysis is tailored to each company.** At least two of the seven covered stocks use company-specific assumptions instead of generic defaults. The output clearly shows which assumptions were changed and why.
3. **Portfolio comparisons work in one step.** The model can answer questions like "Which stock currently has the biggest gap between intrinsic value and market price?" without manual work outside the tool.
4. **The valuation is understandable to non-experts.** A reader can follow how a valuation was produced, what assumptions matter most, and what could change the result, while still being able to trace the underlying data.
5. **The model shows how outcomes can change.** At least one stock model includes a visual view of bear, base, and bull scenarios, along with how the valuation changes over time, directly in the UI.

### Bets backing each outcome

| Outcome | Backing issue(s) |
|---|---|
| 1 — Trusted model | ABA-104 (base-year FCF spike) |
| 2 — Company-specific analysis | ABA-112 (playbook loader) + ABA-116 (ASML) + ABA-117 (GOOG) |
| 3 — Portfolio comparisons | ABA-119 (`/stock-portfolio`) |
| 4 — Understandable valuations | ABA-118 (`/stock-explain`) |
| 5 — Scenario / trajectory visuals | ABA-115 (glidepath + scenario fan) |

### Anti-goals (deliberately not this cycle)

- New ticker coverage beyond the seven
- OSS release work
- UI polish beyond the Model tab (Signal / Timing / Summary / badges / PDF)
- M6 router orchestration
- M2.5 MCP data gaps (ABA-67 / 68 / 69 / 75)

### Cycle health check at 2026-05-24

Per roadmap Rule D1 + universal Rule D2 (post-launch impact review):

- For each shipped bet: did it produce the outcome it was meant to?
- For the playbooks: did the overrides change the IV materially, or only cosmetically — and by how much?
- Did `/stock-explain` and `/stock-portfolio` get used after they shipped, or sit idle?
- What's the smallest next bet to make each outcome stick?

## Capacity allocation

| Category | % of capacity |
|---|---|
| Tech foundation (correctness) | 25% |
| Differentiator — coverage depth (playbooks) | 30% |
| Differentiator — legibility (narrative + visuals) | 20% |
| Differentiator — portfolio + benchmark | 15% |
| Table-stakes — router + data gaps | 10% |
| Embarrassments / KTLO / Speculative | 0% (deliberate; absorbed into Later) |
| **Total** | **100%** |

Customer specials: N/A — single-operator pack. The mix above is intentionally heavy on differentiators because the pack's whole reason for existing is depth on a curated set.

## Theme distribution

| Item | Theme | Confidence | Slot |
|---|---|---|---|
| ABA-110 SBC strip | tech | 9 | Done (2026-05-17) |
| ABA-111 Growth-rate ceiling | tech | 9 | Done (2026-05-17) |
| ABA-104 Base-year FCF effect | tech | 7 | Now |
| ABA-112 Playbook loader | diff | 8 | Now |
| Write playbook: ASML | diff | 8 | Now |
| Write playbook: GOOG | diff | 8 | Now |
| `/stock-explain` skill | diff | 7 | Done (2026-05-20) |
| `/stock-portfolio` skill | diff | 6 | Now — shipped 2026-05-17, pending QA |
| ABA-115 Glidepath + scenario fan visuals | diff | 7 | Now |
| Write playbooks: META, NVDA, AMZN, NFLX, ADYEN | diff | 7 | Next |
| Benchmark overlay (SPY/QQQ on portfolio view) | diff | 6 | Done (2026-06-18) — ABA-125 |
| ABA-67 Bookings/backlog fetch | ts | 7 | Next |
| ABA-68 EPS revisions tool | ts | 7 | Next |
| ABA-69 Next-earnings-date tool | ts | 7 | Next |
| ABA-75 EDGAR SBC fallback | ts | 7 | Next |
| ABA-65 Segment-revenue trend | diff | 6 | Next |
| ABA-42 UI Model tab | diff | 6 | Next |
| ABA-43 UI sensitivity table | diff | 6 | Next |
| ABA-36/37/38/39 M6 Router chain | ts | 7 | Next |
| ABA-62 Router QA | ts | 7 | Next |
| ABA-63 Router install check | ts | 7 | Next |
| ABA-40/41/44/45/46 UI polish (Signal/Timing/Summary/badges/PDF) | incr | 6 | Later |
| ABA-64 Playwright e2e | tech | 6 | Later |
| ABA-107/108 KPI coverage page + helper | incr | 5 | Later |
| ABA-105/103/109/113/95 Spikes + ADR + drift live + parity | tech | 5 | Later |
| AlphaSpread reconciliation checklist (doc only) | diff | 7 | Later (doc work) |
| ABA-50/51/52/53/54/55/56/57 OSS release prep | spec | 6 | Later |

## Now

### ABA-110 SBC strip + ABA-111 growth-rate ceiling — DONE 2026-05-17
**Problem:** For the operator, un-stripped SBC and trough-extrapolated FCF growth were causing `/stock-model` IVs to be systematically inflated — making every output non-decision-grade.
**Outcome:** Both shipped same day. `/stock-model` now strips SBC from the FCF base and applies a consensus/fallback growth-rate ceiling. Reports going forward are decision-grade on the correctness axis; CLAUDE.md "built on sand" caveat lifts.
**Theme:** tech foundation
**Follow-up:** ABA-104 spike (base-year FCF effect) still open — paper-cover that ABA-111 only partially addresses.

### ABA-104 Base-year FCF growth-rate spike
**Problem:** For the operator, we believe the choice of FCF base-year is causing unstable growth-rate inputs (one weak quarter dominates the projection). Without resolving this, ABA-111 partially papers over the symptom rather than fixing the cause.
**Success criterion:** Spike output recommends a base-year selection rule (rolling avg vs trailing single year vs analyst NTM); recommendation either implemented or filed as a follow-up issue with rationale.
**Appetite:** 2 days. Spike, not a build.
**Theme:** tech foundation

### ABA-112 Playbook loader for watchlist tickers
**Problem:** For the operator, we believe generic ESTABLISHED/EMERGING defaults are causing per-ticker output to smooth over the specialist knowledge (capex-cycle position, segment mix, governance facts) that's the whole reason the seven names are covered.
**Success criterion:** `/stock-model TICKER` on a covered ticker loads `playbooks/TICKER.md`, applies its overrides, and names which fields were overridden in the OUTPUT block. Verified on at least one playbook end-to-end.
**Appetite:** ~1 week. Cap.
**Theme:** differentiator

### Write playbook: ASML
**Problem:** For the operator, we believe ASML's EUV-monopoly + capex-cycle + China-overhang structure cannot be captured by generic ESTABLISHED defaults. Without a playbook, the IV will look reasonable and be wrong on the swing factor.
**Success criterion:** `playbooks/ASML.md` written per the structure in COVERAGE.md; `/stock-model ASML` produces output that reflects the playbook overrides (cap source named, narrative applied, audit trail intact).
**Appetite:** 2–3 days after ABA-112 lands.
**Theme:** differentiator

### Write playbook: GOOG
**Problem:** As above, for GOOG — the AI-search-disruption debate is the central question and generic defaults won't engage with it.
**Success criterion:** `playbooks/GOOG.md` written; `/stock-model GOOG` reflects overrides; sell-side disagreement axes are surfaced in output.
**Appetite:** 2–3 days after ABA-112 lands.
**Theme:** differentiator

### `/stock-explain` skill — DONE 2026-05-20 (ABA-118)
**Problem:** For the operator, we believe model outputs use sophisticated terminology that's correct but not understandable on a quick read — making the IV a "stupid number" rather than something usable. Existing skills' methodology sections are present but dense.
**Success criterion:** New `/stock-explain TICKER` skill takes the latest report for a ticker and produces a plain-English walkthrough — what the number means, how it was derived, what assumptions are doing the work, what would change it. Tested on two reports; operator confirms it reads as friendly without losing the audit trail.
**Outcome:** Shipped. `skills/stock-explain/SKILL.md` reads the latest cached report and emits a five-question narrative (bottom line / how it was built / what's driving it — including WACC-to-interest-rate framing and an implied year-5 free cash flow anchor / failure modes / qualitative trust context). Three iterations on the eval loop; operator approved iter-3 output on NVDA + META as journalistic and decision-grade. Read-only — no MCP calls, no writes to `reports/`.
**Appetite:** ~1 week.
**Theme:** differentiator (legibility)
**Notes:** Separate skill, not an inline output section — keeps existing outputs unchanged and lets the explainer evolve independently. Per operator: "i need to understand how the valuation system works."

### `/stock-portfolio` skill
**Problem:** For the operator, we believe the current per-ticker pattern is causing portfolio-level questions ("which of my seven is most overvalued right now?") to require manual aggregation — which means they don't happen.
**Success criterion:** `/stock-portfolio` runs the screen + signal (and reads latest cached model) on all seven covered tickers, produces a ranked table: ticker / current price / our IV / margin of safety / verdict / last updated. Operator can answer "where should I add" in one invocation.
**Appetite:** ~1 week. v1 reads from `reports/`; does not re-run model every time.
**Theme:** differentiator (portfolio)

### ABA-115 Glidepath + scenario fan visuals
**Problem:** For the operator, we believe text-only model outputs are causing the future trajectory of a company to be hard to internalise. Visuals would shorten the path from "I read the IV" to "I see what it implies."
**Success criterion:** `/stock-model` report includes a glidepath visual (revenue/FCF projection) and scenario fan (bear/base/bull); rendered in UI Model tab.
**Appetite:** ~1 week.
**Theme:** differentiator (legibility)

## Next

### Write remaining playbooks: META, NVDA, AMZN, NFLX, ADYEN
**Problem:** Five of the seven covered tickers still run on generic defaults. The whole depth-over-breadth thesis is unrealised until all seven have playbooks.
**Theme:** differentiator

### Benchmark overlay (SPY / QQQ comparator) — DONE 2026-06-18 (ABA-125)
**Problem:** For the operator, we believe per-ticker IVs don't answer the actual question — "should I buy this or just buy the index?" Without a benchmark layer, the pack can't help with opportunity-cost decisions, which is the second-most-common reason it's used.
**Outcome:** Landed as an addition to `/stock-portfolio`. New columns: implied annualised return (5y, from base IV vs current price), vs SPY (5y trailing total-return CAGR), vs QQQ. Chat-table `Verdict` reframed as opportunity-cost against the better of the two benchmarks (`BEATS INDEX` / `MATCHES INDEX` / `BUY INDEX INSTEAD`). New `mcp__yf__get_total_return_cagr` tool added so the benchmark CAGRs are fetched live, single yfinance call each.
**Theme:** differentiator (portfolio)

### M2.5 data gaps — ABA-67, ABA-68, ABA-69, ABA-75
**Problem:** Bookings/backlog (capital-equipment cos), EPS revisions, next-earnings-date, and EDGAR SBC fallback (for non-US filers like ADYEN) are missing. `/stock-timing` and `/stock-model` quality is capped until these land.
**Theme:** table-stakes

### ABA-65 Segment-revenue trend as growth modifier
**Problem:** For tickers where blended growth hides segment divergence (AWS in AMZN, Cloud in GOOG, DC in NVDA), blended NTM estimates produce wrong growth inputs.
**Theme:** differentiator

### M6 Router — ABA-36/37/38/39/62/63
**Problem:** Manual chaining of Screen → Signal → Model works but creates friction; the router is how the pack becomes a daily tool rather than a per-decision tool.
**Theme:** table-stakes
**Notes:** Kept per operator decision — chain orchestration is core UX even though it's six issues.

### UI Model tab + sensitivity table — ABA-42, ABA-43
**Problem:** Model outputs need a structured place to live; sensitivity is best read interactively.
**Theme:** differentiator (legibility)

## Later

### AlphaSpread reconciliation checklist (doc, not build)
**Hypothesis:** A written checklist for reconciling our IV against AlphaSpread's IV — where to look for the largest deltas (WACC, terminal growth, FCF base, capex schedule), how to decide which is right, when to update our model vs note an unreconciled disagreement — would capture most of the value of a build, with none of the brittleness.
**Theme:** differentiator
**Notes:** Per operator: ship as `docs/operations/reconciliation-checklist.md` when it's the next-most-valuable thing. No build slot.

### UI polish — ABA-40, ABA-41, ABA-44, ABA-45, ABA-46
**Hypothesis:** Once Model tab + visuals are landed, the Signal / Timing / Summary tabs, verdict badges, and PDF export round out the UI. Lower urgency than the differentiator work above.
**Theme:** incremental

### ABA-64 Playwright e2e suite
**Hypothesis:** Worth doing once the UI surface is stable — running it earlier means rewriting tests every cycle.
**Theme:** tech foundation

### ABA-107 / ABA-108 KPI coverage page + ticker-add helper
**Hypothesis:** Useful as the pack matures, low marginal value while only seven tickers are covered.
**Theme:** incremental

### Spikes / ADR / drift live / parity — ABA-105, ABA-103, ABA-109, ABA-113, ABA-95
**Hypothesis:** Quality-of-life and structural cleanups. Important, not urgent.
**Theme:** tech foundation

### M8 OSS release — ABA-50 / 51 / 52 / 53 / 54 / 55 / 56 / 57
**Hypothesis:** Still want to ship publicly, but personal-tool usability comes first. Kept per operator decision; revisit after Now and Next clear.
**Theme:** speculative

## Validation slots

None this cycle. All Now items are confidence ≥ 6; the build-vs-validation gate doesn't trigger. `/stock-portfolio` is the lowest-confidence Now item (6) and is a small build, so the appropriate move is to ship v1 and learn from usage rather than spike it separately.

## Shape review

| Pattern | Status | Notes |
|---|---|---|
| Customer-specials dominance | ok | N/A — single-operator pack |
| Tech foundation starvation | ok | 25% allocated; correctness fixes are P0 |
| Differentiators at low confidence | ok | All `diff` items in Now are confidence ≥ 6; ABA-112 + playbooks at 7–8 |
| No speculative bets | flagged | Speculative is 0% this cycle. Intentional — pack is in "make trustworthy + deepen coverage" mode, not exploration mode. OSS release sits in Later as the speculative slot when it reactivates. |
| Must-be gaps unfixed | ok | ABA-110/111 (the must-be gap) are in flight in Now |
| Validation items in build slots | ok | No low-confidence items in build slots |

## What's deliberately absent this cycle

- **OSS release work** — Later, per operator. Personal-tool quality first.
- **New ticker coverage beyond the seven** — depth-over-breadth principle stands. Adding a name is a deliberate contribution, not a casual edit.
- **Non-tech instrument support (GLDM etc.)** — out of scope per CHARTER.
- **AlphaSpread scraping / MCP** — doc-only reconciliation chosen over a brittle build.
