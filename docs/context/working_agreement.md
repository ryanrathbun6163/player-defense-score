# Working Agreement

## Resource policy and engineering effort: Ryan's 2026-10-05 clarification

Ryan is comfortable devoting substantial computer resources to the project,
while keeping computer safety a high priority. Operational timings are design
choices, not scientific accuracy requirements. Before pursuing repeated or
increasingly complex optimizations to satisfy a timing setting, compare the
cost with a simpler monitoring-policy or architecture change and explain the
tradeoff to Ryan. Existing limits remain effective until the change is approved;
they do not prevent proposing an amendment. Do not retroactively change failed
results, consumed budgets, scientific gates or sealed evidence.

Ryan approved the responsive-monitor revision after this comparison. Its
separate policy retains frequent safety checks while allowing slower complete
storage accounting; implementation/validation do not authorize Git mutations
or a real scientific execution. See `../ball_crop_candidate_retention_monitor_revision.md`.

## Failure handling: Ryan's 2026-10-05 instruction

Ryan explicitly instructed: "You are allowed to move and NOT stop on any
failures, only stop on failures that are large and issues you feel deserve an
actual investigation."

This supersedes earlier blanket stop-on-any-failure instructions. Correct
ordinary tooling, command and helper problems within approved scope without
repeated permission requests. Preserve failed evidence, explain meaningful
corrections simply, and verify the resulting work. Rerun affected checks when a
real correction warrants it; do not repeat completed work merely for resumption.

Pause for issues that materially affect correctness, evidence integrity,
resource limits, or the approved scope. This change does not authorize Git
mutations, scientific body access, new experiments, renewed consumed attempts,
budget resets, weakened gates, or reopening completed visual reviews. Apply
Ryan's latest explicit scope and approvals rather than treating historical
failure instructions as permanently binding.

## Communication

Ryan is technically capable but is refreshing hands-on software engineering, Git, Python, computer vision, and ML. Use plain language first, then introduce the exact technical term. Explain what a command changes, why it is needed, what success looks like, and how to recover if it fails.

When Ryan must run a command manually:

- prefer one copyable PowerShell command;
- use repository-, branch-, HEAD-, input-, and output-guards when risk warrants it;
- do not hide meaningful behavior inside an unexplained wall of shell code;
- ask for the complete terminal output;
- never assume the command ran until its effects are verified.

Ryan values quality and context preservation over speed for ambiguous architecture, identity, geometry, validation, and scoring decisions.

Teach as the project progresses: give short, simple explanations of what we are
doing, why it matters, and where it fits in the overall project. Introduce new
terms with a concrete example, keep implementation detail digestible, and
explain meaningful choices and tradeoffs so Ryan can suggest changes and help
direct the work. Carry this teaching preference across sessions.

## Git workflow

Use this sequence, with explicit approval between mutating steps:

1. inspect branch, HEAD, status, and relevant diffs;
2. edit on a narrowly scoped feature branch;
3. validate code and artifacts;
4. propose exact staging scope;
5. stage only after approval;
6. show the staged diff and checks;
7. commit only after approval;
8. push only after approval;
9. create a PR only after approval;
10. merge only after Ryan reviews and approves.

Never push directly to `main`. Do not bundle staging, committing, pushing, PR creation, or merging into a single implied authorization.

## Artifact hygiene

- Keep raw video and generated outputs under ignored `data/` paths.
- Remove only clearly temporary downloaded/obsolete ZIPs after their contents and successful application are verified.
- Avoid accumulating `__pycache__`; prefer `PYTHONDONTWRITEBYTECODE=1` for diagnostics.
- Do not delete a review artifact merely because a newer one exists unless its role and recoverability are confirmed.
- Hash important uploaded/downloaded packages when they are used as review evidence.

## Review responsibilities

The agent should perform structural, numerical, code, and artifact checks. Ryan makes final visual judgments about whether identity, court mapping, trajectories, and future ball tracks look correct. Present narrowly targeted review material: exact frames, time ranges, candidate pairs, or synchronized videos.

## Session continuity

At a stopping point, record:

- current branch and exact HEAD;
- clean/dirty/staged/untracked status;
- last command actually completed;
- commands supplied but not run;
- validation results;
- generated artifacts that exist and their hashes when important;
- unresolved human-review decisions;
- exact first action for the next session.

This prevents a later task from confusing a proposed action with a completed one—a failure mode that occurred during the historical ReID review handoff.

## Traceability

- Ryan's background and learning goal: Chat 01, messages `29214222-c0f2-4448-bf20-7ade7be4c86a` and `e1a9d25d-052c-476c-81e3-38b2d0524e58`.
- Explicit workflow rules: Chat 05, message `a0b4f63f-838f-49f5-a825-e4f2bfb1f971`.
- Example of an unrun command preserved as a checkpoint: Chat 05, messages `83152b6e-f4df-4507-b17f-e3cf4a8b2514` and `d7e48921-b96a-59c9-9fc6-93e0708c19cd`.
