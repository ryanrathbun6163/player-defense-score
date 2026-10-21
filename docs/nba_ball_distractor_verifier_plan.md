# Bounded ball-versus-distractor test

**Design complete; execution not approved or run.** Ryan requested this design
after the [fixed appearance screen failed](nba_appearance_feature_screen_results.md).
The [proposal](../configs/ball_tracking/proposals/nba_ball_distractor_verifier_v0_1.json)
binds the exact example inventory, recipe and existing evidence. This is one
bounded supervised test with an end-to-end tracking decision, not another
nearest-neighbor screen or an open-ended tuning exercise.

The question is: **can one small trained classifier remove actual distractor
outputs while preserving every verified useful ball position?** A positive
answer must survive the complete five-clip comparison and human motion review.
Wrong-to-missing is useful abstention, not ball recovery or phase completion.

## What the design investigation established

The previous screen rejected two of six check balls and retained all three
points on the known SAC head. Its four correctly classified check hands were
**never selected by the tracker**. Correcting those four classifications alone
would remove no tracking errors. All resolved fitting examples were SAC-only;
the five P002 examples were unresolved.

Read-only reconstruction of the retained detector's existing caches found
490 exact-coordinate groups at 142 fixed targets. All 142 reconstructed means
exactly reproduce the saved original observations. This took 11.765 seconds,
426 triplet reads (678,226,005 bytes), at most three arrays resident, and no new
source-pixel access, labels, model calls, fit or trajectory changes. Original
smaller planning inventories remain preserved, not misrepresented as trial runs.

Nearby contributor predictions often describe the same physical object. In
particular, 88 NFHS fit coordinate groups occupy just 20 frames; only four
frames have coordinate spread above 32 pixels. Neither 490 coordinates nor
184 proposed judgments means that many independent examples. This is why the
design includes distinct source-selected training distractors and explicit
object/block coverage gates before any fit.

## Finite examples and source roles

The bound candidate registry fixes **160 new candidate judgments** at 105
targets, with 525 distinct native context frames (target minus two through
target plus two). Their context frames do not intersect the 149 context keys
in the prior appearance and gap-reference packages. There are no new source
pixels or semantic labels from this design investigation.

| Source and role | Candidate judgments | Complete permitted blocks, inclusive |
| --- | ---: | --- |
| SAC, fit | 48 | 660-719; 940-1059; 1240-1359 |
| P001, fit | 36 | 100-124; 250-274; 375-399 |
| P002, fit | 12 | 318-367, kept as one complete block |
| DET, excluded check | 40 | 10788-10847; 11000-11119; 11420-11579 |
| P003, excluded check | 24 | 150-174; 300-324; 416-440 |

P001 is an **explicit expansion of this verifier's fit sources** onto historical
detector-training blocks. DET and P003 remain entirely excluded from this
classifier's fitting. These are exposed development sources; P003 trained the
retained detector. Neither is an unseen benchmark. SAC/P001/P002 tracking
results are fit-source diagnostics and regression protection, reported apart
from DET/P003. TOR and protected holdouts/buffers remain outside all preparation,
feature extraction, fitting, scoring and playback.

The prelabel rule uses block start plus two, stride five, and requires the full
five-frame context to remain in the block and outside old context keys. It
reconstructs original mean and contributor components at strict heatmap >0.3,
without a new detector run. Within frozen block quotas, it first retains
emitted geometric-error/hidden-alarm diagnostic points, covers candidate-rich
and ordinary targets, and then chooses spatially separated contributor points.
The bound registry records the precise rule, centers and original provenance.
Geometric error is a sampling cue, **never an other-object label**.

The 96 fit records contain 58 mean and 38 contributor coordinates; the 64
check records contain 42 mean and 22 contributor coordinates. Of these,
57 fit and 42 check candidates were actually emitted. The excluded checks
include six emitted geometric-error diagnostics: DET11027/11102 hidden alarms,
DET11542/11557/11562 wrong positions, and DET11552 hidden alarm. Their object
identity still needs source review. They may be unresolved rather than heads,
hands or clothing. No semantic outcome is promised by these counts.

