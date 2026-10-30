# Player tracking, identity, and court geometry research

Research date: **2026-10-08**. Scope: basketball broadcast video, with explicit limits on transfer from soccer, pedestrian tracking, and fixed cameras. Companion: [machine-readable source ledger](player_tracking_sources.json).

## What this changes for Player Defense Score

**Keep the reviewed player-coordinate foundation for the three curated possessions.** The research supports testing specific improvements when a documented failure warrants them; it does not establish that a newer tracker would improve this repository. Human identity reconciliation and camera/court review remain useful sources of ground truth. The immediate ball-tracking work need not wait for a player-tracking replacement.

The strongest practical opportunities are:

| Priority | Opportunity | Why it might help | What must establish value |
|---|---|---|---|
| Keep | Existing detector + ByteTrack + OSNet + reviewed identity/calibration | Already integrated and reviewed on the project possessions | Preserve those results as the comparison baseline |
| First small challenger | OC-SORT association using the same saved detections | Different motion treatment without adding an appearance network | Fewer swaps/fragmentations in actual screening, crossing, and occlusion failures |
| First appearance challenger | BoT-SORT with and without ReID; Deep OC-SORT if confidence-adaptive appearance helps | Camera compensation, spatial/appearance gates, or conservative appearance updates | Correct return after occlusion without merging same-team players |
| Later learned challenger | CAMELTrack with explicit checkpoint and cues | Modern learned association; released SportsMOT weights | Improvement large enough to justify pose/ReID dependencies and integration work |
| Assist review | SAM 2 or Cutie on a selected ambiguous player/occlusion | Masks can help human correction and cleaner appearance crops | Less correction time and no identity drift |
| Assist geometry | Court-only correspondences or point tracking between reviewed calibration frames | Reduce repetitive landmark work during a continuous camera shot | Stable court residuals and reliable abstention at cuts/poor views |
| Retain human decision | Tracklet-to-roster identity, ambiguous feet, court orientation, final trajectories | None of the surveyed components proves these together on this NBA game | Inspect synchronized footage, overlays, and uncertainty |

These are recommendations derived from the sources below, **not local experimental results**. No packages, weights, datasets, or media were installed/downloaded for execution; no model runs or repository tests were performed for this research.

## Separate the six problems

A useful implementation preserves distinct outputs:

1. **Detection:** a person box or mask with a score.
2. **Association:** a shot-local track ID linking observations.
3. **Attributes:** team, role, visible jersey evidence, and appearance descriptors.
4. **Identity:** a reviewed mapping from tracklets to a real roster entry, possibly unknown.
5. **Geometry:** image-to-court mapping plus validity and uncertainty.
6. **Analytics:** distances, velocities, matchup hypotheses, and eventually defensive value.

