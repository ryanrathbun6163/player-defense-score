# Completion campaign: NBA reference batch 18

## Acceptance recorded on 2026-10-23

Ryan said **“I accept these proposals. Do we only have 1 more batch now?”**
in response to the complete NBA18 review. The separate
[acceptance receipt](../configs/ball_tracking/reviews/nba_completion_reference_batch_18_acceptance_v0_1.json)
and [publication audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/acceptance_audit/publication_audit.json)
record acceptance of all **240 judgments** for HOU–OKC e06 frames **210–449**:
**212 centers, 28 nulls, 128 full/94 partial/18 not-visible judgments and
5–9px center uncertainty**. The date is October 23, 2026 in America/Phoenix;
exact user-event UTC is null. Publication time is separate, with no playback
telemetry or independent human annotation claim.

Publication passes the actual reference/inventory readers and duplicate-native-
frame guard in **31.616 seconds**, preserving **5,882 original files**, all
**2,640 earlier NBA rows** and all **868 curated references**. Original proposals,
review media, failures, corrections and inspection history remain unchanged.
No source pixel decoding, model inference, fitting, scoring or tests ran during
acceptance publication. No repeat NBA18 review is needed.

Current NBA coverage is **2,880/3,839 accepted: 2,638 centers and 242 nulls**,
comprising **1,920 training and all 960 checkpoint-validation judgments**.
One NBA game remains: **SAC–MEM, with six fixed episodes totaling 959 training
judgments**. The episode sizes are **120, 120, 120, 120, 239 and 240**; the
current one-episode review pattern therefore means **six NBA review batches**.
The separate curated package still has **405 uncovered positions** alongside
868 accepted judgments and 760 eligible centers. No next NBA batch was prepared
in this acceptance-only increment.

Accepted validation references remain excluded from gradient fitting. The
completion-campaign fit has not started: the complete accepted source/label/role
package and executable recipe must be frozen first. New labels still require
acceptance. Protected evaluation remains closed pending a frozen method and
separate explicit authorization.

## Historical preparation and review before acceptance

The original pending-era account below is retained unchanged. Its pending
language and earlier counts are superseded by the separate acceptance above.

This increment prepares fixed checkpoint-validation HOU–OKC episode
`hou-vs-okc-0022400879_e06`, source `253.mp4`, native frames **210–449**.
The 240 selected frames cover **[3.5,7.5) seconds**. The complete native/slow
review is ready for human reference acceptance. All 240 new judgments remain
pending; preparation and review create no accepted labels.

## Fixed role and timing

The [configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_18_v0_1.json)
retains the unchanged [source roles](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json).
The game was assigned checkpoint validation before new model predictions.
These references are reserved for later saved-checkpoint selection and excluded
from gradient fitting. Both pending eligibility flags remain false.

The source is 1280×720 at 60 fps, timebase 1/60000, with 511 frames.
Batch final **449** differs from full-source final **510**. Selected PTS are
210000–449000 in [210000,450000), with 1000 ticks per frame. The fixed
source-selection category is recovery; source-only notes describe a crowded
drive, shot and rebound with ball obscuration among arms and bodies. Per-frame
proposals must preserve uncertainty and unknown centers wherever current pixels
do not support a defensible center.

## Source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/preparation.json)
and [pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/source_pixel_audit.json)
pass all **240 exact PNG and native PTS checks**. PyAV pixels match explicit
BT.709 TV-range to full-range RGB conversion by FFmpeg. Both paths use FFmpeg
components; this checks pixel transport rather than independent ground truth.
All **5,352 prior files** remain unchanged. Successful source preparation takes
**46.364 seconds**.

The initial preparation command failed after **0.5438975 seconds**, before
pixel decoding or creation of preparation outputs: inspection-helper setup
had already created the destination directory, which the preparer requires to
be absent. The [failure record](../data/outputs/ball_tracking/completion_campaign_v0_1/setup_nba18_preserved_20261023_01/preparation_initial_failure.json)
and original setup/helpers remain in the separate preserved directory. The
unchanged preparer then ran at the available configured path; helper copies
were restored unchanged. The failed attempt remains a failure.

The primary decoder returned frames 0–449 after 451 submitted packets.
Alternate conversion emitted 450 RGB frames and reported filter frames 0–450.
Prefix 0–209 and filter frame 450 are disclosed context from the same validation
source; only selected frames 210–449 were saved.

A premature read-only documentation lookup found that the NBA18 configuration
had not yet been created. It created or changed no data or review output;
documentation subsequently used the completed configuration and preparation.

## Manual proposals and inspection

All three sealed parts provide **212 centers and 28 nulls** across 240 judgments,
with **5–9px center uncertainty**. Visibility is **128 full, 94 partial and
18 not visible**. Each current source/proposed frame and full part endpoint has
been inspected. Null-center frames are **210–221, 238–245, 264–267 and 274–277**.

The first [inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/inspection/part_210_289_receipt.json)
seals **52 centers and 28 nulls**, with 56 partial/six full/18 not-visible
judgments and **6–9px uncertainty**. Body/arm overlap hides the ball at 210–221
and 240–245; fragments at 238–239, 264–267 and 274–277 do not support stable
whole-ball centers. Separated dribble contours at 224–229 support full centers;
the remaining localized frames retain overlap and blur. No null interval is
interpolated. Root inspected all 80 source frames, all detail/precision/extra
crops, every proposed overlay crop and full native/proposed endpoints 210/289.
A second AI source-only review corroborated conservative missingness and broad
partial centers; it does not establish independent human ground truth.

