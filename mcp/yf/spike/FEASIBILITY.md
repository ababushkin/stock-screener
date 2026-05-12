# ABA-47 — yfinance feasibility spike

**Date:** 2026-05-12
**yfinance version:** 1.3.0
**Tickers tested:** NVDA, META, RDDT
**Raw output:** `output_raw.txt`, `output_followup.txt`
**Probe scripts:** `feasibility.py`, `segments_sbc.py`

## Decision matrix

| # | Need | Used by | yfinance result | Decision |
|---|------|---------|-----------------|----------|
| 1 | SBC line, last 3 FYs | ABA-17, ABA-34 | **OK** — `cashflow.loc["Stock Based Compensation"]` present on all 3 tickers; annual 4y deep (oldest of 5 cols is NaN), quarterly 5q deep | **yfinance-primary.** EDGAR demoted to fallback for grant-level dilution detail only. |
| 2 | NTM EPS consensus | ABA-18, ABA-9 | **OK** — `earnings_estimate` returns avg/low/high/numberOfAnalysts/growth for 0q/+1q/0y/+1y on all 3 (RDDT has 21–26 analysts) | **yfinance-primary.** |
| 3 | NTM revenue consensus | ABA-25, ABA-9 | **OK** — `revenue_estimate` same shape, 25–58 analysts | **yfinance-primary.** |
| 4 | Consensus EPS history + surprise, last 8q | ABA-28 | **PATCHY** — `earnings_history` returns only **4 quarters** on every ticker | **Degrade scope.** SUE v1 uses 4-quarter window (still computable; std-dev weaker). Update ABA-28 acceptance criteria. Backfill to 8q deferred — can be reconstructed from `quarterly_income_stmt` + scraped consensus archives if signal proves useful. |
| 5 | Analyst EPS revision counts, 30/60/90d windows | ABA-29 | **PATCHY** — `eps_revisions` only exposes **7d / 30d** up & down counts. `upgrades_downgrades` carries a richer time series but is **stale on META** (latest entry 2024-09-30 vs current 2026-05-12) | **Degrade scope.** Revision momentum v1 uses 7d/30d directly from `eps_revisions`. 60/90d windows deferred. Update ABA-29 acceptance criteria. |
| 6 | Analyst price targets + buy/hold/sell counts | ABA-11 | **OK** — `analyst_price_targets` dict (current/high/low/mean/median) + `recommendations_summary` 4-month rolling strongBuy/buy/hold/sell/strongSell | **yfinance-primary.** |
| 7 | Revenue segments | ABA-12 | **MISSING** — no `get_revenue_segments` or equivalent; nothing in `info` keys | **Route to EDGAR.** ABA-12 reframed: tool reads 10-K Item 1 / segment footnote via EDGAR XBRL (or rendered HTML parse for textual segments). Defer until EDGAR MCP (M2 task) is built. |
| 8 | Piotroski 9 raw inputs (multi-year B/S + CF deltas) | ABA-24 | **OK** — `balance_sheet` 4-5y, `cashflow` 4-5y, `financials` 4-5y (oldest col often NaN on annual). Sufficient for the YoY-delta inputs Piotroski needs | **yfinance-primary.** |
| 9 | 5-year FCF | ABA-31, ABA-34 | **OK (4y)** — `cashflow.loc["Free Cash Flow"]` 4 usable years per ticker (5 cols, oldest NaN). 5th year reconstructable from operating-cf − capex if needed | **yfinance-primary.** Accept 4y horizon for DCF base year; document limitation. |
| 10 | Management guidance text | ABA-31 | **MISSING** — no `guidance`/`outlook` keys in `info`. `longBusinessSummary` is corporate description only | **Route to EDGAR + drop for v1.** Model DCF v1 substitutes NTM consensus (surface #3) for "guidance"; guidance-text extraction is a Later item — needs 8-K press releases or earnings transcripts (separate provider). |

## SBC specifics (the original concern that motivated the FMP→yfinance swap)

SBC values pulled directly:

| Ticker | FY-latest SBC | FY-1 SBC | FY-2 SBC | FY-3 SBC |
|--------|---------------|----------|----------|----------|
| NVDA   | 6.39B (Jan-26) | 4.74B  | 3.55B  | 2.71B |
| META   | 20.43B (Dec-25)| 16.69B | 14.03B | 11.99B |
| RDDT   | 343M (Dec-25) | 802M   | 48M    | 55M   |

RDDT's FY24 spike (IPO year) is the kind of artefact the EDGAR cross-check is for — but the value itself is present and signs are correct. SBC strip on yfinance is viable.

## META `upgrades_downgrades` staleness — caveat

META's `upgrades_downgrades` table stops at 2024-09-30 even though `eps_revisions` and `recommendations_summary` are current. This is a known yfinance behaviour (Yahoo's per-ticker feed quality is uneven). Implication: **do not depend on `upgrades_downgrades` as primary data for revision counts** — use `eps_revisions` (7d/30d) as the authoritative source. `upgrades_downgrades` is supplementary colour at best.

## Scope changes to flag in Linear

- **ABA-28** (SUE/PEAD): 8-quarter window → **4-quarter window** for v1; deferred backfill noted as follow-up.
- **ABA-29** (revision momentum): 30/60/90d windows → **7d/30d windows** for v1; 60/90d deferred.
- **ABA-12** (`get_revenue_segments`): yfinance → **EDGAR-only**. Blocked on EDGAR MCP build.
- **ABA-31** (Model DCF): guidance-text input → **NTM consensus substitute** for v1; transcript/guidance extraction is Later.

No new third-party source required. The original "do we need Finnhub or paid FMP" question is answered: **no, for v1.**
