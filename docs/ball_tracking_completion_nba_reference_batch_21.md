# Completion campaign: NBA reference batch 21

**Accepted on 2026-10-24.** Ryan accepted all 120 judgments; the
[separate publication](#human-acceptance-published-2026-10-24) below supersedes
the original pending status. The preparation record remains preserved.

NBA20 is accepted, bringing NBA coverage to **3,120/3,839 judgments: 2,803
centers and 317 nulls**. This increment prepares the next fixed training episode,
SAC–MEM e03, native frames **106690–106809**. Its **120 pending judgments**
contain **75 centers and 45 nulls**, with **6–10px center uncertainty**. Source
and proposal inspection, complete encoded review and final integration pass.
NBA21 is ready for Ryan's acceptance or corrections; no NBA21 label has been
accepted.

## Fixed role and native timing

The [configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_21_v0_1.json)
retains episode `sac-mem-0022500829_e03` and the unchanged
[source roles](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json).
SAC–MEM was assigned training before new model predictions. Both eligibility
flags remain false pending reference acceptance.

The **1920×1080** full source contains **357,233 frames**, with timebase
**1/90000**. The fixed selection window is **[1780,1782) seconds**. Selected
native PTS span **160200422–160379072**; the final presentation ends at
**160380602**, giving **2.002 seconds** of native playback. Actual presentation
intervals remain **16/17ms**, derived from the next global PTS; raw packet
durations stay separate. Batch final **106809** differs from full-source final
**357232**. Nominal 60 fps is annotation-bounds metadata, not a replacement for
actual presentation timing.

## Source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/preparation.json)
and [pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/source_pixel_audit.json)
pass **120 exact native PNG/PTS checks** in **61.298 seconds**, preserving
**6,455 preexisting files**. Primary decoding returned **357 frames,
106453–106809**, after **359 submitted packets**. The **237 decoded prefix
frames, 106453–106689**, inherit the fixed training role; only selected frames
106690–106809 were saved. Secondary conversion emitted **120 RGB frames** and
reported **120 filter frames**, exactly the selected range. Both paths use
FFmpeg components; matching pixels verify transport rather than independent
ground truth.

## Proposals and inspection

Visibility comprises **84 partially visible, 19 indeterminate, 14 not visible
and three fully visible judgments**. Unknown centers remain at **106708–106721,
106739–106746 and 106757–106779**, without interpolation. Severe rectangular
compression blocks merge with the ball, hands, defender or floor during the
dribble. Visible fragments alone do not always support a defensible center;
unsupported centers remain null.

| Native frames | Centers | Nulls | Inspection receipt |
| --- | ---: | ---: | --- |
| 106690–106729 | 26 | 14 | [First part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/inspection/part_106690_106729_receipt.json) |
| 106730–106769 | 19 | 21 | [Middle part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/inspection/part_106730_106769_receipt.json) |
| 106770–106809 | 30 | 10 | [Final part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/inspection/part_106770_106809_receipt.json) |

The team inspected every current source and proposed overlay frame, including
full part endpoints. Final 106809 retains **[700,167] ±9 pixels**, fully visible:
the released ball is separated from the shooting hand, with blur and compression
preserved as uncertainty. These are AI-assisted proposals and AI visual checks,
not independent human ground truth. No interpolation or model prediction
supplied coordinates.

The initial root inspection ROI was insufficient and remains retained. Complete
proper precision coverage was inspected before annotation. The three receipts
record no annotation corrections or failed annotation-helper attempts; original
drafts remain preserved.

## Complete review and validation

The [complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/review_v1/index.html)
includes the [native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/review_v1/review_native.mp4)
and [slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/review_v1/review_slow.mp4),
the [proposal](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/proposal.json)
and [exception list](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/review_v1/exception_list.json).
The [delivery record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/review_v1/delivery_result.json)
passes its first attempt in **37.609 seconds**. Each video contains all **120
frames**: native playback retains **2.002 seconds** of actual timing; slow
playback lasts **12 seconds at 10 fps**.

The [completed visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/root_visual_review.json)
records actual inspection of all **ten emitted/source sheets**, covering all
**75 localized center crops and 45 null contexts**, plus the full source final
106809 and the native/slow actual encoded finals. No geometry correction was
needed after initial part publication. The delivery receipt retains its earlier
awaiting-inspection state; the later visual receipt records completion.

The initial HTML inferred a high pass. The final source frame did not support
that classification, so the [retained prose revision](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/scene_text_revision_01/revision.json)
uses “raises and releases the ball.” Original HTML, delivery and completion
records remain preserved. This correction changes no annotations and reencodes
no media.

The [current focused receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/focused_validation/20261024T205753Z_1242cce8/references.json)
passes **ten renderer tests** against NBA21's actual proposal and media in
**26.937 seconds**, with no failures, errors or skips. NBA19's **eight acceptance
tests** remain historical coverage of unchanged reader/test code. A separate
[actual pending-consumer check](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/finalization_attempts/20261024T210525Z_f78fbbba/pending_review_reader_check.json)
validates all **120 annotation/native joins**, accepting no new labels. No new
eight-test execution is claimed.

The first finalizer completes in **61.406 seconds**, including a **50.203-second
[integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/integration_audit.json)**
of **6,947 bindings, 120 native joins, 240 encoded frames, 150 markers and 120
exact source PNGs**. All **3,120 accepted NBA rows, 868 curated references and
6,455 preexisting preparation files** remain unchanged. The
[final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_21_result_v0_1.json)
records `ready_for_human_reference_acceptance`, with human acceptance null and
both eligibility flags false. The finalizer performs no source pixel decoding,
model inference, fitting or scoring.

## Campaign status and next decision

[NBA20's separate acceptance](ball_tracking_completion_nba_reference_batch_20.md#human-acceptance-published-2026-10-24)
preserves all earlier labels and review evidence. Accepted NBA roles are
**2,160 training and all 960 checkpoint validation**; validation labels remain
excluded from gradient fitting. **Four fixed SAC–MEM episodes totaling 719
judgments remain unaccepted**, including NBA21. The other **three episodes
contain 599 judgments** without proposals. Curated coverage remains
**868/1,273 accepted, 760 eligible centers and 405 uncovered**, evaluation-only.

Next is Ryan's acceptance or correction of the complete 120 NBA21 judgments.
Complete accepted source/label/role manifests and the executable recipe still
need freezing before the approved fit. Fitting, checkpoint scoring, protected
evaluation, model-output acceptance and ball-phase completion remain closed.

## Human acceptance published 2026-10-24

Ryan's structured reply **“Accept all 120 proposals”** accepts the complete
NBA21 review. The [separate acceptance receipt](../configs/ball_tracking/reviews/nba_completion_reference_batch_21_acceptance_v0_1.json)
and [accepted reference publication](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/accepted/reference.json)
record all **120 SAC–MEM e03 judgments**, native frames **106690–106809**,
including **75 centers, 45 nulls and 6–10px uncertainty**. All visibility
judgments, null intervals, uncertainty, AI authorship and original annotations
remain unchanged. Acceptance date is **2026-10-24, America/Phoenix**; exact
user-event UTC is null and publication time is separate. No playback telemetry
or independent human annotation is claimed.

The [publication audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_21/acceptance_audit/publication_audit.json)
passes its first attempt in **228.018 seconds**, including the actual SAC
publication and mixed-inventory readers and duplicate native-frame guard. It
preserves **6,875 original files, all 3,120 prior NBA rows and all 868 curated
references**. The unchanged publisher reuses NBA19's completed eight-test receipt
solely as historical coverage of unchanged reader/test code, while separately
validating NBA21's current pending-consumer evidence and accepted publication.
No tests, source decoding, model inference, fitting or scoring ran in publication.

The [inventory after NBA21](../data/outputs/ball_tracking/completion_campaign_v0_1/accepted_nba_reference_inventory_after_batch_21.json)
contains **3,240/3,839 accepted judgments: 2,878 centers and 362 nulls**. Roles
are **2,280 training and all 960 checkpoint validation**; validation labels remain
excluded from gradient fitting. Three fixed SAC–MEM training episodes remain,
totaling **599 judgments**. NBA22 proceeds with e04. Curated coverage remains
**868 accepted, 760 eligible centers and 405 uncovered**, evaluation-only.

Acceptance grants label-level training eligibility only. Complete accepted
source/label/role manifests and the executable recipe still need freezing before
the approved fit. Fitting, checkpoint scoring, protected evaluation, model-output
acceptance and ball-phase completion remain closed. Original review evidence,
the retained insufficient ROI and the prose correction remain preserved.
