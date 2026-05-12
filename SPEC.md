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
/equity    → Router        orchestrates full chain or dispatches to sub-skills
/screen    → Screen        fast go/no-go; two variants by profit stage
/signal    → Signal        GARP signal analysis; outputs MODEL_READY flag
/model     → Model         conviction-building model; two variants by profit stage
/timing    → Timing        when-to-act overlay; standalone invocation
```

Two routing dimensions are inferred before any skill executes:
- **Profit stage**: established (>2yr FCF history) vs emerging/pre-profit
- **Track**: growth (almost always) vs yield (rare edge case)

Router infers both from user phrasing and available data. States its inference. Does not ask.

---

## Project Structure

```
/
├── CLAUDE.md
├── SPEC.md
├── skills/                    # Skill definition files (markdown)
│   ├── equity.md              # Router — /equity
│   ├── screen.md              # Screen — /screen
│   ├── signal.md              # Signal — /signal
│   ├── model.md               # Model — /model
│   └── timing.md              # Timing — /timing
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
    ├── fmp/                   # Financial Modeling Prep MCP server
    │   ├── server.py
    │   ├── tools.py           # Tool definitions
    │   └── requirements.txt
    └── edgar/                 # SEC EDGAR MCP server
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

**`mcp/fmp/` — Financial Modeling Prep**

Primary source for: income statements, balance sheets, cash flow statements, financial ratios, analyst estimates and price targets, earnings surprises, EV multiples, NTM revenue estimates, SBC line items, segment data.

Tools to expose:
- `get_financials(ticker, period)` → annual/TTM income, balance sheet, cashflow
- `get_ratios(ticker)` → P/E, EV/EBITDA, P/FCF, P/S, EV/Revenue
- `get_estimates(ticker)` → consensus EPS/revenue for NTM, analyst count
- `get_earnings_history(ticker, n)` → last n quarters: reported vs estimate, surprise %
- `get_analyst_targets(ticker)` → price target distribution, buy/hold/sell counts
- `get_revenue_segments(ticker)` → segment breakdown where available

**`mcp/edgar/` — SEC EDGAR**

Authoritative source for: 10-K and 10-Q filings, exact SBC figures, capex, D&A, operating lease obligations. Used for Piotroski raw data and as verification layer against FMP.

Tools to expose:
- `search_filings(ticker, form_type)` → list of recent filings with accession numbers
- `get_filing_facts(ticker, concept)` → specific XBRL fact (e.g. StockBasedCompensation)
- `get_filing_text(accession_number, section)` → raw text of a filing section (MD&A, Risk Factors)

**Scraping layer (no MCP — direct web search)**

Used only for: earnings call transcripts (Motley Fool, Seeking Alpha free pages). Skills use the built-in web search tool directly. No separate MCP needed.

### Data Priority Chain

```
1. FMP API (pre-computed, updated)
2. EDGAR XBRL facts (authoritative for SBC, capex, D&A)
3. Web search (transcripts, recent news, guidance quotes)
4. User-provided (last resort — skill asks explicitly)
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

Model reads this block from context. If it is absent, Model states it cannot proceed and instructs the user to run `/signal [ticker]` first.

### All Skills → Report JSON

Every skill appends or creates a report file at `reports/TICKER_YYYYMMDD.json`. Structure:

```json
{
  "ticker": "NVDA",
  "company": "Nvidia",
  "date": "2026-05-12",
  "stages": {
    "screen": { ... },
    "signal": { ... },
    "model": { ... },
    "timing": { ... }
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
/equity NVDA                          # Full chain
/equity Anthropic -- pre-profit AI    # Full chain with hint
/screen AAPL, NVDA, META, RDDT, CRWV  # Screen only
/signal Meta Platforms                 # Signal only
/model Meta -- standard DCF           # Model (requires signal in context)
/timing NVDA                           # Timing overlay

# UI development
cd ui && npm run dev
cd ui && npm run build

# MCP server startup (for testing)
cd mcp/fmp && python server.py
cd mcp/edgar && python server.py
```

---

## Testing Strategy

**Methodology validation (primary):** Run each skill against three known reference tickers and manually verify the output matches the expected methodology:
- NVDA — established profitable tech, AI infrastructure, large capex
- META — established profitable tech, incumbent with AI optionality
- RDDT — emerging/pre-profit, recent IPO, limited FCF history

**MCP integration tests:** Unit test each tool function against live API responses with known tickers. Snapshot the response schema so regressions in the API structure are caught.

**Signal contract test:** Run `/signal NVDA`, capture the output block, confirm all required fields are present and correctly typed before invoking `/model NVDA`.

**SBC stripping test:** For a ticker with a known large SBC line (e.g. Salesforce CRM), verify that clean EPS diverges from reported EPS by the expected amount.

**UI smoke test:** After any report JSON is written, confirm the UI renders without console errors and all tabs display data.

No automated test runner is mandated. Tests are skill-invocation runs with expected output documented in `tests/reference/`.

---

## Boundaries

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

1. **MCP servers** — FMP and EDGAR. Skills can't run without data.
2. **Signal skill** — most complex; v1 draft exists per the brief. Implement tech-specific extensions (SBC, AI layer, TAM check).
3. **Screen skill** — both variants. Depends only on FMP data.
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
