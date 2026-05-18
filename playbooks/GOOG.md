---
ticker: GOOG
last_updated: 2026-05-18
base_wacc: 9.0
growth_ceiling: 0.13
terminal_margin: 0.30
confidence_anchor: MEDIUM
bear_narrative: "Interface displacement + cost-permanent: AI-native assistants capture commercial-intent query share, revenue-per-search compresses as ad density and CPC (Cost Per Click) fall, and AI serving costs remain structurally elevated. Terminal margin anchors to low-20s; long-run earnings growth converges to low single digits."
base_narrative: "Cost-temporary, monetisation-resilient: AI Overviews and AI Mode keep users inside Google surfaces; capex-to-revenue ratio mean-reverts post-2027 as model efficiency improves; Cloud (GCP) margin expands toward mid-20s. Terminal margin recovers to ~30% SBC (Stock-Based Compensation)-stripped FCF (Free Cash Flow) basis as the AI build-cycle normalises."
bull_narrative: "AI amplifier: Gemini integration lifts Search monetisation density; GCP TPU/Vertex stack creates durable economic differentiation vs. AWS/Azure; Waymo and Other Bets optionality matures. Growth ceiling reaches 18%; terminal margin expands above base as operating leverage reasserts."
failure_modes:
  - "Interface displacement (structural): Multi-quarter monotonic migration of commercial-intent queries to AI-native interfaces — invalidates base revenue growth assumption. [interface layer]"
  - "Monetisation compression (structural): AI Overview / AI Mode rollout compresses revenue-per-search durably; ad density and CPC (Cost Per Click) decline in parallel. [monetisation layer]"
  - "Cost disruption (structural): AI capex/revenue ratio stays elevated beyond 2028 with no margin recovery — terminal margin re-anchors permanently at TTM-distressed levels. [cost layer]"
  - "Distribution remedy: DOJ remedies impair default-placement economics materially (Chrome divestiture, payments-for-default banned, AdTech (Advertising Technology) structural separation). [ecosystem layer]"
  - "Cloud commoditisation: GCP margins fail to expand durably above mid-teens by 2027 — eliminates the optionality embedded in the base case. [ecosystem layer]"
  - "Geo-regulatory contagion: EU DMA (Digital Markets Act) / India / other-jurisdiction remedies replicate US distribution-economics erosion outside the US market. [ecosystem layer]"
scenario_axes:
  bear:
    growth_ceiling: 0.04
    terminal_margin: 0.22
  bull:
    growth_ceiling: 0.18
    terminal_margin: 0.32
---

# GOOG Playbook

**Coverage status:** ESTABLISHED · INCUMBENT  
**Thesis in one line:** AI-search-disruption debate + DOJ distribution-economics remedies + AI capex cost-permanence question — three structurally intertwined uncertainties that generic INCUMBENT/ESTABLISHED defaults cannot price.

---

## 1. Business Architecture

### Segment mix (approximate FY2025 basis)

| Segment | Revenue share | Growth trajectory |
|---|---|---|
| Google Search & Other | ~57% | Low-to-mid single digits; AI disruption is the structural risk |
| YouTube Ads | ~11% | Mid-teens; subscription (YouTube Premium) adds a recurring layer |
| Google Network (AdSense / AdMob / DV360) | ~9% | Declining; programmatic ad-tech under AdTech regulatory scrutiny |
| Google Cloud (GCP + Workspace) | ~13% | ~28–30% YoY; becoming the second material earnings contributor |
| Google Other (Pixel, Play, Maps, subscriptions) | ~5% | Mid-single digits; hardware margins thin |
| Other Bets (Waymo, Verily, etc.) | ~1% | R&D-stage; not meaningful to near-term FCF |

**Revenue driver mechanics:**

1. **Search:** Paid clicks × CPC (Cost Per Click). Absolute quarterly Search CPM (Cost Per Thousand Impressions) and click volumes are not disclosed by Alphabet (noted as OQ6 gap in the engagement-KPI map) — revenue-per-search trend is inferred from total Search & Other revenue YoY, not directly observable. This limits the precision of monetisation-compression monitoring; the playbook does not attempt quarterly KPI tracking.

2. **YouTube:** Primarily video ad auction (CPM-based); YouTube Premium subs add a lower-variance recurring line. Ad load and engagement trends are disclosed directionally but not with unit-economics granularity.

3. **Cloud:** Committed GCP revenue backlog + Workspace seats. Backlog growth is disclosed quarterly; it is the leading indicator for Cloud revenue trajectory.

