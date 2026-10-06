# By-name identity equivalence: review and proposed follow-up

Status: identity-contract review completed on 2026-10-05; the implementation and
new execution envelope below are proposed for approval. This document does not
renew the completed by-name series or change the production scanner.

## Finding and decision

The completed component attempt `d774f180726d47a08a6aead2658a807a` returned the
same file ID and 64-byte logical size through both APIs, but different volume
identifiers. The Python tuple was `(986718957, 1125899906873685, 64)`; the native
tuple was `(14572188484234126061, 1125899906873685, 64)`. The first comparison
therefore failed the approved cross-API numeric-identity requirement. Its result
remains `identity_contract_review_required`; none of its later correctness or
timing stages ran. Its 72 artificial tests and successfully sealed supervision
remain valid evidence for their respective scopes.

Review of `src/ball_tracking/crop_retention_resources.py:output_bytes` shows that
the counter uses identities as equality keys. It needs to recognize which names
refer to the same file and whether that identity persists between inventories.
It does not perform arithmetic on the identifier values or expose them as the
returned byte total. The recovery and prefix candidates use the same semantics.

**Recommendation:** preserve each backend's complete identifiers and compare
their file relationships, continuity and sizes. Do not require equal identifier
numbers across APIs. This is an explicit amendment to component validation,
subject to approval, not a correction to the old outcome or permission to ignore
an identity discrepancy.

## What documentation establishes

