# Proposed split of saved final-output losses

Status: concrete proposal, prepared after Ryan's "move forward chat". That
instruction authorizes this planning step. Implementation, the new derived
diagnostic and any new scientific-body access below await approval. The previous
recovery is complete and its one attempt is consumed. No Git permission follows
from this proposal.

## Question and smallest useful scope

For each saved `S_path_choice_loss` frame, did the selector emit no current
observation, or emit an observation that failed the existing localization rule?
Answer for every one of the same 48 rows: six development windows, TT/TW/WT/WW,
cap20/all, confidence .01 and raw radius 10 source-image pixels. Keep the two
pools separate and retain empty rows and their original execution roles.

The completed breakdown already contains enough information for this split.
There is no need to reopen its large evaluation pools, selection observations,
candidate lists, annotations, traces or media. This is a new derivation of saved
memberships, not new detector performance, scoring or independent trials.

It will not distinguish wrong-object output from inaccurate ball-center
placement. The completed human-review record explicitly says
`frame_specific_verdicts_provided=false` and `new_object_identity_labels=false`.
Package approval cannot be converted into per-frame semantic labels. Preserve
that review and all twelve earlier YOLO reviews without requesting them again.

## Why the split is identifiable

The following source contracts hold at current commit
`de134d942767b70dfc6da360745f50405a8b3f8d`. All four relevant Git blobs were
compared with original scoring commit
`f36237247191e726ad7e81bdc6651f9340a9063d` and are unchanged.

1. `crop_retention_evaluation.loss_partition` defines S as retained matching
   availability minus selected matches, reconciles all four categories to saved
   eligible misses, and records eligible false-observation frame memberships.
2. `evaluation.evaluate_detections` records a false negative for an unmatched
   eligible frame and sets its false-positive count to the accepted output count.
3. The cap20 history arms in `crop_motion_factorial` emit at most one original
   candidate at the configured confidence threshold. A winning earlier endpoint
   produces no current observation. `crop_motion_evaluation` scores those
   emissions at the same threshold.
4. The all-policy validator in `crop_retention_evaluation` likewise requires
   zero or one original candidate at confidence at least .01, from the current
   endpoint, and evaluates it at .01.

Therefore, within S, an eligible false-observation membership means one current
output that failed localization. Its absence means no current emitted output.
There is no emitted-but-below-threshold exception for these exact motion rows.
This proof does not extend to raw/multiple-output controls or other settings.

The completed formatter copied S and the eligible false-observation lists
without changing them. Its schema and source map preserve their row identity.
The new implementation must bind these source contracts and refuse unsupported
schemas, settings or authority; it must not infer missing fields as empty lists.

## One scientific input, worker-only

