# SPEC.md — Equity Research Skill-Pack

This document is the authoritative implementation reference. The project brief (embedded below as an appendix) contains methodology and design decisions that are final. This spec adds the technical layer: project structure, data contracts, MCP specs, UI architecture, testing strategy, and boundaries.

---

## Objective

A personal equity research assistant for a tech-focused investor. The pack implements a structured three-stage research process — screen → signal → model — with a timing overlay callable at any stage. Target universe: AI companies (infrastructure, application, model layers) through to established profitable tech (Meta, Google, Nvidia). Occasional pre-IPO coverage.

**Primary users:** Individual investor running their own portfolio. Secondarily: validating or challenging sell-side analyst calls.

**Educational intent:** Every output explains the methodology and the numbers — it does not just produce a verdict.

---

## Architecture Overview

```
/stock:equity    → Router        orchestrates full chain or dispatches to sub-skills
/stock:screen    → Screen        fast go/no-go; two variants by profit stage
/stock:signal    → Signal        GARP signal analysis; outputs MODEL_READY flag
/stock:model     → Model         conviction-building model; two variants by profit stage
/stock:timing    → Timing        when-to-act overlay; standalone invocation
```

Two routing dimensions are inferred before any skill executes:
- **Profit stage**: established (>2yr FCF history) vs emerging/pre-profit
- **Track**: growth (almost always) vs yield (rare edge case)

Router infers both from user phrasing and available data. States its inference. Does not ask.

---

## Namespace Convention

All skills in this pack are namespaced under the `stock:` prefix (e.g. `/stock:screen`, `/stock:signal`, `/stock:timing`, `/stock:model`, `/stock:equity`).

**Reason:** Generic command names (`/model`, `/review`, `/init`, `/ship`) collide with built-in Claude Code commands and with other installed skill packs. The `stock:` prefix gives the pack a stable, conflict-free namespace. The decision was taken pre-M5 (ABA-71) — `/model` would have shadowed the built-in model-switcher.

**Rule:** Every new skill added to this pack MUST use the `stock:` prefix in its SKILL.md `name:` frontmatter field. References to skills in SPEC.md, CLAUDE.md, and other skill descriptions MUST also use the prefixed form. Report JSON schema keys (`stages.screen`, `stages.signal`, etc.) are NOT prefixed — they are JSON keys, not invocations.

---

## Project Structure

```
/
├── CLAUDE.md
├── SPEC.md
├── skills/                    # Skill definition files (markdown)
│   ├── equity.md              # Router — /stock:equity
│   ├── screen.md              # Screen — /stock:screen
│   ├── signal.md              # Signal — /stock:signal
│   ├── model.md               # Model — /stock:model
│   └── timing.md              # Timing — /stock:timing
├── ui/                        # Interactive report viewer
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── components/
│   │   │   ├── EquityReport.jsx     # Full chain report
│   │   │   ├── ScreenReport.jsx
│   │   │   ├── SignalReport.jsx
│   │   │   ├── ModelReport.jsx
│   │   │   └── TimingReport.jsx
│   │   └── lib/
│   │       └── formatters.js        # Number formatting, colour coding
│   ├── package.json
│   └── vite.config.js
├── reports/                   # Generated report data
│   └── TICKER_YYYYMMDD.json   # One file per analysis run
└── mcp/
    ├── yf/                    # yfinance MCP server (M1 ratios)
    │   ├── server.py
    │   ├── tools.py           # Tool definitions
    │   └── requirements.txt
    └── edgar/                 # SEC EDGAR MCP server (M2 deep fundamentals)
        ├── server.py
        ├── tools.py
        └── requirements.txt
```

---

## Skill Authoring Conventions

Each skill file (`skills/*.md`) follows the structure defined in the project brief's "What Each Skill Brief Should Cover" section:

1. Identity (name, command, one-sentence purpose)
2. Methodology (named approach, source attribution)
3. Input schema (required inputs + data-gap handling per field)
4. Execution phases: GATHER → VALIDATE → COMPUTE → THRESHOLD → OVERRIDE → OUTPUT
5. Output schema (exact fields, every run)
6. Data fetching behaviour
7. Invocation patterns
8. Dependencies
9. Tech-specific rules (SBC, AI layer, TAM)
10. Override rules (IF/THEN blocks)

**Universal rules applied in every skill:**
- SBC stripping is step zero before any earnings calculation — never listed alongside other one-offs
- AI layer classification (infrastructure / application / model) is applied in qualitative filters
- Skills web-search for all inputs before prompting the user
- Skills state what they found and what they assumed

---

## Data Layer

### MCP Servers

**`mcp/yf/` — yfinance (Yahoo Finance)**

