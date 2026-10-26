# Working Agreement

## Resolution approval and crash interruption, 2026-10-26

Ryan said "ok move forward with the experiment chat", approving the concrete
[resolution experiment](../ball_tracking_nba_resolution_execution.md). He then
reported a full PC restart distinct in symptoms from the earlier black screens.
The [incident record](../ball_tracking_nba_resolution_restart_2026-10-26.md)
confirms graphics bugcheck 0x116 and zero scientific updates. GPU work is
withheld in response to the observed crash; do not auto-retry or change settings.
This is an operational stop, not a claim of an explicit user training-pause
instruction. Preserve the corrupt summary and valid initial state. Continue
read-only diagnosis; substantial driver/hardware/remediation changes require
a concrete decision with Ryan. The campaign, labels and criteria stay approved.

## NBA diagnosis instruction, 2026-10-25

Ryan requested: "Ok chat, diagnose the remaining NBA misses and false detections,
then recommend our next training experiment. Keep the quality criteria unchanged."
The [completed diagnosis](../ball_tracking_nba_failure_diagnosis.md) includes a
monitored read-only original-weight control. The [768x432 next-fit proposal](../ball_tracking_nba_resolution_experiment.md)
is a recommendation, not training authorization. Existing criteria and accepted
labels need no renewed approval. Human visual acceptance and protected evaluation
remain separate; no new fit or labeling campaign follows automatically.

## NBA-first evaluation instruction, 2026-10-25

Ryan said: "Ok chat, let's move forward with NBA-first. Keep the high school work
and the same quality criteria, and evaluate our saved models on the existing NBA
labels before we do more training." Execute the
[saved-model comparison](../ball_tracking_nba_first_evaluation.md) within that
scope, reusing existing predictions and labels, monitoring any GPU inference,
and retaining all original high-school evidence and failed decisions. Do not
request the same scope or numerical-quality approval again. This instruction
does not authorize new training, new labels or protected evaluation. Present
concrete new trajectory reviews for Ryan's visual judgment.

## Current standing policy: Ryan's 2026-10-08 instruction

Ryan authorized a simpler, practical development workflow going forward. Complete routine path, formatting, report-limit, tooling, and implementation fixes without stopping for a recovery proposal or a new approval ceremony. Read the development data and compute the results needed to answer the current question, including recovery of already computed results after a delivery failure. Use the necessary computer resources safely, and integrate completed increments into the active project.

Validation should match the risk. Use focused checks for local corrections and check actual producer/consumer record formats when relevant. Run the full suite only when the breadth of the change or unresolved risk warrants it. Do not repeat a completed full run simply because a small correction followed it, and do not require routine RED/GREEN certificates, repeated release proposals, or a new validation framework to deliver an answer.

Earlier arbitrary timing, output-size, validation-budget, and read-access restrictions may be adjusted or removed when they obstruct authorized work without protecting a real scientific or computer-safety requirement. Retain practical memory, disk, process-ownership, and cleanup safeguards. Explain meaningful changes plainly. Bring substantial scientific, architectural, evidence-integrity, safety, or cost tradeoffs to Ryan for approval rather than escalating routine fixes.

This authorization does not erase history. Preserve actual failed attempts and resource consumption, original artifacts, uncertainty, and completed human/AI reviews. Keep a failed study marked failed even when its numeric results are recovered. Describe which code a prior validation covered. Keep holdouts separate from development decisions, do not weaken scientific thresholds to obtain a pass, and retain Ryan's visual judgments for identity, calibration, trajectories, and ball tracking.

This policy supersedes conflicting older operational rules, including blanket stop-on-failure instructions, scientific-body read bans, fixed-cap amendment requirements, and mandatory full-suite or certificate procedures. The two October 5 sections below are retained as historical context, not additional current approval gates. Git authorization remains governed by the current Git workflow below and Ryan's explicit session instructions.

## Quality and progress clarification: Ryan's 2026-10-08 instruction

Ryan accepts the current ball-phase finish line: reviewed trajectories across the three curated possessions, synchronized player/ball playback, explicit missing intervals, quantitative error summaries, and a repeatable configuration-driven run. He wants reliable ball tracking before moving to downstream phases. His concern is slow progress and repeated avoidable mistakes; it is not a request to lower the quality bar or change the scientific acceptance criteria.

The time since the last integration into `main` was an illustration of how long this phase has taken, not a request for more frequent within-phase merges. Keep useful local commits and choose main-branch integration around readiness and coherent scope under the existing authorization rules. Merge frequency itself is not the progress target.

Future visual review remains part of accepting actual new results. No opinion or approval is needed merely to acknowledge that responsibility. Present concrete review artifacts and a specific decision when Ryan's judgment is needed; retain completed reviews.

