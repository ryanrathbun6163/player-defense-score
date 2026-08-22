# Current State

Snapshot date: 2026-08-22 (America/Phoenix)

## Repository checkpoint

The local checkout under the user's OneDrive Desktop was inspected read-only.

At inspection time:

- branch: `main`;
- local HEAD: `1954053` (`Merge pull request #5 from .../pipeline-generalization`);
- worktree: clean;
- locally recorded `origin/main`: `1954053`;
- full test suite: 56 tests passed using the desktop app's bundled Python, with bytecode writing disabled.

GitHub is one merge ahead of the local checkout. PR #6, **Document player-defense pipeline and roadmap**, was merged on 2026-08-18. Its merge commit is `2cb98b4`; it changes only `README.md`. The local checkout has not been fetched or fast-forwarded during this migration.

Do not treat the stale local `origin/main` reference as proof that the remote is unchanged. Before development, perform a normal read-only status check, fetch, review the incoming README-only change, then fast-forward local `main` with Ryan's approval.

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

## Not complete

- ball detection/tracking and its quality gate;
- automatic possession segmentation and broadcast-cut handling;
- ball-handler and event inference;
- mapping visual identities to NBA rosters;
- primary-defender, switch, help, and contest inference;
- the defensive scoring model;
- complete-game NBA validation and reporting.

## Immediate next task

Start the ball-tracking phase as an evidence-first evaluation, not as an immediate production implementation:

1. define representative ball-tracking failure modes and annotation format;
2. select small curated clips from the validated possessions;
3. create ground truth or reviewed labels;
4. benchmark candidate basketball detectors and temporal association strategies;
5. render synchronized ball/player/court review output;
6. define quantitative and visual gates across multiple possessions;
7. only then integrate the chosen approach into the resumable pipeline.

No ball-tracking implementation was started in chats 01–06. The prior blocker was intentionally removed only after Possession 003 passed the generalization gate.

## Local data checkpoint

The ignored `data/` tree contains 856 files totaling 6,710,202,697 bytes. Every file was SHA-256 hashed successfully during migration; see the external migration manifest `manifests/local-data-files.csv`. The data tree has not been moved, renamed, copied, or edited.
