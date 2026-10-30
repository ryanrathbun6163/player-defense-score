# Controlled local-plus-context pilot v0.1

October 30, 2026. **Design and CPU metadata preparation only. No neural capture,
training, new score, selector or model adoption has run.** Ryan requested a
critically reviewed design in which either improvement or failure yields useful
evidence. The [proposal](../configs/ball_tracking/proposals/dual_view_context_v0_1.json)
and bound design evidence specify the comparison below.

## Question and evidence

Does adding one fixed wider current-frame input improve candidate-point quality
beyond an equally sized model receiving the original close-up twice? Keep the
old quality model Q and acceptance gate J as saved references. This comparison
tests the **wider-input package**, which changes both field of view and auxiliary
object scale/resampling. It cannot attribute an effect solely to pixels outside
the close-up.

The completed [input screen](ball_tracking_input_context_screen_results.md) found
four useful candidate examples on three frames in two predeclared intervals,
all within one two-second BKN clip. It supports a bounded test, not an expected
accuracy gain. The old box-distance context term, same-crop point/CLS comparison,
Q/J successes, failed origin ablation and failed Q+ population addition remain
material. Changing the input is distinct from those completed interventions.

Two new CPU findings sharpen this design:

- Original all-NBA Q's saved fitting logits have weighted BCE 0.000158833 and
  weighted mean absolute analytic logit derivative 0.0000545006. Of 17,524 fitting
  points, 17,496 have absolute derivative below .001. These are calculations from
  saved scores, not measured parameter gradients. A zero residual around those
  already confident logits could learn almost nothing. Therefore use a fresh
  fusion head, not a correction initialized around the old output score.
- Of 13,776 known distant-negative NBA fitting points, **7,426 contain the accepted
  ball center elsewhere inside the 192px view**. All three outer fits retain
  thousands. This supplies existing supervision for candidate usefulness rather
  than mere ball presence. Geometry does not certify visual identity. All 65
  boundary-unknown candidates stay unknown; no new negative label is created.

The current training-support gap remains: the three wrong chosen-native training
points are boundary-unknown, native-hidden examples are one adjacent CHI pair,
and nearly every weak positive accompanies native success. Wider pixels do not
create diverse current-detector failure situations.

## Matched arms and model

| Reference/arm | Fixed local input | Auxiliary input | New learning |
|---|---|---|---|
| Saved Q | Original local pipeline | None | None; reuse original scores/checkpoints |
| LL, capacity/adaptation control | Frozen corresponding-fold Q point feature | Exact same original local pixels | Generic auxiliary final blocks plus fresh fusion head |
| LC, prespecified treatment | Identical frozen local feature | Fixed candidate-centered 192px view | Identical parameters, initialization, training and budget to LL |

Use the existing pinned DINOv2 ViT-S/14 without registers, revision
`150c8e7bb7cef2d30ec31b13a517af14840ee3f7`; no new model download. For each fit,
the frozen local encoder is that fit's **original six-epoch Q checkpoint**, not
Q+, another fold's Q or the all-NBA checkpoint in an outer fold. Its normalized
384-dimensional point feature is cached in float64 and cast to float32 for fusion.
The original score files contain logits, not these embeddings; capture is real
future neural work and is included in the budget.

The auxiliary encoder starts from the **generic pinned DINO weights** in both
arms. Freeze embeddings and blocks 0–9; adapt blocks 10–11 and final LayerNorm.
Keep the frozen prefix in evaluation mode without gradients. Read the final
normalized sequence in two ways: bilinearly interpolate the four candidate-point
tokens, then L2-normalize once in float64; separately L2-normalize CLS token zero
in float64. Cast each vector to float32. Concatenate, in order:

`[frozen_Q_local_point_384, auxiliary_point_384, auxiliary_CLS_384]`

There is no joint normalization. The fresh head is
`Linear(1152,128) -> GELU -> Linear(128,1)`, with ordinary pinned PyTorch Linear
initialization. It outputs a logit with no old-Q logit offset. The trainable
auxiliary portion has 3,551,232 parameters; the head has 147,713; total
**3,698,945 per arm**. CLS requires no extra backbone forward. Both arms have
the same readouts, shape, trainability and initial tensors.

Point information is retained alongside the global vector. Earlier CLS failure
concerned replacing point information on the same local crop; it does not settle
this complementary use. Conversely, CLS may encourage scene/background shortcuts
or accept a wrong point because a real ball is elsewhere in the crop. The analysis
below explicitly tests those failure patterns. Pooling is an engineering choice,
not an established optimum; no alternate pooling arm is added.

Frozen local features preserve that representation and its saved baseline.
**They do not guarantee preserved decisions:** the new head can misuse them.
Correct-point retention must be measured. Training local features are in-sample
Q features; held-source distributions may differ. Entire outer-fold predictions
remain source-held for Q and fusion, but cosine nine already saw those games.
These are not end-to-end unseen-game tests.

