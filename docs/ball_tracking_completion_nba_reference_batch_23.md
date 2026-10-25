# Completion campaign: NBA reference batch 23

NBA22 is accepted, bringing NBA coverage to **3,360/3,839 judgments: 2,984
centers and 376 nulls**. This increment prepares the next fixed training episode,
SAC–MEM e05, **239 native frames, 23374–23612**. All **239 pending judgments have
centers**, with **119 full/120 partial visibility and 6–10px uncertainty**.
Source preparation, individual source/proposal inspection, complete encoded
review and final integration pass. NBA23 is ready for Ryan's acceptance or
corrections; no NBA23 label is accepted.

## Fixed role and selection

The [configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_23_v0_1.json)
and unchanged [source roles](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json)
assign episode `sac-mem-0022500829_e05` to training. The fixed selection window is
**[390,394) seconds**, or **[35100000,35460000) ticks** at timebase **1/90000**.
It selects **239 native frames, 23374–23612**, from the **1920×1080** full source.
The source contains **357,233 frames**, with full-source final **357232**.
Native PTS span **35101412–35458802**, with final presentation end **35460242**,
covering **3.987 seconds**. Variable 16/17ms presentation timing remains separate
from nominal frame-rate metadata and raw packet durations. Final presentation
duration is **1440 ticks**, while its raw packet duration is **1530 ticks**.

The original fixed `recovery` category and source-selection description remain
unchanged. Current inspection supports centers throughout all 239 frames, with
no fully hidden or unknown-center frame. This interval therefore does not
demonstrate a hidden-to-visible recovery event.

## Source preparation and retained failure

The first preparation failed its complete-census assertion after **74.015
seconds**. Backward seek did not return required native frames **23374–23375**,
leaving **237 saved PNGs**. The [failed attempt](../data/outputs/ball_tracking/completion_campaign_v0_1/source_preparation_attempts/nba23_attempt_01/failure.json)
and [preservation record](../data/outputs/ball_tracking/completion_campaign_v0_1/source_preparation_attempts/nba23_attempt_01_preservation.json)
retain all **243 failed-attempt files**, including the exact error and consumed
time. The failed run is not reported as successful or overwritten.

An earlier seek in the new ignored helper preserves the fixed role, window and
native frame identities. The [successful preparation](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/preparation.json)
and [pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/source_pixel_audit.json)
pass **239 exact native PNG/PTS checks** in **99.562 seconds**, preserving
**7,115 preexisting files**. Primary decoding returned **597 frames, 23016–23612**,
after **599 submitted packets**. The **358 decoded prefix frames, 23016–23373**,
inherit the training role; only selected frames 23374–23612 were saved. Secondary
conversion emitted **239 RGB frames** and reported **239 filter frames**, exactly
the selected range. Both paths use FFmpeg components; matching pixels verify
transport rather than independent ground truth.

## Proposals and inspection

All **239 current source and proposed overlay frames**, full part endpoints and
the full batch source final were inspected. Visibility comprises **119 fully
visible and 120 partially visible judgments**, with no null centers. Final 23612
retains **[1582,617] ±7 pixels**, partially visible.

| Native frames | Centers | Fully visible | Partially visible | Inspection receipt |
| --- | ---: | ---: | ---: | --- |
| 23374–23453 | 80 | 72 | 8 | [First part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/inspection/part_23374_23453_receipt.json) |
| 23454–23533 | 80 | 19 | 61 | [Middle part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/inspection/part_23454_23533_receipt.json) |
| 23534–23612 | 79 | 28 | 51 | [Final part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/inspection/part_23534_23612_receipt.json) |

A second AI source-only check viewed four transition sheets covering
**23546–23549, 23554–23557, 23582–23585 and 23602–23605**. Visible separation
supports full visibility at the inspected separated frames; hand/finger overlap
supports partial visibility at the inspected contact boundaries. Frame **23554**
is borderline at the upper-right rim, so conservative partial visibility is
defensible. This corroboration checks only those 16 source frames, not proposed
numerical coordinates or unseen interval interiors, and changes no labels.

