# Completion campaign: NBA reference batch 13

This increment prepares the fixed **checkpoint-validation** HOU–OKC episode
`hou-vs-okc-0022400879_e01`, source `4.mp4`, native frames **120–239**.
The 120 selected frames cover **[2,4) seconds**. Source and proposal inspection
are complete: **120 centers, zero nulls, 80 partial and 40 fully visible
judgments**, with **5–6px uncertainty**. The
[complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_13/review_v1/index.html),
[two-second native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_13/review_v1/review_native.mp4)
and [12-second slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_13/review_v1/review_slow.mp4)
retain every selected frame through 239 and are ready for Ryan's reference
acceptance. All 120 new labels remain pending.

## Fixed role and timing

The [configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_13_v0_1.json)
retains the unchanged [source roles](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json).
The whole parent game was assigned checkpoint validation before new model
predictions. Labels are for later saved-checkpoint selection, excluded from
gradient fitting. This is permitted development labeling, not protected evaluation.
Both pending eligibility flags remain false. The source is 1280×720, 60 fps,
timebase 1/60000, with 503 frames. Batch final 239 differs from source final 502;
selected PTS 120000–239000 spans [120000,240000), 1000 ticks per frame.

## Source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_13/preparation.json)
and [pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_13/source_pixel_audit.json)
pass 120 exact PNG and native PTS checks. PyAV pixels match explicit BT.709
TV-range to full-range RGB conversion by FFmpeg. Both use FFmpeg components;
this is a pixel-transport check, not independent ground truth. All 3,862 prior
files remain unchanged. First attempt passes in 22.518 seconds.

The primary decoder returned 0–239 after 241 submitted packets. Alternate
conversion emitted 240 RGB frames and reported filter frames 0–240. Prefix 0–119
and filter 240 are disclosed context from this checkpoint-validation source;
only selected 120–239 are saved or labeled.

## Current-frame inspection

The [assembled proposal](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_13/proposal.json)
and all three parts retain AI authorship, pending human acceptance and false
training/checkpoint-selection eligibility. Their sealed receipts cover every
assigned current source frame and proposed overlay, including full native and
proposed part endpoints. No corrections or helper failures occurred; all first
written proposals remain unchanged.

The [120–159 receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_13/inspection/part_120_159_receipt.json)
seals 40 centers: 28 partial and 12 fully visible judgments. It shows a
free-throw preparation dribble and gather from beneath the basket. Fully
visible ball contours occur at 124–135; hands overlap the ball at 120–123 and
136–159. Floor reflections are not used as ball positions.

The [160–199 receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_13/inspection/part_160_199_receipt.json)
seals 40 partial-visible centers as the shooter holds the ball near the waist
and raises it into the shooting lift. Hand overlap, contour blur and compression
remain explicit in each judgment.

The [200–239 receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_13/inspection/part_200_239_receipt.json)
seals 40 centers, with 12 partial judgments at 200–211 and 28 fully visible
judgments at 212–239, zero nulls and 5–6px uncertainty. The free-throw lift and
release retains hand overlap, followed by a separated airborne ball. Final
239 supports **[629,152] ±6 native pixels**. Every assigned current source frame
and proposed overlay, plus full native/proposed endpoints, was actually viewed
before the receipt was recorded. The first proposal is unchanged, with no
corrections or helper failures. Repeated coordinates reflect individually
inspected repeated/near-repeated images, not interpolation or model predictions.
Across all three parts, the fully visible frames are 124–135 and 212–239.
Zero nulls do not remove partial visibility
or the 5–6px center uncertainty. The legacy geometry source
`human_amodal_estimate` describes complete-object geometry under partial
visibility and does not imply human authorship.

The [exception list](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_13/review_v1/exception_list.json)
is empty because every frame supports a center; it does not erase uncertainty.
The review page includes every judgment and the complete encoded center-crop census.

## Complete review validation

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_13_result_v0_1.json)
is `ready_for_human_reference_acceptance`. Its
[integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_13/integration_audit.json)
passes **4,205 file bindings, 120 native source/annotation joins, 240 encoded
frames and 240 center markers**. Both videos contain all 120 selected frames
at 60/10 fps (2s/12s). Every encoded-frame pixel comparison and emitted color
check passes. Review conversion uses a limited-range BT.601 matrix tagged
`smpte170m`, retaining BT.709 primaries and transfer; source PNGs remain unchanged.

Root actually inspected all ten encoded sheets and all 120 center crops, full
native source frames 120, 160, 200 and 239, and both full actual encoded finals
239 before writing the [AI visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_13/inspection/root_visual_review.json).
No annotation or media corrections were needed. Source preparation, complete
delivery and finalization each passed on their first attempt; no failed
annotation-helper attempts are recorded for any part.

The actual pending-review reader passes 120 annotation/native joins and creates
zero accepted labels. All **1,920 previously accepted NBA rows** and **868
curated references** remain unchanged, along with **3,862 files** captured before
source preparation. All twelve earlier acceptance preservation snapshots remain
bound: **286, 543, 809, 1,050, 1,549, 2,000, 2,245, 2,490, 2,742, 3,015, 3,455
and 3,911 files**; these sets overlap. The unchanged renderer and acceptance
reader retain prior **13-test and 12-test evidence**, with no new suite runs.
Original eight-test acceptance-reader history remains separately bound. Current
source/annotation/media checks establish transport and evidence consistency,
not model accuracy or independent human ground truth.

| Evidence | SHA-256 |
| --- | --- |
| Final result | `f114bff874ea92cdd5ef8dced9557b4c174f43a840674af7afda546f2581f84e` |
| Integration audit | `85ff663010c2a2863db0e2a170430cbba235c894ab2fa7a4fea0a46eadbe4140` |
| AI visual receipt | `7321fd25373ad4dd0980ba03b47fa1a27502f4cdaa0f1161160481408b4112a1` |

## Next step

All new labels require Ryan acceptance. NBA12 acceptance is separate:
**1,920 accepted NBA judgments, 1,756 centers and 164 nulls**, leaving **1,919
unaccepted** and **1,799 positions without proposals** after this pending batch.
Curated coverage stays 868 accepted / 760 eligible centers / 405
uncovered, evaluation-only. Ryan reviews the complete overlays and accepts all
120 proposals, including stated uncertainty, or requests corrections. No fit,
checkpoint scoring or protected evaluation has run. The full
accepted package and executable recipe must be frozen before the approved fit;
protected evaluation separately requires a frozen method and explicit authorization.
