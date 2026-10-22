# Completion campaign: reference batch 06

## Later acceptance: 2026-10-22

Ryan explicitly replied “Hold up I approve and accept. Move forward” after the
delivery summary identified batches 05–07 as 102 pending proposals. The grouped
decision accepts this batch's exact 30 judgments, centers and uncertainty. The
separate [acceptance receipt](../configs/ball_tracking/reviews/ball_completion_reference_batch_06_acceptance_v0_1.json)
binds the accepted publication; original proposals, native records, drafts and
media remain byte-identical. No invented form-option answer, playback telemetry
or independent human annotation is claimed. No repeat review is needed.

All three acceptances bring curated coverage to 868/1,273, including 760 eligible
centers, leaving 405 uncovered. Campaign references remain evaluation-only;
acceptance does not authorize final trajectories or protected evaluation.
The following preparation record retains its original pending-era context.

Work began on clean `codex/ball-detector-baseline` at
`e0fe1b87499031332b7b3ef6df520469d244ea34`. All **766 accepted references** and
four campaign acceptance receipts remain unchanged. Ryan requested continued
work; no explicit batch-05 acceptance had arrived. Its 43 pending proposals
were excluded from new selection without promoting them to accepted labels.

This batch contains **30 P003 proposals, frames 120–149 inclusive**. It is the
longest remaining uncovered contiguous run reachable from a permitted keyframe
after excluding batch 05. Selection used accepted coverage and packet metadata
before new source inspection, without model outputs. Keyframe 0 precedes the
protected P003 band at 225–299. Larger late gaps have no safe preceding keyframe
after their protected bands.

## Complete review

The [review page](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_06/review_v1/index.html)
contains every frame in a **1.20-second native-speed** and **6.00-second slow
overlay**, frame controls and all judgments. Frame 149 is the batch final;
the possession's actual final is 499. P003 timestamps start at zero: frame
index multiplied by 512 gives native PTS ticks at timebase 1/12800. Both the
native and clip-relative selected interval are **[4.80,6.00) seconds**.

The sequence shows held-ball handling with hand and forearm overlap, followed
by extension into a low dribble. All **30 frames have proposed centers**, with
**5–8-source-pixel uncertainty**. Visibility is partial in 27 frames and full
in three (146–148). There are no null-center exceptions. Original proposals
remain final, without geometry revisions.

Centers use current source pixels, not predictions or temporal interpolation.
Uncertainty is an AI point-placement estimate, not a calibrated confidence
interval. The legacy `human_amodal_estimate` enum describes the whole-ball
convention; AI authorship remains explicit.

Both batches 05 and 06 await separate human acceptance. Accepted coverage stays
**766/1,273**, including **683 eligible centers**, with **507** permitted positions
without accepted labels. The two pending batches contain 73 proposals; **434**
positions have neither accepted labels nor a current proposal. Accepting only
batch 06 would yield 796 accepted labels and 477 uncovered positions. Accepting
both would yield 839 accepted labels and 434 uncovered positions. These campaign
references remain evaluation-only, ineligible for fitting or checkpoint selection.

## Validation and preservation

Primary PyAV decoding returned outputs 0–149 using **152 packets**, with maximum
presentation index 153. Independent comparison copied **154 original packets,
0–153**, verified their payloads and PTS/DTS before decoding, and returned only
outputs 0–149 with OpenCV. All **30 selected native PNGs match exactly**. Both
decoders may share FFmpeg internals; all submitted and copied context remained
permitted. No protected packet was submitted or copied, and no protected output
frame was decoded.

AI visual checks cover every source frame and encoded crop, plus the complete
actual final frame 149. Both videos passed checks on all **60 encoded frames**
and **60 localized marker regions**. Integration verifies **1,023 file bindings**,
exact annotation/native-frame joins, all review-page links and preservation of
**935 prior campaign files**. These checks establish record/media integrity;
they do not establish independent ground truth or human acceptance.

A separate metadata-only [record audit](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_06/independent_record_review.json)
passes 31 checks and rehashes 105 directly relevant files. It reconstructs the
accepted inventory, verifies pending-batch separation and confirms both actual
video frame counts and timing without additional pixel decoding.

Source preparation, comparison and rendering succeeded on their first attempts.
One part-label helper initially expected a nonexistent `source_pts` field in
the PNG manifest and failed before writing a proposal. The original helper and
failure are preserved; its replacement reads the actual packet timing record.
No annotation or media was altered to pass a check. The renderer, parser and
tests are unchanged; prior focused tests were not rerun. Current validation
checks actual emitted records.

The [preparation result](../configs/ball_tracking/reviews/ball_completion_reference_batch_06_result_v0_1.json)
binds the exact proposals, source audits, media and inspection receipts.
Generated labels, PNGs and videos remain ignored by Git. No fitting, inference,
model scoring, threshold changes or player reruns occurred. Protected evaluation
remains closed pending a frozen method and separate explicit authorization.
The completion plan and numerical ball-quality criteria remain approved.
