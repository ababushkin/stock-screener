# Todo — ABA-72 yf MCP HTML fallback

Tracking the slices in `plan.md`. Tick boxes as work completes.

## Slice 1 — KSPI spike + parser
- [ ] Fetch KSPI quote + key-statistics HTML with realistic UA
- [ ] Implement `_parse_kv_table(soup, label)`
- [ ] Implement `_ratios_from_html(ticker)` for the KSPI fields
- [ ] Define `_ScrapeError`
- [ ] Resolve Open Question 1 — does the page expose currency? Document in design doc
- [ ] Verify: REPL call to `_ratios_from_html("KSPI")` populated; values within ±2% of live page

## Slice 2 — `_fetch_with_retry`
- [ ] Implement helper with 3 attempts, exponential backoff (0.5/1.0/2.0s), 5s timeout
- [ ] Distinguish transient (retry) from non-transient (raise) errors
- [ ] Unit tests with mocked HTTP — confirm retry counts for each error class

## Checkpoint 1
- [ ] Hand-combined smoke test (Slice 1 parser + Slice 2 retry against live Yahoo)
- [ ] Human review of Open Question 1 resolution

## Slice 3 — wire fallback into `get_ratios`
- [ ] Extract current body into `_ratios_from_info(ticker, info)`
- [ ] Add `source` + `reporting_currency` fields to both paths
- [ ] Add try/`_ScrapeError`/`YFNoDataError` branch
- [ ] Add three stderr log lines per Operability section
- [ ] Verify: `get_ratios("AAPL")` unchanged numerics + `source: "yahoo_api"`
- [ ] Verify: `get_ratios("KSPI")` populated + `source: "yahoo_html"`
- [ ] Verify: `get_ratios("NOTREAL")` still raises `YFNoDataError`

## Checkpoint 2
- [ ] End-to-end `/signal KSPI` succeeds
- [ ] End-to-end `/signal AAPL` unchanged
- [ ] Human review before codifying fitness tests

## Slice 4 — fitness functions
- [ ] `test_get_ratios_latency` (AAPL, p95 < 1.0s, nightly)
- [ ] `test_get_ratios_html_fallback_latency` (KSPI < 3.0s, nightly)
- [ ] `test_get_ratios_html_retry_budget` (mocked, < 12s)
- [ ] `test_get_ratios_kspi_fallback_values` (±2% vs fixture, nightly)
- [ ] `test_get_ratios_us_megacap_unchanged` (golden, every commit)
- [ ] `test_get_ratios_html_malformed_raises` (stub HTML)
- [ ] `test_fetch_with_retry_*` (carried over from Slice 2)
- [ ] All tests green locally (hermetic + nightly markers)

## Slice 5 — deps + CI
- [ ] Pin `beautifulsoup4>=4.12` in `mcp/yf/requirements.txt`
- [ ] Confirm `requests` resolves (transitive via yfinance) or pin explicitly
- [ ] `pip-audit` clean on new dep
- [ ] CI workflow (extend existing or document manual command)
- [ ] Clean-venv install passes on Python 3.11+

## Pre-merge
- [ ] Linear ABA-72 → Done after push
- [ ] Design doc status: `draft` → `accepted`
- [ ] Smoke `/signal KSPI` on `main` post-merge
- [ ] Linear wave promotion: find blocked-by-ABA-72 issues, promote 1–3
