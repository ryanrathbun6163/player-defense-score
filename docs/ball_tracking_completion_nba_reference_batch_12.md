# Completion campaign: NBA reference batch 12

## Accepted references

Ryan accepted all 240 proposals on 2026-10-23 (America/Phoenix), saying
**“Looks good to me. Move forward chat”** in response to the complete overlay
and acceptance question. The [separate acceptance receipt](../configs/ball_tracking/reviews/nba_completion_reference_batch_12_acceptance_v0_1.json)
accepts **220 centers and 20 nulls at 182–197 and 386–389**, with **5–8px center
uncertainty**: 176 partial, 54 full, four indeterminate and six not visible.
Exact user-event time is unknown and remains null; publication time is separate.

The [publication audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/acceptance_audit/publication_audit.json)
passes on the first attempt in 21.228 seconds, preserving **3,911 original
files**, all 1,680 earlier accepted NBA labels and all 868 curated references.
Actual publication/inventory readers and the duplicate native-frame guard pass.
The [combined inventory](../data/outputs/ball_tracking/completion_campaign_v0_1/accepted_nba_reference_inventory_after_batch_12.json)
has **1,920 accepted NBA rows, 1,756 centers and 164 nulls**, with **1,919
unaccepted**. All accepted NBA rows have the fixed training role. Acceptance
is label-scoped and does not approve future labels, freeze the fit package or
recipe, accept final trajectories, or open protected evaluation.

No fitting or new tests ran. The [next fixed NBA13 episode](ball_tracking_completion_nba_reference_batch_13.md)
is ready for separate human reference acceptance.

## Original preparation record

The following preparation-time account is retained as history. Its pending
status and counts are superseded by the separate acceptance above; original
proposal, media, inspection receipts and result remain byte-unchanged.

This increment prepares the fixed training-role DEN–BOS episode
`den-vs-bos-0022400866_e06`, source `220.mp4`, native frames **150–389**.
The 240 selected frames cover **[2.5,6.5) seconds**. The
[complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/review_v1/index.html),
[four-second native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/review_v1/review_native.mp4)
and [24-second slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/review_v1/review_slow.mp4)
are ready for Ryan's reference acceptance: **220 centers and 20 nulls**, with
**5–8px center uncertainty**. All 240 new labels remain pending; no acceptance
is created by this document or the review audit.

## Fixed source and native timing

The [batch configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_12_v0_1.json)
retains the unchanged [source roles](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json).
The entire parent game has the training role fixed before new-model predictions.
The source is 1280×720 at 60 fps, timebase 1/60000, with 565 decoded frames.
Batch final **389** differs from full-source final **564**. Selected PTS are
150000–389000 in the half-open interval **[150000,390000)**; each frame lasts
1000 ticks. Review-relative time is [0,4)s.

## Source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/preparation.json)
and [pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/source_pixel_audit.json)
pass all **240 exact PNG and native PTS checks**. Saved PyAV pixels match an
explicit BT.709 TV-range to full-range RGB conversion by FFmpeg. Both paths use
FFmpeg components; this verifies pixel transport rather than independent ground
truth. All **3,403 prior files** are unchanged.

Preparation passed on its first attempt in **58.684 seconds**. The primary
decoder returned frames 0–389 after 391 submitted packets. Alternate conversion
emitted 390 RGB frames and reported filter frames 0–390. Prefix frames 0–149 and
filter frame 390 are disclosed context from the same training source; only
selected frames 150–389 were saved. They do not add labels or review frames.

## Current-frame proposal inspection

The [assembled proposal](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/proposal.json)
retains 240 judgments: **176 partially visible, 54 fully visible, four
indeterminate and six not visible**. Nulls are **182–197 and 386–389**:
182–187 and 386–389 are partial/null, 188–191 indeterminate, and 192–197
occluded. Fully visible frames are 240–243, 274–275 and 336–383.

The [150–229 receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/inspection/part_150_229_receipt.json)
seals 64 centers and 16 nulls, with 70 partial, four indeterminate and six not
visible judgments and 5–7px center uncertainty. The ball is held and lowered
beside the body, then obscured during a low dribble before reappearing at the
waist. Visible fragments at 182–187 do not support a whole-ball center; the
hand/ball-colored fringe at 188–191 remains indeterminate, and 192–197 are
occluded. No hidden position was inferred. The first proposal is unchanged,
with no revisions or annotation-helper failures.

