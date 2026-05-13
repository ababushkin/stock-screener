---
name: yf-ratios-html-fallback
status: draft
authors: Anton Babushkin
created: 2026-05-13
last_updated: 2026-05-13
supersedes: none
linear: ABA-72
---

# yf MCP: HTML fallback for `get_ratios` when `Ticker.info` is unusable

## Problem

`mcp__yf__get_ratios` raises `YFNoDataError` whenever `Ticker.info` does not
return `priceToSalesTrailing12Months`, regardless of whether the underlying
numbers are reachable through other Yahoo surfaces. The current known trigger
is non-US Nasdaq ADRs (e.g. KSPI), where sibling tools `get_financials` and
`get_estimates` return full data for the same ticker — but this is one
manifestation of a more general problem. Yahoo's JSON `quoteSummary` endpoint
has been progressively tightened since 2023; long-tail coverage gaps are
expected to recur for reasons we have not yet catalogued (other dual-listings,
recently-IPO'd tickers, restructured share classes, temporarily throttled
endpoints, etc.). The `/signal` skill treats missing P/S as a hard fail (it is
the minimum viable signal), so the entire workflow stops whenever this gap
fires — even when the data is fetchable elsewhere.

Affected users: the single human investor running this skill pack today, plus
every future skill (`/screen`, `/model`) that consumes `get_ratios`. Affected
universe: any ticker for which `Ticker.info` is sparse — KSPI is the
worked example, not the bound.

Current behaviour: `get_ratios` raises on any ticker where `Ticker.info` is
missing `priceToSalesTrailing12Months`, regardless of why or whether the same
fields are reachable through other Yahoo surfaces.

Desired behaviour: `get_ratios` returns populated `pe_ratio`, `ps_ratio`,
`ev_ebitda`, `ev_revenue`, `pfcf`, `eps_ttm`, `sharesOutstanding`,
`currentPrice`, and `marketCap` for any ticker where those values are reachable
through any Yahoo surface, including the public quote and key-statistics HTML
pages. Callers can distinguish API-sourced from HTML-sourced values via a
`source` field.

## Context

The `yfinance` library calls Yahoo's `query1.finance.yahoo.com` JSON endpoints
(`v7`/`v10`/`v11`). Yahoo tightened crumb/cookie auth in 2023–24 and coverage
gaps have been appearing in the long tail since; non-US filers are the
currently-observed casualty but we should expect this to be one of several
recurring failure shapes rather than the only one. The HTML-rendered pages
at `finance.yahoo.com/quote/{TICKER}` and `/quote/{TICKER}/key-statistics` hit a
different server path with session context and still carry the full numbers —
validated 2026-05-13 against KSPI in the comment thread on ABA-72. The
fallback is positioned as a general escape hatch for `Ticker.info` misses,
not a KSPI- or ADR-specific workaround.

Related prior work:
- `mcp/yf/tools.py:291` — current `get_ratios` implementation.
- `mcp/yf/tools.py:18` — `get_fx_rate` (ABA-73). Already supports the currency
  normalisation path callers will eventually want; orthogonal to this work.
- ABA-74 — skills-side manual-input fallback. This design doc reduces (but does
  not eliminate) the frequency at which ABA-74 fires.
- ABA-75 — EDGAR/20-F SBC fallback. Out of scope: SBC is not on Yahoo's HTML
  page for KSPI either, so it stays in ABA-75's lane.
- ABA-68/69/70 — sibling yf MCP gaps. Independent.

Inherited constraints:
- `get_ratios` is called synchronously inside `/signal`; latency is user-facing.
- Single-user pack; no concurrency or rate-limit pressure on Yahoo today.
- No existing scraping dependencies in the yf MCP — `requirements.txt` is just
  `mcp[cli]` and `yfinance`.

## Constraints

Functional:
- `get_ratios(ticker)` returns the same response shape it does today, plus a
  `source` field with values `"yahoo_api"` | `"yahoo_html"`.
- When `Ticker.info` returns a usable `priceToSalesTrailing12Months`, behaviour
  is unchanged — happy path is not regressed.
- When `Ticker.info` is unusable, the function attempts the HTML fallback
  before raising `YFNoDataError`.
