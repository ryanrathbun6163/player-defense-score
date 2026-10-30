# Training response capture and support census

October 28, 2026. **Completed approved capture and CPU diagnosis; no training,
selector or model adoption.** The unchanged cosine-nine research control now has
saved response maps for all 26 original training blocks and 3,329 unique source
frames. This closes the missing-map question in the
[preparation decision](ball_tracking_training_response_preparation.md).

## Outcome

The weak pool supplies 373 candidates on 130 of 147 certain-hidden frames,
compared with two native candidates on two frames. Both native-emission frames
also have weak candidates; 128 previously abstaining frames therefore add
rejection opportunities. Seventeen hidden frames have no candidate and remain
in the denominator. These are extracted candidates, not newly published false
outputs or evidence that a rejection rule already works.

There are 674 geometrically matching weak candidates on 674 eligible frames:
462 partially visible and 212 fully visible. Of these frames, 673 already have a
correct native selection. Only one is native-missing, CHI e02/frame83. None has
a wrong native selection. These counts do **not** represent 674 recoveries or
evidence of generalization to the difficult NBA development failures.

## Complete source coverage

Matching requires source bounds and the unchanged inclusive ten-source-pixel
tolerance. Eligible, certain-hidden and masked counts retain original accepted
references. No semantic object labels were added.

| Training source | Eligible / hidden / masked frames | Matching weak candidates and frames | Weak hidden candidates / hidden frames with them |
| --- | ---: | ---: | ---: |
| CHI–IND | 836 / 50 / 74 | 250 | 127 / 43 |
| DEN–BOS | 920 / 10 / 30 | 183 | 12 / 8 |
| SAC–MEM, including original SAC windows | 1,055 / 68 / 136 | 177 | 174 / 62 |
| NFHS possession 001 replay | 74 / 1 / 0 | 28 | 10 / 1 |
| NFHS possession 002 replay | 31 / 18 / 1 | 23 | 50 / 16 |
| NFHS possession 003 replay | 25 / 0 / 0 | 13 | 0 / 0 |
| **Total** | **2,941 / 147 / 241** | **674** | **373 / 130** |

Support is present in all three NBA training games, but uneven: DEN contributes
only eight hidden frames with weak candidates. Adjacent frames and candidates
are correlated. There is no source-frame overlap among these 3,329 rows; this
does not make them statistically independent examples. NFHS remains secondary.

All 19,632 retained candidates are accounted for:

- Eligible frames: 3,049 native candidates (2,953 matches, 96 localization
  misses), plus 14,980 weak candidates (674 matches, 14,306 localization misses).
- Certain-hidden frames: two native and 373 weak candidates.
- Masked frames: 111 native and 1,117 weak candidates, all unscored/unknown.
- The 21 empty pools comprise 17 certain-hidden and four masked frames. Eligible
  frames all have candidates, but two still have no geometrically matching one.

The 241 masked rows include 51 probable-hidden, 100 partially visible and 90
indeterminate frames. Their 1,228 candidates are not converted into negatives.
Recorded identity certainty and geometry uncertainty remain in the full census.
Of the localization misses, 70 native and 14,262 weak candidates lie beyond ten
pixels plus recorded placement uncertainty. The remaining 26 native and 44 weak
misses fall within that descriptive band. This neither changes the ten-pixel
criterion nor creates a formal confidence interval or semantic non-ball label.

Original native training outcomes remain 2,937 correct, three wrong and one
missing among 2,941 eligible frames. The full pool contains a match on 2,939:
CHI e02/frames0–1 remain uncovered; frame70 has a correct native alternative;
frame83 has the sole additional weak-only match. No new choice was made.

## Execution and verification

Ryan explicitly approved the concrete capture, then reported rebooting and
ending MSI True Color. The prior GPU-unavailable prelaunch block, Windows
graphics events and all failed preparation actions remain preserved. Fresh
readiness checks verified the expected GPU and existing graphics-app isolation.
Lively restarted again and was temporarily stopped; no startup, driver, clock,
fan or timeout setting was changed.

