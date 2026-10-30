# Choosing the next NBA ball-tracking experiment

## Completed result and current decision, 2026-10-26

The frozen CPU study is complete. It preserves evidence that useful weak ball
responses exist, and rejects the six declared scalar rules as a sufficient next
ranking/visibility mechanism. No new selector, image-model inference or training
ran. The original preparation narrative below is retained; its "not yet run"
checkpoint is historical. Detailed results and validation follow that narrative.

The next recommended experiment is a controlled comparison of whole-crop versus
candidate-local image features using the same saved backbone and crop geometry.
See the [concrete proposal](ball_tracking_point_feature_feasibility_proposal.md).
Its CPU geometry preparation is complete; the model comparison remains proposed
and unrun.
This study does not establish that all joint or temporal response methods fail,
that the local image features will work, or that training is necessary.

## Decision before new descriptor results

Run one bounded **response-structure feasibility study** on saved cosine-nine
outputs before choosing another tracking rule, image representation or fit.
The question is whether spatial information already present in the model's
response map can help rank candidate locations and support choosing absence.
This is a CPU diagnostic with existing labels, no new tracking coordinates,
no model calls and no training. Its
[prospective protocol](../configs/ball_tracking/proposals/candidate_response_feasibility_v0_1.json)
fixes the measurements, cohorts, comparisons and decision branches before the
new descriptor results are computed.

Ryan requested moving forward and being extremely thorough in choosing this
step. The decision reuses the completed
[sixteen-session reassessment](research/ball_tracking_full_history_reassessment_2026-10-26.md),
the current authority map and relevant primary reports/code/saved outputs. It
does not claim another complete transcript reread. Historical approvals and
reviews remain intact; current authorization does not open protected evaluation,
change data roles or initiate a new labeling campaign.

## What the recent progress establishes

The [weak-response study](ball_tracking_weak_response_results.md) shows useful
observed signal. Two different weak candidate pools recover all ten missing
HOU e01 positions. A motion/speed correction restores 51 native-correct points
lost by the first sequence and adds six new correct selections. Those are
concrete gains even though neither complete method passes.

The correction still loses 27 native-correct positions in e03/e06, while narrow
weak selection adds eight certain-hidden e05 emissions and eight SAC emissions.
Corrected HOU strong/weak totals are 821/831 versus native 842/882; DET stays
219/241. This separates usable candidate availability from reliable choice.
The expanded pool's thousands of candidates also make an oracle match less
informative: dense clutter may cover many locations. Actual recovered ball
positions remain evidence, but near-reference availability alone needs a local
density control before being described as distinctive ball signal.

The next step should not assume that a new image encoder is already necessary.
Independent saved-path accounting finds a more immediate limitation: the current
objective gives every admitted strong candidate at least .2 reward and every
weak candidate .35, versus zero for missing; entering/leaving missing costs .5.
All nineteen current certain-hidden native emissions actually receive reward
1.0. Their response mass is normalized relative to other candidates in that
frame, so a strong-looking winner can earn the maximum without proving a ball
is visible.

For example, retaining the wrong native path through HOU e06 hidden frames
210–221 beats making only that span missing by 12.497 objective units; its
motion cost is only .003. The six-frame hidden span 240–245 gains 6.998 units.
The narrowed e05 false weak span 22–27 gains 2.090 units. The e05 native hidden
singleton ties absence exactly, and stable candidate-before-null ordering keeps
it. This analysis changes no choices: it explains why merely making a missing
state available did not make the rule appropriately cautious.

Native hidden mass spans 1.307–37.596 while native-correct mass spans
.941–52.052. Saved global objective margins also overlap: medians 1.9996 hidden
and 1.990 correct. Neither a large mass nor a large path margin is calibrated
visibility evidence. The fixed positive rewards and overlap motivate testing
candidate-specific response information before another motion sweep.

## Alternatives considered against the full history

