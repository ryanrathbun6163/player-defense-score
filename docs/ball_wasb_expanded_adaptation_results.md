# Expanded WASB training: development results and visual review

Recorded 2026-10-08. The approved additional 75 labels, human label review, single
200-update fit and six-window comparison are complete. New model-output visual
review is pending. No operating point or phase quality gate is promoted.

**The additional training data helped.** At the unchanged primary threshold of
0.5, correct positions increased from **98 to 120 of 145 eligible frames**, while
missing positions fell from **46 to 23**. Geometric errors increased from one to
two; both are small center offsets just outside the unchanged ten-pixel scoring
radius. There were no alarms on the five reviewed hidden frames.

P001 improved from **11 to 34 matches out of 50**, supplying all 23 newly matched
frames. One previously matched frame, P002/48, became missing. P003's primary
match/missing classifications were unchanged. This answers the expanded-data
experiment positively, but does not yet establish complete reliable trajectories.

## Primary comparison

Matched, wrong and missing partition the 145 eligible frames. Hidden alarms are
counted separately on five hidden frames. All rows use the same reviewed labels
and ten-pixel rule.

| Method | Matched | Wrong | Missing | Hidden alarms |
| --- | ---: | ---: | ---: | ---: |
| Original pretrained WASB, 0.5 | 31 | 0 | 114 | 0 |
| First 75-frame fit, 0.5 | 98 | 1 | 46 | 0 |
| **Expanded 150-frame fit, 0.5** | **120** | **2** | **23** | **0** |
| Saved RF ranked to expanded output count | 99 | 23 | 23 | 0 |
| Saved RF baseline at confidence 0.01 | 111 | 34 | 0 | 5 |

The equal-count RF row keeps its highest native-confidence top-one observations
separately in each development pool, matching the expanded model's total output
count. It is a post-hoc ranking diagnostic, not a deployable threshold. Relative
to unrestricted RF, expanded WASB gains 22 matches, loses 13 and shares 98.

Each cell below is **matched / wrong / missing**. Only P003 challenge includes
hidden frames; all WASB columns shown have zero hidden alarms there.

| Window | Frames | First fit, 0.5 | Expanded, 0.5 | Expanded candidate, 0.3 |
| --- | --- | ---: | ---: | ---: |
| P001 representative | 50–74 | 0 / 0 / 25 | 22 / 1 / 2 | 25 / 0 / 0 |
| P001 challenge | 200–224 | 11 / 0 / 14 | 12 / 0 / 13 | 16 / 0 / 9 |
| P002 representative | 250–274 | 25 / 0 / 0 | 25 / 0 / 0 | 25 / 0 / 0 |
| P002 challenge | 25–49 | 24 / 0 / 1 | 23 / 0 / 2 | 24 / 0 / 1 |
| P003 representative | 300–324 | 20 / 0 / 5 | 20 / 0 / 5 | 21 / 0 / 4 |
| P003 challenge | 150–174 | 18 / 1 / 1 | 18 / 1 / 1 | 19 / 1 / 0 |

At primary 0.5, missing frames are P001/64–65, 206–209 and 216–224;
P002/48–49; P003/300–304 and 170. The two geometric failures are P001/52 at
10.368 source pixels and P003/164 at 10.972 pixels. Both labels have 3.833-pixel
center uncertainty; the scoring rule is unchanged. Neither distance alone proves
the model chose a different physical object. Existing labels and reviews stand.

## Existing threshold grid and next review candidate

All eight thresholds were declared before this fit and applied to its saved
heatmaps. No additional model run or new threshold search was used. Cells are
**matched / wrong / missing / hidden alarms**.

| Threshold | First fit | Expanded fit |
| ---: | ---: | ---: |
| 0.01 | 26 / 119 / 0 / 5 | 22 / 123 / 0 / 5 |
| 0.025 | 59 / 86 / 0 / 5 | 71 / 74 / 0 / 5 |
| 0.05 | 85 / 60 / 0 / 5 | 117 / 28 / 0 / 5 |
| 0.10 | 98 / 46 / 1 / 2 | 128 / 17 / 0 / 4 |
| 0.20 | 103 / 13 / 29 / 0 | 132 / 4 / 9 / 0 |
| **0.30, review candidate** | **100 / 6 / 39 / 0** | **130 / 1 / 14 / 0** |
| 0.40 | 98 / 2 / 45 / 0 | 125 / 1 / 19 / 0 |
| **0.50, predeclared primary** | **98 / 1 / 46 / 0** | **120 / 2 / 23 / 0** |

The 0.3 candidate retains every one of the 120 primary matches and adds ten:
P001/52, 64, 65, 206, 207, 209, 216; P002/48; P003/304 and 170. Thus it corrects
the new P001/52 geometric error and restores P002/48. Its sole geometric failure
is P003/164. Remaining gaps are P001/208 and 217–224, P002/49 and P003/300–303.