## Exact image geometry

The local path remains original RGB, floor-centered 64px black-padded crop,
bicubic resize to 256, center crop to 224, and original RGB normalization.
LL's auxiliary input is exactly those same pixels and fractional point weights.
It is not a second approximation of the crop.

For LC, crop `[floor(x)-96, floor(y)-96, floor(x)+96, floor(y)+96]` from the same
original current frame with PIL's black padding. Resize directly from 192 to 224
using bicubic; no subsequent center crop. Use the same normalization as Q.
The candidate maps to `u=(x-left+0.5)*224/192-0.5` and the analogous `v`.
Patch-grid coordinates are `(u-6.5)/14,(v-6.5)/14`. Derive interpolation weights
from these coordinates; do not reuse local weights or round the candidate.
Under this fixed geometry the four tokens remain 120/121/136/137.

No accepted-reference-centered crop, reference marker, source/game ID, detector
response, native/weak indicator, old Q/J score, temporal input or trajectory is
fed to the new head. Crops preserve in-bounds status and padding; padding is not
absence truth. The wider view adds padding for 811/17,524 all-NBA fitting points
versus 188 locally, so padding-stratified reporting is required.

## Population, training and endpoints

Reuse original Q's complete 19,632-candidate/3,329-frame package and exact fit
manifests/targets/weights. Its NBA portion has 18,813 candidates on 3,179 frames;
17,524 have fitting targets. Preserve all unknowns, 21 package-empty frames and
native/weak candidates. Exclude the failed Q+ intervention's 461 additions to
avoid mixing an input change with a population change. Do not mine the diagnostic
screen, BKN or HOU into training or change existing labels/weights.

| Fit, repeated once for LL and LC | Known fitting points | Six-epoch updates per arm | Held package score points |
|---|---:|---:|---:|
| Leave CHI out | 11,954 | 2,244 | 5,935 |
| Leave DEN out | 11,912 | 2,238 | 5,790 |
| Leave SAC out | 11,182 | 2,100 | 7,088 |
| All three NBA games | 17,524 | 3,288 | All 19,632 package points; in-sample NBA and secondary NFHS separate |

Eight fits are two matched recipes under four source memberships, not a sweep.
Use initialization seed **20261030** for a single identical initial auxiliary/head
state reused across all eight fits. Initialize the head after setting that seed
explicitly; incidental model-construction RNG consumption must not change it.
Retain original per-epoch candidate permutations using **20261028 + epoch**.
The candidate order is exactly the bound original weights-file membership before
shuffling, with identical batches between LL and LC for each fit.

Use the original weighted BCE objective, AdamW auxiliary rate 1e-5, head rate
1e-3, decay .01, betas(.9,.999), epsilon1e-8, norm clipping1, candidate batch32
and six epochs. The minibatch loss is mean(BCE * original training_multiplier).
Use float32 model/optimizer arithmetic, prescribed float64 normalized readouts,
deterministic eager attention and no AMP/TF32, augmentation, dropout, scheduler,
early stopping, distillation penalty, crop sweep or automatic extension. The
only comparison endpoint is epoch six. Recovery checkpoints are not candidates
for selection. Fit order is CHI-LL/LC, DEN-LL/LC, SAC-LL/LC, all-NBA-LL/LC;
no earlier result changes a later recipe.

At the final checkpoint, also score every known fitting row for each outer fit
(35,048 extra rows per arm); all-NBA training-health rows are already in its
package scores. Compute final weighted losses/margins by target/origin/source,
using these fixed-model scores rather than confusing online loss with final fit
quality. Capture old Q logits alongside local features for fitting-health
comparison without extra backbone calls. Preserve old scalar controls unchanged.

All-NBA external scoring covers 10,778 HOU main candidates, 949 emitted historical
stress queries, 42 permitted non-DET historical queries and all 3,480 BKN points
on 360 frames. Retain the full HOU frame inventory: 960 total, 882 eligible,
34 certainly hidden and 44 other unknown/nonlocalizable frames. Keep 11 missing
stress slots with no image score. The old 18 DET
historical rows are **metadata-only, treatment not scored**, not zero or missing
predictions. No new DET pixels/model query or protected evaluation is included.
Historical semantic roles remain separate; NFHS is secondary regression evidence.

BKN is exposed diagnostic development, permitted to motivate this hypothesis but
excluded from fitting, checkpoint/threshold optimization and primary evidence.
Its whole 360-frame population is reported, not only the 82 BKN candidates in the
100-point screen. Retain its 310 eligible, 32 certainly hidden and 18 unknown frames.
HOU is descriptive/regression-veto only: benefits do not select features or rescue
a failed NBA result. No score is substituted into saved J and J is not refitted.

