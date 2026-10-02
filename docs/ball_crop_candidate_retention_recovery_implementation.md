# Candidate-retention recovery implementation

Ryan approved the bounded recovery with "I approve chat. Please move forward".
The separate approval record is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_recovery_approval_v0_1.json`.
The approved recovery proposal retains its original bytes and historical draft
status; the approval record supplies the current authorization. Its SHA-256 is
`c066bc43b204a09a05e2912589cbc173614cecbe563431ebbeed75c42db3de48`.

Implementation is validated on `codex/ball-detector-baseline`, based on
`0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41`. The recovery is not yet committed or
executed. The original 24 successful selections, 600 trace shards, failed
scoring attempt and incomplete JSON remain preserved. Scoring and rendering
remain incomplete; no tracking-quality conclusion follows from this repair.

## Correction and reuse contract

The resource monitor now compares complete file-identity and hard-link-count
inventories while allowing file sizes and modification times to change. It
charges the largest observed size per identity across two matching inventories,
including each hard-link entry. This is conservative over observed sizes, not
an instantaneous bound on subsequent growth. The half-second scan deadline is
checked during traversal and before accepting a sample. Unresolved membership,
missed monitoring cadence and exceeded resource limits still stop the worker.

All original limits remain: one worker tree, 8 GiB resident memory, 32 GiB for
the entire existing output root, 10 GiB minimum free disk, 30 minutes per
selection unit and four cumulative active worker hours. Failed attempts and
read-only verification remain charged; the failed partial stays in place.

The new recovery entry point accepts only verification, scoring and rendering.
It checks an exact allowlist of 24 original selections and 600 traces against
the successful worker receipts and the pinned interruption evidence. Original
ranking provenance stays at `0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41`; later
evaluation and rendering will record their actual new committed checkpoint.
The original runner's same-specification and same-commit guards are unchanged.
The scoring and review modules accept an explicit recovery loader, with their
original behavior retained by default. No ranking algorithm, candidate center,
confidence, annotation or matching rule changes.

Published outputs require successful completion receipts. A final filename
without a receipt, an altered selection or partial, or a missing journal record
is rejected. Completed scores are read and verified rather than reevaluated.
A narrowly bound completion-audit receipt can be checked during later recovery
verification; it cannot authorize a selection or arbitrary scientific output.

## Preserved evidence and preparation

The new executable manifest is
`configs/ball_tracking/crop_retention_experiments/rfdetr_medium_crop_candidate_retention_recovery_v0_1.json`.
Its preserved inventory is
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/recovery_preparation/preserved_inventory.json`,
SHA-256 `5a05c6644196f7fd0dfb731c538f68077039f74265d62e7b95f3dbbe00b92739`.
It binds all 24 original manifests, 600 trace hashes, original source bindings,
the exact failed partial and 697 resource events covering 29 complete attempts.

The additional preparation worker used the immutable resource module from
the original commit, separately hashed as an ignored snapshot. It reverified
saved bytes without selection, scoring, rendering, model calls or video decode.
Attempt `692ee366897d410ca5ca7357ce80aa73` succeeded in 1.75 seconds, with
completion-event hash
`66e0c9662ffff0c906beefe711ceef3e2eb181bbb98a1bd9b66452f3791584d7`.
The recorded real-run balance is now 621.943 seconds consumed and 13,778.057
seconds remaining. The persistent journal remains authoritative.

The original interruption receipt remains
`audit/interruption_receipt.json` under that run root, SHA-256
`0f90a59c07dd2436ef8618ffd8d3637695b99ab3e56e08f879866d9d702e40df`.
The earlier independent completion helper remains unexecuted and unchanged.
A separate recovery-aware helper was prepared and passed independent static
review. Its SHA-256 is
`3c30f23ab95a340c0b4244c01bc2327ca1c1533ab4bbbff58db8c0b21286b337`.
It remains unexecuted; preparing it does not certify a completed comparison
or human review.

## Validation checkpoint

Validation is complete. Evidence is recorded create-only under
`data/outputs/ball_tracking/crop_candidate_retention_recovery_implementation/0a7f5bc69be9_2026-10-02/`.
The actual recovery command rejected the dirty checkout before starting a
worker or changing the journal. Synthetic tests cover the monitor correction,
exact historical reuse, old/new provenance, unreceipted output rejection and
scoring/review integration. All 107 combined focused tests passed in 101.25
seconds with the 137 source/test/dependency files unchanged.

The first full run attempted 627 tests: 621 passed, five errored during setup,
and one existing Windows directory-symlink test was skipped. The five errors
were in the unchanged development-release test module: the validation harness's
deep temporary path caused Git to reject a fixture filename as too long.
Independent reproduction confirmed the same setup succeeds under a short path.
The raw failed log and receipt remain preserved; the old receipt's skip parser
reported zero because it only recognized successful summaries, while the raw
log correctly records one skip. No production or test file was changed.

The entire affected 14-test module then passed in 40.031 seconds with a short,
ignored temporary directory. The full retry using `data/outputs/t/crr_full_short`
passed: 627 tests run, 626 passed and the one existing Windows directory-symlink
skip; no errors or failures. It took 1,824.921 seconds overall (1,823.343 seconds
reported by unittest). All 137 source/test/dependency hashes remained identical
across both full attempts and the focused validation. No code or test changes
were needed between those runs.

The successful log is `full_short.log` in the evidence directory, SHA-256
`cf7dc92f0c4fb0c11c7e18ca87418b3bf7dc113eb2fb655f87ffc684831936ab`.
`implementation_validation.json` binds all 137 source/test/dependency files,
focused and full results, the preserved failed attempt, temporary-path diagnosis,
independent static reviews and prepared audit helpers. Its SHA-256 is
`71f75c979c5c754c7387df859e885b4a48be1b43fcfc62f683d76a7bc14fc8bc`.
The recovery manifest now binds that certificate; its file SHA-256 is
`2e1a57cfdacfa0359f328d467fd75b513b81fde192f69e4bd2a9919dbb7a6e1f`.
The certificate validates implementation bytes; it does not certify completed
real scoring, rendering, a comparison audit or human visual review.

## Exact intended staging scope

These 15 files include the preceding interruption record and approved proposal:

- `configs/ball_tracking/crop_retention_experiments/rfdetr_medium_crop_candidate_retention_recovery_v0_1.json`
- `configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_recovery_approval_v0_1.json`
- `docs/ball_crop_candidate_retention_interruption.md`
- `docs/ball_crop_candidate_retention_recovery_proposal.md`
- `docs/ball_crop_candidate_retention_recovery_implementation.md`
- `docs/context/current_state.md`
- `docs/context/roadmap.md`
- `docs/context/validation_history.md`
- `src/ball_tracking/crop_retention_resources.py`
- `src/ball_tracking/crop_retention_recovery.py`
- `src/ball_tracking/crop_retention_evaluation.py`
- `src/ball_tracking/crop_retention_review.py`
- `tests/test_ball_crop_retention_resources.py`
- `tests/test_ball_crop_retention_recovery_resources.py`
- `tests/test_ball_crop_retention_recovery.py`

The index remains empty. Staging and committing still require separate explicit
authorization. Scope approval for recovery is already recorded and should not
be requested again. Real recovery requires the separately authorized clean,
tested commit with the source bytes bound by the completed validation certificate.

All nine original prediction embargoes and three sealed holdouts remain
protected. Ryan's twelve YOLO final-frame approvals remain complete. The six
new retention clips require review only after they are successfully produced.
No method, operating point, quality gate or training is selected. Localization
MATCH/UNMATCHED outcomes remain separate from certified ball/non-ball identity.
