# Ball-detector development release proposal

Status: experiment approved by Ryan; implementation validated, 2026-09-18
America/Phoenix (2026-09-19 UTC). Ryan said, "lets move forward I approve of
this experiment". The separate experiment-approval receipt records that
statement and the exact inventory hash. Its timestamp records this session's
receipt creation; the chat message did not supply a separate event timestamp.
The original inventory remains an immutable proposal, not an executable permit.
All nine v0.1 evaluation-window embargoes remain active until the new release
passes its clean-checkpoint requirements. No Git mutation is authorized.

## Purpose and scope

The six representative/challenge windows are now human-reviewed reference
sets. The proposed next experiment measures the same frozen RF-DETR Medium
baseline against those labels. It must retain separate representative and
challenge results, preserve hidden-ball frames, and leave all three holdouts
sealed. It selects neither an operating point nor a detector quality gate.

The reviewed input inventory is
[`rfdetr_medium_development_release_proposal_v0_1.json`](../configs/ball_tracking/proposals/rfdetr_medium_development_release_proposal_v0_1.json).
It records the exact annotation, approval, finalization, visual-manifest, and
source hashes. It is outside the experiment registry and has a deliberately
different schema. It is not a runnable experiment or a release receipt.

| Possession | Representative | Challenge | Holdout retained under embargo |
| --- | --- | --- | --- |
| P001 | 50–74; 25 centers | 200–224; 25 centers | 300–324 |
| P002 | 250–274; 25 centers | 25–49; 25 centers | 200–224 |
| P003 | 300–324; 25 centers | 150–174; 20 centers, 5 occlusions | 250–274 |

All 150 development frames are labeled. The five P003 occlusions at 165–169
have null geometry and remain part of evaluation. These curated same-game
windows do not establish cross-game or broad NBA performance.

## Verified starting point

- Branch `codex/ball-detector-baseline`, HEAD
  `b7a887f55705623889625edf60028e2e39d38dc4`; worktree intentionally dirty.
- Parent experiment:
  `configs/ball_tracking/experiments/rfdetr_medium_image_only_baseline_v0_1.json`.
  SHA-256: `7d82faec9f4d0615a0e870372392a9a9d4f2576ada88e700bec2fd8b3b28d3e3`.
- The parent remains immutable. Its three authorized pilots and nine embargoed
  windows retain their existing statuses, IDs, paths, detector settings,
  selection rules, and scoring grid.
- All six annotation files are `reviewed`, with matching approval/finalization
  receipts. The six-window audit verified all 330 bound review assets.
- None of the nine declared embargoed prediction files exists. None of the
  six proposed development prediction files exists.
- Existing pilot results and their approved review package are historical
  evidence; this proposal does not require rerunning or overwriting them.

## Proposed versioned experiment

Use a new `ball_detector_experiment/v0.2` contract and eventual experiment ID
`rfdetr_medium_development_evaluation_v0_2`. The proposed manifest path is
`configs/ball_tracking/experiments/rfdetr_medium_development_evaluation_v0_2.json`.
That runnable manifest has not been created.

The new contract has exactly six executable window records: the representative
and challenge bindings inherited from the parent, three of each. It names the
parent by repository-relative path and SHA-256. Validation resolves the parent
and proves exact equality of possession, source contract, annotation-set ID,
frame range, and selection purpose. No window may be substituted, shortened,
expanded, relabeled as a pilot, or moved between pools. The parent's full
selection and exclusion checks remain authoritative, including holdouts and
the historical P001 frame-150 prediction exclusion.

The three pilots and three holdouts are not executable entries in the new
manifest. Their bindings remain recorded in the parent. A separately checked
sealed-holdout list must match all three parent holdouts exactly. Including a
holdout or pilot in the six-window executable list is invalid, even if a CLI
argument requests it. There is no `--force` or embargo-bypass option.

Each executable window receives the new versioned window ID, detection-run ID,
and output path specified in the proposal inventory. Existing global collision
checks remain in place: IDs and case-insensitive output paths cannot collide
with any committed experiment. Deliberate reuse of a source-frame interval is
allowed only through this exact parent-and-release binding; it does not permit
reuse of an old run identity or output file.

