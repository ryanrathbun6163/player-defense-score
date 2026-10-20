# Continuous-context validation of the fixed gap rule

Ryan authorized the [prepared five-clip plan](nba_temporal_gap_continuous_validation_plan.md)
with “Move forward chat”. The [approval](../configs/ball_tracking/reviews/nba_temporal_gap_continuous_validation_approval_v0_1.json)
is separate from the earlier resume request and accepted bounded trial.

The saved-evidence comparison passes all 24 numerical conditions, but AI visual
inspection identifies an **unlabeled wrong-object fill at SAC frame 1420**.
The rule extends an existing head distractor. Broader adoption is not recommended
on this numerical pass. Ryan has reported reviewing all five new videos; the
[later review record](../configs/ball_tracking/reviews/nba_temporal_gap_continuous_visual_review_v0_1.json)
records completion without an explicit quality endorsement or per-frame
adjudication. Original pending-era receipts remain unchanged.
Original predictions and retained checkpoint `09da1214e94f` remain unchanged;
this is not a ball-phase pass.

## Same-context results

| Group | Original matched / wrong / missing | Gap-rule matched / wrong / missing | Hidden alarms |
| --- | --- | --- | --- |
| SAC training fit | 218 / 5 / 47 | 218 / 5 / 47 | 0/17 unchanged |
| DET development | 207 / 8 / 22 | **209 / 8 / 20** | 13/69 unchanged |
| NFHS development | 131 / 1 / 13 | **132 / 1 / 12** | 0/5 unchanged |

Both included NBA easy controls remain 60/60. Scoring uses the same 790 reference
frames: 652 eligible, 91 hidden and 47 unknown. No new wrong frame, hidden alarm
or lost correct position occurs. All three accepted short-window additions
(DET 11437–11438 and P001 208) retain their exact coordinates and remain matches.

The historical short-window NFHS baseline was 130/1/14/0. Its longer-context
control was already 131/1/13/0, principally including the existing P002/49 recovery.
The new selector gain is one further match; the context benefit is not credited
to gap repair. Eighteen labeled NFHS centers differ with longer model context.
All 640 NBA labeled original centers retain the earlier longer context.

## Continuous coverage and remaining gaps

The run covers 3,975 permitted positions in eight segments. All 225 protected
NFHS timeline positions remain excluded. All 3,359 original emitted points are
preserved. Ten gaps supply 14 new points; three have accepted labels and eleven
remain unscored. Availability rises to 3,373 points, with 602 positions still
missing. These full-clip counts include training frames and are not accuracy.

| Source | Original → selected points | Missing after | Added source frames |
| --- | ---: | ---: | --- |
| SAC | 1,310 → 1,311 | 160 | 1420 |
| DET | 1,070 → 1,074 | 157 | 11437–11438, 11723–11724 |
| P001 | 324 → 327 | 97 | 19, 91, 208 |
| P002 | 308 → 308 | 116 | None |
| P003 | 347 → 353 | 72 | 194, 205, 333–334, 362–363 |

Of 85 original missing runs, 53 exceed the anchor time limit, eight exceed the
speed limit, ten lack an unambiguous candidate set, four reach a segment edge,
and ten are filled. DET/NFHS still have 32 labeled misses, nine wrong positions
and thirteen hidden alarms. The rule preserves existing wrong points and cannot
repair long gaps or absent visual evidence. The saved summary retains every
changed frame, labeled remaining error and full missing interval.

## Execution and evidence integrity

Implementation began at `e35d20d229c0d8df281c9ed0f86ce16f2114a7cc`.
The first attempt stopped before publishing selections or scores: imported NFHS
cache identities describe the old model/experiment and lack `source_video`.
Its failed receipt remains at
`data/outputs/ball_tracking/nba/temporal_gap_continuous_v0_1/attempts/890e7ac8d160491eb76f6d89d70c31be/failed.json`:
1.391 seconds, 48 cache reads and 76,409,121 compressed bytes. That attempt remains
failed and its resources are not reset.

The routine adapter correction at `ad82b03d2dbad115d188e83f62e99faf3ca1c88b`
joins imported identities to their original bound source window and exact cache
paths. It preserves the old records and uses a separate
[recovery configuration](../configs/ball_tracking/selections/nba_temporal_gap_continuous_recovery_01_v0_1.json).
The unchanged scientific comparison then completed in 4.031 seconds, consuming
83 cached triplets (132,172,876 compressed bytes), with at most three triplet
arrays retained. No inference, training, checkpoint load, threshold search or
source-pixel decode occurred during selection/scoring. Rendering is separate.

Selections were sealed before labels entered scoring. A separate pre-scoring
receipt detects modified selections before recovery. Geometry pruning calls the
existing frozen selector and skips only its pre-candidate rejection paths;
focused tests establish decision equality with full contributor loading.

