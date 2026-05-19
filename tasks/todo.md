# Todo — ABA-115 `/stock-model` glidepath + scenario fan visuals

Tracking slices in `plan.md`. Tick boxes as work completes.

## Slice 1 — Model-tab shell
- [ ] Add new formatters to `ui/src/lib/formatters.js` (`formatCurrency`, `formatPercent`, `formatBillions`, `formatPerShare`), each returning `'—'` on null/NaN
- [ ] Create `ui/src/components/ModelReport.jsx` (header row, IV-range strip, range_vs_price badge, position-sizing line, pre-profit branch)
- [ ] Replace stub in `ui/src/App.jsx:64` to mount `ModelReport` when `tab === 'Model'`
- [ ] Add Model-tab section styles to `ui/src/styles.css`
- [ ] Verify: `npm run dev` → cycle through AMZN/META/NVDA/RDDT, no console errors; RDDT shows ESTABLISHED-only italic; ASML/GOOG keep Model tab disabled

**Gate to Slice 2:** all four ticker reports render the shell correctly.

## Slice 2 — SKILL emits `historical_fcf_margins[]`
- [ ] Add per-year clean+reported margin derivation in COMPUTE Step 1 of `skills/stock-model/SKILL.md` (~line 316)
- [ ] Add `historical_fcf_margins` to ESTABLISHED JSON schema block (~line 567, after `fcf_margin_ttm_reported`, before `fcf_cagr_3y`)
- [ ] Add same field to pre-profit JSON schema block
- [ ] Add audit line to printed OUTPUT block (~line 512 area)
- [ ] Document gap-handling rule (omit years missing `revenue` or `stock_based_compensation`)
- [ ] Add `### v1.11 — ABA-115` changelog entry (line 1101+)
- [ ] Smoke-run `/stock-signal META` → `/stock-model META`; verify audit row reconciles cell-for-cell with JSON `historical_fcf_margins[]`

**Gate to Slice 3:** audit row matches JSON values exactly.

## Slice 3 — Re-run covered tickers
- [ ] `/stock-signal META` → `/stock-model META` → confirm `historical_fcf_margins` present and `intrinsic_value_range` within ±1% of prior file
- [ ] Same for AMZN (note: `gate_bypass: "coverage"`)
- [ ] Same for NVDA
- [ ] Re-run RDDT — confirm `method` still starts with `"pre-profit"` and field is present (or cleanly absent)
- [ ] UI picker picks up new dated reports; shell still renders

**Gate to Slices 4–6:** four fresh same-day reports in `reports/`.

## Slice 4 — Glidepath chart
- [ ] Create `ui/src/components/charts/CagrGlidepath.jsx` (hand-rolled SVG)
- [ ] Trailing-3y point + Y1 implicit + Y2–Y5 flat per scenario
- [ ] Cap annotation reads from `growth_rate.cap_applied / applied_base_cagr / cap_source`
- [ ] Pre-profit guard (no render when `method` starts with `"pre-profit"`)
- [ ] Mount from `ModelReport.jsx`
- [ ] Verify: META cap callout fires; AMZN base bends from 145.7% → 18%; NVDA matches pattern; bear < base < bull at every Y2+ point

## Slice 5 — FCF margin trajectory chart
- [ ] Create `ui/src/components/charts/FcfMarginTrajectory.jsx`
- [ ] Read `historical_fcf_margins[]` + TTM points (clean + reported)
- [ ] Flat-line extension Y1–Y5 at `fcf_margin_ttm`
- [ ] Shade gap between clean and reported (SBC drag)
- [ ] Fallback note when `historical_fcf_margins` absent
- [ ] Handle negative margins (AMZN clean TTM = −1.6%) without breaking Y-axis
- [ ] Pre-profit guard
- [ ] Mount from `ModelReport.jsx`
- [ ] Verify: AMZN dip visible; META gap narrow; NVDA both lines high

## Slice 6 — Scenario fan chart
- [ ] Create `ui/src/components/charts/ScenarioFan.jsx`
- [ ] Per-scenario Y1→Y5 FCF series via `y1_fcf × (1 + y2_5_cagr)^(n-1)`
- [ ] Convert all to FCF/share via `shares_diluted` (raw count — sanity-check magnitude)
- [ ] Terminal IV diamond marker at Y5 per scenario
- [ ] Current-price horizontal reference line
- [ ] Pre-profit guard
- [ ] Mount from `ModelReport.jsx`
- [ ] Verify: META current $614 sits between bear $444 + base $1155 markers (matches `WITHIN BEAR-BASE`); AMZN $264 above base IV $176 marker (matches `WITHIN BASE-BULL`)

## Slice 7 — Captions, styling, docs
- [ ] One-sentence thesis caption under each of the three charts (refine drafts from plan)
- [ ] Harmonise chart styling with existing palette (`#777` / `#fafafa` / `#e5e5e5`) in `ui/src/styles.css`
- [ ] Add Model-tab v1 note to `DESIGN.md` UI Layer section
- [ ] Draft PR description: subsumes ABA-42 v1; ABA-43 explicitly deferred; link both
- [ ] Manual visual review at 960px on all six tickers (META/AMZN/NVDA/RDDT/ASML/GOOG)
- [ ] Capture screenshots of all three charts

## Linear hygiene
- [ ] Move ABA-115 → In Progress on Slice 1 start
- [ ] Move ABA-115 → Done after commits pushed
- [ ] Comment on ABA-42 with PR link + scope-narrowing note
- [ ] Confirm ABA-115 sits in current cycle (Cycle 1, 17–24 May)

## Pre-merge
- [ ] All slice gates passed
- [ ] `npm run build` succeeds from `ui/`
- [ ] Hot-reload latency in `npm run dev` still <1s
- [ ] Final end-to-end verification per `plan.md`
