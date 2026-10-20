# NBA continuation: numerical screen failed; baseline retained

Ryan approved the [bounded experiment](nba_wasb_adaptation_plan.md) with
“Ok I like this chat. Move forward”. The exact [config](../configs/ball_tracking/wasb_experiments/nba_wasb_adaptation_v0_1.json)
and [approval](../configs/ball_tracking/reviews/nba_wasb_adaptation_approval_v0_1.json)
were frozen before execution. One 200-update continuation fit and its fixed
numerical comparison are complete. The candidate **fails four of nine numerical
conditions**, so the expanded checkpoint `09da1214e94f` remains the baseline.
All eight complete comparison videos passed the producing media checks.
Independent comparison audit passed; new model-output human review remains pending.
No second fit, threshold tuning or model promotion has occurred.

## Fixed comparison

The following counts use the unchanged strict `>0.3` response threshold and
inclusive ten-pixel distance in original source coordinates. “Wrong” means an
output exists but its center falls outside that distance; missing outputs are
counted separately. Hidden references have no localization target.
Uncertainty-adjusted errors remain separate diagnostics and do not change the
fixed raw-distance match boundary.

| Cohort | Eligible centers | Old matched / wrong / missing | New matched / wrong / missing | Hidden alarms, old → new |
| --- | ---: | ---: | ---: | ---: |
| SAC training fit, 300 frames | 270 | 218 / 5 / 47 | 265 / 5 / 0 | 0 → 0 of 17 |
| DET development, excluded from fitting, 340 frames | 237 | 207 / 8 / 22 | 206 / 10 / 21 | 13 → 9 of 69 |
| NFHS development, 150 frames | 145 | 130 / 1 / 14 | 129 / 1 / 15 | 0 → 0 of 5 |

Thirteen SAC and 34 DET references remain otherwise unscored; their unknown
centers are not filled in. SAC's 17 hidden references are certain. DET's 69
hidden references have probable confidence and are evaluation-only, not training
negatives. Both separate 60-frame easy NBA controls remain 60/60. These controls
use the longer comparison context; the original short-pilot results are preserved.

| Predeclared condition | Required | Observed | Result |
| --- | ---: | ---: | --- |
| DET matched centers | ≥208 | 206 | Fail |
| DET missing outputs | ≤21 | 21 | Pass |
| DET wrong locations | ≤8 | 10 | Fail |
| DET hidden alarms | ≤13 | 9 | Pass |
| DET easy-control matches | 60 | 60 | Pass |
| NFHS matched centers | ≥130 | 129 | Fail |
| NFHS missing outputs | ≤14 | 15 | Fail |
| NFHS wrong locations | ≤1 | 1 | Pass |
| NFHS hidden alarms | 0 | 0 | Pass |

The strong SAC training-fit improvement does not transfer to the DET development
comparison, and NFHS loses one net match. Fewer hidden alarms and one fewer DET
miss do not offset the failed conditions. This single recipe does not establish
improved NBA transfer or isolate why the regressions occurred.

## Changes to inspect in synchronized video

SAC retains all 218 old matches and adds 47. Of 47 previously missing outputs,
44 become matches and three become wrong locations; three previously wrong
outputs become matches. The new wrong outputs at SAC frames 1274, 1278 and 1279
have errors of 10.994, 35.896 and 39.813 pixels. Thus zero missing outputs does
not mean every old miss was correctly localized.

DET gains frame 11013, while frames 11107 and 11501 lose their old matches.
Frame 11107 moves from 5.865 to **305.575 pixels** of error, a large distractor
switch. Frame 11501 moves from 9.272 to **10.014 pixels**, just outside the fixed
boundary. Seven old hidden alarms disappear, three new alarms appear at
11036–11038, and six persist, giving the net reduction from 13 to nine.

NFHS gains P001/221, P001/223 and P002/49, while P001/206–207, P001/209 and
P003/304 become missing. The full windows and their final frames remain part of
the review; these frame cues do not replace review of surrounding context.

## Complete synchronized videos

The single comparison and media execution completed in **1,425.922 seconds**,
with 2,836 new inference calls and no failed or uncertain calls.
It produced eight paired videos covering 2,852 source frames: 2,702 NBA frames
and 150 NFHS frames. Every source frame appears once. The final encoded frame
has one extra second of duration, rather than added source-frame copies.
The producing checks decoded every frame, verified frame/PTS keys and paired
overlay pixels within the frozen encoding tolerance, and checked the actual
final frame and duration. These transport checks do not constitute human review.