| Option | Supporting evidence | Limitation and current decision |
|---|---|---|
| Response structure and evidence for absence | Current selection ignores local contrast/shape; motion correction produced real gains; complete maps already exist. | Peaks alone restate cutoff evidence, and sharp heads may resemble or exceed blurred balls. Test this cheaply before assuming it works. |
| Preserve every native selection and only fill gaps | Native HOU currently outperforms the sequence overall; original short-gap repair had three accepted additions and eight later geometric gains. | It preserves nineteen native hidden emissions and prevents useful revisions of wrong native points. SAC head anchors already propagated false fills. Keep native as comparator, not an immutable truth source. |
| Higher-detail or point-conditioned image representation | Some balls remain weak despite being depicted; a localized representation could add information beyond the existing map. | The 768 experiment improved DET 212 to 219 but retained its gap; current training fit is 2937/2941. A new crop/representation needs a specific information test, not another unchanged fit. Defer until the cheap response test clarifies what is missing. |
| Reuse the DINO appearance veto | Its fitted model suppressed some actual hand/arm distractors and completed correctly. | It removed 207/581 previously correct positions. Accepted same-frame ball/other pairs include both score calibration failures and rank inversions. Its frozen global crop descriptor cannot be treated as a reliable point-specific veto. |
| More temporal support, player proximity or cross-view agreement | Older player context corrected distant clutter and earlier look-ahead work had useful increments. | Persistent heads, inside-player hidden false points and correlated crop agreement survived those checks. Current selected strong endpoints still support eleven wrong and six of eight new hidden weak points in e05. These cues alone do not identify the ball. |

Primary evidence includes [crop/motion results](ball_crop_motion_factorial_results.md),
[player context](ball_crop_player_context_results.md),
[candidate identity diagnosis](ball_candidate_identity_diagnosis.md),
[DINO training/comparison](nba_ball_distractor_training_results.md),
[resolution](ball_tracking_nba_resolution_results.md),
[continuation and fit/sensitivity diagnosis](ball_tracking_wasb_continuation_results.md),
and [spatial-pilot results](ball_tracking_wasb_spatial_results.md). These findings
reject particular settings or recipes, not entire method classes.

A new read-only diagnosis of the fitted DINO veto distinguishes causes more
carefully. Its optimizer converged. Among four accepted same-frame ball/other pairs, two rank
the ball correctly and two reverse the ordering. DET11431 ranks correctly but
both logits are negative, whereas DET11008/11444 have rank inversions. Moving a
single threshold cannot repair both types. Native 64-pixel crops, a global CLS
descriptor, limited fitting coverage and a point-versus-crop target mismatch
remain plausible confounded causes, not established individual explanations.
These fitted-logistic failures are distinct from the original
[nearest-bank CLS screen](nba_appearance_feature_screen_results.md): its accepted
failures were DET11059/11431, while DET11008/11444
were classified correctly. The proposed point-feature comparison uses the same
nearest-bank rule for both representations and keeps the fitted-veto history
as separately identified adverse evidence.

## Available information and scope

All six HOU contexts have complete 432x768 float32 means and native source PNGs.
The study uses only the means. The main cohort is all 10,778 retained native-plus-
strict-.01 candidates over all 960 frames, including 1,204 native components;
the largest frame pool has 37 candidates. No label-dependent sampling or cap is
introduced. Every old expanded-weak selection, including missing rows, forms a
separate stress cohort; it is selected-output evidence, not an unbiased sample
of all broad candidates. It preserves the useful e05 responses below .01 that
the narrower pool cannot supply.

The broad HOU pool contains 4,020,880 candidates, with approximately 2.288 GB of
pool JSONL and 1.863 GB of raw extraction. It is streamed only for the spatial-
coverage diagnostic. Existing DINO cache overlap is insufficient for a current
HOU appearance test: none of its 3,462 distinct crop keys covers HOU. Its saved
vectors are global 384-dimensional CLS features, not patch tokens or attention.
Eighteen current DET/SAC crop-key matches have matching feature bindings and
source RGB/timing/video provenance. They remain exact-crop-only reuse, not
interchangeable frame descriptors or evidence of HOU coverage.

