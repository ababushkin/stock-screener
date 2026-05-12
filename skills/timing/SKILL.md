---
name: timing
description: When-to-act overlay for a tech stock. Invoked as `/timing TICKER`. Computes SUE (earnings surprise), PEAD window status, EPS revision direction over short windows, and surfaces the next catalyst — then emits a structured TIMING OUTPUT block and merges `stages.timing` into `reports/TICKER_YYYYMMDD.json` without overwriting prior stages. Use whenever the user asks when to enter, whether to wait, what the next catalyst is, or after `/signal` or `/model` returns BUY/WATCH and the user needs an entry decision — even if they don't say "timing."
---

# Timing — When-to-Act Overlay

**Command:** `/timing TICKER`
**Purpose:** Turn a positive Signal/Model thesis into an entry decision. Combines earnings-surprise momentum (SUE + PEAD window), short-window EPS revision direction, and the next scheduled catalyst into a single ACT NOW / WAIT FOR CATALYST / WAIT FOR BETTER ENTRY verdict. Output is merged into the report JSON as `stages.timing`.

---

## 1. Identity

- **Skill name:** timing
- **Command:** `/timing TICKER`
- **Purpose:** Produce a TIMING verdict (ACT NOW / WAIT FOR CATALYST / WAIT FOR BETTER ENTRY) for a single ticker using earnings-surprise, revision, and catalyst signals from the yfinance MCP.

---

## 2. Methodology

Timing is an **overlay**, not a thesis. It assumes the user has already established a positive view from `/screen` and/or `/signal` and is now asking *when*, not *whether*.

Signals:

- **SUE (Standardized Unexpected Earnings)** — `(reported_eps − consensus_eps) / std_dev(surprise over last N quarters)`. Captures both the size and the predictability of the most recent earnings surprise. Positive SUE > 1 indicates a meaningful upside surprise relative to recent variance.
- **PEAD window (Post-Earnings Announcement Drift)** — empirically, stocks that beat tend to drift higher for ~60 days after the announcement. The window status tells the user whether the drift is still in play.
- **EPS revision direction** — short-window (7d, 30d) analyst revision counts. Net upward revisions indicate momentum in the consensus, which usually precedes price.
- **Next catalyst** — the next scheduled date that could re-rate the stock (earnings, investor day, product event).

Source references: Bernard & Thomas (1989) for PEAD; Foster, Olsen & Shevlin (1984) for SUE methodology; Givoly & Lakonishok (1979) for analyst revision drift.

---

## 3. Input Schema

| Input | Source | Data-gap handling |
|---|---|---|
| Ticker | Command argument | Uppercase; fail immediately if blank |
| Last 4 reported quarterly EPS + consensus | `mcp__yf__get_earnings_history(ticker)` | <4 quarters returned → SUE = N/A with reason "insufficient quarterly history" |
| Most recent earnings date | `mcp__yf__get_earnings_history(ticker)` — latest row's date | Null → PEAD window = N/A |
| EPS revisions (7d, 30d up/down counts) | `mcp__yf__get_estimates(ticker)` — `eps_revisions` block | Null → revision direction = N/A with reason "no revision data" |
| Next catalyst date | `mcp__yf__get_estimates(ticker)` — earnings calendar field | Null → fall back to current price ± inference from most recent earnings + ~90d; flag as estimated |
| Current price | `mcp__yf__get_ratios(ticker)` — derived from PE × eps_ttm or market_cap/shares | Null → entry-range fields = N/A |

**Window definitions (locked v1, per ABA-47 spike):**
- **SUE std-dev window:** 4 quarters (the only window yfinance `earnings_history` returns). Output **must** carry a `sue_window: "4q"` field and the output block **must** include a one-line caveat that 4-quarter std-dev is statistically weaker than the 8-quarter window used in the academic literature.
- **EPS revision windows:** 7d and 30d **only**. 60d and 90d are deferred (ABA-47 spike confirmed yfinance does not surface them).
- **`Ticker.upgrades_downgrades` is NOT used.** ABA-47 spike found this surface stale (META latest entry 2024-09-30). Analyst-action momentum is inferred from `eps_revisions` direction only.

---

## 4. Execution Phases

### GATHER

