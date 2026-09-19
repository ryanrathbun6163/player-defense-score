# Current State

## Latest checkpoint: temporal support validated; staging approval pending

Branch remains `codex/ball-detector-baseline` at
`84bcc8da143e54ff17a28b39db0e70c4b8b299c8`. Preserve the intentionally dirty
worktree. Nothing has been staged, committed, or pushed for this step.

Ryan responded "lets move forward" to the linked temporal-association design.
This authorizes its six-window experiment; the exact statement, design hash,
and concrete specification hash are in
`configs/ball_tracking/reviews/rfdetr_medium_temporal_association_approval_v0_1.json`.
Do not request that experiment approval again. The new manifest is
`configs/ball_tracking/temporal_experiments/rfdetr_medium_temporal_association_v0_1.json`;
its specification SHA-256 is
`ef2f7a2a77f334c94d0efc045311c6fd4a3cc86695aec84934bacbfb06605ab5`.
It binds all six saved development outputs and the completed visual review.

Four new `temporal_*.py` modules implement deterministic causal tracklets,
separate derived-output scoring, strict manifest/authorization guards,
resumability, and synchronized review rendering. No protected existing source,
tests, annotations, or raw detector outputs changed. Synthetic tests exercise
all 54 variants, 324 observation files, 1,620 per-window reports, separate pools,
and a complete video bundle. A real-data read-only dry-run passed for all six
windows and 150 frames. No real temporal observations, scores, or videos exist.

Final focused validation passed all 25 new tests. The final full suite ran
324 tests in 147.691 seconds: 323 passed, one existing directory-symlink
capability skip. Both used the repository `.venv` with bytecode writing disabled.
`git diff --check`, new-file JSON/Python syntax and whitespace checks, and exact
13-file scope verification passed. The first full-suite run was deliberately
stopped after the synthetic preview prompted larger headings and moving
tracklet labels away from the ball marker; its partial result is not counted.
No association or scoring rule changed. The agent inspected the final synthetic
comparison preview; real temporal visual review remains future work.

Generated validation artifacts are under
`data/outputs/ball_tracking/temporal_implementation_validation/` and stay ignored:
`focused_final.log`, `full_suite_final.log`, final synthetic preview PNGs, and
`validation_record.json` with output hashes and proposed file/Git-blob scope.
The latest commands completed were the full suite and final evidence/scope
audit. All 59 prior protected files and six raw detection files are unchanged.
The index is empty; worktree scope is three modified context documents plus
ten new source/test/configuration/review/design files. Real execution correctly
refuses this uncommitted state before association output is created.

The next boundary is staging the exact 13-file scope in
`docs/ball_temporal_association_implementation.md`, then separate commit approval.
The runner requires a clean committed checkpoint before real association.
After that checkpoint, run association, scoring, and rendering at the same
commit and obtain Ryan's visual review of the new temporal evidence. All nine
old prediction paths remain absent, three holdouts remain sealed, and no
operating point or quality gate is selected. No manual execution command was
left for Ryan; future post-commit commands are documented in the implementation
note and have not been run.

The detector review below is a completed earlier checkpoint. Its statements
that temporal support is only proposed predate the implementation above.

## Current checkpoint: development experiment visually approved

Verified 2026-09-19 UTC (2026-09-18 America/Phoenix).

- Branch: `codex/ball-detector-baseline`.
- Exact HEAD: `84bcc8da143e54ff17a28b39db0e70c4b8b299c8`.
- Latest commit: `feat(ball-tracking): activate approved development evaluation`.
  Ryan separately approved staging the six release-checkpoint files, then
  authorized their commit with "yes you may chat". Exactly those six files
  were committed. Parent evidence commit:
  `9521569cab36c8d289c4a341b5f33273062cabb4`. Nothing was pushed.
- Clean-commit release validation passed against 59 protected file bindings.
  Detector dry-run preflight passed for exactly six development windows.
  The real frozen RF-DETR Medium run completed all 150 frames, with zero
  incomplete frames and 22,931 raw candidates retained at the 0.01 export floor.
  No labels, detector settings, or protected source/test files changed.
- Scoring created two separate 45-cell grids, containing 270 per-window
  evaluation reports in total. Representative labels have 75 eligible centers;
  challenge labels have 70 centers plus five reviewed hidden-ball frames.