Primary source for M1 valuation ratios. Free, no API key. Returns TTM ratios via `Ticker.info`.

Tools exposed:
- `get_ratios(ticker)` → P/E, P/S, EV/EBITDA, P/FCF, EV/Revenue (TTM)

Future tools (M2+, if yfinance proves sufficient or before adding paid sources):
- `get_financials(ticker, period)` → income / balance sheet / cashflow
- `get_estimates(ticker)` → analyst EPS / revenue consensus
- `get_earnings_history(ticker, n)` → surprises
- `get_analyst_targets(ticker)` → buy/hold/sell distribution

If yfinance is too fragile or coverage gaps appear, candidates are Finnhub (free tier, 60 req/min) or a paid FMP plan.

**M2 feasibility spike outcome (ABA-47, 2026-05-12).** Probed 10 surfaces × NVDA/META/RDDT. yfinance 1.3.0 covers more than expected — including direct `Stock Based Compensation` rows in cashflow, NTM EPS/revenue consensus, price targets, and multi-year B/S + CF for Piotroski. Three scope changes locked in:

- **SUE/PEAD (ABA-28):** `earnings_history` only returns 4 quarters, not 8. v1 SUE uses 4-quarter window; 8-quarter backfill deferred.
- **Revision momentum (ABA-29):** `eps_revisions` exposes 7d/30d up/down counts only. v1 uses 7d/30d directly; 60/90d deferred. `upgrades_downgrades` is stale on META (latest 2024-09-30) so it is not used as a primary source.
- **Revenue segments (ABA-12):** absent from yfinance entirely. Routed to EDGAR; blocked on EDGAR MCP build.
- **Guidance text (ABA-31):** absent from yfinance. v1 substitutes NTM consensus for guidance; transcript/8-K extraction is Later.

No third-party source needed for v1. Full feasibility table at `mcp/yf/spike/FEASIBILITY.md`.

**`mcp/edgar/` — SEC EDGAR**

Authoritative source for: 10-K, 10-Q, 20-F filings, **revenue segments** (primary — yfinance has no segments surface), operating lease obligations, MD&A and risk-factor text, 8-K guidance press releases. Also used as a cross-check on yfinance SBC/capex/D&A when divergence is material.

Tools to expose:
- `search_filings(ticker, form_type)` → list of recent filings with accession numbers
- `get_filing_facts(ticker, concept)` → specific XBRL fact (e.g. StockBasedCompensation)
- `get_filing_text(accession_number, section)` → raw text of a filing section (MD&A, Risk Factors)

**Scraping layer (no MCP — direct web search)**

Used only for: earnings call transcripts (Motley Fool, Seeking Alpha free pages). Skills use the built-in web search tool directly. No separate MCP needed.

### Data Priority Chain

Source priority is **per-field**, not global. Routing below reflects the ABA-47 spike (2026-05-12):

```
Ratios (P/E, P/S, EV/EBITDA, P/FCF, EV/Rev, TTM):
  1. yfinance  →  2. EDGAR (derived)  →  3. user-provided

SBC, capex, D&A, multi-year B/S + CF (Piotroski inputs), FCF history:
  1. yfinance (Stock Based Compensation row + cashflow/balance_sheet 4-5y)
     →  2. EDGAR XBRL facts (cross-check on material divergence)

Revenue segments, operating lease obligations:
  1. EDGAR XBRL facts (yfinance does not surface segments)  →  2. drop in v1 if EDGAR blocked

Forward / consensus estimates (NTM EPS, NTM revenue, price targets, recs):
  1. yfinance (earnings_estimate / revenue_estimate / analyst_price_targets / recommendations_summary)
     →  2. user-provided if degraded

Earnings surprise history (SUE input):
  1. yfinance earnings_history (4-quarter window — v1 scope)

EPS revision counts (revision momentum input):
  1. yfinance eps_revisions (7d/30d only — v1 scope)
     ✗ upgrades_downgrades is unreliable per-ticker (META stale); not used as primary

Guidance text, MD&A, risk factors:
  1. EDGAR filing text (M2 task)  →  2. web search (transcripts)  →  3. drop and substitute consensus

Transcripts, news, qualitative context:
  1. Web search  →  2. user-provided
```

When a skill cannot resolve an input from sources 1–3, it states the gap, uses the most recent available data as a placeholder, sets `CONFIDENCE = MEDIUM` or `LOW`, and asks the user to confirm before proceeding.

---

## Data Contracts Between Skills

### Screen → Signal
Screen passes PASS-rated tickers as natural language context. No structured schema required — the router re-states the ticker when dispatching.