Python documents `st_dev` as the device identifier and nonzero `st_ino` as a file
identifier within that device; on Windows it normally represents the file index.
It does not promise numeric equality with every Windows volume-identifier API.
See [Python's stat-result contract](https://docs.python.org/3.11/library/os.html#os.stat_result).

Microsoft's older
[BY_HANDLE_FILE_INFORMATION declaration](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/ns-fileapi-by_handle_file_information)
contains a `DWORD` volume serial and two halves of a 64-bit file index. The
[FILE_STAT_BASIC_INFORMATION declaration](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-file_stat_basic_information)
used by the prototype has a `LARGE_INTEGER` volume serial, a file ID, and a
separate 128-bit ID. Windows also documents a full-width volume/file identity in
[FILE_ID_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_info).
These declarations support differing representations; they do not establish
which calls the installed Python build makes internally. The saved result alone
does not prove a universal conversion rule between the two volume values.

No bit mask, truncation, modulo operation, padding, or mapping is proposed to
force equality. The earlier restricted CPython source fetch remains untouched;
no alternate source route or claim about its unavailable internals is needed.
The known inconsistent prose in the basic-structure page is not used as an ABI
or identity-encoding authority. The already reviewed adapter declaration stays
frozen.

## Why different labels can preserve byte accounting

For each complete inventory the current counter builds an identity-keyed record
containing the number of in-root names and maximum observed logical size. It
accepts a pair only when earlier identities remain present and their name counts
have not decreased. It then sums each current count multiplied by the larger
size observed for that identity across the pair.

A fixed one-to-one change of labels across **both** inventories leaves those
membership, count, maximum and sum operations unchanged. For example, two names
of a 64-byte file count as 128 bytes under either set of identity labels. This
is logical output accounting per name, not physical disk-block allocation.

The qualification matters: matching hard-link groups separately at each phase
is insufficient. A backend that invents new labels on every scan could preserve
each individual grouping while breaking the scanner's stabilization check.
Continuity of every still-live file must be checked as well. This is a source-
based equivalence argument; it is not evidence that the native API meets its
premises on every workload.

The mathematical correspondence is an explanation, not a runtime translation
table. Neither adapter may replace its identifiers with the other adapter's
values, with path-derived labels, or with invented group numbers.

## Proposed component contract

Keep the existing native key `(full unsigned volume serial, full FileId64)` and
Python key `(complete st_dev, complete st_ino)` separately. Keep the existing
local fixed NTFS restriction and rejection of reparse points/ancestor
indirection. No ReFS, network-volume or multi-volume support is introduced.
Retain volume values in both keys, even on this single-volume fixture.

For each controlled stable phase, require all of the following:

1. Both methods query every selected name freshly and return the independently
   known logical size. Size equality alone is insufficient.
2. Each backend observes exactly one nonzero, constant volume identifier across
   the entire new fixture and all phases. The two constants may differ.
3. Within each backend, the declared primary/alias hard-link pair shares an
   identity, and every other simultaneously live file has a distinct identity.
   Compare the complete sets of names in each identity group across backends as
   an additional check. Reject zero/invalid identities, collisions, split hard
   links, extra aliases, omitted entries and unexpected volume changes.
4. Every file that remains alive keeps its own complete key across growth,
   shrinkage, writing through the other link, closure and later additions.
   Each phase must be stable while reference/native observations are obtained.
5. Retain the full 128-bit native field as opaque evidence. Validate its exact
   16-byte representation and compare its own same-file grouping and continuity
   during correctness phases. Do not infer how it encodes FileId64 or use it to
   redesign the runtime key in this component task.
6. The declared delete/recreate step starts a new lifetime. Record old/new keys
   from both APIs without requiring a new numeric ID. Require the same observed
   reuse relationship in both backends; disagreement is an inconclusive identity
   finding that prevents timing. Never equate a surviving file with a distinct
   simultaneously live file. This controlled observation does not establish
   behavior for arbitrary concurrent replacements.

Keep the earlier missing-file/error checks, known-payload changes with open
writers, Unicode and near-bound filenames, and fixed final 64-name inventory.
Flush writes and stop mutation before each comparison. All unexpected reference
or native errors remain recorded findings. Do not soften a predicate to obtain
a pass after seeing the result.

New artificial checks must cover valid different identity labels, hard-link
splitting, distinct-file collisions, volume drift, changing labels between
phases, size mismatches, inconsistent reuse and malformed opaque IDs. Pure
fabricated two-inventory examples must check unchanged acceptance decisions and
totals under a consistent relabeling, including added names/files, lost names,
growth/shrinkage and conservative maxima. These test the proposed contract;
they do not substitute for later full-scanner validation.

## Fair conditional timing

Only after every correctness predicate passes, freeze **two** expected tuple
dictionaries over the identical 64 paths, one for each backend. Both retain the
same three-integer tuple shape and logical sizes. Each timed query must exactly
match its own frozen tuple; neither side translates its identifiers during
timing. Keep the actual native adapter's validation and conversion overhead.

Retain ten fixed paired passes, alternating native/reference and reference/native
order, 64 fresh queries per backend per pair, 1,280 timed queries total. Use the
same paths and equivalent validation/deadline checks. Preserve the pre/post-query
0.5-second batch deadline and all twenty batch durations, query counts and ten
ratios. No warm-up, discarded pass, reordered series, automatic retuning or rerun.
Serialization occurs after each timed batch and inside the charged unit.

Retain the prospective triage rule: median of the ten native/reference duration
ratios at most 0.80, with all ten native batches strictly faster. Durations must
be positive and finite. Incomplete data, identity/size drift or a deadline error
makes the comparison invalid. A correct but slower result is a valid negative
finding. The warmed tiny fixture cannot predict complete-scanner or cold-cache
performance. `scanner_readiness_passed` remains false for every outcome.

## Concrete approval envelope

Approval would authorize this identity-validation amendment, its implementation,
new artificial checks, independent review and one conditional new native series.

- New ignored implementation: `data/outputs/t/ebni_src_fa730bcb6d2e/`.
- New isolated output root: `data/outputs/t/ebni_fa730bcb6d2e/`.
- New approval record:
  `configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_by_name_identity_equivalence_approval_v0_1.json`.
- Frozen adapter reuse: `data/outputs/t/ebbn_src_fa730bcb6d2e/by_name.py`, SHA-256
  `a7f2ff3ac303cdca272b224e7f9ec5dbd7c97a2095ee79957019a501f6eea998`.
  Reuse its saved 32 passing checks as unchanged component evidence. Do not rerun
  them merely to launch this follow-up. New/changed comparison and supervision
  code requires its own meaningful checks and final source bindings.

The supervisor and ownership protocol remain the original frozen versions.
Gate release, reservation and proven worker ownership precede fixture operations
and native probes. The parent may read/hash allowlisted source, authority and
fabricated-result metadata only. It may not traverse either existing fixture or
the new fixture, or read/hash scientific bodies. The original supervisor may
account its new owned output root as required by its unchanged implementation.

Allocate a **new** maximum 30 seconds of cumulative charged active time, at most
the remaining allowance per attempt; 16 MiB of total new output; 8 GiB for the
owned process tree; and at least 10 GiB free disk. Polling remains 0.25 seconds,
with a 1-second maximum monitor interval. Report external command wall time
separately because the supervisor's final-accounting/sealing tail is outside its
active-time measurement. No old allowance is consumed or reset.

Use at most three sequential supervised launches in this single new root and
append-only journal. Another launch is permitted only for an identified,
corrected and reviewed ordinary startup defect **before** native probing begins.
Preserve and charge every closed failure; an unclosed reservation keeps its
charge. A shared create-only series marker must precede all new native probes,
including the filesystem gate. Existing, partial or ambiguous marker state
consumes the one series. No restart follows a semantic/resource finding or a
timing result. Source revisions, failed validations and launch evidence remain
immutable; routine eligible corrections need no additional permission.

The new fabricated fixture is limited to 64 simultaneous file entries, four
directories including its root, and 1 MiB of logical payload. Hard-link names
count individually. Keep all control/progress/result records and worker
temporary files within the 16 MiB output root and bounded before exit; preserve
phase records and final fixture state through the declared mutations. Preflight
all paths, including publication temporaries, to at most 240 characters. Use
`.venv\Scripts\python.exe -B`, `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUTF8=1`.
Acceptance needs the unchanged supervisor's successful completion, sealed
accounting and result binding, plus an independent post-run metadata audit.

## Scope after this decision

This follow-up does not implement a full scanner, change scientific outputs,
select a ball tracker, run the full suite, or authorize real recovery or any Git
mutation. Even a positive component result only supports proposing scanner
integration. Two complete inventories, multiplicity, conservative sizes,
disappearance/error handling, the 30-call static gate below 0.40 seconds,
dynamic gate below 0.90 seconds and live 0.5/1-second limits remain unchanged.
Regression, integration, the recovery certificate and a separately authorized
clean commit are still required before the saved error breakdown can run.

Preserve all nine embargoes, three sealed holdouts, six completed retention and
twelve completed YOLO reviews, and every prior successful/failed/incomplete
artifact. The previous component remains a numeric-compatibility finding with
zero native series remaining despite 29.21900000000096 arithmetic seconds.
Earlier balances remain: profile 26.560999999998785 seconds; static
27.687000000001717 seconds with zero attempts; real diagnostic
292.73500000001513 seconds; real cumulative 11132.492000000013 seconds.

## Preparation record

This review used existing source, saved metadata and official API documentation.
No new code, tests, native probes, benchmark or fixture/scientific traversal ran.
The preparation receipt under `data/outputs/t/ebni_plan_fa730bcb6d2e/` binds 80
allowlisted inputs. Only this new proposal and continuation text in three
context documents are intended edits. All other 77 bindings and historical
context bodies must be preserved. Expected final status: 20 intended unstaged
files, empty index, branch `codex/ball-detector-baseline`, HEAD
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`.

The earlier [component proposal](ball_crop_candidate_retention_by_name_feasibility_proposal.md)
and its result remain frozen. Ryan's latest failure policy continues to permit
ordinary corrections within approved scope while requiring attention to material
correctness, evidence, resource or scope issues.
