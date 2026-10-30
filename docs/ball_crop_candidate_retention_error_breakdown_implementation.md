# Saved error-breakdown implementation

Ryan approved the exact proposal with "Yes I permit. Move forward".
The separate receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_error_breakdown_approval_v0_1.json`,
SHA-256 `f0eb74cde6077a5741c46ebe1aa1f8633ed2ac031f8b3a5f493d417ca9a2a0cf`.
The proposal remains frozen at SHA-256
`f8525927fa5589b7c5a70aef6fee9bcc813365e267503eaa4f6610438802deee`.
Its historical draft status is superseded by the separate approval record.

## Scope and purpose

This implementation prepares one supervised reading of the two existing scoring
pools and passed independent audit. It explains the saved missing-candidate,
confidence-filter, candidate-cap and path-selection categories at .01 confidence
and 10 source-image pixels. All six windows, four settings and both cap policies
remain in the report. Per-row counts are lengths of saved lists, not a rerun of
matching or scoring. No pool totals or new rates are introduced.

The separate pure formatter is
`src/ball_tracking/crop_retention_error_breakdown_summary.py`; the runner is
`src/ball_tracking/crop_retention_error_breakdown.py`. The formatter receives
objects without filesystem access. The runner restricts real scientific reads
to its worker, processes the large pools sequentially, and returns only the
bounded readable summary after successful completion and receipt validation.

The output is diagnostic: a retained near-reference candidate does not establish
object identity, and failure to localize does not establish physical ball
absence. The new report cannot resolve object identity versus center placement.
It does not select a tracker, operating point or quality gate.

## Preservation and resource limits

Preparation verified the completed interpretation's source/authority metadata,
full resource receipt chain and file metadata before freezing the new prefix.
No scientific body was reopened. The new frozen history has SHA-256
`b765b13e8e76daa9d6108d5a82b5d3e589c93b76415fc97a75054ba8fb0238cf` and records
5,762 existing files, 188 directories, all 3,002 events and 57 closed attempts.
The original three failed attempts remain failed and their result paths absent.
All eighteen completed clip reviews, nine embargoes and three sealed holdouts
remain preserved. The original 147 tracked source/test/dependency files were
separately snapshotted for preservation.

Evidence for this implementation belongs under
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_implementation/e71a4d216562_2026-10-02/`.
The real experiment root and supervisor remain unchanged. The new non-selection
role is `post-review-error-breakdown:summary:`, with a 300-second maximum within
the original cumulative budget. Preserve the existing one-worker, 8 GiB memory,
32 GiB whole-root, 10 GiB free-disk and monitoring/accounting limits. The tighter
reservation is not a completion estimate. No retries or output adoption.

Real outputs remain create-only under the original root's
`audit/post_review_error_breakdown_v0_1/`: `breakdown.json`, `summary.md` and
`provenance.json`. The readable summary is at most 64 KiB. Raw inputs, source
media, annotation bodies, candidate files and traces remain outside the allowed
scientific input set. Existing authorities and evidence are not rewritten.

## Validation status

Implementation and independent source review are complete. All 46 fabricated
focused checks passed in 72.28 unittest seconds, with no skips and unchanged
source/helper/recorder bindings. The actual metadata-only dry-run passed in
15.047 seconds without opening scientific bodies or starting a worker. The
full suite completed successfully: 804 tests run, 803 passed and one existing
Windows directory-symlink skip. Unittest time was 2,040.214 seconds; command wall
time was 2,044.594 seconds (about 34 minutes). No real diagnostic worker has
started.

Focused checks preceded the full suite. The new create-only validation recorder
passed twelve checks, recognized the unique successful unittest result block
and the known optional trailing diagnostic messages, and preserved the actual
exit-zero result. Both runs used bytecode-disabled Python and short ignored
Windows temporary paths. All 151 source/test/dependency bindings and the three
prior helper bindings stayed unchanged, including all 147 prior tracked files.

The completed certificate is `implementation_validation.json` in the evidence
directory above, SHA-256
`c252a3015acd0cc037ac084db8f6a09589f0d41a23d28e2d18312b0be58ca233`.
The manifest now binds that exact certificate. It records the independent
reviews, test receipts, preserved sources and exact approved authorities.
Implementation and validation are complete; separately authorized Git staging
and committing are next. Stop on any new failure without retry.

## Intended Git scope

Branch: `codex/ball-detector-baseline`. Implementation base:
`e71a4d2165623208d624c4839e9321bd9bf779ba`. These eleven files are the intended
scope; this list is not permission to stage or commit them:

1. `configs/ball_tracking/crop_retention_experiments/rfdetr_medium_crop_candidate_retention_error_breakdown_v0_1.json`
2. `configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_error_breakdown_approval_v0_1.json`
3. `docs/ball_crop_candidate_retention_error_breakdown_proposal.md`
4. `docs/ball_crop_candidate_retention_error_breakdown_implementation.md`
5. `docs/context/current_state.md`
6. `docs/context/roadmap.md`
7. `docs/context/validation_history.md`
8. `src/ball_tracking/crop_retention_error_breakdown.py`
9. `src/ball_tracking/crop_retention_error_breakdown_summary.py`
10. `tests/test_ball_crop_retention_error_breakdown.py`
11. `tests/test_ball_crop_retention_error_breakdown_summary.py`

Generated metadata, logs, certificates and results stay ignored. Real execution
requires a validated clean checkpoint following separately authorized staging
and committing. Push, PR creation and merge remain separate decisions.
