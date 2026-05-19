# AGENTS.md

Instructions for any coding agent (Claude Code, Codex, etc.) working in this repository. Tool-agnostic by design — see `CLAUDE.md` for any Claude-Code-specific additions.

## What this repo is

A personal equity research skill-pack for a tech-focused investor. See `CHARTER.md` for what this pack is for and which boundaries are locked, and `DESIGN.md` for the architectural reference.

Tasks and milestones live in Linear: https://linear.app/ababushkin/project/equity-skill-pack-b8446cbaab6b/overview

## Operating principle

Depth on a curated set of specialist-supported tickers — see `CHARTER.md`, `COVERAGE.md`, and `docs/roadmap.md` for current scope and priorities.

## Build tools by component

| Component | Build with |
|-----------|-----------|
| yfinance MCP server | `/pde:design-doc` → `agent-skills:build` |
| EDGAR MCP server | `/pde:design-doc` → `agent-skills:build` |
| `/stock-signal`, `/stock-screen`, `/stock-timing`, `/stock-model`, `/stock-equity` skills | `skill-creator:skill-creator` |
| Report UI (Vite + React) | `agent-skills:build` |

## Permissions

Per-agent local settings pre-allow `rtk ls *` and `rtk read *` — use these instead of bare `ls`/`cat`.

- Claude Code: `.claude/settings.local.json`
- Codex: `.codex/settings.local.json`

## Linear workflow

Linear is authoritative for status. Local task lists are fine for within-session bookkeeping; they don't replace a Linear issue.

**Project:** Equity skill pack — https://linear.app/ababushkin/project/equity-skill-pack-b8446cbaab6b/overview (team ABA / Personal).

**Cycles.** Work is planned across cycles, often spanning multiple projects at once. When picking up an issue, prefer ones already in the current cycle. If you start something not in the cycle, decide explicitly whether to pull it in or defer — don't silently expand cycle scope. Use `mcp__linear-server__list_cycles` to see the current cycle.

**On start of any issue:**
- Move to **In Progress** via `mcp__linear-server__save_issue`.
- If the issue isn't yet in the current cycle and you intend to ship it this cycle, assign it to the current cycle.

**On completion:**
- Move to **Done** only after the work is committed AND pushed. An issue isn't Done if the work only exists on a local branch.
- Status updates happen at the moment of state change — not batched at end of session.

**Blocked** = leave In Progress + add a blocker comment naming the blocker. Don't silently park work.

**New work surfaced mid-flight** becomes a new Linear issue, slotted into a cycle deliberately. Don't silently expand scope.

## Git

Conventional-commit-ish prefixes: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`. Subject line ≤ 70 chars; details in the body if needed. Push directly to main; PRs only when the owner asks. Do not add `Co-Authored-By` trailers.
