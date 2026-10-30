# Saved error-breakdown recovery proposal

Status: concrete draft for Ryan's review. Ryan authorized preparation with
"move forward with the recovery proposal". This does not authorize recovery
implementation, benchmarks, a real retry, or any Git mutation.

## Purpose and proposed decision

Finish the already-approved saved error breakdown after its resource monitor
stopped execution. The proposed correction removes repeated Python path-object
construction from directory accounting. It keeps the measurement algorithm,
half-second deadline, monitoring cadence, scientific question and resource caps.
Its performance benefit is unproved. Fabricated-data correctness and timing
gates must pass before one explicitly authorized recovery attempt can run.

Approval would cover this exact implementation and conditional execution scope,
after new validation and a separately authorized clean commit. If the timing
candidate is insufficient, stop and propose a different design. Approval would
not permit a larger deadline, a different scanner, an automatic retry, or a
reset of the original allowance.

## Verified interruption

The eleven tested implementation files were separately staged and committed at
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1` on
`codex/ball-detector-baseline`, parent
`e71a4d2165623208d624c4839e9321bd9bf779ba`. The exact committed bytes and clean
checkout were verified before the approved public runner was invoked once.
Nothing was pushed.

Let `R` mean the unchanged real experiment root:
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1`.
Let `E` mean the implementation evidence directory:
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_implementation/e71a4d216562_2026-10-02`.
All abbreviated paths below are repository-relative.

| Item | Verified value |
| --- | --- |
| Failed unit | `post-review-error-breakdown:summary:` |
| Failed attempt | `4adfb390f1f74a1baaec7fb178092218` |
| Error | `ResourceLimitError: Output tree did not stabilize for complete byte accounting` |
| Public command outcome | Exit 1; empty stdout; 41.266 seconds command wall time |
| Charged attempt time | `7.264999999984866` active seconds |
| Worker evidence | Empty log; no worker result file; no diagnostic output directory |
| Recorded peak worker memory | 57,663,488 bytes |
| Recorded maximum whole-root bytes | 7,413,894,332 bytes |
| Final accounting | Succeeded; conservative bound 7,413,910,716 bytes |
| Journal | 3,010 events; 58 closed attempts; 54 successes; four failures; no open attempt |

No time, memory or output-byte overshoot is recorded. These observations do not
certify unobserved instants. The supervisor lock is absent. Neither an empty log
nor absent outputs proves which internal worker step ran or whether it reached
a scientific input. No successful summary was returned. No repair or retry ran.

| Metadata authority | SHA-256 |
| --- | --- |
| `E/execution_fa730bcb6d2e_receipt.json` | `b8c6c80011680d2598b7ecc4a9cd80eebd2892d7bdd6b6c76866e15508208718` |
| `R/resource_events/00003009.json` (raw file bytes) | `dbea689345092c2337d8ec4e8beb3cec90426277a6d18983cccad8b2ff4b8661` |
| Final event's canonical chain digest | `e5f2a832dd961d2615daa30ca77b039ad8dbe68bcbcfa12c2437128fbc83a3b3` |
| Failed attempt reservation seal | `4ef1c86e86bff35e074ee4b186e62f78a92598405d1b8b6aad6e95e6c5cdcde1` |
| Failed attempt completion seal | `2d17d720843867e70f22bc1eaed40b9f62e9ccace612f1a710316ff21eebff45` |

The two seals are `R/attempts/<failed-attempt>.reservation.json` and
`.completion.json`. Preserve them, the empty `.log` and `.start`, the `.temp`
directory, all eight new journal events, and all three earlier failed attempts.
Do not reinterpret a successful final measurement as successful execution.

## What is known about the monitor

`src/ball_tracking/crop_retention_resources.py:41` gives each `output_bytes()`
invocation one 0.5-second deadline covering every traversal, metadata lookup,
restart, comparison and final acceptance. It needs two complete inventories.
A slow scan can exhaust that deadline even when the tree is static. Vanished
paths or reduced identity/link membership can require additional scans. Ordinary
file growth and membership additions are already permitted by the current rule.

The exact message proves deadline exhaustion, not a full disk or actual tree
instability. The saved records do not identify which scan operation was slow.
The proposed optimization therefore targets avoidable scan overhead without
claiming that path construction is the proven cause of this particular failure.

## Exact scanner candidate and unchanged accounting

Implement a recovery-only scanner whose sole counting-loop optimization is:

```python
# Existing per-file metadata lookup
(Path(folder) / name).stat()
# Proposed recovery-only lookup
os.stat(os.path.join(folder, name))
```

Keep `os.walk` and fresh, ordinary `os.stat` semantics, including existing
follow-symlink behavior. The protected output-tree guard must still reject
unapproved indirection. Do not substitute cached metadata, a pathname-only
identity, native batched enumeration, or Windows `DirEntry.stat()` identities.
Python 3.11 documents that the latter returns zero for `st_dev` and `st_ino`
on Windows; it is not an equivalent shortcut for this identity-based rule.
[Python's DirEntry documentation](https://docs.python.org/3.11/library/os.html#os.DirEntry.stat)

Preserve all of the following:

- One 0.5-second deadline for the entire call, with the existing checks during
  traversal, before/after each metadata lookup, and before accepting a result.
- Each file identity is `(st_dev, st_ino)`. Count every encountered directory
  entry, including hard links; do not charge an inode only once.
- Accept only a pair of complete scans in which every earlier identity remains
  present and its entry multiplicity does not decrease. New identities and
  increased multiplicity remain allowed.
- Charge second-scan multiplicity times the larger observed size across the
  accepted pair, including growing or shrinking files, logs and temporary files.
- A vanished path resets the comparison within the original deadline. Other
  filesystem errors propagate. Incomplete scans, partial totals, old samples,
  skipped subtrees and deletion of evidence cannot produce success.
- Recorded maxima, final-accounting reserve, explicit overshoot fields, and
  the one-second maximum monitoring interval remain unchanged.

This remains conservative accounting for observed sizes, not an instantaneous
upper bound on future writes. Optional bounded diagnostic counters may identify
the number of completed scans, phase and elapsed time on a later failure. Keep
them in memory during a scan and pass them through existing failure/log metadata;
do not write files during traversal or omit their overhead from timing tests.

Preserve the existing resource module and original error-breakdown runner bytes.
Add a separate scanner module and separate recovery runner. During the one owned
supervisor call, the recovery adapter may install only the validated scanner
and recovery journal adapter. Assert the expected original function/class
identities first and restore them in `finally` on every exit. The ordinary runner
retains its current behavior and no-retry guards. Do not use a generic monkeypatch
facility or permit concurrent supervisors.

## Validation gates before any real recovery

Use fabricated files and injected faults only. Preparation of this document
does not execute these gates. A failed required gate stops work; no automatic
tuning of the scanner, test workload or thresholds is allowed.

1. Verify parity with ordinary per-file `os.stat` reference inventories on
   static fabricated trees, preserving identities, multiplicity and byte totals.
   Cover hard links, growth, shrinkage, replacement, disappearing paths,
   directory moves, Unicode/long paths, traversal errors, deadline exhaustion,
   and preservation of all checks. Expected negative fixtures must fail closed.
2. Use a fixed Windows stress tree of **12,000 fabricated files and 400
   directories**, including the root, with nested paths and long filenames.
   This exceeds the currently preserved 5,774 files and 189 directories. Freeze
   seed 0 and record the exact fixture layout and sizes before measurement. Reference totals
   use metadata only; the fixture contains no project evidence or media.
3. Record **30 consecutive optimized accounting calls** on that static tree,
   including the first call with no discarded warmup. Every call must return
   the correct total in **less than 0.40 seconds**. Report all durations and the
   maximum, not only an average. Do not silently repeat a failed benchmark.
4. Run one **30-second supervised fabricated child** on that same starting tree.
   At each of 30 one-second ticks, append 4 KiB to 64 fixed files and create
   one new 512-byte temporary/log-style entry. Do not remove entries in this
   success fixture. Each accepted accounting call
   must stay below 0.40 seconds, the measured maximum monitor interval below
   **0.90 seconds**, and resource/finalization checks must pass. Keep adversarial
   deletion/replacement cases in explicit fail-closed correctness fixtures.
5. Test independent memory, time, byte and free-disk limit failures, process-tree
   termination, final accounting, incomplete publication, stale history,
   changed sources, invalid approvals, unexpected outputs and rejected retries.
   Test the failed-attempt budget deduction and bounded summary transport.

The 0.40/0.90-second readiness gates add measured headroom; they do not extend
the live 0.5/1.0-second limits or guarantee future timing. If the candidate fails,
do not dispatch the scientific worker. Prepare a different concrete proposal.
Real initial accounting must still succeed under the unchanged deadline before
the supervisor releases its worker; any real failure stops without a retry.

Run focused tests, independent source review, then the full suite using
`.venv\Scripts\python.exe -B` and `PYTHONDONTWRITEBYTECODE=1`. Bind the exact new
source/test/dependency bytes and all validation evidence in a new certificate.
Earlier 46 focused passes and 803 full-suite passes plus one Windows skip remain
historical evidence for the unchanged implementation, not validation of new code.
Synthetic validation has separately recorded costs and does not reset or consume
the real journal allowance. No completed real experiment or clip review is rerun.

## New authority, preserved history and budget

Prepare a new versioned manifest and separate approval record only after review:

- `configs/ball_tracking/crop_retention_experiments/rfdetr_medium_crop_candidate_retention_error_breakdown_recovery_v0_1.json`
- `configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_error_breakdown_recovery_approval_v0_1.json`

Proposed source additions are `src/ball_tracking/crop_retention_scan_recovery.py`
and `src/ball_tracking/crop_retention_error_breakdown_recovery.py`, with their
own focused tests. These files do not exist as a result of this proposal.
Do not modify the frozen original proposal, approval, manifest, formatter,
runner, supervisor, existing tests, certificates or earlier evidence.

The new authority must bind the exact original scientific approval and inputs,
the new proposal/approval and validation certificate, and all 3,010 existing
resource events through the failed completion. Record the actual recovery code
commit in a create-only post-commit execution checkpoint/receipt that binds the
committed manifest and certificate. Do not embed a commit's own SHA inside the
tracked manifest being committed. Execution must verify the clean actual HEAD
and exact validated source bytes against that checkpoint before dispatch. Require
58 closed attempts, 54 successes, exactly the four known failures and no open
attempt. Bind all existing result/seal metadata with its actual historical role;
do not follow its scientific-body pointers. Require the failed result file and
both old/new diagnostic output destinations to be absent before dispatch.

Freeze the current file/directory metadata inventory outside `R`; verify it
before and after execution. The preparation inventory at
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_recovery_proposal/fa730bcb6d2e_2026-10-04/preparation_before.json`
has SHA-256 `3da326ad4768f8b3f8e991fb176d27cdbe9474305c8f264acfc1b392bfd0dc9b`.
It contains 5,774 files, 189 directories and the complete raw-event bindings;
all 5,762 original files match their frozen metadata. Scientific preservation
uses path/size/mtime/device/inode metadata, not fresh content hashes.

