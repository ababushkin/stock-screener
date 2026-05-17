# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A personal equity research skill-pack for a tech-focused investor. See `CHARTER.md` for what this pack is for and which boundaries are locked, and `DESIGN.md` for the architectural reference.

Tasks and milestones live in Linear: https://linear.app/ababushkin/project/ai-equity-research-skill-pack-b8446cbaab6b/overview

## Operating principle — pointer

This pack optimises for **depth on a curated set of specialist-supported tickers** (see `CHARTER.md` → *Operating Principle — Depth over Breadth* for the full statement, and `COVERAGE.md` for the seven currently-supported names plus the contribution path for adding more). Generic improvements are deprioritised vs ticker-specific depth, except correctness fixes (ABA-110 SBC strip, ABA-111 growth-rate ceiling) which are P0.

**Until ABA-110 and ABA-111 land**, no `/stock:model` report should be treated as decision-grade — IVs are inflated by un-stripped SBC and trough-extrapolated FCF growth; position-sizing recommendations should be discounted.

Playbook layer (`playbooks/TICKER.md` loaded by `/stock:model` for covered tickers): spec lives in `DESIGN.md` → *Playbook Layer*; implementation tracked in ABA-112.

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
