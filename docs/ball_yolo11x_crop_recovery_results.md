# YOLO11x crop comparison: reviewed results

Ryan approved the new twelve-clip package: **"I approve these clips. They have
been reviewed and you are good to move forward"**. This directly follows the
request to review all twelve clips through their final frames. The separate
record is
`configs/ball_tracking/reviews/yolo11x_crop_recovery_visual_review_record_v0_2.json`
(SHA-256 `365facf28a1e2f05339adea1e04e96a8fe7f33d0b3dea0184d16d1caa4c05433`).
It closes that human review without inventing individual-frame verdicts or
claiming every detection is correct. Earlier pending-review snapshots remain
unchanged; do not ask for this review again.

## Completed execution and preservation

The separately authorized local recovery commit is
`3326482e6f7e05527d146f3110c8ec39171cf08d` on `codex/ball-detector-baseline`.
It contains the exact seventeen tested files. Recovery reused 175 completed
crop units at `116e3ed9cb4113521fa8c93adf4a100fea4dc0ec` and completed only the
425 missing units at the new commit, with zero new failures. Each unit retains
its actual inference commit; assembly, scoring and rendering roles are separate.
All 561 original partial-run files remain byte-identical.

The actual accounting is 600 unique completed crops, 602 project attempts and
forwards including the two historical failures, three predictor preparations,
and six synthetic startup forwards. There are no unfinished accounting records.
Six new candidate files and 162 selector files support 810 new scoring reports;
810 existing RF-DETR reports are reused. Each separate pool has 270 aggregate
cells. No earlier detector, selector, scoring or rendering experiment was rerun.

The review bundle contains 12 clips and 1,500 PNGs with 1,200 reused native/source
references. Independent auditing verified the media hashes, all 25 frames at
5 fps in every clip, and 60 final images. Twelve clips and sixty final images
also have byte-identical short-path copies; these are support duplicates, not
additional rendered outputs. Agent layout inspection covered two stills only.
Ryan's later review is the source of the human approval.

Execution evidence is under
`data/outputs/ball_tracking/yolo11x_recovery_execution/3326482e6f7e/`.
The independent audit SHA-256 is
`0aeb970b6b550a7a6ce18840d9e88ebbf3cf6ea0f01155c40bcd0ef1522ea3a4`;
the execution checkpoint SHA-256 is
`df74bfd6f46070fa9b36866c4663b72fc7c89ff0addc2bc45c9f1c2dcc2849ca`.
The closeout rehashed 4,750 bound evidence files, 248 protected existing
non-context files and every short-path copy before recording approval.

## What the fixed comparison shows

YOLO has fewer matched detections than its corresponding RF-DETR simple
selector in all 270 paired aggregate cells across the fixed confidence/radius
grid. These are correlated settings on the same six development windows, not
270 independent trials. YOLO's full exported set often emits fewer false
candidates along with fewer true matches. Its top-one variant has more false
positives in every challenge aggregate cell; the representative tradeoff varies.

At the predefined 10-source-pixel radius, the following cells are **matched
detections / false detections / missed eligible frames**. The denominator is
75 eligible representative frames and 70 eligible challenge frames; five
additional challenge frames have reviewed hidden-ball labels.

| Pool | Confidence | RF-DETR top one | YOLO top one |
| --- | ---: | ---: | ---: |
| Representative | .20 | 51 / 23 / 24 | 26 / 28 / 49 |
| Representative | .35 | 50 / 19 / 25 | 22 / 13 / 53 |
| Challenge | .20 | 59 / 13 / 11 | 24 / 22 / 46 |
| Challenge | .35 | 55 / 6 / 15 | 22 / 16 / 48 |

P002 challenge top one matches 22/25 frames for RF-DETR and 12/25 for YOLO at
both displays. P001 representative has no YOLO match in any of its 25 frames
at either display. At P002 challenge 48-49, YOLO matching candidates exist at
the .01 export floor but are removed by both displayed confidence filters.
At frame 41 a matching candidate survives filtering but is discarded by top
one at both displays. These are different failure mechanisms.

At radius 10 and the .01 export floor, RF-DETR covers 140/145 eligible frames,
while YOLO covers 87/145. Every YOLO-matched frame at that cell is already
covered by RF-DETR's exported set. A union of these saved raw sets therefore
adds no matched frame at that radius on these windows. This does not rule out
different identity evidence, geometry combinations or other configurations;
none is tested or selected here.