Copy the parent's detector contract and scoring grid exactly. This retains
RF-DETR Medium 1.9.1 and the frozen weight hash, CUDA FP32, 576×576 processing,
all raw sports-ball candidates at the inclusive 0.01 export floor, and existing
candidate ordering. No retraining, detector tuning, tracking, smoothing,
interpolation, court filtering, or one-ball post-selection is included.

## Release evidence without label access during inference

The proposal inventory is label-aware evidence for release preparation. It is
not an inference input and must never be forwarded to the detector adapter.

Before any future release, a separate label-aware verifier must validate all
six finalized labels, their source videos, approval/finalization receipts,
approved snapshots, and visual-bundle hashes. It must also establish that the
six candidate output paths and all sealed holdout paths have no predictions.
Changing a label or receipt invalidates the prepared release evidence; it
requires a new reviewed record, not an in-place repair of old approvals.

The proposed release sequence uses two explicit Git checkpoints to avoid
self-referential hashes:

1. After separately authorized staging and committing, record an immutable
   evidence commit containing the reviewed labels, receipts, validated release
   support code, and evidence inventory. This is a future checkpoint, not the
   current dirty HEAD. A completed validation report names that exact commit
   and the relevant Git blob IDs, including release-support source files.
2. Using Ryan's recorded experiment approval, create a new release receipt,
   v0.2 manifest, and two pool-specific visual-review plans referencing that
   earlier evidence commit. A later separately authorized commit contains
   these five activation artifacts. No second experiment approval is needed;
   staging and committing remain separately authorized steps.

The manifest references the release receipt by path and hash. The receipt
binds the exact parent hash, six source/window identities, evidence commit and
validation report, and an `execution_spec_sha256`. Define that digest over the
canonical manifest payload with only its release-receipt reference omitted.
The receipt must not hash a manifest that itself includes the receipt hash;
this avoids a second circular dependency. The receipt records Ryan's actual
release statement and time. Annotation approval alone is not release approval.

The runner validates the permit, ancestry, current clean HEAD, and Git blob
IDs against the recorded evidence commit using Git tree metadata. It does not
open annotation JSON or approved snapshots. The metadata verifier is separate
from the adapter, which receives only the authorized RGB frame and frozen
runtime settings. Edited or newly committed evidence/source bytes invalidate
the old validation binding. Existing symlink, tracked-file, manifest-registry,
source-byte, CUDA/package/weight, and ignored-output protections still apply.

The current clean-worktree requirement is retained. No dirty-tree bypass,
automatic staging, commit, stash, or push is part of this proposal. The two
checkpoints make the extra provenance work explicit; each Git mutation still
needs Ryan's separate authorization under AGENTS.md.

## Evaluation and visual review

The current grid has nine confidence thresholds and five localization radii:
45 combinations. Evaluate every combination for every development window,
producing 270 per-window evaluation reports. Keep two primary 45-cell aggregate
grids: representative and challenge. Retain per-possession/per-purpose results
so a strong possession cannot conceal a weak one. Do not combine these with
pilot or holdout results to select a winner.

Use the existing low-level evaluator semantics unchanged. The representative
pool contains 75 eligible centers; the challenge pool contains 70 eligible
centers and five reviewed not-visible frames. Preserve missing geometry,
unscored cases, empty detections, decode/inference failures, and all original
raw candidates. A failed frame must not silently become a valid negative or
disappear from the report.

Publish a new versioned development scoring-report schema and filename under
an ignored, experiment-scoped output root. Bind every report to exact manifest,
release, detector-run, label, and evaluator-code provenance. Keep
`selected_operating_point` and `quality_gate` null. The v0.1 pilot report loader
and existing report bytes retain their current meaning.

Extend the visual-review contract separately from the pilot contract. Produce
one package per pool, each containing three windows, covering all six windows
and all 150 frames across both packages, with representative/challenge labels,
source pixels, raw candidates, human truth, uncertainty, and explicit gaps.
For the first development review, predeclare the same two descriptive display
views used in the approved pilot review: confidence 0.20 and 0.35, each at a
10-pixel localization radius. These are display views, not a selected operating
point; all 45 numeric grid cells remain available. Review through every final
frame, especially P003 164–170 and 174. Do not draw a truth trajectory through
the five-frame hidden interval. Final visual judgments remain Ryan's.

## Implementation map