- The response on fallback populates at minimum: `pe_ratio`, `ps_ratio`,
  `eps_ttm`, `sharesOutstanding`, `currentPrice`, `marketCap`. `ev_ebitda`,
  `ev_revenue`, `pfcf` are populated when present on the HTML page; `None`
  otherwise (current behaviour for fields the API doesn't return).
- `reporting_currency` field added to `get_ratios` response, sourced from the
  HTML page where possible (KSPI shows USD on the ADR page), `None` when not
  determinable. This is the minimal slice of option (2) from the ticket body —
  full schema-wide currency normalisation across `get_financials` is deferred
  to a follow-up.

Non-functional (with fitness functions):

| NFR | Target | Fitness function |
|---|---|---|
| Happy-path latency (API hit) | p95 ≤ 1.0s, unchanged from today | `test_get_ratios_latency` — measures `time.monotonic()` around `get_ratios("AAPL")`, asserts < 1.0s, runs in CI nightly |
| Fallback latency (HTML hit, no retry) | p95 ≤ 3.0s end-to-end when first HTTP attempt succeeds | `test_get_ratios_html_fallback_latency` — measures `get_ratios("KSPI")`, asserts < 3.0s, runs in CI nightly |
| Fallback latency (worst case, 3 retries) | p99 ≤ 12s end-to-end (3 attempts × 5s timeout, with backoff) | `test_get_ratios_html_retry_budget` — mocks transient failures, asserts total elapsed < 12s and all 3 attempts fire |
| Fallback correctness | KSPI returns `pe_ratio`, `ps_ratio`, `currentPrice` within ±2% of HTML-displayed values | `test_get_ratios_kspi_fallback_values` — calls `get_ratios("KSPI")`, asserts fields populated and within tolerance of a recorded fixture, runs in CI nightly |
| Happy path not regressed | AAPL / MSFT / NVDA return `source: "yahoo_api"` and identical numeric fields as today | `test_get_ratios_us_megacap_unchanged` — golden-fixture comparison, runs in CI on every commit |
| Scraper resilience | When Yahoo HTML markup changes, failure is loud (raises `YFNoDataError`) not silent (returns `None` everywhere) | `test_get_ratios_html_malformed_raises` — feeds the parser a stub HTML with renamed table rows, asserts `YFNoDataError` raised |
| Dependency footprint | At most one new runtime dependency added | `requirements.txt` review at PR time; `pip-audit` in CI |

Out of scope (explicit non-goals):
- Currency normalisation across `get_financials`, `get_estimates`, `get_earnings_history` (heavier schema change; revisit when a second non-USD ticker appears).
- SBC for non-US filers (ABA-75).
- Pre-fetching / caching scraped values across processes (single-user pack — not worth the cache-invalidation surface today).

## Alternatives considered

### A. Do nothing — keep raising `YFNoDataError`; rely on ABA-74 skill-side manual-input fallback

- Description: ship ABA-74 instead (or first), let the human paste KSPI's ratios into the conversation when `/signal KSPI` halts.
- Blast radius: zero (no code change here). Cost is paid every signal run on every non-US ADR — recurring friction.
- Reversal cost: zero.
- Why not: blocks the workflow ABA-72 was filed to fix, and the long tail of non-US ADRs means this friction recurs indefinitely. ABA-74 is still worth shipping as the universal escape hatch but is the wrong primary answer here.

### B. Derive ratios locally from `get_financials` + `Ticker.history`

- Description: option (1) from the ticket body. When `Ticker.info` is sparse, compute `pe_ratio = price × shares / net_income`, `ps_ratio = price × shares / revenue`, etc., from the income statement and a one-day history call.
- Blast radius: moderate. Local derivation introduces numerical drift vs. Yahoo's TTM (which uses interim quarterly data the annual statement doesn't carry). For KSPI specifically, `get_financials` returns annual KZT data while the ADR trades in USD — derivation requires FX normalisation in the MCP, which is exactly the currency-aware-schema work we're deferring.
- Reversal cost: low (one function, easy to delete).
- Why not: lower precision than HTML scrape, more code (~3× the LOC of a focused scraper), and forces the currency work this design is explicitly scoping out. HTML scrape gets us Yahoo's own TTM number for free.

### C. HTML scrape of `finance.yahoo.com/quote/{TICKER}` + `/key-statistics` (recommended)