1. Parse the ticker from the command argument. Uppercase it (e.g. `nvda` → `NVDA`).
2. Call the yfinance MCP tools in this order:
   a. `mcp__yf__get_earnings_history` — Input: `{ "ticker": "NVDA" }` — Returns: last 4 quarterly rows with `period_end`, `reported_eps`, `consensus_eps`, `surprise`.
   b. `mcp__yf__get_estimates` — Input: `{ "ticker": "NVDA" }` — Returns: `eps_revisions` (7d/30d up/down counts) and the next earnings date.
   c. `mcp__yf__get_ratios` — Input: `{ "ticker": "NVDA" }` — Used for current price derivation only (already cached by `/screen` or `/signal` if they ran in the same session; refetch is fine).
3. If any tool errors:
   - **YFNoDataError**: report the gap for the specific signal and continue with the remaining signals. Timing is composed of three semi-independent signals — a missing one degrades the verdict, it does not block it.
   - **Server not connected / other failures**: report the failure for that signal as N/A with the error reason; do not write a partial report if all three signals fail.

### VALIDATE

- At least one of {SUE, revision direction, next catalyst} must resolve. If all three are N/A, stop and report — there is no basis for a Timing verdict.
- State which signals were retrieved and which are N/A before computing the verdict.

### COMPUTE

**Step 1 — SUE (Standardized Unexpected Earnings):** *(implementation in ABA-28)*

This stub defines the contract; ABA-28 fills in the math.

Contract:
- Inputs: last 4 quarters of `(reported_eps, consensus_eps)` from `get_earnings_history`.
- Formula: `SUE = (reported_eps_q0 − consensus_eps_q0) / std_dev(reported_eps − consensus_eps over q0..q-3)`.
- Output fields: `sue` (number or null), `sue_window` (always `"4q"` in v1), `sue_caveat` (always present — see below).
- Caveat string (verbatim in the output block): `"4-quarter std-dev is statistically weaker than the 8-quarter window used in the academic literature; treat SUE > 1.5 as the noise floor for v1."`

Stub behaviour until ABA-28 lands: output `SUE: N/A — pending ABA-28`, `sue` = `null` in JSON, `sue_caveat` still present.

**Step 2 — PEAD window status:** *(implementation in ABA-28)*

Contract:
- Input: most recent earnings date from `get_earnings_history`.
- Compute: `days_since_earnings = today − most_recent_earnings_date`.
- Classify:
  - `IN WINDOW` — 0 ≤ days_since_earnings ≤ 60 AND SUE > 0 (positive surprise drift still in play)
  - `IN WINDOW (negative)` — 0 ≤ days_since_earnings ≤ 60 AND SUE ≤ 0 (drift goes the other way — used as a CAUTION marker)
  - `OUTSIDE WINDOW` — days_since_earnings > 60 OR SUE = N/A
- The PEAD window contract uses **60 days** as the academic-standard upper bound; the 45–60 day band is treated as "late window" where the edge is decaying but not gone. Output fields: `pead_window_status`, `days_since_earnings`.

Stub behaviour: output `PEAD window: N/A — pending ABA-28`, `pead_window_status` = `null`.

**Step 3 — EPS revision direction:** *(implementation in ABA-29)*

Contract:
- Inputs: `eps_revisions` block from `get_estimates`, containing `up_7d`, `down_7d`, `up_30d`, `down_30d`.
- Compute net revision counts per window: `net_7d = up_7d − down_7d`, `net_30d = up_30d − down_30d`.
- Direction classification:
  - `UP` — net_30d > 0 AND net_7d ≥ 0
  - `DOWN` — net_30d < 0 AND net_7d ≤ 0
  - `MIXED` — net signs disagree between the two windows
  - `FLAT` — both windows zero
- Output fields: `revision_direction`, `net_revisions_7d`, `net_revisions_30d`. **Never** compute or output 60d/90d windows — they are explicitly out of scope (ABA-47).

Stub behaviour: output `Revision direction: N/A — pending ABA-29`, `revision_direction` = `null`.

**Step 4 — Next catalyst:** *(implementation in ABA-29)*

Contract:
- Input: next earnings date from `get_estimates`. If absent, infer the next earnings date as `most_recent_earnings_date + ~90d` and flag with `catalyst_source: "estimated"`.
- Output fields: `next_catalyst` (one-line string, e.g. `"Earnings report 2026-05-28"`), `next_catalyst_date` (ISO date), `days_to_catalyst` (integer), `catalyst_source` (`"scheduled"` or `"estimated"`).
- The stub does **not** scan for product events, investor days, or 8-K filings — those are future work (Later).

Stub behaviour: output `Next catalyst: N/A — pending ABA-29`, all catalyst fields `null`.

### THRESHOLD — Combine into TIMING verdict

The verdict combination logic is set here in the stub so ABA-28/29 only need to plug in computed values — the table does not change.

