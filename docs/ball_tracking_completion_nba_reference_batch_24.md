# Completion campaign: NBA reference batch 24

NBA23 is accepted, bringing NBA coverage to **3,599/3,839 judgments: 3,223
centers and 376 nulls**. This increment prepares the last fixed NBA episode,
SAC–MEM training e06, **240 native frames, 197799–198038**. Source preparation
passes. The sealed proposals retain **200 centers, 40 unknown centers and 6–10px
uncertainty**. Complete source/overlay review and final integration pass through
actual final **198038**. The [final result](../configs/ball_tracking/reviews/nba_completion_reference_batch_24_result_v0_1.json)
is ready for Ryan's acceptance; no NBA24 label has been accepted.

## Fixed role and native timing

The [configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_24_v0_1.json)
and unchanged [source roles](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json)
assign episode `sac-mem-0022500829_e06` to training. The fixed selection window is
**[3300,3304) seconds**, or **[297000000,297360000) ticks** at timebase **1/90000**.
It selects **240 native frames, 197799–198038**, from the **1920×1080** full source.
The source contains **357,233 frames**, with full-source final **357232**;
batch final **198038** remains distinct.

Native PTS span **297000512–297359432**, with final presentation end **297360872**,
covering **4.004 seconds**. Presentation intervals remain variable **16/17ms**,
derived from the next global PTS; raw packet durations remain separate. Final
presentation duration is **1440 ticks**, while raw packet duration is **1530
ticks**. The original fixed `recovery` selection category remains unchanged.
Current source inspection preserves obscured/ambiguous intervals and subsequent
visible centers; no tracker recovery or performance result is claimed.

## Source preparation

The [preparation record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_24/preparation.json)
and [pixel audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_24/source_pixel_audit.json)
pass their first attempt with **240 exact native PNG/PTS checks** in **128.240 seconds**, preserving
**7,610 preexisting files**. Primary decoding returned **597 frames,
197442–198038**, after **599 submitted packets**. The **357 decoded prefix
frames, 197442–197798**, inherit the training role; only selected frames
197799–198038 were saved. Secondary conversion emitted **240 RGB frames** and
reported **240 filter frames**, exactly the selected range. Both paths use
FFmpeg components; matching pixels verify transport rather than independent
ground truth.

## Proposals and complete review

The **240 AI-assisted proposals** contain **200 centers and 40 nulls**. Visibility
is **23 fully visible, 181 partially visible, 34 indeterminate and two not
visible**; center uncertainty spans **6–10 pixels**. A null center can coexist
with partial visibility when the fragment does not support an amodal center.

| Native frames | Centers | Nulls | Visibility |
| --- | ---: | ---: | --- |
| 197799–197878 | 52 | 28 | 4 full, 48 partial, 28 indeterminate |
| 197879–197958 | 80 | 0 | 8 full, 72 partial |
| 197959–198038 | 68 | 12 | 11 full, 61 partial, 6 indeterminate, 2 not visible |

Null ranges are **197846–197861, 197867–197878, 197993–197998 and
198008–198013**. The [first](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_24/inspection/part_197799_197878_receipt.json),
[middle](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_24/inspection/part_197879_197958_receipt.json)
and [final-part](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_24/inspection/part_197959_198038_receipt.json)
receipts bind actual inspection of every current source frame, proposed overlay
and full part endpoint. Final **198038** retains **[704,233] ±10 pixels**, fully
visible. No coordinates come from interpolation or model predictions.

Bounded second AI source-only reviews corroborate conservative nulls at ambiguous
body/limb boundaries and the partial emergence at **198014, [646,480] ±10 pixels**.
These reviews cover only their explicitly recorded frames and do not constitute
human acceptance. All three initial proposals remain unchanged. No source
preparation or annotation helper failure is recorded. The final-part receipt
preserves one read-only display truncation affecting four sheets covering
**198023–198038**. All four were reopened in smaller calls and inspected before
proposal writing; no generation failed or artifact changed.

The [delivery record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_24/review_v1/delivery_result.json)
passes its first attempt in **62.719 seconds**. The
[review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_24/review_v1/index.html)
provides complete **4.004-second native** and **24-second slow overlays at 10 fps**,
with **240 frames in each**. The [completed visual receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_24/root_visual_review.json)
records actual inspection of all **20 emitted/source sheets**, covering every
one of the **200 center crops and 40 null contexts**, plus the full source final
and both actual encoded finals at **198038**. No geometry or visibility
corrections followed initial proposal publication. This is AI inspection, with
no playback telemetry or independent human annotation claimed. New labels remain
ineligible pending Ryan's acceptance; both eligibility flags remain false.

## Focused validation

The [current renderer receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_24/focused_validation/20261025T041908Z_d495eae7/references.json)
passes **ten tests** on NBA24's actual proposal and complete emitted media in
**31.422 seconds**, with no failures, errors or skips. The inner unittest run
reports **30.567 seconds**. NBA19's eight acceptance tests remain historical
coverage of unchanged reader/test code; they were not rerun.

The [first finalization record](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_24/finalization_attempts/20261025T043540Z_898a1c51/completed.json)
passes in **104.765 seconds**. Its [integration audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_24/integration_audit.json)
passes in **93.140 seconds**, checking **8,331 bindings, 240 annotation/native
joins, 480 encoded frames, 400 markers and 240 exact source PNGs**. All **3,599
accepted NBA rows, 868 curated references and 7,610 preexisting preparation
files** remain unchanged. The [current pending-consumer check](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_24/finalization_attempts/20261025T043540Z_898a1c51/pending_review_reader_check.json)
independently reads **240 annotation/native joins**, accepting **zero new labels**.
Finalization performs no new source pixel decoding, inference, fitting or scoring.

## Campaign status and next decision

[NBA23's separate acceptance](ball_tracking_completion_nba_reference_batch_23.md#human-acceptance-published-2026-10-24)
preserves all earlier labels, failures and review evidence. Accepted NBA roles are
**2,639 training and all 960 checkpoint validation**; validation labels remain
excluded from gradient fitting. NBA24's **240 judgments** are the remaining
unaccepted fixed NBA selection; no selected NBA frame remains without a proposal.
Curated coverage remains **868/1,273 accepted,
760 eligible centers and 405 uncovered**, evaluation-only.

Next is Ryan's acceptance or correction of all **240 NBA24 judgments**, including
the **40 unknown centers** and stated uncertainty.
Complete accepted source/label/role manifests and the executable recipe still
need freezing before the approved fit. Fitting, checkpoint scoring, protected
evaluation, model-output acceptance and ball-phase completion remain closed.
