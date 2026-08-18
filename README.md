# Player Defense Score

An end-to-end computer vision and basketball analytics project for reconstructing player movement from broadcast video and ultimately measuring possession-level defensive impact.

The long-term goal is to turn a full NBA broadcast into auditable player and ball trajectories, infer defensive matchups and play outcomes, and produce a transparent defender score that can be aggregated across possessions and games.

> [!IMPORTANT]
> This project is under active development. The player-coordinate foundation is working and has passed a multi-possession empirical generalization gate on curated 20-second clips. Ball tracking, automatic possession segmentation, matchup inference, outcome recognition, defensive scoring, and full-game NBA validation are not yet complete.

## Project status

The repository currently contains a configuration-driven, resumable **21-stage player-coordinate pipeline** covering:

- person detection and multi-object tracking;
- playable-court filtering and track-quality auditing;
- jersey-color feature extraction and team classification;
- player ReID embeddings, temporal segmentation, and segment matching;
- reviewed consolidation into exactly ten persistent player identities;
- reference-frame court calibration and per-frame camera-motion compensation;
- projection from image coordinates into real court coordinates;
- conservative trajectory correction and internal-gap interpolation;
- synchronized videos, checkpoint images, reports, and audit files for review.

The pipeline was developed across three curated possessions:

- **Possession 001** established the reviewed behavioral baseline.
- **Possession 002** exposed camera-motion, identity, and generalization failure modes and drove the configuration and safety refactors.
- **Possession 003** completed all 21 stages without possession-specific source edits and passed the empirical generalization gate.

### Possession 003 validation

| Metric | Result |
| --- | ---: |
| Decoded frames with a camera homography | 500 / 500 (100.00%) |
| Player-frame coordinate coverage | 4,921 / 5,000 (98.42%) |
| Complete ten-player frames | 431 / 500 (86.20%) |
| Final player identities | 10 (5 white, 5 dark) |
| Unresolved reviews | 0 |
| Coordinate-key violations | 0 |
| Final motion-jump candidates | 0 |
| Final outside-court coordinates | 0 |

The empirical thresholds require at least 95% coordinate coverage and at least 85% complete expected-player frames. Possession 003 passed both thresholds, unlocking the next major phase: **ball tracking**.

The committed evidence is available in [`configs/possession_003_generalization_evidence.json`](configs/possession_003_generalization_evidence.json). The design and validation details are documented in [`docs/pipeline_generalization.md`](docs/pipeline_generalization.md).

## End goal

The intended production pipeline is:

```text
Full NBA broadcast
        |
        v
Game and possession segmentation
        |
        v
Player + ball detection and tracking
        |
        v
Persistent player identity + roster association
        |
        v
Camera calibration + court-coordinate reconstruction
        |
        v
Ball-handler, matchup, help-defense, and event inference
        |
        v
Possession-level defensive features and outcome labels
        |
        v
Transparent defensive score
        |
        v
Per-matchup, per-player, and per-game reports
```

The final system should answer questions such as:

- Who was the primary defender on a possession?
- How closely did the defender contest the ball handler or shooter?
- Did the defender stay attached through screens and switches?
- When did help defense arrive, and how did it affect the play?
- Did the possession end in a made shot, miss, turnover, foul, or reset?
- How much positive or negative defensive value should be assigned to each involved defender?

The initial NBA case study is the February 23, 2026 San Antonio Spurs vs. Detroit Pistons game, with an initial matchup focus on **Stephon Castle defending Cade Cunningham**.

## Why this is difficult

Broadcast basketball is not a fixed-camera tracking problem. A reliable system has to account for:

- camera pans, zooms, cuts, replays, and score overlays;
- players entering and leaving the frame;
- heavy occlusion and visually similar uniforms;
- raw tracker fragmentation, duplicate boxes, and identity switches;
- a small, fast-moving, frequently occluded basketball;
- changing lineups, substitutions, and off-screen players;
- perspective distortion and court markings that may be partially hidden;
- uncertainty in defensive assignments, switches, help rotations, and outcomes.

