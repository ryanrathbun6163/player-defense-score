# Prefix scanner: bounded static timing request

Status: prepared for Ryan's review. "Move forward" authorized this request's
preparation. No timing helper, benchmark, new budget or Git mutation is authorized
by preparation. The next requested approval covers the implementation, new helper
checks and one conditional static run described below.

## Decision and current evidence

Run the static gate first. It is the prerequisite for the more involved dynamic
gate, so do not build or run the dynamic harness unless this candidate passes.
This preserves both original readiness requirements and limits unused work.

The amended scanner prepares `os.path.join(folder, "_")[:-1]` once per directory
and retains fresh ordinary stat calls, two complete inventories and every original
deadline check. Independent reviews and its first 26 focused tests passed, with
zero failures, errors or skips. Structural comparison passed. Speed remains
unproved; the candidate is not installed in the ordinary supervisor.

Current branch is `codex/ball-detector-baseline`, HEAD
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`, with an empty index and fourteen
intentional dirty files before this request. A dirty checkout is permitted for
this synthetic gate only when its exact intended scope and bytes are frozen.
Real recovery still requires separately authorized staging and a validated clean
commit. Do not infer any Git permission from this request.

| Bound prerequisite | SHA-256 |
| --- | --- |
| `src/ball_tracking/crop_retention_scan_prefix.py` | `e3f137e115d997e3c4148ec841ea607417138603d615469fb4c3439bd82fbe62` |
| `tests/test_ball_crop_retention_scan_prefix.py` | `94f7f1a22491b6999aa2bed83245ead8bae4f34e51a73cc71284475fe43047a2` |
| Focused `validation.json` under `data/outputs/t/ebsx_impl_fa730bcb6d2e/` | `416983627262eb332f74af528ad996aed93029ce81bc3f85b3c23d260f56cd73` |
| Completion checkpoint in that directory | `fdbedfc4cb1126c7206d2208a6bb9b2e62f6913e9123b493ce44c51a626d6384` |
| `src/ball_tracking/crop_retention_resources.py` | `37d3888c50d81128defb92029480fbde02a9408554ea4cdc076d700296b833fe` |

The approved [candidate proposal](ball_crop_candidate_retention_scan_prefix_proposal.md)
and its separate UNC amendment retain their historical roles. The frozen proposal's
empty-prefix expression is superseded only by that recorded amendment; do not
rewrite the original proposal or approval to conceal the blocked version.

## Fixed input and separate result root

Use the existing fabricated tree `data/outputs/t/ebsr_fa730bcb6d2e` read-only:
12,000 files, 400 directories including the root, seed 0, and a reference total
of **12,259,360 bytes**. Do not recreate, grow, warm up, rename or clean this tree.
It remains evidence of the earlier failed candidate and successful profile.

Its frozen records are under
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_recovery_implementation/fa730bcb6d2e_2026-10-04/`:

- `fixture_layout.json`, SHA-256
  `fb94a584c117de5af01811676d2b8cf1382e950f2de8e917cae6bafa514d8e30`;
- `fixture_reference_before_static.json`, SHA-256
  `d4dfccaf78670675f3192afb8eca27693972446db24365e6d12295f237cd9786`.

Before and after candidate calls, compare complete directory/file membership and
file size, mtime, device and inode against that reference, rejecting indirection
and unexpected paths. Use ordinary metadata queries, without reading file bodies.
These preservation checks are not candidate calls or discarded warmups. They
can affect filesystem caches, so do not describe the gate as a cold-cache test.
Retain the existing full reference; record equality results and its binding rather
than making unnecessary copies of its 12,000 rows.

The new supervisor result root is
`data/outputs/t/ebxt_static_fa730bcb6d2e`. Require it absent before dispatch and
create it once. The unchanged original supervisor and original accounting scanner
monitor this small root. The owned worker calls the candidate on the separate,
read-only fixture. No scanner adapter or supervisor monkeypatch is needed here.
The output cap covers new runtime outputs; it does not reclassify the existing
fabricated input as a newly created output.