| Area | Current constraint verified in code | Proposed change |
| --- | --- | --- |
| `detector_experiments.py` | v0.1 fixes 12 entries and allows only pilots to run | Explicit version dispatch; keep v0.1 unchanged; validate v0.2 against parent and release receipt |
| New release-evidence module | No development release verifier exists | Validate labels/receipts outside inference and bind an immutable evidence commit |
| `run_detector_experiment.py` | Clean tracked HEAD, globally unique claims, inference through `windows_for_inference()` | Verify release metadata before source/model execution; return only the six authorized windows; preserve resume and provenance checks |
| `score_detector_experiment.py` | Exactly three pilots; pilot-only report schema and aggregate | Add an explicit development path with two pools, six window bindings, and versioned report validation |
| `prepare_detection_visual_review.py` | Exactly three protocol pilots | Add versioned three-window packages for each of the two development pools; preserve pilot rendering |
| `rfdetr_adapter.py`, `evaluation.py` | Frozen detector and low-level evaluation semantics | Reuse without algorithm or metric changes |

Implement support and synthetic tests while all active manifests remain
unchanged and embargoed. The executable v0.2 manifest and release receipt are
activation artifacts for a later, explicitly authorized step, not fixtures to
publish opportunistically during implementation.

## Validation required before proposing activation

Run focused tests first, then the full repository suite using `.venv` Python
with bytecode disabled, followed by `git diff --check`. New tests should prove:

- v0.1 behavior and parent manifest bytes remain unchanged;
- a proposal, missing approval, stale hash/blob, changed evidence, wrong
  parent, wrong purpose/range/source, or missing development window is rejected
  before adapter construction or output creation;
- only the six exact development windows can reach model inference; neither
  pilots nor holdouts can be added through a CLI override or manifest alias;
- existing global ID/path collision, case-folding, symlink, clean-HEAD,
  tracked-input, ignored-output, and resumability guards still work;
- interrupted/restarted runs preserve prior candidates and explicit failures,
  and cannot adopt outputs from v0.1 or another release;
- all 270 reports are present and recomputable, pool aggregates remain
  separate, and hidden/failed/unscored frames retain their intended semantics;
- visual evidence reaches all six final frames and preserves occlusion gaps;
- scoring and visualization cannot select an operating point or quality gate.

Use injected adapters and synthetic frames for pre-release tests. Generating
or viewing predictions on any real embargoed evaluation window is not part of
implementation validation. After an authorized release and successful runtime
preflight, a later real run may produce development evidence for human review.
Holdout release, detector selection, tracking, and defensive scoring remain
separate later work.

## Checks completed for this proposal

Using the repository `.venv` with `-B`, all 27 existing detector-manifest tests
passed. A read-only audit verified the inventory's 24 evidence-file hashes and
the unchanged parent-manifest hash. The current loader rejected the proposal
as an executable manifest and rejected all nine in-memory attempts to toggle
an embargoed v0.1 window to runnable. No manifest bytes were changed by those
checks. The proposed manifest and prediction outputs remain absent.

The preceding checks describe the original proposal checkpoint. Implementation
now adds `development_experiments.py`, `development_release.py`, and
`development_scoring.py`, plus version dispatch in the existing runner, scorer,
and visual renderer. Focused validation passed: 14 new development tests, 10 existing detector
visual-review tests, and 27 independent-review tests. The final full suite ran
299 tests, with 298 passing and one existing Windows directory-symlink
capability skip. `git diff --check` and untracked-file syntax/whitespace checks
passed. The first full run found a time-dependent test fixture, corrected as
described in the checkpoint scope below; production review rules are unchanged.
The final ignored log is
`data/outputs/ball_tracking/development_implementation_validation/full_suite_20260919_retry.log`.
No real model was loaded or run. These dirty-worktree implementation checks
are not the future clean-commit release evidence.

## Checkpoint procedure

Use `$env:PYTHONDONTWRITEBYTECODE = '1'` so subprocesses also avoid bytecode
artifacts. The repository must first reach a separately authorized clean evidence
commit containing the reviewed labels, all receipts, unchanged proposal inventory,
experiment approval, implementation, and tests. Only then run the repository
`.venv` Python with `-B -m src.ball_tracking.development_release`:

