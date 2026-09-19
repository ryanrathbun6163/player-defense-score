# Fixed overlapping-crop detector comparison

Status: concrete proposal for the next development experiment. No inference,
implementation, operating-point selection, or holdout release is recorded by
this document. Machine-readable scope:
`configs/ball_tracking/proposals/rfdetr_medium_tiled_development_comparison_v0_1.json`.

## Question

Does giving the existing detector more image detail improve ball-candidate
coverage and localization enough to justify the additional false guesses and
computation? The reviewed temporal experiment exposed both candidate scarcity
and suppression of correct observations. See
`docs/ball_temporal_association_results.md` for all-grid evidence.

## Fixed scope

Use the same six already labeled and reviewed development windows:

| Possession | Representative | Challenge |
| --- | --- | --- |
| P001 | 50-74 | 200-224 |
| P002 | 250-274 | 25-49 |
| P003 | 300-324 | 150-174 |

All sources are 1920 by 1080 at 25 fps. Use the existing RF-DETR Medium 1.9.1
package and exact official weight hash, CUDA FP32, uncompiled, one input per
call, 576 by 576 direct RGB resize, and the frozen class/export rules. Do not
train, download another model, change confidence calibration, or expand frames.

Compare two image-input arms:

1. **Whole-frame control:** reuse all six saved detector outputs at
   `84bcc8da143e54ff17a28b39db0e70c4b8b299c8`; do not rerun or modify them.
2. **Four-crop union:** run the same model on these four fixed rectangles,
   in this order. Coordinates are half-open `[x0, y0, x1, y1)` source pixels:
   `tl=[0,0,1152,648]`, `tr=[768,0,1920,648]`,
   `bl=[0,432,1152,1080]`, `br=[768,432,1920,1080]`.

Each crop is 60% of the frame width and height, with 20% of the full dimension
overlapping its neighbor. The grid covers the whole image and is independent
of ball labels, player tracks, previous detections, or court geometry. All four
crops run on every frame, including reviewed hidden-ball frames. With the same
model resize, an object occupies 5/3 as many input pixels along each dimension
when fully inside a crop. This is geometry, not a promised accuracy gain.

There are exactly 150 source frames and 600 new crop-level model calls. Actual
runtime and GPU memory must be measured; four calls per frame do not imply an
exact fourfold end-to-end wall time. Reduced context and crop-edge truncation
may hurt performance. Preserve these failures for review.

## Candidate and provenance contract

Keep every exported COCO sports-ball candidate at the inclusive 0.01 floor
from every crop. Preserve crop-local candidate indices, confidence, box,
center, crop rectangle, and source-frame index. Translate crop-local geometry
back to source pixels by adding the crop origin, without label-based movement.
Use the existing crop-local clipping/validation behavior before translation.

Create a separate tiled-output schema; never label the union as the frozen
whole-frame image-only output. Record original detector provenance, actual
runtime, new execution commit, input view, source hash, and global ordering.
Sort global candidates by descending confidence, global box coordinates,
declared view ordinal, then local candidate index; assign contiguous global
indices. Preserve the local-to-global mapping.

Apply no NMS, deduplication, edge-based rejection, tracking, smoothing,
interpolation, or ball-handler inference. Overlap can produce duplicates;
retain them and count their cost rather than hiding them. The raw union
excludes the saved whole-frame candidates: combining full-frame and cropped
outputs would be another experiment.

Inference may open only source frames and model/runtime inputs. Label files
and their geometry are available solely to later scoring/review. The runner
must reject any window outside this proposal, including all holdouts.

## Fixed evaluation and review

For each image-input arm, score both all candidates and the highest-confidence
candidate per frame, with deterministic global-index ties. Top-one is a
control, not a selected policy. Keep all nine confidence values and five
source-pixel localization radii from the existing protocol:
`0.01,0.03,0.05,0.10,0.15,0.20,0.25,0.35,0.50` and `5,10,15,20,30`.
Use the same reviewed labels, raw-distance matching, null hidden-frame
geometry, and separate representative/challenge pools.

This yields 1,080 per-window report cells across both image arms and both
selectors (540 saved-control cells and 540 new cropped-input cells). Retain
per-possession results. Report correct matches, misses, false guesses,
duplicates, hidden-frame false alarms, localization errors, candidate counts,
and per-frame inference time. Quantify newly recovered and newly lost matches
relative to the saved control at identical settings. Candidate availability at
the export floor remains a label-assisted diagnostic, not tracker accuracy.

Predeclare 12 synchronized review clips: six windows at confidence 0.20 and
0.35, radius 10. Each has four panels: whole-frame raw, whole-frame top-one,
crop-union raw, crop-union top-one. Include native overlays, unmarked source
closeups, crop-edge context, every frame and final frame, and P003's hidden
interval 165-169. Review all six windows, including deteriorations.

## Implementation and execution boundary

Implement separate crop/output contracts, a resumable runner, scoring adapters,
and review support without weakening existing v0.1/v0.2 contracts. Synthetic
tests must cover complete crop coverage, boundary coordinates, local/global
mapping, duplicate retention, equal-confidence ordering, empty inputs,
malformed provenance, exact resume, tamper refusal, forbidden windows, and
scoring parity for the saved controls. Run focused tests, the full suite using
`.venv` with bytecode disabled, and `git diff --check`.

The current temporal authorization is bound to saved detections and its
unchanged specification; it cannot authorize these 600 new crop predictions.
Bind approval of this concrete proposal in a new receipt before real inference.
Real execution must use an independently validated executable manifest and a
clean implementation commit. Git staging and committing remain separate user
steps. This proposal JSON is outside the executable experiment registry.

Create new ignored outputs under
`data/outputs/ball_tracking/tiled_development/rfdetr_medium_tiled_development_comparison_v0_1/`.
Never overwrite reviewed outputs. Resume only exact matching provenance.
Keep the original nine v0.1 embargo paths absent and all three holdouts sealed.

No upstream reviewed player decision changes; no player-pipeline
`--rerun-from` stage is involved. This remains Phase 2 ball measurement. A
detector/tracker operating point and quality gate require a later explicit
decision from reviewed evidence, before any separate holdout release.
