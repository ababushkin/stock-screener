# Plan — ABA-115 `/stock-model` glidepath + scenario fan visuals

**Linear:** ABA-115
**Cycle:** Cycle 1 (17–24 May 2026) — differentiator/legibility theme
**Scope:** add three SVG visuals + v1 of the Model tab to the UI; extend Model SKILL to emit `historical_fcf_margins[]`; re-run covered tickers.
**Plan source:** approved 2026-05-19; see `/Users/anton/.claude/plans/spicy-beaming-stonebraker.md`.

## Context

`/stock-model` now produces methodologically honest but stark-looking scenario outputs after ABA-110 (SBC strip) and ABA-111 (growth-rate cap) landed. Example: META 2026-05-17 — bear $444, base $1155, bull $2440 vs price $614. Reading the base case in isolation is misleading without the trajectory context — the cap mechanically applies a consensus ceiling in Y2 that looks like a cliff but is a smoothing artefact. The reader has to do the unpacking in their head.

The fix is three visuals on a new Model tab, sourced entirely from `stages.model.*`:

1. **CAGR glidepath** — trailing-3y CAGR → Y1→Y5 projected CAGR per scenario, annotated where the cap fires.
2. **FCF margin trajectory** — 3y historical clean vs reported margin + flat-line extension through Y1→Y5, surfacing the "base assumes no operating leverage" assumption.
3. **Scenario fan** — Y1→Y5 FCF/share for bear/base/bull, with per-share terminal IV markers and a current-price reference line.

The Model tab does not yet exist in the UI; this ticket also lands v1 of it (subsumes ABA-42).

## Decisions taken before planning

1. **Schema-extend the Model SKILL** to emit `stages.model.historical_fcf_margins[]` (3y per-year `{year, fcf_margin_clean, fcf_margin_reported}`). UI gracefully falls back to TTM-only when the field is absent.
2. **Scenario fan uses a single per-share axis** — projected FCF is divided by `shares_diluted`; terminal IV markers and the current-price line live on the same axis.
3. **Hand-rolled React + SVG**, no chart dependency.
4. **Model tab includes basic summary** (IV-range, range_vs_price badge, position-sizing line) alongside the three visuals — subsumes ABA-42 v1; flag in PR.
5. **Pre-profit (EMERGING) scoped OUT for v1.** When `stages.model.method` starts with `"pre-profit"`, the tab shows summary only plus a one-line note that visuals are ESTABLISHED-only.

## Dependency graph

```
Slice 1 (Model-tab shell)        ─► land first; no SKILL changes
        │
        └─► mount point for D/E/F

Slice 2 (SKILL: historical_fcf_margins)  ──► Slice 3 (re-run covered tickers)
                                                        │
                                                        └─► Slices 4 / 5 / 6 (charts, independently parallel)
                                                                          │
                                                                          └─► Slice 7 (captions, styles, docs)
```

- Slice 1 is independent of the SKILL change — the summary fields it consumes already exist in current reports.
- Slice 2 must land before Slice 3 (re-runs need new fields).
- Slices 4–6 are mutually independent once Slice 3 lands; can ship serially or in parallel.
- Slice 7 closes out.

## Vertical slicing rationale

Each slice ends in a runnable, demonstrable artefact. We resist horizontal layering — no "all components first, then all data". Every slice exercises a real call path from data → render or from input → JSON. Gates between slices are pass-fail to keep the next slice from inheriting a broken assumption.

## Slices

### Slice 1 — Model-tab shell (no SKILL changes)
**Files:** `ui/src/App.jsx`, new `ui/src/components/ModelReport.jsx`, `ui/src/lib/formatters.js`, `ui/src/styles.css`.

**Reuse:** `verdictClass()` from `formatters.js` for the `range_vs_price` badge; existing `.card`, `.badge`, `.tab` styles; `ScreenReport.jsx` as the shape pattern.

