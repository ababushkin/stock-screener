# How the engagement-KPI drift CI works

A plain-English reference for what `.github/workflows/engagement-kpi-drift.yml` actually does. Built as part of ABA-66 (Task 13). Lives on milestone M5.5.

## What it is

A GitHub Actions workflow that exists to make sure the engagement-KPI modifier keeps working over time. It does not grow the supported-ticker list, it does not propose new KPIs — it's a health check.

It has two completely separate jobs that fire on different events.

---

## Job 1 — `drift_check` (weekly cron + manual trigger)

**Fires every Monday at 09:00 UTC**, and on demand via the "Run workflow" button on GitHub.

What it does:

1. Reads the list of tickers currently in `skills/_shared/engagement_kpi_map.json` (today: META, RDDT, PINS).
2. For each ticker, runs the modifier's extractor logic and checks whether it produces `status: "applied"` — i.e. the regex still matches, the YoY % parses, the direction comes out non-null.
3. Compares against the previous run's per-ticker pass/fail counters (kept in GitHub Actions' cache between runs).
4. **Passes** if every ticker is applied, OR if a ticker has failed only once (transient flake is tolerated).
5. **Fails** if any ticker has failed **two scheduled runs in a row**. That's the signal of real breakage, not a one-off blip.

A single recovery resets a ticker's counter to zero, so a ticker that flaked once and then came back clean is treated as fully healthy.

What it's protecting against:

- A publisher renaming a metric (e.g. Meta's 2023 DAU → DAP rebrand)
- Yahoo restructuring the `/analysis/` page (column shift, header change)
- SEC filing-convention changes
- Our own regex inadvertently breaking on a code change

**Current limitation** (tracked as ABA-109): the run is hermetic against committed test fixtures, not against live Yahoo / SEC fetches. That means it catches code regressions but does *not* yet catch upstream-publisher changes — which is the whole point. Upgrade ticket filed.

---

## Job 2 — `file_pair_check` (every pull request)

Fires on every PR that touches `engagement_kpi_map.json` or `engagement_kpi_map.CHANGELOG.md`.

What it does: asserts that both files moved together in the PR diff. If the JSON was edited but the changelog wasn't (or vice versa), the check fails and blocks the merge.

What it's protecting against: silent map drift. The changelog is the audit trail — every map change has to leave a paper trail with rationale + Linear link. An edit to the JSON without a changelog entry is by definition a bug (ADR D4b).

---

## What it does NOT do

- It does not discover new tickers or propose new KPI mappings. (That's the hand-curated process today, with ABA-108 tracking a helper to make additions less painful, and ABA-105 tracking a far-future auto-discovery skill.)
- It does not edit the map file itself.
- It does not yet make live fetches to EDGAR / Yahoo — ABA-109 tracks that upgrade.
- It does not validate the modifier's output values are economically reasonable — only that extraction succeeds. NFR7's outcome-direction validation is the forward log, separate machinery.

## What happens when it fails

A failed scheduled run shows up as a red X on the workflow run page and sends GitHub's default failure notification. The job output names the tripped ticker(s) and the reason for each (forced unavailable / regex mismatch / fetch error once live fetches land).

The remediation is human — either fix the regex / map entry to handle the new upstream format (bump `schema_version`, append changelog, open PR), or temporarily exclude the ticker until a fix is ready.

## How to test it yourself

From the GitHub UI: **Actions → engagement-kpi-drift → Run workflow** → enter a ticker (e.g. `RDDT`) in the `force_unavailable` field. The first manual run will be tolerated; a second consecutive run with the same forced ticker will trip the gate and the workflow will fail with a red X. Clear the `force_unavailable` field for the third run and the counter resets.

## Where the code lives

- Workflow: `.github/workflows/engagement-kpi-drift.yml`
- Driver script: `scripts/engagement_kpi_drift_check.py`
- Map file (input): `skills/_shared/engagement_kpi_map.json`
- Changelog (file-pair counterpart): `skills/_shared/engagement_kpi_map.CHANGELOG.md`
- ADR governing the contract: `docs/adrs/engagement-kpi-map-versioning.md` (D4 / D4b)

## When this needs to extend

When ABA-65 (segment revenue) and ABA-67 (infra bookings) ship, each gets its own drift CI workflow on the same pattern. The structure here is the template — keep them in sync.
