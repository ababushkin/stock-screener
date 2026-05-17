# stock-review

Personal equity research skill-pack for a **tech-focused investor**. A structured pipeline of Claude Code skills that classify, value, and time entries on technology equities.

See `CHARTER.md` for what this pack is for and which boundaries are locked, and `DESIGN.md` for the architectural reference.

---

## Scope

**In scope:** Listed technology equities — AI infrastructure (NVDA, AMD), AI applications (CRM, NOW), model providers, large profitable tech (META, GOOGL, MSFT, AAPL), emerging/pre-profit tech SaaS (RDDT, NET, DDOG). Occasional pre-IPO coverage.

**Out of scope:** Cyclicals, auto OEMs, financials, energy, consumer staples, industrials, REITs, utilities. The thresholds, DCF variants, and qualitative overlays in this pack are calibrated for tech business models — they will produce confidently-wrong outputs on non-tech names.

Specifically, the pack will not be extended to support:

- **Auto OEMs (GM, F, STLA, TM)** — capex-heavy, financing-arm complexity, cycle-normalised earnings required.
- **Banks and insurers** — book-value / regulatory-capital frameworks, not DCF.
- **Pure cyclicals (chemicals, steel, mining)** — through-cycle EBITDA frameworks required.
- **Yield-track equities** (utilities, REITs, telcos) — dividend-discount frameworks; the YIELD track is dormant by design.

If you want to evaluate a non-tech name, do it outside this pack — the skills will run, but the verdicts won't be trustworthy. Known failure modes for non-tech inputs:

- Signal's P/S and PEG thresholds are tech-calibrated; P/S < 0.5 reads as BUY but is normal for asset-heavy industries.
- Model's two-stage DCF breaks when the trailing FCF series contains negative years (common for cyclicals and EV-transitioning autos).
- Model's pre-profit variant assumes SBC-driven dilution; it does not handle buyback-heavy share-count trajectories.
- AI layer classification has no analogue for non-tech structural advantages (brand, scale, regulatory moat).

---

## Skill order

```
/stock:screen TICKER1, TICKER2, …     fast PASS / WATCH / SKIP across a list
        │
        ▼
/stock:signal TICKER                  GARP verdict + MODEL_READY gate (single ticker)
        │
        ▼
/stock:timing TICKER                  when-to-act overlay (SUE, PEAD, revisions, catalyst)
        │
        ▼
/stock:model TICKER                   DCF intrinsic value range + position sizing
```

All four merge into one `reports/TICKER_YYYYMMDD.json` (stages: `screen`, `signal`, `timing`, `model`). Model is hard-gated on a same-session Signal. Timing is an overlay — only meaningful when Signal or Model is BUY/WATCH. Screen and Signal are independent entry points; you can start at either.

`/stock:equity` (router, planned) orchestrates the full chain or dispatches to sub-skills based on user phrasing.

---

## How `/stock:model` works (and when it refuses)

Model is a valuation calculator that estimates "what is one share actually worth today?" It projects free cash flow 5 years out, adds a terminal value for everything after that, discounts both back to present using a cost-of-capital number, subtracts net debt, and divides by share count. It runs the math three times — bear / base / bull — to produce a range, not a single point.

**The hard requirement.** Model only runs when Signal upstream says `MODEL_READY = YES` (or `CONDITIONAL` with `--confirm`). The gate is deliberate: Signal is the one place that strips stock-based comp from EPS, classifies profit stage, and decides whether a DCF is honest right now. If Signal says NO, Model refuses — `--confirm` does not override a NO.

**The three states Signal can issue:**

| State | What it means | What Model does |
|---|---|---|
| `YES` | Profitable, clean EPS positive, no qualitative red flags | Runs standard two-stage DCF |
| `CONDITIONAL` | One named risk the user must acknowledge (e.g. transition-year ticker) | Refuses until re-invoked with `--confirm` |
| `NO` | Clean EPS negative, qualitative FAIL, or hard CAUTION | Hard refusal; re-run `/signal` if conditions changed |

**Why the standard DCF needs profitability.** The two-stage model assumes a terminal value where earnings ≈ free cash flow in steady state. For a company that pays out more in stock comp than it earns in GAAP profit (e.g. XYZ/Block today), the steady-state assumption is a fiction — small changes to the perpetuity growth rate flip the answer by orders of magnitude. Forcing the calculator on these inputs produces a confident-looking number anchored to nothing.

**The pre-profit variant (`--pre-profit`).** For EMERGING tickers (or any ticker the user forces with `--pre-profit`), Model swaps the Gordon terminal for a revenue-multiple exit and adds an explicit SBC dilution schedule plus an FCF inflection year. This is the right shape for high-growth tech that hasn't reached steady state yet. **It still requires the gate to pass** — pre-profit is a math change, not a gate bypass.

**Common reasons Signal will issue NO:**

- Clean EPS negative after SBC stripping (e.g. heavy stock-comp tech that's GAAP break-even)
- Qualitative FAIL from a TAM ceiling or governance issue
- Pre-profit base effect (EMERGING tickers always default to CAUTION)
- PEG > 2.0 with no overriding qualitative strength

**The fix when Signal says NO is almost never "force Model to run."** It's either:

1. Re-run `/signal TICKER` after using the Manual Input Protocol to supply a missing input (e.g. analyst 5y EPS growth if yfinance returned null), or
2. Acknowledge that the standard DCF isn't the right tool for this company today — and use Signal's qualitative output + Timing for the entry/exit decision instead.

**TL;DR.** Model is a valuation calculator for *profitable, stable tech*. It works cleanly on mature compounders (MSFT, GOOGL, ADBE). It refuses — correctly — on pre-profit names and on profitable-but-SBC-absorbed names where the inputs would lie. The pre-profit variant extends the range but doesn't remove the upstream gate.

---

## Build tools by component

| Component | Build with |
|-----------|-----------|
| yfinance MCP server | `/pde:design-doc` → `agent-skills:build` |
| EDGAR MCP server | `/pde:design-doc` → `agent-skills:build` |
| `/stock:signal`, `/stock:screen`, `/stock:timing`, `/stock:model`, `/stock:equity` skills | `skill-creator:skill-creator` |
| Report UI (Vite + React) | `agent-skills:build` |

---

## Run

```bash
# UI
cd ui && npm run dev        # localhost:5173
cd ui && npm run build

# MCP servers
cd mcp/yf && python server.py
cd mcp/edgar && python server.py
```

Tasks and milestones live in Linear: https://linear.app/ababushkin/project/ai-equity-research-skill-pack-b8446cbaab6b/overview
