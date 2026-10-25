# Critical review of the next ball-tracking decision

Recorded October 25, 2026. Repository reviewed at
`fd9f9d3f7f56900acf8164b57d8b7ba7aa9f379f`, branch
`codex/ball-detector-baseline`, initially clean worktree/index.

## Decision

The previously proposed sequence of an epoch-five-to-ten continuation followed
automatically by a twenty-epoch HLSM/hidden-emphasis fit is **not sufficiently
justified as a complete campaign**. Keep the short continuation as a bounded
control; withdraw the automatic second fit. Measure the training/generalization
gap, and consider an automatically WASB-seeded TAPNext++ comparison before
committing to another custom objective or a new labeling campaign.

This is a recommendation, not an executed experiment or an approved executable
recipe. Ryan requested critical review before proceeding. This review made no
model calls, training runs, protected-data reads, dependency installations or
changes to accepted references. The original completed campaign remains
completed/rejected for adoption. Its frozen recipe, failed attempts, checkpoints
and all quality criteria remain intact.

The review used current code, actual saved training/validation records, the
committed experiment history and relevant primary research/code. It does not
claim to have read every message in sixteen original chats, searched every
internet source, reproduced external models, or established a globally optimal
method. Independent reviews covered training mechanics, local experiment
history, and external alternatives; their disagreements informed this decision.

## What the accumulated experiments establish

| Workstream | Observed result | Consequence for the next decision |
|---|---|---|
| RF-DETR crops, temporal association and player context | Crops improved candidate availability; motion/proximity rules sometimes retained persistent distractors and did not reliably reject hidden-ball outputs. [Crop comparison](../ball_detector_tiled_comparison_results.md), [ranking](../ball_crop_candidate_ranking_results.md), [context](../ball_crop_player_context_results.md). | Another geometric selector is poorly supported as the main next investment. |
| Generic YOLO and detector agreement | YOLO supplied qualifying candidates on 87/145 eligible frames versus RF's 140/145; agreement lost correct outputs without resolving hidden alarms. [YOLO](../ball_yolo11x_crop_recovery_results.md), [agreement](../ball_crop_cross_detector_corroboration_results.md). | These failures reject the tested generic recipes, not all basketball-specific detector training. |
| WASB adaptation | At fixed 0.5, original/75-frame/150-frame fits matched 31/98/120 of 145. The expanded fit used the same 200-update budget; most improvement was P001. The reviewed 0.3 method reached 130/145. [Expanded adaptation](../ball_wasb_expanded_adaptation_results.md). | Relevant examples have produced the strongest local improvement. This is not proof that repetition alone will do so. |
| WASB motion and gap rules | A bounded gap trial added three accepted matches; continuous use exposed a head track despite a narrow numeric pass. [Motion](../ball_wasb_motion_selection.md), [continuous gaps](../nba_temporal_gap_continuous_validation_results.md). | Narrow windows and plausible trajectories are insufficient for phase acceptance. |
| NBA adaptation and heatmaps | Training-scene SAC matches improved 218 to 265; excluded DET changed 207 to 206 and NFHS 130 to 129. Saved NBA heatmaps lacked local above-threshold evidence in every contributor for 58/69 misses. [Adaptation](../nba_wasb_adaptation_results.md), [heatmaps](../nba_hard_example_heatmap_inspection_results.md). | Training fit and transfer differ. Many errors need better image evidence, not another choice among existing points. NBA error counts cannot establish the NFHS failure mechanism. |
| DINO appearance verifier | The fitted crop classifier removed 207/581 previously matched permitted development positions in the regression-protection set. [Result](../nba_ball_distractor_training_results.md). | Keep this recipe rejected; do not revive it as a general-purpose visibility solution. The 225 protected positions were excluded. |
| Completion primary fit | Five epochs produced no eligible replacement. Retained outputs score 924/1117 on the full permitted census; all possessions fail. [Completed result](../ball_tracking_completion_primary_results.md). | A selection pass would still be distinct from a phase pass. The full-census failures are baseline results, not measured full-census results for the rejected trained checkpoints. |

The old 130/145 selection-window result is about 90%; the complete permitted
result is about 83%. This is not a contradiction: the windows sample different
coverage. It explains why optimizing only familiar short examples did not close
the phase. No rejected epoch was evaluated on the complete census during this
review.

## What the actual training records add

The completed update history contains 7,760 contiguous retained updates, with
finite losses and 176 gradient-bearing parameters on each. Mean loss in epochs
one through five was approximately `4.680, 3.492, 3.059, 2.834, 2.650 x 10^-5`.
That is a 43.4% decline from epoch one to five and 6.5% from four to five. Source:
the original attempt's updates through 500 and the
[resumed log](../../data/outputs/ball_tracking/completion_campaign_v0_1/primary_fit_v0_1/attempts/b898cdd299724f1b97a492cc77648462/updates.jsonl)
from 501 onward. The original unsaved/replayed 501-522 updates remain historical
consumption, not extra distinct updates in this trajectory.

Stopping was driven by the absence of an **eligible checkpoint**, not demonstrated
optimization convergence. Decreasing minibatch loss also does not establish
better validation performance or balanced positive/background learning.

