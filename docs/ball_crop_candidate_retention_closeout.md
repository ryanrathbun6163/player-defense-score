# Candidate-retention comparison: execution and visual-review closeout

The approved six-window candidate-retention comparison has completed selection,
scoring, rendering recovery, independent audit and Ryan's requested final-frame
visual review. The next step is to interpret the saved audited results before
proposing another experiment. Completion of this review does not select a
tracker, operating point or ball-tracking quality gate.

## Human review

Ryan responded to the six-new-clip final-frame review request:

> I approve and have reviewed everything’s looking pretty good. Move forward chat

The separate receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_visual_review_record_v0_1.json`,
SHA-256 `9a3089a14747dce7b95670838dd116b2ddaf6cd426837f93435ff6ad6706d46b`.
It records package-level completion and approval without inventing frame-specific
correctness judgments, new object-identity labels or separate native-image
attestations. The earlier twelve YOLO reviews remain complete.

The six reviewed windows are P001 50–74 and 200–224; P002 250–274 and
25–49; P003 300–324 and 150–174. Each clip contains 25 frames at 5 fps,
comparing saved cap20 with all qualified candidates at confidence .01 and
display radius 10, across TT, TW, WT and WW. Their existing manifests and
the review guide retain their historical pending-review fields. The new
receipt supplies the later human decision without rewriting those snapshots.

## Execution and provenance

Publication recovery was separately staged and committed at
`a89cd40838b066c1d2fe3cb1f257dda10e80a3bb` on
`codex/ball-detector-baseline`. The commit contains exactly the seven approved
implementation files. The original rendering commit remains
`cd51bfc1336bba76e4b118b6cfe55d7f74a3b5a6`; original selection and scoring
identities remain separate and unchanged.

Five windows have original successful renderer receipts. The sixth, P003
150–174, has a new independent acceptance receipt for its existing bundle.
Its original failed render attempt `e3ea5536e59d4cdc8fea72d45bc53241` remains
failed with no backfilled result. Acceptance, global finalization, completion
audit and presentation each have their own successful supervised receipt.
No selection, scoring, rendering, inference or training was repeated during
publication recovery.

Evidence under
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/`:

| Artifact | SHA-256 from its successful worker receipt |
| --- | --- |
| `audit/publication_acceptance_cd51.json` | `5ef095793f64b752b887cf228187cb734ab2bc440fb3c3f734778a91cf2b754a` |
| `review/manifest.json` | `20b12bb750b158a6428b6a2c61051b11ebf81a86b45426fcf810928b1fc14b24` |
| `audit/independent_publication_recovery_audit.json` | `a1c944c3e1a5184ff08986adacbb2e623d515a67b33a67a55075dcc3f5fc5da2` |
| `audit/publication_recovery_review_guide.md` | `2a45db2ecfd5f60c3bbe1e4262ff8106bf2a496aa2de57ee9ba3b083131cc867` |

The completed execution checkpoint is
`data/outputs/ball_tracking/crop_candidate_retention_publication_recovery_implementation/cd51bfc1336b_2026-10-02/recovery_completion_checkpoint.json`,
SHA-256 `03ddbd6151b3827afaf98070a5c8ed745f9ccd05b582b84d0c23ab8f0417e7d0`.
It records successful recovery before Ryan's later visual approval; its pending
human-review status is historical. This closeout uses existing supervised
receipts and source/authority/resource metadata. It does not claim a fresh
scientific rehash, media decode or numerical interpretation.

## Validation and resource accounting

Focused tests passed: 38 runner tests and 13 helper tests. The full suite ran
716 tests in 1,873.376 seconds: 715 passed and one existing Windows
directory-symlink capability test was skipped. All 143 source/test/dependency
bindings and three helper bindings stayed unchanged. Independent source review,
the implementation certificate and the clean execution checkpoint passed.
This documentation-only closeout does not change that tested implementation.

The original journal now contains 2,966 events and 56 completed attempts:
53 successful and three preserved failures, with no active worker. All six
publication-recovery workers succeeded. Its canonical tip is
`018a97a3075f46698e215c3f6e8e95cab7cbab4f926e9bad68dbbd25d6c0640e`.
Original cumulative usage is 3,220.103 seconds, leaving 11,179.897 seconds
(3 hours 6 minutes 20 seconds, rounded). Human review and this metadata/document
closeout add no real worker time. The original resource limits and failure
evidence remain unchanged.

All nine original prediction embargo paths remain absent. P001 300–324,
P002 200–224 and P003 250–274 remain sealed and metadata-only. Reviewed player
identities and court calibration are unchanged. No upstream rerun is needed.

## Next step

See `ball_crop_candidate_retention_interpretation_proposal.md` for the concrete
bounded interpretation scope. It would consume only the already-produced guide
and passed audit under supervision, return a bounded summary for discussion,
and identify the next research question without executing another experiment.
It must preserve separate representative/challenge pools, matched-confidence
cap contrasts, gains and regressions, missing observations and hidden alarms.

The current recovery runner has finished all its approved destinations. Do not
rerun it to obtain another interpretation, reopen raw reports/traces/media in
parent code, or request any of the completed clip reviews again. The additional
interpretation scope needs its own explicit approval under the existing
scientific-reading boundary. No tracker choice, tuning, quality gate, training,
new experiment, holdout release or future Git mutation is authorized by this
visual-review receipt. Closeout edits remain unstaged with an empty index.
