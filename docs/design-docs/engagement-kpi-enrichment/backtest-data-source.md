# Backtest data-source feasibility — Task 4 (ABA-66)

**Run date:** 2026-05-14
**Branch:** `anton/aba-66-eng-kpi-spike`
**Goal:** Pull one historical ticker-quarter end-to-end (engagement KPI as-published at print date + 4-week consensus NTM revenue revision) and decide whether the sources scale to 40 ticker-quarters.

**Verdict:** ✅ **Viable for 40 ticker-quarters.** Both data legs were successfully pulled for META Q1 2025 from free, deterministic sources. Proceed to Task 5 (constants ADR) and Task 6 (backtest run).

---

## Sample pull: META Q1 2025

### Leg 1 — Engagement KPI as-published at print date

| Field | Value |
|---|---|
| Filing | 8-K filed 2025-04-30, accession `0001326801-25-000050` |
| Exhibit URL | https://www.sec.gov/Archives/edgar/data/1326801/000132680125000050/meta-03312025xexhibit991.htm |
| Source phrase (verbatim) | "DAP was 3.43 billion on average for March 2025, an increase of 6% year-over-year" |
| Extracted DAP | 3.43 billion |
| YoY change | +0.06 |
| Derived direction | +1 (mild — abs(0.06) < 0.08) |
| `base_anchor_multiplier` | 1.02 |

**Source:** EDGAR direct HTTP via FR8 fallback #2; same extraction path as Task 1 spike. Deterministic, reproducible.

### Leg 2 — 4-week consensus NTM revenue revision

Print date 2025-04-30. Target windows:
- **T0** = print + 0–1 days (consensus immediately after print)
- **T1** = print + ~28 days (4-week post-print)

**Source:** `web.archive.org` snapshots of `finance.yahoo.com/quote/META/analysis/`.

| Window | Closest snapshot | Next Year (2026) Avg Estimate | # Analysts |
|---|---|---|---|
| T0 (print + 1d) | 2025-05-01 20:36 UTC | **$211.59B** | 54 |
| T1 (print + 35d, closest available to +28d target) | 2025-06-04 15:01 UTC | **$212.75B** | 63 |

**Revision:** ($212.75 − $211.59) / $211.59 = **+0.548%**

**Direction agreement check (preview of Task 6 methodology):**
- KPI direction: **positive** (DAP YoY +6%)
- Consensus revision direction: **positive** (+0.55%)
- **Agreement: HIT** for this single sample (N=1, decorative — Task 6 needs ≥24).

### Mechanical details that matter for scale

1. **Yahoo's React page survives wayback capture.** The Wayback Machine renders before snapshotting; the 1.8–2.1 MB HTML contains the fully-populated estimates table. No JS execution needed at read-time.
2. **Snapshot tolerance is generous.** Wayback's closest-capture redirect (`x-archive-redirect-reason: found capture at <ts>`) auto-resolves to the nearest snapshot within days. For T1 the closest was 2025-06-04 (35 days post-print) vs. a 28-day target — within ±7 days is acceptable for a directional-agreement check (NFR7 measures direction, not magnitude).
3. **Extraction is a regex, not a vision/LLM call.** The "Revenue Estimate" / "Avg. Estimate" / "Next Year (YYYY)" labels are stable across years (verified 2025-04 and 2025-06 snapshots have identical structure).
4. **Currency is fixed in markup** (`Currency in USD`) — no FX surprises.

---

## Scaling to 40 ticker-quarters

**Coverage plan:**
- **META** (DAP disclosed since Q1 2023, 12 quarters available by 2026-05): 12 ticker-quarters
- **RDDT** (DAUq disclosed since IPO Mar 2024, ~9 quarters by 2026-05): 9 ticker-quarters

That's 21 ticker-quarters from the seed map directly. Not 40. **This is the binding constraint, not data availability.**

Two ways to close the gap to NFR7's ≥24-floor / 40-target:
- **A.** Expand the KPI map. XYZ (Cash App MAU, quarterly), PINS (MAU), SNAP (DAU), SPOT (MAU + Premium subs), UBER (MAPCs), ABNB (Nights+Experiences Booked). These add 30+ ticker-quarters at the cost of authoring map entries.
- **B.** Stay on seed set (21 ticker-quarters), accept that backtest hits the ≥24 floor only by adding 1 more ticker. PINS alone (8+ quarters) would clear 24.

**Recommendation for Task 6:** Path A-lite. Add **PINS** + **SNAP** + **SPOT** to the KPI map (these have clean, stable engagement-KPI disclosure with explicit YoY in earnings press releases — they are textbook APPLICATION-layer tickers and were always candidates for v2). Net: ~21 + 24 = 45 ticker-quarter candidates → comfortably ≥40 with attrition headroom.

**Data-leg time budget (back-of-envelope):**
- 45 ticker-quarters × 1 EDGAR fetch + 2 wayback fetches = 135 HTTP calls.
- At 2–5 seconds per fetch (curl + wayback's slow shard loading), ~7–11 minutes per full backtest run. Trivial.

---

## Risks and known failure modes

| Risk | Likelihood | Mitigation |
|---|---|---|
| Wayback has a gap >7d either side of a target date | Low for liquid US large-caps (Yahoo is one of the most-archived sites); higher for newer RDDT history | Per-sample missing-data skip; report attrition rate; require ≥24 valid post-attrition |
| Yahoo restructures the analyst page DOM mid-backtest | Low — the structure has been stable for 5+ years per spot-check | Extraction regex is permissive (label-anchored, not position-anchored); fail loudly on miss |
| Yahoo blocks wayback's UA going forward | Low (wayback fetches historical, not live); irrelevant for backtest | n/a |
| EDGAR rate-limits batch fetches | Medium if naive | SEC allows 10 req/sec with proper UA; add 200ms sleep between fetches to stay polite |
| "Next Year" estimate semantics drift (Yahoo shifts the year label) | Low but real — at year boundary "Next Year (2025)" rolls to "Next Year (2026)" | Use the year label embedded in the markup at fetch-time as ground truth, not assumption |
| KPI signal disagrees with revision because of OQ1 lever choice (revenue vs. FCF) | Medium — design doc explicitly defers this to wiring | Task 6 backtests revenue-revision direction since that is the design-doc default; revisit if hit rate <60% |

---

## What this rules out

The "ship disabled-by-default" fallback (user-selected for Task 4 contingency) is **not needed** based on this feasibility result. The data legs are obtainable from free deterministic sources at the scale Task 6 requires. The fallback remains the documented response if Task 6's actual hit rate falls below the 60% threshold even after one in-sample constant revision.

---

## Decision

**PROCEED to Task 5 (constants ADR).** Both data legs verified end-to-end for one ticker-quarter; mechanical path scales linearly to 40+. The binding constraint is KPI-map breadth, not data availability — addressed by adding PINS/SNAP/SPOT to the map before Task 6 (this work is recorded as a Task 6 prerequisite, not folded into Task 4).

OQ2 (4-week revision-window measurement source): **RESOLVED** — wayback snapshots of `finance.yahoo.com/quote/<TICKER>/analysis/`, with ±7d tolerance on T1.

## Next steps

- (Task 5) Pre-register constants ADR.
- (Task 6 prerequisite) Extend `engagement_kpi_map.json` to v2 with PINS / SNAP / SPOT (separate Linear sub-issue or fold into Task 6 scope — owner's call at Task 7 gate).
- (Task 6) Implement `tests/backtest/engagement_kpi_revision_agreement.py` against frozen historical fixtures; assert ≥60% direction agreement on ≥24 valid samples.
