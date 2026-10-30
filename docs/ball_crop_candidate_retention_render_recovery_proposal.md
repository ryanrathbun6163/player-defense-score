# Candidate-retention rendering recovery proposal

**Status: draft for Ryan's review. No implementation or rendering retry is
authorized by this proposal.** The completed forensic audit and its final
resource checkpoint bind the preserved evidence below. This amendment changes
output measurement and permits exact reuse of completed scores; it keeps the
scientific comparison and resource allowances unchanged.

## What completed, and where execution stopped

Ryan separately authorized the prior recovery's exact 15-file staging and
commit. Execution began from clean commit
`f36237247191e726ad7e81bdc6651f9340a9063d` on
`codex/ball-detector-baseline`.

| Stage | Recorded outcome |
| --- | --- |
| Recovery verification | One successful supervised worker |
| Scoring | Eight successful workers; six window reports and two pool reports completed, containing 120 new localization reports and 630 saved reports |
| Rendering preflight | Succeeded in 43.266 seconds |
| First rendering window | Failed after 62.875 seconds with `Output tree did not stabilize for complete byte accounting` |

The first rendering worker's log is empty and its result is null. Ten pending
PNGs remain, totaling 32,989,248 bytes. No MP4, final window manifest, completed
clip or completed comparison audit was produced. The pending folder's reported
basename is:

`.pending_possession_001_frames_0050_0074_representative_evaluation_development_v0_2_6609ad1f69fa47889eae916569336db5`

All completed selections, scores, earlier failures, resource history and this
pending render evidence must remain in place. These execution facts do not
establish tracking quality: the full independent comparison audit and six new
clip reviews remain incomplete. This proposal makes no scientific comparison
claim and selects no method, operating point or quality gate.

## Evidence and limits of the diagnosis

The prior correction permits file sizes to grow while requiring the membership
of two complete inventories to match. Rendering creates new PNG files, so new
file identities may keep those inventories from matching. This is the source
code hypothesis for the real failure; it is not a proven account of the exact
real-time file changes that triggered the abort.

A completed synthetic reproduction supports that mechanism. With 2,001
prefilled files in each case, growth of existing files passed all three trials
(approximately .109 seconds per measurement); adding new files failed all
three trials with the same half-second inventory-stability error. After the
writer stopped, both cases passed and measured bytes equaled actual bytes.
The synthetic receipt records 3.453 seconds of elapsed time. These are separate
synthetic diagnosis costs, not a reset or extension of the real-run allowance.

The reproduction evidence is in
`data/outputs/ball_tracking/crop_candidate_retention_recovery_implementation/0a7f5bc69be9_2026-10-02/render_membership_diagnosis/`:

- `receipt.json`, SHA-256 `6a894647368b1c7a4979de6d04e74a9e94f679ca0b0c31123eea5ea518cb5973`;
- `reproduce.py`, SHA-256 `e5ba8c41f713760d26fceb2e7009d817662231d8691fb0b87ffe36b967353e35`.

The synthetic result demonstrates that membership additions can cause the
observed class of failure. It does not prove that this was the real trigger.
The completed supervised preservation audit bound the exact saved real artifacts
without rendering, scoring or selecting again. It verified artifact bytes and
receipts; it did not interpret scientific results or complete the comparison
audit. Exact receipt and post-diagnosis journal bindings appear below.

## Proposed measurement amendment

Retain two complete recursive inventories and the same .5-second measurement
deadline. Each inventory records file identity `(device, inode)`, the count of
directory entries for that identity, and the largest logical size observed for
it. The second inventory may contain additional identities or increased
entry counts. It may not lose a first-inventory identity or decrease an
identity's multiplicity.

For an accepted pair, charge each identity present in the second inventory its
second-inventory multiplicity times its largest observed size across both
inventories. A new identity is charged from its observed second-inventory
size. A shrinking file retains the larger observed size. Hard links continue
to count as multiple directory entries. Temporary PNGs, logs, failed partials
and all other files in the original output root stay in the accounting.

A pair containing an identity disappearance or decreased multiplicity is
rejected. Missing paths or incomplete traversal cannot produce an accepted
measurement; a missing path resets the prior inventory. Keep the existing
bounded retry behavior: another pair of complete inventories may be attempted
only within the same unchanged .5-second deadline. Check that deadline during
traversal and before accepting a pair. If no acceptable complete pair exists,
fail closed; never substitute a partial or stale measurement.

This accounts conservatively for the sizes actually observed in the accepted
pair. It is not an instantaneous upper bound on bytes written after a size was
read. Existing maximum-size recording, final accounting reserve, measured
monitoring cadence and explicit overshoot reporting remain mandatory.

The new rule must withstand adversarial move, replacement, deletion and
hard-link tests showing that observed bytes cannot be omitted. If the argument
or tests fail, stop and revise the proposal rather than broaden acceptance.

