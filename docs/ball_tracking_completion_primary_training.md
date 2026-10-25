# Completion campaign: accepted package and primary training

The final curated reference group has Ryan's explicit acceptance: **“Accept all
269 proposals.”** This closes the permitted reference-labeling milestone. The
campaign approval already authorizes the primary fit after the accepted package
and executable recipe are frozen. No repeat fit approval is required.

## Fixed roles

The complete curated census contains **1,273 permitted judgments**. New campaign
curated labels remain evaluation-only. Historical NFHS roles are retained:
**150 training frames** and the existing **150 development frames** used for
checkpoint selection. No protected labels or images enter the package.

The fixed NBA package contains **3,839 accepted judgments**: **2,879 training**
from CHI–IND, DEN–BOS and SAC–MEM, and **960 checkpoint-validation judgments**
from HOU–OKC. Retain the earlier **300 accepted SAC training frames**. Parent
games and their alternate encodes keep their roles; DET and TOR stay excluded
from fitting and checkpoint selection. The completed curated census is evaluated
only after selecting a checkpoint.

This gives **3,329 training frames in 26 blocks** and **1,110 selection frames
in 12 blocks**, with **3,103 usable training triplets**. Another **174 triplets**
have no supervised outputs and are retained as exclusions. Unknown outputs are
masked. The package records source identities, native timing, reference
authorship and acceptance. All **4,439 distinct source-frame images** are present.

The [validation-reference audit](../data/outputs/ball_tracking/completion_campaign_v0_1/training_implementation/validation_reference_coverage.json)
checks all 960 HOU–OKC frame/label/timestamp joins: **882 centers and 78 nulls**,
including **34 certain-hidden frames**. Frozen source reviews cover held ball,
ordinary movement, overlap, pass/shot and small/distant views. Accepted e05/e06
labels include occlusion followed by sustained eligible visibility. Events at
window boundaries and ambiguous transitions retain their censoring; this is
available reference coverage, not a claim about model recovery performance.

## Executable recipe

The [frozen recipe](../configs/ball_tracking/completion_campaign/primary_recipe_v0_1.json)
has SHA-256 `d8f53baf72412db535e989b4086e8fb23e02f79ef058829539d1bbe9a486e83c`.
The final producer rebuild and the real runner's read-only preflight both passed
before model execution. The recipe binds 25 local implementation dependencies,
the complete accepted package and all 20 planned epochs.

The primary fit retains WASB at **512×288**, starting from checkpoint
`09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`.
It uses three chronological native RGB frames, batch two, fresh Adam at 0.0001,
seed 1234, the existing gamma-2 masked binary loss and 2.5-pixel target disk.
Batch-normalization running statistics remain frozen; all parameters remain
trainable. No augmentation, mining, threshold search or temporal resampling is
added.

The sampler allocates 25% of draws to NFHS replay and 75% to NBA, balanced over
the three NBA games and then their episodes. Persistent shuffled queues carry
across epochs. One epoch has exactly the number of usable training triplets in
draws. Cumulative quarter quotas use deterministic half-up rounding; actual
fractions, repeats and distinct triplet/frame coverage are recorded. An odd
draw count produces a final singleton batch rather than an extra sample.

The loader verifies accepted native PNG bytes and RGB hashes, performs the same
affine warp as the retained adapter, and stores each warped frame once as uint8
on disk. It assembles normalized float32 triplets on demand. This avoids scaling
the older cache of every complete float32 triplet. Partial cache attempts are
preserved; only completed, hash-verified blocks are reused after a restart.

The [NFHS input manifest](../data/outputs/ball_tracking/completion_campaign_v0_1/training_inputs_nfhs_v0_1/package_inputs.json)
contains all **300 historical training/selection inputs**. Five already approved
training blocks were prepared separately in **32.181 seconds**, with all 150 PNGs
matching a second native-PTS-trimmed extraction. The six existing clean validation
PNG sets were reused and verified in **6.628 seconds**. Older ACL-restricted review
directories were left alone. The package uses actual source PTS at timebase
1/12800: P001/P002 start at 512, P003 at zero, with 512-tick display intervals.
Original synthetic index/25 timestamps remain unchanged in historical records.
No new labels or model work were needed. Codec-internal reference dependencies
remain uninstrumented; successful preparation returned only permitted frames.

Epoch zero is the retained model. Validate it and each trained epoch on exactly
the same fixed contexts. Keep strict `>0.3`, ascending float32 aligned-contributor
averaging, component-mass selection and inclusive ten-source-pixel matching.
Within each of the three NFHS possession cohorts and the fresh NBA cohort, an
eligible checkpoint cannot lose baseline correct matches or add wrong eligible
outputs or certain-hidden emissions. Rank eligible checkpoints by NFHS matches,
NBA validation matches, shorter worst eligible NFHS missing run, then earlier
epoch. A tie retains the earlier checkpoint, including epoch zero.

Run at most 20 epochs. After at least five, stop when five consecutive epochs
have not improved the selected rank. Save the best and final checkpoints plus
resumable optimizer/RNG state and actual exposure. If epoch zero wins, retain it
and reject the trained model for adoption. Selection is not a ball-phase pass.

## Current execution state

All **32 focused checks passed** on the final package, policy, runtime and runner
modules: native-frame/annotation joins, role and protected-band exclusion,
unknown supervision, exact preprocessing, balanced sampling, nonregression
selection, checkpoint transport and interrupted-run recovery. The
[validation receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/training_implementation/focused_validation.json)
binds the actual source and test bytes; the full suite was not repeated.

The initial loader fixture had two invalid schema enum values; correcting those
and closing memory maps explicitly fixed the test failures. The first full
package preflight rejected SAC display intervals because a generic packet helper
used raw packet duration. The correction uses the existing SAC presentation
census and next-frame PTS, retaining original evidence. The corrected preflight
passed in **83.644 seconds**. A final package rebuild during the freeze also
checks all 300 NFHS joins against independently bound native packet records.
These were implementation checks, not scientific fitting attempts.

At this pre-fit checkpoint, **no completion-campaign model inference or optimizer
update has run**. Source labels, original review artifacts and failed attempts
remain preserved. The frozen recipe binds the accepted package, complete
20-epoch sampling schedule, implementation dependencies and runtime versions.
Each epoch draws 3,103 triplets in 1,552 updates, ending with one singleton batch.
Durable update logs and optimizer/RNG saves every 25 updates preserve recovery
evidence; completed epoch model files and validation reports are retained.

The single conditional resolution fit remains subject to the approved
[census and deficit trigger](ball_tracking_completion_plan.md#training-campaign-one-primary-fit-and-one-conditional-fallback).
The **225 protected holdout/buffer positions remain closed** until a frozen
method and separate explicit authorization. New model trajectories still need
Ryan's visual review.