**Acceptance criteria:**
- `App.jsx:64` stub replaced for `tab === 'Model'`.
- ESTABLISHED branch renders: header row (method, profit_stage, base WACC, NTM revenue, clean FCF margin TTM); IV-range strip showing bear/base/bull `intrinsic_value_per_share` and `current_price`; `range_vs_price` badge using existing verdict palette; position-sizing band + one-line `rationale`.
- Pre-profit branch renders summary fields and an italic line: *"Visual breakdown is ESTABLISHED-only for v1."*
- New formatters added: `formatCurrency`, `formatPercent`, `formatBillions`, `formatPerShare`. Each returns `'—'` for `null`/`undefined`/`NaN`.
- Selecting a report without `stages.model` (e.g. ASML_20260517) keeps the Model tab disabled, same as today.

**Verification:** `npm run dev` from `ui/`. Cycle picker through AMZN_20260518, META_20260517, NVDA_20260514, RDDT_20260513. All four render without console errors. RDDT shows the pre-profit note. ASML/GOOG show the Model tab disabled.

**Gate to Slice 2:** all four ticker reports render the shell. If anything breaks, fix before touching the SKILL.

---

### Slice 2 — SKILL schema change (`historical_fcf_margins[]`)
**Files:** `skills/stock-model/SKILL.md` only.

**Insertion points (confirmed by reading SKILL):**
- COMPUTE Step 1 (~line 316): after `fcf_cagr_3y` derivation. For each `y ∈ [0..3]` with revenue and SBC available, compute `fcf_margin_clean = (years[y].free_cash_flow − years[y].stock_based_compensation) / years[y].revenue` and `fcf_margin_reported = years[y].free_cash_flow / years[y].revenue`. Persist as `historical_fcf_margins` (newest-first, matching `years[]` order).
- JSON output block (~line 567): add `"historical_fcf_margins": [{"year": "YYYY-MM-DD", "fcf_margin_clean": <number>, "fcf_margin_reported": <number>}, ...]` immediately after `fcf_margin_ttm_reported`, before `fcf_cagr_3y`.
- Printed OUTPUT block (~line 512 area): add an audit row `Historical clean FCF margin: y-3 X.X% / y-2 X.X% / y-1 X.X% / TTM X.X%` so the JSON value is human-verifiable against the same run.
- Changelog (line 1101+ — convention is `### v1.N — ABA-XXX`): add `### v1.11 — ABA-115 (historical FCF margin series for Model-tab visuals)` with 3–5 acceptance bullets.
- Pre-profit path: emit the same `historical_fcf_margins[]` field when the 3y series is computable (cost is ~5 lines, same audit value); UI does not render it for now.
- Handle gaps: if any year is missing `revenue` or `stock_based_compensation`, omit that year's entry rather than emitting `null` fields — keep the array dense.

**Acceptance criteria:**
- New field documented in both ESTABLISHED and pre-profit JSON OUTPUT schema blocks.
- Printed audit line reconciles cell-for-cell with the JSON array.
- Changelog entry committed in the same diff.

**Verification:** Smoke-run one ESTABLISHED ticker (`/stock-signal META` → `/stock-model META`). Open the printed OUTPUT; verify the audit row's four values match the resulting `reports/META_YYYYMMDD.json` `historical_fcf_margins[]` array values rounded to the same precision.

**Gate to Slice 3:** if audit-row and JSON values disagree, **stop**. The COMPUTE or OUTPUT step is wrong; debug before mass re-runs.

---

### Slice 3 — Re-run covered tickers
**Tickers in scope (latest report has `stages.model`):** META, AMZN, NVDA. RDDT (pre-profit) too, so its report stays fresh — visuals not rendered but audit field present. XYZ skipped (test fixture).

**Tickers explicitly out of scope:** ASML, GOOG, NFLX, ADYEN.AS — latest Signal returned `model_ready=NO`; nothing to re-run.

**Note on AMZN:** the AMZN report uses `"gate_bypass": "coverage"`. The same flow continues to apply.

**Acceptance criteria:**
- Fresh same-day reports for META, AMZN, NVDA, RDDT all contain `stages.model.historical_fcf_margins`.
- `intrinsic_value_range` per ticker is within ±1% of the prior file (no unintended drift from the schema change).
- RDDT's `method` still starts with `"pre-profit"`.

**Verification:** for each of META/AMZN/NVDA, run `/stock-signal TICKER` → `/stock-model TICKER`; diff new vs old `intrinsic_value_range` and confirm no material change. UI picker shows the new dated reports.