All limits remain unchanged: one worker process tree, 8 GiB combined resident
memory, 32 GiB for the whole existing output root, at least 10 GiB free disk,
30 minutes per original selection unit, and four cumulative active real worker
hours. Monitor at least once per second and between stages. The unchanged
real journal includes every failure, diagnosis, preparation and verification
worker. No new root, moved evidence, deleted partial or reset reservation may
be used to obtain additional time or space.

## Exact reuse and execution scope

Prepare a separate versioned rendering-recovery manifest and approval receipt
after this proposal is approved. Preserve all existing manifest, approval,
certificate and successful output bytes. Its allowlist must bind:

- The exact original 24 selections and 600 trace shards, their input bindings,
  successful worker results, completion events and seals, retaining actual
  selection commit `0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41` and original spec.
- The six completed scoring-window files and two completed pool files, their
  file/content hashes and successful worker/resource receipts, retaining actual
  evaluation commit `f36237247191e726ad7e81bdc6651f9340a9063d` and its spec.
- The known failed rendering attempt, all ten pending PNGs, the entire pending
  folder inventory, empty log and null result, plus the older failed score
  partial and prior interruption evidence.
- The complete 1,170-event resource prefix through the completed forensic worker,
  all attempt roles/results/seals, the exact chain tip and current consumed
  budget. Earlier prefixes alone are insufficient.
- Unchanged candidate inputs, 126 saved controls, original saved reports,
  six reviewed development annotation sets and bound source PNGs; original
  source/certificate evidence plus a new exact validation certificate.

The new runner may verify existing evidence and render the six previously
approved .01 clips. It must not rerun selection, score a window, aggregate new
pool results or reevaluate saved controls. Reading and verifying completed
scores is permitted. Default existing loaders retain their strict provenance
checks; only exact allowlisted old artifacts may cross the new spec/commit
boundary. New review manifests retain the original selection and evaluation
roles while recording the actual future renderer commit and new specification.
That future commit must not be invented before it exists.

The first failed render remains incomplete. A later approved retry must use a
fresh uniquely named staging folder while leaving the old folder untouched.
A final review target without a successful resource-completion receipt cannot
be adopted or overwritten. Any unknown target, altered partial or selection,
changed completed score, missing history, unresolved membership or further
resource failure stops execution for investigation. No automatic relaxation,
fallback, graph truncation or indefinite retry is included.

The revised independent completion helper must verify old selection, old score
and new renderer provenance separately, retain both known failures and the full
charged journal, and check the same six-window/pool/alias and final-frame
contracts. Preparing or testing that helper does not mean the real comparison
audit has run. Its eventual real execution must be supervised and charged.

## Required validation before any real retry

Use fabricated inputs for focused tests, followed by the full regression suite
with bytecode disabled and short ignored temporary paths. At minimum cover:

- Continuous new-file creation lasting longer than .5 seconds, existing-file
  growth, shrinking/rewritten files, hard-link additions and multiplicity;
- Atomic file/directory movement and publication, replacement, deletion,
  missing-path races, rejected partial walks and unresolved membership;
- Deadline checks inside traversal, slow system calls, sampling cadence, all
  existing resource limits, final accounting and worker-tree termination;
- Exact old selection/score allowlists, actual commit/spec roles, altered
  inputs, partials and journal seals, unknown outputs and missing certificates;
- Tripwires proving no selector, scorer or saved-control evaluator is called;
- Fresh staging and preserved old evidence, interrupted rendering, and failure
  between final publication and successful completion without silent adoption;
- Six clips, complete final frames, unchanged pool separation and aliases,
  explicit null observations, and correct old/new provenance in review/audit.

Record exact source, test, dependency and evidence hashes before and after
validation. Require independent static review of the accounting rule and reuse
exception, then a new validation certificate binding the final tested bytes.
Real execution additionally requires a clean, separately authorized committed
checkpoint. Completed real selectors, scores or reviews are not test fixtures.

## Why another explicit review is needed

The approved prior recovery requires equal membership between complete scans
and stopping after a new failure. Permitting monotone membership additions is
a change to that execution contract, although budgets and the basketball
question remain unchanged. The frozen design requires a revised explicit scope
for a budget or design change. This proposal presents that concrete amendment;
it does not revoke the original scientific approval or imply that every routine
bug fix requires new experiment approval.

No implementation or retry is authorized yet. Later approval would cover this
bounded implementation and its execution only after focused/full validation,
independent review, exact input checks and the clean committed checkpoint.
Staging, committing, pushing, PR creation and merging remain separate decisions.

