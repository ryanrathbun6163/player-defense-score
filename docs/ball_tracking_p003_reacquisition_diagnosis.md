# P003 occlusion-exit diagnosis

Completed 2026-10-25 (America/Phoenix), following Ryan's instruction: **"ok diagnose it"**.

## Finding

**The persistent miss is a learned loss of a weak, partly occluded ball response,
with a localization shift in the strongest surviving temporal contribution.**
The source/label join, input cache, normalization, frame alignment, contribution
count and fixed postprocessing reproduce exactly. There is no evidence here of
a delivery or indexing bug. This diagnoses the output mechanism; it does not
identify which training examples or gradient updates caused the weight change.

The accepted record marks P003 frames 165-169 fully hidden by the referee, frame
170 partly visible, and 171 onward partly visible with more exposed ball pixels.
The baseline detects 170; all ten trained checkpoints (original and augmented,
epochs one through five) first detect 171 and remain correct through 174.
That is a **one-frame / 40 ms delay at occlusion exit**.

The delay itself is within the phase's 120 ms recovery limit. Epoch three's
rejection is instead the unchanged checkpoint-selection rule: P003 must not lose
a correct count relative to epoch zero. This local diagnosis is not a full-phase
assessment, nor authority to change that rule. The retained full permitted
baseline remains 924/1,117 correct and still fails completion.

## What the replay establishes

A fixed, read-only probe used the retained baseline, original epoch three, and
augmentation epoch three. Its 30 triplet calls cover only 16 permitted native
frames and reproduce **all 15 target observations and their complete averaged
heatmap hashes exactly**. Every loaded model parameter and BatchNorm buffer is
identical before and after. No optimizer, new label, threshold sweep, training
update or protected evaluation was performed.

For frame 170, all three models receive the same three contexts:

- 168-170: two previous frames labeled fully hidden;
- 169-171: one later frame where more of the ball is exposed;
- 170-172: two later visible frames.

At the same heatmap pixel (213,213), the three responses and their original mean are:

| Checkpoint | 168-170 contribution | 169-171 contribution | 170-172 contribution | Mean at (213,213) |
|---|---:|---:|---:|---:|
| Retained baseline | 0.056329 | 0.375912 | 0.477136 | **0.303126** |
| Original epoch 3 | 0.005858 | 0.095543 | 0.313480 | **0.138294** |
| Augmentation epoch 3 | 0.014959 | 0.179046 | 0.344446 | **0.179484** |

These are sigmoid heatmap responses, **not calibrated confidence**. The unchanged
cutoff is strictly greater than 0.300. The baseline's entire averaged map contains
only two above-cutoff pixels, each a separate component: 0.30312553 and 0.30099130.
Both localize within ten source pixels, so its frame-170 success is marginal.
The original and augmented epoch-three mean maps have global maxima of 0.142459
and 0.183136 respectively: neither has any surviving component anywhere.

This is not merely useful detections disappearing through averaging. In the
170-172 contribution, augmentation epoch three retains a local pixel of 0.370756,
but the **actual weighted component center is 21.191 source pixels from the
reference**, outside the ten-pixel criterion. Original epoch three's corresponding
component error is 16.949 pixels; the baseline's correct component error is 4.377.
The trained response shifts toward the referee in the inspected source crop.
Selecting that strongest contribution would therefore produce a wrong point,
not restore a correct detection under the existing component/geometry rules.
No such replacement was applied or scored as a new method.

## Inputs, labels and alternative explanations

Frame 170 is at 6.800 seconds, PTS 87040 with timebase 1/12800. It lies inside the
original validation block 150-174 and has all three expected contributors. It is
not a boundary/padding case and is absent from the training schedule. The accepted
human amodal center remains (800.571,805.714), uncertainty radius 4.848 source
pixels, identity certain, partially visible, with the note "Ball is partially
covered by the referee". This diagnosis does not re-adjudicate that accepted label.

The verified 1920x1080 source is mapped to 512x288: one input pixel spans 3.75
source pixels. Target truncation would place its center at input (213,214),
a 3.694-source-pixel displacement, inside the ten-pixel tolerance. That unchanged
quantization cannot by itself explain why the trained mean has no component.
Every probe input matches both the original cached affine RGB bytes and the
original normalized-tensor producer exactly. All frozen source bindings verify.

The training census gives useful context, not a proven cause: P003 contributes
25 positive frames from 416-440 and no hidden frames. Across all training blocks,
there are four exact consecutive **hidden, hidden, positive** patterns (two NBA,
two P002). This narrow count excludes single-hidden transitions, masked frames
and events crossing block boundaries; it is not a count of every occlusion.
Orientation/brightness augmentation does not introduce new temporal occlusion
sequences. The current evidence cannot separate the effects of training-example
coverage, sampling, the loss function, or other learned feature changes.

