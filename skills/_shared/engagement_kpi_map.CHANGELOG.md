# engagement_kpi_map.json — Changelog

All edits to `engagement_kpi_map.json` are recorded here with date, ticker(s) affected, source-link evidence, and the issue/ADR that motivated the change.

Schema version is monotonic-integer; bumps require an ADR.

---

## v1 — 2026-05-14 — Seed map for ABA-66 walking skeleton

**Schema version:** 1
**Author:** Anton Babushkin
**Linear:** [ABA-66](https://linear.app/ababushkin/issue/ABA-66)
**Spike branch:** `anton/aba-66-eng-kpi-spike`

### Tickers added

- **META** — primary `DAP` (Family Daily Active People), secondary `ad_impressions`. Both disclosed YoY in 8-K Exhibit 99.1 from Q1 2023 onward (META rebranded DAU→DAP in 2023). Evidence: 8-K filed 2026-04-29 (accession `0001628280-26-028364`).
- **RDDT** — primary `DAUq` (Daily Active Uniques), secondary `ARPU`. Both disclosed YoY in 8-K Exhibit 99.1 every quarter since IPO. Evidence: 8-K filed 2026-04-30 (accession `0001713445-26-000067`).

### Tickers deliberately excluded (with reasons)

- **NFLX** (OQ3 resolution) — Netflix stopped quarterly disclosure of paid-sub net adds in Q1 2025. The Q1 2026 shareholder letter contains qualitative engagement language only ("primary internal quality metric hit an all-time high") plus headline revenue (+16% YoY) and operating income (+18% YoY). Revenue-on-revenue is circular for this modifier's purpose. No defensible substitute KPI for v1 — excluded. Revisit if NFLX reintroduces a quarterly engagement disclosure or shifts the bi-annual Engagement Report cadence to per-quarter.
- **GOOGL** (OQ6 resolution) — Alphabet does not disclose absolute Search CPM or impression volume per quarter. "Paid clicks" and "cost-per-click" appear only as YoY percentage deltas, not absolute values; YouTube revenue is a segment line, not an engagement KPI. No defensible primary mapping for v1 — excluded. Revisit if segment disclosure expands or YouTube view-hours become quarterly.

### What's not in this version

- AMZN — segment revenue is owned by ABA-65 (XBRL-structured), out of scope here.
- XYZ (Block) — Cash App MAU + gross-profit-per-active disclosed quarterly in shareholder letter; deferred to v2 pending walking-skeleton evidence on the two anchored tickers.
- INFRASTRUCTURE tickers (NVDA/AMD/AVGO/MU) — out of scope by ticket boundary.
