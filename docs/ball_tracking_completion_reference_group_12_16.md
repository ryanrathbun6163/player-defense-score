# Completion campaign: P002/P003 reference group 12–16

This group prepares **71 pending judgments**, all with centers: **51 partially
visible, 20 fully visible and 5–9px uncertainty**. Source preparation and five
renders, complete encoded inspection and integration pass. The
[group review page](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_12_16/review_v1/index.html)
is ready for Ryan's acceptance or corrections; all 71 judgments remain pending.

Ryan's [acceptance of group 08–11](ball_tracking_completion_reference_group_08_11.md#human-acceptance-published-2026-10-25)
brings curated coverage to **933/1,273**, with **825 localization-eligible
centers**. Of the **340 unaccepted judgments**, **71 have proposals and 269
still lack proposals**. All **3,839 fixed NBA judgments** are accepted and
unchanged. These new curated labels remain evaluation-only, with training and
checkpoint-selection eligibility false.

## Scope and review clips

The [selection record](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_12_16/selection.json)
chooses missing permitted coverage before pixel inspection. Previously accepted
frames are not relabeled. Each range retains its own configuration and review.

| Batch/config | Possession and native frames | Centers | Visibility | Uncertainty | Native / slow duration |
| --- | --- | ---: | --- | --- | --- |
| [12](../configs/ball_tracking/completion_campaign/reference_batch_12_v0_1.json) | P002 0–24 | 25 | 14 partial, 11 full | 5–6px | 1.00s / 5.00s |
| [13](../configs/ball_tracking/completion_campaign/reference_batch_13_v0_1.json) | P002 170–174 | 5 | 5 partial | 8–9px | 0.20s / 1.00s |
| [14](../configs/ball_tracking/completion_campaign/reference_batch_14_v0_1.json) | P003 175–192 | 18 | 9 partial, 9 full | 7–8px | 0.72s / 3.60s |
| [15](../configs/ball_tracking/completion_campaign/reference_batch_15_v0_1.json) | P003 196–203 | 8 | 8 partial | 6px | 0.32s / 1.60s |
| [16](../configs/ball_tracking/completion_campaign/reference_batch_16_v0_1.json) | P003 207–221 | 15 | 15 partial | 5px | 0.60s / 3.00s |

Individual review pages for [12](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_12/review_v1/index.html),
[13](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_13/review_v1/index.html),
[14](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_14/review_v1/index.html),
[15](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_15/review_v1/index.html)
and [16](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_16/review_v1/index.html)
provide complete native 25 fps and slow 5 fps overlays. These are separate ranges,
not one continuous trajectory. Selected finals **24, 174, 192, 203 and 221** remain
distinct from possession finals **498 (P002) and 499 (P003)**. The five slow
segments total **14.2 seconds**.

Both 1920×1080 sources have timebase **1/12800** and **512 ticks per frame**.
P002 frame 0 begins at PTS 512; P003 frame 0 begins at PTS 0. Each source's actual
offset is retained in native joins. Current-frame AI visual proposals preserve
hand overlap and source softness; uncertainty describes placement, not a
calibrated confidence interval. No interpolation or model coordinates are used.
All centers are supported by their current source frames; no unknown centers
are proposed in this group.

## Source preparation and retained failures

The [source preparation and pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_12_16/source_preparation_and_pixel_audit.json)
passes **71 exact saved-PNG/RGB comparisons** in **17.516 seconds**, preserving
all **933 accepted rows** and their authority bindings. Primary and alternate
paths retain permitted prefixes **P002 0–174** and **P003 0–221**; each drains
two already-buffered frames without submitting another packet. Only selected
frames are saved for annotation. The audit records **zero protected packets
submitted/copied and zero protected output frames decoded**. Protected ranges
remain **P002 175–249** and **P003 225–299**. Both paths use FFmpeg components;
agreement validates transport rather than independent ground truth.

The [first failed attempt](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_12_16/source_preparation_failed_attempt_01.json)
stopped after **0.610 seconds**, before pixel decoding, because it assumed
P003 shared P002's 512-tick starting offset. The
[second failed attempt](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_12_16/source_preparation_failed_attempt_02.json)
stopped after **6.453 seconds**, after normal P002 output 0–172, when raw codec
drain frames had `frame.time_base=None`. Its submitted packets remained permitted;
no protected output was decoded. The
[bounded diagnostic](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_12_16/decoder_drain_diagnostic.json)
confirms 175 permitted frames and valid drained PTS with stream timebase 1/12800.
The third helper preserves existing PNGs and uses that stream timebase for
drained-frame metadata. Both failed helpers, timings and diagnostic remain bound.

## Complete inspection and validation

All five render records retain their then-current
`rendered_awaiting_final_visual_check` status, with elapsed times **4.656,
1.375, 3.531, 1.797 and 3.093 seconds** for batches 12–16. Separate final evidence
records the later inspection without rewriting those original render records.
The result records for
[12](../configs/ball_tracking/reviews/ball_completion_reference_batch_12_result_v0_1.json),
[13](../configs/ball_tracking/reviews/ball_completion_reference_batch_13_result_v0_1.json),
[14](../configs/ball_tracking/reviews/ball_completion_reference_batch_14_result_v0_1.json),
[15](../configs/ball_tracking/reviews/ball_completion_reference_batch_15_result_v0_1.json)
and [16](../configs/ball_tracking/reviews/ball_completion_reference_batch_16_result_v0_1.json)
bind each batch's source, proposals, complete media and inspection evidence.

The [final visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_12_16/final_visual_inspection.json)
records team inspection of every current source/proposed frame and root
inspection of **all nine actual encoded crop sheets**, covering **all 71
centers**. Root also viewed **all ten native/slow actual final images** and
all five full selected source finals **24, 174, 192, 203 and 221**. Final P003
221 retains **[1619,583] ±5 pixels**, partially visible. No further annotation
corrections were needed. This is AI image inspection; no full-playback telemetry
or human acceptance is claimed.

The [integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_12_16/integration_audit.json)
passes its first execution in **4.750 seconds**. Actual producer/source/media
checks cover **71 source/annotation joins, 142 encoded frames and their finals,
71 exact encoded crop joins and 288 file bindings**. All **933 accepted rows**
remain unchanged and **zero new labels** are accepted. Production implementation
and tests are unchanged; actual-record validation ran without repeating tests.
Generated source images, annotations and videos remain ignored local artifacts.

## Next decision

Obtain Ryan's acceptance or corrections for these **71 judgments**, including
**5–9px uncertainty**. Accepting the complete group would bring curated coverage
to **1,004/1,273**, including **896 localization-eligible centers**, with **269
still unaccepted**; these are prospective totals. Then continue
the **269 permitted judgments without proposals**. All 340 remaining curated
judgments must be completed and accepted before freezing source/label/role
manifests and the executable recipe under the approved
[milestone 2](ball_tracking_completion_plan.md#delivery-resources-and-sequence).
The fixed NBA selection is complete; completing the curated references remains
part of the same approved reference-package work.
