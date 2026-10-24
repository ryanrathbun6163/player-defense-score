# Completion campaign: NBA reference batch 22

NBA21 is accepted, bringing NBA coverage to **3,240/3,839 judgments: 2,878
centers and 362 nulls**. This increment prepares the next fixed training episode,
SAC–MEM e04, native frames **163873–163992**. Its **120 pending judgments**
contain **106 centers and 14 nulls**, with **6–10px center uncertainty**. Source,
proposal and complete encoded inspection and final integration pass. NBA22 is
ready for Ryan's acceptance or corrections; no NBA22 label has been accepted.

## Fixed role and native timing

The [configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_22_v0_1.json)
and [native selection](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/selection.json)
retain episode `sac-mem-0022500829_e04` and the unchanged
[source roles](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json).
SAC–MEM was assigned training before new model predictions. Both eligibility
flags remain false pending reference acceptance.

The **1920×1080** full source contains **357,233 frames**, with timebase
**1/90000**. The fixed selection window is **[2734,2736) seconds**. Selected
native PTS span **246060692–246239342**; the final presentation ends at
**246240872**, giving **2.002 seconds** of native playback. Presentation intervals
remain **16/17ms**, derived from the next global PTS; raw packet durations remain
separate. Batch final **163992** differs from full-source final **357232**.

## Source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/preparation.json)
and [pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/source_pixel_audit.json)
pass **120 exact native PNG/PTS checks** in **76.046 seconds**, preserving
**6,813 preexisting files**. Primary decoding returned **357 frames,
163636–163992**, after **359 submitted packets**. The **237 decoded prefix
frames, 163636–163872**, inherit the training role; only selected frames
163873–163992 were saved. Secondary conversion emitted **120 RGB frames** and
reported **120 filter frames**, exactly the selected range. Both paths use
FFmpeg components; matching pixels verify transport rather than independent
ground truth.

## Proposals and inspection

Visibility comprises **104 partially visible, 11 not visible and five fully
visible judgments**. Unknown centers remain at **163873–163883, 163954 and
163981–163982**, without interpolation. Body, hand and leg overlap, motion blur
and brief source exposure changes remain explicit; visible fragments do not
always support a defensible center.

| Native frames | Centers | Nulls | Inspection receipt |
| --- | ---: | ---: | --- |
| 163873–163912 | 29 | 11 | [First part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/inspection/part_163873_163912_receipt.json) |
| 163913–163952 | 40 | 0 | [Middle part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/inspection/part_163913_163952_receipt.json) |
| 163953–163992 | 37 | 3 | [Final part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/inspection/part_163953_163992_receipt.json) |

The team inspected every current source and proposed overlay frame, including
full part endpoints. Final 163992 retains **[836,631] ±9 pixels**, partially
visible. Root also inspected source precision views at **163953–163956 and
163981–163984** for a second AI check. All three initial drafts remain unchanged;
the receipts record no annotation corrections or failed helper attempts. These
are AI-assisted proposals and AI visual checks, not independent human ground
truth. No interpolation or model prediction supplied coordinates.

## Complete review and validation

The [complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/review_v1/index.html)
includes the [native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/review_v1/review_native.mp4)
and [slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/review_v1/review_slow.mp4),
the [proposal](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/proposal.json)
and [exception list](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/review_v1/exception_list.json).
The [delivery record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/review_v1/delivery_result.json)
passes its first attempt in **36.516 seconds**, without corrections or failures.
Each video contains all **120 frames**: native playback retains **2.002 seconds**
of actual timing; slow playback lasts **12 seconds at 10 fps**.

The [completed visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/root_visual_review.json)
records actual inspection of all **ten emitted/source sheets**, covering all
**106 localized center crops and 14 null contexts**, plus full source final
163992 and both actual encoded finals. The delivery receipt retains its earlier
awaiting-inspection state; the later visual receipt records completion.

The [current focused receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/focused_validation/20261024T223419Z_3fd2b6d9/references.json)
passes **ten renderer tests** against NBA22's actual proposal and media in
**27.296 seconds**, with no failures, errors or skips. NBA19's eight acceptance
tests remain historical coverage of unchanged reader/test code; no new
eight-test execution is claimed. A separate
[actual pending-consumer check](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/finalization_attempts/20261024T223719Z_e41d663b/pending_review_reader_check.json)
validates all **120 annotation/native joins**, accepting no new labels.

The first finalizer completes in **73.890 seconds**, including a **62.609-second
[integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_22/integration_audit.json)**
of **7,275 bindings, 120 native joins, 240 encoded frames, 212 markers and 120
exact source PNGs**. All **3,240 accepted NBA rows, 868 curated references and
6,813 preexisting preparation files** remain unchanged. The
[final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_22_result_v0_1.json)
records `ready_for_human_reference_acceptance`, with human acceptance null and
both eligibility flags false. The finalizer performs no source pixel decoding,
model inference, fitting or scoring.

## Campaign status and next decision

[NBA21's separate acceptance](ball_tracking_completion_nba_reference_batch_21.md#human-acceptance-published-2026-10-24)
preserves all earlier labels and review evidence. Accepted NBA roles are
**2,280 training and all 960 checkpoint validation**; validation labels remain
excluded from gradient fitting. **Three fixed SAC–MEM episodes totaling 599
judgments remain unaccepted**, including NBA22. The other **two episodes contain
479 judgments** without proposals. Curated coverage remains
**868/1,273 accepted, 760 eligible centers and 405 uncovered**, evaluation-only.

Next is Ryan's acceptance or correction of the complete 120 NBA22 judgments.
Complete accepted source/label/role manifests and the executable recipe still
need freezing before the approved fit. Fitting, checkpoint scoring, protected
evaluation, model-output acceptance and ball-phase completion remain closed.