One owned-job monitored capture completed **2,995/2,995 attempted/returned
forwards**, reusing 288 exact previously saved SAC means. Every saved frame mean
hash and complete native observation equals the original training assessment.
The model tensors are unchanged. Raw maps occupy **4,417,932,544 bytes** including
NPY headers. All candidate pools were sealed before reference-assisted analysis.

Worker time was 131.282 seconds; total supervised time was **141.985 seconds**.
Across 70 telemetry samples, maximum temperature was **55 C**, maximum GPU memory
2,496 MiB and maximum power 130.4 W. The supervisor exited zero, with no stop
reason or remaining owned processes. No matching System/Application graphics
events were observed between capture start and the post-run query. This successful
run does not establish a cure for the earlier graphics failure.

The CPU audit passed **65,491 checks in 18.749 seconds**. It checked every saved
mean/native record, actual pool transport, all 5,990 journal events, import and
call accounting, source/reference joins, bounds, distances and original scored
outcomes. Component extraction deliberately reuses the frozen kernel; it is not
an independently reimplemented connected-components algorithm. A separate
standard-library recount passed **125,019 checks** of actual source/category/frame
accounting, with no repeated map extraction or model execution.

The nine original focused tests remain their original runs; no full suite or
completed experiment was repeated merely to resume. Before the first audit, its
helper's distance-only test was corrected to require source bounds too, and
native statuses were cross-checked against original producer outcomes. The
earlier helper and revision note remain saved. No capture code changed. Also
preserved: the earlier runtime-version probe unexpectedly initialized CUDA and
exited its CPU guard before any model load/forward; a corrected metadata check
then passed. That preparation event is separate from this successful capture.

## Interpretation and decision boundary

The [post-reboot reassessment](../data/outputs/ball_tracking/training_response_preparation_v0_1/reboot_resume_v0_1/decision_reassessment.md)
reuses the completed Sessions1–16 review, selected foundation coverage,
Session17/18 handoffs and subsequent weak/response/point/change evidence. Current
reports, producer records, capture code, bindings and relevant operational
evidence were inspected again. The earlier research-ledger and DeepSport/SAM3
primary-source reconciliation is reused; no fresh full-transcript or every-paper
reread is claimed. Independent implementation review has its own recorded scope.

The result closes a training-support gap: useful weak positive and hidden-frame
rejection opportunities exist across the permitted training scenes. It also
confirms a severe limitation: almost all matching weak examples accompany already
correct native outputs from a model fitted on these scenes. Candidate quantity
alone cannot justify a classifier or show coverage of the hard e01/visibility
failures. Geometric misses still do not establish what object was seen.

Consequently, this result supports specifying a later experiment only after its
target, data construction and evaluation are justified. It does not freeze or
authorize a training architecture/recipe. Candidate-centered pixels, separate
presence modeling, joint/temporal evidence and a bounded different-model
comparison remain open alternatives. No new direction is selected here.

Preserve point information and its e01/historical failures, all shared/added
hidden emissions, below-.01 recovery evidence and the nine source-uncertain
recoveries. The .01 pool is not exhaustive. NBA remains the goal; cosine nine is
research control; HOU is excluded from fitting and DET cannot tune the method.
All accepted references, data roles, numerical/human gates and pending trajectory
reviews remain intact. Protected evaluation stays closed. No fit follows
automatically, and Git staging/commit/publication remain unauthorized.

## Evidence

- [Capture completion](../data/outputs/ball_tracking/training_response_preparation_v0_1/capture_attempt_001/completed.json), with 26 bound block records and their raw means/pools.
- [GPU supervision](../data/outputs/ball_tracking/training_response_preparation_v0_1/monitoring/capture_attempt_001/finished.json).
- [Complete CPU census and audit](../data/outputs/ball_tracking/training_response_preparation_v0_1/reboot_resume_v0_1/post_capture_audit_v0_1/completed.json), with every frame, per-game/block/visibility/uncertainty and native-selection partitions.
- [Independent implementation review](../data/outputs/ball_tracking/training_response_preparation_v0_1/reboot_resume_v0_1/independent_review.json).
- [Independent source/count recount](../data/outputs/ball_tracking/training_response_preparation_v0_1/reboot_resume_v0_1/independent_post_capture_recount.json).
- [Result ledger](../configs/ball_tracking/reviews/training_response_capture_result_v0_1.json).
