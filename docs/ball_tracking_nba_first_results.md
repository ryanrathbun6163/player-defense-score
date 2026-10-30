# NBA-first saved-model results

Completed October 25, 2026, America/Phoenix (October 26 UTC).

## Outcome

The [authorized NBA-first comparison](ball_tracking_nba_first_evaluation.md)
evaluated all **12 saved WASB models** on the same existing NBA evidence. **None
passes the unchanged ball-quality criteria.** No fitting or new labeling ran.
High-school work, historical rejection decisions and protected evaluation remain
unchanged. No candidate is adopted.

Augmentation epoch five has the highest correct-position count on the target
Spurs-Pistons development context: **212/241 (88.0%)**, versus the retained
baseline's **209/241 (86.7%)**. Wrong eligible outputs fall from eight to five;
both leave 24 eligible frames missing. The improvement is nine gains and six
losses, not uniformly better tracking. The same 317ms missing run remains, and
emissions on probable-hidden references increase from 13 to 20. These latter
references remain uncertain; they are review flags, not relabeled certain-hidden
violations. The target's unchanged count gates require at least 229 correct and
at most two wrong outputs, in addition to all temporal and visual requirements.

The more favorable HOU-OKC aggregate does not override failures in individual
episodes. Highest HOU coverage is augmentation epoch three, 854/882 (96.8%),
but that model has nine wrong and 22 certain-hidden emissions; on DET it gives
206/241 with 13 wrong and 30 probable-hidden emissions. NBA-first does not make
that model a passing tracker.

## Complete comparison

All rows use strict >0.3 heatmaps, the original 512x288 preprocessing, exact
native triplet means, component-mass selection and inclusive ten-source-pixel
matching. HOU contains 882 eligible references in six episodes/960 total frames.
DET contains 241 eligible references in 344 labeled frames within its original
1,231-frame context. This includes the four later accepted DET gap labels; older
237-center reports retain their original denominator and must not be conflated.

| Saved model | HOU correct /882 | HOU wrong | HOU certain-hidden emissions | DET correct /241 | DET wrong | DET probable-hidden emissions | SAC correct /270 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Retained baseline | 845 | 29 | 25 | 209 | 8 | 13 | 218 |
| Original epoch 1 | 837 | 34 | 19 | 207 | 10 | 27 | 266 |
| Original epoch 2 | 850 | 9 | 16 | 204 | 5 | 12 | 269 |
| Original epoch 3 | 842 | 4 | 15 | 197 | 1 | 1 | 269 |
| Original epoch 4 | 850 | 8 | 11 | 202 | 15 | 22 | 269 |
| Original epoch 5 | 848 | 9 | 17 | 204 | 9 | 21 | 269 |
| Augmentation epoch 1 | 846 | 17 | 16 | 206 | 13 | 32 | 260 |
| Augmentation epoch 2 | 849 | 4 | 19 | 208 | 6 | 15 | 264 |
| Augmentation epoch 3 | 854 | 9 | 22 | 206 | 13 | 30 | 270 |
| Augmentation epoch 4 | 844 | 3 | 17 | 208 | 6 | 17 | 270 |
| Augmentation epoch 5 | 844 | 3 | 17 | 212 | 5 | 20 | 270 |
| Earlier NBA 200-update fit | 846 | 27 | 27 | 206 | 10 | 9 | 265 |

SAC is descriptive training-fit evidence for the NBA-fitted models. Its 303
reference rows include 300 directly fitted historical rows and three same-game
development additions; 270 have eligible centers. Its near-perfect fitted
results do not certify target-game transfer. HOU never enters gradient fitting,
but was repeatedly used for checkpoint selection. DET is fitting-excluded,
already inspected development data. Neither is a fresh independent test.
The 2,879 new NBA training judgments were not repurposed as validation. The
retained baseline's training exposure remains NFHS-only. These are selected
episodes and sparsely labeled contexts, not complete NBA possessions or games.

## Candidate chosen for review, not adoption

Augmentation epoch five is chosen for the single complete eight-context review
because it offers the highest observed target-game localization count with
fewer wrong eligible positions than the retained model. This is a post-comparison
development choice, not a frozen-method test or automatic replacement. The
saved [review inputs](../data/outputs/ball_tracking/nba_first_v0_1/review_inputs_v0_1.json)
bind all native frames, both models and the completed evaluation.

The [results and review page](../data/outputs/ball_tracking/nba_first_v0_1/index.html)
links the [complete eight synchronized comparisons](../data/outputs/ball_tracking/nba_first_v0_1/augmentation_epoch5_review_v0_1/attempts/9fa05674608d46439acc2bb832c92e40/index.html).
All 3,662 frames pass native presentation, encoded frame-key and final-duration
checks. Rendering completed in 358.031s on its first attempt. AI visual QA
inspected all actual finals: DET11898, HOU239/119/239/269/239/449 and SAC2010.
The two highlighted [DET11476](../data/outputs/ball_tracking/nba_first_v0_1/review_priority_frames/det_11476.png)
and [DET11514](../data/outputs/ball_tracking/nba_first_v0_1/review_priority_frames/det_11514.png)
frames visibly place the new point in the spectator/bench area while the
baseline stays near the accepted ball center. These are AI inspection notes;
formal human trajectory/object-identity acceptance is still pending. The
"selected model" canvas label means selected for this review, not adopted.

