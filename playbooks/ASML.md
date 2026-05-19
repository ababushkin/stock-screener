---
ticker: ASML
last_updated: 2026-05-18
base_wacc: 8.5
growth_ceiling: 0.15
terminal_margin: 0.30
confidence_anchor: MEDIUM
bear_narrative: "Broad semiconductor capex air-pocket: mobile demand softens, memory cycle bottoms slower than expected, mature-node utilisation drops below normal — combined with High-NA economics failing to clear at scale (cost-per-wafer doesn't beat multi-patterning DUV); tightening China rules erode service revenue from installed base; unit volumes flatten well below LRP, terminal FCF (Free Cash Flow) margin compresses to TTM-clean levels on customer under-utilisation"
base_narrative: "Semi capex cycle troughs in 2026 then re-accelerates 2027–2029 on AI infrastructure + advanced-node ramps; High-NA reaches volume production at TSMC + one other customer by 2027 at credible economics; China remains a 15–20% revenue contributor under current export-control framework; ASML lands mid-range of 2030 LRP (Long-Range Plan) envelope"
bull_narrative: "Any combination of independent upside vectors pulls ASML toward upper-LRP: (i) AI-driven advanced-node capex sustained across TSMC Arizona + Intel Ohio + Samsung Taylor; (ii) hyperscaler-funded custom-silicon fabs (Google TPU, Meta MTIA, Amazon Trainium) adding leading-edge wafer demand; (iii) advanced packaging (HBM, glass substrates, chiplets) expanding adjacent litho TAM (Total Addressable Market); (iv) 3D-DRAM / multi-layer memory adoption raising EUV intensity per wafer; (v) High-NA unit economics validating above expectations enabling faster customer ramp; (vi) services + installed-base growth exceeds LRP. China relaxation is an additive (low-probability) upside, not a precondition."
failure_modes:
  - "Structural customer concentration in leading-edge EUV (TSMC + Samsung + Intel for logic; SK Hynix + Micron for memory) — any single major customer delaying a node, cancelling capex, or extending a digestion phase moves IV materially [TODO: verify exact top-3/top-5 % against latest ASML 20-F / annual report risk-factor disclosure] [demand layer]"
  - "China export controls broadened to service/spare-parts of installed DUV base — would damage the most defensive component of ASML's cash flow (services + installed-base management) [regulatory layer]"
  - "High-NA cost-per-wafer fails to clear vs multi-patterning DUV at scale — slows customer adoption and breaks the post-2027 unit-volume growth premise [technology layer]"
  - "Broad-based semi capex air-pocket — mobile (smartphone unit weakness), memory (DRAM/NAND oversupply cycle), or mature-node (industrial / auto demand normalisation) downturn overlapping with leading-edge digestion compresses revenue across all segments at once [demand layer]"
  - "Reported FCF heavily distorted by customer prepayments — using TTM FCF as base year produces misleading CAGRs in either direction without working-capital normalisation [accounting layer]"
  - "Persistent EUR/USD strengthening reduces translated revenue and earnings even with a stable underlying EUR-denominated business [FX layer]"
scenario_axes:
  bear:
    terminal_margin: 0.24
  bull:
    growth_ceiling: 0.20
---

# ASML Playbook

**Coverage status:** ESTABLISHED · INFRASTRUCTURE  
**Thesis in one line:** EUV monopoly + High-NA ramp + China export-control overhang, with the semiconductor capex cycle as the dominant input.

---

## 1. Business Architecture

### Segment mix (approximate FY2025 basis)

| Segment | Revenue share | Growth trajectory |
|---|---|---|
| EUV systems (standard + High-NA) | ~50% | Cycle-dependent; High-NA ramp adds a step-up from 2026 |
| Advanced DUV (immersion) | ~25% | Mature; sensitive to logic node digestion pace |
| Mature DUV (dry, KrF, i-line) | ~10% | Stable; exposed to auto / industrial / mature-node capex |
| Installed Base Management (IBM) — services + upgrades | ~15% | Most defensive; ~25% of revenue; less cyclical than new tool orders |