| TIMING verdict | Conditions |
|---|---|
| **ACT NOW** | SUE > 1.5 AND `pead_window_status` = `IN WINDOW` AND `revision_direction` = `UP` |
| **WAIT FOR CATALYST** | `days_to_catalyst` ≤ 14 (next earnings or named event is imminent) — overrides any other verdict except ACT NOW |
| **WAIT FOR BETTER ENTRY** | SUE ≤ 0 OR `revision_direction` = `DOWN` OR `pead_window_status` = `IN WINDOW (negative)` |
| **NEUTRAL** | None of the above resolve — typically when `pead_window_status` = `OUTSIDE WINDOW` and revisions are FLAT/MIXED. Treated as WAIT FOR BETTER ENTRY for downstream consumers but emitted as NEUTRAL in the block for transparency. |

Stub behaviour: if all three signals are N/A, emit `TIMING: N/A — pending ABA-28/29`. If at least one signal resolves, apply the table to whatever is available and label the others as missing in the rationale.

### OVERRIDE

- **Earnings within 7 days:** if `days_to_catalyst` ≤ 7, force `WAIT FOR CATALYST` regardless of SUE / revisions. The cost of being wrong about earnings within a week is too high relative to the edge from any other signal. (Implemented in ABA-29 alongside the catalyst lookup.)

### OUTPUT

Emit the TIMING OUTPUT block. **All fields must appear every run.** Unimplemented fields show a placeholder — they are never omitted.

```
TIMING OUTPUT
  Ticker:               [TICKER]
  Date:                 [YYYY-MM-DD]

  SUE:                  [x.xx (4q window) | N/A — reason]
  SUE caveat:           4-quarter std-dev is statistically weaker than the 8-quarter window used in the academic literature; treat SUE > 1.5 as the noise floor for v1.
  PEAD window:          [IN WINDOW | IN WINDOW (negative) | OUTSIDE WINDOW | N/A]
  Days since earnings:  [N | N/A]

  Revision direction:   [UP | DOWN | MIXED | FLAT | N/A — reason]
    Net revisions 7d:   [+N | -N | 0 | N/A]
    Net revisions 30d:  [+N | -N | 0 | N/A]

  Next catalyst:        [one-line description | N/A — reason]
  Days to catalyst:     [N | N/A]
  Catalyst source:      [scheduled | estimated | N/A]

  TIMING:               [ACT NOW | WAIT FOR CATALYST | WAIT FOR BETTER ENTRY | NEUTRAL | N/A]
  Rationale:            [one-line reason citing the decisive signal(s)]
```

**Report JSON write:**
Run `mkdir -p reports` before writing.
Write to `reports/TICKER_YYYYMMDD.json` where YYYYMMDD is today's date.

**Merge behaviour (ABA-29 implements; contract locked here):**

- If the file already exists (e.g. written by `/screen`, `/signal`, or `/model` earlier), READ it first, then merge — add/update `stages.timing` and the `meta.confidence` field only if Timing has a HIGHER-quality confidence than what is already there. **Never** overwrite `stages.screen`, `stages.signal`, or `stages.model`.
- If the file does not exist, create it with the full outer structure and `stages.timing` as the only populated stage.
- The merge rule is non-negotiable. The skill `/timing` is an overlay; the upstream stages are the thesis. Overwriting them silently is a P0 bug.

**Required `stages.timing` JSON structure:**

```json
{
  "ticker": "NVDA",
  "company": null,
  "date": "2026-05-12",
  "stages": {
    "timing": {
      "verdict": "ACT NOW",
      "sue": 1.82,
      "sue_window": "4q",
      "sue_caveat": "4-quarter std-dev is statistically weaker than the 8-quarter window used in the academic literature; treat SUE > 1.5 as the noise floor for v1.",
      "pead_window_status": "IN WINDOW",
      "days_since_earnings": 12,
      "revision_direction": "UP",
      "net_revisions_7d": 3,
      "net_revisions_30d": 7,
      "next_catalyst": "Earnings report 2026-08-21",
      "next_catalyst_date": "2026-08-21",
      "days_to_catalyst": 101,
      "catalyst_source": "scheduled",
      "rationale": "SUE 1.82 above the 1.5 v1 noise floor, PEAD window still in play (day 12 of 60), and 30d revisions net +7 — entry conditions aligned."
    }
  },
  "meta": {
    "profit_stage": null,
    "track": "GROWTH",
    "ai_layer": null,
    "confidence": "MEDIUM"
  }
}
```

