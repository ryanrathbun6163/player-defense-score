# Saved error-breakdown scanner diagnosis proposal

Status: prepared for Ryan's review. Ryan authorized inspection of the saved
benchmark evidence and preparation of a revised proposal with "yes you may".
That response does not authorize the profiling call proposed here, another
scanner implementation, real recovery, or Git mutations.

## Recommended next step

Authorize one bounded, synthetic-only profile of the unchanged failed scanner.
A profiler records which functions ran and how much time they consumed. This
addresses the missing evidence before choosing another implementation. Stop
after reporting that observation, even if the call happens to return a total.
The previous static and dynamic readiness requirements remain outstanding.

This is a narrower investigation stage in the recovery plan. It cannot unlock
the scientific worker. A subsequent concrete scanner design would need its
own approval, correctness and performance validation, and separately authorized
clean commit before real recovery. The original scientific question and eighteen
completed clip reviews do not need approval again.

## Observed result and its limits

The current branch is `codex/ball-detector-baseline`, HEAD
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`. The index is empty. The seven
preexisting recovery changes remain intentionally unstaged and preserved.

Let `N` mean
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_recovery_implementation/fa730bcb6d2e_2026-10-04/`.
The approved first candidate changed only the per-file metadata expression from
`(Path(folder) / name).stat()` to `os.stat(os.path.join(folder, name))`.
Its 20 focused tests passed with zero skips. The result recorder initially
misread Windows CRLF line endings; Ryan authorized a separate reconciliation
of the preserved log. That reconciliation passed 13 parser checks and accepted
the exact existing 20-pass result without rerunning the tests. The original
failed recorder receipt remains intact.

The static benchmark then ran once on 12,000 fabricated files in 400 directories,
including the root, with seed 0 and a recorded total of 12,259,360 bytes.
The first accounting call raised
`ResourceLimitError: Output tree did not stabilize for complete byte accounting`.
Its wrapper recorded `0.4908125000074506` seconds and `returned_bytes: null`.
The required readiness threshold was less than 0.40 seconds for every one of
30 consecutive calls. There was one attempted call, no warmup and no discarded
result. The remaining calls, dynamic gate and real recovery did not run.

The scanner deadline uses `time.monotonic()`; the wrapper measured duration
using `time.perf_counter()`. No internal clock readings or clock metadata were
captured. Preserve the exception and measured duration as separate observations;
neither their discrepancy nor the slow operation is established by this record.
No completed-scan count was saved. The result does not establish actual tree
instability, a byte-cap overshoot, an optimization speedup, or performance on
the smaller real experiment tree.

| Preserved evidence | SHA-256 |
| --- | --- |
| `N/static_receipt.json` | `f7f12382fa600f1e05d9aaf160e7aec2e064492865d30fce23c035afe4e9e3f2` |
| `N/static_started.json` | `96671c95d7458db2961f72d9f52a27120a9928c61058418d860ee4472f41ea99` |
| `N/fixture_layout.json` | `fb94a584c117de5af01811676d2b8cf1382e950f2de8e917cae6bafa514d8e30` |
| `N/fixture_reference_before_static.json` | `d4dfccaf78670675f3192afb8eca27693972446db24365e6d12295f237cd9786` |
| `N/scanner_focused_reconciliation.json` | `8da31e6c99e29a0512dc7f0d1bc5e742236014e751612ba9383a654b0385af99` |
| `N/scanner_static_parity.json` | `61d2e70e49de526d08e3cf1f10d96380d509e8a88d0460d071a28270d157731d` |
| `N/benchmark_scan.py` | `33ed25a7e5d8dd2ee491f2a402c7c8abd957c2d20c39fda485f8a5be2ed1d7ac` |

Independent read-only review verified all nine source/helper/authority/prerequisite/
layout bindings in the failed receipt. Preparation also verified all original
151 source/test/dependency bindings, three original helpers, exact metadata for
5,774 real files and 189 directories, and the complete failed synthetic fixture.
No scientific file body was read or hashed and no scanner was invoked.