Original detail crops clipped the upper ball in some later frames. Precision
crops expanded coverage; additional crops corrected clipping at 252–253 and
282–283 before annotation. All original inspection assets remain retained.
The first writer failed after **0.3872014 seconds** at frame 224 because the
schema requires `observed_complete_ball_center` for fully visible geometry.
It failed before proposal publication or overlay execution. The original writer
and [failure](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/inspection/part_210_289_write_failure.json)
remain retained; v2 corrects only that geometry-source metadata for full rows,
keeping the legacy amodal source value for partial rows. Coordinates, visibility
and uncertainty did not change. The successful initial proposal is unchanged.

The middle [inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/inspection/part_290_369_receipt.json)
seals **80 centers and zero nulls**, with 72 fully visible/eight partial judgments
and **5–8px uncertainty**. Frames 290–297 retain hand overlap at release;
298–369 show a separated ball against the crowd and backboard. The ball remains
identifiable near the rim, including the softer images at 346–353. Every current
source/proposed frame and full endpoints 290/369 were inspected. Initial
annotations remain unchanged. The receipt preserves the earlier source-setup
failure separately from annotation work.

The final [inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/inspection/part_370_449_receipt.json)
seals **80 centers and zero nulls**, with 50 fully visible/30 partial judgments
and **5–7px uncertainty**. The ball descends against the backboard and crowd,
then passes the rim/net and reaching hands. Frames 396–415 and 422–431 retain
partial visibility; current outer arcs and exposed ball body support centers.
The remaining frames have separated complete contours. Every current
source/proposed frame and full endpoints 370/449 were inspected, including
enlarged source views around rim, net and hand overlap.

Final 449 supports **[351,307] ±6 pixels**, fully visible as the ball moves left
away from the hands. Initial annotations remain unchanged. The earlier source
preparation failure and original helper remain preserved. Complete encoded
review and finalization have passed. These AI inspections do not establish
independent human ground truth or Ryan's reference acceptance.

## Complete review and validation

- [Complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/review_v1/index.html)
- [Native overlay: 4 seconds at 60 fps](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/review_v1/review_native.mp4)
- [Slow overlay: 24 seconds at 10 fps](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/review_v1/review_slow.mp4)
- [All 240 proposals](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/proposal.json) and [28 null-center exceptions](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/review_v1/exception_list.json)
- [Root visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/inspection/root_visual_review.json)

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_18_result_v0_1.json)
and [integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/integration_audit.json)
pass **5,959 bindings, 240 native source/annotation joins, 480 encoded frames
and 424 center markers**, plus all **240 exact source PNG checks**. All-frame
pixel comparisons and emitted color checks pass. Null-center exceptions remain
unmarked and visible for review rather than being replaced with coordinates.

Root actually inspected all 20 final encoded/source sheets, all **212 localized
encoded centers**, **28 unmarked null source contexts**, full native source 449
and both full actual encoded finals before recording the visual receipt.
The three sealed part receipts collectively cover every current source/proposed
frame and full part endpoint. Final 449 retains **[351,307] ±6 pixels**, fully
visible as the ball moves left away from the hands.

Delivery passed its first attempt in **29.813 seconds**. Finalization passed
its first attempt in **13.000 seconds**, including the pending-reader check;
the integration audit was recorded at **12.562 seconds**. The historical
delivery record's `rendered_awaiting_root_visual_inspection` status is superseded
by the later visual receipt and final result. The initial source-preparation
failure, root writer failure, crop adjustments and read-only lookup incident
remain recorded above. No annotation geometry or media changed after publication.
The actual pending-review reader passes all 240 joins and creates zero accepted
labels.

All **2,640 accepted NBA rows**, **868 curated references** and **5,352 files
captured before source preparation** remain unchanged. Earlier acceptance
preservation snapshots stay bound and overlap. Historical **13-test renderer**
and current **12-test acceptance-reader** receipts cover unchanged source;
the original eight-test acceptance history remains separate. No tests were
rerun for this increment. No model inference, fitting or checkpoint scoring ran.

## Campaign status and next decision

Ryan's separate NBA17 acceptance publication supplies **2,640 accepted NBA
judgments, 2,426 centers and 214 nulls**. Accepted roles are **1,920 training
and 720 checkpoint validation**; **1,199 selected judgments remain unaccepted:
959 training and 240 validation**. Its publication preserves **5,406 original
files**, all 2,400 earlier NBA rows and all 868 curated references, and passes
the actual publication/inventory readers and duplicate-native-frame guard in
**27.810 seconds**. The original NBA17 proposals, review media, failure history,
source crops and source-only second-AI review remain unchanged.

Curated references remain evaluation-only: **868 accepted, 760 eligible centers
and 405 uncovered**. These **240 pending proposals** leave **959 positions without
proposals** and **1,199 without accepted references**. The complete accepted
source/label/role package and executable recipe must be frozen before the already
approved fit. Next is Ryan's acceptance or correction of the complete NBA18
review, then continued fixed-package preparation. No completion-campaign fit
has run. Protected evaluation remains closed pending a frozen method and
separate explicit authorization.
