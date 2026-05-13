---
linear: ABA-66
design_doc: docs/design-docs/engagement-kpi-enrichment/design-doc.md
last_updated: 2026-05-14
---

# Tasks: engagement-kpi-enrichment

Spike-then-build, 3-week appetite. Tasks 1–6 are Weeks 1+2 (the spike). Task 7 is the explicit go/no-go gate. Tasks 8–14 only run on PROCEED.

## Phase 1 — Walking skeleton + Week 1 feasibility

### Task 1 — Walking skeleton: three-surface extraction
**Description:** End-to-end GATHER step (EDGAR fetch → Claude extraction → modifier compute → MIP confirm → JSON write) running on META (PDF), RDDT (HTML), NFLX (letter) for their most recent quarter.
**Done when:** A spike-branch invocation of `/stock:model META`, `... RDDT`, `... NFLX` each produces a populated `stages.model.engagement_modifier` block with `kpi_name`, `kpi_value`, `yoy_change`, `direction`, `source_url`, `source_accession`, and the value matches a hand-verified expected within ±2% on each of the three tickers (NFR2 ≥80% met on the seed surface set).
**Dependencies:** none

### Task 2 — KPI map v1 authoring (seed set)
**Description:** Author `skills/_shared/engagement_kpi_map.json` (schema_version=1) + `CHANGELOG.md` for META, NFLX, RDDT, GOOGL, XYZ; resolve OQ3 (NFLX substitute) and OQ6 (GOOGL fallback) by drop-or-map.
**Done when:** JSON file validates against a one-shot schema test; every seed ticker has `primary_kpi`, `secondary_kpi`, `comparison_basis`, `signal_type`, source-link evidence in the changelog; tickers without a defensible mapping are explicitly dropped with a one-line reason in the changelog.
**Dependencies:** none (parallel to Task 1)

### Task 3 — Reproducibility check
**Description:** Repeat-invocation harness that runs the Task 1 GATHER step 5× per seed ticker on the same day and diffs the output.
**Done when:** `tests/spike/engagement_kpi_reproducibility.py` asserts identical `kpi_value`, `yoy_change`, `direction`, `magnitude`, `base_anchor_multiplier` across all 5 trials per ticker (modulo source_accession which is fixed by EDGAR). Test green on all three surfaces.
**Dependencies:** Task 1

### Task 4 — Backtest data-source feasibility
**Description:** Pull one historical ticker-quarter end-to-end — engagement KPI as-published at print date + consensus NTM revenue revision over the 4-week post-print window — and confirm the data source(s) scale to 40 ticker-quarters.
**Done when:** A written feasibility note at `docs/design-docs/engagement-kpi-enrichment/backtest-data-source.md` names the source per data leg, documents the one end-to-end pull, and concludes either (a) source viable for 40 ticker-quarters, or (b) source unviable → modifier ships disabled-by-default per spike fallback in design doc.
**Dependencies:** none (parallel to Task 1)

## Phase 2 — Week 2: ADR pre-registration + backtest

### Task 5 — Pre-register constants ADR
**Description:** Author and merge `docs/adrs/engagement-modifier-constants.md` with deadband (±2% YoY), magnitude threshold (8% YoY), ±4% Y1-anchor input cap, ≤5% base-IV output cap, base-only application, and the 60% backtest-pass threshold with coin-flip + ≥10pp justification — **before** the backtest in Task 6 is executed.
**Done when:** ADR merged to main with status `accepted`; commit precedes any commit that touches the backtest fixture data; ADR cross-linked from the design doc.
**Dependencies:** Tasks 1, 4 (skeleton outputs inform OQ1, OQ5; feasibility outcome informs threshold framing)

### Task 6 — Backtest revision-direction agreement
**Description:** Run `tests/backtest/engagement_kpi_revision_agreement.py` against frozen historical fixtures on the 40-candidate / 32-minimum-valid / 24-floor sample using the pre-registered Task 5 constants; capture hit rate.
**Done when:** Test runs to completion with ≥24 valid ticker-quarter samples, prints rolling agreement rate, and asserts ≥60% (NFR7). On fail, the result is documented and exactly one in-sample constant revision is attempted (recorded as ADR supersession) — a second failure triggers disabled-by-default scoping in Task 7.
**Dependencies:** Tasks 2, 4, 5

## Phase 3 — Spike → Build gate

