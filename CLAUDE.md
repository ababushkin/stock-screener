# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A personal equity research skill-pack for a tech-focused investor. See `SPEC.md` for the full technical spec.

Tasks and milestones live in Linear: https://linear.app/ababushkin/project/ai-equity-research-skill-pack-b8446cbaab6b/overview

## Operating principle — depth over breadth

This skill-pack is the **world's best decision-making (and later prediction) engine for a curated tech watchlist**, not a generalised valuation tool for thousands of tickers. The user's stated frame: *"I don't care if we don't know how to value GM, but I DO VERY MUCH CARE that we know with INCREDIBLE detail how to value META otherwise it's just a stupid number I won't use or trust."*

Implications for every implementation decision:

1. **Ticker-specific knowledge beats generalised heuristics.** A correct META-specific assumption beats a defensible industry default. When the two conflict, encode the ticker-specific knowledge (in a playbook, see below) rather than smoothing it away.

2. **Auditability is non-negotiable.** Every assumption surfaced; every scenario axis disclosed; every cap, override, and manual input named in the output. Opaque algorithmic blending (AlphaSpread-style) is rejected even when it produces better point estimates — a number we can't argue with is a number we can't trust.

3. **Generic improvements are deprioritised against ticker-specific deepening.** When choosing between (a) a methodology improvement that helps every ticker by 5% and (b) a ticker-specific playbook for a watchlist name, choose (b). The exception: correctness fixes (e.g. ABA-110 SBC strip) are always P0 because they're table stakes for any number being usable.

4. **The watchlist is small and explicit.** Six names — **GOOG, META, AMZN, NVDA, ASML, NFLX** — codified in `WATCHLIST.md`. Off-watchlist tickers fall back to generic ESTABLISHED / EMERGING logic; on-watchlist tickers load their playbook from `playbooks/TICKER.md` (segments, capex cycle position, active catalysts, sell-side disagreement axes, failure modes). Watchlist changes are deliberate — discuss before editing.

5. **Backtesting is how the model gets sharper.** Drift CI catches format breaks; historical replay against the watchlist catches methodology drift. To call the engine "world's best" requires a quarterly hit-rate scorecard against actual price history on the watchlist names.

6. **The `/stock:model` skill is downstream of Signal, and both are upstream of trust.** No `/stock:model` report should be treated as decision-grade until ABA-110 (SBC strip) and ABA-111 (growth-rate ceiling) are merged. Until then, IVs are inflated and position-sizing recommendations should be discounted.

## Build tools by component

| Component | Build with |
|-----------|-----------|
| yfinance MCP server | `/pde:design-doc` → `agent-skills:build` |
| EDGAR MCP server | `/pde:design-doc` → `agent-skills:build` |
| `/stock:signal`, `/stock:screen`, `/stock:timing`, `/stock:model`, `/stock:equity` skills | `skill-creator:skill-creator` |
| Report UI (Vite + React) | `agent-skills:build` |

## Commands

```bash
# UI
cd ui && npm run dev        # localhost:5173
cd ui && npm run build

# MCP servers
cd mcp/yf && python server.py
cd mcp/edgar && python server.py
```

## Permissions

`.claude/settings.local.json` pre-allows `rtk ls *` and `rtk read *` — use these instead of bare `ls`/`cat`.

## Linear workflow

When working on a Linear issue:
1. **On start** — set the issue status to **In Progress** using `mcp__linear-server__save_issue`
2. **On complete** — set the issue status to **Done** using `mcp__linear-server__save_issue` only after changes have been committed and pushed

Always update Linear status. Do not leave issues in the wrong state.

## Linear wave promotion

M5 work is grouped into waves via Linear labels (`wave-1`, `wave-1.5-gate`, `wave-2`, `wave-3`, `wave-4`) and gated via `blockedBy` relationships. When a Linear issue moves to Done:

1. Run a 30-second smoke check on the just-completed work (eyeball one representative output). If it fails, the work isn't actually done — reopen and stop.
2. Find issues whose `blockedBy` list contained the just-completed issue — these are now unblocked candidates.
3. Filter unblocked candidates by wave label — promote in wave order; never skip a wave.
4. Promote 1–3 unblocked candidates to Todo, keeping the Todo queue ≤ 3 deep.
5. Linear's blockers enforce the hard stops (Wave 1 → ABA-82 gate → Wave 2 → Wave 3 → Wave 4); never manually bypass them.

## Git

Do not add `Co-Authored-By` trailers to commit messages.
