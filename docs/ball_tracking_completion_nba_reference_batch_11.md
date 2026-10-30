# Completion campaign: NBA reference batch 11

## Accepted references

Ryan accepted all 240 proposals on 2026-10-23 (America/Phoenix), replying
**“I approve caht. move forward”** to the complete review and acceptance question.
The [separate acceptance receipt](../configs/ball_tracking/reviews/nba_completion_reference_batch_11_acceptance_v0_1.json)
accepts the 240 centers, including 172 partial and 68 fully visible judgments,
zero null centers and 5–8px uncertainty. The exact user-event timestamp is
unknown and stays null; the publication timestamp is separate.

The [publication audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/acceptance_audit/publication_audit.json)
preserves **3,455 original files**, all 1,440 earlier accepted NBA rows and all
868 curated references. Actual publication/inventory readers and the duplicate
native-frame guard pass. The [combined inventory](../data/outputs/ball_tracking/completion_campaign_v0_1/accepted_nba_reference_inventory_after_batch_11.json)
now has **1,680 accepted NBA labels: 1,536 centers and 144 nulls**; **2,159 of
3,839 selected judgments remain unaccepted**. These are training-role labels
eligible for a future frozen package; acceptance does not freeze the recipe,
accept final trajectories, approve future batches or open protected evaluation.
No fitting or new tests ran. The [next fixed NBA12 episode](ball_tracking_completion_nba_reference_batch_12.md)
is ready for separate human reference acceptance.

## Original preparation record

The following preparation-time account is retained as history. Its pending
status and counts are superseded by the separate acceptance above; original
proposal, media, inspection receipts and final result remain byte-unchanged.

This increment prepares references for fixed training-role DEN–BOS episode
`den-vs-bos-0022400866_e05`, source `84.mp4`, frames **210–449**. Its 240 selected
frames span **[3.5,7.5) seconds**. Source preparation and all source/proposal
inspection are complete: **240 centers, zero nulls, 172 partial and 68 fully
visible judgments**, with **5–8px uncertainty**. The
[complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/review_v1/index.html),
[four-second native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/review_v1/review_native.mp4)
and [24-second slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/review_v1/review_slow.mp4)
retain every selected frame through 449 and are ready for Ryan's reference
acceptance. All new labels remain pending.

NBA10 is accepted through its separate
[receipt](../configs/ball_tracking/reviews/nba_completion_reference_batch_10_acceptance_v0_1.json).
Accepted NBA coverage is **1,440/3,839 judgments**, including **1,296 centers and
144 nulls**, with **2,399 unaccepted** and **2,159 selected positions without
proposals** after this pending batch. Curated evaluation-only coverage remains
**868/1,273**, including 760 eligible centers and 405 uncovered positions.

## Fixed source and native timing

The [batch configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_11_v0_1.json)
uses the unchanged [source-role manifest](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json).
Its entire DEN–BOS parent game retains the training role fixed before new-model
predictions. The original 1280×720 source contains 587 frames at 60 fps with a
1/60000-second timebase. Batch final **449** differs from full-source final
**586**. Selected PTS are **210000–449000**, with 1000-tick durations in the
half-open interval **[210000,450000)**. Review-relative time is [0,4)s.

## Completed source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/preparation.json)
and [source-pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/source_pixel_audit.json)
pass all **240 selected native PNG comparisons and PTS checks**. Saved PyAV
pixels exactly match explicit BT.709 FFmpeg RGB conversion. Both paths use
FFmpeg components; this establishes transport consistency, not independent
visual ground truth. All **2,969 prior files** remain unchanged.

The primary decoder submitted **451 packets** and returned frames **0–449**.
Alternate conversion emitted **450 RGB frames**, reporting filter frames
**0–450**. Prefix frames 0–209 and filter frame 450 are disclosed context from
the same training source, not additional labels. Only selected frames 210–449
were saved. Preparation passed on its first attempt in **38.448 seconds**.

## Current-frame proposals