Only one new unit, `post-review-error-breakdown-recovery:summary:`, may append
to this exact prefix. Reject any previous recovery attempt, unknown suffix,
unreceipted output or active supervisor. Never run the old runner or its dry-run
as a post-failure verification command; both correctly reject this changed prefix.
New validation must distinguish historical source bindings from the current
expanded source inventory rather than edit old certificates to fit new files.

The original 300-second diagnostic allowance is **shared across the failed
original unit and recovery**, not renewed. Calculate the reservation directly
from the original journal:

```text
min(300 - charged_seconds_for_original_and_recovery_roles,
    14400 - all_charged_real_worker_seconds)
```

At this checkpoint the role balance is `292.73500000001513` seconds and the
cumulative balance is `11132.492000000013` seconds; cumulative usage is
`3267.507999999987` seconds. Preserve journal precision and charge all subsequent
failed or successful worker time. Unclosed reservations remain charged under
the existing rule. No extra real preflight/diagnosis worker or allowance is
included; worker-side input loading, hashing, verification and output work all
share the one reservation. Parent checks remain source/authority/receipt metadata
only. These balances are caps, not completion estimates.

Use the same `R`, one worker tree, 8 GiB combined resident memory, 32 GiB
whole-root accounting, 10 GiB minimum free disk, four-hour cumulative allowance,
and unchanged monitoring frequency. Preserve all partial and failed evidence
in place. No new root, moved evidence, budget reset, relaxed limit or result
adoption is permitted. All new recovery files inside `R` count toward its cap.

