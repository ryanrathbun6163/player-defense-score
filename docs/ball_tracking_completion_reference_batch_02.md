# Completion campaign: reference batch 02

Ryan requested the next reference batch under the already approved completion
plan. Work began on clean `codex/ball-detector-baseline` at
`4ac0b16092bd08c073a3f4196443d9ebcf53a36a`. The 120 accepted P003 references
and their separate human-acceptance receipt were verified unchanged.

The new batch is **P002 frames 50–169 inclusive: 120 proposals**. Selection
used the accepted-reference inventory before inspecting new images: the first
120 frames of the earliest remaining uncovered run of at least 120 frames in
possession order. Five permitted frames remain before the protected band starts
at 175. Selection did not use model errors or predictions.

## Complete review

The [review page](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_02/review_v1/index.html)
contains the complete 4.8-second native-speed overlay and 24-second slow overlay,
frame-step controls, all 120 judgments, uncertainty rings, an exception list
with unmarked source crops, and the actual final frame 169.

Source-native presentation time spans **[2.04, 6.84) seconds**; clip-relative time
spans **[2.00, 6.80)**. Every source frame lasts 40 ms. The source has a nonzero
presentation-time origin, which is preserved separately from relative playback.

The scene covers dribbling, hand contact, changes of hand, body overlap and
reappearance. Centers are current-frame complete-ball estimates, not
interpolated points or model outputs. Frames with insufficient visible boundary
retain null geometry. Indeterminate visibility is not treated as a certain
hidden negative. AI authorship, source coordinates and non-statistical point
placement uncertainty remain explicit. The legacy `human_amodal_estimate` enum
does not claim that a human placed the point.

There are **98 proposed centers**, with 5–10-source-pixel uncertainty, and
**22 null centers**: 15 certain occlusions, five visible fragments with an
indefensible center (64, 123, 141, 142, 149), and two indeterminate-visibility
frames (124–125). The visibility census is 15 fully visible, 88 partially
visible, 15 not visible and two indeterminate.

Ryan reviewed the delivered complete overlay and explicitly answered
**“Accept all 120 proposals.”** The [later acceptance receipt](../configs/ball_tracking/reviews/ball_completion_reference_batch_02_acceptance_v0_1.json)
records that event. A separate accepted publication retains all 120 judgments,
native-frame records and AI authorship. Current accepted coverage is now
**560/1,273**, with **713** uncovered permitted frames. Null centers remain null.
Neither this batch nor existing accepted references need repeat review.
The [accepted reference](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_02/accepted/reference.json)
and [current coverage inventory](../data/outputs/ball_tracking/completion_campaign_v0_1/accepted_reference_inventory_after_batch_02.json)
record this state. A metadata-only acceptance integration check confirms all
440 prior rows are unchanged and future duplicate guards reject this batch.

The original review page, video headers, proposal, config and preparation result
retain their historical pending status unchanged; the later acceptance receipt
is the current acceptance authority. Acceptance does not approve fitting,
final model trajectories or protected evaluation.

## Preservation and validation

The reference loader now accepts explicitly bound prior campaign publications
and their separate acceptance receipts. It checks hashes, recorded human review,
AI authorship, evaluation-only roles, source/range identity and exact agreement
with the original reviewed proposal and native-frame manifest. Conflicting
accepted rows are rejected. The historical batch-01 configuration retains its
original 320-row pre-batch inventory for replay; batch 02 protects all 440
currently accepted rows.

Ten focused tests pass on the changed loader and existing renderer, including
tests derived from the actual accepted batch-01 publication. Their scope includes
relabel rejection, role/acceptance and binding mutations, native-frame/proposal
agreement, conflicts, timing and source-to-overlay geometry. The full suite was
not repeated for this bounded change.

Preparation decoded source output frames 0–169 and saved only 50–169. An
independent PyAV/Pillow audit found all 120 native PNGs pixel-identical to a fresh
sequential decode, with zero pixel or timestamp mismatches. It stopped after 169
without requesting frame 170. Both decoders may use FFmpeg internally; codec
reference-frame lookahead was not instrumented. No protected decoded output
frames were inspected. Protected bands remain closed.

Initial manual drafts and later refinements remain separate. Every source
frame and proposed crop was visually inspected before delivery. Full encoded
overlays are checked against their actual source/label records, including marker
regions, frame counts and actual finals. These checks verify transport and
presentation, not independent ground truth or human acceptance.
The final metadata/media audit verifies 165 file bindings, all 120 proposal/
manifest/native-timing joins, 240 encoded frames and 196 localized marker regions.
Nine manual center refinements retain their original drafts. An initial
positional-argument mistake in a local parser check was corrected before saving
the first part; its inspection receipt retains the correction. No failed fit or
scientific result was replaced.

The [result receipt](../configs/ball_tracking/reviews/ball_completion_reference_batch_02_result_v0_1.json)
binds the exact proposal, manifest, review page, implementation, tests and audits.
Generated video, PNGs and annotation artifacts remain ignored by Git.

No fitting, inference, threshold changes, model scoring, player-pipeline reruns
or protected evaluation occurred. Continue the fixed reference package, including
both accepted campaign publications in future duplicate guards. New reference acceptance remains required before
fitting, and protected evaluation still requires a frozen method and separate
explicit authorization.