**JSON validity rules:**
- Use JSON `null` for any unavailable field — never `""` or `0` as a placeholder
- `sue_window` is always `"4q"` in v1; never `"8q"` (the longer window is not in scope)
- `sue_caveat` string is always present and verbatim — it is the data-quality disclosure the downstream UI depends on
- `revision_direction` is one of `UP`, `DOWN`, `MIXED`, `FLAT`, or `null` — never an empty string
- `verdict` is one of `ACT NOW`, `WAIT FOR CATALYST`, `WAIT FOR BETTER ENTRY`, `NEUTRAL`, or `null`
- No trailing commas, no comments, no NaN values
- `date` is ISO format `YYYY-MM-DD`

**Confidence rules (meta.confidence after Timing merges):**

- **HIGH**: all three signals (SUE, revision direction, next catalyst) resolved to a real value, none of them N/A.
- **MEDIUM**: at least one signal is N/A but the verdict is still computable.
- **LOW**: only one of three signals resolved, or the verdict had to fall back to NEUTRAL.

If the existing report has a `meta.confidence` value, take the **lower** of `existing_confidence` and `timing_confidence` — Timing should never upgrade overall confidence beyond what upstream stages established.

After writing, print:

```
Wrote: reports/NVDA_20260512.json  ← stages.timing
NVDA — ACT NOW | SUE 1.82, PEAD IN WINDOW (day 12), revisions UP (+7 30d), next catalyst in 101d
```

---

## 5. Output Schema

Every run produces the TIMING OUTPUT block above and writes/merges `reports/TICKER_YYYYMMDD.json`. Fields 1–13 are always present in both the block and JSON.

The 13 JSON fields under `stages.timing` are:

1. `verdict` — ACT NOW / WAIT FOR CATALYST / WAIT FOR BETTER ENTRY / NEUTRAL / `null`
2. `sue` — number or `null`
3. `sue_window` — always `"4q"` in v1
4. `sue_caveat` — verbatim caveat string, always present
5. `pead_window_status` — IN WINDOW / IN WINDOW (negative) / OUTSIDE WINDOW / `null`
6. `days_since_earnings` — integer or `null`
7. `revision_direction` — UP / DOWN / MIXED / FLAT / `null`
8. `net_revisions_7d` — integer or `null`
9. `net_revisions_30d` — integer or `null`
10. `next_catalyst` — one-line string or `null`
11. `next_catalyst_date` — ISO date string or `null`
12. `days_to_catalyst` — integer or `null`
13. `catalyst_source` — `"scheduled"` / `"estimated"` / `null`

Plus `rationale` — one-line string summarising the decisive signals.

---

## 6. Data Fetching Behaviour

- Always fetch from yfinance MCP tools — do not use hardcoded values or training-data recall.
- Fetch order: `get_earnings_history` first (SUE/PEAD inputs), then `get_estimates` (revisions + catalyst), then `get_ratios` (price context).
- State what was retrieved, what was missing, and what was assumed before the TIMING OUTPUT block.
- **Do not call `Ticker.upgrades_downgrades`** — it is stale on at least META per the ABA-47 spike and is explicitly excluded from the data priority chain.

---

## 7. Invocation Patterns

```
/timing NVDA
/timing META
```

Timing is a **single-ticker** operation. For multi-ticker batches, the user should run `/screen TICKER1, TICKER2` and then `/timing` on each PASS / WATCH result individually. There is no batch JSON output for Timing — only per-ticker merges into existing `reports/TICKER_YYYYMMDD.json` files.

---

## 8. Dependencies

- **yfinance MCP server** must be connected (`get_earnings_history`, `get_estimates`, `get_ratios`). Registered in `.mcp.json`. If tools are unavailable, tell the user to restart the Claude Code session so the MCP server is reloaded.
- **`reports/` directory** — created on first write via `mkdir -p reports`.
- **Upstream skills** — Timing is an overlay, not a thesis. It runs cleanly on a brand-new ticker (creates a new report file with only `stages.timing` populated), but its real value is on top of an existing `stages.screen` or `stages.signal` result.

---

## 9. Tech-Specific Rules

**SUE window:**
- The std-dev denominator uses **4 quarters** in v1 — that is the only window yfinance exposes via `earnings_history`. Always output `sue_window: "4q"` and always include the SUE caveat string verbatim. Do not silently extend the window or invent prior-period data.

**PEAD window:**
- The empirical PEAD window is **0–60 days** post-earnings. The **45–60 day band is treated as "late window"** — the edge is decaying. ACT NOW remains valid in the late window if SUE > 1.5 and revisions are UP; the rationale must call out that the window is closing.
- OUTSIDE WINDOW = > 60 days since the last earnings announcement.

