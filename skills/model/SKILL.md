---
name: stock:model
description: DCF/valuation model for a tech stock. Invoked as `/stock:model TICKER [--confirm]`. Walking-skeleton v1.1 implements the upstream-context gate AND the MODEL_READY routing decision — it reads `model_ready` from the upstream Signal (conversation context preferred, same-day `reports/TICKER_YYYYMMDD.json` fallback) and branches: YES → proceed past gate to DCF stub; CONDITIONAL → halt and surface the `condition` string; NO → refuse and surface the `qualitative_note`. Full DCF math lands in ABA-31 (ESTABLISHED) and ABA-34 (EMERGING). Use whenever the user asks for an intrinsic value, fair-value range, DCF, or "what's it worth" on a ticker.
---

# Model — DCF & Intrinsic Value

**Command:** `/stock:model TICKER [--confirm]`
**Purpose (v1.1 walking skeleton):** Enforce the upstream-context contract AND the MODEL_READY routing decision. `/stock:model` only runs after `/stock:signal` has produced a SIGNAL OUTPUT (in-session) or written a same-day `reports/TICKER_YYYYMMDD.json`. The gate then branches on `model_ready`. Full DCF math lands in ABA-31 / ABA-34.

---

## 1. Identity

- **Skill name:** stock:model
- **Command:** `/stock:model TICKER [--confirm]`
- **Purpose (v1.1):** Walking-skeleton gate with MODEL_READY routing. Verify the upstream Signal is present and well-formed; branch on `model_ready` (YES proceeds, CONDITIONAL halts pending `--confirm`, NO refuses). No DCF math, no output block, no JSON merge yet — those land in ABA-31 / ABA-34.

---

## 2. Why a context gate

