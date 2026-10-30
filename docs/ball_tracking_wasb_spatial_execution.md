# Authorized two-epoch spatial-augmentation experiment

October 26, 2026, America/Phoenix. Preparation starts on
`codex/ball-detector-baseline` at `3fe16da7a9202813715e7e1501af96e2f6d0bc73`,
with a clean worktree and index.

Ryan explicitly instructed: "Ok chat, let's move forward with the two-epoch
spatial augmentation experiment. Use our existing labels, keep the quality
criteria unchanged, and monitor the GPU as we go."
This authorizes execution of the [proposal](ball_tracking_wasb_spatial_augmentation_proposal.md),
including its focused implementation/geometry checks and complete comparison.
The original proposal and prior results remain unchanged.

## Matched experiment

Initialize from the exact completed 768 epoch-five full state used by the
constant and cosine continuation arms. Retain weights, Adam moments/steps and
RNG history. Train absolute epochs six and seven, exactly 3,104 additional
updates at constant learning rate 0.0001 (10,864 cumulative updates). The
already completed constant-arm epochs six and seven are the matched controls;
do not repeat their fitting or inference.

Use the same immutable sampling schedule, all existing training examples,
75% NBA / 25% NFHS mixture, original mirror/brightness draws, float32, batch two,
frozen BatchNorm buffers and gamma-two weighted binary cross-entropy. Preserve
768x432 inputs and the original binary target meaning. The single intervention
is coherent isotropic scale/translation applied to training inputs and their
targets. No new labels, validation-frame fitting, threshold search, synthetic
occlusion, blur, architecture or loss-weight changes.

Spatial probability is 0.5; requested scale is uniform in [0.9,1.1), and requested
x/y shifts are each within 3% of working width/height. Independent deterministic
keys preserve all prior random draws. One transform applies to all three frames.
The bound implementation policy specifies exact pixel-center mapping, image
interpolation, binary-target transport and constant padding. It must preserve
channel masks, check target and accepted geometry-uncertainty support, and use a
logged identity fallback when a requested transform would clip supervised
support. No wrap/reflect padding or copied ball instances are allowed.

Before freezing the executable recipe, verify the actual producer/consumer
interface and inspect representative transformed training triplets, including
partial/tiny balls, certain-hidden and masked frames, plus boundary fallback.
Retain the exact transform draws and applied/fallback counts. Original accepted
reference files are immutable; augmented targets are derived training tensors.

The implementation uses integer pixel centers and scales about (383.5,215.5),
then translates. An explicit inverse grid uses `align_corners=False`, bilinear
image sampling and nearest sampling of the existing binary target raster; no
new disk is drawn at a rounded transformed center. Padding is normalized zero
(the ImageNet RGB mean). Support checks cover original target pixel cells and
the continuous accepted uncertainty circle, before and after the transform.

CPU preparation covers all 6,206 scheduled examples: 3,127 applied transforms,
3,067 probability bypasses and 12 clipping fallbacks. Eight representative
scheduled triplets were rendered from the verified existing caches. AI inspection
of their target crops and full triplets confirms alignment, shared transforms,
unchanged hidden/masked supervision and identity fallback; this is preparation
QA, not new human labels or model acceptance. The preparation receipt and
separate AI review are bound by the recipe.

## Execution and recovery

Use additive modules and new output root
`data/outputs/ball_tracking/wasb_spatial_v0_1/`. Reuse verified 768 caches, preserve
all earlier frozen source, recipes, reviews, failures and checkpoint history.
Save both new epoch checkpoints, the initial handoff state, resumable states
every 25 updates, and all failure/replay evidence. Validate each epoch using the
unchanged native inputs, retaining the parent epoch-five validation as a reused
anchor. No prior model, evidence file or reviewed baseline is overwritten.

Run only one GPU workload at a time through the existing Windows job supervisor.
Verify the owned Python redirector/worker chain. NVIDIA Overlay, Lively Wallpaper
and MSI True Color remain stopped. Keep telemetry, conservative thermal stops
and cleanup of owned processes; no driver, clock or power changes. A new device
or telemetry failure stops the attempt without automatic retry. Correct routine
implementation issues autonomously while preserving failed evidence.

## Fixed comparison and decisions

Evaluate both new epochs on the same eight NBA contexts. Reuse each epoch's six
HOU validation outputs, infer only the existing SAC/DET contexts, and reuse the
saved parent, constant epochs six/seven and 512 controls. Preserve all per-episode
correct/wrong/missing counts, hidden emissions, native timing/recovery gates,
exact gains/losses and secondary NFHS results.

Every quality criterion remains unchanged: at least 95% correct within ten
source pixels, at most 1% wrong, zero certain-hidden emissions, no eligible
missing interval over 200ms, no human-confirmed wrong-object run of 120ms or
longer, recovery within 120ms followed by two more eligible correct positions,
and complete synchronized human review. Unknown/censored evidence stays unknown.
The nine source-uncertain recovery events cannot be cleared by training alone.

Retain both checkpoints whether they improve or regress. A promising outcome
must improve a remaining failure family without offsetting coverage or
false-emission regressions; pooled accuracy or lower training loss is insufficient.
Do not extend beyond the two epochs automatically. A diagnostic review choice
is explicit inspected development selection, not adoption. Protected evaluation
requires a frozen method and separate explicit authorization; it stays closed.

Measured prior timings suggest about 18 minutes fitting and 4–5 minutes NBA
comparison, plus preparation, audits and visual review. These estimates do not
promise phase completion. Report actual resources and uncertainty.
