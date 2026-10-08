# WASB pilot adaptation: development results

Recorded 2026-10-08. Training and the six-window development evaluation completed. Human synchronized visual review remains pending. No operating point or quality gate has been promoted.

The approved 200-update trial substantially improved the pretrained WASB result at the predeclared heatmap threshold of 0.5: **98 matched frames, one wrong observation, 46 eligible missing frames and no hidden-frame alarms**. Pretrained WASB had 31 matches, no wrong observations and 114 missing frames under the same policy. Adaptation retained every original match and added 67.

At the same number of emitted observations, the saved RF control has 90 matches and nine wrong observations. This is useful same-game development evidence for adaptation. It does not establish reliable complete trajectories: possession 001 still accounts for 39 of the 46 missing frames, including an entire 25-frame window with no output.

## What was trained and evaluated

The [approved plan](ball_wasb_adaptation_plan.md) and `configs/ball_tracking/wasb_experiments/wasb_basketball_adaptation_v0_1.json` define one final checkpoint, selected at update 200 without evaluation-driven early stopping or a checkpoint search.

Training used the three disjoint reviewed pilot windows: P001 frames 375–399, P002 frames 318–342 and P003 frames 416–440. Their 75 frames contain 66 eligible coordinate targets, eight certain hidden negatives and one ambiguous frame, P002 frame 335. The ambiguous output channel was masked; its image remained available as temporal context. The eight negatives are two P002 occlusion episodes. There are no out-of-frame training negatives. The 66 coordinate targets include 12 fully visible and 54 partially visible/amodal centers.

The preset made all 1,481,427 parameters trainable using Adam at learning rate 0.0001, batch size two, seed 1234 and exactly 200 updates. All 176 active parameter tensors changed; 39 tensors belong to upstream branches unused by the configured scale-zero output. The training audit confirmed all 213 BatchNorm running buffers remained unchanged. The 69 complete pilot triplets were sampled through a frozen 400-ID schedule. Training targets retained the official binary disk and affine integer-center conventions; no data augmentation, pseudo-labeling or false-positive mining was used.

Evaluation reused the same six development windows, reviewed labels, saved RF candidates and measurement rules as the [transfer comparison](ball_wasb_transfer_results.md). Each 25-frame window contains 23 complete chronological triplets. Aligned heatmaps are averaged only within that window, with contributions `1, 2, 3, ..., 3, 2, 1`. The primary policy is strict heatmap `> 0.5`, official connected components, weighted centers and highest native component mass. Matching uses a 10-source-pixel radius; reports also retain 5, 15, 20 and 30 pixels. Native component mass is not a probability.

The trial adds no tracker, interpolation, player/court inference input or external temporal context. Training/evaluation frames do not overlap. Existing labels, prior outputs, failed attempts and sealed holdouts remain preserved.

## Primary results by pool

Matched, wrong and missing partition eligible frames. Hidden alarms are separate. The RF equal-count diagnostic selects its strongest saved top-one confidences separately within each pool, retaining the same number of emitted frames as adapted WASB. Its ranking does not use labels, but its count is defined post hoc from WASB output; it is not a deployable RF threshold.

| Pool / method | Eligible | Matched | Wrong | Missing | Hidden alarms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Representative: pretrained WASB | 75 | 17 | 0 | 58 | 0 |
| Representative: adapted WASB | 75 | 45 | 0 | 30 | 0 |
| Representative: equal-count RF | 75 | 40 | 5 | 30 | 0 |
| Challenge: pretrained WASB | 70 | 14 | 0 | 56 | 0 / 5 |
| Challenge: adapted WASB | 70 | 53 | 1 | 16 | 0 / 5 |
| Challenge: equal-count RF | 70 | 50 | 4 | 16 | 0 / 5 |

Across both pools, adapted WASB emits 99 observations: 98 match and one is wrong. Equal-count RF emits 99: 90 match and nine are wrong. These observations occur on partly different frames: adaptation gains 19 matches and loses 11 relative to that RF subset, with 79 shared matches.

The unrestricted saved RF control at confidence 0.01 still has more total matches: 111, with 34 wrong observations, no eligible missing frames and five hidden alarms. Against that control, adapted WASB gains nine matches and loses 22, with 89 shared matches. This comparison exposes the coverage/error tradeoff rather than claiming that every RF capability has been replaced.

## Primary results by window

Each triple is **matched / wrong / eligible missing**. Frame ranges are inclusive source indices. Only P003 challenge contains hidden frames; both WASB models have zero alarms there at threshold 0.5.