## Unchanged scientific scope and new output provenance

Only the supervised worker may open/hash the two saved pools and passed audit
listed in the [approved original proposal](ball_crop_candidate_retention_error_breakdown_proposal.md#exact-existing-inputs).
Keep their exact paths, sizes and hashes from the original manifest. Read pools
sequentially. Keep the unchanged pure formatter and every layout, provenance,
frame-range, category-disjointness and saved-total check.

Return exactly 48 copied .01/10px rows: six development windows, four settings
(TT/TW/WT/WW) and both cap20/all policies, with representative and challenge
pools separate. Copy U/F/C/S frame lists, saved missed totals, eligible false
observations, hidden alarms, roles and exact source pointers. New descriptive
arithmetic remains limited to each copied list's own length. No new scoring,
pool totals, rates, unions, rankings, inference, selection, rendering or training.
Object identity versus center placement remains unresolved; decisions remain
null and hidden-ball generalization is not established by one five-frame episode.

Write create-only scientific outputs to the new explicit directory
`R/audit/post_review_error_breakdown_recovery_v0_1/`: `breakdown.json`,
`summary.md` and `provenance.json`. Keep the original destination absent and
preserve the failed attempt as failed. Bind actual recovery code/specification,
the unchanged extraction/formatter source and original scientific provenance;
do not attribute a future successful result to the failed commit or attempt.

The parent may receive only the successfully verified returned summary, at most
65,536 bytes, after successful supervisor completion and result-receipt checks.
Do not reopen/hash those scientific outputs in the parent or expand the reading
scope through metadata links. No old result is adopted. A failure after output
publication preserves that incomplete/unaccepted evidence and stops recovery.

All nine original prediction embargoes and three sealed holdouts remain intact.
All six retention reviews and twelve earlier YOLO final-frame reviews are
complete; none is requested again. Player identity/calibration decisions remain
unchanged. Ball tracking remains the active phase; no tracker or quality gate
is selected by this diagnostic.

## Preparation checks and approval boundary

Today's Git scope is exactly this proposal plus `docs/context/current_state.md`,
`docs/context/roadmap.md` and `docs/context/validation_history.md`. Before-context
copies and metadata-only preparation evidence remain ignored outside `R`.
Check exact scope, local links, whitespace, unchanged source/authority bindings
and preserved evidence metadata. No runtime code change means no test rerun for
this proposal; no real scanner benchmark, scientific read or retry is performed.

Ryan's earlier scientific approval remains valid for its scientific question.
The requested new approval concerns this scanner candidate, the strict failed-
prefix transition, shared remaining budget and one conditional recovery attempt.
The original proposal explicitly required an unchanged supervisor/accounting
path and rejected a prior attempt, so its approval alone does not authorize
this operational amendment. Freeze this proposal after approval and record the
response separately. Implementation/validation may then proceed; staging and
committing each still require separate authorization under `AGENTS.md`.

Only after every gate and the separately authorized clean commit may the one
recovery unit run. Stop on any new failure; no automatic repair or retry. A
successful bounded summary ends this task. Later algorithm work requires its
own concrete scope. There is no execution command pending in this draft.