Preserve all nine prediction embargoes and three sealed holdouts; do not open
holdout contents. No inference, training, new settings, candidate correction,
identity labeling or player/calibration change is proposed. Localization
MATCH/UNMATCHED is not a certified ball/non-ball training label. The six new
retention clips require Ryan's final-frame review after they exist. The prior
twelve YOLO approvals and previous completed reviews remain complete.

## Exact authority and checkpoint bindings

Paths are repository-relative. The unchanged real output root is
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/`.
The forensic receipt below is the exact inventory of all 24 selection manifests,
600 traces, eight scoring artifacts and ten partial PNGs. It includes their
file bindings and successful worker receipts. The checkpoint extends that
receipt through the diagnosis worker's successful completion, with every event,
reservation and completion seal. These are exact inventories, not wildcard
permission to reuse other outputs.

| Authority or preserved evidence | File SHA-256 |
| --- | --- |
| Original executable manifest: `configs/ball_tracking/crop_retention_experiments/rfdetr_medium_crop_candidate_retention_v0_1.json` | `f2b8834722ddf9f1ce4dcfdf1441a12cc0d52591b57bb66ca726c3aef2ca15ff` |
| Original proposal: `configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_retention_v0_1.json` | `7640784e2a64e81a2064ebb40cd4d1c77366076e5e78a2c19f8f5fc28e29fe1b` |
| Original design: `docs/ball_crop_candidate_retention_proposal.md` | `66db56a2338f86998c67c3a04f4850fa039ac7e8716cc982f5e34fb1593aff58` |
| Original approval: `configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_approval_v0_1.json` | `dcc52439d7e08f17c45f10811b4eb39b34577c23a0a3291aa347246ef6f24219` |
| Original validation certificate: `data/outputs/ball_tracking/crop_candidate_retention_implementation/9fe6a1ef86d2_2026-10-02/implementation_validation.json` | `135bb50a461eec662f70ed4c64d15fe15e36826eefe81ee21e7521f36578890f` |
| Scoring-recovery proposal: `docs/ball_crop_candidate_retention_recovery_proposal.md` | `c066bc43b204a09a05e2912589cbc173614cecbe563431ebbeed75c42db3de48` |
| Scoring-recovery manifest: `configs/ball_tracking/crop_retention_experiments/rfdetr_medium_crop_candidate_retention_recovery_v0_1.json` | `2e1a57cfdacfa0359f328d467fd75b513b81fde192f69e4bd2a9919dbb7a6e1f` |
| Scoring-recovery approval: `configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_recovery_approval_v0_1.json` | `29ba7f01ff0a2bd149d341d064673460f8be87bedd024442015a7a222a6090ae` |
| Scoring-recovery validation certificate: `data/outputs/ball_tracking/crop_candidate_retention_recovery_implementation/0a7f5bc69be9_2026-10-02/implementation_validation.json` | `71f75c979c5c754c7387df859e885b4a48be1b43fcfc62f683d76a7bc14fc8bc` |
| Original interruption receipt: `data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit/interruption_receipt.json` | `0f90a59c07dd2436ef8618ffd8d3637695b99ab3e56e08f879866d9d702e40df` |
| First recovery preserved inventory: `data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/recovery_preparation/preserved_inventory.json` | `5a05c6644196f7fd0dfb731c538f68077039f74265d62e7b95f3dbbe00b92739` |
| Completed rendering-interruption audit: `data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit/render_interruption_f362.json` | `f2bece32af228b0f525b07eb060b1671194812b26af7787283c8ecca2aabea8b` |
| Post-diagnosis resource checkpoint: `data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit/render_interruption_checkpoint_f362.json` | `8dce571305282e59dc61e3ceb610e2ea0e5dbd86ce1896beb9e035c8ee12dcac` |
| Ignored forensic helper: `data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit/render_interruption_audit_f362.py` | `1c57d4e280f724c51f8e56d75229b06ec120e01dcf5a48449e00946a59c3cb3a` |
| Unchanged output monitor: `src/ball_tracking/crop_retention_resources.py` | `e069afba8d9430cad55e32b0f9bb45650a83267c5cdaca3eefdabff851ea6771` |
| Unchanged selector: `src/ball_tracking/crop_retention.py` | `834adb4c80175afebe16f970151e1b365a6f1ed689c2d2db78d1a8b226a8b0c6` |
| Unchanged ordinary runner: `src/ball_tracking/crop_retention_experiment.py` | `4fcac16f9f19318ed4eb07028471b3f4b9aa505a790a2a3c789c960143ba590b` |

The original selection specification's canonical digest is
`e481d645e946f285c655d721563172c4cb8c2f124214840b8c8d8ae5cfb752fd`.
The completed scoring specification's canonical digest is
`4b1f9f3c75ee53eb1358bcb49981118269694ec39adb5a312ae325f8ee273bbf`.
These content digests are distinct from the manifest file hashes above.
The protected source/test/dependency inventory is the exact 137-file inventory
in the bound scoring-recovery validation certificate, verified by the forensic
audit. Future implementation changes require a new certificate; existing
certificates and source identities remain historical evidence.

The eight completed scoring files below must be reused with their exact
successful receipts from the forensic inventory. They retain evaluation commit
`f36237247191e726ad7e81bdc6651f9340a9063d` and the scoring spec above.
Paths in this table are relative to the existing output root.

| Scoring artifact | File SHA-256 |
| --- | --- |
| `evaluation/challenge_evaluation.json` | `01afe5ad0391336c5619e93dea585f79a665dccd02d9201c3dbe9349d1e60f60` |
| `evaluation/representative_evaluation.json` | `82ce2d01b9f61a5d66b358f5aa42654db2413f7a9d5e45867ddffc9fb1e5acfb` |
| `evaluation/windows/possession_001_frames_0050_0074_representative_evaluation_development_v0_2.json` | `e04bed53dd23cafc6c6ffd25d6c6f84aa4bf565bcaf6cdaf0324799fefde44ef` |
| `evaluation/windows/possession_001_frames_0200_0224_challenge_evaluation_development_v0_2.json` | `b21826f50c6d61d3c1af04f4888f10d6538e0ab52a94bdd671cf566a90c471c3` |
| `evaluation/windows/possession_002_frames_0025_0049_challenge_evaluation_development_v0_2.json` | `32b901bb57ef56987f4ae323a9db592bb0755c763e20569d1175974c287a7ed9` |
| `evaluation/windows/possession_002_frames_0250_0274_representative_evaluation_development_v0_2.json` | `08fa0eda8bc2f74574bd4bae411c6b57c2584fa1377a0e29f7ebb8542a237a4f` |
| `evaluation/windows/possession_003_frames_0150_0174_challenge_evaluation_development_v0_2.json` | `d8595f91f9fc87ef7ff1ad959b6a0cf7a00e812d69060ac72d56040a59f838cd` |
| `evaluation/windows/possession_003_frames_0300_0324_representative_evaluation_development_v0_2.json` | `0beb22c685451eea862105fae5fbb6afd72c53962cba8650ca6de8a24caf83f0` |

Failed renderer `158f51be5ab34cdface57f4e0036b7d2` has canonical completion hash
`3127e069233b5cb5caa41a4088e878226289438732c48ed035c8925da359ad6c`.
Its empty log is
`attempts/158f51be5ab34cdface57f4e0036b7d2.log`, SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
Its worker result remains null. The exact pending directory under the output
root is
`review/windows/.pending_possession_001_frames_0050_0074_representative_evaluation_development_v0_2_6609ad1f69fa47889eae916569336db5`.
All ten file paths, sizes and hashes are bound in the forensic receipt's
`partial_review_files`; its `absent_final_review_targets` records all six
unpublished window targets and the unpublished global review target. No pending
MP4 or completed clip exists. Preserve that exact inventory and the older
failed score partial bound by `original_failed_scoring_preserved`.

The post-diagnosis checkpoint records 1,170 events and 41 completed attempts:
39 successes, two preserved failures. Cumulative time is 1,136.756 seconds;
13,263.244 seconds remain from the original four-hour allowance. No new worker
or retry is pending. Any later authorized worker consumes this same allowance.
Diagnosis attempt `8e121d23c2494d969df9af94cc45bbeb` used 9.812 seconds and
succeeded; the completed chain-tip canonical digest is
`19c2134889cb129bb625dbcac09c3c9beca02b5fb086088e3cb01644762f70f5`.
Its raw final event `resource_events/00001169.json` has SHA-256
`f226a368b101d9882eb51c023995859558ff88747f2a9ed41e01fb9e63617032`.
The helper's ignored, uncommitted provenance is recorded separately and must
not be attributed to the f362 execution commit.

If approved, prepare these new files without overwriting existing authorities:

- Manifest:
  `configs/ball_tracking/crop_retention_experiments/rfdetr_medium_crop_candidate_retention_render_recovery_v0_1.json`.
- Approval record:
  `configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_render_recovery_approval_v0_1.json`.
- A new versioned independent completion helper, whose path and exact hash must
  be recorded after it is prepared and reviewed. Preserve the unexecuted
  `audit/independent_audit.py` (SHA-256
  `d15daf629f10eccb68cbd3d45c7d272b3f00bd8fce2baab35386521a32cf94af`)
  and `audit/independent_recovery_audit.py` (SHA-256
  `3c30f23ab95a340c0b4244c01bc2327ca1c1533ab4bbbff58db8c0b21286b337`)
  under the existing output root.

Future manifest, approval, helper, validation certificate and execution commit
hashes do not exist yet. They must be bound to their actual final bytes before
execution, never predicted or substituted with the old identities. This
proposal is concrete preparation for review, not an executable approval record.
