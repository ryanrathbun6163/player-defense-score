# Completion campaign: reference batch 05

Work began on clean `codex/ball-detector-baseline` at
`eb905187df13bdd6c22ffe4c23e88f88eb98cd06`, with all 766 accepted references
and four campaign acceptance receipts verified unchanged.
Ryan requested a shutdown pause, then explicitly resumed on 2026-10-22.
The saved source frames and completed second part were reused. Resume checks
verified all 75 checkpointed batch files and all 829 earlier campaign files;
the first labeling part and complete review were then finished.

This batch contains **43 P002 proposals, frames 275–317 inclusive**. It is the
longest remaining uncovered contiguous run reachable from a keyframe inside a
permitted segment. Selection used the accepted inventory and packet metadata
before source inspection, without model outputs. Keyframe 250 follows the
protected 175–249 band. Longer late gaps in P001/P003 have no safe preceding
keyframe after their protected bands.

## Complete review

The [review page](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_05/review_v1/index.html)
contains every frame in a **1.72-second native-speed** and **8.6-second slow
overlay**, frame controls, all judgments and unmarked source crops for exceptions.
Frame 317 is the batch final; the possession's actual final is 498. Native PTS
spans **[11.04,12.76) seconds**, separately from clip-relative **[11.00,12.72)**.

The sequence shows held-ball handling, dribbles, body overlap and a low crossover.
There are **37 proposed centers**, with **4–10-source-pixel uncertainty**, and
**six null centers**:

- Certain occlusion: 294–296.
- Visible fragments without a defensible complete-ball center: 293 and 312.
- Indeterminate visibility: 313.

Visibility counts are seven fully visible, 32 partially visible, three not
visible and one indeterminate. All original draft parts remain final, with no
post-draft corrections. Source-only second reads supported conservative nulls
for the narrow fragments and ambiguous crossover frame.

Centers use current source pixels, not model predictions or temporal
interpolation. Uncertainty is an AI point-placement estimate, not a calibrated
confidence interval. The legacy `human_amodal_estimate` enum describes the
whole-ball convention; it does not change the recorded AI authorship.

Ryan's acceptance of these new proposals remains pending. All **766 accepted
references**, including **683 eligible centers**, remain unchanged; **507**
permitted positions are still uncovered. If all 43 proposals are accepted,
coverage becomes **809/1,273**, with **464** uncovered. These references remain
evaluation-only and cannot be used for fitting or checkpoint selection.

## Validation and preservation

Primary PyAV decoding entered at original keyframe 250 and returned frames
250–317 only. Codec reordering required **70 submitted packets**, with maximum
presentation index 322. Independent comparison copied **73 original packets,
250–322**, verified every payload hash and PTS/DTS before decoding, and returned
only output frames 250–317 with OpenCV. All **43 selected native PNGs match
exactly**, including final 317. Both decoders may share FFmpeg internals; all
context remained permitted. Protected P002 frames 175–249 were never submitted,
copied or decoded.

All 43 source frames and final review crops were visually inspected, including
the complete encoded final frame 317. Both videos passed checks on all **86
encoded frames** and **74 localized marker regions**. The final integration
audit verifies **944 file bindings**, exact annotation/native-frame joins, all
local review links and preservation of the 829 earlier campaign files. These
checks establish record/media integrity, not independent ground truth or human
acceptance.

The renderer, parser and tests are unchanged. The prior ten focused tests remain
evidence for that implementation and were not rerun; this increment checks its
actual emitted records. Source preparation and its alternate audit completed on
their first attempts. Routine inspection path/runtime errors and recovery are
retained in the local inspection history.
Two metadata checks needed routine corrections: the resume checker initially
counted 17 reference authorities against a returned list that also includes
four receipts; the finalizer initially compared a three-field PNG binding with
a record that additionally contains `frame_index`. The corrected checks verify
17 authorities plus four receipts, and independently match each PNG's path,
hash, size and frame identity. Original failed attempts, consumed time and the
original helper remain preserved. No media or annotations changed to pass them.

The [preparation result](../configs/ball_tracking/reviews/ball_completion_reference_batch_05_result_v0_1.json)
binds the exact proposals, source and media audits, and inspection receipts.
Generated labels, source PNGs and videos remain ignored by Git.

No fitting, inference, model scoring, threshold changes or player-pipeline reruns
occurred. Protected evaluation remains closed pending a frozen method and
separate explicit authorization. The completion plan and ball-quality criteria
remain approved.
