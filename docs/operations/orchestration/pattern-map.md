# Pattern map — task shapes → orchestration patterns

**Purpose.** Once a feature is broken into sub-tasks during cycle planning, the *shape* of that breakdown should imply the orchestration approach — no fresh judgement per cycle. This file maps shape to pattern so the user can run a 60-second checklist at planning time and walk away with an execution plan.

**Companion docs.**

- `landscape.md` (landscape-researcher) — full catalogue of orchestration primitives available in Claude Code.
- `critique.md` (devils-advocate) — hard constraints + failure modes (F1/F2/F3) any recommendation must prevent.

**Hard platform constraints baked in** (from `critique.md` and `landscape.md`):

- **No sub-agent recursion.** Subagents (Agent tool, custom `.claude/agents/`) cannot spawn agent teams. Agent teams cannot nest. Only the top-level session — or, equivalently, the agent-team lead — can fan out.
- **Agent teams are expensive** (≈ N+1× per-session token cost) and *experimental*; use them where the parallelism benefit clears the cost, not by default.
- **Same-file parallel work is unsafe** in agent teams: teammates don't get auto-worktrees and file-locking is at the task-list level, not the file level. Partition by file or use `/batch` worktree-isolated subagents.
- **Plan-shape check is at *planning* time, not implementation time** — otherwise F1 (silent architectural deviation) recurs.

---

## Part 1 — Seven axes that decide the pattern

After looking at recent cycles (ABA-115 7-slice UI feature; ABA-104 single-ticket spike; ABA-117/116/121/etc. queue of playbook writes; ABA-132 3-slice backend recalibration), these seven questions discriminate. Anything more is decoration.


| #      | Axis                                                                                                                                        | Why it matters                                                                                                                                                                                                                                     | How to answer in 10 seconds                                                                                                                                                                                  |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **A1** | **Single ticket or queue of N?**                                                                                                            | Queue → batch primitive; single → focused primitive.                                                                                                                                                                                               | Count the sub-tasks. 1 = single; 2–3 with shared dependency chain = mini-pipeline; 4+ that share a template = queue.                                                                                         |
| **A2** | **Sequential dependency or parallel-safe?**                                                                                                 | Slice N consumes JSON schema, file, or output that slice N-1 produces → must serialize. Otherwise can fan out.                                                                                                                                     | Read the dependency graph in `plan.md`. Arrows = serialize. No arrows = parallel candidates.                                                                                                                 |
| **A3** | **Same-file edits across sub-tasks?**                                                                                                       | Even parallel-safe work that touches the same file produces merge conflicts unless serialized — and agent teams have no per-file lock.                                                                                                             | Skim the "Files to touch" line on each sub-task. Any overlap = treat as serial regardless of A2, or move to `/batch` (worktree-isolated).                                                                    |
| **A4** | **One-way door?**                                                                                                                           | Schema change, public API, methodology constant, namespace change, vendor lock-in. Reversal is expensive — needs a plan-review gate *before* implementation, not "we'll fix it in review."                                                         | Does the change land in `DESIGN.md`, a JSON contract field, a `playbooks/*.md` frontmatter key, a `SKILL.md` schema block, or a public command name? Yes → one-way door.                                     |
| **A5** | **Mechanical or subjective acceptance?**                                                                                                    | Mechanical = agent self-checks against the criteria (number matches, JSON field present, test passes). Subjective = legibility, narrative quality, "does the chart pass the squint test" — needs a *differently-prompted* second pass to catch F3. | If every acceptance criterion can be checked by `grep`, `jq`, a unit test, or "function returns expected value" — mechanical. If any criterion is "reads well," "looks right," "is convincing" — subjective. |
| **A6** | **Implementation or research/spike?**                                                                                                       | A spike's deliverable is a *written recommendation* — wrong skill if you treat it like implementation. The skill `pde-backend-spike` exists exactly for this.                                                                                      | Does the sub-task end in code in the tree, or in a written recommendation that closes with proceed/defer/kill? Latter = spike.                                                                               |
| **A7** | **Does the proposed orchestration shape name a sub-agent that dispatches other sub-agents (a "supervisor"/"coordinator"/"manager" layer)?** | Claude Code does not allow sub-agent recursion. This shape is platform-invalid and is exactly what produced F1 in the recent cycle. **The 60-second ritual must answer A7 explicitly — even when no one-way doors exist.**                         | Read the plan's orchestration line. Any phrase like "supervisor sub-agent", "coordinator that spawns workers", "manager agent dispatches implementors" → yes.                                                |