### Signal → Model
Signal must emit a structured output block before Model will execute. Required fields:

```
SIGNAL OUTPUT
  Ticker:          [TICKER]
  Company:         [Name]
  Profit stage:    [ESTABLISHED | EMERGING]
  Track:           [GROWTH | YIELD]
  AI layer:        [INFRASTRUCTURE | APPLICATION | MODEL | INCUMBENT | N/A]
  
  Clean EPS (TTM): [$ or N/A]
  SBC stripped:    [YES | N/A]
  PEG ratio:       [x or N/A — reason if N/A]
  P/S ratio:       [x]
  Rule of 40:      [score or N/A]
  
  Qualitative:     [PASS | FLAG | FAIL] — [one-line reason]
  
  Signal:          [BUY | WATCH | CAUTION]
  MODEL_READY:     [YES | CONDITIONAL | NO]
  Condition:       [if CONDITIONAL — what the user must confirm]
```

Model reads this block from context. If it is absent, Model states it cannot proceed and instructs the user to run `/stock:signal [ticker]` first.

### All Skills → Report JSON

Every skill appends or creates a report file at `reports/TICKER_YYYYMMDD.json`. Structure:

```json
{
  "ticker": "NVDA",
  "company": "Nvidia",
  "date": "2026-05-12",
  "stages": {
    "screen": {
      "verdict": "WATCH",
      "profit_stage": "ESTABLISHED",
      "ratios": {
        "pe_ratio": 37.7,
        "ps_ratio": 20.9,
        "ev_ebitda": 25.1,
        "pfcf": 42.3,
        "ev_revenue": 19.8
      },
      "rationale": "P/E of 37.7 exceeds the 25 PASS threshold but sits within the 45 WATCH bound; P/S of 20.9 is within the 25 WATCH bound."
    },
    "signal": {
      "verdict": "WATCH",
      "profit_stage": "ESTABLISHED",
      "track": "GROWTH",
      "ai_layer": "INFRASTRUCTURE",
      "clean_eps_ttm": 2.42,
      "sbc_stripped": true,
      "sbc_adjustment_per_share": 0.18,
      "peg_ratio": 1.8,
      "ps_ratio": 20.9,
      "rule_of_40": null,
      "qualitative": "PASS",
      "qualitative_note": "No governance flags; AI infrastructure tailwind.",
      "signal": "WATCH",
      "model_ready": "YES",
      "condition": null
    },
    "model": {
      "verdict": "BUY",
      "profit_stage": "ESTABLISHED",
      "dcf_intrinsic_value": 142.50,
      "current_price": 137.20,
      "upside_pct": 3.9,
      "wacc": 0.09,
      "terminal_growth": 0.03,
      "revenue_cagr_5y": 0.22,
      "sensitivity": {
        "bear": 98.0,
        "base": 142.5,
        "bull": 201.0
      },
      "position_sizing": "2-3% of portfolio",
      "confidence": "HIGH"
    },
    "timing": {
      "verdict": "WAIT_FOR_CATALYST",
      "current_price": 137.20,
      "entry_range_low": 125.0,
      "entry_range_high": 140.0,
      "catalyst": "Earnings report 2026-05-28",
      "technical_note": "Trading near 52-week high; wait for pullback.",
      "confidence": "MEDIUM"
    }
  },
  "meta": {
    "profit_stage": "ESTABLISHED",
    "track": "GROWTH",
    "ai_layer": "INFRASTRUCTURE",
    "confidence": "HIGH"
  }
}
```

The UI reads this file directly. Skills write valid JSON only — no prose in the JSON output.

---

## UI Layer

**Stack:** Vite + React. No backend. Reads report JSON from `reports/` directory (loaded via `fetch` in development, or bundled in future if needed).

**Report viewer behaviour:**
- Opens the most recently written report JSON by default
- Navigation tabs: Screen | Signal | Model | Timing | Summary
- Each tab renders the corresponding skill output with charts and colour-coded verdicts
- Sensitivity table in the Model tab is an interactive grid (editable WACC/terminal growth inputs that recalculate on the fly)
- Verdict badges: green (BUY / PASS / ACT NOW), amber (WATCH / CONDITIONAL / WAIT FOR CATALYST), red (CAUTION / SKIP / WAIT FOR BETTER ENTRY)
- Export button: saves current view as a PDF-ready print layout

**Development:**
```bash
cd ui && npm install
npm run dev       # localhost:5173
npm run build     # dist/ for static serving
```

**Skills open the report** by writing the JSON then printing a file path. The user opens it manually or via a browser-open command if available.

---

## Commands