Let `R` mean the existing ignored experiment root:
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/`.

The only proposed scientific input is:

| Path relative to R | Bytes | SHA-256 |
| --- | ---: | --- |
| `audit/post_review_error_breakdown_recovery_v0_1/breakdown.json` | 744235 | `05b6ea6091ebeada1857b85016c2510f9d65349596f61cd208514c2a31252b32` |

These are copied administrative bindings, not a new parent scientific hash.
Authority is successful recovery attempt `05fe00c14f224c5abfc2cc6008e90f96`:
its worker receipt is `R/attempts/05fe00c14f224c5abfc2cc6008e90f96.result.json`,
SHA-256 `c058335ee3d8a1301c6db55bedd83311cb07031d8fcdc1a8d5b9520fb0caa6d5`.
Its size metadata, successful completion seal, returned transport and new
completion record under `data/outputs/t/ebri_fa730bcb6d2e/` establish the input's
provenance. Completion event `R/resource_events/00003070.json` has chain tip
`d800b77b4db2128d1baa09db59538ab6f16d4aad6d96aaa7a9fd84f96c11bf92`.

Only the owned worker may open/hash this scientific file, before and after use.
Validate the complete `ball_crop_retention_post_review_error_breakdown/v0.1`
structure, both extracted pools and their content digests, all 48 unique rows,
copied source mappings, settings, original roles and null decisions. Existing
pure extraction validators may be reused with supplied objects. Do not invoke
the original runners or loaders that follow pool, label, candidate or trace
bindings. All copied scientific source pointers remain inert.

The parent may verify administrative source/approval/certificate/receipt records
and preserved filesystem metadata. It may receive the successfully verified
bounded summary; it may not reopen/hash the scientific input or output bodies.
This proposal does not extend access to any other scientific body or holdout.

## Exact new operation and output

For each input `/pools/{p}/rows/{r}`, define S as the saved
`parts/S_path_choice_loss` list and E as the saved
`false_observations_on_eligible_frames` list. Preserve S order:

```text
missing_current_output = [frame in S where frame is not in E]
present_nonmatching_current_output = [frame in S where frame is in E]
```

Approval must explicitly permit these within-row ordered difference/intersection
operations and the lengths of their two resulting lists. The old authorization
allowed copying lists and their own lengths; it did not permit this new split.
Reconciliation may verify that every S member appears in exactly one new list,
both new counts sum to the original S count, and each list preserves source
order. This adds no pool totals, rates, rankings, cross-row unions or tests of
statistical significance. False observations outside S and hidden alarms are
not folded into the new categories.

Preserve both pools, all original rows, fields, lists, counts, source pointers
and roles without edits. Store the two new lists/counts in a separate derived
section keyed by the exact input row pointer. Add source-map entries identifying
both operand pointers and `ordered_difference`, `ordered_intersection` and
`list_length` operations. Explicitly record that a new membership derivation
occurred; do not mislabel the new operation as an unchanged copied metric.

New schema: `ball_crop_retention_output_presence/v0.1`. Create only:

- `R/audit/post_review_output_presence_v0_1/presence.json`;
- `R/audit/post_review_output_presence_v0_1/summary.md`, at most 65,536 UTF-8 bytes;
- `R/audit/post_review_output_presence_v0_1/provenance.json`.

The readable summary must show all 48 rows, including empty lists, with both
new categories, counts and original row identity. Fail rather than truncate.
The worker verifies its outputs and binds them to the successful receipt.
The parent receives only the bounded verified summary after sealed completion,
final accounting, cleanup and preservation checks. Partial outputs remain
unaccepted evidence. All paths are create-only and stay ignored.

## Execution envelope and preservation

Proposed new unit: `post-review-output-presence:summary:`, at most one attempt,
with a fresh maximum of 120 charged seconds deducted from the existing remaining
cumulative allowance of `11079.945000000014` seconds. The actual reservation is
the smaller of those values. This requests a new question-specific allocation;
it does not renew the consumed recovery attempt or spend its arithmetic role
remainder of `240.18800000001647` seconds. The limit is not a runtime estimate.

Explicitly adopt the already validated responsive monitor for this new unit:
0.25-second requested polling, one-second maximum completed safety interval,
ten seconds per full scan request, a new request within five seconds of accepted
completion, maximum measurement age thirty seconds, and one accounting helper.
Keep 8 GiB combined sampled RAM, worker/helper committed-memory limits of
8 GiB/512 MiB, at least 50 GiB free disk, the existing 32 GiB whole-root bound,
8 KiB scan records, 1 MiB worker receipts and the 64 KiB publication reserve.
Mandatory initial and distinct post-shutdown accounting remain; charged time
and finalization/external wall time are reported separately.

Preserve the complete now-closed 3,071-event prefix through the successful
recovery, including all four historical failures, old approvals and outputs.
Before dispatch, verify that exact prefix and freeze current allowed metadata;
only the new declared unit may append. Reject unknown suffixes, prior attempts,
unreceipted files or an existing target directory. No automatic scientific
retry, root replacement, budget reset or adoption of partial output is allowed.
Original prediction embargoes, all three sealed holdouts, six retention reviews,
twelve YOLO reviews and reviewed player/court decisions remain unchanged.

## Implementation, validation and approval

After explicit approval, add a separate minimal reader/runner and focused tests,
plus versioned proposal approval and manifest. Reuse the monitor and pure
validators; preserve the existing recovery runner, formatter, manifests,
certificates and execution checkpoint. No upstream stage is invalidated.

Synthetic cases must cover empty S, all-missing/all-present/mixed lists,
false-observation members outside S, overlapping memberships across distinct
rows, hidden-frame separation, missing/malformed fields, reordered/duplicate
rows, both policies, provenance mismatch, forbidden file access, bounded return,
failed publication, exhausted budget and attempt/prefix guards. Test against
fabricated data only. Independent source review, focused tests, then the full
suite with bytecode disabled and `git diff --check` precede release. Reuse the
completed monitor design check; do not repeat its large fixture or benchmarks.
Ordinary implementation/tooling failures may be corrected within approved scope
under Ryan's latest failure policy; preserve evidence and rerun affected checks.
Material evidence/resource/scope failures require investigation. A consumed real
attempt cannot be retried automatically.

A new implementation certificate must cover the resulting source inventory.
Staging and committing remain separate approvals. Only after the separately
authorized validated clean commit may a new create-only execution checkpoint
activate this one unit. Do not overwrite the completed recovery's certificate
or checkpoint to make the new reader pass an old release gate.

Approval requested: implementation, synthetic/full validation, and one conditional
supervised derivation from the single bound input, within this exact envelope.
No new model inference, scoring, selection, media rendering, training, threshold
choice, method choice, quality gate, holdout release or Git step is included.

## Remaining semantic question

`present_nonmatching_current_output` means an emitted original candidate failed
the saved raw 10-pixel rule. It is not a wrong-object label. This input supplies
no emitted candidate identity, coordinates, error magnitude, missing-output
reason or causal explanation. Preserve those fields as unknown, not guessed.

Separating wrong-object from ball-center placement would require new,
frame-specific evidence tied to the emitted candidate and an explicit semantic
judgment with uncertainty. The existing review receipt does not provide it.
If that distinction is still needed after this result, propose a separately
bounded adjudication scope and obtain explicit authorization; do not reopen
completed clip approvals or silently request another full visual review. This
proposal requests no such adjudication and creates no semantic training labels.