The old baseline is on the left and the new continuation is on the right.
Pink marks model outputs; cyan marks accepted reference centers where available.
NBA plays at 30 source frames per second, about half speed; NFHS plays at six.
AI inspection covered 56 sampled source frames and all eight actual encoded
final frames. It confirmed the described recoveries, distractor switch and
visible-ball losses; it was not a complete visual inspection of every video.
All eight new human reviews remain pending.

| Video | Source frames, inclusive | Frames | Duration |
| --- | --- | ---: | ---: |
| [SAC training-fit context](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/comparison/sac_mem_q1_c01/review_attempts/cf1a87c23a3b4968ac64083222c7f251/review.mp4) | 540–2010 | 1,471 | 50.033s |
| [DET development context](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/comparison/sas_det_q1_c02/review_attempts/8e6924462d6441d68cba99e4205cc49d/review.mp4) | 10668–11898 | 1,231 | 42.033s |
| [P001 representative](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/comparison/possession_001_frames_0050_0074_representative_evaluation_development_v0_2/review_attempts/d5ee8130db2840cc849f127d900f410e/review.mp4) | 50–74 | 25 | 5.167s |
| [P001 challenge](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/comparison/possession_001_frames_0200_0224_challenge_evaluation_development_v0_2/review_attempts/c30188c460104cd39a3450ff185f3928/review.mp4) | 200–224 | 25 | 5.167s |
| [P002 representative](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/comparison/possession_002_frames_0250_0274_representative_evaluation_development_v0_2/review_attempts/e4f9483718dc4d7abd4e389cf848b73a/review.mp4) | 250–274 | 25 | 5.167s |
| [P002 challenge](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/comparison/possession_002_frames_0025_0049_challenge_evaluation_development_v0_2/review_attempts/29a2c04fa9cb44478db09db6bf93e36d/review.mp4) | 25–49 | 25 | 5.167s |
| [P003 representative](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/comparison/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/review_attempts/754eae8e651d4c24842a88bd975aa9bf/review.mp4) | 300–324 | 25 | 5.167s |
| [P003 challenge](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/comparison/possession_003_frames_0150_0174_challenge_evaluation_development_v0_2/review_attempts/d76e24da5b964ea394a5f683e1d6d1e4/review.mp4) | 150–174 | 25 | 5.167s |

DET frame 11107 occurs at approximately 14.63 seconds in its video; frame
11501 occurs at 27.77 seconds. Watch the full sequences, including the final
held frame, to assess distractors, missing outputs and continuity.

For phone delivery, the [six NFHS clips in one 31-second video](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/delivery/nfhs_all_six_comparison.mp4)
preserve all 150 decoded frames, their order, timing and each final hold. They
were combined by copying the encoded streams. The initial packet-byte equality
check failed at the first packet of each clip; independent decoded-RGB and timing
checks passed exactly. The original compilation was retained without re-encoding
or new inference, and the failed check remains recorded.

## Training that actually ran

The run started from the preserved expanded checkpoint `09da1214e94f`, with a
fresh Adam optimizer and the fixed recipe. The approved pool contains 450 frames:
300 SAC–MEM frames and 150 earlier NFHS frames, containing
400 positive centers, 36 certain-hidden negatives and 14 masked frames.
Only certain-hidden labels supply negative targets; unsupported labels remain
masked while their image channels can provide temporal context.

There are 434 within-block adjacent triplets. Ten SAC triplets with no supervised
channel were excluded, leaving 424 usable triplets. The deterministic schedule
used 400 distinct triplets: **269 NBA and 131 NFHS**; 24 usable triplets were not
sampled. The samples touch 440 distinct input frames. Ten have no input exposure:
eight masked frames and two positive frames, NFHS P001/375 and SAC/1059. Pool
membership therefore does not mean every frame was trained. Per-sample and
per-frame exposure are recorded. No context crosses a
block boundary; native NBA 16/17 ms and NFHS 40 ms spacing remain unchanged.
Mixed NBA reference containers include both games, but only the approved SAC
rows entered training. DET, TOR, NFHS development labels and holdouts did not
enter optimization.

