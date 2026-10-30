# Approved crop-comparison implementation

Ryan approved the linked fixed-crop comparison with "yes i approve". The
receipt binds that statement to the unchanged proposal and the executable
manifest specification:
`3384a930d8633b202b689857de2bea4939277a2d2f0c3da483c2c48e9e9ef023`.
The historical proposal stays unchanged. No further experiment approval is
needed for this exact scope; Git steps remain separately authorized.

## What is implemented

- `tiled_candidates.py` validates the fixed four-view grid, preserves every
  crop-local candidate, translates geometry into source pixels, and records
  the local/global mapping with deterministic global ordering. Duplicates stay
  visible. A separate tiled schema records the actual input composition.
- `tiled_experiment.py` checks the proposal, approval, frozen detector, source
  videos, saved controls, original embargoes, and clean Git checkpoint. It runs
  only the six declared windows and four crops per frame. Inference never
  opens annotation content or uses labels to choose a crop.
- Every completed crop is saved as an immutable checkpoint. An interruption
  resumes only missing calls; changed checkpoints or final outputs are refused.
  Six complete candidate files accompany 600 crop checkpoints. No existing
  detector output is overwritten or relabeled.
- CUDA-synchronized wall time and peak PyTorch CUDA allocated bytes are stored
  for each crop call. Timing includes lazy initialization on the first call;
  allocation measures PyTorch memory, not total GPU device usage. No timing
  comparison with an unmeasured saved whole-frame baseline is invented.
- `tiled_evaluation.py` separately scores whole-frame and cropped inputs using
  raw and top-one selectors at all nine confidence values and five radii. It
  creates 1,080 per-window reports and 180 aggregate cells in each separate
  pool, with recovered/lost frame IDs and false-positive changes. Original
  candidate indices, model provenance, missingness, and raw-distance matching
  remain explicit.
- `tiled_review.py` renders 12 four-panel slow videos, 300 comparison images,
  300 unmarked-source/overlay closeup sheets, 1,200 native overlays with their
  sidebars, and 150 crop-boundary context images. Complete-frame decoding and
  all final frames are validated. Real human review remains after execution.

The pipeline is independent of the existing 21 player-coordinate stages.
No upstream reviewed player decision changes, so no `--rerun-from` is needed.
No tracker, operating point, quality gate, or holdout release is selected.

## Validation checkpoint

The focused tests cover crop coverage and boundaries, local/global coordinates,
overlap duplicates and ties, empty results, invalid candidates/timing, label
blindness, exact six-window scope, all nine embargoes, dirty-Git refusal,
dry-run behavior, partial resume, changed checkpoints/commits, all 600 synthetic
model calls, all 1,080 report cells, control parity, complete synthetic review
rendering, final-frame decoding, and asset tamper refusal.

Real-source read-only preflight passed with the repository `.venv`, frozen
RF-DETR package/weight checks, verified source clips, and the installed RTX
5070 CUDA runtime. It made no predictions. Agent visual inspection covered
the synthetic comparison and closeup previews, not real new detector output.
The first focused run caught a renderer sidebar-width mismatch and synthetic
class-ID fixture mismatch; both were fixed without changing the experiment.

Final focused tests passed 18/18 in 74.915 seconds. The full suite ran 342 in
223.084 seconds: 341 passed, one existing directory-symlink capability skip.
Formatting, syntax/whitespace, and exact staging-scope checks passed. The final
audit confirms all 59 prior protected files, six saved detections, reviewed
annotations, immutable proposal, and nine absent embargo paths are preserved.
Exact file hashes and proposed Git blobs are recorded in ignored
`data/outputs/ball_tracking/tiled_implementation_validation/validation_record.json`;
the current checkpoint is also recorded in `docs/context/current_state.md`.

## Exact proposed staging scope

Branch: `codex/ball-detector-baseline`.
HEAD: `6769e07476da09d858fa42f82aace024d21f7735`.
The index is empty. These 15 files include the preserved earlier temporal
closeout and the approved crop implementation; generated artifacts stay ignored.

```text
configs/ball_tracking/proposals/rfdetr_medium_tiled_development_comparison_v0_1.json
configs/ball_tracking/reviews/rfdetr_medium_temporal_association_visual_review_record_v0_1.json
configs/ball_tracking/reviews/rfdetr_medium_tiled_development_comparison_approval_v0_1.json
configs/ball_tracking/tiled_experiments/rfdetr_medium_tiled_development_comparison_v0_1.json
docs/ball_detector_tiled_comparison_implementation.md
docs/ball_detector_tiled_comparison_proposal.md
docs/ball_temporal_association_results.md
docs/context/current_state.md
docs/context/roadmap.md
docs/context/validation_history.md
src/ball_tracking/tiled_candidates.py
src/ball_tracking/tiled_evaluation.py
src/ball_tracking/tiled_experiment.py
src/ball_tracking/tiled_review.py
tests/test_ball_tiled_comparison.py
```

## Execution after separate staging and commit authorization

The runner requires a clean committed snapshot before real inference. Once
that checkpoint exists, run all stages at the same commit before editing
context notes. Only the dry-run command below has run against real inputs.

```powershell
.\.venv\Scripts\python.exe -B -m src.ball_tracking.tiled_experiment --manifest configs/ball_tracking/tiled_experiments/rfdetr_medium_tiled_development_comparison_v0_1.json --repository-root . --dry-run
.\.venv\Scripts\python.exe -B -m src.ball_tracking.tiled_experiment --manifest configs/ball_tracking/tiled_experiments/rfdetr_medium_tiled_development_comparison_v0_1.json --repository-root .
.\.venv\Scripts\python.exe -B -m src.ball_tracking.tiled_review score --manifest configs/ball_tracking/tiled_experiments/rfdetr_medium_tiled_development_comparison_v0_1.json --repository-root .
.\.venv\Scripts\python.exe -B -m src.ball_tracking.tiled_review render --manifest configs/ball_tracking/tiled_experiments/rfdetr_medium_tiled_development_comparison_v0_1.json --repository-root .
```

Outputs belong under the new ignored
`data/outputs/ball_tracking/tiled_development/rfdetr_medium_tiled_development_comparison_v0_1/`.
All nine original prediction paths must remain absent; all three holdouts stay
sealed. Do not repeat Ryan's experiment approval or temporal-review request.