4. **Other Bets:** Waymo is the only Other Bets asset with a plausible near-term monetisation path (robotaxi per-mile revenue, fleet licensing). Not material to DCF (Discounted Cash Flow) in the base case.

### End-market exposure

- **Digital advertising (~77% of revenue):** Cyclical sensitivity to global ad-spend budgets; secular tail risk from AI-interface displacement.
- **Enterprise cloud (~13% of revenue):** GCP + Workspace; less cyclical; differentiated through Gemini integration.
- **Hardware / consumer services (~5%):** Pixel, Google One, Maps API — limited operating leverage.

---

## 2. AI Investment Cycle Position

Alphabet spent ~$91B in FY2025 capex, ~70% AI-attributed per public guidance. This depresses TTM clean FCF margin and creates a two-sided uncertainty that is structurally different from a normal capex cycle trough: the normalisation path depends on **which of two competing margin theses proves correct.**

**Path A — cost-temporary (base case):**  
AI model efficiency improves on hardware and software curves (inference cost-per-query falls as TPUs scale and model compression matures). Capex-as-share-of-revenue mean-reverts post-2027 as the build phase completes. Monetisation density per AI-assisted query holds near current levels or improves (AI Overviews maintain ad slots; AI Mode monetises at comparable RPM (Revenue Per Mille) to standard Search). Terminal margin recovers toward 30% SBC-stripped FCF.

**Path B — cost-permanent (bear-case terminal margin thesis):**  
AI serving costs do not decay with scale at the rate Path A assumes — either because competitive pressure forces continued reinvestment, or because each AI query is structurally more compute-intensive than a traditional lookup. Simultaneously, AI-style answering reduces click-through rates, compressing ad density and CPC. Revenue growth decelerates while cost stays elevated. Terminal margin stabilises in the low-20s. This is the basis for `scenario_axes.bear.terminal_margin: 0.22`.

**Base-case choice:** The playbook picks Path A but does not assume the asymmetry away. The `terminal_margin` base of 30% reflects Path A prevailing. The bear `scenario_axes` captures Path B as a discrete scenario — not a symmetric delta from base — because interface displacement and cost-permanence cause joint compression of both growth and margin simultaneously, which a symmetric ±multiplier cannot represent.

**AI-capex normalisation signal:** The evidence-gating condition for Path A is a sustained decline in capex/revenue ratio after FY2026, visible across two consecutive annual periods. A ratio that re-elevates above FY2025 levels by FY2028 would be evidence for Path B.

---

## 3. Active Catalysts

| Catalyst | Probability | IV impact | Direction |
|---|---|---|---|
| DOJ Search remedies finalised (default-payment restrictions, Chrome leverage, or divestiture ordered) | ~35% material remedy by end-2027 | −10–20% | Strongly negative — distribution economics impaired |
| AI Mode Search query-mix data disclosed showing CPC stability | ~40% by end-2026 | +5–10% | Positive — monetisation-compression bear case weakened |
| GCP margin print sustains above 15% for 2+ consecutive quarters | ~55% by end-2027 | +5–8% | Positive — Cloud-as-earnings-contributor thesis validated |
| Gemini consumer adoption milestone (measurable first-place-I-ask share shift, third-party data) | ~30% by end-2027 | +3–7% | Positive — platform-lock thesis reinforced |
| AdTech structural separation ruling (forced unwind of ad-exchange vertical integration) | ~25% | −8–15% | Negative — Network segment economics impaired |
| AI-native interface (ChatGPT / Perplexity / Claude) captures measurable commercial-intent query share (3rd-party panel data, sustained 2+ quarters) | ~30% by end-2027 | −15–25% | Strongly negative — interface-displacement thesis fires |
| Waymo monetisation milestone (revenue-generating fleet in 3+ cities at scale) | ~40% by end-2027 | +2–5% | Modest positive — Other Bets optionality partially realised |
| Capex/revenue ratio trajectory: FY2027 < FY2026 for two consecutive years | ~50% | +8–12% | Positive — Path A confirmed, terminal-margin re-rate |

---

## 4. Sell-Side Disagreement Axes

Organised by the **4-layer AI-disruption taxonomy** plus Cloud differentiation. Each axis names what distinguishes temporary noise from structural change.

### (i) Interface disruption

**The question:** Do AI assistants become the primary discovery and navigation layer, displacing Google Search as the first-place-I-ask interface for high-intent commercial queries?

