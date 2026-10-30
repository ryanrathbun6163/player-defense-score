# Candidate-point quality pilot, 2026-10-28

This is a bounded learning experiment prepared for review, not a trained model
or an adopted tracker. The question is: **can image evidence tell whether an
existing candidate is a useful ball location, while preserving good weak and
native points and rejecting unsupported points?** No training or new neural
inference is authorized by this preparation. The previous capture approval is
fulfilled. Execution needs approval for this concrete recipe.

## Evidence reconciled before choosing the recipe

Actual reading/reuse includes the maintained source/authority map, decisions,
validation history, working agreement, current state and roadmap; the completed
[full-history review](research/ball_tracking_full_history_reassessment_2026-10-26.md);
the [capture report](ball_tracking_training_response_capture_results.md), original
accepted package, captured candidate records and audits; the
[candidate-change result](ball_tracking_candidate_change_comparison_results.md),
[point comparison](ball_tracking_point_feature_comparison_results.md), and original
[failed fitted veto](nba_ball_distractor_training_results.md); relevant ball
research/evaluation chapters and source ledgers. We reuse the completed review
of Sessions 1–16 (398 available turns, 47 pages), selected earlier foundation
decisions, previously read complete Session 17/18 handoffs, and subsequent results
in this continuation. This is not a fresh full-transcript or every-paper reread.

The history supports learning candidate-conditioned evidence without establishing
that it will work. WASB adaptation and motion corrections made real gains;
unchanged extensions and the spatial pilot did not resolve the NBA failures.
Weak e01 responses are useful. Point features rank a matching candidate first on
527/882 HOU frames versus CLS 259, but peak reaches 837. Point fails on e01
recovery ranking (3/10 versus CLS 6/10), hidden separation and historical cases.
In the full native-to-narrow comparison, point favors the correct side on 27/34
pairs, but favors both harmful e05/8–9 changes. All 19 shared native hidden
emissions and eight added hidden emissions remain unresolved. The old frozen
CLS logistic veto removed 207/581 correct points. None of that evidence is erased
by testing a different learning recipe.

