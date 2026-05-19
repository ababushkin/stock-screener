# Critique — stress-test of orchestration recommendations

Stress-testing `landscape.md` (landscape-researcher) and `pattern-map.md` (pattern-mapper) against the user's actual constraints:

- **Cadence:** ~one cycle every 1–2 weeks. Any recommendation that requires multi-hour setup amortised across many cycles is suspect.
- **Platform reality (Claude Code):** sub-agents cannot spawn sub-agents. Only the top-level session can fan out. Anything that implies "supervisor sub-agent dispatches workers" is platform-invalid.
- **Repeatability bar:** the user wants something they can apply during cycle planning without thinking hard each time. Patterns that need fresh judgement per cycle don't clear the bar.

## Reference failure modes the recommendation MUST prevent

These are the three failures from the just-finished cycle. Any recommendation that doesn't prevent all three is a partial solution and should be marked as such.

### F1. Architectural deviation, silent
The lead designed a "supervisor sub-agent that spawns implementor sub-agents." Claude Code doesn't support that — sub-agents can't spawn sub-agents. The supervisor improvised inline (collapsed two layers into one) and didn't escalate. User learned of the deviation only in the final report.

**What prevents this:** a check at *plan-approval time* that the architecture is platform-feasible — and a stop-the-line rule that any sub-agent which cannot execute the assigned shape must escalate before improvising. A recommendation that only governs implementation but not plan shape doesn't catch F1.

### F2. Latent bug folded silently into wrong commit
A NaN SVG crash caused by ticket 1's code was caught during ticket 2's verification and folded into ticket 2's commit. The bug→fix mapping is gone from git history.

**What prevents this:** a discipline that says "a bug discovered during work on ticket N that originated in ticket M produces a *separate* commit (and ideally a Linear issue or note) attributed to M." A reviewer sub-agent that "checks the diff" won't catch this — by the time they review, the merge has already obscured the origin.

### F3. User caught what the agent missed (Y5 label collision)
A visible Y5-axis label-collision bug in the chart was spotted by the user. The acceptance criteria were mechanical (monotone, cap callout, pre-profit guard, three lines) — they didn't ask "is the chart legible?"

**What prevents this:** acceptance criteria that include a *subjective render check* on visual output — e.g. "screenshot at canonical size; does it pass the squint test." A reviewer sub-agent that uses the same mechanical criteria as the implementor will miss it too — the failure is in the criteria, not the reviewer.

## Holes I'm watching for

(populated as drafts land)

- "Add a reviewer sub-agent" without specifying *what the reviewer checks that the implementor doesn't*. If the reviewer applies the same criteria, F3 reproduces.
- "Coordinator sub-agent spawns workers." Platform-invalid (F1 again).
- "Each agent owns one ticket." Doesn't prevent F2 unless there's an explicit rule about cross-ticket bug attribution.
- Hooks the user has to author per cycle. Setup cost > benefit at this cadence.
- Custom skills, MCP servers, or Agent SDK builds that take >1 cycle of setup to amortise.
- "Plan review" steps that produce documents nobody reads — the lead/user already retros after the fact; what's missing is a check *before* the work starts.
- Recommendations that describe an ideal end state without a "first thing the user does next cycle" entrypoint.

## Per-draft critique

### landscape.md

