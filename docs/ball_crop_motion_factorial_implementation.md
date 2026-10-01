# Crop motion factorial: implementation checkpoint

Ryan approved the exact saved-candidate comparison with "I approve chat".
The separate receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_motion_factorial_approval_v0_1.json`.
The approved proposal/design retain their original historical status and bytes.
The executable manifest is
`configs/ball_tracking/crop_motion_experiments/rfdetr_medium_crop_motion_factorial_v0_1.json`;
its specification digest, excluding the authorization binding, is
`51bc58477f5e1273e4ec83588003861f3b095ae46923b46915905ca4600f829f`.

This experiment is part of the ball-observation foundation. It asks whether
allowing more movement, penalizing it less, or their interaction explains the
previous tight/wide differences. It does not establish ball identity, a quality
gate, possession understanding, matchup inference or defensive scoring.

## Implementation

`src/ball_tracking/crop_motion_factorial.py` implements the exact seven-arm,
nine-threshold grid. The four history arms independently set edge allowance
and motion-cost normalization to .01 or .03 source diagonals per elapsed frame.
Normalization is never clipped: the wide-edge/tight-cost setting can have a
normalized step of three and a per-edge cost of 2.25. The five-frame horizon,
top-twenty cap, gap costs, singleton starts, deterministic ties, and empty
hypothesis preserve the existing contract. Original coordinates, confidence
and candidate references remain unchanged. An earlier endpoint emits null.

All five existing controls are mapped explicitly. Behavioral parity compares
complete saved traces, including paths, edges, component scores, alternatives,
margins, candidate dispositions and null reasons. Only declared schema,
configuration names, variant identifiers and code-provenance metadata differ.
Equal-parameter controls preserve arithmetic and traversal order.

`crop_motion_experiment.py` validates the exact approval and inherited six
window/input bindings. Selection reads saved candidates and metadata only;
annotation content, scoring-pool content, source pixels, and model loading
remain outside that stage. The runner verifies saved control file hashes and
crop-content digests, refuses altered existing outputs before resuming, and
requires a clean committed implementation checkpoint for execution. The
read-only dry run invokes no ranking and creates no experiment output.

`crop_motion_evaluation.py` uses unchanged raw-center matching and the five
existing radii. It checks all 1,350 saved control report cells, 270 complete
control traces and 450 saved aggregate cells. Representative and challenge
pools remain separate. Reports include candidate/cap/ranking loss partitions,
graph-versus-control gains/losses, and four same-cell motion-factor comparisons:
vary allowance at each fixed cost, and vary cost at each fixed allowance.
There is no new threshold selection or significance claim.

`crop_motion_review.py` provides a 3-by-3 comparison: seven arms, unmarked
source and legend. Both motion parameters appear on every history panel.
Twelve clips must each decode all 25 frames at 5 fps. The 3,012-asset package
contains those clips plus 3,000 PNGs: native overlays, exact unmarked source,
source-scale closeups and comparisons. Alternatives and null reasons remain
visible; scores are explicitly not probabilities. Inventory, hashes, source
bindings and final frames are validated before reuse. Human review begins
pending; synthetic layout checks do not approve real tracking quality.

## Validation

All 23 focused tests pass (191.201 seconds). The full suite runs 386 tests:
385 pass and one existing Windows directory-symlink test skips (482.413
seconds). Tests use
`.venv` Python with bytecode disabled. Coverage includes an independent
exhaustive small-graph oracle for all four parameter pairs, unclipped motion
cost, complete legacy control traces, ties, gaps, causality, window resets,
cap loss, immutable candidates, hidden-frame false alarms, label-free
selection, malformed scope/approval/input refusal, all nine embargoes,
partial resume, and changed-output refusal.

Synthetic integration generated 378 outputs, 1,890 reports, 315 aggregate
cells per pool, and all 3,012 review assets. All 270 trace, 1,350 report and
450 aggregate control comparisons passed. All 12 clips decoded 25 frames at
5 fps. The agent inspected the comparison and source-faithful closeups; the
unmarked source PNG was checked against the exact synthetic pixels. This
validates structure and behavior, not real tracking quality.

The actual-input dry run confirmed six windows, 150 frames, 63 variants and
zero detector calls. The new real output root remains absent.

Ignored test logs, synthetic previews and the final checkpoint audit belong
under `data/outputs/ball_tracking/crop_motion_implementation_validation/`.
`checkpoint_audit.json` records the exact worktree scope, preserved evidence
and context history, source/test hashes, successful logs, JSON/Python parsing,
whitespace, and the actual dirty-checkpoint execution refusal. It verifies
71 protected non-context files against Git/SHA-256 bindings, all 270 saved
ranking outputs, both scoring pools, six crop/whole-frame inputs and labels,
and the four existing untracked evidence/design files. The index is empty,
all nine embargo paths remain absent, and three holdouts remain sealed.

## Proposed Git scope

These 15 files form the checkpoint, including the existing unstaged closeout:

1. `configs/ball_tracking/crop_motion_experiments/rfdetr_medium_crop_motion_factorial_v0_1.json`
2. `configs/ball_tracking/proposals/rfdetr_medium_crop_motion_factorial_v0_1.json`
3. `configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_ranking_visual_review_record_v0_1.json`
4. `configs/ball_tracking/reviews/rfdetr_medium_crop_motion_factorial_approval_v0_1.json`
5. `docs/ball_crop_candidate_ranking_results.md`
6. `docs/ball_crop_motion_factorial_proposal.md`
7. `docs/ball_crop_motion_factorial_implementation.md`
8. `docs/context/current_state.md`
9. `docs/context/roadmap.md`
10. `docs/context/validation_history.md`
11. `src/ball_tracking/crop_motion_factorial.py`
12. `src/ball_tracking/crop_motion_experiment.py`
13. `src/ball_tracking/crop_motion_evaluation.py`
14. `src/ball_tracking/crop_motion_review.py`
15. `tests/test_ball_crop_motion_factorial.py`

The three intentional context edits retain their earlier notes. Existing
production code, tests, reviewed labels, permits, proposals and generated
experiment baselines remain unchanged. Generated files stay ignored.

## Next action

After validation, obtain separate authorization to stage this exact scope,
then separate authorization to commit it. The existing experiment approval
covers selection/scoring/rendering after that clean implementation checkpoint;
do not ask for the experiment scope again. It authorizes no Git mutation.
Pushes, PR creation and merges remain separate decisions.

The subsequent approved run expects 378 derived outputs, 1,890 per-window
reports, two 315-cell pools and the new 12-clip review package. Ryan reviews
all new clips through their final frames. Do not rerun the completed crop or
ranking experiment, change an operating point/gate, or access sealed holdouts.
No upstream reviewed player decision changes, so no player-pipeline
`--rerun-from` action is needed.