HOU remains repeatedly inspected checkpoint-validation development data, not
fitting data or a fresh independent test. DET receives only the fixed spatial-
coverage diagnostic after the protocol is locked; its outcomes choose no
descriptor, threshold or model. SAC's previous hidden-emission failures remain
adverse evidence without expanding this first feature study unnecessarily.
Existing NFHS evidence, labels, nine uncertain-source recoveries, every numerical
criterion and human trajectory-review requirements remain unchanged.

## Fixed measurements and interpretation

Every candidate receives the same source-centered response patch: integer
source offsets in a ten-pixel-radius disk, sampled by bilinear interpolation
through the frozen affine transform. The disk contains 317 samples; an inner
five-pixel core contains 81. No reference center determines a candidate patch.
All features are computed and saved before joining reference outcomes.

Peak is the amplitude control. Five fixed descriptors examine additional
structure: core-versus-ring contrast, response concentration measured by
entropy, covariance isotropy, distance of the response centroid from the
emitted candidate center, and response spread. Their favorable directions are
declared in advance. They share the same map and are not independent evidence.
The training target is a fixed-radius binary disk (3.75 working pixels), not a
ball silhouette. These descriptors measure the network response, not physical
ball roundness; even uniform clutter has isotropy one, and a false head may
produce a disk-like response.
Incomplete boundary patches, zero support, missing selections and undefined
shape terms remain explicitly unknown. Original mass/area are retained as
baselines; mass comparisons remain within native candidates because different
extraction thresholds give it different meanings.

Reference-assisted analysis reports each episode separately. It asks whether
matching candidates outrank competing locations, with strict ordering and ties
shown separately. A point outside the ten-pixel radius is a localization mismatch,
not a new semantic "non-ball" label. Certain-hidden frames provide evidence
against emitting, while uncertain or unscored frames remain separate.

Two scalar separation bounds use one HOU-wide cutoff per feature, with outcomes
reported by episode, rather than granting six episode-specific cutoffs. They
make tradeoffs explicit: what correct-candidate
coverage survives a cutoff that rejects all observed certain-hidden responses;
and what hidden responses could be rejected while retaining every native-correct
point. These are diagnostic limits derived using known outcomes, not fitted
weights, selected production thresholds or achieved tracker accuracy. Missing
features cannot turn either bound into a complete success. The old e01 ten gains
and e05 six below-.01 gains are explicit stress cases against discarding weak or
partially visible balls to obtain cleaner-looking statistics.

The density control compares native, broad-union and narrowed pools at each
eligible reference and eight fixed translated locations: 64 and 128 source
pixels left/right/up/down. Out-of-source controls are counted and omitted.
These are local spatial-density comparisons, not semantic negatives or independent
trials. Per-frame paired control averages accompany pooled control counts; no
p-value or generalization claim is made. Native-missing HOU frames and the
nineteen-frame DET gap are reported separately.

## What would change the next choice

Consistent ordering gains beyond peak/native mass, together with meaningful
hidden-response rejection that protects valid native and weak points, would
justify one separately frozen evidence-conditioned scoring/abstention test.
That useful increment need not already satisfy every final acceptance gate.

If the descriptors overlap, favor wrong compact peaks, or obtain separation by
discarding valid partial balls, reject only these descriptor rules. The next
proposal would then need to add specified native-pixel, point-conditioned
information and test its feasibility. It would not automatically repeat the
generic DINO veto, run another crop inference campaign or start training.
High spatial-control coverage would qualify the meaning of the broad oracle
ceiling without erasing demonstrated automatic recoveries.

Historical pre-run checkpoint: production feature extraction and reference-assisted
analyses had not yet run when this preparation narrative was written. The planned
results and exact validation receipts are now recorded below.

Primary new evidence is ignored under
`data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/`: `history/`,
`inventory/`, `design_review/` and `study_v0_1/` (then forthcoming, now complete).
No Git staging, commit, push, PR or merge is authorized or performed.