Hidden false alarms also move: at .20, YOLO alarms on P003 165-166, whereas
RF-DETR alarms on 167-169. At .35 YOLO has no hidden alarm versus RF-DETR's one,
alongside fewer visible matches in that window. A lower hidden-alarm count
alone is not evidence of a usable ball tracker.

These are complete detector configurations: preprocessing, best-class
assignment, NMS and caps differ. Equal numerical confidence is not calibrated
probability equivalence. A missed localization is not a certified non-ball
identity label. Repeatedly inspected development frames do not establish
unseen-game generalization or a training/validation split for a learned verifier.

## Consolidated saved-method audit

The bounded audit is complete in
`data/outputs/ball_tracking/yolo11x_crop_closeout/3326482e6f7e/frontier/`.
It covers RF crop top one, four motion settings, four player-context settings,
and YOLO top one: ten families, nine existing confidence thresholds and five
radii in two separate pools. It reconciles 900 aggregate cells, 2,700 per-window
reports and 3,000 displayed frame-setting records. The 810 duplicated RF
reports and 270 aggregate copies match exactly and are counted once. Raw and
top-twenty reports supply availability references only; earlier whole-frame
and temporal families are outside this audit.

The audit retains a setting when no considered setting in the same pool/radius
has at least as many true matches and at most as many false detections, with
one strict improvement. This descriptive tradeoff boundary retains all tied
settings and their provenance. It does not optimize localization error, runtime
or temporal continuity, combine the pools, or select a winner.

At radius 10, eight representative and seven challenge settings remain on that
boundary. YOLO top one at .50 retains a representative tradeoff with 17 matches,
3 false detections and 58 misses. Calling YOLO universally dominated would
therefore be incorrect. No YOLO setting remains on the challenge boundary.

At the predefined .20/.35, radius-10 displays, twenty source frames are missed
by all ten families at both settings. These are twenty correlated setting
incidences per source frame, not twenty independent observations.

| Pool | Persistent missed source frames | RF candidate cause |
| --- | --- | --- |
| Representative | P001 51-53, 59, 67-73; P002 257; P003 304 | Five unavailable at .01; eight confidence-filtered |
| Challenge | P001 204, 217, 219; P002 34; P003 164, 170, 173 | Seven confidence-filtered |

The five unavailable RF cases are P001 59/67/68/69 and P002 257. All other
persistent misses have a matching RF proposal at the export floor which both
display filters remove. A path-choice rule cannot recover a proposal removed
before path selection. P001 representative 71 is the only frame with a false
detection in every displayed setting; that is a localization outcome, not a
certified non-ball identity. Hidden false alarms remain a separate category.

The complete audit SHA-256 is
`9a83a996f4c4772a45530e1050dc9337c8caa3fabaf6095ed96bbc44bc5cfe21`.
Its `display_residual_frames` retain all 150 source frames, twenty displayed
setting outcomes per frame, exact report pointers, candidate indices and
saved error causes. `summary.md` contains all display counts and tradeoff sets.

## Next saved-evidence task

Inspect weak matching proposals alongside emitted alternatives before adding
another ranking or proximity rule. The bounded inspection uses the twenty
persistent misses above, the five hidden frames P003 165-169, and seven useful
controls: P001 challenge 200-201 (flight), P002 representative 262-264, and P003
challenge 171/174 (reacquisition). These are 32 unique existing development
frames, all already present in the saved audit and source inventory.

Use the saved .01/radius-10 match indices and the displayed emitted-candidate
indices, retaining detector and crop provenance. Show unselected useful
alternatives as well as emitted errors with their original source pixels and
reviewed uncertainty. On unavailable frames, show source context and existing
outputs without inventing a matching proposal. This is a diagnostic, not new
detector execution, rematching, annotation revision or training.

The earlier 215-winner appearance catalog omits useful unselected alternatives.
It cannot supply certified non-ball labels. A learned verifier would need
separately reviewed identity labels and a defensible training/evaluation split;
that design remains a later decision. No new model, rule or threshold is
proposed for execution in this closeout.

The reviewable file scope is exactly the new visual-review record, this results
document, and `docs/context/current_state.md`, `docs/context/roadmap.md`, and
`docs/context/validation_history.md`. Generated audit evidence stays ignored.

All nine original prediction embargoes and three sealed holdouts remain intact.
No production code changes in this closeout. The same tested implementation
has 27 recovery-focused and 15 adapter passes, with 491 full-suite passes and
one existing Windows skip; those tests are not repeated for evidence/doc edits.
Staging, committing, pushing, PR creation and merging remain separate steps.