**Review this existing candidate before adding more training or motion rules.**
It has better measured coverage and fewer errors on these development windows.
It is selected for review after seeing development results, so it must not replace
the declared primary result or be described as independent validation.

## Six new clips for Ryan's review

These clips display the **0.3 review candidate**, checkpoint `09da1214e94f`.
Each contains all 25 source frames, slowed to five seconds, and was decoded through
its final frame. Green marks the reviewed center, magenta the candidate WASB
position, and yellow the saved RF top-one position. White player labels reuse the
reviewed player identities. Heatmap mass is not a probability.

| Possession | Representative clip | Challenge clip |
| --- | --- | --- |
| P001 | [Frames 50–74](../data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/review_threshold_0_3/possession_001_frames_0050_0074_representative_evaluation_development_v0_2/candidate_review.mp4) | [Frames 200–224](../data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/review_threshold_0_3/possession_001_frames_0200_0224_challenge_evaluation_development_v0_2/candidate_review.mp4) |
| P002 | [Frames 250–274](../data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/review_threshold_0_3/possession_002_frames_0250_0274_representative_evaluation_development_v0_2/candidate_review.mp4) | [Frames 25–49](../data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/review_threshold_0_3/possession_002_frames_0025_0049_challenge_evaluation_development_v0_2/candidate_review.mp4) |
| P003 | [Frames 300–324](../data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/review_threshold_0_3/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/candidate_review.mp4) | [Frames 150–174](../data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/review_threshold_0_3/possession_003_frames_0150_0174_challenge_evaluation_development_v0_2/candidate_review.mp4) |

Check the previously missed P001 sequence, remaining gaps and the P003 transition
behind the referee. Report any wrong physical-ball selection or problematic return
after occlusion, with possession/frame IDs. These are new model outputs; the prior
six model-output reviews and three new-label reviews remain completed.

Primary 0.5 videos are preserved under each window in `evaluation/`, named
`adapted_review.mp4`. Diagnostic stills compare the two models at
[P001/52](../data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/diagnostics/selected_frames/possession_001_frame_000052_comparison.png),
[P002/48](../data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/diagnostics/selected_frames/possession_002_frame_000048_comparison.png)
and [P003/164](../data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/diagnostics/selected_frames/possession_003_frame_000164_comparison.png).
Those stills explicitly show 0.5, not the 0.3 candidate.

## Execution and limits

Ryan approved the 75-frame addition and then accepted all three completed label
clips. The new 150-frame training set contains 130 positive centers, 19 hidden
negatives and one masked ambiguous frame. Its five blocks produce 140 complete
triplets, including the two crossing P002's former 342/343 annotation boundary.
The original six annotation authorities remain separate.

One fit started from the same original pretrained checkpoint, using 200 updates,
batch two, seed 1234, Adam 0.0001, float32, frozen BatchNorm running buffers and
the original target/loss/mask rules. No augmentation, mining or evaluation-driven
checkpoint selection was added. The 400 sampled triplets comprise cycles of
140, 140 and 120. Fixed compute changes per-scene exposure; it does not isolate
appearance, position or any single added training window as the cause.

Training completed without retry in 24.346 seconds, using 1.87 GiB peak allocated
GPU memory and about 945 MiB of cached CPU tensors. Evaluation including cached
calibration took 32.714 seconds; primary rendering 12.630 seconds and candidate
rendering 9.315 seconds. Seventeen focused checks passed before execution. No
full test suite was run. Independent audits reconciled actual checkpoint tensors,
sampling, reports, control bindings and successful completion records.

These repeatedly inspected clips come from the same game. They establish useful
development improvement, not generalization to other games or complete possession
tracking. Fourteen candidate gaps, one geometric error, human output review and
full-possession trajectories remain unresolved. Holdouts were not accessed.
No further training fit or operating-point promotion is implied by this report.

## Evidence

- [Frozen experiment config](../configs/ball_tracking/wasb_experiments/wasb_basketball_expanded_adaptation_v0_1.json).
- [Completed human label review](../configs/ball_tracking/reviews/wasb_training_expansion_label_review_v0_1.json).
- [Training completion](../data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/training/completion.json).
- [Comparison with first adapted model](../data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/prior_adapted_comparison.json) and [pretrained model](../data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/comparison.json).
- [Independent numerical audit](../data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/diagnostics/independent_evaluation_audit_v0_1.json).
- [Candidate review manifest](../data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/review_threshold_0_3/review_manifest.json).

Implementation commit: `3928f7fee7f6e41eb3ffa05b0db062b176442e6e`.
Final checkpoint SHA-256:
`09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`.
All generated videos, model outputs and source footage remain uncommitted.

A subsequent [longer development observation](ball_wasb_development_observation.md)
uses the same checkpoint and 0.3 candidate on the non-holdout segments of all
three possessions. Its unlabeled timelines support gap/distractor review and
include training frames; they do not replace any metric in this report.
