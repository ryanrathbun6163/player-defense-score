# NBA resolution experiment result

Completed October 26, 2026, America/Phoenix.

## Outcome

The approved five-epoch **768x432** experiment completed all **7,760 updates**
and the full five-model NBA comparison. **No checkpoint passes the unchanged
quality criteria; no model is adopted.** This is partial Detroit improvement,
not completion of the ball-tracking phase.

Epoch five improves the target Spurs-Pistons context from **212/241 (88.0%) to
219/241 (90.9%) correct**, with wrong eligible outputs reduced from **five to
one** and missing eligible outputs from **24 to 21**, compared with the saved
512x288 augmentation-five control. It gains nine previously incorrect positions
and loses two previously correct positions. Emissions on probable-hidden DET
references fall from 20 to seven; those references remain uncertain, not
reclassified as certain-hidden violations.

The persistent **DET 11075-11093 gap remains missing in every new epoch**:
19 eligible frames / 317ms, above the unchanged 200ms limit. Epoch five still
needs ten additional correct positions to reach 229/241. Its other missing
eligible frames are 11557-11558 and its remaining wrong point is 11561.
Meanwhile HOU correct positions fall from 844 to 841, wrong outputs rise from
three to twenty, and certain-hidden emissions rise from 17 to 18. Better DET
counts therefore do not establish a better general NBA tracker.

The experiment answers the proposed resolution question: this configuration
recovers some errors, including the two prior large DET errors at 11476/11514,
but **additional spatial detail alone does not fix the persistent gap or the
visibility/distractor problem**. This is one controlled development experiment,
not proof that every higher-resolution architecture would fail. It does not
justify automatically extending this fit or replacing the retained model.

## Authorization, fixed method and recovery

Ryan approved the [five-epoch execution](ball_tracking_nba_resolution_execution.md),
then explicitly requested resumption after the crash-dump analysis: "ok move
forward with the training now please". The successful attempt resumed the valid
update-zero state; the original [graphics-crash attempt](ball_tracking_nba_resolution_restart_2026-10-26.md),
corrupt all-NUL supervisor summary and checkpoint recovery history remain intact.
The earlier crash made zero optimizer updates. This resume made all 7,760 unique
updates, with no duplicate/replayed updates or partial update-log fragments.

The [frozen recipe](../configs/ball_tracking/proposals/wasb_resolution_v0_1.json)
retains the same initializer `09da1214...`, labels, first-five-epoch schedule,
75% NBA / 25% NFHS mixture, optimizer, masked loss, augmentation draws, float32,
batch two and frozen BatchNorm buffers as the 512 augmentation experiment.
Native frames are resized directly to 768x432; target radius 3.75 preserves the
nominal source footprint while retaining the disclosed rasterization difference.
The strict >0.3 threshold, complete native triplet means, component-mass selection,
ten-source-pixel match radius and all numerical/visual criteria are unchanged.
No new labels, interpolation, protected reads or additional fitting were added.

All five epochs were evaluated; the superseded high-school selection veto was
not reapplied. The frozen earliest-qualifying-epoch rule returns **null**.
Unknown/censored temporal evidence remains inconclusive, not a pass. Human
trajectory/object-identity review remains separate from quantitative checks.

## All five NBA checkpoints

Each count cell is **correct / wrong / missing**. HOU has 882 eligible references
in six episodes, DET 241 eligible references within its original 1,231-frame
context, and SAC 270 eligible references within its original 1,471-frame context.
The complete reports retain each episode, unknown interval and gate separately;
pooled counts do not override a failure in an individual episode.

| Model | HOU /882 | HOU certain-hidden emissions | DET /241 | DET probable-hidden emissions | SAC /270 |
|---|---:|---:|---:|---:|---:|
| Retained 512 baseline | 845 / 29 / 8 | 25 | 209 / 8 / 24 | 13 | 218 / 5 / 47 |
| 512 augmentation epoch 5 | 844 / 3 / 35 | 17 | 212 / 5 / 24 | 20 | 270 / 0 / 0 |
| 768 epoch 1 | 848 / 15 / 19 | 18 | 211 / 8 / 22 | 14 | 263 / 2 / 5 |
| 768 epoch 2 | 844 / 17 / 21 | 18 | 216 / 3 / 22 | 6 | 266 / 4 / 0 |
| 768 epoch 3 | 828 / 34 / 20 | 23 | 218 / 2 / 21 | 1 | 268 / 2 / 0 |
| 768 epoch 4 | 832 / 25 / 25 | 18 | 218 / 2 / 21 | 1 | 268 / 2 / 0 |
| 768 epoch 5 | 841 / 20 / 21 | 18 | 219 / 1 / 21 | 7 | 269 / 1 / 0 |