## Completed response study

The protocol and implementation were frozen at 00:26:51 UTC on October 27
(October 26 in Phoenix). Extraction then completed all six HOU contexts in
5.130 seconds: 960 frames, 10,778 main candidates and all 960 old expanded-choice
stress rows. All feature files were sealed before either the label-assisted
feature analysis or translated-control calculation. The latter processed 2,191
complete HOU/DET frames, including 1,123 eligible references, in 47.500 seconds.
No new coordinates, semantic labels, model outputs or fitted parameters result.

### Ranking: the additional scalar structure does not improve the main problem

Each of the five shape descriptors has fewer strict-first matching candidates
than peak strength in **every HOU episode**. There are small individual gains,
but substantially more losses. A strict-first gain means a matching candidate
beats every geometric miss under that feature when the baseline did not; it is
an ordering diagnosis, not an emitted correct trajectory.

| Fixed measurement | Available-feature strict-first matches / 882 | Complete paired gains / losses versus peak | Native-only gains / losses versus native mass |
|---|---:|---:|---:|
| Peak strength | 837 | control | 0 / 11 |
| Core/ring contrast | 294 | 2 / 533 | 0 / 114 |
| Entropy concentration | 80 | 6 / 748 | 0 / 121 |
| Isotropy | 317 | 3 / 511 | 3 / 80 |
| Center alignment (negative centroid distance) | 625 | 13 / 220 | 7 / 46 |
| Compactness (negative spread) | 281 | 4 / 548 | 0 / 114 |
| Native mass, native candidates only | 842 | different candidate pool | control |

The available-feature column is explicitly incomplete in 17 eligible frames;
it must not be mistaken for full-pool success. The paired peak comparisons use
859 complete frames with a matching candidate, exclude those 17, and separately
report six frames with no matching narrowed candidate. Native-only comparisons
have 857 frames with matching native candidates and 25 without. Twenty-five
main descriptors are unknown at boundaries: 22 eligible, two certain-hidden and
one visible-unlocalizable. These competitors remain recorded. Missing features
never disappear from the denominator to manufacture a ranking improvement.

### Visibility: clean-looking cutoffs discard the useful signal

Each bound below uses one shared HOU cutoff, computed from known development
outcomes. It is an explanatory bound, not a selected operating threshold. The
first bound rejects every measured certain-hidden candidate. The second keeps
all 842 originally correct native points. Neither bound is an automatic tracker.

| Measurement | Native-correct points retained at all-measured-hidden rejection bound / 842 | Hidden frames with a known surviving candidate at native-preserving bound / 34 | Old correct gains from native-missing retained at native-preserving bound / 21 |
|---|---:|---:|---:|
| Peak strength | 701 | 19 | 0 |
| Core/ring contrast | 0 | 34 | 16 |
| Entropy concentration | 0 | 34 | 21 |
| Isotropy | 12 | 34 | 17 |
| Center alignment | 62 | 34 | 6 |
| Compactness | 0 | 34 | 18 |
| Native mass, native candidates only | 735 | 19 | not applicable |

All six new measurements lose every one of the 21 old weak recovery points at
the all-measured-hidden rejection bound. At the native-preserving bound, entropy
keeps all 21, including all ten e01 gains and all six e05 gains below .01, but
leaves known candidates in every certain-hidden frame. Peak discards all those
weak gains while still leaving nineteen hidden frames. The two unknown hidden
descriptors prevent a complete zero-hidden claim for the new measurements even
where all finite hidden values are rejected. The source's `complete_visibility_claim`
is also false for the native-mass diagnostic because no tracker/adoption was run.

Thus a sharper, rounder or more centered response is not adequate evidence for
visibility in these clips. The positive-emission/restart bias diagnosed above
also remains real. This result does not isolate an exclusively semantic identity
problem or prove that every multivariate/temporal map method is exhausted.

### Density: preserve the localized recovery and qualify the broad ceiling

