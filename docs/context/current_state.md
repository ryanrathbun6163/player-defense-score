# Current State

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