IBM (Installed Base Management) is the earnings-floor segment: service contracts and upgrades on the ~4,000-tool installed base continue regardless of new-system order cycles. It is the component most vulnerable to a China-service-rule tightening scenario (see Failure Modes).

### Key revenue drivers

1. **EUV unit shipments** — the volume metric for leading-edge logic. Consensus expects a step-up to ~90–100 units/year by 2027 from ~50–60 in 2024; below-60 for two consecutive years is a bearish inflection signal.
2. **High-NA EUV ramp** — ASP (Average Selling Price) per High-NA tool is ~€350M vs ~€200M for standard EUV. Even 5 additional High-NA units/year moves blended ASP materially. First customer is TSMC; Intel and Samsung are expected second/third.
3. **China revenue share** — ranged 20–49% of system revenue (2022–2023 peak) before export-control restrictions; tracking ~15–20% under current rules. Further rule tightening is the bear-case revenue risk; stabilisation at current levels is the base case.
4. **IBM attach rate** — services revenue as % of cumulative installed base value. Rising attach rate signals customer utilisation and confidence; falling attach rate (e.g., from China service restrictions) is the canary in the earnings-floor thesis.

### End-market exposure

- **Leading-edge logic (HPC/AI + smartphones):** TSMC, Samsung Foundry, Intel Foundry — drive EUV and High-NA demand
- **Memory (DRAM + NAND):** SK Hynix, Micron, Samsung Memory — drive EUV-for-DRAM and advanced-patterning demand
- **Mature logic / specialty:** auto, industrial, IoT via mature DUV (less cyclically exposed but not immune)

Customer concentration: TSMC + Samsung + Intel represent the dominant share of EUV system revenue. [TODO: verify exact top-3/top-5 % against latest ASML 20-F / annual report risk-factor disclosure — do not cite a specific number without verification]

---

## 2. Capex-Cycle Position

ASML is in a **cycle-trough / inflection** phase as of mid-2026. The 2024–2025 digestion period (customers pausing orders after COVID-era over-ordering of DUV tools) is expected to trough in 2026, with re-acceleration in 2027–2029 on two overlapping drivers:

1. **AI-driven advanced-node demand:** TSMC N2/N2P, Samsung 2GAP, Intel 18A ramps require sustained EUV intensity. Hyperscaler custom-silicon fabs (Google, Meta, Amazon) are incremental new demand on top of smartphone-driven baseline.
2. **High-NA volume ramp:** First High-NA tools are being qualified at TSMC Arizona and Intel Ohio. If High-NA economics validate (cost-per-wafer clears vs multi-patterning DUV), the step-up in ASP per unit creates a revenue tailwind independent of unit-volume growth.

**Normalised-margin thesis:** The `terminal_margin` override of 30% assumes High-NA reaches mature unit economics, customer utilisation normalises post-trough, and customer-prepayment working-capital swings dampen over a full cycle. TTM clean FCF (Free Cash Flow) margin (~24%) is trough-distorted by both the demand digestion period and ramp-related investment; anchoring the DCF on TTM understates steady-state. The 30% base sits between TTM clean FCF (~24%) and TTM earnings margin (~35%, implied by P/E 49.5 / P/S 17.18) — a defensible midpoint.

**Bear case:** If High-NA economics fail to clear at scale OR if the semi cycle air-pocket is deeper than expected, utilisation stays weak and terminal margin compresses to TTM-clean levels. This is exactly what `scenario_axes.bear.terminal_margin: 0.24` captures — it anchors the bear terminal margin at the observed trough rather than at a symmetric ±delta from base.

