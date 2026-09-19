# Current State

## Current local checkpoint: development labels complete; experiment support implemented

Verified 2026-09-18 America/Phoenix (2026-09-19 UTC). This section supersedes
the historical snapshot below for session continuation.

- Branch: `codex/ball-detector-baseline`.
- Exact HEAD: `b7a887f55705623889625edf60028e2e39d38dc4`.
- Worktree intentionally contains uncommitted work. Preserve the existing
  working-agreement edit, six development annotation files, approval and
  finalization receipts, pilot review record, annotation initializer, and its
  tests. This context update is also uncommitted. Nothing is staged; no commit,
  push, PR, or merge was performed during this annotation continuation.
- All six representative/challenge development windows are labeled, visually
  approved by Ryan through their final frames, and finalized as `reviewed`.
  They use the established single-annotator visual self-review policy.

| Possession | Purpose | Inclusive frames | Labeled | Localization eligible | Not visible |
| --- | --- | ---: | ---: | ---: | ---: |
| P001 | Representative | 50–74 | 25 | 25 | 0 |
| P001 | Challenge | 200–224 | 25 | 25 | 0 |
| P002 | Representative | 250–274 | 25 | 25 | 0 |
| P002 | Challenge | 25–49 | 25 | 25 | 0 |
| P003 | Representative | 300–324 | 25 | 25 | 0 |
| P003 | Challenge | 150–174 | 25 | 20 | 5 |

The development sets total 150 labeled frames: 14 fully visible centers,
131 partially visible amodal center estimates, and five `not_visible`
occlusions. All 145 geometry points are localization eligible. There are no
unlabeled or excluded rows. P003 challenge frames 165–169 remain explicitly
occluded by the referee with null geometry; no interpolation crosses this gap.

### Evidence and validation at this checkpoint

- Annotation authority: the six `*_representative_evaluation_v0_1.json` and
  `*_challenge_evaluation_v0_1.json` files in
  `configs/ball_tracking/annotations/`.
- Approval authority: the matching frame-scoped `*_visual_review_approval_v0_1.json`
  and `*_single_annotator_finalization_v0_1.json` receipts in
  `configs/ball_tracking/reviews/`. Receipts bind the source, approved draft,
  visual bundle, and finalized file hashes to Ryan's actual approval statements.
- Finalization changed only `/review/status`, `/review/reviewer_id`, and
  `/review/reviewed_at_utc`. Every frame-level decision is unchanged.
- P003 representative final annotation SHA-256:
  `2b35475e715e9a4b816ad997b58be3201370695a2f420a35a6947696bbe3637e`.
- P003 challenge final annotation SHA-256:
  `ab77e6c8570ee8fc536632e43ee71d978e72cd16188f7564c77ae256873994ee`.
- Generated visual packages remain ignored beneath
  `data/outputs/ball_tracking/annotation_visual_review/`. P003 bundle IDs are
  `82e049e3ea6d16f944f1a64345ef7f692e285864edbf47ce3c27161cf35353bf`
  for frames 300–324 and
  `0c6b7ea0d768643f6f4b36d0151a40001d2b2b88f3dc2db5a091ec5b981fa35b`
  for frames 150–174. Their immutable snapshots correctly retain draft status;
  the receipts document the subsequent metadata-only finalization.
- The repository `.venv` with bytecode writing disabled passed strict schema
  and source-video verification for all six sets, the existing finalization
  receipt assertions for all six, and hash/size verification of all 330 review
  assets. This six-window audit completed; it was not merely proposed. At that
  annotation-only checkpoint, runtime code was unchanged and the full suite
  had not been rerun; the implementation checkpoint below supersedes this.
- The existing local pilot candidate-comparison review record reports Ryan's
  approval at `2026-08-24T05:05:09Z`. Its bound review plan, scoring report, and
  visual manifest still match their recorded hashes. The old snapshot's
  instruction to run the first pilot baseline is historical, not a current
  request to regenerate those artifacts.

### Prediction boundary and next action

All nine evaluation windows still have
`annotation_pending_prediction_embargo` in the unchanged v0.1 experiment
manifest. None of their nine declared prediction output files exists.
Completed annotation does not release predictions. No operating point or
quality gate was selected; no inference ran in this continuation.

