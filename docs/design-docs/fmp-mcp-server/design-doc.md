---
name: fmp-mcp-server
status: accepted
authors: Anton Babushkin
created: 2026-05-12
last_updated: 2026-05-12
supersedes: none
---

# FMP MCP Server

## Problem

The equity research skills (/screen, /signal, /model, /timing, /equity) need real financial data — income statements, valuation ratios, earnings history, price targets, revenue segments — to produce research output. Currently there is no programmatic interface between those skills and the Financial Modeling Prep REST API.

Without a shared data interface, each skill would either: (a) fall back to user-provided inputs and produce placeholder output, or (b) implement its own HTTP layer — duplicating FMP-specific logic across five skill files and making the data source impossible to change without touching every skill.

Desired behaviour: each skill calls a named MCP tool (e.g. `get_ratios("NVDA")`) and receives a typed Python dict. The HTTP details, API key, and response-shape normalisation are invisible to the skill.

## Context

**Project:** Equity research skill-pack at `/Users/anton/src/stock-review`. See `SPEC.md` for the full spec.

**FMP API:** Financial Modeling Prep, basic tier. Base URL: `https://financialmodelingprep.com/stable/`. API key stored in `.env` as `FMP_API_KEY` (gitignored; never committed).

**Stable/ prefix is mandatory.** The legacy `v3/` endpoints return HTTP 402. Confirmed in prior testing.

**Known basic-tier constraints (confirmed by testing):**
- `earnings-surprises` endpoint: premium-only, returns empty.
- `analyst-estimates` history: premium-only, returns empty.
- SBC (stock-based compensation): no dedicated field in the income statement response; must be fetched from EDGAR separately.
- SUE derivation: `epsActual` vs `epsEstimated` fields in `stable/earnings` calendar — no pre-computed endpoint.
- NTM estimates: `epsEstimated` and `revenueEstimated` fields in `stable/earnings` calendar entries.
- CIK for EDGAR: available directly from `stable/profile` response (`cik` field).

**Data priority chain (from SPEC.md):** FMP (primary) → EDGAR XBRL (authoritative for SBC, capex, D&A) → web search (transcripts) → user-provided (last resort).

**MCP transport:** Claude Code loads MCP servers from `.claude/settings.json`. The server runs locally; skills call it via the MCP tool-calling protocol.

**No prior design docs or ADRs.** This is the first component in the project.

## Constraints

**Functional:**
1. Expose 6 tools matching SPEC.md names: `get_financials`, `get_ratios`, `get_estimates`, `get_earnings_history`, `get_analyst_targets`, `get_revenue_segments`.
2. API key loaded from environment (`os.environ["FMP_API_KEY"]`); never hardcoded.
3. Each tool returns a Python dict with named fields — not a raw JSON string or list.
4. Each tool raises a descriptive exception (not silently returns `{}`) when FMP returns an error or empty response.
5. `get_financials` includes the `cik` field from `stable/profile` so skills can pass it to the EDGAR MCP without a separate call.

**Non-functional:**
- **Response latency:** < 5 s p95 per tool call. FMP typical response is 200–500 ms; 10 s timeout headroom. Fitness function: manual timing during integration test on Task 1 acceptance.
- **API key security:** `FMP_API_KEY` must not appear in tool return values or stderr logs. Fitness function: grep tool outputs and stderr for the key string after a test run.
- **Rate limit compliance:** FMP basic tier limit is approximately 250 requests/day. No server-side throttle is required for single-developer use, but callers must not batch-call all 6 tools per ticker in automated loops. Fitness function: manual awareness; documented in SPEC.md constraint list.
- **Startup reliability:** `python mcp/fmp/server.py` exits non-zero with a clear message if `FMP_API_KEY` is absent. Fitness function: `unset FMP_API_KEY && python mcp/fmp/server.py` returns non-zero.
- **Dependency footprint:** ≤ 3 direct Python dependencies, managed via `mise`. Fitness function: `mise run pip-check` in `mcp/fmp/`.