**Cycle re-acceleration signal:** The evidence-gating condition for the base-case trough-and-re-acceleration thesis is three concurrent observables: (a) SEMI book-to-bill ratio sustained above 1.2 for ≥2 consecutive quarters; (b) ASML's quarterly earnings commentary guiding EUV unit shipments toward ≥70 units/year run-rate; (c) published guidance confirming the 2030 LRP (Long-Range Plan) envelope without downward revision at a Capital Markets Day event. A ratio that stays below 1.0 and LRP guidance that steps down by FY2028 would constitute evidence for the extended-digestion bear case rather than a V-shaped recovery.

---

## 3. Active Catalysts

| Catalyst | Probability | IV impact | Direction |
|---|---|---|---|
| High-NA volume production milestone at TSMC (first 5+ unit run-rate quarter) | ~40% by end-2027 | +10–15% | Positive — validates post-2027 ASP and unit thesis |
| China export-control broadened to DUV service/spare-parts | ~25% | −15–20% | Strongly negative — removes earnings floor |
| TSMC Arizona N2 ramp goes to plan (capex not deferred) | ~55% | +5–8% | Positive — confirms leading-edge demand base |
| Intel 18A achieves volume yield (customer ramp on-track) | ~30% | +5–10% | Positive — adds a third High-NA anchor customer |
| Broad semi-capex freeze (memory + logic simultaneously) | ~20% | −20–30% | Strongly negative — all segments decelerate |
| Hyperscaler custom-silicon fab commitments (Google/Amazon/Meta) | ~35% by 2028 | +5–10% | Positive — incremental leading-edge demand |
| Rapidus (Japan) first production milestone | ~25% by 2027 | +3–5% | Positive — new geographic customer |
| Semi-cycle inflection confirmed by leading indicators (SEMI book-to-bill >1.2 for 2+ quarters) | ~50% by end-2026 | +8–12% | Positive — re-rates forward estimates |

---

## 4. Sell-Side Disagreement Axes

The real arguments the sell-side is having on ASML right now. Each axis identifies what distinguishes recoverable cycle noise from a thesis-breaking structural signal.

---

### 1. Capex-cycle trough timing

**The question:** Does the semiconductor capex cycle trough in H2 2026 and re-accelerate cleanly into 2027–2028, or is digestion deeper and longer — extending into 2027–2028 on memory oversupply and smartphone demand weakness?

- **Bull:** TSMC has sustained its 2025 and 2026 capex guidance across multiple earnings calls; SK Hynix is proceeding with HBM3E expansions despite DRAM pricing softness; AI-driven advanced-node demand is pulling forward leading-edge EUV tool orders. A V-shaped re-acceleration beginning H1 2027 is consistent with prior semi-cycle trough-to-recovery timelines (2019 trough recovered in ~14 months; 2022–2023 trough recovered in ~12 months).

- **Bear:** Memory oversupply (DRAM/NAND inventory digestion) is slower-than-consensus; smartphone unit demand remains soft and depresses mature-node utilisation; Intel's financial difficulties and delayed 18A ramp reduce one of the three leading-edge anchor customers. In this scenario the digestion period extends to 2027–2028, producing an L-shaped trough rather than a V, and ASML's unit volume misses the upper-LRP trajectory by 2+ years.

- **Noise vs. structural:** A single quarter of order intake recovery or SEMI book-to-bill above 1.0 is noise — quarterly lumpiness in order timing is normal. Structural re-acceleration signal requires all three of the following simultaneously: (a) SEMI book-to-bill ratio sustained above 1.2 for ≥2 consecutive quarters; (b) ASML's own published EUV unit shipment guidance pointing to ≥70 units/year run-rate (disclosed quarterly in earnings commentary); (c) no downward revision to the 2030 LRP envelope in a Capital Markets Day or investor guidance event. Any one criterion alone is insufficient; the three together constitute a falsifiable trough-confirmation signal.

---

### 2. High-NA economics at scale

