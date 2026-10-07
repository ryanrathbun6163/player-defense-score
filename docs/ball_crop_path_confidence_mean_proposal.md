# Compare mean path confidence with the saved sum-score baseline

Status: proposed, not authorized for implementation or execution. Ryan's latest
"move forward chat" authorizes preparing this follow-up. Prepared on
`codex/ball-detector-baseline` at `10e5fcb90f51909891d5df08d0b84ea5932a4033`.
The companion scope is
`configs/ball_tracking/proposals/rfdetr_medium_crop_path_confidence_mean_v0_1.json`.
This proposal does not renew any prior experiment or Git permission.

## One question

Does averaging the confidence along a candidate path, while retaining the
existing movement and gap rules, improve current-frame ball localization across
the six development windows, or merely change the wrong-output/missingness tradeoff?

The completed eight-frame contrast found six pairs where the emitted endpoint's
past-confidence contribution overcame its weaker current confidence. Ryan had
identified seven emitted marks as hands or players and one as ball with a displaced
center. These selected, correlated examples motivate a structural comparison;
they do not establish a cause, a tuned parameter, or improved tracking.

The new arm replaces the sum of path confidences with their mean. No weight sweep
or new threshold is proposed. Merely removing all past reward largely reproduces
the existing top-one control, because each current candidate can start a singleton
without a motion penalty. Dividing only the saved winning paths is also inadequate:
normalization can change which path is best. The proposal therefore permits one
new selector arm on the saved candidates and reuses the completed control results.

Mean confidence still can favor a persistent wrong object. It also makes the
unchanged gap/motion penalties stronger relative to confidence. The comparison
tests this complete scoring intervention; it cannot isolate path length alone,
establish physical object identity, or validate the method on unseen footage.

## Fixed development scope

| Possession | Representative frames | Challenge frames |
| --- | --- | --- |
| P001 | 50-74 | 200-224 |
| P002 | 250-274 | 25-49 |
| P003 | 300-324 | 150-174 |

All ranges are inclusive: 150 frames, 145 localization-eligible labels and five
hidden frames (P003 165-169). Keep both pools and each window separately visible.
Do not add windows, annotations, holdouts, confidence settings or localization radii.

Use one new arm, `history_mean_edge_tight_cost_tight`, at the inherited .01
candidate floor, top-twenty cap, five-frame current-and-past horizon, maximum
two skipped internal/trailing frames, and .01 image-diagonal edge/cost scales.
Retain candidate order and original indices, boxes, centers and confidence values.
The main comparator is saved `history_edge_tight_cost_tight` (TT/cap20); saved
`crop_top_one` is a descriptive reference, not a second newly executed arm.
Both controls use .01 and raw center radius 10 source pixels. No old control
selection, scoring, rendering package or human review is repeated.

## New score and deterministic algorithm

For a path with confidence sum C, node count n, internal skipped-frame count G,
normalized squared-motion sum N, and trailing age T:

```text
interpretive score = C/n - 0.25*G - 0.25*N - 0.25*T
```

Edge eligibility and edge cost follow `crop_motion_factorial.py`: for elapsed
frames dt in 1..3, permit distance <= .01*source_diagonal*dt; normalize distance
by the same denominator. Gap cost is .25*(dt-1), motion cost .25*normalized**2.
There is no clipping, confidence recalibration, interpolation or extrapolation.

The existing single-best-prefix recurrence cannot simply be reused with a
changing denominator. For each terminal node count n=1..horizon length, maintain
separate states `(n, endpoint, actual_node_count)`:

1. Initialize a singleton state to original confidence/n.
2. Extend an eligible edge in binary64, preserving the legacy operation order:
   `((parent_score + confidence/n) - gap_cost) - motion_cost`.
3. At the same state retain the highest stored score, then lexicographically
   smallest complete `(frame,index)` path on exact equality. Extend only to
   actual_node_count <= n. Use the original frame/candidate traversal order.
4. Only states with actual_node_count=n compete as completed paths. At each
   endpoint choose the highest stored score across n, then the lexicographically
   smallest complete path on exact equality. Subtract .25*T afterward.
5. Preserve the empty score-zero hypothesis and the existing global ordering:
   descending score; empty first on an exact tie; otherwise latest endpoint,
   higher endpoint confidence, lower original candidate index, then path order.
   Only a current-frame winning endpoint emits an observation. Earlier or empty
   winners stay missing; scores and margins remain uncalibrated heuristics.

This defines deterministic dynamic programming with fixed terminal path lengths,
not an exact-real-arithmetic optimizer. Do not claim exhaustive floating-point
tie equivalence: rounding can collapse unequal prefix scores during extension.
Store actual binary64 scores for selection, with original C,n,G,N,T and path
alongside them. Reconcile the interpretive formula at relative/absolute 1e-9
for arithmetic integrity only; never apply this tolerance to rankings or ties.
Do not introduce rational scoring or change the saved baseline arithmetic.

