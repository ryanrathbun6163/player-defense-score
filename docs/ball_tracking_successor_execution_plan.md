# Approved successor execution: duration control and conditional image tracker

Prepared 2026-10-25 on `codex/ball-detector-baseline` at
`3f37e2880c39e89c64c0000951eccbf2501c5974`, with a clean worktree/index before
these additive files. The machine-readable scope is
[successor_v0_1](../configs/ball_tracking/proposals/ball_tracking_successor_v0_1.json).

Ryan approved the [critical assessment](research/ball_tracking_next_step_review_2026-10-25.md):
**“Thank you for this assessment chat. I like this, and I am cool to move forward with it”.**
His earlier instruction remains active: **“Ok I lift the pause. Please monitor the GPU as we go, and lets move forward”.**
This authorizes the assessment, bounded continuation and conditional pilot below,
including routine implementation and compatibility preparation. It is not a new
approval gate for those routine choices. Protected evaluation remains closed.

## Fixed scope and sequence

1. Assess the preserved epoch-five model once on its accepted training contexts:
   positive matches/wrong/missing, certain-hidden emissions and unknowns by source,
   plus separately normalized positive/background/hidden loss contributions.
   Keep repeated output-channel exposures separate from unique frame counts.
   Use complete original block contexts and the unchanged WASB inference policy.
   This is training-fit evidence, not validation; do not score the rejected epoch
   on the complete post-selection census or choose new thresholds from it.
2. Run one additive epoch-five-to-ten duration control, unless the training-fit
   evidence makes it clearly uninformative; record that decision if skipped.
   Preserve all original settings except the explicit stopping budget. No automatic
   HLSM, negative weighting, replay change, augmentation or resolution fit follows.
3. If the selected continuation does not close the permitted development screen,
   run the single automatically WASB-seeded TAPNext++-512 policy below after
   compatibility preparation. Release preparation may overlap CPU-only work;
   root serializes all GPU workloads and supervises the actual processes.
4. Deliver the fixed comparisons and a definite retain/reject decision. Any later
   learning/data/architecture intervention is a separate evidence-based choice,
   not a queued extra arm. Preserve all failures and accepted references/reviews.

## Exact continuation contract

The parent is the completed five-epoch run at
`data/outputs/ball_tracking/completion_campaign_v0_1/primary_fit_v0_1/`.
Load `states/update_007760.pth` with original identity, preserving model tensors,
Adam moments/steps, RNG, losses, BatchNorm reference and epoch/batch position.
Do not restart from the model-only `checkpoints/epoch_005.pth`.

Use the original frozen package and schedule, specifically epochs 6–10:
**7,760 additional updates, 15,520 cumulative updates**, ending at epoch 10.
Suppress the old five-epoch early-stop condition only for this bounded control.
Keep the original retained epoch zero, inherited epoch 1–5 reports and exact
selection function; validate and select across epochs 0–10. Existing reports
retain their original identities and are imported by verified reference.
The new run binds its parent state, parent completion, original recipe and its
own implementation. A new output root is not a new independent initialization.

Use additive code. The original runner would return its completed result and
also stop again at epoch five; changing its `max_epochs` alone is insufficient.
Restore RNG after initialization and around validation. Verify the first new
batch is the original epoch-six batch one and update 7,761. New checkpoints,
logs, failures and cleanup are confined to the successor root. Never delete or
rewrite the parent result, epoch-five optimizer state, original failed attempts,
earlier recovery states, validation reports or frozen dependencies.

If epoch zero still wins, reuse the existing complete comparison without new
baseline inference. Otherwise compare the selected candidate once on the bound
permitted package using the unchanged score/cohort contract. Selection success
does not establish phase success; rejected epochs are not full-census candidates.

## One TAPNext++ policy, fixed before scoring

Use source commit `730cda1c730877cfedbe01bf87fb1cadb78a565d`, the official
generation-pinned 512 checkpoint and the exact upstream support-point generator:
one real query plus **64 local support points**. Support outputs are never ball
observations. Store float32 weights, CUDA float16 autocast, eager inference with
no compilation, full model depth, and stream one prepared frame at a time.
The original retained WASB `09da1214e94f…` is always the seed source, even if the
continuation selects another checkpoint. This isolates the new tracker policy.

Apply this state machine independently to each complete block below:

1. Begin without tracker state. A seed is the current retained-WASB selected
   point if finite and in source-image bounds. Use no reference, future seed,
   semantic label, mass cutoff or human rescue. Before a seed, publish missing.
