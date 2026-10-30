# Adapted WASB: remaining development gaps

Recorded 2026-10-08 after Ryan reviewed all six adapted review clips and authorized
continued work. This is a diagnosis of saved development outputs. It does not
change the reviewed checkpoint, annotations, primary threshold or quality gates.

## What remains missing

The fixed 0.5 result remains 98 matched, one geometric error and 46 missing
eligible frames, with no emissions on the five hidden frames. P001 accounts for
39 missing frames. Its entire representative window, frames 50–74, has no primary
observation to initialize a trajectory from.

The eight already-completed settings show that weaker candidate responses exist.
The table uses the reviewed labels to classify each primary missing frame across
that fixed grid; it is not a deployable per-frame threshold rule.

| Primary missing frames | Selected correctly at some existing setting | Matching raw component exists, never selected correctly | No raw match at any setting |
| --- | ---: | ---: | ---: |
| P001 representative, 50–74 | 3 | 22 | 0 |
| P001 challenge, 200–224 | 8 | 6 | 0 |
| All P001 missing frames | 11 | 28 | 0 |
| All six windows' missing frames | 14 | 32 | 0 |

At threshold 0.05, P001 representative contains a matching raw component on 22/25
frames, but its highest-mass component is correct on none. There are 306 components
across those 25 frames. At 0.025, raw availability is 23/25, selected matches remain
zero, and there are 863 components. The pretrained model had zero raw matches in
that window at every tested setting. Adaptation supplies useful new nearby
responses, but labels are currently needed to identify which ones match. A nearby
component in a cluttered heatmap is not independent proof of physical ball identity.

## Lowering one threshold does not solve the problem

Each cell is matched / wrong / missing on eligible frames. The final column counts
emissions during the single five-frame hidden episode in P003.

| Threshold | P001, 50 eligible frames | P002 and P003, 95 eligible frames | Hidden alarms |
| ---: | ---: | ---: | ---: |
| 0.50 | 11 / 0 / 39 | 87 / 1 / 7 | 0 |
| 0.40 | 12 / 0 / 38 | 86 / 2 / 7 | 0 |
| 0.30 | 14 / 2 / 34 | 86 / 4 / 5 | 0 |
| 0.20 | 17 / 7 / 26 | 86 / 6 / 3 | 0 |
| 0.10 | 19 / 31 / 0 | 79 / 15 / 1 | 2 |
| 0.05 | 12 / 38 / 0 | 73 / 22 / 0 | 5 |
| 0.025 | 10 / 40 / 0 | 49 / 46 / 0 | 5 |
| 0.01 | 3 / 47 / 0 | 23 / 72 / 0 | 5 |

The task is to discriminate ball evidence from competing responses while preserving
abstention. A threshold-only change trades many missing outputs for wrong outputs.

## The strongest pixel is usually elsewhere in the worst window

A separate descriptive calculation mapped the single strongest pixel in each saved
adapted mean heatmap through the existing source-coordinate transform. This asks
whether component size or weighted centering discards a stronger ball signal. It
does not run the model again or propose forced output as a tracking policy.

Forced peaks match 110/145 eligible frames, are wrong on 35 and emit on all five
hidden frames. They retain all 98 primary matches and recover 12 of the 46 missing
frames. Within P001, they recover nine of 39 missing frames; the other 30 have
wrong strongest-pixel positions. In P001 representative specifically, only 2/25
peaks match, with a median error of 1,228 source pixels. The competing peaks are
usually far from the reviewed ball, not merely slightly off-center.

Component extraction does matter on individual frames: P003/303 becomes correct
under the peak diagnostic, while P001/73's component match at threshold 0.1 is lost
under its strongest pixel. But replacing largest-mass selection with strongest
pixel selection does not fix P001's main weakness. Better visual discrimination
remains the principal next hypothesis.

## What the training labels do and do not establish

The first fit used only three one-second pilot scenes: 66 eligible centers, eight
hidden frames and one ambiguous masked frame. P001's training centers occupy
approximately x1054–1524/y566–730 in source pixels; its representative development
centers occupy x223–286/y633–660, and challenge centers x312–439/y204–290.

All 25 representative P001 labels have both hand and player overlap; only four
P001 training frames have player-overlap tags. P002 supplies 16 eligible
player-overlap training examples, so this is not an entirely unseen difficulty
category. The longer training occlusion ends at its window boundary and does not
provide a subsequent visible recovery within that training window.

These observations motivate better appearance/occlusion diversity but do not prove
positional bias, inadequate image scale or any single visual cause. There are no
ball-size labels; annotation uncertainty radius must not be treated as ball radius.
All six development windows remain excluded from training. Their repeated use for
development decisions must not be described as independent generalization.

## Motion history and review observations

Ryan's two attached examples show yellow RF top-one marks while adapted WASB
reports missing: a bleacher distractor at P002/49 and a dark-uniform distractor
during referee occlusion at P003/168. His broader P001/P002 observations remain
preserved without inventing additional frame IDs or method-specific error counts.
See the [completed human review record](../configs/ball_tracking/reviews/wasb_basketball_adaptation_visual_review_v0_1.json).

Motion may help choose weaker observed candidates near an established ball track.
It cannot supply a trustworthy starting identity in P001's entirely unanchored
representative window. Earlier [motion experiments](ball_crop_motion_factorial_results.md)
showed persistent false paths and false two-frame support; [player-context work](ball_crop_player_context_results.md)
showed that player proximity does not reject player-adjacent occlusion mistakes.
Do not repeat those broad parameter grids or silently fill hidden intervals.

## Concrete next data step

The [training-data expansion proposal](ball_wasb_training_data_expansion.md)
identifies 75 new training-only frames, with source-only previews: P001/100–124,
P001/250–274 and P002/343–367. The P001 scenes add left-side ball appearances;
the P002 addition extends the existing training episode beyond its occlusion into
visible ball recovery. Ryan approved the additions and one fit after label review;
[three annotation drafts are ready](ball_wasb_training_expansion_annotation_guide.md).
The labels and new fit are not complete. Existing evaluation/holdout windows remain
out of training, and the added human labeling/review work remains explicit.

## Saved evidence

The create-only diagnostic records live under
`data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/diagnostics/`:

- `saved_grid_gap_diagnosis.json`, SHA-256
  `8f9c9d6763885f3f61d8fe02dccacf911d6fae51e42e31b2957f5a4928050b5c`;
- `saved_grid_diagnosis.py`, SHA-256
  `9a9e779ae49e34b06af9415c90f73a8188b9332626768291d6c49f7c61abd573`.
- `adapted_peak_diagnosis.json`, SHA-256
  `b4d0454f1cc1920f8e908832c4f85974c3f7dbe48451a0c2106ae5d456f77942`;
- `adapted_peak_diagnosis.py`, SHA-256
  `a2bb51d2597ae1ac5ca63273ddfd891b4da97f0cd554af3a2648a5af5774b7a2`.

The aggregation reconciles the 48 adapted and 48 pretrained saved window/threshold
cells, existing primary reports and exact missing-frame classifications. Its 104
input bindings preserve which records were inspected. It did not run inference,
training, point scoring, a new threshold screen, tests or holdout access. Earlier
evidence and failed attempts remain unchanged.

The separate peak calculation reads six bound mean-heatmap caches and development
annotations. Its transform matrices match the recorded producer metadata in all
six windows, using the same float32 homogeneous point and ten-source-pixel radius.
It produces new descriptive point-distance calculations only; no model, threshold
search, source-video decoding or holdout access occurs in that calculation.
Source-only preview preparation is a later separate step and is recorded as such.