Model is downstream of Signal: it consumes the profit-stage classification, clean EPS, AI layer, and MODEL_READY flag that Signal produces. Running `/stock:model` without first running `/stock:signal` would force this skill to either re-derive those inputs (duplicating Signal's MCP calls and methodology) or fabricate them (silently wrong). The gate enforces the contract — Signal first, Model second.

The gate also routes on `model_ready`. Signal's classification is the authoritative call on whether a DCF is sensible right now:

- `YES` — proceed past the gate; downstream DCF logic runs.
- `CONDITIONAL` — a specific user-confirmable risk exists. Halt and surface the `condition` string; require `--confirm` on re-invocation before continuing.
- `NO` — Signal has already ruled the DCF out (pre-profit, qualitative FAIL, or hard CAUTION). Refuse and point back to Signal.

This is v1.1 — the gate plus the routing decision. DCF math itself still lives in ABA-31 / ABA-34.

---

## 3. Execution Phases

### GATHER

1. Parse the ticker from the command argument. Uppercase it (e.g. `nvda` → `NVDA`). If blank, refuse immediately with: "Usage: `/stock:model TICKER [--confirm]`".
2. Parse the optional `--confirm` flag. Its only effect is to allow a CONDITIONAL Signal to pass through (see GATE step 3 below).

### GATE — Resolve upstream Signal, then branch on MODEL_READY

**Step 1 — Locate the upstream Signal.** Two sources, in this precedence order:

1. **Conversation context (preferred).** Scan the messages above this invocation for a `SIGNAL OUTPUT` block whose `Ticker:` line matches the requested ticker (uppercase comparison). If multiple are present, use the most recent.
2. **Filesystem fallback.** If no in-context block is found, look for `reports/TICKER_YYYYMMDD.json` where `YYYYMMDD` is **today's date** (the same date format Signal writes). Read it and use `stages.signal` as the upstream payload. **Reject any file not dated today** — stale on-disk Signal data is fabrication risk; require the user to re-run `/stock:signal` instead.

If both sources are present, conversation context wins (it reflects the current session's reasoning).

**If neither source yields a valid upstream Signal for the requested ticker**, refuse with exactly this message (substituting the requested ticker):

> `/stock:model TICKER` requires a SIGNAL OUTPUT block in context. Please run `/stock:signal TICKER` first, then re-run `/stock:model TICKER` in the same session.

The literal phrase **"run `/stock:signal TICKER` first"** (with TICKER substituted) MUST appear in the refusal — it is verified by the ABA-30 smoke check.

Do not proceed past this step. Do not call any MCP tool. Do not write any file.

**Step 2 — Extract routing fields from the upstream Signal:**

- `model_ready` — `YES`, `CONDITIONAL`, or `NO`. Required.
- `condition` — string, only meaningful when `model_ready = CONDITIONAL`.
- `qualitative_note` — string, surfaced when `model_ready = NO`.
- `verdict` (or `signal`) — `BUY` / `WATCH` / `CAUTION`. Used in the YES acknowledgement.

From the in-context SIGNAL OUTPUT block, read by line label (`MODEL_READY:`, `Condition:`, `Qualitative:`, `Signal:`). From the JSON fallback, read `stages.signal.model_ready`, `stages.signal.condition`, `stages.signal.qualitative_note`, `stages.signal.verdict`.

**Step 3 — Branch on `model_ready`:**

**`YES`:** Gate passed. Emit:

> Gate passed: SIGNAL OUTPUT for TICKER found (source=SOURCE, verdict=VERDICT, MODEL_READY=YES). Ready for DCF.
> Full Model logic (DCF for ESTABLISHED, alternative path for EMERGING) is not yet implemented — see ABA-31 and ABA-34. No report file written in v1.1.

Substitute SOURCE as `context` or `reports/TICKER_YYYYMMDD.json`, VERDICT from upstream, and TICKER throughout.

**`CONDITIONAL` — without `--confirm`:** Halt. Emit:

> Model is CONDITIONAL on Signal — confirm: `<condition>`. Re-invoke `/stock:model TICKER --confirm` to proceed.

Surface the `<condition>` string from the upstream Signal **verbatim** (no paraphrasing). Do not proceed.

**`CONDITIONAL` — with `--confirm`:** Treat as YES for routing purposes. Emit:

> Gate passed (confirmed): SIGNAL OUTPUT for TICKER MODEL_READY=CONDITIONAL, user confirmed `<condition>`. Ready for DCF.
> Full Model logic is not yet implemented — see ABA-31 and ABA-34.

**`NO`:** Refuse. Emit:

> Signal for TICKER is MODEL_READY=NO — Model will not run. Reason: `<qualitative_note>`. Re-run `/stock:signal TICKER` if conditions have changed.

Surface the `qualitative_note` from the upstream Signal verbatim. Do not proceed; do not call any MCP tool; do not write any file.

**Ticker mismatch** (SIGNAL OUTPUT in context is for a different ticker, AND no same-day JSON for the requested ticker exists) is treated as "no upstream Signal" — use the Step 1 refusal message.

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
| "There's a `reports/TICKER_YYYYMMDD.json` with a `stages.signal` block — that should count as upstream context." | Accepted, but **only if dated today**. Same-day JSON is a valid upstream source; conversation context still wins when both are present. Reject any report file not dated today — stale Signal data is fabrication risk; instruct the user to re-run Signal. |
| "The SIGNAL OUTPUT block is for a different ticker but it has useful classification info." | Tickers are not fungible. A SIGNAL OUTPUT for META tells you nothing about NVDA's profit stage or AI layer. Refuse and instruct. |
| "MODEL_READY is CONDITIONAL but the condition looks minor — I'll proceed without `--confirm`." | The whole point of CONDITIONAL is to force an explicit user acknowledgement of the named risk before DCF inputs are committed. Surface the condition verbatim and halt. Do not pre-judge what "minor" means on the user's behalf. |
| "MODEL_READY is NO but the user clearly wants a number — I'll produce one with a caveat." | A NO from Signal is a hard refusal, not a soft warning. Pre-profit companies and qualitative-FAIL companies have no defensible DCF; producing one with a caveat gives the user a confident-looking number anchored to nothing. Refuse and point back to Signal. |
| "I'll paraphrase the `condition` / `qualitative_note` to make it punchier." | Surface them **verbatim**. The user needs to see the exact wording Signal produced — paraphrasing introduces drift between what Signal said and what Model reported, which breaks the audit trail. |
| "A DCF input is null — I'll assume a reasonable default (WACC 10%, terminal growth 3%, …)" | Forbidden. Per the Manual Input Protocol (`skills/_shared/MANUAL_INPUT_PROTOCOL.md`), when any DCF input cannot be derived from MCP data the skill MUST ask the user via a grouped paste-in (this fires in the downstream DCF logic tracked in ABA-31/ABA-34, not in the v1 stub). Defaults are fabrication once written to JSON. |

---

## 5. Acceptance criteria

### v1 — ABA-30 (still in force)

1. **No upstream Signal in context or on disk →** invoking `/stock:model NVDA` returns a refusal message containing the literal phrase **`run /stock:signal NVDA first`** (with the requested ticker substituted).
2. **Valid SIGNAL OUTPUT block in context for the requested ticker (MODEL_READY=YES) →** invoking `/stock:model NVDA` proceeds past the gate and emits the "Gate passed" acknowledgement, naming the verdict and MODEL_READY value from the upstream block.
3. **Mismatched ticker** (SIGNAL OUTPUT for META, request for NVDA, no same-day NVDA report on disk) → treated as "no upstream Signal" — same refusal message, substituting the requested ticker (NVDA).

### v1.1 — ABA-93 (MODEL_READY branching)

4. **Filesystem fallback — same-day `reports/TICKER_YYYYMMDD.json` exists, no in-context block →** the gate reads `stages.signal.model_ready` from the JSON and branches accordingly.
5. **Stale on-disk Signal** (date in filename is not today) → ignored; treated as if no upstream Signal exists; standard refusal.
6. **`model_ready = YES` →** gate passes; "Ready for DCF" acknowledgement emitted; DCF body still stubbed.
7. **`model_ready = CONDITIONAL`, no `--confirm` flag →** gate halts with: `Model is CONDITIONAL on Signal — confirm: <condition>. Re-invoke /stock:model TICKER --confirm to proceed.` The `<condition>` string appears verbatim from the upstream Signal.
8. **`model_ready = CONDITIONAL`, `--confirm` passed →** gate passes (treated as YES); acknowledgement notes the confirmation and surfaces the confirmed condition.
9. **`model_ready = NO` →** gate refuses with: `Signal for TICKER is MODEL_READY=NO — Model will not run. Reason: <qualitative_note>. Re-run /stock:signal TICKER if conditions have changed.` The `<qualitative_note>` string appears verbatim.
10. **Context precedence:** when both an in-context SIGNAL OUTPUT and a same-day JSON exist for the same ticker, the in-context block is the source of truth.

DCF and EMERGING-path math are explicitly out of scope and tracked in ABA-31 and ABA-34.