P003 frames 170 and 304 became missing at every trained epoch, with no P003
gains. Their candidate lists were empty. Frame 170's retained selected component
was one pixel at 0.3031255, just above the fixed 0.3 cutoff. This establishes
lost detectable support; without saved raw validation heatmaps it does not
identify why. See [epoch zero](../../data/outputs/ball_tracking/completion_campaign_v0_1/primary_fit_v0_1/validation/epoch_000.json)
and [epoch five](../../data/outputs/ball_tracking/completion_campaign_v0_1/primary_fit_v0_1/validation/epoch_005.json).

The frozen training package has 2,941 positive, 147 certain-hidden and 241 masked
frames. Certain-hidden frames already receive zero-map supervision; uncertain
channels are excluded from the loss. All usable triplets were sampled by epoch
five. P003 has only 25 distinct positive training frames, already used in 1,914
output-channel exposures; repetition is not new scene diversity. The new large
labeling package expanded NBA training, whereas the immediate phase gate is on
the three NFHS possessions. The new curated census remains evaluation-only.
Sources: [target/loss implementation](../../src/ball_tracking/wasb_training.py),
[sampling policy](../../src/ball_tracking/completion_training_policy.py),
[frozen package](../../data/outputs/ball_tracking/completion_campaign_v0_1/frozen_primary_package_v0_1/package.json).

No wiring defect has been established. Existing tests already cover upstream
binary-target/loss parity, masked gradients, tiny-model updates and preprocessing.
Repeating a generic overfit exercise is not required to resume. A new target or
loss would need its own focused checks.

## Why HLSM is conditional