- **Bull:** AI Overviews and AI Mode keep users inside Google surfaces for the queries that generate ad revenue; "where do you start a purchase or research query" surveys remain Google-dominant. Competitors capture curiosity and informational queries, not commercial-intent ones.
- **Bear:** AI-native interfaces (ChatGPT, Perplexity, Claude, in-OS assistants, browser-native AI) capture meaningful share of commercial-intent queries — the queries that actually produce CPC revenue. Users who stop clicking to Google for high-intent searches stop generating ad impressions entirely.
- **Noise vs. structural:** A single-quarter deceleration in Search revenue growth is noise — ad-cycle effects, macro, seasonality, and mix-shift within Search all produce this. Structural signal requires: monotonic commercial-intent query-share migration **sustained across ≥3 quarters**; "first-place-I-ask" data from third-party consumer panels showing a durable shift (not curiosity queries — specifically purchase-research, product-comparison, local-service-intent); revenue-per-search trend declining even in periods of macro-stable ad spend. All three together constitute structural signal; any one alone is insufficient.

### (ii) Monetisation compression

**The question:** Even at stable Search query share, does AI-style answering structurally compress revenue-per-search — via fewer ad slots per query, reduced click-through, or lower CPC?

- **Bull:** AI Overviews maintain or improve revenue-per-search through better ad-intent matching; users who get AI answers and then click on ads are higher-intent buyers; blended RPM (Revenue Per Mille) holds or expands.
- **Bear:** AI summaries satisfy the user's need without a click; ad slot count per query falls as above-the-fold content becomes AI-generated; CPC compresses as advertiser competition for fewer slots declines.
- **Noise vs. structural:** Revenue-per-search trend over ≥2 quarters, filtered against macro ad-cycle movements by comparing to peer ad platforms (Meta, Snap, Pinterest) at the same periods. A revenue-per-search decline that tracks macro peers is cycle noise; one that diverges negatively from peers while the macro environment is stable is monetisation-compression signal. Absolute click volumes and CPM are not disclosed (OQ6 gap), so the observable proxy is total Search revenue growth rate relative to peer ad-platform growth rates.

### (iii) Cost disruption

**The question:** Does AI inference cost remain structurally elevated, preventing margin recovery even if Search revenue holds?

- **Bull:** Inference cost-per-query declines on TPU hardware scaling and model-efficiency curves (distillation, quantisation, smaller purpose-built models); capex/revenue mean-reverts post-2027; operating leverage reasserts as fixed-cost build phase completes.
- **Bear:** AI serving cost is a permanent elevated line item — each AI query is computationally costlier than a keyword lookup by a structurally different order of magnitude; competitive pressure forces continued reinvestment to match quality; the cost-efficiency gains are real but are competed away in the form of better product rather than margin expansion.
- **Noise vs. structural:** Capex/revenue ratio trend post-FY2026 across two consecutive annual periods. A ratio that declines from FY2025 peak toward pre-AI levels (≤15% of revenue) is Path A signal. A ratio that stabilises above 18% of revenue through FY2028 is Path B signal. Gross-margin segmentation data (if and when disclosed at the Cloud or AI-products segment level) would be the most direct evidence but is not currently available.

### (iv) Ecosystem and distribution displacement

**The question:** Does regulatory and competitive erosion of Google's distribution advantages structurally weaken the default-placement economics that underpin Search market share?

- **Bull:** Distribution moats hold: Chrome browser default-search leverage continues, Apple default-search-engine payment (~$18–20B/year, market estimate) survives legal scrutiny in modified form, Android OEM agreements sustain Google's first-call position. Regulatory remedies stay at the margins (conduct rules, not structural separation).
- **Bear:** DOJ remedies materially weaken default-placement economics — payments-for-default restricted or banned, Chrome divested or usage-gated, Android default-app leverage limited. Independent of which specific remedy is imposed: the structural question is whether Google's distribution advantages durably erode. An ecosystem-level erosion would move Search market share on a multi-year lag, not immediately — making it a slow-burn bear case, not a binary one.
- **Noise vs. structural:** Actual remedies imposed (with material appeals exhausted, not just initial rulings); third-party measurement of default-search-engine market share in the 12–24 months post-remedy implementation. Court rulings that are appealed and do not result in operational changes are procedural noise; operational changes to the Chrome default or the Apple TAC (Traffic Acquisition Cost) payment are structural signal.

### (v) Cloud differentiation

**The question:** Is GCP developing durable economic differentiation, or participating in a capital-intensive AI infrastructure cycle where margins normalise to mid-cycle hyperscaler economics?