A stable track number is not an NBA identity. A plausible jersey string is not proof of identity. An image-motion transform is not court calibration. A complete-looking trajectory is not evidence that an occluded player was observed. The integrated [SoccerNet GSR task](https://arxiv.org/abs/2404.11335) makes the value of separating localization, association, and attributes particularly clear.

For cross-cut persistence, use a durable reviewed player identity above disposable shot-local track IDs. End the image-motion/calibration state at a cut; reconnect identities only when appearance, team, number, roster/time context, and review support it. Keep conflicting candidates rather than forcing ten named players into every frame.

## Tracking methods and their actual implementations

### ByteTrack: retain as the reference

[ByteTrack, ECCV 2022](https://arxiv.org/abs/2110.06864), associates high-confidence detections first and uses lower-confidence detections to recover existing tracks. The [official implementation](https://github.com/FoundationVision/ByteTrack/blob/d1bf0191adff59bc8fcfeaa0b33d3d1642552a99/yolox/tracker/byte_tracker.py) filters low scores above 0.1, performs a second IoU match against remaining **tracked** tracks, and uses a higher threshold to initialize tracks. Its buffer scales with the provided frame rate.

This matters in basketball: a temporarily weak detection may preserve a player through overlap, but association cannot recover a person for whom no usable detection exists. Lowering every threshold can create extra bench/referee tracks. Match detector outputs and frame-rate conventions before attributing a change to tracking.

The [official model zoo and evaluation instructions](https://github.com/FoundationVision/ByteTrack) provide YOLOX weights and report MOT17 test MOTA 80.3, IDF1 77.3, HOTA 63.1, and about 30 FPS on a V100. Their recipes include particular training mixtures, tuning, and interpolation. Those numbers are a published configuration, not a speed or accuracy promise for this machine or this footage.

### OC-SORT: a useful motion-only comparison

[OC-SORT, CVPR 2023](https://arxiv.org/abs/2203.14360), emphasizes observations when estimating motion and recovering from occlusion. In [the tracker code](https://github.com/noahcao/OC_SORT/blob/8462e7e729a93ccd3bd995c0a79a890336cb3a0b/trackers/ocsort_tracker/ocsort.py), prior observations, a configurable observation interval, estimated direction, and an inertia term enter association; an optional ByteTrack-style stage is separately configurable.

The [repository](https://github.com/noahcao/OC_SORT) reports MOT17 private-detection HOTA 63.2 and DanceTrack HOTA 55.1. It distinguishes roughly 28 FPS with a detector on an RTX 2080 Ti from 700 FPS for association alone on an i9 CPU. The inspected revision also includes 2026 optimizations, so paper-era code and current runtime should not be conflated.

**Project use:** try as a small association-only challenger if existing detections survive but identities swap during nonlinear motion. It still needs detections and does not identify players across a broadcast cut.

### BoT-SORT and Deep OC-SORT: add cues with explicit failure boundaries

[BoT-SORT](https://arxiv.org/abs/2206.14651) combines motion, camera-motion compensation, and optional ReID. Its [association code](https://github.com/NirAharon/BoT-SORT/blob/251985436d6712aaf682aaaf5f71edb4987224bd/tracker/bot_sort.py) gates appearance matches using spatial proximity and an appearance threshold, then combines costs. Its [GMC implementation](https://github.com/NirAharon/BoT-SORT/blob/251985436d6712aaf682aaaf5f71edb4987224bd/tracker/gmc.py) supports several methods; sparse optical flow estimates a partial affine transform with RANSAC. That mode does not use the same person-masking path as every feature-based mode.

This is **image stabilization for association**, not a metric court model. It can help pans; it cannot safely bridge a hard cut, remove all parallax, or establish where a player's feet touch the court. The [official README](https://github.com/NirAharon/BoT-SORT) supplies detector/ReID weights and reports MOT17 BoT-SORT-ReID HOTA 65.0, IDF1 80.2, MOTA 80.5. Its documented environment is older Ubuntu/Python/Torch, and evaluation examples include interpolation.

[Deep OC-SORT](https://arxiv.org/abs/2302.11813) adds appearance and camera compensation to OC-SORT. The inspected [embedding tracker](https://github.com/GerardMaggiolino/Deep-OC-SORT/blob/6bb51d027b137233f5c520b6fcc4f2ae387a6ba9/trackers/ocsort_embedding/ocsort.py) makes an appearance update more conservative as detection confidence decreases. This is a concrete defense against contaminating a track with an occluder's appearance. Its [README](https://github.com/GerardMaggiolino/Deep-OC-SORT) provides weights, ablation switches, and a separate `--post` interpolation step; reported DanceTrack HOTA 61.3 must be interpreted with those choices.

**Project use:** fixed-detection ablations should separate camera compensation, ReID, and any offline interpolation. Same-team uniforms reduce appearance discrimination; a confident embedding match can still be wrong.

### StrongSORT / StrongSORT++: distinguish online tracking from completion

[StrongSORT](https://arxiv.org/abs/2202.13514) upgrades DeepSORT components. [StrongSORT++](https://github.com/dyhBUPT/StrongSORT) adds AFLink for tracklet linking and Gaussian-smoothed interpolation. These completion stages use information beyond simple causal frame-to-frame association. The repo supplies AFLink weights and precomputed detections/features/ECC data; its historical environment includes old dependency versions and manual paths.

**Project use:** an offline linker could reduce review effort, but interpolation must retain its inferred status. A smoothed path through an occlusion is not a new observed position. Component throughput for AFLink/GSI is not end-to-end FPS.

### SportsMOT / MixSort and CAMELTrack: stronger sports relevance

[SportsMOT, ICCV 2023](https://openaccess.thecvf.com/content/ICCV2023/html/Cui_SportsMOT_A_Large_Multi-Object_Tracking_Dataset_in_Multiple_Sports_Scenes_ICCV_2023_paper.html), contributes basketball, football, and volleyball sequences with rapid motion and similar appearance. [MixSort](https://github.com/MCG-NJU/MixSort) adds appearance association to ByteTrack/OC-SORT backends and releases weights. Its reported SportsMOT test comparisons include ByteTrack HOTA 64.1 → MixSort-Byte 65.7, and OC-SORT 73.7 → MixSort-OC 74.1. These within-backend deltas are more interpretable than ranking unrelated rows with different detection accuracy.

[CAMELTrack, 2025](https://arxiv.org/abs/2505.01257), learns association from multiple cues. The [official release](https://github.com/TrackingLaboratory/CAMELTrack) includes SportsMOT and general checkpoints, cached model outputs, and reports SportsMOT HOTA 80.3 with appearance and keypoints. It is a serious modern comparison candidate, not merely a conceptual paper.

However, inspection of [the default pipeline](https://github.com/TrackingLaboratory/CAMELTrack/blob/46a74bb22a28d2d699b4c5c5e317a26d3b87f1e2/cameltrack/configs/cameltrack.yaml) shows pose estimation, KPR ReID, and an **offline engine** for module batching. The [tracker configuration](https://github.com/TrackingLaboratory/CAMELTrack/blob/46a74bb22a28d2d699b4c5c5e317a26d3b87f1e2/cameltrack/configs/modules/track/camel.yaml) defaults to a general checkpoint, explicit confidence/lifecycle thresholds, and a similarity override differing from its SportsMOT comment. Online association does not mean its default whole pipeline is a low-latency streaming application.

**Project use:** only after a cheaper association comparison establishes the remaining error. Use the correct checkpoint and fixed cues; do not import the entire framework just to obtain a new track ID format.

### Learned detection/tracking watchlist

[MOTR](https://github.com/megvii-research/MOTR) carries transformer track queries from frame to frame; [MOTRv2](https://arxiv.org/abs/2211.09791) adds pretrained detector proposals. [MOTIP, CVPR2025](https://openaccess.thecvf.com/content/CVPR2025/papers/Gao_Multiple_Object_Tracking_as_ID_Prediction_CVPR_2025_paper.pdf), learns to predict in-context track IDs, with [released code and checkpoints](https://github.com/MCG-NJU/MOTIP). These are important alternatives to heuristic association. Their IDs still mean within-video correspondence, not a player's real-world name. MOTIP's current engine differs from its older branch; checkpoint compatibility and detector recipe must be explicit.

Compared with CAMELTrack's external-cue modularity, these approaches change more of the detector/tracker integration. They belong on a later watchlist when training data and measured failures justify that cost. The original MOTR README reports eight-GPU training and roughly 7.5 FPS at 1536×800 under its historical recipe; that is not a requirement or performance estimate for all modern learned trackers. MOTIP declares Apache-2.0; independent checkpoint/data/dependency terms and this project's accuracy remain to be checked.

### Reported numbers are not a common leaderboard

| Method/configuration | Benchmark | Reported result | Main comparability limitation |
|---|---|---|---|
| ByteTrack | MOT17 test | HOTA 63.1; IDF1 77.3 | Specific private detector/training recipe; interpolation/tuning in instructions |
| BoT-SORT-ReID | MOT17 test | HOTA 65.0; IDF1 80.2 | ReID and camera compensation added; own recipe |
| OC-SORT | MOT17 private / DanceTrack | HOTA 63.2 / 55.1 | Different scenes; tracking-only speed differs from detector-plus-tracker speed |
| Deep OC-SORT | DanceTrack | HOTA 61.3 | Appearance, compensation, and postprocessing settings matter |
| MixSort-Byte | SportsMOT test | HOTA 65.7, versus 64.1 for its ByteTrack baseline | Do not compare directly with another backend's detector |
| MixSort-OC | SportsMOT test | HOTA 74.1, versus 73.7 for its OC-SORT baseline | Small incremental difference under that recipe |
| CAMELTrack, appearance + keypoints | SportsMOT | HOTA 80.3 | Learned association plus extra upstream cues/checkpoint |
| StrongSORT++ | MOT benchmarks | Offline linking/interpolation added | A completed trajectory and a causal tracker answer different questions |

Sources are the method-specific primary repositories linked above. These numbers were **read**, not reproduced. Evaluate identity accuracy and court-position error separately from box tracking.

## Basketball and transfer datasets

| Dataset / task | Verified scope and access | What it can establish | Transfer limitation |
|---|---|---|---|
| [SportsMOT](https://github.com/MCG-NJU/SportsMOT) | 240 sequences, over 150K frames and 1.6M boxes across three sports; 720p/25 FPS; public annotations/videos under declared CC BY-NC 4.0 | Association under athletic motion and similar uniforms | Clips explicitly have **no shot changes**; excludes non-playing sideline people; no NBA roster identity or court-position truth |
| [DeepSportradar ReID](https://github.com/DeepSportRadar/player-reidentification-challenge) | Basketball crops; 20-frame sequences; query from first frame, gallery from later frames; 2023 challenge differs from 2022 | Appearance retrieval within this sampling/viewpoint protocol | High mAP on short same-view sequences is not cross-cut identity accuracy |
| [DeepSportradar calibration](https://github.com/DeepSportRadar/camera-calibration-challenge) | 728 image/calibration pairs; default 480/164/84 split; arena-based test separation; FIBA geometry and undistorted generated views | Basketball-specific court line/calibration development | Keemotion-derived views and FIBA dimensions differ from NBA broadcast; challenge holdout differs from default test |
| [TrackID3x3](https://github.com/open-starlab/TrackID3x3) | Indoor/outdoor fixed-camera and drone subsets; six player boxes every frame, ten keypoints on selected frames; data/intermediates released | Player tracking, attributes, and pose in a smaller basketball game | Manual court localization; six players; specific uniform/number heuristics; not broadcast cuts or 5-on-5 crowding |
| [SoccerNet Tracking](https://www.soccer-net.org/tasks/tracking) | Main-camera 1080p clips; separate 2022 ground-truth-detection association and 2023 detection-plus-tracking protocols | How to separate association quality from detector quality | Soccer roles, object sizes, field scale, and main-camera selection |
| [SoccerNet GSR](https://arxiv.org/abs/2404.11335) | 200 annotated clips; image-to-field position, role/team/jersey and tracks; code/model distribution | A complete modular minimap benchmark and integrated metric | Soccer-specific field/roles and identity attributes; not an NBA-name benchmark |
| [SoccerNet ReID](https://github.com/SoccerNet/sn-reid) | 340,993 crops from 400 games; action versus replay viewpoints | Cross-view retrieval of the same action | Same action/replay correspondence is not arbitrary long-term roster tracking |
| [DeepSportLab](https://arxiv.org/abs/2112.00627) | Basketball instance/pose/ball multitask research; [official code](https://github.com/ispgroupucl/DeepSportLab) | Joint perception and occlusion-aware instance analysis | Calibrated sports-image setting is not a complete moving-broadcast identity system |
| [TeamTrack](https://github.com/AtomScott/TeamTrack) | Basketball, soccer, handball; 4K–8K full-pitch video; over four million boxes; MOT and projected-trajectory formats | Small-player/full-court tracking and trajectory research | Fixed side/fisheye/drone views, not edited broadcast; trajectory subset only covers fixed side views; MIT code, data-specific terms not established here |
| [BasketLiDAR](https://github.com/Keio-CSG/BasketLiDAR) | Professional basketball, synchronized LiDAR and multi-view RGB; baseline notebooks; research access by request | Sensor-fusion tracking and metric spatial reference | Requires sensors unavailable in a broadcast file; MIT code, research/noncommercial data with redistribution restrictions |

The [DeepSportradar paper](https://arxiv.org/abs/2208.08190) covers four tasks, including 3D ball localization; do not treat those datasets as a single interchangeable benchmark. Its ReID README's older 98.44% CLIP result is on the **2022** challenge, while the ~61.1 mAP baseline quoted there is on the harder **2023** challenge. They are not a valid direct comparison.

The [TeamTrack paper](https://arxiv.org/abs/2404.13868) and [BasketLiDAR paper](https://arxiv.org/abs/2508.15299) are useful basketball counterpoints: better scene coverage or an extra depth sensor changes what is observable. Their advantages should not be attributed to a tracker that has only a moving single broadcast view. TeamTrack's repository still labels some scripts/documentation as in preparation; BasketLiDAR similarly promises fuller reproduction guidance. Availability of research artifacts does not establish a turnkey production pipeline.

### TrackID3x3 is available, but its assumptions are visible in code

The [revised paper](https://arxiv.org/abs/2503.18282) and released repository improve on an “available soon” abstract: there is now a concrete dataset and baseline. The implementation assembles CAMELTrack, BoT-SORT, jersey recognition, and per-subset notebooks. Its [outdoor color script](https://github.com/open-starlab/TrackID3x3/blob/9822a3dde59fc80fbb5eaacd443e79e8b059d94e/script/Outdoor/calculate_color_hist.py) computes 8×8×8 color histograms and takes a track-level median. This offers a useful team-cue pattern, but fixed folder structures, tracklet preprocessing, and subset-specific notebooks demonstrate adaptation work still required. Manual court localization is explicitly part of Track-ID, so the task does not remove this project's calibration review.

## Team, jersey, and identity through occlusion

### Keep identity evidence independent

The current OSNet embeddings are a sensible reference. [OSNet](https://arxiv.org/abs/1905.00953) and [Torchreid's released models](https://github.com/KaiyangZhou/deep-person-reid) offer mature appearance features, but pedestrian pretraining does not guarantee separation of teammates in matching uniforms.

Candidate evidence should remain inspectable:

| Evidence | Useful application | Failure to represent explicitly |
|---|---|---|
| Appearance embedding | Rank candidate tracklet links | Same uniform, camera color shift, blur, partial body, contaminated crop |
| Jersey OCR | Strong positive evidence when legible and consistent | Unreadable number, partial digit, front/back differences, wrong player's crop |
| Team color / segmentation | Reject implausible cross-team links | Referee/bench confusion, court colors, alternate kits, shadows |
| Motion / court position | Local association within a shot | Cuts, fast moves, swaps during occlusion, incorrect homography |
| Roster/time context | Restrict valid player candidates | Substitutions, mistaken game timestamp, replay footage |
| Human reconciliation | Resolve consequential ambiguity | Record uncertainty rather than force a name |

This table is a project design recommendation; it does not assert calibrated probabilistic independence between cues. A detector score or embedding distance should not be relabeled “identity probability” without calibration.

### Occlusion-aware ReID and sports attributes

[BPBreID](https://github.com/VlSomers/bpbreid) compares mutually visible body parts; [PRTReID](https://github.com/VlSomers/prtreid) adds team and role objectives. These address relevant failure mechanisms, but the published/released sports model is soccer-oriented. The [GSR adapter](https://github.com/SoccerNet/sn-gamestate/blob/1c958345067218297d221e45e1a6405f975f83e0/sn_gamestate/reid/prtreid_api.py) exposes embeddings, visibility, body masks, role predictions, and confidence, and downloads a named baseline checkpoint. A useful integration would retain those fields rather than collapse everything to a single identity.

The GSR [team clustering](https://github.com/SoccerNet/sn-gamestate/blob/1c958345067218297d221e45e1a6405f975f83e0/sn_gamestate/team/tracklet_team_clustering_api.py) averages player embeddings by track then applies two-cluster K-means. Its [team-side labeling](https://github.com/SoccerNet/sn-gamestate/blob/1c958345067218297d221e45e1a6405f975f83e0/sn_gamestate/team/tracklet_team_side_labeling_api.py) uses mean field position, with special goalkeeper handling. Reusing that latter rule in basketball would embed an unjustified assumption about team location.

GSR's [current release](https://github.com/SoccerNet/sn-gamestate) explicitly pins TrackLab 1.3.24 following a May 2026 GS-HOTA evaluation fix. Its current configuration also differs from the original paper's calibration stack. Record evaluator and pipeline versions before comparing published or reproduced results.

### Jersey recognition should abstain

[Koshkina and Elder's jersey framework](https://arxiv.org/abs/2405.13896) addresses legibility, outlier removal, pose-guided cropping, text recognition, and tracklet consolidation. The [official release](https://github.com/mkoshkina/jersey-number-pipeline) includes models and data links; its experiments are hockey and SoccerNet. It uses several dependencies and older environments, not a single generic OCR call. Its dependency named “SAM” is **Sharpness-Aware Minimization**, not Meta's Segment Anything.

For this project, use jersey predictions to suggest roster links and show the supporting frames. Store repeated consistent reads, conflicting reads, and unreadability separately. Do not let temporal voting amplify a wrong track merge into a confident roster label. GSR's [tracklet voting implementation](https://github.com/SoccerNet/sn-gamestate/blob/1c958345067218297d221e45e1a6405f975f83e0/sn_gamestate/jersey/voting_tracklet_jn_api.py) is a practical pattern to examine, not proof that voting solves the upstream identity problem.

### Emerging integrated soccer models

[SoccerMaster's official 2026 release](https://github.com/haolinyang-hlyang/SoccerMaster) exposes code/checkpoints and still combines multiple perception modules; its instructions include SAM2 plus external calibration/ReID models and large Qwen variants for jersey/role tasks. This is evidence of active integrated research, not an immediate lightweight basketball replacement. Keep it on the watchlist; dataset transfer, component licenses, memory cost, and NBA-specific accuracy remain unverified here.

## Masks and point tracks: complementary tools

| Family | Verified capability / released artifact | Appropriate use here | Why it is not complete player tracking |
|---|---|---|---|
| [SAM 2 / 2.1](https://github.com/facebookresearch/sam2) | Prompted multi-object video masks, checkpoints and training code | Interactive correction, occlusion inspection, foreground crops | Prompt identity and mask propagation do not establish roster identity; review drift/reappearance |
| [SAM 3 / 3.1](https://github.com/facebookresearch/sam3) | Concept/text/exemplar detection, segmentation, and video tracking; gated checkpoints; 3.1 released 2026-03-27 | Explore player/team concept proposals after cheap methods | “Player in white” can match multiple people; no verified NBA identity benchmark |
| [Cutie](https://github.com/hkchengrex/Cutie) | CVPR2024 video object segmentation, interactive GUI, released model downloader | Propagate corrected masks through a difficult short segment | Needs object initialization/corrections; segmentation scores do not measure named identity |
| [XMem](https://github.com/hkchengrex/XMem) | ECCV2022 long-video segmentation with several memory timescales and GUI | Reference for sustained prompted-object masks | Long memory is not proof of correct re-identification after a cut |
| [CoTracker3](https://github.com/facebookresearch/co-tracker) | Joint queried point tracks with visibility; online/offline checkpoints | Track court marks or selected visible body detail between reviews | Point tracks do not discover all players, decide team, or supply metric coordinates |
| [TAPIR / BootsTAPIR](https://github.com/google-deepmind/tapnet) | Matching/refinement point tracker; causal and offline models; JAX/PyTorch weights | Another correspondence/visibility assistant | Pixel-point continuity is neither full-body identity nor 3D ground-contact truth |

[SAM2's predictor implementation](https://github.com/facebookresearch/sam2/blob/main/sam2/sam2_video_predictor.py) has separate video/state CPU-offload options and correction-memory behavior. Offloading trades GPU memory for other costs; “streaming memory” does not mean every API stores no video-sized data. Its reported 2.1 speeds span 91.2 FPS for tiny to 39.5 for large **on an A100 with compilation and the documented software stack**.

[SAM3.1's release notes](https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md) report roughly 7× speedup at 128 objects on an H100 relative to its November 2025 release. That is not a forecast for ten NBA players on this computer. Original SAM3's 848M-parameter size and CUDA/PyTorch requirements make it a more substantial experiment than a tracker swap.

In [CoTracker's predictor](https://github.com/facebookresearch/co-tracker/blob/main/cotracker/predictor.py), query points use `(t,x,y)`, coordinates are resized internally, and backward tracking is an explicit option. In [TAPIR's implementation](https://github.com/google-deepmind/tapnet/blob/main/tapnet/torch/tapir_model.py), outputs include occlusion and expected-distance uncertainty logits, with query chunking and refinement resolutions. Preserve visibility/uncertainty and original pixel coordinates; a returned point is not automatically a visible measurement. TAPIR's README reports approximately 17 FPS at 480×480 on a mobile Quadro RTX4000 for a particular causal demo, with separate offline/causal accuracy tables.

**Practical distinction:** court marks lie on the plane; tracked jersey pixels and jumping feet usually do not. Point tracking can help propagate calibration evidence, but must be checked against court-line geometry. Prompted masks can reduce review effort, but need measured human correction time as well as mask quality.

## Court registration, camera motion, and 3D limits

### What a homography can support

For points on the court plane, image and court coordinates are related by a projective map. Camera intrinsics/distortion and scene assumptions determine whether that planar model is adequate; see the [OpenCV homography tutorial](https://docs.opencv.org/4.13.0/d9/dab/tutorial_homography.html). A body box's bottom midpoint is only a proxy for floor contact. Cropping, occluded feet, jumping, shadows, and segmentation leakage can move it away from the correct projected ground point.

An airborne ball is not on the court plane. Projecting its image center with the same homography creates a plane-intersection estimate, not a verified 3D ball position. The same limitation applies to a player's torso center. Keep image coordinates, chosen ground-contact point, court coordinates, and the method/status of each transformation distinct.

### Candidate calibration approaches

| Approach | Evidence | Advantage | Basketball/broadcast limitation |
|---|---|---|---|
| Reviewed court correspondences + robust fit | Existing project foundation; [OpenCV geometry](https://docs.opencv.org/4.13.0/d9/dab/tutorial_homography.html) | Inspectable, no new training requirement | Needs enough well-spread visible landmarks and updated geometry after camera changes |
| DeepSportradar segmentation → intersections → calibration | [Baseline code](https://github.com/DeepSportRadar/camera-calibration-challenge/blob/main/modeling/example_camera_model.py) | Basketball-specific line classes and camera targets | FIBA/undistorted data; defaults to average camera parameters when fitting fails |
| TVCalib | [WACV2023 paper/project](https://mm4spa.github.io/tvcalib/) and [code](https://github.com/MM4SPA/tvcalib) | Differentiable segment-reprojection optimization and self-verification | Soccer line taxonomy/checkpoint; learned segmentation and ground-truth segmentation results differ |
| No Bells, Just Whistles / PnLCalib | [NBJW official code](https://github.com/mguti97/No-Bells-Just-Whistles), [PnLCalib](https://github.com/mguti97/PnLCalib) | Keypoint/line geometry and broader camera-view support | Soccer-trained weights and field models need adaptation; not a turnkey NBA homography |
| Temporal court-feature propagation | GMC/CoTracker/TAPIR mechanisms above | Reduces repetitive marking during a continuous shot | Drift, moving people, non-court features, zoom/distortion, and cuts require checks |

The DeepSportradar implementation initializes from `MEAN_H`, calls `cv2.calibrateCamera` only with more than five intersections, fixes distortion terms, and can return the default on fitting errors. **Do not import that silent fallback as a valid reviewed position source.** Return a failed/uncertain calibration state and retain the last reviewed evidence only under an explicit continuity assumption.

[The universal sports-calibration benchmark paper](https://openaccess.thecvf.com/content/CVPR2024W/CVsports/papers/Magera_A_Universal_Protocol_to_Benchmark_Camera_Calibration_for_Sports_CVPRW_2024_paper.pdf) explains why metrics based on different field masks, point projections, or camera models are not interchangeable. In particular, a field-shaped overlay can look good while positions important to player analytics are wrong. Its dataset survey distinguishes public DeepSportradar camera parameters from non-public college-basketball homography data.

### Camera events to retain as explicit states

This is a proposed extension pattern, not a claim that the current pipeline already detects every event:

- Continuous main-camera pan/zoom: propagate only while court residuals and orientation remain plausible.
- Hard cut or new angle: restart image-motion tracking/calibration; keep roster-link candidates separately.
- Replay or slow motion: distinguish video time from game time; do not differentiate positions using the wrong clock.
- Close-up/crowd view: court coordinates may be unavailable although player identity is recognizable.
- Heavy occlusion/limited lines: retain missingness; do not manufacture calibration from an average camera.
- Camera return to a known view: use prior calibration as a proposal, then verify alignment.

### Error propagation into defensive analytics

The following is a mathematical design implication, not a fitted uncertainty model for this repository. Let court position be `p = f(u, H)`, where `u` is the image ground-contact point and `H` the estimated mapping. A local linear approximation gives:

```text
Cov(p) ≈ J_u Cov(u) J_uᵀ + J_H Cov(H) J_Hᵀ
         + cross terms when image-point and calibration errors are dependent.
```

The Jacobians express sensitivity: the same pixel error can become different court-distance errors in different parts of the image. Near ill-conditioned views this approximation can fail; use perturbation or resampling rather than a falsely precise Gaussian interval.

For two players, relative-position covariance includes cross-covariance because both share the camera estimate. Some common error cancels, but not all. Speed from `(p[t+1]-p[t])/Δt` amplifies localization noise and becomes invalid across cuts or incorrect timestamps. Identity swaps produce discontinuities that smoothing can conceal.

Consequently, matchup/closeout/help-distance conclusions should retain the source identity status, calibration status, foot-point confidence, visibility, timing, and interpolation flags. If plausible geometric perturbations change which defender is “nearest” or whether a distance threshold is crossed, that event needs uncertainty or review. Better tracking metrics alone cannot validate possession-level defensive value.

## Code, checkpoints, licenses, and maturity

“Code available” and “weights linked” mean the primary source exposes them; links were inspected without downloading model binaries. A repository license is not automatically a license for its training videos or every dependency. “Unverified” is a recorded gap, not a statement that use is prohibited.

| Component | Code declaration inspected | Weights/data status | Practical maturity judgment |
|---|---|---|---|
| ByteTrack | MIT | Official YOLOX model zoo; dataset terms separate | Established reference; historical dependencies |
| BoT-SORT | MIT | Official detector and ReID links; separate weight-specific grant not established here | Concrete code; older tested Ubuntu environment |
| OC-SORT | MIT declared | Official model-zoo instructions; original detection source matters | Lightweight challenger; 2026 code changes require pinning |
| Deep OC-SORT | MIT | Official pretrained folder; weight-specific terms not separately established | Research reproduction available; several external feature dependencies |
| StrongSORT | GPL-3.0 declared | AFLink/precomputed data links; dependencies and source datasets separate | Useful offline reference; older/manual setup |
| MixSort | MIT root license | Released checkpoints; SportsMOT dataset CC BY-NC4.0 | Sports-specific code, no verified NBA transfer |
| CAMELTrack | Apache-2.0 | Official Hugging Face model card declares Apache-2.0; external detector/ReID/pose terms separate | Released trained association; more integration cost |
| OSNet / Torchreid | MIT | Model zoo and official Hugging Face; training datasets separate | Appropriate current appearance baseline |
| BPBreID / PRTReID | Hippocratic HL3-LAW-MEDIA-MIL-SOC-SV declaration | Pretrained links/GSR checkpoint exist; inspect each release's terms | Occlusion/role research with custom terms |
| SoccerNet GSR | GPL-3.0 | Multiple external checkpoints; protected video access may require NDA | Modular research framework; exact evaluator version matters |
| Jersey-number-pipeline | CC BY-NC3.0 | Hockey/SoccerNet weights; hockey data requested from author | Concrete multi-stage code, domain adaptation needed |
| TrackID3x3 | Original code Apache-2.0; bundled MIT/Apache/CC BY-NC components | Dataset declared CC BY4.0; external pretrained models separate | Available baseline/data; manual courts and subset notebooks |
| SAM2 | Apache-2.0 explicitly includes checkpoints and training/demo code | Direct official checkpoints; SA-V dataset terms separate | Strong annotation candidate; GPU/Windows integration work |
| SAM3/3.1 | Custom SAM License covers code and trained weights | Gated official checkpoints; current license acceptance needed | Released model; substantial stack/hardware requirements |
| Cutie / XMem | MIT roots; third-party GUI components separate | Official pretrained downloads; dataset and weight-specific terms must be checked | Practical research GUIs and mask propagation |
| CoTracker | CC BY-NC4.0 majority; third-party exceptions | Official online/offline checkpoints; datasets separate | Strong point-tracking candidate with noncommercial terms |
| TAPIR / BootsTAPIR | Apache-2.0 software | README explicitly extends Apache-2.0 to released checkpoints; TAP-Vid annotations CC BY4.0, underlying videos vary | Useful causal/offline alternatives; JAX/PyTorch choices |
| TVCalib / NBJW | MIT / GPL-2.0 respectively | Soccer checkpoints available; weight/data terms separate | Calibration research references, not basketball plug-ins |
| DeepSportradar subprojects | Uniform code/data license not established by inspected README pages | Public challenge data/models linked; confirm per-task distribution terms | Basketball-relevant; old task-specific release structure |

License evidence: the ledger links each inspected license/README, including [SAM2's explicit grant](https://github.com/facebookresearch/sam2#license), [SAM3's license](https://github.com/facebookresearch/sam3/blob/main/LICENSE), [CoTracker's license](https://github.com/facebookresearch/co-tracker/blob/main/LICENSE.md), [TAPNet's declarations](https://github.com/google-deepmind/tapnet#license-and-disclaimer), and [TrackID3x3's component distinctions](https://github.com/open-starlab/TrackID3x3#license). SoccerNet's [data access page](https://www.soccer-net.org/data) distinguishes public annotations/features from protected video access.

No local throughput, peak VRAM, installation success, model-file integrity, or commercial deployment suitability was established. Component FPS cannot be added or compared without the same resolution, object count, detector, device, preprocessing, and output requirements.

## Proportionate next experiments, when a player issue justifies them

1. **Use the existing evidence first.** Identify whether an actual error is detection, association, roster identity, foot localization, or calibration. A tracker change is not the fix for all five.
2. **Compare saved detections.** Start with the existing tracker and one motion-only challenger. Keep identical input boxes, scores, timestamps, ignored-region handling, and review clips.
3. **Add the cue needed by the failure.** Camera compensation for pans; appearance for separable re-entry cases; masks for contaminated crops; OCR for visible number evidence. Ablate the added cue.
4. **Measure useful outputs.** Report swaps/fragmentation around actual occlusions, identity accuracy with unknowns, court-position error, and human correction time. Separate observed and interpolated coverage.
5. **Check runtime on a representative sample.** Measure end-to-end wall time and peak resource use on available hardware. Choose batch sizes and model sizes from measurements, not paper FPS.
6. **Keep held-out possessions independent.** Do not tune on them or treat reused training footage as unseen validation. Reuse reviewed outputs as regression evidence without regenerating them unnecessarily.
7. **Integrate only the increment that helps.** Preserve possession-scoped configuration, provenance, and human review; avoid a new general framework unless the benefit requires one.

Annotation cost should be measured in person-minutes on representative material. Relative burden is predictable, exact hours are not: dense masks and every-frame poses cost more than sparse court landmarks or a few legible jersey frames; tracking-assisted annotation can reduce drawing while increasing drift-checking. For this repository, focused corrections to already-reviewed player data are likely more economical than replacing all annotations, but that is a hypothesis to measure.

## Research limitations and reproducibility

- This is a primary-source desk review and selective source inspection, not reproduction or a systematic meta-analysis.
- Core repository revisions are recorded in the JSON ledger. GitHub's API rate limit prevented resolving every remaining branch tip; those entries explicitly retain access-date/branch references.
- No live webpage content dated after the research date is used as a new research finding. Where release pages evolve, explicit publication/release dates or pinned revisions are preferred.
- Some checkpoint/data licenses remain unresolved; no license was inferred solely from a download link.
- SportsMOT, fixed-camera 3x3, pedestrian MOT, and soccer minimap results do not establish NBA-broadcast performance.
- No source found establishes that end-to-end named-player identity, calibrated court trajectories, and defensive attribution are solved together for this project.
- The next useful action remains delivering and reviewing the current ball/player trajectory increment, then applying these options to a demonstrated player or geometry failure.