Fresh primary reading reopened Van Zandycke and De Vleeschouwer's
[basketball candidate-crop study](https://arxiv.org/html/2204.00003), particularly
sections 2.2 and 4. Its implementation uses ImageNet-pretrained VGG16, not a tiny
network learned from scratch. Its principal training balls are 14–37 pixels and
its camera/data conditions differ from these NBA broadcasts. It supports the
possibility of learned candidate-centered image evidence, not the performance
of this DINO recipe or a transfer of semantic presence labels to our geometric
targets. No external weights, repository or dataset was imported.

The chosen change adapts spatial image features; it does not repeat the old
classifier on frozen global descriptors. A small CNN from scratch, separate
presence learning, wider context, joint temporal evidence, or a materially
different detector remain open. Partial adaptation of the existing pinned model
is the most attributable first test: it preserves the useful point/crop contract,
needs no new model acquisition, and limits the trainable portion. The exact
layer count, rates and six-epoch budget are declared engineering choices,
not settings proven optimal by research or selected from HOU outcomes.

## Supervision and all-case coverage

Keep all 26 captured training blocks, 3,329 frames and 19,632 candidates in the
manifest. All 21 empty frames remain records; no image or point is invented for
them. NBA fitting uses only CHI–IND, DEN–BOS and SAC–MEM. Historical NFHS remains
secondary scoring evidence and does not choose this NBA recipe.

| NBA candidate target | Count | Fitting meaning |
| --- | ---: | --- |
| Accepted-coordinate match | 3,433 | In source bounds, distance at most 10 source pixels; 2,823 native and 610 weak |
| Clearly distant eligible point | 13,776 | Distance greater than 10 plus recorded placement radius |
| Certain-hidden point | 315 | Existing candidate in a certainly hidden frame |
| Near-boundary miss | 65 | Unknown for fitting: 10 < distance <= 10 plus placement radius |
| Masked reference | 1,224 | Unknown for fitting, regardless of appearance |

Thus the all-NBA fit uses 17,524 candidates. All 241 masked frames / 1,228
candidates across NBA and NFHS remain unknown; the complete inventory also keeps
70 near-boundary misses. No new semantic object labels are created. A wrong
coordinate can still lie inside a crop containing the actual ball.

The asymmetric uncertainty mask retains accepted <=10 positives and excludes
only ambiguous negative targets. Requiring distance plus radius <=10 would
discard 294/674 matching weak examples, including 128/177 SAC examples, and leave
453/2,941 eligible frames without a positive. That would systematically remove
difficult evidence we intend to protect. A placement radius is not a confidence
interval or a probability distribution. Evaluation keeps the original inclusive
10-pixel rule and eligibility; fitting masks do not weaken those rules.

The captured 674 weak matches are mostly alternatives to success: 673 accompany
an already-correct native selection, one covers CHI e02/frame 83 native missing,
and none fixes the three native-wrong frames. They are not 674 recoveries.
The .01 pool is not exhaustive, and a scorer cannot recover a missing candidate.
Temporally adjacent examples remain correlated even when their frame IDs differ.

Use a single binary cross-entropy objective for usable-point quality. Allocate
half the objective weight to positives, one quarter to distant visible-frame
misses and one quarter to certain-hidden candidates. Within each stratum divide
weight equally by available game, block, frame, nonempty native/weak origin and
then candidate. This limits domination by dense negative pools and gives weak
positives explicit representation. Absent child groups share mass among present
siblings; a globally absent required stratum is an error. All fitting candidates
are visited once per epoch, with deterministic shuffled order. Minibatch loss is
the mean of BCE times N*objective_weight. These are objective weights, not
population probabilities; unequal weights and clipping can increase gradient
variance, which the logged batch losses/norms will expose.

## Fixed image model and learning recipe

Use the existing pinned DINOv2 ViT-S/14 without registers, revision
`150c8e7bb7cef2d30ec31b13a517af14840ee3f7`. Preserve the 64-source-pixel crop,
floor-center placement, black padding, bicubic resize to 256, center crop to
224 and original RGB normalization. Its effective field is 56 source pixels.
Upsampling adds no lost detail. Preserve each fractional candidate coordinate:
interpolate the four final normalized spatial tokens in float64, L2-normalize
once, then cast that vector to float32 for the new head. Never normalize each
patch before interpolation. Self-attention still mixes context throughout the
crop; this is point conditioning, not an isolated-pixel detector.

Freeze the embeddings and first ten transformer blocks. Adapt the final two
blocks and final LayerNorm, followed by a 384 → 128 → 1 head with GELU. There are
3,600,641 trainable parameters. No CLS, peak response, source/game identity,
previous trajectory or reference-bank similarity is supplied to the head.
The frozen prefix remains in evaluation mode with no gradients. The pinned
configuration has no dropout or stochastic depth. Original model files and
WASB/cosine-nine parameters never change.

Use AdamW, backbone learning rate 0.00001, head rate 0.001, weight decay 0.01,
betas (0.9, 0.999), epsilon 1e-8, norm clipping at 1.0, batch size 32 and six
epochs. Use seed 20261028 for each fresh identical initialization and seed plus
epoch for the candidate permutation. PyTorch Linear initialization is retained.
Use float32 model/optimizer computation, the specified float64 readout, eager
attention, deterministic algorithms, no AMP/TF32, no augmentation, no scheduler,
no sweep and no automatic extension. A short run may underfit; that is a limit,
not a reason to silently add epochs. Only epoch six is the comparison checkpoint.
Earlier epoch online losses describe learning progress, not validation results.

## Four fits with distinct purposes

| Fit | Fitting candidates | Updates over six epochs | Score after the final epoch |
| --- | ---: | ---: | --- |
| Leave CHI out | 11,954 | 2,244 | All 5,935 CHI candidates |
| Leave DEN out | 11,912 | 2,238 | All 5,790 DEN candidates |
| Leave SAC out | 11,182 | 2,100 | All 7,088 SAC candidates |
| All three NBA games | 17,524 | 3,288 | All package candidates, HOU and the original historical checks |

These are four copies of one recipe, not four competing settings or an ensemble.
No result from an earlier fit changes a later fit. Source games are separated
for the NEW scorer only: cosine nine already trained on all three and produced
these pools. The folds do not establish end-to-end unseen-game generalization.
Report the all-NBA fit's in-sample scores separately from each game's out-of-fold
scores; never average the two as validation.

HOU is repeatedly exposed development, excluded from fitting and threshold
selection. Score the full 11,798 existing query registry: 10,778 HOU pool points,
960 broad-choice stress slots (949 emitted, 11 missing), and 60 historical cases.
Those include 18 original DET appearance cases; they are fixed post-fit
diagnostics only and choose no architecture, weights, thresholds or checkpoint.
Historical semantic/AI judgments stay separate from accepted coordinate targets;
the old ten reference-bank entries do not become independent check cases.
No new DET frames or protected-evaluation data are requested.

## Measurements and how they inform the next decision

Save every score and join back to the full inventory before summarizing:

- Per game, episode, native/weak origin, visibility, target kind and uncertainty:
  matching-point ranking, positive retention, distant-miss survival and
  certain-hidden frame survival. Keep empty and masked frames in denominators
  appropriate to their original roles; never count unknown as wrong or negative.
- For HOU retain all 960 frames: 882 eligible, 34 certain-hidden, 14 indeterminate,
  eight uncertain-hidden and 22 visible-unlocalizable. Rejoin all seven old arms,
  6,720 choice slots and 6,720 declared contrasts, including agreements, unchanged
  errors, both-missing cases and unavailable comparisons.
- Preserve overlapping adverse/useful subsets: the ten e01 recoveries, all six
  below-.01 e05 gains, 21 old broad gains, 842 native-correct points, the original
  six-gain/27-loss tags, e05/8–9 failures, e05/206 increment, and shared/added
  hidden emissions. These tags explain results; they never filter inclusion.
- Compare with saved peak, point and CLS controls. Report strict ranks, ties,
  missing-state comparisons, per-episode tables and complete score breakpoints.
  A fixed zero-logit reference gives a declared rejection comparison: >0 survives,
  =0 is a tie. Missing has no image score; zero is only its comparison reference.
  No threshold is fitted to HOU or selected from the diagnostic curves, and no
  new emitted point or trajectory is constructed.
- Log weighted online loss by target stratum, gradient norms, exact update/call
  counts, trainable-tensor changes and frozen-tensor parity. A failed runtime or
  non-learning model is an implementation/training-health result, not evidence
  that all image recognition fails.

Useful separation that transfers across the declared folds and preserves the
native/weak evidence in HOU would support a later, separately specified integration
decision. Success confined to fitted games would expose scene dependence.
Improved ordering with failed hidden rejection would separate recognition value
from an unresolved visibility problem. Good fits but no useful full-data
retention/rejection tradeoff would argue against this concrete crop/recipe,
without rejecting wider context, presence or temporal methods. Any headline gain
must show its correct-point losses and adverse subsets next to it. Existing
numerical acceptance and human visual-review gates remain unchanged; none of
these diagnostic outcomes alone adopts a model or finishes NBA ball tracking.

## Execution boundary and practical budget

The fixed budget is 9,870 optimizer updates and 315,432 fitting candidate
presentations, plus 50,232 post-fit candidate scores. Four runtime
producer/consumer parity forwards add 128 candidate presentations: 11,446 neural
forwards and 365,792 candidate presentations overall. The first actual batch of
each fit is checked against the standard pinned producer and original point
consumer at absolute/relative tolerance 1e-10, before its first update. Finite,
nonzero gradients must reach both the head and adapted backbone.
This is unbenchmarked on the GPU: no honest precise completion time or measured
peak memory is available. A one-hour supervised attempt limit bounds the
requested expenditure; it is not a prediction that training needs an hour or
that all fits will finish. A stop preserves partial results and never retries or
changes the batch size automatically.

Native uint8 crop caches are about 386 MB in total; four final trainable-parameter
checkpoints about 58 MB. Recovery checkpoints at each completed epoch also retain
optimizer and RNG state, about 1.04 GB across all 24 epochs. These support a later
explicit continuation without discarding completed work; they are not scored or
used to select an epoch, and no automatic resume is implemented. Total expected
generated storage is roughly 1.5 GB plus manifests, score files and journals.
The frozen prefix avoids storing its training activations, but GPU memory and
throughput still require measurement during the approved attempt. No additional
benchmark, model download or model sweep is included.

Reuse the existing owned Windows-job GPU supervisor: two-second telemetry,
80 C/device/thermal stop, owned-process cleanup, and no automatic retry. Recheck
readiness, temporary graphics isolation, runtime and frozen bindings immediately
before launch. Prior device-loss events and both reboots remain evidence;
the successful 55 C capture does not prove the graphics fault is cured.
No driver, startup, fan or clock setting changes are part of this work.

Implementation and CPU preparation/test results are recorded in the
[proposal](../configs/ball_tracking/proposals/candidate_quality_pilot_v0_1.json)
and ignored `data/outputs/ball_tracking/candidate_quality_pilot_v0_1/` receipts.
Neural forward/backward execution, actual GPU memory/time and scientific outcomes
remain untested until the specific new execution is approved. No staging,
committing, publication, new labels, selector or protected access follows.
