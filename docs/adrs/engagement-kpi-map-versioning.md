---
id: ADR-engagement-kpi-map-versioning
status: accepted
date: 2026-05-14
authors: Anton Babushkin
linear: ABA-66
supersedes: none
---

# ADR — Engagement KPI map versioning + drift detection

## Status

**Accepted.** Governs `skills/_shared/engagement_kpi_map.json`, the authoritative ticker→KPI mapping consumed by `/stock-model`'s engagement modifier. Codifies the schema-version bump rule, the changelog format, and the weekly drift-CI gate.

## Context

The KPI map is a small JSON file with outsized blast radius: every `/stock-model` run on an INCUMBENT or APPLICATION ticker reads it to locate the source phrase used by the EDGAR Ex 99.1 regex. A silent edit can change the KPI a ticker is measured against, which changes the modifier's direction and the audit trail without any code change visible in a PR diff to the model skill.

Two failure modes need to be made structurally hard:

1. **Schema drift without an audit trail.** A field renamed or a ticker added in passing leaves no record of who changed what, when, or why. A future post-launch review or backtest replay loses reproducibility.
2. **Source-page drift without detection.** Yahoo / EDGAR / press-release wording shifts (e.g. META rebranded DAU→DAP in 2023). If the `source_phrase` in the map no longer matches the live filing, the modifier silently degrades to `status: "unavailable"` on the ticker, and the user notices only when a real model run misfires.

This ADR addresses both: (1) by mandating a schema version + changelog discipline that requires an ADR for every bump; (2) by mandating a weekly CI dry-run (built in Task 13) that fails when any seed ticker no longer produces `status: "applied"`.

The map already carries `schema_version: 2` (v1 → v2 bumped in this branch when PINS was added). This ADR formalises the convention that produced that bump.

## Decision

### D1 — Schema version is a monotonic integer

`schema_version` is an integer at the root of `engagement_kpi_map.json`. It increments by exactly 1 on every change to the file's structure or contents. Semver does not apply — this is a single-consumer artefact with no external clients; the field exists to make replays reproducible against a known map state, not to communicate compatibility.

**What bumps the version:**

- Adding a ticker
- Removing a ticker
- Moving a ticker between `tickers` and `excluded_tickers`
- Changing any field within a ticker entry (`primary_kpi`, `secondary_kpi`, `evidence`, `ai_layer`)
- Renaming a field, adding a field, or removing a field

**What does NOT bump the version:**

- Comment-only edits to `_comment`
- Whitespace / key-order changes that preserve semantic content

Rationale: bumping on every semantic change keeps the version monotonic with the audit trail; bumping on cosmetic edits floods the changelog and devalues each bump.

### D2 — Every bump requires a changelog entry AND an ADR cross-reference

`skills/_shared/engagement_kpi_map.CHANGELOG.md` is the human-readable audit trail. Every bump produces a new section at the top of the file (most-recent first) with:

- Version (`v3`, `v4`, …)
- Date (ISO)
- Author
- Linear issue link
- Tickers added/removed/modified, each with:
  - Source-link evidence (8-K accession + filing URL)
  - One-paragraph rationale citing the design doc or task plan

The changelog is the contract. An edit to `engagement_kpi_map.json` without a corresponding changelog entry is a bug — the file-pair check in D4 enforces this mechanically.

ADR cross-reference: any bump beyond ticker addition (i.e. anything that changes the **structure** — new field, renamed field, new excluded-ticker reason vocabulary) requires a new ADR that supersedes or extends this one. Pure ticker additions live in the changelog only — they don't change the contract, just its population.

### D3 — `excluded_tickers` is part of the schema and follows the same rules

`excluded_tickers` is not a scratch pad. Each entry documents why a ticker that *could* plausibly carry a KPI does not — preserves the reasoning so a future reader (or future me) doesn't re-litigate NFLX or GOOGL every six months. Edits to this block bump `schema_version` and produce a changelog entry, identical to `tickers`.

