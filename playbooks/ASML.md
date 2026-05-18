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
  - "Structural customer concentration in leading-edge EUV (TSMC + Samsung + Intel for logic; SK Hynix + Micron for memory) — any single major customer delaying a node, cancelling capex, or extending a digestion phase moves IV materially [TODO: verify exact top-3/top-5 % against latest ASML 20-F / annual report risk-factor disclosure]"
  - "China export controls broadened to service/spare-parts of installed DUV base — would damage the most defensive component of ASML's cash flow (services + installed-base management)"
  - "High-NA cost-per-wafer fails to clear vs multi-patterning DUV at scale — slows customer adoption and breaks the post-2027 unit-volume growth premise"
  - "Broad-based semi capex air-pocket — mobile (smartphone unit weakness), memory (DRAM/NAND oversupply cycle), or mature-node (industrial / auto demand normalisation) downturn overlapping with leading-edge digestion compresses revenue across all segments at once"
  - "Reported FCF heavily distorted by customer prepayments — using TTM FCF as base year produces misleading CAGRs in either direction without working-capital normalisation"
  - "Persistent EUR/USD strengthening reduces translated revenue and earnings even with a stable underlying EUR-denominated business"
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

The real arguments the sell-side is having on ASML right now:

1. **Capex-cycle trough timing:** Does the cycle trough in H2 2026 and re-accelerate in 2027, or is the digestion period deeper and longer (into 2027–2028) given memory oversupply and smartphone demand weakness? Bulls model a sharp V-shaped inflection; bears model a prolonged L-shaped digestion. This is the single largest source of 12-month price-target dispersion.

2. **High-NA economics at scale:** Will High-NA cost-per-wafer clear the threshold where customers prefer it to multi-patterning DUV at volume? Bulls cite TSMC's public endorsement and Intel's production commitments. Bears note that High-NA tools are €350M+ each, early yield data is opaque, and multi-patterning DUV (using multiple cheaper tools) remains a credible alternative for all but the most leading-edge nodes.

3. **China revenue durability:** Is 15–20% China revenue a stable floor under the current export-control framework, or will progressive rule-tightening (especially to DUV service/spare-parts) erode it further? The sell-side range on China's 2027 revenue contribution spans roughly 8–22% — a wide disagreement that drives meaningful valuation divergence.

4. **TAM ceiling — real or expandable?** ASML's own LRP (Long-Range Plan) implies ~$28B advanced-logic equipment TAM at ~86% EUV penetration. Is this a hard ceiling (the stock is penetration-limited, not share-limited), or is the TAM itself expanding via: (a) 3D-DRAM and multi-layer NAND raising EUV intensity per wafer, (b) advanced packaging (HBM stacks, glass substrates, chiplets) requiring new litho steps, (c) geographic fab proliferation (US, Japan, Europe) adding new customer relationships? Bulls argue the TAM is dynamic; bears argue the LRP already captures it.

5. **IBM (services) growth as the moat anchor:** Is Installed Base Management (IBM) a durable ~25% revenue floor that grows with the installed base regardless of cycle, or is it more exposed to cycle risk than consensus assumes (specifically: customer utilisation drops reduce upgrade spend; China service restrictions reduce the addressable installed base)? Bears who challenge the IBM floor are implicitly challenging the "earnings-floor" thesis that underpins the MEDIUM confidence anchor.

---

## 5. Failure Modes

These are the thesis-breaking scenarios that the DCF does not capture because they are discrete rather than smooth:

- **Customer concentration shock:** TSMC + Samsung + Intel represent the dominant share of EUV system revenue. [TODO: verify exact % against latest 20-F] A single customer deferrring a node by 12+ months or announcing a major capex freeze moves ASML's near-term revenue by a multiple of consensus expectations. This is not a gradual risk — it is a lumpy, concentrated exposure.

- **China service/spare-parts export controls:** Current restrictions primarily cover new EUV and advanced DUV system sales. If rules extend to servicing or supplying spare parts to the existing DUV installed base in China, ASML's most cycle-resistant revenue stream is impaired. This would be the bear case's "earnings-floor-removal" event — the scenario where the business becomes more cyclical than the base case assumes.

- **High-NA economics failure:** High-NA adoption depends on cost-per-wafer clearing the threshold where customers prefer it to multi-patterning DUV. If High-NA tool yields remain low, learning curves are steeper than expected, or customer process engineers can't close the cost equation, adoption slows. This breaks the post-2027 unit-volume and ASP expansion thesis simultaneously — the two largest contributors to LRP upper-bound revenue.

- **Broad capex air-pocket (multi-segment, simultaneous):** The bear case is NOT "AI investment pauses." The more dangerous scenario is a broad-based semi downturn overlapping across memory (DRAM/NAND oversupply), mobile (smartphone unit weakness), and mature-node (industrial / auto demand normalisation) segments at once. In this scenario, even IBM service revenue is pressured by customer utilisation declines, and ASML's financial performance is worse than any single-segment stress model predicts.

- **FCF distortion from customer prepayments:** ASML's reported FCF is significantly affected by customer prepayment timing. In strong-order years, prepayments boost FCF above earnings; in weak-order years, the reverse. Using any single-year TTM FCF as a DCF anchor without working-capital normalisation produces misleading base-year CAGRs. The `terminal_margin` override partially mitigates this by anchoring on a normalised steady-state rather than TTM, but the Y1 FCF used in the DCF can still be distorted.

- **EUR/USD strengthening:** ASML reports in EUR. Persistent EUR appreciation against USD reduces translated revenue and EPS for US-listed ADR investors (ASML US), even with no change in the underlying business. Because the customer base (TSMC, Samsung, SK Hynix, Micron) operates in USD-denominated capital markets, ASML's competitive position is unaffected by FX — but the P&L in USD terms is sensitive.

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
