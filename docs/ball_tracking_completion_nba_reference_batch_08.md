# Completion campaign: NBA reference batch 08

Ryan accepted this increment for the second fixed DEN–BOS episode,
`den-vs-bos-0022400866_e02`, original source `19.mp4`, native frames **0–119**.
The selected window contains **120 frames**, spanning **[0,2) seconds**.
The [complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_08/review_v1/index.html)
contains **120 centers, zero nulls and 4–6px uncertainty**.
The [two-second native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_08/review_v1/review_native.mp4)
and [12-second slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_08/review_v1/review_slow.mp4)
retain every selected frame. Every source/proposed frame, encoded center crop
and full native/slow final 119 was inspected. Ryan answered
**“I approve chat. Move forward”** after the review and question identifying
all 120 proposals, including 92 partial and 28 full centers and 4–6px uncertainty.
The separate [acceptance receipt](../configs/ball_tracking/reviews/nba_completion_reference_batch_08_acceptance_v0_1.json)
records that decision. Original preparation records and media retain their
pending-era status. No fitting or protected evaluation has run.

Ryan later answered **“Accept all 120 proposals”** to the same structured question.
A separate [follow-up confirmation](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_08/acceptance_audit/explicit_followup_confirmation.json)
retains that reaffirmation without changing the accepted publication or counting
the labels twice. It does not accept NBA09.

NBA08 acceptance brings the combined NBA inventory to **1,200 accepted labels:
1,076 centers and 124 nulls**. Of 3,839 selected judgments, **2,639 remain unaccepted**.
The [publication audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_08/acceptance_audit/publication_audit.json)
preserves **2,490 original files**, all 1,080 earlier accepted NBA labels and all
868 curated references. Actual publication/inventory readers pass and the
duplicate guard rejects repeated native frames.
Curated coverage remains **868/1,273 accepted**, with **760 eligible centers**
and **405 uncovered**.

The earlier [NBA07 acceptance](ball_tracking_completion_nba_reference_batch_07.md)
remains intact. NBA08's new receipt supplies its separate acceptance authority;
future batches still require their own acceptance.

## Fixed source and native timing

The [batch configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_08_v0_1.json)
uses the episode fixed in the
[source-role manifest](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json)
before new-model predictions. Its entire DEN–BOS parent game retains the training
role. Native source identity includes the original video hash.

The source is **1280×720 at 60 fps**, with a **1/60000-second timebase** and
1000-tick frame durations. Selected PTS are **0–119000**, in the half-open
interval **[0,120000) ticks**. Batch final is **119**; the full 399-frame source
ends at **398**. Native PTS, source-relative time and review-relative time are
recorded separately. Both complete review videos retain all 120 selected frames,
giving two seconds at native 60 fps and 12 seconds at slow 10 fps.

## Completed source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_08/preparation.json)
and [source-pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_08/source_pixel_audit.json)
pass all **120 selected native PNG comparisons and PTS checks**. Saved PyAV
pixels match explicit BT.709 FFmpeg RGB conversion exactly; original PNGs remain
unchanged. All **2,201 files captured before preparation** are preserved. Both
decoder paths use FFmpeg components, so these comparisons establish transport
consistency rather than independent visual truth.

The primary decoder submitted **121 packets** and returned **frames 0–119**.
The alternate conversion emitted **120 RGB frames** and reported **121 filter
frames, 0–120**. Filter frame 120 is disclosed context from the same training-role
source, not an additional label or review frame. Only selected frames 0–119
were saved. Preparation succeeded on its first attempt in **22.15 seconds**.

## Proposed references

The [assembled proposal](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_08/proposal.json)
contains **120 centers**, comprising **92 partially visible and 28 fully visible
judgments**, with **4–6-source-pixel uncertainty** and no nulls. The free-throw
shooter gathers and raises the ball toward the shooting position. Hand/finger overlap remains through frame 91; the ball is
visibly separated and airborne in frames 92–119, passing across court, bench
and crowd backgrounds. Compression, blur and repeated/near-repeated source
imagery remain in the review.

Every current-frame source/context and proposed overlay was inspected,
including full native/proposed endpoints for all three parts. Each first written
part remains final, without corrections or failures. The
[exception list](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_08/review_v1/exception_list.json)
is empty; partial visibility and uncertainty remain explicit in every applicable
proposal and the complete review.

Centers are manually proposed from each frame's pixels, without model
coordinates or temporal interpolation. Uncertainty is a placement estimate,
not a calibrated confidence interval. AI authorship remains explicit. Fixed
training role alone does not accept the labels. Both eligibility flags remain
false in the original preparation records; the separate accepted publication
now makes these training references eligible at label scope.

The renderer and acceptance reader remain unchanged; their prior
**13-test and 12-test evidence** is historical, with no new suite run claimed.
The actual source, annotation and encoded-media joins were verified separately
under explicit prior-implementation test scope. The original eight-test
acceptance-reader record remains separate retained history.

## Complete review validation

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_08_result_v0_1.json)
retains its preparation-time `ready_for_human_reference_acceptance` status. The
[integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_08/integration_audit.json)
passes **2,514 file bindings, 120 native source/annotation joins, 240 encoded
frames and 240 center markers**. Both videos contain all 120 selected frames
at 60/10 fps (2s/12s); emitted color metadata and every encoded-frame comparison
pass. All ten inspection sheets and 120 encoded center crops were inspected
through actual batch final 119. The full native source frame 119 and both full
encoded finals were also inspected. Final frame 119 retains center **[527,82]**
with **6px uncertainty**. The
[visual-inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_08/inspection/root_visual_review.json)
binds the inspected assets. The actual pending-review consumer passes without
accepting any labels.

All **1,080 earlier accepted NBA labels** and **868 curated references** remain
unchanged. The audit preserves the 2,201-file source-preparation snapshot and
all seven prior acceptance snapshots: **286 NBA01, 543 NBA02, 809 NBA03,
1,050 NBA04, 1,549 NBA05, 2,000 NBA06 and 2,245 NBA07 files**. These preservation
sets overlap. Source preparation, delivery and finalization succeeded on their
first attempts. No tests were rerun. Transport checks and AI inspection establish
review integrity; they do not measure model accuracy or replace Ryan's acceptance.

Continue the next fixed DEN–BOS episode, with separate review of its new proposals.
Freeze the full accepted source/label/role package and executable recipe before
the already approved fit; protected evaluation requires a frozen method and
separate explicit authorization.
