# Player Defense Score

An end-to-end computer vision and basketball analytics project for reconstructing player movement from broadcast video and ultimately measuring possession-level defensive impact.

The long-term goal is to turn a full NBA broadcast into auditable player and ball trajectories, infer defensive matchups and play outcomes, and produce a transparent defender score that can be aggregated across possessions and games.

> [!IMPORTANT]
> This project is under active development. The player-coordinate foundation is working and has passed a multi-possession empirical generalization gate on curated 20-second clips. Ball tracking, automatic possession segmentation, matchup inference, outcome recognition, defensive scoring, and full-game NBA validation are not yet complete.

## Project status

The approved [ball-phase completion campaign](docs/ball_tracking_completion_plan.md)
has started. Its [first increment](docs/ball_tracking_completion_first_increment.md)
delivers the retained-baseline player/ball development package, fixes four NBA
game roles and 24 episode windows, and publishes 120 new P003 assisted references
accepted by Ryan. Remaining labels still need review; no new fit or phase pass is
claimed. The rejected crop verifier and retained WASB baseline remain intact.
Ryan also accepted the [second reference batch](docs/ball_tracking_completion_reference_batch_02.md):
120 P002 judgments, including uncertainty and null centers. Accepted curated
coverage is now 560/1,273 frames; the earlier 440 references remain unchanged.

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

The [sports-video research collection](docs/research/README.md) compares ball models, player tracking, court geometry, complete sports pipelines, datasets and analytics using primary sources and selected implementation inspection. The subsequent [WASB basketball transfer comparison](docs/ball_wasb_transfer_results.md) completed on all six development windows: at its published heatmap threshold it matched 31/145 eligible frames, emitted no wrong selections, and left 114 eligible frames missing. This coverage is insufficient to replace the saved RF baseline; no method or quality gate is promoted. The tested RF/YOLO agreement rule also has a [recovered negative result](docs/ball_crop_cross_detector_corroboration_results.md).

The approved [pilot adaptation trial](docs/ball_wasb_adaptation_results.md) is
complete. At the original threshold, trained WASB improves from 31 to **98/145
matched positions**, with one wrong output, 46 missing eligible frames and zero
alarms on the five hidden frames. RF ranked to the same output counts gives
90 matches and nine wrong outputs. Training used only the 75 reviewed pilot
frames; the 150 development frames stayed out of training. This is useful
same-game development evidence, not ball-phase completion: 39 of the 46 missing
frames are in possession 001. Ryan reviewed all six new videos and authorized
continued work with distractor observations recorded; holdouts and the quality
bar remain unchanged. The earlier
[calibration-only result](docs/ball_wasb_calibration_results.md) remains preserved.

The [remaining-gap diagnosis](docs/ball_wasb_remaining_gap_diagnosis.md) found
that lower thresholds and strongest-pixel selection do not resolve P001's main
failure. A [75-frame training-data addition](docs/ball_wasb_training_data_expansion.md)
is now complete: Ryan labeled and reviewed all 75 additions, then one original-
initialized 200-update fit ran successfully. The [expanded-data comparison](docs/ball_wasb_expanded_adaptation_results.md)
raises primary matches from **98 to 120/145** and halves missing frames from 46
to 23, with two geometric errors and no hidden alarms. P001 improves from 11 to
34 matches. The existing threshold grid also gives **130 matches, one error and
14 missing at 0.3**. That setting is a visual-review candidate, not an accepted
operating point. Complete possession trajectories and phase acceptance remain ahead.

A [longer development observation pass](docs/ball_wasb_development_observation.md)
now provides three synchronized 20-second review timelines using that frozen
0.3 candidate. Across 1,273 visible frames it emits 979 points and leaves 294
missing; these unlabeled, training-inclusive counts are **not accuracy**. Sealed
holdouts and buffers appear as black sections. The run completed without retry,
reusing prior predictions, and Ryan reviewed all three videos. The labeled
improvement stands; reliable continuous ball tracking remains unfinished.

The subsequent [fixed motion-selection comparison](docs/ball_wasb_motion_selection.md)
is complete. On identical longer-context labeled frames, native mass and motion
both give **131 matches, one error, 13 missing and no hidden alarms**. Motion
changes no scored choice. It removes some distractors elsewhere, but also drops
visible ball observations during recovery; this rule is not promoted. All
originally empty frames remain empty. Three new comparison videos and a complete
changed-frame AI review preserve the negative result; their human review is pending.