Its HOU pooled count is only one lower than baseline, but that hides important
episode regressions. Episode e01 falls from 107 to 99 correct and develops a
267ms missing run; e03 falls from 98 to 95. In contrast e02 and e04 become
120/120, and e06 reaches 212/212 eligible locations while still emitting on
twelve certain-hidden frames. Correct visible-ball counts are insufficient.

Specific review priorities, all using existing accepted references:

- DET 11460-11514: new probable-hidden emissions and new errors at 11476
  (about 660px) and 11514 (about 945px), where baseline had matched. Large
  geometric errors flag review; they do not automatically establish object identity.
- DET 11075-11093: the unchanged 317ms missing run; frame 11101 becomes a
  marginal 10.276px wrong output under the unchanged ten-pixel rule.
- DET 11542-11562: gains at 11542 and 11557-11558, with residual errors at
  11561-11562. Frames 11504, 11722 and 11725 are newly missing.
- HOU e01 160-205: increased missingness around hand/ball overlap.
- HOU e06 210-245: certain-hidden output despite excellent visible-ball counts.

The proper next decision is about these visibility, partial-ball localization
and distractor failures. This evidence does not justify extending the same fit
simply because training is iterative. Any next training experiment should target
a measured failure and be judged on the same NBA evidence roles and quality bar.
Protected evaluation remains closed pending method freeze and separate authority.

## Execution and verification

The new comparison completed on its first supervised attempt: **27,928 forward
calls, zero optimizer updates, zero new labels**, 720.468s in the runner and
725.078s under supervision. It reused **15,964** original observations and emitted
**43,944** model/frame observations across 96 model/context pairs. GPU telemetry
has 353 samples: peak **58 C, 107.94 W, 2,611 MiB**, no device/thermal stop,
no forced termination and zero remaining owned processes. The graphics extras
were stopped before execution; this does not establish a PC-stability cure.

Thirty-four focused checks pass: seventeen new analyzer/inference/review checks
plus seventeen existing completion-scoring checks. Real source preprocessing is
byte-equal on 24 first/middle/final triplets. The real saved validation reader
reproduces all original geometric counts; clipped context boundaries are now
explicitly censored using the unchanged metric kernel. Unknown labels remain
unknown, and no recovery is invented across episodes. A Windows mmap cleanup
error in an initial synthetic test fixture was corrected; no scientific run failed.

The [independent audit](../data/outputs/t/nba_first_inventory_20261026/final_audit_20261026T023210817446Z.json)
passes **705,822 checks with zero discrepancies**. It independently checks all
43,944 rows, native times, component selection, raw geometry, hidden-output
counts, integer gates, 96 receipt links, complete published summaries and
validation aggregates. It reconstructs every new mean's strict-threshold
components (27,980 maps), checks all 15,964 reused original observations, and
verifies frozen code/reference/model bindings and monitor cleanup. Its own
earlier metadata lookup/category-count corrections remain preserved separately.

Primary evidence:

- [Frozen NBA-first scope](../configs/ball_tracking/proposals/nba_first_saved_models_v0_1.json), SHA `63e82b178b46fd1f5bd20d8d7777b05c594968133d545ff072b0fcd33a6345f9`.
- [Completed model comparison](../data/outputs/ball_tracking/nba_first_v0_1/comparison_v0_1/completed.json) and [all model/episode results](../data/outputs/ball_tracking/nba_first_v0_1/comparison_v0_1/evaluation.json).
- [Saved-only eleven-model HOU analysis](../data/outputs/ball_tracking/nba_first_v0_1/saved_validation_analysis_v0_1/completed.json).
- [GPU completion](../data/outputs/ball_tracking/nba_first_v0_1/monitoring/attempt_001/finished.json).
- Independent audit SHA `8b2ca290ce504c45fbbefb56bb3bb362f6912df6c37c6bb99bec596b1ddea63f`.

All new human trajectory judgments remain pending. All original high-school
labels, reviewed outputs, frozen recipes, failed fits and recovery history are
preserved. No additional training, holdout opening or model promotion follows
automatically from this report.

## Subsequent diagnosis and visual clarification, 2026-10-25

The [later diagnosis](ball_tracking_nba_failure_diagnosis.md) preserves this
comparison and its original AI notes. Full native inspection locates the far
selected points at DET11476/11514 on a standing sideline official's head,
clarifying the earlier spectator/bench-area description. Formal human visual
acceptance is still pending. The later original-weight control and recommended
resolution experiment do not change these historical results or adopt a model.
