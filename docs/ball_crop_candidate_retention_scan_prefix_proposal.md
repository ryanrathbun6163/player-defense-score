# Saved error-breakdown scanner: directory-prefix proposal

Status: draft for Ryan's review. Ryan authorized finishing this proposal with
"Yes you may move forward chat" after the source-lookup and external-documentation
interruptions. This preparation authorizes documentation and review only.

## Recommended change and why

Prepare a second, separate sequential scanner candidate. Keep ordinary fresh
`os.stat` calls and the entire existing two-inventory accounting algorithm.
Build the directory prefix once for each directory yielded by `os.walk`, then
append each filename to that prefix:

```python
for folder, _, files in os.walk(root, onerror=fail):
    check_deadline()                        # existing directory check
    prefix = os.path.join(folder, "")        # once per directory
    check_deadline()                        # charge prefix work to the deadline
    for name in files:
        check_deadline()                    # existing pre-query check
        info = os.stat(prefix + name)       # still a fresh ordinary query
        check_deadline()                    # existing post-query check
        # Existing identity, multiplicity and size aggregation follows.
```

This is a design excerpt, not an installed implementation. The complete candidate
must retain every other deadline check, restart, comparison and acceptance rule.
`folder` and `name` come directly from the unchanged native `os.walk`; there is
no new caller-supplied filename-list interface. The prefix expression handles
directory separators through the existing path library. Equivalence to
`os.path.join(folder, name)` must be checked for native filename components,
including drive roots, UNC/extended paths and Unicode, before timing is proposed.

This removes repeated generic path parsing for filenames that enumeration has
already separated from their directory. It does not reduce the number of fresh
metadata queries. The benefit is unproved and may be too small to meet the
unchanged timing gates. No speedup estimate is inferred from the profile.

## Evidence supporting this limited candidate

