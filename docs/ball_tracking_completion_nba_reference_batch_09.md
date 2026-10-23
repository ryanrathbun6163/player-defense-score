# Completion campaign: NBA reference batch 09

This increment prepares the third fixed DEN–BOS episode,
`den-vs-bos-0022400866_e03`, original source `44.mp4`, native frames **0–119**.
The selected window contains **120 frames**, spanning **[0,2) seconds**.
The [complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_09/review_v1/index.html)
is ready for separate acceptance: **120 centers, zero nulls and 5–8px uncertainty**.
The [two-second native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_09/review_v1/review_native.mp4)
and [12-second slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_09/review_v1/review_slow.mp4)
retain every selected frame. Every source/proposed frame, encoded center crop
and full native/slow final 119 was inspected. All 120 labels remain pending
Ryan's separate acceptance. No fitting or protected evaluation has run.

[NBA08 acceptance](ball_tracking_completion_nba_reference_batch_08.md) brings
the combined NBA inventory to **1,200 accepted labels: 1,076 centers and 124 nulls**.
Of 3,839 selected judgments, **2,639 remain unaccepted**. Its separate publication
preserves **2,490 original files** and passes actual publication/inventory readers
and the duplicate-frame guard. NBA09 is not covered by that acceptance.
NBA08's later [explicit confirmation](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_08/acceptance_audit/explicit_followup_confirmation.json)
reaffirms its unchanged receipt, adds zero labels and explicitly excludes NBA09.
NBA09 proposals leave **2,519 selected positions without proposals**.
Curated coverage remains **868/1,273 accepted**, with **760 eligible centers**
and **405 uncovered**.

## Fixed source and native timing

The [batch configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_09_v0_1.json)
uses the episode fixed in the
[source-role manifest](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json)
before new-model predictions. Its entire DEN–BOS parent game retains the training
role. Native source identity includes the original video hash.

The source is **1280×720 at 60 fps**, with a **1/60000-second timebase** and
1000-tick frame durations. Selected PTS are **0–119000**, in the half-open
interval **[0,120000) ticks**. Batch final is **119**; the full 475-frame source
ends at **474**. Native PTS, source-relative time and review-relative time are
recorded separately. Both complete review videos retain all 120 selected frames,
giving two seconds at native 60 fps and 12 seconds at slow 10 fps.

## Completed source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_09/preparation.json)
and [source-pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_09/source_pixel_audit.json)
pass all **120 selected native PNG comparisons and PTS checks**. Saved PyAV
pixels match explicit BT.709 FFmpeg RGB conversion exactly; original PNGs remain
unchanged. All **2,445 files captured before preparation** are preserved. Both
decoder paths use FFmpeg components, so these comparisons establish transport
consistency rather than independent visual truth.

The primary decoder submitted **121 packets** and returned **frames 0–119**.
The alternate conversion emitted **120 RGB frames** and reported **121 filter
frames, 0–120**. Filter frame 120 is disclosed context from the same training-role
source, not an additional label or review frame. Only selected frames 0–119
were saved. Preparation succeeded on its first attempt in **20.743 seconds**.

A routine [config-guard argument error](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_09/config_preflight_correction.json)
was corrected before the config was written. Two temporary model-capacity
[agent-dispatch failures](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_09/agent_dispatch_notes.json)
were retried with the same model and scope. These retained orchestration records
are separate from source-preparation and annotation evidence.

## Proposed references

The [assembled proposal](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_09/proposal.json)
contains **120 centers**, comprising **112 partially visible and eight fully
visible judgments**, with **5–8-source-pixel uncertainty** and no nulls. Complete
ball contours are visible at frames **12–15 and 80–83**; the remaining judgments
retain partial visibility. The advancing ballhandler dribbles as the camera pans
and a teammate moves toward a screen. Hand, leg and crossing-player overlap
remain explicit. Frames 72–75 carry 8px uncertainty; additional source detail
70–79 was inspected for overlap. No center was inferred through a hidden interval.

Every current-frame source/context and proposed overlay was inspected,
including full native/proposed endpoints for all three parts and an additional
contour crop for frames 80–85. All first written parts remain final, without
corrections or annotation-helper failures. The
[exception list](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_09/review_v1/exception_list.json)
is empty; partial visibility and uncertainty remain explicit in every applicable
proposal and the complete review.

Centers are manually proposed from each frame's pixels, without model
coordinates or temporal interpolation. Uncertainty is a placement estimate,
not a calibrated confidence interval. AI authorship remains explicit. Fixed
training role does not accept the labels; both eligibility flags remain false
while acceptance is pending.

The renderer and acceptance reader remain unchanged; their prior
**13-test and 12-test evidence** is historical, with no new suite run claimed.
The actual source, annotation and encoded-media joins were verified separately
under explicit prior-implementation test scope. The original eight-test
acceptance-reader record remains separate retained history.

## Complete review validation

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_09_result_v0_1.json)
is `ready_for_human_reference_acceptance`. The
[integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_09/integration_audit.json)
passes **2,768 file bindings, 120 native source/annotation joins, 240 encoded
frames and 240 center markers**. Both videos contain all 120 selected frames
at 60/10 fps (2s/12s); emitted color metadata and every encoded-frame comparison
pass. All ten inspection sheets and 120 encoded center crops were inspected
through actual batch final 119. The full native source frame 119 and both full
encoded finals were also inspected. Final frame 119 retains center **[185,335]**
with **5px uncertainty**. The
[visual-inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_09/inspection/root_visual_review.json)
binds the inspected assets, including the additional current-source 70–79 review.
The actual pending-review consumer passes without accepting any labels.

All **1,200 earlier accepted NBA labels** and **868 curated references** remain
unchanged. The audit preserves the 2,445-file source-preparation snapshot and
all eight prior acceptance snapshots: **286 NBA01, 543 NBA02, 809 NBA03,
1,050 NBA04, 1,549 NBA05, 2,000 NBA06, 2,245 NBA07 and 2,490 NBA08 files**.
These preservation sets overlap. Source preparation, delivery and finalization
succeeded on their first attempts; the separate config-check and capacity
failures remain recorded above. No tests were rerun. Transport checks and AI
inspection establish review integrity; they do not measure model accuracy or
replace Ryan's acceptance.

Obtain Ryan's separate acceptance or corrections for these 120 proposals.
Freeze the full accepted source/label/role package and executable recipe before
the already approved fit; protected evaluation requires a frozen method and
separate explicit authorization.
