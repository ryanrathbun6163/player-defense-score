# Candidate-retention published-bundle recovery proposal

Status: concrete amendment ready for explicit scope approval; not yet approved. This document authorizes no recovery
implementation, acceptance, finalization, audit execution or Git mutation.

## Problem and intended result

Five retention clips completed with successful resource receipts. The sixth,
P003 challenge frames 150–174, reached its final directory but its worker failed
before recording success. It remains an unreceipted publication, not a completed
comparison. The global review manifest and independent completion audit are absent.

The proposed recovery would validate that exact existing sixth bundle and, only
if it passes, create a new acceptance receipt. It would then finalize and audit
the six-clip package. It would not render any video again or change the monitor.
This is an explicit, narrow amendment to the existing no-adoption rule.

The original failed attempt, its null worker result, every old partial, and all
successful outputs remain unchanged. New validation would attest the files it
actually inspected; it would never rewrite the failed attempt as successful or
claim an unavailable pre-failure hash history for the sixth bundle.

## Verified starting checkpoint

- Branch: `codex/ball-detector-baseline`.
- Rendering commit: `cd51bfc1336bba76e4b118b6cfe55d7f74a3b5a6`.
- Failed attempt: `e3ea5536e59d4cdc8fea72d45bc53241`, 304.141 seconds.
- Failure: `Output tree did not stabilize for complete byte accounting`.
- Its canonical completion hash is
  `600dfd29a507d4443fa8275802183fe9f6fc5abc1c2e8c6658e307063e307d58`.
- The failure checkpoint contains 2,614 events and 49 completed attempts:
  46 successful, three failed. It consumed 2,822.664 active seconds, leaving
  11,577.336 seconds of the original allowance. A later supervised preservation
  diagnosis must extend, not replace, this checkpoint and its consumed time.
- There was no recorded time, memory or output-byte overshoot. Final byte
  accounting succeeded. Those facts do not prove what invalidated the earlier
  measurement.