## Proposed new allocation

| Limit | Static unit |
| --- | --- |
| Recorded unit and cumulative active time | **30 seconds**, one attempt only |
| New supervised output root | **16 MiB** (16,777,216 bytes) |
| Combined resident memory of owned worker tree | **8 GiB** |
| Minimum free disk | **10 GiB** |
| Polling / live maximum monitor interval | 0.25 seconds / 1.0 second |
| Candidate accounting deadline | Unchanged 0.5 seconds per whole call |
| Static readiness threshold | Every call strictly below 0.40 seconds |

This is an explicitly proposed **new synthetic allocation**, not a renewal of
the completed profiling allowance. That allowance retains
`26.560999999998785` seconds and no unused execution authorization. Neither it
nor the real journal is charged, reset or amended by this proposed static unit.
Record this new unit's successful or failed time in its own append-only journal;
an unclosed reservation remains charged. One attempted unit consumes its one-run
authorization even if unused time remains. No resume, alternate root or retry.

The 30-second allocation uses the original supervisor's recorded active interval:
worker startup, ownership checks, source/fixture verification inside the worker,
all candidate calls, worker-result publication and shutdown through its elapsed
capture. In the frozen supervisor, the final accounting scan and finished-event/
seal publication follow that capture. They remain mandatory success checks, but
this allocation is not a hard 30-second ceiling on total command wall time.
Report both the journal's charged time and total command wall time; do not rewrite
the historical charging rule. The allocation is not a completion estimate.
Parent source/authority preflight and new helper unit tests are separate
preparation work, not hidden candidate calls. Keep the unchanged supervisor's
failure, process-tree termination and final-accounting behavior.

All runtime logs, temporary files, call records, worker result and summary belong
inside the new result root. Refuse any planned absolute path above 240 characters,
including atomic journal filenames; the checked reservation-temporary example is
184 characters. Do not change system path settings, dependencies or interpreter.

## Exactly one static execution

1. Bind this request and its explicit approval; the exact candidate, 26-pass
   evidence and amendment; frozen fixture records; original supervisor; ownership
   helper; new harness/tests and their review/validation. Require the frozen
   branch, HEAD, empty index and exact intended worktree bytes. Reject existing
   run markers, output root, reservation, result or incomplete prior output.
2. Use `.venv\Scripts\python.exe -B`, `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUTF8=1`.
   Start one owned worker tree through unchanged `run_supervised`, unit
   `synthetic-scan-prefix-readiness:static:`. Reuse the already-validated ownership
   protocol that accounts for the `.venv` launcher intermediary. Do not assume the
   worker is the supervisor's immediate child or add a startup diagnostic run.
3. After ownership/gate/reservation checks, verify the frozen fixture metadata.
   Invoke the exact candidate **30 consecutive times**, with no discarded
   warmup, profiler, deliberate inter-call sleep or extra candidate verification
   call. Ordinary result recording and checks between calls remain included in
   the active worker time.
4. Measure each invocation with `time.perf_counter()` immediately around the
   unchanged function; leave its internal monotonic deadline intact. Require a
   non-boolean integer equal to 12,259,360 and a finite, nonnegative duration below
   0.40 seconds.
   Save every attempted call's index, duration, returned value or exception.
5. Stop candidate dispatch at the first exception, wrong total or missed threshold.
   The previously observed deadline exception is a **failed timing gate** here,
   unlike the earlier profiling observation. No remaining calls run after a
   failure; do not tune the code, fixture, thresholds or allowance automatically.
6. After 30 passes, verify the full fixture metadata again and publish the
   bounded result and summary. On failure, preserve available attempt evidence
   and perform only required shutdown/preservation bookkeeping. Never invoke the
   candidate again for cleanup or report a partial series as a pass. The unchanged
   supervisor's scans during cleanup concern only the small result root.
