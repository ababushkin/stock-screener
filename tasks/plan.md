# Plan — yf MCP `get_ratios` HTML fallback (ABA-72)

**Spec:** `docs/design-docs/yf-ratios-html-fallback/design-doc.md` (status: accepted, crit-approved 2026-05-13)
**Linear:** ABA-72
**Scope:** single function in `mcp/yf/tools.py` + new helpers + new dep + tests.

## Dependency graph

```
Slice 1 (spike + parser) ──┬─→ Slice 3 (wire fallback in get_ratios)
Slice 2 (retry helper) ────┘                  │
                                              ↓
                                       Slice 4 (fitness tests)
                                              │
                                              ↓
                                       Slice 5 (deps + CI)
```

Slices 1 and 2 are independent and can run in parallel; both feed Slice 3. Slice 4 codifies Slice 3 behaviour. Slice 5 finalises packaging.

## Vertical slicing rationale

Each slice ends with a runnable, demonstrable artefact. We avoid horizontal layering (e.g. "all parsers first, then all callers"); each slice exercises a real call path.

---

## Slice 1 — KSPI spike: fetch + parse Yahoo HTML pages

**Goal:** resolve Open Question 1 (does `financialCurrency` appear on the HTML page?) and produce a working `_ratios_from_html(ticker)` helper for KSPI.

**Work:**
- Fetch `https://finance.yahoo.com/quote/KSPI/key-statistics/` with `curl_cffi` (`impersonate="chrome"`). Plain `requests` / `curl` get 404 — Yahoo bot-detects by TLS fingerprint. (Resolved in spike 2026-05-13.)
- Parse with `BeautifulSoup`. Implement `_parse_valuation_table(soup)` that targets `<section data-testid="qsp-statistics"> > .table-container > table` (first table in the section) and returns a `{label → Current value}` dict using the "Current" column (index 1).
- Extract from the table: `pe_ratio` (Trailing P/E), `ps_ratio` (Price/Sales), `marketCap` (Market Cap), `enterpriseValue` (Enterprise Value), `ev_revenue` (Enterprise Value/Revenue), `ev_ebitda` (Enterprise Value/EBITDA). Convert "16.24B" / "189.88M" / "2.42T" strings to floats via a small `_parse_si_number` helper.
- Open Question 1 already resolved in the spike (HTML page does not surface `financialCurrency`; read it from `Ticker.info` on the wired path).
- Define internal `_ScrapeError` exception.

**Acceptance criteria:**
- `_ratios_from_html("KSPI")` returns a dict with all required fields populated.
- Returned `pe_ratio`, `ps_ratio`, `currentPrice` are within ±2% of values manually read off the Yahoo page at the same moment.
- Open Question 1 is answered in writing (in the design doc) — either "`reporting_currency` is read from element X" or "no currency indicator on the page; default to None and document".

**Verification:**
- Manual REPL from `mcp/yf/`: `.venv/bin/python -c "from tools import _ratios_from_html; print(_ratios_from_html('KSPI'))"` prints populated dict.
- Eyeball comparison vs. live Yahoo page.

**Not in this slice:** retry logic, integration into `get_ratios`, tests as CI fitness functions.

---

## Slice 2 — `_fetch_with_retry` helper

**Goal:** isolate the retry policy in one tested helper. Independent of parsing.

