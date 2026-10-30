# Output-accounting reassessment after the identity-equivalence experiment

Status: design-only reassessment on 2026-10-05, requested by Ryan. No runtime
implementation, compiler installation, native probe, test run, experiment or Git
mutation is authorized by this document. All consumed attempts remain consumed.

## Decision

Do not integrate the completed Python by-name adapter: it missed its prospective
speed gate. Do not substitute directory-entry sizes or stop accounting for old
files. The preferred next investigation is a **compiled sequential loop with
fresh per-file queries**, preserving complete whole-root accounting. First
establish a supported build path and review its interface; speed is unproved.

This changes where the repeated work runs, not which files count. It is a
separate candidate, not a retry of the completed adapter series. The native
identity contract would need explicit scanner-integration review; the completed
tiny component is not a full-scanner certificate.

## What the saved evidence establishes

The historical profile at
`../data/outputs/t/ebsp_fa730bcb6d2e/profile_statistics.json` records 16,134
`nt.stat` calls taking 291.710 ms, about 59.8% of the scanner's 487.581 ms
profiled call. That call exhausted its deadline and returned no accounting
total. It was not a complete successful two-inventory benchmark. Nested profile
timings must not be added together, and profiling overhead prevents treating
these figures as an unprofiled performance bound.

The later prefix candidate failed its first static readiness call. The latest
by-name component passed 94 comparisons across seven controlled phases and the
separate missing-file check, but its 1,280-query timing comparison had median
native/reference ratio `0.8992258224480973`, versus the required at most `0.80`.
Native won six of ten pairs, missing the every-pair-faster requirement too.
The completed audit is
`../data/outputs/t/ebni_src_fa730bcb6d2e/outcome_audit_01.json`.

Execution order was associated with the observed timing: native won all five
pairs where it ran second and one of five where it ran first. The second method
won nine of ten pairs overall. This is descriptive order sensitivity, not proof
of a cache mechanism, statistical significance, or a reason to discard runs.
The 64-file warmed fixture cannot predict whole-scanner or cold-cache speed.

The structural concern is supported by source: each accepted measurement needs
two complete inventories, repeatedly querying every historical file entry.
Changing a single lookup leaves that scaling intact. The evidence does not
prove filesystem instability or the internal cause of the original real-run
interruption.

## Alternatives assessed

| Direction | Assessment |
| --- | --- |
| Further Python path/query tuning | The tested candidates did not establish readiness. No saved result justifies another small substitution or renewed attempt. |
| Directory-level metadata batches | Reject as a demonstrated equivalent substitute. Fresh enumeration does not prove fresh sizes through other hard-link names. |
| Frozen history plus bounded new writes | Potentially removes most repeated work, but current code does not enforce the required immutable history or complete write budget. This is a larger accounting-contract redesign. |
| Compiled loop, fresh query for every entry | Preferred source/build feasibility direction. It can reduce language-boundary and Python loop/object overhead without excluding history. Kernel-query cost remains; no speedup is established. |

