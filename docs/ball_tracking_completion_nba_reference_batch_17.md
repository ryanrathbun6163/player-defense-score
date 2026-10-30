# Completion campaign: NBA reference batch 17

This increment prepares fixed checkpoint-validation HOU–OKC episode
`hou-vs-okc-0022400879_e05`, source `23.mp4`, native frames **0–239**.
The 240 selected frames cover **[0,4) seconds**. The complete native/slow review
was reviewed for human reference acceptance. Ryan accepted all 240 proposals
on October 23, 2026, with the exact statement **“Accept all 240 proposals”**.
The original pending proposal and review remain unchanged; acceptance is a
separate publication.

The [acceptance record](../configs/ball_tracking/reviews/nba_completion_reference_batch_17_acceptance_v0_1.json)
binds all **212 centers and 28 unknown centers**, retaining **5–9px uncertainty**.
The actual publication audit preserves **5,406 original files** and passes the
accepted-reference reader and duplicate-identity guard in **27.810 seconds**.
The NBA inventory now contains **2,640 accepted judgments**, including
**2,426 centers and 214 nulls**: **1,920 training** and **720 validation**.
These fixed validation references remain excluded from gradient fitting.
Acceptance does not authorize checkpoint scoring, final trajectories, future
labels, package freezing, or protected evaluation. No playback completion or
exact acceptance-event UTC time is inferred from the user reply.

## Fixed role and timing

The [configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_17_v0_1.json)
retains the unchanged [source roles](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json).
The game was assigned checkpoint validation before new model predictions.
These references are reserved for later saved-checkpoint selection and excluded
from gradient fitting. Both eligibility flags in the preserved pending artifacts
remain false; the separate accepted publication records the accepted role.

The source is 1280×720 at 60 fps, timebase 1/60000, with 559 frames.
Batch final **239** differs from full-source final **558**. Selected PTS are
0–239000 in [0,240000), with 1000 ticks per frame. The fixed source-selection
category is recovery; its source-only notes identify overlap during a handoff
and later ball reappearance. Per-frame proposals must retain uncertainty and
unknown centers wherever current pixels do not support a defensible center.

## Source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_17/preparation.json)
and [pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_17/source_pixel_audit.json)
pass all **240 exact PNG and native PTS checks**. PyAV pixels match explicit
BT.709 TV-range to full-range RGB conversion by FFmpeg. Both paths use FFmpeg
components; this checks pixel transport rather than independent ground truth.
All **4,883 prior files** remain unchanged. The first attempt passes in
**42.630 seconds**.

The primary decoder returned frames 0–239 after 241 submitted packets.
Alternate conversion emitted 240 RGB frames and reported filter frames 0–240.
Filter frame 240 is disclosed context from the same validation source; only
selected frames 0–239 were saved.

## Manual proposals and inspection

All three sealed parts provide **212 centers and 28 nulls** across 240 judgments,
with **5–9px center uncertainty**. Visibility is **200 partial, 20 full,
16 not visible and four indeterminate**. Each current source/proposed frame and
full part endpoint has been inspected. Null-center frames are **0–7, 12–13,
22–29, 162–165 and 214–219**.

The first [inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_17/inspection/part_0_79_receipt.json)
seals **62 centers and 18 nulls**, with 68 partial/12 not-visible judgments and
**5–9px uncertainty**. Early body overlap hides the ball or leaves insufficient
fragments. Visible arcs at 8–11 and 14–21 support broad partial centers;
14–17 remain especially uncertain at 9px. Exposed contours support centers
from 30 onward. Root inspected all 80 source frames, detail and precision crops,
every proposed overlay crop and full native/proposed endpoints 0/79. A second
AI source review corroborated the early null intervals and broad uncertainty;
it is not independent human ground truth.

Original broad crops clipped the ball at 76–79. Those assets remain retained;
wider precision crops were inspected before annotation. The initial writer
failed on an unsupported `body_overlap` tag at its first row, before publishing
a proposal or running an overlay (**0.5026152 seconds**). The original helper
and failure are retained. Its v2 replacement changes only that vocabulary to
`player_overlap`; no coordinate, visibility or uncertainty changed. The
successful initial proposal remains unchanged after visual review.

The middle [inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_17/inspection/part_80_159_receipt.json)
seals **80 partially visible centers and zero nulls**, with **5–6px uncertainty**.
The handler holds, extends and returns the ball beside his waist. Hand overlap
persists throughout; the final eight frames also include a small body-edge
overlap. Every source/proposed frame and full endpoints 80/159 were inspected.
The initial annotations remain unchanged, with no failed attempts or incidents.