Ryan approved the development experiment with "lets move forward I approve
of this experiment". The statement and immutable proposal-inventory hash are
recorded in
`configs/ball_tracking/reviews/rfdetr_medium_development_experiment_approval_v0_1.json`.
This authorizes implementation and the proposed six-window experiment once
its clean-checkpoint release conditions pass; it does not authorize staging,
committing, pushing, a holdout release, an operating point, or a quality gate.

Versioned support is implemented in `development_experiments.py`,
`development_release.py`, and `development_scoring.py`, with explicit v0.2
handling in the existing loader, runner, scorer, and visual renderer. The
strict six-window parent binding retains frozen detector settings and all
45 grid cells. Scoring produces two separate pools and 270 per-window results;
visual review produces one complete three-window package for each pool.
Synthetic tests use artificial frames and injected adapters only.

The release verifier checks approved labels and assets during evidence
preparation. At runtime it checks the release receipt and committed Git blob
identities without opening annotation JSON or review images. Evidence belongs
to a future clean commit; activation artifacts belong to a later separately
authorized commit. The new executable manifest and its six prediction outputs
remain absent. All nine original embargoed outputs remain absent. Existing
uncommitted files and the old manifest are preserved.

Implementation validation completed using the repository `.venv` with bytecode
writing disabled. The 14 new development tests, 10 existing detector visual
review tests, and 27 independent-review tests passed. The final full suite ran
299 tests: 298 passed, one existing directory-symlink capability test skipped.
`git diff --check` passed; new untracked Python syntax and whitespace checks
also passed. The ignored full-suite log is
`data/outputs/ball_tracking/development_implementation_validation/full_suite_20260919_retry.log`.
The first full run exposed an old independent-review test fixture with a fixed
August review timestamp earlier than its newly generated September creation
time. The fixture now derives its timestamp from creation; production review
rules and annotation data are unchanged. The full suite then passed.

The audit reverified all 24 approved inventory bindings, the frozen parent
hash, all nine original absent prediction outputs, and the six absent new
outputs. The existing working-agreement edit retains SHA-256
`55eb9c73c29c3f6f8c8e6c30d8caa1e9506adbded15a57e813b76f4c6fe13be3`.
No operating point or quality gate was selected; no real model inference ran.
The new source code remains uncommitted, so this successful implementation
validation is not a clean-commit release receipt.

The next external boundary is separate staging authorization for the exact
35-file list in the proposal document, then separate commit authorization. The approved experiment does not need approval again.
See `docs/ball_detector_development_release_proposal.md` for the checkpoint
procedure. Keep all three test holdouts sealed.
No development-window visual approvals remain unresolved, and no manual
commands were supplied but left unrun. The existing annotation editors may
still be open; their now-reviewed files must not be edited as drafts.

## Historical snapshot retained for provenance

The sections below describe the earlier checkpoint. In particular, their
inference and annotation to-do lists predate the local evidence above.

Snapshot date: 2026-08-23 (America/Phoenix)

## Repository checkpoint

At the current ball-detector precommit checkpoint:

- branch: `codex/ball-detector-baseline`;
- development base: `51c084c6dc8a11df883db6780a9a024d9506e5bf`
  (`feat(ball-tracking): add reviewed annotation foundation`);
- the strict RF-DETR Medium image-only adapter, resumable inference runner,
  experiment-manifest contract, source verification refactor, and regression
  coverage are implemented;
- Ryan approved nine prediction-blind evaluation windows across the same three
  possessions, and their reproducible selection record is frozen in
  `docs/ball_detector_baseline_selection.md`;
- only the three reviewed protocol pilots are marked `ready_for_inference`;
  all nine new windows remain `annotation_pending_prediction_embargo`;
- focused ball source/detector tests: 129 passed, with one Windows
  symlink-capability skip;
- full test suite: 264 passed, with the same one skip and bytecode writing
  disabled;
- no manifest-authorized baseline run or prediction on any of the nine approved
  evaluation windows has been generated; the quarantined historical exploratory
  prediction at Possession 001 frame 150 remains explicitly excluded.
- the real installed RF-DETR class mapping and a non-inference construction of
  the frozen CUDA model both pass the adapter contract; no video frame was
  supplied.

The preceding durable migration checkpoint was:

- branch: `main`;
- local HEAD and `origin/main`: `1f086ba` (merged PR #7, **Add durable desktop project context**);
- PR #6's thorough README update is included;
- the local and remote `docs/desktop-context-migration` feature refs are deleted;
- worktree: clean;
- all eight durable context files match the reviewed migration proposal;
- full test suite: 56 tests passed using the desktop app's bundled Python, with bytecode writing disabled.

Future work should still begin by checking the current branch, HEAD, worktree, and remote state rather than assuming this snapshot remains current.

## Completed technical foundation

- RF-DETR Medium person detection and ByteTrack multi-object tracking.
- Playable-court filtering and tracking audits.
- Uniform-feature team classification.
- OSNet-AIN ReID embeddings, temporal segmentation, segment reconciliation, and reviewed consolidation.
- Exactly ten persistent player identities, with five white and five dark players in validated possessions.
- Reference court calibration and one homography per decoded frame.
- Player floor-point projection to court coordinates.
- Conservative trajectory refinement and bracketed internal-gap interpolation with provenance.
- Configuration-driven, possession-scoped, resumable 21-stage orchestration.
- Explicit identity and calibration review gates.
- Multi-possession empirical generalization gate passed on Possession 003.
- Reviewed ball-center annotations for three 25-frame protocol pilots, plus a
  strict raw-detection and evaluation data contract.
- A precommitted, label-blind RF-DETR Medium ball-detector baseline contract with
  exact runtime provenance, raw-candidate preservation, resumability, and
  prediction embargoes.

## Not complete

- real ball-detector inference, scoring, temporal tracking, and their quality
  gates;
- automatic possession segmentation and broadcast-cut handling;
- ball-handler and event inference;
- mapping visual identities to NBA rosters;
- primary-defender, switch, help, and contest inference;
- the defensive scoring model;
- complete-game NBA validation and reporting.

## Immediate next task

The annotation contract, detector adapter/runner, experiment contract, scoring
grid, and prediction-blind window selection are complete. The next operational
sequence is:

1. from a clean committed snapshot, run the runner's read-only preflight and
   confirm the exact source clips,
   RF-DETR package, official weight bytes, CUDA runtime, ignored outputs, and
   three authorized pilot windows;
2. run the first descriptive baseline over only the three reviewed pilot
   windows, preserving every exported COCO `sports ball` candidate at or above
   the frozen `0.01` export floor;
3. inspect and score the fixed confidence/localization grid on those pilots;
4. annotate and review the six representative/challenge windows, then use a
   reviewed, versioned schema/manifest release instead of toggling v0.1 in
   place; freeze an operating point before separately releasing the three test
   holdouts;
5. render candidate-versus-truth evidence before proposing a temporal tracker
   experiment or any detector quality gate.

No ball-tracking implementation was started in chats 01–06. The prior blocker was intentionally removed only after Possession 003 passed the generalization gate.

### Ball-tracking annotation checkpoint

- The v0.1 annotation schema, prediction-blind editor, source verification,
  neutral review assets, visual-review renderer, and detection-evaluation
  contract are implemented on `codex/ball-annotation-foundation`.
- Possession 001 frames 375–399, Possession 002 frames 318–342, and Possession
  003 frames 416–440 each contain 25 completed annotations and are
  single-annotator, visually reviewed reference sets. Ryan approved all three
  bound visual-review packages through their final frames.
- Across the three windows, all 75 frames are labeled: 67 contain geometry, 66
  are localization eligible, eight are reviewed `not_visible` negatives, and
  one visible ambiguous frame is intentionally unscored.
- Possession 002 contains 17 geometry estimates, of which 16 are localization
  eligible, plus eight reviewed `not_visible` occlusion frames. Missing geometry
  remains explicit and un-interpolated.
- Possession 003 contains 25 continuous geometry points: five fully visible
  observed centers and 20 partially visible amodal estimates. All 25 are
  localization eligible; no geometry gap or interpolation is present.
- Duplicate or independent annotation is not a prerequisite for review or the
  current milestone. It remains optional for a specifically declared
  inter-rater or intra-rater reproducibility study.
- The protocol-declared synthetic evaluator cases pass. The raw, image-only
  detector export harness and precommitted experiment manifest are implemented.
  The next runtime task is the clean preflight and three-pilot descriptive run,
  not temporal tracking yet.

## Local data checkpoint

At migration time, the ignored `data/` tree contained 856 files totaling
6,710,202,697 bytes, all successfully SHA-256 hashed in the external manifest
`manifests/local-data-files.csv`. The ball-annotation workflow subsequently
added ignored review assets beneath `data/outputs/`; that migration-era count
is therefore historical, not the current tree total. All three source clips
still match their declared hashes, and generated review media remains ignored.