The unchanged experiment root is
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/`.
The sole candidate for later acceptance is its existing directory
`review/windows/possession_003_frames_0150_0174_challenge_evaluation_development_v0_2/`.
The supervised preservation diagnosis subsequently passed. It verified the
24 selection manifests, 600 trace bindings, eight completed score artifacts,
ten old partial PNGs, other preserved failure evidence, bound development
inputs, and all five successful window manifests/assets. For the sixth it
recorded a current snapshot and internal asset-hash consistency only. No media
was decoded, no scientific scores were recomputed, and the sixth remains
unaccepted. Holdout contents were not accessed and all nine embargoes remain absent.

The final frozen checkpoint has **2,644 events, 50 completed attempts,
47 successes and three failures**. Diagnosis attempt
`d9a385de7da243e9b905e28a07936649` succeeded in 32.985 seconds.
Cumulative consumption is **2,855.649 seconds**; **11,544.351 seconds** remain.
There was no resource overshoot or final accounting error. Branch and HEAD
remain as above; the worktree is clean and the index empty.

Exact approval inputs (paths are relative to the repository root):

| Input | Path | SHA-256 |
| --- | --- | --- |
| Preservation receipt | `data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit/publication_preservation_audit_cd51.json` | `a400911f83b7408c6f9c5ddabf5eae47f704d9f73fed16f538ac135fc04d2106` |
| Full post-diagnosis checkpoint | `data/outputs/ball_tracking/crop_candidate_retention_render_recovery_implementation/cd51bfc1336b_2026-10-02/publication_diagnosis/checkpoint.json` | `ae72b7d729e342dd5123c49e27d027315cf18e9ccd29280210dfd1d81d74d356` |
| Separately reviewed ignored helper | `data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit/publication_preservation_audit_cd51.py` | `ae7497feb3d992bbebf0b5372d4d0f30a6cc9f420d444acd705ba4d0e295b3a8` |
| Successful diagnosis worker receipt | `data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/attempts/d9a385de7da243e9b905e28a07936649.result.json` | `a2e4f99d8609e4a27fc7570f1eac30f65af8e7135ff16b3041ee233dbf34cd27` |
| Sixth manifest, new unaccepted snapshot | `data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/review/windows/possession_003_frames_0150_0174_challenge_evaluation_development_v0_2/manifest.json` | `5665beabdbdcf7da2c3ad70f11a90095e14f251bf0c9ffe8bd284fcac2eaa29e` |

The checkpoint binds every event file, reservation/completion seal and existing
worker result through event 2,643, whose canonical chain tip is
`1287e985661c4b76ba3a680e299f916bd01977268547a7b550df84199bb48ecc`.
The preservation receipt binds all six manifests and their 301 assets each;
its sixth-window status is `new_snapshot_unreceipted_not_accepted`.
All four proposed result destinations below are bound absent, alongside the
older unexecuted comparison-completion audit destinations. The two proposed
new authority files are also absent. These bindings are required inputs to
any later approved implementation; they do not themselves grant acceptance.


## Diagnosis and limits

The current monitor already tracks actual file identities and hard-link counts.
A directory rename between completed scans preserves those identities. A rename
during traversal can invalidate an old path, however, discarding the scan pair.
Two fresh complete scans still have to finish before the original half-second
deadline. The existing rename tests publish between scans and do not cover a
late publication during traversal at the final output-tree scale.

Fabricated-file diagnostics used the unchanged production monitor:

- Controlled virtual-clock tests passed with no rename, between-scan rename,
  and an early interrupted scan; a late interrupted scan produced the same
  accounting error.
- Ten quiescent measurements over 5,323 fabricated files and 179 directories
  passed in 0.306–0.445 seconds each.
- One actual-time early publication recovered successfully in 0.323 seconds.
- One deliberately late publication, at file-stat call 5,022, reset the scan
  and triggered the monitor deadline. Separate `perf_counter` timing was
  0.488 seconds; the deadline uses `monotonic`. No delay was injected in this
  probe, and it was not retried.

These instrumented synthetic runs establish a possible failure mechanism, not
the actual real-run interleaving. Their file/directory counts match the observed
resource metadata, but their topology, payloads, cache state and workload are
fabricated. The byte-total checks do not establish full content identity.
Slow quiescent scans or scheduling delays can also produce the same error.

Evidence lives under
`data/outputs/ball_tracking/crop_candidate_retention_render_recovery_implementation/cd51bfc1336b_2026-10-02/publication_diagnosis/`:

| File | SHA-256 |
| --- | --- |
| `reproduce.py` | `fa64b7f332804f7ac525631c7dc01539217770c623dc38cb7d6c210096b95af6` |
| `receipt.json` | `b67716d95a87b849ed1cd29415dfc8c8767d37cb31d466aecd2973ef1f8bdeed` |
| `reproduce_late_order.py` | `8432bcdd8ba56c3c1a625deb7a07ffd47ddf002b3237a9bd1dfaef4db2efae37` |
| `late_order_receipt.json` | `0f3a85bf6412c35fe35a2793aa75ffb509e0973f45751f34bd17b7435709eee1` |

## Exact proposed recovery

Prepare a separate versioned authority and narrowly scoped runner after approval.
Keep the current rendering manifest, approval, certificate and runner unchanged.
The new runner may dispatch only verification, acceptance of the one bound
publication, global finalization, the separately reviewed completion audit,
and supervised presentation of the audited results.
It must have no renderer, selector, scorer, aggregation, inference, training or
directory-publication dispatch.

The new authority paths are
`configs/ball_tracking/crop_retention_experiments/rfdetr_medium_crop_candidate_retention_publication_recovery_v0_1.json`
and
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_publication_recovery_approval_v0_1.json`.
No other input window or acceptance target is permitted. All new result paths
below are relative to the unchanged experiment root and must be absent before
their first attempt; never overwrite an existing file:

| Purpose | Exact result path |
| --- | --- |
| Sixth-bundle acceptance | `audit/publication_acceptance_cd51.json` |
| Versioned global review manifest | `review/manifest.json` |
| Independent comparison-completion audit | `audit/independent_publication_recovery_audit.json` |
| Audited summary and six-clip guide | `audit/publication_recovery_review_guide.md` |

These absent destinations are bound in the preservation checkpoint above. New helper
sources and their final hashes must be separately reviewed and recorded before
execution; helper source is not evidence of an executed audit or acceptance.

1. Verify the exact approved authority, clean tested commit, full preserved
   journal and seals, three known failures, five successful render receipts,
   completed selections/scores, and diagnostic snapshot. Refuse any changed
   binding, unexpected target, new failure or unfinished attempt.
2. Independently validate the sixth bundle against that frozen snapshot and
   its original sources. Check the exact 301 assets plus manifest, frame
   coverage/order, dimensions, confidence .01/radius 10, four paired motion
   rows, explicit missingness, original candidate/report/annotation bindings,
   all asset hashes and valid PNG contents, and decode its video through all
   25 frames at 5 fps including the final frame. Do not rematch or rescore.