The two comparison frames have distinct behavior:

- **304:** three contributions, same native context. Original epoch three's mean
  global maximum is 0.235800 and it misses. Augmentation epoch three raises the
  correct response above the cutoff (mean peak 0.369340) and recovers the match.
  The original model still has a correctly localized component in its 304-306
  contribution (9.445 px error), which its mean suppresses. Augmentation restores
  the averaged match. It preserves this baseline match, rather than adding a
  previously unseen one.
- **323:** the earlier augmentation-epoch-one failure is a component-ranking error.
  A correct candidate survives (4.516 px error, mass 17.9404), but a distant
  candidate wins (390.309 px error, mass 18.7805). Frame 323 is penultimate in its
  fixed block and has two contributions in every arm. The replayed epoch-three
  models remain correct there. Epoch one was not rerun in this probe.

The diagnostic implication is to address preservation and localization of weak
occlusion-exit evidence during adaptation, while retaining hidden-frame abstention.
This run does not establish a particular loss/sampling remedy or authorize a new
fit. Frame 170 remains validation data; no frame-specific training exception or
new target is introduced. More generic epochs are not justified by this local
result, and no replacement tracking policy is adopted.

## Visual evidence

All overlays use existing accepted geometry and saved model points. Green circles
show the ten-source-pixel scoring radius, not annotation uncertainty. Hidden
positions remain blank; no trajectory interpolation was introduced. Image checks
are assistant structural/diagnostic inspection, not new human trajectory acceptance.

- [Native context 164-174](../data/outputs/t/wasb_p003_diagnosis_20261026/native_context_164_174.png).
- [Frame 170 native and actual network input](../data/outputs/t/wasb_p003_diagnosis_20261026/frame170_native_and_network.png).
- [Individual contributions and unchanged mean](../data/outputs/t/wasb_p003_diagnosis_20261026/frame170_contributor_heatmaps.png), [PDF](../data/outputs/t/wasb_p003_diagnosis_20261026/frame170_contributor_heatmaps.pdf).

## Validation, resources and provenance

The saved-record diagnostic checks 264 records (24 frames across eleven arms),
passing 1,375 checks. Seven focused CPU tests of the additive probe pass, covering
actual validation-producer transport, full and endpoint contribution windows,
strict threshold/inclusive spatial tolerance, raw-map retention on failure,
actual synthetic cache normalization, and immutable model buffers. The real
metadata preflight and exact real-output reproduction pass. A separate audit
passes **6,681 checks**, reconstructing all 15 means byte-for-byte from the 30 raw
triplet arrays, rederiving component geometry and checking all three sets of 428
before/after tensor-digest records. No full suite rerun.

One probe attempt completed all 30 calls in **5.485 seconds**; its supervisor
finished in **8.297 seconds**, with five samples, peak **48 C**, 42.85 W and
2,426 MiB GPU memory. It exited cleanly with no stop condition, forced termination
or remaining owned process. NVIDIA Overlay, Lively Wallpaper and MSI True Color
remained stopped. The post-probe System query returned no events for the queried
interval. This small successful workload is not a PC stability diagnosis.
All original attempts, accepted labels, checkpoints and review artifacts remain.

- [Frozen probe scope](../configs/ball_tracking/proposals/wasb_p003_validation_probe_v0_1.json), SHA-256 `64c3a40e024390d0f225390a2c75b7bfd53ec1289087d9756eecdf4462db2d58`.
- [Focused validation receipt](../data/outputs/t/wasb_p003_diagnosis_20261026/validation_receipt.json).
- [Saved-record diagnosis](../data/outputs/t/wasb_p003_diagnosis_20261026/saved_record_diagnosis.json).
- [Actual replay completion and raw-map bindings](../data/outputs/ball_tracking/wasb_p003_diagnosis_v0_1/attempt_001/completed.json).
- [Independent replay audit](../data/outputs/t/wasb_p003_diagnosis_20261026/independent_probe_audit.json).
- [Visual manifest](../data/outputs/t/wasb_p003_diagnosis_20261026/visual_manifest.json), [heatmap figure manifest](../data/outputs/t/wasb_p003_diagnosis_20261026/heatmap_figure_manifest.json).
- [Supervisor completion](../data/outputs/ball_tracking/wasb_p003_diagnosis_v0_1/monitoring/attempt_001/finished.json).