The [root annotation failure](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/inspection/root_annotation_attempt_01/failure.json)
records `annotations[75].difficulty_tags must be sorted and unique`. Validation
failed in memory before any proposal or media was written. The
[original helper](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/inspection/root_annotation_attempt_01/annotate_nba23_root.py)
is retained; sorting tags changed no geometry and did not revise a published
proposal.

The middle receipt retains the initial precision crops that clipped the right
ball edge at **23513 and 23521**. A wider
[source supplement](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/inspection/part_23454_23533_source_supplement_23513_23521_23523_23524.png)
was actually inspected before any labels were written. The final-part receipt
retains two path lookup errors: the helper had moved with the preserved failed
source attempt, and an endpoint lookup omitted the canonical filename's leading
zero. The unchanged helper was copied back before execution and the correct
`frame_023534.png` was opened afterward. These errors created no labels or
outputs, and all three initial proposals remain unchanged.

These are AI-assisted proposals and AI visual checks, not independent human
ground truth. No interpolation or model prediction supplied coordinates.

## Complete review and validation

The [complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/review_v1/index.html)
includes the [native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/review_v1/review_native.mp4)
and [slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/review_v1/review_slow.mp4),
the [proposal](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/proposal.json)
and [exception list](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/review_v1/exception_list.json).
The [delivery record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/review_v1/delivery_result.json)
passes its first attempt in **56.312 seconds**. Each video contains all **239
frames**: native playback retains **3.987 seconds** of actual presentation timing;
slow playback lasts **23.9 seconds at 10 fps**.

The [completed visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/root_visual_review.json)
records actual inspection of all **20 emitted/source sheets**, covering all **239
localized center crops**, plus full source final 23612 and both actual encoded
finals. No geometry correction followed initial proposal publication. The
delivery receipt retains its earlier awaiting-inspection state; the later visual
receipt records completion.

The [current focused receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/focused_validation/20261025T002128Z_222660d3/references.json)
passes **ten renderer tests** against NBA23's actual proposal and media in
**30.078 seconds**, with no failures, errors or skips. NBA19's eight acceptance
tests remain historical coverage of unchanged reader/test code; no new
eight-test execution is claimed. A separate
[actual pending-consumer check](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/finalization_attempts/20261025T003357Z_7b5e23b6/pending_review_reader_check.json)
validates all **239 annotation/native joins**, accepting no new labels.

The first finalizer completes in **83.703 seconds**, including a **72.297-second
[integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_23/integration_audit.json)**
of **7,783 bindings, 239 native joins, 478 encoded frames, 478 markers and 239
exact source PNGs**. All **3,360 accepted NBA rows, 868 curated references and
7,115 preexisting preparation files** remain unchanged. The
[final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_23_result_v0_1.json)
records `ready_for_human_reference_acceptance`, with human acceptance null and
both eligibility flags false. The finalizer performs no source pixel decoding,
model inference, fitting or scoring.

## Campaign status and next decision

[NBA22's separate acceptance](ball_tracking_completion_nba_reference_batch_22.md#human-acceptance-published-2026-10-24)
preserves all earlier labels and review evidence. Accepted NBA roles are
**2,400 training and all 960 checkpoint validation**; validation labels remain
excluded from gradient fitting. **Two fixed SAC–MEM episodes totaling 479
judgments remain unaccepted**, including NBA23. The other fixed episode contains
**240 judgments** without proposals. Curated coverage remains
**868/1,273 accepted, 760 eligible centers and 405 uncovered**, evaluation-only.

Next is Ryan's acceptance or correction of the complete 239 NBA23 judgments.
Complete accepted source/label/role manifests and the executable recipe still
need freezing before the approved fit. Fitting, checkpoint scoring, protected
evaluation, model-output acceptance and ball-phase completion remain closed.