**Not on the list (deliberately culled):**

- "Long-running vs short" — Claude Code sessions persist; runtime isn't a planning-time variable.
- "How many engineers" — N/A (single operator).
- "Confidence level" — handled by the per-task acceptance criteria, not by orchestration choice.

---

## Part 2 — Decision tree (leaves point at concrete primitives from `landscape.md`)

Read top-down. First match wins. Each leaf names: the **shape**, the **pattern**, the **activation trigger**, and the **F1/F2/F3 guards** that the pattern must include.

### Leaf L0 — Plan-review gate (default for *any* multi-slice plan, mandatory on A4 or A7)

**Trigger:** **Any of:** A4 = yes (one-way door), **OR** A7 = yes (platform-invalid orchestration shape), **OR** A1 ≥ 2 (any multi-slice plan, by default).

The default-for-multi-slice rule is deliberate: F1 in the recent cycle had *zero* one-way doors — it was a pure plan-shape deviation. Routing only A4 plans through L0 leaves a hole exactly where ABA-115's failure lived. The cost is one `/pde-plan-review` invocation per multi-slice ticket — well inside the 60-second planning budget.

**Pattern:** `**/pde-plan-review` skill, single-session sequential, before any implementation begins.**

**Activation:** From the top-level Claude Code session, invoke `/pde-plan-review` against the current `tasks/plan.md`. The skill auto-fires on any plan with a one-way-door decision; this leaf extends "auto-fires" to all multi-slice plans.