| Possession / pool | Frames | Pretrained WASB | Adapted WASB | Saved RF at 0.01 | Adapted gains / losses versus RF |
| --- | --- | ---: | ---: | ---: | ---: |
| P001 representative | 50–74 | 0 / 0 / 25 | 0 / 0 / 25 | 8 / 17 / 0 | 0 / 8 |
| P001 challenge | 200–224 | 1 / 0 / 24 | 11 / 0 / 14 | 20 / 5 / 0 | 2 / 11 |
| P002 representative | 250–274 | 15 / 0 / 10 | 25 / 0 / 0 | 20 / 5 / 0 | 5 / 0 |
| P002 challenge | 25–49 | 13 / 0 / 12 | 24 / 0 / 1 | 23 / 2 / 0 | 1 / 0 |
| P003 representative | 300–324 | 2 / 0 / 23 | 20 / 0 / 5 | 23 / 2 / 0 | 0 / 3 |
| P003 challenge | 150–174 | 0 / 0 / 20 | 18 / 1 / 1 | 17 / 3 / 0 | 1 / 0 |

The nine RF failures recovered by adapted WASB are P001 frames 204 and 210; P002 representative frames 257–261; P002 challenge frame 48; and P003 challenge frame 173. These are geometric matches to the existing reviewed annotations, not a new independent physical-identity judgment.

## Fixed eight-threshold screen

The complete predeclared grid was applied to saved final-checkpoint heatmaps without another inference pass. No threshold was added after seeing adaptation outcomes. The pretrained column reuses the completed calibration evidence.

Each cell is **matched / wrong / eligible missing / hidden alarms**. Equal-count RF includes hidden-frame emissions when determining the retained count, so equal total emissions need not mean equal eligible-frame coverage.

| Heatmap threshold | Pretrained WASB | Adapted WASB | RF at adapted output count |
| ---: | ---: | ---: | ---: |
| 0.01 | 36 / 109 / 0 / 5 | 26 / 119 / 0 / 5 | 111 / 34 / 0 / 5 |
| 0.025 | 69 / 76 / 0 / 5 | 59 / 86 / 0 / 5 | 111 / 34 / 0 / 5 |
| 0.05 | 75 / 41 / 29 / 5 | 85 / 60 / 0 / 5 | 111 / 34 / 0 / 5 |
| 0.10 | 70 / 5 / 70 / 0 | 98 / 46 / 1 / 2 | 110 / 33 / 2 / 3 |
| 0.20 | 62 / 0 / 83 / 0 | 103 / 13 / 29 / 0 | 100 / 15 / 30 / 1 |
| 0.30 | 54 / 1 / 90 / 0 | 100 / 6 / 39 / 0 | 96 / 9 / 40 / 1 |
| 0.40 | 42 / 0 / 103 / 0 | 98 / 2 / 45 / 0 | 91 / 9 / 45 / 0 |
| **0.50, predeclared primary** | **31 / 0 / 114 / 0** | **98 / 1 / 46 / 0** | **90 / 9 / 46 / 0** |

Training changes the output distribution as well as locations: the very low thresholds become worse, and lowering the adapted threshold admits substantial error. The primary 0.5 result demonstrates a useful development improvement without searching for a new primary threshold. These observations do not separate every effect of learned localization from confidence calibration, nor do they certify an operating point.

Raw candidate availability also improves: across the fixed grid, adapted WASB contains a candidate within ten pixels of the reviewed center on at most 133/145 eligible frames (threshold 0.05), compared with a maximum of 85 for pretrained WASB (0.025) and 140 for saved RF candidates. This diagnostic uses labels to determine whether any candidate could be correct; it does not mean the model selects that candidate. At the primary 0.5 threshold, adapted raw availability and selected matches are both 98. Per-window raw counts remain in the cached calibration reports.

## Specific visual-review targets

Human visual review of the adapted model remains pending. The numeric audit did not view or reinterpret the footage. Review all six synchronized windows, with particular attention to:

- **P003 frame 164:** the only wrong observation at the primary policy. The predicted center `(724.2333, 847.9696)` is 11.433 source pixels from the reviewed center `(735.429, 850.286)`, outside the unchanged 10-pixel rule. The reviewed point is an amodal estimate with 3.833-pixel annotation uncertainty. The result remains a geometric failure; that alone does not prove the prediction is on a different physical object. It precedes the reviewed hidden interval 165–169. Frame 170 is missing; frames 171–174 then match. Inspect the transition without filling the hidden interval or treating a geometric return as certified identity continuity.
- **P001 frames 50–74:** all 25 frames remain missing. This is the largest unresolved coverage failure.
- **P001 frames 206–209 and 215–224:** the other 14 P001 missing frames. Together the two P001 windows account for 39/46 missing eligible frames.
- **P003 frames 300–304** and **P002 frame 49:** the remaining six missing frames outside P001 and the P003 occlusion boundary.
- **P002 frames 257–261:** five consecutive recovered RF failures in an adapted window with 25/25 geometric matches. Confirm the object being localized, not only the score.