The approved single synthetic profile completed successfully at HEAD
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`, branch
`codex/ball-detector-baseline`. It captured the anticipated accounting deadline;
the scanner returned no total and `readiness_passed` remains false.

| Recorded function | Profile observation |
| --- | --- |
| Fresh `nt.stat` queries | 291.710 ms, approximately 60% of scanner cumulative time |
| `ntpath.join` | 71.589 ms cumulative, including nested path processing |
| `ntpath.splitdrive` | 34.578 ms self time, already included in nested callers |
| Whole scanner | 487.581 ms cumulative in the truncated, instrumented call |

Do not add nested cumulative timings or extrapolate a completed scan from these
figures. Profiling changes execution time. The observation establishes neither
the original real-run cause nor actual filesystem instability.

The largest measured cost is still metadata lookup. Changing that interface or
adding parallel queries introduces a larger correctness problem. This proposal
first targets the measured path-processing cost while preserving that interface.
It is deliberately one fixed candidate, with no automatic tuning or fallback if
validation or a subsequently approved timing gate fails.

Evidence, relative to the repository:

- `data/outputs/t/ebsp_fa730bcb6d2e/profile_statistics.json`, SHA-256
  `06ee889ded721f65eabe15e3e2788cc2a49dcfe6ab37b30396bc00b307b37337`.
- `data/outputs/t/ebsp_src_fa730bcb6d2e/profile_execution_continuity.json`, SHA-256
  `bdb79f4f527beb7b3927b5c02dd5779d8a60e45c9deefac21f7416c6727b730b`.
- Completed profile attempt `4932f5dc070640e3a96cf094ff86859b`: 2.594 active
  seconds, no recorded resource overshoot, successful diagnostic preservation.

## Alternatives considered

Threaded queries retain `os.stat`, but running futures cannot simply be cancelled.
Waiting for shutdown can extend a failed call; returning without waiting leaves
queries active. The current sequential call also cannot preempt a single OS
query, but several outstanding queries add a new cleanup obligation. No threads
or background accounting are proposed.
[Python executor documentation](https://docs.python.org/3.11/library/concurrent.futures.html)

A sequential native handle reader could query file identity and size, but exact
parity of identity, error and reparse behavior would need separate validation.
A compiled implementation would add build and binary provenance; a per-file
`ctypes` wrapper adds call crossings. Neither has a measured benefit here.
[Microsoft CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew),
[GetFileInformationByHandle](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfileinformationbyhandle)

Cached directory-entry sizes and Windows `DirEntry.stat()` identities remain
excluded. No new interpreter, compiler, dependency, installation or native
backend is part of this candidate.
[Python DirEntry documentation](https://docs.python.org/3.11/library/os.html#os.DirEntry.stat)

## Accounting rules that must remain unchanged

- One `time.monotonic()` deadline of 0.5 seconds covers all work, including
  prefix construction, both complete inventories, any restart and acceptance.
  Keep all existing checks and add the shown post-prefix check. Never accept
  a partial inventory or return a result after the deadline.
- Keep `os.walk`, its error callback and ordinary fresh `os.stat` behavior.
  Keep root/indirection guards. Do not cache metadata, skip subtrees or use
  filename identity. No supervisor adapter is installed during this stage.
- Aggregate by `(st_dev, st_ino)` and count every encountered directory entry,
  including hard links. Do not replace in-root multiplicity with total link count.
- Accept only two complete inventories whose earlier identities and entry
  multiplicities remain present in the second. Additions remain permitted.
  Charge second-inventory multiplicity times the larger observed size across
  the pair, including growth and shrinkage.
- `FileNotFoundError` discards the prior and incomplete inventories within the
  same deadline. Other filesystem errors propagate. Preserve the exact deadline
  exception. No fallback scanner, retry wrapper, evidence cleanup or limit change.

The original supervisor, first recovery candidate and their existing tests remain
frozen. Their hashes are bound in this proposal's preparation record. Preserve
all successful, failed and incomplete evidence and all prior approval records.

## Next requested approval: implementation and focused correctness only

After approval, add these separate files, refusing existing destinations:

- `src/ball_tracking/crop_retention_scan_prefix.py`;
- `tests/test_ball_crop_retention_scan_prefix.py`;
- `configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_scan_prefix_approval_v0_1.json`.

The approval records this exact proposal hash and Ryan's response. A new ignored
validation directory holds the helper, structural review and test result. Retain
the existing code rather than rewriting the failed candidate. Context documents
may record the new stage without changing historical evidence.

Independent source review must establish that the accounting function changes
only prefix preparation, its additional deadline check and the query expression.
Review all new helper code before executing it. New focused tests must cover:

1. Path equivalence for native filename components: directory/root separators,
   drive and UNC/extended forms, spaces, Unicode and long names. String-only
   path cases need no network or physical drive access.
2. Fresh query dispatch for every entry in every scan; no cached stat result.
   Fabricated outcomes cover hard links, different devices, growth, shrinkage,
   replacement, additions, disappearance, directory moves and propagated errors.
3. Prefix construction consuming the deadline, existing pre/post-query checks,
   repeated disappearance, stable-pair acceptance and final deadline rejection.
4. A small temporary Windows tree with Unicode names, nested directories and
   a hard link, compared with an independent ordinary-stat reference.

These validate new code. Do not rerun the completed first-candidate test command,
profiler or old experiments. Use the repository `.venv\Scripts\python.exe -B`
with `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUTF8=1`. Record unittest result counts
structurally, the exact command, source hashes and a preserved log; do not add
another line-ending-sensitive log parser. No stress fixture or timing loop is
part of these focused checks. Stop on any new failure without repair or retry.

Return the exact implementation diff and focused results for review. This stage
does not claim complete validation: a new runtime candidate still needs the full
suite and the performance gates before adoption. Those checks are deferred until
the separate timing-execution scope is concrete and approved.

## Later gates and budgets; no execution authorized here

All existing readiness requirements remain: the fixed 12,000-file/400-directory,
seed-0 layout; 30 consecutive correct calls each below 0.40 seconds, including
the first call with no discarded warmup; then the prescribed 30-second growth
workload with accounting below 0.40 seconds and maximum monitor interval below
0.90 seconds. The live limits remain 0.5 and 1.0 seconds respectively. See the
[original recovery proposal](ball_crop_candidate_retention_error_breakdown_recovery_proposal.md)
for the exact growth workload and remaining recovery gates.

Do not modify the preserved synthetic tree to run a future dynamic workload.
A later execution request must specify a separate fabricated dynamic destination,
the same frozen starting layout/workload, path-length checks, owned process
supervision, memory/disk/output bounds, active-time allowance and exact source
bindings. A new candidate's benchmark is new work; it cannot adopt or resume
the failed candidate's benchmark markers. All previous evidence stays in place.

The completed profiling allowance has `26.560999999998785` seconds remaining
but no unused execution authorization. It is not a new benchmark allowance,
and cannot cover the required 30-second dynamic workload. This proposal neither
resets that balance nor requests a new runtime budget. Any future allocation
must be explicit in a separately approved execution request.

Real recovery still requires the unchanged correctness/performance gates, full
regression, exact validation certificate and separately authorized staging and
clean commit. Its last verified balances remain `292.73500000001513` diagnostic
seconds and `11132.492000000013` cumulative seconds. Those are preserved receipt
values, not a new real-root inspection. No real worker or scanner runs here.

## Scientific scope and preparation checkpoint

The approved scientific task remains the same 48 copied saved-error rows with
pools separate. Its output is pending. No scientific body is read or hashed by
the parent; no inference, scoring, rendering, training or new scientific metric
is authorized. Preserve all nine embargoes, three sealed holdouts, six completed
retention reviews and twelve completed YOLO final-frame reviews.

This preparation edits only this new proposal and the three existing context
documents: `docs/context/current_state.md`, `roadmap.md` and
`validation_history.md`. The nine-file intentional dirty checkpoint becomes
ten files, with an empty index and unchanged branch/HEAD. Existing source,
approvals, frozen proposals and synthetic evidence stay byte-for-byte unchanged.
Before-context copies and bindings are saved under
`data/outputs/t/ebsx_plan_fa730bcb6d2e/`.

Preparation checks cover exact scope, preserved bytes, local links, whitespace
and independent proposal review. No tests are needed for these documentation
edits. No manual command is pending. The next decision is approval of the narrow
implementation/focused-correctness stage above; no benchmark, full-suite run,
real retry or Git mutation is implied by approval of this document.
