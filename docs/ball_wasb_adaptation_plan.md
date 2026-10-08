# Proposed WASB adaptation trial

Prepared 2026-10-08. **Training has not run.** This is a concrete next-step design,
not a selected model, changed quality gate or claim of improvement. Read the
[completed transfer comparison](ball_wasb_transfer_results.md) and
[cached calibration result](ball_wasb_calibration_results.md) before deciding to
execute it. Calibration reached 62 correct observations without observed errors,
but still missed 83 eligible frames; it did not remove the need to improve visual
discrimination.

## Question and scope

Can a small amount of training on our already reviewed pilot footage improve
WASB's ball localization on different, already reviewed development windows?
Start from the official basketball checkpoint; retain RF and the unmodified WASB
checkpoint as controls. The trial changes learned image features, which output
threshold changes cannot do. It does not change the player pipeline, introduce
interpolation, or consume sealed holdouts.

This is an economical adaptation diagnostic. Its purpose is to decide whether
training deserves further investment, not to certify reliable ball tracking.

## Data split

Keep the original annotation files and their review/purpose fields unchanged.
A derived training manifest should reference those frozen files explicitly.
Do not randomly split neighboring frames between training and evaluation.

| Training pilot | Inclusive frames | Eligible coordinates | Certain hidden frames | Ambiguous frames |
| --- | --- | ---: | ---: | ---: |
| Possession 001 | 375–399 | 25 | 0 | 0 |
| Possession 002 | 318–342 | 16 | 8 | 1 |
| Possession 003 | 416–440 | 25 | 0 | 0 |
| Total | 75 reviewed frames | 66 | 8 | 1 |

The three existing sources are:

- `configs/ball_tracking/annotations/possession_001_frames_0375_0399_protocol_adjudication_v0_1.json`
- `configs/ball_tracking/annotations/possession_002_frames_0318_0342_protocol_adjudication_v0_1.json`
- `configs/ball_tracking/annotations/possession_003_frames_0416_0440_protocol_adjudication_v0_1.json`

Use all 23 complete chronological triplets inside each pilot: 69 distinct
triplets in total. Overlap supplies different temporal context, not 69 independent
scenes. P002 frame 335 is ambiguous despite retaining point geometry: ignore its
output channel in the loss. Keep its image as temporal context. The eight
reviewed hidden frames are P002 frame 330 and frames 336–342, two occlusion
episodes. They receive empty target maps. None represents an out-of-frame ball.

Evaluation remains the six existing windows bound by
`configs/ball_tracking/wasb_experiments/wasb_basketball_transfer_v0_1.json`:

| Possession | Representative frames | Challenge frames |
| --- | --- | --- |
| 001 | 50–74 | 200–224 |
| 002 | 250–274 | 25–49 |
| 003 | 300–324 | 150–174 |

These contain 145 eligible coordinates and five hidden frames, the latter all in
one P003 episode. Training and evaluation input frames do not overlap. The
nearest pilot-to-evaluation gaps contain 150, 43 and 91 intervening frames for
P001, P002 and P003 respectively, using within-window inputs only. All three
sealed holdout windows remain outside training, context, checkpoint choice and
this development evaluation.

The pilot labels have already informed protocol development and descriptive RF
baseline evaluation with completed visual review. The evaluation
windows have informed multiple model decisions. Both come from the same game
and gym; this split supplies a useful same-game transfer check, not an untouched
or independent-game test. Training has 12 fully visible and 54 partially visible
eligible balls; evaluation has 14 fully visible and 131 partially visible balls.
This heavy reliance on reviewed partial/amodal centers must accompany the result.

## One preset, one final checkpoint

The following is a local diagnostic preset, not a reproduction of the authors'
training recipe:

| Setting | Proposed value |
| --- | --- |
| Initialization | Official basketball checkpoint, SHA-256 `8d1ba9870d0a6ab37b06ab82bed593c6c09133e713810bac475d0c000bb7e948` |
| Model / inputs | Existing verified HRNet adapter; chronological RGB triplets, 512×288, float32 |
| Trainable parameters | Full network; BatchNorm running means/variances frozen, affine parameters trainable |
| Optimizer | Adam, learning rate `0.0001`, default betas `(0.9, 0.999)`, epsilon `1e-8`, weight decay zero |
| Schedule | 200 optimizer updates, batch size two, seed 1234; no learning-rate search |
| Sampling | Concatenate seeded shuffled cycles of the 69 triplets, take exactly 400 IDs, then batch consecutive pairs; record all IDs, including the final partial cycle |
| Targets | Official binary disk, radius 2.5 output pixels, at the transformed integer ball center |
| Loss | Official gamma-two weighted binary cross-entropy form, sigmoid clamped to `[1e-4, 1-1e-4]`; exclude ambiguous output channels from numerator and denominator |
| Augmentation / mining | None for this first diagnostic; no false-positive mining or synthetic labels |
| Checkpoint choice | Final update 200 only; no evaluation-driven early stopping or best-checkpoint selection |