- Description: option (3) from the comment thread. On `Ticker.info` miss, fetch the two HTML pages with `requests` + a real `User-Agent` header, parse with `BeautifulSoup`, extract the labelled table rows. Return the standard `get_ratios` shape with `source: "yahoo_html"`. No Playwright — both pages render the needed fields in server-side HTML; no JS execution required (re-verified during context-loading step).
- Blast radius: moderate. Coupled to Yahoo's HTML structure — when they rename a table row label or restructure the page, the scraper breaks. Bounded by the fitness function `test_get_ratios_html_malformed_raises` which makes the failure loud rather than silent.
- Reversal cost: low. The scrape path is one helper function (`_scrape_yahoo_html`) gated by an exception handler in `get_ratios`. Removing it restores today's behaviour with one revert.
- Why this: matches Yahoo's own TTM numbers (no derivation drift), no FX wrangling needed for KSPI (the ADR page is already USD), small dependency footprint (`requests` + `beautifulsoup4` — both boring, both 15+ years old).

### D. Playwright headless browser

- Description: full browser automation against the same pages.
- Blast radius: large. ~100MB of Chromium per environment, slow startup, new operational surface.
- Reversal cost: moderate.
- Why not: unnecessary — manual Playwright verification (2026-05-13 comment) confirmed the fields are in server-rendered HTML. Reaching for Playwright burns innovation tokens (Universal Principle 10) when `requests` suffices.

## Recommended approach

**Alternative C — `requests` + `BeautifulSoup` HTML fallback inside the MCP.**

Implementation shape:

```python
def get_ratios(ticker: str) -> dict:
    info = yf.Ticker(ticker).info or {}
    ps = info.get("priceToSalesTrailing12Months")
    if ps:
        return _ratios_from_info(ticker, info)  # source: "yahoo_api"
    try:
        return _ratios_from_html(ticker)        # source: "yahoo_html"
    except _ScrapeError as e:
        raise YFNoDataError(...) from e
```

Helper structure:
- `_ratios_from_info(ticker, info)` — extracted from current code, no behaviour change. Adds `source: "yahoo_api"` and `reporting_currency` (from `info.get("financialCurrency")` when present).
- `_ratios_from_html(ticker)` — new. Fetches two URLs with a 5s timeout, parses with `BeautifulSoup`. Returns the standard shape with `source: "yahoo_html"`. Raises `_ScrapeError` (internal) on any parse failure.
- `_fetch_with_retry(url, attempts=3)` — new. Retries up to 3 attempts on transient network errors (connection failure, timeout, 5xx, 429) with exponential backoff (0.5s, 1.0s, 2.0s). Does **not** retry on 4xx other than 429, on successful 200 with malformed HTML, or on parse failures — those are not transient and a retry is wasted time.
- `_parse_kv_table(soup, label)` — small helper. The two pages share a labelled-row pattern (`<td>Label</td><td>Value</td>`); one parser handles both.

New dependency: `beautifulsoup4`. `requests` is already a transitive of `yfinance` so does not add a new top-level. We pin `beautifulsoup4>=4.12` in `requirements.txt`.

The recommendation beats B (derive locally) on precision and on staying out of the currency-schema work. It beats D (Playwright) on dependency footprint and latency. It beats A (do nothing) on the entire reason the ticket was filed.

## Consequences

Positive:
- `/signal KSPI` runs end-to-end without manual input. Same path will work for the next non-US ADR encountered.
- `source` field gives downstream skills a signal to factor into their qualitative overlay (e.g. `/signal` can note "ratios HTML-sourced — re-check if anomalous").
- Latency budget for happy path is unchanged (fallback is only invoked on API miss).
- Small, surgical PR — one helper added, one branch added in `get_ratios`.

Negative:
- New maintenance surface: when Yahoo restructures the HTML, the scraper breaks. Mitigated by the `test_get_ratios_kspi_fallback_values` nightly fitness function — failure shows up in CI, not in a live signal run weeks later.
- Adds `beautifulsoup4` as a dependency. Boring, but still a token spent.
- `reporting_currency` is partial — populated only when Yahoo exposes it. The schema gap (currency-aware `get_financials`) remains.

**Walking skeleton: not required.** Integration risk is fully known. The path is a single function call into an existing tested module, with no new deployment, no new service, no new contract for upstream consumers. The happy path is unchanged. We proceed straight to incremental implementation.

## Operability plan

**Metrics (stderr structured logs — same pattern as existing tools):**
- `[yf] get_ratios({ticker}).info → {n_keys} keys in {elapsed:.2f}s` — unchanged, happy path.
- `[yf] get_ratios({ticker}).html → {n_fields} fields in {elapsed:.2f}s source=yahoo_html` — new, fallback path.
- `[yf] get_ratios({ticker}).html FAILED in {elapsed:.2f}s reason={short}` — new, fallback failure.

**Logs:** the three log lines above are the operability surface. Single-user pack means stderr is the dashboard.