- Both visual packages were rendered and passed bundle-integrity verification:
  150 synchronized comparison frames, 150 truth-region panels, 300 full-resolution
  overlays, and six 25-frame videos. Every final frame is present. All six
  videos were fully decoded for validation. H.264 playback copies are provided
  for app playback; original bound MP4V videos and PNGs are unchanged.
- Agent inspection covered all six final-frame closeups and selected P003
  occlusion-boundary images (164, 165, 169, 170). Ryan subsequently approved the
  six linked comparison clips: "the videos look good. they pretty much track
  the whole trajectory of the ball, with small little blips of possible
  detections. overall though it looks pretty solid to start". The new review
  receipt preserves this exact statement and binds both packages and all six
  playback clips. This is approval of the visual evidence as a starting point,
  not a quantitative quality gate or a claim of complete temporal trajectories.
- No operating point, quality gate, model winner, or generalization claim was
  selected. All three test holdouts remain sealed. The unchanged parent v0.1
  manifest retains nine embargoes and all nine of its old prediction paths
  remain absent. The six new versioned development outputs are the only newly
  generated predictions authorized by this release.
- Execution, scoring, and rendering all completed with a clean worktree at the
  exact activation commit. Later context, roadmap, and validation-history edits,
  the new visual-review receipt, and a temporal-association proposal remain
  uncommitted; the index is empty. Generated media/results remain Git-ignored.

### Results at the two predeclared display settings

Both use the protocol's 10-pixel localization tolerance with stored label
uncertainty. These are descriptive views, not selected operating points.

| Pool | Confidence | Correct matches | False guesses | Misses | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Representative | 0.20 | 47 | 105 | 28 | 30.9% | 62.7% |
| Representative | 0.35 | 39 | 12 | 36 | 76.5% | 52.0% |
| Challenge | 0.20 | 48 | 53 | 22 | 47.5% | 68.6% |
| Challenge | 0.35 | 41 | 9 | 29 | 82.0% | 58.6% |

P001 is the weakest possession in both displayed views. In P003's five
hidden-ball frames, the 0.20 view includes four false candidates across three
frames; 0.35 includes one false candidate. Frame 164 has an offset candidate
at 0.20 that still counts as FP plus FN under the displayed localization rule.
The six reviewed annotation sets, all approval receipts, the frozen parent,
and the historical pilot scoring report retain their original hashes.

### Evidence and exact next action

- Review guide: `data/outputs/ball_tracking/development_execution/84bcc8da143e/review_guide.md`.
  It links all six playback clips, every final-frame closeup, all-frame contact
  sheets, both full scoring grids, and their review manifests.
- Audited run record: `data/outputs/ball_tracking/development_execution/84bcc8da143e/execution_record.json`.
  This binds all detection/report/visual files and records the exact scope of
  agent image inspection. Its execution-time pending-review state is preserved;
  the later receipt below records completion. Runtime warnings are retained
  in the inference log; the installed source documents `_kp_active_mask` as a
  deterministic keypoint buffer. No package or model configuration was changed.
- Representative visual bundle:
  `data/outputs/ball_tracking/detection_review/rfdetr_medium_development_evaluation_v0_2_representative_evaluation_comparison/5ca366b16581f0a2156f1b64badd39e1`.
- Challenge visual bundle:
  `data/outputs/ball_tracking/detection_review/rfdetr_medium_development_evaluation_v0_2_challenge_evaluation_comparison/a8e607388bfbb511212b3956a63f55a3`.
- Human review receipt:
  `configs/ball_tracking/reviews/rfdetr_medium_development_candidate_comparison_review_record_v0_1.json`,
  SHA-256 `a60dea646736135620fb97eba9f1985f7b06f0c7bfc7abee38537580c05f4dba`.
  Its timestamp is receipt creation time, not an invented message event time.
  Both bundle-integrity checks, all six original/playback clip hashes, all 59
  protected file hashes/Git blobs, and all nine absent old outputs passed again.
- Candidate-availability diagnostic:
  `data/outputs/ball_tracking/development_execution/84bcc8da143e/candidate_availability_diagnostic.json`,
  SHA-256 `2bf4efc3bf94472c8f5411fd28194c72a308584ece6faab071841cb856cf55b3`.
  At the stored 0.01 floor and 10-pixel scoring radius, P001 has a qualifying
  candidate in only 10/25 representative and 18/25 challenge frames. These are
  label-assisted ceilings for retaining original candidate centers at those
  settings, not achievable tracking results. No inference or scoring was rerun.