## Alternatives considered

**Alt 1 — Do nothing (skills call FMP via Bash curl)**  
Each skill uses the Bash tool to call `curl https://financialmodelingprep.com/stable/...` and parses stdout.  
*Blast radius:* FMP-specific HTTP logic is duplicated across all five skills. API key location change requires touching every skill. Response-shape changes (FMP schema drift) require coordinated fixes in multiple files.  
*Reversal cost:* High — all 5 skills must be rewritten to remove inline HTTP calls.  
*Rejected because:* Violates single-responsibility; makes the data layer impossible to maintain independently.

**Alt 2 — Standalone Python script (not an MCP server)**  
A `mcp/fmp/fetch.py` script that skills invoke via `python mcp/fmp/fetch.py get_ratios NVDA`.  
*Blast radius:* Skills shell out via Bash and parse stdout JSON — brittle to stdout formatting. No type checking on tool inputs.  
*Reversal cost:* Medium — the script logic ports cleanly to MCP; only the invocation interface changes.  
*Rejected because:* Bash subprocess parsing is fragile and loses the structured tool-calling protocol that MCP provides.

**Alt 3 — FastMCP Python server (recommended)**  
A Python server using `mcp.server.fastmcp.FastMCP` at `mcp/fmp/server.py`.  
*Blast radius:* If FastMCP is the wrong framework, migration to the lower-level MCP SDK rewrites `server.py` only — all tool implementations (`tools.py`) stay identical.  
*Reversal cost:* Low — tool signatures are framework-agnostic Python functions.

**Alt 4 — Official low-level MCP Python SDK**  
`mcp.server.Server` directly, without FastMCP.  
Functionally equivalent to Alt 3 but 3–5× more boilerplate per tool. FastMCP is the officially recommended pattern (it is part of the `mcp` package as of v1.x).  
*Rejected because:* No benefit over FastMCP; higher cognitive overhead with identical blast radius.

## Recommended approach

**FastMCP Python server** at `mcp/fmp/server.py` with tool implementations in `mcp/fmp/tools.py`.

```
mcp/fmp/
├── server.py           # FastMCP app, registers tools, loads env
├── tools.py            # Tool implementations (one function per tool)
├── requirements.txt    # mcp[cli], httpx, python-dotenv
└── mise.toml           # Python task runner
```

**Framework:** `from mcp.server.fastmcp import FastMCP`. Each tool is a `@mcp.tool()` decorated function. This is the canonical FastMCP pattern as of `mcp` v1.x.

**API key loading:** `python-dotenv` loads `.env` at startup. `server.py` validates `FMP_API_KEY` is present before registering tools; raises `SystemExit(1)` with a clear message if absent.

**HTTP client:** `httpx` (sync, not async) for simplicity. All FMP calls use `httpx.get(url, params={"apikey": key}, timeout=10.0)`.

**Tool → FMP endpoint mapping:**

| Tool | FMP endpoint(s) | Returns |
|------|-----------------|---------|
| `get_financials(ticker, period="annual")` | `stable/income-statement`, `stable/cash-flow-statement`, `stable/profile` | dict with income, cashflow, and cik fields |
| `get_ratios(ticker)` | `stable/key-metrics` | dict with pe_ratio, ps_ratio, ev_ebitda, pfcf, ev_revenue |
| `get_estimates(ticker)` | `stable/earnings` (future entries) | dict with ntm_eps_estimate, ntm_revenue_estimate, analyst_count |
| `get_earnings_history(ticker, n=8)` | `stable/earnings` (past n entries) | list of dicts: {date, eps_actual, eps_estimated, surprise_pct, revenue_actual, revenue_estimated} |
| `get_analyst_targets(ticker)` | `stable/price-target-consensus` | dict with target_high, target_low, target_consensus, target_median |
| `get_revenue_segments(ticker)` | `stable/revenue-product-segmentation` | list of dicts: {segment, revenue, period} |