The preparation record is
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_scan_diagnosis_proposal/fa730bcb6d2e_2026-10-04/preparation_before.json`,
SHA-256 `e7b8e01b920c25dea4ed3ff7d671aad82f8e46ac1c223e93d5436af57c518ba3`.
It binds before-context copies, all seven existing dirty files, and preserved
benchmark evidence. These are metadata checks, not a fresh scientific audit.

## Why another scanner is not selected now

Microsoft documents that NTFS directory-entry sizes may remain stale while a
writer is open, and that size changes can appear only at the hard link used
for writing. Two directory listings could repeat an understated size. Therefore
a batched directory-size query has not established equivalence to the required
fresh per-file queries. It is excluded from this proposal.
[Open-writer sizes](https://devblogs.microsoft.com/oldnewthing/20111226-00/?p=8813/),
[hard-link metadata](https://learn.microsoft.com/en-us/windows/win32/fileio/hard-links-and-junctions).

A compiled fresh-query loop might reduce Python overhead but adds compiler and
binary provenance requirements. Parallel queries add cancellation, cleanup and
monitor-load concerns. Neither has a measured benefit here. This proposal
selects neither, and does not authorize cached sizes, path-only identity,
background scanning, a larger deadline, a smaller stress fixture, or a relaxed
readiness threshold.

## Exact proposed synthetic investigation

After separate approval, create a new ignored, reviewed diagnostic helper and
its focused artificial tests. Do not alter any existing runtime module, test,
authority, certificate, benchmark helper, failed receipt, or fixture.

1. Bind this proposal and a new approval record. Verify the exact current
   scanner, original resource module, focused-test source, prior approval,
   failed receipt and reconciliation/parity records. The scanner SHA-256 is
   `fe0806db8d9958400a13bde0ce2c861b06ea7c96a4102081cb13aec447135a3a`;
   the unchanged resource module SHA-256 is
   `37d3888c50d81128defb92029480fbde02a9408554ea4cdc076d700296b833fe`.
   Refuse any previous diagnostic marker, reservation, result or partial output.
2. Use the existing fabricated tree
   `data/outputs/t/ebsr_fa730bcb6d2e` as read-only input. Verify exact path,
   directory membership, file size, mtime, device and inode against its bound
   before-static reference immediately before and after the call. Reject
   indirection, changed metadata or an unknown path. Do not recreate, clean,
   warm up, grow or rewrite this tree. Ordinary metadata verification is outside
   the profiled call and is not an unrecorded accounting benchmark.
3. Under the explicit repository `.venv\Scripts\python.exe -B`, with
   `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUTF8=1`, invoke the unchanged recovery
   scanner exactly once. Enable `cProfile.Profile(timer=time.perf_counter,
   subcalls=True, builtins=True)` immediately around that call and disable it
   in `finally`. Keep all original deadline checks and the 0.5-second allowance.
   Do not substitute a clock, mock filesystem, modified function or fallback.
4. Capture the returned integer, or the exact exception class and message.
   Capture external monotonic and performance-counter readings bracketing the
   call, `time.get_clock_info()` for both clocks, interpreter/version/platform,
   source/approval/helper hashes, and profile statistics. Report primitive/total
   call counts, self time and cumulative time by complete function identity
   (source path, line and name), retaining distinct built-in functions. These
   timings overlap when cumulative; do not add them as independent phases.
   Identify available traversal, stat, path-join, deadline and aggregation
   observations. Do not infer completed inventories from function-call counts.
5. The known accounting-deadline exception is an explicitly anticipated
   diagnostic observation. Save it as `captured_known_deadline`, with
   `readiness_passed: false`, and stop after preservation/finalization checks.
   A correct returned total is `captured_return`, also with
   `readiness_passed: false`. Reject a wrong total, any other exception,
   profiler/transport failure, changed inputs or an incomplete record. Preserve
   partial evidence and stop; no repair, retry or alternative call follows.
6. Report the observation and its limits to Ryan. Even if the call returns
   quickly, do not resume the old 30-call benchmark, run its dynamic phase,
   select a replacement scanner, or dispatch the scientific worker.

Python describes profiling as a way to inspect calls and time, and explicitly
distinguishes it from benchmarking because instrumentation changes timings.
The profile may be truncated by the deadline and cannot identify the original
real-run cause or certify unprofiled speed. It can also be inconclusive. Do not
calibrate or subtract overhead, extrapolate a full scan, or schedule another
profile automatically. [Python profiling documentation](https://docs.python.org/3.11/library/profile.html).

## Bounded execution and records

Proposed new approval path:
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_scan_diagnosis_approval_v0_1.json`.
Proposed ignored implementation/evidence directory:
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_scan_diagnosis_implementation/fa730bcb6d2e_2026-10-04/`.
Use the fixed short path `data/outputs/t/ebsd_fa730bcb6d2e` as the synthetic
supervisor output root. It contains no scientific inputs and does not replace
the real root. The short path accommodates the unchanged journal writer's
long temporary filenames on Windows; check every planned absolute path is at
most 240 characters before dispatch. Do not change system path-length settings.

Use the unchanged `run_supervised` and original scanner to monitor that small
synthetic output root; install no adapter. Its scans of the new root are supervision
overhead, distinct from the single profiled call on the 12,000-file fixture.
Use exactly one owned worker process tree, the existing 8 GiB combined resident
memory cap, 10 GiB free-disk minimum, 0.25-second polling and one-second maximum
monitor interval. Give this separately recorded synthetic unit a 30-second
active budget and cumulative cap, and a 16 MiB output cap. Keep failure,
process-tree termination and final-accounting behavior unchanged. No new
dependency, installation, elevation or network access is needed during execution.

All runtime temporaries, logs, profile/result output and resource receipts
belong inside this new short output root. Before dispatch, require that root to be
absent; create it once. A known scanner-deadline observation can coexist with a
successfully captured diagnostic record, but does not convert either prior
failure or the scanner readiness status to success. The unit name must make
its synthetic diagnostic role explicit. A timeout or interrupted reservation
does not permit another attempt.

Save profile statistics as create-only JSON, at most 512 function records and
256 KiB; refuse oversize output instead of dropping records. Save a bounded
result receipt (64 KiB) and a plain-language summary (16 KiB). Do not use a
profile dump API that overwrites an existing file. The full entry metadata
reference remains the separately bound existing fixture record; do not insert
12,000 file rows into the small returned receipt. The parent may read these
synthetic-only outputs after normal supervisor/result verification.

Validate the new helper with small fabricated/injected cases for exactly-one
dispatch, return/deadline classification, unexpected failure, source/approval/
fixture drift, duplicate attempts, output bounds and incomplete publication.
Use independent source review before the single profile. These are new helper
checks, not repeats of the completed 20 tests or earlier full suite. No tracked
runtime code changes are proposed at this stage, so do not spend a full-suite
run to validate documentation or the profiling observation. Any later runtime
implementation still requires focused tests, independent review and the full
suite, plus the unchanged 30 static and 30-second dynamic readiness gates.

## Preserved real-experiment boundary

The unchanged real root remains
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1`.
The original failure `4adfb390f1f74a1baaec7fb178092218` remains failed. Its
3,010-event prefix, 58 closed attempts, four failures and zero open attempts
are not extended by this proposal or the proposed synthetic diagnosis.
The last verified real cumulative balance is `11132.492000000013` seconds;
the shared original-and-recovery diagnostic balance is `292.73500000001513`
seconds. Neither is renewed or consumed by separately recorded synthetic work.
The same whole-root, memory, disk and monitoring limits continue to apply to
any future real recovery.

No parent scientific-body reading/hashing, new scoring, inference, selection,
training, rendering, label changes or holdout release is authorized. Preserve
all nine original embargoes and three sealed holdouts. All six retention and
twelve earlier YOLO final-frame reviews remain complete. The approved future
scientific result remains the same 48 copied .01/10px rows with pools separate;
it has not been produced. Decisions and quality-gate selection remain null.

## Preparation scope and next approval

Today's edits are this new proposal plus updates to `docs/context/current_state.md`,
`docs/context/roadmap.md` and `docs/context/validation_history.md`. Keep all seven
preexisting changes, bringing the intended total to eight unstaged files.
Preparation evidence and before-context copies stay ignored. Check exact scope,
preserved source/evidence bindings, local links and whitespace; obtain independent
proposal review. No tests, benchmark, profile or real worker run in preparation.

The next requested approval covers implementing/validating the narrowly scoped
ignored helper and performing its one synthetic profile. It does not cover a
new scanner, timing-gate retry, real recovery, staging or committing. If approved,
freeze this proposal and record the approval separately; preserve the older
proposal and approval as the history of the candidate that failed. No manual
command is pending. Stop on any new failure.
