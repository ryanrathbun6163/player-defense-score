# Candidate-retention execution interrupted during scoring

The approved comparison started from the clean tested commit
`0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41` on
`codex/ball-detector-baseline`, after Ryan separately authorized staging and
committing the exact 24-file implementation scope. All 24 new selection units
completed. Scoring preflight completed, but the first scoring window stopped
with `ResourceLimitError: Output tree did not stabilize for complete byte accounting`.
No scoring retry or rendering followed. There is no completed accuracy
comparison or new visual-review package.

The historical implementation checkpoint remains
`ball_crop_candidate_retention_implementation.md`. Its precommit and
pre-execution statements describe that earlier checkpoint. The frozen proposal,
approval and experiment manifest retain their exact committed bytes.

## Completed work and preserved interruption

Selection used 25 successful supervised workers: the selection preflight plus
24 window/setting units. The scoring preflight was the twenty-sixth successful
worker. The first scoring worker failed, giving 26 successful workers and one
failed worker in total. The 24 selection outputs and their complete traces
remain saved; none has been rerun or replaced.

There are no successful window scoring reports, aggregate pools, rendered
clips or new clip approvals. The completion-audit script had been prepared but
was never executed. These interruption checks are not a completed independent
comparison audit and do not support a comparison-accuracy claim.

All run evidence is retained under:

`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/`

The failed attempt is `e1ba648def3f4e1f887332e850396e4c`. Its completion-event
SHA-256 is `9031c188c940980de2c858d59722114aaa8dcd68f2b70d314a9bfb0ff1d40104`.
The worker log is empty and its worker result is null. The interrupted JSON
write remains as this 16,861,477-byte file beneath the run root:

`evaluation/windows/possession_001_frames_0050_0074_representative_evaluation_development_v0_2.json.incomplete-f295c1ac00f64b8a96ed924fe55650d1`

The ignored `audit/interruption_receipt.json` binds the completed limited
forensic audit. Its SHA-256 is
`0f90a59c07dd2436ef8618ffd8d3637695b99ab3e56e08f879866d9d702e40df`.
No partial file or resource history is removed.

This audit verified 24 selection-manifest hashes and canonical content,
600 compressed trace hashes, all 27 pre-diagnosis attempt seals and their
journal hash chain, 134 source bindings, six saved crop files, 126 saved
controls, absence of all nine embargo outputs and the metadata of three sealed
holdouts. It did not decompress traces, open holdout contents or rerun
selection, scoring, rendering or inference. It verifies preserved evidence;
the full comparison-completion audit remains unexecuted.

The single supervised diagnosis worker completed in 2.0 seconds, under attempt
`4f8797ac75b543af9168098f5b9538a5`. Its finished-event SHA-256 is
`00fd14c3c82c8b56ab45c633305bd22ca2f394d39b8d758acd12c82572da0ac9`.
Including this diagnosis, 28 attempts comprise 27 successful workers and one
failed worker. Consumed active time is now 620.193 seconds, leaving 13,779.807
seconds of the original cumulative budget. The maximum recorded output size
increased to 882,157,412 bytes; peak resident memory and the maximum monitoring
interval remained unchanged. Diagnosis does not reset consumed budgets.

## Resource observations and failure mechanism

| Recorded measurement through the interruption | Value |
|---|---:|
| Cumulative active worker time, seconds | 618.1929999999993 |
| Peak worker-tree resident memory, bytes | 279,302,144 |
| Maximum sampled output-tree size, bytes | 881,741,466 |
| Maximum recorded monitoring interval, seconds | 0.469 |
| Recorded resource-limit overshoots | 0 |

The failure concerns accounting certainty, not a recorded time, memory or
output-limit overrun. In the committed implementation, `output_bytes` requires
two identical whole-tree inventories within half a second. Each inventory
includes file identity, size and modification time. The scoring writer writes
a large JSON document continuously into a create-only temporary file before
renaming it into its final checkpoint. A growing file can therefore change
between scans even when directory membership is stable.

The observed error and retained partial JSON are consistent with this conflict
between continuous writing and the monitor's stability requirement. The empty
worker log and null result do not provide an additional worker traceback.
The monitor stopped execution rather than treating uncertain accounting as a
valid sample. No silent repair, relaxed bound or automatic retry occurred.

## Next boundary

The bounded recovery design is described in
`ball_crop_candidate_retention_recovery_proposal.md`. It must preserve completed
selection units, partial failure evidence, persistent consumed budgets and the
original comparison scope. The original scientific approval remains valid.
The proposed measurement of live writes and reuse across execution commits
amend the execution contract. The frozen proposal says, "A budget or design
change requires a revised explicit scope"; this concrete amendment is ready
for approval under that boundary. No recovery code has been implemented.
Any later staging, committing,
pushing, PR creation and merging remain separate explicit decisions.

All nine original prediction embargoes and three sealed holdouts remain in
force. Ryan's prior twelve YOLO final-frame approvals and previous comparison
reviews remain complete. The six new retention clips still need to be generated
and reviewed through their final frames after successful recovery. No method,
operating point, quality gate or training is selected or authorized. Candidate
retention, uncertain object identity and center placement remain separate;
localization MATCH/UNMATCHED outcomes are not certified ball/non-ball labels.

Tracked changes in this checkpoint are documentation only. Committed source,
tests, configs, frozen proposals and all saved outputs remain untouched.
Documentation remains unstaged and the index empty; no Git mutation is part
of this interruption record.
