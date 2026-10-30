# Candidate-retention recovery proposal

**Status: draft for Ryan's review. No recovery implementation or execution is
authorized by this document.** The approved comparison stopped during its first
scoring window. Selection completed successfully for all 24 units at
`0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41`. Those outputs must be preserved and
reused without running selection again.

The proposed recovery changes resource measurement and explicit resume
provenance. It does not change the basketball question, candidates, path
arithmetic, localization rule, settings or review scope.

## Interruption and preserved checkpoint

The resource supervisor stopped the first scoring worker with
`ResourceLimitError: Output tree did not stabilize for complete byte accounting`.
The monitor currently requires two identical inventories of file identity,
size and modification time within 0.5 seconds. The scorer writes a large JSON
document incrementally before renaming it into place. An actively growing file
can therefore prevent the inventories from becoming identical. This abort
condition does not itself establish that the memory, byte or time limit was
exceeded.

Root's inspection confirmed that the first final scoring target was not
published. A 16,861,477-byte incomplete scoring file remains. It is incomplete
evidence, not a completed report or an output that may be silently adopted.
Selection's 24 completed manifests and 600 trace shards remain successful
outputs. No later scoring window or rendering stage ran after the failure.

The independently verified interruption receipt is
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit/interruption_receipt.json`.
Its SHA-256 is
`0f90a59c07dd2436ef8618ffd8d3637695b99ab3e56e08f879866d9d702e40df`.
It binds the exact 24 successful selection manifests and 600 trace hashes,
26 successful worker receipts, the resource-journal prefix through the failed
attempt, the failed partial and log hashes, and 134 unchanged source files.
The failed attempt identifier and incomplete-file path are taken from that
exact bound receipt, not inferred from a directory search or filename pattern.

At the reported interruption checkpoint, cumulative real worker time was
618.1929999999993 seconds, leaving approximately 13,781.807 seconds of the
original four-hour budget. A subsequent supervised read-only diagnosis,
attempt `4f8797ac75b543af9168098f5b9538a5`, verified the bound bytes without
selection, scoring or rendering and consumed another 2.0 seconds. Its
completion-event SHA-256 is
`00fd14c3c82c8b56ab45c633305bd22ca2f394d39b8d758acd12c82572da0ac9`.
The reported balance is therefore 620.193 seconds consumed and 13,779.807
seconds remaining. These are historical balances, not a new allowance.
The recovery must preserve the full journal through this diagnosis, including
all intermediate records, rather than stopping at the failure prefix captured
inside the interruption receipt. Any subsequent supervised worker or read-only
verification also consumes the same budget; the current journal takes precedence.

The frozen comparison remains bound to these files:

| Authority | SHA-256 |
| --- | --- |
| Original executable manifest: `configs/ball_tracking/crop_retention_experiments/rfdetr_medium_crop_candidate_retention_v0_1.json` | `f2b8834722ddf9f1ce4dcfdf1441a12cc0d52591b57bb66ca726c3aef2ca15ff` |
| Original proposal: `configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_retention_v0_1.json` | `7640784e2a64e81a2064ebb40cd4d1c77366076e5e78a2c19f8f5fc28e29fe1b` |
| Original design: `docs/ball_crop_candidate_retention_proposal.md` | `66db56a2338f86998c67c3a04f4850fa039ac7e8716cc982f5e34fb1593aff58` |
| Original approval: `configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_approval_v0_1.json` | `dcc52439d7e08f17c45f10811b4eb39b34577c23a0a3291aa347246ef6f24219` |
| Original implementation certificate: `data/outputs/ball_tracking/crop_candidate_retention_implementation/9fe6a1ef86d2_2026-10-02/implementation_validation.json` | `135bb50a461eec662f70ed4c64d15fe15e36826eefe81ee21e7521f36578890f` |

The original proposal, executable manifest, approval, certificate and reviewed
artifacts stay unchanged. The new recovery authority must reference them by
these exact bytes.

## Proposed monitor correction

Keep two complete recursive inventories and the existing bounded retry policy.
Each inventory records file identity `(device, inode)`, the number of observed
directory entries for that identity, and observed logical file sizes. Compare
the identity/multiplicity inventories rather than requiring sizes or modification
times to remain unchanged.

When identities and multiplicities agree, charge each identity's multiplicity
times its largest observed size across the two inventories. A growing file can
then produce a measurement conservative over the sizes observed in those
inventories without needing to stop writing. This is not an instantaneous
upper bound on growth after a file's size was read.
A file that shrinks between scans is still charged its larger observed size.
Counting multiplicity preserves the existing accounting of multiple directory
entries; an atomic move must not drop or double count a subtree unnoticed.

A missing path during traversal, a changed identity inventory or an incomplete
scan requires another complete scan within the existing 0.5-second measurement
window. Check that deadline during traversal and before accepting a result.
If complete membership cannot be established within the window, fail closed.
Do not silently omit a path, accept a partial inventory, ignore temporary files
or substitute a stale successful sample. An operating-system call that takes
too long must be reported as incomplete measurement or a cadence failure when
control returns; it cannot be reported as compliant.

Sizes may change between samples, as with any periodic monitor. The existing
maximum measured size, final accounting reserve, explicit overshoot reporting
and actual interval check remain. This is a correction for measuring live
writes, not a higher byte allowance or permission to ignore growth.

Keep every existing limit unchanged: one worker process tree; 8 GiB combined
resident memory; 32 GiB for the entire existing output root, including the
failed partial, audit files, temporaries and logs; at least 10 GiB free disk;
30 minutes per selection unit; and four cumulative active real worker hours
across all stages, failures, diagnosis, verification and resumed attempts.
Monitor at least once per second and between stages. Synthetic implementation
tests retain their separate recorded costs.

## Strict recovery manifest and provenance

Create a separate, versioned recovery manifest after approval, proposed at
`configs/ball_tracking/crop_retention_experiments/rfdetr_medium_crop_candidate_retention_recovery_v0_1.json`,
with a separate recovery approval record. Its canonical experiment-spec digest
will differ from the original manifest's digest. Both identities must remain
explicit; do not overwrite the original manifest or rewrite old receipts to
make them appear to belong to the recovery specification.

The recovery manifest must contain or bind an exact allowlist with:

- The original manifest's file and canonical-content hashes, original proposal,
  design, approval and validation certificate, plus the frozen six-window,
  126-control, 630-report and higher-confidence-equivalence scope.
- Exactly 24 successful original selection entries, each identifying its
  comparison unit, window and unchanged configuration; original spec digest;
  actual selection commit; manifest path/file hash and observation-content
  hash; all 25 trace paths/hashes; original candidate-input bindings; and the
  successful worker-result and resource-completion receipts that authorize
  reuse. This is an exact 600-trace inventory, not a wildcard directory grant.
- The interruption receipt, exact failed scoring attempt, incomplete-file path,
  size and hash, and the immutable pre-recovery resource-event inventory and
  chain-tip hash. This inventory includes the entire later diagnosis attempt
  and its completion event above, plus any subsequent authorized worker
  records. Bind prior successful preflight and diagnostic receipts with their
  actual roles as well; they are not new scientific outputs.
- Exact original implementation/source bindings and a new recovery validation
  certificate. The selection algorithm, its relevant dependencies and saved
  candidate/control inputs must retain their approved hashes.
- The new recovery approval, manifest schema and permitted stages. Recovery
  permits scoring, rendering and read-only verification of this comparison.
  It must not dispatch a selection stage or invoke a selector to validate an
  existing result.

Only an allowlisted original selection may retain the old specification and
commit while being consumed by the recovery run. Every accepted original
selection file, trace and completion receipt must match its exact binding.
An arbitrary old commit, matching filename, compatible schema or similar
configuration is insufficient. Reject missing, additional, modified or
unreceipted selections; do not repair them through recomputation.

Original observations keep
`ranking_code_commit = 0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41` and their original
specification digest. Detector and saved-control commits also remain unchanged.
New reports use the recovery specification and actual new evaluator commit,
while retaining each observation's actual selection commit. New review
manifests record the actual renderer commit and recovery specification. The
new execution checkpoint cannot be invented before it exists; execution must
verify a clean, separately authorized committed checkpoint with source bytes
matching the new validation certificate.

Apply this distinction in narrow recovery-specific loaders and orchestration.
Preserve the ordinary runner's strict same-specification/same-commit behavior.
Do not replace its checks with a generic allow-any-ancestor rule, accept a
receipt based only on its configuration, or relabel old outputs with the new
commit. Matching mathematics and evaluation/report definitions remain unchanged.

## Continuation and failure behavior

Use the same real output root:
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/`.
Continue its existing resource journal and unchanged resource-limit digest.
The failed attempt remains failed and charged. Preserve its incomplete bytes
in place and include them in every subsequent byte inventory. Do not create a
fresh root, reset reservations or move evidence out of accounting to obtain
more time or space.

