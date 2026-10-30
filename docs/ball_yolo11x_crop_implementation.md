# YOLO11x development comparison implementation

Ryan approved the exact six-window proposal after completing the twelve
player-context clips. The separate approval receipt binds that statement and
the executable manifest. The historical proposal and earlier review snapshots
retain their original bytes. This implementation passed synthetic
validation and read-only preflight; real project inference requires a separately
authorized clean tested commit. Git steps remain individually authorized.

## What this adds

The comparison tests whether one complementary detector supplies useful ball
evidence on the same 150 development frames. It compares complete detector
configurations. YOLO letterboxing, best-class assignment, NMS and candidate caps
differ from RF-DETR. Equal confidence thresholds are not calibrated equivalents.
Repeatedly reviewed windows do not establish unseen-game generalization.

- `yolo11x_adapter.py` validates the isolated runtime and official checkpoint,
  warms each predictor using synthetic pixels, preserves native postprocessor
  order, translates class 32 to category 37, then applies inclusive .01 export.
- `yolo_crop_candidates.py` maps the four crop coordinates to full-frame
  coordinates, retains duplicates and implements all/top-one/top-twenty views.
- `yolo_crop_experiment.py` reads only bound source PNGs and metadata for
  inference. It writes immutable preparation, attempt and crop receipts;
  verified completed units are reused after interruption.
- `yolo_crop_evaluation.py` scores only the new selections and combines their
  reports with exact saved RF-DETR results. It reports all paired frame changes
  and separates absent exports, confidence filtering and selection losses.
- `yolo_crop_review.py` produces paired clips, native new views and source-scale
  closeups while referencing exact prior native/source PNGs.

No earlier detector, selector, scorer, renderer or source-video decoder is
invoked. Missing observations remain missing. All nine original prediction
paths remain embargoed; P001 300–324, P002 200–224 and P003 250–274 remain sealed.
No method, operating point or quality gate is selected.

## Runtime and actual synthetic checks

The isolated interpreter is
`data/outputs/ball_tracking/yolo11x_runtime/ultralytics_8_4_171_py311/env/Scripts/python.exe`.
Packages are physical copies plus separately installed additions, without
changing the baseline environment. `ultralytics==8.4.171`, all resolved package
versions, wheel hashes, 24,190 installed files, Python build and CUDA device are
recorded in ignored runtime evidence. The extra audit covers top-level wheel
modules as well as package directories.

The official `yolo11x.pt` bytes match SHA-256
`7bc158aa95c0ebfdd87f70f01653c1131b93e92522dbe15c228bcd742e773a24`.
The frozen runtime receipt SHA-256 is
`bd549dff7c4d7810b3154c9a5442cf43516e15bd5c72ab6abe631f819652e7ba`.
The original environment lock and embedded checkpoint training metadata are
retained locally; exact training-footage overlap remains unverified. The
proposal records the upstream licensing terms without relicensing this repo.

Actual GPU validation used zeros and constant RGB arrays only. It verified
640-square input, 640x360 content, 140-pixel vertical pads, channel order,
division by 255, inverse box mapping, FP32 on CUDA device 0, two synthetic startup
forwards and exactly one forward on the ordinary inference route. That route's
counter names say `project`, but these validation inputs were synthetic:
**zero project pixels were processed**. TF32 is disabled. The SDK deep-copies
the network; the forward hook and live precision checks cover the actual copy.
Its canonical `quantize=32` makes the approved `half=False` precision explicit.
Runtime settings stay in the ignored runtime directory with offline behavior
and automatic dependency installation disabled.

Final source bytes are bound by
`data/outputs/ball_tracking/yolo11x_implementation/119159817df5/final_adapter_synthetic_validation.json`.
The full resize/channel checks are in `synthetic_runtime_validation.json` in
the same directory. Read-only preflight verified all 150 PNG bindings, six
windows, 600 planned crop units and 162 new selector outputs without constructing
a detector. Runtime tests do not establish ball-detection quality.

## Output and review contract

| Item | New | Reused |
| --- | ---: | ---: |
| Project crop inference units | 600 unique | 0 rerun |
| Window candidate files | 6 | 6 |
| Selector outputs | 162 | 162 |
| Per-window scoring reports | 810 | 810 |
| Aggregate cells per separate pool | 135 | 135 |
| Review PNG assets | 1,500 | 1,200 references |
| Review clips | 12 | 0 rerendered |

Attempts and retries are separate from unique units. Failed/interrupted work
preserves what is known; unresolved accounting is explicitly unknown. New
clips contain 25 frames at 5 fps at confidence .20/.35 and radius 10. Their rows
compare all exported, top one and top twenty. Old candidate identifiers remain
independent of new ones. Hidden-frame closeups show an inspection location,
never invented truth. Human review of these new real clips will be pending
until Ryan watches them through their final frames.

Synthetic tests cover interruption/resume, changed bindings, label isolation,
exact selection prefixes, confidence boundaries, duplicate preservation,
native order, model/crop provenance, scoring arithmetic, hidden observations,
loss partitions, unchanged controls, final-frame video decoding and saved-data
renderer integration. Synthetic comparison/native/closeup panels were also
visually inspected for layout and honest labeling. All 41 focused tests pass; the full suite reports 460 passes and
1 existing Windows directory-symlink skip. Test logs and final results
are in the implementation evidence directory.

## Exact intended staging scope

These nineteen files include the previously completed review/results/design
closeout and the new implementation. Generated runtime, model, videos, data,
logs and receipts under `data/` remain ignored. The three context files retain
their previous intentional changes; their preceding bytes are backed up.

1. `configs/ball_tracking/proposals/yolo11x_crop_development_comparison_v0_1.json`
2. `configs/ball_tracking/reviews/rfdetr_medium_crop_player_context_visual_review_record_v0_1.json`
3. `configs/ball_tracking/reviews/yolo11x_crop_development_comparison_approval_v0_1.json`
4. `configs/ball_tracking/yolo_crop_experiments/yolo11x_crop_development_comparison_v0_1.json`
5. `docs/ball_crop_player_context_results.md`
6. `docs/ball_yolo11x_crop_comparison_proposal.md`
7. `docs/ball_yolo11x_crop_implementation.md`
8. `docs/context/current_state.md`
9. `docs/context/roadmap.md`
10. `docs/context/validation_history.md`
11. `src/ball_tracking/yolo11x_adapter.py`
12. `src/ball_tracking/yolo_crop_candidates.py`
13. `src/ball_tracking/yolo_crop_evaluation.py`
14. `src/ball_tracking/yolo_crop_experiment.py`
15. `src/ball_tracking/yolo_crop_review.py`
16. `tests/test_ball_yolo11x_adapter.py`
17. `tests/test_ball_yolo_crop_evaluation.py`
18. `tests/test_ball_yolo_crop_experiment.py`
19. `tests/test_ball_yolo_crop_review.py`

Before staging, verify the implementation checkpoint's exact hashes and scope,
branch `codex/ball-detector-baseline`, HEAD
`119159817df5414f534f133f0954c1f78c7e51de`, empty index and passing validation.
Staging permission does not imply committing, pushing, PR creation or merging.

After separately authorized staging and commit, revalidate clean preflight using
the isolated interpreter. Only then execute the already approved 600-unit run,
score the new outputs, render the new twelve clips and prepare their review
guide. Resume completed units by their immutable receipts. Do not rerun prior
experiments, alter the approved design or release holdouts.