Retain an auditable trace of retained candidates, eligible edges, surviving
states and their chosen predecessors for each terminal n, completed endpoint
scores, winner, runner-up margin, emission/missing reason and source pointers.
One horizon has at most 100 nodes. All history is rebuilt from original candidates
inside the same window, never from future frames or the previous emitted choice.

## Exact access allowance requested

The companion JSON binds the committed retention proposal as an inventory
authority and copies only the named subset with its original expected hashes.
Preparation used metadata-only file sizes; no scientific body was read or hashed.

| Future worker inputs | Count | Bytes at preparation | Allowed phase |
| --- | ---: | ---: | --- |
| Saved RF-DETR crop-candidate runs | 6 | 50166803 | Selection, scoring, rendering |
| Saved TT and top-one observation wrappers at .01 | 12 | 34481821 | Post-selection comparison, rendering |
| Finalized development annotation files | 6 | 82211 | Scoring, rendering only |
| Saved motion scoring pools | 2 | 45044695 | Extract the 12 fixed .01/raw10 reports only |
| Bound unmarked source PNGs | 150 | 428952303 | Rendering only |

The requested access is 176 unique existing files, 558727833 bytes in total.
Only an owned monitored worker may verify their hashes and read their bodies.
Parsing/hashing a whole pool or wrapper does not authorize analysis of other
settings. Embedded pointers, source videos and old scientific manifests remain
inert. The inventory's source-video bindings are metadata, not decode permission.

Freeze and bind all six new selection outputs before the first annotation,
saved scoring report or pixel is opened. Selection sees candidate runs and
source metadata only. Later phases cannot revise these outputs. Use separate
phase functions/access allowlists; reject premature access rather than relying
on convention. New generated outputs can be read by later phases of this same
owned attempt after their create-only publication and hash binding.

The parent keeps scientific JSON bodies opaque and receives one verified bounded
return. Existing administrative ledgers, receipts, source and proposal metadata
remain readable. A narrowly requested future exception permits presenting only
the new verified review images/clips to Ryan after successful execution and
inspecting their layout. It does not allow reopening source-image files, reading
scientific JSON bodies, hashing media from the parent, or making human identity
judgments. No such exception is active during proposal preparation.

## Evaluation and human review

Run the existing raw-center evaluator on only the six new outputs, at .01/raw10.
Read saved controls' already scored reports; do not pass them through a loader
that reruns their selectors or evaluator. Verify expected file/content digests,
candidate namespace, window, config, annotation bindings and frame alignment.
Preserve old control provenance rather than relabelling it with a new commit.

Report each eligible frame in exactly one state: `matched`, `wrong_present`,
or `missing`. A wrong emission is already a missed eligible frame; do not add
it twice. Publish 3x3 paired transition counts and exact frame lists against
saved TT and against top-one, per window and per separate pool. Also publish
new per-window raw evaluator reports, counts with denominators, correct-run
lengths and longest missed-eligible runs. No pooled representative/challenge
score, new quality gate, significance claim or method ranking is requested.
Runs use consecutive original source frames within one window: `matched`
extends a correct run; `wrong_present` or `missing` extends a missed-eligible
run. Hidden/ineligible frames break both runs. Never concatenate windows or
pools; an absent run has length zero.

For the five hidden frames, separately show alarm versus no-current-output
transitions, never a fabricated center or raw-distance match. Report path-node
counts, current/older/empty endpoint choices and singleton emissions so apparent
gains cannot conceal increased missingness or loss of temporal support.

Retain a fixed diagnostic table for P003 frames 300,301,302,304,308,319,320,324.
Copy the completed human judgments only onto the originally reviewed emissions;
new choices have no inherited semantic identity. Human-recorded null indices
remain null, even if scientific indices are known. These eight rows are not an
evaluation denominator or an invitation to repeat their identity review.
Frame 300 must be unchanged because only singleton paths exist at startup;
also verify startup parity in every window. Display frame 304 and all six
history-dominated comparisons without assigning them a new causal verdict.
Include hidden frames 165-169 and final frame 174 in the new P003 challenge review.

Produce six new synchronized 25-frame clips at 5 fps, with panels for unmarked
source, saved TT, new mean arm and saved top-one. Supply native-resolution
overlays (source scale) for each arm/frame and an index to the exact changed
frames. Show candidate indices, frame index, floor/cap/score rule, missingness
and disclosed reference markings; do not present heuristic scores as probabilities.
Use only the bound PNGs, with no source-video decode or inference. Verify 25
frames, first/last indices, synchronization, native overlays and final panels.
Ryan reviews all six new clips through their final frames. This review evaluates
new outputs; prior six retention, twelve YOLO and eight candidate reviews remain
complete. No new identity-labeling or annotation study is implied.

## What counts as success

An informative completed experiment requires six frozen outputs, six new reports,
all 12 bound saved report comparisons, exact transition accounting, both separate
pools, bounded provenance, all six review packages and Ryan's final-frame review.
No positive accuracy result is required to preserve valid evidence as complete.