## Measurements and fixed decision rules

Keep original native and original-Q-top identities fixed. New scores only produce
strictly-positive acceptance or abstention for those choices; zero is rejection.
Missing stays missing. No reranking/fallback/trajectory is adopted. Evaluation
retains the inclusive 10-source-pixel match rule, while training boundary masks
remain unchanged. Preserve unknown, off-boundary and absent cases explicitly.

**1. Primary practical context comparison: LC versus matched LL.** On each held
NBA game and each of the two fixed policies require: correct kept not lower,
wrong eligible kept not higher, and certain-hidden emission frames not higher.
Require no loss of any LL-kept correct policy identity. At least one strict
improvement in a primary NBA cell is required; equality is no context advantage.
Show every gained/lost identity, not just aggregate counts. This is a finite
engineering criterion, not statistical proof, and remains one seed/three games.

**2. Useful component advance: LC versus saved Q.** Apply the same per-game,
per-policy nonregression, no-lost-correct and strict-gain rules. Additionally
retain all bound protected Q successes: 6,207 NBA/HOU policy rows, 547 known-correct
Q-positive weak-point rows, and 745 protected HOU stress queries. These overlap;
never sum them as independent cases. No HOU per-episode/policy correct loss,
increased wrong/hidden count or newly accepted wrong/hidden identity is permitted
to pass this component gate. Preserve all 21 named recoveries, including all six
below-.01 points, even where they are negative controls rather than protected
positive scores. A primary context gain failing this gate is evidence, not a
replacement component.

**3. Relation to our strongest saved result.** For all original 8,578 fixed-policy
rows and the separate 720 BKN rows, compare LC and LL with saved J at identical
choices: newly retained correct points J rejects, newly rejected wrong/hidden
points J accepts, and every J-kept correct point lost. Include all agreements
and unknowns. An image-component gain over Q is not automatically progress over
J's 2,541/2,811 (90.39%) quality-top result. Any lost J-kept correct identity or
increased wrong/hidden outcomes rules out a claim of drop-in readiness. No
integration is performed even if this descriptive check is favorable.

**4. Full-pool ranking evidence.** Score the complete original uncapped pool.
For every eligible frame report whether a match exists, strict match-first rank,
ties, best matching/wrong score margins and paired improvements/regressions versus
LL and Q. Report all 21 package-empty frames and nonlocalizable/hidden frames
separately; a missing matching proposal cannot be created by this scorer. Fixed
original-Q-top choices contain only 2,542/2,811 correct points (90.43%), so acceptance
alone cannot reach 95% on those choices. Improved full-pool ranking can justify
a later selection design even if a fixed-zero acceptance gate fails. It cannot
be reported as a new deployed selector or as repaired coverage.

Required slices include game/block, native/weak, target/visibility, current native
success/failure, padding, boundary uncertainty and named recovery/hidden cases.
For known distant-negative points, contrast accepted reference center inside
versus outside the192px crop, including the 4,753 inside-context/outside-nominal-
local56 cases. This is analysis-only geometry, not visibility certification or
an input. Report all score breakpoints descriptively; no threshold is chosen from
them. Do not average fitted and source-held scores or treat adjacent frames,
duplicate candidates or the three folds as independent random trials.

## How each result changes the next decision

| Observed result | Supported next inference/action |
|---|---|
| LC beats LL, preserves Q successes/HOU vetoes, and offers useful cases beyond J | The fixed wider-input package earns a later integration/selection design; no automatic adoption. |
| Both improve similarly over Q | Additional learned processing helps; no specific context advantage. Do not prefer LC just because it is newer. |
| LC improves full-pool ordering but fails fixed-zero retention or hidden rejection | Ranking information is useful; acceptance/abstention remains unresolved. Preserve the gains and exact harms for a later design, with no threshold rescue here. |
| LL preserves Q while LC regresses | Reject this wider-input recipe. Examine nearby-ball, background/padding and source slices; these suggest mechanisms but do not prove which caused harm. |
| Both regress against Q despite fitting | New fusion/generalization or supervision support remains suspect; the result does not establish that context is useless. |
| Gains occur only on fitting sources or motivating BKN frames | No held-source advantage established; scene dependence/diagnostic exposure is a concern. |
| Model fails input/parity/gradient checks or does not learn fitting targets | Implementation/optimization-health result. Do not call it a scientific rejection of visual context. |

A healthy fit with poor held results does **not** uniquely separate insufficient
training situations, representation limits and optimization/generalization. No
single experiment can promise a unique cause for every failure. This design
does distinguish the practical wider-input intervention from extra capacity,
and separates ranking, acceptance, coverage and overlap with J. No failed row
automatically triggers another seed, epoch extension, data addition or model.