**The question:** Will High-NA EUV cost-per-wafer clear the threshold where customers prefer it to multi-patterning DUV at volume production — or does the economics crossover point remain too far out to support the post-2027 unit-growth and ASP premise?

- **Bull:** TSMC's public endorsement and Intel's production commitments for High-NA are not speculative — both have qualified High-NA tools for their most advanced nodes. The cost-per-wafer equation improves on learning curves: lithography steps collapse from 4–6 DUV multi-patterning passes to a single High-NA pass, reducing process complexity, cycle time, and defect probability. Even before full cost crossover, High-NA enables EUV-only nodes that multi-patterning DUV cannot achieve — making adoption a technical requirement, not a pure economics decision.

- **Bear:** High-NA tools are €350M+ per unit vs ~€200M for standard EUV — a 75% ASP premium that must be recovered through wafer-cost savings. Early yield data is not publicly disclosed; learning curves at initial production yields are slower than mature EUV yields, and the cost crossover point is sensitive to assumptions about yield improvement pace. Multi-patterning DUV is proven technology at current-generation production nodes; Intel and TSMC both retain the option to extend multi-patterning for one additional node generation if High-NA economics don't validate quickly enough.

- **Noise vs. structural:** ASML's quarterly High-NA unit shipment count (disclosed by tool category in earnings) is the primary observable. Fewer than 5 High-NA units shipped in 2027 would indicate adoption is materially below the bull-case trajectory, but could still reflect timing delays rather than economic rejection. A structural signal that High-NA economics have failed to clear requires a qualitative threshold event: a major customer (TSMC or Intel) publicly reducing its High-NA unit plan for its most advanced node, or announcing a reversion to multi-patterning DUV for a node previously committed to High-NA. No such event has occurred as of Q1 2026. The bear case as of today is a timing risk — "crossover happens later" — not yet a thesis-breaking failure.

---

### 3. China revenue durability

**The question:** Is 15–20% China revenue a stable floor under the current export-control framework, or will progressive rule-tightening — particularly an extension to DUV service/spare-parts — erode it further toward 5–10%?

- **Bull:** Current export controls primarily restrict new EUV system sales and the most advanced DUV (immersion) systems. The existing DUV installed base in China (thousands of tools qualifying for China-node manufacturing) continues to generate service, maintenance, and spare-parts revenue under current rules. SMIC and other Chinese fabs are expanding mature-node capacity on the DUV installed base; utilisation of existing tools supports ongoing IBM (Installed Base Management) attach revenue. The bull case requires no relaxation of current rules — simply that no further expansion occurs.

- **Bear:** The export-control framework is ratcheting incrementally: 2023 EUV ban, 2024 advanced-DUV restriction, with the next logical policy step being service/spare-parts supply restriction on the DUV installed base already in China. Each incremental tightening reduces the addressable revenue pool. The bear case is that China revenue converges toward 5–10% (service on increasingly restriction-impaired installed base) rather than stabilising at 15–20%, compressing IBM revenue simultaneously with new-system revenue.