Add **24 fit-only source-selected contrast slots** at already fixed fit targets:
eight heads, eight hands and eight clothing regions, each split four NBA/four
NFHS and spread over at least two blocks in each domain. The separate slot
manifest fixes each frame, requested subtype and selection anchor now. Choose
the nearest clearly identifiable requested object to that anchor in native
pixels; ties use x then y. Use the center of the visible head or hand, or the
center of a contiguous visible jersey/shorts region. Save the source evidence,
extent and actual center. Do not choose by descriptor, model output or excluded
check result. An unavailable, ambiguous or duplicate slot stays documented and
unused; no replacement frame/object is sought.

These are explicitly new **appearance-only centers**, not ball-center truth,
detector candidates or evidence of emitted errors. Every detector candidate
retains its original center. All crops use identical clean pixels and processing;
no object-specific zoom, annotation marks, background cleanup or rejection just
because a real ball also appears nearby. Their sampling mismatch with detector
errors is why real candidate negatives remain mandatory and their loss weight
is capped.

Thus **184 is the new attempted-judgment ceiling**, not a usable-label promise.
Reuse the 26 accepted appearance references in their existing roles: ten resolved
SAC fit, ten resolved DET/P003 checks, six unknowns. Do not repeat their completed
review. The older 34 selected gap/anchor points remain an exposed qualitative
regression set; they never enter training, new-label quotas or accepted semantic
accuracy totals.

## Label meaning, grouping and adequacy

Before features or fitting, propose `ball`, `other_object` (head, hand, clothing
or other subtype), or `unresolved` for the object at each fixed center using
native target/context evidence. Occlusion, an apparent geometric match or a
hidden-ball annotation does not resolve the object automatically. Preserve
reader disagreements and uncertainty. Assign same-frame physical-object IDs:
multiple mean/contributor centers on the same object are aliases. Different
objects in one frame can be separate groups; different frames of the same
object are correlated and share an episode ID. Complete historical blocks are
the conservative split/weight units. No random frame-level train/check split.

The grouping supplement must also assign the 26 reused appearance records to
exact containing historical blocks and source/frame/object groups, without
changing accepted classes or repeating their completed label review. Their
unresolved records remain unresolved. If a proposed group would contain
conflicting accepted classes, or its membership is ambiguous, resolve the
grouping issue before fitting; never silently merge, relabel or count aliases
independently to satisfy coverage.

Count each resolved frame/object group once toward these **pre-fit** minima:

| Requirement | Minimum |
| --- | --- |
| Fit, accepted old plus new, after grouping | 64 groups: at least 32 ball and 32 other |
| NFHS fit | Eight ball and eight other; each class spans at least two blocks |
| New real detector-candidate fit negatives | Eight groups across at least two blocks, including at least two NFHS groups |
| Fit head and clothing coverage | Each subtype spans at least two complete blocks |
| Excluded checks, accepted old plus new | 32 groups: at least 16 ball and 16 other |
| Excluded domain coverage | Both ball and other represented in NBA and NFHS; at least one head and one clothing group overall |
| Contributor coverage, each fit/check role | Four resolved groups across at least two blocks, with both classes represented |
| New actually emitted excluded distractors | At least two distinct episodes in different complete blocks, including head and a non-head subtype |

These are diversity requirements for a bounded development decision, not a
power calculation or independent sample-size claim. The known DET near-head
ball sequence remains a separate exposed protection check. Record near-head,
blurred/partly occluded, mean/contributor and emitted/unselected subsets without
turning an uncertain appearance into a resolved class to fill a quota.

Present one compact source-based label package containing all new records,
unknowns, groups, slots and each context/final frame. The assistant performs the
first pass; Ryan accepts or corrects the new package. Seal accepted labels,
object/episode assignments and the adequacy report before extracting new
features. If the fixed batch lacks required coverage, complete a precise
**insufficient-data result and stop before fitting**. No replenishment loop,
quota reduction or promotion of old qualitative judgments is part of this test.