### Task 7 — Spike decision memo (PROCEED / KILL / RESHAPE)
**Description:** Write the go/no-go memo summarising spike evidence and recommended path.
**Done when:** `docs/design-docs/engagement-kpi-enrichment/spike-decision.md` exists with: precision/repro/backtest results, OQ1+OQ2+OQ5 resolutions, and one of three explicit verdicts (PROCEED with Task-8-onward scope; RESHAPE with named scope cuts; KILL with ABA-66 closure note). Memo linked from ABA-66.
**Dependencies:** Tasks 1, 2, 3, 4, 5, 6

## Phase 4 — Week 3 implementation (only if Task 7 == PROCEED)

### Task 8 — KPI-map versioning ADR
**Description:** Author and merge `docs/adrs/engagement-kpi-map-versioning.md` (schema versioning, changelog format, drift-detection check).
**Done when:** ADR merged with status `accepted`; references the JSON file path and weekly drift CI from Task 13.
**Dependencies:** Task 7 (PROCEED)

### Task 9 — Wire GATHER step into `/stock:model` (both paths)
**Description:** Land the GATHER step from the spike into the real skill code, conditional on `ai_layer ∈ {APPLICATION, INCUMBENT}` and ticker present in the KPI map, in both ESTABLISHED and EMERGING paths. Includes `--no-engagement-modifier` CLI flag.
**Done when:** A live `/stock:model META` (ai_layer=INCUMBENT) emits the `engagement_modifier` block with `status: "applied"` and user_confirmed flow; `/stock:model META --no-engagement-modifier` emits no block; `/stock:model <emerging-pre-profit-ticker>` skips the step (FR6); a ticker not in the map emits `status: "no_kpi_mapping"` (FR7); missing `ai_layer` emits `status: "unavailable", status_reason: "missing_ai_layer"` (upstream dep).
**Dependencies:** Task 7

### Task 10 — JSON contract schema test
**Description:** Schema test enforcing NFR3 — applied entries have all eight applied-fields populated; non-applied entries have non-null `status_reason` from the documented enum.
**Done when:** `tests/schema/engagement_modifier_contract.py` green; covers all four `status` values and all five `status_reason` values; runs in CI.
**Dependencies:** Task 9

### Task 11 — Cap + confidence unit tests (NFR4, NFR5)
**Description:** Unit tests asserting (a) `abs(iv_with / iv_without − 1) ≤ 0.05` across seed set, and (b) any applied modifier caps `meta.confidence` at MEDIUM.
**Done when:** Both tests green in CI; documented cases include the clamp path (input multiplier at ±4% but base-IV impact pre-clamp would exceed 5%, producing `clamped_from`).
**Dependencies:** Task 9

### Task 12 — Golden-fixture extraction test (NFR2)
**Description:** Promote spike fixtures to permanent goldens at `tests/golden/engagement_kpi_extraction.py` running against frozen press-release fixtures on the seed set.
**Done when:** Test asserts ≥80% precision (numerical ±2%, direction exact-match) across the committed fixtures; runs in CI.
**Dependencies:** Tasks 1, 9

### Task 13 — Weekly drift-CI workflow
**Description:** Author the GH Actions scheduled workflow that dry-runs the modifier against each seed ticker weekly; fails if `status != "applied"` for any ticker on >2 consecutive runs.
**Done when:** Workflow file committed; one manual `workflow_dispatch` run succeeds end-to-end and a second deliberately-stale run (test fixture forcing `status != "applied"`) fails correctly. GH Actions infra confirmed available (no separate setup sub-task needed) or setup completed.
**Dependencies:** Task 9

### Task 14 — UI sub-issue: render `engagement_modifier` block
**Description:** File a Linear sub-issue under ABA-66 and implement the report-UI render for the new block, covering all four `status` values.
**Done when:** Sub-issue filed and closed; UI renders applied / unavailable / no_kpi_mapping / user_skipped distinctly; missing-field defaults to `unavailable`; a live report (Task 9 output) round-trips through the UI without breakage.
**Dependencies:** Task 9 (JSON contract must be live)

## Open questions

OQ1, OQ2, OQ5 are scheduled to resolve within Tasks 1, 6, and 1 respectively (per design doc Sequencing). OQ3 + OQ6 resolve in Task 2. OQ4 resolved in the design doc. OQ7 is filed as ABA-105 (out of scope).

No external/cross-team dependencies. EDGAR MCP server availability (per FR8 resolution order) is a soft dependency — direct EDGAR HTTP fallback is in scope for Task 1 if the MCP server is not built when this lands.
