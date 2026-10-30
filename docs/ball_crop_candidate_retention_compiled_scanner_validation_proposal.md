# Proposed compiled-scanner native validation

Status: proposed next scope, not an execution authorization. Installation and
isolated build have completed; all 39 compiled artificial checks passed. Full
regression validation is still in progress when this proposal is prepared.

## Decision this would answer

Can the complete compiled-batch accounting candidate meet the existing scanner
requirements on fresh controlled files? Test that bottleneck directly. Do not
start another sequence of small wrapper speed substitutions or repeat old runs.
Synthetic success would not establish ball-tracking accuracy or authorize the
scientific error breakdown.

## One proposed allocation

Request a new, separate **120-second cumulative active allocation**, with three
conditional charged units capped at **20, 50 and 50 seconds**. At most one
execution of each unit is permitted. Worker setup, query resolution, guards,
reference measurements and candidate calls belong inside that reserved unit.
Preserve the original supervisor's charging rule: it captures charged elapsed
before final accounting and final event/seal publication. Report those charged
times separately from complete command wall times. Add outer command limits of
**30, 60 and 60 seconds**, respectively, to bound setup/finalization overhead;
all three command windows together are at most 150 seconds. Final accounting
must still succeed. No automatic performance retry, warmup timing pass or
discarded measurement is permitted.

All existing allocations and failures stay unchanged. This is not reuse of
arithmetic time from an exhausted series and does not reset the real diagnostic
or its cumulative budget. Preserve the 8 GiB worker-tree memory cap, 32 GiB
whole-root output cap and 10 GiB free-space floor. Reserve at most 16 MiB for new
receipts/logs, and explicitly bind a fixture-byte allowance before execution.
Use fresh create-only roots; never traverse/reuse old fixtures or scientific
bodies. The ordinary 0.5-second accounting deadline and 1-second live monitor
limit remain in force.

## Conditional gates

1. **Native correctness, at most 20 seconds.** Bind the reviewed production
   binary, wrapper and build provenance. On at most 64 fresh local NTFS file
   entries, independently verify file relationships, full backend identifiers,
   opaque 128-bit values, hard links, held-open growth/shrink, disappearance,
   replacement and native error translation. Retain the approved partition and
   continuity approach rather than requiring equal numeric labels across APIs.
   Exercise complete accounting as well as individual records. Require verified
   root/ancestor/reparse guards; no unrestricted callback is acceptable in live
   use. Any correctness discrepancy prevents the next unit.
2. **Complete static scanner, at most 50 seconds.** Create a fresh instance of
   the existing fixed seeded 12,000-file/400-directory fixture specification.
   Bind its manifest and independently established expected total before timing.
   Run exactly 30 consecutive recorded gate calls. Every result must equal
   the expected total; every duration must be finite, nonnegative and below
   0.40 seconds. Stop on the first failed call/gate; preserve it. No static
   failure permits the dynamic unit. Existing cache state is not controlled;
   this is not a claim of cold-cache performance. Identify and retain supervisor
   accounting calls separately from these 30 gate calls; their reads and timing
   must not become undocumented warmup. The static fixture total and the broader
   supervised tree, which also contains growing receipts, are distinct measured
   scopes, both explicitly recorded.
3. **Complete dynamic scanner, at most 50 seconds.** Use the successful new
   static tree for the existing 30-second prescribed mutation schedule: each
   scheduled tick appends 4 KiB to 64 fixed files and creates one 512-byte file.
   Total permitted growth is exactly 7,879,680 bytes. Preserve two complete
   inventories, per-name multiplicity, conservative sizes and disappearance
   resets. Every scanner call stays below 0.40 seconds and monitor intervals
   below 0.90 seconds. Retain all mutations, scan results and timing evidence.

The fixture-byte allowance must equal the frozen initial fixture total plus
the prescribed growth, with the tiny correctness fixture explicitly included.
Allocation figures are maxima, not promises that setup will fit. An exhausted
unit remains a recorded finding and does not grant another attempt.

## Required implementation before any native execution

The proposed approval would cover building/reviewing the isolated harness and
its relevant artificial checks, followed by the conditional native units only
if prerequisites pass. It must bind actual guard implementations and the frozen
binary, rather than caller-supplied no-op guards. Preserve original source files.

The supervisor must account for the whole mutable validation tree. Monitoring
only a small receipt directory would not qualify this candidate. Bind the new
scanner explicitly at the original supervisor's accounting-function boundary
inside the isolated worker/harness, retaining its cadence, resource caps,
ownership, reservations, failure paths and final accounting. Review and test
that binding, including failure cleanup, before executing it. If it requires
unreviewed control-flow or limit changes, stop for a substantive reassessment.
An unsuccessful or incomplete final accounting record cannot certify a run.

The initial acceptance gate also requires successful full regression validation
of the compiled prototype. Keep its 39 passing checks and completed full-suite
result as evidence; rerun only checks justified by subsequent code changes.

No production scanner replacement, scientific body access, model execution,
new human visual review, staging, commit, push, PR or merge is included. After
these gates, production integration and a validated clean commit remain
necessary before real scientific recovery. The six retention and twelve YOLO
reviews remain complete.