For that reason, this repository treats review evidence and failure visibility as first-class outputs. The pipeline pauses at explicit human-review gates instead of silently forcing uncertain identity or calibration decisions.

## Current pipeline

The 21 stages are declared in [`src/pipeline/planner.py`](src/pipeline/planner.py) and executed through a possession manifest.

| # | Stage | Purpose | Mode |
| ---: | --- | --- | --- |
| 1 | `court_polygon` | Select the playable-court region on a reference frame. | Interactive |
| 2 | `tracking` | Detect and track court-filtered people. | Automatic |
| 3 | `tracking_audit` | Audit counts, continuity, short tracks, and handoff candidates. | Automatic |
| 4 | `uniform_features` | Extract aggregate jersey-color features by raw track. | Automatic |
| 5 | `team_classification` | Assign white, dark, or unknown team labels. | Automatic |
| 6 | `reid_embeddings` | Extract sampled OSNet-AIN appearance embeddings. | Automatic, GPU |
| 7 | `reid_segmentation` | Split raw tracks at temporal or reviewed appearance boundaries. | Automatic with overrides |
| 8 | `segment_matching` | Generate strict and reviewable segment matches. | Automatic with overrides |
| 9 | `identity_review_cycle` | Consolidate segments into the expected players and team balance. | Human review gate |
| 10 | `identity_visualization` | Render and validate persistent player identities. | Review output |
| 11 | `calibration_preparation` | Prepare candidate court-calibration frames and motion evidence. | Review output |
| 12 | `court_landmarks` | Select image-to-court landmark correspondences. | Interactive |
| 13 | `calibration_review_gate` | Record reviewed landmark corrections and fit choices. | Human review gate |
| 14 | `calibration_finalize` | Apply reviewed decisions to the reference homography. | Review output |
| 15 | `boundary_refinement` | Constrain the visible camera-side court boundary. | Interactive |
| 16 | `camera_motion` | Propagate and audit one camera homography per frame. | Review output |
| 17 | `coordinate_export` | Project player floor points into court coordinates. | Automatic |
| 18 | `coordinate_review` | Render synchronized source and top-down coordinates. | Review output |
| 19 | `trajectory_refinement` | Correct implausible observations conservatively with an audit trail. | Audited correction |
| 20 | `gap_interpolation` | Fill only bounded internal gaps with suitable anchors. | Audited interpolation |
| 21 | `final_coordinate_review` | Render the final synchronized coordinate foundation. | Review output |

## Design principles

### Configuration instead of possession-specific code

Each possession is described by a JSON manifest containing its video path, reference frame, expected player/team counts, court geometry, and reviewed algorithm parameters. `PipelinePaths` derives possession-scoped config and output paths from that manifest.

Adding a new possession should require a new manifest and review decisions—not edits to Python source files.

### Resumable execution

The runner records ignored state under `data/outputs/pipeline`. Rerunning the same command skips stages whose commands, inputs, and manifest signatures have not changed. Failed stages retry on the next run, and reviewed upstream corrections can deliberately invalidate all downstream stages.

### Human review is explicit

Identity reconciliation and court calibration remain explicit review gates. The pipeline generates candidate reports, montages, synchronized videos, and checkpoint frames, then pauses with the exact reason and review commands.

### Missingness is better than fabricated certainty

Trajectory correction and gap interpolation are intentionally conservative. Corrections are audited, only bracketed internal gaps are eligible for interpolation, and observations without sufficient evidence remain missing.

### Generated media stays out of Git

Raw video, clips, model outputs, review videos, coordinate exports, and diagnostic archives are intentionally ignored. The repository commits source code, tests, configuration, and compact validation evidence—not copyrighted footage or large generated artifacts.

## Repository structure

