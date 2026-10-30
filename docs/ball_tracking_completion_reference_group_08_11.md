# Completion campaign: P001 reference group 08–11

> **Accepted 2026-10-25:** Ryan accepted all 65 judgments with “clips review.
> please move forward” after the all-65 question. The [separate acceptance
> publication](#human-acceptance-published-2026-10-25) below supersedes the
> pending status and totals in this preserved original review record.

This group supplies **65 pending P001 judgments**, all with centers: **57
partially visible, eight fully visible and 6–9px uncertainty**. It covers four
separate ranges, **0–17, 75–89, 93–99 and 225–249**. Source preparation, all
four renders, final encoded inspection and integration pass. The
[group review page](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_08_11/review_v1/index.html)
is ready for Ryan's acceptance or corrections. These new labels remain pending.

The fixed NBA selection is already complete: [NBA24's acceptance](ball_tracking_completion_nba_reference_batch_24.md#human-acceptance-published-2026-10-25)
brings it to **3,839 accepted judgments, 3,423 centers and 416 nulls**. That
completes NBA reference preparation, not the whole reference package. Curated
coverage remains **868/1,273 accepted**, including **760 eligible centers**.
Of the **405 unaccepted curated judgments**, these **65 have pending proposals**
and **340 still lack proposals**.

## Scope and review clips

The [selection record](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_08_11/selection.json)
chooses missing P001 frames from accepted coverage before inspecting pixels.
Previously accepted frames are not relabeled. Four configurations retain their
own frame ranges and evidence while sharing one review group.

| Batch and config | Native frames | Centers | Visibility | Native / slow duration |
| --- | --- | ---: | --- | --- |
| [08](../configs/ball_tracking/completion_campaign/reference_batch_08_v0_1.json) | 0–17 | 18 | 18 partial | 0.72s / 3.60s |
| [09](../configs/ball_tracking/completion_campaign/reference_batch_09_v0_1.json) | 75–89 | 15 | 15 partial | 0.60s / 3.00s |
| [10](../configs/ball_tracking/completion_campaign/reference_batch_10_v0_1.json) | 93–99 | 7 | 7 partial | 0.28s / 1.40s |
| [11](../configs/ball_tracking/completion_campaign/reference_batch_11_v0_1.json) | 225–249 | 25 | 17 partial, 8 full | 1.00s / 5.00s |

The result records for [08](../configs/ball_tracking/reviews/ball_completion_reference_batch_08_result_v0_1.json),
[09](../configs/ball_tracking/reviews/ball_completion_reference_batch_09_result_v0_1.json),
[10](../configs/ball_tracking/reviews/ball_completion_reference_batch_10_result_v0_1.json)
and [11](../configs/ball_tracking/reviews/ball_completion_reference_batch_11_result_v0_1.json)
bind each batch's source, annotations, media and completed inspection evidence.

The individual review pages for [08](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_08/review_v1/index.html),
[09](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_09/review_v1/index.html),
[10](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_10/review_v1/index.html)
and [11](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_11/review_v1/index.html)
provide complete native overlays at **25 fps** and slow overlays at **5 fps**.
The ranges are separate clips, not one continuous trajectory. Their selected
final frames are **17, 89, 99 and 249**; possession final **498** is distinct.
Native timebase is **1/12800**, with **512 ticks per frame**; source frame 0
starts at PTS **512**, so native timestamps are **0.04 seconds** ahead of
clip-relative time. Both intervals remain explicit in each result.

Current-source visual proposals preserve hand/arm overlap, soft edges and
amodal uncertainty. A partially hidden center estimates the complete ball,
not the center of its exposed fragment. AI authorship remains explicit even
where the legacy geometry-source enum reads `human_amodal_estimate`. The
uncertainty is a placement estimate, not a calibrated confidence interval.
No interpolation or model coordinates are used. There are **no null centers**
in this group; that does not remove uncertainty from its partial-ball judgments.

## Source transport and preservation

The [source preparation and pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_08_11/source_preparation_and_pixel_audit.json)
passes **65 exact saved-PNG/RGB comparisons** in **16.688 seconds**, preserving
all **868 accepted curated rows** and their authorities. Primary and alternate
paths each decode source frames **0–249**; only the selected **65 frames** are
saved for labeling. Packet payloads and timestamps are checked. Both paths use
FFmpeg components, so agreement verifies transport rather than independent
ground truth.

The permitted decoder context stays before protected P001 frames **275–349**.
The audit records **zero protected packets submitted or copied** and **zero
protected output frames decoded**. These references retain the
`post_selection_evaluation_only` role. Both training and checkpoint-selection
eligibility remain false, including after any future label acceptance.

All four renders succeeded in **3.640, 3.140, 1.843 and 4.703 seconds**, respectively.
The original render records retain their then-current
`rendered_awaiting_final_visual_check` status; the separate completed evidence
below records the later inspection without rewriting that history.

## Complete inspection and validation

The [final visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_08_11/final_visual_inspection.json)
binds team inspection of every selected source frame and root inspection of all
**eight actual encoded crop sheets**, covering **all 65 centers**. Root also
inspected **all eight native/slow encoded finals** and full source finals
**17, 89, 99 and 249**. Final 249 retains **[333,303] ±6 pixels**, fully visible.
This is frame-by-frame AI image inspection, not a claim of browser playback
telemetry or human acceptance.

The [integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_08_11/integration_audit.json)
passes its first execution in **4.687 seconds**. Actual producer/source/media
checks cover **65 source RGB hashes, 130 encoded frames and their finals,
65 exact encoded crop joins and 242 file bindings**. All **868 accepted curated
rows and 27 accepted authority bindings** remain preserved; **zero new labels**
are accepted. Production implementation and tests are unchanged; actual-record
checks ran without repeating the focused tests or full suite.

The [first delivery-helper attempt](../data/outputs/t/curated_group_08_11_delivery_helper_attempt_01.json)
failed syntax validation before execution with
`SyntaxError: f-string: single closing brace is not allowed`. An unescaped
JavaScript closing brace in the HTML f-string caused the error. The failed
helper snapshot is retained; that attempt performed **zero source pixel reads,
label changes or renders**. The corrected helper then produced the four reviews.

Batches [09](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_09/inspection_receipt_part_75_89.json)
and [10](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_10/inspection_receipt_part_93_99.json)
preserve initial and refined point-review sheets after small adjustments from
magnified source inspection. Only their final coordinates enter the proposals.
The completed encoded review required **no further annotation corrections**.
Generated labels, PNGs and videos remain local ignored artifacts.

## Next decision

Obtain Ryan's acceptance or corrections for all **65 judgments**, including
their **6–9px uncertainty**. Acceptance is
pending; the **868 accepted curated references** and all **3,839 accepted NBA
judgments** remain the current inventory. Accepting the complete group would
bring curated coverage to **933/1,273**, with **825 eligible centers** and
**340 still unaccepted**; these are prospective totals, not current acceptance.

Continue the **340 permitted curated judgments without proposals** and obtain
acceptance of all remaining curated labels. The approved
[milestone 2](ball_tracking_completion_plan.md#delivery-resources-and-sequence)
requires complete permitted curated references and the fixed NBA package before
freezing source/label/role manifests and the executable recipe for the approved
fit. No completion-campaign fit, checkpoint scoring, protected evaluation,
model-output acceptance or ball-phase completion is claimed.

## Human acceptance published 2026-10-25

Ryan's exact **“clips review. please move forward”** accepts all **65 P001
judgments**, including **57 partial/eight full visibility judgments and 6–9px
uncertainty**. The acceptance date is **2026-10-25, America/Phoenix**; exact
user-event UTC is null. Separate receipts for
[08](../configs/ball_tracking/reviews/ball_completion_reference_batch_08_acceptance_v0_1.json),
[09](../configs/ball_tracking/reviews/ball_completion_reference_batch_09_acceptance_v0_1.json),
[10](../configs/ball_tracking/reviews/ball_completion_reference_batch_10_acceptance_v0_1.json)
and [11](../configs/ball_tracking/reviews/ball_completion_reference_batch_11_acceptance_v0_1.json)
record one grouped human decision. Publication times do not substitute for an
unknown user timestamp. AI authorship, geometry and uncertainty are unchanged;
no independent human annotation or playback telemetry is claimed.

The [inventory after batch 11](../data/outputs/ball_tracking/completion_campaign_v0_1/accepted_reference_inventory_after_batch_11.json)
contains **933/1,273 accepted rows**, with **825 localization-eligible centers**
and **340 remaining**. It retains **107 null geometries and one existing
geometry excluded from localization scoring**, P002 frame 335. That row is
unchanged from the previous 868; eligibility and missing geometry are distinct.
All **868 prior rows, 65 new annotations/native-frame records and 305 original
files** remain unchanged. The **3,839 accepted NBA judgments** are unchanged.

The [publication audit](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batches_08_11_acceptance/publication_audit.json)
confirms all four actual accepted-publication and inventory readers, exact
native-frame joins and duplicate guards. Its first helper failed after
**1.559 seconds**, after all four validated publications were written, because
it incorrectly expected 108 nulls. The
[preserved failed attempt](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batches_08_11_acceptance/publication_attempt_01_failed.json)
and original helper remain intact. A separate **0.524-second metadata recovery**
validated the correct census and original files without rewriting any accepted
publication, receipt, inventory or label. The audit also retains a read-only
file-discovery access error. No prior tests were repeated; no source pixels,
model inference, fitting or scoring were executed during publication.

These accepted references remain `post_selection_evaluation_only`; both
training and checkpoint-selection eligibility stay false. Continue the
[next curated group 12–16](ball_tracking_completion_reference_group_12_16.md)
and remaining permitted coverage before freezing the complete package and
executable recipe. Protected evaluation and ball-phase acceptance remain closed.
