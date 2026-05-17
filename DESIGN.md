# DESIGN.md — Equity Research Skill-Pack

This document is the **architectural reference** for the equity research skill-pack. It covers project structure, data contracts, MCP specs, the playbook layer, UI architecture, testing strategy, and skill-authoring conventions. For product positioning, scope boundaries, and locked design decisions, see `CHARTER.md`.

---

## Architecture Overview

```
/stock-equity    → Router        orchestrates full chain or dispatches to sub-skills
/stock-screen    → Screen        fast go/no-go; two variants by profit stage
/stock-signal    → Signal        GARP signal analysis; outputs MODEL_READY flag
/stock-model     → Model         conviction-building model; two variants by profit stage
/stock-timing    → Timing        when-to-act overlay; standalone invocation
```

Two routing dimensions are inferred before any skill executes:
- **Profit stage**: established (>2yr FCF history) vs emerging/pre-profit
- **Track**: growth (almost always) vs yield (rare edge case)

Router infers both from user phrasing and available data. States its inference. Does not ask.

---

## Namespace Convention

All skills in this pack are namespaced under the `stock-` prefix (e.g. `/stock-screen`, `/stock-signal`, `/stock-timing`, `/stock-model`, `/stock-equity`).

**Reason:** Generic command names (`/model`, `/review`, `/init`, `/ship`) collide with built-in Claude Code commands and with other installed skill packs. The `stock-` prefix gives the pack a stable, conflict-free namespace. The decision was taken pre-M5 (ABA-71) — `/model` would have shadowed both the built-in model-switcher and `agent-skills:model`. The convention was originally a `stock:` colon-style namespace; ABA-114 switched to `stock-` because the bare slug after the colon (e.g. `model`) still showed up in the loaded-skill list and confused triggering.

**Rule:** Every new skill added to this pack MUST use the `stock-` prefix in its SKILL.md `name:` frontmatter field. References to skills in `CHARTER.md`, `DESIGN.md`, `CLAUDE.md`, and other skill descriptions MUST also use the prefixed form. Report JSON schema keys (`stages.screen`, `stages.signal`, etc.) are NOT prefixed — they are JSON keys, not invocations.

---

## Project Structure