The first scoring window may be attempted again only because its final target
was not published. It must write a fresh uniquely named temporary file and
retain the original incomplete file. Then complete the other five scoring
windows and the two separated scoring pools. This still produces exactly
120 new localization reports and reuses the original 630 reports; it does not
rescore completed controls. No completed selection is rerun.

Next produce the six already-approved .01 comparison clips and their bounded
saved-PNG review assets. The .20/.35 comparisons remain structural-equivalence
references with original cap20 headers and commits. They are not new executed
arms. No source MP4 is decoded and no model inference occurs.

Any unexpected published scoring target, changed partial, changed completed
selection, missing journal event or unbound prior receipt stops recovery for
investigation. A published target without a successful completion receipt is
not silently adopted. A subsequent resource failure also stops the sequence;
do not automatically relax limits, retry indefinitely, truncate a graph or
fall back to a candidate cap.

The prepared independent completion helper at
`audit/independent_audit.py` remains unexecuted. Its current SHA-256 is
`d15daf629f10eccb68cbd3d45c7d272b3f00bd8fce2baab35386521a32cf94af`.
If this recovery is approved, that helper needs its own explicitly recorded
revision to verify the allowed old/new provenance roles and retained failed
attempt. It must not require all historical attempts to have succeeded or
pretend the failed attempt disappeared. Its eventual execution remains
supervised and charged to the same real budget; no ranking is recomputed.

