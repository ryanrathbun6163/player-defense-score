# Responsive resource monitoring revision

Ryan approved implementation and validation on 2026-10-05 with
"ok I like it. Move forward", following the plain-language design review.
This revision supersedes the proposed pursuit of a half-second scanner for
this recovery path. It does not rewrite or invalidate the earlier results.

## Purpose

Keep memory, disk-free-space and runtime checks responsive while counting the
entire output tree in an independently owned Python process. A slow metadata
query must not occupy the supervisor's safety-check loop. No compiled scanner
or additional dependency is required. Preserve the earlier compiled candidate,
build tools, failed attempts and all completed reviews without rerunning them.

The original resource module, scientific runner, reviewed manifests and
historical journal remain byte-for-byte unchanged. The new monitor is a
separate backend; activating it in a real recovery requires the versioned
recovery runner/authority and the separately authorized validated clean commit.
No real scientific run or Git mutation is authorized by this implementation.

## Explicit revised operating policy

| Setting | Value and meaning |
| --- | --- |
| Requested safety polling | Every 0.25 seconds |
| Maximum completed safety-check interval | 1 second; measured, not a hard real-time OS guarantee |
| Full accounting request deadline | 10 seconds, including initial helper startup/dispatch |
| Next scan scheduling | At most 5 seconds after an accepted scan completes |
| Oldest accepted measurement | At most 30 seconds from that scan's start; never relabel a cached total as fresh |
| Concurrent accounting requests | One, in one owned helper process |
| Whole-root output cap | Existing 32 GiB, observed by complete scans |
| Aggregate sampled resident memory | Existing 8 GiB, including worker and accounting helper |
| Free-space reserve | At least 50 GiB, or a higher limit supplied by the existing authority |
| Windows worker committed-memory ceiling | 8 GiB |
| Windows helper committed-memory ceiling | 512 MiB |
| Scanner protocol record bound | 8 KiB per serialized record |
| Worker completion-receipt bound | 1 MiB; distinct from scanner protocol |
| Final publication reserve | 64 KiB, covering bounded post-measurement administrative records |

The 30-second freshness allowance accommodates two 10-second scans with a
5-second interval and scheduling margin. It is a separate check from the
10-second deadline on an individual outstanding request. These are operational
settings to validate, not ball-tracking accuracy thresholds.

Committed memory is memory Windows has promised to processes; it differs from
the resident RAM sampled by the existing monitor. Both controls apply. The
Windows ceilings are allocation backstops, not claims of an identical memory
metric. Keep kill-on-close ownership and bounded termination for both process
trees, including on failed startup or interrupted monitoring.

## Accounting and failure behavior

Use fresh per-file metadata and the existing two-complete-inventory semantics:
full file identity, hard-link entry multiplicity, maximum observed sizes,
disappearance resets and conservative acceptance. Guard path ancestors and
entries against symlinks and Windows reparse indirection. Do not open or hash
scientific file bodies. Do not skip preserved files, substitute stale directory
sizes, move history or reset any budget.

Before releasing a scientific worker, require complete initial accounting.
After every writer has stopped, require successful final accounting before
returning success. During execution, retain the scan identifier and actual
measurement timestamps in each applicable receipt/sample. Failed, incomplete,
malformed, mismatched or stale results cannot become a successful measurement.
Scanner timeout or failed safety checks stop and clean up both owned trees.

Launch each process suspended, assign Windows job ownership and the memory
ceiling, then resume its verified initial thread. This owns children created
by the Python virtual-environment launcher before any worker instructions run.
An already outstanding scan at worker shutdown cannot substitute for the final
scan: drain it, then request a distinct complete scan after shutdown. This may
use two 10-second request windows while cheap safety checks continue. Report
this finalization time separately from the charged attempt interval. During
final accounting, periodic journal writes stop; bounded final publications are
covered by the reserve. The 1 MiB completion-receipt bound is a new explicit
interface constraint, not a claim that legacy receipts had that same limit.

Output and free-space checks are sampled. Files may grow between measurements;
the 32 GiB cap is not an instantaneous filesystem quota. Delayed counting may
increase the observed overshoot. Record violations and mark the attempt failed;
do not hide an overshoot or claim the 50 GiB reserve is OS-reserved disk space.
This monitor addresses software resource exhaustion, not hardware temperatures.

Retain original limit bindings in the existing journal. Record this stricter
free-space policy and revised timing separately with an explicit policy version
and digest. Keep worker-time accounting, finalization time and overall wall time
distinguishable, including failed attempts. Never renew an exhausted allowance.

## Validation scope

Use only fresh artificial fixtures, source/configuration and administrative
receipts. Focused tests must cover file accounting, delayed/stalled/invalid
results, safety checks continuing while scans run, startup and descendant
cleanup, memory ceilings, disk/time failures, freshness and final accounting.

Run one explicit fresh 12,000-file/400-directory design check after focused
tests pass. It verifies correct totals and end-to-end supervision under the
revised timing; it is not a repetition of the old 0.40-second performance gate.
Keep it outside unittest discovery so the full suite does not repeat it.
Then run the required full suite once on the final source. Repeat affected
checks only when a correction or new finding justifies it.

Validation uses fresh ignored output roots and the existing Python environment,
with bytecode disabled. Allow at most 1,200 seconds for focused checks, 180
seconds for the separate design check, and 3,600 seconds for full regression.
These are artificial validation bounds, separate from real journal balances.
Use 8 GiB sampled validation-worker memory, 32 GiB validation output and a
50 GiB free-space floor. Preserve failed logs and revisions if repairs are needed.

No real experiment files, old timing fixtures, sealed holdouts or embargoed
predictions are read or hashed by the parent. The saved 48-row error breakdown
remains pending. All six retention and twelve YOLO final-frame reviews remain
complete. No new visual review is needed for this infrastructure-only change.

## Starting state and continuation

Branch `codex/ball-detector-baseline`, HEAD
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`; 25 intended unstaged files and empty
index. Preparation protects 181 source/test/configuration/context bindings in
`data/outputs/t/ebdm_fa730bcb6d2e/before.json`.

Implementation, focused validation, one design check and full regression are
authorized. Staging, committing, pushing and scientific execution remain
distinct boundaries. Source changes require a new validation certificate for
the recovery path; old certificates and failed execution evidence stay intact.
