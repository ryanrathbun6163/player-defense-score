# Saved crop candidate ranking: implementation checkpoint

Ryan approved the exact proposed experiment with "I approve chat". The separate
approval receipt binds the immutable proposal; it does not authorize Git steps.
The proposal retains its original proposed status as historical evidence.

This implementation prepares the next experiment in Phase 2, ball tracking.
It asks whether a short recent history can choose a useful original detector
candidate when top confidence points elsewhere. Player coordinates are already
complete for the three curated possessions. Possession understanding, roster
identity, matchups, and defensive scores remain future work.

## Implemented behavior

`src/ball_tracking/crop_ranking.py` implements the five approved arms and all
nine confidence thresholds. Each recent-history decision rebuilds an exact
acyclic graph from the current frame and four earlier frames. It preserves
the declared cap, motion limits, score components, deterministic ties, and
empty hypothesis. Outputs retain original candidate references and explicit
missingness. Detector centers and confidences are unchanged.

The selector opens no labels, scoring reports, source video, or model. Its
audit records include candidate dispositions, eligible edges, best paths,
competing endpoints, winning path, and score margin. Persistent clutter can
win; a surviving earlier endpoint produces no current observation. The path
score is an uncalibrated heuristic, not a probability.

`crop_ranking_experiment.py` binds the approved six saved crop inputs from
`1a9479f83a1766d8979fad07c604bc686d3c52c6`, exact specification, approval,
completed crop review, and selector commit. Real selection requires a clean,
committed feature branch. Existing outputs must match exact rederivation
before missing outputs are created. The read-only dry run creates no selection.

`crop_ranking_evaluation.py` scores original selected centers with the existing
evaluator and unchanged radius grid. It keeps representative and challenge
pools separate, checks all 540 saved crop raw/top-one outcome cells, and
separates raw availability, cap losses, and additional ranking losses. Only
input/below-threshold bookkeeping is excluded from outcome parity.

`crop_ranking_review.py` provides six synchronized panels: five crop arms and
saved whole-frame top one as context. It retains native overlays, unmarked
source closeups, alternative current hypotheses, gap reasons, and final frames.
Every new clip must decode all 25 frames at 5 fps. Review asset hashes and
complete frame inventories are checked before reuse. Human review starts
pending; synthetic inspection does not approve the later real evidence.

## Validation

All 21 focused tests pass (97.651 seconds). The full suite runs 363 tests:
362 pass and one existing directory-symlink test skips because Windows symlinks
are unavailable (325.472 seconds). Validation uses `.venv` Python with
bytecode disabled. Synthetic fixtures
exercise exhaustive small graphs, lower-confidence recovery, stable clutter,
tight/wide motion limits, ties, cap loss, crop duplicates, inclusive confidence,
gaps/expiry, causality, window reset, hidden-frame false alarms, immutable
inputs, provenance tampering, embargoes, dirty-checkpoint refusal, partial
resume, all-grid saved-control parity, and complete review rendering/reuse.

The synthetic integration generates 270 derived outputs, 1,350 per-window
reports, 225 aggregate cells per separate pool, and 12 clips plus 2,400 PNGs.
The agent inspected the synthetic comparison and source closeups. These are
layout/contract checks, not evidence of real tracking quality.

The real-input read-only preflight confirms six windows, 150 source frames,
45 variants, and zero new model calls. The real ranking output root remains
absent. The completed fixed-crop inference, scoring, and rendering were not
rerun. Existing reviewed player, detector, and tracklet code remains unchanged.

Ignored validation evidence is under
`data/outputs/ball_tracking/crop_ranking_implementation_validation/`.
`checkpoint_audit.json` binds the exact 15-file scope and successful test logs,
checks preserved Git/SHA-256 bindings for all 59 protected files, the six saved
whole-frame detections and six labels, frozen proposal/review evidence and
saved crop inputs, and all embargo/holdout identities. It also confirms
`git diff --check`, JSON/Python parsing, ignored output hygiene, an empty index,
an absent real output root, and refusal to execute from this dirty checkpoint.

## Exact proposed Git scope

The index remains empty. The proposed checkpoint contains these 15 files:

1. `configs/ball_tracking/crop_ranking_experiments/rfdetr_medium_crop_candidate_ranking_v0_1.json`
2. `configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_ranking_v0_1.json`
3. `configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_ranking_approval_v0_1.json`
4. `configs/ball_tracking/reviews/rfdetr_medium_tiled_development_comparison_visual_review_record_v0_1.json`
5. `docs/ball_crop_candidate_ranking_implementation.md`
6. `docs/ball_crop_candidate_ranking_proposal.md`
7. `docs/ball_detector_tiled_comparison_results.md`
8. `docs/context/current_state.md`
9. `docs/context/roadmap.md`
10. `docs/context/validation_history.md`
11. `src/ball_tracking/crop_ranking.py`
12. `src/ball_tracking/crop_ranking_experiment.py`
13. `src/ball_tracking/crop_ranking_evaluation.py`
14. `src/ball_tracking/crop_ranking_review.py`
15. `tests/test_ball_crop_ranking.py`

The three existing context edits retain their previous execution/review notes.
Generated predictions, reports, synthetic media, logs, and audit records remain
ignored. The immutable approved proposal/design are not rewritten.

## Next action

Seek separate authorization for staging this exact validated scope, then
separate authorization for committing it. The existing experiment approval
allows real selection, scoring, and rendering after that clean committed
implementation checkpoint; it does not grant staging or committing. No push,
PR, or merge is authorized.

After the checkpoint, execute only the new ranking stages. Their expected
counts are 270 derived outputs, 1,350 per-window reports, two 225-cell pools,
540 crop-control parity checks, and 12 new review clips. Ryan then reviews all
12 new clips through their final frames, including P002 challenge 48-49 and
P003 hidden frames 165-169 and boundaries 164/170/174.

All nine original prediction embargo paths remain absent. P001 300-324,
P002 200-224, and P003 250-274 remain sealed. No operating point, quality gate,
winner, or holdout release is selected. No upstream player decision changed,
so no player-pipeline `--rerun-from` action is needed.