The single fit completed all 200 updates without retry in **50.328 seconds**.
Peak allocated GPU memory was 2,004,807,168 bytes; cached preprocessed CPU tensors
occupied 3,001,025,784 bytes. These are component measurements, not total process
RAM. BatchNorm running buffers stayed frozen. The final checkpoint is 6,084,071
bytes with SHA-256
`da44ce06cdf7b3bf97468b5780f0f02e435807299cf3d771494c367d9010da26`.
No intermediate checkpoint was selected from evaluation results.

## Validation and preserved attempts

Independent preflight verified all 33 bound inputs. Its first helper incorrectly
expected every NFHS segment to have purpose `training`; three authorized pilot
segments retain `protocol_adjudication`. The helper was corrected to compare
each label purpose with its frozen segment authority, permitting those two
authorized purposes. The second attempt passed. The passed receipt records that
history; the original traceback remains in tool output. No source label or
scientific output was changed.

Independent training audit passed **3,469 checks**: all 428 published tensors
equal update 200, all 213 BatchNorm buffers match initialization, 176 trainable
tensors changed and all 176 Adam parameter states reached step 200. The first
audit attempt completed 2,821 metadata checks before the system Python lacked
PyTorch; the unchanged helper passed under the project environment. Both attempts
are preserved. This audit correction did not repeat training.

Seventeen distinct focused checks passed: eight trainer checks and nine
comparison checks. The comparison commands ran eight checks followed by two,
one of which repeated the decoder contract. They cover actual producer records,
native joins, scoring/gates, cached-call recovery and complete paired media
transport; synthetic failure cases in those tests are not failed scientific
runs. The full suite was not repeated.

Independent comparison audit passed **48,264 checks** on its first attempt in
15.038 seconds. It independently derived all 790 scored rows, verified all 2,852
source joins and all 2,836 cache metadata/start records, and confirmed that all
33 frozen input bindings are unchanged. Numeric mean/component reconstruction
covered 56 deterministic rows from 72 cache bodies (115,173,064 compressed bytes),
not every heatmap body. It checked all eight video bindings, manifests, probes
and producing every-frame decode receipts without decoding the videos again.
The four failed numerical conditions were independently reproduced.

The phone-compilation verification correction above was a packaging check,
not a failed scientific run. A later inspection helper also stopped at its
exclusive-create guard before starting FFmpeg; that event is preserved in the
delivery failure record. Neither event repeated training, inference or encoding.

## Interpretation boundaries

SAC is now training data for this experiment; its new scores measure training
fit. DET remains outside fitting but was already inspected and used to design
this development experiment. It is not an independent test game. The accepted
NBA references retain AI authorship and Ryan's later visual acceptance, including
their uncertainty and unknown centers.

The continuation changes both data composition and optimization exposure. It
cannot isolate the effect of NBA data alone or establish representative NBA
accuracy. Existing scores and checkpoints remain unchanged. TOR, protected
holdouts and buffers, the original NFHS finish line and the negative motion
result remain intact; three motion-video human reviews are still pending.

## Evidence

- [Tracked result and exact artifact bindings](../configs/ball_tracking/reviews/nba_wasb_adaptation_result_v0_1.json).
- [Completed comparison and bound review packages](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/comparison/report.json).
- [Fixed score report](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/comparison/score_report.json).
- [Training completion](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/training/completion.json).
- [Training manifest](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/training/training_manifest.json) and [sample exposure](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/training/sample_exposure.json).
- [Independent preflight](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/preparation/independent_preflight.json).
- [Independent training audit](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/independent_audit_01/training_audit_02.json).
- [Independent comparison audit](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/independent_audit_01/comparison_audit_01.json).
- [Sampled AI inspection and all encoded finals](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/visual_review/ai_visual_review.json).
- [Verified phone compilation](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/delivery/nfhs_compilation_receipt.json) and [preserved packaging-check failure](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/delivery/concat_attempt_01_failure.json).
- [Eight focused trainer checks](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/preparation/trainer_focused_tests_01.log).
- [Comparison checks](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/validation/comparison_tests_01.log) and [producer-contract follow-up](../data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/validation/comparison_tests_02.log).

All generated media, checkpoint tensors and prediction artifacts remain ignored
by Git. New model-output human review remains pending.
