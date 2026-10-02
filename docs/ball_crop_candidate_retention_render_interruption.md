# Candidate-retention scoring complete; rendering interrupted

Ryan explicitly authorized committing the exact 15 staged recovery files.
The local commit is `f36237247191e726ad7e81bdc6651f9340a9063d`, on
`codex/ball-detector-baseline`, with parent
`0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41`. All committed blobs matched the
approved staging record; the checkout and index were clean and all validated
source/evidence hashes matched. Nothing was pushed.

The already approved recovery then ran from that clean commit. Verification
passed in one supervised worker. Scoring passed in eight workers: preflight,
six windows and finalization into separate representative and challenge pools.
The scope remains 120 new localization reports and 630 preserved reports,
using the 24 original completed selections and unchanged controls. No selection,
model inference, source-video decode or training was performed by recovery.

Rendering preflight passed in 43.266 seconds. The first rendering worker stopped
after 62.875 seconds with:

`ResourceLimitError: Output tree did not stabilize for complete byte accounting`

No retry, later rendering window or comparison-completion audit followed.
There is no completed new review clip or final review manifest. The original
twelve YOLO final-frame approvals remain complete; none are being requested again.

## Exact failure evidence

All paths below are under
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/`.

- Failed render attempt: `158f51be5ab34cdface57f4e0036b7d2`.
- Completion-event canonical SHA-256:
  `3127e069233b5cb5caa41a4088e878226289438732c48ed035c8925da359ad6c`.
- The attempt log is empty; the worker result is null. The supervisor failure
  is authoritative; an empty log does not establish the precise render operation.
- The pending directory is
  `review/windows/.pending_possession_001_frames_0050_0074_representative_evaluation_development_v0_2_6609ad1f69fa47889eae916569336db5`.
  Its observed metadata contains ten PNG files totaling 32,989,248 bytes,
  with no MP4 or successful bundle manifest. These are incomplete evidence,
  not a completed clip or material to publish as reviewed output.
- Peak worker-tree memory was 590,622,720 bytes; maximum sampled output was
  1,436,386,389 bytes; maximum measured monitor interval was .547 seconds.
  Recorded time, memory and output-byte overshoots were zero. Final byte
  accounting succeeded. These observations do not prove that measurement was
  complete during the failing half-second scan.

The journal through the failure contains 40 completed attempts: 38 successes
and two preserved failures. Cumulative active real-worker time is 1,126.944
seconds, leaving 13,273.056 seconds of the original four-hour allowance.
Any subsequent read-only diagnosis also consumes that same allowance; its
completed receipt and journal take precedence over this historical balance.

## Diagnosis and its limits

The committed monitor accepts two complete inventories only when file identities
and directory-entry multiplicities match. It tolerates changes in sizes of those
same files. The renderer creates new PNG paths repeatedly before publishing its
bundle. New identities can prevent equal-membership inventories even when total
bytes remain below the cap. A delayed traversal/stat or a rename race can also
produce the recorded error, so the exact real trigger is still inferred.

A bounded synthetic reproduction used the unchanged resource module and 2,001
prefilled dummy files per case. All three measurements passed while an existing
file grew; all three failed at the .5-second deadline while new files appeared.
Both cases measured the correct total after the writer stopped. The helper
stopped and joined both writer threads and accessed no real experiment content.
This reproduces the mechanism, not the precise real-world interleaving.

Synthetic receipt:
`data/outputs/ball_tracking/crop_candidate_retention_recovery_implementation/0a7f5bc69be9_2026-10-02/render_membership_diagnosis/receipt.json`,
SHA-256 `6a894647368b1c7a4979de6d04e74a9e94f679ca0b0c31123eea5ea518cb5973`.
Its helper SHA-256 is
`e5ba8c41f713760d26fceb2e7009d817662231d8691fb0b87ffe36b967353e35`.
The recorded synthetic elapsed time is 3.453 seconds and is separate from
real-worker accounting. Source and test files were not changed.

## Completed preservation audit

A supervised read-only audit verified the exact 24 completed selections, 600
trace files, eight completed scoring artifacts and ten partial PNGs. It also
verified the original failed scoring partial, successful worker receipts,
resource history and 137 source/test/dependency bindings. It read artifact bytes
for hashing without parsing scientific report bodies, labels, selection content
or trace content, and without decoding media. Its result is preservation
verified, comparison incomplete; it is not the independent completion audit.

The receipt is
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit/render_interruption_f362.json`,
SHA-256 `f2bece32af228b0f525b07eb060b1671194812b26af7787283c8ecca2aabea8b`.
It binds the exact file paths, sizes, hashes, worker receipts and absent final
review targets. The ignored, uncommitted helper
`audit/render_interruption_audit_f362.py` under the same output root has SHA-256
`1c57d4e280f724c51f8e56d75229b06ec120e01dcf5a48449e00946a59c3cb3a`.
That helper is separately recorded and is not attributed to the execution commit.

Diagnosis attempt `8e121d23c2494d969df9af94cc45bbeb` succeeded in 9.812 seconds.
Its canonical completion-event SHA-256 is
`19c2134889cb129bb625dbcac09c3c9beca02b5fb086088e3cb01644762f70f5`.
The raw completion file `resource_events/00001169.json` under the output root
has SHA-256 `f226a368b101d9882eb51c023995859558ff88747f2a9ed41e01fb9e63617032`.

The post-diagnosis checkpoint is
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit/render_interruption_checkpoint_f362.json`,
SHA-256 `8dce571305282e59dc61e3ceb610e2ea0e5dbd86ce1896beb9e035c8ee12dcac`.
It binds the full 1,170-event prefix and all 41 completed attempts: 39 successes
and two preserved failures. Cumulative active real-worker time is 1,136.756
seconds; 13,263.244 seconds remain. This supersedes the earlier balance above.
The checkpoint was assembled from completed audit and resource metadata after
the supervised worker finished; no scientific report body was reopened.

## Next boundary

The first recovery repaired measurement of a growing file and completed scoring.
Rendering now needs a separately reviewed amendment for additions to the file
inventory and exact reuse of the completed scoring checkpoint. The proposed
render-only recovery must preserve both failures, all partial files, completed
selections and scores, all resource history and the original budgets.

No scientific interpretation or method, operating point or quality gate is
selected here. A completed comparison audit and the six new final-frame human
reviews remain outstanding. All nine original prediction embargoes and three
sealed holdouts remain in force. Localization outcomes are not certified
ball/non-ball identity labels. The original scientific comparison approval
remains recorded; this interruption does not authorize a rendering retry.
