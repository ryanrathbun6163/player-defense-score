# Working Agreement

## Communication

Ryan is technically capable but is refreshing hands-on software engineering, Git, Python, computer vision, and ML. Use plain language first, then introduce the exact technical term. Explain what a command changes, why it is needed, what success looks like, and how to recover if it fails.

When Ryan must run a command manually:

- prefer one copyable PowerShell command;
- use repository-, branch-, HEAD-, input-, and output-guards when risk warrants it;
- do not hide meaningful behavior inside an unexplained wall of shell code;
- ask for the complete terminal output;
- never assume the command ran until its effects are verified.

Ryan values quality and context preservation over speed for ambiguous architecture, identity, geometry, validation, and scoring decisions.

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
