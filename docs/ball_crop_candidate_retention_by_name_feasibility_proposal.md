# Fresh Windows metadata feasibility proposal

Status: proposed on 2026-10-05; implementation and execution are not yet approved.

## Decision this would support

Build a small adapter that asks Windows for a file's current identity and logical
size by name. Check its correctness on newly fabricated files, then conditionally
compare its query time with ordinary `os.stat` on the same files. This would tell
us whether a different metadata interface merits a full scanner implementation.
It would not establish scanner readiness or authorize scientific recovery.

The saved profile of the older recovery scanner attributed 291.710 ms of one
487.581 ms instrumented, deadline-truncated call to 16,134 `nt.stat` calls.
The profile did not complete accounting. Its nested timings must not be added
together or extrapolated to a completed scan. The later prefix candidate passed
26 correctness checks, but its first static timing call returned no byte total
and raised the unchanged accounting deadline exception after about 0.485 seconds.
The static harness itself had passed 29 artificial checks. These are different
results: the tests passed; the candidate failed its performance gate.

Those results justify examining the metadata interface. They do not prove the
latest candidate has the same cost distribution or that this alternative is
faster. Another minor loop edit has no strong supporting evidence.

## Specific interface and unresolved compatibility

The candidate is Windows `GetFileInformationByName`, selecting
`FileStatBasicByNameInfo`, called through Python's standard-library `ctypes`.
Microsoft documents a query by filename without returning an opened file handle
to the caller. This is a fresh synchronous query for each path, not cached
directory-entry metadata. Its speed relative to this installed Python is unknown.
See the [official API declaration](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getfileinformationbyname).

