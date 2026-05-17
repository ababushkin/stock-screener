# CHARTER.md — Equity Research Skill-Pack

This document is the **product charter** for the equity research skill-pack. It states what the pack is for, who it serves, how scope decisions are made, and which design decisions are locked. For architecture, data contracts, MCP specs, the playbook layer, UI architecture, testing strategy, and skill-authoring conventions, see `DESIGN.md`.

---

## Objective

A personal equity research assistant for a tech-focused investor. The pack implements a structured three-stage research process — screen → signal → model — with a timing overlay callable at any stage. Target universe: AI companies (infrastructure, application, model layers) through to established profitable tech (Meta, Google, Nvidia). Occasional pre-IPO coverage.

**Scope is tech-only by design.** Non-tech names (auto OEMs, banks, cyclicals, yield-track equities) are explicitly out of scope — the skills will run but verdicts won't be trustworthy. See `README.md` for the full scope statement and known failure modes for non-tech inputs.

**Primary users:** Individual investor running their own portfolio. Secondarily: validating or challenging sell-side analyst calls.

**Educational intent:** Every output explains the methodology and the numbers — it does not just produce a verdict.

---

## Operating Principle — Depth over Breadth

This pack optimises for **depth on a curated set of specialist-supported tickers** (see `COVERAGE.md`), not breadth across thousands of names. The intended use is high-conviction decision-making — and later, prediction — on a small number of tickers the project explicitly supports with playbooks. The skills will run on any ticker; off-coverage runs use generic ESTABLISHED / EMERGING logic, with confidence capped at MEDIUM by default.

The user's stated frame: *"I don't care if we don't know how to value GM, but I do very much care that we know with incredible detail how to value META — otherwise it's just a stupid number I won't use or trust."*

Implications for every implementation decision:

1. **Ticker-specific knowledge beats generalised heuristics.** When a supported ticker has a known capex-cycle position, segment mix, governance fact, or sell-side disagreement axis that materially affects valuation, encode it in `playbooks/TICKER.md` (see `DESIGN.md` → *Playbook Layer*). Smoothing ticker-specific knowledge into industry-average defaults is the failure mode this pack exists to avoid.

2. **Auditability is non-negotiable.** Every assumption surfaced in output, every scenario axis disclosed, every cap / override / manual input named. Opaque algorithmic blending is rejected even when it produces better point estimates — a number the user cannot argue with is a number the user will not trust.

3. **Generic improvements are deprioritised against coverage depth.** When choosing between (a) a methodology improvement that helps every ticker marginally and (b) a coverage-specific deepening for a supported ticker, choose (b). Exception: correctness fixes (e.g. SBC stripping in the DCF base — ABA-110) remain P0 because they are table stakes for any number being usable.

4. **Off-coverage tickers run on generic fallback logic.** That is a deliberate cost — confidence caps at MEDIUM by default for off-coverage invocations, and users should expect a less informative answer than for a name with a playbook. Adding specialist coverage for a new ticker is a contribution path (see `COVERAGE.md` → *Contributing new coverage*), not a casual edit.

5. **Backtesting is how the engine gets sharper.** Quarterly historical replays against the covered tickers (see `DESIGN.md` → *Testing Strategy*) feed methodology drift back into the skills. Drift CI catches format breaks; backtesting catches methodology drift.

---

## Boundaries

### Non-equity instruments

This pack covers **equities only**. ETFs, commodity funds, fixed income, and derivatives are out of scope for v1 and v2.

**GLDM (and similar commodity ETFs)** require a fundamentally different methodology — no earnings, no DCF, no P/E or PEG. Valuation is driven by gold price vs. macro factors (real rates, dollar strength, inflation expectations) and fund-level metrics (expense ratio, AUM, tracking error). Adding support would require a new instrument type routing dimension at the `/stock-equity` router level and a separate methodology track. Explicitly deferred to a future milestone; if added, GLDM is the reference case.

If a user passes a non-equity ticker, the router should detect the instrument type (ETF, closed-end fund, etc.) and state that the pack does not support it rather than running equity methodology on it.

### Leading indicator enrichment (Later scope — /stock-model only)

For companies where current-period ratios are lagging indicators, `/stock-model` will add optional enrichment steps that fetch leading indicators before locking in DCF growth rate inputs. Three enrichment paths are planned:

- **Segment revenue trend** (ABA-65): for AMZN, GOOGL, NVDA, RDDT — fetch segment data from EDGAR, compare segment growth to blended NTM estimate
- **Engagement KPIs** (ABA-66): for META, NFLX, RDDT, GOOGL — fetch DAU/ARPU/subscriber metrics from earnings press releases via web search
- **Bookings/backlog** (ABA-67): for INFRASTRUCTURE capital equipment companies (ASML reference case) — fetch net bookings and backlog from earnings press releases via web search

These enrichments do not affect `/stock-signal` verdicts or PEG computation. They are `/stock-model`-only and are implemented when `/stock-model` is built.

### Always do
- Strip SBC before any earnings calculation in every skill — and from the FCF base in `/stock-model` (ABA-110)
- State data sources and assumptions in every output
- Flag `CONFIDENCE = MEDIUM` or `LOW` when any input is estimated
- Include methodology explanation alongside every verdict
- Apply AI layer classification (infrastructure / application / model / incumbent / N/A) in Signal qualitative filters
- Load playbook overrides for covered tickers and surface which overrides applied in every output (see `DESIGN.md` → *Playbook Layer*)

### Ask first
- Before running Model without a Signal output in context
- Before using user-provided numbers as primary inputs (confirm the source)
- Before applying the yield track (confirm this is genuinely an income thesis, not a misclassification)
- Before adding or removing tickers from the coverage list (`COVERAGE.md`) — composition is deliberate, not casual; addition is a contribution path with rationale, not a quick edit

### Never do
- Run a standard P/E or PEG ratio on a pre-profit company without flagging it as invalid
- Proceed with Model on a CAUTION or MODEL_READY = NO signal without explicit user override
- Skip SBC stripping on grounds that SBC is "immaterial" — always check, always note
- Re-litigate the design decisions listed in the project brief (see *Appendix* below)
- Add features not described in this charter, in `DESIGN.md`, or in the project brief without user instruction
- Silently apply playbook overrides — the OUTPUT block must name every overridden field and its source
- Treat off-coverage `/stock-model` runs as decision-grade — confidence caps at MEDIUM by default and the user must be told

---

## Appendix — Design Decisions (Do Not Re-Litigate)

From the project brief. These are fixed:

- Yield track is a dormant edge case. Do not expand it.
- SBC stripping is mandatory step zero in every skill, not listed alongside other one-offs.
- Magic Formula replaces Rule of 40 for established profitable tech at the screen stage.
- Router infers depth and profit stage — it does not ask the user which level to run.
- Model skill requires a signal output as context. It is not standalone.
- Timing overlay is always a separate invocation — not in the linear chain.
- AI layer classification is a qualitative filter in Signal, not a routing dimension.
- Position sizing is an output of the Model skill, not a separate skill.
- Pre-profit DCF uses revenue multiple exit, not P/E exit.