| HOU pool | Eligible references with a candidate within 10 px / 882 | Valid translated locations covered / 6,982 | Equal-frame average translated coverage |
|---|---:|---:|---:|
| Native | 857 | 0 | 0.00% |
| Broad union | 882 | 5,522 | 79.12% |
| Native plus strict .01 | 876 | 37 | 0.52% |

Seventy-four out-of-source translated locations are explicitly excluded. The
equal-frame average gives each frame equal weight despite different numbers of
valid controls; it is not exactly the pooled-location fraction. Broad control
coverage ranges from 67.60% to 83.65% across episodes. These translated positions
are geometric density controls, not annotated non-ball examples or independent
statistical trials. No significance test or independent generalization claim is
appropriate.

On the 21 original native-missing HOU frames, the broad pool covers all 21 but
also 111/168 translated locations. The narrowed pool covers 15/21 with 0/168
translated hits. Crucially, **all ten e01 recoveries survive in that narrowed
pool with 0/80 translated hits**. That is evidence of localized useful response;
it strengthens the case for preserving this increment. Six e05 correct broad
recoveries fall below .01, which is why the full old-choice stress cohort remains
necessary.

The fixed DET diagnostic covers all nineteen original gap frames with the broad
pool and 91/152 translated locations; the narrowed pool covers two with 0/152
translated hits. These are descriptive results under the locked protocol. They
do not choose a parameter, representation or model. The original broad matching
ceiling remains true, but its density limits how strongly it supports an identity
claim. Neither this ceiling nor the new diagnosis changes DET accuracy or closes
the 317 ms gap.

## Decision after the results

Keep cosine nine, its observed weak candidate evidence and native-selection
comparison. Do not adopt any tested scalar as a veto, undertake another broad
motion/threshold sweep, or extend the unchanged fit. Another objective-only
experiment could alter the positive-emission bias, but the current measurements
do not provide a persuasive visibility signal with which to make that change.
No amount of reward reweighting has been shown here to separate the overlapping
correct and hidden responses.

The [next proposal](ball_tracking_point_feature_feasibility_proposal.md) isolates
one information question: with the same saved image encoder and the same image
input, do spatial features centered on the candidate distinguish useful points
from competing locations and certain-hidden responses better than its old
whole-crop descriptor? Keeping the backbone and crop fixed avoids confounding a
new crop scale, new architecture and new classifier. A token tied to the point
still incorporates surrounding context; it is a hypothesis to test, not proof
of ball identity. This is different from repeating the rejected global DINO veto
and is not a training decision.

Proceed first with source-bound CPU crop/point geometry preparation and a frozen
comparison design. Existing accepted SAC appearance references may supply the
fixed reference bank under their original roles; HOU remains development analysis
without fitting. Preserve native-correct cases, every old weak-choice stress row,
hidden and uncertain cases separately. A later representation result would
justify a bounded choice/absence test only if it improves ordering and useful
hidden separation without paying for it with large native/weak losses. A partial
improvement can justify a focused next variation; missing final acceptance alone
is not grounds to abandon it. A failed representation would reject that setting,
with its failure cases preserved.

There is no claim that final NBA ball tracking is complete. Existing numerical
criteria, data roles, accepted labels, source-uncertain recovery events and human
review requirements are unchanged. Previous complete synchronized trajectory
videos remain available in the weak-response result; no new trajectory is being
submitted for acceptance in this CPU study. Protected evaluation stays closed.

## Subsequent CPU preparation of the proposed image comparison

The [point-feature proposal](ball_tracking_point_feature_feasibility_proposal.md)
now has complete source-bound crop/geometry preparation: 11,798 query records,
10,883 distinct source/crop/tensor inputs, 1,009 PNGs, 41 padded main crops and
eleven missing stress rows. Every unique crop/tensor matches the old producer;
all sixty historical crop/input/CLS artifact bindings and current model/runtime
bytes verify. This checks existing CLS records, not newly computed model outputs.
Seven focused preparation tests pass. Two metadata-transport failures are
preserved before the successful 54.640-second CPU crop pass; neither decoded
source images or ran a model. The corrections keep the geometry unchanged.