```bash
# Skill invocation (Claude Code slash commands)
/stock:equity NVDA                          # Full chain
/stock:equity Anthropic -- pre-profit AI    # Full chain with hint
/stock:screen AAPL, NVDA, META, RDDT, CRWV  # Screen only
/stock:signal Meta Platforms                 # Signal only
/stock:model Meta -- standard DCF           # Model (requires signal in context)
/stock:timing NVDA                           # Timing overlay

# UI development
cd ui && npm run dev
cd ui && npm run build

# MCP server startup (for testing)
cd mcp/yf && python server.py
cd mcp/edgar && python server.py
```

---

## Testing Strategy

**Methodology validation (primary):** Run each skill against three known reference tickers and manually verify the output matches the expected methodology:
- NVDA — established profitable tech, AI infrastructure, large capex
- META — established profitable tech, incumbent with AI optionality
- RDDT — emerging/pre-profit, recent IPO, limited FCF history

**MCP integration tests:** Unit test each tool function against live API responses with known tickers. Snapshot the response schema so regressions in the API structure are caught.

**Signal contract test:** Run `/stock:signal NVDA`, capture the output block, confirm all required fields are present and correctly typed before invoking `/stock:model NVDA`.

**SBC stripping test:** For a ticker with a known large SBC line (e.g. Salesforce CRM), verify that clean EPS diverges from reported EPS by the expected amount.

**UI smoke test:** After any report JSON is written, confirm the UI renders without console errors and all tabs display data.

No automated test runner is mandated. Tests are skill-invocation runs with expected output documented in `tests/reference/`.

---

## Boundaries

### Non-equity instruments

This pack covers **equities only**. ETFs, commodity funds, fixed income, and derivatives are out of scope for v1 and v2.

**GLDM (and similar commodity ETFs)** require a fundamentally different methodology — no earnings, no DCF, no P/E or PEG. Valuation is driven by gold price vs. macro factors (real rates, dollar strength, inflation expectations) and fund-level metrics (expense ratio, AUM, tracking error). Adding support would require a new instrument type routing dimension at the `/stock:equity` router level and a separate methodology track. Explicitly deferred to a future milestone; if added, GLDM is the reference case.

If a user passes a non-equity ticker, the router should detect the instrument type (ETF, closed-end fund, etc.) and state that the pack does not support it rather than running equity methodology on it.

### Leading indicator enrichment (Later scope — /stock:model only)

For companies where current-period ratios are lagging indicators, `/stock:model` will add optional enrichment steps that fetch leading indicators before locking in DCF growth rate inputs. Three enrichment paths are planned:

- **Segment revenue trend** (ABA-65): for AMZN, GOOGL, NVDA, RDDT — fetch segment data from EDGAR, compare segment growth to blended NTM estimate
- **Engagement KPIs** (ABA-66): for META, NFLX, RDDT, GOOGL — fetch DAU/ARPU/subscriber metrics from earnings press releases via web search
- **Bookings/backlog** (ABA-67): for INFRASTRUCTURE capital equipment companies (ASML reference case) — fetch net bookings and backlog from earnings press releases via web search

These enrichments do not affect `/stock:signal` verdicts or PEG computation. They are `/stock:model`-only and are implemented when `/stock:model` is built.

### Always do
- Strip SBC before any earnings calculation in every skill
- State data sources and assumptions in every output
- Flag `CONFIDENCE = MEDIUM` or `LOW` when any input is estimated
- Include methodology explanation alongside every verdict
- Apply AI layer classification (infrastructure / application / model / incumbent / N/A) in Signal qualitative filters

### Ask first
- Before running Model without a Signal output in context
- Before using user-provided numbers as primary inputs (confirm the source)
- Before applying the yield track (confirm this is genuinely an income thesis, not a misclassification)

### Never do
- Run a standard P/E or PEG ratio on a pre-profit company without flagging it as invalid
- Proceed with Model on a CAUTION or MODEL_READY = NO signal without explicit user override
- Skip SBC stripping on grounds that SBC is "immaterial" — always check, always note
- Re-litigate the design decisions listed in the project brief (see Appendix)
- Add features not described in this spec or the brief without user instruction

---

## Implementation Order

1. **MCP servers** — yfinance and EDGAR. Skills can't run without data.
2. **Signal skill** — most complex; v1 draft exists per the brief. Implement tech-specific extensions (SBC, AI layer, TAM check).
3. **Screen skill** — both variants. Depends only on yfinance data.
4. **Timing skill** — lightest data requirement; fastest to implement.
5. **Model skill** — both variants. Depends on Signal output contract.
6. **Router skill** — implement last; requires all sub-skills to be stable.
7. **UI** — can be built in parallel with skill authoring once the JSON report schema is stable.

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