3. Create a separate acceptance document and successful supervised completion
   receipt only after every required check passes. Record original rendering
   commit/specification and failed attempt separately from the actual new
   validation commit/specification and current validated artifact hashes.
   A published acceptance document without its successful completion receipt
   cannot authorize continuation. Never backfill the old failed worker result.
4. Finalize the global manifest using exactly five original success receipts
   plus the new acceptance receipt. Preserve all six old window headers and
   assets. Use an explicit versioned global schema that separates original
   rendering from the new finalization/acceptance provenance.
5. Run a new, separately reviewed independent completion helper under the same
   supervisor and remaining budget. It must bind all old selection/scoring
   identities, five renderer successes, the sixth failure and new acceptance,
   every resource seal, exact assets, unchanged copied score arithmetic and
   pool/alias separation, and all six clips through their final frames.
   Preserve all earlier comparison-completion helpers and their unexecuted
   status. Preserve the truthful completed status of earlier forensic and
   preservation audits.
6. Only after that audit passes, provide the six new retention clips for Ryan's
   final-frame review and summarize the existing representative/challenge
   results separately. Use a supervised presentation worker to read the passed
   audit and create the exact guide above, with separate helper/input/output
   provenance. Copy audited results with transparent formatting/arithmetic only;
   do not rematch, recompute scores or perform new scientific aggregation.
   Parent code may open/link the guide without reopening scientific bodies.
   Earlier twelve YOLO reviews remain complete.

Any failed validation, changed file, missing receipt, incomplete worker or
resource error stops the sequence. There is no fallback adoption, overwrite,
rerender or automatic retry. A failed acceptance attempt does not authorize
changing the acceptance criteria.

## Unchanged limits and exclusions

Use the same root and persistent budget: one worker tree, 8 GiB combined resident
memory, 32 GiB total output, at least 10 GiB free disk, four cumulative active
worker hours, monitoring at least once per second and between stages, and the
same half-second two-complete-scan inventory rule. Keep the original selection
unit limit. All verification, failed work and acceptance/audit time is charged.
No evidence deletion, root replacement, budget reset or relaxed measurement is
included. Quiescent synthetic success does not guarantee future measurements.

All scientific file reading, hashing and media decoding remains supervised.
Parent operations stay limited to source, authority, certificate, Git and resource
metadata. The nine embargo paths must remain absent; the three holdouts remain
metadata-only. No labels, boxes, centers, confidence thresholds, graph rules,
player identities or calibration decisions change. No method, operating point,
quality gate, training plan or certified object-identity label is selected.

Coordinating future directory publication with resource scans may merit a later
engineering change. It is outside this proposal: the current recovery can finish
without publishing or rerendering any window directory.

## Validation and authorization boundary

Before execution, require focused synthetic tests, the full project suite with
bytecode disabled, independent source/helper review, exact source/evidence
bindings and a clean separately authorized implementation commit. Tests must
cover the exact three-failure history, successful-five/unreceipted-sixth boundary,
tampering/missing/extra assets, wrong provenance, invalid/truncated final frames,
failure before/after acceptance publication, preserved old bytes and no forbidden
dispatch. They must prove that neither manifest presence nor an unreceipted
acceptance result can silently authorize reuse. Exercise the frozen resource
rules without using real scientific outputs as test fixtures.

Implementation scope should be restricted to new recovery authority/configuration,
runner/finalization support, new synthetic tests, a new independently reviewed
audit helper and compact documentation. Existing selection/scoring/rendering and
resource-monitor behavior must remain unchanged. Bind actual final source and
helper hashes after implementation; do not invent a future commit identity.

Ryan's “please move forward chat” authorized the diagnosis following the recorded
failure. Accepting a published bundle without an original successful worker
receipt changes the approved execution contract. That requires explicit approval
of this concrete amendment. Approval would cover its bounded implementation and
later execution subject to the validation requirements above. Staging, committing,
pushing, PR creation and merging each still require separate authorization.

The existing approved rule is in `docs/ball_crop_candidate_retention_render_recovery_proposal.md`, lines 138–143: “A final review target without a successful resource-completion receipt cannot be adopted or overwritten.” This proposal changes only that boundary for the one snapshot-bound sixth bundle after successful independent validation; all other exclusions and stop conditions continue to apply.
