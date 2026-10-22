# Completion campaign: NBA reference batch 02

This increment delivers **120 new NBA center proposals**, with
**no null centers**, for fixed episode
`chi-vs-ind-0022400868_e02`, native frames **0–119** of CHI–IND source clip
`17.mp4`. Its parent game retains the training role. These new labels require
Ryan's separate acceptance; neither training nor checkpoint-selection
eligibility is enabled for the pending proposals. The
[complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_02/review_v1/index.html)
is ready. Ryan's acceptance or corrections for these exact 120 labels is the
immediate next step.

Ryan has accepted all 120 labels from [NBA batch 01](ball_tracking_completion_nba_reference_batch_01.md),
including 96 centers and 24 nulls. Its separate receipt and accepted publication
preserve all original artifacts. Thus **120 of 3,839 selected NBA judgments are
accepted**, with **3,719 not yet accepted**. This second completed 120-frame
proposal leaves **3,599 without proposals**. The NBA package remains
separate from curated coverage: **868/1,273 accepted**, 760 eligible centers
and 405 uncovered permitted positions.

## Fixed source and timing

The [batch configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_02_v0_1.json)
uses the episode selected before new-model predictions in the
[source-role manifest](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json).
This is a different native source file from batch 01, within the same training
game. Its frame indices and PTS start at zero again; source-video hashes keep
the two clips' references distinct.

The source is 1280×720 at 60 fps, with **1/60000-second timebase**, frame `f`
at PTS `f × 1000` and duration 1000 ticks. The selected half-open interval is
**[0,120000) ticks**, or **[0,2) seconds**. Batch and episode final is **119**;
the underlying 359-frame source clip continues through **358**. Review delivery
retains every selected frame in the
[two-second native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_02/review_v1/review_native.mp4)
at 60 fps and
[twelve-second slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_02/review_v1/review_slow.mp4)
at 10 fps. Both complete actual final frames were inspected.

The source shows an overhead free-throw lift and release, flight through the
rim/net region, and subsequent hand overlap. The final proposal contains
**68 fully visible and 52 partially visible** judgments. Center uncertainty is
**4–7 source pixels**: 52 judgments at 4px, 28 at 5px, 12 at 6px and 28 at 7px.
These are AI placement estimates, not calibrated confidence intervals.

All centers come from separate current-frame source inspection. No model,
optical flow or temporal interpolation supplies positions. Partial visibility
preserves hand-overlap uncertainty around the whole-ball center; the legacy
`human_amodal_estimate` geometry field does not claim human authorship.
The initial 60–119 draft remains preserved. Final inspection corrected frames
108–109 and 114–117 from full to partial visibility with unchanged centers and
uncertainty increased from 6px to 7px. The separate revised overlay is retained.

The first 0–59 writer invocation failed because its direct script path omitted
the repository package from Python's import path. A following overlay command
also failed because no proposal had been written. Both failures occurred before
proposal or overlay creation and remain recorded. Running the unchanged writer
from the repository root resolved the import path; the completed part required
no annotation revisions.

## Completed preparation and validation

Source preparation passed: all **120 PyAV source PNGs match explicit BT.709
FFmpeg RGB conversion exactly**, with native PTS checks. The original PNGs are
unchanged. The preparation audit preserves all **253 files present before its
run**, including the prior episode's evidence. This is pixel transport evidence;
both decoder paths use FFmpeg components.

The primary decoder submitted 121 packets and returned the 120 selected
frames. Alternate conversion produced 120 compared RGB frames and reported
frame 120 as filter context at PTS 120000. That context belongs to the same
training-role source and is not included in the labels or review.

The source identity check compares game, original source hash, native frame,
PTS and timebase and found no overlap with the previously prepared episode.
The production review module remains unchanged from batch 01. Its original
**13-test result** remains prior implementation coverage, with no renderer-suite
rerun this increment. The new batch's actual records and encoded media were
validated separately.
The acceptance reader's original eight-test evidence is preserved separately.
Its current **12 focused tests pass**, adding four checks for safely reusing
unchanged producer-test evidence beside each new batch's exact current audit.
The default proposal-specific scope stays strict; the explicit reuse scope
requires the unchanged producer/test hashes and this batch's current audit.
These tests do not replace the completed NBA02 media checks.

The [final preparation result](../configs/ball_tracking/reviews/nba_completion_reference_batch_02_result_v0_1.json)
is `ready_for_human_reference_acceptance`. Its
[integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_02/integration_audit.json)
passes **527 file bindings, 120 native source/annotation joins, 240 encoded
frames and 240 markers**. All source frames, final encoded center crops and
complete native/slow final 119 were visually inspected. There are no null-center
exceptions in this batch. The actual emitted result also passes the production
pending-review reader.

The audit confirms that all **120 accepted NBA01 labels** and **868 accepted
curated labels** remain unchanged. It preserves the source-preparation snapshot
of 253 prior files and the NBA01 acceptance snapshot of 286 original files.
Successful source/media transport checks and AI visual inspection establish
review integrity; Ryan's label acceptance remains pending.

No fitting, model scoring, checkpoint selection or protected evaluation is
authorized by this batch. Continue the fixed reference package and human label
review; freeze the complete accepted source/label/role package and executable
recipe before the approved fit. Protected evaluation still requires a frozen
method and separate explicit authorization.