Resolution fields (`resolves: "OQ3"`, `revisit_when: "..."`) are required when an exclusion resolves a design-doc open question. The `revisit_when` clause is the trigger for re-evaluating the exclusion — it must name an observable condition, not a date.

### D4 — Drift detection runs weekly via CI (built in Task 13)

A scheduled GitHub Actions workflow (`.github/workflows/engagement-kpi-drift.yml`, authored under Task 13) dry-runs the modifier's GATHER step against every ticker in `tickers` once per week. The dry-run:

1. Fetches the latest 8-K Ex 99.1 for the ticker via EDGAR submissions API.
2. Runs the source-phrase regex from the map.
3. Asserts `status == "applied"`.

A workflow run **fails** when:

- Any ticker produces `status != "applied"` on **two consecutive scheduled runs** (one-run flakes are tolerated; sustained drift is not).
- The file-pair check fires: `engagement_kpi_map.json` was modified in HEAD without `engagement_kpi_map.CHANGELOG.md` being modified in the same commit, or vice versa.

Why two consecutive runs: EDGAR transient 5xx, SEC rate-limit, and 8-K filing-day timing windows produce one-off flakes. Requiring two in a row filters those without papering over real drift.

The file-pair check (D4b) is a single grep in the workflow: `git diff --name-only HEAD~1 HEAD | grep -E '(engagement_kpi_map\.json|engagement_kpi_map\.CHANGELOG\.md)'` and assert both appear together or neither does.

### D5 — Replay reproducibility: model runs record the schema version

Every `/stock-model` run that applies the engagement modifier records `kpi_map_schema_version` in the `stages.model.engagement_modifier` JSON block (Task 11 scope). This lets a replay against a stored report know which version of the map was in effect at run time, and surfaces a diff when a re-run against the current map produces a different KPI.

## Consequences

**Positive.**

- Schema bumps are auditable: changelog + Linear link + ADR (for structural changes) means a future reader can trace every map state to a decision.
- Drift detection is mechanical: CI catches Yahoo/EDGAR wording changes before they silently degrade modifier coverage. The two-consecutive-run rule keeps the signal-to-noise high.
- File-pair check prevents the most common future failure mode — editing the JSON and forgetting the changelog — at zero ongoing cost.
- Excluded-ticker block carries its own reasoning, so NFLX/GOOGL re-evaluation is not a re-research task.

**Negative.**

- Adding a single ticker now requires a changelog entry. This is friction for casual edits — the trade is intentional. The file is small enough and the audit value high enough that the friction is correctly priced.
- CI failure on two consecutive missed runs is delayed by one week (the cadence is weekly). Faster cadence is over-served for a personal skill-pack; weekly is the smallest cadence that catches real drift without burning CI minutes on a stable artefact.
- Schema-version-as-integer breaks if a future use case needs semver-like compatibility signalling. That use case is not anticipated; if it arises, supersede this ADR.

**Neutral / open.**

- The forward-log file (`tests/fixtures/engagement_kpi/forward_log.jsonl`, written by Task 10b) is **not** governed by this ADR — it is append-only telemetry, not a contract artefact. Its schema is governed by its own format and any future change to that schema gets its own ADR.

## Linkage

- File governed: `skills/_shared/engagement_kpi_map.json`
- Changelog: `skills/_shared/engagement_kpi_map.CHANGELOG.md`
- CI workflow (built next): `.github/workflows/engagement-kpi-drift.yml` (Task 13)
- Reproducibility hook: `stages.model.engagement_modifier.kpi_map_schema_version` in audit-trail JSON (Task 11)
- Design doc: `docs/design-docs/engagement-kpi-enrichment/design-doc.md`
- Task plan: `docs/tasks/engagement-kpi-enrichment.md` (Task 8 = this ADR; Task 13 = CI workflow)
- Related ADR: `engagement-modifier-constants.md` (the constants ADR; the version bump rule here is parallel to the one-revision-budget rule there).