## Progress and usage clarification: Ryan's 2026-10-19 instruction

Ryan wants carefully designed experiments that produce concrete progress toward
the existing ball-phase finish line. He explicitly raised accumulated usage and
asked us to push harder while keeping the same requirements. Each experiment
should resolve a stated decision, reuse saved results and verified code where
possible, and use focused validation. Avoid repeated diagnostics, elaborate
release machinery or repeated approvals that do not advance that decision.
Efficiency does not authorize weaker quality criteria or skipped human review
of actual new trajectories.

## Completion-campaign approval: Ryan's 2026-10-21 instruction

Ryan explicitly approved the [completion plan](../ball_tracking_completion_plan.md)
and its proposed numerical ball-quality criteria, then requested a handoff so
execution can start in a new session. The
[approval record](../../configs/ball_tracking/reviews/ball_tracking_completion_campaign_approval_v0_1.json)
preserves the statement and exact approved plan revision. Do not ask for the
same campaign approval again. Prepare and integrate the authorized work in
batches, including the single conditional higher-resolution fit only when its
declared trigger holds. New references must be accepted before fitting; final
trajectories require human review. Protected evaluation still needs a frozen
method and separate explicit authorization. No campaign execution occurred
during the requested title/handoff turn. Prior reviews, failed attempts and
Git publication boundaries remain unchanged.

## Historical resource policy: Ryan's 2026-10-05 clarification

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

## Historical failure handling: Ryan's 2026-10-05 instruction

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

Use this sequence, applying existing session or standing authorization without asking repeatedly for the same permission:

1. inspect branch, HEAD, status, and relevant diffs;
2. edit on a narrowly scoped feature branch;
3. validate code and artifacts in proportion to risk;
4. report the exact local integration scope;
5. stage within Ryan's authorization;
6. show the staged diff and checks;
7. commit within Ryan's authorization;
8. push only with explicit authorization;
9. create a PR only with explicit authorization;
10. merge only after Ryan reviews and approves.

If local staging or committing has not been authorized, obtain that authorization. Never push directly to `main`. Authorization for local integration does not imply permission to push, create a PR, or merge. Report branch, HEAD, worktree status, and intended file scope before a Git mutation, then verify its exact result.

## Artifact hygiene

- Keep raw video and generated outputs under ignored `data/` paths.
- Remove only clearly temporary downloaded/obsolete ZIPs after their contents and successful application are verified.
- Avoid accumulating `__pycache__`; prefer `PYTHONDONTWRITEBYTECODE=1` for diagnostics.
- Do not delete a review artifact merely because a newer one exists unless its role and recoverability are confirmed.
- Hash important uploaded/downloaded packages when they are used as review evidence.

## Review responsibilities

The agent should perform structural, numerical, code, and artifact checks. Ryan makes final visual judgments about whether identity, court mapping, trajectories, and future ball tracks look correct. Present narrowly targeted review material: exact frames, time ranges, candidate pairs, or synchronized videos.

### Assistant first pass: Ryan's 2026-10-18 clarification

Ryan asked the assistant to take on more ball-tracking work and streamline the
process. Within approved development scope, the assistant should inspect source
images, propose first-pass ball labels, check records, fix routine problems and
prepare compact visual reviews before handing work back. Do not make Ryan enter
every frame manually or approve each mechanical step. Batch related work into a
reviewable result, explain uncertain cases plainly and handle requested corrections.

AI proposals must retain their actual authorship and source-frame evidence.
They are not independent human annotations or accepted reference labels. Keep
them separate from existing drafts and reviewed baselines until Ryan reviews
the proposed labels, missing intervals, uncertain cases and actual final frames.
Present complete short overlays alongside an exception list; reviewing only
flagged frames could miss confident AI mistakes. Never fill a hidden ball's
position merely by interpolating neighboring points.

This changes the division of labor, not the ball-phase quality bar. Human
acceptance, identity and calibration gates remain. Protected holdouts, approved
game roles, completed experiments and completed reviews retain their existing
boundaries. First-pass labeling does not itself authorize training or evaluation.

After Ryan accepts a proposal, record that later event and publish a separate
human-accepted AI reference. Preserve the original proposal, its prior status,
review media and blank human drafts. In model-output records, distinguish
reference authorship/acceptance from model authorship and model-output review;
accepted reference labels do not make new predictions visually accepted.

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
- Current operating policy: Ryan's 2026-10-08 standing instruction to fix routine delivery issues autonomously, use necessary development data/resources, test proportionally, preserve honest evidence, and bring substantial tradeoffs for approval.
- Example of an unrun command preserved as a checkpoint: Chat 05, messages `83152b6e-f4df-4507-b17f-e3cf4a8b2514` and `d7e48921-b96a-59c9-9fc6-93e0708c19cd`.
