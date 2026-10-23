# Completion campaign: NBA reference batch 15

This increment prepares fixed checkpoint-validation HOU–OKC episode
`hou-vs-okc-0022400879_e03`, source `88.mp4`, native frames **120–239**.
The 120 selected frames cover **[2,4) seconds**. The complete native/slow review
is ready for human reference acceptance. All 120 new judgments remain pending;
no new labels are accepted.

## Fixed role and timing

The [configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_15_v0_1.json)
retains the unchanged [source roles](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json).
The whole game was assigned checkpoint validation before new model predictions.
These references are reserved for later saved-checkpoint selection and excluded
from gradient fitting. Both pending eligibility flags remain false.

The source is 1280×720 at 60 fps, timebase 1/60000, with 473 frames.
Batch final **239** differs from full-source final **472**. Selected PTS are
120000–239000 in [120000,240000), with 1000 ticks per frame. The source window
contains a guarded dribble near the sideline/baseline, referee/player overlap,
and a gather/lift near the head. Current pixels determine geometry and missingness.

## Source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_15/preparation.json)
and [pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_15/source_pixel_audit.json)
pass all **120 exact PNG and native PTS checks**. PyAV pixels match explicit
BT.709 TV-range to full-range RGB conversion by FFmpeg. Both paths use FFmpeg
components; this checks pixel transport rather than independent ground truth.
All **4,350 prior files** remain unchanged. The first attempt passes in
**23.969 seconds**.

The primary decoder returned frames 0–239 after 241 submitted packets.
Alternate conversion emitted 240 RGB frames and reported filter frames 0–240.
Prefix 0–119 and filter frame 240 are disclosed context from the same validation
source; only selected frames 120–239 were saved.

## Manual proposals and inspection

All three sealed parts provide **120 judgments: 98 centers and 22 nulls** at
**126–129, 142–145, 184–189 and 230–237**. Visibility is **32 fully visible,
70 partially visible, ten indeterminate and eight not visible**, with **5–9px
center uncertainty**. Every source/proposed frame and full part endpoint has
been inspected. The initial proposals remain unchanged.

The first [inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_15/inspection/part_120_159_receipt.json)
seals **32 centers and eight nulls at 126–129 and 142–145**, with 28 partial,
four full, six indeterminate and two not-visible judgments, and 6–9px uncertainty.
Root actually inspected all 40 source/proposed frames, thirteen source sheets
including two focused ambiguity sheets, and full source/proposed 120/159 before
sealing. No coordinates are propagated through hidden or unresolved intervals.
Its separate read-only operational note retains an `rg` search access denial
for two unrelated old temporary directories. Existing named helpers were used
directly; no data or outputs changed and elapsed time is unknown. This was not
an annotation-helper failure.

The middle [inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_15/inspection/part_160_199_receipt.json)
seals all 40 source/proposed frames and full endpoints 160/199: **34 centers and
six occluded/null centers at 184–189**, with 22 full/12 partial/six not-visible
judgments and 5–6px center uncertainty. It retains two read-only lookup failures:
a null-geometry indexing error (0.189059s) and a Windows `rg` wildcard-path error
(0.1929893s). Neither created outputs or changed geometry; corrected lookups used
the producer schema, without borrowing coordinates from another episode.

The final [inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_15/inspection/part_200_239_receipt.json)
seals all 40 source/proposed frames and full endpoints 200/239: **32 centers and
eight nulls at 230–237**, with six full/30 partial/four indeterminate judgments
and 5–8px center uncertainty. Frames 230–233 are ambiguous ball-versus-arm/shoulder
pixels; 234–237 retain visible fragments without defensible whole-ball extent.
Frames 238–239 support partial centers **[420,355] ±8 pixels** from the upper
rounded ball arc, with head/hands overlap explicit. Root's second AI source look
agrees; this is not independent human ground truth or label acceptance. No earlier
coordinate is propagated through the null interval. The initial proposal is
unchanged, with no annotation-helper failures or corrections.

Complete encoded review and final validation have passed; all new judgments
still require Ryan's separate acceptance.

## Complete review and validation

- [Complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_15/review_v1/index.html)
- [Native overlay: 2 seconds at 60 fps](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_15/review_v1/review_native.mp4)
- [Slow overlay: 12 seconds at 10 fps](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_15/review_v1/review_slow.mp4)
- [All 120 proposals](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_15/proposal.json) and [all 22 null-center exceptions](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_15/review_v1/exception_list.json)
- [Root visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_15/inspection/root_visual_review.json)

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_15_result_v0_1.json)
and [integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_15/integration_audit.json)
pass **4,732 bindings, 120 native source/annotation joins, 240 encoded frames
and 196 center markers**, plus all **120 exact source PNG checks**. Every encoded
frame passes its pixel comparison and emitted color checks. Null contexts remain
unmarked; their rectangles identify inspection areas, not inferred centers.

Root actually inspected all ten final encoded/source sheets, all **98 center
crops**, all **22 null contexts** and both complete actual encoded finals before
writing the visual receipt. Root personally inspected full native source
120/159/239 and focused late source details 228–239; the three sealed part
receipts collectively cover every source/proposed frame and full part endpoint.
Final 239 retains **[420,355] ±8 pixels**, a partial upper ball arc above the head.
This second AI look does not create independent human ground truth.

Delivery passed first attempt in **14.031 seconds**; finalization passed first
attempt in **8.859 seconds**. Initial labels and images remain unchanged.
The three read-only lookup incidents are preserved separately; there were no
annotation-helper failures, annotation corrections or media corrections.
The actual pending-review reader passes all 120 joins and creates zero
accepted labels.

All **2,160 accepted NBA rows**, **868 curated references** and **4,350 files
captured before source preparation** remain unchanged. Earlier acceptance
preservation snapshots remain bound and overlap. Historical **13-test renderer**
and current **12-test acceptance-reader** receipts cover unchanged source;
the original eight-test acceptance history remains separate. No tests were
rerun for this increment. No model inference, fitting or checkpoint scoring ran.

## Pending decision and campaign status

NBA14 acceptance is separate: **2,160 accepted NBA judgments, 1,996 centers
and 164 nulls**; **1,679 selected judgments remain unaccepted**. Accepted roles
are 1,920 training and 240 checkpoint validation; 959 training and 720 validation
judgments remain unaccepted. Curated references remain evaluation-only:
868 accepted, 760 eligible centers and 405 uncovered.

These 120 pending proposals leave **1,559 selected positions without proposals**,
while **1,679 remain without accepted references**. All new labels require Ryan's
acceptance. The complete accepted source/label/role
package and executable recipe must be frozen before the already approved fit.
No completion-campaign fit has run. Protected evaluation remains closed pending
a frozen method and separate explicit authorization.