Microsoft documents that changes through a hard link need not update the size
shown in other directory entries. Two such inventories, or taking a maximum
with an older value, cannot account for growth neither inventory observes.
See [hard links and junctions](https://learn.microsoft.com/en-us/windows/win32/fileio/hard-links-and-junctions).
The presence of file IDs and end-of-file sizes in
[FILE_ID_EXTD_DIR_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_extd_dir_info)
does not supply the missing freshness guarantee.

## Source-only write audit

The original diagnostic's intended scientific output is small, but its complete
write surface is larger. These findings come from source, without opening
scientific inputs or outputs. The separate recovery runner is not implemented.

| Writer and source | Present behavior | Gap in a proposed fixed write budget |
| --- | --- | --- |
| Diagnostic artifacts, `crop_retention_error_breakdown.py:104,539-566` | Create-only final files; the readable summary is limited to 65,536 bytes before writing. | Breakdown JSON and provenance JSON have no explicit serialized-byte cap. |
| Worker receipt, same module `:584-592` | Create-only result JSON, then integrity readback. | Its embedded text is capped; the complete result is not. |
| Journal, seals and lock, `crop_retention_resources.py:27,119,165` | Create a pending file, publish with a hard link, remove the temporary name. | No serialized-record cap; overlapping names and failed pending publications count. Time reservations are not byte reservations. |
| Child stdout/stderr, same module `:360-368` | Both streams write to the attempt log. | No per-log write-time quota. Error/runtime output also uses this stream. |
| Temporary/runtime output, same module `:361-366` | Redirect temporary-directory environment variables and disable bytecode. | These settings guide cooperating code; they do not confine filesystem writes or impose byte quotas. |

The preservation whitelist detects unexpected names and changed metadata when
checked; it does not prevent mutation. The final 16,384-byte accounting reserve
does not impose that byte limit on the journal writer. Current monitoring bounds
observed output, not all future writes between samples.

Consequently, cached baseline bytes plus a declared allowance for three output
files is not a proven whole-root bound. A broker would also need to cover logs,
journals, receipts, temporary names, partial failures, transitive runtime writes,
hard-link aliases and changes to historical files. Receipts do not make files
immutable. Held handles alone do not establish immutable directory membership;
[CreateFileW sharing rules](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
also exempt attribute/extended-attribute access. Full confinement would introduce
access-control, token and inherited-handle requirements. No ACL, ownership or
historical-file change is proposed or performed here.

## Preferred next scope: a build and interface plan

Inspect the supported local toolchain before proposing implementation. This
reassessment found no `cl.exe`, `clang.exe`, `gcc.exe`, `cargo.exe` or `cmake.exe`
on PATH, and no Visual Studio locator at its usual installer path. This limited
inventory is not proof that no compiler exists elsewhere. No compiler was run
or installed. A compiler dependency, if needed, must be made concrete rather
than silently installed as part of an experiment.

The proposed interface should batch the language boundary, **not** substitute
directory metadata for fresh queries. Microsoft documents
[GetFileInformationByName](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getfileinformationbyname)
as a path-based query without a returned file handle. Its measured wrapper did
not pass the speed gate; moving the loop into compiled code is only a hypothesis
about overhead. The documentation currently carries a prerelease notice, so a
build plan must pin the supported local ABI/API and fail closed if unavailable.

Before a prototype is reviewable, specify:

1. A supported compiler/runtime, exact flags and dependencies, source and binary
   hashes, reproducible build instructions and an isolated ignored build path.
2. A bounded sequential interface with checked buffers, integer overflow checks,
   explicit ownership/cleanup, and no background worker or partial-success path.
3. Complete fresh names and per-file metadata for both inventories; full backend
   identities; per-name hard-link multiplicity; conservative maximum sizes;
   disappearance resets; native error propagation; and indirection rejection.
4. One original 0.5-second deadline covering discovery, queries, aggregation,
   restarts and acceptance, including checks before/after each query. A native
   clock must not silently replace Python's current clock contract. Using its
   existing callable through a supported public interface is one option whose
   overhead would also count.
5. Independent correctness checks for the new binary and interface, followed by
   an explicitly bounded performance plan that includes the whole candidate
   cost. Existing component tests remain historical evidence, not binary
   validation. No old fixture traversal or benchmark replay follows from this
   reassessment.

This is a design preference, not implementation readiness. If a supported build
path and faithful contract cannot be made practical, report that limitation
before considering the broader immutable-history/write-budget redesign.

## Preserved project boundary

The existing 30-call static gate below 0.40 seconds, dynamic gate below 0.90
seconds, live 0.5/1-second limits, regression/integration and recovery certificate
remain. No gate is lowered. The whole-root cap remains 32 GiB, worker-tree memory
8 GiB and free-disk floor 10 GiB. Real diagnostic and cumulative balances remain
`292.73500000001513` and `11132.492000000013` seconds. No synthetic allowance is
renewed; the latest component has zero series remaining.

The planned 48-row error breakdown is still pending. No tracker or quality gate is
selected. All nine embargoes, three sealed holdouts, six retention reviews and
twelve earlier YOLO reviews remain preserved. No scientific body was read or
hashed, and no fixture was traversed. Git authorization remains separate.

Preparation and preservation records are under
`../data/outputs/t/ebra_plan_fa730bcb6d2e/`. This task adds this note and updates
continuation text in three context files. Starting state: 21 intended unstaged
files, empty index, branch `codex/ball-detector-baseline`, HEAD
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`. Expected final state: 22 intended
unstaged files, with the branch, HEAD and index unchanged.