**What the L0 reviewer must check** (in addition to the skill's own checks):

1. **Platform feasibility.** Does the orchestration line name any sub-agent that dispatches other sub-agents? Reject — reshape to top-level fan-out (lead-led agent team) before approval.
2. **Leaf assignment.** Does the orchestration line resolve to one of L1–L7 in this map? If not, the plan is free-form and must be rewritten in the leaf vocabulary. Free-form plans are the surface F1 originated on.
3. **Phase transitions for L7.** If the leaf is L7, are the phase boundaries named, with a pattern label per phase? "Slices 1–3 chain (L4); 4–6 fan-out (L5); 7 chain (L4)" is acceptable. "We'll figure out the fan-out when we get there" is not.

**Why this is the F1 guard.** F1 is a deviation between *planned shape* and *platform capability*. That bug is independent of whether the work touches a one-way door. L0 is the only check that runs before anyone touches code — it's the only place a platform-invalid shape can be caught cheaply.

**Then route the resulting sub-tasks through L1–L6 below.**

---

### Leaf L1 — Single ticket, research/spike

**Trigger:** A1 = 1, A6 = spike.

**Examples this repo:** ABA-104 (base-year-effect detection), ABA-103 (auto-derive WACC).

**Pattern:** **Single-session sequential + `pde-backend-spike` skill.**

**Activation:** `claude` → invoke the spike skill. No fan-out, no subagent, no team. The deliverable is a written recommendation, not code. Spike skill closes with proceed/defer/kill and a follow-up implementation ticket if proceed.

**F-guards:** N/A (no orchestration layer to deviate, no parallel commits, no subjective render).

---

### Leaf L2 — Single ticket, implementation, mechanical acceptance

**Trigger:** A1 = 1, A5 = mechanical, A6 = implementation.

**Examples this repo:** ABA-110 (SBC strip), ABA-111 (growth-rate cap), ABA-130 (coverage bypass), ABA-135/136/137 individually.

**Pattern:** **Single-session sequential + `agent-skills:build`.**

**Activation:** `claude` → `agent-skills:build` or the relevant skill. Sub-agent is overkill — the criteria are checkable in-session, and the cost of spawning a subagent isn't repaid.

**Optional optimisation:** If the ticket would blow context (large file scan, log dive), spawn one `Explore`-type subagent inline via the Agent tool — cheap, ephemeral, and the result returns to the main thread.

**F-guards:** N/A.

---

### Leaf L3 — Single ticket, implementation, subjective acceptance

**Trigger:** A1 = 1, A5 = subjective.

**Examples this repo:** ABA-138 in isolation (CAGR glidepath — *if* it had been the whole ticket). The Y5-label collision (F3) lived in this leaf's territory.

**Pattern:** **Single-session sequential for implementation, then a fresh-context second pass via `/crit` (or a `code-reviewer` custom subagent) with one of the canonical squint prompts in Part 3.5.**

**Activation:**

1. `agent-skills:build` for implementation.
2. Immediately after the implementor's first verification, invoke `/crit` (or spawn a custom `code-reviewer` subagent via the Agent tool) with the squint prompt that matches the output type (chart / narrative / tabular — see Part 3.5). **Pick from the canonical list; do not write a new prompt from scratch under cycle time pressure** — that's how F3 reproduces in the reviewer.

**Why this is the F3 guard.** The reviewer must *not* see the original AC. The label-collision bug passed all five mechanical criteria. If the reviewer uses the same criteria, it passes again. The squint prompts in Part 3.5 are deliberately *different* checklists, designed to fail on the kinds of bugs mechanical AC misses.

**F-guards:**

- F3 — guarded by the differently-shaped second pass.
- F1, F2 — N/A.

---

### Leaf L4 — Multi-slice with sequential dependency (chained gates)

**Trigger:** A1 = 2–N, A2 = sequential.

**Examples this repo:** ABA-115 slices 1→2→3 (UI shell → SKILL schema change → re-run reports). ABA-132 slices 1→2→3 (calibration design → impl → verification).

**Pattern:** **Single-session sequential, one sub-task per turn, explicit gate read at each boundary.**

**Activation:** No fan-out, no team, no subagent layer between slices. After each sub-task lands, the *operator* reads the gate criterion at the end of that slice's plan.md section and confirms before kicking off the next slice. Use `agent-skills:build` per task.

**Why agent-teams is wrong here.** The slices share state (schema, JSON output, file contents). Agent teams' file-locking is task-level not file-level, and the upstream slice's output is the downstream slice's input — there's no parallelism gain to amortise the +1× token cost.

**F-guards:**

- F1 — N/A.
- F2 — **partially mitigated, not prevented.** *This is the F2-hot leaf.* The written rule (slice-N+1 finds a bug from slice N → separate commit attributed to slice N, before slice N+1 work resumes) is the same shape as the rule that already failed in ABA-138 → silently-folded-into-ABA-139. Add a **human commit gate**: before approving any commit in a multi-slice chain, the *operator* (not an agent) runs `git diff --stat` on the staged change, compares the file list against the current slice's "Files to touch" line in `plan.md`, and asks "is anything in this diff from a prior slice?" If yes — abort the commit, extract the prior-slice fix as a separate commit attributed to its originating ticket, then re-stage the current slice. This is 15 seconds of human-eyeball-on-the-diff per commit; it costs less than the next F2 incident. Full mechanical prevention requires the `PreToolUse` hook listed in Part 5 — deferred to the user.
- F3 — apply L3's second-pass review at the chain's end if any slice produced subjective output.

---

### Leaf L5 — Multi-slice, parallel-safe slices after a shared prefix

**Trigger:** A1 = 2–N, A2 = parallel after some shared prefix, A3 = different files.

**Examples this repo:** ABA-115 slices 4/5/6 (three independent chart components, each `ui/src/components/charts/*.jsx`, all consuming the same JSON contract from Slice 3).

**Pattern:** **Agent teams (the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` primitive) — top-level lead + N teammates, one slice per teammate.**

**Activation:** From the top-level Claude Code session, spawn an agent team (3–5 teammates is the Anthropic-suggested sweet spot, matches the chart trio exactly). Lead writes the task list, each teammate claims one slice's task, all teammates report to the lead. **The lead must be a top-level session, not a subagent** — agent teams cannot nest.

**Fallback if agent teams unavailable** (flag removed, Claude Code <2.1.32, or org policy gates it): demote L5 to N sequential L2/L3 single-sessions. F-guards still apply; only wallclock changes. The cost note below covers when this is actually a downgrade vs. when it's a wash.

**Pre-flight checklist before fan-out** (lead runs this once before assigning tasks):

1. Confirm each slice touches a *different file set* (A3). If two slices touch the same file, demote that pair to L4 chain — agent teams' file-locking won't save you.
2. Confirm the shared upstream dependency has landed (the gate from L4 → L5 transition). The agent team should start *after* the chain ends, not in parallel with it.
3. Each slice gets its own commit. Restate the F2 rule in the lead's task assignment to each teammate.

**F-guards:**

- F1 — caught at L0 plan review (now mandatory on A7 = yes and on any multi-slice plan).
- F2 — **partially mitigated, not prevented** — same caveat as L4. The "separate commit, escalate, do not silently fold" rule is written into each teammate's brief, but it's the same shape that already failed. Add the **lead commit gate**: when a teammate reports back with a commit ready to merge, the *lead* (the top-level operator, not a sub-agent) reads `git diff --stat` against that teammate's assigned "Files to touch" list before approving. Any file outside the list = abort the merge, extract the cross-slice fix as its own commit attributed to the originating ticket. Full mechanical prevention requires the `PreToolUse` hook in Part 5.
- F3 — at the end of the fan-out, the lead invokes L3's second-pass review (`/crit` with one of the canonical squint prompts in Part 3.5) across the *aggregated* output, not per-slice. The label-collision bug was visible at aggregated render, not in any single component.

**Cost note.** Agent teams are ≈ N+1× a single-session cost. Three chart teammates ≈ 4× a single session. **Heuristic:** use agent teams when **(a)** each slice has ≥1 hour of implementation work AND **(b)** the operator actually wants the wallclock back. Otherwise run sequentially in L4 — same total token cost across all slices, simpler shape, no experimental-flag dependency. The 4× spend only buys parallelism in calendar time; it does not reduce work.

**When `/batch` is better than agent teams here.** If the parallel slices are truly *mechanical* (codemod-style — same instruction over many files), use the bundled `/batch` command instead. It auto-creates worktrees per unit and opens one PR per unit. The recent cycle's chart slices are *not* mechanical (each chart has bespoke data flow), so agent teams is the right fit.

---

### Leaf L6 — Queue of N file-isolated tickets sharing one template

**Trigger:** A1 = 4+, A2 = independent, A3 = each touches a different file.

**Examples this repo:** ABA-120/121/122/123/124 (write playbooks: META, NVDA, AMZN, NFLX, ADYEN) — each touches `playbooks/TICKER.md`, format is locked, no inter-dependencies.

**Pattern:** **Two viable paths, picked by the *per-unit input size* test below — not by gut-feel "is this mechanical?"**

**Path test (deterministic):**

- **Per-unit input fits in <100 tokens** (a filename, a ticker symbol, a regex, an import string)? → **Path B (`/batch`).** The instruction is the same across all units; only a small parameter varies.
- **Per-unit input is ≥200 tokens** (a brief, a narrative spec, a ticker's sell-side debate axes, a per-unit context dossier)? → **Path A (Agent teams).** Each unit needs enough context that worktree-isolated subagents would lose nuance.
- 100–200 tokens is the gray zone; default to Path A unless the work is truly templated.

**Path A — Agent teams** (per the test above).

- Same activation as L5: top-level lead + N teammates, one ticket per teammate. The template prompt is identical; the per-ticket context is what varies.

**Path B — `/batch`** (per the test above).

- `/batch "rewrite all imports of X to Y"` style. Each unit gets its own worktree and PR. Best when the per-unit parameter is small and the instruction is identical.

**For the playbook queue specifically: Path A.** Each playbook's brief is on the order of 500+ tokens (business architecture, capex cycle, sell-side debate axes, failure modes, narrative tone). That's well above the 200-token threshold — Path A by the rule, not just by intuition.

**F-guards:**

- F1, F2 — same as L5.
- F3 — apply *once across the batch*, not per-playbook. Cross-playbook vocabulary drift and narrative inconsistency is invisible in any single playbook. One reviewer reads all N back-to-back.

---

### Leaf L7 — Mixed: feature with a shared prefix and a fan-out tail (composition of L4 + L5)

**Trigger:** ABA-115-shaped: chain → fan-out → close-out.

**Pattern:** **Compose L4 and L5 explicitly in the plan. Write the orchestration plan as "Slices 1–3 chain (L4); Slices 4–6 fan-out (L5); Slice 7 chain (L4)." Each phase uses its own primitive.**

**Activation:** Don't try to make a single orchestration primitive cover all of it. The phase transitions are where F1 and F2 surface most often — pause between phases, confirm gates, then choose the next primitive.

**Phase-transition checklist** (run at *every* L4→L5, L5→L4, L4→L3, L5→L3 boundary — this is the procedure, not just a label):

1. **Gate read.** Open the prior phase's last slice in `plan.md`; read its acceptance criteria aloud. Each one met? If no — pause; do not transition.
2. **Cross-slice diff scan.** `git log <prior-phase-start>..HEAD --stat`. Did any commit touch files attributed to a slice in a *different* phase? If yes — that's an F2 hit; extract those changes into a separately-attributed commit before continuing.
3. **Next-phase pattern restated.** Say the next phase's leaf name (L4, L5, L6, or L3) out loud. If the answer is "I'm not sure" — go back to Part 4 ritual step 6 and re-derive from axes.
4. **Dispatch.** Only now spawn the next phase's primitive.

This is ~90 seconds at each transition. It's the difference between L7 being a procedure and L7 being a sticker on the plan that means nothing in execution.

**This is the most common shape this repo will produce** given the multi-stage skill architecture (UI ↔ SKILL ↔ reports). Plan must *name the phase transitions* so the operator knows when to switch primitives — and run the checklist above at each one.

---

## Part 3 — Three worked examples from this repo

### Example 1: ABA-115 — Model tab v1 (L7 composition: L0 → L4 → L5 → L4 → L3)

**Sub-tasks (7 slices, see `tasks/plan.md`):**

1. UI shell (no SKILL change)
2. SKILL schema: emit `historical_fcf_margins[]`
3. Re-run covered tickers
4. CAGR glidepath chart
5. FCF margin trajectory chart
6. Scenario fan chart
7. Captions / styling / docs

**Axis read:**

- A1: 7 slices.
- A2: 1→2→3 sequential; 4/5/6 parallel-safe; 7 final.
- A3: 4/5/6 each touch their own file (`charts/*.jsx`).
- A4: yes — Slice 2 changes a JSON contract (`historical_fcf_margins[]`).
- A5: slices 1–3 mechanical (JSON field present, audit row matches); slices 4–7 subjective (chart legibility).
- A6: implementation.

**Pattern: L0 (`/pde-plan-review`) → L4 single-session chain (1→2→3) → L5 agent team of 3 teammates (4‖5‖6) → L4 single-session (7) → L3 `/crit` squint-test pass across the aggregated UI.**

**What actually went wrong** (per `critique.md`): the lead picked "supervisor sub-agent + implementor sub-agents" — platform-invalid because subagents can't nest. L0 would have caught this at planning time and reshaped to top-level fan-out. Instead, F1 fired (the supervisor improvised inline, didn't escalate), F2 fired (a NaN bug from slice 4 was folded into slice 5's commit instead of attributed back as ABA-143/144), F3 fired (Y5 label collision shipped because AC was mechanical).

**What L0→L5→L3 would have changed:**

- L0 catches "supervisor spawns implementor" at plan review → reshapes to the lead-led agent team.
- L5's separate-commit rule + the 15-second lead `git diff --stat` gate partially mitigates F2 (full mechanical prevention waits on the deferred `PreToolUse` hook in Part 5).
- L3's `/crit` with the canonical chart squint prompt from Part 3.5 catches F3 before merge.

---

### Example 2: ABA-104 — Base-year-effect spike (L1)

**Sub-tasks (1):** Investigate the failure mode, recommend detection tripwire + response strategy + scope, file follow-up.

**Axis read:**

- A1: 1.
- A6: spike (recommendation-only).

**Pattern: L1 — single-session + `pde-backend-spike`.**

This is the case where adding sub-agents or a team is *worse* than running solo. The deliverable is reasoning, not code, and reasoning fragments badly across context boundaries.

**Outcome (already shipped):** Done; recommendation produced an implementation follow-up (ABA-134). No F1/F2/F3 exposure because no orchestration layer existed.

---

### Example 3: ABA-120/121/122/123/124 — Five playbook writes (L6, Path A)

**Sub-tasks (5):** One playbook per remaining covered ticker (META, NVDA, AMZN, NFLX, ADYEN.AS).

**Axis read:**

- A1: 5.
- A2: independent.
- A3: each touches its own `playbooks/TICKER.md`.
- A4: the *first* playbook established the template (ABA-117/116 already shipped). Subsequent five are not one-way.
- A5: subjective (narrative quality, sell-side argument balance).
- A6: implementation (creative writing).

**Pattern: L6 Path A — agent team, 5 teammates, one ticker each, lead aggregates.**

Why not `/batch`: each playbook is *not* mechanical. Each ticker has a different debate (AI search disruption for GOOG, EUV monopoly for ASML, etc.). `/batch` would produce structurally identical playbooks; agent teams produces ticker-thesis-aware playbooks.

**F-guard for this case:** L3 cross-playbook second pass. One reviewer reads all five back-to-back to catch vocabulary drift and narrative-style inconsistency. *Not* one reviewer per playbook — the failure mode is between playbooks, invisible inside one.

---

## Part 3.5 — Canonical squint prompts (use these verbatim; do not write fresh)

L3's second-pass review is only as good as the prompt it runs. The recent cycle's Y5 label collision happened because the AC was mechanical; an L3 reviewer given a generic "review for legibility" prompt would have reproduced the same blind spot. These prompts are pre-written so the planner can pick one in five seconds at planning time, not draft one under time pressure.

**Rules of use:**

- Pick the prompt that matches the output type. Don't mix.
- The reviewer must *not* see the original acceptance criteria. Send the squint prompt and the rendered artefact only.
- Run after the implementor reports green on mechanical AC, *before* merge.

---

**Squint prompt — CHARTS / visualisations** (the F3-original failure mode)

> "You have not seen the acceptance criteria for this chart. Open the rendered chart at its canonical viewport size (the size a reader would actually see — assume desktop browser unless told otherwise).
>
> Answer these questions, in order. Do not skip any.
>
> 1. **One-sentence thesis test.** Without reading the underlying data or any caption, can you state in one sentence what this chart is arguing? If no — what's confusing?
> 2. **Label legibility.** Are any labels overlapping, clipped at chart edges, or unreadable at the rendered size? Look in particular at: axis tick labels, scenario/series endpoints (right edge, top edge), data-point callouts, and any annotation that points at a specific location on the chart.
> 3. **Axis sanity.** Does the y-axis range make sense — or is one extreme outlier blowing out the scale and flattening the rest? Does the x-axis tick density match the rendered width (too dense = ticks collide; too sparse = unclear time scale)?
> 4. **Colour and ordering.** If there's an implied ordering (bear < base < bull, low to high, etc.), does the visual ordering match? Do any two series share enough colour/style that a reader could swap them?
> 5. **Edge cases.** What happens at the chart's edges — left edge (start of series), right edge (most-recent or projected-Y5), top edge (chart maximum)? List anything that looks wrong, ugly, overlapping, or unclear at the edges specifically. Edges are where label collisions hide.
> 6. **What's missing.** Is there a current-state reference line, a callout for a fired condition (e.g. a growth cap), or a unit/scale indicator that a reader needs and isn't there?
>
> Name every issue, even small ones. Do not stop at the first issue — list them all. An issue that 'technically passes the spec' but produces a worse reader experience is in-scope for this review."

This prompt would have caught the Y5 endpoint-label collision (question 5) and the AMZN negative-fcf y-axis blowout (question 3).

---

**Squint prompt — NARRATIVE OUTPUT** (playbooks, methodology notes, signal/model rationale prose)

> "You have not seen the acceptance criteria for this document. Read it once at normal speed — do not study it.
>
> Answer these questions in order:
>
> 1. **One-paragraph thesis test.** In one paragraph, what is this document arguing? If you can't state the thesis after one read-through, the document is unclear.
> 2. **Vocabulary consistency.** Are the same concepts named with the same words throughout? List any term that drifts (e.g. 'segment' in one section, 'business line' in another, 'vertical' in a third — three names for the same thing is a smell).
> 3. **Confident-but-unsupported claims.** Are there assertions that a sceptical reader would push back on — and is the supporting evidence in the document? Quote one such claim verbatim if you find one.
> 4. **Audience leakage.** Is this written for the same reader throughout? If sections switch register (technical → marketing → internal-jargon), name the shifts.
> 5. **Structural mismatch.** Does the document's section ordering match what a reader looking for the answer would expect? Or do they have to hunt?
> 6. **Comparison to siblings (only if applicable — multi-document review).** If you are reviewing this alongside sibling documents (e.g. multiple playbooks), what's *different* between them in style, depth, structure, or vocabulary that isn't justified by the subject matter?
>
> Name every issue. The goal is to find the gap between 'technically correct' and 'a reader would actually use this'."

This prompt is the right shape for the L6 cross-playbook second pass — question 6 is specifically the cross-doc vocabulary-drift check.

---

**Squint prompt — TABULAR / STRUCTURED REPORT OUTPUT** (Signal/Model/Screen JSON, the report viewer's tabs)

> "You have not seen the acceptance criteria for this report or JSON output. Open the rendered view (UI tab if applicable, or the JSON itself).
>
> Answer in order:
>
> 1. **At-a-glance verdict.** What is this report *telling* a reader? State the verdict and primary number in one sentence. If you have to read three sections to know, the report is buried.
> 2. **Number sanity.** For every numeric field: does the magnitude look right (units in the right place — billions vs millions, percent vs decimal)? Does any number conflict with another (e.g. P/E and PEG implying different growth rates without explanation)?
> 3. **Missing fields, silent.** Are there fields you'd expect for this kind of report that are absent — and is the absence acknowledged (e.g. 'N/A — pre-profit') or just silently missing?
> 4. **Audit trail.** If overrides, caps, or substitutions were applied, are they named — or did some assumption silently swap in?
> 5. **Reader's next question.** What's the most likely next question a reader has after seeing this? Is the answer in the report?
>
> Name every issue you find."

---

**How to pick.** A5 = subjective with a chart artefact → use the charts prompt. A5 = subjective with prose artefact → narrative prompt. A5 = subjective with a structured report → tabular prompt. If the artefact is mixed (e.g. ABA-115 Model tab has charts + summary text), run the charts prompt for the chart components and the tabular prompt for the summary strip — they take ~2 minutes each.

---

## Part 4 — The cycle-planning ritual

A seven-question checklist applied to each parent ticket during planning. Output is the orchestration plan, written one line into the parent's `plan.md`.

```
1. Count sub-tasks (A1). One → L1 / L2 / L3 by axes A5/A6. Several → continue.
2. Draw the dependency graph (A2). All arrows? L4. No arrows after a prefix? L5/L7. Pure independent → L6.
3. Highlight same-file overlaps (A3). Any overlap → serialize that pair regardless of step 2 (or move to `/batch` if truly mechanical).
4. Mark one-way doors (A4). Any → run `/pde-plan-review` (L0) before kicking off any sub-task implementation.
5. Read the plan's orchestration line (A7). Does it name a sub-agent that dispatches other sub-agents ("supervisor", "coordinator", "manager")? Yes → reject the plan; reshape to top-level fan-out (lead-led agent team) before continuing. This is the F1 catcher and is independent of one-way-door status.
6. Mark subjective acceptance (A5). Any → schedule L3 second pass (`/crit` with squint-test prompt) after implementation. Write the squint-test prompt now, not at review time.
7. Write the one-line orchestration plan into `plan.md`, e.g.: "L0 → L4(1-3) → L5 team-of-3(4‖5‖6) → L4(7) → L3 squint pass."
```

**Add to the bottom of `plan.md` for every multi-slice ticket:**

- The orchestration plan from step 7 above.
- The squint-test prompt (if step 6 fired) — pre-written, ready for the reviewer.
- The F2 rule restated verbatim: *"If an agent finds a bug from a prior slice, commit the fix as a separate commit attributed to the originating ticket before continuing. Do not silently fold."*

**Total time: ≈ 60 seconds per parent ticket** once the axes are memorised.

---

## Part 5 — Open questions / follow-ups (out of scope for this map)

- **F2 enforcement hook.** Currently F2 is a rule in the teammate brief. A `PreToolUse` hook on `git commit` that compares the staged diff against the teammate's "Files to touch" list and exits 2 on out-of-scope edits would mechanically prevent the failure. One small script, one config entry. Worth one cycle of setup if F2 recurs.
- **Custom `squint-reviewer` subagent.** L3's second pass currently uses `/crit`. A custom `.claude/agents/squint-reviewer.md` with the squint-test prompt baked into the system prompt would be a one-time cost that pays back across every L3 leaf — and removes the risk of the operator forgetting to pre-write the prompt at planning time.
- **Agent-teams cost calibration.** `landscape.md` flags that Anthropic hasn't published per-pattern token numbers. After the next L5 fan-out, log actual token consumption and compare against the "≈ N+1×" rough mental model. If costs are 2× the estimate, the L5 threshold for "is parallelism worth it?" needs revisiting.
- **Channels for async hand-off** between phase transitions in L7. Currently the operator is the courier between L4 and L5 phases. A channel that pushes "L4 done; gate criterion met" into the agent-team lead's session might tighten the L7 hand-off, but it adds dependency on a research-preview feature — defer unless the L7 transition becomes a recurring drag.