2. On the first seed frame, start fresh state with that query and the official
   support points. Preserve the exact WASB seed coordinate as provenance, not
   as a forced published point. There is exactly one initialization per block.
3. On the seed frame and every subsequent frame, use the current-image tracker
   result. If the real-query
   visibility logit is **strictly greater than zero** and its source coordinate
   is in bounds, publish that TAP coordinate as an automatic image-conditioned
   observation. Do not substitute WASB merely because the two disagree.
4. Otherwise publish missing and retain the hidden tracker state to permit
   image-based re-detection. There is no detector fallback or reseeding inside
   the block, even when WASB has a point. This avoids overriding a hidden vote
   with a detector false alarm. Later WASB points are comparison evidence only.
5. Nonfinite outputs, decode failures or inference failures are operational
   failures, never ordinary model misses. Preserve the failed attempt. Predicted
   hidden/out-of-image coordinates remain diagnostic fields only and are never
   drawn as trajectory points or counted as automatic observations.

Log disagreement distance whenever both methods have in-image points; it does
not gate, fuse or move a coordinate. Use no extra certainty cutoff, periodic
reset, distance/speed threshold, interpolation or sweep. The visibility default
comes from the release, not a claim of calibrated ball correctness. A wrong seed
or confidently drifting track may persist; that is a central measured risk.

Reset state at every block boundary, protected interval and declared source cut.
The bound blocks are existing uninterrupted action segments; this pilot adds no
cut detector. Unexpected source discontinuity is an input failure. Never bridge
a protected boundary or read a protected image. Preserve exact native PTS and
display intervals; no frame duplication, deduplication or temporal resampling.
WASB seeds already contain their original future image context: make no live or
strictly causal system claim.

| Complete permitted block | Frames |
|---|---:|
| P001 0–274; 350–498 | 424 |
| P002 0–174; 250–498 | 424 |
| P003 0–224; 300–499 | 425 |
| SAC–MEM 540–2010 | 1,471 |
| SAS–DET 10668–11898 | 1,231 |
| Total, eight independently reset blocks | 3,975 |

Consume the already prepared package/PNG and original observation bindings.
Inference receives a label-free projection: source/frame/PTS, image binding,
dimensions, retained observation and reset metadata only. Seal predictions
before scoring against accepted references. Keep SAC training-exposed cohorts,
DET excluded development, curated exposure roles and all unscored NBA context
separate. The 225 protected timeline positions remain black/withheld metadata.

## Compatibility, preservation and verification

The checkpoint is 2,532,283,010 bytes. Verify its generation/length/MD5 and freeze
local SHA-256 after download; no upstream SHA-256 was provided. Use an ignored
pinned source checkout and subprocess-only isolated `einops==0.8.2`, preserving
the existing frozen environment. JAX, TensorFlow and the VOT toolkit are not
needed for the inspected direct PyTorch inference path. Actual loading/CUDA
memory compatibility is still unverified; no RTX5070 speed claim is made.

Before scientific inference, save an immutable execution receipt binding this
proposal, implementation, downloaded weights, source and runtime. Test exact
512-input/256-coordinate transforms, BGR/RGB handling, support-point generation,
visibility zero boundary, one-seed-per-block initialization, hidden suppression, failure
   semantics and actual emitted-record/scorer/render transport. A brief feasibility
check may use only permitted training context, with outputs excluded from model
selection. It cannot quietly change precision or policy after scientific scoring.

Measure all per-cohort correct/wrong/missing/hidden outcomes, gained/lost points,
seed coverage, reset causes, disagreement, drift, gaps and recovery. Report all
16 existing cohorts: preserve their 13 guarded comparisons (including both 60/60
controls) and three descriptive SAC training-exposed comparisons, then apply the
unchanged full permitted curated screen. Unknown identity remains unknown;
inconclusive required judgments cannot become a pass. Render synchronized
baseline/candidate evidence at exact native timing through actual final frames.
This is a complete declared output policy, not gap filling that preserves all
baseline errors. A pilot pass still does not authorize protected evaluation or
establish full-clip acceptance; Ryan retains final trajectory review.

Root retains GPU telemetry and owned-process supervision for actual work. Stop
on device loss or new instability and preserve the durable recovery state.
Compatibility failures permit routine repairs with separate receipts; they do
not authorize scientific parameter searches. Tests stay focused, generated
artifacts stay ignored, and no new audit framework or repeated old review is needed.
