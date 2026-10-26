# Approved five-epoch WASB augmentation experiment

Prepared 2026-10-25 (America/Phoenix), from branch
`codex/ball-detector-baseline`, HEAD
`7030aa612b8800bf1f9f3efc4d5febc1da9fee99`, initially clean.

Ryan explicitly authorized: **"Ok chat, let's move forward with the five-epoch
WASB augmentation experiment. Keep the quality criteria unchanged, use our
existing labels, and monitor the GPU as we go."** This authorizes preparation,
the bounded fit, checkpoint selection and the conditional permitted comparison
described here. It does not open protected evaluation or authorize another
labeling campaign. The optional TAP seed diagnostic is not part of this work.

## Question

Does one fixed, mild training-augmentation recipe improve transfer while
retaining the existing validation protections? The prior epoch-five checkpoint
fits 2,931/2,941 eligible training frames, including all 130 NFHS training
positives, but fails checkpoint selection. The retained baseline separately
scores 924/1,117 on the full permitted curated census. Those are different
models and splits; they are not a direct same-checkpoint accuracy gap.

The original five-epoch fit is the unaugmented control. Its original outputs,
failed attempts, completed result and recovery history remain unchanged. No
duplicate control fit is required. This is a hypothesis, not a promised phase
pass or proof of the original failure mechanism.

## Fixed intervention

Only training inputs/targets receive augmentation. For each sampled triplet:

- With probability 0.5, reverse the horizontal pixel order of all nine image
  channels and all three already-rasterized target maps together. This is an
  exact discrete mirror, without another interpolation or target quantization.
- Draw one brightness multiplier uniformly from [0.9, 1.1], shared by all three
  RGB images. Recover the original cached uint8 pixels from their normalized
  tensors, multiply in float32 pixel space, clamp to [0,255], and apply the
  unchanged normalization. There is no rounding after the brightness change.
- Use a separate deterministic SHA-256-derived random stream keyed by seed
  1234 and the epoch, batch and sample positions. Do not consume the original
  Python, NumPy or Torch random streams. The frozen sample schedule binds the
  identity of the triplet at every position.

No crop, translation, scale change, rotation, blur, temporal resampling, new
hidden target or synthetic ball is introduced. Target maps remain binary.
Certain-hidden zero maps and supervision masks stay unchanged; masked channels
remain excluded from the loss. No validation or evaluation image is augmented.
The exact numeric policy and implementation bytes are bound before execution.

These transformations deliberately preserve tiny-object geometry while testing
orientation and mild brightness variation. They cannot create new camera angles,
occlusion situations or independent scenes, and therefore may not solve the
remaining transfer failures.

## Controlled fit and stopping rule

Start again from the retained WASB checkpoint
`09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`,
with the original fresh Adam initialization and seed. Do not continue epoch-five
weights or optimizer state. Use the original accepted package (3,329 training
frames, 1,110 checkpoint-selection frames, 3,103 usable triplets), existing cache,
and **exactly the first five epochs of the frozen original sample schedule**.
The update budget is **7,760**, with 25% NFHS / 75% NBA sampling unchanged.

Keep 512x288 inputs, batch size two, Adam learning rate 0.0001, original gamma-two
masked weighted binary cross-entropy, target radius, float32 training and frozen
BatchNorm running buffers unchanged. All original trainable parameters remain
trainable. Save every epoch checkpoint and retain resumable optimizer/RNG state
every 25 updates. Preserve failed attempts and any replayed unsaved updates.

Validate each trained epoch on the same original native selection contexts,
without augmentation. Retain the original epoch-zero reference and use the
unchanged per-cohort nonregression conditions and ranking. The experiment ends
at epoch five even if it improves; there is no automatic duration extension,
threshold change, target sharpening, mining, sampling change or second fit.

## Conditional comparison and acceptance

If no trained checkpoint is eligible, retain epoch zero and report the complete
epoch-by-epoch comparison against the saved unaugmented control. Do not run a
new full-census evaluation of rejected checkpoints or regenerate unchanged
baseline videos merely to produce another artifact.

If a trained checkpoint is selected, freeze that choice and perform one
comparison on the same eight permitted blocks / 3,975 frames. Preserve all
16 cohort reports (13 guards and three descriptive training-exposed cohorts),
the unchanged strict >0.3 threshold, component-mass choice, complete-triplet
means and native timing. Render synchronized retained-baseline/candidate
reviews through all five actual finals. The three curated timelines retain
their 225 protected positions as black, withheld slots.

The per-possession completion criteria remain: at least 95% correct automatic
positions within ten source pixels; at most 1% wrong eligible outputs; zero
certain-hidden/out-of-view emissions; no eligible missing run over 200ms;
no confirmed wrong-object run of 120ms or longer; recovery within 120ms with
the first correct and next two eligible frames correct; and complete human
review. Preserve all original unknown/censoring rules. A trained checkpoint
selection is not a full-phase pass. Protected evaluation still requires a
separate explicit authorization after method freeze.

## Verification, resources and provenance

Use focused checks derived from the actual normalization, target, sample and
validation producers. Verify exact pixel reconstruction, paired image/target
mirroring, identical triplet brightness, unchanged masks/hidden zeros, no input
mutation, separate RNG, exact resume parameters and the five-epoch boundary.
Inspect a small training-only augmentation alignment review before GPU fitting.
Verify actual emitted records against their consumers; tests do not substitute
for checking the real completed result.

The original recipe, package, schedule and its 25 source dependencies remain
hash-bound and unmodified. New augmentation and orchestration modules are
additive, with a new recipe and ignored output root:
`data/outputs/ball_tracking/wasb_augmentation_v0_1/`.

Use the existing Windows owned-process supervisor and two-second GPU telemetry.
Stop on failed telemetry/device loss, temperature at 80 C or active thermal
slowdown; preserve the current attempt and checkpoint. Do not alter hardware,
driver, power-limit, fan or clock settings. Verify the three graphics extras
remain stopped. The previous roughly 18-minute control suggests 20–30 minutes
for this fit; that estimate excludes preparation, checks and conditional
comparison/rendering and is not a guarantee. Record actual consumption.