- **Bull:** TPU + Vertex AI + Gemini-on-Cloud create a stack-level differentiation that justifies sustained pricing power; enterprise customers building Gemini-powered workflows create switching-cost stickiness analogous to AWS-native application lock-in; GCP margin expands sustainably toward AWS/Azure levels (high-20s to low-30s).
- **Bear:** GCP participates in the AI capex cycle as a capacity provider, but without the enterprise-grade trust, developer ecosystem depth, or data-gravity advantages of AWS or Azure; margins normalise to mid-cycle hyperscaler economics (mid-teens); GCP is a strategic hedge for Alphabet but does not compensate for Search revenue risk.
- **Noise vs. structural:** GCP operating margin trajectory reported across ≥4 consecutive quarters at scale; pricing power signals from renewal rate commentary and enterprise customer-mix data (disclosed intermittently). GCP margins below 15% by FY2027 would weaken the base-case Cloud offset; margins expanding above 20% by FY2027 would strengthen the bull case.

---

## 5. Failure Modes

These are the thesis-breaking scenarios that the DCF does not capture because they are discrete structural shifts rather than smooth-curve adjustments:

- **Interface displacement (structural):** Multi-quarter monotonic migration of commercial-intent queries to AI-native interfaces — invalidates the base revenue growth assumption. This is the failure mode that does not have a historical analogue in Alphabet's operating history: prior Search challengers (Bing, Yahoo relaunch) did not change user behaviour at the interface layer; AI assistants potentially do. [interface layer]

- **Monetisation compression (structural):** AI Overview and AI Mode rollout compresses revenue-per-search durably; ad density falls as AI summaries occupy above-the-fold positions; CPC declines as advertiser competition for fewer slots decreases. This failure mode can coexist with stable query volumes — making it harder to detect via search share data alone. [monetisation layer]

- **Cost disruption (structural):** AI capex/revenue ratio stays elevated beyond FY2028 with no margin recovery. In conjunction with monetisation compression, this produces joint revenue-and-margin pressure — the scenario captured by `scenario_axes.bear` compressing both `growth_ceiling` and `terminal_margin` simultaneously. [cost layer]

- **Distribution remedy:** DOJ remedies impair default-placement economics materially. The specific form matters less than the functional outcome: if Google cannot pay for or mandate default Search placement in Chrome, Android, and Apple Safari, the structural query-share floor is removed. Independent of any single ruling's outcome — the structural impairment of distribution economics is the failure condition, not the legal calendar. [ecosystem layer]

- **Cloud commoditisation:** GCP margins fail to expand durably above mid-teens by FY2027. This eliminates the optionality embedded in the base case — the assumption that Cloud eventually becomes a material second earnings engine that partially offsets Search risk. If GCP remains a mid-margin business, the base case requires Search to sustain its current earnings contribution with no structural offset. [ecosystem layer]

- **Geo-regulatory contagion:** EU DMA, India CCI, and other-jurisdiction remedies replicate the distribution-economics erosion pattern outside the US market. The US DOJ case creates a precedent and negotiating template; a coordinated multi-jurisdiction wave of structural remedies could impair non-US revenue streams that are not currently in the bear-case model. [ecosystem layer]

---

## 6. Ticker-Specific Overrides (Rationale)

| Field | Value | Rationale |
|---|---|---|
| `base_wacc` | 9.0% | US 10y ~4.5% + Beta ~1.05 × 5.5% ERP (Equity Risk Premium) ≈ 10.3%. Less ~1.0pp moat-durability discount (dominant Search economics + Cloud share gains remain intact today). Plus ~0.3pp regulatory premium (active DOJ remedies + AdTech + EU DMA + jurisdictional contagion risk). Sits at META parity (9.0%) rather than ASML monopoly level (8.5%) — Search durability is a live contested thesis, unlike ASML's EUV monopoly which has no credible near-term challenger. |
| `growth_ceiling` | 13% | Fallback ceiling when `eps_growth_5y` is unavailable (current state per yfinance MCP). Below the generic 18% INCUMBENT default because: (a) $4.7T mega-cap mathematics constrain absolute growth, (b) Search (~57% of revenue) grows at ~5–7% and is the dominant segment, (c) Cloud (~13% of revenue) grows at ~28–30% but is not yet large enough to move the blended rate materially. Consensus `eps_growth_5y` takes precedence when populated; this override is the floor/ceiling for the fallback path only. |
| `terminal_margin` | 30% | SBC-stripped FCF margin assuming Path A (cost-temporary) prevails. TTM clean margin is depressed by the AI build cycle. 30% sits between Search-segment-implied margin and capex-blended group margin — a defensible mid-range under the cost-temporary path. Path B (cost-permanent) downside is held discretely in `scenario_axes.bear.terminal_margin: 0.22`, not absorbed into the base value. Without `scenario_axes`, a 30% base-case terminal margin would be overconfident; with it, the base stays clean and the structural asymmetry is priced in the bear DCF. |
| `confidence_anchor` | MEDIUM | The AI-disruption thesis spans four distinct structural questions (interface / monetisation / cost / ecosystem) that cannot be resolved from current financials. MCP data quality is adequate (4y FCF (Free Cash Flow), SBC, diluted shares present); LOW would be too pessimistic on data quality grounds. Structural-behavioural uncertainty is what caps confidence, not data availability. Below META's HIGH because META's central debate (regulatory) is discrete and binary; GOOG's central debate (interface displacement) is continuous, multi-modal, and decision-relevant in the base case, not just in tail scenarios. |

