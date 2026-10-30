# Sports tracking projects and downstream analytics

Research snapshot: **2026-10-08**. Scope: public implementations and primary research relevant to Player Defense Score, from camera video through tracking, coordinates, identity, events and defensive value. This is a source and literature inspection, **not a local reproduction**. Public source text and repository metadata were read over HTTP. No packages were installed; no weights, dataset archives or media were downloaded; no inference or project tests were run for this research.

The strongest open reference for a modular, evaluated reconstruction pipeline is SoccerNet Game State Reconstruction (GSR), built on TrackLab. Roboflow's examples and two basketball repositories provide concrete implementation patterns but much weaker end-to-end evidence. DeepSport offers unusually relevant basketball measurement tasks, with input assumptions that must be respected. Libraries such as kloppy and socceraction begin after much of the difficult visual measurement has already happened. No inspected source establishes a validated, auditable NBA defensive score from ordinary broadcast video on this project's data.

## How to interpret this chapter

**Implemented** means code for the named step was inspected. **Author-reported** means a paper or repository reports a result; it was not reproduced here. **Demonstrated** means a tutorial/example is provided without adequate independent evaluation for the claimed downstream task. **Commercial claim** means an official vendor or league describes a product or deployment without releasing the relevant implementation and validation data.

A working command, downloadable checkpoint or attractive overlay is not evidence that a project solves identity, possession or defensive credit. Code license, model license, annotation license and underlying footage rights are separate questions. Dates below are verified publication or repository metadata where available, not assumed from search-engine freshness. Detailed URLs, inspection depth, limitations and inspected revisions are in [sports_projects_sources.json](sports_projects_sources.json).

### Coverage map

| Reference | What is actually represented | Evidence inspected | Useful role here | Important boundary |
|---|---|---|---|---|
| TrackLab + SoccerNet GSR | Athlete detection, image tracking, pitch projection, role/team/jersey labels | Pipeline YAML, calibration, team and jersey code; paper | Architecture and joint identity/position evaluation | Soccer; inspected pipeline does not solve ball trajectory, possession or defensive value |
| Roboflow sports soccer | Detection, ByteTrack, team clustering, pitch transform and radar examples | Main program and ball/team/transform modules | Small, understandable adapters and visualization | Recent-position ball heuristic; radar path does not include ball |
| Roboflow basketball notebook | Player/number detection, SAM2 propagation, team clustering, OCR, court keypoints, shot-state demo | Notebook code and shot state machine | Human-readable evidence visualization and OCR ideas | Seeded masks and model dependencies; no published end-to-end error study found |
| DeepSport / DeepSportradar | Basketball ball localization, calibration, segmentation and re-identification tasks | Paper, task README, training config | Task design and calibrated measurement references | Some ball tasks assume the ball's image position is already known |
| Nolan-Lo capstone | Detection/tracking, teams, court projection and proximity possession | Ball and acquisition modules, configuration, entrypoints | Clear small-project decomposition | Missing ball positions are filled; no independent downstream benchmark found |
| cyrushadavi nbacv | Multi-stage NBA prototype with ball, identities, coordinates, heuristic events and cached artifacts | Ball/possession/event code, evaluation and assessment | Closest broad basketball implementation reference inspected | Local author evaluations and qualitative ball coverage; documentation drift |
| Metrica / kloppy / sportypy | Existing tracking/event data, common interfaces, court visualization | Data README and domain schema | Output schema and analytics prototyping | Do not reconstruct tracks from pixels |
| socceraction / EPV research | Action value or possession-outcome modeling from structured inputs | Schema/code, primary papers and author demo | Future value-model formulation | Not a ball tracker, matchup oracle or causal defensive-credit solution |
| BasketballBench / SportsTime | Video questions, temporal evidence and sports understanding | Primary papers/project documentation | Later evidence-backed querying and event review | Question-answer accuracy is not trajectory or identity accuracy |
| SkillCorner / Hawk-Eye / Second Spectrum | Commercial tracking or analytics services | Official vendor/league pages and sample output schema | Understand production data contracts and system separation | Closed methods; vendor outputs are not independent ground truth |

## 1. SoccerNet GSR and TrackLab: the most useful system architecture