All three parts retain AI authorship and pending human acceptance; both training
and checkpoint-selection eligibility remain false. The
[assembled proposal](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/proposal.json)
retains all 240 judgments. The
[210–289 receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/inspection/part_210_289_receipt.json),
[290–369 receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/inspection/part_290_369_receipt.json)
and [370–449 receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/inspection/part_370_449_receipt.json)
bind every current native source and proposed overlay inspection, including full
part endpoints. All first written proposals are unchanged, with no corrections
or annotation-helper failures. No temporal interpolation or model coordinates
supplied centers.

The observed scene includes a drive and gather, an interior pass and catch,
then a shot release, flight and rim/net and hand interaction. The fixed
selection category `recovery` is retained as provenance; this batch does not
establish a hidden interval or measure model recovery. Fully visible intervals
are 220–235, 298–315, 380–411 and 448–449. Hand overlap, rim/net overlap, motion
blur and compression remain explicit in the other 172 judgments. Every current
frame supports a whole-ball center; zero nulls do not remove the stated
uncertainty. The geometry source `human_amodal_estimate` describes complete-object
geometry under partial visibility and does not imply human authorship.

Extra source details cover rim/net and reaching-hand overlap in 410–449. The
[additional root source review](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/inspection/root_source_detail_438_449.png)
supports partial visibility in 438–447 and a separated complete contour in
448–449. It is an additional AI source judgment, not Ryan's acceptance. Final
frame 449 proposes **[517,190] ±6 native pixels**.

The [exception list](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/review_v1/exception_list.json)
is empty because all frames support centers. It does not erase partial visibility
or uncertainty. The review page includes every judgment and the complete encoded
center-crop census.

## Complete review validation

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_11_result_v0_1.json)
is `ready_for_human_reference_acceptance`. Its
[integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/integration_audit.json)
passes **3,494 file bindings, 240 native source/annotation joins, 480 encoded
frames and 480 center markers**. Both videos contain all 240 selected frames
at 60/10 fps (4s/24s). Every encoded-frame comparison and emitted color-metadata
check passes. Review conversion explicitly uses a limited-range BT.601 matrix,
tagged `smpte170m`, while retaining BT.709 primaries and transfer; native source
PNGs remain unchanged.

All twenty inspection sheets and all 240 encoded center crops were inspected,
along with full native source 449 and both full actual encoded finals 449. The
[confirmed AI visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/inspection/root_visual_review_confirmed.json)
binds these inspections and the additional source detail. The first
[root receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/inspection/root_visual_review.json)
was written within the same tool call that fetched the final images, before
those outputs returned. After actually viewing both returned images, the root
wrote the separate confirmation used by finalization, preserving the original
receipt and explaining the sequence correction. No labels or media changed;
no source or test rerun was needed. Source preparation, delivery and finalization
each passed on their first attempt.

The actual pending-review reader passes all 240 annotation/native joins and
creates zero accepted labels. All **1,440 previously accepted NBA labels** and
**868 curated references** remain unchanged. The audit also preserves the
**2,969 files** captured before preparation and all ten earlier acceptance
snapshots of **286, 543, 809, 1,050, 1,549, 2,000, 2,245, 2,490, 2,742 and
3,015 files**; these preservation sets overlap. The unchanged renderer and
acceptance reader retain prior **13-test and 12-test evidence**, without new
suite runs. The original eight-test acceptance-reader history remains separate.
Current source/annotation/media validation is not model accuracy or independent
human ground truth. No inference or fitting ran.

| Evidence | SHA-256 |
| --- | --- |
| Final result | `3792465fe897092d5ae3f047995324deebc6cd8663c69303d3ea3627d4cb5181` |
| Integration audit | `e1205de06feb84856f006248a4ad33c5ca9649bba428251f94b6cce1bec50bd0` |
| Confirmed AI visual receipt | `46dca7c0e2cbd669f55bb15e670534967da64a52d7aa055708e7fe83114ad5a2` |

## Preparation-time next step (completed by acceptance above)

Ryan reviews the complete overlays and decides whether to accept the 240
reference proposals, including their stated uncertainty, or request corrections.
No new fit or protected evaluation has run. Complete and freeze the accepted
source/label/role package and executable recipe before the already approved fit;
protected evaluation still requires a frozen method and separate authorization.
