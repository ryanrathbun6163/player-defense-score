# Candidate-retention publication recovery implementation

This recovery validates the existing P003 challenge bundle (frames 150–174),
whose renderer published its directory before failing during resource accounting.
Five other windows have successful renderer receipts. Selection and scoring are
complete; the six-window comparison and human review remain incomplete.

Ryan approved the exact proposal in
`docs/ball_crop_candidate_retention_publication_recovery_proposal.md`.
The separate approval JSON records that decision and its limits. The proposal
copy retains the exact bytes presented for approval, including its historical
pre-approval status. Neither that approval nor this implementation authorizes
staging, committing, pushing, a pull request or a merge.

## Execution contract

The new module is `src.ball_tracking.crop_retention_publication_recovery`.
Its versioned manifest is
`configs/ball_tracking/crop_retention_experiments/rfdetr_medium_crop_candidate_retention_publication_recovery_v0_1.json`.

| Stage | Purpose | New artifact under the original experiment root |
| --- | --- | --- |
| Preflight | Verify frozen evidence, history, current source and authority | Successful worker receipt only |
| Acceptance | Validate the exact sixth bundle, all 300 PNGs and all 25 video frames | `audit/publication_acceptance_cd51.json` |
| Finalization | Bind five original renderer successes and the new acceptance success | `review/manifest.json` |
| Independent audit | Check preserved evidence, score arithmetic and all six videos | `audit/independent_publication_recovery_audit.json` |
| Presentation | Copy audited results and final-frame links for human review | `audit/publication_recovery_review_guide.md` |

The CLI accepts `--stage verify` or `--stage recover`. `--dry-run` checks
metadata only; it does not validate scientific outputs or authorize execution.
Real execution requires the exact validation certificate and a clean, separately
authorized implementation commit descended from `cd51bfc1336bba76e4b118b6cfe55d7f74a3b5a6`.

Every stage runs in the unchanged resource supervisor. A published output alone
never authorizes the next stage: its successful completion receipt is required.
The original failed attempt stays failed, with no backfilled worker result.
The old rendering runner remains unchanged and must not be retried against this
new failure history. There is no rerendering, selection, scoring, inference,
training or resource-monitor change in this implementation.

## Preservation and provenance

The approved starting checkpoint contains 2,644 resource events and 50 completed
attempts: 47 successes and three failures. The ignored preservation receipt binds
24 selection manifests, 600 trace shards, eight score artifacts, ten old partial
PNGs, original failure evidence, scientific inputs and all six window bundles.
For the sixth bundle it records a current snapshot, not historical success.

All six existing window headers keep their actual renderer commit and
specification. The new acceptance and global manifest separately identify the
new validator/finalizer commit and specification. Ignored independent helper
source has its own certificate hashes and is not attributed to the Git commit.
The independent audit reuses selected hash-bound legacy validation functions;
the legacy completion entry points remain unexecuted.

All scientific reads, hashes and media decoding are supervised. The three
holdouts remain metadata-only and all nine original embargo paths remain absent.
Earlier twelve YOLO final-frame reviews are complete. Only the six new retention
clips will need human review after the completion audit succeeds.

## Runtime allowance

The original experiment permits four cumulative hours of supervised worker
runtime. Failed attempts, preflight, verification, acceptance, audit and
presentation all consume that same allowance. Conversation, idle gaps, human
review and separately recorded synthetic validation do not consume it.

At the approved checkpoint, 2,855.649 seconds had been consumed and 11,544.351
seconds remained (about 3 hours 12 minutes). That is a remaining resource
allowance, not an estimate of task duration. The same one-worker, memory, output,
free-disk and monitoring limits remain in force. A new failure stops the sequence
without automatic retry, deletion, overwrite or relaxation.

Focused synthetic tests precede the full suite. The ignored implementation
certificate binds the final source, helper hashes, test logs and independent
review. Preparing these checks does not mean a real acceptance or audit ran.