**Revision windows:**
- v1 reports **7d and 30d only**. 60d and 90d are not implemented and not surfaced by yfinance per the ABA-47 spike. Do not estimate them, do not extrapolate from 7d/30d, do not output them.

**Stale-source exclusion:**
- `Ticker.upgrades_downgrades` is not used. ABA-47 confirmed staleness on META (latest entry 2024-09-30). Do not fall back to it even if `eps_revisions` is missing — instead emit `revision_direction: N/A` with the reason "no revision data".

**Catalyst inference:**
- When the next earnings date is missing from `get_estimates`, fall back to `most_recent_earnings_date + 90d` and set `catalyst_source: "estimated"`. Never guess product event dates or investor-day dates — those require external sources not yet wired up.

---

## 10. Override Rules

All active and planned overrides are defined in the OVERRIDE section of Section 4. As of the stub, the only active override is:

- **Earnings within 7 days → WAIT FOR CATALYST** (forced).

Planned future overrides (not implemented):
- Material 8-K announcement in the last 5 days → WAIT FOR CATALYST until 8-K text is parsed (requires EDGAR `get_filing_text`).
- Insider buying cluster in last 30 days → bias toward ACT NOW (requires Form 4 ingestion, not in scope).

---

## Common Rationalisations

| Rationalisation | Rebuttal |
|---|---|
| "yfinance only returned 3 quarters of earnings history so I'll estimate the 4th" | Don't fabricate a quarterly print. If fewer than 4 quarters resolve, output `SUE: N/A — insufficient quarterly history`. Estimation here would produce a SUE number with no statistical meaning. |
| "I'll use the 8-quarter SUE because the literature says it's stronger" | yfinance only returns 4 quarters per the ABA-47 spike. The skill is locked to a 4q window in v1; the caveat string discloses the weaker basis. Do not silently extend the window. |
| "`upgrades_downgrades` has data so I'll use it as a revision proxy" | That surface is stale (META latest 2024-09-30 per ABA-47). It is explicitly excluded from the data priority chain. Use `eps_revisions` only; if it's missing, output N/A. |
| "60d and 90d revision counts would make the signal stronger so I'll compute them from 7d/30d trends" | 60d/90d windows are out of scope per ABA-47 — yfinance does not surface them and extrapolation is not the same as measurement. Output only 7d and 30d. |
| "Next earnings date is missing so I'll skip the catalyst field" | Every field appears every run. If the scheduled date is missing, infer `most_recent_earnings_date + 90d` and set `catalyst_source: "estimated"`. Never omit the field. |
| "stages.signal already exists in the report so I'll overwrite the whole file with my Timing payload" | Merge behaviour is mandatory. READ the existing file, ADD `stages.timing`, write the merged structure. Overwriting `stages.screen`, `stages.signal`, or `stages.model` is a P0 bug. |
| "The report doesn't exist yet so I'll skip writing one" | Timing creates a new report file when none exists, with `stages.timing` as the only populated stage. The UI reads whatever stages are present. |
| "All three Timing signals are N/A so I'll still emit a verdict to be useful" | If SUE, revision direction, and next catalyst are all N/A, there is no basis for a verdict. Stop and report the gaps. A guessed verdict is worse than no verdict. |
| "Earnings are tomorrow but SUE is 2.1 and revisions are UP so I'll say ACT NOW" | Override: earnings within 7 days forces WAIT FOR CATALYST. The asymmetry — full earnings risk vs. a few days of held edge — is not worth the bet. |
| "I'll round SUE to 1 decimal place in the JSON" | Preserve full numeric precision in the JSON. Rounding belongs in the display block, not the data file. |
| "PEAD window status is `IN WINDOW (negative)` but SUE is missing so I'll say `IN WINDOW`" | `IN WINDOW (negative)` requires a computed negative SUE. If SUE is N/A, PEAD window is also N/A (the positive vs. negative split depends on the SUE sign). Don't fake it. |

---

## Boundaries

- Never overwrite `stages.screen`, `stages.signal`, or `stages.model` — Timing only writes `stages.timing` and may downgrade `meta.confidence`.
- Never use `Ticker.upgrades_downgrades`.
- Never extend the SUE window beyond 4 quarters or invent 60d/90d revision counts.
- Never emit a verdict when all three signals are N/A.
- Timing is single-ticker only — no batch SCREEN_YYYYMMDD.json equivalent.
- `company` is `null` in JSON; do not guess or hardcode the company name (it's a Screen/Signal-phase concern).
- Do not add fields not listed in the output schema above.
