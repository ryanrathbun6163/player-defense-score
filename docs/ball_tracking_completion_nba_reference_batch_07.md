# Completion campaign: NBA reference batch 07

This increment is ready for reference acceptance for the first fixed DEN–BOS episode,
`den-vs-bos-0022400866_e01`, original source `3.mp4`, native frames **0–119**.
The selected window contains **120 frames**, spanning **[0,2) seconds**.
The [complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_07/review_v1/index.html)
contains **120 partially visible centers, zero nulls and 5–6px uncertainty**.
The [two-second native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_07/review_v1/review_native.mp4)
and [12-second slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_07/review_v1/review_slow.mp4)
retain every selected frame. Every source/proposed frame, encoded center crop
and full native/slow final 119 was inspected. All 120 proposals remain pending
Ryan's separate acceptance. No fitting or protected evaluation has run.

[NBA06 acceptance](ball_tracking_completion_nba_reference_batch_06.md) brings
the combined NBA inventory to **960 accepted labels: 836 centers and 124 nulls**,
completing all six fixed CHI–IND episodes. Of 3,839 selected judgments,
**2,879 remain unaccepted**; these 120 proposals leave **2,759 without proposals**.
Curated coverage remains **868/1,273 accepted**,
with **760 eligible centers** and **405 uncovered**.

Ryan said **“Looks good. Please move forward chat. I approve the batch”** in
response to the complete NBA06 review. Its separate
[acceptance receipt](../configs/ball_tracking/reviews/nba_completion_reference_batch_06_acceptance_v0_1.json)
preserves 2,000 original files and all earlier accepted labels. That decision
does not accept these new DEN–BOS proposals.

## Fixed source and native timing

The [batch configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_07_v0_1.json)
uses the episode fixed in the
[source-role manifest](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json)
before new-model predictions. Its entire DEN–BOS parent game retains the training
role. Native source identity includes the original video hash.

The source is **1280×720 at 60 fps**, with a **1/60000-second timebase** and
1000-tick frame durations. Selected PTS are **0–119000**, in the half-open
interval **[0,120000) ticks**. Batch final is **119**; the full 603-frame source
ends at **602**. Native PTS, source-relative time and review-relative time are
recorded separately. Both complete review videos retain all 120 selected frames,
giving two seconds at native 60 fps and 12 seconds at slow 10 fps.

## Completed source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_07/preparation.json)
and [source-pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_07/source_pixel_audit.json)
pass all **120 selected native PNG comparisons and PTS checks**. Saved PyAV
pixels match explicit BT.709 FFmpeg RGB conversion exactly; original PNGs remain
unchanged. All **1,957 files captured before preparation** are preserved. Both
decoder paths use FFmpeg components, so these comparisons establish transport
consistency rather than independent visual truth.

The primary decoder submitted **121 packets** and returned **frames 0–119**.
The alternate conversion emitted **120 RGB frames** and reported **121 filter
frames, 0–120**. Filter frame 120 is disclosed context from the same training-role
source, not an additional label or review frame. Only selected frames 0–119
were saved. Preparation succeeded on its first attempt.

## Proposed references

The [assembled proposal](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_07/proposal.json)
contains **120 partially visible judgments**, with defensible whole-ball centers
and **5–6-source-pixel uncertainty**. No frame requires a null center. Uncertainty
is a placement estimate rather than a calibrated confidence interval. The
[exception list](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_07/review_v1/exception_list.json)
is empty. Partial visibility and per-frame uncertainty remain explicit in the
proposal and complete review; an empty exception list does not imply certainty.

The right-wing ballhandler holds the ball overhead, lowers it toward the waist,
then continues holding it as teammates move and cut. No pass occurs during the
selected window. Hands and fingers partly obscure the ball, while exposed arcs
support its whole center. Compression, slight blur and repeated/near-repeated
source imagery remain in the review.

Every current-frame source image and proposed overlay was inspected, including
full native/proposed endpoints for all three parts. Each center was manually
proposed from that frame's pixels; no model coordinates or temporal interpolation
supplied positions. All three initial parts remain final, without corrections
or helper failures. New labels remain pending, with training and checkpoint
selection eligibility false.

The renderer and acceptance reader remain unchanged; their prior
**13-test and 12-test evidence** is historical, with no new suite run claimed.
The actual source, annotation and encoded-media joins were verified separately
under explicit prior-implementation test scope. The original eight-test
acceptance-reader record remains separate retained history.

## Complete review validation

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_07_result_v0_1.json)
is `ready_for_human_reference_acceptance`. The
[integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_07/integration_audit.json)
passes **2,264 file bindings, 120 native source/annotation joins, 240 encoded
frames and 240 center markers**. Both videos contain all 120 selected frames
at 60/10 fps (2s/12s); emitted color metadata and every encoded-frame comparison
pass. All ten inspection sheets and 120 encoded center crops were inspected
through actual batch final 119. The full native source frame 119 and both full
encoded finals were also inspected. The
[visual-inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_07/inspection/root_visual_review.json)
binds the inspected assets. The actual pending-review consumer passes without
accepting any labels.

All **960 accepted NBA labels** and **868 curated references** remain unchanged.
The audit preserves the 1,957-file source-preparation snapshot and all six prior
acceptance snapshots: **286 NBA01, 543 NBA02, 809 NBA03, 1,050 NBA04, 1,549 NBA05
and 2,000 NBA06 files**. These preservation sets overlap. Source preparation,
delivery and finalization succeeded on their first attempts. Transport checks
and AI inspection establish review integrity; they do not measure model accuracy
or replace Ryan's acceptance.

Ryan's acceptance or corrections for these 120 proposals is the next step.
New proposals need his acceptance before use as training references. Freeze the
full accepted source/label/role package and executable recipe before the already
approved fit; protected evaluation requires
a frozen method and separate explicit authorization.
