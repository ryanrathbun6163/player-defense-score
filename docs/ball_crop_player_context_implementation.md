# Player-context comparison: implementation and release checkpoint

Ryan approved the exact proposed comparison with "I approve chat". The separate
receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_player_context_approval_v0_1.json`.
It binds the unchanged proposal SHA-256
`b41dd0094755de726db6de196c28376cdfc2bceb40b645b1ce91fa56a6be80e7`
and experiment specification
`7478fe4a3e5a3aaeb328c71b6ed1fe06db42dd3f904af17ca4ed13eb8a294e0d`.
The earlier proposal retains its historical proposed status; approval is a
separate record. No additional experiment-scope approval is needed.

This adds the approved soft distance cost to four motion configurations while
retaining original detector confidence, geometry, candidate order and null
observations. The same-frame player boxes are frozen offline reviewed inputs;
they do not identify a ball handler or establish an online player pipeline.
The new context term is a hypothesis under comparison, not a selected method,
operating point or quality gate.

## Implementation boundaries

Four new modules keep existing reviewed implementations unchanged:

- `src/ball_tracking/crop_player_context.py`: validated observed box context,
  the fixed normalized-distance cost, signed node utility, and audited ranking.
- `src/ball_tracking/crop_player_context_experiment.py`: exact scope/approval
  checks, source/context alignment, immutable inputs and resumable new outputs.
- `src/ball_tracking/crop_player_context_evaluation.py`: new-arm scoring and
  explicit comparisons with reused, unchanged motion controls.
- `src/ball_tracking/crop_player_context_review.py`: paired comparison clips,
  native context overlays and independent observed-player-box views using
  existing source/control images.

The selector receives candidate and observed rectangle inputs, without ball
annotations. Labels enter only scoring and review. Source files and reviewed
upstream decisions remain unchanged, so no upstream `--rerun-from` is needed.

The runner creates 216 new context outputs. Scoring creates 1,080 new per-window
reports and reuses 1,890 existing reports without recomputing them. Each separate
pool has 495 aggregate cells: 315 reused and 180 new. Reused records retain their
original execution provenance; they are not attributed to the new code commit.

The review uses twelve paired 4-by-3 comparison clips at the previously declared
.20/.35 display confidences and 10-pixel radius, with all 25 frames at 5 fps.
It reuses native PNG references for all seven controls and the unmarked source.
Crop raw/top-twenty remain native-only references outside the composite. Newly
rendered context/player/mosaic/closeup images belong to a distinct ignored root.
Ryan's visual review through each final frame will follow real execution.

## Validation checkpoint

All 34 focused tests passed, then the full suite passed 419 tests with one
existing Windows directory-symlink skip. Bytecode writes were disabled. The
core matches an independent exhaustive path oracle and reproduces complete
old motion traces when the context cost is zero. Integration tests exercise
the entire new synthetic output/report grid, preservation of every saved
control, source/provenance guards, interrupted resume and tamper rejection.

Review tests produced all twelve synthetic clips and decoded 25 frames at
5 fps from each, with 2,112 new assets and 2,400 reused native PNG references.
The renderer never invokes a selector, scorer, old renderer or source-video
decoder. Agent inspection of the final synthetic comparison, closeups and
player-box layout checked alignment, readable labels and the cost example.
This is structural validation; Ryan's real-data visual review remains pending.

The real-input dry run passed on all six approved windows/150 frames, with
selectors, scoring and media decoding disabled. It also confirmed the real
execution gate rejects the current dirty checkout. No real player-context
ranking, scoring or rendering has run; the real output root is absent. All
83 protected existing files and five prior untracked review/design files
remain unchanged. All nine original embargoes and three sealed holdouts persist.

A separate read-only check verified all 2,400 actual existing native/source PNG
bindings without decoding images or videos, recorded in
`saved_native_input_preflight.json`.

Actual logs and receipts are in
`data/outputs/ball_tracking/crop_player_context_implementation/2274ab6097cd/`.
`implementation_handoff.json` binds the final files, actual test receipts,
read-only preflight and synthetic QA images. JSON/AST and whitespace checks
pass. Historical player video/model provenance remains incomplete; current
hash checks do not recreate missing historical evidence.

## Exact proposed staging scope

The expected scope is eighteen files. Confirm against the final validation
receipt and `git status --short` before any staging:

1. `docs/context/current_state.md`
2. `docs/context/roadmap.md`
3. `docs/context/validation_history.md`
4. `configs/ball_tracking/reviews/rfdetr_medium_crop_motion_factorial_visual_review_record_v0_1.json`
5. `docs/ball_crop_motion_factorial_results.md`
6. `docs/ball_candidate_identity_diagnosis.md`
7. `docs/ball_crop_player_context_proposal.md`
8. `configs/ball_tracking/proposals/rfdetr_medium_crop_player_context_v0_1.json`
9. `configs/ball_tracking/reviews/rfdetr_medium_crop_player_context_approval_v0_1.json`
10. `configs/ball_tracking/crop_player_context_experiments/rfdetr_medium_crop_player_context_v0_1.json`
11. `src/ball_tracking/crop_player_context.py`
12. `src/ball_tracking/crop_player_context_experiment.py`
13. `src/ball_tracking/crop_player_context_evaluation.py`
14. `src/ball_tracking/crop_player_context_review.py`
15. `tests/test_ball_crop_player_context.py`
16. `tests/test_ball_crop_player_context_experiment.py`
17. `tests/test_ball_crop_player_context_review.py`
18. `docs/ball_crop_player_context_implementation.md`

Only the three intentional context files are modifications to existing tracked
files. Preserve all prior untracked review/design bytes. Generated outputs,
images, context snapshots, clips and validation receipts stay ignored under
`data/outputs/ball_tracking/`.

## Release sequence

Start from `codex/ball-detector-baseline` at
`2274ab6097cd841421e2b606f723b047cd7dc62b`, with an empty index. After validation,
staging needs explicit authorization for the final exact scope. Then verify
the staged diff and obtain separate commit authorization. Real execution is
already approved in scope, but remains gated on that clean, tested implementation
commit and unchanged approved input hashes. Recheck all nine absent original
prediction paths and all three sealed holdouts at every execution boundary.

Once those conditions hold, use the new manifest under
`configs/ball_tracking/crop_player_context_experiments/`; perform selection,
scoring and rendering as separately audited stages. Verify all new/reused
counts and review assets before asking Ryan for final-frame inspection.
Do not rerun a completed detector, crop, ranking or motion experiment. Pushes,
PR creation, merges, holdout release and any method/quality-gate selection
remain separate decisions.