- `--repository-root . prepare-evidence --proposal
  configs/ball_tracking/proposals/rfdetr_medium_development_release_proposal_v0_1.json
  --approval configs/ball_tracking/reviews/rfdetr_medium_development_experiment_approval_v0_1.json`
  verifies the six approval chains and 330 assets, runs the full test suite, and
  writes an ignored validation record naming the evidence commit.
- `--repository-root . prepare-activation --evidence <printed-validation-path>`
  verifies that evidence against the clean repository and creates five new
  files: evidence copy, release receipt, executable manifest, and two review
  plans. It never stages, commits, or runs inference. Existing files are never
  overwritten; interrupted publication must be inspected before recovery.

After those exact activation artifacts are separately authorized and committed,
the existing runner can perform a dry-run preflight and then execute the six
new windows. The existing scorer emits two reports containing all 270 window
results. Run the visual-review renderer once per generated plan; Ryan reviews
both packages. The parent manifest, pilots, and holdouts are unchanged. Any
protected code/label change invalidates this release and needs new evidence.
No command in this procedure has yet been run on real development footage.

## Proposed evidence-checkpoint file scope

These 35 existing worktree changes are the proposed staging scope. Nothing
is staged. This includes the previously prepared annotation initializer, pilot
review record, and teaching preference, preserving their existing contents.
The independent-review test fixture also now derives its review timestamp
from its creation time: its fixed August date had become invalid for a newly
created September workspace. Production review rules are unchanged.
Generated footage, predictions, review images, and validation logs stay ignored.

```text
configs/ball_tracking/annotations/possession_001_frames_0050_0074_representative_evaluation_v0_1.json
configs/ball_tracking/annotations/possession_001_frames_0200_0224_challenge_evaluation_v0_1.json
configs/ball_tracking/annotations/possession_002_frames_0025_0049_challenge_evaluation_v0_1.json
configs/ball_tracking/annotations/possession_002_frames_0250_0274_representative_evaluation_v0_1.json
configs/ball_tracking/annotations/possession_003_frames_0150_0174_challenge_evaluation_v0_1.json
configs/ball_tracking/annotations/possession_003_frames_0300_0324_representative_evaluation_v0_1.json
configs/ball_tracking/proposals/rfdetr_medium_development_release_proposal_v0_1.json
configs/ball_tracking/reviews/possession_001_frames_0050_0074_single_annotator_finalization_v0_1.json
configs/ball_tracking/reviews/possession_001_frames_0050_0074_visual_review_approval_v0_1.json
configs/ball_tracking/reviews/possession_001_frames_0200_0224_single_annotator_finalization_v0_1.json
configs/ball_tracking/reviews/possession_001_frames_0200_0224_visual_review_approval_v0_1.json
configs/ball_tracking/reviews/possession_002_frames_0025_0049_single_annotator_finalization_v0_1.json
configs/ball_tracking/reviews/possession_002_frames_0025_0049_visual_review_approval_v0_1.json
configs/ball_tracking/reviews/possession_002_frames_0250_0274_single_annotator_finalization_v0_1.json
configs/ball_tracking/reviews/possession_002_frames_0250_0274_visual_review_approval_v0_1.json
configs/ball_tracking/reviews/possession_003_frames_0150_0174_single_annotator_finalization_v0_1.json
configs/ball_tracking/reviews/possession_003_frames_0150_0174_visual_review_approval_v0_1.json
configs/ball_tracking/reviews/possession_003_frames_0300_0324_single_annotator_finalization_v0_1.json
configs/ball_tracking/reviews/possession_003_frames_0300_0324_visual_review_approval_v0_1.json
configs/ball_tracking/reviews/rfdetr_medium_development_experiment_approval_v0_1.json
configs/ball_tracking/reviews/rfdetr_medium_pilot_candidate_comparison_review_record_v0_1.json
docs/ball_detector_development_release_proposal.md
docs/context/current_state.md
docs/context/working_agreement.md
src/ball_tracking/detector_experiments.py
src/ball_tracking/development_experiments.py
src/ball_tracking/development_release.py
src/ball_tracking/development_scoring.py
src/ball_tracking/initialize_detector_annotation_windows.py
src/ball_tracking/prepare_detection_visual_review.py
src/ball_tracking/run_detector_experiment.py
src/ball_tracking/score_detector_experiment.py
tests/test_ball_detector_annotation_initialization.py
tests/test_ball_development_experiment.py
tests/test_ball_independent_review.py
```