7. Accept only successful worker and supervisor completion, exact result binding,
   sealed complete journal, absent supervisor lock, no resource overshoot/final
   accounting error, and unchanged source/authority/fixture bindings. Report all
   30 timings and their maximum. Set `static_gate_passed: true` only then, while
   overall performance readiness remains false until the other gates pass.

Preserve call progress in a create-only append log, flushing each start/completion
record outside the measured invocation. Limit it to 64 KiB, the worker result to
64 KiB and the summary to 16 KiB; refuse overflow instead of dropping records.
A timeout may leave an incomplete call-start record. Report it as incomplete,
without inventing a returned total or completed duration. Publish results before
worker exit so the unchanged supervisor accounts for them normally. The parent
may read these synthetic-only records after receipt verification.

## Implementation and validation covered by the requested approval

Create only new ignored harness/test/validation files under
`data/outputs/t/ebxt_src_fa730bcb6d2e`. Add the separate tracked approval at
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_scan_prefix_static_timing_approval_v0_1.json`.
Keep existing runtime modules, tests, approvals, certificates and failed evidence
unchanged. No dynamic harness or fixture is part of this stage.

Reuse the frozen helper `data/outputs/t/ebso_src_fa730bcb6d2e/ownership.py`, SHA-256
`e87fc800656d3e6535c9a8c4dbe3694607d352f048bbfc80d1a522b377dff35b`, with its existing
validation/integration receipts. Reuse only explicitly reviewed utility functions
if useful; never call an old benchmark/profiler entry point. Do not alter those
sources to fit the new stage.

Independently review all new harness code before execution. New artificial helper
checks must verify exactly-30 dispatch, first-failure stop, strict timing/total
validation, complete call recording, approval/source/fixture drift rejection,
ownership binding, create-only publication, output bounds and refusal of a prior
attempt. Mock candidate calls and supervision for these checks; use only small
fabricated metadata cases. Do not run the real candidate on the stress fixture
as a helper test. Capture unittest counts structurally and bind final source bytes.

Do not repeat the completed 26 candidate tests, prior helper suites, startup
observations, profiler or historical full suite. If new helper review/checks
pass, the requested approval permits the one static execution above without an
additional routine confirmation. Any new failure stops; no automatic repair or
retry. This is not approval of full regression or real recovery.

## What remains after this gate

The [original recovery proposal](ball_crop_candidate_retention_error_breakdown_recovery_proposal.md)
still requires a supervised 30-second growth workload: 30 one-second ticks,
4 KiB appended to each of 64 fixed files per tick, plus one new 512-byte file.
Each accounting call must be below 0.40 seconds and the dynamic maximum monitor
interval below 0.90 seconds. Successful static supervision cannot satisfy that
dynamic monitor gate.

That workload adds 7,879,680 bytes, taking the fabricated payload from 12,259,360
to 20,139,040 bytes before control files. A later dynamic request must therefore
specify its own sufficient time/output allocation and a new fabricated destination
with the identical starting layout. It must count that fixture inside its
supervised root and measure the candidate there through a narrowly owned adapter.
The original fixture remains unchanged. No dynamic budget is requested now.

Full regression and remaining recovery integration/validation still follow before
real recovery. The saved real balances remain `292.73500000001513` diagnostic
seconds and `11132.492000000013` cumulative seconds. No scientific body or real
output root is read, hashed or traversed during this preparation. Preserve all
nine embargoes, three sealed holdouts, six retention reviews and twelve YOLO
final-frame reviews. The real saved error breakdown remains pending.

Preparation adds this request and updates the three existing context documents,
bringing the current intended dirty scope to fifteen files with an empty index.
Bindings and before-context copies are under
`data/outputs/t/ebxt_plan_fa730bcb6d2e/`. Check exact scope, preserved bytes, local
links, whitespace and independent request review. No test or experiment runs
during preparation, and no manual command is pending.
