# Candidate acceptance experiment: preserve useful points, reject errors

October 29, 2026. **Design and metadata preparation complete; unimplemented and
unrun.** This is the next bounded experiment after the accepted CPU failure
study. Ryan requested this design and online research, building on earlier work.
No new neural inference, fitting, gate endpoint or threshold study occurred
during preparation. Existing results and all 111 prior worktree contents remain.

## Question and intended decision

**Can an acceptance score combining learned point quality with observable
candidate-pool and response evidence retain more correct points while rejecting
wrong locations and certain-hidden emissions, on scorer-held games?**

Keep candidate ranking fixed. Compare the original native point and the current
quality-top point as two separate diagnostic policies. Each policy either keeps
its fixed point or abstains. There is no fallback, reordering, temporal path,
replacement candidate or model adoption. A third, complete candidate-set view
reports every point, available match and hidden survivor without emitting a track.

The proposed gate predicts **geometric candidate usefulness**, not semantic
ball-presence in a crop. Existing labels do not justify the latter: a wrong
coordinate's crop can contain the real ball elsewhere. This is a small
conditional acceptance model using different information, not a renamed copy
of the existing image-quality head.

We are closer to a useful ranking component, with 862/882 strict-first HOU
frames and all ten e01 recoveries. A reliable tracker is not established.
Held quality ranking is 2,542/2,811 (90.43%); rejection alone cannot raise that
correct/eligible ceiling to the existing 95% requirement. The native policy's
ceiling is 2,807/2,811. HOU ceilings are 842/882 native and 862/882 quality-top;
the native policy could lose only four correct points and still reach 95% there.
These exposed-data ceilings are scope limits, not forecasts of acceptance.

## Evidence carried forward and new research

The [completed CPU study](ball_tracking_saved_score_failure_study_results.md)
retains 7,468 context frames, 50,243 score slots, all 6,720 contrasts and 60
historical cases. Its accepted attempt003 passed 25 tests and 1,615,156 output
checks. It found 267 held frames with correct ordering but no positive match,
264 paired rank regressions, median matching-native/weak score shifts of
-4.529/-6.751, and a median full-pool margin reduction of 8.310. Those failure
groups can overlap; do not add them as distinct failed frames. Support patterns
include both successful unsupported cells and failures with available support.

We reuse the completed 398-turn/47-page historical reconciliation, inherited
56/75 research-ledger coverage with its limits, Session17/18/19 handoffs and the
current-session CPU design/execution reviews. Fresh team reading inspected
material original reports/code, actual cached-record schemas and the primary
research listed below. This is not a fresh every-session/every-paper reread.

| Earlier evidence | Consequence for this design |
| --- | --- |
| Crop/motion/player-context results improved candidate support but left player-adjacent hidden errors | Pool agreement is evidence to test, not proof of identity; no generic proximity or smoothness rule is assumed safe |
| Weak-response work recovered e01; original native 842 HOU correct versus strong/weak selected 821/831 | Protect native successes and weak recoveries together; do not reward weak replacements automatically |
| Six scalar response rules failed sufficient ranking/absence tests | The new question concerns joint response, tuned quality and pool evidence; no new scalar-cutoff sweep |
| Frozen CLS logistic veto removed 207/581 correct points | A verifier is not acceptable merely because it removes negatives |
| Frozen point ranks improved CLS 259 to 527/882 but failed rejection/recovery cases | Preserve these controls; do not claim frozen descriptor similarity solves acceptance |
| Current quality scorer already adapts two DINO blocks plus a learned head with positive/distant/hidden targets | Repeating the same crop/head/labels under the name presence would not isolate a new explanation |
| Current quality ranks 862/882 HOU, but loses points and ordering across games | Freeze its ranking and test acceptance separately; keep unresolved rank errors visible |

Fresh primary-source findings informing the choice:

- [Guo et al., calibration, §4.2](https://proceedings.mlr.press/v70/guo17a/guo17a.pdf):
  confidence adjustment can preserve the underlying prediction. For our scalar
  logit, positive temperature preserves order and sign at zero. It cannot create
  better retention/error ordering; include a score-only control instead of
  assuming numerical probability calibration solves the project.
- [Liang et al., selective classification under shift, §§2.4–2.5, 3.1–3.2](https://arxiv.org/html/2405.05160v2):
  compare rejection scores with the predictor fixed; distinguish full-curve
  potential from a deployable cutoff. Their class-logit margins motivate an
  observable competition control, but independent candidate scores are not
  mutually exclusive class logits. Our spatial version is an engineering test.
- [Cattelan and Silva, post-hoc confidence study](https://proceedings.mlr.press/v244/cattelan24a.html):
  useful classification and useful confidence ordering can differ. The work
  supports comparing rejection functions without retraining the predictor; its
  ImageNet/multiclass normalization results do not transfer automatically here.
- [Corbière et al., learned confidence, §§2.1–2.2](https://proceedings.neurips.cc/paper_files/paper/2019/file/757f843a169cc678064d9530d12a1881-Paper.pdf):
  failure prediction can be learned separately. Their true-class training target
  is unavailable at inference; similarly, no annotation-derived margin or
  visibility field may become our gate input. This is conceptual support, not a
  replication or performance guarantee.
- [Ovadia et al., uncertainty under dataset shift, §§4.2–5](https://arxiv.org/abs/1906.02530):
  calibration on familiar data can fail after a distribution change. We therefore
  require source-held results and report model-training-size changes explicitly.
- [SelectiveNet, §§4.2–5](https://proceedings.mlr.press/v97/geifman19a/geifman19a.pdf):
  rejection must be evaluated with retained coverage. Its jointly trained network
  changes the predictor and is a larger first intervention than this fixed-ranker
  test; its training coverage target does not guarantee test coverage.
- [Basketball candidate crops, §§2.2, 3.2, 4 and 4.6](https://arxiv.org/html/2204.00003):
  learned image evidence remains a plausible later alternative. That study uses
  pretrained VGG16, diameter supervision and principally 14–37px training balls;
  its camera/crop conditions differ from these broadcasts. It does not establish
  our best crop size or justify semantic absence labels from wrong coordinates.
- [Stacking guidance](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.StackingClassifier.html)
  and [nested evaluation guidance](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html)
  support separating base predictions, second-stage fitting and outer evaluation.
  The source-specific construction below is required; ordinary row-wise cross
  validation does not provide it.

## Fixed populations, labels and source roles

Reuse the original 3,329 package frames / 19,632 candidates, including 21 empty
frames. NBA contains 3,179 frames / 18,813 candidates; NFHS is secondary only.
Fit gate targets exactly as before: 3,433 NBA matches at <=10 source pixels,
13,776 clearly distant eligible points and 315 certain-hidden points. Exclude
65 boundary-unknown and 1,224 masked candidates from fitting; preserve all their
scores, records and reporting roles. Accepted labels never change.

HOU's full registry remains 960 frames, 10,778 main queries, 960 stress slots
(949 observed, 11 missing), plus 60 historical rows in their four original roles.
HOU does not choose features, regularization, checkpoint or cutoff. DET remains
the original 18 historical queries only; no new frames or protected data.
The original 6,720 choice slots / seven directed contrasts, 299 missing choice
slots, all 17 incomplete-peak cases and every prior case tag remain.

## Comparisons, fixed before any endpoint measurement

1. **Q, existing raw quality.** Reuse all saved logits, zero reference and
   existing candidate-set curves. Extract new fixed-policy views only where the
   original consumers did not already publish them; do not rerun old producers.
2. **S, score-only acceptance head.** One nonnegative-slope logistic score using
   Q alone, fitted on the same nested rows and weights as J. This isolates a
   changed score scale/intercept at zero. With positive slope its full threshold
   ordering must equal Q's; zero slope is a constant-score degeneracy, reported
   explicitly rather than claimed as equivalent discrimination.
3. **J, joint acceptance head, the primary experimental arm.** One fixed
   16-feature regularized logistic score using the contract below. Compare J
   with both Q and S to distinguish additional information from a shifted cutoff.
4. **M, unlearned spatial-competition control.** Candidate quality minus the
   highest quality at a distinct center farther than 20 source pixels; if no
   distant rival exists, use that candidate's raw Q score. Preserve a no-rival
   flag and separate fallback counts/curves. Never substitute infinite
   confidence. This composite fallback is fixed engineering, not a calibrated
   probability or a direct reproduction of a multiclass-margin paper.

M adds no model fit. Its full unselected curves are the intended comparison;
at zero a unique quality-top candidate normally beats its rivals by construction,
so that reference alone does not establish useful rejection. No outcome-driven
feature additions, alternative radii, hyperparameter sweep or arm selection.

For both fixed policies, select the point before applying any acceptance score.
Native uses the exact saved native-selected identity. Quality-top uses maximum
saved quality over the original main pool, breaking exact top ties by stable
candidate/query ID, never by reference labels. Record ties, all tied identities
and strict-first rankings separately. A rejected point produces abstention;
another surviving point is not substituted. Empty/missing choices remain missing.

## Observable feature contract

For a scored candidate/probe i, take coordinates from the saved producer/query,
never the annotation. Its original main pool supplies the neighbor context.
Include all observed main candidates, including fitting-unknown ones. Group
exactly equal numeric (x,y) centers and use their maximum quality for context
only; preserve every original candidate for fitting, ranking and reporting.
Exclude the entire group at i's coordinate as self/duplicate support. For stress
probes, use the same original main pool without adding the stress point.

Near centers have 0 < distance <=20; far centers have distance >20 source pixels.
The radius is fixed as twice the accepted 10px tolerance: two matching points
can be 20px apart. It is not a measured ball diameter or proof that neighbors
are the same object. Wrong nearby points can also be excluded as rivals.

| Features | Count | Definition |
| --- | ---: | --- |
| Core continuous | 4 | Q; log(1+saved response mass); log(1+component pixels); padded pixels/4096 |
| Origin indicators | 2 | native=1/weak=0; separate origin-unavailable indicator |
| Core missing indicators | 3 | response mass, component pixels, padding |
| Pool continuous | 4 | Q-max(far); Q-max(near); log(1+number of distinct near centers); log(1+number of distinct far centers) |
| Pool missing indicators | 3 | far maximum unavailable; near maximum unavailable; complete main-pool context unavailable |
| Total | 16 | Plus one unpenalized intercept |

Available empty neighborhoods have count zero and missing maxima. Unavailable
historical pool context has null counts/maxima and the unavailable flag; do not
invent a zero-sized observed pool. Missing continuous inputs are imputed to
their fitting-data mean only inside the CPU transform, giving standardized zero;
raw nulls and indicators remain in persisted records. Weighted means/variances
use only observed values in the gate's own known-target fitting rows, with the
same weights renormalized over observed rows. An all-missing feature uses mean0,
scale1 and an explicit degeneracy record; zero variance uses scale1. Binary flags
are not standardized. Reject unexpected nonfinite/negative response quantities.

Package and HOU-main response/component/origin fields are available. All 949
observed stress queries have response mass and saved padding, but component
pixels and thresholds are unavailable. Historical rows retain crop geometry and
padding, but lack complete pools and response/origin information. Preserve their
missing indicators and mark their new gate scores as out-of-fitting-schema
semantic diagnostics; they are not independent geometric accuracy measurements.
The 11 missing-image stress slots have no Q or gate score and no fake image.
For NFHS and HOU use existing all-NBA Q; only NBA outer rows use held Q.

Forbidden inference inputs include reference visibility, identity certainty,
uncertainty radius, difficulty tags, target group, accepted coordinates or
distances, game/source IDs, selection-category annotations, and the completed
study's max-matching-minus-max-miss margin. That margin uses labels. Do not use
fitted targets to filter the neighbor pool or derive any input feature.

## Honest source nesting and reuse

Naïvely training a leave-CHI-out gate on existing OOF DEN/SAC scores leaks CHI
through the models that produced those training scores. Conversely, training
on in-sample quality scores can be outer-game-disjoint but faces the saturation
shift the study exposed; it is not held-score calibration. Use this fixed matrix:

| Gate | Gate fitting scores | Evaluation scores |
| --- | --- | --- |
| Outer CHI | DEN from SAC-only quality; SAC from DEN-only quality | CHI from existing leave-CHI-out quality |
| Outer DEN | CHI from SAC-only quality; SAC from CHI-only quality | DEN from existing leave-DEN-out quality |
| Outer SAC | CHI from DEN-only quality; DEN from CHI-only quality | SAC from existing leave-SAC-out quality |
| Final all-NBA | Existing two-game OOF quality for each of CHI/DEN/SAC | Existing all-NBA quality on HOU, NFHS and historical rows |

Fit S and J separately for each row: eight CPU gate fits. Each feature row's
whole pool must use the same base scorer as its point. No outer-game labels,
scores or feature standardization enter that outer gate's fit. The three new
single-game scorers are reused across outer folds; they are not an ensemble.
Final-gate package OOF training predictions may be retained as fitting diagnostics,
never presented as another independent gate test.

The required post-fit evaluation registry has **4,289 context frames** (3,179 NBA
outer-held,150 NFHS,960 HOU) and **31,430 score slots per learned head**:18,813 NBA,
819 NFHS,10,778 HOU-main,960 stress and60 historical. Each head has31,419 observed
scores and11 missing-image slots, thus62,860 slots/62,838 observed across S and J.
The old NBA fitted context remains available in reused controls; it is not
fabricated as a new independent gate evaluation. Training-feature registries
are separately the37,626 new nested cross-score slots and18,813 existing OOF
final-gate input slots, with known-target masks. They are not extra test cases.

Inner base models see one game, evaluated outer models see two; final gate
training bases see two and HOU's base sees three. This training-size shift is
part of the test, not eliminated by nesting. Cosine nine previously saw these
package games, so none of this establishes end-to-end unseen-game evaluation.
Three games also leave no independent source for a third calibration layer.

## Fixed fitting recipes and workload

New quality fits use the original pinned DINOv2 initialization, target mask,
64px crop/readout, two adapted blocks/head, optimizer, six epochs, seed20261028,
float32/deterministic execution and batch32 from the original quality pilot.
Initialize afresh from the pinned pretrained model, **never from a trained
all-NBA/leave-game-out checkpoint**. Recompute original hierarchical objective
weights using only that single game's candidates; do not reuse all-NBA weights.

| New fit | Match / distant / hidden fitting candidates | Fitting total | Updates | Score only these other games |
| --- | --- | ---: | ---: | --- |
| CHI-only | 1098 / 4343 / 129 | 5,570 | 1,050 | DEN 5,790; SAC 7,088 |
| DEN-only | 1103 / 4497 / 12 | 5,612 | 1,056 | CHI 5,935; SAC 7,088 |
| SAC-only | 1232 / 4936 / 174 | 6,342 | 1,194 | CHI 5,935; DEN 5,790 |

DEN hidden support is only eight frames in one block, all weak-origin. All three
required target strata exist in each fit; an absent origin child is permitted
by the original weighting rule, not replaced with invented examples.

Exact proposed neural work: **3,300 updates / 105,144 training presentations**;
**37,626 cross-game score presentations**, scored separately by game in batches32
for **1,178 score forwards**; three first-batch parity forwards /96 presentations.
Total: **4,481 neural forwards /142,866 presentations**. No new HOU/NFHS/historical
neural inference is needed; their old Q scores and original queries are reused.
All existing four-fit training/results remain untouched.

For each gate, use all known-target candidates in its fitting games. Retain the
original .5 positive/.25 distant/.25 hidden hierarchy, then game/block/frame/
nonempty origin/candidate, normalized to sum1. Existing outer/all-NBA weights
can be reused by candidate ID where their fitting population exactly matches;
verify equality. This prevents dense clutter from supplying an implicit prior.
The scores are not claimed to be calibrated probabilities.

In float64 minimize sum_i w_i*BCEWithLogits(y_i, b+beta*x_i) +
(0.01/2)*sum_j beta_j^2, with intercept unpenalized. Use installed NumPy2.4.6
and SciPy1.17.1, analytic gradient, L-BFGS-B, zero initialization, maxiter10000,
ftol1e-12, gtol1e-9. S constrains its slope >=0; J is unconstrained. No library
install or hyperparameter search. Require solver success and finite parameters,
loss and predictions; preserve failures without changing solver/regularization
after examining evaluation. Record termination reason, iterations and gradient
residual. No predicted retention guarantee is inferred from fitting performance.

## Measurements and predeclared outcomes

Use score>0 as the fixed operating reference for Q/S/J; equality is an explicit
tie/rejection. M's zero result is descriptive, with the limitations above.
Also report every unique-score threshold, with tied scores moved as groups,
plus accept-all/reject-all endpoints. Reuse equivalent Q curves where available.
No cutoff is selected on held games, HOU, NFHS or historical data, and no fitted
99% retention rule is represented as a calibrated promise.

For each outer game, block, fixed point policy and arm, publish retained-correct,
rejected-correct, accepted wrong-eligible and certain-hidden emissions; exact
paired gains/losses/agreements; missing choice/empty-pool cases; and all original
unknown/reference roles. Wrong-eligible evaluation retains the original <=10
metric, with near-boundary unknown-for-fitting errors reported separately.
Show source totals before pooled summaries. Fixed-policy denominators are all
original eligible/hidden frames, not only emitted or easy cases.

Full candidate views retain native/weak positives, distant/boundary/hidden/unknown
slots, any-match survival, matching pool coverage, all hidden surviving candidates
and distinct hidden frames. Keep candidate and distinct-frame units explicit.
Primary tradeoff views are correct-retention versus wrong-eligible outputs and
correct-retention versus hidden-frame emissions, for each policy/source, with
full score breakpoints. These are descriptive discrimination curves, not selected
deployment operating points. Report annotated oracle/Pareto comparisons only as
potential, never as a chosen threshold or independent validation result.

Retain all ten e01 recoveries; six e05/14–19 below-.01 cases; all21 broad gains;
842 correct/19 wrong/21 missing HOU native choices; six strong gains/27 losses
including two missing; e05/8–9 and206; 19 shared/eight added hidden emissions;
all78 noneligible HOU; three point/two CLS/11 peak rank regressions;17 incomplete
peak controls; all seven old contrasts/agreements; and four historical roles,
including the two accepted balls still negative under Q and six unresolved cases.

Interpret results using these fixed branches:

- **Promising acceptance component at the fixed reference:** J0 retains at least
  as many correct points, accepts no more wrong-eligible points, and emits in no
  more certain-hidden frames than both Q0 and S0, for every NBA outer game and
  both fixed policies; at least one strict improvement must occur. Also require
  no new loss of a Q0-kept correct fixed-policy point in the named HOU
  recovery/adverse protection views, separately for native and quality-top.
  Additionally protect the exact known-correct, Q0-kept named HOU stress probes,
  including the ten e01 recovery queries. Other matching alternatives remain
  complete candidate diagnostics rather than an extra unstated veto. Require
  HOU hidden-emission counts no greater than either Q0 or S0 separately for each
  fixed policy. HOU can veto a regression but cannot choose a repair.
  This supports later integration design only; it is not tracker acceptance.
- **Better discrimination, unresolved operating point:** J's complete tradeoff
  curves offer improvements but fixed zero fails the preceding criterion.
  This is a descriptive per-source assessment, not an additional automated pass
  rule or arm selection. Report exact tradeoffs; any future threshold/calibration design
  is separate. Do not discard useful curve evidence or pick its best cutoff.
- **Only score adjustment helps:** S accounts for the fixed-reference gains and
  J adds no consistent separation. The additional metadata hypothesis is not
  supported by that result; do not claim a new presence capability.
- **No consistent improvement / source dependence:** preserve all losses and
  failures. This bounded scalar/pool recipe is insufficient; it does not prove
  all image learning fails. Wider candidate-conditioned image context or a
  structured pool-answerability objective remains a separate design question.

The original >=95% correct, <=1% wrong, zero-hidden, temporal/recovery and human
trajectory gates remain unchanged. A rejection-only policy cannot repair a wrong
ranking or an absent candidate; those failures continue to bound the result.

## Preparation, implementation checks and execution boundary

Preparation verifies current 111-file preservation, 74 existing input bindings,
actual schema availability and the above per-game counts. It computes no new
gate features, margins, curves or scientific endpoints. Fine-tuned postfit DINO
embeddings were not saved; do not claim a cached image-feature experiment exists.
Original training/evaluation uint8 crop caches are available. Model-free schema
and hashing preparation needs no GPU query or setting change.

Next implementation must add a new consumer/runner and new output attempt, with
frozen code/tests and independent review before execution. Focused tests must
cover numerical-category equality, duplicates/self exclusion, <=20 versus>20,
missing versus zero, empty pools, external stress probes, all unknown neighbors,
label-permutation invariance of features, whole-game exclusion through every
base/gate path, fitting-only standardization, single-game weights, constant-score
S, tied threshold groups, policy no-fallback, all named populations, and exact
transport of reused outputs. Compare the new raw-score adapter to existing
published results without rerunning completed experiments. Independently audit
new scores, fits, coefficient/normalization transport and complete outcome rows.

The current request is design/research. This protocol is not a launch command,
and no execution approval is being requested before implementation is concrete.
The additional neural work requires its own prepared launch/readiness review.
Reuse the last successful owned-job supervision design, Debug Mode ON, fixed
workload and a 90-minute operational watchdog; time is a stop limit, not an
estimate or scientific budget. Keep two-second telemetry and existing80C/device/
thermal-fault stops, preserve checkpoints/logs and stop on a renewed substantive
device fault without automatic retry. No driver/clock/power/fan changes. No
trustworthy new runtime or peak-memory estimate is claimed from metadata alone.

There is no new label campaign, protected evaluation, external dataset/weights,
outside specialist, ACB prototype or Git integration. Reuse the original
Session17 preservation chain and all failed/completed work. The machine-readable
proposal binds this document and its metadata receipt; independent review and
additive context preservation are saved under
`data/outputs/ball_tracking/candidate_acceptance_gate_v0_1/preparation/`.