**Gate to Slices 4–6:** all four reports present in `reports/`, dated same-day, shell still renders.

---

### Slice 4 — Glidepath chart
**Files:** new `ui/src/components/charts/CagrGlidepath.jsx`; mounted from `ModelReport.jsx`. CSS additions in `styles.css`.

**Data flow:**
- Trailing-3y CAGR from `stages.model.growth_rate.trailing_3y_cagr` (single point on the left).
- Y1 implicit CAGR per scenario: `scenarios.{s}.y1_fcf / fcf_ttm − 1` (back-derived client-side).
- Y2–Y5 CAGR per scenario: `scenarios.{s}.y2_5_cagr` (flat through Y2–Y5).
- Cap annotation when `growth_rate.cap_applied === true`, surfaces `applied_base_cagr` and `cap_source` (e.g. *"capped from 145.7% by fallback_ceiling (18%)"*).

**Acceptance criteria:**
- Three lines (bear/base/bull) colour-coded; legend at top.
- Y2-onwards bear < base < bull at every year (monotone-ordered).
- Cap footnote rendered for any base run where `cap_applied`.
- No render for `method` starting with `"pre-profit"`.

**Verification:** Model tab on META — base line bends at Y2 with the cap callout; on AMZN — base line bends harder (1.46 → 0.18); on NVDA — confirms similar pattern.

---

### Slice 5 — FCF margin trajectory chart
**Files:** new `ui/src/components/charts/FcfMarginTrajectory.jsx`.

