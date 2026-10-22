# Completion campaign: reference batch 03

Ryan requested continued execution of the approved plan after accepting both
120-frame campaign batches. Work began on clean `codex/ball-detector-baseline`
at `ef4f2668e8f8c10ae6af1cf356baffa8fe155bd0`. Both accepted publications and
their separate acceptance receipts were verified unchanged.

This batch contains **131 new P002 proposals, frames 368–498 inclusive**, through
the actual clip final. It is the earliest remaining uncovered contiguous run of
at least 120 frames in possession order. The whole run was selected from the
accepted inventory before inspecting source pixels, without using model errors.

## Complete review and acceptance

The [review page](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_03/review_v1/index.html)
contains the complete **5.24-second native** and **26.2-second slow** overlays,
frame controls, all 131 judgments, uncertainty rings and unmarked source crops
for exceptions. Both videos include the actual final frame 498. Native source
PTS spans **[14.76,20.00) seconds**, while clip-relative time is **[14.72,19.96)**.
Every native frame is included once at each playback speed.

The sequence includes a shot, prolonged rim/net overlap, retrieval, pass and
dribble. There are **114 proposed centers** with **4–10-source-pixel uncertainty**
and **17 null centers**. Visibility counts are 34 fully visible, 84 partially
visible, nine not visible and four indeterminate. The exceptions are:

- Certain occlusion, no geometry: 431–438 and 470.
- Visible fragments with no defensible complete-ball center: 408–409, 413, 440.
- Indeterminate visibility and no geometry: 410–412 and 439.

Centers come from current source pixels, without model predictions or temporal
interpolation. Uncertainty is an AI point-placement estimate, not a calibrated
statistical interval. The legacy `human_amodal_estimate` enum describes the
complete-ball target convention; AI authorship remains explicit.

Ryan explicitly answered **“Accept all 131 proposals”** after delivery of the
complete overlay and exceptions. The [later acceptance receipt](../configs/ball_tracking/reviews/ball_completion_reference_batch_03_acceptance_v0_1.json)
records that decision. A separate [accepted publication](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_03/accepted/reference.json)
retains all 131 annotations and native-frame records, including all 17 nulls.
All 560 prior accepted references remain unchanged. Current coverage is now
**691/1,273**, with **582** permitted positions uncovered and 625 eligible centers.
The [current inventory](../data/outputs/ball_tracking/completion_campaign_v0_1/accepted_reference_inventory_after_batch_03.json)
records that state. Metadata integration verifies exact publication/proposal
agreement and rejects future re-proposal of these accepted frames.

The original [proposal](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_03/proposal.json),
review media/page, config and preparation result retain their historical pending
status unchanged. The later receipt is the acceptance authority; no repeat
review is needed. Acceptance does not authorize fitting, final model trajectories
or protected evaluation.

## Preservation and validation

Source preparation seeks to the verified keyframe at 250, after the protected
P002 band 175–249. Every submitted encoded packet and decoded frame is guarded;
only permitted frames 250–498 are decoded, and only selected frames 368–498 are
saved. Independent comparison remuxes only those 249 permitted packets into a
bounded copy, checking every payload hash and PTS before OpenCV decodes it.
All 131 saved PNGs match exactly, with zero pixel or native-time mismatches.
Both decoders may share FFmpeg internals; packet boundaries are explicitly
checked. No protected packet was submitted or copied and no protected output
frame was decoded. The exact source, selection and audit are bound in the result.

All 560 accepted rows across 15 authorities were rebuilt and verified unchanged.
The renderer and annotation parser are unchanged from the starting commit.
The prior ten focused tests remain evidence for that implementation; no test
suite was repeated. New checks use actual batch-03 source, proposal, manifest
and emitted-media records, including all **262 encoded frames**, **228 localized
marker regions**, native timing, frame census and both actual finals.

Every source frame and proposed overlay was inspected. Original drafts and
refinements remain separate. An independent source-only reader disagreed with
six first-reader net-overlap center estimates. The final proposals conservatively
keep null geometry for 408–413 and indeterminate visibility for 410–412; the
initial estimates and disagreement remain in the inspection records. Frame 414
uses a complete-ball estimate [1041,139] with 10-pixel uncertainty; the independent
estimate [1038,145] is retained as a reader difference. These are AI judgments
accepted by Ryan as references, not independently established ground truth.

A first attempt at the preservation audit used the wrong row-count field for
the gap-reference authority. The helper was corrected and the failed attempt
preserved. No labels, model results or prior evidence changed as a consequence.
The [result receipt](../configs/ball_tracking/reviews/ball_completion_reference_batch_03_result_v0_1.json)
binds all exact inputs, proposals, media and checks. Generated media, source
PNGs and label artifacts remain ignored by Git.

No fitting, inference, model scoring, threshold change or player-pipeline rerun
occurred. Protected evaluation remains closed until a frozen method and separate
explicit authorization. The campaign and its ball-quality criteria remain
approved, and this batch's reference review is complete. Continue the fixed
reference package with all three accepted campaign publications in duplicate
guards; remaining new labels still require acceptance.
