# Candidate-retention render recovery implementation checkpoint

This note records the implemented render-only recovery that Ryan approved with **“I approve, move forward chat.”** Focused and full regression validation passed. No new real verification, rendering, selection, scoring, aggregation, or model worker has run under this recovery identity.

The authoritative approval is `configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_render_recovery_approval_v0_1.json`, SHA-256 `133981a85b191e931e739ad0c3030659072282665db0dd5cb234716fb52f71f6`. It binds the frozen `docs/ball_crop_candidate_retention_render_recovery_proposal.md`, SHA-256 `2d9ea51ca4f93fbc77d902266dcbf1ef496edcb8c320c7a0dbbe6d86bf884b48`. The approval authorizes implementation and execution subject to successful validation and a clean, separately authorized commit. It does not authorize Git mutations or training.

## What changed

The new `src/ball_tracking/crop_retention_render_recovery.py` exposes only verification and rendering. It verifies the historical resource chain, immutable artifact allowlists, source bindings, approval, and implementation certificate before supervised execution. Parent orchestration performs authority/source checks; saved-output inspection runs inside workers charged to the existing budget. Metadata-only dry-run does not start a worker or verify scientific output bodies.

The resource monitor in `src/ball_tracking/crop_retention_resources.py` now accepts monotone membership additions across two complete directory scans within the existing half-second deadline. Previously observed file identities must remain present and their hard-link multiplicity must not decrease. Accounting uses second-scan multiplicity and the larger observed size for each identity. Missing paths reset the comparison; incomplete walks and inadmissible scan pairs cannot be accepted. Existing bounded retries and all resource limits remain unchanged. This measures conservatively across the two completed scans; it does not claim an upper bound on future growth between samples.

The minimal `crop_retention_review.py` bridge accepts an explicit saved-score loader alongside the existing observation loader. Default loaders retain their previous strict behavior. The render-only loader verifies the exact successful score receipts and then reads the completed scoring documents under their original evaluation identity. It never invokes selection, scoring, matching, or pool aggregation.

Each new render attempt uses fresh staging. The ten previous partial PNGs remain preserved. A published target without a successful resource completion receipt is rejected rather than adopted during resume. A new failed or unfinished attempt stops further continuation for investigation. Successful resume validates completed outputs without rerendering them.

## Preserved evidence and provenance

- Original selections: exactly 24 manifests and 600 compressed traces from commit `0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41`, original specification `e481d645e946f285c655d721563172c4cb8c2f124214840b8c8d8ae5cfb752fd`.
- Completed scoring: exactly six window documents and two pool documents from commit `f36237247191e726ad7e81bdc6651f9340a9063d`, scoring specification `4b1f9f3c75ee53eb1358bcb49981118269694ec39adb5a312ae325f8ee273bbf`. These retain the 120 new and 630 saved localization reports without recomputation.
- Historical checkpoint: all 1,170 events and 41 completed attempts, including 39 successes and both failures. The forensic receipt is SHA-256 `f2bece32af228b0f525b07eb060b1671194812b26af7787283c8ecca2aabea8b`; the post-diagnosis checkpoint is `8dce571305282e59dc61e3ceb610e2ea0e5dbd86ce1896beb9e035c8ee12dcac`.
- Preserved partials: the original failed scoring JSON and ten nested PNGs totaling 32,989,248 bytes from the failed first renderer. Their exact bindings remain in the historical receipts.
- Existing budget: 1,136.756 seconds consumed and 13,263.244 seconds remaining after the forensic diagnosis. The output root and all time, memory, disk, and sample-cadence limits are unchanged. There is no fresh budget.

New review headers identify the original selection commit/specification, original evaluation commit/specification, preserved inventory, scoring manifest, interruption receipt, and resource checkpoint. The renderer will record its actual future clean commit and the final new manifest specification. Earlier artifacts are not relabeled as newly generated evidence.

Historical source protection permits only three explicitly reviewed differences from the completed scoring certificate: the resource monitor, the renderer bridge, and the one conflicting membership-expectation test in `tests/test_ball_crop_retention_recovery_resources.py`. New regression tests live in new test modules. The new certificate must bind every current Python source/test and `requirements.txt`.

## Validation checkpoint

The focused resource set passed **44 tests**. Independent reviews checked the monitor amendment and render recovery boundaries, including preserved provenance and the exact historical allowlists. The actual metadata-only CLI dry-run succeeded with no worker dispatch. Its temporary specification is not an execution certificate or evidence of a completed experiment.

