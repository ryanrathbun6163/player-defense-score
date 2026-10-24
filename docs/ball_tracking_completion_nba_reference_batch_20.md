# Completion campaign: NBA reference batch 20

NBA19 is now accepted, bringing NBA coverage to **3,000/3,839 judgments: 2,698
centers and 302 nulls**. This increment prepares the next fixed training episode,
SAC–MEM e02, native frames **73603–73722**. Its **120 pending judgments** contain
**105 centers and 15 nulls**, with **6–9px center uncertainty**. Complete source,
proposal and encoded review includes every frame through actual final 73722.
Final validation passes; Ryan's reference acceptance remains pending. No NBA20
label has been accepted.

## Fixed role and native timing

The [configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_20_v0_1.json)
retains episode `sac-mem-0022500829_e02` and the unchanged
[source roles](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json).
SAC–MEM was assigned training before new model predictions. Both proposal
eligibility flags remain false pending Ryan's acceptance.

The **1920×1080** full source contains **357,233 frames**, timebase **1/90000**.
The fixed selection window is **[1228,1230) seconds**. Selected native PTS span
**110520242–110698892**; the final presentation ends at **110700422**, giving
**2.002 seconds** of native playback. Presentation intervals remain **16/17ms**,
derived from the next global PTS; raw packet duration stays separate. Batch
final **73722** differs from full-source final **357232**. Nominal 60 fps is
metadata for annotation bounds and does not replace actual presentation timing.

## Source preparation and preserved incidents

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/preparation.json)
and [pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/source_pixel_audit.json)
pass **120 exact native PNG/PTS checks** in **62.235 seconds**, preserving
**6,170 preexisting files**. Primary decoding returned **357 frames,
73366–73722**, after **359 submitted packets**. The **237 decoded prefix
frames, 73366–73602**, inherit the fixed training role; only selected frames
73603–73722 were saved. Secondary conversion emitted **120 RGB frames** and
reported **120 filter frames**, exactly the selected range. Both paths use
FFmpeg components; matching pixels verify transport rather than independent
ground truth.

The root annotation helper failed twice before publishing any draft. First,
the binding-only source record lacked `decoded_frames`; then the parser rejected
identity category `uncertain`. The successful third run used full source
metadata and the existing `ambiguous` category. Both failed helper snapshots
and incident records are retained in the
[first-part receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/inspection/part_73603_73642_receipt.json).
The first successful draft remains unchanged; no later annotation correction
or overwrite is claimed.

## Proposals and inspection

Visibility comprises **104 partially visible, six fully visible, seven not
visible and three indeterminate judgments**. Unknown centers remain at
**73613–73623, 73629–73630 and 73680–73681**, without interpolation.

| Native frames | Centers | Nulls | Inspection receipt |
| --- | ---: | ---: | --- |
| 73603–73642 | 27 | 13 | [First part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/inspection/part_73603_73642_receipt.json) |
| 73643–73682 | 38 | 2 | [Middle part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/inspection/part_73643_73682_receipt.json) |
| 73683–73722 | 40 | 0 | [Final part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/inspection/part_73683_73722_receipt.json) |

The team inspected every current source and proposed overlay frame, including
full part endpoints. Final 73722 retains **[183,580] ±7 pixels**, fully visible.
The coordinates and inspection are AI-assisted proposals, not independent human
ground truth. The original drafts, uncertainty and null judgments remain intact.

## Complete review and validation

- [Complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/review_v1/index.html)
- [Native overlay: 2.002 seconds with original variable timing](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/review_v1/review_native.mp4)
- [Slow overlay: 12 seconds at 10 fps](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/review_v1/review_slow.mp4)
- [All 120 proposals](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/proposal.json) and [15 null-center exceptions](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/review_v1/exception_list.json)
- [Review manifest](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/review_v1/manifest.json) and [delivery record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/review_v1/delivery_result.json)
- [Root visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/root_visual_review.json)

Delivery passes its first attempt in **35.703 seconds**. The native overlay
preserves the complete **2.002-second** presentation interval; the slow overlay
contains all 120 frames over **12 seconds at 10 fps**. Root inspected all ten
emitted/source sheets, all **105 localized centers and 15 unmarked null
contexts**, both actual encoded finals and the full unmarked source image
73722. The delivery record retains its original
`rendered_awaiting_root_visual_inspection` status; the later completed visual
receipt supersedes that status without overwriting it.

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_20_result_v0_1.json)
and [integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/integration_audit.json)
pass **6,604 bindings, 120 native joins, 240 encoded frames and 210 markers**,
plus all **120 exact source PNG matches**. Finalization passes its first attempt
in **47.922 seconds**, including the actual pending-review consumer check; the
integration audit takes **36.703 seconds**. The consumer validates all 120 joins
and creates zero accepted labels. Source preparation, delivery, visual review
and finalization retain their separate records.

The [current renderer receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_20/focused_validation/20261024T193054Z_b346c158/references.json)
records **ten tests passed on NBA20's actual proposal and media**, first attempt,
in **27.141 seconds**, with zero failures, errors or skips. The unchanged SAC
acceptance reader reuses NBA19's [completed eight-test receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/focused_validation/acceptance_complete.json).
Those are historical tests of the exact bound code, including actual NBA19
transport; no new eight-test execution is claimed. NBA20's current
pending-review consumer validation is separate evidence. No full-suite rerun,
model inference, fitting or checkpoint scoring occurred.

## Campaign status and next decision

[NBA19's separate acceptance](ball_tracking_completion_nba_reference_batch_19.md#human-acceptance-published-2026-10-24)
preserves all earlier accepted labels and originals. Current NBA roles are
**2,040 training and all 960 checkpoint validation**; validation labels remain
excluded from gradient fitting. **Five fixed SAC–MEM episodes totaling 839
judgments remain unaccepted**, including NBA20. The other **four episodes contain
719 judgments** without proposals. Curated coverage remains **868/1,273 accepted,
760 eligible centers and 405 uncovered**, evaluation-only.

Next is Ryan's acceptance or correction of these complete 120 judgments.
Complete accepted source/label/role manifests and the executable recipe must
still be frozen before the approved fit. No fitting, checkpoint scoring or
protected evaluation is authorized by this preparation; protected evaluation
requires a frozen method and separate explicit authorization.
