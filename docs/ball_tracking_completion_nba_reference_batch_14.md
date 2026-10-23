# Completion campaign: NBA reference batch 14

This increment prepares fixed checkpoint-validation HOU–OKC episode
`hou-vs-okc-0022400879_e02`, source `43.mp4`, native frames **0–119**.
The 120 selected frames cover **[0,2) seconds**. The complete native/slow review
is ready for human reference acceptance. All 120 labels remain pending;
no new labels are accepted.

## Fixed role and timing

The [configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_14_v0_1.json)
retains the unchanged [source roles](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json).
The whole game was assigned checkpoint validation before new model predictions.
These labels are reserved for later saved-checkpoint selection and excluded
from gradient fitting. Both pending eligibility flags remain false. No model
results or protected evaluation are being inspected.

The source is 1280×720 at 60 fps, timebase 1/60000, with 597 frames.
Batch final **119** differs from full-source final **596**. Selected PTS are
0–119000 in [0,120000), with 1000 ticks per frame. The clip shows an advancing
dribble and camera pan across midcourt.

## Source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_14/preparation.json)
and [pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_14/source_pixel_audit.json)
pass all 120 exact PNG and native PTS checks. PyAV pixels match explicit
BT.709 TV-range to full-range RGB conversion by FFmpeg. Both paths use FFmpeg
components; this checks pixel transport rather than independent ground truth.
All **4,106 prior files** remain unchanged. The first attempt passes in
22.939 seconds.

The primary decoder returned frames 0–119 after 121 submitted packets.
Alternate conversion emitted 120 RGB frames and reported filter frames 0–120.
Filter frame 120 is disclosed context from the same validation source;
only selected frames 0–119 were saved. There is no decoded prefix before the
selected interval.

## Manual proposals and inspection

Three parts contain **120 centers and zero nulls**, including **71 partially
visible and 49 fully visible judgments**, with **5–7px native-pixel uncertainty**.
The clip shows an advancing dribble and camera pan across midcourt. Hand overlap,
motion blur and compression remain explicit; each coordinate comes from its
current frame rather than interpolation or model predictions. Fully visible
intervals are **3–7, 42–73 and 108–119**. All source/proposed frames and full
part endpoints have been inspected; the initial proposals remain unchanged.

The first [inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_14/inspection/part_0_39_receipt.json)
credits `/root/baseline_package` for all source inspection and initial annotation.
After two worker interruptions, `/root` actually inspected all seven proposed
detail sheets and full overlays 0/39 before sealing the receipt. No unconfirmed
worker-overlay review is asserted, and no labels or images changed.

The middle [inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_14/inspection/part_40_79_receipt.json)
retains a helper failure from unsorted difficulty tags, after 0.4475467 seconds.
Validation stopped at the first row before writing any proposal or overlay.
The failed helper is preserved; sorting tags allowed a successful 1.6081469-second
run without changing coordinates, visibility or uncertainty. The final
[inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_14/inspection/part_80_119_receipt.json)
records all 40 source/proposed frames and full endpoints 80/119 as inspected,
with an unchanged initial proposal and no failures. Final 119 proposes
**[846,568] ±6 pixels**, fully visible and separated from the hand and referee.

## Complete review and validation

- [Complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_14/review_v1/index.html)
- [Native overlay: 2 seconds at 60 fps](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_14/review_v1/review_native.mp4)
- [Slow overlay: 12 seconds at 10 fps](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_14/review_v1/review_slow.mp4)
- [All 120 proposals](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_14/proposal.json) and [empty null-center exception list](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_14/review_v1/exception_list.json)
- [Root visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_14/inspection/root_visual_review.json)

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_14_result_v0_1.json)
and [integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_14/integration_audit.json)
pass **4,456 bindings, 120 source/annotation native joins, 240 encoded frames
and 240 center markers**, plus all 120 exact source PNG checks. Every encoded
frame passes its pixel comparison and emitted color checks. The empty exception
list means no null centers; it does not remove hand overlap or uncertainty.

Root actually inspected all ten encoded sheets, all 120 center crops, full
native source 0/40/80/119 and both full actual encoded finals before writing
the visual receipt. Source final 596 remains distinct from batch final 119.
Delivery passed first attempt in **12.922 seconds**; finalization passed first
attempt in **8.468 seconds**. The earlier middle annotation-helper failure
remains recorded separately. There were no annotation or media corrections.

The actual pending-review reader passes 120 native joins and creates zero
accepted labels. All **2,040 accepted NBA rows**, **868 curated references**
and **4,106 preparation-era files** remain unchanged. Prior acceptance
preservation snapshots remain bound and overlap. Historical **13-test renderer**
and current **12-test acceptance-reader** receipts cover unchanged source;
the original eight-test acceptance history remains separate. No tests were
rerun for this increment. No model inference, fitting or checkpoint scoring ran.

## Pending decision and campaign status

NBA13 acceptance is separate: **2,040 accepted NBA judgments, 1,876 centers
and 164 nulls**; **1,799 selected judgments remain unaccepted**. Accepted roles
are 1,920 training and 120 checkpoint validation. Curated references remain
evaluation-only: 868 accepted, 760 eligible centers and 405 uncovered.

The 120 pending proposals leave **1,679 selected positions without proposals**;
**1,799 remain without accepted references**. All new labels require Ryan's
acceptance. The full accepted source/label/role package and executable recipe
must be frozen before the already approved fit.
Protected evaluation remains closed pending a frozen method and separate
explicit authorization.