**Error handling:** Two custom exceptions in `tools.py`:
- `FMPNoDataError(ticker, endpoint)` — FMP returned `[]` or `{}`.
- `FMPPremiumError(endpoint)` — HTTP 402 (premium-only endpoint called by mistake).

All other HTTP errors propagate as `httpx.HTTPStatusError`.

**Walking skeleton scope (Task 1 / ABA-5):** Implement `server.py` + `get_ratios` only. The skeleton proves: env loading works, httpx call succeeds, FastMCP tool registration works, and the MCP client receives a typed dict. The remaining 5 tools are Task 4–8 (ABA-8 through ABA-12).

## Consequences

**Positive:**
- All five skills get a clean, versioned data interface — FMP-specific logic lives in one place.
- CIK is available to skills from `get_financials` without a separate EDGAR call.
- Swapping FMP for a different data provider requires only changes to `tools.py`, not skill files.
- FastMCP's `@mcp.tool()` decorator auto-generates tool schemas from Python type hints — no manual schema maintenance.

**Negative:**
- Requires 3 Python dependencies (`mcp`, `httpx`, `python-dotenv`) managed via `mise` (already installed). First-time `mise install` + `pip install` takes ~60 s; subsequent starts are instant.
- Skills must run in a Claude Code session with the MCP server configured in `.claude/settings.json`.
- Basic-tier rate limit (~250 req/day) is not enforced server-side. A skill that calls all 6 tools per ticker uses ~6 requests; a 10-ticker screen uses ~60. Acceptable for personal use, but skill authors must not loop without thought.

**Walking skeleton (Rule B2):** Task 1 builds `get_ratios` only and verifies the full path (env → httpx → FastMCP → MCP client → typed dict) before the remaining 5 tools are implemented.

## Operability plan

**Metrics:** None beyond manual verification. Single-developer local tool; no monitoring infrastructure.

**Structured logs:** `server.py` logs to stderr (MCP protocol requirement):
- On each tool call: `[fmp] {tool_name}({ticker}) → HTTP {status} in {elapsed:.2f}s` (API key redacted from URL before logging).
- On startup: `[fmp] FMP MCP server ready` or `[fmp] ERROR: FMP_API_KEY not set`.

**Traces:** Not applicable — local tool, single developer, no distributed tracing.

**Alerts:** Not applicable. Failure is immediate: the skill call raises an exception with a clear message.

**Rollback plan:** `git revert <commit>` restores the previous `server.py` and `tools.py`. Claude Code MCP server restarts automatically on next session. Time estimate: < 2 minutes.

**Capacity headroom:** ~250 req/day (basic tier). A full `/equity` run uses ~10–15 FMP calls. Single-developer use stays well within limits.

**Known failure modes:**

| Failure | Symptom | Mitigation |
|---------|---------|------------|
| `FMP_API_KEY` missing | `SystemExit(1)` at startup with clear message | Validate at import time; message names the `.env` file |
| HTTP 402 (premium endpoint) | `FMPPremiumError` propagates to skill | Document premium-only endpoints in SPEC.md (already done); don't call them |
| HTTP 429 (rate limit hit) | `httpx.HTTPStatusError(429)` | Pass-through; skill logs and asks user to retry later |
| FMP returns `[]` (valid — no data for ticker) | `FMPNoDataError` propagates to skill | Explicit check before dict construction; skill can request user input |
| FMP down / network error | `httpx.ConnectError` or `TimeoutException` | 10 s timeout; pass-through with clear traceback |
| FMP schema drift (field renamed) | Tool returns `None` for affected fields | Defensive `.get(key, None)` on all field extractions; skill checks for `None` and sets CONFIDENCE = LOW |

**Upstream dependency:** FMP API. No SLA for basic tier. If FMP is unreachable, all skills requiring financial data degrade to user-provided inputs (per SPEC.md data priority chain).

**Downstream dependency:** None. The MCP server has no downstream dependencies of its own.

## Open questions

None blocking implementation. All API constraints are confirmed from prior testing. FastMCP vs low-level SDK is resolved in favour of FastMCP (Alt 3 above).
