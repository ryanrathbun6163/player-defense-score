# Completion campaign: reference batch 04

Work began on clean `codex/ball-detector-baseline` at
`6c4759fd73a4471aa93cf3d43c6d4441a0fe8a8a`, with all 691 accepted references
and three campaign acceptance receipts verified unchanged.

The next batch is **75 P001 proposals, frames 125–199 inclusive**. No remaining
uncovered contiguous run reaches 120 frames. This is the longest remaining run
reachable without protected packets or decoded frames. The larger P001 400–498
gap lacks a keyframe after protected frames 275–349. Selection used the accepted
inventory and packet metadata before source inspection, without model outputs.

## Complete review

The [review page](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_04/review_v1/index.html)
contains every frame in a **3-second native-speed** and **15-second slow overlay**,
frame controls, all judgments and unmarked source crops for exceptions. Frame
199 is the batch final; the possession's actual final is 498. Native PTS spans
**[5.04,8.04) seconds**, separately from clip-relative **[5.00,8.00)**.

The sequence shows a held ball, hand/torso overlap, a turn with self-occlusion,
a brief bounce reappearance, and a pass. There are **58 proposed centers** with
**4–10-source-pixel uncertainty** and **17 null centers**:

- Certain occlusion: 176–181 and 185–192.
- Visible fragments without a defensible complete-ball center: 182 and 184.
- Indeterminate visibility: 175.

Visibility counts are six fully visible, 54 partially visible, 14 not visible
and one indeterminate. Centers use current source pixels, not model predictions
or temporal interpolation. Uncertainty is an AI point-placement estimate, not a
calibrated confidence interval. The legacy `human_amodal_estimate` enum describes
the whole-ball convention; it does not change the recorded AI authorship.

**Human acceptance is pending.** Current accepted coverage remains **691/1,273**,
with **582** permitted positions uncovered. Acceptance of this whole batch would
bring coverage to 766 and leave 507. Existing accepted labels need no repeat
review. Acceptance of these references would not authorize fitting, final
trajectories or protected evaluation.

## Validation and preservation

Primary PyAV decoding returned frames 0–199 only. Codec reordering required
202 submitted packets, with maximum presentation index 204. Independent
comparison copied 205 original packets for frames 0–204, verified every payload
hash and PTS/DTS, and decoded only output frames 0–199 with OpenCV. All 75 selected
native PNGs match exactly, including final 199. Both decoders may share FFmpeg
internals; all context remained permitted. Protected P001 frames 275–349 were
never submitted, copied or decoded.

Every source and proposal overlay was visually inspected. The original drafts
remain final; no post-draft corrections were needed. All **150 encoded frames**,
**116 localized marker regions**, exact native-frame/annotation joins and both
video finals passed actual-record checks. The integration audit checks 170 file
bindings and all review-page links. These checks establish record/media integrity,
not independent ground truth or human acceptance.

The renderer, parser and tests are unchanged. The prior ten focused tests remain
evidence for that implementation and were not rerun; this increment checks its
actual emitted records. Source preparation and delivery had no failed attempts.
The [preparation result](../configs/ball_tracking/reviews/ball_completion_reference_batch_04_result_v0_1.json)
binds the exact proposals, source and media audits, and inspection receipts.
Generated labels, source PNGs and videos remain ignored by Git.

No fitting, inference, model scoring, threshold changes or player-pipeline
reruns occurred. Protected evaluation remains closed pending a frozen method
and separate explicit authorization. The completion plan and ball-quality
criteria remain approved.