Every new epoch fails DET coverage and missing continuity, and every one emits
on certainly hidden HOU frames. Epochs three through five meet DET's wrong-output
count limit, but this single passed metric is insufficient. Recovery and
wrong-object gates also retain their unknown/censored/human-review limitations.
The detailed [audited summary](../data/outputs/t/nba_resolution_resume_20261026/resolution_compact_summary_20261026T163853194303Z.json)
contains change counts, failure-frame IDs and all per-context gate statuses.
Exact gained/lost frame lists are in the
[full evaluation](../data/outputs/ball_tracking/wasb_resolution_v0_1/nba_comparison_v0_1/evaluation.json).

HOU was repeatedly used for checkpoint selection, DET is already-inspected
development footage excluded from fitting, and SAC is training-exposed.
These results are neither a fresh independent test nor full-possession/game
certification. Protected evaluation remains closed pending a frozen method and
separate explicit authorization. NBA player identities and court calibration
also retain their future validation requirements.

## High-school regression evidence and epoch zero

These are the existing checkpoint-selection cohorts, not a new full curated
census. Cells are **correct / wrong / certain-hidden emissions**.

| Model | P001 | P002 | P003 |
|---|---:|---:|---:|
| Retained 512 baseline | 41 / 0 / 0 | 49 / 0 / 0 | 40 / 1 / 0 |
| 512 augmentation epoch 5 | 38 / 1 / 0 | 49 / 0 / 0 | 38 / 1 / 0 |
| Fresh 768 epoch 0 | 26 / 3 / 0 | 46 / 4 / 0 | 33 / 9 / 0 |
| 768 epoch 1 | 49 / 1 / 0 | 49 / 1 / 0 | 38 / 1 / 0 |
| 768 epoch 2 | 43 / 2 / 0 | 49 / 1 / 0 | 39 / 1 / 0 |
| 768 epoch 3 | 47 / 1 / 0 | 49 / 1 / 0 | 39 / 1 / 0 |
| 768 epoch 4 | 41 / 2 / 0 | 49 / 1 / 0 | 39 / 1 / 0 |
| 768 epoch 5 | 40 / 1 / 0 | 49 / 1 / 0 | 37 / 1 / 0 |

At epoch five, total correct NFHS positions are 126 versus 125 for the 512
augmentation control and 130 for the retained baseline. P003 regresses against
both; P002 introduces a wrong output despite unchanged matches. These secondary
regressions are reported without rewriting prior decisions or reinstating the
old veto. All original high-school labels, outputs and reviews remain preserved.

Epoch zero was recomputed at 768 with the unchanged initializer: HOU is
745 correct / 136 wrong / 33 certain-hidden emissions. That is not the original
512 epoch-zero result. No full SAC/DET epoch-zero comparison was added. All six
validation reports and their missing-gap summaries are linked in the
[validation table receipt](../data/outputs/t/nba_resolution_resume_20261026/fit_validation_summary_20261026T162412.json).

## Verification and measured resources

The frozen implementation already passed **38 focused checks** and 114 actual
native-triplet parity checks before execution. No frozen scientific code changed
during this resume; those checks were not rerun merely for resumption.

The independent [fit audit](../data/outputs/t/nba_resolution_resume_20261026/completed_resolution_audit_20261026T162412599155Z.json)
passes **168,396 checks**. It verifies all 7,760 updates, 15,515 deterministic
augmentation draws spanning all 3,103 triplets, 6,660 validation rows, five saved
models, 213 unchanged BatchNorm buffers, Adam state and 316 recovery save points.
The first audit failed on a hard-coded optimizer inventory assumption. Its
script/receipt remain preserved. The corrected helper derives registration from
the pinned HRNet on a meta device without a forward call: 215 parameters are
registered, 176 connect to the configured loss, and 39 unused final fusion
parameters remain unchanged. No trained tensor or production code was corrected.