The current [SoccerNet configuration](https://raw.githubusercontent.com/SoccerNet/sn-gamestate/main/sn_gamestate/configs/soccernet.yaml) explicitly orders detection, re-identification, tracking, pitch processing, calibration, jersey reading, tracklet aggregation, team clustering and team-side assignment. Defaults include Ultralytics detection, PRTReID, BPBreID/StrongSORT, MMOCR and NBJW calibration. This is materially more useful than a diagram because intermediate outputs and module dependencies are represented in configuration.

[TrackLab](https://github.com/TrackingLaboratory/tracklab) supplies reusable image-, detection- and video-level modules and tracking evaluation integration. Its README describes a research framework still under development. The [GSR entrypoint](https://github.com/SoccerNet/sn-gamestate) is `uv run tracklab -cn soccernet`; default behavior can download weights/data and evaluate one validation sequence. Cached tracker states support stage reuse. These are documented entrypoints, not commands tested here. The TrackLab and GSR installation descriptions target different dependency generations, so a compatible pinned environment would be part of any reproduction.

Source inspection exposes the assumptions behind the impressive architecture:

- [Jersey aggregation](https://raw.githubusercontent.com/SoccerNet/sn-gamestate/main/sn_gamestate/jersey/voting_tracklet_jn_api.py) selects a confidence-weighted vote across a tracklet. This can turn repeated weak observations into usable evidence, but a track identity switch can contaminate all later votes.
- [Team assignment](https://raw.githubusercontent.com/SoccerNet/sn-gamestate/main/sn_gamestate/team/tracklet_team_clustering_api.py) averages player embeddings and clusters into two teams. A cluster label is not a named roster identity.
- [NBJW calibration](https://raw.githubusercontent.com/SoccerNet/sn-gamestate/main/sn_gamestate/calibration/nbjw_calib.py) uses line/keypoint networks and a homography, then projects bounding-box bottom points to the field. It optionally reuses a previous homography. Adopting that option would require recording its age and camera-motion validity; it is not fresh geometric evidence.
- The inspected YAML has no complete ball-to-possession-to-defensive-credit chain. Adding such modules would be new research and validation, not simply enabling a switch.

The [2024 GSR paper](https://arxiv.org/html/2404.11335v1) contributes an especially useful evaluation lesson. Its 200 thirty-second clips contain athlete positions and attributes; GS-HOTA jointly penalizes position and role/team/jersey mistakes. The original baseline's reported test GS-HOTA was 22.26, substantially below its image-space tracking score of 57.64. Original inference took about eleven minutes for a thirty-second clip on an A100. Those results describe the paper's implementation, not the current NBJW configuration. Its soccer spatial tolerance must not be imported as an NBA acceptance threshold.

**Borrow:** modular contracts, saved intermediate states, identity evidence aggregation and a final metric that cannot hide identity mistakes behind good boxes. **Do not borrow unexamined:** soccer geometry tolerances, two-team clustering as roster truth, stale calibration, or the assumption that a high image-space tracking score means usable analytics.

TrackLab's repository license is [MIT](https://raw.githubusercontent.com/TrackingLaboratory/tracklab/main/LICENSE); GSR's is [GPL-3.0](https://raw.githubusercontent.com/SoccerNet/sn-gamestate/main/LICENSE). This says nothing by itself about distributing soccer footage. [SoccerNet's current access page](https://www.soccer-net.org/data) separates public datasets from gated protected video requiring account approval and NDA acceptance.

Another framework lead is [SportsLabKit](https://github.com/AtomScott/SportsLabKit). Its README exposes swappable detector/ReID/tracker components, pitch calibration and frame-indexed bounding-box/coordinate dataframes. The example invokes a SORT tracker on a camera object; event detection and richer interoperability remain roadmap items. This pass inspected its README and license, not its tracker internals or installation. It is an alternative architecture reference, not evidence of complete basketball analytics. Its [license](https://raw.githubusercontent.com/AtomScott/SportsLabKit/main/LICENSE) is GPL-3.0, so it should not be treated as interchangeable with MIT TrackLab for code reuse.

## 2. Roboflow sports: useful code examples, different levels of completeness

### Soccer implementation

The [soccer main program](https://raw.githubusercontent.com/roboflow/sports/main/examples/soccer/main.py) implements separate modes for pitch, players, ball, tracking, teams and radar. It combines object detection, ByteTrack and cropped-image processing. Ball detection uses sliced inference and NMS; the radar branch plots player/team/referee information. A documented-style entrypoint is `python examples/soccer/main.py --source_video_path INPUT --target_video_path OUTPUT --mode RADAR`, with weights and environment prepared separately.

The [ball selector](https://raw.githubusercontent.com/roboflow/sports/main/sports/common/ball.py) stores recent candidate centers, computes their average and selects the current candidate nearest that average. It stores all candidates in the buffer, so repeated clutter can bias the reference point. It has no explicit calibrated occlusion probability or ball-flight model. Empty detections remain empty, which is preferable to inventing an observation.

[Team code](https://raw.githubusercontent.com/roboflow/sports/main/sports/common/team.py) uses SigLIP embeddings, UMAP and two-cluster KMeans. [View transformation](https://raw.githubusercontent.com/roboflow/sports/main/sports/common/view.py) fits a homography and transforms points; the small helper does not expose a measurement uncertainty model. These pieces are understandable enough to inspect, but that simplicity is not proof of transfer to basketball.

### Basketball notebook

The [basketball notebook](https://github.com/roboflow/notebooks/blob/main/notebooks/basketball-ai-how-to-detect-track-and-identify-basketball-players.ipynb) is a richer integration demo: RF-DETR detections, SAM2 mask propagation, SigLIP team features, jersey OCR, court keypoints and a top-down view. It requires hosted/model access credentials and a separate `feat/basketball` sports branch. SAM2 is initialized from first-frame boxes. Jersey evidence is linked to masks and repeated across frames. Named team/roster mappings and smoothing choices are supplied in the notebook. These are tutorial assumptions, not evidence of robust substitutions, camera cuts or complete-game identity.

One implementation detail matters for auditability: its displayed coordinate-building loop appends points only on frames with enough court keypoints. An adopter must preserve explicit frame/time indices and missing calibration rather than treating the compacted array as an unbroken time series.

The separate [shot state machine](https://raw.githubusercontent.com/roboflow/sports/feat/basketball/sports/basketball/tools.py) advances after repeated action detections, then declares a make from repeated ball-in-basket detections or a miss after a timeout. This is a useful event-proposal mechanism. A missing visual cue or interrupted shot can otherwise become a false miss. Evaluate event precision/recall and outcome uncertainty before using it in a defensive score.

**Borrow:** clear overlays, team/number evidence inspection and small components. **Do not equate:** a hosted model's detector confidence with verified player identity; a SAM mask ID with a complete roster identity; an event timeout with an observed outcome. The [sports repository](https://github.com/roboflow/sports) is MIT, while notebook dependencies, hosted models, weights and tutorial footage need their own checks.

## 3. DeepSport and DeepSportradar: relevant basketball measurement, constrained inputs

[DeepSportradar v1](https://arxiv.org/html/2208.08190) separates basketball into ball 3D localization, calibration, instance segmentation and player re-identification. The original acquisition uses calibrated arena cameras rather than an arbitrary moving broadcast feed. Its ball annotations combine image localization with a ground projection, and its arena separation is a useful generalization design.

Crucially, the [3D ball challenge](https://raw.githubusercontent.com/DeepSportradar/ball-3d-localization-challenge/main/README.md) supplies crops with **oracle image position**. It asks a model to estimate ball size/localization from an already centered ball crop. That does not establish that the model can find the right ball among hands, shoes and crowd objects. Its documented preparation/training commands and baseline notebook provide an experiment starting point, but not a drop-in replacement for this project's candidate selector.

The current [DeepSport training config](https://raw.githubusercontent.com/gabriel-vanzandycke/deepsport/main/configs/ballsize.py) confirms this distinction: 64-pixel ball-centered crops, a VGG16-based network, diameter/offset losses and dataset preprocessing. The inspected configuration sets `public_dataset=False`, so running its default unchanged would require checking the actual dataset route. The [environment](https://raw.githubusercontent.com/gabriel-vanzandycke/deepsport/main/pyproject.toml) pins Python 3.10 and TensorFlow 2.15-era dependencies, separate from this project's current detector environment.

The [player re-identification challenge](https://github.com/DeepSportRadar/player-reidentification-challenge/blob/master/README.md) evaluates cropped-person retrieval, not full-game named identity. Its documented baseline reports 72.7% mAP on its test set and 61.1% on the updated challenge. A much higher winner result shown for an older challenge split must not be compared as though the data were identical. The reusable idea is a retrieval protocol with query/gallery separation and explicit split identity.

[DeepSportLab](https://arxiv.org/abs/2112.00627) is a separate joint ball detection, player segmentation and pose research direction. It should not be conflated with a complete tracker, identity resolver or defensive model.

**Borrow:** arena-disjoint testing, separate localization versus detection metrics, explicit camera assumptions, task-specific annotation. **Investigate later:** whether ball-size or appearance evidence helps reject existing crop candidates. **Do not claim:** calibrated 3D ball accuracy from a broadcast homography alone.

The [DeepSport README](https://raw.githubusercontent.com/gabriel-vanzandycke/deepsport/main/README.md) declares CC BY-NC-ND 4.0, despite its open-source description. The ball challenge README inspected here did not resolve all code/data rights. Treat that uncertainty as a reason to verify exact files before reuse, not as permission inferred from GitHub availability.

## 4. Public basketball projects: inspect the assumptions after detection

### Nolan-Lo basketball-computer-vision

This [UCSD capstone](https://github.com/Nolan-Lo/basketball-computer-vision) is a concrete staged project, not merely a landing page. It combines player/ball models, ByteTrack, court keypoints, team classification, ball acquisition and a minimap. The repository provides model links and a Python 3.12 environment; `uv run python -m src.pipeline --input INPUT --output OUTPUT` is its documented pipeline route. No weights or entrypoint were executed here.

The [ball tracker](https://raw.githubusercontent.com/Nolan-Lo/basketball-computer-vision/main/src/trackers/ball_tracker.py) keeps the highest-confidence candidate, filters large displacements, interpolates the resulting coordinates and backward-fills missing values. The inspected interpolation path does not preserve an explicit observed/interpolated/missing distinction or a small bounded-gap rule. A visually continuous ball trace can therefore hide long periods without visual evidence.

Its [acquisition detector](https://raw.githubusercontent.com/Nolan-Lo/basketball-computer-vision/main/src/ball_acquisition_detector.py) uses player-box geometry, containment and frame persistence. That is a possession heuristic, not an independently evaluated model of controlled dribbles, passes, loose balls and shots. One containment branch selects by a maximum distance; this merits a unit-level interpretation check before reuse, rather than assuming the variable names imply the intended nearest-player rule.

**Disposition:** useful portfolio-scale decomposition; weak evidence for copying the selection/possession behavior. No project license was located in the inspected repository metadata/tree. No independent basketball ball or possession benchmark was found in the inspected materials.

### cyrushadavi1/nba_video_analysis_v2 (nbacv)

This is the closest inspected public basketball implementation to a broad broadcast-analysis stack. Its [README](https://raw.githubusercontent.com/cyrushadavi1/nba_video_analysis_v2/main/README.md) documents a real `nbacv clip.mp4` CLI, cached stage artifacts, named identity work, a clip finder and a query index. Inputs include public player, court, ball and jersey checkpoints. The repository calls itself a research prototype. Its macOS/Apple-silicon testing statement is author-reported; this review did not establish Windows/CUDA reproducibility.

The [ball implementation](https://raw.githubusercontent.com/cyrushadavi1/nba_video_analysis_v2/main/src/nbacv/ball.py) uses three-frame WASB heatmaps, several connected-component candidates, a Viterbi path containing a missing state, and bounded interpolation. Output distinguishes observed, interpolated and missing. Penalties for motion, misses and reacquisition are manually chosen; the resulting score is not a calibrated probability of ball identity. A selected detector output labeled observed is still not human-confirmed truth.

The [possession module](https://raw.githubusercontent.com/cyrushadavi1/nba_video_analysis_v2/main/src/nbacv/possession.py) combines player-box distance, normalized thresholds and persistence, with unknown/loose/flight states. Its confidence values are formulas rather than empirically calibrated probabilities. The [event module](https://raw.githubusercontent.com/cyrushadavi1/nba_video_analysis_v2/main/src/nbacv/events.py) proposes passes, turnovers, shots and rebounds from those states. Projecting a rim's floor coordinates through a court-plane homography cannot recover the image position of an elevated rim; shot proximity from that construction needs separate validation.

The [evaluation report](https://raw.githubusercontent.com/cyrushadavi1/nba_video_analysis_v2/main/reports/evaluation.md) contains real evaluation scripts and author-reported SportsMOT results: fine-tuned detection AP50 about 0.968, tracking with stitching HOTA 50.2 and IDF1 52.1. Those are player-box/association measurements. Reported NBA ball coverage is explicitly qualitative without a ball ground-truth accuracy score. Reprojection error against the same fitted keypoints also is not independent court-position truth.

There is documentation drift: the [final assessment](https://raw.githubusercontent.com/cyrushadavi1/nba_video_analysis_v2/main/reports/final_assessment.md) describes missing roster identity and cut handling, while the newer README describes added identity and clip extraction. A careful reproduction must tie each claim to a specific commit, dataset and result artifact instead of combining every document into one supposedly validated release.

**Borrow:** explicit observation status, raw/derived artifact separation, cached modules, uncertainty-aware rendering and reproducible evaluation entrypoints. **Do not treat as new proof:** Viterbi, missing states or nearest-player context. This project has already tested a null-capable recent-history graph, motion penalties and a soft player-box prior. Our remaining wrong-object and occlusion failures require evidence that changes the discrimination problem, not merely a new name for temporal smoothing.

No top-level project license was found in inspected metadata. Upstream components have mixed permissive, AGPL and noncommercial terms. Resolve permissions before copying code or distributing a combined application.

### Smaller shot-analysis demonstrations

[chonyy/AI-basketball-analysis](https://github.com/chonyy/AI-basketball-analysis/blob/master/README.md?plain=1) provides a Flask/OpenPose-oriented shooting analysis demo. It is relevant to shot mechanics and a narrower user experience, not ten-player identity, calibrated court state or matchup attribution. The README itself flags OpenPose's noncommercial limitation. This project was screened at README level only; it received less weight than source-inspected candidates.

## 5. Datasets, annotation workload and rights

Dataset names do not imply interchangeable labels. A ball-centered crop, a player bounding box, an action tube, a roster identity and a defensive responsibility label answer different questions.

| Source | Available supervision/output | Useful evaluation | Boundary and rights to check |
|---|---|---|---|
| [SportsMOT](https://github.com/MCG-NJU/SportsMOT) | Player boxes and track IDs across basketball, volleyball and soccer | Detection/association generalization | No ball or roster truth; clips selected without camera cuts; CC BY-NC 4.0 plus distribution terms |
| [SoccerNet GSR](https://arxiv.org/html/2404.11335v1) | Athlete pitch locations and role/team/jersey attributes | Joint identity/position evaluation design | Soccer geometry; some video gated; reconstruction labels are not defensive labels |
| [DeepSportradar](https://arxiv.org/html/2208.08190) | Basketball calibration, ball localization, masks and re-ID task data | Measurement components and arena transfer | Calibrated acquisition and oracle-crop assumptions; inspect per-task terms |
| [Metrica sample data](https://raw.githubusercontent.com/metrica-sports/sample-data/master/README.md) | Synchronized tracking and event examples | Analytics interfaces and time alignment | Already processed trajectories; anonymized data; acknowledgement request is not a general footage redistribution license |
| [SkillCorner open data](https://raw.githubusercontent.com/SkillCorner/opendata/master/README.md) | Vendor tracking, detected/extrapolated flags, some dynamic events and pose samples | Consumer schemas and uncertainty-aware analytics | Vendor-produced estimates, not independent ground truth; verify sample terms |
| [SkillCorner basketball](https://github.com/SkillCorner/opendata-basketball) | Ten ACB games of player/ball tracking and derived events; broader offensive aggregates | Basketball time, uncertainty, possession and matchup interfaces | Proprietary predictions; sample games do not reproduce season aggregates; MIT repository license, no footage grant established |
| [MultiSports](https://github.com/MCG-NJU/MultiSports) | Spatiotemporal action tubes | Action localization precision/recall | Action tube boxes are not ball coordinates; published CC BY-NC 4.0 data terms |
| [BasketballBench](https://arxiv.org/abs/2608.23435) | Reported possession clips and question-answer annotations | Basketball understanding questions | Author code/data availability not confirmed here; benchmark is not dense metric tracking |
| [PL-NBA](https://github.com/holhouse/PL-NBA-Dataset) | Possession clips, sub-events, named players and textual descriptions | Sequential event recognition and annotation design | README declares noncommercial research use; annotation archive listed, not downloaded; no trajectory supervision established |
| [SportsTime](https://github.com/ustiniansy/SportsTime) | Sports questions and temporal evidence annotations | Grounded reasoning and time evidence | Gated video and noncommercial conditions; no metric trajectory target |

The [SportsMOT paper](https://arxiv.org/abs/2304.05170) reports 240 sequences, over 150,000 frames and over 1.6 million boxes. That scale illustrates why extensive identity labeling is expensive, but this review did not verify annotator hours or a transferable dollar cost. Its task excludes spectators, referees and coaches; a detector evaluated there does not automatically solve every person class in a broadcast.

For a new Player Defense Score label set, estimate effort by **annotation operations**, then measure minutes on a small pilot: ball visibility and center/radius; hard-negative candidate identity; track continuity corrections; calibration landmarks; jersey/name evidence; possession intervals and ambiguous transitions; defensive assignments requiring adjudication. Do not estimate cost from frame count alone. Dense frame coordinates and subjective matchup labels have different review burdens.

A practical rights checklist is per artifact: code license; exact checkpoint/model terms; annotation terms; original video permission; redistributable derived output; required attribution. This is a research inventory, not a legal determination. A portfolio can be useful without shipping game footage or third-party weights.

## 6. Analytics interfaces: where these tools begin

[Metrica's sample data](https://raw.githubusercontent.com/metrica-sports/sample-data/master/README.md) pairs synchronized events and tracking. Its normalized coordinates and 105-by-68-metre soccer field are useful examples of an explicit coordinate convention. Neither the sample nor an analytics notebook explains how to reconstruct equally accurate tracks from a new camera.

[kloppy](https://github.com/PySport/kloppy) supplies a vendor-independent event/tracking model and coordinate/orientation conversions. Its inspected [tracking types](https://raw.githubusercontent.com/PySport/kloppy/master/kloppy/domain/models/tracking.py) include frame IDs, player data, ball coordinates and metadata. The useful pattern is a stable interface separating data production from consumers. Preserve this project's richer provenance and missingness even if exporting into a simpler interchange model. Vendor readers—including SkillCorner, Metrica and others—are parsers, not alternative detectors.

[sportypy](https://github.com/sportsdataverse/sportypy/blob/main/README.md) draws rule-based sports surfaces, including basketball. It is a good source for a consistent court plotting layer; it does not estimate a camera transform or validate a point's coordinates.

[socceraction](https://github.com/ML-KULeuven/socceraction) converts event data to SPADL/atomic-SPADL and supports xT/VAEP. Its [action schema](https://raw.githubusercontent.com/ML-KULeuven/socceraction/master/socceraction/spadl/schema.py) makes game, period, time, team, player, location, action type and result explicit, including original-event provenance. Its README says development is not currently active; use it as a research reference with a pinned environment.

[VAEP](https://github.com/ml-kuleuven/socceraction/blob/master/docs/documentation/valuing_actions/vaep.rst) values actions through changes in scoring and conceding probabilities over subsequent actions. That is a model of event value, not a solution to who should receive credit for an off-ball basketball rotation. [LaurieOnTracking](https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking) similarly provides readable pitch-control/EPV examples starting from tracking data.

Basketball has more direct primary precedents: [Cervone et al.](https://arxiv.org/abs/1408.0777) model expected possession value through continuous movement and discrete transitions; the authors' [EPVDemo](https://github.com/dcervone/EPVDemo) includes an R demonstration and a permitted game sample. [Franks et al.](https://arxiv.org/abs/1405.0231) study defensive contributions with spatial/statistical models. These justify a staged value-model research program. They do not validate a simple closest-defender score or establish a causal effect for an individual defender from three possessions.

A future interface should keep frame observations, derived tracks, named identity decisions, event hypotheses, reviewed events, matchups and value estimates in distinct records linked by time and provenance. A value score should state the target it predicts, training population, calibration error and uncertainty; responsibility under switches/help defense should remain explicit rather than silently allocated to the nearest player.

The [2025 Action Valuation survey](https://arxiv.org/html/2504.06163v1) is a useful second-pass map of outcomes, credit horizons, player-aware models and evaluation choices. It highlights the shortage of explicit value ground truth and standardized evaluation, and the difficulty of off-ball valuation. Use its taxonomy to specify the intended defensive quantity; do not interpret agreement with a ranking or prediction target as demonstrated causal credit. This pass read the survey as a research map, not as experimental validation of a particular method.

## 7. Event recognition and VLMs: useful assistants, different measurement contracts

[MultiSports](https://raw.githubusercontent.com/MCG-NJU/MultiSports/main/README.md) has official action detection baselines and evaluation for spatial/temporal action tubes. [Sports-QA](https://arxiv.org/abs/2401.01505) studies fine-grained sports video questions. These support separate evaluation of an event proposal system or question-answering layer. Good event recognition can coexist with poor ball localization; conversely, accurate coordinates do not imply an understanding of a switch or defensive scheme.

[BasketballBench](https://arxiv.org/abs/2608.23435), posted August 24, 2026, reports 2,501 possession clips and 7,980 questions across ten tasks. Its [paper](https://arxiv.org/html/2608.23435v1) combines structured basketball tools with video models: detection/tracking, event processing, temporal alignment and SQL-style queries. Some questions use coarse court regions or score/time readings; these are not continuous image/metric ball trajectories. The annotation workflow mixes structured data and manual review. No author code/data release URL was confirmed in the inspected paper and searches, so it remains a promising understanding benchmark, not a verified runnable replacement pipeline.

[SportsTime](https://github.com/ustiniansy/SportsTime) emphasizes stepwise temporal evidence, with 14,326 questions across 1,575 videos as reported by the project. Its source-grounded evaluation idea is useful: an explanation should identify supporting moments, not only give a fluent answer. The repository documents gated video access and noncommercial conditions.

[PL-NBA](https://raw.githubusercontent.com/holhouse/PL-NBA-Dataset/main/README.md) reports over 7,000 possessions from 40 NBA games, over 30,000 events, three-expert consensus annotation and LLM-generated descriptions. The repository lists an annotation ZIP and a video-access link; neither was downloaded here. Its reported Gemini experiment on 200 possessions achieved 27.00% complete-possession matching and 60.76% event recognition. These are author results with a sparsely specified model/version and protocol, not a reproduced benchmark. The joint-versus-event accuracy distinction is valuable: several individually plausible events can still produce an incorrect possession narrative. The README declares CC BY-NC 4.0 and research-only use. No inspected implementation establishes dense player/ball tracking or defensive-credit validity.

[SpotTheBall](https://arxiv.org/abs/2511.00261) evaluates models and humans on images with the ball removed, using a coarse grid. Reported low model performance is evidence of difficulty on that particular hidden-ball reasoning task; it is not a ranking of all current tracking models. The relevant design lesson is to distinguish **observed**, **inferred** and **unknown**, especially when a plausible explanation can be produced without visible measurement evidence.

For this project, a VLM could propose replay/camera-cut labels, summarize reviewed evidence, suggest event intervals or help search possessions. It should return evidence times/regions and abstentions for review. Do not let prose confidence overwrite missing ball coordinates, infer roster identity without evidence, or assign defensive intent as measured fact. Evaluate localization, temporal grounding and unsupported claims separately from answer plausibility.

## 8. Closed commercial systems: learn from contracts, not unsupported equivalence

### SkillCorner basketball: the strongest inspected downstream schema reference

The official [basketball release](https://raw.githubusercontent.com/SkillCorner/opendata-basketball/main/README.md) supplies ten 2025–26 ACB games with tracking and derived events, plus offense-only shot/drive/pick aggregates spanning 293 of 327 games. Those aggregates cannot be reproduced from the ten published event files. This is a useful public output sample of a proprietary generator, not its implementation or a human-labeled benchmark.

The [tracking dictionary](https://raw.githubusercontent.com/SkillCorner/opendata-basketball/main/docs/data_dictionary/tracking_data.md) documents 25 fps, feet, player ground-plane coordinates, ball height, separate video/game clocks, and explicit detected versus extrapolated flags. Dead-time frames preserve the timeline while their object collections are empty. Player `predError` is described as a radius containing the true position in 90% of cases; ball error is separately described and less accurate. These are vendor-stated uncertainty semantics. Their averages are not independently observed residual errors in this review, and no raw reference trajectories were inspected to check calibration. The player flag is integer while the ball flag is float, a small but real ingestion detail.

Its [primer](https://raw.githubusercontent.com/SkillCorner/opendata-basketball/main/docs/PRIMER.md) separates tracking, inferred event records and aggregated statistics. It distinguishes a possession from a scoring chance after an offensive rebound, and identifies which fields derive from official play-by-play. The tracking dictionary describes a camera-relative orientation while event documentation uses an offense-relative convention; verify transformations per table rather than assuming all coordinates can be joined without an orientation check. The more specific tracking dictionary also permits slightly negative ball height from noise, unlike the primer's simplified positive-height description.

The [matchup table](https://raw.githubusercontent.com/SkillCorner/opendata-basketball/main/docs/data_dictionary/matchups.md) represents defender/offender assignments as time intervals with possession/chance IDs. [Closeout records](https://raw.githubusercontent.com/SkillCorner/opendata-basketball/main/docs/data_dictionary/closeouts.md) connect touch time, start/end positions, distances and subsequent ball-handler action. These are useful proposed output shapes for our later reviewed labels. They do not make the assignments ground truth or establish that the nearest defender caused a shot outcome.

The vendor's [known-issues document](https://raw.githubusercontent.com/SkillCorner/opendata-basketball/main/docs/KNOWN_ISSUES.md) openly records duplicate season player IDs, ambiguous scoring roll-ups, event omissions, and a receiver-named field that actually contains an intercepting defender. Some aggregate definitions differ from raw event counts. This is a valuable reminder that even commercial analytics need semantic validation, identity reconciliation and explicit data-quality checks.

The repository includes an actual [MIT license](https://raw.githubusercontent.com/SkillCorner/opendata-basketball/main/LICENSE), dated 2026. Keep its attribution when reusing covered material. The inspected license does not establish permission to redistribute NBA/ACB broadcast footage. For public dataset repackaging or commercial derived products, confirm the intended coverage of that software/documentation wording rather than inventing a broader media grant.

### Other official commercial evidence

[SkillCorner's September 30, 2026 product description](https://www.skillcorner.com/articles/data-on-demand) advertises tracking from single-camera footage with supporting match information. This is a commercial capability claim. Its [open-data schema](https://raw.githubusercontent.com/SkillCorner/opendata/master/README.md) is more directly reusable evidence: tracking samples distinguish detected from extrapolated players, record a field-of-view polygon, and provide coordinates and possession-related fields. Some pose and tracking outputs are generated separately and may not align exactly. Preserve those caveats when using samples; vendor predictions are not labels suitable for validating the same type of prediction.

The NBA's [Hawk-Eye announcement](https://pr.nba.com/nba-sony-hawk-eye-innovations-partnership/) describes 3D player/ball tracking and pose beginning with the 2023–24 season. The [Second Spectrum announcement](https://pr.nba.com/nba-genius-sports-second-spectrum-expanded-partnership/) describes analytics and augmented viewing, with additional research/development. These are primary evidence of different system roles—capture/measurement versus analytics—not proof that a public broadcast clip contains the same recoverable information as an arena installation.

Do not compare a vendor's coverage or identity percentage with our frame match rate unless definitions, independent labels, camera inputs and missingness are equivalent. No closed weights, production annotations or independently reproducible NBA benchmark were obtained from these announcements.

## 9. What changes the next decision for Player Defense Score

The existing player foundation is reviewed for three curated possessions. The current ball work already separates raw candidate availability from final selection, and has tested motion/context hypotheses. [Motion-factorial results](../ball_crop_motion_factorial_results.md) and [player-context results](../ball_crop_player_context_results.md) establish benefits in some development conditions without solving persistent nearby clutter or hidden-ball alarms. Current project context reports raw RF availability on 140/145 eligible frames, selection of 111, and RF/YOLO agreement selection of 78; those are project measurements, not claims from external repositories.

That evidence changes how to use this research:

1. **Preserve the reviewed foundation.** No inspected external pipeline provides evidence strong enough to justify replacing it wholesale.
2. **Use public code as a challenger specification.** A three-frame heatmap model or learned candidate appearance verifier is worth evaluating only with a defined input/output contract and the same missingness-aware labels. Temporal smoothing alone is not a new hypothesis here.
3. **Measure selection errors separately from proposal availability.** A detector can offer the true ball while a selector follows clutter. Track candidate identity, false selection on hidden frames and abstention, not just trajectory coverage.
4. **Keep geometry honest.** Court-plane player coordinates and an airborne ball have different projection models. A smooth path on a court diagram is not evidence of ball height or correct camera calibration.
5. **Delay defensive value until its inputs are observable.** Possession, named identity, matchup changes and event outcomes need their own reviewed evidence and error accounting.
6. **Adopt useful schema ideas without migrating frameworks.** Explicit status flags, time indices, source links and separate raw/derived outputs can be integrated incrementally.
7. **Keep sealed holdouts sealed.** Public datasets can inform methods and training; they cannot turn our development comparisons into an independent test.

These are recommendations inferred from the comparison, not demonstrated improvements. Any selected new model needs a small, fair transfer evaluation before a larger integration commitment.

## 10. Publishable portfolio artifacts and second-pass questions

A credible portfolio result can show engineering and scientific judgment without claiming a finished product. Publish the architecture and data contracts; reproducible evaluation scripts; clearly separated detection/association/coordinate/event metrics; failure taxonomy; ablations including the negative corroboration result; synthetic or rights-cleared examples; and an uncertainty-aware review interface. Keep private footage, unlicensed model files and generated scientific outputs outside the repository as required. Link to official datasets rather than redistributing them.

For hiring or public presentation, label outcomes precisely: source inspected, author reported, locally reproduced, or transferred to this project's clips. Show how a wrong candidate or missed observation propagates into an event decision, and where review prevents a confident but unsupported score. A short honest failure analysis is stronger evidence of measurement discipline than an uninterrupted trail produced by filling gaps.

Remaining questions before choosing an external implementation:

- Can the exact candidate model/weights be used under the intended distribution terms, and are preprocessing, frame cadence and checkpoint hashes documented?
- Does a small transfer study distinguish true-ball recall from clutter rejection and hidden-ball false positives?
- Are reported identities evaluated on named players with independent evidence, or only anonymous track consistency?
- Is geometric error measured against independent reference points/positions, rather than the points used to fit the transform?
- Are event and possession labels independently annotated with ambiguity, and are their time tolerances declared?
- Can an example run be reproduced from a pinned revision without undocumented private files or manual curation?
- For recent benchmarks such as BasketballBench, where are the author release, evaluation implementation, media access terms and annotation provenance?

This chapter records the answer available from public primary sources on the access date. Unverified availability, licenses and performance remain explicitly unresolved.
