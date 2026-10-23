# Validation History

## NBA17 accepted; NBA18 complete review ready for acceptance

Ryan's structured reply **“Accept all 240 proposals”** accepts every NBA17
judgment through HOU–OKC e05 frame 239: **212 centers, 28 nulls and 5–9px center
uncertainty**, with 200 partial/20 full/16 not-visible/four indeterminate
judgments. The
[separate receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_17_acceptance_v0_1.json)
and [publication audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_17/acceptance_audit/publication_audit.json)
preserve **5,406 originals**, all 2,400 earlier NBA rows and 868 curated references.
Publication passes actual readers and the duplicate guard in **27.810 seconds**.
Coverage is **2,640 accepted: 2,426 centers and 214 nulls**, comprising 1,920
training and 720 validation judgments. **1,199 remain unaccepted: 959 training
and 240 validation**. Original proposals, failed writer/tag correction, source
crops and source-only second-AI review remain unchanged. Validation labels are
excluded from gradient fitting; no scoring, fit, source pixel decoding or tests
ran in publication. Exact user-event UTC is null; publication time is recorded
separately without claiming playback telemetry.

[NBA18 source preparation](../ball_tracking_completion_nba_reference_batch_18.md)
passes **240 exact native PNG/PTS checks** for checkpoint-validation HOU–OKC e06,
frames 210–449, native [3.5,7.5)s, preserving **5,352 prior files**. Successful
preparation takes **46.364 seconds**. Primary decoding returned frames 0–449
after 451 submitted packets; alternate conversion emitted 450 RGB frames and
reported filter frames 0–450. Prefix 0–209 and filter frame 450 are disclosed
same-role context; only selected 210–449 were saved. Source final 510 differs
from batch final 449.

The initial command failed before source decoding after **0.5438975 seconds**:
inspection-helper setup had created the destination directory, while the source
preparer requires an absent destination. The
[failure and original setup](../../data/outputs/ball_tracking/completion_campaign_v0_1/setup_nba18_preserved_20261023_01/preparation_initial_failure.json)
remain preserved separately. The unchanged preparer then succeeded; helpers
were copied back unchanged. A premature read-only documentation lookup also
found the configuration not yet created, without changing data or review output.

The three sealed parts provide **212 centers and 28 nulls** at **210–221,
238–245, 264–267 and 274–277**, with **5–9px center uncertainty**. Visibility
is **128 full, 94 partial and 18 not visible**. Every current source/proposed
frame and full part endpoint was inspected. Root's broad detail crops clipped
the upper ball in some later frames; wider precision and additional crops at
252–253/282–283 were viewed before annotation, with all originals retained.
A second AI source-only review corroborates conservative null judgments and
broad partial centers without claiming independent human ground truth.

The initial root writer failed after **0.3872014 seconds** at frame 224 because
fully visible geometry must use `observed_complete_ball_center`. It failed
before publishing a proposal or running overlays. The original helper and
[failure record](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/inspection/part_210_289_write_failure.json)
remain retained. V2 corrects only geometry-source metadata for full rows;
coordinates, visibility and uncertainty did not change. All initial published
annotations remain unchanged. The middle and final parts preserve the same
source-setup incident separately from their annotation work.

The [NBA18 final result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_18_result_v0_1.json)
is ready for human reference acceptance. Its
[integration audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/integration_audit.json)
passes **5,959 bindings, 240 native source/annotation joins, 480 encoded frames
and 424 center markers**, plus 240 exact source PNG checks. All-frame pixel
comparisons and emitted color checks pass. Complete overlays run 4s at 60 fps
and 24s at 10 fps. Root actually inspected all 20 encoded/source sheets,
212 localized centers, 28 unmarked null source contexts, full native source 449
and both actual encoded finals before the
[visual receipt](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_18/inspection/root_visual_review.json).
The three part receipts collectively cover every source/proposed frame and
full part endpoint. Final 449 retains **[351,307] ±6 pixels**, fully visible.

Delivery (**29.813s**) and complete finalization (**13.000s**, including the
pending-reader check) pass on their first attempts. The integration audit was
recorded at **12.562s**. The earlier source-preparation and writer failures remain
failures. No annotation geometry or media changed after publication. The
pending-review reader passes all 240 joins and creates zero accepted labels.
All **2,640 accepted NBA rows**, **868 curated references** and **5,352
preparation-era files** remain unchanged. Earlier acceptance preservation
snapshots stay bound and overlap. New labels stay pending with both eligibility
flags false, leaving **959 positions without proposals** and **1,199 without
accepted references**. Historical 13-test renderer, current 12-test
acceptance-reader and separate original eight-test evidence remain retained.
No tests, models, fitting, checkpoint scoring or protected evaluation ran for
this increment.

## NBA16 accepted; NBA17 complete review ready for acceptance

Ryan's structured reply **“Accept all 120 proposals”** accepts every NBA16
judgment through HOU–OKC e04 frame 269: 70 fully visible/50 partial centers,
zero nulls and 5–8px uncertainty. The
[separate receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_16_acceptance_v0_1.json)
and [publication audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_16/acceptance_audit/publication_audit.json)
preserve **4,936 originals**, all 2,280 earlier NBA rows and 868 curated references.
Publication passes actual readers and the duplicate guard in **25.370 seconds**.
Coverage is **2,400 accepted: 2,214 centers and 186 nulls**, comprising 1,920
training and 480 validation judgments. **1,439 remain unaccepted: 959 training
and 480 validation**. Original proposals, six center refinements, crop
adjustments, read-only lookup incident and restart history remain unchanged.
Validation labels are excluded from gradient fitting; no scoring, fit, source
pixel decoding or tests ran in publication. Exact user-event UTC is null;
publication time is recorded separately without claiming playback telemetry.

[NBA17 source preparation](../ball_tracking_completion_nba_reference_batch_17.md)
passes **240 exact native PNG/PTS checks** for checkpoint-validation HOU–OKC e05,
frames 0–239, native [0,4)s, preserving **4,883 prior files**. The first attempt
takes **42.630 seconds**. Primary decoding returned frames 0–239 after 241
submitted packets; alternate conversion emitted 240 RGB frames and reported
filter frames 0–240. Filter frame 240 is disclosed same-role context; only
selected 0–239 were saved. Source final 558 differs from batch final 239.

The three sealed parts provide **212 centers and 28 nulls** at **0–7, 12–13,
22–29, 162–165 and 214–219**, with **5–9px center uncertainty**. Visibility is
**200 partial, 20 full, 16 not visible and four indeterminate**. Every current
source/proposed frame and full part endpoint was inspected. Early partial
centers at 14–17 retain especially broad 9px uncertainty. A second AI source-only
review corroborates the early judgments without claiming independent human
ground truth. Original broad crops clipped the ball at 76–79; wider precision
crops were inspected before annotation, and the initial assets remain retained.

The first writer failed after **0.5026152 seconds** on an unsupported
`body_overlap` difficulty tag at its first row, before publishing a proposal or
running overlays. The original helper and failure remain retained. Its v2
replacement changes only the tag to `player_overlap`; no coordinate, visibility
or uncertainty changed. All initial published annotations remain unchanged.
Neither remaining part had annotation corrections, helper failures or incidents.

The [NBA17 final result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_17_result_v0_1.json)
is ready for human reference acceptance. Its
[integration audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_17/integration_audit.json)
passes **5,475 bindings, 240 native source/annotation joins, 480 encoded frames
and 424 center markers**, plus 240 exact source PNG checks. All-frame pixel
comparisons and emitted color checks pass. Complete overlays run 4s at 60 fps
and 24s at 10 fps. Root actually inspected all 20 encoded sheets, all 212 center
crops, 28 unmarked null source contexts and both full actual encoded finals before
the [visual receipt](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_17/inspection/root_visual_review.json).
Root personally inspected full native source 0/79/239; the three part receipts
cover every source/proposed frame and full part endpoint collectively. Final 239
retains **[439,152] ±8 pixels**, partial with hand/net overlap.

Delivery (**27.750s**) and complete finalization (**10.312s**) pass on their first
attempts; the integration audit was recorded at **9.875s** before the pending-reader check.
No annotation geometry or media changed after publication. The pending-review
reader passes all 240 joins and creates zero accepted labels. All **2,400 accepted
NBA rows**, **868 curated references** and **4,883 preparation-era files** remain
unchanged. Earlier acceptance preservation snapshots stay bound and overlap.
New labels stay pending with both eligibility flags false, leaving **1,199
positions without proposals** and **1,439 without accepted references**.
Historical 13-test renderer, current 12-test acceptance-reader and separate
original eight-test evidence remain retained. No tests, models, fitting,
checkpoint scoring or protected evaluation ran for this increment.

## NBA15 accepted; NBA16 complete review ready for acceptance

Ryan's **“I accept chat. Move forward”** accepts all 120 NBA15 judgments:
98 centers and 22 nulls, including visibility and 5–9px uncertainty. The
[separate receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_15_acceptance_v0_1.json)
and [publication audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_15/acceptance_audit/publication_audit.json)
preserve **4,673 originals**, all 2,160 earlier NBA rows and 868 curated references.
Publication passes actual readers and the duplicate guard in **25.391 seconds**.
Coverage is **2,280 accepted: 2,094 centers and 186 nulls**, comprising 1,920
training and 360 validation judgments. **1,559 remain unaccepted: 959 training
and 600 validation**. Original review evidence and lookup incidents are retained.
Validation labels are excluded from gradient fitting; no scoring, fit or tests
ran in publication.

[NBA16 source preparation](../ball_tracking_completion_nba_reference_batch_16.md)
passes **120 exact native PNG/PTS checks** for checkpoint-validation HOU–OKC e04,
frames 150–269, native [2.5,4.5)s, preserving **4,621 prior files**. The first
attempt takes **25.052 seconds**. Primary decoding returned frames 0–269 after
271 packets; alternate conversion emitted 270 RGB frames and reported filter
frames 0–270. Prefix 0–149 and filter frame 270 are disclosed same-role context;
only selected 150–269 were saved. Source final 670 differs from batch final 269.
All three parts are sealed: **120 centers, zero nulls, 70 fully visible and
50 partial judgments**, with **5–8px uncertainty**. Every source/proposed frame
and full part endpoint was inspected. Root retained initial clipped source crops
at 156–161/166–167, inspected supplemental 156–167 crops before annotation,
and expanded overlay regions. Six centers at 172–177 were refined after actual
source/overlay review; visibility and uncertainty are unchanged, and the original
part and all initial overlays are retained. A read-only `rg` access denial for
unrelated old temporary directories took 0.2188052s and changed no data/output.
After Ryan reported a restart, root verified existing critical hashes without
rerunning acceptance publication or source preparation.

The [NBA16 final result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_16_result_v0_1.json)
is ready for human reference acceptance. Its
[integration audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_16/integration_audit.json)
passes **5,000 bindings, 120 native source/annotation joins, 240 encoded frames
and 240 center markers**, plus 120 exact source PNG checks. All-frame pixel
comparisons and emitted color checks pass. Complete overlays run 2s at 60 fps
and 12s at 10 fps. Root actually inspected all ten encoded sheets, all 120 center
crops and both full actual encoded finals before the
[visual receipt](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_16/inspection/root_visual_review.json).
Full native source 150/170/189/269 received root inspection; the three sealed
part receipts cover every source/proposed frame collectively. Final 269 retains
**[694,60] ±6 pixels**, fully visible against the crowd. An empty null-center
exception list does not erase hand-overlap, motion-blur or background uncertainty.

Delivery (**15.062s**) and finalization (**18.797s**) pass on their first attempts.
The retained first-part refinements above are the only annotation corrections;
there were no media corrections. The pending-review reader passes all 120 joins
and creates zero accepted labels. All **2,280 accepted NBA rows**, **868 curated
references** and **4,621 preparation-era files** remain unchanged. Earlier
acceptance preservation snapshots remain bound and overlap. New labels stay
pending with both eligibility flags false, leaving **1,439 positions without
proposals** and **1,559 without accepted references**. Historical 13-test renderer,
current 12-test acceptance-reader and separate original eight-test evidence are
retained; no tests, models, fitting, checkpoint scoring or protected evaluation
ran for this increment.

## NBA14 accepted; NBA15 complete review ready for acceptance

Ryan's **“Reviewed. Keep moving forward chat”** accepts all 120 NBA14 judgments
through HOU–OKC e02 frame 119: 71 partial/49 full centers, zero nulls and 5–7px
uncertainty. The [separate receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_14_acceptance_v0_1.json)
and [publication audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_14/acceptance_audit/publication_audit.json)
preserve **4,401 originals**, all 2,040 earlier NBA rows and 868 curated references.
Publication passes actual readers and duplicate guard in **22.945 seconds**.
Coverage is **2,160 accepted: 1,996 centers and 164 nulls**, comprising 1,920
training and 240 validation judgments. **1,679 remain unaccepted: 959 training
and 720 validation**. Original review artifacts, first-part collective reviewer
attribution and the earlier helper failure remain unchanged. Validation labels
are excluded from gradient fitting; no scoring, fit or tests ran in publication.

[NBA15 source preparation](../ball_tracking_completion_nba_reference_batch_15.md)
passes **120 exact native PNG/PTS checks** for checkpoint-validation HOU–OKC e03
frames 120–239, native [2,4)s, preserving **4,350 prior files**. First attempt
takes **23.969 seconds**. Primary decoding returned frames 0–239 after 241
packets; alternate conversion emitted 240 RGB frames and reported filter
frames 0–240. Prefix 0–119 and filter frame 240 are disclosed same-role context;
only selected 120–239 were saved. Source final 472 differs from batch final 239.

All three parts are sealed after actual source/proposed-frame and full-endpoint
inspection: **98 centers and 22 nulls** at **126–129, 142–145, 184–189 and
230–237**, with **5–9px center uncertainty**. Visibility is **32 full, 70 partial,
ten indeterminate and eight not visible**. All initial annotations remain
unchanged. Complete encoded review and finalization have now passed.
The middle sealed part keeps six occluded
nulls at 184–189. The final sealed part keeps four indeterminate/nulls at 230–233
and four partial/nulls at 234–237; final 239 supports a partial center with broad
8px uncertainty. Two middle-part read-only schema lookup failures created no
outputs and changed no annotation geometry. The first receipt separately retains
a read-only `rg` access denial for unrelated old temporary directories; existing
named helpers were used without altering outputs, and elapsed time is unknown.
These lookup incidents are distinct from annotation-helper failures.
New labels remain pending with both
eligibility flags false; their 120 proposals leave **1,559 positions without
proposals** and **1,679 without accepted references**. Historical 13-test
renderer/current 12-test acceptance
coverage and separate original eight-test history are retained; no tests, models,
fitting, checkpoint scoring or protected evaluation ran for this increment.

The [NBA15 final result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_15_result_v0_1.json)
is ready for human reference acceptance. Its
[integration audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_15/integration_audit.json)
passes **4,732 bindings, 120 native source/annotation joins, 240 encoded frames
and 196 center markers**, plus all 120 exact source PNG checks. All-frame pixel
comparisons and emitted color checks pass. Complete overlays run 2s at 60 fps
and 12s at 10 fps. Root actually inspected all ten encoded/source sheets,
98 center crops, 22 unmarked null contexts and both actual encoded finals before
writing the [visual receipt](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_15/inspection/root_visual_review.json).
Root also inspected full native source 120/159/239 and late source details
228–239; the three part receipts cover every source/proposed frame collectively.
Final 239 retains **[420,355] ±8 native pixels**, a partial upper ball arc above
the head. No coordinate is carried through the late null interval.

Source preparation, delivery (**14.031s**) and finalization (**8.859s**) each
passed on the first attempt. There were no annotation or media corrections;
the read-only lookup incidents above remain preserved. The actual pending-review
reader passes 120 joins and creates zero accepted labels. All **2,160 accepted
NBA rows**, **868 curated references** and **4,350 preparation-era files** remain
unchanged. Earlier acceptance preservation snapshots stay bound and overlap.

## NBA13 accepted; NBA14 complete review ready for acceptance

Ryan's **“Looks good chat. Move forward my brother”** accepts all 120 NBA13
judgments through HOU–OKC e01 frame 239, including 80 partial/40 full centers,
zero nulls and 5–6px uncertainty. The
[separate receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_13_acceptance_v0_1.json)
and [publication audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_13/acceptance_audit/publication_audit.json)
preserve **4,156 originals**, all 1,920 earlier NBA rows and 868 curated
references. Actual publication/inventory readers and duplicate guard pass.
Coverage is **2,040 accepted: 1,876 centers and 164 nulls**, comprising 1,920
training and 120 checkpoint-validation judgments. **1,799 remain unaccepted:
959 training and 840 validation**. Original review evidence is unchanged;
accepted validation labels remain excluded from gradient fitting. No scoring,
fit or tests ran during publication.

[NBA14 preparation](../ball_tracking_completion_nba_reference_batch_14.md)
passes all **120 exact PNG/PTS checks** for checkpoint-validation HOU–OKC e02
frames 0–119 and preserves **4,106 earlier files**. First attempt elapsed
22.939 seconds. Primary decoding returned 120 frames after 121 submitted
packets; alternate conversion emitted 120 RGB frames and reported filter
frames 0–120. Filter frame 120 is same-role context; only selected 0–119 were
saved. Full-source final 596 is distinct from batch final 119.

The three proposals contain **120 centers, zero nulls, 71 partial and 49 fully
visible judgments**, with **5–7px uncertainty**. Fully visible intervals are
3–7, 42–73 and 108–119. All current source/proposed frames and full part endpoints
are inspected. The first worker completed source inspection and initial annotation;
after two worker interruptions, root actually inspected its seven proposed detail
sheets and full overlays 0/39 before sealing the receipt. It makes no unconfirmed
worker-overlay claim. The middle helper failed tag-order
validation after 0.4475467 seconds before creating a proposal or overlay;
its original code is retained. Sorting tags corrected the helper without
changing manual geometry, visibility or uncertainty. New labels remain pending
with both eligibility flags false. Their 120 proposals leave 1,679 selected
positions without proposals and 1,799 without accepted references. Historical
13-test renderer and current 12-test acceptance-reader evidence is unchanged;
the original eight-test history stays separate. No tests, model calls, fit,
checkpoint scoring or protected evaluation ran for this increment.

The [NBA14 final result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_14_result_v0_1.json)
is ready for human reference acceptance. Its
[integration audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_14/integration_audit.json)
passes **4,456 bindings, 120 native source/annotation joins, 240 encoded frames
and 240 center markers**, including all-frame pixel comparisons and emitted
color checks. Complete overlays run 2s at 60 fps and 12s at 10 fps. Root
actually inspected all ten encoded sheets, all 120 center crops, full source
0/40/80/119 and both actual encoded finals before recording the
[visual receipt](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_14/inspection/root_visual_review.json).
Final 119 proposes **[846,568] ±6 native pixels**. Initial labels remain unchanged.
Source preparation, delivery (12.922s) and finalization (8.468s) each passed on
their first attempt; this does not erase the annotation-helper failure above.
The actual pending-review reader passes 120 joins and creates zero accepted
labels. All 2,040 accepted NBA rows, 868 curated references and 4,106 files
captured before preparation remain unchanged. Earlier acceptance preservation
snapshots remain bound and overlap.

## NBA12 accepted; NBA13 complete review ready for acceptance

Ryan's **“Looks good to me. Move forward chat”** accepts all 240 NBA12 judgments,
including 220 centers, 20 nulls and 5–8px uncertainty. The separate acceptance
publication passes actual readers and the duplicate guard, preserving **3,911
original files**, all 1,680 earlier NBA labels and 868 curated references.
Combined NBA coverage is **1,920 accepted: 1,756 centers and 164 nulls**,
with **1,919 unaccepted**. Original pending review evidence and annotation
correction/helper failure history remain unchanged. No tests or fit ran.

NBA13 source preparation passes all **120 exact native PNG/PTS checks** for
fixed checkpoint-validation HOU–OKC e01 frames 120–239, preserving **3,862
prior files**. First attempt takes 22.518 seconds. Primary decoding returned
240 frames 0–239 after 241 packets; alternate conversion emitted 240 RGB frames
and reported 241 filter frames 0–240. Prefix 0–119 and filter 240 are disclosed
same-role context; only 120–239 were saved. Batch final 239 differs from full-source
final 502. All three parts are sealed: 120 centers, zero nulls, 80 partial and
40 fully visible judgments, with 5–6px uncertainty. Every source/proposal frame
and full part endpoint was actually inspected; all initial drafts are unchanged,
with no corrections or helper failures. Fully visible frames are 124–135 and
212–239. No inference, fitting, checkpoint scoring or protected evaluation has run.

The [NBA13 final result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_13_result_v0_1.json)
is ready for human reference acceptance. Its
[integration audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_13/integration_audit.json)
passes **4,205 bindings, 120 native source/annotation joins, 240 encoded frames
and 240 center markers**. The complete 2s native/12s slow overlays retain every
selected frame. Root actually inspected all ten encoded sheets, all 120 center
crops, full source 120/160/200/239 and both actual encoded finals before writing
the [visual receipt](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_13/inspection/root_visual_review.json).
Final 239 proposes **[629,152] ±6 native pixels**. All-frame pixel comparisons
and emitted color checks pass. Source preparation, delivery and finalization
each passed on the first attempt, without annotation or media corrections.

The actual pending-review reader passes 120 joins and creates zero accepted
labels. All 1,920 accepted NBA rows, 868 curated references and 3,862 files
captured before source preparation remain unchanged. Earlier acceptance
preservation snapshots remain bound and overlap. These 120 pending
checkpoint-validation proposals leave **1,799 positions without proposals**
and **1,919 without accepted references**; both eligibility flags remain false.
Historical 13-test renderer and current 12-test acceptance-reader evidence is
unchanged, with original eight-test history separately bound. No suite was rerun.

## NBA11 accepted; NBA12 complete review ready for acceptance

Ryan's **“I approve caht. move forward”** accepts all 240 NBA11 judgments through
DEN–BOS e05 frame 449, including 172 partial/68 full centers, zero nulls and
5–8px uncertainty. The [separate receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_11_acceptance_v0_1.json)
and [publication audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/acceptance_audit/publication_audit.json)
preserve 3,455 originals, all 1,440 earlier NBA labels and 868 curated references.
Actual readers and duplicate guard pass. NBA totals are **1,680 accepted,
1,536 centers and 144 nulls**, with **2,159 unaccepted**. Original review evidence
and the preserved receipt-timing correction remain unchanged. No fit or tests ran.

[NBA12 source preparation and complete review](../ball_tracking_completion_nba_reference_batch_12.md)
passes 240 exact native PNG/PTS checks for DEN–BOS e06 frames 150–389 and preserves
3,403 earlier files. First attempt elapsed 58.684 seconds; primary returned 390
frames after 391 packets, alternate emitted 390 RGB frames and reported 391
filter frames. Prefix 0–149 and filter frame 390 are disclosed same-training-source
context; only 150–389 were saved. Full-source final 564 is distinct from batch
final 389. Source preparation, complete delivery and finalization each passed
on their first attempt.

All three sealed parts provide **240 pending judgments, 220 centers and 20
nulls at 182–197 and 386–389**, with **5–8px center uncertainty**. Visibility
is 176 partial, 54 full, four indeterminate (188–191) and six not visible
(192–197); ten of the partial judgments have null centers. Middle notes/tags
at 272–273 and 276–277 were corrected without changing geometry, visibility
or uncertainty. The original proposal is retained. Its receipt also retains
a system-Python launch failure caused by missing PIL: no outputs were created,
and the unchanged helper succeeded with the project `.venv`. First and final
parts remain unchanged from their initial proposals.

The [final result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_12_result_v0_1.json)
is ready for human reference acceptance. The
[integration audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/integration_audit.json)
passes **3,954 bindings, 240 source/annotation native joins, 480 encoded frames
and 440 center markers**. Complete 4s native/24s slow overlays preserve every
selected frame. Root actually inspected all twenty encoded/source sheets,
220 encoded center crops, 20 null contexts, full source 389 and both actual
encoded finals before recording the
[visual receipt](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_12/inspection/root_visual_review.json).
Final frame 389 remains partial/null; no flight position is propagated through
rim/net overlap. All-frame pixel comparisons and emitted color checks pass.

The actual pending-review reader passes 240 joins and creates zero accepted
labels. All 1,680 accepted NBA rows and 868 curated references remain unchanged;
the pending batch leaves **1,919 selected positions without proposals** and
**2,159 without accepted references**. Earlier acceptance preservation sets
remain separately bound and overlap. Prior 13-test renderer and current
12-test acceptance-reader receipts remain unchanged implementation evidence;
the original eight-test acceptance history stays separate. No tests, model
calls, fitting or protected evaluation ran for this increment.

## NBA11 complete review ready for reference acceptance

[NBA11](../ball_tracking_completion_nba_reference_batch_11.md) uses fixed
training-role DEN–BOS e05, `84.mp4`, frames **210–449**, native **[3.5,7.5)s**;
full-source final is **586**. Preparation passed on its first attempt in
**38.448 seconds**, with **240 exact native PNG/PTS matches** and **2,969 prior
files unchanged**. The primary decoder returned frames 0–449 after 451 submitted
packets; alternate conversion emitted 450 RGB frames and reported filter frames
0–450. Prefix 0–209 and filter frame 450 are disclosed same-training-source
context; only selected frames 210–449 were saved. All 240 source and proposed
frames, including full part endpoints, are inspected: **240 centers, zero nulls,
172 partial and 68 fully visible judgments**, with **5–8px uncertainty**.
All initial written proposals remain unchanged, with no annotation corrections
or annotation-helper failures. The source shows a drive, pass, catch and shot,
followed by rim/net and hand interaction. The fixed selection category
`recovery` remains provenance, not a measured model recovery or hidden interval.
The [final result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_11_result_v0_1.json)
and [integration audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/integration_audit.json)
pass **3,494 bindings, 240 native joins, 480 encoded frames and 480 center
markers**. Complete 4s/24s overlays retain every frame at 60/10 fps; emitted
color metadata and every encoded-frame comparison pass. All twenty sheets,
240 encoded center crops, full native source 449 and both actual encoded finals
were inspected. Final 449 retains **[517,190] ±6px**. Delivery and finalization
passed on their first attempts; the actual pending-review reader also passes.

The first root receipt was written in the same tool call that fetched the final
images, before those images returned. After actual inspection of both returned
images, a separate [confirmed receipt](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_11/inspection/root_visual_review_confirmed.json)
preserved the original and documented the sequence correction. Finalization uses
that confirmation. No labels or media changed; no source or test rerun followed.

All **1,440 accepted NBA labels** and **868 curated references** are unchanged,
including prior acceptance snapshots of 286, 543, 809, 1,050, 1,549, 2,000, 2,245,
2,490, 2,742 and 3,015 files; these preservation sets overlap. Prior 13-test renderer
and current 12-test acceptance evidence remains historical, with zero reruns;
the original eight-test acceptance record stays separate. Current record/media
validation is not model accuracy or independent human ground truth. These pending
proposals leave **2,159 selected positions without proposals** and **2,399 without
accepted references**. No new accepted labels, model calls, fitting or protected
evaluation.

## NBA10 accepted; reference preparation continues

Ryan said **“I approve chat. Where are we at in the training”** after the complete
NBA10 review and question identifying all 120 proposals, including **100 centers,
20 nulls at 270–289 and 5–8px uncertainty**. The separate
[acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_10_acceptance_v0_1.json)
and [publication audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_10/acceptance_audit/publication_audit.json)
preserve **3,015 original files**, all 1,320 earlier accepted NBA labels and all
868 curated references. Actual publication/inventory readers and the duplicate
guard pass. Combined coverage is **1,440/3,839 accepted**, with **1,296 centers and
144 nulls**; **2,399 remain unaccepted**. The exact user-event time remains null;
publication time is separate. Original proposals, pending-era result and media
remain unchanged. Prior 12-test acceptance and 13-test renderer evidence is
retained without rerunning tests; the original eight-test reader history remains
separate. No source decoding, inference or fitting occurred for this publication.

The stage remains reference preparation. No completion-campaign fit has run,
and the full accepted source/label/role package and executable recipe are not
yet frozen. NBA10 acceptance makes the reviewed labels training-eligible at label
scope; checkpoint selection stays false. Package readiness, recipe freeze and
fitting authorization from this label-acceptance artifact remain false. Continue
the fixed NBA references and remaining 405 permitted curated positions, then
freeze the full package and recipe before the already approved fit. Curated
references remain evaluation-only. Protected evaluation stays closed pending
a frozen method and separate explicit authorization; no next-batch preparation
is claimed.

## Earlier NBA09 acceptance and completed NBA10 preparation

Ryan answered **“Accept all 120 proposals”** to the exact NBA09 review question,
including 112 partial and eight full centers, zero nulls and 5–8px uncertainty.
The [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_09_acceptance_v0_1.json)
and [publication audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_09/acceptance_audit/publication_audit.json)
preserve **2,742 original files**, all 1,200 earlier accepted NBA labels and all
868 curated references. Actual publication/inventory readers and the duplicate
guard pass. Combined coverage is **1,320/3,839 accepted**, with **1,196 centers and
124 nulls**; **2,519 remain unaccepted**. The exact user-event time remains null;
publication time is separate. Original pending-era review records and media
remain unchanged. Prior 12-test acceptance and 13-test renderer evidence is
retained without rerunning tests. No source decoding, inference or fitting
occurred for acceptance publication.

[NBA10](../ball_tracking_completion_nba_reference_batch_10.md) uses fixed training-role
DEN–BOS e04, original `132.mp4`, frames **240–359**, native **[4,6)s**; source final
is **578**. Source preparation passes **120 exact RGB/PTS checks**, preserving
**2,696 prior files**. The primary decoder submitted 361 packets and returned
frames 0–359; alternate conversion emitted 360 RGB frames and reported filter
frames 0–360. Frames 0–239 and filter frame 360 are disclosed same-training-source
context, not additional labels or review frames. Only selected 240–359 were saved.
Preparation succeeded on its first attempt in **22.086 seconds**. Both decoder
paths use FFmpeg components, establishing transport consistency without independent
visual ground truth. All three source/proposed parts are inspected: **100 centers,
20 nulls and 5–8px uncertainty**, with 68 full, 40 partial, two indeterminate and
ten not-visible judgments. Nulls span 270–289: clipped fragments at 270–273 and
286–289, ambiguous fringe at 274–275, and no visible ball at 276–285. Current
arcs support re-entry centers [391,4] at 290–291 with 7px uncertainty; no center
was extrapolated or clamped to the image boundary. All first written proposals
remain unchanged, with no annotation corrections or annotation-helper failures.
The first-part receipt separately retains a recovered oversized endpoint-image
response and an initial wrong documentation filename; both were resolved before
annotation without altering source evidence.

The [NBA10 result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_10_result_v0_1.json)
and [integration audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_10/integration_audit.json)
pass **3,049 file bindings, 120 native joins, 240 encoded frames and 200 center
markers**. Complete 2s/12s overlays retain all 120 frames at 60/10 fps; emitted
color metadata and every encoded-frame comparison pass. All ten sheets,
100 encoded center crops and 20 null source contexts were inspected, plus full
native source frame 359 and both full encoded finals. Additional source-edge
details 264–279 and 280–297 were also inspected. The actual pending-review reader
passes. Prior 13-test renderer and current 12-test acceptance-reader evidence
remains historical, with no new suite run; the original eight-test acceptance
record remains separate retained history. All 1,320 accepted NBA and 868 curated
labels remain unchanged, including prior acceptance snapshots of 286, 543, 809,
1,050, 1,549, 2,000, 2,245, 2,490 and 2,742 files. These preservation sets overlap.
The 120 pending proposals leave **2,399 selected positions without proposals**
and **2,519 without accepted references**. No fitting or protected evaluation ran.

## Earlier NBA08 acceptance and completed NBA09 preparation

Ryan said **“I approve chat. Move forward”** in response to the complete NBA08
review and question identifying 120 centers, zero nulls and 4–6px uncertainty.
The [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_08_acceptance_v0_1.json)
and [publication audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_08/acceptance_audit/publication_audit.json)
preserve **2,490 original files**, all 1,080 earlier accepted NBA labels and all
868 curated references. Actual publication/inventory readers and the duplicate
guard pass. Combined coverage is **1,200/3,839 accepted**, with **1,076 centers and
124 nulls**; **2,639 remain unaccepted**. The exact user-event time remains null;
publication time is separate. Original pending-era review records and media
remain unchanged. Prior 12-test acceptance and 13-test renderer evidence is
retained without rerunning tests. No source decoding, inference or fitting
occurred for acceptance publication. The later structured response
**“Accept all 120 proposals”** is preserved as an
[explicit NBA08 confirmation](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_08/acceptance_audit/explicit_followup_confirmation.json)
binding the unchanged original receipt; it adds zero labels and excludes NBA09.

[NBA09](../ball_tracking_completion_nba_reference_batch_09.md) uses fixed training-role
DEN–BOS e03, original `44.mp4`, frames **0–119**, native **[0,2)s**; source final
is **474**. Source preparation passes **120 exact RGB/PTS checks**, preserving
**2,445 prior files**. The primary decoder submitted 121 packets and returned
frames 0–119; alternate conversion emitted 120 RGB frames and reported filter
frames 0–120. Filter frame 120 is disclosed same-training-source context, not an
additional label or review frame. Only selected 0–119 are saved. Preparation
succeeded on its first attempt in **20.743 seconds**. Both decoder paths use
FFmpeg components, establishing transport consistency without independent visual
ground truth. All three parts are inspected: **120 centers, zero nulls and
5–8px uncertainty**, with 112 partial and eight full judgments. Fully visible
frames are 12–15 and 80–83. The advancing ballhandler dribbles toward a developing
screen; hand, leg and crossing-player overlap remain explicit. Every current-frame
source/proposed overlay and each part's full endpoints was inspected; extra source
70–79 review confirms centers supported within uncertainty. All initial drafts
remain unchanged, without annotation corrections or annotation-helper failures.

A routine [config-guard argument error](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_09/config_preflight_correction.json)
was corrected before the config was written. Two temporary model-capacity
[agent-dispatch failures](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_09/agent_dispatch_notes.json)
were retried with the same model and scope. These retained orchestration records
are separate from successful source preparation and annotation evidence.

The [NBA09 result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_09_result_v0_1.json)
passes **2,768 file bindings, 120 native joins, 240 encoded frames and 240
markers**. Complete 2s/12s overlays retain all 120 frames at 60/10 fps; emitted
color metadata and every encoded-frame comparison pass. All ten sheets and
120 encoded center crops were inspected, plus full native source frame 119 and
both full encoded finals. The actual pending-review reader passes. Source
preparation, delivery and finalization succeeded on their first attempts; no
suite was rerun. Prior 13-test renderer and current 12-test acceptance-reader
evidence remains historical; the original eight-test acceptance record is
separate retained history. All 1,200 accepted NBA and 868 curated labels remain
unchanged, including prior acceptance snapshots of 286, 543, 809, 1,050, 1,549,
2,000, 2,245 and 2,490 files. These preservation sets overlap. The 120 new labels
remain pending: **2,519 selected positions have no proposals** and **2,639 have no
accepted reference**. No fitting or protected evaluation ran.

## Earlier NBA07 acceptance and completed NBA08 preparation

Ryan answered **“Accept all 120 proposals”** to the exact NBA07 question,
including 120 partially visible centers, zero nulls and 5–6px uncertainty. The
[acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_07_acceptance_v0_1.json)
and [publication audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_07/acceptance_audit/publication_audit.json)
preserve **2,245 original files**, all 960 earlier accepted NBA labels and all
868 curated references. Actual publication/inventory readers and the duplicate
guard pass. Combined coverage is **1,080/3,839 accepted**, with **956 centers and
124 nulls**; **2,759 remain unaccepted**. The exact user-event time remains null;
publication time is separate. Original pending-era review records and media
remain unchanged. Prior 12-test acceptance and 13-test renderer evidence is
retained without rerunning tests. No source decoding, inference or fitting
occurred for acceptance publication.

[NBA08](../ball_tracking_completion_nba_reference_batch_08.md) uses fixed training-role
DEN–BOS e02, original `19.mp4`, frames **0–119**, native **[0,2)s**; source final
is **398**. Source preparation passes **120 exact RGB/PTS checks**, preserving
**2,201 prior files**. The primary decoder submitted 121 packets and returned
frames 0–119; alternate conversion emitted 120 RGB frames and reported filter
frames 0–120. Filter frame 120 is disclosed same-training-source context, not an
additional label or review frame. Only selected 0–119 are saved. Preparation
succeeded on its first attempt in 22.15 seconds. Both decoder paths use FFmpeg
components, establishing transport consistency without independent visual ground
truth. All three parts are now inspected: **120 centers, zero nulls and 4–6px
uncertainty**, with 92 partial and 28 full judgments. The free-throw shooter
gathers/lifts the ball, then releases it into flight. Every current-frame
source/proposed overlay and each part's full endpoints was inspected. All initial
drafts remain unchanged, with no corrections or helper failures.

The [NBA08 result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_08_result_v0_1.json)
passes **2,514 file bindings, 120 native joins, 240 encoded frames and 240
markers**. Complete 2s/12s overlays retain all 120 frames at 60/10 fps; emitted
color metadata and every encoded-frame comparison pass. All ten sheets and
120 encoded center crops were inspected, plus full native source frame 119 and
both full encoded finals. The actual pending-review reader passes. Source
preparation, delivery and finalization succeeded on their first attempts; no
suite was rerun. Prior 13-test renderer and current 12-test acceptance-reader
evidence remains historical; the original eight-test acceptance record is
separate retained history. All 1,080 accepted NBA and 868 curated labels remain
unchanged, including prior acceptance snapshots of 286, 543, 809, 1,050, 1,549,
2,000 and 2,245 files. These preservation sets overlap. The 120 new labels remain
pending: **2,639 selected positions have no proposals** and **2,759 have no
accepted reference**. No fitting or protected evaluation ran.

## Earlier NBA06 acceptance and completed NBA07 preparation

Ryan said **“Looks good. Please move forward chat. I approve the batch”** after
review delivery and the status identifying all 240 NBA06 proposals, including
224 centers, 16 nulls and 5–8px uncertainty. The separate
[acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_06_acceptance_v0_1.json)
and [publication audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_06/acceptance_audit/publication_audit.json)
preserve **2,000 original files**, all 720 earlier accepted NBA labels and all
868 curated references. Actual publication/inventory readers and the duplicate
guard pass. Combined coverage is **960/3,839 accepted**, with **836 centers and
124 nulls**; 2,879 remain unaccepted. All six fixed CHI–IND episodes are accepted.
The exact user-event timestamp remains null; publication time is separate.
Original pending-era review records and media remain unchanged. Prior 12-test
acceptance and 13-test renderer evidence is retained without rerunning tests.
No source decoding, inference or fitting occurred for acceptance publication.

[NBA07](../ball_tracking_completion_nba_reference_batch_07.md) begins the fixed
training-role DEN–BOS episodes: e01, original `3.mp4`,
frames **0–119**, native **[0,2)s**, source final **602**. Its three sealed parts
contain **120 partially visible centers, zero nulls and 5–6px uncertainty**.
The ball is held overhead and lowered toward the waist while teammates move;
no pass occurs during the selected window. Every current-frame source/proposal
and full part endpoints were inspected. All initial drafts remain final, without
corrections or helper failures. The labels remain pending separate acceptance;
**2,759 selected positions have no proposals**. Protected evaluation is closed.

Source preparation passes **120 exact RGB/PTS checks**, preserving **1,957 prior
files**. The primary decoder submitted 121 packets and returned frames 0–119;
alternate conversion emitted 120 RGB frames and reported filter frames 0–120.
Filter frame 120 is disclosed same-training-source context, not an additional
label or review frame. Only selected 0–119 are saved. Source preparation succeeded
on its first attempt; both decoder paths use FFmpeg components, establishing
transport consistency without independent visual ground truth.

The [NBA07 result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_07_result_v0_1.json)
passes **2,264 file bindings, 120 native joins, 240 encoded frames and 240
markers**. Complete 2s/12s overlays retain all 120 frames at 60/10 fps; emitted
color metadata and every encoded-frame comparison pass. All ten sheets and
120 encoded center crops were inspected, plus full native source frame 119 and
both full encoded finals. The actual pending-review reader passes. Source
preparation, delivery and finalization succeeded on their first attempts; no
suite was rerun. Prior 13-test renderer and current 12-test acceptance-reader
evidence remains historical; the original eight-test acceptance record is
separate retained history. All 960 accepted NBA and 868 curated labels remain
unchanged, including prior acceptance snapshots of 286, 543, 809, 1,050, 1,549
and 2,000 files. These preservation sets overlap. The 120 new labels remain
pending; **2,759 selected positions have no proposal**, while **2,879 have no
accepted reference**. No fitting or protected evaluation ran.

## Earlier NBA05 acceptance and completed NBA06 preparation

Ryan answered **“Accept all 240 proposals”** to the exact NBA05 review question,
including 178 centers, 62 nulls and 4–9px uncertainty. The separate
[acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_05_acceptance_v0_1.json)
and publication preserve **1,549 original files**. Actual publication/inventory
readers and the duplicate guard pass. All 480 earlier NBA labels and 868 curated
references remain unchanged. Combined coverage is **720/3,839 accepted**, with
**612 centers and 108 nulls** and **3,119 not yet accepted**. The exact user-event
time remains null; publication time is separate. Prior 12-test acceptance and
13-test renderer evidence is retained, with no rerun, source decoding, inference
or fitting for publication. The original NBA05 preparation result and media
remain unchanged; the later receipt supplies the accepted status.

[NBA06](../ball_tracking_completion_nba_reference_batch_06.md) uses fixed CHI–IND
e06, `221.mp4`, native frames **240–479**: **240 frames** in **[4,8)s**, at timebase
1/60000. The full source ends at **718**. Its final proposals contain
**224 centers and 16 nulls**, with **5–8px uncertainty**: 134 partial, 100 full,
four not-visible and two indeterminate judgments. Nulls preserve unresolved
observations at 280–281, occlusions at 282–285 and partial fragments at 404–413.
Every current-frame source/proposal was inspected; all three initial parts remain
unchanged, with no corrections or failures. These new references remain pending
separate acceptance.

Source preparation passes **240 exact RGB/PTS checks**, preserving **1,507 prior
files**. Primary decoding submitted 481 packets and returned frames 0–479;
alternate conversion emitted 480 RGB frames and reported filter frames 0–480.
Lead-in 0–239 and filter frame 480 are disclosed same-training-source context,
not additional labels. Only 240–479 are saved for review. Source preparation
succeeded on its first attempt; both decoder paths use FFmpeg components,
establishing transport consistency without independent visual ground truth.

The [NBA06 result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_06_result_v0_1.json)
passes **2,014 file bindings, 240 native joins, 480 encoded frames and 448
markers**. Complete 4s/24s overlays retain all 240 frames at 60/10 fps; emitted
color metadata and every encoded-frame comparison pass. All 20 sheets, including
224 encoded center crops and 16 null-source-context crops, were inspected, plus
native source frame 479 and both full encoded finals. The actual pending-review
reader passes. Delivery and finalization succeeded on their first attempts;
no suite was rerun. All 720 accepted NBA and 868 curated labels remain unchanged,
including prior acceptance snapshots of 286, 543, 809, 1,050 and 1,549 files.
These preservation sets overlap. New labels remain pending; **2,879 selected
positions have no proposal**, while **3,119 have no accepted reference**.
No fitting or protected evaluation ran.

## Earlier NBA04 acceptance and completed NBA05 preparation

Ryan answered **“Accept all 120 proposals”** to the exact NBA04 review question,
including 118 centers, two unknown centers at 300–301 and 5–7px uncertainty.
The separate [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_04_acceptance_v0_1.json)
and publication preserve **1,050 original files**. Actual publication/inventory
readers and the duplicate guard pass. All 360 earlier NBA labels and 868 curated
references remain unchanged. Combined coverage is **480/3,839 accepted**, with
**434 centers and 46 nulls** and **3,359 not yet accepted**. The exact user-event
time remains null; publication time is separate. Prior 12-test acceptance and
13-test renderer evidence is retained, with no rerun, source decoding, inference
or fitting for publication.

[NBA05](../ball_tracking_completion_nba_reference_batch_05.md) is ready for separate acceptance
from fixed CHI–IND e05, `174.mp4`, native frames **270–509**: **240 frames**
in **[4.5,8.5)s**, at timebase 1/60000. The full source ends at **756**.
The final proposals contain **178 centers and 62 nulls**, with **4–9px uncertainty**:
170 partial, 32 full, 32 not-visible and six indeterminate judgments. Nulls
preserve 24 partial fragments, 32 occlusions and six unresolved observations.
Every current-frame source/proposal was inspected; all three initial parts remain
unchanged, with no revisions or failures.

Source preparation passes **240 exact RGB/PTS checks**, preserving **1,009 prior
files**. Primary decoding submitted 511 packets and returned frames 0–509;
alternate conversion emitted 510 RGB frames and reported filter frames 0–510.
Lead-in 0–269 and filter frame 510 are disclosed same-training-source context,
not additional labels. Only 270–509 are saved and reviewed.

The [NBA05 result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_05_result_v0_1.json)
passes **1,558 file bindings, 240 native joins, 480 encoded frames and 356
markers**. Complete 4s/24s overlays retain all 240 frames at 60/10 fps.
Every encoded center crop and null-source-context crop across 20 sheets was
inspected, plus native source final 509 and both full encoded finals. The actual
pending-review reader passes. Source preparation, delivery and finalization
succeeded on their first attempts; no suite was rerun. All 480 accepted NBA and
868 curated labels remain unchanged, including prior acceptance snapshots of
286, 543, 809 and 1,050 files. New labels remain pending; **3,119 selected positions
have no proposal**, while **3,359 have no accepted reference**. No fitting or
protected evaluation ran.

## Earlier NBA03 acceptance and completed NBA04 preparation

Ryan's **“Accept all 120 proposals”** answers the complete NBA03 review question,
accepting its 100 centers, 20 nulls and 4–8px uncertainty. The separate
[acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_03_acceptance_v0_1.json)
and accepted publication preserve **809 original files**, including the prior
240 NBA labels. Actual publication, inventory and duplicate-guard checks pass.
Combined coverage is **360/3,839: 316 centers and 44 nulls**, with 3,479 not yet accepted. All 868
curated references and 760 eligible centers remain unchanged. No tests reran:
the unchanged code retains prior 12-test acceptance and 13-test renderer evidence.

[NBA04 source preparation](../ball_tracking_completion_nba_reference_batch_04.md)
passes all **120 selected native PNG/PTS comparisons**, frames 300–419 of
CHI–IND `81.mp4`, timebase 1/60000, source final 552. All **765 captured prior
files** are preserved. Primary decoding used 421 packets and returned 0–419;
alternate conversion emitted 420 RGB frames and reported filter context 0–420.
Only 300–419 are selected labels/review frames. The sealed proposal contains
**118 centers and two indeterminate nulls at 300–301**, with **5–7px uncertainty**;
visibility totals are 78 partial, 40 full and two indeterminate. All source and
proposed-overlay frames/endpoints were inspected; neither part needed revisions
or had helper failures.

The [NBA04 result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_04_result_v0_1.json)
is ready for human reference acceptance. Current validation passes **1,054
bindings, 120 native joins, 240 encoded frames and 236 markers**. Every encoded
center crop and both unmarked null-context crops across all ten sheets were
inspected, along with native source final 419 and both full encoded finals.
Complete native/slow overlays contain all 120 frames at 60/10 fps (2s/12s),
and the actual pending-review reader passes. All 360 accepted NBA and 868 curated
labels remain unchanged; prior acceptance snapshots of 286, 543 and 809 files
also pass preservation checks. The 120 new labels remain pending separate
acceptance, with 3,359 selected positions without proposals and 3,479 without
accepted references. No fitting or protected evaluation ran.

The original [NBA03 preparation result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_03_result_v0_1.json)
contains **100 centers and 20 nulls**, with 4–8px uncertainty: 100 partially
visible, four fully visible and 16 hidden judgments. Frames 138–153 remain
hidden/null; 154–155 and 208–209 remain partial/null. Corrections to centers
130–131 preserve the initial draft and superseded overlay. A receipt-writer
keyword failure and pre-output unsorted-tag failure remain recorded with their
separate corrected helpers.

Its preparation validation passed **808 bindings, 120 native joins, 240 encoded frames
and 200 markers**. Every source/proposed frame, encoded center crop and null
source-context crop was inspected, along with native/slow full final 239.
Complete overlays retain 120 frames at 60/10 fps (2s/12s); the actual pending
review reader passed. The preparation record and its original pending status
remain unchanged; the later acceptance receipt supplies the accepted status.
It preserved all 240 earlier NBA and 868 curated labels, including prior
acceptance snapshots of 286 and 543 files. No fitting or protected evaluation ran.

Ryan's earlier **“I accept this batch. Let’s move forward”** accepted all 120
NBA02 centers and their visibility/uncertainty judgments. Its separate
[acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_02_acceptance_v0_1.json)
preserves 543 original files and brought the inventory to 240 accepted NBA
labels (216 centers, 24 nulls). Actual reader and duplicate checks passed;
curated coverage stayed unchanged. The later NBA03 event builds on that record.

## Earlier NBA01 acceptance and completed NBA02 preparation

Ryan's **“Ok I approve chat. Please move forward”** directly accepts NBA01's
complete 120-label review, including 96 centers and 24 nulls. The separate
[receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_01_acceptance_v0_1.json)
and accepted copy preserve all 286 original files, AI authorship, native timing,
uncertainty and nulls. The unknown user-event time remains null; publication
time is separate. No playback telemetry or independent human annotation is
claimed.

The new acceptance reader validates the actual producer result, config, roles,
native source hash, reviewed annotation/frame joins and completed 13-test
delivery receipt. All **eight new acceptance tests pass**, as do actual emitted
publication/receipt and inventory readers; duplicate native-source frames are
rejected. An initial successful eight-test run is preserved before compact
video-evidence serialization was added; the final eight-test run covers it.
The original review implementation and its 13-test result are unchanged, and
no full suite was rerun. Reference-label training eligibility is true, while
package readiness, recipe freeze and fitting/protected authorization are false.
Accepted NBA coverage is 120/3,839; curated coverage remains 868/1,273.

A later acceptance-reader revision passes **12 focused tests**: the original
eight plus four scope regressions. Exact pre-revision code/tests and original
eight-test receipts were preserved first. Reusing the unchanged producer's
13-test receipt now requires explicit prior-implementation scope and the new
batch's bound, complete integration audit; default proposal-specific checks
remain strict. The original accepted publication and receipt still validate
unchanged. No old test run is claimed to cover the revised acceptance reader.

[NBA02 preparation](../ball_tracking_completion_nba_reference_batch_02.md) uses
fixed CHI–IND source `17.mp4`, frames 0–119 at timebase 1/60000, source final 358.
All 120 native PNGs match explicit BT.709 comparison; 253 preexisting files were
preserved by preparation. Source identity includes the original video hash, so
its frame 0 does not alias NBA01's frame 0. The sealed 120-label proposal has
120 centers, no nulls, 68 fully visible and 52 partially visible judgments with
4–7px uncertainty. Six hand-overlap revisions preserve their initial draft and
unchanged centers. Two failed pre-output helper invocations are preserved.

The [NBA02 result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_02_result_v0_1.json)
is ready for human reference acceptance. Its current audit verifies **527
bindings, 120 source/native annotation joins, 240 encoded frames and 240
markers**, with all source frames, encoded center crops and native/slow final
119 inspected. Both complete overlays preserve all 120 frames at 60/10 fps
(2s/12s). The actual production pending-review reader also passes. Source
preparation used 121 packets to return 120 frames; alternate conversion reports
frame 120 as filter context only, outside the labels and review.

The unchanged renderer retains its original 13-test evidence, with zero reruns
this increment; this batch's actual records and encoded media were checked
separately. All 120 accepted NBA01 and 868 accepted curated references remain
unchanged. Source preparation's 253 prior files and acceptance publication's
286 original files pass preservation checks. NBA02's 120 labels remain pending
Ryan's acceptance, with 3,599 selected NBA judgments still without proposals
and 3,719 without accepted references. No fitting or protected evaluation ran.

## First NBA completion reference batch: complete review, acceptance pending

The [NBA batch-01 report](../ball_tracking_completion_nba_reference_batch_01.md)
records 120 pending training-episode proposals: 96 centers, 24 nulls and
3–7-source-pixel uncertainty. All 120 native source PNGs and PTS joins match
explicit BT.709 comparison. The initial OpenCV conversion used BT.601 and failed
the exact-pixel check; the failed attempt and original PNGs remain preserved.
A detail-sheet syntax error before output creation is also recorded.

The new NBA consumer validates fixed episode/game roles, native timing and
completed source-audit evidence while preserving pending-label eligibility.
Its rendering path currently requires constant cadence. An independent
metadata audit verifies 185 bindings, all 120 native joins and both actual
annotation parts; production accepted-reference readers still return 868 rows,
760 eligible centers, 20 authorities and seven acceptance receipts. That audit
predates the render-only color fix; its exact module snapshot is retained.

The first native render failed because emitted primaries/transfer tags were
absent despite encoder options. Failed `review_v1` media and the executed code
remain preserved. Explicit color conversion and frame properties resolved the
metadata loss in `review_v2`; source PNGs and proposals were unchanged. All 13
focused tests pass with zero failures, errors or skips and bind the final code.
The [preparation result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_01_result_v0_1.json)
records 317 verified bindings, 120 native joins, 240 emitted frames and 192
markers. All source frames, encoded center crops, 24 null-center context crops
and complete final 119 were visually inspected. Native/slow playback is 2s/12s;
source clip final remains 662. All 868 accepted curated rows remain preserved,
and new NBA labels remain pending human acceptance.
No fitting, model inference or protected evaluation ran for this preparation.

## Grouped acceptance of reference batches 05–07

Ryan's 2026-10-22 statement “Hold up I approve and accept. Move forward” accepts
the 102 judgments identified in the preceding delivery summary. Separate receipts
for [05](../../configs/ball_tracking/reviews/ball_completion_reference_batch_05_acceptance_v0_1.json),
[06](../../configs/ball_tracking/reviews/ball_completion_reference_batch_06_acceptance_v0_1.json)
and [07](../../configs/ball_tracking/reviews/ball_completion_reference_batch_07_acceptance_v0_1.json)
bind exact accepted copies, preserving 77 centers, 25 nulls, native timing and
AI authorship. The grouped event is recorded honestly without invented form
answers, playback telemetry or independent human annotation.

Actual production consumers pass with sequential accepted counts 809, 839 and
868; eligible centers rise to 720, 750 and 760. Duplicate guards reject all three
ranges under the final inventory. All 766 prior rows and 330 bound original files
remain unchanged, including 283 original batch artifacts. The final metadata
inventory has 20 reference authorities plus seven campaign acceptance receipts,
868 accepted positions and 405 uncovered. No source pixels, models, scoring or
fitting ran to record acceptance. Protected evaluation remains unauthorized.

## Completion reference batch 07: complete review, acceptance pending

The [batch-07 result](../../configs/ball_tracking/reviews/ball_completion_reference_batch_07_result_v0_1.json)
binds 29 P001 proposals for frames 21–49: 10 centers with 7–10px uncertainty and
19 nulls. Visibility counts are 14 partial, three indeterminate and 12 hidden.
Nulls preserve partial fragments at 24/40–42, indeterminate hand/ball evidence
at 25–26/39 and body occlusion at 27–38. Original drafts remain final. Complete
native/slow overlays span 1.16/5.80 seconds through batch final 49. Native time
[0.88,2.04) differs from relative [0.84,2.00); P001 has a 512-tick native origin.

Selection used coverage and packet metadata before pixels, excluding both
pending batches 05/06 without promoting their 73 rows. Primary decoding returned
0–49 from 52 submitted packets through presentation index 52. Alternate decoding
used 53 copied packets 0–52 after payload and PTS/DTS verification. All 29 native
RGB arrays match exactly; no protected packet or output frame was used. Both
decoders may share FFmpeg internals.

All source frames, encoded center crops, unmarked exception crops and the
complete actual final were inspected. Checks cover 58 emitted frames, 20 markers,
1,129 file bindings, all native-frame/annotation joins and all review links.
All 1,011 earlier campaign files and 766 accepted rows remain unchanged.
Accepted coverage stays 766/1,273 with 683 eligible centers; pending batches
05–07 now contain 102 proposals, leaving 405 positions without any proposal.
A separate metadata-only audit passes 35 checks and verifies 133 directly
relevant files, including all null exceptions, accepted/pending separation and
actual video counts/timing, without additional pixel decoding.

Source preparation, pixel comparison, labeling and rendering passed first
attempts. Before execution, helper adaptation hit an absent lowercase-string
assertion; the failed guard and elapsed time are retained. A stale helper-path
binding was corrected before rendering. No media or label was changed to pass
checks. Production code/tests are unchanged, with no repeated suite, fitting,
inference, scoring, threshold change, player rerun or protected evaluation.
Human acceptance remains pending; campaign approval is already in force.

## Completion reference batch 06: complete review, acceptance pending

The [batch-06 result](../../configs/ball_tracking/reviews/ball_completion_reference_batch_06_result_v0_1.json)
binds 30 P003 proposals for frames 120–149: 30 centers, no nulls, 27 partially
visible and three fully visible judgments, with 5–8-source-pixel uncertainty.
All source and encoded crops plus the complete actual final were inspected.
Native/slow overlays span 1.20/6.00 seconds. P003's zero-origin PTS gives native
ticks 61440–76288 at timebase 1/12800; selected time is [4.80,6.00).

Metadata selected this run before pixels and excluded 43 pending batch-05
proposals without accepting them. Primary decoding returned outputs 0–149 using
152 packets through presentation index 153. Alternate comparison verified 154
copied packets 0–153 before decoding; all 30 selected PNGs match exactly. No
protected packets or output frames were used. Both decoders may share FFmpeg.

Integration checks 1,023 file bindings, all 30 annotation/native-frame joins,
60 encoded frames, 60 markers and all local review links. All 935 earlier
campaign files, 766 accepted rows and four acceptance receipts remain unchanged.
Accepted coverage stays 766/1,273 with 683 eligible centers and 507 uncovered;
73 pending proposals across batches 05/06 leave 434 with no current proposal.
A separate metadata-only audit passes 31 checks and rehashes 105 directly
relevant files, independently reconstructing accepted coverage, pending-batch
separation and actual video timing/counts without new pixel decoding.

Source preparation, pixel comparison and rendering passed on their first
attempts. A part-label helper failed on a nonexistent PNG-manifest `source_pts`
key before writing a proposal; original helper and failure remain preserved.
Its replacement uses actual packet metadata. Original proposals remain final.
Implementation and tests are unchanged; no repeated suite, fitting, inference,
model scoring, threshold change, player rerun or protected evaluation occurred.
New labels still require Ryan's acceptance; campaign approval remains in force.

## Completion reference batch 05: complete review, acceptance pending

The [batch-05 result](../../configs/ball_tracking/reviews/ball_completion_reference_batch_05_result_v0_1.json)
binds 43 P002 proposals for frames 275–317: 37 centers, six nulls and complete
native/slow overlays. Visibility counts are seven full, 32 partial, three
not-visible and one indeterminate. Partial/null293/312, occluded294–296 and
indeterminate313 retain uncertainty. Localized centers carry 4–10px uncertainty.
Ryan's human acceptance is pending; these are evaluation-only references.

Metadata selected the range before source pixels. Primary decoding used70
packets with presentation indices250–322 and returned68 outputs250–317. The
alternate copy held73 packets250–322, verified payload/PTS/DTS before decoding;
all43 native PNG arrays matched, including final317. No protected175–249 packets
or frames were submitted, copied or decoded. Native timebase1/12800 and source
interval[11.04,12.76) remain distinct from relative[11.00,12.72).

After Ryan's requested shutdown pause and explicit2026-10-22 resumption, all75
checkpointed files and829 earlier campaign files matched their hashes. The
completed second part and source pixels were reused; the first22-frame part was
finished. All43 source/proposed/encoded crops and actualfinal317 were inspected.
Checks cover86 emitted frames,74 localized markers,944 file bindings, exact
annotation/native-frame joins and all review-page links. Original drafts remain
final. Accepted coverage is unchanged at766/1,273, with683 eligible centers and
507 permitted positions uncovered.

Resume metadata validation initially confused17 reference authorities with the
returned21 files, which include4 receipts. Finalization initially compared a
three-field PNG binding with the same binding plus a frame_index. Both assertions
were corrected against actual producer records, preserving original attempts,
consumed time and helper. The passing comparison separately verifies file path,
SHA256, size and source-frame identity. Source preparation and both renderings
succeeded without reruns. Earlier inspection path/runtime failures are retained.

Source implementation/tests are unchanged; the prior ten focused tests were not
repeated. No fitting, inference, model scoring, threshold change, player rerun or
protected evaluation occurred. Human reference acceptance and final-trajectory
review remain separate gates; the completion plan and ball criteria are approved.

## Completion reference batch 04: prepared, reviewed and accepted

The [batch-04 result](../../configs/ball_tracking/reviews/ball_completion_reference_batch_04_result_v0_1.json)
binds 75 P001 proposals for frames 125–199: 58 centers and 17 nulls, with complete
native/slow overlays through batch-final 199. Selection used uncovered coverage
and packet metadata before pixels. All 691 previous accepted rows and three
earlier acceptance receipts remain unchanged. Ryan explicitly accepted all 75
proposals, including uncertainty and nulls, in the later review response.

Guarded PyAV decoding returned 0–199 using 202 packets with maximum presentation
index 204. Independent OpenCV comparison used a bounded copy of 205 original
packets 0–204, with payload hashes and PTS/DTS verified. All 75 native PNGs match
exactly; no protected packet or frame was used. Native selected time is
[5.04,8.04), separately from relative [5.00,8.00). Both decoders may share FFmpeg.

Every source/proposal crop and final encoded crop was inspected. No draft
revisions were required. Actual-record validation checks 170 file bindings,
75 source/annotation/timing joins, 150 encoded frames, 116 marker regions and
both video finals. Code/tests are unchanged; earlier ten focused tests were
not rerun. No source/delivery failures, fitting, inference, model scoring,
player reruns or protected evaluation occurred.

Acceptance publication from clean `4dac2e79cdfb` preserves all 75 exact
annotation/native-frame records and original pending-era artifacts. Metadata-only
integration confirms all 691 prior rows unchanged, all 17 new nulls retained,
and future duplicate-guard rejection. Current coverage is 766/1,273, including
683 eligible centers, with 507 permitted frames uncovered. No new source pixels,
models or tests were run to record the acceptance.

## Completion reference batch 03: prepared, reviewed and accepted

The [batch-03 result](../../configs/ball_tracking/reviews/ball_completion_reference_batch_03_result_v0_1.json)
binds 131 new P002 proposals for frames 368–498 and both complete overlays,
including the actual source final. Selection used missing accepted coverage
before new source inspection. All 560 accepted rows across 15 authorities and
both campaign acceptance receipts remain unchanged.

Source decoding started at the verified keyframe 250 after the protected band.
Every submitted packet and emitted frame was guarded. An independent bounded
copy retained only encoded packets 250–498, with all 249 payload hashes and PTS
checked before its OpenCV decode. All 131 selected PNGs are pixel-identical;
native timing remains [14.76,20.00), separate from relative [14.72,19.96).
Both decoders may share FFmpeg internals, but no protected packet was submitted
or copied, and no protected output frame was decoded.

The unchanged renderer checks all 262 encoded frames and localized marker
regions against their actual source/annotation records. AI visual checks cover
every source frame, final encoded crop and actual final. Original drafts and
small manual refinements are retained. An independent source-only reader
disagreed with six first-reader net-overlap center estimates; frames 408–413
retain null geometry in the final proposal, with visibility indeterminate at
410–412. Ryan subsequently accepted all 131 proposals, including uncertainty
and nulls. A separate publication preserves the original reviewed records and
pending-era artifacts. Human acceptance does not change the AI origin.

No code or tests changed. The prior ten focused tests are recorded only for
the unchanged implementation; they were not rerun. New validation checks the
actual batch-03 records. A preservation-reader schema error was corrected and
the failed attempt preserved separately. No fit, inference, model scoring,
player rerun or protected evaluation occurred. Acceptance integration confirms
all 560 previous rows unchanged, 131 exact annotation/native-frame joins and
duplicate-guard rejection of this accepted batch. Current accepted coverage is
691/1,273, with 625 eligible centers and 582 permitted frames uncovered.

## Completion reference batch 02: prepared, reviewed and accepted

The [batch-02 result](../../configs/ball_tracking/reviews/ball_completion_reference_batch_02_result_v0_1.json)
binds 120 new P002 proposals for frames 50–169 and complete native/slow overlays.
Ten focused reference tests pass, including five additions derived from the
actual accepted batch-01 producer records. They verify accepted publication and
receipt bindings, roles, exact annotation/native-frame agreement, duplicate and
conflict rejection, and historical batch-01 replay. No full suite was repeated.

An independent metadata inventory reproduces all 440 accepted keys and 833
uncovered positions. All 120 selected frames are uncovered and permitted; the
batch was chosen before new source inspection. Native times are [2.04,6.84),
separate from clip-relative [2.00,6.80). A PyAV/Pillow sequential-decode audit
matches every saved PNG pixel and timestamp, with no output frame requested
after169. The preparation used OpenCV; both may use FFmpeg internally, and
codec-internal lookahead was not instrumented.

Every current source frame was visually inspected, with null centers retained
where not defensible. Original drafts and manual refinements are preserved.
All 240 encoded overlay frames, localized marker regions and both actual finals
are checked against their source/label records. Ryan subsequently accepted all
120 proposals, including uncertainty and null centers. A separate metadata-only
publication preserves the exact annotations/native records and original
pending-era artifacts. Accepted coverage is now 560/1,273 with 713 remaining;
the earlier 440 accepted references remain unchanged. No fitting, inference,
model scoring or protected evaluation ran.

## Completion campaign first increment: retained baseline and accepted references

The [first-increment result](../../configs/ball_tracking/reviews/ball_completion_first_increment_result_v0_1.json)
binds four passing baseline tests and five passing reference-delivery tests to
their exact implementations. Actual-record checks preserve all 1,498 original
baseline observations; full review-video decoding verifies 225 protected
blackouts and all three finals. Availability is 979 observed / 294 missing,
not a new accuracy estimate. No inference or fit ran.

All 120 native P003 source PNGs were independently found pixel-identical to
sequentially decoded source frames 0–119; decoding stopped before frame 120.
Both complete overlays were decoded and checked across all 240 encoded frames
and marker regions. Ryan accepted all 120 assisted proposals, including stated
uncertainty. A separate publication preserves all annotation/native-frame
records, AI authorship, original drafts and pending-era review artifacts.
Current curated coverage is 440/1,273, with 833 frames remaining.

The final integration audit verifies 316 file hashes, exact native PTS/frame
lists for 3,839 selected NBA reference slots, all 24 episode preview receipts,
whole-game role isolation and no overlap with the existing 300 SAC training
rows. These slots await labeling and acceptance. Structural verification and
human reference acceptance do not accept model trajectories or the ball phase.

Preserved routine failures include a baseline test import indentation error,
the first reference encode's relative-path binding failure, an acceptance-helper
import path error, and the integration helper's wrong frame-container lookup
and stale duplicate P003 count. The final helper derives and checks that count
from the frame list. No scientific result, failed run, or original evidence was
replaced. Full suite not repeated; no protected source pixels read or protected
evaluation authorized. See the [increment report](../ball_tracking_completion_first_increment.md).

## Provisional fixed verifier: one converged fit; scientific protection failure

The [training result](../nba_ball_distractor_training_results.md) records one
33.125-second feature/fit run: 177 new encoder calls, 60 original cached crop
features, 176 cached source PNG decodes, no source video reads, and one optimizer
call. The 109-crop/90-object fit converged in 17 iterations / 20 function evaluations,
with no warnings. No retry or threshold tuning followed the failed checks.
Previously accepted checks are 5/10 correct, including only 2/6 balls.

The full feature pass completed first attempt in 569.860 seconds: 3,225 new
encodings plus 148 cached features, 2,295 NBA PNG reads and 1,273 NFHS permitted
frames. Independent audit verified all 3,373 vectors, crop/input transforms,
source/PTS/provenance joins and scalar logits (57,367 checks; maximum score
rounding difference 4.44e-16). The 3.266-second policy comparison keeps 1,847
points and 374/581 protected matches; it loses 207 protected matches and revokes
all 14 gap fills. This is a completed scientific failure, not an execution failure.

There are 26 distinct focused checks across classifier (7), training transport (3),
emission extraction (4), policy (6), renderer (3), and completed-phase replay (3).
They pass on the code versions bound in their receipts;
only affected checks were rerun after the fixture/output-guard corrections.
The first policy test run's two invalid synthetic certainty values are preserved;
changing `uncertain` to the producer's valid `ambiguous` enum corrected the fixture,
without changing production policy. A post-run CLI replay correction preserves the
original executed driver and verifies existing results before returning them; its
three actual-record checks perform no model or policy work and reject changed
bindings. Original completion receipts are unchanged. Full suite was not repeated.

A separate actual-record synthetic all-positive control reproduces 824 geometric
reference outcomes and preserves 3,373 emissions, 602 missing positions and all 581
unique protected matches. This is transport evidence, not model performance.
Independent initial-fit audits reproduce all weights, objective/gradient and
206 reference plus 60 old-case logits without a refit. Source/helper path failures
remain in their original receipts. New AI labels and new motion review remain
pending; no baseline, holdout, previous review or acceptance gate is promoted.

The complete media package verifies all 4,200 slots / 225 protected blackouts,
305 changed episodes, eight permitted-segment finals and five actual finals.
Six source encodes include two preserved P002 failures at 64.078s and 60.000s;
the duplicate was an unintended overlap between main and independent workers.
P002 recovery fully decodes the first existing review video and verifies a
video-bound exception for four exact RGB compression pixels, with <=3 elsewhere,
intended raw panels exactly zero, and two negative controls. No source reread,
re-encode, model call or production renderer change was needed. Its original
failure receipts remain failed. Encoded still layout/transport inspection covers
all five actual finals and representative suppressed points; human review pending.

## Approved bounded reference preparation: provisional insufficient-data result

The [complete result](../nba_ball_distractor_reference_results.md) records one
successful 104.085-second preparation of all 525 permitted source frames,
61.359-second source-sheet rendering, and a 1.808-second successful merge of
184 new proposals plus 26 unchanged accepted controls. New labels are
106 ball / 51 other / 27 unresolved. Grouped totals are 90 fit and 57 check;
25/27 provisional adequacy conditions pass. Excluded clothing and a new
actually emitted excluded head error are absent. No features or fit ran.

All 14 distinct focused tests pass (four preparation, four labels, six review).
Independent source/PNG, producer/consumer, physical-group/count and complete
encoded-media audits are bound in the
[result record](../../configs/ball_tracking/reviews/nba_ball_distractor_reference_result_v0_1.json).
Human label/grouping acceptance is pending. Every target and context final is
available; no new trajectory acceptance is claimed. Initial path-guard test,
prose-comparison audit and origin/role merge failures remain preserved; routine
corrections changed no scientific judgments or baseline. Full suite not repeated.

## Design-only inventory: bounded ball-versus-distractor verifier

The [new plan](../nba_ball_distractor_verifier_plan.md) and
[proposal](../../configs/ball_tracking/proposals/nba_ball_distractor_verifier_v0_1.json)
follow Ryan's request to design the next test. Read-only reconstruction of 426
existing triplet caches (678,226,005 bytes, peak three arrays) completed in
11.765 seconds; all 142 original means reproduced exactly. The 490 coordinate
groups support a frozen 160-candidate census and 24 separate unassigned contrast
slots, across 105 targets/525 context frames. Earlier planning candidates remain
preserved. No source pixels, new labels, model calls, fitting or policy run.

Distinct coordinates are not independent objects. Semantic adequacy remains
conditional on future accepted labeling, including new real candidate negatives,
NFHS coverage and actually emitted excluded head/non-head errors. Design checks
verify bindings, exact source/block roles, counts, context separation and bounded
policy semantics; they are not model or trajectory validation. No full suite is
required for this documentation/proposal increment. The failed feature screen
and earlier quantitative/visual evidence remain unchanged.

Independent inventory review passed 2,382 checks; 26 affected checks passed
after the explicit reused-reference grouping clarification. The root's final
binding/count/source-boundary audit passed 426 checks against the current plan
and proposal. Receipts are ignored `data/outputs/t/ball_distractor_design_audit_01.json`,
`ball_distractor_design_audit_02.json` and
`ball_distractor_verifier_design_audit_01.json`. These are design checks, not
evidence that the classifier works. Scientific review found no remaining
material design contradiction. `git diff --check` passed before integration.

## Completed approved experiment: fixed appearance-feature screen completed and rejected

Ryan approved the fixed screen with “Ok move forward chat”. The
[results and complete crop review](../nba_appearance_feature_screen_results.md)
and [bound result](../../configs/ball_tracking/reviews/nba_appearance_feature_screen_result_v0_1.json)
record one 12.594-second run: 60 crops from 49 cached frames, 500 similarities,
no training, no operational failure and no trajectory changes.

The strict gate failed: **8/10 accepted checks**, comprising 4/6 balls and
4/4 hands. DET11059 and DET11431 balls preferred other objects. All three
SAC1419–1421 head points still preferred ball; all four valid DET11722–11725
near-head ball points remained ball-preferred. The six accepted unknowns stay
unscored. The 34 older points have eleven qualitative disagreements and eight
unresolved judgments; they are not newly accepted class truth or pooled checks.

Six focused tests passed; the later affected renderer check passed after a
header-only change. Independent audit verified all 500 similarities, all source
and crop/input pixels, provenance and unchanged earlier evidence. All 50 query
rows and the actual final were AI-inspected; all 150 displayed crop panels
match their saved crops. New human review is not claimed, and no prior review
must be repeated to close this failed setup.

**Next direction:** close this exact nearest-reference setup. A subsequent
bounded supervised-verifier proposal must specify necessary NFHS, distinct
head/clothing and contributor-candidate coverage together with one fixed test.
It is not yet an execution proposal or approval. No cutoff or crop/encoder sweep
follows from this failure. The saved trajectories, retained 09da checkpoint,
rejected continuation, accepted references, protected holdouts and three older
pending motion reviews retain their status. Ball tracking remains unfinished.

## All 26 appearance references accepted; separate publication audited

Ryan explicitly accepted the presented package: “I accept the proposals. Move
forward chat”. The [acceptance results](../nba_appearance_reference_acceptance_results.md)
and [compact publication result](../../configs/ball_tracking/reviews/nba_appearance_reference_publication_result_v0_1.json)
bind the separate accepted artifact. All 26 labels/candidates, fifteen targets
and 75 context frames remain exact. Counts are ten ball, ten other-object and
six unresolved; source roles and AI authorship remain intact. DET11499 retains
the recorded reader disagreement and accepted unresolved judgment. Original
draft/seal/media/result receipts preserve their historical pending status.

Six focused publication tests initially passed in 10.845 seconds. A final
test-only correction made the suite skip when ignored captured evidence is
absent in a fresh checkout; all six passed again in 10.971 seconds. Initial test
source and log remain preserved, and the production publisher did not change.
One actual publication
completed in 0.696 seconds, with zero source-pixel decoding, model/array reads,
inference, fitting or geometric scoring. The implementation's tested local
bytes are bound in completion; the run does not claim a pre-execution commit.
Independent standard-library audit passed 380 checks covering full row/candidate
transport, native source/PTS joins, exact acceptance, counts/roles, disagreement,
review-byte preservation and unchanged earlier accepted27/original790 evidence.
No full suite or prior scientific comparison was repeated.

The separate [feature-screen plan](../nba_appearance_feature_screen_plan.md) and
[proposal](../../configs/ball_tracking/proposals/nba_appearance_feature_screen_v0_1.json)
remain unapproved and unexecuted: one fixed DINOv2 ViT-S/14 nearest-reference
screen, 60 crops/49 cached targets, strict ten-of-ten resolved-check gate,
unknowns unscored and 34 exposed regression objects reported separately.
No training, parameter search or prediction change follows from this acceptance.

## Earlier checkpoint: candidate appearance preparation and complete review; new label acceptance pending

Ryan's later “Move forward chat” approved appearance-reference preparation from
clean `codex/ball-detector-baseline` at
`31c84281821d22f66ae3963e88301cc556087218`. The fixed scope contains fifteen
targets, all 26 original mean candidates and 75 native context frames. Metadata
and whole-source roles were frozen before new source inspection; all current
34 gap/anchor targets and their 74 context frames remain separate regression
evidence. The scope audit passed 86 checks.

One source-preparation attempt completed in 14.968 seconds, reading 55 existing
hash-verified NBA PNGs and decoding twenty permitted NFHS frames after checking
both source-video hashes. No model calls, candidate-array reads, new centers,
geometric scoring or prediction changes occurred. Exact implementation bytes
are bound in the receipts; code was integrated locally after execution rather
than claiming a pre-execution commit.

Five preparation tests passed in 2.977 seconds. Five distinct renderer tests
passed across the last affected runs: three in the second run and the remaining
two in the third (4.010 seconds). The first renderer test run failed because a
synthetic producer fixture omitted `time_base`; the second exposed two test-only
error-string mismatches. These failures remain in their original logs. The
fixture and regex fixes changed tests only; production implementations match
the actual source/media receipts. No full suite was repeated.

The sealed AI draft proposes ten ball, ten other-object and six unresolved
labels. Potential-fit SAC/P002 contributes 4/6/5; excluded-check DET/P003
contributes 6/4/1. All five P002 objects remain unresolved. DET11499 also remains
unresolved, preserving disagreement between the first reader and another AI
reader's upper-arm interpretation. Check negatives are hands, with no new
excluded-check head example. Counts represent correlated candidate records,
not independent episodes or unseen validation data.

The first actual render completed in 20.359 seconds and produces a complete
48-second review. All 75 encoded frames passed source/candidate/class keys,
timing, paired pixels and local-marker checks. An independent audit passed
1,649 checks, including all 75 joins/probe times and 31 encoded stills; maximum
independent paired-pixel mean absolute error was 3.255 RGB levels. An AI reviewer
individually inspected all fifteen targets, fifteen context finals and the
actual compilation final (P003430, source PTS1548000), finding no material
delivery defect. This is encoded-still inspection, not continuous manual
playback or human acceptance.

The [results and review links](../nba_appearance_reference_results.md) and
[compact result](../../configs/ball_tracking/reviews/nba_appearance_reference_result_v0_1.json)
bind the complete evidence. Ryan's acceptance or corrections to these new
appearance labels remain pending. Earlier center-reference acceptance and
reviews, the original 790-frame report and accepted 27-reference extension are
unchanged. No future verifier fit, inference, threshold selection or trial is
authorized by this preparation.

## Accepted gap/anchor reference publication and evaluation completed

Ryan accepted the presented package with “ok great chat they have been reviewed.
move forward”. The separate acceptance and evaluator were committed at
`9ee85aee0d468674efae855bb8da6893e183a2b8`. One publication/evaluation run
completed in 2.156 seconds, preserving the sealed draft, pending-era receipts,
seven accepted controls and original 790-frame report. No new inference,
candidate-array read, source-pixel read, fit or prediction change occurred.

Four focused tests passed in 6.428 seconds, covering actual producer transport,
metadata-only publication/scoring, exact old controls, unchanged inclusive
ten-pixel semantics, five unknowns, uncertainty diagnostics, write-once outputs
and tamper rejection. No full suite was repeated. The
[compact result](../../configs/ball_tracking/reviews/nba_gap_anchor_reference_evaluation_result_v0_1.json)
binds the focused log, independent actual-run audit and exact artifacts. The
audit passes 1,901 checks, independently recomputing all 68 score records and
every summary with standard-library math, checking all 34 source joins and
seven controls, and verifying 27 artifact bindings without pixel decoding.

The 27 new references change from 14 matched/8 missing/5 unscored to
22 matched/0 missing/5 unscored, with zero geometric errors. All seven controls
reproduce their full prior score records exactly and are excluded from these
totals. The eight added geometric matches comprise six AI ball judgments and
two unresolved P001 boundary cases. All six P001 eligible targets remain
semantically unresolved despite geometric matches. SAC1419–1421 remain unknown
ball centers and separate adverse head-tracking evidence; P003333–334 remain
unknown and unresolved. No hidden-ball labels or fabricated error distances
were added. Full interpretation and the next proposed appearance-verification
increment are in the [evaluation report](../nba_gap_anchor_reference_evaluation_results.md).

The source-only reference review is complete; the original AI authorship,
non-blind correlated development scope and lack of separate human object
adjudication remain explicit. Broader unchanged-rule adoption remains unsupported.

## Gap/anchor reference preparation and review completed; acceptance pending

Ryan's later “Move forward chat” approved the
[reference batch](../nba_gap_anchor_reference_results.md). Code/scope integrated
at `dc4687780af407c1ae6b3a4c7e12376e7f4e5ffb`. Preparation attempt
`d799a9c5b0e847e8ab97de3dfcef1dcc` completed in 22.016 seconds: 23 existing NBA
PNG reads and 51 permitted NFHS decoded frames, zero model/array calls. Its
74 source identities were sealed before new labels. Twenty-seven AI judgments
comprise 22 partial-ball centers and five indeterminate/null frames; seven
accepted controls remain exact. No protected bands were decoded by the requested
segments and no context-only frames were labeled.

Six preparation tests pass; independent actual-source audit passes 792 checks.
Five renderer tests pass on final code, preserving the first successful set,
one overly strict codec marker-tolerance failure, and the affected checks'
successful rerun. Eleven distinct focused checks total; no full-suite repeat.
The proposal was sealed before separate 34-object inspection: 23 ball, three
other-object (SAC head anchors/fill), eight unresolved. Those are qualitative AI
judgments, not new geometric scores or human acceptance.

Render attempt `281e8692da094388aadb39391605f82a` completed in 21.437 seconds,
without an actual render failure. All 74 encoded frames, exact 24.8-second timeline,
reference/source/crop keys, both image panels and local reference markers pass.
Independent media audit passes 1,232 checks without repeating decode. AI still
inspection covers all 34 targets, ten context finals and actual final P003/366;
this does not claim continuous manual playback. The
[compact result](../../configs/ball_tracking/reviews/nba_gap_anchor_reference_result_v0_1.json)
binds drafts, source/object evidence, audits, test logs and media. Human reference
acceptance remains pending; prior 790-frame scores and all accepted evidence stand.
The default staged whitespace check flagged CRLF in the new result JSON.
Its original bytes and a semantic-equality note are preserved under the ignored
preparation directory; the unpublished record was normalized to LF without
changing scientific artifacts, and the default check was repeated.

## Continuous-context video review completion recorded

Ryan said “Ok videos reviewed. What’s next chat” after all five complete videos
were embedded in the preceding response. The
[later review record](../../configs/ball_tracking/reviews/nba_temporal_gap_continuous_visual_review_v0_1.json)
binds those exact five videos, manifests, render completions and actual finals.
This records user-reported completion without playback telemetry, explicit
quality endorsement or adjudication of the SAC head fill and uncertain NFHS
points. Their AI findings, all 24 numerical conditions, prior accepted bounded
gains and broader non-adoption recommendation remain unchanged. Original
pending-era result/media receipts remain preserved. The five reviews need not
be repeated; the three older negative motion reviews remain pending separately.

Read-only inventory of emitted gap records and the scored report confirms the
[next reference proposal](../nba_gap_anchor_reference_plan.md): 34 unique
gap/anchor targets, seven accepted overlaps, 27 new judgments and 74 permitted
context frames. The first metadata queries used a nonexistent gap field and
the historical NFHS window ID; both helper assumptions were corrected against
actual emitted records. The ignored `preparation/next_reference_batch_census.json`
preserves these inspection corrections. No annotation, new scoring, array load,
model call or media decode occurred. This is a proposed new development-reference
batch, not an executed experiment or independent test.

## Continuous-context validation — numerical pass with adverse unlabeled visual evidence

Ryan's explicit “Move forward chat” authorized the five-clip continuous plan;
the earlier resume and accepted bounded trial did not authorize this execution.
The [results report](../nba_temporal_gap_continuous_validation_results.md) and
[compact record](../../configs/ball_tracking/reviews/nba_temporal_gap_continuous_validation_result_v0_1.json)
preserve the original implementation, failure, correction and separate recovery
scope. Frozen selector policy and retained checkpoint `09da1214e94f` are unchanged.

Subsequent AI inspection identifies a wrong-object fill at SAC source frame 1420
(14.681 seconds into its comparison): the new point is on the foreground
light-blue defender's head/face. Unmarked native crops 1418–1422 place the original
1419/1421 anchors on the same moving head. All five source PNG and decoded RGB
hashes match their producer records. The exact notes, crop bindings and encoded
still are recorded in ignored `review/ai_sac_context_inspection.json` under the
continuous output root. This is a qualitative observation outside the 790 scored
references, not a new accepted label or numerical error-distance measurement.
The ball's true center/visibility remains uncertain; no scores changed. Broader
unchanged-rule adoption is not recommended. The three previously accepted
additions remain accepted, and Ryan's new trajectory review/adjudication is pending.

Attempt `890e7ac8d160491eb76f6d89d70c31be` failed before saving selections or
scores: an imported NFHS cache identity has no `source_video` field. The failed
receipt retains 1.391 seconds, 48 cache reads and 76,409,121 compressed bytes.
Commit `ad82b03d2dbad115d188e83f62e99faf3ca1c88b` corrects source binding through
the original experiment window and exact cache paths, preserving imported
model-only identities. The new regression derives that structure through the
actual producing `cache_index` and verifies the consuming loader.

Recovery attempt `c4c9e3e80c5b4beaaa49147f0e0ad3b5` completed in 4.031 seconds:
83 triplets, 132,172,876 compressed bytes, at most three arrays retained. All
3,975 choices were sealed before loading labels; 225 protected positions remain
excluded. All 3,359 original emitted points are exact. Fourteen new points in ten
gaps include three labeled matches and eleven unscored positions. DET changes
207/8/22 to 209/8/20 and NFHS 131/1/13 to 132/1/12 matched/wrong/missing;
SAC remains 218/5/47. Hidden alarms remain DET thirteen/NFHS zero, both NBA
controls remain 60/60, and the three accepted bounded additions retain exact
coordinates. All 24 numerical conditions pass; among the 790 reference frames,
no new wrong frame, hidden alarm or lost correct position occurs. The earlier short-window NFHS 130/1/14 control
is preserved separately from this same-context comparison.

Twenty-one distinct runner/renderer test methods have passed, using focused
reruns for affected corrections. The initial fixture/transport failures, native
timestamp zero-origin assumption failure, and protected-border chroma-bleed
failure remain recorded. Black-pixel requirements were preserved when correcting
the protected canvas. No full suite was repeated. NFHS packet inspection used
no pixel decoding: P001/P002 container origins are 40 ms, P003 zero, with actual
container PTS retained beside the existing clip-relative reference clock.

Independent result audit passed 42,844 checks on its first result-audit attempt.
It independently rebuilt all 3,975 geometric decisions without the producer
selector and all 790 reference outcomes/distance errors, checked protected
positions and full missing intervals, and reconstructed every added component
from fourteen original caches (22,307,800 compressed bytes). All 24 gates agree.
Its earlier inspection helper's missing-field error remains separate evidence.
The audit is at `data/outputs/t/continuous_gap_audit_2026-10-20/audit_01.json`.

No model inference, fit, checkpoint load, threshold search or source-pixel decode
occurred during selection/scoring. Five new review renders completed in 676.688
seconds with no failed render attempt. Every encoded frame's native timestamp,
duration, paired pixels and frame/panel keys passed verification: 4,200 timeline
slots, 225 protected black pairs, eight segment finals and five actual-final holds.
Independent media audit passed 12,832 checks and rehashed 54 unique delivery
bindings (246,740,339 bytes) without repeating source or output-video decoding.
Its receipt is `data/outputs/t/continuous_gap_audit_2026-10-20/media_audit_01.json`.
AI inspection covered all fourteen encoded additions and all eight segment
finals, plus five original SAC neighbors and four encoded P003 neighbors.
P001 19/91 and P003 333/334 remain visually uncertain; no label was invented.
This is bounded image inspection, not manual continuous review of all 4,200 slots.
Ryan's visual acceptance remains pending.
The earlier bounded review remains accepted, the three older motion reviews
remain pending, and no holdout or ball-phase gate is promoted.

## Earlier increment: completed fixed temporal gap selection — numerical pass; later visual approval recorded

Ryan's “Ok awesome move forward chat” approved one frozen rule on all 790
existing frames in twelve independent consecutive windows. The
[scope](../../configs/ball_tracking/selections/nba_temporal_gap_selection_v0_1.json)
binds the original candidate report, manifests, prospective design, implementation
and tests. Native `1/90000` PTS/PNG joins were verified without image decoding.
All choices were saved before scoring, and all original outcomes/errors were
independently recreated against the existing producer records.

The sole run completed in 0.391 seconds with no producer failure: DET matches
207→209/237, missing 22→20; NFHS matches 130→131/145, missing 14→13; SAC unchanged.
Only DET 11437, DET 11438 and P001 208 changed, all missing→matched. Wrong
outputs, hidden alarms and the included 120/120 easy controls are unchanged.
Sixteen fixed numeric conditions pass. No new inference, fit, checkpoint load,
heatmap read, pixel decode or threshold sweep occurred in selection/scoring.

Thirteen distinct focused tests (eight selector, five renderer) passed on their
first commands, including actual
component/score producer transport, label separation, inclusive time/spatial
boundaries, all-or-none gaps, failure preservation and review-record transport.
The deliberate failure fixture is a test, not an actual experiment failure.
No full suite was repeated. Independent audit passed 165,219 checks in 0.281
seconds on its first attempt: all 790 source/label joins and decisions, all
1,580 before/after scores, twenty maximal gaps, missing intervals and sixteen
conditions. It confirms all 597 original emitted points are unchanged and only
three correct saved candidates were added. There was no audit or producer retry.
All three videos completed on their first attempts: SAC 300 frames/13 seconds,
DET 340/14.333333 seconds and NFHS 150/31 seconds. Every source key, native PTS,
encoded duration, source PNG/RGB identity and paired image passed verification,
with twelve actual encoded window-final images. Rendering and verification
took 306.063 seconds in total, separately from selector/audit runtimes. AI
inspection covers all three encoded changed frames and twelve encoded finals,
not manual continuous review of every frame. It retains known P001/P002 missing
finals and the existing DET offset. The original artifacts recorded human review
as pending. Ryan subsequently explicitly approved the three delivered videos;
the [later visual review](../../configs/ball_tracking/reviews/nba_temporal_gap_selection_visual_review_v0_1.json)
closes that gate for this bounded increment. Approval recording verified the
bound video/manifest/verification/completion files; no scientific execution or
tests were repeated. Individual frame viewing or playback telemetry is not claimed.
The [appended result](../nba_temporal_gap_selection_experiment.md#completed-single-run-result)
and [compact result](../../configs/ball_tracking/reviews/nba_temporal_gap_selection_result_v0_1.json)
record this small improvement without baseline replacement or phase acceptance.

## Earlier increment (historical): completed candidate-preservation experiment

The [frozen design and appended result](../nba_candidate_preservation_experiment.md)
record one 22.094-second run across 790 frames, 1,580 means and 4,668 contributor
planes. It read 1,580 caches (2,519,893,616 compressed bytes) and six original
NFHS mean bundles (79,271,884 bytes). All original means, candidates, selections
and scores were preserved. No model, fit, media decode or prediction change ran.

Seven distinct focused tests pass: the initial command passed six and failed one
fixture missing `game_id`; only that corrected case was rerun and passed. The
old fixture/log are preserved; production source stayed unchanged and actual
metadata validation passed. No full-suite rerun occurred.

Independent audit passed 181,673 checks in 4.423944 seconds on its first attempt.
All 790 rows, 1,580 arm evaluations/cache sidecars and aggregate decisions were
checked. Numerical coverage was 141 unique frame-arm rows, including all 34
availability gains, all 24 newly nonempty hidden cases, 20 prior-anchor arms and
72 endpoint/midpoint arms; these reasons overlap. It read 325 cache bodies
(518,372,749 bytes), reconstructed 373 contributor planes and compared 26 old
NFHS means after loading six bundles/150 stored planes. Ordinary unsampled
cases were not numerically reconstructed a second time. No audit or producer
retry was needed.

The retained baseline gains nine of 45 unavailable DET/NFHS frames; 36 remain
unavailable. Non-anchor gains in both domains pass the minimal usefulness screen,
while 51 extra ambiguous development frames and five new DET hidden nonempty
frames constrain the benefit. The screen supports one future fixed selector
test only; no selector, checkpoint or phase is accepted. Prior failures, human
reviews and protected evidence remain unchanged.

## Earlier increment (historical): completed 37-frame regression diagnostic

Ryan explicitly said: “Ok move forward chat. Run the 37-frame diagnostic.” The
[bound scope](../../configs/ball_tracking/selections/nba_adaptation_regression_diagnostic_v0_1.json)
covers 37 unique source frames and 74 old/new means using original complete
cached contributor contexts. One actual producer attempt completed in 2.375
seconds with no producer failure, reproducing all original means, candidates,
selections and scores. It read 94 triplet caches (149,913,392 compressed bytes)
and three original NFHS mean bundles (39,639,143 bytes); 75 stored bundle planes
were loaded and only 22 selected old NFHS planes measured. Maximum rolling
triplet arrays occupied 5,308,416 bytes, retained anchor planes 11,796,480 bytes
and one NFHS bundle 14,745,600 bytes. These are not total process-RAM readings.

Eight focused tests passed on the first command in 3.486 seconds. Independent
audit fully recomputed all 74 means, contributor metrics, components, selections
and scores, checked all source joins and 94 cache bodies, and verified 22 old
NFHS planes plus 20 exported anchor planes. It passed 20,962 checks in 1.630051
seconds. Its first helper omitted `in_source_bounds` from independent component
records and stopped after 1,128 checks; the failed attempt and correction are
preserved. The producer and diagnostic output were not rerun or modified.

The [results record](../nba_adaptation_regression_diagnostic_results.md) separates
a DET component-ranking loss, a marginal centroid-boundary loss and four NFHS
averaging/response losses. All four recoveries cross the same mean threshold.
No model was loaded, no inference or training ran, no source PNG/video was
decoded, and no labels, predictions, thresholds or scores changed. Old NFHS
caches retain their historical frame/model/window provenance limitation without
invented captured PNG/PTS bindings. The failed adaptation screen, retained
baseline and completed video review remain unchanged.

A subsequent cached candidate-preservation experiment is proposed only. Its
790-frame count is the existing SAC 300 + DET 340 + NFHS 150 comparison; the 120
easy NBA controls are included subsets. No experiment, threshold/temporal rule
change, fit or new inference followed this diagnostic.

## Earlier NBA continuation review: user-reported completion

Ryan said: “Ok I reviewed these chat. What’s the next step?” The
[later review record](../../configs/ball_tracking/reviews/nba_wasb_adaptation_visual_review_v0_1.json)
covers the three inline embeds delivered in chat: the two complete NBA comparisons
and the verified 31-second compilation containing all six NFHS comparison windows.
The statement records review completion without playback telemetry or an explicit
quality endorsement. The original generated `human_review: pending` records remain
unchanged as publication-time evidence. The four failed numerical conditions,
retained expanded baseline and earlier three pending motion reviews are unchanged.
No new fit or threshold tuning is authorized by the next-step question.
The next saved-output diagnosis is planned but has not run: 37 unique context
frames around six lost matches and four recoveries, with 74 old/new means using
their original complete cached contexts. This review/status update does not
repeat the scientific run or its tests.

## Approved NBA continuation: fixed numerical screen failed

The [approved experiment](../nba_wasb_adaptation_plan.md) binds the exact inputs,
recipe, comparison and numerical screen before execution. Independent preflight
verified 33 file bindings and the 450-frame mixed pool. Eight focused trainer
tests passed in 2.102 seconds, covering actual approved metadata, native PNG
transport, 16/17 ms cadence, masks/role exclusions, fresh optimizer and frozen
BatchNorm, immutable final publication and altered-approval rejection. No full
suite was repeated. Nine distinct comparison checks also passed: eight in the
first command, then the repeated decoder check and one new actual-calibration
producer check. They exercise exact record transport, scoring/gates, cache
recovery and complete paired video transport. There are 17 distinct focused
checks for this increment; synthetic failures are expected recovery-test cases,
not failed scientific calls.

The first independent preflight helper incorrectly required all NFHS segment
purposes to be `training`. Three explicitly authorized pilot segments correctly
retain `protocol_adjudication`. The helper was corrected to compare each source
purpose to its frozen segment authority, allowing both authorized purposes;
the second attempt passed without changing labels, configs or scientific outputs.
Its passed receipt preserves the first attempt's history; the original traceback
is in tool output, with no separate failed preflight receipt.

One real fit completed all 200 updates without retry in 50.3275655 seconds.
Final checkpoint SHA-256 is
`da44ce06cdf7b3bf97468b5780f0f02e435807299cf3d771494c367d9010da26`.
The 400 samples use 269 NBA and 131 NFHS triplets from 424 usable triplets.
Twenty-four triplets were unsampled; 440 input frames were exposed. Ten frames
have no input exposure: eight masked frames, P001/375 and SAC/1059. No claim
that all 450 pool frames were trained is made.

Independent training audit passed 3,469 checks: all 428 checkpoint tensors equal
the update-200 state, all 213 BatchNorm buffers match initialization, 176 trainable
tensors changed, and all 176 optimizer states reached step 200. The first audit
completed 2,821 metadata checks before the system Python failed to import PyTorch.
The same helper then passed under `.venv`; both attempts remain preserved and no
fit was repeated. Peak GPU allocation was 2,004,807,168 bytes; cached CPU tensors
occupied 3,001,025,784 bytes, not a total process-memory measurement.

The fixed comparison uses strict `>0.3` and inclusive ten-source-pixel matching.
SAC training fit changes from 218/5/47 to 265/5/0 matched/wrong/missing among 270
eligible centers. DET development changes from 207/8/22 to 206/10/21 among 237;
hidden alarms fall from 13 to nine of 69 probable-hidden references. NFHS changes
from 130/1/14 to 129/1/15 among 145, with zero of five hidden alarms. Both easy
NBA controls remain 60/60. Four of nine predeclared conditions fail: DET matches
and wrong locations, NFHS matches and misses. The expanded baseline is retained.

The single comparison/media execution completed in 1,425.922 seconds with
2,836 inference calls and no failed or uncertain calls. Eight videos contain
2,852 source frames, each once, with an extra second on each final frame's
duration. Producing decode checks verified every frame/PTS key and paired overlay
within the frozen pixel tolerance, plus actual finals and durations.

Independent comparison audit passed 48,264 checks on its first attempt in
15.0375274 seconds. It independently derived all 790 scores and checked all
2,852 source joins, 2,836 cache/start records and unchanged 33 frozen inputs.
Numeric reconstruction covered 56 rows from 72 cache bodies (115,173,064
compressed bytes); the remaining means/components were not independently
recomputed. Eight review bindings, manifests, probes and every-frame decode
receipts were checked without another media decode. It confirmed the failed
screen. Model-output human review was pending at publication; the later completion
record above supersedes that current status without rewriting generated evidence.

AI inspected 56 sampled source frames and all eight actual encoded finals;
this is not complete visual inspection of all video frames. The six NFHS videos
were stream-copied into a 31-second, 150-frame phone compilation. Initial encoded
packet-byte equality failed only at each clip's first packet; all decoded RGB
pixels, timestamps and durations then matched exactly. The original compilation
was retained without re-encoding, new inference or a fit. A subsequent helper
inspection stopped at an exclusive-create guard before FFmpeg. Both routine
packaging-check events are preserved in the delivery failure receipt.

The [current result report](../nba_wasb_adaptation_results.md)
links immutable training, scores, exposure and audit evidence. Old checkpoints,
labels, scores, protected holdouts and the three pending motion-video reviews
are unchanged. No second fit or tuning followed the failed screen.

## Earlier increment (historical): approved saved-heatmap inspection completed

Ryan approved the inspection with “Let’s do it. Move forward chat”. The
[recorded scope](../../configs/ball_tracking/selections/nba_hard_example_heatmap_inspection_v0_1.json)
fixed 640 rows and descriptive comparisons before heatmap reads. One actual inspection completed in 19.937
seconds. It read 652 existing NPZ caches (1,037,888,584 compressed bytes), rebuilt
all 640 original float32 means in their original addition order, and required
exact mean hashes and candidate/selection agreement. The peak rolling cache
held three triplet arrays, 5,308,416 bytes; this is not a total process-memory
measurement. There were no model calls, checkpoint loads, training runs, source
image/video decodes, label changes or prediction updates.

Seven new focused tests passed. The first command passed 15 checks because an
imported existing test class contributed eight extra checks; the corrected
import yielded the intended seven passing new checks. Both logs remain recorded,
with no failed tests or scientific runs. These are distinct from the earlier
publication/scorer validations below; the full suite was not repeated.
The independent [actual-output audit](../../data/outputs/ball_tracking/nba/hard_example_heatmap_inspection_v0_1/independent_audit_01/audit.json)
passed on its first attempt in 3.297 seconds. All 640 rows/summaries and 652 cache
metadata records were checked structurally. Independent numeric reconstruction
covered 126 rows (all 82 failures plus 44 context rows) from 237 caches containing
377,272,217 compressed bytes. The other 514 rows were not independently
recomputed numerically; the producing run verified exact original mean hashes
and candidate/selection agreement across all 640.

The [preservation receipt](../../data/outputs/ball_tracking/nba/hard_example_heatmap_inspection_v0_1/preservation.json)
confirms all nine authority/source bindings and five tracked prior code/result
files are unchanged. Separate visual preparation made 12 cache reads
(19,097,646 bytes) and four PNG decode events across two unique source images.
Both final figures were visually checked. The [visual receipt](../../data/outputs/ball_tracking/nba/hard_example_heatmap_inspection_v0_1/visuals/visual_check.json)
retains the initial clipped colorbar and corrected second layout; the diagnostic
itself performed no image decoding.

The frozen report retains all 82 primary failures and descriptive context:
305 matched difficult frames, 120 pilot controls, 86 hidden references and 47
other unsupported references. Missing local responses have median 0.117843 and
maximum 0.293772. Eleven misses have an above-threshold original contributor
but no local support in the mean; 58 have none. Global peaks match on only
21/69 missing frames. Eleven of 13 wrong components have active support inside
the reference disk, but component peaks match only three; six previously
matched difficult frames have nonmatching peaks. These are descriptive geometric
measurements, not changed selections or new scores. Hidden/unsupported rows
retain null local geometry. Sigmoid responses are not calibrated probabilities.

The [result report](../nba_hard_example_heatmap_inspection_results.md) and
[compact result](../../configs/ball_tracking/reviews/nba_hard_example_heatmap_inspection_result_v0_1.json)
retain original scores, labels, caches and uncertainty. No threshold sweep,
fit or model-output promotion occurred. A bounded NBA adaptation/data proposal
using SAC plus eligible NFHS training examples is recommended; no exact new
training scope or fit is approved. Game roles, holdouts, NFHS gates and the three
pending motion human reviews are unchanged.

## Earlier increment (historical): difficult-scene label acceptance, reference publication and saved-output scoring

Ryan accepted all four complete prepared label packages without corrections.
The [acceptance record](../../configs/ball_tracking/reviews/nba_hard_example_label_acceptance_v0_1.json)
binds that later human event and retains AI authorship, prior prediction exposure,
uncertainty and the original proposal/media bytes. Publication produced a
separate 520-frame accepted reference: 387 centers and 133 null geometries.
The [prior-artifact preservation receipt](../../data/outputs/ball_tracking/nba/hard_example_reference_v0_1/validation/acceptance_prior_preservation_01.json)
confirms all 29 scoped prior bindings are unchanged.

Thirty distinct focused checks passed in this increment: 21 publication-related
checks (six new, six existing reviewed-reference and nine asset checks), plus
nine saved-output scorer checks. The initial scorer run had seven fixture
setup errors across nine tests; that attempt remains recorded, and corrected
fixtures passed the affected checks. The prior 26 tests below belong to label
preparation; these are separate validation scopes, not one combined suite.
The full suite was not repeated. Independent review of the scorer found no
actionable issues. The independent [actual-report audit](../../data/outputs/ball_tracking/nba/hard_example_reference_v0_1/diagnostics/saved_score_v0_1/independent_audit_01/audit.json)
passed on its first attempt with zero issues: 20 bound JSON/source files, all
2,702 producer inventory records and 640 emitted scored rows. Summaries and
native-time intervals agree; 112 pilot interiors and eight changed-context
edges were independently checked. A separate [original-pilot preservation
check](../../data/outputs/ball_tracking/nba/hard_example_reference_v0_1/validation/original_short_pilot_preservation_01.json)
confirms the original tracked result and five generated score JSON files remain
byte-identical.

The saved-only diagnostic completed in 1.094 seconds with zero inference calls,
training runs, image/video decodes or heatmap reaggregations. It verified the
complete saved observation/component inventory and scored the approved 520
new frames plus 120 separate pilot controls. At the unchanged inclusive
10-source-pixel rule, new eligible centers yielded 305 matches, 13 wrong
locations and 69 misses out of 387. The 13 wrong distances exceed ten pixels
and reach 14.755 pixels; uncertainty is reported separately without changing
matches. There were 13 alarms among 86 hidden references; 47 other frames stayed
unscored. No localization geometry was fabricated for the 133 null centers.

All 82 eligible failures lack an alternative saved strict `>0.3` component
within ten pixels. Existing-candidate reranking cannot recover them. The longer
pilot controls remain 120/120, explicitly retaining their eight context-edge
changes; the original short-context score was neither recomputed nor replaced.
See the [result report](../nba_hard_example_reference_results.md) and
[compact result record](../../configs/ball_tracking/reviews/nba_hard_example_saved_diagnostic_result_v0_1.json).

This failure-selected, correlated human-accepted AI reference is a development
diagnostic, not an independent NBA benchmark. Slowed label-overlay appearance
is not model improvement. No fitting or threshold change is approved by this
result. Game roles, protected holdouts, the NFHS finish line and three pending
motion human reviews remain unchanged.

## Earlier preparation (historical): NBA hard-example labels awaiting acceptance

Ryan approved the exact 520-frame scope with “Ok move forward”. The separate
[approval](../../configs/ball_tracking/reviews/nba_hard_example_reference_approval_v0_1.json)
binds the unchanged original proposal. Four [complete review packages](../nba_hard_example_reference_review.md)
now contain 387 proposed centers and 133 null centers: SAC recovery 90/120,
SAC held ball 120/120, DET gap 65/120 and DET rim 112/160. Visibility totals are
355 partially visible, 56 fully visible, 86 not visible and 23 indeterminate.
Twenty-four partially visible frames still lack a defensible center. These
counts describe AI proposals, not accepted truth or prediction accuracy.

All 520 original native frames were visually inspected, including each actual
final frame. Labels use source evidence, not saved prediction coordinates;
prior model exposure and source/model-selected windows are disclosed. Drafts,
visual corrections, helper import failures and the targeted review agent's
capacity error remain in the [bound preparation record](../../configs/ball_tracking/reviews/nba_hard_example_reference_preparation_v0_1.json).
The targeted twelve-frame independent AI check retained the proposed geometry
and uncertainty; it does not replace Ryan's review.

The existing renderer was reused. Hard-example asset verification checks the
approved scope and native source manifest. Twenty-six focused checks passed:
nine hard-example asset, twelve NBA annotation and five assisted-review tests.
The full suite was not repeated. Independent media checks verified all 520
source/render PNG pairs, all four MP4 timelines and 544 encoded frames including
final holds. Actual finals 1059, 1359, 11119 and 11579 passed visual inspection.
Playback is six source frames per second with native source timestamps retained
and a one-second final hold; total review duration is 90.666667 seconds.

No accepted new reference, scoring, inference, training or full-game decode was
produced. Human acceptance remains pending. The earlier pilot result, game
roles, protected holdouts, NFHS finish line and negative motion result remain
unchanged; three motion-study human reviews remain pending. Passed transport
checks do not establish label accuracy, overall NBA accuracy or a phase pass.

## Longer NBA review completion and proposed reference diagnostic

Ryan reported: “Ok reviewed. What’s the next step” after both complete longer
videos were delivered in chat for phone viewing. The separate
[visual-review record](../../configs/ball_tracking/reviews/nba_wasb_action_observation_visual_review_v0_1.json)
binds that later event; it claims neither playback telemetry nor explicit
acceptance of prediction quality. The original pending-era result record and
media remain unchanged. The reported distractor/gap failures remain unresolved.
Prior short-pilot acceptance and three pending motion reviews are unchanged.

The [next reference proposal](../nba_hard_example_reference_plan.md) is
design-only: 520 new AI-proposed labels over four failure-focused source ranges,
followed by Ryan's reference-overlay acceptance and scoring of saved frozen
observations. At most 640 frames would be scored, including 120 existing pilot
references used as separate longer-context easy controls. The original pilot
score stays unchanged. Uncertainty and AI origin remain explicit; source/model
selection prevents an independent or representative accuracy claim. No new
labels, scoring, inference, training, threshold or motion experiment was run or
authorized by the review-completion message.

## 2026-10-19: longer NBA action observation completed and audited

Ryan approved the exact longer plan: “I approve. Move forward chat”. The
[approval record](../../configs/ball_tracking/reviews/nba_wasb_action_observation_approval_v0_1.json)
binds the preserved proposal's original bytes. The implementation was committed
as `4b67d0850897d539ab2994afc6349c0b6af11667` after 23 distinct focused checks:
seven input, twelve observation and four review checks. This count describes
distinct checks, not total test invocations. The full suite was not repeated.

The checks cover actual synthetic native-PTS extraction/render transport,
producer-derived old cache imports, exact streamed float32 aggregation,
unchanged pilot interiors, threshold/tie semantics, scope rejection, preserved
failed calls and resume, cut boundaries and withheld frames, final-frame
transport, and read-only prepared-input loading. Same-state/same-kind segments
retain separate intervals across declared boundaries. Prepared-input loading
uses small source/manifest/receipt checks without redundantly decoding every
PNG; actual model/render consumption still verifies its inputs.

The observation test history preserves the initial system-Python import failure
(NumPy unavailable) and the subsequent six fixture setup errors caused by a
reference-publication path outside `data/outputs`. The interpreter and fixture
path were corrected; affected/new checks then passed. The first integration
check also rejected a full-window approval comparison; the implementation now
compares the exact approved field projection. No scientific model calls occurred
in those failed checks. Logs remain under ignored
`data/outputs/t/nba_action_implementation_2026-10-19/`.

The initial six input checks preceded real preparation; seven checks passed
after recovery and pre-decode source-stat safeguards were added. The running
preparation process had already loaded the initial input helper, SHA-256
`ee20bea139aa639806ab79739ec7572066433a04fd8f8a7608e078531c3c2842`.
That exact snapshot and the [provenance explanation](../../data/outputs/ball_tracking/nba/wasb_action_observation_v0_1/diagnostics/helper_loaded_provenance_01/provenance.json)
are preserved. A later extraction-start receipt hashes the then-current disk
file, not the already loaded code. No receipt was rewritten. Fresh extraction
commands, native-PTS/RGB checks and successful output construction were
unchanged; preparation completed with exit 0 in 162.884 seconds without a
repeat decode to resolve that bookkeeping distinction. Inference/rendering
used the committed `4b67d08` source. Preparation also used an earlier runner
version, retained in its start receipt; later runner changes concerned
post-preparation/inference handling. A DET inspection-helper import failure
occurred before image reads and remains recorded; it was not a scientific
model-call failure.

The approved real run completed with exit 0 in 1,238.416 seconds of process
wall time (1,237.234 seconds inside the runner). It made 2,582 new calls and
imported 116 original triplets, with zero failed or unresolved model calls.
SAC has 1,310 observed/161 missing/0 withheld; DET has 1,070 observed/161
missing/0 withheld. All 112 pilot interior observations are identical, and
eight pilot-edge observations have longer context. The original short-window
120/120 score was not recomputed. These longer counts describe availability,
not accuracy.

Both new videos passed every-frame native-PTS, frame-key and overlay-pixel
verification, including final frames 2010 and 11898 with an additional 90,000-
tick hold. Maximum overlay RGB mean absolute errors were 3.323705 for SAC and
3.543898 for DET, below the declared limit of 8. The independent
[saved-output audit](../../data/outputs/ball_tracking/nba/wasb_action_observation_v0_1/diagnostics/independent_audit_01/audit.json)
passed on its first attempt in 27.172 seconds: 687,915 structural/numerical
checks, 8,157 file bindings and zero issues. It reconstructed 2,702 aligned
float32 means from all 2,698 actual NPZ caches, all 2,711 final components and
selected points, and verified frame/PTS joins, availability intervals, original
attempt identities and 112/8 pilot-context preservation. It checked bound
renderer receipts and stored ffprobe records without another media decode,
model call, annotation score or old experiment repeat.

Inherited adapter metadata still describes its unused default `>0.5`
components. The audited final path recomputes strict `>0.3` components after
averaging; both facts are retained without rewriting provenance. AI inspection
covered all 2,702 frames and both actual final frames, preserving 14 SAC and
seven DET cues. It reports distractors and visible-ball gaps. The
[compact result record](../../configs/ball_tracking/reviews/nba_wasb_action_observation_result_v0_1.json)
binds the completed evidence; the [result and review report](../nba_wasb_action_observation_results.md)
links both videos and their seekable cues.
Original pilot acceptance, consumed resources, failed attempts, game roles,
holdouts and the NFHS finish line remain preserved; new longer-video human
reviews and the motion study's three new human reviews remain pending.

## 2026-10-19: native pilot model outputs accepted; broader scope prepared

Ryan reported review of both videos and accepted the predictions without
corrections. A separate [acceptance record](../../configs/ball_tracking/reviews/nba_wasb_native_pilot_visual_review_v0_1.json)
binds the original result, configuration, observations and both presented
complete review packages, including final frames 719 and 10847. This is a later
human event; no playback telemetry is claimed. Original pending-era result and
completion records, media, page and reference-label acceptance remain unchanged.
A separate accepted-status page links the same videos.

The [longer observation plan](../nba_wasb_action_observation_plan.md) and
[non-runnable proposal](../../configs/ball_tracking/selections/nba_wasb_action_observation_proposal_v0_1.json)
define two existing action cores with 2,702 source frames, at most 2,698 complete
triplets, 116 planned prior imports and at most 2,582 new calls. This is design
preparation, not implementation validation or executed science. No model calls,
raw-video decoding, labeling, scoring or tests ran during this increment. One
additional read-only cache-feasibility check repeated already audited
hash/metadata/array checks for all 116 saved NPZ records and found zero issues;
its duration was not measured. It did not rerun inference, media decoding or
the original scoring. The completed diagnostic and its consumed resources
remain as recorded below.

Longer context could change eight pilot-edge means while 112 interior means
should remain identical unless a newly declared scene boundary changes their
input context; the original accepted 120/120 score is preserved.
The proposed broader scope awaits approval to implement, validate and execute
once. It adds no training, new-label benchmark or phase acceptance. Existing
roles, protected holdouts, completed reviews and the negative motion result
remain unchanged; the motion study's three new human reviews remain pending.

## 2026-10-19: approved NBA native-cadence diagnostic completed

Ryan approved the exact prepared recipe and its 16–17 ms native input spacing.
One run completed in 49.766 seconds: 116 model-call starts, 116 unique completed
triplets, zero failures and no unresolved starts. The expanded checkpoint and
strict `>0.3` selection remained frozen. Each game scored 60 matches, zero wrong
and zero missing at the inclusive ten-source-pixel radius. Mean raw distances
are 2.779011 pixels (SAC–MEM) and 2.894105 (SAS–DET); all endpoints are scored.
No new training, original recording decode, holdout access or old experiment
repeat occurred. Original references and their separate acceptance are retained.

Both new complete review videos are prepared with actual final frames 719 and
10847. Independent saved-output/media verification passed on its first attempt
in 18.094 seconds, with 7,015 checks, 494 file bindings and zero issues. It
reconstructed 120 mean heatmaps from all 116 cached triplets, all 127 final
components and every selected point, then confirmed all 120 scoring outcomes
without importing the project's scoring functions or making new model calls.
Both videos fully decoded to 66 frames at 6 fps; all 132 frames, including the
six extra final-frame copies per video, matched the overlays within lossy
tolerance. Maximum whole-image RGB mean absolute differences were 2.2586 (SAC)
and 2.3794 (DET), below 4. Original metadata was retained with a separate note
explaining adapter-default `>0.5` versus the independently verified final `>0.3`.

The assistant inspected all 120 overlays through both final frames and found
no obvious switch or dropout. Both human reviews remain pending; numerical and
AI checks do not supply Ryan's acceptance. No source or test code changed, and
no earlier suite or experiment was repeated. See the [result report](../nba_wasb_native_pilot_diagnostic_results.md)
and [compact bound evidence](../../configs/ball_tracking/reviews/nba_wasb_native_pilot_diagnostic_result_v0_1.json).
There are no hidden negatives or independent test games. The result does not
compare cadences, promote a tracking method or complete the ball phase.
The negative motion result and its three pending new human reviews stand.

## 2026-10-18: accepted NBA reference and prepared native-cadence diagnostic

Ryan accepted the two presented AI label packages. Six new reference-loader
checks passed on their first run (1.341 s, no skips), using actual draft/review
producers and explicitly synthetic encoder bytes. One separate publication
verified all 120 native PNGs and retained exact source-frame/PTS mappings, AI
origin and placement uncertainty. A root comparison of the actual published
record against its bound original drafts/proposals also passed all 120 rows.
Original proposals retain historical pending status; the later acceptance is
separate. No original game video was read or decoded for this increment.

The new NBA diagnostic runner's first seven focused checks passed (2.803 s).
They exercise actual producer-shaped records, fake model outputs, scoring,
strict-threshold selection, recovery and an actual synthetic MP4 final hold.
That first command's output was not redirected and its exact then-current
source hash was not recorded; its tool-output transcription is explicitly
labeled as such. It does not certify subsequent changes.

Independent review identified ambiguous reference/model authorship fields in
the new observations record. These were separated, with new model-output
review explicitly pending. The final implementation also binds the aggregation
and native-image verifier code, records actual adapter provenance, and uses an
OS-held lock that releases when its process exits. Six affected/new checks
then passed in 1.956 s, covering these paths, overlapping triplets, authorization
ordering and cached recovery. Unchanged threshold/scoring and encoded-tail
checks were not repeated. Two independent read-only reviews found no remaining
material issue; actual NBA model behavior remains untested.

The updated actual read-only plan passed with 120 frames and 116 distinct
triplets, without model construction, image decoding or diagnostic output
creation. Both plan versions and test executions remain recorded. See the
[bound preparation record](../../configs/ball_tracking/reviews/nba_wasb_native_pilot_preparation_v0_1.json)
and [exact proposed recipe](../nba_wasb_native_pilot_diagnostic.md). Scientific
execution awaits approval; no real model calls, new fit, old experiment/full
suite repeat, holdout access or phase promotion occurred.

## 2026-10-18: assistant-first NBA proposals and compact review delivery

The new separate review renderer passed five focused checks on its first run
(0.525 s, no skips). The checks cover exact inventory/evidence bindings,
rejection of changed provenance and human-acceptance/interpolation claims,
point/missingness rendering, and an actual synthetic H264 encode. The encoded
fixture contains three source frames plus six final-hold frames; a tail RGB
decode matches the final overlay within lossy tolerance. No earlier suite or
scientific experiment was repeated. The exact code/test hashes and output are
preserved in the ignored `assisted_review_tool_validation.json` receipt.

Both actual AI proposals passed the existing FrameAnnotation semantics and
new consumer validation. Detroit's real render completed once in 11.343 s;
Sacramento's completed once in 11.797 s, with empty FFmpeg warning/error logs.
An independent audit checked all 120 actual source frame/PTS/PNG/RGB mappings,
rendered PNG hashes, marker coordinates, copied proposals and receipt artifacts.
Both videos report 1280x720, 66 encoded frames, 11 seconds and 6 fps. One decoded
tail image per new video matches the final source overlay: whole-image RGB MAE
2.0122 (DET) and 1.9802 (SAC), below the declared limit of 4. These are transport
and rendering checks, not a label-accuracy metric or full encoded-video decode.

The original source recordings were not read again. Both native editor drafts
retain their exact preparation hashes, revision zero and 60 unlabeled rows.
Root inspected both first/final overlays and selected contact/blur frames;
this remains an AI sanity check, not Ryan's visual acceptance. See the
[preparation record](../../configs/ball_tracking/reviews/nba_assisted_annotation_pilot_v0_1.json)
and [current workflow](../nba_native_annotation_guide.md). The 120 first-pass
proposals and their 13 priority frames await human review. No detector inference,
training, evaluation, protected holdout access or phase promotion occurred.

## 2026-10-18: NBA native-timestamp annotation preparation and editor

The separate NBA path passed 12 schema/save checks (0.436 s), three actual
synthetic H264/FFmpeg extraction checks (0.161 s), and 12 current HTTP/editor
checks (1.195 s). An earlier 11-check editor run passed in 1.481 s before the
session provenance guard was added; do not apply that earlier run to the later
guard. Synthetic fixtures use actual producer-shaped native PTS records and
real emitted FFmpeg/HTTP records. No frozen NFHS module changed and no full
suite or earlier scientific experiment was rerun.

Both approved 60-frame extractions completed once, with exact source PTS and
RGB PNG equality, empty FFmpeg logs and unchanged original source size/mtime.
A separate independent earlier-seek verification passed for all 120 frames.
Its two original-source reads were explicitly bounded to 13 seconds each;
FFmpeg elapsed time totaled 4.656 seconds. No full-source hash or decode pass,
old holdout access, model call, fit or evaluation occurred.

Root browser QA saved and reloaded one synthetic label and verified that the
next frame stayed blank. The unsaved-change confirmation appeared, followed by
browser-control timeouts; those tooling failures and the unobserved cancellation
result remain recorded. A fresh real workspace loaded both pilots through their
actual last frames, with every real annotation still unlabeled and no annotator
identity invented. The synthetic server was stopped deliberately. Root and two
independent code reviews found no open material issue. See the [guide and bound
preparation record](../nba_native_annotation_guide.md) for files, limitations and
next human annotation/review work.

## 2026-10-08: fixed motion comparison completed and audited without scientific retry

Implementation commit `915ba13c2910efa7f875cb251b7bc049790d1df3` adds a frozen
candidate-only selector, same-context paired evaluator, synchronized renderer
and resumable evidence publication. The consolidated 19 focused checks passed
in 2.568 seconds before the final renderer correction to accept the producer's
valid out-of-source candidate coordinates. Four affected renderer checks then
passed in 0.764 seconds. Do not imply that the earlier consolidated run tested
that later correction. No full suite was run.

Focused validation preserves the initial wrong-module import attempt and TEMP
sandbox fixture/cleanup failures, followed by successful execution outside the
sandbox. The independent resume regression demonstrates that a synthetic render
failure preserves its failed invocation and reuses completed selections and
scores. These were validation/tooling attempts, not scientific failures.

One actual invocation completed in 175.5554 seconds with zero model calls,
without scientific retry. Selection took 0.2004 seconds; selection and scoring
together took 0.3083 seconds. All selections were saved before labels opened.
Both arms retain identical choices on all 150 scoring frames, giving 131 matches,
one wrong-present output, 13 missing and zero hidden alarms. Training and withheld
frames were excluded. The older 130/1/14 short-window result remains unchanged;
P002/49 is a shared longer-context match at 4.530709637 pixels, not a motion gain.

The independent audit in
`data/outputs/ball_tracking/wasb/wasb_motion_selection_v0_1/diagnostics/independent_saved_output_audit_01/`
checks all 1,498 timeline rows against hash-bound original observations, all 300
arm/frame classifications against released labels, report statistics, paired
changes and pool/overall totals. It preserves 225 protected positions and all
294 originally empty visible frames. No selector, evaluator, model, tests or
media processing ran during that audit. `short_window_check.json` separately
verifies the original saved result and P002/49's former missing output.

The renderer verified all 1,498 video frames, final frames and 225 black protected
frame pairs. Motion leaves 969 observed / 304 missing / 225 withheld positions,
with 13 changes: three switches and ten abstentions. AI inspection notes for all
13 changes are preserved in `diagnostics/visual/p001_selection_notes.json`,
`p001_recovery_notes.json` and `p002_p003_notes.json`. The inspection-helper's
partial failure is retained in `p001_root_detail_manifest.json`; its routine
correction did not rerun scientific work. AI review finds visible-ball recovery
losses despite some apparent distractor suppression; this setting is not promoted.
P001/256 remains an unscored training-frame visual concern.

Human review of the three new comparison videos remains pending; prior completed
reviews are unchanged. No new labels, holdout release, operating point or phase
quality gate is established. See [comparison report](../ball_wasb_motion_selection.md).

## 2026-10-08: Ryan reviewed all three longer possession videos

Ryan confirmed "Ok what’s the next move. I reviewed the possessions". The review
record `wasb_expanded_development_observation_visual_review_v0_1.json` binds the
three exact video and render-receipt artifacts from the completed run. No new
frame-specific judgment, accuracy claim or phase acceptance is inferred. The
original creation-time pending receipts remain unchanged. This closeout changes
review metadata and documentation only; no test, model, score or video run was
repeated. The next motion-selection comparison is recommended, not executed.

## 2026-10-08: longer development observation completed without retry

Implementation commit `23fc90876458068ca422708bef92a35357bfa201` passed nine
focused tests in 1.808 seconds, covering source-band exclusion, cache producer/
consumer records, aligned means, missing/withheld semantics, resumability and
real synthetic H264 playback through its final frame. One check also consumed an
actual previous model cache without altering it. No full suite was run.

The actual metadata check confirmed 1,273 visible frames, 225 protected positions,
138 reused raw triplets and 1,123 new ones before runtime. One real invocation
completed in 212.761 seconds with exactly 1,123 model calls (17.832 inference
seconds), 263 MiB peak allocated/400 MiB reserved GPU memory, no retry and no fit.
Its three review videos decode all 1,498 frames and contain 225 black protected
source areas. AI endpoint review passed; human trajectory acceptance is pending.

An independent saved-output audit took 14.976 seconds and reconciled actual
records, lineage, exact-frame inventories and cache bindings. All 130 old
same-context means are identical; the 20 changed-context boundary means differ.
It emitted descriptive missing-run/jump cues without labels or rescoring.
Counts are 979 observed/294 missing/225 withheld, not accuracy estimates.
P001/223–224 remain missing despite extra context; P002/49 emits a new unscored
point. Original six-window results are preserved. Audit SHA-256:
`0d86a7a72d1767c5dfd7e92965edd5f6e6643c00b06ae6358967ca8f60e23cb2`.
See [longer observation report](../ball_wasb_development_observation.md).

## 2026-10-08: reviewed expanded-data fit and comparison completed

Ryan approved all three new label clips and continuation. The human review record
binds each clip, its exact corrected draft snapshot and reviewed annotation file.
Only review status/reviewer/timestamp changed; all frame labels remained unchanged.
The new versioned config composes six preserved annotation authorities into five
training blocks: 150 frames, 130 positive centers, 19 hidden negatives and one
masked ambiguous frame. P002's adjacent segments supply both crossing triplets.

Implementation commit `3928f7fee7f6e41eb3ffa05b0db062b176442e6e` passed 13 focused
trainer checks (1.887 seconds) and four evaluator checks (1.819 seconds), including
actual reviewed-data composition, exact sampling, original behavior, stale-review
and overlap rejection, saved comparison consumption and baseline preservation.
Independent static review confirmed bindings and unchanged training semantics.
No full-suite run occurred.

One uninterrupted expanded fit completed 200 updates in 24.3455 seconds. All
400 sample IDs, 200 loss rows and update-200 state agree. Its 428 final tensors
match the published checkpoint; 213 BN buffers equal the original checkpoint,
176 active parameter tensors changed with Adam step 200, and 39 unused branch
tensors remain unchanged. Peak allocated/reserved GPU memory was 1.87/2.32 GiB;
cached CPU tensors occupied 990,904,740 bytes. No training retry occurred.

Evaluation and the fixed cached threshold screen completed in 32.714 seconds;
primary rendering took 12.630 seconds. At 0.5, 120 matched/2 wrong/23 missing with
zero hidden alarms compares with prior 98/1/46. Paired records show 23 gains and
one loss, P002/48. Both primary errors remain outside ten pixels: P001/52 10.368px
and P003/164 10.972px. At already-declared 0.3, 130/1/14 with zero hidden alarms
retains all 120 primary matches and adds ten. This is a review candidate only.

An independent saved-record audit reconciled 144 threshold/window reports, 96
comparison binding rows, paired frame sets, 60 RF-control cells, point/identity/
render receipts and successful invocations. All six primary clips decode through
25 frames and their final frame. Selected diagnostic stills use only three source
frames and saved points. No baseline model rerun, rescoring audit, holdout access
or label revision occurred. New-output visual acceptance remains pending; the
new single fit is complete and its authorization consumed. See the expanded
results document for evidence paths and review material. Six separately labeled
0.3 candidate clips were subsequently rendered from the already-scored cached
points in 9.315 seconds. Point/control canonical signatures match the actual
saved reports; every video decodes all 25 frames and its final frame. This added
no inference, training, scoring or operating-point selection. Candidate review
remains pending; primary videos are unchanged.

## 2026-10-08: all 75 expansion labels saved and review playback prepared

Ryan completed all three new training windows. Schema and exact-frame checks
confirm 75 labeled rows with no unfinished or duplicate frames: 64 eligible
centers (four fully visible, 60 partially visible) and 11 hidden frames with null
geometry. Combined with the existing pilot data, this gives 130 eligible centers,
19 hidden frames and one masked ambiguous frame across 150 frames.

Ryan clarified that his camera-motion difficulty tags meant motion blur. Eight
tags were changed: P001/258–261 and 274; P002/347, 360 and 361. A correction record
binds the original completed snapshots and corrected files, with all geometry,
visibility, identity, eligibility, notes and review fields preserved. The old
three pilots and six released development sets contain no `camera_motion` tags.

Existing annotation renderers produced three full-resolution H264 clips at 5 fps,
75 native overlays, 75 zoom/status panels and three decoded final-frame images.
Each clip decoded exactly 25 frames through EOF. Source hashes and annotation
bindings matched; rendering took 12.069 seconds without changing labels or running
a model. The manifest is at
`data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/training_expansion_labels_v0_1/visual_review/manifest.json`.
These checks establish completeness and review delivery, not visual acceptance.
All three label sets remain drafts pending Ryan's review. No production code,
full-suite run, training fit or holdout access was involved.

## 2026-10-08: Ryan completed all six adapted-WASB video reviews

Ryan reported all six clips reviewed and authorized continuation, with bleacher-ball
and dark-uniform/referee-occlusion distractor observations. The record at
`configs/ball_tracking/reviews/wasb_basketball_adaptation_visual_review_v0_1.json`
binds the actual six videos to checkpoint `98912a271791` and preserves his exact
statement plus byte-identical copies of both attachments under the ignored trial
directory. P002/49 and P003/168 show yellow RF top-one marks and WASB missing;
the broader observations do not supply additional exact frame IDs or counts.
No new judgment on P003/164's center offset, changed annotation, operating point,
quality-gate acceptance or full-possession trajectory acceptance is inferred.
Original receipts and captions retain their creation-time pending review state.

## 2026-10-08: cached gap diagnosis and source-only training-data proposal

Saved-grid aggregation found that all 46 primary missing eligible frames have a
matching raw component at some already-completed setting; only 14 are selected
correctly somewhere in the grid. P001's split is 11 selected-recoverable and 28
raw-only. This label-assisted union is diagnostic, not an achievable policy.
A separate strongest-pixel calculation on the six cached adapted heatmaps gives
110 correct/35 wrong, with forced output on all five hidden frames; P001's fully
missed representative window has only two correct peaks. Existing transform
matrices match the producer metadata. No model inference, retraining, threshold
search or full-suite run occurred; existing scores and primary output are unchanged.

Source-only inspection considered seven candidate training windows (four sparse
frames each). Three selected previews contain P001/100–124, P001/250–274 and
P002/343–367, each encoded and decoded through all 25 frames. This is preparation,
not human label review. The two source-video hashes match their existing manifests.
Metadata checks show no overlap with old development/holdout windows and at least
25 intervening frames; P002 intentionally adjoins its old training pilot. No
holdout frames or annotation bodies were requested. Ryan subsequently approved
75 new frames and one fit after label review. The separate approval record binds
the original proposal and the three initial annotation drafts, each schema-valid
with exactly 25 unlabeled training-only rows. Initial draft hashes are provenance
for blank templates, not a ban on the authorized human annotation edits. New
coordinate/visibility labels and the controlled next fit are not yet done. See
the diagnosis/proposal and annotation guide; no production source code was changed.

The ignored annotation helper's one actual input check passed: all three drafts
loaded against their verified sources and all 75 approved frames decoded as
1920x1080 RGB images for the existing editor. No GUI opened and no draft bytes
changed. Its receipt is in the trial's `annotation_session_v0_1/check_only_receipt.json`.
The check used HEAD `1b35f067e51da554adc66adb8ebb172df358429d`; after local integration,
only the launch binding's expected HEAD is refreshed. The successful check is
preserved without repeating its decoding or implying that human labeling occurred.

## 2026-10-08: approved pilot adaptation, paired evaluation and review rendering

Implementation commit `193319f984e5d150fbb86e9da2c5ec559540d61e` passed 21 unique
focused checks: nine training, eight derived-checkpoint adapter and four paired
evaluation tests. Training checks use the actual pinned upstream target/loss
producer and real pilot annotation records, plus small synthetic models for
gradients, masks, frozen BN buffers and safe state recovery. Independent review
found and corrected receipt-bound calibration reuse and final-state recovery
edge cases before the real fit. The affected focused tests passed after fixes;
earlier focused receipts remain preserved. No full-suite run occurred.

One real, non-resumed training attempt completed all 200 updates and 400 sampled
triplets in 23.207 seconds. The final checkpoint matches the saved update-200
state exactly. All 213 BatchNorm buffers remain unchanged. All 215 parameter
tensors were trainable and in the optimizer; the 176 active tensors changed and
have Adam step counters of 200. The other 39 belong to upstream final-fusion
branches unused by its configured scale-zero output, not accidentally frozen
layers. Actual input/mask/sampling accounting agrees with 66 positive, eight
hidden and one ambiguous pilot frame. No evaluation/holdout label or image was
used in training or checkpoint selection.

All six development windows completed 138 triplet inference calls, point scoring,
the fixed eight-threshold cached comparison and 60 saved-RF parity cells. At 0.5,
adapted WASB has 98 matches, one wrong point, 46 missing eligible frames and zero
hidden alarms. Original WASB has 31 matches; equal-output-count RF has 90 matches
and nine wrong points. Independent audits reconciled all 48 grid-window results,
16 equal-count rankings and 96 original/adapted report bindings. The model and
comparison remain development results, with no operating point/quality gate
promoted.

Evaluation plus calibration took 32.705 seconds. A separate render-only invocation
took 12.551 seconds, reusing inference. All six new 25-frame review videos decode
through their actual final frames and explicitly identify the adapted checkpoint
and threshold. Root inspected four snapshots/endpoints for display/marker context;
this is not human trajectory acceptance. Human review remains pending. Generated
weights, states, heatmaps, reports and media remain ignored under
`data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/`.

No real training/evaluation failure occurred in this trial. Earlier failed
scientific attempts, consumed resources, reviewed annotations, old model results
and completed human reviews remain unchanged. See
`../ball_wasb_adaptation_results.md` for the exact results and remaining P001 gaps.

## 2026-10-08: cached WASB calibration and adaptation-data inspection

Nine focused calibration tests passed (unittest runtime 1.171 seconds), covering
the real component producer and point consumer, strict thresholds, native-mass
selection, hidden-inclusive label-free RF ranking, cache binding and preservation
of conflicting/failed records. An independent static review found no actionable
scoring, ranking or label-boundary defect. No full-suite run was needed.

One real cached-only screen completed in 2.851 seconds across six windows and
eight declared thresholds. Original 0.5 candidate records and raw/top-one reports
agree on all six windows; saved RF baseline reports also agree. All 42 bound
original inputs remain unchanged. An independent audit reconciled all 48 window
evaluations and all 16 RF ranking records with the saved inputs. No model loading,
media reads, new inference, training or holdout access occurred. The source/test/
config and execution receipts are preserved under
`data/outputs/ball_tracking/wasb/wasb_basketball_calibration_v0_1/`.

Threshold 0.2 gives 62 matches, zero wrong outputs, 83 missing eligible frames and
zero hidden alarms. Equal-count RF gives 61 matches and one wrong output. This is
development calibration, not a method promotion. The separate read-only pilot
inventory confirms 66 eligible centers, eight certain hidden negatives and one
ambiguous frame across 75 reviewed frames; all input frames are disjoint from
the 150 development frames. The adaptation plan has not been executed. See
`../ball_wasb_calibration_results.md` and `../ball_wasb_adaptation_plan.md`.

## 2026-10-08: WASB adapter and completed six-window development comparison

Commit `96907dfdf77fd29474357c6ee7845c2be49fc9dc` adds an isolated WASB adapter,
temporal point evaluator, cached development runner, synchronized review renderer,
configuration and focused tests. Ten adapter tests, eleven point-evaluator tests
and eight runner tests passed. The adapter checks include safe strict loading of
the official checkpoint and real CUDA inference on synthetic images; runner
checks cover frame/channel alignment, actual component-to-evaluator transport and
reuse after partial cache publication. Existing detector evaluation code was not
modified. No full test suite was run for this increment.

Both scientific invocations completed: first one real window, then all six while
reusing the first window's cache. There were 138 unique triplet calls, 2.111 seconds
of measured adapter inference and 33.432 seconds across both invocation receipts.
All 60 saved RF raw/top-one control cells agree with the new point evaluator.
All six videos contain 25 frames and decode through their final source frame.
Independent actual-frame preprocessing comparison on P001 frames 50–52 was
bit-identical to the official RGB/affine/normalization path; no new inference was
needed for that check.

WASB at its fixed threshold matches 17/75 representative and 14/70 challenge
frames, with no wrong observations, 114 eligible missing frames and no alarms
on five hidden frames. It is not a replacement for RF's 51/75 and 60/70 matches.
A separately labeled post-hoc forced-peak diagnostic, using only cached heatmaps,
matches 76/145 but is wrong on 69 and emits on all five hidden frames. These are
development findings, not a method promotion or independent generalization test.
Human visual acceptance remains pending; numerical rejection does not require
reopening completed reviews. Earlier failed attempts remain failed and preserved.
See `../ball_wasb_transfer_results.md` and the ignored WASB output directory.

## 2026-10-08: focused path repair and saved corroboration result recovery

Path-repair commit `decfcbaf642bcff8d04496f8c1274a1c7a415811` followed one exact
producer-backed regression failure, 98 passing focused tests, and a passing check
of the actual emitted certificate. Those three checks consumed 65.203 seconds;
no new full-suite run occurred. Earlier full-suite receipts retain their original
scope and are not evidence for later source changes.

The subsequent scientific attempt `dcdfd95a942c44f3bccb8d41fe8c795c` failed writing
an oversized Markdown summary after calculation/rendering. Its finished event
records 58.562999999994645 charged seconds and verified owned cleanup. It remains
failed, with no completed worker receipt. The saved JSON summary and all six
window/two pool reports consistently show worse matches with YOLO agreement:
51→41 representative, 60→37 challenge, no recovered matches or suppressed wrong
outputs/hidden alarms. Counts were recovered without rerunning the experiment.

The Markdown writer now uses the compact pool totals. Its existing whole-protocol
regression exercises 150 artificial frames with long window IDs and the real
65,536-byte Markdown limit, checks every reported total, and confirms the previous
raw representation exceeds that limit. All three whole-comparison tests passed
in 5.402 seconds after correcting the fixture's required `synthetic_` prefix.
The full suite and scientific experiment were not repeated for this repair.

See `../ball_crop_cross_detector_corroboration_results.md` and the fresh recovery
record under `data/outputs/t/corroboration_path_normalization_c946aed/`.
Ryan's October 8 policy replaces mandatory full-suite and routine proposal/
certificate requirements with risk-proportionate checks; historical failed
attempts, test evidence, reviews, and consumed resources remain unchanged.

## 2026-10-07: final human batch and joint diagnostic completion

Ryan's final P003/170 and P003/171 response is preserved in
`data/outputs/t/error_type_review_b71c64d3fd46/submission_0019.json` (15,300 bytes;
SHA-256 `7b9b8044f0fa67e78cc77dcf7103bfa9a6057c42acae8a7b0b1e193a3cca9758`).
His clarification is appended in `submission_0020.json` (10,160 bytes; SHA-256
`72d586c67f0629251c16fafedbec00a3d4ed5810c142eb665d1025bd4daa2efa`): right meant
red, and 171 mean/top-one contain green predictions on the ball. No red marker
was not converted into total prediction absence. Foot targets, uncalibrated
25-foot estimates and same-as inheritance remain explicit. No race/uniform color
or candidate index is inferred from the player wording. Visibility categories and
separate human centering extent remain unspecified where not supplied.

A text-only interpretation/conclusion check confirmed the reference/prediction
distinction and required keeping P001/219 mean human presence confirmation separate
from AI off-ball interpretation. The summary retains P003/164 on-ball slight-left
judgments alongside the different saved center-distance criterion. Disagreements,
prompted clarifications and unknowns remain explicit; no generic accuracy is claimed.

Administrative consistency checks passed exact 16-frame coverage, three methods
per frame for each reviewer, frozen media/state bindings, null identity/alignment
for absent predictions, no invented human indices, and original file preservation.
No pixels or scientific bodies were reopened for completion. The completed files:

- `summary.md`: 7,208 bytes; SHA-256
  `178e899526d686a635a45bb16ebc56dbdbed616bd2dc812fbbd5c05d6f0ed16a`.
- `completion.json`: 13,226 bytes; SHA-256
  `7996f3c2254649a8e10efaf7fc25ef2f1ceef51d5305b29654f244e1e809adf2`.

Twenty submissions plus those two files total 232,784 bytes, within all approved
individual/count/aggregate limits. Coverage is 16/16 for both reviewers; questions
are resolved and unspecified fields remain null. No tests, scientific execution,
renders, scientific-body/media hashes, original-source reads or Git mutations
occurred. Evidence, consumed budgets, embargoes and holdouts remain preserved.
The next scientific step requires a separately bounded proposal; completion does
not authorize implementation, execution, method selection or a Git step.

## 2026-10-07: seventh human frame batch recorded; final AI pair sealed

Ryan's P003/168 and P003/169 response is preserved in
`data/outputs/t/error_type_review_b71c64d3fd46/submission_0015.json` (14,549 bytes;
SHA-256 `b1b32709bc160dbf76589ea1e29c57257b7d83ba23ad5bfcb62096e5bba8c499`).
Leg/head descriptions remain explicit and the coach role remains attributed to
Ryan; approximate distances are uncalibrated. Frame169's original "red" wording
is preserved, with the referee clarification appended in `submission_0016.json`
(3,548 bytes; SHA-256 `46b8c6c56856c0e8a159cd35fe0ecbd10be76947ded305430d59af29e5237e42`).
A text-only interpretation check confirmed that this is a clarification of the
same frame, not a new independent review. No hidden center or index is inferred.

Six final-overlay metadata bindings matched. Codex viewed P003/170 and P003/171,
sealing `submission_0017.json` (11,426 bytes; SHA-256
`de6b0eea96dda3c44ce3b729a0e2a12ae46ca56d6453832c1ca0efc5e07eb516`).
Appended `submission_0018.json` (2,560 bytes; SHA-256
`2d270f6750a0e9fc0f18c72b7862a6779fd064a825f92448e6635efe76de2c11`)
removes unsupported observation chronology and clarifies screen-right versus
anatomical foot side; no image was reopened and no target judgment changed.
Coverage is AI 16/16, human 14/16. Eighteen create-only records total 186,890 bytes,
within the existing bounds; prior records remain unchanged. The final human pair
is pending. No scientific execution, tests, renders, scientific-body/original-source
reads, media hashes or Git mutations occurred. Evidence, budgets, embargoes and
holdouts remain preserved.

## 2026-10-07: sixth human frame batch recorded; seventh AI batch sealed

Ryan's P003/166 and P003/167 response is preserved in
`data/outputs/t/error_type_review_b71c64d3fd46/submission_0013.json` (13,593 bytes;
SHA-256 `3d45593a324160cd28f7716067e17e299bdcedd9048e890c569f522daecd842e`).
Independent interpretation review confirmed same-as/except inheritance, baseline
judge to referee normalization, and retention of 30-foot/10-foot descriptions as
uncalibrated estimates. Human anatomy and visibility remain unspecified; absent
crosshairs do not establish hidden-ball labels, and 165 visibility is not carried
forward. No exact player identity or candidate number is inferred.

Six next-overlay metadata bindings matched. Codex viewed P003/168 and P003/169,
sealing `submission_0014.json` (10,525 bytes; SHA-256
`77223aa2565a6297d39ea55b6ae8d1d8e95ed320b5ed33a6e2b6716d65b78ca8`).
Coverage is AI 14/16, human 12/16. Fourteen create-only records total 154,807 bytes
within the existing bounds; prior records remain unchanged. No scientific execution,
tests, renders, scientific-body/original-source reads, media hashes or Git mutations
occurred. Evidence, budgets, embargoes and holdouts remain preserved.

## 2026-10-07: fifth human frame batch recorded; sixth AI batch sealed

Ryan's P003/164 and P003/165 response is preserved in
`data/outputs/t/error_type_review_b71c64d3fd46/submission_0011.json` (14,585 bytes;
SHA-256 `3bd99402eac57ddfa6205872ff343c61635cfb0dc2e48a714210ebcc1a3c61f7`).
An independent normalization check supported preserving the 164 slight-leftward
offset as text, without inventing a displacement threshold or attributing
uncertainty to Ryan. His explicit 165 hidden-by-referee statement applies to all
three views. Shoe identity is retained without inferring race or uniform color
from the raw phrase; the approximate 10-foot distance remains unmeasured. Mean
absence has null identity/alignment, and all numeric candidate indices remain null.

Six next-image metadata bindings matched. Codex viewed P003/166 and P003/167 and
sealed `submission_0012.json` (10,667 bytes; SHA-256
`d3b151abda0d16bbd2882165910435117f7cd0a0af278acdcfcaa1b9b4cb1bb3`).
Coverage is AI 12/16 and human 10/16. Twelve records total 130,689 bytes within
the original bounds; prior records are unchanged. No new scientific execution,
tests, renders, scientific-body/original-source reads, media hashes or Git
mutations occurred. Evidence, budgets, embargoes and holdouts remain preserved.

## 2026-10-07: fourth human batch, appended clarification and fifth AI batch

Ryan's mixed-window P001/219 and P003/163 response is preserved in
`data/outputs/t/error_type_review_b71c64d3fd46/submission_0008.json` (14,198 bytes;
SHA-256 `24abe63109ff01debebf03df35089a56ac5fbd83a00d78e5c6eccdedc162924a`).
An independent interpretation check confirmed the distinct windows, same-as
references, null unspecified fields and unmeasured top-one distance estimate.
The initial P001/219 mean no-marker report differed from AI. After a metadata
check, Codex reopened only that existing native image for this specific disagreement
and again saw red #1 near the bench. This was targeted clarification, not resumption
replay. Ryan confirmed the marker and said it blended into the bench. The exact
question/reply are appended in `submission_0009.json` (3,407 bytes; SHA-256
`ad6fb8e57c05952c064f97c2001fbdd771f5749bf1f3bcba9002f96078ac12d9`).
Presence is resolved; neither initial record was edited. No extra independent
review, target identity, physical distance or numeric candidate confirmation is claimed.

Six next-overlay metadata bindings matched. Codex viewed P003/164 and P003/165,
sealing `submission_0010.json` (11,037 bytes; SHA-256
`193c4610e2f22eb091c49f097074c3cf8cdcd7896d18989ceae8fe8ba1ee061a`).
Coverage is AI 10/16, human 8/16. Ten records total 105,437 bytes within the original
individual and aggregate bounds; prior records remain unchanged. No scientific
execution, tests, renders, scientific-body/original-source reads, media hashes
or Git mutations occurred. Budgets, old evidence, embargoes and holdouts persist.

## 2026-10-07: third human frame batch recorded; fourth AI batch sealed

Ryan's 216/217 observations are preserved in
`data/outputs/t/error_type_review_b71c64d3fd46/submission_0006.json` (12,933 bytes;
SHA-256 `4328de9931a8d0388a6cb8416d965b5e717410f6728020ea902982754d5c7dfb`).
An independent interpretation check confirmed that "about 6 feet" and the greater
217 distance are uncalibrated human descriptions. Explicit off-ball observations
are recorded separately from unspecified target identity; no physical distance,
visibility category or candidate index was inferred. Prior AI observations remain
separate, including TT fine-centering uncertainty.

Six existing native-overlay metadata bindings matched. Codex reviewed P001/219
and P003/163, sealing `submission_0007.json` (9,981 bytes; SHA-256
`0b258c47c81f47ca5a1b887e66371bbace570f88835649323e01154614f7b018`).
The two windows retain distinct identifiers. Coverage is AI 8/16, human 6/16;
review is incomplete. Seven create-only records total 76,795 bytes and satisfy
existing individual/aggregate bounds; the previous five are unchanged. No new
scientific execution, tests, renders, scientific-body access, original-image
reads, media hashes or Git mutations occurred. Budgets, embargoes and holdouts
are preserved.

## 2026-10-07: second human frame batch recorded; third AI batch sealed

Ryan's six panel statements for 211/215 are preserved in
`data/outputs/t/error_type_review_b71c64d3fd46/submission_0004.json` (10,933 bytes;
SHA-256 `9de235aef38d174e3d34e2bba21ac5c37365a1e73faf3eb6b468974c280a2eee`).
An independent interpretation check confirmed same-as mapping, reference-crosshair
separation, null identity/alignment for absent mean output, and no inferred explicit
visibility category or candidate index. Ryan's TT/top-one centering judgments do
not replace the sealed AI uncertainty.

Six next-image metadata bindings matched. Codex viewed only the fixed native
overlays for 216/217 and sealed `submission_0005.json` (9,919 bytes; SHA-256
`fd40775a5cb47d8cad721e97213c1ebe11f8ed9124e8df587cae993cdf6abccd`).
Coverage is AI 6/16, human 4/16; the review remains incomplete. Five create-only
records total 53,881 bytes and satisfy the existing individual and aggregate bounds.
The previous three records are unchanged. No scientific-body or original-image
reads, media hashes, renders, tests, scientific attempts or Git mutations occurred.
Prior results, consumed budgets, embargoes and holdouts remain unchanged.

## 2026-10-07: first human frame batch recorded; next AI batch sealed

Ryan's six panel statements map to frames 204/210 and TT/mean/top-one in table
order. The raw wording, same-as references and conservative normalized fields are
saved in `data/outputs/t/error_type_review_b71c64d3fd46/submission_0002.json`
(13,769 bytes; SHA-256 `5f820a7f4168a13d1dbd758077d37ede564e9ac310b4e114a15e1e52e810cf66`).
An independent interpretation review confirmed that seeing the ball does not
specify visibility extent, proximity does not identify another object, and reported
green reference marks must not become second predictions. The 210 clothing-location
disagreement remains explicit; neither reviewer record overwrites the other.

Codex viewed the next six fixed native overlays, frames 211 and 215, and sealed
`submission_0003.json` (9,761 bytes; SHA-256
`be5dfc0fc9c53484cad35e08f26bb4d04a3b92169051dc7d68cc5e54498e1266`).
AI coverage is 4/16 and human frame-specific coverage 2/16; the review is incomplete.
Three create-only records total 33,029 bytes, each below 16 KiB and together below
1 MiB. Original submission 0001 is unchanged. After Ryan reported a computer
restart, saved administrative bindings and next-frame metadata matched; no completed
visual review or scientific checkpoint was repeated. No scientific-body or original
image reads, media hashes, renders, tests, scientific attempts or Git mutations were
performed. Earlier results, consumed budgets, embargoes and holdouts are unchanged.

## 2026-10-06: joint diagnostic review accepted; first AI batch sealed

Ryan approved the fixed scope and asked Codex to make its own visual observations.
The approval amendment permits semantic AI review of the same 48 native overlays,
with separate reviewer records and AI batches sealed before requesting new human
frame judgments. It preserves the original access, output and scientific limits.
An independent protocol review supported separate attribution, explicit uncertainty
and no claim of a second human or blinded review.

Existing media metadata and administrative bindings matched the frozen scope.
Codex viewed six existing native PNGs, covering three methods at P001 challenge
204 and 210, then created `data/outputs/t/error_type_review_b71c64d3fd46/submission_0001.json`.
The 9,499-byte record has SHA-256
`531acd9f54613e25fc59f0231b5a040491eba9256e176ae746813c8f677a8c84`.
Its AI observations are provisional; new frame-specific human responses remain
pending. The record fits the 16 KiB submission and 1 MiB aggregate limits, with
no overwrite or truncation. No new tests, scientific execution, image hashes,
source-image reads, derived media or scientific-body access occurred. Prior
judgments, quantitative results, consumed attempts, budgets and holdouts remain
unchanged. No Git mutation was performed.

## 2026-10-06: metadata-only preparation of a 16-frame error-type review

The new proposal/scope binds 16 exact frames and 48 existing native overlays from
the completed mean comparison, totaling 143,320,299 existing media bytes. Frames
were derived before any pixel access from the already verified bounded return:
all seven TT-matched to mean-wrong/missing transitions in the unique worst net-loss
window, and the sole hidden interval plus two adjacent frames on each side.
Expected media hashes were copied from the bounded worker receipt; only file
metadata was checked in preparation. Original images, scientific JSON output
bodies and media hashes were not opened/recomputed.

Independent design and boundary reviews found no material blockers. They confirmed
the selection rules, 16/48 inventory, existing presentation exception, unblinded
diagnostic status, uncertainty rules and create-only administrative-output bounds.
Prior judgments and the unresolved P003 impression discrepancy remain unchanged.
No new review response, model call, selector/evaluator run, render, test, release
checkpoint or scientific attempt occurred. The proposed review has zero new
scientific budget charge and no application-code change.

The next boundary is acceptance of the diagnostic scope, not another execution.
Its proposal and JSON scope, plus current_state.md, roadmap.md and this history,
remain unstaged at `b71c64d3fd46bb27072efa8644e90c1c222bb65c`, with an empty index.
The 3,330-event journal, 63 closed attempts, remaining 10852.476000000015 seconds,
old validation, all evidence, nine embargoes and three sealed holdouts are preserved.

## 2026-10-06: six qualitative mean-confidence clip reviews recorded

Ryan responded to the request to review all six clips through their final frames.
The six responses were recorded verbatim with normalized panel observations in
`data/outputs/t/mean_impl_10e5fcb90f51/human_review_0001.json` (SHA-256
`3fcc37bc7969e99cc294c6a3bd3b56d4d3322e4baec309bac8a22f1494cd8589`).
`human_review_receipt_0001.json` binds all six submissions (SHA-256
`47faf088a3057903d3f8888f9a2b82f8fa7172a6a51543b1100f64d7bbc9e6b9`).
Separate explicit final-frame attestation and exact error-frame/candidate indices
remain null; no numerical accuracy or production-gate approval was inferred.

Independent interpretation review confirmed the six-clip mapping, the inferred
bottom-pair reference in "both two", and the P002 representative mapping by reply
order. The unmarked top-left source panel is expected. TT received strong praise
on P001 challenge; mean received strong praise on P003 representative. All three
methods still had reported misses near the referee, with better centering from
the bottom pair before that passage. Other clip observations remain qualitative.
Exact wording, including the player-hand description, is preserved without added
race, jersey, frame or candidate-identity inference.

Metadata-only checks matched all six clips and review indices to their existing
worker receipt. The administrative completion/return bindings and unchanged
3,330-event journal tip were checked. No original media or scientific JSON output
body was opened/hashed, and no tests, experiment, render or visual review reran.
All 636 scientific artifacts and the eight earlier human judgments are immutable.
Validation remains 55 focused passes and 1,103 full passes plus the existing skip.
The mixed quantitative interpretation, budgets, embargoes and holdouts are unchanged.

## 2026-10-06: mean-confidence implementation committed; one authorized attempt succeeded

The exact 15-file scope was staged and committed at
`06d3bb96ebb2659005716b7390f40f64e563e44b` under Ryan's explicit conditional
permission. Staged whitespace checks passed; worktree and index were clean.
The new post-commit checkpoint verified exact validated sources, authority,
preserved history and metadata before the single scientific attempt.
Validation stayed at 55 focused passes and 1,103 full passes plus the existing
Windows skip; it was not rerun for release or execution.

Attempt `b36133afc62a4c9fb34547ab6ad2c4ac` succeeded. The worker enforced the
176-input allowlist, froze all six new selections before labels/reports/pixels,
reused saved controls without selector/evaluator reruns and made zero model calls.
It verified 636 create-only artifacts totaling 1,457,619,447 bytes, including six
25-frame/5-fps clips, 450 native overlays and twelve first/final composites.
Parent return was 127,959 bytes; stderr was empty. Parent scientific JSON outputs
were not opened or hashed. Post-success layout inspection viewed only two newly
verified composites; original-image files and human judgments were untouched.

Charged time was 98.719 seconds; supervisor wall time before publication was
99.516 seconds and full command wall time was 144.468 seconds. The monitor used
19 complete scans, maximum safety interval 0.282 seconds and peak sampled combined
memory 419,037,184 bytes. Whole-root final accounting bound was 8,875,232,080 bytes;
the incremental 4-GiB and whole-root 32-GiB limits passed. Minimum free disk was
1,458,809,614,336 bytes. Owned cleanup passed without errors.

The journal has 3,330 events, 63 closed attempts, 59 successes and the unchanged
four historical failures; tip `4dd2b89f3fea67f3be9e3f409e7b937fc6da8a2a622c9b2a98505041c2a31fd6`.
Consumed time is `3547.523999999985`; remaining cumulative time is
`10852.476000000015` seconds. The new attempt cannot retry automatically.
All prior evidence/reviews, nine embargoes and three sealed holdouts are preserved.

The verified bounded result is mixed: representative matched/wrong/missing changed
32/39/4 to 49/24/2; challenge changed 53/14/3 to 57/9/4, with hidden alarms 4 to 3.
Saved top-one remains 51/24/0 and 60/10/0, with five hidden alarms. Every window
regression is retained, including P001's match losses of two and seven frames.
All six new Ryan final-frame reviews remain pending; no method or quality gate
was selected. Exact returned accounting and completion are preserved in
`data/outputs/t/mean_impl_10e5fcb90f51/study_stdout.json` and
`path_confidence_mean_completion_06d3bb96ebb2.json` (SHA-256
`0a83fbcd35079b57738ce32c05c8d31d5c979b8384d84c17a60d20eabc4e2071`).

## 2026-10-06: approved mean-confidence implementation passed artificial validation

Ryan approved the exact proposal, its validation/conditional run and staging plus
committing if checks pass. The immutable approval and separate experiment manifest
bind the unchanged proposal/scope and the new metadata/admin-only history snapshot.
Four new modules and four test files leave historical scientific and monitor
semantics unchanged. No real scientific attempt, input body/hash or pixel access
has occurred in the parent.

Independent reviews cover the fixed-terminal-length arithmetic and ties, phase
access, all-six selection freezing, control reuse, rendering and report accounting.
Final review found three report-consistency gaps: complete diagnostic selections
and startup/human-index reconciliation, startup changed-frame inventory checks,
and review-index digest cross-links. Those checks and mutation coverage were added
before accepted full validation; final independent review passed.

`data/outputs/t/mean_impl_10e5fcb90f51/` preserves all administrative evidence:

- `focused_01`: 54 passes, 1.922 supervised seconds.
- `full_01`: deliberately interrupted after 35.375 seconds for the review correction;
  no sources changed during that run, and owned cleanup was verified.
- `correction_01.json`: reason and exact interrupted-worker stop verification.
- `focused_02`: corrected 55 passes, 3.234 supervised seconds.
- `full_02`: 1,104 total tests = 1,103 passes plus the one existing Windows
  directory-symlink skip; no errors/failures. 2,121.558 unittest seconds and
  2,123.766 supervised seconds on unchanged corrected source bindings.

All actual correction time remains charged to the 4,200-second artificial allowance:
2,164.297 seconds total. Full-suite peak sampled memory was 1,088,929,792 bytes;
peak observed output was 797,763,357 bytes across the fresh admin/temp trees and
the ten explicit artificial-fixture roots (including their preexisting bytes).
Disk reserve, exact 177-source before/after bindings and owned cleanup passed.
The create-only `implementation_validation.json` binds all four validation
receipts, retained snapshots/logs, the correction and final independent review.
Certificate SHA-256: `51384f02cf27f56bd5bfb0b2281fcc62cecd30c2726f528c9671fccb2fc92093`.
The manifest binds this certificate; no execution checkpoint exists yet.
The unchanged responsive-monitor validation is reused, not rerun. Existing 3,221
scientific journal events and 62 closed attempts, nine embargoes, three sealed
holdouts, eight completed human judgments and prior outputs remain preserved.
The new scientific attempt and its 1,200-second allowance are still unused.

## 2026-10-06: mean-confidence follow-up preparation only

The new proposal `../ball_crop_path_confidence_mean_proposal.md` and companion
`configs/ball_tracking/proposals/rfdetr_medium_crop_path_confidence_mean_v0_1.json`
describe one unapproved scoring comparison across the six existing development
windows. Scientific expected hashes were copied from the committed retention
inventory; 176 input path sizes (558,727,833 bytes total) came only from filesystem
metadata. No scientific input/output body was read or hashed and no pixels were
accessed. New selectors, evaluators, renders, tests and human reviews did not run.

The proposed algorithm normalizes confidence per terminal path length while
preserving the existing movement and gap rules, with explicit floating-point
state pruning and tie semantics. Saved TT/top-one controls would be read without
rerunning them. Quantitative evaluation and six new final-frame visual reviews
are future scope requiring approval; no improvement has been measured or claimed.

Independent numerical-design and access-boundary reviews passed. The proposal
now requires disclosure of every window regression even when pool totals improve,
and defines temporal runs so hidden/ineligible frames break them. Metadata-only
checks confirmed all 176 input bindings against the committed authority, all 636
unique relative output paths, the proposal/document binding and false authorization
flags. Document whitespace checks passed. These checks do not validate the future
implementation or establish runtime feasibility. An ordinary context-patch mismatch
was corrected before publication; it caused no partial edit or scientific retry.

Existing completed validation remains 55 focused passes and 1,048 full passes
plus one existing Windows skip. All 3,221 resource events, 62 consumed/closed
attempts, 58 successes and four historical failures remain preserved, along with
the latest contrast outputs, completed human reviews, nine embargoes and three
sealed holdouts. No prior run or release checkpoint was replayed. The proposal
does not change the cumulative balance of 10951.195000000016 seconds or authorize
its proposed single 1,200-second attempt. Source, tests and monitor are unchanged.

## 2026-10-06: saved-decision contrast committed and one authorized attempt succeeded

The eleven-file implementation was staged and committed under Ryan's explicit
conditional permission at `26242d13a5a93043d35fa832c348a44445c1759e` on
`codex/ball-detector-baseline`. The clean descendant commit and its release
checkpoint were verified, then the single authorized comparison succeeded.
Validation remains **55 focused passes** and **1,048 full-suite passes plus the
one existing Windows skip**; no tests were repeated for this execution.

Only the owned worker read and hashed the two fixed saved scientific inputs.
The parent inspected the verified bounded return and administrative records;
no scientific input/output body or pixel was reopened. No inference, selector,
evaluator, rendering, tuning or new human review ran. Existing human judgments,
null human indices and original raw-10 localization outcomes are unchanged.

For the fixed saved winner–comparison pairs in frames 301, 302, 308, 319,
320 and 324, the emitted endpoint had lower current confidence, but its larger
saved past-confidence contribution outweighed that disadvantage and the combined
gap/motion differences. Frame 300 was confidence-only. In frame 304, higher
current confidence and a smaller motion penalty outweighed lower past confidence.
There were no exact score ties. These are descriptive saved-score arithmetic,
not a controlled causal finding or overall performance estimate. The comparator
remains the saved highest-confidence raw-10-qualified retained endpoint; its
visual identity, nearest-point status and best-compatible-objective status are
not established. The saved global margin remains distinct from this pair gap.

Signed differences below are winner minus the fixed comparison, rounded to six
decimals for continuity. The worker artifacts/verified return retain full precision
and exact source pointers. Candidate indices below come from the saved scientific
records; they do not overwrite null indices in Ryan's human-review ledger.

| Frame | Winner index | Comparison index | Current confidence Δ | Past confidence Δ | Gap Δ | Motion Δ | Pair score gap | Saved global margin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 300 | 0 | 1 | +0.007903 | +0.000000 | +0.000000 | +0.000000 | +0.007903 | +0.007903 |
| 301 | 1 | 0 | -0.223674 | +0.415812 | +0.000000 | +0.015307 | +0.207444 | +0.207444 |
| 302 | 1 | 0 | -0.160452 | +0.192138 | +0.000000 | +0.171548 | +0.203234 | +0.155710 |
| 304 | 0 | 5 | +0.192307 | -0.255778 | +0.000000 | +0.301832 | +0.238361 | +0.131841 |
| 308 | 3 | 0 | -0.711348 | +1.409314 | +0.000000 | -0.007421 | +0.690545 | +0.001663 |
| 319 | 14 | 0 | -0.538594 | +0.773399 | +0.250000 | +0.000736 | +0.485541 | +0.262307 |
| 320 | 5 | 0 | -0.806809 | +2.212062 | -0.250000 | -0.413984 | +0.741269 | +0.007299 |
| 324 | 1 | 0 | -0.473951 | +0.868971 | +0.000000 | -0.005010 | +0.390009 | +0.335418 |

The new attempt `9b7ad2e59c67420ea70e0a2be8b7767d` is consumed: **42.078
charged seconds of 120**, 42.625 supervisor wall seconds and
85.313 command wall seconds. The journal now has **3,221 events,
62 closed attempts, 58 successes and four preserved historical failures**.
Remaining cumulative time is `10951.195000000016` seconds; this balance does
not authorize another attempt. All prior diagnostic/recovery/verification roles
remain consumed. No automatic retry is authorized. Nine prediction embargoes
and three sealed holdouts remain intact.

The ignored outputs are `contrast.json`, `summary.md` and `provenance.json`
under `data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit/post_review_saved_decision_contrast_v0_1/`.
The administrative completion is
`data/outputs/t/sdc_impl_7a2e660a3887/saved_decision_contrast_completion_26242d13a5a9.json`;
its verified bounded transport is
`data/outputs/t/sdc_impl_7a2e660a3887/saved_decision_contrast_execution_26242d13a5a9_stdout.json`.
Use those administrative bindings for resumption; do not open the scientific
artifact bodies merely to recover context.

All worker integrity checks passed. Maximum completed monitor interval was
0.282 seconds, below the one-second requirement;
the successful completion verified owned cleanup and final accounting.
Output sizes were 100,374 bytes (`contrast.json`), 9,289 (`summary.md`) and
35,810 (`provenance.json`), all inside their approved bounds. The bounded parent
transport was 121,497 bytes, untruncated, with no stderr output. Independent
interpretation review confirmed the signed arithmetic and the limited wording.

A closeout-only script initially used the wrong administrative field name for
supervisor wall time. Its original source is preserved; the field was corrected
to `total_wall_seconds_before_publication` and only the administrative closeout
was rerun. No worker, experiment or test was repeated, and no evidence or budget
was reset. The implementation commit remains the execution identity; the later
three-document continuity commit changes no source or validated configuration.

Next is a separately scoped decision about a possible follow-up to the saved
history contribution. Any change to selection/scoring or new experiment needs
a concrete proposal and approval; this diagnostic grants neither. Do not rerun
the consumed comparison, the completed tests, or the eight visual reviews for
resumption. Nothing was pushed. These three completion-context documents are
the only follow-up changes and are covered by the existing associated-documentation
stage/commit permission; verify Git for the later documentation commit.

## 2026-10-06: saved-decision contrast implementation validated

Ryan explicitly approved the exact saved-decision contrast proposal and added:
"Yes you may, and you also have my permission to stage and commit if nothing is broken after you implement this".
The separate approval record authorizes implementation, artificial validation,
one conditional execution, and staging/committing the passing scope. No further
permission is needed for those approved steps; pushing, PR creation and merging
remain unauthorized.

The new runner and pure formatter are validated with **55 focused passes** and
**1,048 full-suite passes plus the one existing Windows directory-symlink skip**
(1,049 total; no failures or errors). Independent implementation/helper reviews
passed. The certificate in `data/outputs/t/sdc_impl_7a2e660a3887/` binds all 169
source/test/requirements files, unchanged authority and validation evidence.
The original selector, evaluator, monitor and prior tests remain unchanged.


The full run finished in 2141.094 supervised seconds. Both
validation phases verified owned cleanup and strict final output accounting.
Validation output accounting covers the fresh phase TEMP tree and log; legacy
fixture paths are outside that subtotal. Logs, snapshots and receipts are ignored
under `data/outputs/t/sdc_impl_7a2e660a3887/`; accepted records are `focused_01`
and `full_01`, with additive static review `source_review_release.json`.
Certificate SHA-256: `8199d31f5c952754f5e87e15fb11d045ba939c0e760ee10da68020feb153e9b7`.

The original responsive monitor and its validated accounting-race evidence were
reused without rerunning the completed design/race experiment. New tests used
only artificial inputs. One ordinary source-generation helper error occurred
before validation (a Python namespace lookup while building the new manifest);
the runner had been saved, the manifest was then created by a corrected separate
helper, and no scientific reservation or test run was consumed by that tooling error.

Fresh preservation metadata records the 3,172-event prefix, 61 closed attempts
(57 successes and four preserved historical failures), nine human-review records,
sixteen prior review-image metadata rows and the two future scientific inputs.
No real scientific body was opened/hashed by the parent, no pixels accessed,
and no completed visual review repeated. New execution remains unspent and gated
on the clean approved commit; all earlier attempts and budgets remain unchanged.
The exact eleven-file implementation/documentation scope is unstaged here with
an empty index and HEAD `7a2e660a38877e2000fa997e675c86b97d55e9ac`.

## 2026-10-06: saved-decision contrast proposal prepared and independently reviewed

Ryan's "move forward chat" authorized planning only. The proposal
`../ball_crop_saved_decision_contrast_proposal.md` and companion scope
`configs/ball_tracking/proposals/rfdetr_medium_crop_saved_decision_contrast_v0_1.json`
fix the same eight frames and one saved highest-confidence raw-10-compatible
top-twenty comparison endpoint per frame. Saved S membership already proves
retained availability; completed availability and visual work are not repeated.

The future worker's two inputs are the original motion representative pool
(22,583,132 bytes) and TT observations (5,522,898 bytes). Their combined
28,106,030-byte size comes from metadata; expected hashes were copied from
committed metadata. Proposed signed saved-score contributions cover current
and past confidence, gaps and motion; frame 300 has no history contribution.
Pair gaps remain separate from global margins, with no global causal claim.

Independent source/document reviews of the proposal passed, covering its
mathematical scope and exact input/schema bindings; no code-validation or test
pass is claimed. No
scientific body was read/hashed, no pixel accessed, and no test, experiment or
Git mutation ran during preparation. The proposed new unit is one attempt of
at most 120 seconds within the unchanged `10993.273000000017` cumulative balance.
All old attempts, the 3,172-event history, human decisions, original outcomes,
nine embargoes and three holdouts remain preserved.

Exact-proposal approval is required before implementation and artificial
focused/full validation. Conditional execution additionally requires the
separately approved staging/commit and verified clean release checkpoint.
The three context documents and two new proposal/scope files form five intended
unstaged files; the index is empty and HEAD remains
`7a2e660a38877e2000fa997e675c86b97d55e9ac`.

## 2026-10-06: final frame 324 response and eight-frame human review completed

Ryan's exact response was: "ok this one is the furthest from the ball of all 8 frames. This one is on the white player in the left corner, very far from the ball".
The final `human_review_0008.json` records `another_object`, center
`not_applicable`, and candidate index null. The left-corner-player description
and furthest-of-eight comparison remain qualitative, without numerical distance
or player-identity inference. The administrative closeout is
`human_review_completion_v0_1.json` in the approved review directory.
Administrative checks confirmed the eight-record chain, one new answer per
record, preserved other rows/image bindings/raw outcomes, and unchanged
verification-artifact metadata and resource-journal event count and tip.

All eight selected frames are complete: hands in 300, 301, 302, 304 and 308;
ball with a clearly displaced outer-edge center in 319; the dribbling player
in 320; and the left-corner player in 324. There are seven `another_object`
judgments and one `ball` judgment, with no pending or uncertain rows. These
correlated, selected failures do not establish overall rates, method rankings
or causal proof. Original 10-pixel results, journals, consumed budgets, test
evidence, nine embargoes and three holdouts remain unchanged. No scientific
input/image access, experiment/test rerun or Git mutation accompanied these
notes. The three context documents remain unstaged; the index is empty.
Next is bounded follow-up planning; no further experiment or visual review is authorized.

## 2026-10-06: frame 320 candidate-identity human response recorded

Ryan's exact response was: "ok this one is off the ball but it is not nearly as far as frames 1-5. This one landed on the player who is actively dribbling the ball".
The immutable administrative `human_review_0007.json` records `another_object`,
center `not_applicable`, and candidate index null. No body part or candidate
number was supplied. The closer-than-first-five comparison remains Ryan's
qualitative judgment; no distance, cause or matchup identity is inferred.
Record `0006` and all other rows are preserved. Seven of eight frames are
reviewed; only frame 324 remains pending and is next, source first.
Original outcomes, budgets and test evidence are unchanged. Recording this
response required no scientific input or image access, experiment/test rerun
or Git mutation. The three context documents remain unstaged; the index is empty.

## 2026-10-06: frame 319 candidate-identity human response recorded

Ryan's exact response was: "so this one is on the ball, but it is on the outer edge of the ball and not in the center".
The immutable administrative `human_review_0006.json` records identity `ball`,
center `clearly_displaced`, and candidate index null because no number was
supplied. This preserves a qualitative outer-edge judgment without deriving
numerical displacement or cause. Record `0005` and all other rows are preserved.
Six of eight frames are reviewed; 320 and 324 remain pending, with frame 320 next.
Original 10-pixel outcomes, budgets and test evidence remain unchanged. Recording
this response required no scientific input or image access, experiment/test
rerun or Git mutation. The three context documents remain unstaged; the index is empty.

## 2026-10-06: frame 308 candidate-identity human response recorded

Ryan's exact response was: "same thing with this one, it is only a players hand".
The immutable administrative `human_review_0005.json` records `another_object`
(player's hand), center `not_applicable`, and candidate index null because no
number was supplied. Record `0004` and all other rows are preserved. Five of
eight frames are reviewed; 319, 320 and 324 remain pending, with frame 319 next.
Budgets, localization outcomes and test evidence are unchanged. Recording this
response required no scientific input or image access, experiment/test rerun
or Git mutation. The three context documents remain unstaged; the index is empty.

## 2026-10-06: frame 304 candidate-identity human response recorded

Ryan's exact response was: "same thing with this one, it is on a black players hand".
The immutable administrative `human_review_0004.json` records `another_object`
(player's hand), center `not_applicable`, and candidate index null because no
number was supplied. Record `0003` and all other rows are preserved. Four of
eight frames are reviewed; 308, 319, 320 and 324 remain pending, with frame 308 next.
Budgets, localization outcomes and test evidence are unchanged. Recording this
response required no scientific input or image access, experiment/test rerun
or Git mutation. The three context documents remain unstaged; the index is empty.

## 2026-10-06: frame 302 candidate-identity human response recorded

Ryan's exact response was: "same thing with this one, it is on a black players hand".
The immutable `human_review_0003.json` records `another_object` (player's hand),
center `not_applicable`, and candidate index null because no number was supplied.
Record `0002` and all other rows are preserved. Three of eight frames are
reviewed; 304, 308, 319, 320 and 324 remain pending, with frame 304 next.
Budgets, localization outcomes, test evidence and Git boundaries are unchanged.
The response was saved in a new administrative ledger; earlier records remain
unchanged. No scientific input or image was opened/hashed, and no experiment,
test or Git mutation occurred. The three context notes remain unstaged and the
index remains empty.

## 2026-10-06: frame 301 candidate-identity human response recorded

Ryan's exact response was: "same thing with this one, the candidate is on a black players hand".
The immutable administrative `human_review_0002.json` records frame 301 as
`another_object` (player's hand), center `not_applicable`, candidate index null.
No numeral was supplied for this frame, so frame 300's index 0 was not inherited.
Record `0001` and all other rows remain preserved. Two of eight frames are
reviewed; 302, 304, 308, 319, 320 and 324 remain pending, with frame 302 next.

Original localization outcomes, budgets and test evidence remain unchanged.
No scientific body or pixel inspection, experiment, test or Git mutation was
performed for these notes. The three context files remain unstaged; the index is empty.

## 2026-10-06: first candidate-identity human response recorded

Ryan reported for frame 300: "That candidate landed on a black players hand,
not very close to the ball". The immutable administrative snapshot
`human_review_0001.json` under the approved candidate-identity review directory
preserves this exact response and all eight rows: frame 300 is `another_object`,
center `not_applicable`; seven rows remain pending. Candidate index 0 comes
from the preceding marker clarification, not a separately restated numeral in
Ryan's answer. The saved timestamp denotes receipt creation, not a guessed
message time. The uploaded marked screenshot remains clarification context,
not a replacement for the frozen image bindings.

Original artifact metadata and all pending rows were preserved. The original
verification ledger, localization results, resource journal and budgets were
not changed. No scientific input read/hash, new pixel inspection, experiment
or test was performed to record this response. No Git mutation occurred.

## 2026-10-06: candidate-identity commit and one-time verification completed

Ryan separately authorized the exact nine-file staging scope and its commit.
Commit `7a2e660a38877e2000fa997e675c86b97d55e9ac`, parent
`efeefd58f6801ffe5de106a48f8dad1e835b9647`, was verified clean with an empty index
on `codex/ball-detector-baseline`. The post-commit checkpoint released the
already conditionally approved single verification. Nothing was pushed.

Attempt `89268748193e45b4a598af6bd4747f05` completed with exit code zero. The
owned worker verified exactly sixteen approved PNG byte bindings without
image decoding and published create-only verification, pending-review, guide
and provenance artifacts. Parent scientific-body reads/hashes and pixel
inspection remained absent. No inference, scoring, selection or semantic
labels were produced. All eight frames, 300, 301, 302, 304, 308, 319, 320 and
324, remain pending with zero human judgments. Ryan's next step is the approved
source-first review; saved localization outcomes remain unchanged.

Charged time was 43.938 seconds against the 120-second limit. Supervisor wall
time was 44.750 seconds and complete command wall time was 86.094 seconds.
Owned cleanup and final accounting passed, with no time, memory or output
overshoot. The 3,121-event predecessor prefix remained intact as the journal
advanced to 3,172 events and 61 closed attempts: 57 successes and the same four
failures. The completion tip is
`10ce622caf54c06526fa2b0b259889157711adeb35d4185d793e74cf845dad13`.
Cumulative consumed time is `3406.7269999999826` seconds; remaining allowance
is `10993.273000000017` seconds. Identity verification, output-presence and
prior recovery all have zero authorized attempts remaining. Arithmetic
unused time authorizes no retry or renewed allocation.

Completion evidence is
`data/outputs/t/ci_impl_efeefd58f680/identity_review_completion_7a2e660a3887.json`;
the bounded verified summary transport is
`identity_verification_execution_7a2e660a3887_stdout.json` in that directory.
A post-run administrative summary assertion was corrected to the journal's
`started` event kind instead of `reserved`; no worker, verification or test was
rerun. Existing validation remains 33 focused passes, 993 full-suite passes
and the one Windows directory-symlink skip. No completed visual review was
repeated. All nine embargoes, three sealed holdouts and prior decisions remain
preserved.

The command finished with a clean worktree and empty index. Only these three
post-execution context updates are now intentionally unstaged; HEAD remains
`7a2e660a38877e2000fa997e675c86b97d55e9ac`. Further staging and committing
require separate approvals. Human judgment is next; no new scientific
execution, automatic retry or budget renewal is authorized.

## 2026-10-06: prior candidate-identity implementation and artificial-validation checkpoint

Ryan's exact statement, "ok I'm back chat. Lets move forwar sir", approved the
frozen candidate-identity proposal and scope, implementation, artificial
validation and one conditional byte-verification unit followed by Ryan's
human review. The separate approval receipt records its creation time without
inventing a user-message timestamp. Staging, committing and pushing were not
authorized. The proposal and scope bytes remain unchanged.

The implementation adds one runner and one test module for exactly sixteen
existing PNG bindings across eight P003 representative TT/cap20 frames.
Pending judgments remain Ryan's: unmarked source first, then existing overlay,
with reference markings disclosed. Parent scientific-body reads/hashes and
pixel inspection remain prohibited. No scientific unit, image review,
rendering, inference or scoring has run for this scope.

Accepted `focused_01`: 33 passes, no skips/failures/errors, 10.953 supervised
seconds. Accepted `full_01`: 994 tests, 993 passes and the existing Windows
directory-symlink capability skip, no failures or errors, 2,090.750 supervised
seconds (2,085.596 seconds reported by unittest). Full discovery equals the
previous 961 tests plus 33 new tests. All 165 source/test/requirements bindings
matched before and after both runs; the accepted runs used unchanged helpers.
Owned cleanup and final accounting passed. Full-run peak RSS was 966,332,416
bytes; final measured TEMP-plus-log output was 189,719 bytes and final free disk
was 1,462,928,089,088 bytes. The driver retained owned
Windows-process cleanup, a 1,200-second focused/3,600-second full limit,
8 GiB memory ceiling, 50 GiB free-disk floor and 32 GiB measured-output limit.
That output subtotal covers the fresh TEMP tree and log; legacy fixture paths
remain outside it. Bytecode is disabled. The previously passed monitor-design
and live-walk race checks are reused, not repeated.

Create-only records, logs, two source snapshots per run, starting-file copies,
review and certification helpers are under
`data/outputs/t/ci_impl_efeefd58f680/`. Its create-only
`implementation_validation.json` certificate binds 165 source/test/requirements
files and the validation evidence. The 37,604-byte certificate SHA256 is
`58a54d89bcd887f211c523a76d204ddbd135c57f7b4c4a3f71e630ec1ab3b165`.
Only the manifest's certificate binding changed; the approved specification
remained unchanged. The real review target and post-commit execution checkpoint
remain absent. Separate staging approval, then separate commit approval, is next.
Branch/HEAD remain `codex/ball-detector-baseline` /
`efeefd58f6801ffe5de106a48f8dad1e835b9647`; the nine intended files are unstaged
and the index is empty.

The distinct conditional `post-review-candidate-identity:verify:` unit remains
unrun and unspent: one attempt, at most 120 charged seconds, with cumulative
allowance still `11037.211000000018` seconds. The completed 3,121-event prefix
retains 60 closed attempts, 56 successes and four failures. Consumed recovery
and output-presence attempts are not renewed. All nine embargoes, three sealed
holdouts and prior visual decisions remain preserved.

## 2026-10-05: output-presence commit and conditional execution completed

Ryan separately approved the exact ten-file staging scope and its commit.
Commit `efeefd58f6801ffe5de106a48f8dad1e835b9647` on
`codex/ball-detector-baseline` was verified before execution with a clean
worktree and empty index. The existing conditional approval then authorized
one output-presence unit after its create-only post-commit checkpoint bound
the actual HEAD, manifest, certificate and preserved predecessor history.
Nothing was pushed.

Attempt `395c3038fe7440a1b59912df476c3dd7` completed successfully. Its owned
worker read only the bound recovered breakdown, derived the approved ordered
lists and their lengths separately for all 48 rows, and published create-only
presence, summary and provenance outputs. The complete original breakdown,
row identities, settings, pools, source pointers and execution roles remain
preserved. No cross-row aggregation, rates, rankings, inference, scoring,
selection, media decoding or semantic labels were created. Wrong-object
identity, center-placement errors and missing-output causes remain unresolved.

The parent accepted only the 11,566-byte bounded summary from the verified
administrative transport. It did not reopen or hash scientific input/output
bodies. Successful completion, output bindings, preserved metadata, final
accounting and owned-process cleanup passed. No time, memory or output
overshoot was recorded.

Charged elapsed time was 42.734 seconds against the 120-second reservation.
Supervisor wall time was 43.265 seconds; complete command wall time was
84.703 seconds. The journal advanced from the preserved 3,071-event prefix to
3,121 events and 60 closed attempts: 56 successes and all four historical
failures. The new tip is
`7a990a3fd2b86502dd6245d6d08d2d17c75abe4534bad8d6cc323aa9c43ba701`.
Remaining cumulative allowance is `11037.211000000018` seconds. The single
output-presence attempt is consumed and has zero authorized attempts remaining;
the earlier recovery also remains consumed. Unused arithmetic time does not
authorize a retry or a new allocation.

Administrative completion evidence is
`data/outputs/t/op_impl_de134d942767/output_presence_completion_efeefd58f680.json`;
the verified summary is transported in
`output_presence_execution_efeefd58f680_stdout.json` in the same directory.
The existing implementation validation remains 42 focused passes, 960
full-suite passes plus the one Windows directory-symlink skip, and 16 helper
checks. Those tests and the completed monitor design check were not rerun for
execution or closeout. No completed visual review was repeated. All nine
embargoes, three sealed holdouts and prior review decisions remain protected.

After the clean execution, only the three context documents receive unstaged
continuation notes; the index remains empty and HEAD stays
`efeefd58f6801ffe5de106a48f8dad1e835b9647`. Further staging and committing require
separate approval. The next scientific work must first have a separately
bounded proposal; no further scientific access, real retry, budget allocation
or new study is authorized by this completion.

## 2026-10-05: approved output-presence implementation and artificial validation

Ryan's "Yes move forward chat" approved implementation, focused/full artificial
validation and one conditional unit under the exact output-presence proposal.
The approval and manifest bind the frozen proposal and completed predecessor
history; the only new scientific input is copied from the successful producer's
administrative receipt. No parent scientific body was read or hashed.

Independent production and test review passed. Before helper execution, review
tightened exact test-count checks, explicit outcomes, verified process cleanup,
final temporary-output/free-disk accounting, normalized administrative paths and
bounded log reads. These were ordinary implementation corrections, not failed
scientific runs or changes to the approved envelope.

The first focused run (`focused_01`) ran 42 tests: 41 passed and one failed
because a test compared `1.9999999999986358` with exactly `2` seconds.
Its log, result and four implementation snapshots remain preserved.
`correction_01.json` records the one-line change to a seven-decimal comparison,
consistent with existing budget precision. Production behavior was unchanged.

The first full run (`full_01`) stopped after 500.031 supervised seconds when
the validation helper encountered a directory removed during a live TEMP scan.
No completed test failure or resource-limit breach was reported. All owned
processes stopped; final accounting passed and source bytes were unchanged.
The original driver/certifier, log, result and four source snapshots remain
preserved. `correction_02.json` records the reviewed live-scan-only handling of
vanished nested paths; final post-cleanup accounting remains strict. Production
source and test bytes did not change for this correction. Sixteen deterministic
helper checks passed, covering the live race and required fatal conditions. The successful
`focused_02` run under the former helper is retained as intermediate evidence.

Accepted `focused_03`: 42 passes, no skips/failures/errors, 15.235
seconds under the validation supervisor. Accepted `full_02`: 961 tests,
960 passes and the existing Windows directory-symlink capability skip, no
failures/errors, 2206.828 supervised seconds. Source inventories matched
before and after both runs; owned cleanup and final resource accounting passed.
Bytecode was disabled. The full discovery count equals the prior 919 tests
plus 42 new tests.

The create-only implementation certificate binds 163 source/test/requirements
files and 48 evidence files, including both interrupted/failed runs, original helpers and corrections.
The manifest's certificate binding changed only after successful validation;
its approved specification stayed unchanged. The completed responsive-monitor
design check was reused, not rerun. Records, snapshots, logs, source review,
certificate and completion checkpoint are under
`data/outputs/t/op_impl_de134d942767/`.

No scientific output-presence attempt or other scientific execution occurred.
All validation fixtures were artificial; no real media was inspected and no
completed visual review was repeated. The prior 3,071-event history, 59 closed
attempts, 55 successes, four failures and cumulative balance
`11079.945000000014` seconds remain unchanged. The completed recovery is consumed;
the distinct new one-attempt 120-second role has not been reserved.

Branch/HEAD remain `codex/ball-detector-baseline` /
`de134d942767b70dfc6da360745f50405a8b3f8d`. Ten intended files are unstaged,
the index is empty, and `git diff --check` passed. Staging and committing still
need separate approval. The new post-commit execution checkpoint remains absent.

## 2026-10-05: output-presence proposal prepared using source and receipts only

After successful recovery, Ryan asked to move forward. Preparation produced
`../ball_crop_candidate_retention_output_presence_proposal.md`, requesting a
new within-row split of S memberships using only the recovered breakdown.
Its 744,235-byte size and SHA-256 were copied from the successful worker's
administrative receipt; the scientific breakdown body was not opened or hashed.

The source contract establishes single current, threshold-qualified output for
both cap policies and false-positive count equal to accepted output count on
an unmatched eligible frame. Git confirmed unchanged blobs since original
scoring commit `f36237247191e726ad7e81bdc6651f9340a9063d` for
`crop_retention_evaluation.py`, `evaluation.py`, `crop_motion_factorial.py` and
`crop_motion_evaluation.py`. This is a source-based derivation proof, not a new
empirical result. No new memberships, counts, semantic labels or performance
claims were produced. The reviewed package receipt explicitly lacks individual
frame identity verdicts.

Before-context copies and source bindings are preserved under
`data/outputs/t/output_presence_plan_de134d942767/`. An initial read referenced
a nonexistent proposal filename; the correct existing filename was found from
the documentation inventory. This was an ordinary read-command correction,
not a failed test or experiment, and required no permission stop.
No tests, scientific reads/hashes, real workers, media inspection or Git
mutations occurred. The previous 32 focused passes and 918 full-suite passes
plus one existing skip remain the latest implementation validation.
The original recovery allowance and attempt are unchanged. The new 120-second
one-attempt diagnostic requests separate approval; no code was implemented.

## 2026-10-05: one scientific error-breakdown recovery completed successfully

Ryan separately authorized the 34-file staging and commit, then continued with
"ok lets move forward". The clean execution commit was
`de134d942767b70dfc6da360745f50405a8b3f8d`. Committed blobs matched the verified
index and all working-file bindings remained unchanged. Release preparation
verified 159 source bindings and 16 validation-evidence bindings, then created
the exact post-commit checkpoint. It reused the completed 32 focused passes and
918 full-suite passes plus the existing Windows skip; no tests were rerun.

The new public recovery entry point ran exactly once as attempt
`05fe00c14f224c5abfc2cc6008e90f96`. It passed its metadata preflight, owned-worker
execution, final accounting, cleanup, preservation and bounded-summary release
checks. Command exit code was zero and stderr was empty. The unchanged formatter
copied the approved 48 rows, with representative/challenge pools kept separate.
No inference, scoring, decoding, training, new visual review or method selection
occurred. Scientific input/output body reads and hashes stayed in the owned
worker; the parent used administrative receipts and the accepted transport.

Charged time was `52.54699999999866` seconds from the existing
`292.73500000001513`-second balance. Supervisor wall time before publication was
`53.09300000000076` seconds; complete external command wall time was
`106.45300000000134` seconds. Eleven accounting scans completed. Maximum safety
interval was `0.2960000000020955` seconds, peak sampled combined memory
419,811,328 bytes, final output bound 7,415,183,417 bytes and minimum free disk
1,465,797,832,704 bytes. Time/memory/output overshoots were zero; final-accounting
and cleanup errors were absent, and owned cleanup was verified.

The original failure and 3,010-event prefix remain preserved. Completion event
`00003070.json` has chain tip
`d800b77b4db2128d1baa09db59538ab6f16d4aad6d96aaa7a9fd84f96c11bf92`.
The recovery attempt is consumed; no automatic retry or renewed budget exists.
Launch command, wall time, stdout/stderr bindings, release checkpoint and
completion record are under `data/outputs/t/ebri_fa730bcb6d2e/`. Scientific
outputs are ignored under the original experiment root at
`audit/post_review_error_breakdown_recovery_v0_1/` and must not be reopened or
hashed by the parent. All holdouts, embargoes and completed reviews remain.

## 2026-10-05: recovery integration passed focused and full validation

Ryan authorized continuation with "move forward chat". The new recovery runner
uses the responsive monitor through an explicit journal adapter, preserving
the original failed execution and deducting its charged time from the shared
300-second allowance. A new manifest and certificate separate current source
validation from immutable historical certificates. A missing post-commit
checkpoint prevents public execution before the separately authorized clean
commit. Source/configuration review preceded test execution.

Final focused validation passed all 32 synthetic tests in
8.719 supervised seconds. Full regression completed
919 tests: **918 passes, one existing Windows directory-symlink
capability skip, zero failures/errors** on the final validated run, in
2241.687 supervised seconds. Peak sampled full-suite worker
memory was 963,837,952 bytes. Source/test bytes were frozen during
the successful focused and full runs. The monitor's prior 12,000-file design
evidence was reused; no new large fixture or performance benchmark ran.

The first focused run completed 32 tests with 30 passes, one error and one
failure. Both came from the same path check: it required preserved directories
to be strictly below the output root and therefore rejected the root itself.
The correction explicitly accepts the exact output root while retaining all
ancestor/reparse checks and the stricter descendant boundary. The original
source snapshot, log, result and review receipt remain preserved. Focused tests
were rerun after this real correction; the full suite ran on the corrected
source. No real data or diagnostic execution was involved in that failure.

Exact command, source snapshots, logs, resource observations, review receipt,
implementation certificate and preservation checkpoint are under
`data/outputs/t/ebri_fa730bcb6d2e/`. Validation used fresh ignored artificial
fixtures, owned Windows processes and disabled bytecode. Its output subtotal
covers fresh TEMP plus logs; legacy fixed fixture destinations are explicitly
outside that subtotal. No scientific body was read or hashed by the parent,
and no real recovery unit was dispatched. Ordinary read-command corrections
are separate from this recorded focused-test failure.

The final intended scope adds five files to the prior 29-file dirty worktree:
runner, tests, integration design, integration approval and recovery manifest.
Only three existing context documents were updated during this step; their
historical bodies and all other prior bindings are preserved. The index remains
empty at `fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`. Staging and committing still
require separate authorization. The saved 48-row diagnostic remains pending.

## 2026-10-05: responsive monitoring passed focused, design and full validation

Ryan approved implementation after reviewing the engineering choice behind the
half-second deadline. A separate Python monitor now keeps cheap resource checks
independent of whole-root metadata scans. The original resource module,
scientific runner, journal limit bindings, consumed budgets and earlier evidence
were preserved. The compiled-scanner benchmark proposal was set aside without
executing its pending allocation.

Independent static review passed before execution. Review corrections included
suspended process startup before Windows Job assignment/resume, exact primary
thread ownership verification, separate worker/IPC receipt bounds, actual
serialized-byte bounds, tick-start cadence, observed overshoot recording and
validation-driver phase/source bindings. These were pre-test source corrections;
no failing validation attempt occurred in this implementation.

All 37 focused tests passed in 0.978 unittest seconds (1.641 supervised seconds),
covering metadata accounting, slow/stalled scans, responsive memory/disk/time
checks, preserved budgets, bounded records and startup/descendant cleanup. Actual
Windows checks confirmed a small job rejects an allocation above its committed
memory ceiling and owns/terminates child processes. Test allocations were tiny
and controlled; no system-wide memory pressure test was performed.

One fresh artificial design check created 12,000 file names and 400 directories,
including a hard-link pair, with 192,000 initial logical bytes. It ran a seven-
second growing worker under the new monitor. Three complete scans succeeded;
the final scan took 0.890 seconds, while the maximum safety-check gap was 0.266
seconds. Combined sampled worker/helper RSS peaked at 75,661,312 bytes. Final
reference bytes were 236,340 and within the conservative published bound.
Charged attempt time was 8.766 seconds; wall time before final publication was
9.797 seconds. The outer design check took 15.531 supervised seconds including
fixture setup and verification. No original 0.40/0.50-second speed gate was
applied or retroactively changed, and no historical fixture was revisited.

The single full suite completed 887 tests: **886 passes, one existing Windows
directory-symlink capability skip, zero failures/errors**. It took 2197.840
unittest seconds and 2199.922 supervised seconds. All source/test bindings
remained unchanged during validation. The ignored evidence directory is
`data/outputs/t/ebdm_fa730bcb6d2e/`; its completion checkpoint binds the outputs
and verifies preservation, branch/HEAD and the empty index.

The 29-file unstaged scope consists of the original 25 intended files plus the
new monitor, focused tests, revision design and approval record. Git staging,
committing and real scientific execution did not occur. Recovery-runner and
authority integration remain necessary before the saved error breakdown. All
embargoes, holdouts and completed human reviews remain preserved.

## 2026-10-05: compiled prototype built; 39 focused and 849 full-suite passes

Ryan authorized the planned compiler/SDK installation, isolated implementation,
build and artificial/full-regression validation. Preparation under
`data/outputs/t/ebcb_src_fa730bcb6d2e/` verified 123 protected bindings, HEAD
`fa730bcb6d2e`, branch `codex/ball-detector-baseline`, 23 intended unstaged files
and empty index. No live candidate query allocation was granted.

The official fixed Build Tools 17.14.41 bootstrapper had a valid Microsoft
signature, ProductVersion 17.14.41, FileVersion 17.14.37710.0 and SHA-256
`37bb0fb429d163ecebd272a865d11a37b906d152bef960da2ddb29c2e2fd6eeb`.
The selected offline layout used exactly the three approved component IDs and
en-US. Setup exited zero; the installed instance is complete, launchable and
requires no reboot. Dependency/version, layout, installer and setup records are
preserved. No runtime downgrade was requested; installed runtime registrations
are recorded. No scientific data were involved in installation.

Independent source review passed for the C core, artificial provider, wrapper
and 39 focused checks. Build 01 stopped at CPython's header warning C4115 under
strict /WX. Source revision 02 adds only `struct timeval;` before Python.h;
revision 01 and its failed build/log are preserved. Build 02 compiled both
modules successfully and inspected their x64 exports/dependencies, with 260
input bindings. Its production binary SHA-256 is
`54242db5b678e06bbb50fa2f0d74e1e6bf3f3280dd3bf64465d402ffd557b290`.

The first validation launcher invocation failed before its marker or worker
launch because `psutil` is absent. The failed driver was retained unchanged;
the reviewed replacement reuses hash-verified `_WindowsJob`/`_rss` from the
existing resource helper. No dependency was installed and no tests were rerun
because of that pre-test failure. The corrected validator preserves exceptions,
bounded cleanup, create-only logs, explicit binary/source bindings and limits.

Focused validation passed all 39 checks in 0.011 unittest seconds, 0.516
supervised seconds. Full regression ran once: **850 tests, 849 passes, one
existing directory-symlink capability skip, zero failures/errors**, in 2290.353
unittest seconds and 2296.125 supervised seconds. Peak sampled owned-tree RSS
was 955,551,744 bytes; minimum sampled free disk was 1,469,064,687,616 bytes.
Both jobs were assigned/closed successfully with no remaining members or
cleanup errors. All 156 production/test/requirements bindings stayed unchanged.

These results establish build and artificial correctness, not native metadata
correctness or performance. No production candidate query, benchmark, old
fixture traversal, scientific body read/hash, scanner integration or Git
mutation occurred. The independently reviewed next native proposal explicitly
separates original charged elapsed from finalization/outer command wall time
and records static gate calls separately from whole-tree supervisor calls.
Its 120-second allocation is proposed only; previous budgets are unchanged.

Final scope adds the installation/prototype approval and next validation
proposal to the prior worktree, plus three context continuations: 25 intended
unstaged files, empty index, unchanged branch/HEAD. Before context updates,
all 123 preparation bindings matched; final preservation retains the other
120 bindings and all historical context text with prior-heading demotions.

## 2026-10-05: compiled-batch toolchain inventory and interface plan

Planning began at HEAD `fa730bcb6d2e`, branch `codex/ball-detector-baseline`,
22 intended unstaged files and empty index. A preparation receipt under
`data/outputs/t/ebcb_plan_fa730bcb6d2e/` verified 119 protected bindings and saved
the three context bodies before continuation edits.

Read-only checks found CPython 3.11.15/x64, its headers/import libraries and
`.cp311-win_amd64.pyd` suffix. PATH, known installation locations and registry
roots supplied no usable compiler/SDK. Existing Visual C++ runtimes and VS Code
were recorded without treating them as build tools. No exhaustive disk search,
installer download, compilation, test, live query or benchmark occurred.

The new plan specifies Microsoft Build Tools 17.14.41/required C++ dependencies,
one SDK family, isolated build provenance and a bounded public-CPython interface.
The same deadline closure surrounds successful fresh queries; failed queries
preserve the original error precedence. Python retains complete inventories,
multiplicity, conservative sizes and disappearance behavior. Independent review
covers the proposal; artificial tests and native validation remain future work.

Only the new plan and three context continuations change. Final preservation
checks require the other 116 bound files unchanged, historical context bodies
preserved, exact 23-file unstaged scope, unchanged branch/HEAD, empty index and
clean whitespace. No scientific bodies or old fixtures are read or hashed, and
no experimental allocation or Git authorization is renewed. The next approval
concerns specified machine installation plus isolated implementation/artificial
validation, with a live candidate query series outside that block.

## 2026-10-05: saved-evidence accounting reassessment and source-only write audit

Ryan requested reassessment after the identity-equivalence experiment. Current
Git state matched its completion checkpoint: HEAD `fa730bcb6d2e`, the expected
branch, 21 intended unstaged files and empty index. A preparation receipt under
`data/outputs/t/ebra_plan_fa730bcb6d2e/` bound 114 source/authority/context/synthetic
metadata files. No fixture or scientific body was inspected or hashed.

Review confirmed the older profile's 291.710 ms of `nt.stat` time in a failed
487.581 ms scanner call. The latest component's second method was faster in nine
of ten pairs; this descriptive order sensitivity supplies no cache-causation or
whole-scanner speed claim. All completed tests and timing results remain intact.

Source review mapped scientific artifacts, worker receipts, journal publication
temporaries/seals, stdout/stderr logs and temporary/runtime output. Only readable
summary text has the cited 65,536-byte pre-write limit; a complete fixed budget
for new writes and enforceably immutable history were not established. Official
Microsoft documentation confirms the directory-entry hard-link freshness caveat.

The new reassessment note prefers a supported build/interface plan for a
compiled sequential fresh-query loop, with unchanged complete accounting and
timing gates. No speed benefit or implementation readiness is claimed. A limited
read-only tool inventory found no `cl.exe`, `clang.exe`, `gcc.exe`, `cargo.exe` or
`cmake.exe` on PATH, nor the default Visual Studio locator; no global compiler
absence is inferred. No compiler, test, native probe or experiment was run.

A routine read-only `rg` wildcard-path error was corrected with its `-g` filter;
it was not a failed test or diagnostic. Only the new decision note and three
context continuations change. Preserve the other 111 bound files and historical
context bodies. Final documentation checks cover independent review, references,
whitespace and exact 22-file unstaged scope with unchanged branch/HEAD and empty
index. No experimental allowance, scientific scope or Git authorization changed.

## 2026-10-05: identity equivalence passed; completed speed comparison missed its gate

Ryan approved the reviewed follow-up and fresh 30-second/16 MiB envelope. The
before receipt under `data/outputs/t/ebni_src_fa730bcb6d2e/` verified 84 protected
source/authority/context/metadata bindings and the exact 20-file starting status.
The new approval adds one intended unstaged file. The adapter and original
supervisor/ownership helper remain frozen. Before validation, review removed an
unnecessary 64-bit cap on complete Python identifiers and added a wider-label
artificial case; no native result prompted that refinement.

Two independent source reviews passed. Validation revision 01 ran 35 new series
checks plus 15 adapted harness regressions: 50 passes, zero failures/errors/skips,
in `0.370976400001382` seconds. The prior 32 unchanged adapter checks were reused.
No old experiment, adapter test run or full suite was repeated. Source revision,
review, test log and validation report are preserved create-only.

One native series ran at `data/outputs/t/ebni_fa730bcb6d2e/`, attempt
`0148ff4a58d247aa83b1e4758b48902e`. All 94 correctness comparisons across seven
phases passed, including held-open growth/shrink, other-link writes, closure,
replacement and the final 64-name inventory. The separate missing-file check
also passed. Full raw
backend identifiers and opaque128 evidence remain preserved. The replacement
had a different identity under both APIs; no general ID-reuse rule is inferred.

All 20 batches/ten alternating pairs/1,280 timed queries completed. Median
native/reference ratio: `0.8992258224480973`; six native wins and four slower
pairs (1, 3, 7, 9). The required median at most `0.80` and every-native-faster
conditions both failed. Outcome: `component_comparison_complete`, correctness
true, `worth_full_scanner_proposal:false`, `scanner_readiness_passed:false`.
This valid negative finding is preserved without retuning, discard or retry.

Sealed accounting: `1.5780000000013388` charged seconds; 44,625,920-byte peak
worker memory; 204,677-byte maximum observed output; 221,061-byte final output
bound; maximum monitor interval `0.26599999999962165` seconds; minimum free disk
1,481,896,800,256 bytes; zero overshoots/accounting errors. Parent-reported
harness/external wall times were `2.0964757000001555`/`2.2839816` seconds.
Arithmetic unspent time is `28.42199999999866` seconds, with zero series left.

Independent `outcome_audit_01.json` checked 25 allowlisted source/evidence files,
all six journal events and seals, ownership, result bindings, phase evidence
and timing calculations. It passed. Only continuation text in three context
files changes afterward; the other 81 before-bindings and historical context
bodies remain protected. Final status is 21 intended unstaged files, empty
index, unchanged branch/HEAD. All earlier allowances, failures and completed
reviews remain preserved; no parent fixture/scientific traversal or Git mutation
occurred. Real error-breakdown recovery remains pending.

## 2026-10-05: identity-equivalence contract review and follow-up proposal

Ryan asked to move forward after the completed by-name identity finding. Review
used current source, frozen component metadata and official Python/Microsoft
documentation. It did not inspect fixture contents, scientific bodies or the
installed CPython implementation. No native probe, new test, benchmark or retry
occurred. The original 72-pass validation and sealed component outcome stand.

The counter's source uses identities for equality, membership and multiplicity.
A fixed one-to-one label change across both inventories preserves its formula
and acceptance conditions; matching separate per-phase partitions without
continuity is insufficient. Independent conceptual review supported retaining
full native FileId64/volume and Python inode/device keys separately on the
already restricted local NTFS fixture. Documentation supports representation
differences without establishing a universal conversion between saved values.

The new proposal explicitly amends cross-API comparison to test known groups,
continuity, per-backend volume stability and known sizes. It preserves raw
128-bit evidence and replacement/reuse uncertainty. It proposes separate frozen
timing expectations and a new bounded allocation; neither implementation nor
that new execution is approved by this preparation. No readiness pass or
tracking-quality improvement is claimed.

The preparation receipt at
`data/outputs/t/ebni_plan_fa730bcb6d2e/preparation_before.json` binds 80 allowlisted
inputs. Three context files receive continuation text; the remaining 77 bindings
and historical bodies are checked for preservation. Final validation for this
documentation task consists of independent proposal review, local-link and
whitespace checks, exact 20-file worktree status, unchanged HEAD and empty index.
A routine setup-command quoting error was corrected before execution and is
recorded in the preparation receipt; it did not run or repeat an experiment.

## 2026-10-05: 72 new component checks passed; native identity mismatch preserved

Ryan approved implementation, new artificial checks and the conditional bounded
series in `../ball_crop_candidate_retention_by_name_feasibility_proposal.md`
(SHA-256 `b74d2681b85c40564a27a89bc15873cf154ddfb775f8a88769474f3f8173e57f`).
Preflight verified 51 source/authority/context/fabricated-metadata bindings and
the exact 18-file starting status, branch/HEAD and empty index. The separate
approval added one intended unstaged file; generated helpers remain ignored.

The adapter, series engine and supervisor wrapper received independent combined
source review. Review corrections removed a post-supervision runtime receipt
outside the charged output root and added summary/result consistency checks.
The final new test inventory was 32 adapter + 25 series + 15 supervision tests.
All 72 ran once and passed, with zero failures, errors, skips, expected failures
or unexpected successes, in `0.33760719999918365` seconds of helper elapsed time.
No old tests/full suite/native probe were part of this artificial validation.
The bound report, log, independent review and source snapshot are under
`data/outputs/t/ebbn_src_fa730bcb6d2e/`.

The authorized native series ran once under the unchanged original supervisor,
using the preserved ownership protocol and a create-only series marker. Its
attempt ID is `d774f180726d47a08a6aead2658a807a`. The fixed local NTFS guard passed.
The worker created four fixture directories and five initial file entries, then
stopped the series at its first initial comparison: ordinary volume identifier
`986718957` differs from full native `14572188484234126061`. Both reported file
ID `1125899906873685` and logical size 64. Full raw values, including the 128-bit
ID and signed native storage, are retained. There was no query exception.

Outcome: `identity_contract_review_required`; compatibility and scanner
readiness are false. The five progress records contain no batch/timing events.
No growth/shrink/replacement phase or later 64-entry inventory was reached.
This observation cannot establish freshness across changes or any speed benefit.
It is a completed negative compatibility finding, not a diagnostic crash or a
failed test suite. No truncation, remapping, retry or threshold change followed.

The five-event journal sealed one successful supervised execution with no
resource violation or final-accounting error. Charged time was
`0.7809999999990396` seconds, harness wall time `1.1970968999994511` seconds and
external command wall time `1.3705132` seconds. Peak worker memory was 49,811,456
bytes, final output accounting bound 34,770 bytes, and maximum monitor interval
0.25 seconds. Final event digest:
`23af9026d35da59de3d6500b33e8bca498948c3bd9ec7d10e40e1a9c683d400a`.
Bound worker-result digest:
`f3c2b225d7934b3deb5778492d6615a6c1b75d342ed880c4951a4905f007d552`.
The native series is consumed despite `29.21900000000096` seconds arithmetically
remaining. All earlier allocations and successful/failed evidence are unchanged.

Routine shell/bookkeeping issues were corrected under Ryan's latest policy:
a setup-command quoting parse error before execution, a missing metadata folder
lookup corrected from the supervisor's source, and a path-array expression in
the post-run receipt builder. None ran or repeated an experiment.
Post-run independent review and final preservation bind the
component evidence without traversing the fixture or scientific bodies.

## 2026-10-05: metadata feasibility proposal and revised failure policy

Ryan authorized read-only review and a next proposal, then explicitly replaced
the blanket stop-on-any-failure rule with judgment about material issues. The
new working-agreement section persists that instruction. It changes routine
failure handling; Git steps, evidence protections and resource limits remain.

Review used saved source and fabricated-result metadata plus official Microsoft
API declarations. The earlier restricted CPython raw-source fetch is preserved
as a lookup interruption, not a failed test or diagnostic; it was not retried.
The proposed Windows by-name metadata interface has not been called. Its native
availability, complete identity compatibility, freshness and speed remain open.

The proposal binds a new isolated component task and conditional tiny paired
comparison; its new allocation is unapproved. No old or new test suite, benchmark,
scientific diagnostic, stress-fixture traversal or native probe ran in this
preparation. The prior 26 candidate and 29 helper passes stand, alongside the
separate failed first static call. The old balances and sealed failure remain.

Preparation receipt `data/outputs/t/ebbn_plan_fa730bcb6d2e/preparation_before.json`
binds 46 allowlisted source/authority/context/fabricated-metadata files. Four
context files receive new text; the other 42 bindings and historical context
bodies are checked for preservation. Independent proposal review, whitespace,
local links, exact 18-file dirty scope, unchanged branch/HEAD and empty index are
the relevant final checks. No implementation validation is claimed for a design.

## Approved static harness passed 29 checks; first timing call failed

Ryan's "Yes move forward" approved implementation, independent review, new
artificial checks and one conditional static timing run. The new approval binds
`../ball_crop_candidate_retention_scan_timing_request.md` at SHA-256
`c6c02f4264b075815e703f0efee6da03a764b2125c255abb94667ce4dcb48d3b`.
Preflight verified the fifteen-file starting scope and 32 source/authority/
synthetic-metadata bindings without traversing the fabricated or scientific root.

New ignored files under `data/outputs/t/ebxt_src_fa730bcb6d2e/` implement the
static harness, 29 artificial tests and once-only structured validator. Independent
combined review passed with no blockers. The first helper validation ran all
29 tests successfully: zero failures, errors, skips, expected failures or unexpected
successes. Helper elapsed time was `0.29927740000130143` seconds; external command
wall time was `0.6919108` seconds. Existing candidate tests, earlier helper suites,
startup observations, profiler and full suite were not repeated.

The one conditional static attempt ran at `data/outputs/t/ebxt_static_fa730bcb6d2e/`,
ID `5650139001c240c5bb6c9e243927f0de`. It used the unchanged original supervisor
and ownership protocol with the exact amended candidate in the owned worker.
The worker verified the frozen synthetic fixture metadata before timing. Its
first candidate call raised `ResourceLimitError: Output tree did not stabilize
for complete byte accounting`, returned no total and recorded
`0.4854300000006333` seconds. The per-call threshold remains strictly below
0.40 seconds. Dispatch stopped immediately; no later candidate call or after-series
fixture check occurred. The failed worker result has no successful supervisor
result binding, and is preserved only as failure evidence alongside its progress
log. No static or overall readiness pass is claimed.

Read-only failure bookkeeping verified the six-event journal's sole failed,
closed attempt, matching reservation/completion seals and absent lock. Final tip:
`3dfa324db2969075accea17ea8485898cc4962a98c277311a54a1cd6dd4a48c1`.
Charged time was `2.312999999998283` seconds; external command wall time was
`2.6772916` seconds. Peak worker memory was 53,428,224 bytes, maximum observed
output 12,207 bytes, final accounting bound 28,591 bytes, and maximum monitor
interval `0.26599999999962165` seconds. All three overshoot fields were zero;
final-accounting error was null. The new 30-second allocation has zero remaining
attempt authorizations regardless of its `27.687000000001717` unspent seconds.

`failed_execution.json` in the new helper directory preserves both command
outputs and the failure details. No automatic repair, retry, parent fixture
traversal, scientific body/root access, old-budget modification or Git mutation
occurred. Only the new approval and three existing context documents join this
stage's ignored artifacts; the intended dirty scope is now sixteen files with
an empty index. Further work requires approval under the stop-on-failure rule.

## Static timing request prepared; no new execution

After the amended candidate's first 26-test pass, Ryan authorized a bounded
timing request. The new document is
`../ball_crop_candidate_retention_scan_timing_request.md`. It preserves the
original static/dynamic readiness gates while requesting only the static phase
now, avoiding dynamic setup before a static pass.

Read-only source review identified the exact frozen supervisor timing semantics:
charged elapsed is captured before its final accounting scan and finished-event/
seal publication. The draft was clarified during preparation to describe a
30-second recorded active allocation, mandatory later checks and separate total
wall-time reporting. No runtime code or approved resource accounting was changed.
Independent request review then passed with no remaining blockers.

Preparation checked the fourteen-file preexisting Git scope and recorded 31
bindings for current source, authorities, focused results, ownership helpers and
frozen synthetic fixture metadata. It did not traverse either the fabricated
fixture or real scientific root and did not read/hash scientific bodies. Planned
new destinations were absent; the checked atomic reservation path is 184
characters, within the unchanged 240-character ceiling. Before-context copies
and preparation evidence are under `data/outputs/t/ebxt_plan_fa730bcb6d2e/`.

No test, scanner call, benchmark, profile or real worker ran in preparation.
The 26 focused passes remain the latest validation of this candidate; performance
is still unproved. The new 30-second synthetic allocation is proposed, not yet
granted. Old profiling and real balances, failed evidence, embargoes, sealed
holdouts and completed reviews remain preserved. Only the new request and the
three existing context documents change; the current dirty scope is fifteen
files with an empty index. Approval of the request is the next boundary.

## Amended prefix candidate: first focused validation passed

Ryan approved implementation and 26 new focused checks, then explicitly approved
the UNC amendment after static review found the empty-prefix expression omitted
a separator at a bare share root. The corrected expression is
`os.path.join(folder, "_")[:-1]`. The old candidate/test/helper bytes are preserved
in `data/outputs/t/ebsx_impl_fa730bcb6d2e/blocked_snapshot/`; the original proposal,
approval and blocked review remain unchanged. The amendment approval SHA-256 is
`9a1ac3d04aa2b3f4589d9a0409fa17c2e3575f4bcd5887928f731bd5153f241a`.

Fresh independent reviews passed for the amended scanner/tests and the helper/
authority checks. A later tool-wrapper parenthesis error prevented a preparation
command from starting; it was not a failed test or scanner call. Ryan explicitly
authorized the corrected wrapper and the already-approved first test run.
The corrected binding/scope checks succeeded, then the helper ran once under
the explicit repository `.venv\Scripts\python.exe -B`, with bytecode disabled
and UTF-8 enabled.

All 26 tests passed, zero failures/errors/skips. Unittest reported 0.016 seconds;
helper elapsed time was 0.24663389999841456 seconds and command wall time was
0.583733 seconds. Structural comparison proved the executable accounting code
differs from the frozen first candidate only by the approved prefix preparation,
additional deadline check and fresh-stat query expression. All 23 bound files
and the exact fourteen-file Git scope remained unchanged across execution.

The validation receipt is
`data/outputs/t/ebsx_impl_fa730bcb6d2e/validation.json`, SHA-256
`416983627262eb332f74af528ad996aed93029ce81bc3f85b3c23d260f56cd73`.
Its log SHA-256 is
`2f5e6316d89bbc780f34773507246cf7867d46bf81a5979e4e3d032284cab1bd`;
review receipt SHA-256 is
`e1a3fd997f9aa066d3d8d12ca93e409c05518997a44ee2e686b76241d9b8ff24`.
Independent result review confirmed the counts and log/review/source bindings.
Later context-document updates are reporting changes; their earlier receipt
hashes retain their historical role as the validation snapshot.

This establishes focused correctness only. No stress benchmark, profile, full
suite or real scientific worker ran. No completed test command was repeated.
Existing profile/real resource balances, protected scientific data, embargoes,
holdouts and completed visual reviews remain unchanged. No Git mutation occurred.
The next task is a bounded timing-execution request, not an automatic benchmark.

## Synthetic profile completed; directory-prefix proposal prepared

The final integrated profiling helper passed 15 new focused tests and independent
review. Ryan then authorized its single execution. Attempt
`4932f5dc070640e3a96cf094ff86859b` exited zero and captured the known accounting
deadline as the explicitly approved diagnostic observation. There was exactly one
profiled fixture call, no returned byte total and no passing readiness result.

The scanner's recorded cumulative time was 487.581 ms; fresh `nt.stat` calls
accounted for 291.710 ms. Path joining took 71.589 ms cumulative, with nested
work included. These instrumented, incomplete timings cannot establish a full
scan duration, completed inventory count, speedup or the original real failure's
cause. Independent read-only interpretation review confirmed these limits.

The supervised attempt used 2.594 active seconds, observed peak worker memory
54,411,264 bytes and maximum monitor interval about 0.281 seconds. It recorded
zero resource overshoots and successful final accounting. Seven resource events
ended at canonical tip
`9f1a861c090e800d7e5e18b5b8cabd001915276e393623e56ff0a134f7c12cdb`.
The profile JSON SHA-256 is
`06ee889ded721f65eabe15e3e2788cc2a49dcfe6ab37b30396bc00b307b37337`;
the result receipt SHA-256 is
`f0146c994ef77d181ed47389fc9c5454ffcf81727ef2d6c422f36205035c1351`.
Evidence is under `data/outputs/t/ebsp_fa730bcb6d2e/`, with the complete checkpoint
at `data/outputs/t/ebsp_src_fa730bcb6d2e/profile_execution_continuity.json`.
The prior failed recorder, static benchmark and startup/ownership observations
retain their historical roles; successful profiling does not replace them.

Ryan subsequently approved preparing and finishing the new proposal at
`../ball_crop_candidate_retention_scan_prefix_proposal.md`. A delegated lookup
first named an absent source file; work stopped and Ryan authorized correction.
An optional external documentation retrieval then failed; work stopped again
and Ryan authorized completing the proposal from sources already retrieved.
No affected page was retried and neither interruption was a software-test or
scientific failure.

This preparation contains documentation and static review only. No runtime code,
scanner call, test command, benchmark or real worker runs in preparation. The
old 46 focused passes, 803 full-suite passes with one existing Windows skip,
first-candidate 20 passes and profiling-helper results are preserved evidence,
not validation of the proposed new candidate. Source/evidence preservation,
document scope, local links and whitespace are the applicable preparation checks.

## Scanner correctness passed; static timing failed; diagnosis proposal prepared

Ryan approved the first scanner recovery proposal with "yes I do move forward".
The separate approval is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_error_breakdown_recovery_approval_v0_1.json`,
SHA-256 `4b82583e1bbd54ab489f9ea67432d9af61acb8397ee382284ae8298a5f0cd1af`.
It did not authorize another backend, weaker limits, automatic retry or Git steps.

The separate scanner preserves the original counting-function AST except for
the ordinary-stat path expression. Twenty focused tests passed in 0.014 unittest
seconds, zero skips, exit 0; command wall time was 0.687 seconds. Their source
hashes stayed unchanged. The parent recorder's line-anchored regex missed CRLF
line endings and recorded `passed: false` with an empty parsed summary. Work
stopped; Ryan authorized correction. A separately reviewed reconciler passed
13 positive/negative parser checks and accepted the exact saved 20-pass log,
creating a new receipt while preserving the old one. No test was rerun.

All these records are under
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_recovery_implementation/fa730bcb6d2e_2026-10-04/`.
The reconciliation SHA-256 is
`8da31e6c99e29a0512dc7f0d1bc5e742236014e751612ba9383a654b0385af99`.
Its source checks and the independent AST-parity record passed before timing.

The fixed synthetic benchmark then created 12,000 files in 400 directories
using seed 0, with 12,259,360 bytes and maximum absolute path length 172.
Layout/sizes and ordinary-stat reference were saved before the first measured
accounting call. That call failed with
`ResourceLimitError: Output tree did not stabilize for complete byte accounting`.
The measured duration was `0.4908125000074506` seconds; returned bytes were null.
There was no warmup, discarded call or retry. It failed the required first-call
readiness gate; the other 29 calls and the dynamic test did not run. No after-
static reference or dynamic marker/receipt exists. The failed static receipt
SHA-256 is `f7f12382fa600f1e05d9aaf160e7aec2e064492865d30fce23c035afe4e9e3f2`.

The scanner's `time.monotonic()` deadline and wrapper's `time.perf_counter()`
duration are distinct observations. No captured internal readings, completed-
scan count or phase measurements establish their discrepancy or the slow
operation. The failure is not evidence of a disk-byte overshoot, a speedup,
actual membership churn, or performance on the real tree.

With Ryan's subsequent permission, independent read-only investigation verified
all nine bound benchmark files and matching layout/reference metadata. A separate
preparation check verified 151 original source/test/dependency bindings, three
helpers, preserved metadata for all 5,774 real files/189 directories and all
12,000 synthetic files/400 directories, plus protected absent paths. No source
or failed evidence was repaired, no scientific body was read/hashed and no
scanner, test, profile, dynamic gate or real worker was run in preparation.

The new draft is `../ball_crop_candidate_retention_error_breakdown_scan_diagnosis_proposal.md`.
Its preparation evidence is under
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_scan_diagnosis_proposal/fa730bcb6d2e_2026-10-04/`;
`preparation_before.json` SHA-256 is
`e7b8e01b920c25dea4ed3ff7d671aad82f8e46ac1c223e93d5436af57c518ba3`.
It proposes one future synthetic profiling observation, not a passing timing
benchmark. No new runtime implementation is validated or authorized by this
documentation. Earlier focused/full results retain their historical roles.

## Error-breakdown execution interruption and recovery-proposal preparation

Ryan separately authorized the eleven-file staging and commit. The staged,
working and committed bytes matched the readiness record; staged whitespace,
exact scope, correct parent, clean checkout and empty index checks passed.
Commit is `fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`. Earlier handoff verification
and independent staging-check invocation errors were corrected only after
separate permission. Their original evidence and readiness record remain intact.

The approved public summarize command exited 1 after 41.266 wall seconds.
Attempt `4adfb390f1f74a1baaec7fb178092218` was charged
`7.264999999984866` active seconds and failed with
`ResourceLimitError: Output tree did not stabilize for complete byte accounting`.
Its empty log, absent worker result, absent output directory and failed
completion were verified from logs/receipts and filesystem metadata. The exact
internal worker phase, including whether scientific inputs were reached, is
unknown. No successful summary was returned. No repair or retry followed.

The supervisor recorded peak worker memory 57,663,488 bytes, maximum whole-root
size 7,413,894,332 bytes, zero recorded time/memory/output overshoots and successful
final accounting. Source review establishes a fixed 0.5-second deadline for two
complete scans; that error is not proof of tree instability or an exceeded byte
cap. A slow scan is possible, but the historical records cannot prove its cause.

Read-only investigation verified all 3,010 canonical event links, the original
3,002-event prefix tip, exact new failed reservation/completion seals, 58 closed
attempts, 54 successes, four failures and no open attempt. New chain tip is
`e5f2a832dd961d2615daa30ca77b039ad8dbe68bcbcfa12c2437128fbc83a3b3`.
Remaining cumulative allowance is `11132.492000000013` seconds; a recovery would
retain only `292.73500000001513` seconds from the original diagnostic allowance.

Ryan subsequently authorized documentation-only recovery preparation. The new
draft is `../ball_crop_candidate_retention_error_breakdown_recovery_proposal.md`.
Preparation preserved all 5,762 original files by frozen metadata and recorded
the current 5,774-file/189-directory inventory, all 3,010 raw-event bindings and
unchanged 151 source/test/dependency plus three helper bindings. No scientific
body was opened or freshly hashed. Before-context copies and preparation records
remain ignored under
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_recovery_proposal/fa730bcb6d2e_2026-10-04/`.
No runtime code changed and no scanner benchmark ran in preparation. Prior focused/full test results
were not repeated; they do not establish that the proposed optimization works.
The recovery draft requires its own focused/full tests and fixed timing gates
after approval. Scope/link/whitespace and independent proposal review apply now.

## Approved saved error-breakdown implementation: validation complete

The new reader/formatter and two fabricated test modules passed independent
source review. They preserve existing sources, the exact 3,002-event prefix,
57 completed attempts, three earlier failures and all existing resource limits.
The focused inventory is 46 checks; the full suite contains 804 tests.
No real diagnostic worker or scientific-body read has occurred.

The new recorder passed twelve fabricated checks in 0.019 unittest seconds.
It also parsed the exact preserved previous 758-test log, including the two
known trailing diagnostic messages, without rerunning those tests. Recorder
checks exited zero and recorded immutable source, command, environment and log
bindings. Independent review of the validation/certificate orchestration passed.
Its corrected authority guard checks exact approved paths and digests before
following any manifest-referenced binding. Evidence is under
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_implementation/e71a4d216562_2026-10-02/`.
All 46 focused checks subsequently passed: zero skips, 72.28 unittest seconds
and 72.625 command wall seconds, with unchanged source/helper/recorder bindings.
The actual metadata-only dry-run also passed in 15.047 seconds, with no worker
or scientific-body access. Its log and receipt are saved alongside the tests.
The full suite exited zero: 804 tests run, 803 passed and the one existing
Windows directory-symlink skip. Unittest time was 2,040.214 seconds; command
wall time was 2,044.594 seconds. The recorder accepted the exact success block
and two known buffered diagnostic lines, with no failure markers. All 151
source/test/dependency bindings and three helper bindings remained unchanged.
The create-only certificate assembler passed and produced
`implementation_validation.json`, SHA-256
`c252a3015acd0cc037ac084db8f6a09589f0d41a23d28e2d18312b0be58ca233`.
The new manifest binds this exact certificate. No Git mutation or real
diagnostic execution occurred; separately authorized staging and committing
remain necessary before the approved worker can run.

## Interpretation execution complete; documentation-only continuation

The exact thirteen-file interpretation scope was separately authorized and
committed at `e71a4d2165623208d624c4839e9321bd9bf779ba`. After verifying the clean
checkpoint, the one approved interpretation unit exited zero and passed receipt,
source, authority, preservation and resource checks. Attempt
`7bd613d71cef48d38c15a72e9647fc10` used 40.14 active seconds. Its external worker
result SHA-256 is `07d810dcfe98bf2937d2e6bfdfbb1985cdbd05b974c3d974f6919bcb7a19fa62`.
Three create-only scientific outputs were completed and their bounded readable
summary returned after success verification. No inference, scoring or media
decoding occurred.

The metadata completion checkpoint is under
`data/outputs/ball_tracking/crop_candidate_retention_interpretation_implementation/a89cd40838b0_2026-10-02/interpretation_completion_checkpoint.json`,
SHA-256 `c6e55a921c44bd6dfa29b291dd753fb80b72637ecc86ba035802210f5bb80bf5`.
It records 3,002 resource events, 57 completed attempts, 54 successes, the three
unchanged failures and zero active workers. All 5,718 original frozen files
remain preserved on the recorded metadata/receipt basis. Previously validated
source, certificate and evidence bindings remained unchanged. The 42 focused
passes and full-suite 757 passes plus one existing Windows skip were not rerun.

During the next documentation preparation, a read-only command requested the
wrong single-file journal path and returned an error. It changed no files and
started no worker. Work stopped. Ryan's "You can move forward chat" authorized
correcting that metadata check and finishing the documentation-only proposal.
The actual `resource_events/` directory contains the expected 3,002 JSON events;
the final successful event and completion-checkpoint digest match. The proposed
new output directory is absent. No generated scientific body was opened or
freshly hashed for this preparation. Source inspection establishes that the
saved pool breakdown must use companion window IDs for its block mapping.
The new proposal remains unimplemented and unexecuted; documentation changes
do not require a full regression rerun.
Documentation checks passed for the exact four-file scope, whitespace, empty
index, unchanged HEAD and unchanged frozen proposal/approval/checkpoint hashes.
An independent source-and-metadata scope review cleared the completed draft;
it did not inspect scientific bodies or calculate experimental results.

## Interpretation recorder correction complete; original passing results accepted

Ryan approved the narrow correction with "Ok move forward chat". The new ignored
recorder reconciler passed 12 synthetic checks in 0.013 seconds and independent
source review. The checks include duplicate or failed summaries, wrong counts
and durations, altered skips, reordered or unexpected diagnostics, incorrect
commands, changed file bindings and refusal to overwrite an existing record.
The correction verifies its own exact test command, source bindings and receipt.

The reconciler accepted the preserved 42-test focused run and 758-test full run
from their exact commands, exit-zero results, unique unittest summary blocks,
known Windows skip and unchanged 147 source/test/dependency files plus three
helper sources. It permits only the two exact diagnostic lines observed after
the full-suite success summary. The original recorder's failed receipt, original
logs, original scripts and historical reviews remain unchanged. A separate
acceptance record distinguishes that recorder failure from the passing tests.
The full suite was not rerun and no project source or test file was edited.

Evidence remains under
`data/outputs/ball_tracking/crop_candidate_retention_interpretation_implementation/a89cd40838b0_2026-10-02/`.
The reconciliation SHA-256 is
`d9bf5e6e330f4153657eb1beccdaf58adb85dbcb0afbc684ecf35c7df6bc45a5`;
the implementation certificate SHA-256 is
`fd18eb13f5b9d88251b21b47282e82cba3c17226d602482a8faa180c686424cf`.
The interpretation manifest now binds the completed certificate. No scientific
body, video or holdout content was opened, no real worker ran and no Git mutation
occurred. Staging and committing the exact thirteen-file scope remain separately
unauthorized; the actual interpretation still requires that clean checkpoint.

## Candidate-retention interpretation: tests passed; recorder stopped

The bounded interpretation implementation and two test modules are new files;
all 143 earlier source/test/dependency bindings and three ignored helper sources
remain unchanged. Independent source review cleared the new runner and pure
summary formatter. Review fixes enforce sample/final-counter consistency,
exact authored output hashes and refusal of incomplete journal publications.

The recorded focused run passed 42 tests. The full unittest process exited zero
after 758 tests in 1,846.555 seconds: 757 passed and one existing Windows
directory-symlink test was skipped. All 147 current source/test/dependency
bindings and three helper sources stayed unchanged. The full log SHA-256 is
`344fd3a54eeae912df45678fde0876af2d7d9c261497ec3efe11a5555de92534`.
Logs, snapshots, reviews and receipts are under
`data/outputs/ball_tracking/crop_candidate_retention_interpretation_implementation/a89cd40838b0_2026-10-02/`.

The validation recorder itself exited one after writing a failed receipt. It
incorrectly required the last combined-log line to be the unittest status;
buffered `Saved context: context.jpg` and `Saved identities: identities.jpg`
messages followed the unique `OK (skipped=1)` summary. This is a recording
failure, not a failed unittest. Its receipt remains `passed: false` and is not
rewritten or silently treated as complete. The certificate assembler shares
the terminal-line assumption and has not run.

Work stopped under Ryan's stop-on-new-failure instruction. No recorder repair,
test rerun, certificate assembly, scientific read, real interpretation worker
or Git mutation followed. The exact proposed correction is documented in
`../ball_crop_candidate_retention_interpretation_implementation.md`. Separate
approval is needed to fix the recorder and reconcile the saved successful
test result while preserving the failed receipt. The experiment history remains
2,966 events and 56 completed attempts, including the same three failures;
all clip reviews, embargoes and sealed holdouts remain preserved.

## Possession 001 — reviewed behavioral baseline

- decoded frames: 499;
- camera homographies: 499;
- possible player-frame pairs: 4,990;
- final coordinate rows: 4,948 (99.16%);
- complete ten-player frames: 473/499 (94.79%);
- trajectory corrections: 98;
- interpolated coordinates: 58 across 23 bracketed gaps;
- remaining gaps: 42 leading observations without a left anchor;
- observed outside-court positions preserved: 22;
- audited interpolated outside-court positions: 3;
- visual review completed through frame 498.

This possession defines behavioral compatibility, not the empirical generalization result.

Sources: Chat 05 opening message `a0b4f63f-838f-49f5-a825-e4f2bfb1f971`; `docs/pipeline_generalization.md`.

## Possession 002 — failure-discovery and hardening case

Possession 002 exposed camera-motion, identity-contamination, team-balance, and path-generalization problems. Important reviewed findings included raw tracks that changed players, incorporated bench/referee phases, or crossed team appearance boundaries. These failures drove explicit splits, match accepts/rejects, config-driven review helpers, geometry safety, and resumable execution.

Possession 002 should not be summarized only by a final coverage number; its durable value is the failure taxonomy and the refactors it forced.

Sources: Chats 05–06; committed `configs/possession_002_*` review files; commits `d1e428a` and `8bd9486`.

## Possession 003 — empirical generalization gate

Possession 003 completed all 21 stages against frozen source commit `8bd9486` without possession-specific source edits.

| Metric | Result | Gate |
|---|---:|---:|
| Homographies | 500/500 (100.00%) | 100% required |
| Coordinate coverage | 4,921/5,000 (98.42%) | at least 95% |
| Complete ten-player frames | 431/500 (86.20%) | at least 85% |
| Final identities | 10 (5 white, 5 dark) | expected 10 and 5/5 |
| Unresolved reviews | 0 | 0 |
| Coordinate-key violations | 0 | 0 |
| Final motion-jump candidates | 0 | reviewed zero |
| Final outside-court positions | 0 | audited |

Synchronized visual review reached the final frame, and generated data/media remained uncommitted. The empirical gate passed, unlocking ball tracking.

Sources: `configs/possession_003_generalization_evidence.json`; `docs/pipeline_generalization.md`; commit `7f603af`.

## Migration-time regression

On 2026-08-22, the clean local checkout at `1954053` passed all 56 discovered unit/regression/safety tests with bytecode writing disabled. This verifies the preserved checkout, not GitHub's later README-only merge.

## Ball annotation — Possession 001 pilot reference

On 2026-08-23, Ryan completed and visually reviewed all 25 approved source
frames (`375..399`) from Possession 001. The set contains 25 labeled rows, 25
geometry points, and no unlabeled or excluded rows. The approved review evidence
is bound to the exact source video and draft annotation hashes; finalization
changes only `review.status`, `review.reviewer_id`, and
`review.reviewed_at_utc`. No ball coordinate or frame-level semantic decision
changes during that transition.

The reference set uses the approved single-annotator review path. It is suitable
for the protocol pilot and initial detector experiments, but it does not claim
inter-rater agreement, unbiased benchmark sampling, cross-game generalization,
or a completed ball-tracking quality gate.

## Ball annotation — Possession 002 pilot reference

On 2026-08-23 America/Phoenix (`2026-08-24T00:30:19Z`), Ryan completed and
visually approved all 25 source frames (`318..342`) from Possession 002. The set
contains 17 partially visible geometry estimates and eight reviewed
`not_visible` occlusions. Sixteen geometry points are localization eligible;
frame 335 preserves an ambiguous visible estimate for audit context but excludes
it from localization scoring.

The reviewed sequence preserves an internal no-geometry gap at frame 330 and a
trailing no-geometry interval at frames 336–342. No hidden-ball coordinate is
interpolated or invented. The approved review package reaches frame 342 and is
bound to the exact source, neutral bundle, draft annotation, generator, and
manifest hashes. Finalization changes only `review.status`,
`review.reviewer_id`, and `review.reviewed_at_utc`.

Like Possession 001, this is a single-annotator pilot reference suitable for
initial detector experiments. It does not claim inter-rater agreement,
unbiased benchmark sampling, cross-game generalization, or a completed
ball-tracking quality gate.

## Ball annotation — Possession 003 pilot reference

On 2026-08-23 America/Phoenix (`2026-08-24T01:05:50Z`), Ryan completed and
visually approved all 25 source frames (`416..440`) from Possession 003. The set
contains five fully visible observed centers and 20 partially visible amodal
center estimates. All 25 identities are `certain`, all 25 geometry points are
localization eligible, and no geometry gap, interpolation, excluded row, or
unlabeled row remains.

The annotation has geometry on every frame, and the center sequence is visually
continuous through final frame 440. Visual review explicitly included the
motion slowdown around frames 432–434 and the overlap-heavy final frames. The
approved package is bound to the exact source, neutral bundle, draft annotation,
generator, and manifest hashes. Finalization changes only `review.status`,
`review.reviewer_id`, and `review.reviewed_at_utc`; the frame-level decision
payload is unchanged.

The three reviewed pilot references now total 75 labeled frames, 67 geometry
points, 66 localization-eligible positives, eight reviewed `not_visible`
negatives, and one visible ambiguous frame intentionally excluded from
localization scoring. These are suitable for initial detector experiments but
remain a curated one-game protocol pilot, not an unbiased benchmark,
cross-game validation set, or completed ball-tracking quality gate.

## Ball detector — label-blind baseline precommit

On 2026-08-23 America/Phoenix, before any selected-window detector prediction
was generated or viewed, Ryan approved three 25-frame evaluation windows per
possession:

| Possession | Representative | Challenge | Holdout |
| --- | ---: | ---: | ---: |
| `possession_001` | `50..74` | `200..224` | `300..324` |
| `possession_002` | `250..274` | `25..49` | `200..224` |
| `possession_003` | `300..324` | `150..174` | `250..274` |

The selection used only verified source pixels and metadata. It applied fixed
edge, pilot, historical-prediction, and between-split separation guards; a
deterministic SHA-256 holdout rule; robust raw-video representative metrics; and
a frozen motion/blur/variability challenge score. Prediction-free 5-by-5 source
contact sheets confirmed uninterrupted live play and no cuts or corruption.
Post-selection congestion observations did not enter the numeric ranking. The
complete reproducibility record and the P001 stale temporary-sheet
reconciliation are in `docs/ball_detector_baseline_selection.md`.

The accompanying feature foundation freezes RF-DETR Medium 1.9.1, the official
weight filename and SHA-256 with package-resolved absolute-path verification,
CUDA FP32 uncompiled inference at 576 by 576,
the raw COCO `sports ball` candidate contract, an inclusive `0.01` export floor,
strict source/Git/runtime provenance, atomic resumability, and an unselected
confidence/localization-radius scoring grid. Focused source/detector validation
passed 129 tests; the full repository suite passed 264 tests. One Windows-only
directory-symlink capability test was skipped in both runs. Bytecode writing was
disabled and formatting checks passed.

The installed RF-DETR 1.9.1 package's real sparse 80-class mapping passed the
adapter contract, and a non-inference construction loaded the frozen weights on
CUDA with the declared 576-pixel resolution, 300 queries, 90 detector classes,
and `num_select=27300`. No source or synthetic frame was supplied. RF-DETR
reported that the older checkpoint lacks `_kp_active_mask`; package source
defines that item as a deterministic keypoint-schema buffer rather than a
learned ball-detection weight.

Only the three reviewed protocol pilots are ready for inference. The nine new
windows remain `annotation_pending_prediction_embargo`, the detector output
directory is absent, and no operating point or ball-detector quality gate has
been selected.

## Ball detector — development execution and visual approval

On 2026-09-19 UTC (2026-09-18 America/Phoenix), the approved versioned
development release completed at clean commit
`84bcc8da143e54ff17a28b39db0e70c4b8b299c8`: 150/150 inference frames,
22,931 raw candidates, two separate 45-cell scoring grids containing 270
per-window reports, and six synchronized comparison clips. Implementation
validation ran 299 tests: 298 passed, one existing directory-symlink capability
test skipped. No production code changed during the later review-record step.

Ryan subsequently approved the six linked comparison videos as a solid starting
point while noting small detection blips. His exact statement is preserved in
`configs/ball_tracking/reviews/rfdetr_medium_development_candidate_comparison_review_record_v0_1.json`
(SHA-256 `a60dea646736135620fb97eba9f1985f7b06f0c7bfc7abee38537580c05f4dba`).
Both bundle-integrity checks, all six original/playback video hash pairs, and
59 protected file hash/Git-blob bindings were reverified when recording approval.
The original execution record remains unchanged as an earlier pending-review
snapshot. The approval receipt is a later audit record, not a new execution permit.

Visual approval does not establish complete trajectories: these remain
independent frame detections. At the two 10-pixel display cells, representative
recall is 62.7% at confidence 0.20 and 52.0% at 0.35; challenge recall is 68.6%
and 58.6%, respectively. P001 remains the weakest possession. All original
v0.1 embargo paths remain absent; only six separately authorized v0.2 development
outputs were generated. Three test holdouts remain sealed, and no operating
point, quality gate, or model winner was selected. A temporal-association
experiment is proposed but has not run.

## Ball temporal association — synthetic implementation validation

The first temporal-association experiment is authorized by Ryan's "lets move
forward" response to its linked design. Separate derived contracts, 54-variant
association, scoring, resumable execution, and synchronized review support are
implemented without changing the frozen detector or annotations. The manifest
specification SHA-256 is
`ef2f7a2a77f334c94d0efc045311c6fd4a3cc86695aec84934bacbfb06605ab5`.

The final focused suite passed 25 tests. The full repository suite ran 324
tests in 147.691 seconds: 323 passed and one existing directory-symlink
capability test skipped. Tests used `.venv` with bytecode disabled. Synthetic
integration exercised all 324 observation files, 1,620 per-window reports,
two distinct 270-cell pools, complete review-video decoding, final-frame
inclusion, exact resume, and tamper rejection. Raw control metrics match the
established evaluator. The first full-suite attempt was stopped after an
agent-inspected synthetic preview prompted a readability fix; the reported
full-suite result is the subsequent run against final code.

Real-data dry-run passed for exactly six saved development windows and 150
frames. Prior protected files, saved detection hashes, and nine absent parent
prediction paths were reverified. No real temporal outputs exist yet. Staging
and committing the documented 13-file scope remain separately authorized steps
before execution at a clean checkpoint. The three holdouts remain sealed, and
operating-point and quality-gate selections remain unset.

## Ball temporal association — execution and inspected evidence

Ryan separately authorized the 13-file implementation commit with "yes commit".
Commit `6769e07476da09d858fa42f82aace024d21f7735` then ran the already approved
experiment at a clean checkpoint: 324 saved-detection observation files,
1,620 per-window reports, two separate 270-cell aggregate pools, and 12 review
clips. All 270 raw-control reports reproduce the earlier detector metrics and
per-frame outcomes, excluding the intentionally different derived input count.
All 2,412 bound review assets verified; 12 original videos and their 12 H.264
playback copies fully decoded through their 25th frame. The agent inspected
the 12 final-frame closeup sheets without claiming all-frame visual inspection.

Ryan then stated "inspected. please move forward" in response to the linked
temporal review package. The new
`configs/ball_tracking/reviews/rfdetr_medium_temporal_association_visual_review_record_v0_1.json`
binds that statement to the exact 12 clips and review artifacts. Its timestamp
records receipt creation, not an invented event time. This completes the
requested inspection; it does not select a tracker or approve a quality gate.
The original execution record and visual manifest retain their historical
pending-review state. All source media and generated outputs remain ignored.

A read-only closeout over all saved cells found that 63 representative and
29 challenge tracklet cells gain correct matches versus same-cell top-one;
every gain also adds false guesses. The 360 comparisons and 270 raw miss
decompositions are recorded in
`data/outputs/ball_tracking/temporal_closeout/6769e07476da/diagnostic.json`,
SHA-256 `845dc1d7e7ead0ec952c27985595878c3e13488af54c1dc1f946ae207d6cce77`.
These are descriptive correlated comparisons, not independent trials.
At the two displayed confidence settings/radius, every tracklet variant loses
correct matches in both pools. The diagnostic also identifies detector and
confidence-filter losses that association cannot recover with unchanged centers.

Receipt creation rehashed the review assets, playback clips, observations,
reports, six annotations/raw detections, and 59 protected files. All bindings
matched; all nine original prediction output paths remain absent. No new
production code or detector inference was introduced during closeout, so no
new full-suite result is claimed. The next fixed-crop comparison is a concrete
proposal awaiting its own experiment approval, not an executed result. All
three holdouts stay sealed; operating-point and quality-gate fields stay null.

## Ball detector crop comparison — approval and implementation

Ryan approved the linked fixed-crop experiment with "yes i approve". Its new
approval receipt binds the unchanged proposal to executable specification
`3384a930d8633b202b689857de2bea4939277a2d2f0c3da483c2c48e9e9ef023`.
Separate candidate, inference/resume, scoring, and review modules preserve the
existing whole-frame detector contract. Crop geometry is independent of labels;
both coordinate systems, duplicates, original candidate references, timing,
and CUDA peak allocated bytes are recorded. The existing player pipeline and
the approved temporal design/manifest remain unchanged.

Final focused validation passed 18 synthetic tests in 74.915 seconds. Coverage
includes all 600 model calls, exact and interrupted resume, whole-frame control
parity across every cell, all 1,080 per-window scores, 12 fully decoded review
videos, every final frame, and 1,950 supporting images. It also checks dirty-Git
refusal, label-blind loading, all nine original embargo paths, changed input
scope/provenance, and tampering. The first focused run found a sidebar-width
rendering mismatch and a synthetic class-ID fixture mismatch; both were fixed.

Real-input preflight passed against the source clips, frozen RF-DETR package
and weights, and installed RTX 5070 CUDA runtime. No model prediction ran.
Agent visual inspection covered synthetic comparison and closeup previews only.
The final full suite ran 342 tests in 223.084 seconds: 341 passed and one
existing directory-symlink capability test skipped. Bytecode writing was
disabled. Formatting, new-file syntax/whitespace, and exact 15-file scope
checks passed. The final audit reverified 59 protected files, six raw
predictions, all reviewed labels, the immutable proposal, and the nine absent
embargo outputs. Logs, synthetic previews, and hash/Git-blob validation records
remain ignored under `data/outputs/ball_tracking/tiled_implementation_validation/`.

Separate staging and commit approval are still needed for the documented
15-file implementation checkpoint. The already approved experiment may run
after that clean checkpoint, with human visual review afterward. No operating
point or quality gate is selected, and all three test holdouts remain sealed.

## Ball detector crop comparison — committed execution and review handoff

Ryan authorized staging with "yes stage" and the exact 15-file commit with
"commit please". Commit `1a9479f83a1766d8979fad07c604bc686d3c52c6` has parent
`6769e07476da09d858fa42f82aace024d21f7735`; its complete tree and all 15 Git
blobs match the previously validated staged scope. The index and worktree
were clean after commit. Nothing was pushed.

The already approved fixed-crop experiment then ran at that clean commit:
600 crop calls across 150 source frames in exactly the six declared windows,
600 immutable view checkpoints, and six separate candidate files. All stages
used the repository `.venv` with bytecode disabled. End-to-end inference took
136.28 seconds; synchronized model calls totalled 96.02 seconds, including
16.32 seconds for the first call. Median four-crop frame time was 0.532 seconds,
and peak PyTorch CUDA allocation was 0.220 GiB. Saved whole-frame timing was
not measured, so no runtime ratio is claimed. The installed model emitted
the same deterministic keypoint-buffer warning recorded for the frozen control;
package, weights, runtime, precision, and target-class rules were unchanged.

Scoring produced 1,080 per-window reports and 180 aggregate cells in each
separate representative/challenge pool. A read-only audit compared all 540
saved-control raw/top-one cells to the prior reviewed temporal reports.
Scoring metrics and per-frame outcomes match exactly; adapter-stage input and
below-threshold bookkeeping counts are excluded. Candidate provenance,
all 600 crop checkpoints, six saved detection files, six annotation bindings,
and 59 protected files verified. All nine original embargo paths stay absent;
the three holdouts remain sealed.

Rendering produced 1,962 hash-verified assets: 12 synchronized four-panel
videos, 300 comparison PNGs, 300 closeup sheets, 1,200 native overlays, and
150 crop-context images. All 12 originals and separate H.264 playback copies
fully decoded through 25 frames at 5 fps. The agent directly inspected every
final-frame closeup plus a hidden-frame comparison and crop-boundary context;
all-frame human visual review is pending. This does not replace Ryan's review.

At both displayed confidence settings and 10-pixel radius, both pools gain
matches with crop inputs but also add false guesses. Individual deteriorations
are preserved: P002 challenge frames 48-49 lose top-one matches at both views.
The full grid and per-frame recovered/lost lists remain available. No setting,
winner, quality gate, or generalization claim is selected.

The ignored handoff is
`data/outputs/ball_tracking/tiled_execution/1a9479f83a17/review_guide.md`.
The corresponding `execution_record.json` has SHA-256
`4d7977be4e08c9e70df438a007cbe92de4be60bed14eccc4d75a581aff137b52`.
The review bundle is
`data/outputs/ball_tracking/tiled_development/rfdetr_medium_tiled_development_comparison_v0_1/review/a007aa4b358587789f7ef1f28b1c66b5/`.
Execution and verification completed before these three context-file edits.
No new code changed, so the existing 18 focused passes and 341 full-suite
passes plus one skip were not rerun; the context diff received a whitespace
check. Next is Ryan's inspection of all 12 clips through their final frames.

## Ball detector crop comparison — completed human review

Ryan responded to the complete 12-clip review package with "all of them look
pretty good to me. even P002 challenge". The separate receipt
`configs/ball_tracking/reviews/rfdetr_medium_tiled_development_comparison_visual_review_record_v0_1.json`
(SHA-256 `6e108189b792d505c97adbcfcce5aa635a6e140893a6306e0c08bfe910218adb`)
binds his exact statement to the execution commit, review manifest, both scoring
pools, all original/playback clips, and final-frame closeups. Receipt time is
creation time; no separate user-message event time is invented. The original
pending-review evidence remains unchanged as historical provenance.

Read-only closeout rehashed all 1,962 review assets, 12 playback clips and final
closeups, two pool reports, six crop candidate files, and six saved whole-frame
detection files; all hashes matched. All nine original prediction embargo paths
remain absent, and all three holdouts remain sealed. No experiment or tests were
rerun and no production code changed. Visual review completion does not select
an operating point, quality gate, winner, or authorize another experiment or
Git mutation. The previously reported numerical gains and losses remain valid.

## Ball detector crop comparison — saved-result closeout and next design

Following "lets move forward chat", a new ignored diagnostic extracted all
180 same-cell aggregate crop/whole-frame comparisons and 48 displayed
per-window reports from the two bound scoring pools. It checked displayed
per-frame TP/FP/FN/duplicate/hidden counts and exact raw/top-one miss
decompositions. Label-blind overlap counting retains 300 frame/display
records with original cross-crop candidate references. No candidate was
suppressed, no selected output was created, and no detector or scoring ran.

Diagnostic SHA-256:
`87a2e57e147da2907d42286bc6d81d333c011eb5609ba3f71c09291265c0cc3d`;
path: `data/outputs/ball_tracking/tiled_closeout/1a9479f83a17/diagnostic.json`.
The new results note distinguishes extra qualifying centers from geometric
overlap and preserves all-grid losses as well as gains. It does not select
a winner or interpret correlated grid cells as independent trials.

The next recent-history ranking proposal binds this diagnostic, reviewed crop
receipt, saved candidates, scoring pools, labels, and exact six-window scope.
Its SHA-256 is `f9a3ae162d2227ddffab9a9da68811ea629cf7dfa6ffa48625546ac1ab5ad2ca`.
It remains non-executable and awaits specific experiment approval; no selector
support or experiment validation is claimed. No production code changed, so
the prior code-test result remains unchanged. Git staging and other mutations
remain unauthorized; all original embargoes and holdouts are preserved.

## Approved saved crop candidate ranking — implementation validation

Ryan's "I approve chat" authorizes the exact saved-six-window, 45-variant
experiment. A separate approval receipt binds the unchanged proposal; the
new executable specification digest is
`c3541d45fcc4db384d2222a56cd4fe18885c7212ad9f7c77b0e933bdd3eb2fe4`.
This approval does not authorize staging, committing, pushing, PRs, or merging.

Four new modules implement exact five-frame causal ranking, immutable/resumable
execution, separate scoring, and six-panel synchronized review. New synthetic
tests cover exhaustive small-graph agreement, deterministic ties including
empty-score-zero, lower-confidence recovery and stable-clutter failure,
tight/wide motion limits, cap losses, duplicate retention, causal prefixes,
window reset, gaps/expiry without extrapolation, hidden-frame false alarms,
malformed inputs, label-blind loading, immutable inputs, dirty-checkpoint
refusal, exact scope and all nine embargo paths, and tampered provenance.

All 21 focused tests pass in 97.651 seconds. The full suite runs 363 tests in
325.472 seconds: 362 pass, with one existing directory-symlink skip because
Windows symlinks are unavailable. Both commands use
`.venv` Python with `-B`. The synthetic integration reproduces all 540 saved
crop raw/top-one outcome cells across 1,350 reports and two 225-cell pools;
adapter input/below-threshold bookkeeping is the sole parity exclusion.
It creates all 270 outputs, interrupts after seven and resumes only the
remaining 263, verifies exact reuse, and rejects changed derived outputs.
Twelve synthetic review clips fully decode all 25 frames at 5 fps. Their
2,412 assets have complete inventories and hashes, including final frames.
The agent directly inspected the synthetic comparison and unmarked-source
closeups; Ryan's real ranking visual review remains pending execution.

Real-input read-only preflight verifies six windows, 150 source frames,
45 variants, and zero model calls. The real ranking output root remains absent.
The completed crop inference/scoring/rendering were not rerun. No upstream
player, detector, crop, tracklet, or label decision changed. The prior three
context-file edits and historical snapshots remain preserved.

The final `checkpoint_audit.json` binds the exact 15-file scope and successful
test logs, all 59 unchanged protected Git/SHA-256 bindings, six saved detections,
six finalized labels, and frozen proposal/crop/review bindings. It confirms
all nine original embargo paths absent, all three holdouts sealed, an absent
real ranking output root, successful `git diff --check`, Python/JSON parsing,
and refusal to execute before the clean implementation checkpoint.
All generated synthetic outputs, previews, logs, and audits are ignored under
`data/outputs/ball_tracking/crop_ranking_implementation_validation/`.
The index remains empty at branch `codex/ball-detector-baseline`, HEAD
`1a9479f83a1766d8979fad07c604bc686d3c52c6`. No operating point, quality gate,
winner, holdout release, staging, commit, push, PR, or merge was performed.
Next is separately authorized staging/commit of the exact validated 15-file
scope, followed by the already approved real experiment and Ryan's final-frame
review. No unrun manual command or player-pipeline rerun stage is involved.

## Saved crop candidate ranking — committed execution and review package

Ryan separately approved staging the exact validated 15 files and committing
them as `feat(ball-tracking): add approved crop candidate ranking`, each with
"I approve" in response to that specific step. Commit
`3c4894656fd5da11708a54089444d41f0a6f7773` has the expected parent
`1a9479f83a1766d8979fad07c604bc686d3c52c6`, exact file scope and staged blobs,
and a clean worktree/index. Separate ignored staging/commit receipts are under
`data/outputs/ball_tracking/crop_ranking_implementation_validation/`.
Nothing was pushed. The unchanged implementation retains 21 focused passes
and full-suite 362 passes with one existing Windows directory-symlink skip.

Real execution at the clean new commit completed all 270 derived outputs in
51.13 seconds with zero new model calls. It used exactly six saved development
crop files and the approved 45 variants. Scoring completed in 60.65 seconds:
1,350 per-window reports and 225 aggregate cells per separate pool. All 540
saved crop raw/top-one scoring cells reproduce the prior reviewed outcomes;
only adapter input/below-threshold bookkeeping is excluded from parity.

Rendering plus deterministic verification of the new scoring outputs took
251.09 seconds. All 2,412 review assets were hash-verified: 12 videos, 300
comparison PNGs, 1,800 native overlays, and 300 closeups. All 12 originals and
12 separate H.264 playback copies fully decoded 25 frames at 5 fps, including
each window's final frame. Original crop inference/scoring/rendering were not
rerun. No label, detector, tracklet, or upstream player decision changed.

The agent inspected all 12 final-frame closeups, P003 hidden frame 165 at 0.20,
P002 representative 262's regression, and P002 challenge 48's recovery. This
is structural/targeted visual inspection; Ryan's full new clip review remains
pending. The guide links all clips, final evidence, P002 gains/losses, and P003
hidden frames 165-169 and boundaries 164/170/174.

Descriptive findings at 0.20/10 pixels: wide history changes representative
top-one 51 TP/23 FP to 54/19 and challenge 59/13 to 63/6. Tight history has
29/37 representative and 53/13 challenge. At 0.35/10, wide changes 50/19 to
51/17 representative and 55/6 to 58/2 challenge. P002 challenge 48-49 recover
at both settings; P002 representative 262 loses while 258 recovers. Tight
loses many matches, including P003 challenge final 174. Across all 45 grid
cells per pool, wide has 37/3/5 representative gains/ties/losses and 45/0/0
challenge; tight has 0/0/45 in both. Grid cells are correlated and do not
constitute independent trials. No winner, operating point, or gate is selected.

All 74 protected Git/SHA-256 bindings matched through final execution audit;
all nine original embargo paths remain absent, and the three holdouts remain
sealed. The execution evidence is under
`data/outputs/ball_tracking/crop_ranking_execution/3c4894656fd5/`, including
`review_guide.md`, `results_summary.md`, `score_audit.json`, and the final
`execution_record.json` (SHA-256
`95c0b8f92c8af1fde8a842bf7e4bd6993b87880cfbc2a690ae758bf267a14b5d`).
The actual review bundle is
`data/outputs/ball_tracking/crop_candidate_ranking/rfdetr_medium_crop_candidate_ranking_v0_1/review/b7e93ff579f3d8d6069109c069a5a56d/`.

Only after the clean execution audit were these three context files updated
as intentional unstaged notes. The index remains empty; no further Git step
is authorized. No code changed or tests needed repeating. The context diff
receives a whitespace check, with its new hashes saved in an ignored handoff.
Next: Ryan reviews all 12 clips through their final frames. No unrun manual
command or upstream player-pipeline rerun is involved.

## Saved crop candidate ranking — visual-review response recorded

Ryan replied "looks good to me" after being given the 12-clip guide and the
first embedded clip. A separate evidence-bound receipt records package-level
review completion in response to that requested scope. The exact statement
does not enumerate the clips or independently attest each final frame; the
receipt does not invent those details or claim per-frame/quantitative approval.
Receipt creation time is distinguished from the unknown user-message timestamp.

The new receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_ranking_visual_review_record_v0_1.json`,
SHA-256 `21d896cd6842fc28293f3196ecce3b2e3dc81d6ae65c694a0aaa93fb753054a5`.
It binds the execution commit, approved manifest, scoring reports, review
manifest/guide, all 12 original/playback clips, and final comparison/closeup
images. Older pending-review snapshots remain immutable historical evidence.

Read-only closeout rehashed all 2,412 review assets, 12 playback clips,
270 derived outputs, two pool reports, six crop inputs, six saved detections,
and six finalized labels. All bindings matched. Protected committed blobs
and all 71 non-context protected worktree files remain unchanged. The three
intentional context-file hashes matched the prior handoff before this update.
All nine embargo paths remain absent, and all three holdouts remain sealed.

No selection, inference, scoring, rendering, or code tests were rerun; the
prior 21 focused passes and full-suite 362 passes plus one skip still apply.
The new receipt parses as JSON and the context diff receives a whitespace
check. Branch/HEAD remain `codex/ball-detector-baseline` at `3c4894656fd5`,
with three unstaged context edits, one untracked review receipt, and an empty
index. No staging, commit, push, PR, or merge was performed.

Favorable visual feedback does not remove the recorded numerical losses or
select a method, operating point, quality gate, or new experiment. Next is
read-only analysis of saved misses/path choices before proposing another
design; no holdout access or rerun is needed for that analysis.

## Saved crop ranking — mechanism diagnosis and next design

After "move forward", a create-only diagnostic joined immutable saved scoring
outcomes and endpoint traces. It invoked no detector, selector, scorer or
renderer. All 540 history/window/radius cells partition exactly into no match
at export floor, confidence loss, top-twenty cap loss and additional ranking
loss. The last category also separates wrong current emissions from null
observations. An independent read-only calculation reproduced all counts.

At radius 10/confidence .20, representative tight losses are 5+8+0+33=46;
wide losses are 5+8+0+8=21. Challenge tight losses are 0+7+0+10=17; wide
losses are 0+7+0+0=7. At .35, the respective partitions are 5+11+0+30=46,
5+11+0+8=24, 0+12+0+8=20, and 0+12+0+0=12. There is no cap loss in any
of the 120 .20/.35 history/window/radius cells. Proximity of a low-confidence
exported candidate to a label is not proof of reliable ball identity.

The diagnostic binds its generator and inputs, verifies all 270 derived
outputs and 71 protected non-context files, and records 180 aggregate cells,
600 display frame outcomes and 88 detailed endpoint traces. It is
`data/outputs/ball_tracking/crop_ranking_diagnosis/3c4894656fd5/diagnostic.json`,
SHA-256 `b5fc30f8dd8e5bd4b8a7c1bf98bf9e51108cdd3cc45397dd6a12fe614a84014d`.
The prior three context hashes and review receipt matched before updating
context. All nine embargo paths remain absent and all three holdouts sealed.

Results and case details are in `../ball_crop_candidate_ranking_results.md`.
P002 262 is a wrong-path scoring choice despite available correct continuity;
P002 258 reveals a ninefold motion-cost change without changing that useful
path's admissibility. P003 has both motion-gate exclusions and false singleton
starts while hidden. Stored score margins compare endpoint hypotheses,
including old/empty alternatives, and are not object-level probabilities.

The next concrete design is `../ball_crop_motion_factorial_proposal.md`, bound
by `configs/ball_tracking/proposals/rfdetr_medium_crop_motion_factorial_v0_1.json`
(SHA-256 `66e7c9aae8c66747d62a480d00c256f1e196df3044d5284be501a76a1edd1c64`).
Its independent edge/cost grid adds two combinations while retaining all
existing controls. Counts, mechanism claims and scope received independent
read-only review. No new experiment approval, implementation or execution is
claimed. The new output root remains absent.

No production code changed and no code tests were repeated; the previous 21
focused passes and full-suite 362 passes plus one skip remain applicable.
The proposal's JSON, hashes, exact input/control bindings, counts and whitespace
receive validation. HEAD remains `3c4894656fd5`, the index stays empty, and the
worktree has three intentional context edits plus four untracked scope files.
No staging, commit, push, PR or merge occurred. The final ignored handoff saves
their exact hashes. No upstream decision changed or manual command is unrun.

## Crop motion factorial - approved implementation validation

Ryan approved the exact new comparison with "I approve chat". The separate
receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_motion_factorial_approval_v0_1.json`
(SHA-256 `5169aee6b162494bf4650c308728459f499ecd9b280242d6c36a43411e962a5d`).
The new executable manifest is under `configs/ball_tracking/crop_motion_experiments/`;
specification digest excluding authorization is
`51bc58477f5e1273e4ec83588003861f3b095ae46923b46915905ca4600f829f`.
Approved proposal/design bytes remain immutable. No Git step is authorized.

All 23 focused tests pass in 191.201 seconds. The full suite runs 386 tests:
385 pass and one existing Windows directory-symlink test skips in 482.413
seconds. Python bytecode is disabled; hashes for the four source modules and
new test file were recorded before the full run and verified afterward. Logs and synthetic
previews are in `data/outputs/ball_tracking/crop_motion_implementation_validation/`.

Tests cover independent exhaustive path enumeration across all four parameter
pairs, inclusive edge limits, independent unclipped normalization above one,
full legacy control traces, deterministic path/endpoint/empty ties, gaps and
expiry, cap/threshold losses, duplicates, causality and window reset, immutable
inputs, hidden-frame false alarms, label-free selection, dirty-checkpoint
refusal, exact approval/window binding, all nine original embargoes, and
rebound crop-content mismatch/tampered-output refusal.

Synthetic integration creates 378 derived outputs with interrupted-run resume,
1,890 per-window reports and 315 aggregate cells per pool. All 270 saved trace,
1,350 report and 450 aggregate control checks pass. The synthetic review has
3,012 assets: 12 fully decoded 25-frame/5-fps clips plus 3,000 PNGs. The agent
inspected the nine-panel comparison and closeups. Exact unmarked source pixels
are verified separately. Synthetic inspection establishes rendering behavior,
not real ball-tracking quality; Ryan's new review remains pending execution.

Read-only real-input preflight verifies six windows, 150 frames, 63 variants
and zero model calls without invoking ranking or creating real outputs. The
new output root is absent. The final `checkpoint_audit.json` binds the exact
15-file scope, successful logs and preview hashes; it verifies all 71 protected
non-context files, four prior untracked evidence/design files, 270 saved ranking
outputs, two saved pools, six crop/whole-frame inputs and labels, and unchanged
approved documents. JSON/Python parsing, whitespace, empty index and actual
dirty-checkpoint refusal pass. All nine original embargo paths remain absent
and all three holdouts stay sealed. No completed real experiment was rerun.

HEAD remains `3c4894656fd5da11708a54089444d41f0a6f7773` on
`codex/ball-detector-baseline`. Preserve three intentional unstaged context
edits and 12 new scope files. No staging, commit, push, PR or merge occurred.
Next is separate staging approval for the exact validated scope, then separate
commit approval. Existing experiment approval permits the fixed new execution
after that clean checkpoint; do not request it again. No operating point,
quality gate or holdout release is selected, no upstream player decision
changes, and no manual command was supplied but left unrun.

## Crop motion factorial - clean execution and pending visual review

Ryan separately approved staging the validated 15-file scope ("yes you may mr
chat sir") and committing it ("yes you may"). Commit `2274ab6097cd841421e2b606f723b047cd7dc62b`
on `codex/ball-detector-baseline` has the expected parent, title, exact file
scope and blobs. No push, PR or merge occurred. The existing experiment approval
then permitted execution at the clean checkpoint with an empty index.

Selection produced all 378 outputs from six saved crop windows and 63 variants
in 87.632 seconds. Scoring produced 1,890 reports and 315 aggregate cells per
pool in 113.247 seconds. All 270 complete control traces, 1,350 control reports
and 450 aggregate cells reproduce saved evidence exactly. An independent saved
report extraction checked all 1,080 history/window false-negative partitions
and 2,100 displayed arm/frame rows without rerunning selectors or scorers.
There were zero new model calls; completed original crop/ranking runs were not
rerun. The initial local-helper preflight stopped on a stale manifest filename
before creating outputs; correcting that helper required no source change.

Rendering completed in 418.471 seconds with 3,012 hash-verified assets: 12
clips, 300 comparison panels, 2,100 native overlays, 300 unmarked source images
and 300 closeups. All 12 original clips and 12 separate H.264 copies fully decode
25 frames at 5 fps, including each final source frame. Agent image inspection
covers all 12 final closeups and selected mechanism cases. Ryan's review is
pending; agent checks do not assert his approval or a full-clip visual judgment.

Increasing movement allowance at fixed cost scale improves matched-frame counts
in all 45 grid cells in each pool without adding false positives. Gentler cost
with tight allowance loses challenge matches in all 45 cells; with wide allowance
it gains in 37 and ties in eight. These repeated development comparisons are
correlated. All four histories still choose incorrectly at P002 representative
262. P002 challenge 48 exposes a new tight-allowance/gentler-cost loss at .20;
only wide-allowance/gentler-cost matches P003 challenge final 174 at both display
settings. Hidden P003 false alarms remain in every history arm. No winner,
operating point, quality gate or holdout release is selected.

Ignored evidence is under
`data/outputs/ball_tracking/crop_motion_execution/2274ab6097cd/`.
Start with `review_guide.md`. `execution_record.json` SHA-256 is
`1e732738669cb3f6c4389a92248cd1435b376b2fb023a2b02abacda9bb4eb40f`. It binds 86 protected files,
all derived outputs, both scoring pools, the review manifest, playback and
inspection records. All protected inputs and previous controls stayed unchanged;
all nine original embargo paths remain absent and all three holdouts sealed.
The implementation retains its 23 focused passes and full-suite 385 passes plus
one existing Windows directory-symlink skip. No production code changed and tests
were not repeated. Only three intentional context files changed after the clean
execution audit; the index remains empty and whitespace is checked. The final
ignored receipt binds those edits. Next is Ryan's 12-clip final-frame review.

## Crop motion factorial - completed human review and saved-evidence closeout

Ryan said "I have reviewed all of these clips. move forward" in response to
the 12-clip final-frame review package. The separate receipt
`configs/ball_tracking/reviews/rfdetr_medium_crop_motion_factorial_visual_review_record_v0_1.json` has SHA-256
`d629f93d4c4081dd89fcbc98c997fff0f5aea7fe9d8555a16d9328f803d6fd40`. It binds the precise scope and statement
without adding individual-frame verdicts or quality/operating-point decisions.
All 3,012 review assets, 12 playback copies, 378 outputs, two scoring pools,
six crop files, six saved whole-frame detections and six finalized labels were
rehashed. Previous execution/guide snapshots remain unchanged.

The new saved-evidence audit independently reconciles 1,080 loss partitions and
extracts 4,843 emitted winners from all 216 history outputs. It preserves path
support, source-frame span, gaps, boundary flags, candidate coordinates and
confidence, component scores and competing endpoint records, joined to saved
radius-10 outcomes. No matching or abstention policy is recomputed. Its JSON
SHA-256 is `2eb17ff8c26237f3009396a5a54f9646fba187db7409d9e87cfe83c678361c5c`.
Across correlated arm/confidence records there are 313 matched singleton
emissions, 71 unmatched eligible singleton emissions and 19 hidden singleton
false alarms; 1,221 unmatched eligible and 52 hidden emissions already have
at least two supporting nodes. Independent review reproduced these counts,
all eight paired-grid contrasts, all four display table rows and receipt bindings.

The mechanism diagnostic copies 112 saved traces with 38 exact input bindings.
Its SHA-256 is `496a2c6cdfa01d46e43ca7dec052bdffbe0329876cc6d9018618b3acee2b203a`.
All arms at both displays choose a five-node false path at P002 262 despite an
available five-node ball path. P003 hidden .20/168 has two nodes, whereas correct
171 is a singleton in every arm/display. Tight allowance/gentler cost rewards
a distractor at P002 challenge48. These findings bound what support rules can
address. The context feasibility audit inventories reviewed image-space inputs
and existing candidate geometry without changing any emitted observations;
its JSON SHA-256 is `cb06d0804bed5ea5f0ca76685696f87dd12bfe7d0e99157ff7735132c0471a0e`.
It does not infer ball possession or project airborne points onto the court.

Artifacts are under `data/outputs/ball_tracking/crop_motion_closeout/2274ab6097cd/`.
The compact result is `../ball_crop_motion_factorial_results.md`. No selector,
scorer, model or renderer ran; no new prediction or quality gate is produced.
All 83 protected non-context files remain unchanged, all nine original embargo
paths remain absent and all three holdouts stay sealed. HEAD remains
`2274ab6097cd841421e2b606f723b047cd7dc62b` with an empty index. Preserve the three
context edits plus new review receipt/results note. Whitespace, exact scope,
hashes and JSON/Python parsing are checked in `closeout_handoff.json`. The last
production tests remain 23 focused passes and 385 full-suite passes plus one
existing Windows skip; no code change required repeating them. No staging,
commit, push, PR or merge occurred. Next is a bounded candidate-identity design,
with abstention treated separately and no operating point or winner selected.

## Candidate identity diagnosis and proposed soft player context

At unchanged HEAD `2274ab6097cd841421e2b606f723b047cd7dc62b`, the agent inspected all 12
new diagnostic sheets covering 215 distinct already emitted candidates. The
catalog preserves 430 exact native bbox/context crops from 149 saved unmarked
review PNGs; source/crop hashes and decoded crop pixels were verified. Radius-10
scoring labels remain diagnostic outcomes, not semantic object annotations.
No candidate selection, matching, model, completed pipeline or clip render was
rerun. Bright distant seating objects, near-player body/footwear regions and
imprecisely localized genuine balls are distinct observed failure patterns.

The crop audit found that 93/125 matched centers have no alternate crop coverage,
while a hidden false candidate repeats closely across two views. No cross-view,
size, color, border or clustering rule was applied. A create-only context
snapshot preserves all 20 original CSV fields, typed and string-valued, for
exactly 1,353 rows/150 frames/six windows, with all six prior window digests
reproduced. SHA-256: `272c0f14e86420f4b667a0a24d4723914c87efa31fdc0244b1348573a2a441a0`.
No sealed holdout geometry was decoded. Current hashes and metadata alignment
do not create missing historical player video/model provenance.

The proposed comparison JSON SHA-256 is `b41dd0094755de726db6de196c28376cdfc2bceb40b645b1ce91fa56a6be80e7`.
It fixes one bounded coefficient/formula before execution, applies it separately
to each motion control, preserves signed utilities and original confidence,
uses neutral explicit missing context, and reuses all 378 previous outputs and
1,890 reports. Planned new work is 216 outputs/1,080 reports and 12 synchronized
clips, with no detector calls. The exact recurrence, independent synthetic
oracle/parity tests, separate score components, own-frame context and offline
player-provenance limitation are specified. The proposal is not an approved
manifest or completed experiment, and no quality or operating-point decision
is made.

See `../ball_candidate_identity_diagnosis.md`,
`../ball_crop_player_context_proposal.md` and the ignored
`data/outputs/ball_tracking/candidate_identity_diagnosis/2274ab6097cd/` evidence.
Independent reviews checked input hashes, pixel provenance, frozen row digests,
formula/counts, and the proposal's human-review scope. JSON/AST parsing and
`git diff --check` pass. All 83 protected non-context files, prior review/results
bytes and saved controls remain unchanged. Nine embargo outputs remain absent
and three holdouts sealed. The final `diagnosis_handoff.json` binds the eight
unstaged/untracked files; index empty, no Git mutation. Production code/tests
remain at 23 focused and 385 full passes plus one existing Windows skip, without
unnecessary reruns for this saved-data/documentation change.

## Player-context comparison - approval and synthetic implementation validation

Ryan's "I approve chat" approves the unchanged proposal SHA-256
`b41dd0094755de726db6de196c28376cdfc2bceb40b645b1ce91fa56a6be80e7`.
The separate approval receipt SHA-256 is
`6e6f0fa4016c2b187593a11af55e45ef5a0d3f87ad26783af05136d9d80c84c1`;
the new experiment manifest SHA-256 is
`716b397d5ef03b178f8c59565f6c1b41574674a6390cb457dfba258fa3c989c4`.
The experiment specification remains
`7478fe4a3e5a3aaeb328c71b6ed1fe06db42dd3f904af17ca4ed13eb8a294e0d`.
The historical proposal bytes/status remain unchanged. Scope approval does
not authorize Git mutations or select an operating point or quality gate.

Four new modules implement the fixed .25*z/(1+z) cost with signed node utility,
own-frame observed box context and exact prior graph/tie/missingness rules.
All 34 focused tests pass, followed by 419 full-suite passes and one existing
Windows directory-symlink skip. Bytecode writes were disabled. Ninety-six
positive-cost graph cases use an independent exhaustive path/geometry oracle;
zero-cost traces reproduce the old graph across nine confidence thresholds,
four motion settings and seven horizons. Tests cover malformed/missing context,
filter-before-cost, original-confidence ties, negative utility/abstention,
window reset, future independence and annotation exclusion.

Synthetic workflow validation covers resumable creation of 216 new outputs,
exact reuse of 378 prior outputs and 1,890 reports, 1,080 new reports, and 495
aggregates per separate pool. Saved-control execution is disabled during the
new stages. Tests exercise cross-purpose frame alignment, complete provenance,
all nine embargoes, dirty-checkout rejection and changed-input rejection.
The production renderer preparation function is exercised on synthetic saved
outputs/reports with ranking/scoring disabled and a substituted image inventory;
separate renderer tests verify the native PNG bindings.
Twelve synthetic clips decode all 25 frames at 5 fps; their 2,112 new assets and
2,400 reused native references pass hash, final-frame, atomic resume and tamper
checks. Independent review tightened exact source-PNG evidence validation and
the saved alternate-hypothesis legend. Agent inspection of the final synthetic
comparison, closeups and player-box view found readable, aligned layouts; this
does not establish Ryan's real-data visual judgment.

The separate real-input dry run checks the approved six windows/150 frames and
1,353 frozen player rows with every selector/scorer and media decoding disabled.
The saved-native preflight also verifies all 2,400 actual existing source/control
PNG bindings with both image and video decoding disabled. Its separate
`saved_native_input_preflight.json` preserves those exact bindings.
The real execution gate rejects the current dirty checkout. No new real output
root exists. No completed model/crop/ranking/motion experiment was rerun and no
sealed holdout geometry was decoded. Legacy missing player-source/model
provenance and possible offline hindsight remain explicit limitations.

Evidence and actual test logs are under
`data/outputs/ball_tracking/crop_player_context_implementation/2274ab6097cd/`.
`implementation_handoff.json` binds the final exact eighteen-file scope,
test receipts, real-input preflight and v3 synthetic QA images. All 83 protected
existing files and five prior untracked files remain unchanged; nine original
embargo paths stay absent and three holdouts sealed. JSON/AST parsing and
whitespace checks pass. Branch/HEAD remain `codex/ball-detector-baseline` at
`2274ab6097cd841421e2b606f723b047cd7dc62b`; index empty, no Git mutation. The three
intentional context documents are advanced with their prior bytes saved locally.
Next is exact-scope staging approval, then staged verification and separate
commit approval. Already approved real execution waits for that clean tested
commit. No manual command is pending.

## Player-context comparison - clean execution and pending new visual review

Ryan explicitly approved staging the eighteen-file scope ("yes go ahead and
stage"), then committing it ("yes you may"). Commit
`119159817df5414f534f133f0954c1f78c7e51de` has the exact expected title, parent,
scope and blobs. Git metadata required the sandbox's write-permission override;
the authorized actions completed and were verified. No push, PR or merge ran.
The earlier experiment approval then permitted execution at the clean tested
checkpoint. Production code is unchanged from 34 focused passes and 419 full
passes plus one existing Windows directory-symlink skip; tests were not repeated.

Selection created all 216 new outputs in 157.302 seconds. Scoring added
1,080 new reports in 420.797 seconds; all 378 saved outputs, 1,890 reports
and 630 aggregate cells retain their exact bytes/content and prior provenance.
Together the two pools contain 2,970 reports; each has 495 aggregate cells.
Completed detector/crop/ranking/motion stages were disabled by execution guards;
no detector calls or source-video decoding occurred. Frozen PNG inputs remain
confined to the approved six windows. No sealed holdout geometry was decoded.

Independent audits read saved evidence only. The selection audit checks 216
outputs/5,400 frames, 47,198 source candidate records (crop duplicates retained), 222,888 node-cost
and recorded-path records, 684,466 edges and 145,400 endpoint/trailing records.
It replays recorded arithmetic without choosing winners. Every frame has
observed player context. The scoring audit reconciles 2,970 reports, 990
aggregate cells, 1,080 paired differences, 1,080 loss partitions and 360 aggregate
contrasts, with exact saved-control equality and all 594 output bindings checked.

Across the 360 correlated paired aggregate cells, none reduces matched frames
or increases false positives. At the two fixed review settings (.20/.35,
radius 10), representative gains are 6-11 matches per variant and challenge
gains 0-4, with no matched display-frame losses. P002 representative 262 recovers
for all four arms at both displays; P002 challenge 48 recovers for TW at .20.
Hidden false alarms persist at P003 167 (.20) and 168 (both displays). P001
representative final 74 recovers at .20 but remains wrong at .35; P003 challenge
final 174 still matches only for WW. These are development observations, not
independent-trial evidence, a selected winner or a quality/operating-point gate.

Rendering finished in 414.968 seconds. The 2,112 new assets (2,100 PNGs,
12 clips) and 2,400 reused native/source PNG references are hash verified.
All 12 originals and 12 separate H.264 copies fully decode 25 frames at 5 fps,
including their final source frames. Independent helper review tightened
per-clip sidecar identity/destination checks before playback preparation.
Agent image inspection covers all 12 final closeups and targeted real panels;
Ryan's new visual review remains pending. Existing crop/ranking/motion approvals
do not assert review of this new package.

Evidence is under
`data/outputs/ball_tracking/crop_player_context_execution/119159817df5/`.
Start with `review_guide.md`; `results_summary.md` contains the exact tables.
`execution_record.json` SHA-256 is
`300eecaecc8b99c2e44d765ec1757a10f9431a1f2e1c2766ccfddcd86b3c1615`. It binds the stages,
new/reused output inventories, score/selection audits, review manifest, playback,
inspection and 101 protected files at the clean execution checkpoint.
Only the three context documents were advanced afterward, with their original
bytes retained locally and final hashes in `post_execution_context.json`.
Whitespace passes, index empty, nine original embargo paths absent, and three
holdouts sealed. No upstream reviewed player decision changed. No manual
command is pending. Next is Ryan's review of all twelve new clips through their
final frames; completed stages must not be rerun.

## Player-context visual review complete and saved-results closeout

Ryan answered "Yes, reviewed all 12; proceed" to the explicit question about
watching all twelve new player-context clips through their final frames.
The separate review receipt SHA-256 is `0ebaabad929558d9c07339161f0d37362d6da9477883853146345cc56a848ef6`.
All 2,112 new assets, 2,400 reused PNG references, twelve playback copies,
216 new outputs, 378 controls and 98 protected non-context files were rehashed.
An independent read-only check verified all 73 receipt file bindings and exact
agreement of its twelve clip entries with the playback manifest. Historical
pending-review evidence was preserved; no itemized human verdict was invented.

The new saved-evidence diagnosis reconciles all 1,080 per-window comparisons
and loss partitions. Compared with each matching motion control, there are
no newly lost matches, added false-positive frames or worse center errors on
shared matches. It separately preserves residual failures against top one and
all exported candidates. At radius 10 the .01 exported pool covers 140/145
eligible frames; .20/.35 still have confidence and path-selection losses.
The hidden P003 167/168 cases retain zero context cost. No selector, scorer,
renderer, model, source-video decoder or holdout geometry reader ran.

The numerical artifact `residual_diagnosis.json` has SHA-256
`3f2744d8c88c26abd2595384ac83147b623e35a204dbd4aded1704c92ad569e8`.
The closeout document is `docs/ball_crop_player_context_results.md`.
All settings reuse the same six windows and do not establish generalization.

Primary-source research supports preparing one bounded YOLO11x Detect
challenger; the concrete proposal JSON SHA-256 is `f891c04464422428dadbcfdf425436d3347464dbcab6d96ae23cac963dca5492`.
It binds 150 unmarked source PNGs, all 162 reused simple-selector outputs,
two saved scoring pools (405 selected report cells each), labels and protected
embargo/holdout scope. Published checkpoint digest and package version are
pinned; local artifact verification and isolated runtime validation are future
preconditions. No package or model was downloaded, installed, loaded or run.
The design explicitly retains preprocessing/NMS/candidate-budget differences,
uncalibrated model confidences and unverified exact training overlap. It is
not an execution permit and requires separate exact-scope experiment approval.

Only evidence/design/context files changed; production code and prior evidence
are unchanged. The latest 34 focused and 419 full-suite passes plus one existing
Windows skip remain applicable; no redundant tests were run. Index empty,
nine original prediction paths absent, three holdouts sealed, no selected
method/point/gate and no Git mutation. Previous context bytes and final binding
inventory are preserved under
`data/outputs/ball_tracking/crop_player_context_closeout/119159817df5/`.
No manual command is pending. Next is the exact new proposal review, not a
repeat of Ryan's completed clip inspection.

## Approved YOLO11x implementation and synthetic validation

Ryan's exact approval is bound by the new approval receipt and executable
manifest. The design JSON remains SHA-256
`f891c04464422428dadbcfdf425436d3347464dbcab6d96ae23cac963dca5492`.
The isolated Ultralytics 8.4.171 environment records exact package/wheel/file
inventories and verified publisher weights. Baseline package metadata remains
unchanged. The runtime receipt SHA-256 is
`bd549dff7c4d7810b3154c9a5442cf43516e15bd5c72ab6abe631f819652e7ba`.

Actual synthetic GPU tests passed color conversion, 640-square letterbox with
140-pixel vertical pads, normalization, inverse boxes and FP32 device 0 checks.
Each fresh predictor performed two synthetic startup forwards and one further
ordinary-route forward on a constant synthetic image. No project pixels were
used. SDK deepcopy and canonical precision handling were checked against the
installed version. Offline configuration remains inside the ignored runtime.

All 41 focused tests pass, followed by 460 full-suite passes and
1 existing Windows directory-symlink skip. Focused tests cover all 600
synthetic crop units, retry/preparation accounting, 162 new outputs, 810 new plus
810 unchanged saved reports, 270 aggregate cells per pool and twelve 25-frame
synthetic clips with 1,512 new assets and 1,200 reused references. Independent
review caught and fixed wrong-prefix acceptance and a PNG hash/decode race.
Root and renderer agent inspected synthetic comparison/native/closeup layouts.
The first combined test invocation failed on flat fixture imports; the normal
repository discovery command passed. Failed and passing logs are preserved.

Read-only actual preflight verified 150 PNGs/600 planned crop units without
constructing a model. The dirty-tree gate was separately verified before
runtime access. No new real inference, scoring or rendering has occurred;
the approved challenger output root remains absent. All 98 protected files,
four preceding design/review files and old local evidence bindings are intact.
No old pipeline or source-video decoding occurred. Embargoes and holdouts
remain protected, with no operating point, method or quality gate selected.

The final implementation checkpoint and before-context backups are under
`data/outputs/ball_tracking/yolo11x_implementation/119159817df5/`.
Git branch/HEAD are unchanged and the index is empty. Exact next step is
separate staging authorization for the nineteen-file scope documented in
`docs/ball_yolo11x_crop_implementation.md`, followed by separate commit approval.

## YOLO committed run: safe stop, native-row repair and recovery design

Ryan explicitly authorized staging, then answered "Yes you may chat" to the
separate commit request. Commit `116e3ed9cb4113521fa8c93adf4a100fea4dc0ec` contains the
exact nineteen-file snapshot, with a clean tree at execution start. The commit
receipt binds all 239 tracked files. No push, PR or merge occurred.

Guarded preflight passed. Initial inference saved 175 crop checkpoints and one
candidate window with 27 selectors before failing on P001 challenge frame 218
BR. A traced normal retry at the unchanged commit reproduced the same error
without recomputing completed units. All175 retained their hashes. Ledgers
record 177 project forwards/attempts (175 successes, two failures), two fresh
predictors and four synthetic warmup forwards. Inference is incomplete;
scoring and rendering never started.

The ignored diagnostic preserves native postprocessor row 55, with zero height
at the image edge and confidence `8.813966019260988e-7`.
SDK inverse-letterbox mapping clips corners
independently, allowing a collapsed below-floor native row. The adapter's
strict geometry check mistakenly applied exported-box requirements to it.
The unstaged repair preserves such native evidence below .01 while retaining
strict positive geometry at and above .01. No model settings, score, candidate
order, native rows or export floor changed. Saved replay has all 60 native rows
and zero exports; all completed checkpoint bytes remain intact.

Validator repair validation: 15 focused passes; 464 full-suite passes plus one
existing Windows directory-symlink skip. Logs and exact source hashes are in
`validator_fix_tests.json` under the execution directory. Runtime/model
inference was not used for repair validation.

A v0.2 recovery proposal binds the complete partial-run inventory and declares
actual inference commits per crop separately from the assembly commit. It
preserves all earlier outputs, reuses 175 crop units without GPU calls and
proposes 425 remaining units in a new recovery subtree. New derived selectors
would preserve the old 27 artifacts while enabling an honest complete dataset.
No result is relabeled as having been inferred by the future repair commit.
This contract change requires review under the approved proposal; it remains
proposed, unapproved and unimplemented. Its JSON digest is
`b0a6a6ee81711d59f35b6360ce6c9595fce80c1625d45ff407683958a65612fe`.

All nine original embargoes and three holdouts remain protected; no complete
YOLO quality result, operating point, gate or generalization claim exists.
The latest handoff and final file bindings are in `handoff_failure.md` and
`failure_checkpoint.json` under
`data/outputs/ball_tracking/yolo11x_execution/116e3ed9cb41/`.

## Approved YOLO recovery implementation checkpoint

Ryan approved the exact bound recovery proposal with "Yes I approve chat".
A separate approval and executable manifest preserve its historical bytes.
Three recovery modules implement explicit per-unit inference provenance,
separate assembly/selection/evaluation/rendering commits, guarded missing-unit
execution, and immutable resume. The native-box correction retains below-floor
zero-area evidence while keeping positive geometry for all exported detections.

All 27 recovery-focused and 15 adapter tests
passed, followed by 491 full-suite passes and one existing Windows
directory-symlink skip. Synthetic tests cover complete scoring, control reuse,
final frames and failure/resume boundaries; agent inspection covers synthetic
review layouts. Exact tested bytes and logs are bound in `final/test_results.json`.

The approved isolated runtime's real read-only preflight verified 150 bound
source PNGs and all 175 original completed crops without a model, media decode
or annotation access. Dirty execution is rejected before runtime inspection.
Independent preservation checks retain all 561 original partial-run files,
all nine prediction embargoes and three holdouts. Real recovery, scoring and
rendering remain unexecuted; the new output subtree is absent. No quality,
method, operating-point or unseen-game generalization claim is made.

Branch/HEAD remain `codex/ball-detector-baseline` / `116e3ed9cb4113521fa8c93adf4a100fea4dc0ec`;
index empty, no Git mutation. Before-context bytes and final evidence are under
`data/outputs/ball_tracking/yolo11x_recovery_implementation/116e3ed9cb41/`.
The next boundary is staging the exact documented scope, then separate commit
authorization. The approved experiment itself does not need approval again.

## YOLO recovery execution, completed visual review and saved-results closeout

Ryan separately authorized staging the exact seventeen-file scope, then replied
"Yes you can" to the explicit commit request. Local commit
`3326482e6f7e05527d146f3110c8ec39171cf08d` contains the tested staged bytes and
has parent `116e3ed9cb4113521fa8c93adf4a100fea4dc0ec`. Clean branch, index,
scope and blobs were verified. No push, PR or merge occurred.

The approved recovery completed all 425 missing crop units, retaining the 175
original checkpoints and all 561 original partial-run files unchanged. It
created six candidate files and 162 selectors with explicit actual inference
commits for every unit, separate from assembly provenance. The observed totals
are 600 unique crops, 602 attempts/forwards including two historical failures,
three predictor preparations and six synthetic forwards. There are no new
failures or incomplete accounting records.

Scoring produced 810 new reports while reusing 810 exact RF-DETR reports. Each
separate pool contains 270 aggregate cells. Rendering produced twelve clips
and 1,500 PNGs with 1,200 reused native/source references. The independent audit
verified asset bytes, all twelve clips through all 25 frames at 5 fps, sixty
final PNGs, all original files and all embargoes. Its SHA-256 is
`0aeb970b6b550a7a6ce18840d9e88ebbf3cf6ea0f01155c40bcd0ef1522ea3a4`.
The execution checkpoint is
`df74bfd6f46070fa9b36866c4663b72fc7c89ff0addc2bc45c9f1c2dcc2849ca`.
Both are under `data/outputs/ball_tracking/yolo11x_recovery_execution/3326482e6f7e/`.

Twelve clips and sixty final-image support copies preserve the original bytes
at shorter paths. They are not new model or rendering outputs. Agent visual
inspection covered only two final stills; machine decoding is not human review.
Ryan subsequently stated "I approve these clips. They have been reviewed and
you are good to move forward" in direct response to the twelve-clip final-frame
request. The separate review record SHA-256 is
`365facf28a1e2f05339adea1e04e96a8fe7f33d0b3dea0184d16d1caa4c05433`.
It records completed package review without inventing specific frame verdicts.
All earlier pending snapshots remain unchanged.

The closeout rehashed 4,750 frozen evidence bindings and 248 existing
non-context tracked files. At radius 10/.01, RF-DETR covers 140/145 eligible
frames while YOLO covers 87/145, with no additional YOLO-matched frame. YOLO
has fewer matches in all 270 paired aggregate grid cells; these reuse the same
development frames and are not independent trials. No method, threshold,
operating point, quality gate or generalization claim is selected.

The bounded ten-family saved-report audit reconciles 900 aggregate cells,
2,700 per-window reports, 3,000 displayed frame-setting records and sixty
existing context/YOLO loss partitions. The 810 duplicate RF reports and 270
aggregate copies match and are counted once. Every pool/radius tradeoff set
retains all outcome-tied settings and provenance. At radius 10, eight
representative and seven challenge settings remain nondominated on TP/FP.
YOLO top one at .50 retains a representative 17 TP/3 FP/58 FN tradeoff; no
YOLO setting is nondominated in challenge. This is not a method selection.

Twenty frames are missed by every family at both displays. RF causes are five
unavailable proposals and fifteen confidence-filtered matches; P001 71 is the
only frame with a false positive in all twenty displayed setting incidences.
The audit retains all frame pointers and causes without rematching coordinates.
Its SHA-256 is `9a83a996f4c4772a45530e1050dc9337c8caa3fabaf6095ed96bbc44bc5cfe21`.
The next 32-frame saved-evidence inspection is specified in the results doc;
it has not run and does not authorize training or new identity labels.

This evidence/documentation closeout changes no production code. Existing
27 recovery-focused and 15 adapter passes, plus 491 full-suite passes and one
Windows capability skip, remain the relevant validation. No completed pipeline
stage, model inference or media decode is repeated. All nine embargo paths
remain absent, all three holdouts sealed, and the index remains empty.

## Approved saved candidate-retention and localization diagnostic

On October 2, 2026, Ryan's "mover forward chat" response authorized the exact
bounded saved-evidence diagnostic. The separate approval receipt binds the
unchanged proposal and design. It authorizes neither a new tracking experiment
nor training or a Git step. The earlier closeout is committed at
`9fe6a1ef86d23391c64b7d5b16198ad7bb005c25`; the later 32-frame agent inspection
was already complete and remains distinct from human identity labeling.

The new helper and its 28 focused synthetic tests passed, followed by the full
suite: 520 tests run, 519 passes and one existing Windows directory-symlink
capability skip. Tests cover assembly/output, original candidate indices,
RF/YOLO namespaces and crop schemas, mixed actual inference commits, hidden
nulls, uncertainty, threshold/cap overlap, missing optional membership versus
contradictory evidence, exact approval bindings and create-only output.
Both validation commands disabled bytecode writing. Source/test hashes were
unchanged before and after validation and real execution:

- helper: `12adbe87c83f3f801e7bf76e06d6ea31210c539cec84138c5d6b717e00d93f82`;
- focused tests: `ecdfcfd516e756cfd5294680d84a08d7345857205a80f3eb91e09634196e5120`.

One real diagnostic execution returned zero and wrote only `case_ledger.json`,
`summary.md` and `integrity.json` to
`data/outputs/ball_tracking/candidate_retention_localization_diagnostic/v0_1_9fe6a1ef86d2/`.
The integrity SHA-256 is
`a15e99a163ee169a38ac37097d3e1ca6b3a4fa827e016b8bc89bddd037f51326`.
Creation HEAD and dirty helper hashes are recorded separately from actual
detector inference provenance. No model, selector, evaluator, renderer or
media decoder was called by this real diagnostic.

An independent audit, without importing the implementation, checked all 32
frames, 82 original candidate records, 640 saved display/report/trace records,
1,060 same-detector candidate settings and fifteen cap memberships. The latter
resolve to eight rejected and seven retained saved floor-match candidates.
Original report payloads and null matched-error fields are preserved; separate
dx/dy/distance fields match independent arithmetic. Five hidden residuals stay
null. All 82 certified identities stay null and training eligibility false.
All 231 original assets, 177 input bindings and newly bound records retain
their hashes. The existing final gallery and twelve-clip review remain complete.

The exact commands, logs and source/output hashes are in `final1_tests.json`,
`execution_receipt.json` and `independent_output_audit.json` under
`data/outputs/ball_tracking/candidate_retention_localization_implementation/9fe6a1ef86d2_2026-10-02/`.
`git diff --check` passes. Branch/HEAD remain unchanged and the index is empty;
implementation and documentation remain unstaged. All nine original prediction
embargoes remain absent and all three holdouts sealed. No method, operating
point, quality gate or training labels are selected.

## Approved candidate-retention implementation: synthetic validation

Ryan's October 2, 2026 approval authorizes the exact new retention comparison,
subject to its tested clean-commit prerequisite. A separate approval receipt
preserves the original proposal/design bytes. The new implementation changes
only cap retention at .01 for four fixed motion settings; it does not move
centers, change confidence, certify identities or select a method.

All 78 distinct focused synthetic tests pass. Coverage includes exhaustive
small-graph path oracles, exact legacy cap20 parity, all four motion settings,
old-path feasibility, original indices beyond twenty, gaps/ties/causality,
confidence and cap partitions, original-report reuse, higher-confidence
equivalence references, hidden nulls, uncertainty, immutable checkpoints,
complete rendering and resource abort/resume. Windows tests exercise actual
Job Object process trees and verify child memory accounting and termination.

Final fabricated 400-candidate/25-frame stress fixtures both passed complete
lossless serialization and decoding. Dense: 31,840,000 serialized edges,
491.578 seconds, 1,280,413,696 peak worker-tree resident bytes and 118,447,870
new root bytes at the final sample. Sparse: 112,280 edges, 10.266 seconds,
74,559,488 peak resident bytes and 3,439,756 new root bytes. Maximum monitor
intervals were .328 and .266 seconds, with no time/memory/output overshoot.
Final receipt space is conservatively reserved. These are separate synthetic
validation costs, not real experiment resource consumption or accuracy claims.

The first benchmark snapshots remain preserved. Final fixtures use the fixed
Windows portable receipt paths and bind unchanged implementation bytes. The
full suite then passed: 598 tests run, 597 passes and one existing Windows
directory-symlink capability skip, in 1,638.766 seconds. All 134 production,
test and requirements files retained their exact hashes throughout validation.
Both focused and full commands disabled bytecode writing.

An independent preservation audit checked 755 unique files, including all
312 non-video proposal-bound files, 126 saved controls, 150 saved source PNG
bindings, the completed diagnostic's original bindings, and all 134 inventory
files. Eight prior non-context working files remain unchanged. No source video
or holdout contents were opened. The actual dirty-checkout guard rejected real
dispatch before any worker or experiment output was created.

Evidence is under
`data/outputs/ball_tracking/crop_candidate_retention_implementation/9fe6a1ef86d2_2026-10-02/`.
No real candidate selection/scoring/rendering, inference, training or Git
mutation has occurred. The original nine embargoes remain absent, the three
holdouts remain sealed, and prior human reviews remain complete.

The final certificate is `implementation_validation.json`, SHA-256
`135bb50a461eec662f70ed4c64d15fe15e36826eefe81ee21e7521f36578890f`.
The executable manifest binds it and has SHA-256
`f2b8834722ddf9f1ce4dcfdf1441a12cc0d52591b57bb66ca726c3aef2ca15ff`.
It includes the full-suite receipt/log and both independent audits. All 755
preservation bindings were reverified after the full suite. The benchmark audit
also independently checked all 50 compressed trace hashes, resource journals,
completion seals and analytic edge counts without rerunning selection.
The 24-file implementation/diagnostic preparation remains unstaged; index empty.
The next step is separate staging authorization, followed separately by commit
authorization. The already approved real comparison requires that clean commit.

## Candidate-retention execution: selection complete, first scoring window interrupted

Ryan separately authorized the exact 24-file staging scope and its commit.
The real comparison started from clean commit
`0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41` on
`codex/ball-detector-baseline`, with an empty index. All 24 selection units
completed after successful selection preflight, giving 25 successful workers.
Scoring preflight also succeeded, but the first scoring window failed with
`ResourceLimitError: Output tree did not stabilize for complete byte accounting`.
The total is 26 successful workers and one failed worker. No retry or rendering
followed. No successful scoring report, aggregate pool, new review clip or
comparison-accuracy conclusion is available. The prepared completion audit was
never executed; it must not be represented as an independent completed audit.

Through the interruption, the journal records 618.1929999999993 cumulative
active seconds, 279,302,144 peak worker-tree resident bytes, 881,741,466 maximum
sampled output bytes and a .469-second maximum monitoring interval. Recorded
resource overshoots are zero. The committed monitor requires two identical
file-identity/size/mtime inventories within half a second. The scorer writes
its JSON continuously before publishing the final checkpoint. The observed
accounting-stability failure and retained partial write are consistent with
these conflicting requirements; they do not establish an exceeded resource
budget. The worker log is empty and its result null.

Failed attempt `e1ba648def3f4e1f887332e850396e4c` has completion-event SHA-256
`9031c188c940980de2c858d59722114aaa8dcd68f2b70d314a9bfb0ff1d40104`.
The 16,861,477-byte incomplete scoring file, all selection outputs and persistent
budgets remain under
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/`.
See `../ball_crop_candidate_retention_interruption.md` for the exact partial
path and evidence status. The limited forensic audit subsequently passed in
one supervised diagnosis worker, without selection, scoring, rendering or
inference. It verified 24 selection-manifest hashes and canonical content,
600 compressed trace hashes without decompression, 27 failure-prefix attempt
seals and their journal hash chain, 134 source bindings, six saved crop files,
126 saved controls, nine embargo absences and three holdout metadata bindings.
Its ignored `audit/interruption_receipt.json` has SHA-256
`0f90a59c07dd2436ef8618ffd8d3637695b99ab3e56e08f879866d9d702e40df`.
This limited preservation audit does not replace the unexecuted full
comparison-completion audit.

The diagnosis attempt `4f8797ac75b543af9168098f5b9538a5` completed in 2.0
seconds; its finished-event SHA-256 is
`00fd14c3c82c8b56ab45c633305bd22ca2f394d39b8d758acd12c82572da0ac9`.
Totals are now 27 successful workers and one failure across 28 attempts,
620.193 active seconds consumed and 13,779.807 seconds remaining. Maximum
sampled output is now 882,157,412 bytes; peak memory and the maximum monitoring
interval are unchanged. Consumed budgets remain persistent. The prior
focused/full synthetic validation remains historical implementation evidence;
no tests were rerun for this documentation record.

The next step is review of `../ball_crop_candidate_retention_recovery_proposal.md`,
which presents the live-write accounting and cross-commit reuse amendment under
the frozen proposal's revised-explicit-scope boundary. The original scientific
approval remains valid; no recovery code or retry has occurred. No source, test,
config, frozen proposal or saved output is changed by the interruption record.
Documentation remains unstaged, index
empty; later Git steps require separate authorization. All nine original
prediction embargoes and three sealed holdouts remain in force, and all twelve
prior YOLO final-frame approvals remain complete. The six new retention clips
still require generation and human review. No method, operating point, quality
gate, training or certified identity labels are selected or authorized.

## Approved retention recovery: focused and full validation complete

Ryan approved the specific recovery with "I approve chat. Please move forward".
Its separate approval receipt preserves the frozen recovery proposal's exact
bytes, SHA-256 `c066bc43b204a09a05e2912589cbc173614cecbe563431ebbeed75c42db3de48`.
The original scientific approval remains valid. The implementation changes
live-write resource measurement and adds strict recovery-specific reuse of the
original completed selections. It does not change selection mathematics,
candidate centers, confidence, matching or review scope. Ordinary runner
checks remain strict, and successful completion receipts are required before
any published score or review target is reused.

The bound preserved inventory is
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/recovery_preparation/preserved_inventory.json`,
SHA-256 `5a05c6644196f7fd0dfb731c538f68077039f74265d62e7b95f3dbbe00b92739`.
It includes 24 selection manifests, 600 compressed trace hashes, original
source bindings, the failed partial and all 697 resource events through
29 completed attempts. The additional supervised preparation attempt
`692ee366897d410ca5ca7357ce80aa73` used an immutable resource-module snapshot
from the original commit and reverified saved bytes without selection,
scoring, rendering, inference or video decode. It consumed 1.75 seconds;
its completion-event SHA-256 is
`66e0c9662ffff0c906beefe711ceef3e2eb181bbb98a1bd9b66452f3791584d7`.
Recorded real-run consumption is 621.943 seconds, with 13,778.057 seconds
remaining. The journal retains all failure, diagnosis and preparation costs.

The combined focused run passed 107 tests in 101.25 seconds, with all 137
production/test/requirements hashes unchanged. Coverage includes growing,
shrinking and moved files; hard-link multiplicity; scan deadlines; worker-tree
resource limits; exact original receipt and journal bindings; tampered or
unreceipted outputs; no selection rerun; original ranking versus new evaluator
and renderer commits; and scoring/review integration. Independent static review
passed. The first full run finished with 627 tests: 621 passes, five errors and
one existing skip. All five errors occurred in the initial `git add` performed
by older `ReleaseMetadataTests` temporary fixture repositories. Independent
reproduction confirmed the deep validation TEMP path caused Windows Git's
`Filename too long` error. All 137 production/test/requirements hashes remained
unchanged throughout the failed run; no implementation or test correction was
made in response to this environment failure.

The failed `full_final.log` and `full_final_receipt.json` remain unchanged.
The raw log is authoritative for its one skip: the original receipt incorrectly
reports `skipped: 0` because that version of the summary parser recognized only
`OK` summaries. This discrepancy is recorded rather than rewriting evidence.
All 14 tests in the affected module subsequently passed in 40.031 seconds using
the short ignored TEMP root `data/outputs/t/crr_setup_short`; `setup_short.log`
and `setup_short_receipt.json` record that check. The full-suite retry with a
short TEMP path passed: 627 tests ran, with 626 passes and one existing Windows
directory-symlink capability skip, zero errors and zero failures. Command wall
time was 1,824.921 seconds; unittest reported 1,823.343 seconds. All 137
production/test/requirements hashes remained unchanged, matching the same
frozen source inventory used by focused validation and the initial full run.
The successful result is recorded in `full_short_receipt.json`; `full_short.log`
has SHA-256 `cf7dc92f0c4fb0c11c7e18ca87418b3bf7dc113eb2fb655f87ffc684831936ab`.

The completed `implementation_validation.json` certificate binds all 137
production/test/requirements files, the focused/full results, independent
review and the preserved recovery inventory. Its SHA-256 is
`71f75c979c5c754c7387df859e885b4a48be1b43fcfc62f683d76a7bc14fc8bc`.
The executable recovery manifest now references that exact certificate;
its file SHA-256 is `2e1a57cfdacfa0359f328d467fd75b513b81fde192f69e4bd2a9919dbb7a6e1f`.

The preserved validation evidence is under
`data/outputs/ball_tracking/crop_candidate_retention_recovery_implementation/0a7f5bc69be9_2026-10-02/`.
The actual dirty-checkout guard rejected dispatch before any recovery worker
or resource-journal change. No real recovery stage, scoring retry or rendering
has run. The original independent completion helper remains unexecuted;
preparing its separate recovery-aware successor is not a completed comparison
audit or human review.

See `../ball_crop_candidate_retention_recovery_implementation.md` for the exact
15-file intended staging scope. Branch/HEAD remain
`codex/ball-detector-baseline` / `0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41`;
changes are unstaged and the index empty. Next is separate authorization to
stage the exact 15-file scope, then separate commit authorization. The already
approved recovery execution requires that clean tested commit. No new real
worker ran after the recorded 621.943-second consumed balance.
The already approved recovery scope should not be requested again. All nine
prediction embargoes and three sealed holdouts remain protected, and the
twelve prior YOLO final-frame approvals remain complete. The six new retention
clips still need generation and final-frame human review. No method, operating
point, quality gate, training or certified identity labels are selected.

## Committed recovery: scoring complete, rendering interrupted, forensic evidence preserved

Ryan separately authorized staging and committing the tested 15-file recovery
scope at `f36237247191e726ad7e81bdc6651f9340a9063d`. The clean checkpoint
passed the recovery verification worker. All eight scoring-stage workers then
succeeded, completing six window JSON files and two separate pool files with
120 new localization reports and 630 saved reports. The 24 original selections
and their original provenance were reused without reranking.

Rendering preflight passed in 43.266 seconds. The first rendering attempt,
`158f51be5ab34cdface57f4e0036b7d2`, failed after 62.875 seconds with the output
tree stabilization error. Its log is empty and its worker result null. Ten
partial PNGs totaling 32,989,248 bytes remain; no completed clip, global review
manifest or full comparison-completion audit was produced. Both this failure
and the earlier scoring failure remain preserved. No scientific interpretation
or human review is inferred from completed scoring files.

A supervised read-only forensic audit succeeded without selection, scoring,
rendering or model inference. Its receipt is
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit/render_interruption_f362.json`,
SHA-256 `f2bece32af228b0f525b07eb060b1671194812b26af7787283c8ecca2aabea8b`.
The checkpoint in the same audit folder is
`render_interruption_checkpoint_f362.json`, SHA-256
`8dce571305282e59dc61e3ceb610e2ea0e5dbd86ce1896beb9e035c8ee12dcac`.
Diagnosis attempt `8e121d23c2494d969df9af94cc45bbeb` consumed 9.812 seconds.
The complete preserved journal contains 1,170 events and 41 completed attempts,
39 successful and two failed. Cumulative real worker time is 1,136.756 seconds,
with 13,263.244 seconds remaining. This limited forensic audit is distinct from
the still-unexecuted full comparison-completion audit.

Separate synthetic reproduction found that existing-file growth passed three
trials while new-file additions failed three trials under the current
equal-membership requirement. Both measured correctly after their writers
stopped. This reproduces a possible mechanism; the exact real trigger remains
inferred. See `../ball_crop_candidate_retention_render_interruption.md` for
the saved real and synthetic evidence, and
`../ball_crop_candidate_retention_render_recovery_proposal.md` for the bounded
draft amendment. It proposes monotone membership additions within two complete
scans and the unchanged half-second deadline, retaining all budgets and exact
old selection/score provenance. Its execution scope would be rendering only.
Implementation and retry require explicit approval of that new contract.

All 137 production/test/requirements hashes remain unchanged. The 107 focused
passes and full-suite 626 passes plus one existing Windows skip remain the
validation of the committed code; no new source or test change occurred during
this documentation preparation. No tests, real selectors or completed scores
were rerun for these records. HEAD remains
`f36237247191e726ad7e81bdc6651f9340a9063d`; five documentation files are the
unstaged scope, with an empty index and no Git mutation. All nine embargoes
and three sealed holdouts remain protected. The twelve prior YOLO approvals
remain complete; the six new retention clips do not yet exist as completed
review items. No method, operating point, quality gate, training or certified
identity labels are selected.

## Approved rendering recovery implementation: final regression validation passed

Ryan approved the bounded rendering recovery with "I approve, move forward chat".
The separate approval receipt binds the frozen proposal SHA-256
`2d9ea51ca4f93fbc77d902266dcbf1ef496edcb8c320c7a0dbbe6d86bf884b48`.
Implementation is restricted to the new verification/rendering runner, saved-score
loader injection, the monotone file-inventory amendment and synthetic tests.
Scoring/evaluation and the original selector remain unchanged. The three changed
historical files are the resource monitor, review module, and one resource-test
expectation; new code/tests are additional files.

The resource subset passed all 44 tests. The new recovery subset passed all 26
tests in 104.376 seconds. Independent static review identified and resolved
two actual-schema mismatches: comparing a file binding to a binding containing
a canonical-content digest, and treating nested pending PNGs as flat files.
The corrected cases are covered by the new tests. Independent review also
added global review schema/no-selection assertions to the prepared completion
helper. No real audit execution is implied by that preparation.

All 145 combined retention tests passed in 198.604 seconds, with no skips and
all 140 source/test/dependency bindings unchanged. Logs, inventories and review
receipts are saved under
`data/outputs/ball_tracking/crop_candidate_retention_render_recovery_implementation/f36237247191_2026-10-02/`.
The actual metadata-only dry-run succeeded without dispatching a worker.
The full suite completed 665 tests in 1,882.854 seconds (1,884.437 seconds harness
elapsed): 664 passed and one existing Windows directory-symlink test was skipped.
All 140 source/test/dependency bindings stayed unchanged. Its log SHA-256 is
`8718be18e1cfab70e8290688315e107c5de91f6931af803114a844ec9796eaa7`; both runs
share source-inventory SHA-256
`545592e57cfc716b8a9b7ad542fd0a493621a848c61516ca3374f2ae2b1d6148`.
Independent certificate-guard review passed. The assembler checked exact commands,
complete successful log summaries, required independent-review bindings, all
1,170 journal event hashes and all 41 reservation/completion seals. It rejects
optimized Python. The final create-only certificate SHA-256 is
`652a8bb8926ea21be2e1863e34105b1c737986e46c5615a342e682be497644dc`, binding
140 source/test/dependency files and 27 evidence artifacts. The final manifest
file SHA-256 is `72f15b1d43750b00b49d0bd83c3e8ab0c4351064aeadad582008429580c00fcf`;
its canonical specification SHA-256 is
`326ba1cec475aa32d172a76a2ea760ceffb3e9188631c16ed2b1af5914fab3cd`.
The final metadata-only CLI dry-run also passed without worker dispatch.

The real checkpoint remains 1,170 events, 41 completed attempts, both preserved
failures, 1,136.756 seconds consumed and 13,263.244 seconds remaining. No real
verification, rendering or other scientific worker has run under the new
recovery identity. The nine embargoes and three sealed holdouts remain protected;
the twelve prior YOLO reviews remain complete. Staging and committing remain
separately unapproved. See
`../ball_crop_candidate_retention_render_recovery_implementation.md` for the
implementation and intended 14-file staging scope.

## Candidate-retention publication recovery and human review complete

The separately authorized publication-recovery implementation executed at
`a89cd40838b066c1d2fe3cb1f257dda10e80a3bb` on `codex/ball-detector-baseline`.
It followed the approved amendment for the exact sixth window published before
the renderer's failure at `cd51bfc1336bba76e4b118b6cfe55d7f74a3b5a6`.
The five successfully receipted original renders remained unchanged. The sixth
received independent validation and a new acceptance receipt; its original
failed attempt remains failed. Original selections, scores, rendering provenance,
all three historical failures and partial evidence remain preserved. No selection,
scoring or rendering was replayed.

All 38 focused runner tests and 13 helper tests passed. The full suite completed
716 tests in 1,873.376 seconds: 715 passed, with one existing Windows
directory-symlink skip. All 143 source/test/dependency files and three helper
sources remained unchanged. Implementation certificates and generated scientific
evidence remain frozen.

Six new supervised workers succeeded: verification, recovery preflight,
acceptance, global review finalization, independent comparison-completion audit
and review-guide creation. The final journal has 2,966 events and 56 completed
attempts: 53 successes and the unchanged three failures. No attempt is active.
Cumulative active-worker time is 3,220.103 seconds, with 11,179.897 seconds
remaining under the original limits; idle and human-review time do not consume
that allowance. The final chain tip is
`018a97a3075f46698e215c3f6e8e95cab7cbab4f926e9bad68dbbd25d6c0640e`.
The completion checkpoint is
`data/outputs/ball_tracking/crop_candidate_retention_publication_recovery_implementation/cd51bfc1336b_2026-10-02/recovery_completion_checkpoint.json`,
SHA-256 `03ddbd6151b3827afaf98070a5c8ed745f9ccd05b582b84d0c23ab8f0417e7d0`.
The completed independent audit under the real output root is
`audit/independent_publication_recovery_audit.json`, SHA-256
`a1c944c3e1a5184ff08986adacbb2e623d515a67b33a67a55075dcc3f5fc5da2`.

Ryan approved the requested six-clip final-frame review with "I approve and have
reviewed everything’s looking pretty good. Move forward chat". The new receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_visual_review_record_v0_1.json`,
SHA-256 `9a3089a14747dce7b95670838dd116b2ddaf6cd426837f93435ff6ad6706d46b`.
This records package completion and approval without invented frame verdicts,
independent native-image attestations, new identity labels or a chosen quality
gate. Generated pending-review snapshots remain unchanged. Both these six
reviews and the earlier twelve YOLO reviews are complete and must not be
requested again.

See `../ball_crop_candidate_retention_closeout.md`. This documentation-only
closeout performs no fresh scientific hashing, decoding, interpretation or test
execution. The next bounded interpretation proposal is a draft in
`../ball_crop_candidate_retention_interpretation_proposal.md`; scope approval
is next, and no interpretation worker has run. All nine embargoes and three
sealed holdouts remain protected. No method, operating point, quality gate,
training or holdout release is selected. These documents and the review receipt
remain unstaged with an empty index; no current-turn Git mutation is authorized.