The approved [NBA native-cadence pilot diagnostic](docs/nba_wasb_native_pilot_diagnostic_results.md)
is complete. The frozen expanded WASB checkpoint at strict `>0.3` matches
**60/60 accepted reference positions in each game**, with no wrong or missing
outputs at the fixed ten-pixel radius. Mean center distances are 2.779 pixels
for SAC–MEM and 2.894 for SAS–DET. One run completed all 116 native three-frame
inputs without training. These two short, visible-ball scenes use human-accepted
AI references; they are not an independent NBA benchmark or a ball-phase pass.
Ryan reviewed both complete model-output videos and accepted the predictions
on October 19. Ryan subsequently approved the [longer action observation](docs/nba_wasb_action_observation_plan.md),
which completed across the two existing cores: 2,702 native frames, about 45
seconds total. It emits 2,380 observations and leaves 322 frames missing; these
are availability counts, not accuracy. AI inspection finds spectator/head
distractors and visible-ball gaps. Independent saved-output verification and
both complete videos passed transport checks. The
[results and new review videos](docs/nba_wasb_action_observation_results.md)
preserve these limitations. After both complete videos were delivered in chat
for phone viewing, Ryan reported: “Ok reviewed. What’s the next step”. This
records review completion, without playback telemetry or an explicit quality
endorsement. Ryan then approved the [520-frame reference batch](docs/nba_hard_example_reference_plan.md):
“Ok move forward”. Ryan has now accepted all four complete
[label-review packages](docs/nba_hard_example_reference_review.md) without
corrections. The separate accepted AI reference retains **387 defensible centers
and 133 unknown centers**. The [saved-output diagnostic](docs/nba_hard_example_reference_results.md)
finds 305 matches, 13 localization errors and 69 missing outputs among the 387
eligible frames, plus 13 alarms in 86 hidden-ball frames. The 120 easy controls
remain 120/120 in their longer context. None of the 82 localization failures has
an alternative saved candidate within ten pixels, so reranking the existing
candidates cannot recover them. The approved [saved-heatmap inspection](docs/nba_hard_example_heatmap_inspection_results.md)
reconstructed all 640 original means exactly. Missing frames have weak ball-region
responses (median 0.118); only 11/69 had above-threshold support in an individual
contributor that disappeared in the mean. Changing component centers to peaks
would recover three wrong locations but lose six current matches. These findings
led to the approved [bounded NBA continuation](docs/nba_wasb_adaptation_plan.md)
using SAC alongside eligible NFHS training examples, with DET excluded from
fitting. The [fixed comparison](docs/nba_wasb_adaptation_results.md) after one
200-update fit **fails its numerical screen**, so the expanded baseline is
retained. SAC training-fit matches improve from 218 to 265 of 270, but DET
matches fall from 207 to 206 of 237 and wrong locations rise from eight to ten.
NFHS matches fall from 130 to 129 of 145. Eight complete synchronized videos
passed media checks, and independent training/comparison audits passed. Ryan
reported reviewing the three inline embeds covering both NBA videos and all six
NFHS windows through the verified compilation: “Ok I reviewed these chat. What’s
the next step?” The [later review record](configs/ball_tracking/reviews/nba_wasb_adaptation_visual_review_v0_1.json)
records completion without playback telemetry or an explicit quality endorsement.
The failed screen and retained baseline are unchanged. No second fit or threshold
tuning followed.
Ryan then authorized the [37-frame diagnostic](docs/nba_adaptation_regression_diagnostic_results.md):
“Ok move forward chat. Run the 37-frame diagnostic.” It compares existing old/new
heatmaps around six lost matches and four recoveries, preserving their original
contexts and fixed scoring rules. One 2.375-second run reproduced all 74 means
and passed independent audit. It found a stronger distractor overtaking a correct
candidate, a marginal weighted-center error, and four NFHS means losing support
despite an individual above-threshold response. These are distinct mechanisms;
the diagnostic changes no prediction. The subsequently approved
[candidate-preservation experiment](docs/nba_candidate_preservation_experiment.md#completed-comparison)
is complete. The retained baseline gains six available DET positions and three
NFHS positions, covering nine of 45 previously unavailable development frames;
36 still have no matching candidate. The expanded pool also adds 51 ambiguous
frames and five nonempty DET hidden frames. This modest gain supports one future
fixed selector trial; no selected prediction changed in that availability experiment.
Ryan then approved the [temporal gap-selection trial](docs/nba_temporal_gap_selection_experiment.md#completed-single-run-result):
“Ok awesome move forward chat”. One frozen rule now recovers **two DET matches
and one NFHS match**, raising selected matches to 209/237 and 131/145 respectively,
with no additional wrong outputs or hidden alarms and both easy controls still
60/60. SAC stays unchanged. The numerical gates pass, and Ryan explicitly
[approved the three comparisons](configs/ball_tracking/reviews/nba_temporal_gap_selection_visual_review_v0_1.json).
The bounded increment is accepted. Ryan separately authorized the
[continuous-context validation](docs/nba_temporal_gap_continuous_validation_results.md)
with “Move forward chat”. Its saved-evidence comparison passes all 24 numerical
conditions across 3,975 permitted frames, preserving all 3,359 original points.
Visual inspection identifies an adverse unlabeled case: at SAC source frame 1420
(14.681 seconds into its comparison), the added point lies on a defender's head,
between original head-tracking anchors at 1419 and 1421. This frame is outside
the 790 scored references, so the numerical results remain unchanged. Broader
adoption of the unchanged rule is not recommended from these results.
It adds 14 points in ten gaps: three labeled matches and eleven unscored points.
Against the same-context controls, DET improves **207→209/237** and NFHS
**131→132/145**, with no new wrong outputs or hidden alarms and both NBA easy
controls still 60/60. The earlier short-window NFHS baseline of 130 matches is
kept separate from the longer-context control. The first attempt's imported-cache
identity failure and its corrected recovery remain recorded. Twenty-one focused
tests and 42,844 independent audit checks pass. The
[compact result](configs/ball_tracking/reviews/nba_temporal_gap_continuous_validation_result_v0_1.json)
records the evidence. Ryan subsequently reported reviewing all five complete
comparisons: “Ok videos reviewed. What’s next chat”. The
[later review record](configs/ball_tracking/reviews/nba_temporal_gap_continuous_visual_review_v0_1.json)
records completion without an explicit quality endorsement or broader-rule
adoption. The head-fill finding and uncertain NFHS cases remain. Continuous
tracking and ball-phase completion remain ahead.
The approved [gap/anchor reference preparation](docs/nba_gap_anchor_reference_results.md)
is complete, and Ryan accepted its 27 new AI judgments after review:
“ok great chat they have been reviewed. move forward”. The
[acceptance record](configs/ball_tracking/reviews/nba_gap_anchor_reference_acceptance_v0_1.json)
preserves AI authorship and five unknown centers. The separate
[saved-output evaluation](docs/nba_gap_anchor_reference_evaluation_results.md)
gives **14→22 geometric matches**, zero wrong outputs and **8→0 missing** among
22 eligible new references; five remain unscored. Eight of eleven new fills
match, while three are unscored. Seven accepted controls reproduce exactly and
are excluded from the new denominator; the original 790-frame report is unchanged.
The [compact result](configs/ball_tracking/reviews/nba_gap_anchor_reference_evaluation_result_v0_1.json)
binds the evidence. Geometric matches do not validate object identity: six P001
points remain visually unresolved, and the three SAC head points remain adverse,
unscored evidence. Reference acceptance does not separately adjudicate those AI
object judgments. Ryan then approved the
[appearance-reference preparation](docs/nba_appearance_reference_preparation.md)
with “Move forward chat”, preserved in the
[approval record](configs/ball_tracking/reviews/nba_appearance_reference_preparation_approval_v0_1.json).
The [completed preparation](docs/nba_appearance_reference_results.md)
and [compact result](configs/ball_tracking/reviews/nba_appearance_reference_result_v0_1.json)
cover 26 saved mean candidates at 15 targets with 75 native context frames.
SAC/P002 supply 15 potential-fit objects; DET/P003 supply eleven excluded checks,
with prior training and development exposure disclosed. The existing gap/anchor
regression package stays separate. A complete 48-second review is verified for
all 75 source frames; independent audit passes 1,649 checks. AI still inspection
covers all fifteen targets, fifteen context finals and the actual final frame.
Ryan then explicitly accepted all 26 proposals: “I accept the proposals. Move
forward chat”. The [separate accepted publication](docs/nba_appearance_reference_acceptance_results.md)
retains ten ball, ten other-object and six unresolved judgments, AI authorship
and the recorded reader disagreement. The original draft and media remain intact.
Publication took 0.696 seconds; six focused tests and 380 independent audit
checks pass. The [publication result](configs/ball_tracking/reviews/nba_appearance_reference_publication_result_v0_1.json)
binds the evidence, and this appearance-label review is complete.

The approved [fixed appearance-feature screen](docs/nba_appearance_feature_screen_results.md)
is complete and **failed its feasibility gate**: eight of ten accepted checks
correct, including only four of six balls. All three points in the known SAC
head episode still preferred ball; four valid DET near-head balls were retained.
One 12.594-second run encoded 60 crops from 49 cached frames. Six focused tests,
an independent audit of all 500 similarities and complete crop/neighbor review are done.
This exact setup is rejected without tuning or trajectory changes. Six unknowns
remain unscored; 34 old AI-assessed points stay a separate qualitative supplement.
The [compact result](configs/ball_tracking/reviews/nba_appearance_feature_screen_result_v0_1.json)
binds the evidence. The approved [bounded ball-versus-distractor test](docs/nba_ball_distractor_reference_results.md)
initially stopped on missing check coverage after completing all 184 proposed
labels. Ryan then explicitly requested training. The [single fixed-model
training result](docs/nba_ball_distractor_training_results.md) converged in a
33.125-second feature/fit run using 90 object groups and 109 distinct crops.
It fails ball protection: only 5/10 previously accepted checks are correct,
including 2/6 balls. The full 3,373-point comparison loses 207/581 protected
matches; all five comparison videos are saved. The recipe is rejected for adoption. The new labels remain
AI proposals pending human acceptance, and the missing clothing/emitted-head
coverage remains a limitation. The earlier [coverage result](configs/ball_tracking/reviews/nba_ball_distractor_reference_result_v0_1.json)
and all original evidence remain intact.
The original baseline remains intact, and the failed NBA continuation stays rejected.
These correlated, failure-selected labels are
a development diagnostic; slowed label overlays do not demonstrate improved
model trajectories or comparative NBA accuracy. The preceding heatmap inspection
used no new inference or training; the subsequent approved fit is separate.
SAC's new scores describe training fit. Existing holdouts, the NFHS finish
line, DET's exclusion from fitting and the negative motion result remain unchanged; three motion-video
human reviews remain pending.

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

### Phase 2 — Ball tracking (in progress)

- [x] Define an auditable ball-center annotation and evaluation protocol
- [x] Label and visually review a 75-frame pilot across three possessions
- [x] Precommit new contiguous representative, challenge, and holdout pools
- [x] Implement the frozen image-only detector adapter and guarded runner
- [x] Research relevant sports tracking models, implementations, datasets and evaluation practices
- [ ] Evaluate and select a small-object basketball detector
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
- Ball detection/tracking and basketball event recognition have not yet been
  integrated; the 75-frame annotation/evaluator pilot is complete.
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

The first label-blind, image-only ball-detector experiment is now precommitted:
its RF-DETR Medium runtime contract, raw-candidate export behavior, scoring grid,
three reviewed pilot windows, and nine prediction-embargoed evaluation windows
are frozen in code and configuration. The selection method is documented in
`docs/ball_detector_baseline_selection.md`. The immediate next operational task
is a clean preflight followed by descriptive inference on only the three reviewed
pilot windows. No operating point or quality gate has been selected, and the nine
evaluation windows must remain prediction-blind until their declared release
conditions are met; v0.1 cannot be toggled in place, so release requires a
reviewed, versioned schema/manifest transition. Once reliable player and court
trajectories and time-aligned ball observations coexist, the project can begin
reasoning about possession state, matchups, defensive actions, and outcomes.