**Work:**
- Implement `_fetch_with_retry(url, attempts=3, timeout=5.0)` returning a `curl_cffi` response.
- Retry on: `curl_cffi.requests.errors.RequestsError` with `code` matching connection/timeout, HTTP 5xx, HTTP 429. Backoff: 0.5s, 1.0s, 2.0s.
- Do NOT retry on: other 4xx, parse failures (parse failures don't reach this helper anyway).
- Raise `_ScrapeError` after exhausting retries.

**Acceptance criteria:**
- Helper retries exactly the documented set of transient errors.
- Helper does not retry non-transient 4xx (e.g. 403, 404).
- Total wall-clock for 3-retry exhaustion bounded by ~3.5s of sleeps + 3×5s timeouts ≤ 12s (matches NFR row 3).

**Verification:**
- Pytest with `requests_mock` or `responses`: 200 first try → 1 call; 500/500/200 → 3 calls, total elapsed > 1.5s sleep; 500/500/500 → raises after 3 calls; 404 → raises after 1 call (no retry); 429/200 → 2 calls.

---

## Checkpoint 1 — after Slices 1 + 2

Smoke test: hand-call `_fetch_with_retry` against the real Yahoo KSPI page, pass to `_ratios_from_html`. Confirm dict matches Slice 1 output. **Human review** of the answer to Open Question 1 before locking the response schema in Slice 3.

---

## Slice 3 — Wire fallback into `get_ratios`

**Goal:** the user-visible behaviour change. `get_ratios("KSPI")` returns populated data; `get_ratios("AAPL")` is unchanged.

**Work:**
- Extract current `get_ratios` body into `_ratios_from_info(ticker, info)`. Add `source: "yahoo_api"` and `reporting_currency: info.get("financialCurrency")`.
- Add the fallback branch:
  ```python
  if not ps_ratio:
      try:
          return _ratios_from_html(ticker)
      except _ScrapeError as e:
          raise YFNoDataError(...) from e
  ```
- Add `source: "yahoo_html"` and `reporting_currency` (per Slice 1 finding) to the HTML path return.
- Add the three new stderr log lines from the Operability section.

**Acceptance criteria:**
- `get_ratios("AAPL")` returns identical numeric fields to today (golden fixture) plus `source: "yahoo_api"`.
- `get_ratios("KSPI")` returns populated `pe_ratio`, `ps_ratio`, `currentPrice`, `marketCap`, `source: "yahoo_html"`.
- `get_ratios("CLEARLY_NOT_A_TICKER")` raises `YFNoDataError` (loud failure preserved).
- Stderr logs match the three lines documented in Operability.

**Verification:**
- Manual from `mcp/yf/`: `.venv/bin/python -c "from tools import get_ratios; print(get_ratios('KSPI'))"` and `... 'AAPL'`.
- Run `/signal KSPI` end-to-end — workflow completes through the ratios step.

---

## Checkpoint 2 — after Slice 3

End-to-end smoke: `/signal KSPI` and `/signal AAPL` both produce reports without error. **Human review** before codifying the behaviour as CI fitness functions (so we lock the right behaviour, not a buggy first cut).

---

## Slice 4 — Fitness functions (the 7 tests from the NFR table)

**Goal:** every NFR in the design doc has an automated check.

**Work:** add `mcp/yf/tests/test_get_ratios.py` with:

1. `test_get_ratios_latency` — `get_ratios("AAPL")` p95 < 1.0s (run 5×, take median to dampen noise; doc as nightly).
2. `test_get_ratios_html_fallback_latency` — `get_ratios("KSPI")` < 3.0s when first HTTP attempt succeeds.
3. `test_get_ratios_html_retry_budget` — mock 3 transient failures; assert total elapsed < 12s and 3 attempts fired.
4. `test_get_ratios_kspi_fallback_values` — `get_ratios("KSPI")` returns fields within ±2% of recorded fixture.
5. `test_get_ratios_us_megacap_unchanged` — golden fixture for AAPL/MSFT/NVDA, `source: "yahoo_api"`, numeric fields match within tolerance.
6. `test_get_ratios_html_malformed_raises` — feed parser stub HTML with renamed table rows; assert `YFNoDataError` (loud, not silent `None`-everywhere).
7. (impl-detail) `test_fetch_with_retry_*` — the Slice 2 retry tests live here.

**Acceptance criteria:**
- All tests pass locally (`pytest mcp/yf/tests/`).
- Tests requiring live Yahoo are marked `@pytest.mark.nightly` (so the every-commit CI run stays hermetic; nightly run hits the network).

**Verification:**
- `pytest mcp/yf/tests/ -m "not nightly"` green in the hermetic path.
- `pytest mcp/yf/tests/` green including live calls.

---

## Slice 5 — Dependencies and CI wiring

**Goal:** the new code is reproducibly installable and the fitness functions actually run.

**Work:**
- `mcp/yf/requirements.txt`: add `beautifulsoup4>=4.12` and `curl_cffi>=0.7`. Bare `requests` is insufficient — Yahoo bot-blocks it at the TLS layer for sub-pages.
- Add a `pytest` test-dep section if `requirements.txt` doesn't already have one, or add `mcp/yf/requirements-dev.txt`.
- If `.github/workflows/` exists, add or extend a workflow to run the hermetic tests on every push and the nightly tests on a schedule. If not, document the manual command in `mcp/yf/README.md` (single-user pack — CI is nice-to-have, not blocking).

**Acceptance criteria:**
- `pip install -r mcp/yf/requirements.txt` in a clean venv resolves cleanly.
- `pip-audit` reports no known CVEs against the new dep.
- CI workflow (if added) is green.

**Verification:**
- Clean-venv install test (Python 3.11+).
- Push to a feature branch and confirm Actions run green.

---

## Final checkpoint — pre-merge

- All slices verified.
- Linear ABA-72 set to In Progress at start of Slice 1, Done after merge.
- Smoke test `/signal KSPI` one more time on `main` after merge.
- Design doc status flipped from `draft` → `accepted`.
- Linear wave promotion check (per CLAUDE.md) — find issues blocked by ABA-72 and promote 1–3.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Slice 1 discovers `financialCurrency` isn't on the HTML page | Acceptable per design doc — `reporting_currency: None` is documented behaviour; document the finding and move on. |
| Yahoo HTML changes mid-build | Fitness function `test_get_ratios_html_malformed_raises` catches structural changes; if live KSPI breaks during build, retry once then escalate. |
| `beautifulsoup4` resolves an unexpected sub-dep | Slice 5 pip-audit and clean-venv install gate this. |
| Latency NFRs flake in CI | All latency tests measure median of N runs, not single-shot p95. Nightly-only so a single bad run doesn't block merges. |

## Out of scope (explicit non-goals — do not let scope creep in)

- Currency normalisation across `get_financials` / `get_estimates` (deferred per design doc).
- Skill-side manual-input fallback (ABA-74 — separate ticket).
- EDGAR SBC fallback (ABA-75 — separate ticket).
- UA-rotation / proxy pool for 429 mitigation (premature; not in design).
- Caching scraped values across processes (premature).
