# Five-epoch WASB augmentation result

Completed 2026-10-25, America/Phoenix (2026-10-26 UTC).

## Outcome

The authorized experiment completed **five epochs / 7,760 updates** in one
successful monitored attempt. **No trained checkpoint qualifies; epoch zero
remains selected.** This augmentation recipe is not adopted. The retained
baseline, accepted labels, original reviews, failed attempts and checkpoint
recovery history are unchanged. Ball tracking has not passed the completion gate.

Epoch three is a useful near miss on checkpoint-selection validation: P001
44 correct versus 41 at baseline; P002 50 versus 49; P003 **39 versus 40**;
NBA 854 versus 845, with wrong outputs reduced from 29 to nine. It fails solely
because P003 frame **170** changes from correct to missing. There are no new P003
matches offsetting that loss. All five trained checkpoints miss frame 170.
Epochs four and five regress further. These results do not support an automatic
extension of the same fit or a claim that additional epochs reliably improve it.

These are selection-set results, not a new full-census score or phase pass.
The retained full permitted result remains **924/1,117 correct**, 28 wrong,
165 missing and nine certain-hidden emissions. As specified before execution,
there was no new 3,975-frame comparison and no duplicate video rendering after
epoch-zero retention. Protected evaluation remains closed.

## Controlled experiment

Ryan explicitly approved the [five-epoch experiment](ball_tracking_wasb_augmentation_experiment.md).
The [frozen recipe](../configs/ball_tracking/proposals/wasb_augmentation_v0_1.json)
adds synchronized horizontal mirroring (probability 0.5) and one shared RGB
brightness multiplier in [0.9,1.1] per three-frame training example. Rasterized
ball targets mirror with the images; hidden zero maps and masks are preserved.
No validation images receive augmentation and no new labels are introduced.

Initialization is the same retained checkpoint `09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`,
with fresh Adam and the exact first five epochs of the original frozen schedule.
Inputs, loss, learning rate, BatchNorm policy, sampling, threshold, component
selection, native timing and quality criteria are unchanged. All 25 original
frozen source bindings, the three additive bindings and 70 accepted-reference
file bindings verified. The original unaugmented run is reused as the control.

The actual update audit confirms 15,515 draws across all 3,103 available training
triplets: 3,879 NFHS and 11,636 NBA draws. There are 7,706 mirrored samples.
Brightness gains range from 0.9000141104 to 1.0999673479, mean 1.0007820870.
There were no interrupted attempts or replayed updates in this experiment.
Original failed runs remain preserved in their original directories.

## Complete validation comparison

Each cell is **correct / wrong / certain-hidden emissions**. These counts cover
checkpoint-selection cohorts; they are not the full permitted possession census.
Epoch zero is reused from its original saved report with explicit provenance and
zero new model calls. Epochs one through five are newly validated.

### Augmentation experiment

| Epoch | P001 | P002 | P003 | NBA validation |
|---|---:|---:|---:|---:|
| 0 | 41 / 0 / 0 | 49 / 0 / 0 | 40 / 1 / 0 | 845 / 29 / 25 |
| 1 | 47 / 1 / 0 | 50 / 0 / 0 | 38 / 2 / 0 | 846 / 17 / 16 |
| 2 | 42 / 0 / 0 | 49 / 0 / 0 | 38 / 1 / 0 | 849 / 4 / 19 |
| 3 | 44 / 0 / 0 | 50 / 0 / 0 | 39 / 1 / 0 | 854 / 9 / 22 |
| 4 | 36 / 1 / 0 | 49 / 0 / 0 | 38 / 1 / 0 | 844 / 3 / 17 |
| 5 | 38 / 1 / 0 | 49 / 0 / 0 | 38 / 1 / 0 | 844 / 3 / 17 |

Only epoch zero is eligible. Epoch one also increases P001/P003 wrong outputs.
Epochs two and three fail only P003 correct-count nonregression. Epochs four and
five lose correct outputs in P001, P003 and NBA validation, and add a P001 error.
All NFHS certain-hidden emission counts remain zero on this selection set.

### Original unaugmented control

| Epoch | P001 | P002 | P003 | NBA validation |
|---|---:|---:|---:|---:|
| 0 | 41 / 0 / 0 | 49 / 0 / 0 | 40 / 1 / 0 | 845 / 29 / 25 |
| 1 | 44 / 0 / 0 | 49 / 0 / 0 | 38 / 1 / 0 | 837 / 34 / 19 |
| 2 | 39 / 0 / 0 | 49 / 0 / 0 | 38 / 1 / 0 | 850 / 9 / 16 |
| 3 | 37 / 0 / 0 | 49 / 0 / 0 | 38 / 1 / 0 | 842 / 4 / 15 |
| 4 | 39 / 0 / 0 | 49 / 0 / 0 | 38 / 1 / 0 | 850 / 8 / 11 |
| 5 | 42 / 0 / 0 | 50 / 0 / 0 | 38 / 1 / 0 | 848 / 9 / 17 |

