# Proposed comparison: YOLO11x on the six saved development windows

Status: concrete design for review; not implemented, approved or executed.

The reviewed player-context experiment reduced distant distractors but cannot
recover absent candidates or distinguish false proposals inside player boxes.
This comparison asks whether one complementary image detector supplies better
ball evidence. It does not combine another tracking change or choose a winner.
The rationale and remaining cases are in `ball_crop_player_context_results.md`.

## One frozen challenger

Use official **YOLO11x Detect**, a generic COCO detector with 80 categories,
including sports ball. It is not a basketball-specific model. The choice is a
bounded comparison of a different detector family, made before running these
frames; published COCO performance does not predict success here.
[Official model documentation](https://docs.ultralytics.com/models/yolo11/).

- Package: `ultralytics==8.4.171`, tied to the
  [versioned release](https://github.com/ultralytics/ultralytics/releases/tag/v8.4.171).
- Weight file: `yolo11x.pt` from
  [official assets v8.4.0](https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11x.pt).
  Publisher SHA-256:
  `7bc158aa95c0ebfdd87f70f01653c1131b93e92522dbe15c228bcd742e773a24`.
  This is the [published digest](https://github.com/ultralytics/assets/releases/expanded_assets/v8.4.0),
  not a claim that local bytes have already been downloaded or verified.
- Source class 32, name `sports ball`, maps explicitly to the repository's
  COCO category 37; these numbering systems must not be interchanged.
  [Versioned COCO class map](https://raw.githubusercontent.com/ultralytics/ultralytics/v8.4.171/ultralytics/cfg/datasets/coco.yaml).
- Ultralytics documents AGPL-3.0 and Enterprise model licensing. The proposal
  records that dependency; it does not change the repository's license.
  [Model licensing](https://docs.ultralytics.com/models/yolo11/).

COCO-trained models are not independent training-data evidence. Exact training
overlap with the local footage is unverified. Preserve that limitation rather
than claiming a clean external test or reconstructing absent provenance.
No fine-tuning, new annotation or model-size sweep is included.

## Frozen image and output scope

Use the existing 150 lossless unmarked source PNGs, one for every frame in:

| Possession | Representative | Challenge |
| --- | --- | --- |
| P001 | 50-74 | 200-224 |
| P002 | 250-274 | 25-49 |
| P003 | 300-324 | 150-174 |

The machine-readable proposal binds every PNG, the source/frame metadata, six
finalized label files for later scoring, and all reused outputs. Inference must
read only the source-image inventory and model contract. It must not open
labels, review overlays, player context, court arrays or source videos.

Keep the four existing half-open crop rectangles on 1920x1080 source frames:
TL `(0,0,1152,648)`, TR `(768,0,1920,648)`, BL `(0,432,1152,1080)`,
BR `(768,432,1920,1080)`. Run one crop at a time: **600 unique project-crop
inference units**. Initialize and warm each fresh predictor with synthetic
non-project pixels before it sees any project frame. Count synthetic forwards,
project attempts and retries separately; a successful first pass has 600
project forwards. Record one completed checkpoint per unit and resume verified
completed units without executing them again.
Translate crop-local boxes back to source coordinates and preserve original
scores, local coordinates, crop IDs and all cross-crop duplicates.

Use ordinary YOLO Detect preprocessing with `imgsz=640`, `rect=False`, FP32,
batch one, CUDA, augmentation and compilation disabled. Fixed square letterbox
produces 640x360 image content with 140 pixels of padding above and below for
these crops. Record the actual transform and validate RGB/BGR conversion,
division by 255 and inverse coordinate mapping against synthetic images.
[Versioned preprocessing](https://raw.githubusercontent.com/ultralytics/ultralytics/v8.4.171/ultralytics/engine/predictor.py),
[letterbox implementation](https://raw.githubusercontent.com/ultralytics/ultralytics/v8.4.171/ultralytics/data/augment.py).

The frozen prediction contract uses `classes=[32]`, predictor `conf=0.0`,
best-class-only assignment, class-aware NMS IoU .7 and `max_det=300` per crop.
Import and verify torchvision explicitly so its NMS backend is fixed. Apply
the inclusive .01 export floor afterward. Preserve postprocessor return order
as provenance, then use the existing deterministic crop/global ordering.
Record pre-export count and cap saturation; reject NMS timeout/error outputs.
[Versioned NMS implementation](https://raw.githubusercontent.com/ultralytics/ultralytics/v8.4.171/ultralytics/utils/nms.py).

Call these **postprocessed/exported candidates**, not raw head proposals.
An absent exported match may reflect learned scores, best-class assignment,
suppression or the internal cap; final outputs cannot separate those causes.
Do not claim equal candidate budgets or isolate architecture from preprocessing
and postprocessing. RF-DETR used direct 576x576 resizing without NMS; this is
a comparison of complete detector configurations. Equal numeric confidence
thresholds are not equal calibrated probabilities.

## Paired comparisons and accounting

For each detector retain three selectors: all exported candidates, highest
confidence, and highest twenty. Filter inclusively by original confidence,
then order by confidence descending and original global index. Leave empty
frames empty. Do not add graphs, player costs, deduplication, interpolation,
new geometric corrections, appearance filters or retrospective revisions.

Reuse all 162 saved RF-DETR crop selector outputs and their 810 reports from
the existing motion comparison. Do not rerun old inference, selection, scoring
or rendering. New provenance belongs only to the challenger outputs.

Use the unchanged confidence grid `.01,.03,.05,.10,.15,.20,.25,.35,.50` and
source-pixel radii `5,10,15,20,30`. Keep representative/challenge pools separate.
Use the same raw-center matching with annotation uncertainty diagnostic only.
Report availability at the export floor, subsequent confidence/selector loss,
matches, false/hidden observations, duplicates, missing runs and center errors.
Show every paired gained/lost frame, not only pooled improvements. Report both
models' full curves; never infer model superiority from one equal-score cell.

| Artifact | New challenger | Reused control | Combined |
| --- | ---: | ---: | ---: |
| Source frames / unique project-crop units | 150 / 600 | 0 rerun | 150 frames |
| Window candidate files | 6 | 6 existing | 12 |
| Selector/confidence/window outputs | 162 | 162 | 324 |
| Per-window/radius reports | 810 | 810 | 1,620 |
| Aggregate cells per separate pool | 135 | 135 | 270 |

Prepare twelve paired 25-frame clips at 5 fps, at .20/.35 and radius 10.
Rows compare all exported, top one and top twenty, with unmarked source and
clear legends available. Reuse exact old native control PNGs. Include native
views and source-scale closeups; mark YOLO's NMS/cap policy in the legend.
Review every final frame. Highlight unavailable P001 59/67-69 and P002 257,
confidence-sensitive P001 74, P002 262, P003 representative 300-308,
hidden 165-169, reacquisition 170-174, and P001 passes 200-201. These are
diagnostic contrasts, not a new performance gate or semantic relabeling set.

## Implementation and execution conditions

The local baseline environment has no Ultralytics installation. Prepare an
isolated ignored environment and record exact wheel/source hashes and the
resolved dependency inventory; preserve the reviewed baseline environment.
Verify downloaded checkpoint bytes against the published digest before loading
them, then inspect class names, task, stride and embedded training metadata.
Keep unavailable training provenance explicit. Test installed runtime/CUDA
compatibility without feeding project frames. No package/model is installed,
downloaded or loaded by this proposal.

Implementation should be separate and synthetic first: independent tests for
mapping, threshold inclusion, class-number translation, NMS/backend pinning,
cap/timeout handling, ordering, empty outputs, resumability, provenance rejection,
label isolation and unchanged controls. Then run the full suite. Freeze actual
dependency/runtime evidence before real execution; a contract mismatch requires
review of the change, not silent substitution. A fresh ignored output root and
a separately authorized clean tested code commit are required.

The companion JSON is a proposal, not an executable manifest or release.
Experiment approval covers only this one challenger and six-window design;
Git staging, committing, pushing, PR creation and merging remain separate.
All nine original embargo paths stay absent. P001 300-324, P002 200-224 and
P003 250-274 remain sealed. No operating point, quality gate, production method
or holdout release is selected. These repeatedly inspected windows support
development decisions, not an unseen-game generalization claim.