```text
player-defense-score/
|-- configs/                      # Per-possession manifests and reviewed decisions
|-- data/
|   |-- raw/                      # Full source broadcasts (ignored)
|   |-- clips/                    # Possession clips (ignored)
|   `-- outputs/                  # Tracking, ReID, coordinates, reviews (ignored)
|-- docs/                         # Pipeline design and validation notes
|-- src/
|   |-- classification/           # Uniform features and team classification
|   |-- court/                    # Calibration, homographies, coordinates, trajectories
|   |-- identity/                 # Identity construction and review helpers
|   |-- pipeline/                 # Manifests, planning, execution, and gates
|   |-- reid/                     # Appearance embeddings and segment review
|   |-- tracking/                 # RF-DETR, ByteTrack, audits, reconciliation
|   `-- visualization/            # Identity and court-coordinate review videos
|-- tests/                        # Unit, regression, and safety tests
|-- README.md
`-- requirements.txt
```

## Technology stack

- **Python 3.11**
- **PyTorch + CUDA** for GPU inference
- **RF-DETR Medium** for person detection
- **ByteTrack** through the `trackers` package for multi-object tracking
- **OSNet-AIN** appearance embeddings for player ReID
- **OpenCV** for video processing, geometry, calibration, and rendering
- **NumPy / SciPy** for numerical processing and trajectory analysis
- **FFmpeg** for clip preparation and media inspection

The current development environment uses an NVIDIA GPU, but most review, planning, and validation tools are CPU-capable. ReID embedding extraction and detector inference are the primary GPU stages.

## Setup

### Prerequisites

- Git
- Python 3.11
- FFmpeg available on `PATH`
- An NVIDIA GPU and compatible CUDA-enabled PyTorch build are strongly recommended

### Windows PowerShell

```powershell
git clone https://github.com/ryanrathbun6163/player-defense-score.git
cd player-defense-score
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The pinned PyTorch packages target a CUDA build. If that build does not match the machine, install the appropriate PyTorch package for the local CUDA environment before installing the remaining requirements.

## Running a possession

### 1. Add the local clip

Place the source clip under `data/clips/`. Video files are ignored by Git.

### 2. Create a possession manifest

Use one of the committed manifests as a starting point:

- [`configs/possession_001_pipeline.json`](configs/possession_001_pipeline.json)
- [`configs/possession_002_pipeline.json`](configs/possession_002_pipeline.json)
- [`configs/possession_003_pipeline.json`](configs/possession_003_pipeline.json)

At minimum, update the possession ID, video path, reference frame, expected counts, court profile, and any reviewed overrides.

### 3. Validate the plan

```powershell
python -m src.pipeline.run_player_coordinates --config configs/possession_003_pipeline.json --dry-run --check-inputs
```

The dry run validates the manifest and prints all stage and review commands without executing the pipeline.

### 4. Execute or resume

```powershell
python -m src.pipeline.run_player_coordinates --config configs/possession_003_pipeline.json --run
```

The runner stops normally when human review is required. Record the review decisions, then rerun the same command to resume.

### 5. Deliberately rerun an upstream stage

```powershell
python -m src.pipeline.run_player_coordinates --config configs/possession_003_pipeline.json --run --rerun-from reid_segmentation
```

This invalidates the selected stage and every downstream stage without requiring broad manual output deletion.

## Validation and tests

Run the test suite with the standard library test runner:

```powershell
python -m unittest discover -s tests -v
```

Verify the reviewed Possession 001 identity baseline without retaining temporary outputs:

```powershell
python -m src.pipeline.verify_existing_player_identity --config configs/possession_001_pipeline.json
```

Evaluate the committed Possession 003 evidence against the baseline generalization gate:

```powershell
python -m src.pipeline.run_player_coordinates --config configs/possession_001_pipeline.json --dry-run --gate-evidence configs/possession_003_generalization_evidence.json
```

The gate validates structural generalization, completed stages and reviews, homography coverage, coordinate coverage, complete-player frames, unique coordinate keys, audited boundaries, final-frame visual review, and output hygiene.

## Roadmap

### Phase 1 — Player-coordinate foundation (completed for curated possessions)

- [x] Person detection and court filtering
- [x] Multi-object tracking and continuity audits
- [x] Team classification
- [x] Player ReID and identity consolidation
- [x] Reference court calibration
- [x] Per-frame camera-motion compensation
- [x] Player court-coordinate export
- [x] Audited trajectory refinement and gap interpolation
- [x] Resumable configuration-driven orchestration
- [x] Multi-possession empirical generalization gate