At epoch three the augmentation run has 21 more correct outputs across the four
cohorts than the same-epoch control, but its NBA wrong outputs increase from four
to nine and certain-hidden emissions from 15 to 22. At epoch five it is worse
than the control on P001/NBA correct counts. This is one fixed paired experiment,
not evidence of a consistent benefit across epochs or independent games, and
it does not separate the effects of mirroring from brightness.

The [independent P003 comparison](../data/outputs/t/wasb_augmentation_20261026/p003_validation_changes.json)
identifies exact changes relative to the retained checkpoint:

| Epoch | Newly correct P003 frames | Previously correct frames lost |
|---|---:|---|
| 1 | 0 | 170 missing; 323 wrong |
| 2 | 0 | 170 and 304 missing |
| 3 | 0 | 170 missing |
| 4 | 0 | 170 and 304 missing |
| 5 | 0 | 170 and 304 missing |

At frame 170 the baseline localization error is 7.198 source pixels; every
augmentation checkpoint emits no candidate. The baseline selected component
mass is 0.30312553; that quantity is **not a calibrated confidence**. Saved
records establish the output change, not its visual cause or a justified new
threshold. No threshold adjustment, fallback rule or new frame-specific training
intervention was made.

## Validation and resources

**14 focused CPU checks passed**: eight for augmentation and six for the additive
runner. Checks cover actual producer normalization/targets, paired mirroring,
brightness, zero maps/masks, independent deterministic draws, recovery, actual
saved control transport and the five-epoch boundary. Independent source review
found no execution blocker. The full suite was not rerun.

Training-only visual QA covers three triplets (27 panels), preserving image/target
alignment and a certain-hidden zero map. Its separate QA cache was created before
a later cache-reuse preference arrived and is preserved; the fit reused the
original verified cache. QA read 265 training PNGs, zero validation/protected
PNGs and made no model calls. The original training cache and receipts are intact.

The actual completed result passed its new consumer. A separately implemented
standard-library audit passed **171,615 checks with zero discrepancies** in
1.140 seconds. It independently rederived all 13,320 saved frame records across
the six original and six new validation reports, schedule/augmentation receipts,
checkpoint selection, epoch-zero reuse and telemetry maxima. It verified 38 cache
receipts. It did not load models, tensors, pixels or protected content; heatmap
component extraction was not rerun. Two audit-script checks were strengthened
before its first execution; no scientific run or bound fitting code was changed.

The worker took **1,332.316 seconds (22.2 minutes)**; supervision took
**1,337.032 seconds (22.3 minutes)**. The supervisor recorded 650 samples:
**60 C maximum**, **134.36 W maximum**, **4,750 MiB maximum GPU memory**.
It exited successfully with no stop condition, active throttle flag, forced stop,
cleanup error or remaining owned process. Post-run System event queries found
no matching graphics/WHEA/unexpected-power records and no query error. NVIDIA
Overlay, Lively Wallpaper and MSI True Color were stopped at launch and after
completion; no Python/FFmpeg job remained. This successful workload is not proof
that the earlier PC stability problem is permanently resolved.

## Evidence and next decision

- [Actual completed result](../data/outputs/ball_tracking/wasb_augmentation_v0_1/fit_v0_1/completed.json), SHA-256 `062c0630c9d1e87004b16f49008c8bb84edda7281f8c9a2ef74383ff84757941`.
- [Independent audit](../data/outputs/t/wasb_augmentation_20261026/actual_run_audit.json), SHA-256 `1c0f3a3c4e69e177065c5634f503b86725dc179424996a3d7639689f6ac43223`.
- [Completed-result consumer audit](../data/outputs/t/wasb_augmentation_20261026/completed_consumer_audit.json).
- [Augmentation checks and visual QA](../data/outputs/t/wasb_augmentation_20261026/validation.json); [runner checks](../data/outputs/t/wasb_augmentation_20261026/runner_validation_attempt01.json).
- [Supervisor completion](../data/outputs/ball_tracking/wasb_augmentation_v0_1/monitoring/fit_attempt_001/finished.json); [post-run system check](../data/outputs/t/wasb_augmentation_20261026/post_run_system_state.json).
- Recipe SHA-256 `f89b547f14d9de7e4304d530d6116f024babdc15ce660f03d37157640b8a572a`; all new code bytes remain exactly those bound before execution.

The bounded experiment is complete. A useful next step is a focused diagnosis of
frame 170 and the recurring missing-output cases using existing labels and
saved development evidence, before choosing another general method change.
No additional fit, new label campaign, full-census evaluation of a rejected
checkpoint or protected evaluation is implied or authorized by this result.
No new trajectory or human visual acceptance is claimed.
