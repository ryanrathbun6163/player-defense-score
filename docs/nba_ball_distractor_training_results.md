# Fixed ball-versus-distractor training result

**The model trained successfully, but the classifier fails the protection checks.**
One frozen-feature logistic model was fitted, with no retry, parameter sweep,
threshold tuning, or change to the saved baseline. Its training and initial
reference extraction completed in 33.125 seconds. The complete 3,373-point
comparison rejects this recipe: it removes 207 of 581 previously matched positions, with all original evidence preserved.

## Execution authority and the earlier stop

The earlier [reference result](nba_ball_distractor_reference_results.md) remains
an insufficient-coverage result. The inventory sampled candidate geometry,
time and provenance, but could not guarantee the required semantic categories.
It yielded no excluded clothing example and no newly sampled, actually emitted
excluded head error. Those are still missing; no label was changed to fill them.

Ryan subsequently said: “ok chat fixed this and train the model please. I don't
like it when you make mistakes”. The separate
[execution amendment](../configs/ball_tracking/reviews/nba_ball_distractor_execution_amendment_v0_1.json)
records the interpretation: run one provisional experiment using the qualified
fit set now, keeping original adoption criteria and human review requirements.
It does not record the new AI labels as human accepted. All 26 previously
accepted classes remain unchanged. The frozen plan, original approval and
earlier insufficient-coverage result retain their original bytes.

The bounded AI follow-up search screened 1,072 DET emitted-point target crops
with permitted five-frame support. Complete five-frame context was inspected
for two arm leads, DET10952 and 11831. A separate P003 search screened 22 fresh
targets and confirmed arm/wrist leads at 19, 23 and 64 using complete context.
The search found no defensible example to fill either missing category; this
is not proof that no such example exists. The source inspection receipts remain
separate discovery evidence, and none of these examples entered the fit or the
original check census.

## Exactly what trained

The DINOv2 ViT-S/14 backbone remains frozen. The fitted component is a
385-parameter logistic classifier: 384 feature weights and one bias. It uses
the approved native 64-pixel crop, fixed 224-pixel preprocessing, float64
L2-normalized features, penalty 0.005, zero decision boundary, and one
zero-initialized L-BFGS-B call. These logits are not calibrated probabilities.

Labels fixed before inference yield 90 training object groups: 52 ball,
18 detector distractor, and 20 source-authored distractor groups. They produce
109 distinct native crops representing 111 resolved rows. Weight masses are
0.50 / 0.25 / 0.25 respectively, allocated equally through occupied blocks,
objects and distinct crops. All 75 check rows and 24 fit unknowns are excluded
from fitting. Four unavailable contrast slots have no crop or feature; all
33 combined unknown rows remain unscored for semantic correctness.

The run reused the original 60 crop descriptors and computed 177 new distinct
ones. Its 237-feature cache includes all 206 reference rows with non-null
centers and the separate 34 previously exposed qualitative cases. It decoded
176 cached source PNGs and no source video. The optimizer converged after
17 iterations / 20 function evaluations, with objective 0.5318141097931007,
maximum absolute gradient 2.5518189337428096e-08, and no optimizer warnings.

## Initial reference results

| Excluded check | Correct / total | Interpretation |
| --- | ---: | --- |
| Ball crops, old plus proposed | 24 / 46 | Fails strict protection of every ball |
| Distractor crops, old plus proposed | 19 / 20 | Diagnostic classification; many were never emitted |
| Ball object groups, every member correct | 19 / 39 | Repeated crops are grouped, not counted as independent objects |
| Distractor object groups, every member correct | 17 / 18 | Grouping remains AI-proposed |
| Ten previously accepted checks | 5 / 10 | Only 2/6 balls and 3/4 distractors classified correctly |
| Exposed SAC1419–1421 head crops | 2 / 3 negative | Frame 1419 remains positive |
| Exposed DET11722–11725 near-head balls | 1 / 4 positive | Frames 11723–11725 would be vetoed |

The accepted old references already establish failure, independently of the
pending new labels. Train-set row results are 62/70 ball and 39/41 distractor;
these are fit diagnostics, not validation accuracy. New check labels are AI
proposals, and all clips are exposed development material, not independent
test data. Correct classification of an unselected candidate removes no
tracking error.

## Complete five-clip comparison

The separate arm applies the frozen zero boundary to all 3,373 saved emissions
across 3,975 permitted positions. The feature pass completed in 569.860 seconds:
3,225 new encodings, 148 cache reuses, 2,295 NBA source PNG reads and 1,273 NFHS
permitted-frame decodes. All 225 protected positions stayed excluded. No refit,
new candidate selection, coordinate replacement or new gap repair occurred.