Both the preparation agent and root inspected all six fixed geometry sheets.
They show first/middle/last frames, actual point/token locations, missing entries
and padding status; this is sparse AI geometry inspection, not human trajectory
acceptance or new semantic labeling. A separate emitting-manifest audit passes
147,319 checks over all 11,798 queries and 10,883 inputs, including actual HOU
timing/preparation records, historical NBA manifests and NFHS native timestamps.
It independently verifies source/frame/PTS/time-base/duration joins, all 1,009
source PNG byte hashes, exact candidate choices, bank identities and original
roles. It does not rehash/redecode videos or repeat RGB/tensor computation.
No Torch import, model load, descriptor inference or fitting occurred.

One subsequent same-pass comparison would require 10,883 source-specific input
encodings, estimated at 32–38 CPU minutes from historical rates before additional
audit/storage overhead. The input preparation is complete; model comparison
implementation, its execution freeze and the new-inference decision remain
outstanding. Existing raw CLS vectors would be checked with the prospectively
declared tolerances before outcome analysis. Both representations use their own
vectors for the same ten SAC bank identities; bank self-matches are excluded
from checks. No new training is proposed by this step.

## Validation and primary evidence

Twenty-two synthetic focused tests passed before freeze: seven feature/transport,
six analysis and nine geometry/coverage checks. The independent arithmetic helper
also passed its seven synthetic self-checks. No full-suite repeat was needed.
An independent audit checks every actual mean hash and candidate/stress transport,
all 25 boundary unknowns, and 53 deterministic first/middle/last descriptors with
separate scalar interpolation and covariance arithmetic. Maximum absolute
difference is 3.07e-14 (declared tolerances 1e-10 absolute / 1e-9 relative).
This is sampled numerical recomputation, not independent recomputation of all
10,778 descriptor vectors.

The coverage-summary audit passes 100,068 checks of actual emitted distance
decisions, borders, counts, subsets, averages, artifact hashes and chronology.
It does not independently repeat nearest-neighbor search. Synthetic geometry
checks and actual producer pool identity validation cover that boundary. The
analysis explicitly reuses the frozen reference-category kernel; localization
distances and the descriptor arithmetic have separate checks. Independent code
review and per-episode result review found no substantive correctness issue.

Primary ignored evidence under
`data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/`:

- `design_review/saved_hou_objective_accounting.json`: exact saved objective
  accounting and candidate/missing counterfactuals; all 24 HOU objectives match.
- `history/saved_dino_diagnosis_v02.json`: accepted pair ranking/calibration
  distinctions, with original diagnostic attempts preserved.
- `inventory/saved_availability.json`: source/map/cache inventory and exact old
  crop-key provenance; `history/sealed_findings_addendum.txt` records limitations.
- `study_v0_1/prepared.json` and `prospective_freeze.json`: input/source bindings,
  fixed protocol and pre-result chronology.
- `study_v0_1/extraction_complete.json` and six sealed feature JSONLs: complete
  candidate/stress feature transport.
- `study_v0_1/analysis_v0_1/completed.json`: all episode/pooled ranks, bounds,
  stress retention, unknowns and exact source bindings.
- `study_v0_1/spatial_coverage_v0_1/summary.json` and its frame records: complete
  HOU and locked DET density diagnostics.
- `study_v0_1/independent_feature_math_audit.json` and
  `independent_spatial_summary_audit.json`: independent checks with stated scope.

The [compact result ledger](../configs/ball_tracking/reviews/candidate_response_feasibility_result_v0_1.json)
binds these artifacts and records the decision separately from the untouched
prospective recipe. All current work is local and uncommitted, on
`codex/ball-detector-baseline` at `8c040fca385dd8fffa0d7a13c45c53e79950bae1`.
The index remains empty. Original six handoff documents and prior study contents
are preserved through additive context updates; frozen scientific code, recipes,
accepted references, failed attempts and checkpoint recovery history remain intact.
