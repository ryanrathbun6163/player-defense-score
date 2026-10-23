# Completion campaign: NBA reference batch 16

This increment prepares fixed checkpoint-validation HOU–OKC episode
`hou-vs-okc-0022400879_e04`, source `140.mp4`, native frames **150–269**.
The 120 selected frames cover **[2.5,4.5) seconds**. The complete native/slow
review is ready for human reference acceptance. All 120 new judgments remain
pending; preparation and review create no accepted labels.

## Fixed role and timing

The [configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_16_v0_1.json)
retains the unchanged [source roles](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json).
The game was assigned checkpoint validation before new model predictions.
These references are reserved for later saved-checkpoint selection and excluded
from gradient fitting. Both pending eligibility flags remain false.

The source is 1280×720 at 60 fps, timebase 1/60000, with 671 frames.
Batch final **269** differs from full-source final **670**. Selected PTS are
150000–269000 in [150000,270000), with 1000 ticks per frame. The observed sequence
includes a pass, catch, shot lift/release and airborne flight. Current source
pixels support each judgment; no coordinates are interpolated.

## Source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_16/preparation.json)
and [pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_16/source_pixel_audit.json)
pass all **120 exact PNG and native PTS checks**. PyAV pixels match explicit
BT.709 TV-range to full-range RGB conversion by FFmpeg. Both paths use FFmpeg
components; this checks pixel transport rather than independent ground truth.
All **4,621 prior files** remain unchanged. The first attempt passes in
**25.052 seconds**.

The primary decoder returned frames 0–269 after 271 submitted packets.
Alternate conversion emitted 270 RGB frames and reported filter frames 0–270.
Prefix 0–149 and filter frame 270 are disclosed context from the same validation
source; only selected frames 150–269 were saved.

## Manual proposals and inspection

All three sealed parts provide **120 centers and zero nulls**, with **70 fully
visible and 50 partially visible judgments**, and **5–8px uncertainty**. Every
current source/proposed frame and full part endpoint has been inspected.

The first [inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_16/inspection/part_150_189_receipt.json)
seals **40 centers**, with 14 partial/26 full judgments and **5–7px uncertainty**.
Initial source crops clipped the moving ball at 156–161 and 166–167. Those
assets were retained; supplemental crops 156–167 were inspected before initial
annotation, and a separate overlay helper expanded the crop regions. No source
pixels changed.

Actual overlay and enlarged source review refined six centers at **172–177**
to correct small initial rightward offsets. Visibility and uncertainty stayed
unchanged; the original proposal and all initial overlays remain preserved,
and complete review uses the final v2 part. Root inspected all seven initial
and seven final detail sheets and full final overlays 150/189. The receipt also
retains a read-only `rg` access denial for unrelated old temporary directories
(0.2188052s), with no data/output change. After Ryan reported a restart, root
verified existing branch/HEAD and critical acceptance, preparation, proposal
and receipt hashes before resuming. No acceptance publication or source
preparation was rerun.

The middle [inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_16/inspection/part_190_229_receipt.json)
seals **40 centers and zero nulls**, with 36 partial and four fully visible
judgments and **5–8px uncertainty**. The shooter settles, lifts and releases the
ball. Frames 190–225 retain hand overlap; 226–229 show the ball separated from
the hands. Strong release blur is represented by 8px uncertainty. All 40 current
source/proposed frames and full endpoints 190/229 were inspected, with no
annotation corrections or failed attempts.

The final [inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_16/inspection/part_230_269_receipt.json)
seals **40 fully visible centers and zero nulls**, with **6–7px uncertainty**.
The released ball stays airborne against the crowd throughout 230–269.
Motion blur and compression soften its contour; similar-colored spectator
clothing at 254–259 reduces contrast without hiding the ball. Every current
source/proposed frame and full endpoints 230/269 were actually inspected.
Final 269 supports **[694,60] ±6 pixels**. The initial part is unchanged,
with no annotation-helper failures or corrections.

Complete encoded review and finalization have passed. This AI inspection does
not establish independent human ground truth or Ryan's label acceptance.

## Complete review and validation

- [Complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_16/review_v1/index.html)
- [Native overlay: 2 seconds at 60 fps](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_16/review_v1/review_native.mp4)
- [Slow overlay: 12 seconds at 10 fps](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_16/review_v1/review_slow.mp4)
- [All 120 proposals](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_16/proposal.json) and [empty null-center exception list](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_16/review_v1/exception_list.json)
- [Root visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_16/inspection/root_visual_review.json)

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_16_result_v0_1.json)
and [integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_16/integration_audit.json)
pass **5,000 bindings, 120 native source/annotation joins, 240 encoded frames
and 240 center markers**, plus all **120 exact source PNG checks**. All-frame
pixel comparisons and emitted color checks pass. The empty exception list
does not remove the stated hand-overlap, blur and background uncertainty.

Root actually inspected all ten final encoded sheets, all **120 encoded center
crops** and both full actual encoded finals before recording the visual receipt.
Root personally inspected full native source 150/170/189/269; the three part
receipts cover every source/proposed frame and full part endpoint collectively.
Final 269 retains **[694,60] ±6 pixels**, fully visible against the crowd.

Delivery passed first attempt in **15.062 seconds**; finalization passed first
attempt in **18.797 seconds**. The first-part crop adjustments, six coordinate
refinements and read-only lookup incident remain recorded above; there were
no other annotation changes or media corrections. The actual pending-review
reader passes all 120 joins and creates zero accepted labels.

All **2,280 accepted NBA rows**, **868 curated references** and **4,621 files
captured before source preparation** remain unchanged. Earlier acceptance
preservation snapshots stay bound and overlap. Historical **13-test renderer**
and current **12-test acceptance-reader** receipts cover unchanged source;
the original eight-test acceptance history remains separate. No tests were
rerun for this increment. No model inference, fitting or checkpoint scoring ran.

## Campaign status and next decision

NBA15 acceptance is separate: **2,280 accepted NBA judgments, 2,094 centers
and 186 nulls**; **1,559 selected judgments remain unaccepted**. Accepted roles
are 1,920 training and 360 checkpoint validation; 959 training and 600 validation
judgments remain unaccepted. Its publication preserves 4,673 original files.
Curated references remain evaluation-only: 868 accepted, 760 eligible centers
and 405 uncovered.

These **120 pending proposals** leave **1,439 positions without proposals**
and **1,559 without accepted references**. Next is Ryan's acceptance or
correction of the complete review. The complete accepted source/label/role
package and executable recipe must be frozen before the already approved fit.
No completion-campaign fit has run. Protected evaluation remains closed
pending a frozen method and separate explicit authorization.
