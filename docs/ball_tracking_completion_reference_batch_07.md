# Completion campaign: reference batch 07

Work began on clean `codex/ball-detector-baseline` at
`034893b75af658cde22817c14f4e5a5f7dc7bb1c`. All **766 accepted references** and
four campaign acceptance receipts remain unchanged. Batches 05 and 06 still
await explicit human acceptance; their 73 proposals were excluded from new
selection without being promoted to accepted labels.

This batch contains **29 P001 proposals, frames 21–49 inclusive**, selected from
coverage and packet metadata before source inspection. It is the longest
remaining contiguous uncovered run with a permitted preceding keyframe after
excluding the two pending batches. Entry is at keyframe 0, before the protected
P001 band at 275–349.

## Complete review

The [review page](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_07/review_v1/index.html)
contains every frame in a **1.16-second native-speed** and **5.80-second slow
overlay**, frame controls, all judgments and unmarked source crops for the
exceptions. Frame 49 is this batch's final, not possession final 498. Native
selected time is **[0.88,2.04) seconds**, distinct from clip-relative
**[0.84,2.00)**: P001 frame 0 has PTS 512 at timebase 1/12800.

The sequence shows held-ball handling, self-occlusion behind the player and
reappearance beside his forearm. There are **10 proposed centers**, with
**7–10-source-pixel uncertainty**, and **19 null centers**:

- Frames 24 and 40–42: visible fragments without a defensible complete-ball center.
- Frames 25–26 and 39: ambiguous hand/ball fragments, visibility indeterminate.
- Frames 27–38: ball hidden behind the player's body.

Visibility counts are 14 partial, three indeterminate and 12 not visible.
Centers at 21–23 and 43–49 estimate the complete ball, so a center can lie over
the occluding forearm. They are not centroids of the exposed fragment. Current
source pixels support the judgments; hidden coordinates were not interpolated.
Uncertainty is an AI placement estimate, not a calibrated confidence interval.
AI authorship remains explicit, including where the legacy geometry enum is
`human_amodal_estimate`. Original draft proposals remain final without revisions.

Ryan's acceptance is pending. Accepted coverage remains **766/1,273**, including
**683 eligible centers**, with **507** positions without accepted labels. Batches
05–07 now supply **102 pending proposals**; **405** positions have neither an
accepted label nor a current proposal. Accepting batch 07 alone would produce
795 accepted judgments and leave 478 uncovered. These curated references remain
evaluation-only and cannot enter fitting or checkpoint selection.

## Validation and preservation

Primary decoding returned frames 0–49 from 52 submitted packets with maximum
presentation index 52. Alternate comparison copied exactly 53 original packets
0–52, verified their payloads and PTS/DTS before decoding, and returned only
frames 0–49. All **29 selected native PNGs match exactly**. Both decoders may
share FFmpeg internals; no protected packet was submitted or copied, and no
protected output frame was decoded.

All source frames, encoded center crops, null-center context crops and the
complete encoded final frame were visually inspected. Checks cover **58 encoded
frames**, **20 localized markers**, **1,129 file bindings**, exact source and
annotation joins, all review links and **1,011 unchanged prior campaign files**.
These establish record/media integrity, not human acceptance or ground truth.

A separate metadata-only [record audit](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_07/independent_record_review.json)
passes 35 checks and verifies 133 directly relevant file bindings. It reconstructs
accepted coverage and pending-batch separation, confirms every null exception
and checks actual video frame counts/timing without another pixel decode.

Source preparation, pixel comparison, labeling and rendering completed without
failed execution attempts. A helper-transformation guard failed before writing
the new delivery helper because an expected lowercase phrase was absent; its
failure and elapsed time are retained. A stale helper-provenance path was also
corrected before execution. No annotations or media were changed to pass checks.
Production code and tests are unchanged; prior focused tests were not repeated.

The [preparation result](../configs/ball_tracking/reviews/ball_completion_reference_batch_07_result_v0_1.json)
binds the proposals, source/media audits and visual inspection receipts. Generated
labels, PNGs and videos remain ignored by Git. No fitting, inference, model
scoring, threshold changes or player reruns occurred. The approved campaign and
numerical criteria remain in force. Protected evaluation stays closed until a
frozen method and separate explicit authorization.

The fixed NBA training package is still ahead. Metadata verification identifies
`chi-vs-ind-0022400868_e01` as its first episode: 120 native 1280×720 frames,
indices 0–119, with timebase 1/60000 and training role already fixed in the
[source manifest](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json).
Its new native PNGs and labels have not been prepared. The legacy NBA package
reader fixes timebase 1/90000; the new package must preserve this source's actual
timing and role rather than reuse that assumption.