**Data flow:**
- Historical points from `stages.model.historical_fcf_margins[]` (3–4 years), plotted as two thin lines (clean vs reported).
- TTM point from `fcf_margin_ttm` and `fcf_margin_ttm_reported`.
- Y1→Y5 extension: flat at `fcf_margin_ttm` (or playbook's `terminal_margin` if surfaced — out of v1 unless it lands in JSON; default flat).
- Gap between clean and reported lines shaded to visualise SBC drag.

**Acceptance criteria:**
- Fallback when `historical_fcf_margins` absent: render TTM-only with a small note "3y history unavailable — re-run /stock-model with v1.11+ for trajectory".
- Negative margins handled (AMZN clean TTM = −1.6%) — Y-axis spans signed range without breaking.
- No render for pre-profit.

**Verification:** Model tab on AMZN — clean line dips below historical due to capex AI cycle; META — clean and reported lines closer together (smaller SBC drag); NVDA — both lines high, narrow gap.

---

### Slice 6 — Scenario fan chart (per-share single axis)
**Files:** new `ui/src/components/charts/ScenarioFan.jsx`.

**Data flow per scenario:**
- Year FCF series: `y1_fcf` then iterated `× (1 + y2_5_cagr)` for Y2–Y5.
- Divide each by `stages.model.shares_diluted` → FCF/share/year.
- Terminal IV marker = `scenarios.{s}.intrinsic_value_per_share` at Y5 (single ◆ marker per scenario).
- Horizontal reference line at `stages.model.current_price`.

**Acceptance criteria:**
- Three bands (bear/base/bull) fanning out across Y1–Y5; per-share IV diamond markers at Y5; current-price line spans full chart.
- Sanity check: terminal markers ordered bear < base < bull; current_price line position visually matches `range_vs_price` text on the tab.
- No render for pre-profit.

**Verification:** Model tab on META — current $614 line crosses between bear ($444) and base ($1155) markers, matching `WITHIN BEAR-BASE` badge. AMZN — current $264 line above base IV $176 marker, matching `WITHIN BASE-BULL`.

---

### Slice 7 — Captions, styling, docs
**Files:** `ui/src/styles.css`; `ui/src/components/charts/*.jsx` for caption text; `DESIGN.md` for the UI Model-tab note; PR description.

**Acceptance criteria:**
- One-sentence caption under each chart that explains the *thesis implication*, not the chart mechanics. Draft copy (refine during build):
  - Glidepath: *"How fast the model thinks FCF compounds — and where the consensus/fallback ceiling clamps it."*
  - Margin trajectory: *"Base case assumes today's clean FCF margin holds flat — operating-leverage upside lives in the bull case."*
  - Scenario fan: *"Today's price is the market's read; the markers are ours. The fan is where the assumptions live."*
- Styles harmonise with existing palette (`#777` axis labels, `#fafafa` panel bg, `#e5e5e5` borders).
- `DESIGN.md` UI Layer section gets a one-line note that Model tab v1 shipped under ABA-115.
- PR description flags: subsumes ABA-42 v1; sensitivity-table interactive grid (ABA-43) explicitly deferred.

**Verification:** Manual visual review at 960px viewport on all four tickers + ASML/GOOG (Model tab disabled). Screenshot all three charts.

## Checkpoints

- **Checkpoint A (after Slice 1):** Model tab shell renders on all four reports. Gate to Slice 2.
- **Checkpoint B (after Slice 2):** SKILL prints an audit row whose values reconcile with the new JSON field on a single smoke ticker. Gate to Slice 3.
- **Checkpoint C (after Slice 3):** four re-run reports present and `intrinsic_value_range` unchanged within ±1%. Gate to Slices 4–6.
- **Checkpoint D (after Slices 4–6):** all three charts render correctly on META + AMZN + NVDA; pre-profit (RDDT) shows summary only. Gate to Slice 7.
- **Pre-merge final:** Linear hygiene + DESIGN.md note + ABA-42 cross-link.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Schema change drift in Slice 3 | Diff `intrinsic_value_range` per ticker against the prior file; ±1% tolerance gate. |
| `shares_diluted` units in fan chart | AMZN value is raw 10.8B — sanity-check Y1 FCF/share against base IV order of magnitude before declaring Slice 6 done. |
| AMZN normalisation edge in margin chart | Plot the unmodified clean TTM (`fcf_margin_ttm = −1.64%`), not the normalised `fcf_margin_normalized = 7.74%`. The chart's purpose is to surface the gap that justified normalisation. |
| Cap-annotation phrasing | One canonical sentence template across all `cap_source` values; pin in Slice 4 and reuse. |
| Vite bundle bloat | `import.meta.glob` is already eager. Watch hot-reload latency stays <1s as charts land. |
| Old reports missing `historical_fcf_margins` | Slice 5 must render TTM-only fallback without crashing. |

## Critical files

- `skills/stock-model/SKILL.md` — Slice 2 only (~lines 316, 540, 567, 1101).
- `ui/src/App.jsx:64` — Slice 1 stub replacement.
- `ui/src/components/ModelReport.jsx` — Slice 1 new file.
- `ui/src/components/charts/CagrGlidepath.jsx` — Slice 4 new file.
- `ui/src/components/charts/FcfMarginTrajectory.jsx` — Slice 5 new file.
- `ui/src/components/charts/ScenarioFan.jsx` — Slice 6 new file.
- `ui/src/lib/formatters.js` — Slice 1 additions.
- `ui/src/styles.css` — Slice 1 + Slice 7 additions.
- `DESIGN.md` — Slice 7 one-line note.

## End-to-end verification

1. From `ui/`, `npm run dev` → localhost:5173.
2. Pick latest META → Model tab → confirm IV-range strip, range_vs_price badge, position-sizing line, and three charts render.
3. Pick AMZN → negative clean margin handled cleanly in trajectory chart; fan chart per-share axis sane.
4. Pick NVDA → glidepath cap callout fires.
5. Pick RDDT → summary + italic "ESTABLISHED-only" note; no charts.
6. Pick ASML → Model tab disabled (unchanged from today).
7. Manual diff of any one re-run report's `intrinsic_value_range` against its previous-day file → within ±1%.

## Linear hygiene

- Move ABA-115 → In Progress when Slice 1 starts.
- Move ABA-115 → Done after Slice 7 lands, commits are pushed.
- Comment on ABA-42 linking the PR; note v1 of the Model tab is live; ABA-42 narrows to "interactive controls / sensitivity grid".
- ABA-43 (sensitivity table) is explicitly not in this PR.

## Out of scope (explicit non-goals)

- Glidepath shaping (year-by-year CAGR taper) — separate ticket if worth doing.
- Margin-expansion lever in base case — separate methodology ticket.
- Sensitivity heatmap (WACC × g) — ABA-43.
- Pre-profit (EMERGING) visuals — separate ticket after at least one more pre-profit ticker is added to COVERAGE.
- Playwright e2e — ABA-64, Later.