NFHS packet timestamps were inspected without decoding pixels. P001 and P002
start at 40 ms in their containers; P003 starts at zero. Actual container PTS
are retained alongside the established frame-zero-relative reference clock.
The constant translation changes neither elapsed time nor interpolation fraction.
The initial zero-origin assertion failure and correction remain in preparation
evidence; no protected image was exposed.

Twenty-one distinct focused tests have passed across the runner and renderer,
with affected checks rerun after their corrections. Original synthetic fixture
failures and the renderer's protected-border chroma-bleed failure remain logged.
The latter was corrected by making the protected canvas black, without relaxing
the black-pixel condition. No full suite was repeated.

Independent audit passed 42,844 checks on its first result-audit attempt. It
reconstructed all 3,975 selection decisions without calling the producer's
selector, independently computed all 790 outcomes and distance errors, checked
all protected slots and missing intervals, and reconstructed every new point
from 14 original contributor caches (22,307,800 bytes). All 24 gates agree.
The earlier inspection helper's missing-field error is recorded separately.

## Review status and limits

At SAC frame 1420 (14.681 seconds into its comparison), the new marker sits on
the foreground light-blue defender's head. Independent inspection of original
frames 1418–1422 confirms that both original anchors, 1419 and 1421, also follow
that head. Their 0.034-second separation satisfies the frozen temporal rule;
smoothness cannot establish that an anchor is the ball. The exact true-ball
center/visibility is not confidently established in this blurred, occluded
context. Frame 1420 has no label among the 790 scored references, so the numeric
results stay unchanged. This qualitative counterexample is preserved separately
from scoring. Ryan's subsequent video-review report did not explicitly adjudicate
this individual finding; no label, rule or threshold was changed.

Five complete comparisons are available in the
[local review guide](../data/outputs/ball_tracking/nba/temporal_gap_continuous_v0_1/review/review.html),
with same-context originals on the left and the unchanged gap rule on the right.
The guide links every changed-frame image and every segment final, and supports
slower playback. Pink marks the ball prediction; white NFHS player IDs are
existing reconciled display overlays.

| Comparison | Duration including final hold | Added-frame review cues |
| --- | ---: | --- |
| SAC | 25.541 s | **14.681 s: wrong-object head fill**, source 1420 |
| DET | 21.537 s | 12.829–12.846 s; 17.601–17.617 s |
| P001 | 20.960 s | 0.760 s; 3.640 s; 8.320 s |
| P002 | 20.960 s | No added points; review the unchanged continuous baseline |
| P003 | 21.000 s | 7.760 s; 8.200 s; 13.320–13.360 s; 14.480–14.520 s |

Rendering and complete verification finished in 676.688 seconds with no failed
render attempt. Every encoded native timestamp, duration, frame/panel key and
paired image passed verification: 4,200 timeline slots, 225 protected black
pairs, eight segment finals and five actual-final holds. Independent media audit
passed 12,832 checks and rehashed 54 delivered bindings without repeating video
decoding. Integrity checks establish faithful delivery, not prediction quality.

AI inspection covered all fourteen encoded added frames and all eight encoded
segment finals (including every actual clip final), plus five adjacent original
SAC frames and four adjacent encoded P003 frames. It did not manually inspect
all 4,200 timeline slots. P001 additions 19/91 remain partly occluded at the
ball/forearm boundary. P003 additions 333/334 remain unresolved near the left
wrist/hip; neighboring frames support a carrying sequence but cannot certify
their visibility or exact centers. Those four remain uncertain, unscored cases.

Ryan reported reviewing all five complete videos: “Ok videos reviewed. What’s
next chat”. Their review is complete, without a claimed favorable quality
judgment or playback telemetry. The original bounded-trial acceptance remains
complete, and the three older negative motion-comparison reviews remain pending
separately. The
[compact record](../configs/ball_tracking/reviews/nba_temporal_gap_continuous_validation_result_v0_1.json)
binds the numerical, media, test and AI-inspection evidence. Broader adoption of
the unchanged rule is not recommended; use the preserved wrong-anchor example
and remaining-error inventory to define any subsequent improvement.

The [next proposal](nba_gap_anchor_reference_plan.md) covers all ten repaired
gaps and their original endpoints with 27 new source-first frame judgments and
seven accepted controls. It is not yet executed. Its purpose is to make the
unlabeled failure and uncertain cases measurable before changing the rule.

This is offline development evidence using future anchors. NBA references retain
their AI authorship and later human acceptance; they are not independent human
annotations. SAC is training-fit evidence, DET remains excluded from fitting,
and all protected holdouts remain sealed. The rejected NBA continuation remains
rejected. Reliable continuous tracking, possession understanding, NBA identity
and calibration, matchup inference and defensive scoring remain unfinished.
