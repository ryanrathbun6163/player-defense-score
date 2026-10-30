# Completion campaign: NBA reference batch 06

Ryan accepted this increment for fixed CHI–IND episode
`chi-vs-ind-0022400868_e06`, native source frames **240–479** of `221.mp4`.
The fixed window contains **240 frames**, spanning **[4,8) seconds**.
The [complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_06/review_v1/index.html)
contains **224 centers and 16 nulls**, with **5–8px uncertainty**.
The [four-second native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_06/review_v1/review_native.mp4)
and [24-second slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_06/review_v1/review_slow.mp4)
retain every selected frame. Every source/proposed frame, encoded center crop,
null-context crop and full native/slow final 479 was inspected. Ryan then said
**“Looks good. Please move forward chat. I approve the batch”** in response to
the complete NBA06 review and status. The separate
[acceptance receipt](../configs/ball_tracking/reviews/nba_completion_reference_batch_06_acceptance_v0_1.json)
records acceptance of all 240 judgments, including uncertainty and null centers.
The original preparation records and media retain their pending-era status.
No fitting or protected evaluation has run.

NBA06 acceptance brings the combined inventory to **960 accepted NBA labels:
836 centers and 124 nulls**, completing all six fixed CHI–IND episodes.
Of 3,839 selected judgments, **2,879 are not yet accepted**. The
[publication audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_06/acceptance_audit/publication_audit.json)
preserves **2,000 original files**, all 720 prior NBA labels and all 868 curated
references. Actual publication/inventory readers pass and the duplicate guard
rejects repeated native frames. Curated coverage remains **868/1,273 accepted**,
with **760 eligible centers** and **405 uncovered**.

## Fixed source and native timing

The [batch configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_06_v0_1.json)
uses the episode fixed in the
[source-role manifest](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json)
before new-model predictions. Its entire CHI–IND parent game retains the training
role. Native source identity includes the original video hash.

The source is **1280×720 at 60 fps**, with a **1/60000-second timebase** and
1000-tick frame durations. Selected PTS are **240000–479000**, in the half-open
interval **[240000,480000) ticks**. Batch final is **479**; the full 719-frame
source ends at **718**. Native PTS, source-relative time and review-relative time
remain separate. Both complete review videos retain all 240 selected frames,
giving four seconds at native 60 fps and 24 seconds at slow 10 fps.

## Completed source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_06/preparation.json)
and [source-pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_06/source_pixel_audit.json)
pass all **240 selected native PNG comparisons and PTS checks**. Saved PyAV
pixels match explicit BT.709 FFmpeg RGB conversion exactly; original PNGs remain
unchanged. All **1,507 files captured before preparation** are preserved. Both
decoder paths use FFmpeg components, so these comparisons establish transport
consistency rather than independent visual truth.

The primary decoder submitted **481 packets** and returned **frames 0–479**,
saving only selected frames 240–479. The alternate conversion emitted **480 RGB
frames** and reported **481 filter frames, 0–480**. Lead-in frames 0–239 and filter
frame 480 are disclosed context from the same training-role source, not additional
labels or review frames. Preparation succeeded on its first attempt.

## Proposed references

The [assembled proposal](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_06/proposal.json)
retains **134 partially visible, 100 fully visible, four not-visible and two
indeterminate judgments**. Null centers
remain at frames **280–285 and 404–413**: two unresolved observations at 280–281,
four occlusions at 282–285 and ten partial rim/net fragments at 404–413. Visible
fragments without a defensible whole-ball center remain null. The 224 proposed
centers carry 5–8-source-pixel uncertainty, a placement estimate rather than a
calibrated confidence interval. The
[exception list](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_06/review_v1/exception_list.json)
retains uncertain observations and their notes. Every center comes from separately
inspected current-frame source pixels; no temporal interpolation or model
coordinates supply these judgments. All three initial parts remain final,
without annotation corrections or helper failures.

The original proposals remain unchanged with pending-era eligibility flags.
The separate accepted publication makes these fixed-role training references
eligible for the future frozen package. Acceptance does not approve final
trajectories, complete the package or open protected evaluation.

The renderer and acceptance reader remain unchanged. Prior **13-test renderer
and 12-test acceptance-reader evidence** remains historical. No suite was rerun;
the actual source, annotation and encoded-media joins were verified separately
under explicit prior-implementation test scope.

## Complete review validation

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_06_result_v0_1.json)
retains its preparation-time status `ready_for_human_reference_acceptance`. The
[integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_06/integration_audit.json)
passes **2,014 file bindings, 240 native source/annotation joins, 480 encoded
frames and 448 center markers**. Both videos contain all 240 selected frames
at 60/10 fps (4s/24s); emitted color metadata and every encoded-frame comparison
pass. All 20 inspection sheets, including 224 encoded center crops and 16
unmarked null-context crops, were inspected through the actual final. The full
native source frame 479 and both full encoded finals were also inspected. The
[visual-inspection receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_06/inspection/root_visual_review.json)
binds the inspected assets. The actual pending-review consumer passes without
accepting any labels.

At preparation, all **720 earlier accepted NBA labels** and **868 curated references** remained unchanged.
The audit preserves the 1,507-file source-preparation snapshot and all five prior
acceptance snapshots: **286 NBA01, 543 NBA02, 809 NBA03, 1,050 NBA04 and 1,549
NBA05 files**. These preservation sets overlap. Source preparation, delivery and
finalization succeeded on their first attempts. Transport checks and AI
inspection establish review integrity; they do not measure model accuracy or
replace Ryan's acceptance.

Continue with the next fixed NBA episode. Its new proposals need separate
acceptance before use as training references. Freeze the full accepted
source/label/role package and executable recipe before the approved fit;
protected evaluation requires a frozen method and separate explicit authorization.