## Required implementation validation

Before real recovery, focused synthetic tests must demonstrate:

- A JSON file can grow continuously for longer than 0.5 seconds while complete
  byte measurements continue; each accepted sample conservatively accounts
  for the sizes it actually observed, including temporary and log files.
- Atomic file and directory publication, files appearing during traversal,
  hard-link multiplicity, shrinking/rewritten files and path disappearance
  cannot silently remove bytes. Unresolved membership and delayed monitoring
  still stop with a failure receipt.
- Time, memory, total-byte and free-space limits still abort the worker tree;
  final accounting and measured cadence remain enforced. Completed output and
  failure evidence survive, and retry or supervisor interruption cannot reset
  either cumulative or per-unit consumed time.
- Only exact allowlisted original selections and successful receipts can be
  reused under the new specification. Reject wrong source/specification/commit
  roles, changed manifests or traces, a changed failed partial, truncated
  history, unknown artifacts and missing validation. Assert that selectors and
  old-control evaluators are never called during recovery loading.
- New scoring preserves the actual original ranking commit and records the
  new evaluation commit; rendering and the completion audit retain their own
  actual roles. Six-window report counts, pool separation, alias deduplication,
  explicit missing observations and final-frame review checks remain valid.
- Interruption during a new score write or between publication and successful
  completion cannot cause an incomplete target to be blessed or overwritten.

Run focused tests first, then the full regression suite with bytecode writing
disabled. Record exact source, test, dependency and evidence hashes and verify
them after testing. Tests use fabricated data; completed real selectors,
experiments and reviews are not repeated to validate this correction.

An independent static review must inspect resource accounting and the explicit
provenance transition. A new validation certificate must cover the exact final
recovery implementation and its dependencies. Existing validation remains
historical evidence; it does not certify changed code.

## Authorization and next boundary

The [frozen comparison design](ball_crop_candidate_retention_proposal.md#resource-bounds-and-validation)
states: "A budget or design change requires a revised explicit scope; no
result-dependent workaround is allowed." This draft changes how live output
writes are measured and introduces a tightly bound exception for accepting
original selections across a new execution commit and specification. We
interpret that combination as a recovery design change requiring review.
The original scientific comparison approval remains valid; it is not revoked,
and this does not imply that every routine bug fix requires renewed experiment
approval. The requested decision concerns this explicit recovery mechanism.

Approval of this proposal would authorize the bounded recovery implementation
and its later execution only after the focused/full tests, exact input checks
and clean committed checkpoint requirements pass. It would not authorize
staging, committing, pushing, PR creation or merging. Each Git step still
requires its own explicit authorization.

All nine original prediction embargoes and three sealed holdouts remain
protected. Holdout content is not opened. No training, new detector, additional
setting, candidate correction, semantic identity label, selected method,
operating point or quality gate is included. MATCH/UNMATCHED remains a
localization outcome, not a training label. No reviewed player identity or
calibration decision changes.

The six new .01 clips still require Ryan's review after they are actually
produced. His completed twelve-clip YOLO review and prior higher-confidence
reviews remain complete. The immediate decision is whether to approve this
specific recovery; no recovery command is pending or implicitly running.
