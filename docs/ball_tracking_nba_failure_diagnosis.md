# NBA misses and false-detection diagnosis

Completed October 25, 2026, America/Phoenix (October 26 UTC), from
`codex/ball-detector-baseline` at `fe243085bfafc2bdc9cfa33fb49004acb4b432c8`.
Ryan requested diagnosis and a recommended training experiment with unchanged
quality criteria. No training, new labels, method adoption or protected reads
occurred. Human trajectory acceptance remains pending.

## What remains wrong

The [twelve-model comparison](ball_tracking_nba_first_results.md) still has no
passing model. The following breakdown uses augmentation epoch five, selected
for review because it has the highest observed Spurs-Pistons development count.
It is not an adopted model.

| Spurs-Pistons error mechanism | Frames | Evidence |
|---|---:|---|
| No component above the unchanged 0.3 threshold | 24 | Includes all 19 frames at 11075-11093, frame 11504, and 11722-11725 |
| Correct candidate exists, but component-mass ranking selects another | 2 | 11476 and 11514: selected errors 660.176 and 944.657 source pixels |
| Above-threshold support near the reference, but no centroid within ten pixels | 3 | 11101: 10.276px; 11561: 10.304px; 11562: selected 60.448px, nearest component 11.323px |

Thus 212/241 eligible frames match, five are wrong and 24 are missing. The
unchanged count requirements alone need at least 229 matches and at most two
wrong outputs, plus all visibility, continuity, recovery and visual gates.

The main 19-frame gap lasts 317ms. Every previously compared model fails these
frames; augmentation epoch three emits a wrong point at 11088 while the other
models omit that frame. Augmentation-five heatmap peaks inside the ten-source-pixel
reference circle are only 0.00227-0.02577 throughout the gap. This is not a
near-threshold candidate that a small confidence adjustment would rescue.
Frame 11504 is genuinely marginal at 0.292963. These measurements are distinct
from the shifted, quantized training-target disk and do not change the evaluation
radius. Its nominal source radius is 9.375px at width 1920 and 6.25px at width
1280; integer center truncation means these masks need not contain each other.

Houston has 35 eligible misses and three wrong outputs. None of those 38 errors
has an alternate correct candidate. Episode e01 contributes 21 misses, including
a 267ms run; some held/lifted balls remain discernible in the actual 512x288
input. Insufficient input resolution alone cannot explain every miss. Episode
e05 has two roughly 93px wrong outputs at frames 8-9 and one 12.210px error at
173. Its partial-ball contours also encounter foreground/leg overlap.

## False detections and visual findings

Houston has **17 emissions on certain-hidden references**, five in e05 and
twelve in e06. The unchanged contract permits zero. At e06 frames 210-217 the
incorrect point persists for eight frames (133ms), moving at most 1.15px per
step. Simple persistence could reinforce this error rather than reject it.
The 210-212 input triplet is entirely certain-hidden, so that case is not merely
a visible neighboring ball leaking into a hidden frame. At 220 the output is
on another player's head. At 245, proximity to the next visible ball makes
cross-frame spillover plausible, but this is not a demonstrated cause.

Full native images clarify the large DET errors at 11476 and 11514: the selected
points lie on a **standing sideline official's head**. This corrects the earlier
AI note describing the spectator/bench area; the original report and review are
preserved. The other candidate near the accepted ball is already present in
both frames. Ranking can therefore address these two errors, but cannot recover
the 24 absent detections. These are AI inspection findings, not new formal human
object-identity judgments. The twenty DET probable-hidden emissions remain
uncertain review flags, not certain-hidden violations.

The [visual evidence](../data/outputs/ball_tracking/nba_diagnosis_v0_1/index.html)
links native-detail crops, exact 512x288 inputs, neighboring frames and the
original synchronized review. No reference was changed. Inspection covered
26 distinct source frames, including four full native images.

## Training audit: no missing-negative wiring defect

The frozen package contains 3,329 training frames and 3,103 usable triplets.
Actual five-epoch logs match the frozen schedule: 15,515 examples and 7,760
updates per fit, with every usable triplet sampled. Partial positives account
for 70.63% of valid-channel denominator weight; certain-hidden channels account
for 7.38%. These are exposure weights, not gradient measurements. Negatives
are correctly zero-targeted, and uncertain/masked channels are excluded.

The original epoch-five training assessment matches 2,931/2,941 eligible
positions (99.66%), with ten wrong, no missing and three certain-hidden
emissions. This is the original fit, not an exhaustive augmentation-five
training assessment. Its measured loss numerator is 51.17% foreground, 48.65%
visible background and 0.18% certain-hidden. A large background pixel count
therefore does not establish background-dominated loss. The current loss is
already a gamma-two focal-style binary cross entropy.

Independent NBA transition variety is limited: only two directly supervised
certain-hidden-to-visible NBA exits occur within the training blocks, both in
CHI-IND. Repeating these examples would not create new scenes. More partial
sampling, negative weight or training duration has no demonstrated remedy here.
All twelve compared models share the NFHS-adapted initialization. BatchNorm
running statistics remain frozen throughout; changing initialization would
change learned weights/affine parameters, not repair different running buffers.

