# Orchestration guide

A short, self-contained reference for deciding how to break a Linear ticket into agent work. Run the seven-question checklist at cycle planning; write one line into the ticket's `plan.md`; execute.

If this is your first read, work top-to-bottom. Once you have run the ritual on a couple of tickets, you'll come back only to Section 2 (the questions) and Section 5 (the reviewer prompts).

## Contents

1. [What this is](#1-what-this-is)
2. [The seven questions](#2-the-seven-questions)
3. [The seven execution shapes](#3-the-seven-execution-shapes)
4. [The 60-second ritual](#4-the-60-second-ritual)
5. [Reviewer prompts](#5-reviewer-prompts)
6. [Worked example — ABA-115](#6-worked-example--aba-115)
7. [What this doesn't fix](#7-what-this-doesnt-fix)
8. [Reference](#8-reference)

---

## 1. What this is

A planning-time checklist that decides how a ticket gets executed by agents. The point is to make the call before any agent touches code, not at retrospective.

Multi-agent ticket work surfaces three structural challenges that are cheap to handle at planning time and expensive to fix after code has landed:

- **Platform constraint mismatches.** Claude Code supports exactly one layer of agent fan-out — the top-level session (or an agent-team lead) dispatches workers; workers do not spawn sub-workers. A plan that assumes a deeper hierarchy will fail silently: the agent improvises and only notes the deviation in its final report, if at all.
- **Cross-sub-task bug attribution.** A bug introduced by one sub-task is often discovered while working on the next. Without an explicit rule, agents fold the fix into the current commit — and the git history can no longer tell you which sub-task caused which bug, or whether the originating sub-task's scope crept.
- **Subjective quality gaps.** Acceptance checks that an agent can answer mechanically ("is the JSON field present?") are reliable. Checks that require judgement ("is this chart readable?") are not — the agent re-passes whatever it checked during implementation, reproducing the same blind spots. Only a second-pass reviewer with a different checklist catches what the implementer missed.

The seven questions below address each of these at planning time. Answer them, write one orchestration line into the ticket's plan, and any of the three challenges has somewhere to surface before any code is written.

---

## 2. The seven questions

Ask these of every parent ticket during cycle planning. Most have a 10-second answer once the ticket plan is in front of you.

### Question 1 — How many sub-tasks does this ticket break into?

Count the items in the ticket's `plan.md`. One is a single-session job. Two or three with arrows between them is a chain. Four or more that share a template is a queue.

### Question 2 — Do they have to happen in order, or can they run in parallel?

Look at the dependency graph in `plan.md`. If sub-task two consumes a JSON schema, file, or output that sub-task one produces, you have to serialise. If they don't share inputs, they're candidates for parallel work.

### Question 3 — Do any of them touch the same file?

Skim each sub-task's "files to touch" line. Any overlap means you serialise that pair regardless of what Question 2 said — agent teams don't lock at the file level, and parallel edits on the same file produce merge conflicts.

### Question 4 — Does anything change a public contract?

By "public contract" I mean a JSON schema field, a `SKILL.md` schema block, a `playbooks/*.md` frontmatter key, a public command name, or anything in `DESIGN.md`. These are expensive to reverse — they need a plan-review pass before implementation, not "we'll fix it in review."

### Question 5 — Are the acceptance checks mechanical or subjective?

Mechanical means a test passes, a number matches, a JSON field is present, a function returns the expected value. Subjective means a chart looks right, prose reads well, a report is legible. Any subjective check needs a second-pass reviewer who has not seen the original acceptance criteria — otherwise the reviewer just re-checks the same things the implementer already checked.

### Question 6 — Is the deliverable code in the tree, or a written recommendation?

If the ticket ends in a "proceed / defer / kill" memo with no code change, it's a spike. Spikes use a different skill (`pde-backend-spike`) and have different acceptance: the deliverable is the recommendation, not running code.

### Question 7 — Does the plan describe an agent dispatching other agents?

Read the orchestration line in `plan.md` (the one you're about to write — or one you've drafted in your head). Does it contain any phrase like "supervisor sub-agent," "coordinator that spawns workers," or "manager agent dispatches implementers"? Claude Code does not allow sub-agents to spawn other sub-agents. This shape is platform-invalid. Reject the plan; reshape it so the top-level Claude Code session — or an agent-team lead, which is functionally a top-level session — does the dispatching. Only one layer of fan-out is supported.

---

## 3. The seven execution shapes

The seven questions narrow to one of these shapes. Pick the first match top-to-bottom.

| Shape | When it applies | Building block |
|-------|-----------------|----------------|
| **Plan-review gate** | Any multi-slice plan, or a one-way door (Q4 = yes), or a coordinator-agent shape (Q7 = yes) | `/pde-plan-review` skill, before any other work |
| **Single session, spike** | One sub-task, deliverable is a recommendation (Q6 = spike) | `pde-backend-spike` skill |
| **Single session, mechanical** | One sub-task, acceptance is mechanical (Q5 = mechanical) | `agent-skills:build` (or the relevant skill) |
| **Single session, subjective** | One sub-task, acceptance is subjective (Q5 = subjective) | Build skill, then `/crit` with a [reviewer prompt](#5-reviewer-prompts) |
| **Sequential chain** | Multiple sub-tasks with arrows between them (Q2 = sequential) | Single session, one sub-task per turn, explicit gate at each boundary |
| **Parallel team** | Multiple sub-tasks, parallel-safe, different files (Q2 = parallel, Q3 = no overlap) | Agent teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`), lead plus 3–5 teammates |
| **Composition** | Mix of chain and parallel within one ticket (most common shape this repo produces) | Compose chain + team explicitly in the plan, with named phase transitions |

### Decision flow

```
                  ┌──────────────────────────────┐
                  │ Q7: coordinator-agent shape? │──yes──┐
                  └──────────────┬───────────────┘       │
                                 no                      ▼
                                 │              [Reject; reshape]
                                 ▼
                  ┌──────────────────────────────┐
                  │ Q4: one-way door?            │──yes──┐
                  └──────────────┬───────────────┘       │
                                 no                      ▼
                                 │           [Plan-review gate first,
                                 │              then continue]
                                 ▼
                  ┌──────────────────────────────┐
                  │ Q1: how many sub-tasks?      │
                  └──────────────┬───────────────┘
                                 │
                  ┌──────────────┴───────────────┐
                  ▼                              ▼
              [one]                        [several]
                  │                              │
                  ▼                              ▼
       ┌──────────────────┐         ┌─────────────────────────┐
       │ Q6: spike?       │         │ Q2: arrows between them?│
       └──┬───────────┬───┘         └────┬─────────────┬──────┘
        yes          no                  yes           no
          │           │                   │             │
          ▼           ▼                   ▼             ▼
     [Spike]    ┌──────────┐       [Sequential    ┌──────────┐
                │ Q5:      │        chain]        │ Q3: same │
                │ mech or  │                      │  file?   │
                │ subj?    │                      └──┬───────┘
                └─┬──────┬─┘                       yes    no
                mech   subj                         │      │
                  │     │                           ▼      ▼
                  ▼     ▼                       [Demote  [Parallel
              [Single  [Single                   to       team]
               mech]    subj]                    chain]
```

If you land on the composition shape (chain + team mixed), write the orchestration line as a sequence of shape names — e.g. `chain(1-3) → team(4‖5‖6) → chain(7)` — and run a phase-transition check at each boundary.

### Phase transitions inside a composition

```
   ┌─────────────────┐   ┌──────────────────┐   ┌─────────────────┐
   │ chain phase     │──→│ gate check       │──→│ team phase      │
   │ (sub-tasks 1-3) │   │ — read AC of last│   │ (sub-tasks 4-6) │
   │                 │   │   slice          │   │   in parallel   │
   └─────────────────┘   │ — git diff scan  │   └─────────┬───────┘
                         │   for cross-     │             │
                         │   slice bug folds│             ▼
                         │ — name next      │   ┌──────────────────┐
                         │   shape out loud │   │ gate check       │
                         └──────────────────┘   │ (same three      │
                                                │  steps)          │
                                                └─────────┬────────┘
                                                          ▼
                                                ┌─────────────────┐
                                                │ chain phase     │
                                                │ (sub-task 7)    │
                                                └─────────────────┘
```

The gate check takes about 90 seconds. It's the difference between composition being a real procedure and being a label on the plan that means nothing in execution.

---

## 4. The 60-second ritual

For each parent ticket during cycle planning:

1. **Count** the sub-tasks ([Question 1](#question-1--how-many-sub-tasks-does-this-ticket-break-into)). One sub-task → jump to [single-session shapes](#3-the-seven-execution-shapes). Several → continue.
2. **Draw the dependencies** ([Question 2](#question-2--do-they-have-to-happen-in-order-or-can-they-run-in-parallel)). All arrows → chain. No arrows after a shared prefix → composition. Pure independent → queue.
3. **Look for same-file overlaps** ([Question 3](#question-3--do-any-of-them-touch-the-same-file)). Any overlap means that pair serialises regardless of what step 2 said.
4. **Mark one-way doors** ([Question 4](#question-4--does-anything-change-a-public-contract)). Any → run `/pde-plan-review` before kicking off any sub-task implementation.
5. **Check the orchestration line for coordinator-agent shapes** ([Question 7](#question-7--does-the-plan-describe-an-agent-dispatching-other-agents)). Any "supervisor sub-agent that spawns workers" wording → reject the plan and reshape before continuing.
6. **Mark subjective acceptance** ([Question 5](#question-5--are-the-acceptance-checks-mechanical-or-subjective)). Any → schedule a reviewer pass and paste the matching [reviewer prompt](#5-reviewer-prompts) into the plan now, not at review time.
7. **Write one line into `plan.md`** describing the orchestration. E.g. `plan-review → chain(1-3) → team-of-3(4‖5‖6) → chain(7) → reviewer pass on UI`.

Also add to the bottom of `plan.md` for every multi-slice ticket:

- The orchestration line from step 7.
- The reviewer prompt (if step 6 fired) — pre-written, ready for the reviewer to receive.
- This sentence, verbatim: *"If an agent finds a bug from a prior sub-task, commit the fix as a separate commit attributed to the originating ticket before continuing. Do not silently fold."*

About a minute per parent ticket once the questions are memorised. Question 6 (spike or implementation) is implicit in step 1 above — if the deliverable is a recommendation, you took the single-session-spike branch and never reached step 2.

---

## 5. Reviewer prompts

Three prompts the reviewer agent receives in place of the original acceptance criteria. The point is to ask a *different* set of questions than the implementer answered — otherwise the reviewer reproduces the implementer's blind spot.

Pick by output type. Paste the prompt into the ticket's `plan.md` at planning time so the reviewer has it ready when its turn comes.

### Chart prompt

Use this for any ticket that produces a rendered chart or visualisation (e.g. anything under `ui/src/components/charts/`).

> You have not seen the acceptance criteria for this chart. Open the rendered chart at its canonical viewport size (the size a reader would actually see — assume desktop browser unless told otherwise).
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
> Name every issue, even small ones. Do not stop at the first issue — list them all.

### Narrative prompt

Use this for any ticket that produces prose — playbooks, methodology notes, signal/model rationale text. Particularly useful when reviewing several documents together (cross-document vocabulary drift is invisible in any single document).

> You have not seen the acceptance criteria for this document. Read it once at normal speed — do not study it.
>
> Answer in order:
>
> 1. **One-paragraph thesis test.** In one paragraph, what is this document arguing? If you can't state the thesis after one read-through, the document is unclear.
> 2. **Vocabulary consistency.** Are the same concepts named with the same words throughout? List any term that drifts (e.g. "segment" in one section, "business line" in another, "vertical" in a third — three names for the same thing is a smell).
> 3. **Confident-but-unsupported claims.** Are there assertions that a sceptical reader would push back on — and is the supporting evidence in the document? Quote one such claim verbatim if you find one.
> 4. **Audience leakage.** Is this written for the same reader throughout? If sections switch register (technical → marketing → internal-jargon), name the shifts.
> 5. **Structural mismatch.** Does the document's section ordering match what a reader looking for the answer would expect? Or do they have to hunt?
> 6. **Comparison to siblings (only if applicable).** If you are reviewing this alongside sibling documents (e.g. multiple playbooks), what's *different* between them in style, depth, structure, or vocabulary that isn't justified by the subject matter?
>
> Name every issue.

### Tabular prompt

Use this for any ticket that produces a structured report — Signal/Model/Screen JSON output, a tab in the report viewer, a results table.

> You have not seen the acceptance criteria for this report or JSON output. Open the rendered view (UI tab if applicable, or the JSON itself).
>
> Answer in order:
>
> 1. **At-a-glance verdict.** What is this report telling a reader? State the verdict and primary number in one sentence. If you have to read three sections to know, the report is buried.
> 2. **Number sanity.** For every numeric field: does the magnitude look right (units in the right place — billions vs millions, percent vs decimal)? Does any number conflict with another (e.g. P/E and PEG implying different growth rates without explanation)?
> 3. **Missing fields, silent.** Are there fields you'd expect for this kind of report that are absent — and is the absence acknowledged (e.g. "N/A — pre-profit") or just silently missing?
> 4. **Audit trail.** If overrides, caps, or substitutions were applied, are they named — or did some assumption silently swap in?
> 5. **Reader's next question.** What's the most likely next question a reader has after seeing this? Is the answer in the report?
>
> Name every issue you find.

---

## 6. Worked example — ABA-115

Take the ABA-115 ticket: the Model tab v1 feature. Seven sub-tasks:

1. UI shell (no skill change)
2. Skill schema change — emit `historical_fcf_margins[]`
3. Re-run covered tickers
4. CAGR glidepath chart
5. FCF margin trajectory chart
6. Scenario fan chart
7. Captions and styling

### Running the seven questions

- **Q1 (count):** Seven sub-tasks. Multi-slice.
- **Q2 (sequential or parallel):** Sub-tasks 1, 2, 3 are arrows (UI consumes schema; schema requires re-run). Sub-tasks 4, 5, 6 are parallel-safe — each consumes the same JSON contract from sub-task 3. Sub-task 7 follows the rest.
- **Q3 (same-file overlap):** 4, 5, 6 each touch their own chart component file. No overlap.
- **Q4 (one-way door):** Yes — sub-task 2 changes a JSON contract field. Plan-review gate required.
- **Q5 (mechanical or subjective):** 1–3 are mechanical (JSON field present, audit row matches). 4–7 are subjective (chart legibility). Reviewer pass scheduled for after sub-task 7.
- **Q6 (implementation or spike):** Implementation.
- **Q7 (coordinator-agent shape):** Drafting the orchestration line — does it name an agent that dispatches other agents? No, the lead spawns teammates directly. Fine.

### The orchestration line

`plan-review → chain(1-3) → team-of-3(4‖5‖6) → chain(7) → chart-reviewer pass on UI`

### Where each guard fires

```
   plan-review (Q4 + Q7)
        │
        ▼
   chain(1-3) ──→ gate check ──→ team-of-3(4‖5‖6) ──→ gate check ──→ chain(7) ──→ chart reviewer (Q5)
                       │                                   │
                  Reads AC of                         Reads AC of
                  sub-task 3.                         sub-task 6.
                  git diff scan                       git diff scan
                  for any commit                      against teammate
                  touching files                      "files to touch"
                  outside sub-task                    lists. Cross-slice
                  3's scope.                          bug fold = abort.
```

The chart reviewer at the end catches label collisions and axis blowouts before merge — the kind of defects a mechanical acceptance check re-passes because it checks for presence, not readability. The gate check between team and chain catches bugs silently folded across phase boundaries: any commit touching files outside the active phase's scope aborts the gate before the next phase starts.

---

## 7. Limitations

Three limitations worth naming before you rely on this checklist:

### Risk → which question catches it

| Risk | Caught by | Strength |
|------|-----------|----------|
| Coordinator-agent plan assumes platform capability that doesn't exist | [Question 7](#question-7--does-the-plan-describe-an-agent-dispatching-other-agents) + plan-review gate | Strong — the question is mechanical and the gate runs before any code |
| Bug from an earlier sub-task silently bundled into a later sub-task's commit | The "do not silently fold" rule in the ticket plan + 15-second `git diff --stat` eyeball before each commit | Partial — depends on a written rule the agent must remember to follow |
| Subjective defect (overlapping labels, axis blowout) passing mechanical acceptance | [Question 5](#question-5--are-the-acceptance-checks-mechanical-or-subjective) + the [chart reviewer prompt](#chart-prompt) | Strong — reviewer never sees the original acceptance criteria, so it can't re-pass the same checks |

### Caveats

**The bundled-fix problem is mitigated, not eliminated.** The rule about separate attributed commits is in the ticket plan, but it's still a written rule the agent has to remember to follow. The short-term mitigation is fifteen seconds of you reading the staged diff yourself before each commit lands. The durable fix is a `PreToolUse` hook that rejects any commit touching files outside the assigned sub-task's scope. The hook is about a cycle's worth of work and is worth building if the manual diff-read isn't catching things after a couple of cycles.

**Agent-team costs are not measured.** Anthropic hasn't published per-token figures. The rough mental model is roughly N+1× a single session for N parallel teammates, but that's a guess, not a number. Rule of thumb: only run agents in parallel when each parallel sub-task would take an hour or more of work on its own. Otherwise run them sequentially. The token cost is roughly the same either way — you only buy back wall-clock time by parallelising.

**Agent teams use an experimental flag.** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` could be removed or renamed without warning. If it goes away, the fallback is to run the same sub-tasks sequentially in single sessions. The checklist still works; only the parallelism goes away.

---

## 8. Reference

If this guide doesn't answer a question, the depth is in three companion files in the same folder:

- **[`pattern-map.md`](pattern-map.md)** — the research-grade version of this guide. Read this if you want the formal axis definitions (A1–A7), the decision-tree leaves (L0–L7), the activation triggers, and the three worked examples in their original level of detail. It's denser and uses internal codes, but it's authoritative.

- **[`landscape.md`](landscape.md)** — the catalogue of every Claude Code orchestration primitive (single session, sub-agents via the Agent tool, custom sub-agents, agent teams, hooks, skills, slash commands, the `/batch` command, MCP servers, channels, Agent SDK, worktrees, the agent view, plus third-party tools). Includes platform constraints, cost notes, and setup friction. Read this when you need to know what an agent team actually is or what `/batch` does.

- **[`critique.md`](critique.md)** — the stress-test of the recommendation. Read this if you want the "what could still go wrong" view, the items that didn't fully close, or the reasoning behind why certain things were deferred.

The three reference files go deeper on the reasoning and the primitives. This guide is what you actually run during cycle planning.

### Quick glossary

| Term in this guide | What it is |
|--------------------|------------|
| Sub-task | One numbered item in a Linear ticket's `plan.md` |
| One-way door | A change that's expensive to reverse (schema field, public command name, methodology constant, frontmatter key, anything in `DESIGN.md`) |
| Chain | Multiple sub-tasks in a single session with explicit gates between them |
| Team | Agent teams primitive — top-level lead plus 3–5 teammates running in parallel |
| Composition | A ticket that mixes chain and team phases — most common shape in this repo |
| Reviewer pass | A fresh-context second look at subjective output using one of the prompts in [Section 5](#5-reviewer-prompts) |
| Gate check | The three-step procedure at each phase boundary: read the prior phase's acceptance criteria, scan `git log` for cross-phase bug folds, name the next shape out loud |
