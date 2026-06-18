# AGENTS.md

Instructions for any coding agent (Claude Code, Codex, etc.) working in this repository. Tool-agnostic by design — see `CLAUDE.md` for any Claude-Code-specific additions.

## What this repo is

A personal equity research skill-pack for a tech-focused investor. See `CHARTER.md` for what this pack is for and which boundaries are locked, and `DESIGN.md` for the architectural reference.

## Operating principle

Depth on a curated set of specialist-supported tickers — see `CHARTER.md`, `COVERAGE.md`, and `docs/roadmap.md` for current scope and priorities.

## Build tools by component

| Component | Build with |
|-----------|-----------|
| yfinance MCP server | `/pde:design-doc` → `agent-skills:build` |
| EDGAR MCP server | `/pde:design-doc` → `agent-skills:build` |
| `/stock-signal`, `/stock-screen`, `/stock-timing`, `/stock-model`, `/stock-equity` skills | `skill-creator:skill-creator` |
| Report UI (Vite + React) | `agent-skills:build` |

