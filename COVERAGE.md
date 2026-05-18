# Coverage

This file lists the tickers that have **specialist coverage** in this skill-pack — meaning a ticker-specific playbook (`playbooks/TICKER.md`) with bespoke evaluation criteria, KPIs, scenario narratives, and overrides for the generic ESTABLISHED / EMERGING defaults.

**The skills will run on any ticker.** Off-coverage tickers fall back to generic ESTABLISHED / EMERGING logic — they get a valid output, just without the ticker-specific depth (capex-cycle position, segment splits, catalyst-aware scenarios, sell-side disagreement axes). Confidence caps at MEDIUM by default for off-coverage runs; users should expect a less informative answer than for a name with a playbook.

The seven names below are the ones currently in scope. The list is deliberately small — see `CHARTER.md` → *Operating Principle — Depth over Breadth* for the reasoning. Adding ticker support is a contribution path (see *Contributing new coverage* below), not a casual edit.

## Currently supported

| Ticker | Stage | AI layer | Investment thesis (one line) | Playbook status |
|---|---|---|---|---|
| **GOOG** | ESTABLISHED | INCUMBENT | Search moat + Cloud growth + YouTube monetisation, with the AI search-disruption question as the central debate | Not yet |
| **META** | ESTABLISHED | INCUMBENT | Family of Apps cash machine + Reality Labs binary option + AI ad-targeting accuracy lift, regulatory overhang as recurring drag | [`playbooks/META.md`](playbooks/META.md) |
| **AMZN** | ESTABLISHED | INCUMBENT | AWS margin trajectory + Ads as third pillar + retail operating leverage, with AI-capex cycle position as the swing factor | Not yet |
| **NVDA** | ESTABLISHED | INFRASTRUCTURE | Data-centre GPU TAM penetration + AI training-to-inference mix shift + customer concentration risk | Not yet |
| **ASML** | ESTABLISHED | INFRASTRUCTURE | EUV monopoly + High-NA ramp + China export-control overhang, with the semiconductor cap-ex cycle as the dominant input | [`playbooks/ASML.md`](playbooks/ASML.md) |
| **NFLX** | ESTABLISHED | APPLICATION | Subscriber growth maturity + ad-tier monetisation + content-cost discipline + password-sharing-crackdown durability | Not yet |
| **ADYEN.AS** | ESTABLISHED | N/A | European unified-payments platform; take-rate stability + EBITDA margin recovery from the 2023 growth reset + cross-border e-commerce share gain, with the European regulatory moat against US incumbents as the durable edge | Not yet |

"Playbook status: Not yet" means the ticker is on the supported list but its `playbooks/TICKER.md` has not been written yet. Remaining playbook authoring tracked in ABA-120 (META done), ABA-117 (GOOG), ABA-122 (AMZN), ABA-121 (NVDA), ABA-116 (ASML), ABA-123 (NFLX), ABA-124 (ADYEN). Loader infrastructure (ABA-112) is complete.

## Playbook structure

Each `playbooks/TICKER.md` encodes:

1. **Business architecture** — segments with revenue / operating-income mix and per-segment growth rates
2. **Capex cycle position** — where in the AI / infrastructure investment arc (ramp / peak / digest / steady) and implications for normalised margin
3. **Active catalysts** — specific named events with probability and IV impact estimates
4. **Sell-side disagreement axes** — the 3–5 real arguments the sell-side is having about this name right now
5. **Failure modes** — what breaks the thesis, and what to monitor
6. **Ticker-specific overrides** — base WACC, growth ceiling, terminal margin, scenario narratives (replacing the generic defaults)
7. **Historical reset-and-recover priors** — past drawdowns and recovery patterns, calibrating mean-reversion expectations

Full file-format and loader spec lives in `DESIGN.md` → *Playbook Layer*. See `playbooks/META.md` for a complete working example.

## Contributing new coverage

The pack is intentionally extensible — if you have a tech ticker you care about that isn't on the list, opening a PR to add specialist support is the encouraged path. A coverage contribution is:

1. **One row added to the table above** — ticker, stage, AI layer, one-line thesis.
2. **One new `playbooks/TICKER.md` file** — written to the structure spec above and `DESIGN.md` → *Playbook Layer*. Frontmatter with the machine-readable overrides, body with the narrative content.
3. **A smoke run** demonstrating that `/stock-signal TICKER` + `/stock-model TICKER` produce coherent output that reflects the playbook's overrides (cap source named, narrative applied, audit trail intact).
4. **One-paragraph rationale in the PR description** explaining why the ticker warrants specialist depth — typically: it's a name you actively hold or evaluate, the generic ESTABLISHED / EMERGING logic produces visibly-wrong outputs on it, or it sits at an interesting boundary case (regional, sector-adjacent, transition-year) that exercises an edge of the methodology.

What does **not** justify adding a ticker:
- Curiosity ("I wonder what META looks like"). Just run the skills generically — the output is fine for that.
- Watchlist breadth for its own sake. The whole point of this design is to **not** be a 1,000-ticker tool.
- Non-tech names — the pack's thresholds, DCF variants, and qualitative overlays are tech-calibrated and will produce confidently-wrong outputs on autos, banks, REITs, etc. See `README.md` → *Scope* for the exclusion list.

If you're unsure whether your candidate fits, open an issue first and discuss the thesis before writing the playbook.

## Removing coverage

Tickers leave coverage when:
- The user (or, if open-sourced, the project maintainer) decides the name no longer warrants depth (acquired, delisted, business model fundamentally changed, lost relevance).
- A playbook has gone stale and no contributor is maintaining it. Stale playbooks are removed rather than carried, because a stale playbook produces silently-wrong overrides — worse than no playbook at all.

Removal is a PR like addition: delete the row, delete the playbook, note the reason in the commit.

## Why these seven specifically

Six of the seven (GOOG, META, AMZN, NVDA, ASML, NFLX) are AI-exposed in some way — incumbent AI deployers, AI infrastructure providers, or AI-enabled application-layer SaaS. The pack's tech-AI focus shows up in the coverage list.

**ADYEN.AS** is the one non-AI-thesis name in the current set. It's included because the project's first contributor (the user) has active European-payments evaluation use cases, and it exercises a different methodology edge (European reporting, payments-infra cycle, euro-denominated FCF) that the generic logic doesn't handle gracefully. It's also the demonstration that the pack isn't only for the FAANG-and-NVDA list — coverage scope is "tech I care about," not "AI-only."

Contributions of other regions, sectors-adjacent-to-tech (fintech, devtools, infra-software), and transition-year names are welcome.
