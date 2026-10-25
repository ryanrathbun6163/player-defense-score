# Completion campaign: final permitted curated reference group 17–23

The [complete review](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_17_23/review_v1/index.html)
contains all **269 remaining permitted curated judgments**: **221 centers and 48 unknown centers**, with **5–10px uncertainty**.
All seven overlays, actual final frames and integration checks pass. Ryan's
acceptance remains pending; no new labels are accepted by this report.

Ryan's [acceptance of group 12–16](ball_tracking_completion_reference_group_12_16.md#human-acceptance-published-2026-10-25)
is published separately. All **1,004 accepted curated judgments** and **3,839
accepted NBA judgments** remain unchanged. Accepting this entire group would
complete **1,273/1,273 permitted curated references**. The **225 protected
positions remain closed**. These completion-campaign curated references are
evaluation-only, excluded from fitting and checkpoint selection; existing
historical training/development roles are unchanged.

## Complete review scope

The seven disjoint clips total **10.76 seconds at native 25fps**, or **53.8
seconds at slow 5fps**. They are separate source ranges, not one continuous
trajectory. Review each through its actual selected final: **374, 498, 224,
331, 360, 415 and 499**. Batches 18 and 23 reach their full-source finals
498 and 499 respectively; other selected finals are earlier.

| Batch/config | Possession and native frames | Centers | Unknown | Visibility | Uncertainty |
| --- | --- | ---: | ---: | --- | --- |
| [17](../configs/ball_tracking/completion_campaign/reference_batch_17_v0_1.json) | P001 350–374 | 25 | 0 | 25 partial | 6–9px |
| [18](../configs/ball_tracking/completion_campaign/reference_batch_18_v0_1.json) | P001 400–498 | 67 | 32 | 73 partial, 17 not visible, 7 indeterminate, 2 full | 6–10px |
| [19](../configs/ball_tracking/completion_campaign/reference_batch_19_v0_1.json) | P003 222–224 | 3 | 0 | 3 partial | 5px |
| [20](../configs/ball_tracking/completion_campaign/reference_batch_20_v0_1.json) | P003 325–331 | 7 | 0 | 7 partial | 7px |
| [21](../configs/ball_tracking/completion_campaign/reference_batch_21_v0_1.json) | P003 336–360 | 11 | 14 | 13 partial, 10 not visible, 1 full, 1 indeterminate | 7–9px |
| [22](../configs/ball_tracking/completion_campaign/reference_batch_22_v0_1.json) | P003 365–415 | 49 | 2 | 44 partial, 7 full | 5–8px |
| [23](../configs/ball_tracking/completion_campaign/reference_batch_23_v0_1.json) | P003 441–499 | 59 | 0 | 50 partial, 9 full | 6–8px |

Total visibility: **215 partial, 27 not visible, 8 indeterminate, 19 full**. Uncertainty describes placement ambiguity; it is
not a calibrated confidence interval. Partly visible fragments can remain
unlocalized when they do not support a whole-ball midpoint. No model
coordinates or interpolation supply the proposals.

Each [batch result](../configs/ball_tracking/reviews/ball_completion_reference_batch_17_result_v0_1.json)
binds its source records, proposal, actual media and final inspection. Individual
review pages include frame controls, native and slow overlays, every judgment
and source crops for unknown centers. Null-center source frames are:

- Batch 18: 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 461, 464, 465, 466, 467, 468, 476.
- Batch 21: 336, 337, 338, 339, 340, 341, 342, 343, 350, 351, 352, 353, 354, 355.
- Batch 22: 391, 392.

## Source preparation and preserved limitations

The [selection](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_17_23/selection.json)
was fixed from missing permitted coverage before pixels. The successful
[preparation](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_17_23/source_preparation_and_pixel_audit.json)
took **60.625 seconds**, verifying **269 exact RGB/PNG matches**, including
**eight exact matches to earlier bound native PNGs**. All 1,004 accepted rows
and their authorities are unchanged. P001 native PTS starts at 512 and P003
at zero, both at timebase **1/12800** with **512 ticks per frame**.

Extraction reuses the established guarded permitted-segment reader. The
comparison retains original timestamps and trims to the selected native PTS.
Only permitted frames are saved or exposed in the successful preparation.
Interframe codec internals are uninstrumented and may use internal reference
frames; this is not a zero-protected-packet claim. Earlier stricter prefix
receipts remain unchanged. Both paths share FFmpeg components, so equality
checks transport rather than independent ground truth.

The [first attempt](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_17_23/source_preparation_failed_attempt_01.json)
failed after **6.343 seconds** on the first alternate-seek equality check.
It had saved 25 guarded P001350–374 PNGs; the retry verified and preserved them.
One untrimmed comparison frame was read and hashed, but its native identity
was never established. It could have been an adjacent protected position.
It was not displayed, saved, labeled, scored or supplied to a model.
The [additive clarification](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_17_23/failed_attempt_scope_clarification.json)
therefore supersedes the failed receipt's unverified initialized zero-output
count. The bounded [native-PTS diagnostic](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_17_23/source_seek_diagnostic_02/receipt.json)
and successful retry establish permitted output identities. Protected
reference review and evaluation remain unopened; no protected basketball
judgment was made.

## Annotation and delivered-media checks

AI authorship is explicit. Every proposed source frame and point crop was
inspected before rendering. Original drafts remain preserved. P003331's center
was refined from [278,668] to [282,669] during crop inspection, retaining 7px
uncertainty. Batches 19 and 20 initially failed parser checks because difficulty
tags were unsorted. Their original files and four failed preflight operations
are retained in each `failed_transport_attempt_01` directory. Sorting tags
changed no coordinates, visibility or uncertainty; both corrected renders pass.
Batch 22 separately preserves a sorted-tag writer failure before any proposal
write; its failed helper/receipt and corrected helper are retained, with the
unrecorded failure runtime left unknown. Source-based refinements at P003
368–370 are preserved as a separate part revision. Root's proposed-overlay
review refined P003446 from [1088,459] to [1088,452] and final499 from
[1009,476] to [1007,464], with final499 uncertainty increased to 8px.
The original proposals and revised-image inspection remain bound. Batch18
retains both annotator parts and receipts rather than claiming one person
independently annotated all 99 frames.

The [final visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_17_23/final_visual_inspection.json)
records every delivered crop sheet, all 14 native/slow encoded finals and all
seven full-size selected source-final frames. It is AI inspection, not Ryan's acceptance or a claim
of full-playback telemetry. The [integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_17_23/integration_audit.json)
passes in **18.000 seconds**: **269 source/annotation joins,
538 encoded frames and their finals, 221 exact encoded-center crop joins**, source/null-context
crop joins and **744 bound artifacts**. Accepted references remain unchanged.
Production source and tests are unchanged; actual emitted records/media are
checked without repeating the historical test suite.

No inference, fitting, checkpoint scoring or phase acceptance ran. Following
Ryan's acceptance or corrections, freeze the full reference/role manifests and
executable recipe before the already-approved fit. Protected evaluation still
requires a frozen method and separate explicit authorization.
