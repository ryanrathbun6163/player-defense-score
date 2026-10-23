# Completion campaign: NBA reference batch 10

This increment is ready for reference acceptance for the fourth fixed DEN–BOS episode,
`den-vs-bos-0022400866_e04`, original source `132.mp4`, native frames **240–359**.
The selected window contains **120 frames**, spanning **[4,6) seconds**. The
[complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_10/review_v1/index.html)
contains **100 centers, 20 nulls and 5–8px uncertainty**. The
[two-second native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_10/review_v1/review_native.mp4)
and [12-second slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_10/review_v1/review_slow.mp4)
retain every selected frame. Every source/proposed frame, encoded center crop,
null context and full native/slow final 359 was inspected. New labels remain
pending Ryan's separate acceptance, with training and checkpoint eligibility false.

Ryan accepted all 120 NBA09 proposals through its separate
[acceptance receipt](../configs/ball_tracking/reviews/nba_completion_reference_batch_09_acceptance_v0_1.json).
Combined NBA coverage is **1,320 accepted labels: 1,196 centers and 124 nulls**;
**2,519 of 3,839 selected judgments remain unaccepted**. The NBA09
[publication audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_09/acceptance_audit/publication_audit.json)
preserves **2,742 original files**. Original NBA09 preparation records and media
retain their historical pending status. Curated coverage remains **868/1,273
accepted**, with **760 eligible centers** and **405 uncovered**.

## Fixed source and native timing

The [batch configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_10_v0_1.json)
uses the episode fixed in the
[source-role manifest](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json)
before new-model predictions. Its entire DEN–BOS parent game retains the training
role. The source is **1280×720 at 60 fps**, with a **1/60000-second timebase** and
1000-tick frame durations. Selected PTS are **240000–359000**, in the half-open
interval **[240000,360000) ticks**. Batch final is **359**; the full 579-frame
source ends at **578**. Native time [4,6)s and review-relative time [0,2)s remain
distinct. Complete review retains all 120 frames, giving two seconds at 60 fps
and 12 seconds at slow 10 fps.

## Completed source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_10/preparation.json)
and [source-pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_10/source_pixel_audit.json)
pass all **120 selected native PNG comparisons and PTS checks**. Saved PyAV
pixels match explicit BT.709 FFmpeg RGB conversion exactly; original PNGs remain
unchanged. All **2,696 files captured before preparation** are preserved. Both
decoder paths use FFmpeg components, establishing transport consistency rather
than independent visual truth.

The primary decoder submitted **361 packets** and returned **frames 0–359**.
The alternate conversion emitted **360 RGB frames** and reported **361 filter
frames, 0–360**. Frames 0–239 and filter frame 360 are disclosed context from the
same training-role source, not additional labels or review frames. Only selected
frames 240–359 were saved. Preparation succeeded on its first attempt in
**22.086 seconds**; no config or source-preparation failure occurred.

## Completed reference inspection

The [assembled proposal](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_10/proposal.json)
contains **120 judgments: 100 centers and 20 nulls**, with
**5–8px center uncertainty**. Visibility is **68 fully visible, 40 partially
visible, two indeterminate and ten not visible**; eight partial judgments have
null geometry. The selected scene starts with a contested shot lift/release,
continues flight above the top edge and re-entry, then descends through the
rim/net toward the baseline.

Nulls span **270–289**: partial fragments at **270–273 and 286–289** do not
support whole centers, **274–275** preserve ambiguous edge pixels, and
**276–285** contain no supported ball pixels. Current lower/side arcs support
re-entry centers **[391,4] at 290–291 with 7px uncertainty**; 292–293 remain
partial with 6px uncertainty. Nothing is interpolated through the gap or clamped
to the image boundary. Rim/net overlap remains partial at **324–337**; the
final center at 359 is **[279,384] with 6px uncertainty**.

Every current source context/detail and proposed overlay was inspected, including
each part's full endpoints. Additional source edge sheets preserve the clipping
and re-entry judgments; three extra rim/net sheets preserve that overlap judgment.
The [exception list](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_10/review_v1/exception_list.json)
contains all 20 nulls with source context crops. These pending proposals leave
**2,399 selected positions without proposals**; accepted coverage is unchanged.

The [first-part receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_10/inspection/part_240_279_receipt.json)
retains two routine tooling notes: an oversized endpoint image response was
reopened successfully, and an initially absent documentation filename was
resolved through search. These did not alter source or annotation artifacts and
are distinct from annotation-helper failures. All three sealed parts
retain their first written proposals without corrections or failed helper runs.

Centers are proposed manually from each current image, without model coordinates
or temporal interpolation. Uncertainty is a non-statistical placement estimate.
AI authorship remains explicit; fixed training role does not accept labels.
The renderer and acceptance reader are unchanged; their prior **13-test and
12-test evidence** remains historical, with no new suite run. The original
eight-test acceptance-reader record remains separate retained history.

## Complete review validation

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_10_result_v0_1.json)
has status `ready_for_human_reference_acceptance`. The
[integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_10/integration_audit.json)
passes **3,049 file bindings, 120 native source/annotation joins, 240 encoded
frames and 200 center markers**. Both videos contain all 120 selected frames
at 60/10 fps (2s/12s); emitted color metadata and every encoded-frame comparison
pass. All ten inspection sheets, 100 encoded center crops and 20 null source
contexts were inspected through actual batch final 359. Full native source
359 and both full encoded finals were also inspected. Final frame 359 retains
center **[279,384] with 6px uncertainty**. The
[complete AI visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_10/inspection/root_visual_review.json)
binds these inspections and additional source-edge details for 264–279 and
280–297. This AI review does not supply Ryan's acceptance.

The actual pending-review consumer passes all 120 annotation/native joins and
creates zero accepted labels. All **1,320 accepted NBA labels** and **868 curated
references** remain unchanged. The audit also verifies the **2,696 files** saved
before source preparation and prior acceptance snapshots of **286, 543, 809,
1,050, 1,549, 2,000, 2,245, 2,490 and 2,742 files**; these preservation sets
overlap. No new tests, inference or fitting ran. Current source/annotation/media
validation is separate from historical test coverage and is not a model-accuracy
or independent human-ground-truth claim.

| Evidence | SHA-256 |
| --- | --- |
| Final result | `ea8497d5e935fb357d6927b0e6a49035028ad22463f9a48792d003aa3bafce3f` |
| Integration audit | `7124fac091dbe856359d1ade7b832dcbefc10167dc99b7be885f9357d47f03f3` |
| Complete AI visual receipt | `31666d03f7fa315cd34f8926d12cbe6d095b947b923d606aff335ca40eb60ae5` |

## Next step

Record Ryan's separate acceptance or corrections after the complete review.
Until then all 120 NBA10 proposals remain pending, including uncertainty and
null centers; NBA09's acceptance does not cover them. Finish the accepted
source/label/role package and
freeze the executable recipe before the already approved fit. No fitting or
protected evaluation has run; protected evaluation still requires a frozen method
and separate explicit authorization.
