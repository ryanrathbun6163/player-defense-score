# Completion campaign: NBA reference batch 05

Ryan accepted **all 240 frame judgments** for fixed CHI–IND episode
`chi-vs-ind-0022400868_e05`, native source frames **270–509** of `174.mp4`.
The [complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_05/review_v1/index.html)
is ready: **178 proposed centers and 62 nulls**, with **4–9px uncertainty**.
The [four-second native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_05/review_v1/review_native.mp4)
and [24-second slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_05/review_v1/review_slow.mp4)
retain every selected frame. Every source/proposed frame, encoded center crop,
null-context crop and full native/slow final 509 was inspected. Ryan answered
**“Accept all 240 proposals”** to the question identifying this exact batch,
its 178 centers, 62 unknown centers and 4–9px uncertainty. The separate
[acceptance receipt](../configs/ball_tracking/reviews/nba_completion_reference_batch_05_acceptance_v0_1.json)
preserves every judgment and AI authorship. Training eligibility applies only
to these accepted reference labels; checkpoint-selection eligibility remains
false. The original proposal and media retain their preparation-era status.

Following [NBA04](ball_tracking_completion_nba_reference_batch_04.md), the
combined inventory now contains **720 accepted NBA labels: 612 centers and
108 nulls**. Of 3,839 selected judgments, **3,119 are not yet accepted**.
[NBA06](ball_tracking_completion_nba_reference_batch_06.md) continues with fixed
CHI–IND e06 frames 240–479; its new labels need separate acceptance. Curated coverage
remains **868/1,273 accepted**, with **760 eligible centers** and **405 uncovered**.

The acceptance publication preserves **1,549 original files**. Actual publication,
inventory and duplicate-guard checks pass; no tests, source decoding, inference
or fitting were repeated for publication. The exact user-event timestamp remains
null, with publication time recorded separately. No playback telemetry or
independent human annotation is claimed.

## Fixed source and native timing

The [batch configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_05_v0_1.json)
uses the episode fixed in the
[source-role manifest](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json)
before new-model predictions. Its entire CHI–IND parent game retains the training
role. Native source identity includes the original video hash.

The source is **1280×720 at 60 fps**, with a **1/60000-second timebase** and
1000-tick frame durations.
Selected PTS are **270000–509000**, in the half-open interval
**[270000,510000) ticks**. Batch final is **509**; the full 757-frame source
ends at **756**. Native PTS, source-relative time and review-relative time remain
separate. Both complete review videos retain all 240 selected frames.

## Judgments and uncertainty

The [assembled proposal](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_05/proposal.json)
contains **170 partially visible, 32 fully visible, 32 not-visible and six
indeterminate judgments**. The 178 defensible whole-ball centers retain
**4–9-source-pixel uncertainty**, a placement estimate rather than a calibrated
confidence interval. The 62 nulls preserve **24 partial fragments, 32 occlusions
and six ambiguous observations**.

Null centers occur at frames **312–317, 356–389, 392–393, 442–453, 482–487 and
490–491**. The six indeterminate frames are **314–315, 370–371 and 386–387**:
their brown patches cannot be separated confidently from surrounding body or
limb surfaces. They remain distinct from certain-hidden judgments. Identifiable
partial fragments without enough whole-ball contour also remain null.

The sequence covers a drive/dribble behind the referee, handoff and body overlap,
then a pass, catch, gather and close-range finish. The ball later descends beside
the player. Blur, compression and repeated source imagery remain in the review.
Every center comes from separately inspected current-frame pixels; no model
coordinates or temporal interpolation supply positions. All three initial parts
remain final, without annotation revisions or helper failures.

## Completed source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_05/preparation.json)
and [source-pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_05/source_pixel_audit.json)
pass all **240 selected native PNG comparisons and PTS checks**. Saved PyAV
pixels match explicit BT.709 FFmpeg RGB conversion exactly; original PNGs remain
unchanged. All **1,009 files captured before preparation** are preserved. Both
decoder paths use FFmpeg components, so these comparisons establish transport
consistency rather than independent visual truth.

The primary decoder submitted **511 packets** and returned **frames 0–509**,
saving only selected frames 270–509. The alternate conversion emitted **510 RGB
frames** and reported **511 filter frames, 0–510**. Lead-in frames 0–269 and filter
frame 510 are disclosed context from the same training-role source, not additional
labels or review frames.

The renderer and acceptance reader remain unchanged. Prior **13-test renderer
and 12-test acceptance-reader evidence** remains historical. No suite was rerun;
the actual source, annotation and encoded-media joins were verified separately
under explicit prior-implementation test scope.

## Complete review validation

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_05_result_v0_1.json)
retains `ready_for_human_reference_acceptance` as its original preparation status. The
[integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_05/integration_audit.json)
passes **1,558 file bindings, 240 native source/annotation joins, 480 encoded
frames and 356 center markers**. Both videos contain all 240 selected frames
at 60/10 fps (4s/24s); emitted color metadata and every encoded-frame comparison
pass. All 20 inspection sheets, including 178 encoded center crops and 62
unmarked null-context crops, were inspected through the actual final. The full
native source frame 509 and both full encoded finals were also inspected.
The actual pending-review consumer passes without accepting any labels.

All **480 accepted NBA labels** and **868 curated references** remain unchanged.
The audit preserves the 1,009-file source-preparation snapshot and all four prior
acceptance snapshots: **286 NBA01, 543 NBA02, 809 NBA03 and 1,050 NBA04 files**.
These preservation sets overlap. Source preparation, delivery and finalization
succeeded on their first attempts. Transport checks and AI inspection establish
review integrity; they do not measure model accuracy or replace Ryan's acceptance.

The later receipt supplies acceptance without rewriting the original review.
Continue with [NBA06](ball_tracking_completion_nba_reference_batch_06.md), whose
new labels require separate acceptance. No fitting or protected evaluation has
run. Accepted-label training eligibility does not make the full source/label/role
package or executable recipe ready. Freeze the full accepted
source/label/role package and executable recipe before the approved fit;
protected evaluation requires a frozen method and separate explicit authorization.