## One trained model and one fixed boundary

Reuse the locally verified DINOv2 ViT-S/14 backbone and the previous screen's
exact 64-native-pixel crop, bicubic resize to 256, center 224, RGB normalization,
CPU float32 inference, batch one, four threads, eager attention and final
normalized CLS token. Convert its 384 dimensions to float64 and L2-normalize.
Reuse saved vectors only with exact source, center, crop, model and transform
bindings. Native +/-2 context supports annotation only; it is not model input.

Train **one regularized logistic classifier: 384 weights and one bias**. This
learns which image-feature directions distinguish ball from other, instead of
asking which single old crop looks most similar. Frozen CLS logistic regression
is a documented DINOv2 use, not evidence it will solve our basketball errors.
[Meta model card](https://github.com/facebookresearch/dinov2/blob/main/MODEL_CARD.md)

Let `z_i = w.T @ x_i + b`, with ball `y=1` and other `y=0`. Minimize
`sum(q_i * (logaddexp(0,z_i) - y_i*z_i)) + 0.005 * sum(w*w)`.
Initialize all 385 parameters to zero; do not penalize the bias. Total positive
weight is 0.5. Let `G_A` and `G_D` count resolved authored and detector-negative
frame/object groups. Authored-negative weight is
`M_A = 0.5 * min(0.5, G_A / (G_A + G_D))`; detector-negative weight is
`0.5 - M_A`. Thus source-selected negatives receive at most 0.25 total weight,
and fewer resolved authored groups cannot receive a disproportionate share.
Within each of these three pools, divide weight equally across occupied complete
blocks, then resolved frame/object groups, then their distinct crop records.
Save these label-only weights once and verify they sum to one. A supplement on an already sampled
same-frame object is an unused duplicate, not an additional training observation.
Use all eligible resolved groups; never choose an easy balanced subset.

Use installed SciPy 1.17.1 `minimize(method='L-BFGS-B')`, float64 full-batch
analytic gradient, `maxiter=500`, `maxfun=2000`, `maxcor=10`, `maxls=40`,
`ftol=1e-12`, `gtol=1e-8`. Use the final converged solution once; nonfinite input
or nonconvergence yields a preserved invalid-fit result. No restart, alternate
optimizer, feature/crop sweep, augmentation, backbone tuning or calibration.
[Optimizer contract](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html)

Freeze **zero** as the boundary before labels: positive is ball-supported,
negative is other-supported, exact zero abstains. Scores are uncalibrated logits,
not probabilities. Excluded labels do not affect training, weights, convergence,
checkpoint choice or boundary. The small number of independent blocks does not
justify a claimed calibrated risk threshold.

## Separate tracking arm and measurable success

Apply the frozen classifier to every one of the **3,373 existing emissions**
across the same five clips: 3,975 permitted positions in eight segments, with
225 protected timeline positions excluded. The proposal lists exact ranges.
Original saved selections, model outputs and accepted baselines stay immutable.
This new experimental arm explicitly permits suppressing an original emission,
which the earlier gap rule did not permit:

1. An original point with negative logit becomes missing; positive or exactly
   zero retains its exact coordinate and provenance.
2. A filled gap survives only if **both original anchors and every proposed
   fill have strictly positive logits**. Otherwise revoke the entire gap's
   fills. Classify/veto the original anchors individually under step 1.
3. Never form new gaps for filling, use fills as new anchors, rerank candidates,
   substitute coordinates, interpolate or rerun the selector. Original missing
   positions remain missing.

All of these gates are required for a clean result supporting adoption review:

- **Ball protection:** every resolved excluded ball, including the old six,
  has positive logit. The ten old resolved checks all classify correctly;
  ties fail. Report unselected-ball classification separately from retention.
- **Actual benefit:** every newly resolved, actually emitted excluded distractor
  has negative logit and is suppressed, with the pre-fit two-episode/head plus
  non-head coverage satisfied. Unselected distractor accuracy is diagnostic
  and cannot count as a removed tracking error. Report direct vetoes separately
  from fills removed only because another member of their gap failed.
- **Exact geometric protection:** preserve every formerly matched frame/point
  in the 790-reference continuous report: SAC218, DET209, P00142, P00250 and
  P00340. Preserve all 22 additional eligible matches and the three older
  accepted gains (DET11437/11438, P001208). Build a deduplicated key union and
  report each named cohort separately; their counts must not be added blindly.
  Keep the inclusive ten-pixel metric and both 60/60 NBA pilot controls.
- **Known exposed failures:** suppress SAC1419, 1420 and 1421 (one qualitative
  head episode), while retaining DET11722-11725 exactly. Neither sequence is
  new independent class truth. These are hard regression conditions, with
  their different evidence status visible in the report.
- **Integrity and uncertainty:** no new coordinate, wrong output or hidden
  alarm; all retained coordinates/provenance exact. Report every removed
  unscored/unknown emission, every revoked gap, missing interval and duration.
  The six accepted appearance unknowns, five new geometry unknowns and eight
  older semantic unknowns stay unscored. Suppressing them never counts as a
  correct rejection. A veto-only rule's main risk is losing valid but unscored
  balls; construction invariants alone do not establish safety.
- **Human motion acceptance:** inspect synchronized old/new player-ball
  playback for all five clips, every changed episode with surrounding motion,
  uncertainty and actual finals. Ryan judges actual new trajectories before
  adoption. Earlier completed reviews remain complete.

Keeping everything fails actual benefit; deleting everything fails ball
protection. A small aggregate error reduction cannot hide a lost verified ball.

## Bounded execution, deliverables and decision

Approval of this proposal would cover preparation/implementation, the single
184-slot label package, publication after human acceptance, one eligible fit,
and the entire five-clip evaluation. It should not require another fitting
proposal after label acceptance when the frozen adequacy gate passes. The
label-acceptance and final-trajectory decisions remain distinct human gates.

At most 3,617 crop records need features before deduplication: 3,373 saved
emissions, 184 new slots and 60 old feature-screen records. Reuse exact existing
vectors and cached PNGs. Native decode is bounded to the 525 label-context
positions and the already permitted five-clip segments; no new WASB inference,
weights download or package install. Resource use is dominated by CPU crop
encoding and video rendering; record actual time, reads, memory and failures.
Do not run another representation just because this one fails.

Implement a separate configuration-driven verifier and output arm. Focused
checks must cover actual candidate-producer transport, source/PTS joins,
same-object grouping and weights, numerical objective/gradient, exact crop
reuse, fixed-zero behavior, whole-gap revocation, original immutability and
excluded/buffer access. Independently reproduce saved logits, weight totals,
every removal reason and the exact protected-match union. Audit the actual
rendered playback through its finals. No full-suite repetition merely for this
design or isolated implementation is implied.

The final report contains a fit/check coverage table; every excluded judgment
and logit; original-versus-fill deletions; preserved/lost matches by source;
all unknown removals; before/after missing intervals; synchronized review media;
and one decision. Complete that report even on a scientific failure. A data
shortfall stops before fitting; a valid-fit gate failure closes this exact
recipe without tuning; a full pass supports human review of the bounded policy,
not full-game readiness or a completed ball phase. This arm cannot recover the
602 positions already missing from the continuous baseline.

Execution is a new scientific choice: new appearance labels, P001 fit expansion,
a learned decision boundary and permission to suppress original points in a
separate arm. The [working agreement](context/working_agreement.md#current-standing-policy-ryans-2026-10-08-instruction)
says, "Bring substantial scientific, architectural, evidence-integrity, safety,
or cost tradeoffs to Ryan for approval rather than escalating routine fixes."
The current request authorizes this concrete design; no new fit or output-policy
execution has been inferred from it.