The [230–309 receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/inspection/part_230_309_receipt.json)
seals 80 centers: 74 partial and six fully visible judgments, with 5–8px
uncertainty. This segment shows an inward dribble, gather and shooting lift.
Four notes/tag corrections at 272–273 and 276–277 clarify player overlap;
geometry, visibility and uncertainty are unchanged. The original proposal and
correction record are retained. A system-Python launch failed because PIL was
unavailable, created no outputs, and is recorded in the receipt. Running the
unchanged helper with the project `.venv` succeeded.

The [310–389 receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/inspection/part_310_389_receipt.json)
seals 76 centers and four partial/nulls at **386–389**, with 32 partial and
48 fully visible judgments and 6–8px center uncertainty. The observed shot
lift/release continues into separated flight, then rim/net interaction. Broad
ball contours support centers in 384–385 with 8px uncertainty. In 386–389,
only weak ball fragments are visible among rim and net; whole-ball centers
remain null. The additional [source-only final-frame crop](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/inspection/root_source_final_389_roi_820_110_970_260.png)
was actually viewed and supports retaining this uncertainty. It is an AI
review, not human acceptance. The final part is unchanged from its initial
proposal, with no annotation-helper failures.

All three receipts bind every assigned current source frame and proposed overlay,
including full native/proposed endpoints. Centers come from current source
pixels, without temporal interpolation or model coordinates. Partial/null
judgments preserve missing geometry rather than propagating flight positions.
The legacy geometry source `human_amodal_estimate` describes complete-object
geometry under partial visibility and does not imply human authorship.
The [exception list](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/review_v1/exception_list.json)
retains all twenty null judgments and their reasons. The review page includes
every judgment, every encoded center crop and separate source context for nulls.

## Complete review validation

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_12_result_v0_1.json)
is `ready_for_human_reference_acceptance`. Its
[integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/integration_audit.json)
passes **3,954 file bindings, 240 native source/annotation joins, 480 encoded
frames and 440 center markers**. Both videos retain all 240 selected frames
at 60/10 fps (4s/24s). All encoded-frame pixel comparisons and emitted color
checks pass. Review conversion explicitly uses a limited-range BT.601 matrix,
tagged `smpte170m`, while retaining BT.709 primaries and transfer; native source
PNGs remain unchanged.

Root actually inspected all twenty encoded/source sheets, all **220 encoded
center crops and 20 null contexts**, full native source 389 and both full
actual encoded finals 389. The
[AI visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/inspection/root_visual_review.json)
was written after the image outputs returned and were viewed. Final frame
389 remains partial/null, with no center marker. Source context is provided in
the separate exception crops.
No media or geometry corrections followed the complete inspection. Source
preparation, complete delivery and finalization each passed on the first
attempt; the separate earlier annotation-helper launch failure remains recorded.

The actual pending-review reader passes all 240 annotation/native joins and
creates zero accepted labels. All **1,680 accepted NBA labels** and **868
curated references** remain unchanged, as do the **3,403 files** captured before
source preparation. All eleven earlier acceptance preservation snapshots remain
bound: **286, 543, 809, 1,050, 1,549, 2,000, 2,245, 2,490, 2,742, 3,015 and
3,455 files**; these sets overlap. The unchanged renderer and acceptance reader
retain historical **13-test and 12-test evidence**, without new suite runs.
Original eight-test acceptance-reader history remains separately bound.
Current source/annotation/media checks establish transport and evidence
consistency, not model accuracy or independent human ground truth.

| Evidence | SHA-256 |
| --- | --- |
| Final result | `1fd0cf6a6349875fbbf8cd9d774060f10c5d4033e099992572da780d5fbc5295` |
| Integration audit | `6b96875b5e092b83fb0b4fcf3a76ca2585024757eb17942a42a52fcebed6085c` |
| AI visual receipt | `ed23edd4e98a66f9949228fe7d4d5b13f00c82b0f1fbb184823b983eea1cd5d6` |

## Preparation-time next step (completed by acceptance above)

All new labels retain AI authorship, pending human acceptance, and false training
and checkpoint-selection eligibility. NBA11 acceptance remains separate:
**1,680 accepted NBA judgments, 1,536 centers and 144 nulls**, with **2,159
unaccepted** and **1,919 selected positions without proposals** after this
pending batch. Curated references remain evaluation-only: **868 accepted,
760 eligible centers and 405 uncovered**.

Ryan reviews the complete overlays and accepts the 240 proposals, including
uncertainty and null centers, or requests corrections. No inference, fitting,
model scoring or protected evaluation has run. The complete accepted source/label/role package
and executable recipe must be frozen before the already approved fit. Protected
evaluation still requires a frozen method and separate explicit authorization.
