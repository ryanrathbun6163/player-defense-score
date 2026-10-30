# YOLO11x crop recovery implementation

The original comparison stopped after 175 of 600 crop units because the
adapter rejected a native box clipped to zero height below the export floor.
Ryan approved the exact recovery proposal with "Yes I approve chat". The
separate approval record binds the unchanged proposal; the earlier proposal
remains a historical pre-approval snapshot.

Approval record:
`configs/ball_tracking/reviews/yolo11x_crop_recovery_approval_v0_2.json`
(SHA-256 `5d9ec4a2d2d7c310ed304f4ce41e5b5aed9c76dd2829fdeb469201478c773782`).

Implementation and validation are complete. Real recovery remains pending
separately authorized staging and a clean tested commit.

## Behavior and provenance

The validator retains finite, bounded, non-reversed native boxes below .01,
including boxes collapsed by SDK clipping. At and above the inclusive .01
export floor, every exported box still requires positive width and height.
The detector, weights, runtime, scores, ordering, preprocessing, NMS, caps and
cross-crop duplicates retain their approved settings.

The recovery must consume the 175 original checkpoints without new model
calls, execute only the 425 missing units, and resume any newly completed
units without repeating them. All 561 original checkpoint, attempt,
preparation, candidate and selector files remain byte-identical.

Each crop's inference commit is separate from the commit that assembles a
window. The typed evaluation view's single model commit describes assembly
only; candidate, selector, scoring and review records carry explicit actual
per-unit inference provenance. Original results are never relabeled as having
been inferred by the future recovery commit.

The comparison retains the same six development windows, 150 source PNGs,
three simple selectors and fixed scoring grid. It creates 162 selector files
and 810 new reports while reusing 810 saved RF-DETR reports. Each separate
pool contains 270 aggregate cells. Review will produce twelve paired clips
and 1,500 PNGs with 1,200 existing control/source PNG references.

## Execution and review boundary

Real recovery requires the approved scope and a separately authorized clean,
tested implementation commit. Implementation approval does not authorize
staging, committing, pushing, PR creation or merging.

All nine original prediction embargoes and three sealed holdouts remain
intact. No operating point, method or quality gate is selected. Ryan's earlier
player-context review is complete; the future twelve YOLO recovery clips
require their own review through the final frame after execution.

Local implementation evidence belongs under
`data/outputs/ball_tracking/yolo11x_recovery_implementation/116e3ed9cb41/`.

## Validation and exact staging scope

All 27 recovery-focused tests and 15 adapter
tests pass. The full suite has 491 passes and one existing Windows
directory-symlink skip. Synthetic tests cover the partial-run boundary,
failure/resume, per-unit provenance, scoring controls and all final frames.
Agent visual inspection covers synthetic review layouts only.

The read-only preflight verifies the actual frozen runtime, 150 source PNGs
and 175 preserved checkpoints. Model construction, source-media decoding and
annotation access are forbidden during that check. Real recovery is rejected
on this dirty checkout. All 561 old files are unchanged; the recovery output
root is absent. `git diff --check` passes.

At branch `codex/ball-detector-baseline`, HEAD `116e3ed9cb4113521fa8c93adf4a100fea4dc0ec`,
the proposed staging scope is exactly these 17 files:

- `configs/ball_tracking/proposals/yolo11x_crop_recovery_v0_2.json`
- `configs/ball_tracking/reviews/yolo11x_crop_recovery_approval_v0_2.json`
- `configs/ball_tracking/yolo_crop_experiments/yolo11x_crop_recovery_v0_2.json`
- `docs/ball_yolo11x_crop_recovery_implementation.md`
- `docs/ball_yolo11x_crop_recovery_proposal.md`
- `docs/context/current_state.md`
- `docs/context/roadmap.md`
- `docs/context/validation_history.md`
- `src/ball_tracking/yolo11x_adapter.py`
- `src/ball_tracking/yolo_crop_recovery.py`
- `src/ball_tracking/yolo_crop_recovery_evaluation.py`
- `src/ball_tracking/yolo_crop_recovery_review.py`
- `tests/test_ball_yolo11x_adapter.py`
- `tests/test_ball_yolo_crop_recovery.py`
- `tests/test_ball_yolo_crop_recovery_evaluation.py`
- `tests/test_ball_yolo_crop_recovery_guards.py`
- `tests/test_ball_yolo_crop_recovery_review.py`

Generated data and runtime files remain ignored. The index is empty.