## Finite workload, verification and execution boundary

| Future backbone work | Calls | Candidate presentations |
|---|---:|---:|
| Frozen per-fold Q feature capture, reused by both arms | 2,776 | 88,742 |
| Eight fits, auxiliary training | 19,740 | 630,864 |
| Final original/external/BKN scoring, both arms | 3,360 | 107,388 |
| Final outer-fit training-health scoring, both arms | 2,194 | 70,096 |
| Four local + eight auxiliary reference parity calls | 12 | 384 |
| **Total** | **28,082** | **897,474** |

These count backbone forwards, not merely unique points. Head calculations on
cached features and CPU audits are not additional backbone calls. The auxiliary
point/CLS readouts share each forward. No warmup, uncounted ablation or automatic
retry is included. Exact finite registries and stream boundaries are bound in
the proposal. New Q feature capture is necessary because original embeddings
were not retained; old scores and completed detector inference are reused.

Local features require 272,615,424 bytes before headers in float64. Reuse saved
local64 crops and derive only the new192 crops from already permitted PNGs.
Use memory-mapped caches and bounded batches; identical crop pixels do not merge
fractional point identities or checkpoint-specific features. A conservative
new-artifact allowance is 20 GiB, including contexts, outputs, journals and
recovery state. Before launch verify at least that much free space and 16 GiB
available RAM; these are operational margins, not scientific hyperparameters.

The fixed workload has not been benchmarked. Propose a 90-minute supervised
watchdog with a 30-second cleanup reserve; it is a cap, not a predicted runtime.
Keep current Debug Mode ON and current driver/RAM/power policy. True Color may
remain running under the recorded narrow exception. Fresh supervisor/readiness,
fault/thermal/worker checks remain required; no setting change is part of this
design. A stop retains counters, checkpoints and partial outputs without resetting
consumed work or automatically retrying.

Implementation must validate actual producer-to-consumer records, all source/Q
checkpoint identities, local pixel and fractional-readout equality, correct
folds, matching initial states, finite nonzero trainable-group gradients and
frozen fingerprints. Extra local parity compares the manual Q point path with
the pinned reference producer; auxiliary parity checks both point and CLS from
the first actual batch. These twelve extra calls are counted above. Captured
Q logits must agree with saved overlapping controls within atol1e-5/rtol1e-6,
with identical signs at zero and fixed-choice identities. Numeric disagreement
stops before fitting; it does not replace the controls. No tolerance relaxation
or rerun is automatic. Focused geometry/source/transport tests precede execution;
all final outputs and decision counts receive an independent audit afterward.

All 172 inherited worktree contents and previous scientific outputs are preserved.
This design authorizes no new GPU execution by itself. Next is implementation
of this concrete protocol, CPU checks and a bound execution package. Existing
reference reviews do not need to be repeated. Git staging/commit/push, new labels,
protected evaluation, detector changes and adoption are outside this increment.

## Research and actual review coverage

Reused the completed full-history reconciliation and maintained source/authority
map, then freshly inspected relevant original Q code, saved scores/manifests,
Q/J/origin/producer-transfer/coverage/input-screen results and historical role
rules. Three independent agents challenged architecture, population/budget and
scientific interpretation. This is not a fresh reread of every chat or paper.

- [DCR](https://arxiv.org/html/1803.06799v3) supports studying hard false positives
  separately and cautions against excessive contextual evidence. Its detection
  benchmarks do not validate this crop size or point-quality model.
- [Multi-region detection](https://www.cv-foundation.org/openaccess/content_iccv_2015/papers/Gidaris_Object_Detection_via_ICCV_2015_paper.pdf)
  motivates retaining object detail alongside complementary regions; context can
  also mislead. Its architecture and benchmark gains are not transferred here.
- [Side-Tuning](https://arxiv.org/abs/1912.13503) supplies a precedent for preserving
  a base representation during adaptation, not a guarantee that this fresh fusion
  head preserves predictions. Its additive-logit variant was not selected.
- [Fine-tuning and feature distortion](https://arxiv.org/abs/2202.10054) warns that
  improved fitting can worsen shifted-source performance. Our local encoder stays
  frozen, but the auxiliary representation can still overfit; matched outer folds
  measure that risk. No LP-FT benefit is assumed and no warmup arm is added.
- [Background reliance](https://arxiv.org/html/2006.09994v1) motivates the explicit
  source/background and nearby-ball error checks. This is not evidence that our
  model necessarily has the same failure mechanism or effect size.

Primary abstracts and relevant full-text sections were checked as recorded in
the design reviews. Inaccessible CVF pages were not represented as read. Wider
context, training-support repair and later calibrated selection remain distinct
options; this bounded experiment does not silently combine them.