The [WASB paper, sections 3.2 and 5](https://arxiv.org/html/2311.05237v2)
supports a specific hypothesis: mine difficult training localizations, then
sharpen targets for those examples. Applying the change to all examples did not
statistically improve results. The isolated ablation does not establish a
basketball gain under our criteria. Its scratch-training schedule does not
determine the right adaptation schedule here. HLSM does not add a visibility
classifier; hidden-frame emphasis is a separate hypothesis.

There is a reproduction detail to settle before implementation. The local pinned
upstream [target producer](../../data/outputs/wasb_assets/WASB-SBDT-923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/utils/heatmap.py)
zeros soft values below 0.5, instead of the paper's hard radius boundary. At an
integer center and radius 2.5 this gives 25 supported pixels rather than 21.
Choose and name the intended semantics explicitly. The parameter 0.7 is a target
value, not a detector-confidence threshold. Our component-mass score can exceed
one and is not a calibrated correctness probability.

Changing HLSM, negative weighting, replay balance, learning rate and duration
together would make the next result hard to interpret. Sharpened targets also
deserve care for accepted partial-ball centers with placement uncertainty; do
not revise those labels to suit the method.

## External alternatives that can change the decision

**TAPNext++ with automatic WASB seeds is a credible new comparison.** The
[official project](https://github.com/google-deepmind/tapnet) provides PyTorch
weights, including a 512-input variant, under Apache 2.0. It tracks query points
using image evidence and predicts visibility. My inference is that automatic
WASB seeds could make it useful for visible-ball recovery without new labels.
This is materially different from joining saved detections with geometric rules.
It is not established basketball accuracy: tiny balls, rotation, partial
occlusion, false seeds, image resizing and identity drift remain risks.

The [512 wrapper](https://github.com/google-deepmind/tapnet/blob/main/tapnet/tapnextpp/votsp2026/tracker.py)
stretches input to 512 square but uses 256-space query/output coordinates; its
standard independent-query path adds support points. Later seeds require fresh
state. Its optional uncertainty radius is not our ten-source-pixel criterion.
Any adapter must test these transforms, preserve native timing and distinguish
visible image-conditioned estimates from hidden extrapolation. Hidden positions
must remain absent; manual seed/reference coordinates cannot become inputs to an
automatic evaluation. Release/weight bytes and local feasibility remain to be
verified before execution.

**Basketball-specific RF-DETR adaptation is a genuine alternative.**
[BasketballSkills, appendix B.2.1](https://arxiv.org/html/2608.23435v1#A2.SS2.SSS1)
reports basketball box AP@50:95 improving from 0.1734 to 0.5122 after fine-tuning
on 3,000 frames sampled one per training video. This is box detection evidence,
not a 95% center/visibility/continuity result. The reported four-hour RTX 3090 run
is not a local runtime estimate. No specialized released checkpoint was verified
in this review. Our accepted centers are not automatically verified boxes.

**BasketEvent supplies a real basketball implementation, with different costs.**
Its [official code](https://github.com/zhangyu2003/BasketEvent) uses SAM3 and
Qwen2.5-VL to generate/filter player and ball tracks for event recognition. That
provides a possible detector/data route, but event results do not certify our
ball gates. Model-generated boxes/trajectories require provenance and quality
inspection; their availability does not silently accept them as our references.

The [WASB model zoo](https://github.com/nttcom/WASB-SBDT/blob/main/MODEL_ZOO.md)
also links a basketball MonoTrack model. It is an accessible fallback candidate,
not evidence of superiority to locally adapted WASB. The remaining alternatives
have weaker immediate fit: [BlurBall](https://github.com/cogsys-tuebingen/blurball)
has table-tennis weights and different blur-center targets;
[TOTNet](https://github.com/AugustRushG/TOTNet) studies racket-sport occlusion and
inferred hidden positions; [TrackNetV5 SDK](https://github.com/thaonan/TrackNetV5-SDK)
does not supply the needed training data/weights. Those differences preclude
treating their reported percentages as solutions to our contract.

## Useful tools, with a bounded purpose

- [TensorBoard](https://docs.pytorch.org/tutorials/intermediate/tensorboard_tutorial.html)
  can display training and per-cohort curves. The project already has JSON logs
  and Matplotlib; a small local chart is sufficient unless interactive monitoring
  saves work. TensorBoard is not installed in the project environment.
- FiftyOne could organize error examples, but migrating the review system is not
  necessary. Existing frame records, overlays and source links can support a
  filtered error view. It is not installed; generic evaluation defaults must not
  replace the project's scorer.
- [Torchvision transforms](https://docs.pytorch.org/vision/stable/transforms.html)
  support synchronized video/keypoint transformations. Label-preserving
  augmentation is an available no-new-label hypothesis if source generalization
  is the problem. It cannot create missing occlusion situations or justify
  unsynchronized transforms across the temporal input.
- Keep the existing GPU telemetry and exact owned-process supervision for future
  runs. No stress testing, cloud purchase, large experiment platform or parameter
  search is needed for this decision.

## Recommended execution sequence and decision rules

1. **Prepare one bounded training-only assessment.** Reuse the epoch-five
   checkpoint and accepted training contexts to measure positive matches/misses,
   wrong centers and certain-hidden emissions by source. Inspect separate
   foreground/background/hidden loss contributions. One assessment, one compact
   scorecard; no new labels, protected access or full-census scoring of rejected
   epochs. This distinguishes poor fitting from poor transfer. A low aggregate
   loss alone cannot make that distinction.
2. **Keep epoch five to ten as a cheap controlled experiment, not the main
   promised solution.** Preserve optimizer/RNG/sampling state and all settings
   except the explicit stopping budget. Save a separate immutable continuation;
   stop at epoch ten, retaining the original completed result. Five additional
   epochs imply 7,760 updates and about 18-20 minutes of fitting at measured
   throughput, excluding preparation and assessment. If the training-only
   assessment already shows strong memorization with poor transfer, deprioritize
   this control rather than expecting more repetition to supply missing scenes.
3. **If no candidate closes the development screen, prepare one fixed
   automatically seeded TAPNext++ pilot before committing to HLSM or more labels.**
   First verify release compatibility and memory on permitted training context.
   Predeclare deterministic seed eligibility, reseeding, visibility, conflicts,
   cuts and protected-boundary resets. Use the retained WASB baseline as the seed
   source; references are scoring-only. Score complete predeclared development
   blocks, not hand-selected successful tracks. No manual seed rescue, parameter
   sweep, hidden-coordinate filling or source-label transfer. A promising pilot
   must satisfy the existing per-cohort protections and then the complete
   permitted screen; it is not itself a phase pass.
   Evaluate its complete declared output policy: merely adding points to WASB's
   gaps inherits WASB's existing wrong and hidden emissions and cannot establish
   completion. Image-conditioned predicted-visible tracking may be tested as
   automatic observation; predicted-hidden coordinates stay separate and absent.
4. **Choose at most one subsequent learning intervention from the evidence.**
   Training localization failures can support HLSM alone; training hidden false
   outputs can support a separately specified suppression intervention, checked
   against loss of true balls. Good training fit but weak held-out development
   suggests source coverage/transfer: consider synchronized augmentation or a
   finite batch of independent target-domain episodes. Do not begin another
   labeling campaign based only on frame counts. Basketball-specific RF-DETR is
   the different detector route if needed; verify weights/box data before
   committing to that cost. These are alternative decisions, not an authorized
   queue of extra experiments.
5. **Keep the finish line unchanged.** Freeze a selected method before separately
   authorized protected evaluation. Keep 95% correct within ten source pixels,
   at most 1% wrong, zero certain-hidden emissions, the exact gap/wrong-object/
   recovery rules and complete human review. An inconclusive required judgment
   is not a pass. The original resolution-fallback trigger remains unsatisfied;
   a new review does not silently release it.

The automatic second fit is withdrawn, so the earlier 6-10-hour estimate is not
a guaranteed duration for this revised route or phase completion. The measured
continuation time is useful; new adapter and data work need an estimate once
their concrete scope is known. Each next experiment must state its hypothesis,
one principal change, data roles, fixed comparison, resource estimate and stop
condition before execution. Reuse existing records and focused checks; do not
turn that discipline into another reporting framework.

The near-term aim is two decisive comparisons at most: a training-duration
control and, if needed, one different source of image-based tracking evidence.
No evidence currently guarantees that either reaches 95%. If both fail, record
the remaining mechanism and choose one explicit change of approach rather than
continuing a sequence of small selector or threshold adjustments.
