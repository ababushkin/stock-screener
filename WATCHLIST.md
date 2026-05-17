# Watchlist

The core tech watchlist. These six names get **playbook-grade depth** in `/stock:model` — ticker-specific segment buildups, capex-cycle position, catalyst-aware scenarios, sell-side disagreement axes, ticker-specific WACC/growth/margin overrides, and failure-mode monitoring.

Off-watchlist tickers fall back to generic ESTABLISHED / EMERGING logic. That's a deliberate cost: we are not optimising for breadth.

See `CLAUDE.md` → "Operating principle — depth over breadth" for why.

## The seven

| Ticker | Stage | AI layer | Investment thesis (one line) | Playbook status |
|---|---|---|---|---|
| **GOOG** | ESTABLISHED | INCUMBENT | Search moat + Cloud growth + YouTube monetisation, with the AI search-disruption question as the central debate | Not yet |
| **META** | ESTABLISHED | INCUMBENT | Family of Apps cash machine + Reality Labs binary option + AI ad-targeting accuracy lift, regulatory overhang as recurring drag | Not yet |
| **AMZN** | ESTABLISHED | INCUMBENT | AWS margin trajectory + Ads as third pillar + retail operating leverage, with AI-capex cycle position as the swing factor | Not yet |
| **NVDA** | ESTABLISHED | INFRASTRUCTURE | Data-centre GPU TAM penetration + AI training-to-inference mix shift + customer concentration risk | Not yet |
| **ASML** | ESTABLISHED | INFRASTRUCTURE | EUV monopoly + High-NA ramp + China export-control overhang, with the semiconductor cap-ex cycle as the dominant input | Not yet |
| **NFLX** | ESTABLISHED | APPLICATION | Subscriber growth maturity + ad-tier monetisation + content-cost discipline + password-sharing-crackdown durability | Not yet |
| **ADYEN.AS** | ESTABLISHED | N/A | European unified-payments platform; take-rate stability + EBITDA margin recovery from the 2023 growth reset + cross-border e-commerce share gain, with the European regulatory moat against US incumbents as the durable edge | Not yet |

## Playbook structure (target)

Each `playbooks/TICKER.md` should encode:

1. **Business architecture** — segments with revenue/operating-income mix and per-segment growth rates
2. **Capex cycle position** — where in the AI/infrastructure investment arc (ramp / peak / digest / steady) and implications for normalised margin
3. **Active catalysts** — specific named events with probability and IV impact estimates
4. **Sell-side disagreement axes** — the 3-5 real arguments the sell-side is having about this name right now
5. **Failure modes** — what breaks the thesis, and what to monitor
6. **Ticker-specific overrides** — base WACC, growth ceiling, terminal margin, scenario narratives (replacing the generic defaults)
7. **Historical reset-and-recover priors** — past drawdowns and recovery patterns, calibrating mean-reversion expectations

## Sequencing

Playbooks unlock depth, but only after the foundation is honest:

- **ABA-110** (SBC strip) and **ABA-111** (growth-rate ceiling) — must land first; playbook overrides on top of broken base = noise on top of bias
- **ABA-NEXT** (playbook loader) — infrastructure for `/stock:model` to load `playbooks/TICKER.md` when present
- Then: six playbook tickets, one per watchlist name. Each is a discrete artifact, ~1-2 days of research + write-up.

## Composition notes

Six of the seven names (GOOG, META, AMZN, NVDA, ASML, NFLX) are AI-exposed in some way — incumbent AI deployers, AI infrastructure providers, or AI-enabled application-layer SaaS. The watchlist is fundamentally an AI-tech specialist book.

**ADYEN.AS is the deliberate non-AI tech name** on the list, included for cycle and geographic diversification: European exposure, payments-infrastructure cycle (uncorrelated with the AI capex cycle), euro-denominated revenue. Its AI layer is `N/A` — Adyen's internal ML (fraud detection, risk scoring) is operational rather than customer-facing or revenue-driving. If the AI thesis on the other six names mean-reverts hard, ADYEN is the diversifier expected to absorb less of the drawdown.

## Adding / removing tickers

Watchlist changes are deliberate, not casual. Discuss before editing. The whole point is focus.
