# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A personal equity research skill-pack for a tech-focused investor. See `SPEC.md` for the full technical spec.

Tasks and milestones live in Linear: https://linear.app/ababushkin/project/ai-equity-research-skill-pack-b8446cbaab6b/overview

## Build tools by component

| Component | Build with |
|-----------|-----------|
| yfinance MCP server | `/pde:design-doc` → `agent-skills:build` |
| EDGAR MCP server | `/pde:design-doc` → `agent-skills:build` |
| `/signal`, `/screen`, `/timing`, `/model`, `/equity` skills | `skill-creator:skill-creator` |
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

## Git

Do not add `Co-Authored-By` trailers to commit messages.