## Original basketball weights: useful control, not a replacement

A monitored read-only control evaluated the already downloaded official WASB
basketball weights on the same eight contexts and unchanged inference policy.
It uses no optimizer, no locally adapted weights, no reference-conditioned seeding and
no threshold adjustment.

| Weights | HOU correct /882 | HOU wrong | HOU missing | HOU certain-hidden outputs | DET correct /241 | DET wrong | DET missing |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original basketball | 801 | 0 | 81 | 0 | 167 | 5 | 69 |
| Retained NFHS-adapted baseline | 845 | 29 | 8 | 25 | 209 | 8 | 24 |
| Augmentation epoch five | 844 | 3 | 35 | 17 | 212 | 5 | 24 |

The original model contributes **zero unique HOU matches** over augmentation
five and only one DET match (11101). It also fails all nineteen frames in the
shared gap, with local peaks 0.00748-0.01788. Even an oracle choosing a correct
answer from any of the thirteen models would reach only 218/241 DET matches,
below the required 229; that oracle is a diagnostic ceiling for these saved
outputs, not an implementable tracker.

The cleaner original output is mostly greater abstention, not recovered
missing-ball evidence. This does not prove catastrophic forgetting or establish
that original initialization is the best remedy. Nor does its poor zero-shot
coverage prove that a direct NBA adaptation could not improve. SAC's original
175/270 versus augmentation-five 270/270 is training-exposure evidence for the
latter, not independent success.

## Recommended next experiment

Recommend the [bounded five-epoch 768x432 experiment](ball_tracking_nba_resolution_experiment.md),
with the same initial weights, labels, sampling and optimization as the completed
augmentation control. Scale the target radius only to preserve its nominal
source-space footprint. This tests whether additional input detail helps the
dominant shared miss; it does not promise to fix independent hidden/head errors.
Original-initialization-only was considered, then deprioritized after the
frame-level control showed almost no unique recoveries. No new fit was started.
The proposal is a new NBA research scope, not a claim that the older conditional
resolution fallback was satisfied.

## Verification and boundaries

The control performed 3,646 forward calls and produced 3,662 native frame maps
in 66.84s; supervision took 72.25s. Peak GPU telemetry was 56 C, 118.24 W and
2,530 MiB across 36 samples, with exit zero, no stop condition and no remaining
owned process. NVIDIA Overlay, Lively Wallpaper and MSI True Color were absent
from the process check. This workload does not establish that past blackouts
are resolved.

Seventeen focused tests pass: four new control guards and thirteen reused
NBA inference/validation checks. Twenty-one local report/page links and seven
frozen control bindings verify. Independent verification reconstructs the
actual maps/components/geometry and summaries, passing 44,691 checks. The
saved-error census passes 45,623 checks. These check record integrity, not model
quality. A training-audit timestamp assertion was corrected in a second local
analysis attempt; both attempts remain preserved. No scientific attempt was
rewritten as a success.

HOU is fitting-excluded but repeatedly used for selection; DET is already
inspected development data; SAC is training-exposed. No result is an independent
test claim. Protected evaluation remains closed. High-school labels, failures,
reviews, checkpoints and recovery history remain intact.

## Evidence ledger

- [Frozen control manifest](../configs/ball_tracking/proposals/nba_original_weight_control_v0_1.json), SHA256 `47e7aa5cb8296764acea7544119b064f86a76bc11fe662b4a78b717527f558eb`.
- [Completed original-weight control](../data/outputs/ball_tracking/nba_diagnosis_v0_1/original_weight_control_v0_1/completed.json), SHA256 `8e7e54d5422cdcc75f45663bc21cdcbc2e7b88718954f13a05f76b294c750a22`.
- [Saved-error census](../data/outputs/t/nba_error_diagnosis_20261026/saved_error_mechanisms_attempt01.json), SHA256 `634d1db93e4d78aa6a895a63fbcf02c4a4f6cf29128d31a74eb3322a02376427`.
- [Original-weight overlap contrast](../data/outputs/t/nba_error_diagnosis_20261026/original_weight_contrast_attempt01.json), SHA256 `e1199de84066a0f79562d48133f84a0eb85afeea6b326d5cd310dd91962a39e2`.
- [Independent control audit](../data/outputs/t/nba_error_diagnosis_20261026/original_control_audit_20261026T032137887314Z.json), SHA256 `925dfc53fb9e92876bd4dc75eff77fb32346b669b2d7a319b884bbeb9d5020d5`.
- [Training/sampling/loss audit](../data/outputs/t/nba_training_diagnosis_20261026/FINDINGS.md), with its bound logs and correction history. Its initialization recommendation preceded the completed original-weight contrast; use the later recommendation linked below.
- [Visual inspection notes](../data/outputs/t/nba_first_visual_diagnosis_20261026/inspection_notes.json), SHA256 `d616d6a18ae4d7037263aaebfdcf14cc4f7461158a2beace7e9a5f1b09ddcd5b`.
- [GPU completion](../data/outputs/ball_tracking/nba_diagnosis_v0_1/monitoring/original_control_attempt_001/finished.json).
