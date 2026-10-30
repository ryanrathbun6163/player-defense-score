# Completion campaign: NBA reference batch 03

Ryan accepted **all 120 judgments: 100 centers and 20 nulls**, for fixed CHI–IND episode
`chi-vs-ind-0022400868_e03`, native source frames **120–239** of `38.mp4`.
The [complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_03/review_v1/index.html)
is ready, including the
[two-second native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_03/review_v1/review_native.mp4)
and [twelve-second slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_03/review_v1/review_slow.mp4).
All source/proposed frames, encoded center crops, null-context crops and complete
native/slow final 239 were inspected. Ryan answered **“Accept all 120 proposals”**
to the question identifying this exact batch, its exceptions and 4–8px uncertainty.
The separate [acceptance receipt](../configs/ball_tracking/reviews/nba_completion_reference_batch_03_acceptance_v0_1.json)
and accepted publication preserve every reviewed judgment and AI authorship.
Training eligibility applies only to these accepted reference labels;
checkpoint selection, complete-package readiness, recipe freeze and fitting
authorization from this label-acceptance artifact remain false. The approved
campaign already authorizes fitting once its package and recipe conditions are
met. The original proposals and review artifacts retain
their preparation-era status unchanged.

Following [NBA02](ball_tracking_completion_nba_reference_batch_02.md), the
combined NBA inventory now contains **360 accepted labels, 316 centers and
44 nulls**. Of 3,839 selected judgments, **3,479 are not yet accepted**.
[NBA04](ball_tracking_completion_nba_reference_batch_04.md) now has a complete
review awaiting separate acceptance: 118 centers and two indeterminate nulls.
Curated coverage
remains **868/1,273 accepted**, with **760 eligible centers** and **405 uncovered**.

The acceptance publication preserves **809 original files**. Actual publication,
combined inventory and duplicate-guard checks pass, with no tests rerun and no
source decoding, fitting or model scoring for acceptance. The exact user-event
timestamp remains null; publication time is separate. No playback telemetry or
independent human annotation is claimed.

## Fixed source and native timing

The [batch configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_03_v0_1.json)
uses the episode fixed in the
[source-role manifest](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json)
before new-model predictions. CHI–IND retains its training role. Source identity
includes the original video hash, so frame numbers from this clip cannot alias
the other accepted CHI–IND sources.

The source is **1280×720 at 60 fps**, with a **1/60000-second timebase** and
1000-tick frame durations. Selected PTS are **120000–239000**; the selected
half-open interval is **[120000,240000) ticks**, or **[2,4) seconds**. The batch
final is **239**. The underlying source has 509 frames and ends at **508**.
Native PTS, clip-relative time and review-relative time remain separate.

## Judgments and uncertainty

The source shows a held ball raised beside the body, obscured by a foreground
defender, then lifted toward the rim. The final proposal contains **100 partially
visible, four fully visible and 16 not-visible judgments**. Its 100 defensible
centers retain **4–8-source-pixel uncertainty**, a placement estimate rather than
a calibrated confidence interval.

Frames **138–153** have no visible ball outline. Frames **154–155 and 208–209**
retain narrow fragments without a defensible whole-ball center. All 20 remain
null; no neighboring positions or model coordinates fill them. Every proposed
center comes from separately inspected current-frame pixels.

The initial draft remains preserved. Source/overlay inspection corrected the
centers at frames **130–131 from [682,254] to [682,250]**, retaining 5px
uncertainty; the superseded crop sheet is kept. Two tooling failures also remain
recorded: a receipt writer used an unsupported parser keyword before publication,
and the second-half writer rejected unsorted difficulty tags before producing
proposal or overlay files. Separate corrected helpers retain the original
failures and visual judgments.

## Completed source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_03/preparation.json)
and [source-pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_03/source_pixel_audit.json)
pass all **120 selected PNG comparisons and native PTS joins**, with exact RGB
equality between the saved PyAV source pixels and explicit BT.709 FFmpeg
conversion. The original PNGs remain unchanged, and all **500 files captured
before preparation** are preserved. This is transport evidence; both decoder
paths use FFmpeg components.

Reaching a nonzero starting frame required disclosed source context. The primary
decoder submitted **241 packets** and returned **frames 0–239**, saving only
120–239. The alternate conversion emitted **240 RGB frames** and reported
**241 filter frames, 0–240**. Frames 0–119 and filter frame 240 are context from
the same training-role source; they are not additional labels or review frames.

The production renderer and acceptance reader are unchanged. Their prior
**13-test renderer and 12-test acceptance-reader receipts** remain distinct
from this batch's current source and media checks. No suite was rerun for this
increment; explicit prior-implementation scope requires the exact unchanged
code/test hashes and the new batch's complete current audit.

## Complete review validation

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_03_result_v0_1.json)
retains `ready_for_human_reference_acceptance` as the original preparation status. The
[integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_03/integration_audit.json)
passes **808 file bindings, 120 native source/annotation joins, 240 encoded
frames and 200 center markers**. Both overlays retain all 120 selected frames
at 60/10 fps; emitted color metadata and every encoded-frame comparison pass.
All 100 encoded center crops, all 20 unmarked null-context crops and the complete
native/slow final 239 were inspected. The actual pending-review consumer also
passes without accepting any labels.

All **240 accepted NBA labels** and **868 accepted curated labels** remain
unchanged. The audit preserves the 500-file source-preparation snapshot and
both prior acceptance snapshots: 286 NBA01 files and 543 NBA02 files. The
accepted inventories, current proposals and historical test receipts remain
separate; source/media transport checks are not model accuracy or human acceptance.

The later receipt supplies the accepted status without rewriting the original
review. The [NBA04 review](ball_tracking_completion_nba_reference_batch_04.md) is now ready;
its new labels require separate acceptance. No fitting, model scoring or
protected evaluation has run. The complete accepted source/label/role package and executable recipe
must be frozen before the approved fit; protected evaluation requires a frozen
method and separate explicit authorization.