Solid catalogue overall — the four platform constraints at the top (especially #1 sub-agent recursion and #2 agent-team teammate non-spawning) directly inoculate against F1, and the table is consistent. The "Honest gaps" section is genuinely honest. Below are the holes that matter for the eventual user-facing recommendation.

#### C-LS-1 (HIGH) — The June 15 2026 SDK billing change is buried and is *the* relevant decision-cost trigger for the user *this* cycle

Line 64 mentions: *"from June 15, 2026, subscription-plan Agent SDK and `claude -p` usage draws from a separate monthly Agent SDK credit pool, not the same interactive limits as Claude Code itself."*

Today is 2026-05-19. That's 27 days away. Any recommendation that suggests "build an Agent SDK orchestrator" *this cycle* is about to walk into a billing-model change the user hasn't budgeted for. The pattern-map (correctly) doesn't recommend SDK for any L0–L7 leaf — but landscape.md doesn't escalate this enough. It reads like an interesting fact, not a planning constraint.

Recommend: lift the billing date into the platform-constraints block at the top (alongside the "no nested subagents" constraint), framed as: *"5. Agent SDK billing changes June 15, 2026 — if you're picking a pattern that uses the SDK at all, this is a TCO decision, not just an interface decision."* This is the exact category of fact the user needs at planning time.

#### C-LS-2 (HIGH) — "Setup friction: Low" is doing too much work; several "Low"-tagged rows hide multi-hour first-time setup

Several rows are tagged "Low" friction in ways that aren't honest at the user's cycle cadence:

- **Channels (line 30):** "Medium — Bun, plugin install, sender allowlist, org enablement on Team/Enterprise." Read the last clause: *org enablement on Team/Enterprise.* If the user isn't on Team/Enterprise (the email is personal `@gmail.com` per the env), channels are *unavailable*, not Medium. This should be a hard gate, not a friction tier.
- **Custom skills (line 25):** "Low — one folder per skill." True for the artefact, but `SKILL.md` skills compete for the 25k-token description budget (line 58), and the doc itself notes this. "Low setup, ongoing description-budget tax" is the honest framing.
- **MCP servers (line 29):** "Low–medium per server (config + secrets)." Per server, sure. But the doc doesn't note that adding an MCP server is *also* a tool-description-budget tax on every session in that scope. The honest framing for a user at this cadence: each MCP server is a permanent context-budget cost the moment it's enabled.
- **Custom subagents (line 21):** "Low — one markdown file with frontmatter." True. But the doc doesn't note that custom subagents that reference `skills:` and `mcpServers:` behave *differently* as teammates (those fields silently drop per platform constraint #4, line 12). The cost of this isn't setup — it's debugging time when the same role behaves differently in two contexts.

Recommend: split "Setup friction" into two columns — *first-time setup* (one-off) and *ongoing context-budget tax* (recurring). At the user's cycle cadence, recurring is the more important number.

#### C-LS-3 (MEDIUM) — v2.1.32+ version requirement on agent teams is unsourced and load-bearing

Line 22: *"Medium — env var `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, requires v2.1.32+."*

Agent teams is the central new primitive the pattern-map recommends (L5, L6 Path A). If the user's Claude Code is older than v2.1.32, the entire L5 leaf doesn't work and silently falls back. The doc lists 17 sources at the bottom but I cannot tell which one(s) actually verified that version number. This is exactly the agentic-engineering "hallucination is the default" failure mode — a specific version number that *might* be plausible interpolation rather than fact.

Recommend: either (a) add an inline source link for the version requirement, or (b) soften to "requires a recent Claude Code version that has the experimental flag — verify with `claude --version` before planning around L5."

#### C-LS-4 (MEDIUM) — Cost column is acknowledged as "relative ordering, not measurement" but the pattern-map treats it as measurement

The "Honest gaps" section at line 86 says: *"Treat the cost column as relative ordering, not measurement."* But the pattern-map (and the synthesis the lead will eventually write) reads "≈ N+1× per teammate" as a number it can plan against. The two docs need to agree on this. Either landscape.md gets concrete numbers (it can't — Anthropic hasn't published them), or pattern-map.md needs to stop quoting "≈ N+1×" as a planning fact.

This isn't landscape.md's bug — it's a synthesis bug between the two docs. Flagging here so the lead handles it. The number to remove is in pattern-map line 138 and line 267.

#### C-LS-5 (LOW) — Third-party tools (Squad, opencode, Aider, Roo, tmux orchestrators) take 6 rows but are noise at the user's cadence

Rows for Claude Squad, opencode, Aider, Roo Code, and "Other tmux orchestrators" each represent a separate third-party tool to learn. At one cycle every 1–2 weeks, picking up a new third-party tool is itself a cycle's worth of cost. None of these survive a "would I start this next cycle?" filter.

Recommend: in a separate "third-party orbiters (do not adopt without standalone justification)" section, collapse the five rows into one paragraph noting their existence and the conditions under which they'd be worth re-evaluating (e.g. "if Claude Code adds a hard limitation you can't work around" / "if you want to mix providers"). This frees the catalogue to focus on the patterns the user might actually choose.

#### What landscape.md gets right (don't change)

- Platform constraints block at the top is excellent — exactly the right discipline. Constraint #1 (no sub-agent recursion) and #4 (teammate frontmatter drops skills/mcpServers) are the two things that *will* burn the user if they don't know them.
- "Honest gaps" section is real (line 84). Don't sand it down. The fact that the doc names uncertainty about `/batch`'s actual availability (line 88) is the right register.
- Splitting "Hooks (enforcement)" from "Hooks (orchestration glue)" is the right call — they're the same primitive used for very different things, and most landscape docs conflate them.
- The "Best for / Worst for" columns on each row are genuinely useful — they're what the pattern-map ended up using. Keep.
- The deeper notes per pattern (lines 46–80) are where the real signal is. The table is the index; the notes are the document.

---

## Final sweep — v3 pattern-map.md + v2 landscape.md

### pattern-map.md v3

| Concern | Status |
|---|---|
| C-PM-1 (L0 trigger doesn't catch F1) | **CLOSED.** A7 axis added (line 29); L0 trigger expanded to "A4 OR A7 OR A1 ≥ 2" with explicit reasoning (line 43–45); concrete L0 reviewer checklist added (lines 52–54). |
| C-PM-2 (F2 rule-based vs mechanical) | **CLOSED.** Lines 122 and 145 now explicitly say "partially mitigated, not prevented" and add a 15-second human commit gate ("operator runs `git diff --stat`, asks 'is anything in this diff from a prior slice?'"). Full mechanical prevention deferred to Part 5 hook. |
| C-PM-3 (canonical squint prompts) | **CLOSED & EXPANDED.** Part 3.5 ships three full verbatim prompts (charts / narrative / tabular) with rules of use and worked-example annotations. Chart prompt explicitly claims it would have caught Y5 endpoint collision and AMZN axis blowout. |
| C-PM-4 (L5 pre-flight ownership) | **CLOSED.** Line 138: "lead runs this once before assigning tasks." |
| C-PM-5 (L7 phase-transition procedure) | **CLOSED.** Lines 182–188 add a four-step phase-transition checklist (gate read, cross-slice diff scan, next-phase pattern restated, dispatch) at ~90 sec/transition. |
| C-PM-6 (A4 missing orchestration shape) | **CLOSED via A7 axis.** |
| C-PM-7 (L5 cost heuristic) | **CLOSED.** Line 148: explicit "use agent teams when (a) each slice ≥1 hour AND (b) operator wants wallclock back; otherwise sequential L4 — same total tokens." |
| C-PM-8 (experimental-flag fallback) | **CLOSED.** Line 136: "Fallback if agent teams unavailable: demote L5 to N sequential L2/L3 single-sessions." |
| C-PM-9 (`/batch` vs teams test fuzzy) | **NOT ADDRESSED.** L6 still uses "mechanical?" as the test. LOW severity — letting go. |

**v3 nits (not worth blocking):** Line 220 in the ABA-115 worked example says "the optional `PreToolUse` git hook prevents F2" — but Part 5 lists the hook as deferred. Honest reading is "would prevent if implemented." Minor tense issue; doesn't materially mislead.

### landscape.md v2

| Concern | Status |
|---|---|
| C-LS-1 (June 15 SDK billing buried) | **CLOSED.** Added as platform constraint #6 (line 14) with explicit "27 days from today" framing. Opening sentence updated: "platform-invalid (or, for #6, billing-invalid)." |
| C-LS-2 (Setup friction column too coarse) | **PARTIAL → ACCEPTED.** Column not split into two, but specific rows enriched inline: custom subagents (line 22) and custom skills (line 26) now have "One-off: Low. Recurring: [specific budget tax]." The pattern is right; not every row needs it. Landscape-researcher also corrected my over-claim on channels: personal claude.ai accounts get channels automatically; only org-managed are admin-gated. My critique was sharper than the truth — corrected honestly in their revision. |
| C-LS-3 (v2.1.32 unsourced version) | **CLOSED.** Softened to "a recent Claude Code version with the experimental flag (verify with `claude --version`)" — exact language I suggested. |
| C-LS-4 (cost column treated as planning fact) | **CLOSED by pattern-map.md** — pattern-map's L5 cost heuristic now frames the ≈ N+1× as a deliberate spend with a "use when ≥1hr + wallclock matters" gate. Landscape's "Honest gaps" stays as-is — correct division of responsibility. |
| C-LS-5 (3rd-party rows) | **NOT ADDRESSED.** Kept. LOW severity — reasonable to leave. |

**New v2 content reviewed:** The "default ~1% of model context window; overflow truncates *other* skills' descriptions" claim on line 26 is new and specific. Cannot directly verify, but is consistent with the cited Skills docs and matches plausible doc-language. Accepting.

### Net verdict

Both documents are in good shape. All HIGH concerns closed. MEDIUM concerns closed or honestly downgraded. The two LOW items still open (C-PM-9 mechanical-test wording, C-LS-5 third-party rows) are non-load-bearing.

The MUST 1–3 items in my message to team-lead remain the load-bearing surfacings. The teammates' revisions reinforce all three rather than undermine them — pattern-map.md v3 makes MUST 1 and MUST 2 *easier* to surface in the final recommendation by giving them explicit hooks in the document (the "partially mitigated" framing on L4/L5 and the A7 axis + L0 always-on-multi-slice rule).

No remaining holes worth blocking on. Devil's advocate role complete.

### pattern-map.md

Strong skeleton overall — six axes are well-chosen, the L1–L7 leaves are crisp, and the 60-second ritual is genuinely repeatable. Below are the holes I found that I think matter enough to surface.

#### C-PM-1 (HIGH) — L0's trigger is wrong; it must fire on orchestration shape, not just one-way doors

Per pattern-map line 43: *"Leaf L0 — One-way door of any kind. Trigger: A4 = yes."*

This means L0 fires only when A4 (one-way door) is true. But the ABA-115 failure (F1, "supervisor spawns implementor") was *not* triggered by a one-way door per se — it was triggered by *the lead choosing an infeasible orchestration shape during planning.* If the same lead designs a "supervisor spawns N implementors" plan for a future feature that has *zero* one-way doors (say, five independent UI tweaks across five components, all reversible), nothing in the current decision tree fires L0 — the plan would route straight to L5 or L6, and the platform-invalid supervisor layer would never be reviewed.

**The structural bug:** F1 is a deviation between the *planned shape* and the *platform's capabilities*. That bug is independent of one-way-doorness. L0's trigger must include something like:

> **A7 (new): Does the plan name a "supervisor sub-agent," a "coordinator sub-agent that spawns workers," or any pattern where a sub-agent dispatches other sub-agents?** If yes → L0 plan review, regardless of A4.

Or, more robustly: the 60-second ritual's *output line* should be a pattern leaf name (L1–L7) from this map — and any line that doesn't match a defined leaf goes through L0 by default. Right now the ritual lets the planner write a free-form orchestration plan into `plan.md`, which is exactly the surface where ABA-115's failure originated.

#### C-PM-2 (HIGH) — F2's "separate commit" rule is unenforced and depends on the same agent that violated it

Pattern-map line 109 (L4) and line 126 (L5) carry the F2 rule. Line 251 acknowledges:

> "F2 enforcement. Currently a *rule* the agent must follow. A hook ... could mechanically refuse to commit a diff that touches files outside the assigned slice's 'Files to touch' list. Out of scope here — flag to user as a future hook candidate."

This is the most important failure mode in the recent cycle (it destroyed bug→fix provenance in git history) — and the proposed guard is "the agent should follow a rule we wrote down." That's exactly the discipline that *already failed* in ABA-138. The agent that folded the NaN fix into the wrong commit had access to the same rules; what was missing was a mechanical check.

I don't think the user will write the hook on cycle one. But the recommendation needs to either (a) acknowledge that F2 is **partially mitigated, not prevented** at the recommendation level, or (b) propose a lighter-weight mechanism than a hook — e.g. *"the lead must read `git diff` against the assigned 'Files to touch' list before approving the commit"* — which is a human gate, not an agent rule.

The current text implies F2 is solved at L4/L5. It isn't.

#### C-PM-3 (HIGH) — L3's "differently-shaped second pass" only works if the planner wrote the squint prompt; planner exhaustion is the obvious failure mode

Line 91: *"The second pass MUST NOT re-apply the mechanical acceptance criteria."*
Line 240: *"the squint-test prompt (if step 5 fired) — pre-written, so the L3 reviewer has it ready."*

Two problems:

1. **The squint prompt is the load-bearing part of L3.** If the planner is tired and writes a generic "review this for legibility" prompt — or worse, copy-pastes the original AC — the L3 reviewer reproduces the F3 blind spot exactly. The pattern moves the failure from implementor to reviewer; it doesn't eliminate it.

2. **There's no library of squint prompts.** The user is expected to write a tailored prompt per cycle. That's a non-trivial cognitive load — exactly the thing the document promises to avoid in the opening paragraph ("no fresh judgement per cycle"). At minimum, the pattern map should ship with 3–4 canonical squint prompts (one for charts, one for narrative output, one for tabular reports) the planner can pick from.

Concrete fix: add a section "**Canonical squint prompts**" with pre-written language for the most common subjective output types in this repo. For charts: *"Open the rendered chart at canonical viewport size. Without reading the underlying data, can you state the thesis in one sentence? Are any labels overlapping, clipped, or unreadable? Does any axis tick appear to collide with a callout?"* That's the specific shape the Y5 collision would have failed.

#### C-PM-4 (MEDIUM) — L5's pre-flight checklist is unenforced and lives in the wrong place

Line 123–127: L5's pre-flight checklist (different files, dependency landed, separate commits) is run by *who*, exactly? If it's the lead before fan-out, fine — but the document doesn't say. If it's the implementor agents, they have an incentive not to flag conflicts (it's faster to proceed). And the checklist sits *inside* the L5 leaf, meaning it gets re-discovered on every fan-out instead of being a ritual the user has memorised.

Recommend: move the pre-flight to Part 4 (the planning ritual) — make it part of step 6, so the user runs it once at planning time, not at fan-out time. The discipline is "plan the parallelism, then execute," not "decide to parallelise as you go."

#### C-PM-5 (MEDIUM) — L7 (compositions) is where deviation creeps in, and the doc acknowledges this without addressing it

Line 156: *"This is the most common shape this pack will produce ... Plan should *name the phase transitions* — they're the gate moments where F2 (latent bug) is most likely to surface."*

True. But what does the agent *do* at a phase transition? Right now L7 says "compose L4 and L5 explicitly in the plan." That's not a procedure — it's a label. Concrete fix: L7 should include a phase-transition checklist:

> At each L4→L5 or L5→L4 transition: (a) confirm prior phase's gate criterion is met (read the AC back); (b) check git log: did any commit in the prior phase touch files attributed to a *different* slice? (F2 detector); (c) re-state the next phase's pattern name; (d) only then dispatch.

Without this, L7 is decorative — and L7 is *also* the shape that produced the recent failure.

#### C-PM-6 (LOW) — A4's one-way door list is incomplete

Line 25 lists DESIGN.md, JSON contract, `playbooks/*.md` frontmatter, SKILL.md schema, public command name. Missing: **the orchestration choice itself for a multi-slice feature.** Once you've decided "this is L5 fan-out," walking back to L4 sequential mid-feature is expensive (already-spawned agents have state). The recommendation: A4 should include "orchestration shape for features with ≥4 slices" — these warrant L0 review at planning, period.

This overlaps with C-PM-1 — and is probably best solved together by routing *all* multi-slice plans through L0 by default.

#### v2 review — what closed, what didn't, what's new

**C-PM-1 — still open (partial close).** L0's trigger is still `A4 = yes` only (line 42). The A7 axis I proposed isn't there. The doc instead leans on `pde-plan-review`'s own auto-fire condition ("any plan with a one-way-door decision, or that breaks into more than a single independently verifiable slice"). That second clause is broader than the doc surfaces — and is the real F1 catcher. But this is *implicit*: the L0 leaf trigger as written would not fire for a 5-slice all-reversible feature. Recommend either (a) explicitly add to L0 trigger: "OR plan breaks into ≥2 independently verifiable slices" — which matches `pde-plan-review`'s actual behaviour — or (b) restate at the top of Part 4: "L0 always runs for multi-slice features, regardless of A4."

**C-PM-2 — partial close, improved.** Line 135 now names a concrete `PreToolUse` hook (one script, exit 2 on out-of-scope file). This is meaningfully better than v1's hand-wave. But the hook is still framed as "stronger guard" and is in Part 5 (out-of-scope follow-ups) at line 265. The *primary* guard remains the written rule in the teammate brief — the same shape as the rule that already failed. Recommend the doc explicitly mark in the F-guard block: *"F2 prevention is rule-based until the optional PreToolUse hook is in place — track recurrence."*

**C-PM-3 — closed.** Line 91 ships a concrete squint-prompt verbatim with the critical "you have not seen the acceptance criteria" instruction. Line 266 proposes the custom `squint-reviewer` subagent as a follow-up to remove per-cycle prompt-writing. Good fix.

#### New concerns introduced in v2

**C-PM-7 (MEDIUM) — L5 cost claim is uncalibrated and the leaf still recommends agent teams as default.** Line 138: "Agent teams are ≈ N+1× a single-session cost. Three chart teammates ≈ 4× a single session." Line 267 acknowledges this number isn't calibrated. For ABA-115 4/5/6, was wallclock actually binding? Three sequential single-session chart implementations would have been 3× a single session (no team overhead), versus 4× with the team — and at this cycle cadence (1 cycle / 1–2 weeks) the wallclock savings of doing them in parallel is probably a few hours, not days. The leaf needs a "when not to fan out" check: if the slices are small and sequential single-session would finish in the same operator-attention window, skip the team. Suggest a concrete heuristic in L5: *"Use agent teams when (a) each slice has ≥1 hour of implementation work AND (b) the operator wants the wallclock back. Otherwise, run them sequentially in L4 — same total token cost, simpler shape."*

**C-PM-8 (MEDIUM) — Experimental flag is a fragile foundation for the load-bearing leaf.** Line 124 names `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` as the activation mechanism. L5 is the central new primitive the recommendation introduces. If Anthropic changes or removes the flag mid-cycle, the user's planning ritual points at a non-existent primitive. Recommend the doc include a "fallback" line at L5: *"If agent teams are unavailable, demote L5 to N sequential L2/L3 single-sessions. The F-guards still apply; only the wallclock changes."* This is a one-line addition that makes the recommendation survive the experimental flag going away.

**C-PM-9 (LOW) — `/batch` vs agent-teams branching in L6 is reasonable but the test is fuzzy.** Line 157: *"For the playbook queue specifically: Path A. Each playbook is a different ticker with different sell-side debate axes; the work is not mechanical."* Fine for the specific case. But the *general* test "is this mechanical?" is exactly the kind of subjective call the doc is otherwise good at avoiding. Recommend a sharper rule: *"If the per-unit input fits in <100 tokens (e.g. just a filename, a ticker, a regex), use `/batch`. If it needs ≥200 tokens of context (a playbook brief, a domain narrative), use agent teams."* A token-count test is mechanical; a "is this mechanical?" judgement is not.

#### What pattern-map.md gets right (don't change)

- The six axes are the right level of resolution. I tried to add a seventh (cognitive-load axis) and couldn't justify it.
- A3 (same-file overlap demotes parallelism) is the kind of constraint people forget — keep it.
- The "Not on the list" cull (line 30) is correct discipline; runtime and engineer-count are red herrings.
- The three worked examples make the document concrete in a way pure rules wouldn't. Keep all three.
- The acknowledgement at line 251 that F2 enforcement is a future hook candidate is honest — but the *current* claim that L4/L5 prevent F2 should be softened to match.