The final [inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_17/inspection/part_160_239_receipt.json)
seals **70 centers and ten nulls**, with **6–8px center uncertainty**. Visibility
is 52 partial, 20 full, four indeterminate and four not visible. Frames 162–165
remain indeterminate/null during hand/body overlap. Frames 214–217 are occluded;
218–219 retain partial visibility but lack enough contour for a reliable center.
Centers resume at 220 from current visible contours. No coordinate bridges
either null interval.

Every current source/proposed frame and full endpoints 160/239 were inspected,
including enlarged source details around overlap, release and the final frame.
The separated ball at 186–205 carries 8px uncertainty for motion blur. Final
239 supports **[439,152] ±8 pixels**, partially visible with hand/net overlap.
The original part is unchanged, with no annotation corrections, helper failures
or read-only incidents. Complete encoded review and finalization have passed.
These AI inspections do not establish independent human ground truth or Ryan's
label acceptance.

## Complete review and validation

- [Complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_17/review_v1/index.html)
- [Native overlay: 4 seconds at 60 fps](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_17/review_v1/review_native.mp4)
- [Slow overlay: 24 seconds at 10 fps](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_17/review_v1/review_slow.mp4)
- [All 240 proposals](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_17/proposal.json) and [28 null-center exceptions](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_17/review_v1/exception_list.json)
- [Root visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_17/inspection/root_visual_review.json)

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_17_result_v0_1.json)
and [integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_17/integration_audit.json)
pass **5,475 bindings, 240 native source/annotation joins, 480 encoded frames
and 424 center markers**, plus all **240 exact source PNG checks**. All-frame
pixel comparisons and emitted color checks pass. Null-center exceptions remain
unmarked and visible for review rather than being replaced with coordinates.

Root actually inspected all 20 final encoded sheets, all **212 encoded center
crops**, **28 unmarked null source contexts** and both full actual encoded
finals before recording the visual receipt. Root personally inspected full
native source 0/79/239; the three sealed part receipts collectively cover every
source/proposed frame and full part endpoint. Final 239 retains
**[439,152] ±8 pixels**, partially visible with hand/net overlap.

Delivery passed its first attempt in **27.750 seconds**. Finalization passed
its first attempt in **10.312 seconds**, including the pending-reader check;
the integration audit was recorded at **9.875 seconds**. The historical delivery record's
`rendered_awaiting_root_visual_inspection` status is superseded by the later
visual receipt and final result. The retained first writer failure and source
crop adjustments are recorded above. No annotation geometry or media changed
after publication. The actual pending-review reader passes all 240 joins and
creates zero accepted labels.

All **2,400 accepted NBA rows**, **868 curated references** and **4,883 files
captured before source preparation** remain unchanged. Earlier acceptance
preservation snapshots stay bound and overlap. Historical **13-test renderer**
and current **12-test acceptance-reader** receipts cover unchanged source;
the original eight-test acceptance history remains separate. No tests were
rerun for this increment. No model inference, fitting or checkpoint scoring ran.

## Campaign status at original delivery

The figures and pending decision below preserve the original review-delivery
state. Ryan's subsequent NBA17 acceptance above supersedes that pending step.
The current next review is [NBA18](ball_tracking_completion_nba_reference_batch_18.md).

Ryan's separate NBA16 acceptance publication supplies **2,400 accepted NBA
judgments, 2,214 centers and 186 nulls**. Accepted roles are **1,920 training
and 480 checkpoint validation**; **1,439 selected judgments remain unaccepted:
959 training and 480 validation**. Its publication preserves **4,936 original
files**, all 2,280 earlier NBA rows and all 868 curated references, and passes
the actual publication/inventory readers and duplicate-native-frame guard in
**25.370 seconds**. The original NBA16 proposals, review media, corrections and
restart history remain unchanged.

Curated references remain evaluation-only: **868 accepted, 760 eligible centers
and 405 uncovered**. These **240 pending proposals** leave **1,199 positions
without proposals** and **1,439 without accepted references**. Next is Ryan's
acceptance or correction of the complete review. The complete accepted
source/label/role package and executable recipe must be frozen before the already
approved fit. No completion-campaign fit has run. Protected evaluation remains
closed pending a frozen method and separate explicit authorization.