Next: review the concrete design in
`docs/ball_temporal_association_experiment_proposal.md` and implement its
synthetic-first support before proposing a new execution manifest. It compares
raw candidates, a highest-confidence control, and causal tracklets using only
the six saved development outputs. No tracker has been implemented or run.
The completed visual review need not be requested again. The new proposal is
not an execution permit, operating-point choice, or quality gate. Keep all
holdouts sealed. Completed detector artifacts remain bound to `84bcc8d`;
inspect them without overwriting them or changing provenance to bypass resume
checks. No unrun manual command was left with Ryan. Staging, further commits,
and pushing need separate authorization. No production code changed this turn;
the existing full-suite result remains 299 run, 298 passed, one capability skip.

The release-preparation and annotation snapshots below are historical. This
section supersedes their old Git states and next-action instructions.

## Earlier release-preparation checkpoint

Verified 2026-09-19 UTC (2026-09-18 America/Phoenix).

- Branch: `codex/ball-detector-baseline`.
- Exact HEAD: `9521569cab36c8d289c4a341b5f33273062cabb4`.
- Commit: `feat(ball-tracking): add approved development evaluation support`.
  Ryan separately authorized staging the 35-file scope and then said
  "yes commit please". The commit contains exactly those 35 files; their
  working-file bytes were preserved. Nothing was pushed.
- The clean evidence commit passed release preparation using the repository
  `.venv` with bytecode disabled: full-suite return code 0, 299 tests recorded,
  all six annotation approval chains and 330 review assets verified. The
  validation report binds 59 protected code, test, label, receipt, and proposal
  files to the evidence commit's Git blobs.
- Ignored validation report:
  `data/outputs/ball_tracking/release_evidence/9521569cab36c8d289c4a341b5f33273062cabb4/validation.json`.
  Its copied evidence file has SHA-256
  `9a47a6c4e48a77cf0e91311faceae085956a61952ae01697064d0bf778ef03b4`.
- The approved preparation command created five new activation files: evidence
  copy, release receipt, v0.2 experiment manifest, and two pool review plans.
  Their hashes, approval/parent bindings, exact six-window scope, and global
  window/run/output uniqueness were verified. This context file is the sixth
  proposed release-checkpoint file.
- Current worktree: five untracked activation JSON files and this modified
  context file; the index is empty. No activation file has been staged or
  committed. Runtime release validation correctly refuses this uncommitted
  state before model construction.
- The parent v0.1 manifest is unchanged with all nine historical embargoes.
  None of its nine embargoed prediction files or the six new development
  prediction files exists. The new manifest names only the approved six
  development windows (150 frames); all three holdouts stay sealed.
  No operating point or quality gate was selected, and no real inference ran.

The next step is separate staging authorization for the six exact files below,
followed by review of their staged contents and separate commit authorization.
Ryan's experiment approval is already recorded; do not request it again.
After that activation commit, run the existing detector's dry-run preflight,
then the approved six-window experiment, separate-pool scoring, and both visual
review plans. Do not modify protected source/labels or relax any gate. Ryan
must review the resulting real visual evidence; push remains unauthorized.

### Proposed release-checkpoint staging scope

```text
configs/ball_tracking/reviews/rfdetr_medium_development_evaluation_v0_2_9521569cab36_evidence.json
configs/ball_tracking/reviews/rfdetr_medium_development_evaluation_v0_2_9521569cab36_release.json
configs/ball_tracking/experiments/rfdetr_medium_development_evaluation_v0_2.json
configs/ball_tracking/reviews/rfdetr_medium_development_evaluation_v0_2_representative_evaluation_comparison.json
configs/ball_tracking/reviews/rfdetr_medium_development_evaluation_v0_2_challenge_evaluation_comparison.json
docs/context/current_state.md
```

The checkpoint below records the earlier annotation/implementation work.
Its old HEAD, uncommitted status, and next-action statements are historical;
this section supersedes them. Always verify current Git state first.

## Earlier annotation and implementation checkpoint

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