The production recovery module is frozen at SHA-256 `a8f42b6904373a9474c62de1403677df11373ab10b8b2be65ec3be179505102a`; the renderer bridge is frozen at `552c02ccf4cda3be35b0652d01040a02eae1152ed1fc4c9b2e2ee264fd4b188b`.

The new rendering-recovery tests also passed all 26 cases in 104.376 seconds.
All 145 combined retention tests passed in 198.604 seconds (199.203 seconds
harness elapsed), with no skips. All 140 source/test/dependency bindings stayed
unchanged. The full regression suite completed 665 tests in 1,882.854 seconds
(1,884.437 seconds harness elapsed): **664 passed and one existing Windows
directory-symlink test was skipped**. All 140 source/test/dependency bindings
remained unchanged in both runs. No scientific output was regenerated.

The common source inventory has SHA-256 `545592e57cfc716b8a9b7ad542fd0a493621a848c61516ca3374f2ae2b1d6148`.
The focused log has SHA-256 `2c44f25e871592818bc09d497df0297aac0b99c7d3b7c6283b140ed1a2b5f7ed`;
the full log has SHA-256 `8718be18e1cfab70e8290688315e107c5de91f6931af803114a844ec9796eaa7`.
Receipts, logs, inventories and independent reviews are saved under
`data/outputs/ball_tracking/crop_candidate_retention_render_recovery_implementation/f36237247191_2026-10-02/`.
Independent review also passed the certificate assembler's guards: exact test
commands and complete success summaries, nonempty reviewed-file bindings, all
1,170 journal event hashes, and 41 reservation/completion seals. Optimized Python
is rejected because it would disable assertion guards.

The final create-only `implementation_validation.json` has SHA-256
`652a8bb8926ea21be2e1863e34105b1c737986e46c5615a342e682be497644dc` and binds
140 source/test/dependency files plus 27 evidence artifacts. The final recovery
manifest has file SHA-256
`72f15b1d43750b00b49d0bd83c3e8ab0c4351064aeadad582008429580c00fcf` and canonical
specification SHA-256
`326ba1cec475aa32d172a76a2ea760ceffb3e9188631c16ed2b1af5914fab3cd`.
Its final metadata-only CLI dry-run passed without worker dispatch.

The separately prepared, independently reviewed completion-audit helper is
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit/independent_render_recovery_audit.py`,
SHA-256 `83572bf8c1cd016207a308a71e9b340b8720c010afc2b86bd35a30d5f71be13e`.
It has not run. After rendering it will check saved report arithmetic, provenance,
successful completion receipts, and the final frames of all six new clips under
the original remaining resource budget. Human visual review remains separate.

## Expected review and Git boundary

The verified staging scope is exactly 14 files, all currently unstaged:

1. `docs/context/current_state.md`
2. `docs/context/validation_history.md`
3. `docs/context/roadmap.md`
4. `docs/ball_crop_candidate_retention_render_interruption.md`
5. `docs/ball_crop_candidate_retention_render_recovery_proposal.md`
6. `docs/ball_crop_candidate_retention_render_recovery_implementation.md`
7. `configs/ball_tracking/crop_retention_experiments/rfdetr_medium_crop_candidate_retention_render_recovery_v0_1.json`
8. `configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_render_recovery_approval_v0_1.json`
9. `src/ball_tracking/crop_retention_resources.py`
10. `src/ball_tracking/crop_retention_review.py`
11. `src/ball_tracking/crop_retention_render_recovery.py`
12. `tests/test_ball_crop_retention_recovery_resources.py`
13. `tests/test_ball_crop_retention_render_resources.py`
14. `tests/test_ball_crop_retention_render_recovery.py`

Branch is `codex/ball-detector-baseline`, HEAD is
`f36237247191e726ad7e81bdc6651f9340a9063d`, and the index is empty.
Staging and committing each require separate explicit authorization after validation and review. Pushing, PR creation, and merging remain separately unauthorized. The already approved recovery execution requires the resulting clean, validated commit; the scientific scope does not need repeated approval.

All nine prediction embargoes, three sealed holdouts, original candidate coordinates/confidences, saved controls, and localization uncertainty remain protected. No method, operating point, quality gate, training labels, or scientific conclusion has been selected. The earlier twelve YOLO comparison reviews remain complete. Six new retention clips and the full independent comparison completion audit remain pending; the later human visual review must include every final frame.