| Source | Saved emissions | Retained points | Removed | Unique protected matches retained |
| --- | ---: | ---: | ---: | ---: |
| SAC | 1,311 | 763 | 548 | 195 / 218 |
| DET | 1,074 | 390 | 684 | 71 / 213 |
| Possession 001 | 327 | 192 | 135 | 20 / 48 |
| Possession 002 | 308 | 267 | 41 | 50 / 50 |
| Possession 003 | 353 | 235 | 118 | 38 / 52 |
| **Total** | **3,373** | **1,847** | **1,526** | **374 / 581** |

The 581-point protection set is a deduplicated union. Report its cohorts
separately: 369/559 original matches retained, 5/22 additional eligible matches
retained, and 0/3 previously accepted gains retained. Those three gains overlap
the original cohort and must not be added again. The original 790 reference
outcomes change from 559 matches / 14 wrong / 79 missing / 13 hidden alarms to
369 matches / 7 wrong / 276 missing / 0 hidden alarms. Its 47 unscored positions
remain unscored. SAC's easy control retains 60/60; DET's drops to 35/60.

All four newly proposed emitted check distractors are suppressed: DET11027,
11102, 11097 and 11552. They are four object groups in two blocks, comprising
hands and arms. This is a limited observed benefit; it does not satisfy the
missing head coverage or compensate for lost balls. SAC1419 remains on the
head, while 1420/1421 disappear. DET11722 remains; the three valid near-head
points 11723–11725 disappear. These known sequences remain exposed qualitative
regressions, not new independent truth.

There are 1,512 individual original-point vetoes and 14 revoked fills across all
10 existing repaired gaps. Of the 1,526 removals, 1,523 have negative logits;
three positive fills disappear only because another required gap member fails.
Original missing positions remain missing. Missingness rises from 602 positions
in 75 intervals (16.683 seconds) to 2,128 positions in 285 intervals (48.991 seconds),
with every interval split at the permitted segment boundaries.

All retained coordinates and provenance remain exact. The scored geometric
references show no new wrong outputs or hidden alarms. Those construction properties do not establish safety:
1,305 removals have at least one audit flag for absent/unscored geometric
evidence or an unresolved reference. This union is not a count of semantic
unknown labels: some points have separate proposed appearance labels. Every
removal carries its separate evidence status; unresolved identity never counts
as a correct rejection. Geometric matches alone do not establish object
identity. The original selection and all accepted baseline artifacts are unchanged.

## Saved model and comparison package

The [saved fitted parameters](../data/outputs/ball_tracking/nba/ball_distractor_training_v0_1/fit.json)
and [complete five-video comparison](../data/outputs/ball_tracking/nba/ball_distractor_training_v0_1/review/review.html)
are local ignored artifacts. The comparison places the original saved output
on the left and the failed experimental filter on the right. It preserves
native timing, explicit missingness, protected blackouts, NFHS player IDs,
every changed episode and the actual final frames. New human label and motion
review remain pending; the failed model is not an accepted replacement.

The [compact result record](../configs/ball_tracking/reviews/nba_ball_distractor_training_result_v0_1.json)
binds the fitted model, all scores, full comparison, implementation, checks,
independent audits, and preserved repair history. Independent calculations
reproduced the initial objective/weights, every one of the 3,373 emission scores,
and all policy decisions without another fit. Those checks establish numerical
and record consistency, not independent semantic ground truth.

A later review found that reopening an already completed evaluation phase would
try to write a new completion timestamp. The original executed driver is saved;
the corrected driver verifies and returns existing results without loading the
encoder or recomputing the policy. The original training, feature and comparison
receipts remain unchanged.

The full review verifies all 4,200 timeline slots, 225 protected blackouts,
305 suppressed episodes, eight permitted-segment finals and five actual finals.
There were six source encodes because the main renderer repeated P002 while an
independent worker was finishing it. Both P002 verification failures are kept:
four compression-residual pixels exceeded the strict black threshold. A separate
video-hash-bound check accepts only those exact four RGB values, verifies intended
raw panels are zero, and retains the original threshold everywhere else. It
fully rechecked the first existing video with no source reread or encode; two
negative controls passed. The production renderer and scientific outputs did
not change. This repair does not convert the original failed receipts to success.

There are 26 distinct passing focused tests, plus the two recovery negative
controls. Representative encoded stills, including all actual finals, were
inspected for layout and marker transport. This is not continuous human playback
or acceptance of the new labels or trajectories.

## Decision

This fixed feature/crop/classifier recipe is rejected for adoption. The model
has learned some distractor distinction, but does not preserve valid balls.
The remaining evaluation coverage gaps cannot turn this failure into success.
No additional fit or boundary search is part of this run. Ball tracking and
the wider Player Defense Score pipeline remain unfinished.