**Traces:** N/A (no distributed system).

**Alerts:** the CI fitness functions are the alerting layer. Nightly KSPI fallback test failing = page-equivalent for this single-user system (manifested as a red GitHub Actions run on the next push).

**Rollback plan:**
1. Revert the PR adding `_ratios_from_html` and the branch in `get_ratios`. One commit.
2. Estimated time: 5 minutes including CI run.
3. Behaviour reverts to today: `YFNoDataError` on KSPI; `/signal KSPI` falls back to ABA-74 manual-input path (once ABA-74 ships) or hard stop (today).

**Capacity headroom:** Yahoo's public HTML pages are not rate-limited at the volumes a single-user research pack generates (well under 100 requests/day). No concurrency to worry about. A 5s `requests` timeout caps worst-case latency.

**Known failure modes:**
- Yahoo HTML markup change → `_ScrapeError` → `YFNoDataError` raised → caller sees same error as today. Loud failure. Detected by nightly fitness function.
- Yahoo rate-limits the User-Agent → 429 → `_fetch_with_retry` retries up to 3 times with exponential backoff; if all retries fail, `_ScrapeError` → `YFNoDataError`. 403 is treated as non-transient (no retry). If 429s become routine, escalate to a UA-rotation pool (not in this design — premature).
- Ticker exists on Yahoo HTML but `key-statistics` page is missing a row → field returns `None` → response shape preserved with that field nulled. Existing pattern for partial coverage.
- `requests` connection failure / timeout → `_ScrapeError` → `YFNoDataError` after 5s. Acceptable for a non-real-time research workflow.

**Upstream dependencies:** `finance.yahoo.com` HTML rendering — no SLA, never had one. We are a guest. Mitigation: fail loud, fixture-test continuously.

**Downstream dependencies:** `/signal`, `/screen`, `/model` all consume `get_ratios`. Adding `source` and `reporting_currency` fields is additive — existing callers ignore them. No breaking change.

## Resolved decisions (carried forward from open questions)

- **Q2 (resolved 2026-05-13):** `source` field is scoped strictly to `get_ratios` in this PR. Sibling tools (`get_financials`, `get_estimates`) gain the field in a follow-up if/when they grow fallbacks of their own.
- **Q3 (resolved 2026-05-13):** Retry up to 3 attempts on transient network errors (connection failure, timeout, 5xx, 429) with exponential backoff (0.5s / 1.0s / 2.0s). Do not retry on 4xx (other than 429) or on parse failures.
- **Q1 (resolved 2026-05-13 during Slice 1 spike):** Yahoo's key-statistics HTML page does NOT surface `financialCurrency` (KZT for KSPI) as a structured field. The visible header reads "NasdaqGS - Nasdaq Real Time Price • USD" — that's the *trade* currency, not the reporting currency. Decision: on the HTML path, set `reporting_currency` from `Ticker.info["financialCurrency"]` when present (it is present for KSPI even when ratios are missing), otherwise `None`. The HTML page is parsed only for *ratios*, not for currency.
- **Transport (resolved 2026-05-13 during Slice 1 spike):** `requests` and `curl` both receive HTTP 404 from `/quote/{TICKER}/key-statistics/` for KSPI and AAPL — Yahoo's edge bot-detects by TLS fingerprint, not just User-Agent. Switched to `curl_cffi` with `impersonate="chrome"` which returns 200/~2MB on all probed tickers. `curl_cffi` is a ~1MB pure-Python wrapper around libcurl-impersonate; it does NOT require a real browser binary. Dependency change in Slice 5: add `curl_cffi>=0.7` instead of (or in addition to) bare `requests`. Still pinned: `beautifulsoup4>=4.12`.
- **DOM hook (recorded 2026-05-13 during Slice 1 spike):** the Valuation Measures block lives at `<section data-testid="qsp-statistics"> > div.table-container > table` (first table within that section). Each `<tr>` has the format `label | Current | Q-1 | Q-2 | Q-3 | Q-4 | Q-5`. The "Current" column (index 1) is the value we want. Confirmed labels: "Market Cap", "Enterprise Value", "Trailing P/E", "Forward P/E", "PEG Ratio (5yr expected)", "Price/Sales", "Price/Book", "Enterprise Value/Revenue", "Enterprise Value/EBITDA". The `data-testid` attribute is a stable hook; the inner `yf-l6kdm7` class is generated and must NOT be relied on.

## Open questions

(none — Q1 resolved during Slice 1 spike, see above.)