The [information-class declaration](https://learn.microsoft.com/en-us/windows/win32/api/minwinbase/ne-minwinbase-file_info_by_name_class)
places `FileStatBasicByNameInfo` at implicit C enum value 3. Use the documented
`Kernel32.dll` export, Windows calling convention, explicit argument/return
types, and thread-local last-error capture. Do not substitute a kernel API,
download a DLL, or silently fall back to a different query.

The [basic information structure](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-file_stat_basic_information)
contains logical end-of-file size, file attributes, a volume serial, and file IDs.
Its declared fields imply this x64 layout: size 104 bytes, alignment 8, file ID
offset 0, end-of-file 48, attributes 56, reparse tag 60, volume serial 80, and
128-bit ID 88. Verify these inferred ABI values before any native call. The
linked [FILE_ID_128 declaration](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-file_id_128)
specifies 16 bytes. The basic-structure page has inconsistent surrounding prose;
do not copy its erroneous byte count or its unrelated directory-offset remarks.

Keep the complete raw volume serial, 64-bit file ID and 16-byte ID in evidence.
Document signed/unsigned interpretations without discarding any bits. Compare
native identities and logical sizes against independent `os.stat` results.
Do not truncate a volume serial, replace IDs, or manufacture numeric equality.
In particular, Python and this API may expose different-width volume identifiers;
numeric compatibility is an open question, not an assumed pass. Any mismatch
must be reported as `identity_contract_review_required` before timing and requires
an explicit identity-contract decision.
Use `EndOfFile`, never allocation size or link count, as logical file size.

Restrict this component to the new local NTFS fixture. Within the owned unit,
reject reparse points in its ancestor chain and entries; establish its volume
and confirm NTFS using the documented
[GetVolumeInformationW filesystem-name output](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumeinformationw).
That API's volume serial is not a replacement identity for the candidate's full
serial. Reject unsupported filesystems, ambiguous identities, unsupported API
exports, and invalid ABI. The saved Windows build and Python version do not
prove API availability or compatibility.

## Proposed approval envelope

Approval would cover the following ordered work as one bounded component task.
It would expressly amend the previous ordinary-`os.stat` interface restriction
only for this isolated feasibility adapter.

1. Create the adapter, artificial tests, validator and supervised feasibility
   harness under new ignored `data/outputs/t/ebbn_src_fa730bcb6d2e/`. Create a
   separate approval record at
   `configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_by_name_feasibility_approval_v0_1.json`.
   Bind this proposal and final helper sources. Review the source independently.
2. Run only new artificial checks for ABI, injected metadata/errors, output
   normalization, deadline coverage, supervision, gates and dispatch. Native
   filesystem queries are mocked at this stage. Ordinary helper defects may be
   corrected and affected checks rerun, with failed evidence preserved and final
   source hashes rebound. Do not rerun old candidate, helper or full suites.
3. If those checks and review pass, use the unchanged original supervisor and
   reviewed ownership protocol to run the new feasibility series. All native
   probes, fixture setup, correctness queries and timing happen in the owned
   worker after the gate and reservation. Parent work is limited to allowlisted
   source, authority and fabricated-result metadata.

The new allocation would be 30 seconds of cumulative supervisor-charged active
time, maximum 30 seconds per attempt subject to the remaining balance, 16 MiB
total output under new `data/outputs/t/ebbn_fa730bcb6d2e/`, 8 GiB for the owned
process tree, and at least 10 GiB free disk. Preserve 0.25-second requested
polling and the 1-second maximum monitor interval. Report external wall time
separately: existing supervisor final accounting and sealing occur after its
active-time measurement, so 30 seconds is not a hard total command-wall ceiling.

Allow at most three sequential supervised launches within that one cumulative allocation,
solely to recover ordinary startup/harness defects before native correctness
execution begins. Each launch needs its own preserved, sealed accounting and
source binding. Use one fixed output root and append-only journal; an unclosed
reservation retains its existing charge. A corrected helper must pass affected
checks and source review before another eligible launch. Write a shared create-only
series-start marker before any native probe, including the filesystem gate. An
existing, partial or ambiguous marker consumes the sole series authorization.
There is at most one native correctness/timing series. Once that series starts,
do not restart it, discard measurements, or spend a new allocation implicitly.
API absence, unsupported filesystems, ABI/identity/freshness findings, resource
violations and timing outcomes are findings, not retry opportunities. Exhaustion
or inability to preserve accounting is a material issue.

The fixture is a new child of that output root, never the old stress fixture.
Limit it to 64 simultaneous file entries, four directories including its own
root, and 1 MiB of logical payload. Hard-link names count as entries. Control
records outside the fixture remain within the 16 MiB total output limit.
Preflight every output, temporary and atomic-journal path against the established
240-character bound. The declared growth, shrinkage, removal and replacement
steps below may mutate their fabricated files; preserve phase records, final
fixture state, failed-attempt trees and all result evidence. No cleanup of
completed or failed attempts is included.

Use the explicit repository `.venv\Scripts\python.exe -B`, with
`PYTHONDONTWRITEBYTECODE=1` and `PYTHONUTF8=1`. Reuse the reviewed ownership helper
that handles the virtual-environment launcher's intermediary process. Do not
replace it with a direct-parent assumption or modify the original supervisor.

## Correctness before timing

Within the new fixture, compare independently obtained values for distinct files,
multiple names for one hard-linked file, Unicode names and a near-bound name.
Check growth and shrinkage while a writer remains open, after a write through
the other hard-link name, and after closure. Flush user-space writes before
querying; keep the handle open for the held-open cases. Pause mutation while
obtaining each reference/native pair. Check both names against the reference at
every stable phase. Do not cache either side's query result.

Exercise disappearance and replacement. A removed name must raise the matching
error; a replacement's current values must match the reference, without assuming
that Windows never reuses a deleted file's ID. Confirm missing-file translation
to `FileNotFoundError`; other errors must propagate with native details. Inject
access/sharing failures, malformed buffers, unexpected attributes and reparse
cases in artificial checks without changing permissions or requiring elevated
symlink creation. Record the limits of mocked cases. No native correctness
failure can be relabeled as a successful performance comparison.

## Conditional timing and decision rule

Only after all correctness comparisons pass, prepare and freeze exactly 64
stable fixture paths and their post-correctness metadata, then make ten paired
passes over them. Each pair performs 64 native queries
and 64 ordinary `os.stat` queries, for 1,280 timed queries total. Fix the same
path order and alternate native/reference then reference/native order by pair.
Both sides return the same tuple shape and perform equivalent validation and
deadline checks. Include real adapter overhead. Use `perf_counter` durations;
check a 0.5-second batch deadline before and after every query, with the existing
supervisor enforcing the outer bounds. Record all twenty batch durations and
all pair ratios. Never drop a slow pass, insert warm-ups or rerun the series.

Every timed result must still match the stable reference. Timing excludes the
subsequent serialization equally on both sides, but all serialization is inside
the charged unit. Earlier correctness queries will have warmed some system
caches; this is a paired component comparison, with no cold-cache or complete-
scanner performance claim.

The prospective engineering triage rule is a median native/reference duration
ratio at most 0.80, with every native batch faster than its paired reference.
The 20% margin is a chosen threshold for worthwhile further engineering, not an
estimated speedup, statistical significance claim, or scientific quality gate.
Nonpositive or nonfinite clock durations, incomplete data, a deadline exception, or any
incorrect tuple make the comparison invalid. A correct comparison that does not
meet the speed criterion is a valid negative finding; do not try alternate thresholds.

Write bounded structured progress, correctness, timing and final-result records
before worker exit. A success claim requires original-supervisor completion and
result binding, closed accounting, preserved failures, and no resource violation.
If successful and sufficiently faster, the outcome is permission to *propose*
full scanner work, not permission to implement or run that later scope. Record
`scanner_readiness_passed: false` regardless of the component outcome.

## Boundaries that remain in force

The existing scanners, tests, approvals, ownership helper, supervisor, fixtures
and completed/failed evidence stay frozen. No parent traversal or hashing of
scientific bodies, no existing stress-fixture traversal, no real-root execution,
no scientific output, and no Git mutation are included. All nine embargoes,
three sealed holdouts, six completed retention reviews and twelve earlier YOLO
final-frame reviews remain intact. No repeated visual review is needed.

The actual scanner would still need two complete fresh inventories, identity
multiplicity per in-root entry, conservative maximum sizes across the pair,
correct disappearing-file restart behavior and all existing error/deadline
semantics. Additions may be accepted; lost earlier identities or multiplicities
may not be silently ignored. A component result does not prove those properties.
The unchanged 30-call static threshold below 0.40 seconds, dynamic threshold
below 0.90 seconds, live 0.5/1-second limits, regression, integration, recovery
certificate and separately authorized clean commit remain prerequisites.

Old arithmetic balances remain unchanged: profiling 26.560999999998785 seconds;
failed static allocation 27.687000000001717 seconds with zero attempts remaining;
real diagnostic 292.73500000001513 seconds; real cumulative
11132.492000000013 seconds. None is renewed by this proposal.

Ryan's 2026-10-05 instruction supersedes the blanket stop-on-any-failure rule.
Resolve routine tool and helper issues within approved scope without repeated
permission requests, preserving evidence and explaining meaningful corrections.
Pause for material correctness, evidence, resource or scope issues. This does
not grant the new interface/allocation proposed here or any Git action.

## Preparation evidence

Preparation is documentation and read-only source/evidence review only. The
earlier restricted CPython raw-source fetch was a lookup interruption, not a
test or diagnostic failure; its receipt remains unchanged and that fetch was
not retried. No claim about installed CPython's internal stat implementation is
needed for this proposal.

Preparation records are under `data/outputs/t/ebbn_plan_fa730bcb6d2e/`. The initial
receipt binds 46 allowlisted source, authority, context and fabricated-metadata
files. The four context documents may receive new continuation text; historical
bodies and the other 42 bindings must remain intact. The expected final worktree
has 18 intended unstaged files on `codex/ball-detector-baseline`, HEAD
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`, with an empty index. No component
code, native probe, new tests or experiment ran while preparing this proposal.

Earlier scope and evidence: [recovery proposal](ball_crop_candidate_retention_error_breakdown_recovery_proposal.md),
[prefix proposal](ball_crop_candidate_retention_scan_prefix_proposal.md), and
[completed static timing request](ball_crop_candidate_retention_scan_timing_request.md).
