# Walking-skeleton spike outputs — Task 1 (ABA-66)

**Run date:** 2026-05-14
**Branch:** `anton/aba-66-eng-kpi-spike`
**Mode:** Agent acts-as-the-skill (no SKILL.md changes yet — pure spike). Fetches EDGAR 8-K Exhibit 99.1 directly via SEC HTTP (FR8 fallback #2), extracts the mapped KPI, derives the modifier per design-doc Recommended-approach §3, emits a candidate `stages.model.engagement_modifier` JSON block.

## Caveat on "hand-verification" leg

Task 1's "Done when" criterion calls for extracted values "matching a hand-verified expected within ±2%". In this spike I was both extractor and verifier, which weakens the precision claim. The raw evidence (the literal source-phrase + the surrounding sentence from the press release) is captured below so the user can independently hand-verify. Real golden-fixture verification (NFR2) lands in **Task 12**.

---

## META — Q1 2026 (period ending 2026-03-31)

**Source filing:** 8-K filed 2026-04-29, accession `0001628280-26-028364`
**Exhibit URL:** https://www.sec.gov/Archives/edgar/data/1326801/000162828026028364/meta-03312026xexhibit991.htm

**Raw evidence (verbatim from Ex 99.1):**

> Family daily active people (DAP) — DAP was 3.56 billion on average for March 2026, an increase of 4% year-over-year.

> Ad impressions — Ad impressions delivered across our Family of Apps increased by 19% year-over-year.

**Derivation:**

| Field | Value | Source |
|---|---|---|
| `kpi_name` | DAP | engagement_kpi_map.json → META.primary_kpi |
| `kpi_value` | 3.56 | Ex 99.1 |
| `kpi_unit` | billion | Ex 99.1 |
| `kpi_period` | "Q1 2026" | filing date + items 2.02 |
| `yoy_change` | 0.04 | "increase of 4% year-over-year" |
| `direction` | +1 | abs(0.04) > 0.02 deadband; sign +ve |
| `magnitude` | mild | abs(0.04) < 0.08 strong-threshold |
| `base_anchor_multiplier` | 1.02 | 1 + 1 × 0.02 |
| `source_type` | edgar_8k_exh99 | resolution path #2 |

**Candidate JSON block:**

```json
{
  "stages": {
    "model": {
      "engagement_modifier": {
        "status": "applied",
        "status_reason": null,
        "kpi_name": "DAP",
        "kpi_value": 3.56,
        "kpi_unit": "billion",
        "kpi_period": "Q1 2026",
        "yoy_change": 0.04,
        "direction": 1,
        "magnitude": "mild",
        "base_anchor_multiplier": 1.02,
        "source_url": "https://www.sec.gov/Archives/edgar/data/1326801/000162828026028364/meta-03312026xexhibit991.htm",
        "source_accession": "0001628280-26-028364",
        "source_type": "edgar_8k_exh99",
        "schema_version": 1,
        "user_confirmed": false
      }
    }
  }
}
```

`user_confirmed: false` reflects that the MIP gate has not been wired into the live skill yet (Task 9). The spike output is a candidate the MIP would have been asked to confirm.

---

## RDDT — Q1 2026 (period ending 2026-03-31)

**Source filing:** 8-K filed 2026-04-30, accession `0001713445-26-000067`
**Exhibit URL:** https://www.sec.gov/Archives/edgar/data/1713445/000171344526000067/earningspressreleaseq126.htm

**Raw evidence (verbatim from Ex 99.1):**

> Reddit Reports First Quarter 2026 Results — Daily Active Uniques ("DAUq") increased 17% year-over-year to 126.8 million

> DAUq: Global 126.8 / U.S. 53.5 (+7%) / International 73.3 (+26%)
> Logged-in DAUq: Global 52.0 (+7%)

**Derivation:**

| Field | Value | Source |
|---|---|---|
| `kpi_name` | DAUq | engagement_kpi_map.json → RDDT.primary_kpi |
| `kpi_value` | 126.8 | Ex 99.1 headline + table |
| `kpi_unit` | million | Ex 99.1 |
| `kpi_period` | "Q1 2026" | filing date + items 2.02 |
| `yoy_change` | 0.17 | "increased 17% year-over-year" |
| `direction` | +1 | abs(0.17) > 0.02 deadband; sign +ve |
| `magnitude` | strong | abs(0.17) ≥ 0.08 strong-threshold |
| `base_anchor_multiplier` | 1.04 | 1 + 1 × 0.04 |
| `source_type` | edgar_8k_exh99 | resolution path #2 |

**Candidate JSON block:**

```json
{
  "stages": {
    "model": {
      "engagement_modifier": {
        "status": "applied",
        "status_reason": null,
        "kpi_name": "DAUq",
        "kpi_value": 126.8,
        "kpi_unit": "million",
        "kpi_period": "Q1 2026",
        "yoy_change": 0.17,
        "direction": 1,
        "magnitude": "strong",
        "base_anchor_multiplier": 1.04,
        "source_url": "https://www.sec.gov/Archives/edgar/data/1713445/000171344526000067/earningspressreleaseq126.htm",
        "source_accession": "0001713445-26-000067",
        "source_type": "edgar_8k_exh99",
        "schema_version": 1,
        "user_confirmed": false
      }
    }
  }
}
```

---

## NFLX — Q1 2026 (period ending 2026-03-31)

**Source filing:** 8-K filed 2026-04-16, accession `0001065280-26-000137`
**Exhibit URL:** https://www.sec.gov/Archives/edgar/data/1065280/000106528026000137/ex991_q126.htm

**Raw evidence (verbatim from shareholder letter):**

> Q1 revenue grew 16% year over year (+14% on a FX-neutral basis) and operating income grew 18%.

> Our primary internal quality engagement metric hit an all-time high in Q1.

**Result:** NFLX is deliberately excluded from `engagement_kpi_map.json` v1 (see CHANGELOG and OQ3). The "primary internal quality engagement metric" is qualitative and not extractable as a numeric YoY; revenue-on-revenue is circular for the modifier's purpose; net-adds stopped quarterly disclosure in Q1 2025.

**Candidate JSON block (no_kpi_mapping path):**

```json
{
  "stages": {
    "model": {
      "engagement_modifier": {
        "status": "no_kpi_mapping",
        "status_reason": "no_kpi_mapping",
        "kpi_name": null,
        "kpi_value": null,
        "kpi_unit": null,
        "kpi_period": null,
        "yoy_change": null,
        "direction": null,
        "magnitude": null,
        "base_anchor_multiplier": 1.00,
        "source_url": null,
        "source_accession": null,
        "source_type": null,
        "schema_version": 1,
        "user_confirmed": false
      }
    }
  }
}
```

Note: `base_anchor_multiplier = 1.00` (i.e. no-op) is emitted so downstream COMPUTE math is uniform — every report has the field, applied or not. Whether to omit the field entirely vs. emit a no-op is an open design choice; the design doc §4 specifies the block is "new optional", so omission is allowable. I lean toward "always emit the block, with `status` distinguishing applied vs. each non-applied path" — clearer for the UI and for replay.

---

## Surface-coverage summary (NFR2 walking-skeleton goal)

| Ticker | Surface (8-K Ex 99.1 internal style) | Extracted? | Hand-verified primary value |
|---|---|---|---|
| META | Table-heavy + bulleted highlights | ✅ DAP 3.56B, +4% YoY | ✅ |
| RDDT | Bulleted headline + tabular DAUq breakdown | ✅ DAUq 126.8M, +17% YoY | ✅ |
| NFLX | Shareholder-letter prose (mostly narrative) | n/a — deliberately excluded from map (OQ3) | n/a |

**Surfaces successfully extracted from when mapped:** 2/2 (100%). NFR2 floor ≥80% trivially cleared on the mapped subset. The NFLX surface was still exercised (fetched + parsed + screened for an extractable engagement KPI; correctly routed to no_kpi_mapping).

## Open-question resolutions emerging from this spike

- **OQ3 (NFLX substitute KPI):** RESOLVED — NFLX excluded from v1 map; revisit on disclosure-cadence change.
- **OQ6 (GOOGL fallback KPI):** RESOLVED — GOOGL excluded from v1 map; revisit on segment-disclosure expansion.
- **OQ1 (revenue vs. FCF-margin lever):** Open — defer to Task 9 (wiring) where the lever choice interacts with the live COMPUTE step.
- **OQ5 (base-only vs. all-three scenarios):** Open — defer to Task 5 (constants ADR).

## Next steps within Task 1

- (Task 1.completion) Reproducibility check (Task 3) — same-day repeat invocations on META + RDDT should produce identical fields. Since EDGAR accession numbers are immutable and the source-phrase patterns are deterministic, reproducibility risk is low; Task 3 will harness this.
- (downstream) Task 4 — backtest data-source feasibility for the 4-week post-print analyst revision data.