### Phase 2 — Ball tracking (next)

- [ ] Evaluate and select a small-object basketball detector
- [ ] Create labeled ball-detection and tracking evaluation clips
- [ ] Track the ball through motion blur, occlusion, passes, shots, and rebounds
- [ ] Fuse detections temporally and preserve uncertainty
- [ ] Render synchronized ball and player trajectories
- [ ] Define ball-tracking quality gates across multiple possessions

### Phase 3 — Possession and event understanding

- [ ] Segment full broadcasts into live possessions
- [ ] Detect camera cuts, replays, dead-ball periods, and transitions
- [ ] Infer ball possession and ball-handler changes
- [ ] Recognize passes, shots, rebounds, turnovers, and fouls
- [ ] Associate events with players and court locations

### Phase 4 — NBA player identity and lineup context

- [ ] Map visual identities to rostered NBA players
- [ ] Incorporate jersey-number recognition and game metadata
- [ ] Track substitutions and lineup changes
- [ ] Maintain identity across possessions and broadcast interruptions

### Phase 5 — Defensive matchup inference

- [ ] Infer primary on-ball assignments
- [ ] Detect switches, help rotations, traps, and recoveries
- [ ] Measure defender-ball-handler distance, angle, and closing speed
- [ ] Quantify screen navigation, contest quality, and rim protection
- [ ] Represent uncertainty when assignments are ambiguous

### Phase 6 — Defensive scoring model

- [ ] Define transparent possession-level features and outcome weights
- [ ] Build a human-labeled evaluation set
- [ ] Compare heuristic and learned scoring approaches
- [ ] Validate stability across teams, players, lineups, and game contexts
- [ ] Aggregate possession scores into matchup, player, and game summaries

### Phase 7 — Full NBA-game scale

- [ ] Replace the current NFHS right-half-court profile with NBA court profiles
- [ ] Support both directions of play and full-court transitions
- [ ] Process broadcast cuts, overlays, bench views, and replays robustly
- [ ] Batch GPU work and checkpoint long-running jobs
- [ ] Reduce manual reviews while retaining auditable confidence thresholds
- [ ] Validate complete games rather than curated 20-second clips

### Phase 8 — Reporting and product layer

- [ ] Produce possession-level JSON and review clips
- [ ] Build per-player and per-matchup reports
- [ ] Add interactive court visualizations and game timelines
- [ ] Expose stable outputs through a CLI, API, or dashboard

## Current limitations

- Validation currently covers curated 20-second possessions, not complete NBA games.
- Player identity and court calibration still include human-review gates.
- Current validated court manifests use an NFHS right-half-court model.
- Team labels are visual categories (`white`, `dark`, `unknown`), not NBA roster identities.
- Ball tracking and basketball event recognition have not yet been integrated.
- Defensive assignments and the final defender score have not yet been implemented.
- Broadcast footage and generated outputs are not included in the repository.

## Data and media

This repository does not distribute game footage. Raw broadcasts, possession clips, generated crops, embeddings, CSV files, NPZ archives, reports, and rendered review videos belong under ignored `data/` paths.

Anyone running the project is responsible for obtaining and using video in accordance with the applicable copyright, licensing, and platform terms.

## Development philosophy

The purpose of this project is not merely to draw plausible tracks over video. It is to build a measurement pipeline whose decisions can be inspected and defended.

That means:

- uncertain identity decisions are reviewed instead of hidden;
- geometry is validated visually across time rather than trusted from one frame;
- corrections and interpolations retain audit trails;
- quality gates are quantitative and possession-independent;
- generated data remains reproducible from committed code and configuration;
- each new phase must generalize before the next analytical layer is trusted.

The immediate next milestone is a similarly auditable ball-tracking foundation. Once reliable player and ball trajectories coexist in court coordinates, the project can begin reasoning about possession state, matchups, defensive actions, and outcomes.