The proposal's favorable-development signal is deliberately conservative. Against
saved TT, require in EACH pool: matched eligible frames do not decrease,
wrong-present eligible frames do not increase, missing eligible frames do not
increase, and hidden-frame alarms do not increase; require at least one strict
localization or hidden-alarm improvement somewhere. Always disclose every exact
window-level regression, even when the pool criterion passes; call that outcome
"favorable pool totals with window regressions" rather than unqualified improvement.
Otherwise describe the result as unchanged, mixed or unfavorable. Never call
wrong-to-missing alone an improvement. Report top-one comparisons independently;
a TT gain that still trails top-one is not evidence that history adds value.

This signal is a rule for interpreting a development comparison, not a production
quality gate or automatic selection. Even a favorable signal requires the new
visual review and a separate decision before any deployment, parameter choice,
new experiment or holdout release. Localized centers do not certify ball identity.

## Execution, resource and preservation limits

Request one distinct unit `path-confidence-mean:study:`, at most one attempt and
1,200 charged seconds for loading, selection, scoring, rendering, verification
and publication combined. Use the existing cumulative balance
`10951.195000000016` seconds; reserve at most the smaller of it and 1,200.
This is a ceiling, not a runtime promise. No automatic scientific retry, fallback
algorithm, reduced scope or adopted partial result is permitted. A resource or
integrity failure preserves evidence and consumes the actual charged time/attempt.

Create only `audit/path_confidence_mean_v0_1/` beneath the existing retention
output root. Bound all new attempt outputs, audit shards, images, clips, logs
and temporary bytes to 4 GiB in aggregate (including new administrative attempt
files outside that subdirectory), within the existing 32 GiB whole-root limit.
Per-file caps and exact relative output names are in the companion scope.
The bounded parent summary is at most 512 KiB; the worker receipt remains at
most 1 MiB. Fail instead of truncating or dropping windows/frames.

Reuse the validated responsive monitor unchanged: .25-second requested polling,
one-second maximum completed safety interval, ten-second scan deadline, next
scan within five seconds, measurement age at most thirty seconds and one helper.
Keep 8 GiB combined sampled memory, worker/helper committed-memory limits
8 GiB/512 MiB, at least 50 GiB free disk, 8 KiB scan records, 64 KiB publication
reserve, initial/distinct final scans and owned cleanup. Keep charged time,
supervisor wall time and full command wall time separate. No GPU is required.

Preserve all 3,221 events through tip
`237f3149eada122733f339fb6e3a283c71c8d0e4bd619c54b814c5f2053e451a`, 62 closed
attempts, 58 successes and four historical failures. The latest successful
contrast and every earlier role remain consumed. Future release preparation
must preserve both the old 3,172-event frozen prefix and the successful suffix,
all nine human administrative records, the contrast outputs/receipt, original
raw-10 outcomes, nine embargoes and three sealed holdouts. Record scientific-file
preservation by allowed metadata and existing receipts; no parent body audit.

Reject existing targets and undeclared journal/output changes. Do not rebuild
ignored evidence or make old validators accept a new suffix. No player identity,
court calibration or empirical threshold changes; no player-pipeline
`--rerun-from` stage applies to this isolated experiment.

## Implementation, validation and approval boundary

If approved, add separate mean-selector, guarded orchestration, evaluation and
review support with artificial tests, leaving historical selectors, evaluator
semantics and the responsive monitor unchanged. Test fixed-terminal-length
prefix reversals, ordinary small-graph exhaustive oracles, declared floating-point
pruning/ties, normalization arithmetic, causal/cap boundaries, gaps/missingness,
all-window startup parity, saved-control copying, phase access isolation,
transition accounting, limits, immutable history and consumed-attempt refusal.

Run focused tests then the required full suite with bytecode disabled. Bound
artificial validation to 4,200 supervised seconds total including necessary
correction runs (each focused invocation <=600, full <=3,600), 8 GiB sampled
memory, 50 GiB minimum free disk and 4 GiB fresh validation artifacts/temporaries.
Account for any fixture outputs outside the fresh temporary directory explicitly;
do not label a partial disk measurement as total accounting. Artificial validation
does not spend the scientific allowance. Reuse completed monitor validation;
repeat only affected checks after a real correction. Ordinary tooling failures
may be fixed within scope; material evidence/resource/scope problems require
investigation. No tests or experiments are required to prepare this proposal.

Before real execution require passing artificial validation, independent code and
boundary review, a new exact implementation certificate, separately authorized
staging and committing, a verified clean descendant commit, fresh preservation
metadata and a create-only release checkpoint for this new unit. Do not rerun
or rewrite the completed contrast checkpoint for the documentation HEAD.

Approval of this exact proposal would authorize implementation, its artificial
validation, and one conditional execution plus the six new human review packages
within these limits. Staging, committing, pushing, PR creation and merging each
retain their separate authorization boundaries. Current preparation authorizes
none of those steps, no scientific reads, no implementation and no execution.