The independent [NBA audit](../data/outputs/t/nba_resolution_resume_20261026/resolution_comparison_audit_20261026T163833143856Z.json)
passes **472,085 checks** on all 40 model-context receipts / 18,310 observations.
It reconstructs components and inverse geometry from all 13,510 new saved mean
heatmaps, independently checks native temporal gates and control gains/losses,
and verifies exact reuse of 4,800 HOU observations. The comparison makes 13,490
new forward calls, zero optimizer updates and no new labels. The audit itself
makes no GPU/model calls or source/protected pixel reads.

| Successful supervised workload | Elapsed | Peak temperature | Peak power | Peak GPU memory | Samples |
|---|---:|---:|---:|---:|---:|
| Resumed five-epoch fit | 2,454.641 s (40.9 min) | 61 C | 139.36 W | 7,242 MiB | 1,194 |
| Five-model NBA comparison | 779.391 s (13.0 min) | 59 C | 109.79 W | 2,589 MiB | 380 |

Both supervisors exit successfully, without a stop condition, forced stop,
cleanup error or remaining owned process. These times exclude the preserved
earlier failed attempt and separate preparation/readiness work; they do not
reset consumed history. The [post-GPU system check](../data/outputs/t/nba_resolution_resume_20261026/post_gpu_system_state.json)
finds no matching graphics/WHEA/unexpected-power event since the resumed fit
began, no query error and all three graphics extras stopped. The GPU had cooled
to 45 C / 2% utilization. No hardware or driver setting changed. One clean run
does not resolve the underlying earlier graphics-crash cause.

The [post-run preservation check](../data/outputs/t/nba_resolution_resume_20261026/post_run_preservation_20261026T164512175576Z.json)
rehashes all 141 preflight-bound files and 70 accepted-reference bindings, with
no changes. This includes all 38 complete cache payloads and the 22 original
incident files. Its initial helper stopped before hashing because it expected
a generic status string rather than the producer's specific passed status;
the failed receipt/helper remain preserved. Only that consumer assertion changed.

## Synchronized review and next boundary

The predeclared review rule pairs the saved **512 augmentation epoch five** with
the earliest qualifying new epoch, or fixed **768 epoch five** if none qualifies.
The fallback applies here: this is a diagnostic review, not model adoption or
a new post-hoc checkpoint-selection rule. The
[results page](../data/outputs/ball_tracking/wasb_resolution_v0_1/index.html)
links all [eight synchronized comparisons](../data/outputs/ball_tracking/wasb_resolution_v0_1/paired_nba_review_v0_1/attempts/71672e99d9c74d14af46fe857b8f02d7/index.html).
Rendering completed in 347.436 seconds; all 3,662 native frames, decoded frame
identities and final presentation intervals passed transport checks. No extra
final-frame hold was added. Formal human visual acceptance remains pending.
The inherited canvas labels mean the paired 512 augmentation control on the
orange left ("retained baseline") and diagnostic 768 epoch five on the cyan
right ("selected model"); neither label changes the adopted-model decision.

[AI inspection](../data/outputs/t/nba_resolution_resume_20261026/paired_review_ai_observations.json)
covers all eight actual encoded finals, every frame of the
19-frame DET gap and actual encoded frames 11476, 11514, 11557, 11558 and 11561.
The inspected finals show no visible side-to-side synchronization or blank-tail
problem. At 11476/11514 the 768 point is near the accepted ball center while the
512 point remains in the distant official area. A weaker remote component still
exists at 11514, so this is improved selection, not proof of eliminated distractor
response. The gap remains missing around the arm/hand and signage. Frames
11557-11558 miss the partially visible rim/net scene. Frame 11561 is a nearby
offset in ball/hand/net clutter, not an AI-confirmed remote-object switch; its
10.6795px reference distance still fails the unchanged ten-pixel rule. These
bounded AI observations do not replace complete human trajectory review.

The [committed evidence ledger](../configs/ball_tracking/reviews/wasb_resolution_result_v0_1.json)
binds the completed fit/comparison/review, independent audits, original status
page, helper failures, resume authority and final result page. Generated videos,
heatmaps, checkpoints and source footage remain uncommitted.

The bounded experiment is complete. The next method decision should target the
remaining shared missing-response gap and HOU false detections using these saved
outputs. No extra epochs, new labels, threshold search, alternate architecture,
hardware change or protected evaluation follows automatically.