### `scenario_axes` design rationale

Standard ±multiplier scenarios would produce symmetric bear/bull deltas from the base. GOOG's thesis is structurally asymmetric in a way that requires explicit overrides on both dimensions simultaneously:

- **Bear case:** Interface displacement causes **joint** compression of growth ceiling (query share migrates) and terminal margin (monetisation compresses + costs stay elevated). A symmetric −5pp terminal-margin delta off 30% (i.e., 25%) understates the joint structural-break shape. `bear.growth_ceiling: 0.04` anchors below the symmetric multiplier because the bear case is not a cycle trough — it is an interface-layer shift where EPS growth converges toward low single digits. `bear.terminal_margin: 0.22` sits below the TTM-clean FCF margin to reflect the joint structural break, not a recoverable cycle compression.

- **Bull case:** The bull thesis is monetisation-density improvement + Cloud acceleration. `bull.growth_ceiling: 0.18` matches the upper bound of pre-AI-discount consensus and allows the bull-case DCF to capture upside without being artificially compressed by the 13% fallback. `bull.terminal_margin: 0.32` is a modest above-base anchor for the scenario where Path A delivers cleanly and AI Overviews monetise at parity to current Search.

Unspecified scenario fields fall back to standard ±multiplier per the loader spec.

---

## 7. Historical Reset-and-Recover Priors

| Episode | Drawdown (approx) | Catalyst | Recovery | Lesson |
|---|---|---|---|---|
| 2022 ad recession + iOS privacy reset | ~−45% peak-to-trough | Macro ad-spend contraction; Apple ATT (App Tracking Transparency) headwinds to ad-targeting quality | ~12 months; recovery on ad-market rebound and YouTube brand-advertiser return | Cyclical ad recessions recover on macro normalisation; the underlying monetisation mechanics remained intact throughout |
| 2023 Bing + ChatGPT integration scare | ~−15% drawdown | Microsoft integrated GPT-4 into Bing; sell-side concern about Search displacement | ~6 months; recovered as Bing share gains remained marginal and Google announced Bard/Gemini roadmap | A credible competitive interface challenge caused a multiple de-rate, but was not sufficient to structurally impair query economics at the monetisation layer |
| 2024–2025 DOJ verdict + AI-Mode launch uncertainty | ~−20–25% drawdown (approximate) | DOJ liability finding in Search distribution case; uncertainty around AI Mode cannibalising Search RPM (Revenue Per Mille) | Partial recovery as AI Overviews maintained revenue-per-search in initial disclosed metrics | Regulatory headline risk creates an IV-expansion event; recovery pace correlated with whether monetisation metrics held in the quarters following the ruling |

[Note: episode drawdown magnitudes and recovery durations are approximate; verify against price history before citing numerically.]

**Mean-reversion implication:** Prior episodes where Google experienced sharp drawdowns and recovered shared a common structural condition: user behaviour at the **Search query layer remained intact**. Ad-cycle recessions compressed revenue per query temporarily; Bing integration scared the multiple but did not move query-source share durably; DOJ rulings de-rated the distribution-moat premium but did not change where users began high-intent searches.

**Structural caveat:** These priors apply only when the query-origination behaviour is structurally stable. If Search query share migrates because users adopt AI assistants as their primary discovery layer — the interface-displacement failure mode — the historical mean-reversion priors do not apply. The recovery mechanism in prior episodes was mean-reverting ad economics, not mean-reverting user behaviour. Interface displacement would break the recovery mechanism itself: there is no historical precedent for Google recovering from durable query-origination share loss to a competing interface. The 2023 Bing episode is the closest analogue, and its resolution (Bing share gains marginalised) cannot be reliably extrapolated to a scenario where AI assistants are natively integrated at the OS, browser, and search-bar level at scale.
