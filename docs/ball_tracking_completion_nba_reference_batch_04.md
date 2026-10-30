# Completion campaign: NBA reference batch 04

Ryan accepted **all 120 frame judgments** for fixed CHI–IND
episode `chi-vs-ind-0022400868_e04`, native frames **300–419** of `81.mp4`.
The [complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_04/review_v1/index.html)
is ready: **118 centers and two indeterminate nulls**, with **5–7px uncertainty**.
The [two-second native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_04/review_v1/review_native.mp4)
and [twelve-second slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_04/review_v1/review_slow.mp4)
retain every selected frame. All source/proposed frames, encoded center crops,
null-context crops and full native/slow final 419 were inspected. Ryan answered
**“Accept all 120 proposals”** to the question identifying this exact batch,
its two unknown centers and 5–7px uncertainty. The separate
[acceptance receipt](../configs/ball_tracking/reviews/nba_completion_reference_batch_04_acceptance_v0_1.json)
preserves every judgment and AI authorship. Training eligibility applies only
to these accepted reference labels; checkpoint-selection eligibility remains
false. The original proposal and media retain their preparation-era status.

Following [NBA03](ball_tracking_completion_nba_reference_batch_03.md), the
combined inventory now contains **480 accepted NBA labels: 434 centers and
46 nulls**. Of 3,839 selected judgments, **3,359 are not yet accepted**.
[NBA05](ball_tracking_completion_nba_reference_batch_05.md) has a complete review
for fixed CHI–IND e05 frames 270–509: 178 centers and 62 nulls. Its new labels need
separate acceptance. Curated coverage
remains **868/1,273 accepted**, with **760 eligible centers** and **405 uncovered**.

The acceptance publication preserves **1,050 original files**. Actual publication,
inventory and duplicate-guard checks pass; no tests, source decoding, inference
or fitting were repeated for publication. The exact user-event timestamp remains
null, with publication time recorded separately. No playback telemetry or
independent human annotation is claimed.

## Fixed source and native timing

The [batch configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_04_v0_1.json)
uses the episode fixed in the
[source-role manifest](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json)
before new-model predictions. Its CHI–IND parent game retains the training role.
Source identity includes the original video hash, preserving the distinction
between this clip and the three accepted CHI–IND sources.

The source is **1280×720 at 60 fps**, with a **1/60000-second timebase** and
1000-tick durations. Selected PTS are **300000–419000**; the half-open interval
is **[300000,420000) ticks**, or **[5,7) seconds**. Batch final is **419**;
the 553-frame source clip ends at **552**. Original PTS, source-relative time
and review-relative time remain separate.

## Sealed proposals

The [assembled proposal](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_04/proposal.json)
contains **78 partially visible, 40 fully visible and two indeterminate
judgments**. Frames **300–301** do not resolve the ball separately from the
arm/hand surface and remain null. All remaining 118 frames have proposed
whole-ball centers with **5–7-source-pixel uncertainty**. These are placement
estimates, not calibrated confidence intervals.

The sequence shows a low dribble, gather, shooting lift and release, then the
airborne ball against the crowd. Every center comes from current-frame source
inspection; no model or temporal interpolation supplies positions. All 120
source and proposed-overlay frames, including full endpoints 300, 359, 360 and
419, were inspected. Both initial parts remain final: no annotation revisions
or helper failures occurred in either part. Complete encoded-frame inspection
and native/slow final review are now recorded separately.

## Completed source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_04/preparation.json)
and [source-pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_04/source_pixel_audit.json)
pass all **120 selected native PNG comparisons and PTS checks**. Saved PyAV
pixels match explicit BT.709 FFmpeg RGB conversion exactly, and all original
PNGs remain unchanged. All **765 files captured before preparation** are preserved.
Both decoder paths use FFmpeg components; this is source transport evidence.

The primary decoder submitted **421 packets** and returned **frames 0–419**,
saving only selected frames 300–419. The alternate conversion emitted **420 RGB
frames** and reported **421 filter frames, 0–420**. Lead-in frames 0–299 and
filter frame 420 are disclosed context from the same training-role source,
not additional labels or review frames.

The production renderer and acceptance reader remain unchanged, retaining
separate prior **13-test renderer and 12-test reader evidence**. No suite was
rerun; this batch's actual producer records and emitted media were checked
separately under explicit prior-implementation test scope.

## Complete review validation

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_04_result_v0_1.json)
retains `ready_for_human_reference_acceptance` as its original preparation status. The
[integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_04/integration_audit.json)
passes **1,054 file bindings, 120 native source/annotation joins, 240 encoded
frames and 236 center markers**. Both videos contain all 120 selected frames
at 60/10 fps (2s/12s); emitted color metadata and every encoded-frame comparison
pass. All ten inspection sheets, including 118 encoded center crops and two
unmarked null-context crops, were inspected through the actual final. The full
native source frame 419 and both full encoded finals were also inspected.
The actual pending-review consumer passes without accepting any labels.

All **360 accepted NBA labels** and **868 curated references** remain unchanged.
The audit preserves the 765-file source-preparation snapshot and all three prior
acceptance snapshots: **286 NBA01, 543 NBA02 and 809 NBA03 files**. These
preservation sets overlap.
Transport checks and AI visual inspection establish review integrity; they do
not measure model accuracy or replace Ryan's reference acceptance.

The later receipt supplies acceptance without rewriting the original review.
Review the [NBA05 package](ball_tracking_completion_nba_reference_batch_05.md),
whose 240 new labels require separate acceptance. No fitting or protected
evaluation has run. Accepted-label training eligibility
does not make the full source/label/role package or executable recipe ready.
Freeze that complete package and recipe before the approved fit; protected
evaluation requires a frozen method and separate explicit authorization.
