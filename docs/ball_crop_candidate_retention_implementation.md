# Candidate-retention implementation checkpoint

Ryan approved the exact bounded comparison on October 2, 2026 with
"I approve. Please move forward chat". The separate approval record is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_approval_v0_1.json`.
The approved proposal and design retain their original bytes and historical
draft status; the approval record supplies the current authorization.

Implementation is prepared on `codex/ball-detector-baseline`, based on
`9fe6a1ef86d23391c64b7d5b16198ad7bb005c25`. Real execution has not begun.
The new experiment output root remains absent. Implementation and validation
are complete; the next boundary is separate authorization to stage the exact
24-file scope below.

## What the implementation tests

The question remains whether keeping more saved candidates helps the existing
path scorer, and which wrong choices or resource costs it introduces. The
implementation removes only the cap, from both current and historical frames,
for the four fixed motion settings at .01. It does not move candidate centers,
certify object identity, train a model or select a preferred setting.

The selector streams one complete frame audit at a time. Lossless gzip shards
retain every admissible edge, cost, endpoint competitor and best path. Compact
observations retain original candidate indices, confidence-filter decisions,
winners, margins and links to those complete traces. Serialization is decoded
and checked inside the supervised unit before successful completion is recorded.

There are 24 new selection units and 120 new localization reports. Loaders
reuse the 126 original controls and 630 reports after byte/content/provenance
verification. They never call an old selector or evaluator. The 48 .20/.35
comparisons remain structural-equivalence references with original cap20
headers and execution commits. Each pool contains 125 distinct aggregate
cells and 40 additional aggregate references, without counting references
as new trials.

Reports distinguish confidence loss, cap loss and final choice using ordered
partitions. Gained and lost matches, hidden alarms, candidate burden, original
indices and newly admitted current/history candidates remain explicit.
MATCH/UNMATCHED is localization evidence, never a semantic training label.
Hidden geometry stays null and uncertainty does not enlarge a matching radius.

The review code requires completed scores and uses only bound saved PNGs.
It produces six new .01 clips with the approved paired layout, native views,
source-scale closeups and final-frame checks. Synthetic rendering tests are
software validation, not Ryan's review of actual ball-tracking results.
The prior twelve YOLO approvals and prior .20/.35 reviews remain complete.

## Validation evidence

All 78 distinct focused tests pass. They include independent exhaustive path
enumeration, exact legacy-cap parity, old-path feasibility, original indices
beyond twenty, causal history, equivalence records, hidden nulls, uncertainty,
saved-report reuse, immutable resume, resource aborts and complete rendering.
The full regression suite passed: 598 tests ran, with 597 passes and one
existing Windows directory-symlink capability skip, in 1,638.766 seconds.
All 134 production/test/requirements files retained their exact hashes before
and after the suite. Bytecode writing was disabled.

Both final stress fixtures use fabricated candidates: 400 per frame, for 25
frames. All full trace shards were written, decoded and checked. These costs
are separately recorded synthetic validation, outside the real-run budget.

| Final synthetic fixture | Elapsed worker time | Peak tree memory | New root bytes at final sample | Serialized admissible edges |
| --- | ---: | ---: | ---: | ---: |
| Dense | 491.578 s | 1,280,413,696 | 118,447,870 | 31,840,000 |
| Sparse | 10.266 s | 74,559,488 | 3,439,756 | 112,280 |

Maximum measured monitor intervals were .328 and .266 seconds. Neither run
crossed its time, memory or output limit. Conservative final-accounting byte
bounds include additional receipt space. Earlier benchmark snapshots remain
preserved; final results include the Windows portable-receipt-path fix and
verify unchanged implementation bytes during execution. Synthetic fit is not
a claim that the complete real comparison will fit its cumulative budget.

An independent preservation audit verified 755 unique files, including all
312 proposal-bound non-video files, the original diagnostic bindings, all 126
saved controls, 150 source PNG bindings, and the 134-file implementation/test
inventory. Source video contents and sealed holdouts were not opened. The
actual runner also rejected the dirty checkout before worker dispatch.

The executable manifest now binds `implementation_validation.json` beneath
`data/outputs/ball_tracking/crop_candidate_retention_implementation/9fe6a1ef86d2_2026-10-02/`.
Its SHA-256 is
`135bb50a461eec662f70ed4c64d15fe15e36826eefe81ee21e7521f36578890f`.
It binds exact source files, the full-suite log, both final benchmarks and their
independent audits. All 755 preservation bindings were reverified after the
full suite. The manifest SHA-256 is
`f2b8834722ddf9f1ce4dcfdf1441a12cc0d52591b57bb66ca726c3aef2ca15ff`.

## Execution and recovery

The executable manifest is
`configs/ball_tracking/crop_retention_experiments/rfdetr_medium_crop_candidate_retention_v0_1.json`.
Real stages reject a dirty checkout, a nonempty index, a different branch,
an uncommitted implementation, missing validation or changed bound inputs.
The validation certificate covers all production/test Python files and
`requirements.txt`; modifying a dependency requires new validation.

Selection reads candidate records and source metadata. It does not open
annotation or pixel files. Scoring and rendering enable their own bound inputs
later. No source video is decoded and no model inference is called.

One supervisor owns a single worker process tree. On Windows a Job Object
tracks descendants and terminates the tree on abort or supervisor exit.
Memory, total new bytes, free disk and active time are monitored. Actual
sample intervals are recorded; an interval over one second fails closed.
Two stable file inventories prevent atomic directory publication from hiding
output bytes. A small conservative reserve covers final accounting receipts.

The limits remain 8 GiB combined worker resident memory, 32 GiB total new
outputs, 10 GiB minimum free disk, 30 minutes per window/scorer selection unit
and four cumulative active hours across real stages and retries. Temporary
files, partial shards, logs and playback files stay under the new output root.
No resource limit changes the path rule or acts as a tracking-quality gate.

An append-only resource journal and completion seals retain consumed budgets.
A completed unit is reused only after its successful receipt and bound files
verify. Failed attempts consume their measured time; an interrupted supervisor
without a closing receipt conservatively consumes the entire reservation.
Missing or truncated history cannot silently reset a budget. Completed outputs
are immutable; partial evidence remains visible and counts toward the byte cap.

A published output without a successful completion receipt stops preflight
for investigation. It is not silently blessed, replaced, or treated as a
completed unit. A resource or design change requires a revised scope.

## Reviewable scope and next boundary

The five new modules cover selection, experiment/provenance orchestration,
resource supervision, scoring and review. Five corresponding test files use
fabricated data. Approval and executable-manifest files are separate from the
frozen proposal. This implementation note and current context records explain
the new checkpoint; older diagnostic and reviewed evidence remain unchanged.

The proposed staging scope is exactly these 24 files, including the prior
completed diagnostic preparation that is still unstaged:

```text
configs/ball_tracking/crop_retention_experiments/rfdetr_medium_crop_candidate_retention_v0_1.json
configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_retention_v0_1.json
configs/ball_tracking/proposals/saved_candidate_retention_localization_diagnostic_v0_1.json
configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_approval_v0_1.json
configs/ball_tracking/reviews/saved_candidate_retention_localization_approval_v0_1.json
docs/ball_candidate_retention_localization_proposal.md
docs/ball_candidate_retention_localization_results.md
docs/ball_crop_candidate_retention_implementation.md
docs/ball_crop_candidate_retention_proposal.md
docs/context/current_state.md
docs/context/roadmap.md
docs/context/validation_history.md
src/ball_tracking/candidate_retention_diagnostic.py
src/ball_tracking/crop_retention.py
src/ball_tracking/crop_retention_evaluation.py
src/ball_tracking/crop_retention_experiment.py
src/ball_tracking/crop_retention_resources.py
src/ball_tracking/crop_retention_review.py
tests/test_ball_candidate_retention_diagnostic.py
tests/test_ball_crop_retention.py
tests/test_ball_crop_retention_evaluation.py
tests/test_ball_crop_retention_experiment.py
tests/test_ball_crop_retention_resources.py
tests/test_ball_crop_retention_review.py
```

Generated data, test logs, resource journals and media remain ignored and
outside this scope. The final checkpoint receipt records exact working-file
hashes and the empty index for a later staging decision.

No Git step is authorized by the experiment approval. Staging, committing,
pushing, PR creation and merging remain separate decisions. The approved plan
requires a clean tested commit before the real experiment can run. After that
checkpoint exists, selection, scoring and rendering can proceed within the
already approved scope; experiment approval does not need to be requested again.

All nine original prediction embargoes and three sealed holdouts remain in
force. No method, operating point or quality gate has been chosen. Player
identity/calibration decisions and downstream defensive-scoring work are
unchanged; no upstream `--rerun-from` stage is needed.