```
/
├── CHARTER.md                 # Product charter — objective, operating principle, boundaries
├── DESIGN.md                  # This file — architectural reference
├── CLAUDE.md                  # Operational guidance for Claude Code in this repo
├── COVERAGE.md                # Currently-supported tickers + contribution path
├── README.md                  # Entry-point overview
├── skills/                    # Skill definition files (markdown)
│   ├── equity.md              # Router — /stock-equity
│   ├── screen.md              # Screen — /stock-screen
│   ├── signal.md              # Signal — /stock-signal
│   ├── model.md               # Model — /stock-model
│   └── timing.md              # Timing — /stock-timing
├── playbooks/                 # Ticker-specific overrides loaded by /stock-model (ABA-112)
│   └── TICKER.md              # One per supported ticker (see COVERAGE.md)
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

## Playbook Layer

For supported tickers (see `COVERAGE.md`), `/stock-model` loads ticker-specific overrides from `playbooks/TICKER.md` (uppercase ticker symbol; period-suffixed exchange codes preserved verbatim, e.g. `playbooks/ADYEN.AS.md`). Off-coverage tickers run with generic ESTABLISHED / EMERGING defaults. Implementation tracked in ABA-112; blocked by ABA-110 + ABA-111 (correctness fixes must land first so playbook overrides modulate a trustworthy base).

**File format.** Markdown with YAML frontmatter.

Frontmatter — machine-readable overrides consumed by `/stock-model`:
- `base_wacc` — overrides the MIP-asked default (suppresses the WACC question)
- `growth_ceiling` — overrides the generic 18% fallback ceiling on base Y2-Y5 CAGR (see ABA-111)
- `terminal_margin` — overrides the SBC-stripped TTM margin as the Y5 anchor (see ABA-110)
- `scenario_axes` — optional per-scenario overrides (used when the catalyst structure demands discrete outcomes vs smooth scenarios, e.g. "TikTok divested" as a binary)
- `narrative.{bear,base,bull}` — replace generic per-scenario one-liners with thesis-grounded narratives
- `failure_modes` — surfaced in output as a separate `Monitor:` section
- `confidence_anchor` — playbook-set max confidence (e.g. cap NVDA at MEDIUM until customer concentration risk is resolved)

Body — human-reference content: business architecture, segment splits, capex-cycle position, active catalysts, sell-side disagreement axes, historical reset-and-recover priors, failure-mode commentary.

**Loader behaviour in `/stock-model`** (implementation in ABA-112):

1. After GATE passes, before GATHER, check `playbooks/TICKER.md`.
2. Absent: emit `No playbook for TICKER — using generic ESTABLISHED/EMERGING logic.` and proceed unchanged.
3. Present: load frontmatter, surface `Playbook loaded: playbooks/TICKER.md (last updated YYYY-MM-DD). Overrides applied: [list].` Apply overrides per the hierarchy below; record audit trail in `stages.model.playbook` JSON block.

**Override hierarchy.** Playbook beats generic default; runtime user override (e.g. `--wacc=9.0`) beats playbook.

**Audit trail.** Every playbook-sourced field appears in `stages.model.playbook.overrides_applied` with the source named. Confidence cap from playbook is the binding cap when stricter than the runtime-derived value. Silent application of any override is forbidden — the OUTPUT block names every overridden field.

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

Model reads this block from context. If it is absent, Model states it cannot proceed and instructs the user to run `/stock-signal [ticker]` first.

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
      "method": "two-stage DCF",
      "profit_stage": "ESTABLISHED",
      "route_override": null,
      "current_price": 137.20,
      "shares_diluted": 24500000000,
      "net_debt": -50000000000,
      "fcf_ttm": 60000000000,
      "fcf_margin_ttm": 0.34,
      "fcf_cagr_3y": 0.28,
      "ntm_revenue": 200000000000,
      "base_wacc": 0.09,
      "scenarios": {
        "bear": { "y1_fcf": 55000000000, "y2_5_cagr": 0.12, "terminal_growth": 0.02, "wacc": 0.10, "intrinsic_value_per_share": 98.0, "upside_pct": -28.6, "narrative": "deceleration, multiple compression" },
        "base": { "y1_fcf": 65000000000, "y2_5_cagr": 0.22, "terminal_growth": 0.03, "wacc": 0.09, "intrinsic_value_per_share": 142.5, "upside_pct": 3.9, "narrative": "consensus delivers" },
        "bull": { "y1_fcf": 75000000000, "y2_5_cagr": 0.30, "terminal_growth": 0.035, "wacc": 0.08, "intrinsic_value_per_share": 201.0, "upside_pct": 46.5, "narrative": "AI tailwind, operating leverage" }
      },
      "intrinsic_value_range": { "bear": 98.0, "base": 142.5, "bull": 201.0 },
      "range_vs_price": "WITHIN BASE-BULL",
      "sensitivity": { "dominant_driver": "WACC", "note": "±100 bps WACC moves base IV by ±15%" },
      "sensitivity_table": {
        "wacc_axis": [0.08, 0.085, 0.09, 0.095, 0.10],
        "terminal_growth_axis": [0.02, 0.025, 0.03, 0.035, 0.04],
        "intrinsic_value_per_share": [[ "...5x5 grid..." ]],
        "base_cell": { "row": 2, "col": 2 }
      },
      "position_sizing": {
        "band": "2–3% of portfolio",
        "lower_pct": 2,
        "upper_pct": 3,
        "signal_verdict": "BUY",
        "range_vs_price": "WITHIN BASE-BULL",
        "margin_of_safety_pct": 3.9,
        "confidence_cap_applied": false,
        "rationale": "BUY × WITHIN BASE-BULL → 2–3% band; HIGH confidence cap not binding."
      },
      "manual_inputs": [{ "field": "base_wacc", "source": "user_paste" }]
    },
    /* Pre-profit variant (--pre-profit override or EMERGING profile) replaces
       scenario contents with: y1_revenue, y2_5_rev_cagr, exit_multiple, terminal_margin,
       dilution_rate, fcf_inflection_year, shares_y5, dilution_pct_5y; and the model block
       adds top-level fields: revenue_ttm, rev_cagr_3y, comp_set[], base_exit_multiple,
       terminal_margin_target, sbc_dilution_base, sbc_dilution_3y_trailing, caveat. */
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
/stock-equity NVDA                          # Full chain
/stock-equity Anthropic -- pre-profit AI    # Full chain with hint
/stock-screen AAPL, NVDA, META, RDDT, CRWV  # Screen only
/stock-signal Meta Platforms                 # Signal only
/stock-model Meta -- standard DCF           # Model (requires signal in context)
/stock-timing NVDA                           # Timing overlay

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

**Signal contract test:** Run `/stock-signal NVDA`, capture the output block, confirm all required fields are present and correctly typed before invoking `/stock-model NVDA`.

**SBC stripping test:** For a ticker with a known large SBC line (e.g. Salesforce CRM), verify that clean EPS diverges from reported EPS by the expected amount.

**UI smoke test:** After any report JSON is written, confirm the UI renders without console errors and all tabs display data.

**Coverage backtesting (future, ABA-NEXT):** Quarterly historical replays of `/stock-signal` and `/stock-model` against the supported tickers (`COVERAGE.md`). Grade IV-range coverage of subsequent price action, verdict accuracy, and dominant-driver stability across time. Feeds methodology drift back into the skills per `CHARTER.md` → *Operating Principle* (5).

No automated test runner is mandated. Tests are skill-invocation runs with expected output documented in `tests/reference/`.

---

## Implementation Order

1. **MCP servers** — yfinance and EDGAR. Skills can't run without data.
2. **Signal skill** — most complex; v1 draft exists per the brief. Implement tech-specific extensions (SBC, AI layer, TAM check).
3. **Screen skill** — both variants. Depends only on yfinance data.
4. **Timing skill** — lightest data requirement; fastest to implement.
5. **Model skill** — both variants. Depends on Signal output contract.
6. **Router skill** — implement last; requires all sub-skills to be stable.
7. **UI** — can be built in parallel with skill authoring once the JSON report schema is stable.
8. **Playbook layer** (ABA-112) — depth-over-breadth foundation; depends on ABA-110 (SBC strip) and ABA-111 (growth-rate ceiling) for a trustworthy base.
