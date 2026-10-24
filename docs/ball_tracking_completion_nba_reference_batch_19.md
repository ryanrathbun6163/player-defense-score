# Completion campaign: NBA reference batch 19

This increment prepares fixed training SAC–MEM episode
`sac-mem-0022500829_e01`, native frames **5092–5211**. Its **120 pending
judgments** contain **60 centers and 60 nulls**, with **7–10px center
uncertainty**. The complete native/slow review includes every selected frame
through actual final 5211. Ryan's reference acceptance remains pending;
preparation and AI inspection create no accepted labels.

## Fixed role and native timing

The [configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_19_v0_1.json)
retains the unchanged [source roles](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json).
SAC–MEM was assigned training before new model predictions. Pending proposals
remain ineligible for training or checkpoint selection until accepted.

The full source is **1920×1080**, with **357,233 frames** and timebase
**1/90000**. The fixed selection window is [85,87) seconds; the selected images
have native PTS **7650962–7829702**, and their complete presentation interval
ends at **7831142**, lasting **2.002 seconds**. Actual presentation intervals
are **16/17ms**. Batch final **5211** differs from full-source final **357232**.

Additive [SAC renderer support](../src/ball_tracking/completion_sac_references.py)
and [acceptance support](../src/ball_tracking/completion_sac_acceptance.py)
preserve the legacy implementations already bound to earlier reviews. The
next global presentation PTS determines each image's display duration;
raw packet duration remains separate evidence because reordered packet
duration need not equal presentation duration. Nominal 60 fps never substitutes
for the actual native timing. Both emitted packet and decoded-frame timestamps
are checked against the requested timelines.

## Source preparation and preserved incidents

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/preparation.json)
and [pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/source_pixel_audit.json)
pass all **120 exact PNG/PTS checks**, preserving **5,828 prior files**. Source
preparation passed its first execution in **54.340 seconds**. Primary decoding
returned **178 frames, 5034–5211**, from **180 submitted packets**. Prefix
5034–5091 and submitted context through 5213 inherit the fixed training role;
only selected frames 5092–5211 were saved. Secondary conversion emitted **120
RGB frames** and reported **120 filter frames**, exactly the selected range.
Both paths use FFmpeg components; this verifies pixel transport rather than
independent ground truth.

The initial delegated preparer was interrupted before producing code or
decoding source pixels. Root then implemented the narrow preparation helper;
the first source execution and first delivery both succeeded. Read-only
missing-path searches and old-directory access denials made no evidence
changes. Their history remains retained rather than being described as
successful preparation attempts.

Root's initial broad source crop missed the ball at its right edge. The unused
original remains retained, and corrected precision crops were viewed before
labeling. No annotation correction or overwrite followed publication.

## Proposals and inspection

Visibility comprises **70 partially visible, 40 not visible and ten
indeterminate judgments**. All 60 centers remain partial, with **7–10 native
pixel uncertainty**. Unknown centers span **5108–5144, 5164–5183 and
5193–5195**. These intervals include certain obscuration, unresolved identity
or fragments that do not support a defensible whole-ball center. They remain
null without interpolation.

| Native frames | Centers | Nulls | Inspection receipt |
| --- | ---: | ---: | --- |
| 5092–5131 | 16 | 24 | [First part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/inspection/part_5092_5131_receipt.json) |
| 5132–5171 | 19 | 21 | [Middle part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/inspection/part_5132_5171_receipt.json) |
| 5172–5211 | 25 | 15 | [Final part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/inspection/part_5172_5211_receipt.json) |

The team inspected every current source/proposed frame and each full part
endpoint. Final 5211 supports **[1708,427] ±8 pixels**, partially visible under
the right hand, using exposed lower and side contours. These are AI proposals
and AI visual checks, not independent human ground truth. The legacy geometry
source string does not change the recorded AI authorship. All initial
annotations remain unchanged.

## Complete review and validation

- [Complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/review_v1/index.html)
- [Native overlay: 2.002 seconds with original variable timing](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/review_v1/review_native.mp4)
- [Slow overlay: 12 seconds at 10 fps](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/review_v1/review_slow.mp4)
- [All 120 proposals](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/proposal.json) and [60 null-center exceptions](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/review_v1/exception_list.json)
- [Review manifest](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/review_v1/manifest.json) and [delivery record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/review_v1/delivery_result.json)
- [Root visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/root_visual_review.json)

Delivery passed its first attempt in **36.969 seconds**. Actual records verify
**120 source/annotation joins and 240 emitted frames and their timestamps**,
alongside all source PNG bindings and pixel matches. Null exceptions remain
unmarked. Root inspected all ten emitted/source sheets, all **60 localized
centers and 60 null contexts**, both actual encoded finals and the full unmarked
source image 5211. The delivery record preserves its earlier
`rendered_awaiting_root_visual_inspection` status; the later visual receipt
and final result supersede that status without overwriting it.

The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_19_result_v0_1.json)
and [integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/integration_audit.json)
pass **6,309 bindings, 120 native joins, 240 encoded frames and 120 markers**,
plus all **120 exact source PNG matches**. Finalization passed its first
attempt in **36.828 seconds**, including the actual pending-review reader
check; the integration audit took **25.656 seconds**. The reader passes all
120 joins and creates zero accepted labels. Source preparation, delivery,
inspection and finalization preserve their distinct execution records.

**Ten renderer and eight acceptance tests pass**, with zero failures, errors
or skips. The [complete acceptance receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_19/focused_validation/acceptance_complete.json)
records **22.699 seconds** for four contract checks plus four actual completed
SAC result/timing/uncertainty/mixed-inventory checks. The earlier four-contract
run is preserved and is not four additional distinct tests. Synthetic
test-only acceptance stayed isolated, created **zero campaign accepted
labels**, and is not Ryan's acceptance. Historical eight-test and 12-test
acceptance receipts and 13-test renderer evidence retain their original
implementation scope. No implementation changes followed the tests, and no
full-suite rerun is claimed.

## Campaign status and next decision

NBA18 was already accepted. Ryan's latest structured acceptance response repeats
that decision, so no duplicate acceptance publication is needed. The accepted
NBA inventory remains **2,880/3,839 judgments: 2,638 centers and 242 nulls**,
comprising **1,920 training and all 960 checkpoint-validation judgments**.
All prior accepted records remain unchanged, and validation references remain
excluded from gradient fitting.

**Six SAC–MEM batches totaling 959 judgments remain unaccepted**, including
these 120 proposals. The other five fixed episodes contain **839 judgments**
without proposals. Curated coverage remains **868/1,273 accepted, 760 eligible
centers and 405 uncovered**, evaluation-only.

Next is Ryan's acceptance or correction of the complete NBA19 review, then the
remaining fixed references. Complete accepted source/label/role manifests and
the frozen executable recipe are still required before the already approved
fit. No model inference, fitting, checkpoint scoring or protected evaluation
ran. Protected evaluation remains closed pending a frozen method and separate
explicit authorization.
