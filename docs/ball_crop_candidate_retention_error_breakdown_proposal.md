# Proposed reading of the saved candidate-retention error breakdown

Status: concrete draft for Ryan's approval. Preparation is authorized; this new
scientific reading and its implementation have not been approved or executed.
It grants no staging, committing, pushing, PR or merge permission.

## Question and purpose

When a saved output misses the reviewed reference, was there no nearby saved
candidate, was a nearby candidate removed, or did an available candidate lose
at path selection? Answer this using the completed scoring files' existing
ordered loss categories. Do not run another detector, selector or scorer.

The completed interpretation at `e71a4d2165623208d624c4839e9321bd9bf779ba`
found no additional localization matches at .01 confidence and 10 pixels for
any of the four settings in either development pool when removing the cap.
Some looser radii had gains alongside additional errors. Those findings justify
examining where the remaining misses occur; they do not identify their cause.

Earlier diagnostics already examined selected cases. This proposal does not
repeat their image inspection or calculations. It exposes the existing complete
six-window error breakdown for both cap policies in the completed comparison.
It cannot separate wrong-object identity from inaccurate center placement.

## Exact existing inputs

Let `R` mean the unchanged ignored experiment directory:
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/`.
These are the only scientific bodies the proposed supervised worker may read
and hash. All paths in this table are relative to `R`.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `evaluation/representative_evaluation.json` | 134447507 | `82ce2d01b9f61a5d66b358f5aa42654db2413f7a9d5e45867ddffc9fb1e5acfb` |
| `evaluation/challenge_evaluation.json` | 126628338 | `01afe5ad0391336c5619e93dea585f79a665dccd02d9201c3dbe9349d1e60f60` |
| `audit/independent_publication_recovery_audit.json` | 1770176 | `a1c944c3e1a5184ff08986adacbb2e623d515a67b33a67a55075dcc3f5fc5da2` |

The two pool hashes were copied from the successful scoring result
`R/attempts/98a92bcb9d384f1c9b684d92403c7bc6.result.json`, SHA-256
`a03e3ac99a3cbaad8f0fe48d206f75663fb8fc00a601b60d2cdc7b72163b0873`.
Their sizes came from the frozen preservation metadata. The audit binding came
from the approved interpretation manifest and successful audit receipt
`R/attempts/b5b46e5fac4f442ab960984758cfd469.result.json`, SHA-256
`e45897d7545aa6b2bce15d68af9d8b54077cb32ab88e98bdc67c9103549da87e`.
Preparation did not open or freshly hash any of these scientific bodies.

Window authority remains
`configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_retention_v0_1.json`,
SHA-256 `7640784e2a64e81a2064ebb40cd4d1c77366076e5e78a2c19f8f5fc28e29fe1b`.

| Possession | Representative frames | Challenge frames |
| --- | --- | --- |
| P001 | 50-74 | 200-224 |
| P002 | 250-274 | 25-49 |
| P003 | 300-324 | 150-174 |

The completion authority is
`data/outputs/ball_tracking/crop_candidate_retention_interpretation_implementation/a89cd40838b0_2026-10-02/interpretation_completion_checkpoint.json`,
SHA-256 `c6e55a921c44bd6dfa29b291dd753fb80b72637ecc86ba035802210f5bb80bf5`.
It records 3,002 journal events, 57 completed attempts, 54 successes, the same
three preserved failures and no active worker. The final event digest is
`6c0924cc29f4bdf6b7d6e9311b3fc8205baf8ad0ab251a31ae2bb056a45e1f6c`.
Its successful interpretation result is
`R/attempts/7bd613d71cef48d38c15a72e9647fc10.result.json`, SHA-256
`07d810dcfe98bf2937d2e6bfdfbb1985cdbd05b974c3d974f6919bcb7a19fa62`.

Source, authority, certificate, review and resource/receipt metadata may support
verification. None grants permission to follow a link into another scientific
body. Raw candidates, annotations, observations, path shards, source images,
videos, model files and all sealed holdout contents remain outside this scope.
Loading a pool JSON necessarily parses its embedded fields; interpret only the
specified saved breakdown, identity/provenance fields and integrity checks below.

## Exact extraction and interpretation

Keep representative and challenge pools separate. Copy all four frozen motion
settings (TT, TW, WT, WW), both policies (`cap20`, `all`), and every approved
window at confidence .01 and radius 10 source-image pixels. This is 48 rows of
existing comparisons, not 48 independent trials. No other setting is tested or
selected. The display radius is not a new quality gate.

Use only the existing `loss_decomposition` entries and their saved fields:

| Saved category | Plain-language meaning |
| --- | --- |
| `U_no_candidate_at_export_floor` | No saved candidate center satisfies this radius at the export floor. This is not proof that the ball is absent from the pixels. |
| `F_confidence_filter_loss` | A nearby candidate exists at the floor but is removed by the confidence cutoff. |
| `C_candidate_cap_loss` | A nearby candidate passes confidence filtering but is removed by the candidate cap. |
| `S_path_choice_loss` | A nearby candidate is retained but the final output does not match the reference. This can include missing output; it does not prove a wrong-object emission. |

Copy the four frame-index lists, `total_missed_eligible_frames`,
`false_observations_on_eligible_frames`, `hidden_alarm_frames`, and the original
`selection_execution_role`. The only new descriptive arithmetic allowed is the
length of each copied list for its own window/setting/policy row. Label those
counts as counts of saved memberships, not newly evaluated metrics. Validate
sorted, unique integer indices within window bounds, disjoint loss categories, their reconciliation to the
saved missed total, and separation of eligible misses from hidden alarms.
Contradictory fields stop the unit; do not repair or recompute the underlying
matching. No new pool totals, rates, confidence intervals, rankings, tests or
cross-window/category unions may be reported.

**Window mapping is explicit.** The saved pool writer concatenates each
window's 120 breakdown rows in the same order as its `retention_measurements`
array. Individual breakdown rows do not carry a window ID. Require exactly
three distinct window IDs in that array, matching the authority's windows for
the pool; require 360 breakdown rows. Match each contiguous 120-row block to
the corresponding `retention_measurements[i].window_id`. Do not assume the
caller supplied windows in possession order. Validate each block's full saved
key sequence: four source-defined motion arms, radii 5/10/15/20/30, confidence
.01/.20/.35, then cap20/all, including original execution-role semantics.
Use non-target rows only to validate this layout; extract only .01/10px.

For every copied value, record the exact `/loss_decomposition/<index>/...`
pointer and its `/retention_measurements/<i>/window_id` identity pointer.
Check every copied frame against that window's authority bounds. Verify source
and scoring provenance, published content digests, null decisions, the passed
independent audit and completed receipt bindings. These checks verify the
saved record contract; do not rerun the audit, evaluator or path calculations.

Explain all windows and settings, including unchanged and unfavorable rows.
Do not treat multiple settings' counts as separate evidence or add overlapping
false observations to misses. The five hidden frames from one episode remain
insufficient to establish robust hidden-ball performance. Identity and center
placement remain unresolved, with no semantic labels or training split created.
Missing required fields or ambiguous identity mappings stop execution.

## Execution, preservation and outputs

After approval, implement a separate authority and reader for exactly one unit:
`post-review-error-breakdown:summary:`. Preserve every existing runner, approved
proposal, manifest, certificate, helper and completed output. Freeze the exact
completed 3,002-event prefix from metadata and verify the full receipt chain;
only this one new role may append to it. Reject a prior attempt, partial output,
unknown suffix or active worker. Require the worker's own reservation while
running, not an empty active set. No automatic retry or adoption is permitted.

Use the unchanged supervisor and experiment root. Keep one worker process tree,
8 GiB combined resident memory, the 32 GiB whole-root bound, 10 GiB minimum
free disk, original monitoring cadence and byte-accounting rules. Add a tighter
maximum of 300 active seconds for this non-selection unit within the original
four-hour cumulative budget. The remaining allowance is 11,139.757 seconds
(rounded); use the authoritative full-precision journal value. All loading,
hashing, verification, failures and output work consume the same allowance.
No reset, replacement root, evidence deletion or resource-limit relaxation.
The 300-second cap is not a runtime estimate or a test-suite time estimate.

Read the two large pools sequentially and release each before reading the next.
Hash permitted scientific inputs before and after use inside the supervised
unit. Keep protected-file preservation checks metadata-based outside that input
set; do not claim a fresh content audit of the entire evidence tree. All nine
original prediction embargoes and the three sealed holdouts remain unchanged.

Create only these scientific files under `R/audit/post_review_error_breakdown_v0_1/`:

- `breakdown.json`: the 48 copied rows, per-row membership counts and source pointers;
- `summary.md`: at most 64 KiB, explaining those rows and their limits;
- `provenance.json`: exact source/input/authority bindings and verification basis.

Ordinary supervision metadata, logs and temporary files count against the same
root limit. All outputs are create-only. The external result receipt binds the
three final hashes; successful completion and receipt validation must precede
return of the bounded readable summary to the parent. Permit conversational
explanation of that returned summary, not subsequent parent scientific reads.

## Validation and approval boundary

Approval of this exact proposal would authorize its implementation and bounded
execution after validation and a separately authorized clean commit. Record
approval separately and preserve this draft's bytes. Bind final implementation,
fixtures and evidence hashes in the new authority. Do not repurpose the finished
interpretation's manifest or append a second interpretation attempt.

Use fabricated fixtures to test shuffled window order, empty categories,
duplicate/missing rows, wrong frame ranges, layout/role mismatch, pool mixing,
count fidelity, hidden/eligible separation, changed bindings, forbidden access,
output bounds, partial writes, prefix preservation and failure/no-retry behavior.
Include a supervised synthetic child and receipt-verified bounded return.
Focused tests, independent review, the full suite with bytecode disabled and
`git diff --check` remain required for implementation changes. No test waiver
or full-suite rerun is needed for preparing this documentation alone.

Stop on any new failure. No new inference, scoring, selection, rendering,
training, tuning, tracker choice, operating point, quality gate or holdout
release is authorized. All six retention and twelve YOLO clip reviews remain
complete; no repeat review or new individual identity judgment is requested.

This task ends with the readable error breakdown and explicit unresolved
questions. Any subsequent algorithm experiment needs a concrete new scope.