All six fixed-0.5 videos completed. Each `adapted_review.json` records 25 decoded frames, successful final-frame decoding, the adapted checkpoint digest and pending human review. The video display explicitly identifies adaptation and its threshold; structural inspection of screenshots does not constitute human acceptance.

| Review video | Main issue or improvement to inspect |
| --- | --- |
| [P001 representative, 50–74](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/evaluation/possession_001_frames_0050_0074_representative_evaluation_development_v0_2/adapted_review.mp4) | Entire window missing |
| [P001 challenge, 200–224](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/evaluation/possession_001_frames_0200_0224_challenge_evaluation_development_v0_2/adapted_review.mp4) | Recovered frames 204/210 and remaining long gaps |
| [P002 representative, 250–274](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/evaluation/possession_002_frames_0250_0274_representative_evaluation_development_v0_2/adapted_review.mp4) | 25/25 matches, including recovered frames 257–261 |
| [P002 challenge, 25–49](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/evaluation/possession_002_frames_0025_0049_challenge_evaluation_development_v0_2/adapted_review.mp4) | 24 matches and missing final frame 49 |
| [P003 representative, 300–324](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/evaluation/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/adapted_review.mp4) | Missing opening frames 300–304 |
| [P003 challenge, 150–174](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/evaluation/possession_003_frames_0150_0174_challenge_evaluation_development_v0_2/adapted_review.mp4) | Frame 164 geometric error, hidden interval and return |

Bound snapshots are available for [P001 frame 210](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/review_snapshots/possession_001_frame_000210.png), [P002 frame 257](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/review_snapshots/possession_002_frame_000257.png), [P003 frame 164](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/review_snapshots/possession_003_frame_000164.png) and [P003 frame 170](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/review_snapshots/possession_003_frame_000170.png). Their provenance is preserved in `review_snapshots/snapshots.json`.

## Execution and evidence

The ignored trial root is `data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/`. Principal records are:

- `training/completion.json`: completed update 200, frozen configuration, training manifest, schedule, losses, optimizer/RNG state and retained attempt references.
- `evaluation/experiment.json`, `model_runtime.json`, `summary.json` and six window directories: actual adapted-checkpoint inference, scores, caches and receipts.
- `calibration_config.json` and `calibration/`: adapted fixed-grid results and per-pool equal-count RF ranking records.
- `comparison.json`: paired same-threshold pretrained/adapted evidence, bound summaries and all compared window-report digests.

The final checkpoint digest is `98912a271791326bcfe2d2f468e94002d0986281f27ff1641c795177d1f94289`. Actual model-load provenance records that digest, its 6,084,071 bytes, strict finite tensor-state loading and the original pretrained checkpoint binding. All six inference identities name this completed adapted checkpoint.

The training attempt completed without a resume in 23.207 seconds. Its resource record reports an NVIDIA GeForce RTX 5070, peak allocated CUDA memory 2,004,807,168 bytes (1.867 GiB) and peak reserved memory 2,493,513,728 bytes (2.322 GiB). These framework measurements are not total system/GPU memory use. The evaluation/inference/comparison invocation took 32.705 seconds, including the cached calibration screen's 9.216 seconds; those durations must not be added as independent work. The subsequent render invocation completed in 12.551 seconds. Training loss is retained for diagnostics, not treated as an evaluation metric.

Independent saved-record auditing confirmed all six complete 25-frame outputs, 138 triplet receipts, their exact temporal contribution counts, 60 unchanged RF parity cells, the adapted 0.5 points/report parity, all 48 threshold/window summaries, pool totals and original/adapted paired counts. All 16 equal-count RF rankings matched the saved RF confidences and retained-frame membership; all 96 compared report digests matched. This audit read existing records only: it did not rerun training, inference, tests or point scoring.

## Interpretation and remaining limits

The result supports further work on this adapted model. It does not complete the agreed ball-tracking milestone. Forty-six eligible gaps and the entire P001 representative failure remain, and only short windows have been evaluated rather than full curated possessions.

The training and evaluation windows are disjoint but come from the same NFHS game and gym. The development windows have already informed several decisions. There is one evaluation hidden-ball episode, heavy reliance on partial/amodal labels, and no independent-game evidence. Three-channel inference also uses future frames within each available triplet. Geometric agreement does not independently establish physical identity, uninterrupted trajectories or defensive-value validity.

The checkpoint was selected by the prescribed final update, not its evaluation outcome. Existing reviews remain valid for their original artifacts; they do not approve the changed model. Human synchronized review, broader occlusion/reacquisition evidence and the remaining quantitative/trajectory requirements still stand. `selected_operating_point` and `quality_gate` remain null.