The full model has 1,481,427 parameters. Its final pointwise output convolution
has only 51; training only that layer cannot learn new spatial features. A
full-network small-learning-rate trial therefore asks the more relevant first
question, while freezing BatchNorm statistics avoids estimating them from tiny
batches. This choice can still overfit; the separate development comparison must
detect that rather than treating lower training loss as success.

Use the same complete-ball-center meaning as our reviewed annotations. Preserve
the official affine transform and integer-center target convention (`astype(np.int32)`,
truncation toward zero rather than nearest-integer rounding). Hidden is a
reviewed negative; ambiguous, excluded, unlabeled or indeterminate must never
be silently converted into negative training examples. No target is inferred
from RF, WASB, player proximity or future annotation outside the window.

## Evaluation and decision

Cache the final checkpoint's complete development heatmaps once. Use the same
within-window overlapping-triplet mean policy and source-coordinate point
evaluator. Compare the original threshold 0.5 first. Also report the already
declared eight-threshold calibration grid for both original and adapted outputs;
do not add thresholds after seeing the adaptation result or pick a checkpoint
using these outcomes. Matching stays at ten source pixels, with representative
and challenge pools reported separately.

Report matched, wrong-present, eligible missing, hidden alarms, raw candidate
availability and paired recovered/lost RF matches by window. Include the
same-output-count RF diagnostic, explicitly retaining its post-hoc ranking
interpretation. Distinguish better emission calibration from better localization.
Preserve all frames, including endpoints and ambiguous/hidden accounting.

A useful signal is more correctly localized output at a comparable error burden,
with the per-window table showing where gains and regressions occur. This is a
development decision criterion, not a replacement numerical acceptance gate.
If the trial supplies no useful tradeoff, retain the negative result and decide
between better training examples and a learned RF-candidate verifier. Do not
launch an open-ended optimizer/checkpoint search on these same 150 frames.

If the trial does help, render the changed trajectories and specific remaining
failure episodes for Ryan's synchronized visual review. Do not make him re-review
the rejected settings or count previous visual acceptance as acceptance of a new
model. Independent occlusion/reacquisition examples and broader footage remain
necessary before claiming robust generalization.

## Implementation and practical checks

Implement a small trainer around the verified adapter. The pinned upstream
training runner imports a missing module, lacks a released training-runner YAML,
and uses a NumPy constant removed in our installed version. Importing the whole
legacy runner would add unrelated repair work. No dependency installation is
needed for the proposed local PyTorch path.

Before substantive training, check actual target generation against the pinned
producer, ambiguity masking and hidden targets, affine alignment, finite loss and
gradients, frozen BatchNorm buffers, and a safe checkpoint round trip. Exercise the
real adapted output through the existing evaluator. These are focused checks;
this isolated addition does not itself justify rerunning the full suite.

Use safe tensor-only checkpoint loading, preserve the pretrained file and prior
outputs, and save the adapted weights, optimizer/RNG state, sampling trace and
training losses in a new ignored output directory. Record successful updates,
failures and actual elapsed time; never restart a failed fit and label it the same
uninterrupted run. Routine path/report issues can be fixed without retraining.
The existing adapter pins the original checkpoint: derived-weight loading needs
an explicit path/digest binding and strict state-dictionary validation, not a
bypass of the original provenance check.

Batch two is expected to be practical on the existing RTX 5070, but training
memory and runtime have not been measured. Begin with the real configured batch
and inspect actual allocation. Change batch size only if needed for practical
safety, recording the change and its effect on the training schedule. The 200
updates define this experiment's learning exposure; they are not an obsolete
computer-resource cap.

The proposed result would inform the next implementation choice. The agreed
finish line still requires reliable, reviewed ball trajectories across all three
curated possessions, explicit gaps, synchronized player/ball playback, quantitative
error reporting and a repeatable configuration-driven run.

## Inspected implementation sources

All references are pinned to WASB revision
`923462cacdeb3353b84ddebdedb3f4b7a8553b0f`:

- [Target construction and affine integer conversion](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/dataloaders/dataset_loader.py#L137), [binary disk generation](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/utils/heatmap.py#L6), and [target defaults](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/configs/dataloader/default.yaml#L20).
- [Weighted loss](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/losses/wbce.py#L36) and [sigmoid clamp](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/utils/utils.py#L83).
- [Sliding temporal sequence construction](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/datasets/basketball.py#L277) and [upstream training/checkpoint code](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/runners/train_and_test.py#L148).
