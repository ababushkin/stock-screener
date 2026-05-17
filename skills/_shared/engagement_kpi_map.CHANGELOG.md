# engagement_kpi_map.json — Changelog

All edits to `engagement_kpi_map.json` are recorded here with date, ticker(s) affected, source-link evidence, and the issue/ADR that motivated the change.

Schema version is monotonic-integer; bumps require an ADR.

---

## v2 — 2026-05-14 — Add PINS for Task 6 backtest sample floor

**Schema version:** 2
**Author:** Anton Babushkin
**Linear:** [ABA-66](https://linear.app/ababushkin/issue/ABA-66) — Task 6 prerequisite per `docs/design-docs/engagement-kpi-enrichment/backtest-data-source.md`
**Spike branch:** `anton/aba-66-eng-kpi-spike`

### Tickers added

- **PINS** — primary `MAU` (Global Monthly Active Users), secondary `ARPU` (Global). Both disclosed YoY in 8-K Exhibit 99.1 every quarter since IPO (2019). Source phrase: "Global Monthly Active Users (\"MAUs\") increased 11% year over year to 631 million" — Q1 2026 press release (accession `0001506293-26-000066`, filed 2026-05-04). Adding PINS brings the backtest candidate pool from 21 (META 12 + RDDT 9) to ~29 ticker-quarters — comfortably clearing the NFR7 ≥24 floor with attrition headroom.

### Why PINS only (not PINS+SNAP+SPOT)

Task 4 feasibility note recommended PINS/SNAP/SPOT to comfortably hit the 40-target. Smallest-batch principle (universal P8): one ticker addition is enough to clear the ≥24 floor with headroom (29 candidates). Adding SNAP/SPOT is deferred to a follow-up only if Task 6's hit rate is borderline and the larger sample would tighten the binomial p-value materially. This avoids authoring 3 ticker maps before knowing whether even one extra is needed.

### Schema bump rationale

Per the versioning convention, adding a new ticker bumps `schema_version` from 1 → 2. Future Task 8 will produce the versioning ADR formally — this v2 bump is the first practical instance the ADR will codify.

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