- **Noise vs. structural:** Quarter-to-quarter China revenue fluctuation (from ASML's disclosed China revenue share, reported quarterly) is noise — order timing, tool delivery schedules, FX, and pre-cutoff order pull-forward all create lumpiness. Structural erosion signal requires a binary event: a formally announced and implemented rule expansion that explicitly covers service or spare-parts supply to the existing DUV installed base in China. An announced rule change under review is procedural noise; an implemented rule with ASML subsequently disclosing China service revenue decline in two consecutive quarters is structural signal. The sell-side range on China's 2027 revenue contribution spans roughly 8–22% — this width reflects genuine policy uncertainty, not analytical disagreement on existing data.

---

### 4. TAM ceiling — real or expandable?

**The question:** Does ASML's 2030 LRP (Long-Range Plan) implying ~$28B advanced-logic equipment TAM at ~86% EUV penetration represent a hard ceiling, or is the addressable TAM itself expanding through new lithography demand vectors not captured in the LRP?

- **Bull:** The TAM is dynamic. Three expansion vectors are visible beyond the LRP baseline: (a) **3D-DRAM and multi-layer NAND** architectures raise EUV-intensity per wafer as vertical complexity increases — each additional 3D memory layer requires additional litho steps; (b) **advanced packaging** formats (HBM stacks, glass substrate interposers, chiplet-to-chiplet interconnects) require new lithography steps not present in prior planar-chip LRP planning; (c) **geographic fab proliferation** (TSMC Arizona, Samsung Taylor, Intel Ohio, Rapidus Japan, European IPCEI fabs) creates new-customer tool purchase demand above the historical three-customer-concentration baseline. If these vectors are additive to the LRP rather than captured within it, the effective TAM is $32–36B+ rather than $28B.

- **Bear:** ASML's LRP is built with visibility into customer capex plans — the demand from AI-driven leading-edge fabs, memory complexity growth, and geographic expansion is already modelled by ASML's internal planning team and reflected in the LRP envelope. The "TAM expansion" vectors cited by bulls are in the LRP; the question is not whether they exist but whether they materialise faster or slower than LRP cadence. If the LRP already captures these demand vectors, the bull thesis for above-LRP revenue is equivalent to assuming demand exceeds ASML's own planning — which requires a specific positive surprise, not just a continuation of stated strategy.

- **Noise vs. structural:** ASML's Capital Markets Day guidance revisions are the primary falsification test. If successive CMD guidance revisions show upward adjustments to memory-EUV tools/year or packaging litho unit count above the prior CMD baseline, that is TAM-expansion confirmation signal — demand is outrunning LRP projections. If CMD guidance holds flat or revises down despite visible AI infrastructure investment announcements, it implies the LRP already captured the demand that markets are treating as incremental upside. The 2025 CMD is the most recent reference point; the forward falsification test is whether the next CMD (expected 2027) revises memory and packaging litho demand above 2025 CMD levels.

---

### 5. IBM (services) growth as the moat anchor

**The question:** Is Installed Base Management a durable ~25% revenue floor that grows with the installed base regardless of cycle — or is the IBM earnings-floor thesis overstated given its exposure to utilisation cycles and China service restrictions?

- **Bull:** IBM revenue compounds with the installed base: 4,000+ tools in the field, growing at ~100–150 units/year net, each generating multi-decade service agreements. Customers cannot risk tool downtime at advanced nodes — ASML service engineers are embedded in fabs, and rapid-response maintenance is mission-critical to fab yield and throughput. This operational embedding creates strong pricing power and high contract renewal rates. As long as China-installed-base DUV tools continue operating under current rules, service and spare-parts revenue from that pool flows through. IBM has been the most stable revenue segment through prior cycle troughs (2019, 2022–2023).

- **Bear:** IBM has two structural vulnerabilities that consensus underweights. First: customer utilisation declines during a broad capex air-pocket reduce upgrade spend — upgrades are discretionary within the IBM line even if maintenance contracts are not; in a deep trough, upgrade mix falls and IBM growth stalls. Second: China service/spare-parts export restrictions would remove the China-installed-base IBM revenue pool discretely rather than gradually — this is a non-linear event, not a ramp. The IBM earnings-floor thesis holds only while both customer utilisation is above a minimum threshold and China service rules remain as-is. If either condition breaks, the floor is lower than consensus models.

- **Noise vs. structural:** IBM revenue is disclosed quarterly as a named segment line. A single-quarter IBM revenue decline is noise — seasonal maintenance scheduling, customer-site shutdowns, and FX create quarter-to-quarter lumpiness. Structural IBM impairment signal requires IBM revenue declining year-over-year for ≥2 consecutive quarters while ASML's total installed base is growing — this configuration (shrinking IBM on a growing base) indicates attach-rate compression (customers spending less per tool in the field), not just installed-base-size effects. A China service-restriction announcement is the most decisive binary structural signal: it would be immediately visible in the subsequent quarter's China service revenue commentary and would pre-empt the two-quarter confirmation window.

---

## 5. Failure Modes

These are the thesis-breaking scenarios that the DCF does not capture because they are discrete rather than smooth:

- **Customer concentration shock:** TSMC + Samsung + Intel represent the dominant share of EUV system revenue. [TODO: verify exact % against latest 20-F] A single customer deferring a node by 12+ months or announcing a major capex freeze moves ASML's near-term revenue by a multiple of consensus expectations. This is not a gradual risk — it is a lumpy, concentrated exposure. [demand layer]

- **China service/spare-parts export controls:** Current restrictions primarily cover new EUV and advanced DUV system sales. If rules extend to servicing or supplying spare parts to the existing DUV installed base in China, ASML's most cycle-resistant revenue stream is impaired. This would be the bear case's "earnings-floor-removal" event — the scenario where the business becomes more cyclical than the base case assumes. [regulatory layer]

- **High-NA economics failure:** High-NA adoption depends on cost-per-wafer clearing the threshold where customers prefer it to multi-patterning DUV. If High-NA tool yields remain low, learning curves are steeper than expected, or customer process engineers can't close the cost equation, adoption slows. This breaks the post-2027 unit-volume and ASP (Average Selling Price) expansion thesis simultaneously — the two largest contributors to LRP upper-bound revenue. [technology layer]

- **Broad capex air-pocket (multi-segment, simultaneous):** The bear case is NOT "AI investment pauses." The more dangerous scenario is a broad-based semi downturn overlapping across memory (DRAM/NAND oversupply), mobile (smartphone unit weakness), and mature-node (industrial / auto demand normalisation) segments at once. In this scenario, even IBM service revenue is pressured by customer utilisation declines, and ASML's financial performance is worse than any single-segment stress model predicts. [demand layer]

- **FCF (Free Cash Flow) distortion from customer prepayments:** ASML's reported FCF is significantly affected by customer prepayment timing. In strong-order years, prepayments boost FCF above earnings; in weak-order years, the reverse. Using any single-year TTM FCF as a DCF anchor without working-capital normalisation produces misleading base-year CAGRs. The `terminal_margin` override partially mitigates this by anchoring on a normalised steady-state rather than TTM, but the Y1 FCF used in the DCF can still be distorted. [accounting layer]

- **EUR/USD strengthening:** ASML reports in EUR. Persistent EUR appreciation against USD reduces translated revenue and EPS for US-listed ADR investors (ASML US), even with no change in the underlying business. Because the customer base (TSMC, Samsung, SK Hynix, Micron) operates in USD-denominated capital markets, ASML's competitive position is unaffected by FX — but the P&L in USD terms is sensitive. [FX layer]

---

## 6. Ticker-Specific Overrides (Rationale)

| Field | Value | Rationale |
|---|---|---|
| `base_wacc` | 8.5% | Euro 10y Bund ~3.0% + Beta ~1.15 × 5.5% ERP ≈ 9.3%; less ~0.8pp monopoly-durability discount (EUV is a single-supplier market with no credible near-term challenger — NIKON exited advanced EUV; Canon competes only at dry DUV). Rounds to 8.5%, defensible mid-range of sell-side (8.0–9.0%). Reports in EUR; risk-free rate is EUR-denominated. |
| `growth_ceiling` | 15% | Anchored as a **fallback ceiling, not an absolute cap** — consensus `eps_growth_5y` from `get_estimates` takes precedence per override hierarchy. Set at 0.15 = upper-LRP-bound (13%) + ~2pp headroom for: (a) AI-driven wafer-equivalent demand expansion, (b) advanced packaging litho TAM beyond pure leading-edge logic, (c) 3D-DRAM / memory complexity raising EUV intensity per wafer. Below the generic 18% fallback because the structural TAM-penetration situation (~86% of advanced-logic equipment TAM per ASML signal note) makes the central case TAM-expansion-bounded, not share-gain-bounded. |
| `terminal_margin` | 30% | **Subjective steady-state; bear/bull asymmetric per `scenario_axes`.** Base 30% assumes High-NA reaches mature unit economics and working-capital swings dampen over a full cycle. Bear scenario anchors to `scenario_axes.bear.terminal_margin: 0.24` (TTM-clean, the "High-NA stays expensive / utilisation weakens" case) rather than a symmetric −5pp delta. Bull scenario lifts `growth_ceiling` rather than `terminal_margin` — the bull upside in this name is more volume / demand driven than margin driven. |
| `confidence_anchor` | MEDIUM | TAM ceiling and High-NA economics are live, contested, and unresolved theses. Even with good MCP data quality, the IV range is irreducibly wide. Honest cap is MEDIUM until High-NA volume ramp validates the post-2027 unit-growth premise. |

### `scenario_axes` design rationale

Standard ±multiplier scenarios would produce symmetric bear/bull deltas from the base. ASML's thesis is structurally asymmetric:

- **Bear downside** is bounded: terminal margin can't fall below observed TTM-clean levels (~24%) in a cyclical scenario — setting `bear.terminal_margin: 0.24` pins the bear case to that floor rather than extrapolating below it.
- **Bull upside** is growth-driven: the bull thesis is that the TAM itself is expanding (advanced packaging, 3D-DRAM, geographic fab proliferation) — setting `bull.growth_ceiling: 0.20` allows the bull-case DCF to capture this without being artificially compressed by the 15% base ceiling when consensus is absent.

Unspecified scenario fields fall back to standard ±multiplier per the loader spec.

---

## 7. Historical Reset-and-Recover Priors

| Episode | Drawdown (approx) | Catalyst | Recovery | Lesson |
|---|---|---|---|---|
| 2018–2019 memory downturn | ~−35% peak-to-trough | DRAM/NAND oversupply; Samsung and Micron capex freeze | ~14 months; recovery on 7nm EUV ramp visibility | Memory-cycle resets are severe but time-bounded; the next-node demand catalyst (here: 7nm EUV qualification) is the recovery trigger |
| 2022–2023 post-COVID demand reset + first China export controls | ~−45% peak-to-trough | Inventory digestion; initial US-NL-Japan EUV export-control announcement | ~12 months; recovered to prior highs on AI capex thesis | China-rule announcement created a sharp drawdown but AI infrastructure re-rating overwhelmed it within a year; the recovery speed was highest when the next demand catalyst was already visible |
| 2024 DUV-rule expansion | ~−25% local drawdown | US-NL expanded DUV export-control rules; near-term China revenue ceiling repriced | Partial recovery on pre-cutoff order pull-forward recognition | Export-control tightenings are now modelled by the market as episodic, not one-time; each rule change is priced, partially recovered, and held as a risk premium in the multiple rather than extrapolated linearly |

[Note: episode magnitudes are approximate from general industry knowledge; verify exact drawdown % and dates against price history before citing numerically.]

**Mean-reversion implication:** ASML resets recover faster when the next-node demand catalyst is clearly visible and near-term (e.g., a specific customer node ramp, a confirmed High-NA qualification). Resets during periods of demand uncertainty (2018–2019, mid-2024) take longer. The current cycle-trough environment has a visible catalyst (High-NA ramp, AI capex re-acceleration) but uncertain timing — which is exactly the asymmetry captured in the `confidence_anchor: MEDIUM` override.

Bear scenarios that assume a permanent structural break (China service rules removing the IBM earnings floor, High-NA permanently failing to clear economics) are qualitatively different from cyclical reset scenarios. Historical recovery priors do not apply to structural-break scenarios — those require re-valuing the business at a lower steady-state, not modelling a timed recovery.
