---
name: stock:model
description: DCF/valuation model for a tech stock. Invoked as `/stock:model TICKER`. Walking-skeleton v1 implements only the upstream-context gate — it refuses to proceed unless a `SIGNAL OUTPUT` block for the same ticker is present earlier in the conversation, instructing the user to run `/stock:signal TICKER` first. Full DCF lands in ABA-31 (ESTABLISHED path) and ABA-34 (EMERGING path). Use whenever the user asks for an intrinsic value, fair-value range, DCF, or "what's it worth" on a ticker.
---

# Model — DCF & Intrinsic Value

**Command:** `/stock:model TICKER`
**Purpose (v1 walking skeleton):** Enforce the upstream-context contract — `/stock:model` only runs after `/stock:signal` has produced a SIGNAL OUTPUT block in the same session. Full DCF logic lands in ABA-31 / ABA-34.

---

## 1. Identity

- **Skill name:** stock:model
- **Command:** `/stock:model TICKER`
- **Purpose (v1):** Walking-skeleton gate. Verify the upstream Signal context is present and well-formed; refuse with a clear remediation message if not. No DCF, no output block, no JSON merge yet — those land in follow-up issues.

---

## 2. Why a context gate

Model is downstream of Signal: it consumes the profit-stage classification, clean EPS, AI layer, and MODEL_READY flag that Signal produces. Running `/stock:model` without first running `/stock:signal` would force this skill to either re-derive those inputs (duplicating Signal's MCP calls and methodology) or fabricate them (silently wrong). The gate enforces the contract — Signal first, Model second.

This stub implements only the gate. It is the smallest end-to-end shape that future DCF work (ABA-31, ABA-34) can plug into without rework.

---

## 3. Execution Phases

### GATHER

1. Parse the ticker from the command argument. Uppercase it (e.g. `nvda` → `NVDA`). If blank, refuse immediately with: "Usage: `/stock:model TICKER`".

### GATE — Check for upstream Signal output

Scan the current conversation context (the messages above this invocation) for a `SIGNAL OUTPUT` block. A valid block:

- Contains the literal header `SIGNAL OUTPUT` (matching how `/stock:signal` emits it)
- Has a `Ticker:` line whose value matches the requested ticker (uppercase comparison)
- Has a `MODEL_READY:` line (any value — `YES`, `CONDITIONAL`, or `NO`; gate does not yet branch on this in v1)

**If no SIGNAL OUTPUT block is present in context, or the block is for a different ticker:**

Refuse with exactly this message (substituting the requested ticker):

> `/stock:model TICKER` requires a SIGNAL OUTPUT block in context. Please run `/stock:signal TICKER` first, then re-run `/stock:model TICKER` in the same session.

The literal phrase **"run `/stock:signal TICKER` first"** (with TICKER substituted) MUST appear in the refusal — it is the acceptance criterion for this issue (ABA-30) and is verified by the smoke check.

Do not proceed past this step. Do not call any MCP tool. Do not write any file.

**If a valid SIGNAL OUTPUT block is present in context for the requested ticker:**

Acknowledge that the gate has passed and state that full DCF / intrinsic-value computation is not yet implemented. Use this template:

> Gate passed: SIGNAL OUTPUT for TICKER found in context (verdict=VERDICT, MODEL_READY=READY_FLAG).
> Full Model logic (DCF for ESTABLISHED, alternative path for EMERGING) is not yet implemented — see ABA-31 and ABA-34. No report file written in v1.

Substitute TICKER, VERDICT (the Signal verdict — BUY/WATCH/CAUTION) and READY_FLAG (the MODEL_READY value) from the upstream block.

### COMPUTE / THRESHOLD / OVERRIDE / OUTPUT

**Not implemented in v1.**

- DCF inputs, scenarios, and intrinsic-value computation land in [ABA-31](https://linear.app/ababushkin/issue/ABA-31) (ESTABLISHED path).
- EMERGING-path alternative (no-DCF valuation framework — likely reverse-DCF or revenue-multiple range) lands in [ABA-34](https://linear.app/ababushkin/issue/ABA-34).
- Output block, JSON merge into `reports/TICKER_YYYYMMDD.json` under `stages.model`, and confidence rules are all out of scope for v1.

When those issues land, this section will be filled in following the pattern in `skills/signal/SKILL.md` and `skills/screen/SKILL.md`. The gate in this file remains the entry point.

---

## 4. Common rationalisations to pre-rebut

| Rationalisation | Counter |
|---|---|
| "The user asked for a model, I should produce *some* valuation rather than refuse." | The gate exists precisely to prevent this. Producing a fabricated valuation is worse than refusing — it gives the user a confident-looking number with no methodology behind it. Refuse and instruct. |
| "I can see the ticker; I'll just run the Signal logic inline and then the Model logic." | Two skills, two responsibilities. Inlining Signal here duplicates methodology and bypasses the JSON merge contract that downstream consumers (UI, screen reports) depend on. Refuse and instruct. |
| "There's a `reports/TICKER_YYYYMMDD.json` with a `stages.signal` block — that should count as upstream context." | Not in v1. The gate checks the conversation context, not the filesystem. The user may have run Signal in a different session days ago and the underlying data may be stale. Refuse and instruct the user to re-run Signal in the current session. (A future iteration may extend the gate to accept fresh on-disk reports — that is an ABA-31 design call, not a v1 concern.) |
| "The SIGNAL OUTPUT block is for a different ticker but it has useful classification info." | Tickers are not fungible. A SIGNAL OUTPUT for META tells you nothing about NVDA's profit stage or AI layer. Refuse and instruct. |
| "MODEL_READY is NO so I should refuse with a different message." | v1 gate does not branch on MODEL_READY. Pass the gate, then let the (future) downstream logic decide whether to proceed, abort, or produce a CONDITIONAL output. Recording MODEL_READY in the acknowledgement is enough. |
| "A DCF input is null — I'll assume a reasonable default (WACC 10%, terminal growth 3%, …)" | Forbidden. Per the Manual Input Protocol (`skills/_shared/MANUAL_INPUT_PROTOCOL.md`), when any DCF input cannot be derived from MCP data the skill MUST ask the user via a grouped paste-in (this fires in the downstream DCF logic tracked in ABA-31/ABA-34, not in the v1 stub). Defaults are fabrication once written to JSON. |

---

## 5. Acceptance criteria (this issue — ABA-30)

This walking-skeleton stub is done when:

1. **No upstream Signal in context →** invoking `/stock:model NVDA` returns a refusal message containing the literal phrase **`run /stock:signal NVDA first`** (case-sensitive, with the requested ticker substituted).
2. **Valid SIGNAL OUTPUT block in context for the requested ticker →** invoking `/stock:model NVDA` proceeds past the gate and emits the "Gate passed" acknowledgement, naming the verdict and MODEL_READY value from the upstream block.
3. **Mismatched ticker** (SIGNAL OUTPUT for META, request for NVDA) → treated as "no upstream Signal in context" — same refusal message, substituting the requested ticker (NVDA).

DCF and EMERGING-path logic are explicitly out of scope and tracked in ABA-31 and ABA-34.
