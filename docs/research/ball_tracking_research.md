# Sports ball tracking research and its implications for Player Defense Score

Research date: **2026-10-08**. This is a primary-source literature and implementation review, not a replication, benchmark run, or model selection decision. No external model was installed, trained, or run; no weights, datasets, or media were downloaded. The companion [source ledger](ball_tracking_sources.json) records inspection depth and unresolved access questions. Repository revisions below are the revisions inspected, not promises about later upstream changes.

## What this changes for our project

**The most useful next family to investigate is a model that learns ball appearance and motion from several images together. WASB's basketball checkpoint is the strongest directly relevant starting point found in this review.** That recommendation is about the next comparison, not a claim that WASB already beats RF-DETR on our footage.

The project has already tried much more than one detector: crop candidate retention, recent-history graph ranking, null endpoints, tighter/wider motion links and costs, a soft nearest-player-box prior, and RF-DETR/YOLO agreement. Some wider-motion and player-context choices helped local selection, while player-adjacent false balls and occlusion remained. Those results are documented in [candidate ranking](../ball_crop_candidate_ranking_results.md), [motion factorial](../ball_crop_motion_factorial_results.md), and [player context](../ball_crop_player_context_results.md). Recommending another generic proximity or smoothness rule as though it were new would ignore completed work.

The recovered cross-detector development comparison has 140/145 localization-eligible frames with an RF raw candidate satisfying the geometric match criterion, 111/145 selected matches before agreement, and 78/145 after agreement. These are six development windows, not a full-game or independent-test result. Candidate availability is an upper bound conditional on our labels, tolerance and exported candidates; it does not independently confirm ball identity or guarantee achievable accuracy. Agreement lost useful sightings without the intended compensating benefit. It rejects this particular agreement rule, not every YOLO model, basketball fine-tuning, temporal learning, or detector fusion design. The underlying run's failed publication/provenance status remains visible. The new corroboration clips have not received human review; numerical rejection of this rule does not require repeating completed reviews.

A temporal heatmap model addresses a different question from our existing graph: **what does a ball look like across adjacent images, even when an individual frame resembles a shoe, hand or background object?** The graph ranks already-produced candidates using prescribed costs. A learned temporal image model can change the evidence itself. A learned crop classifier is another distinct possibility, because it can learn appearance differences among the RF candidates that the graph could not resolve. Neither gain has been demonstrated locally.

## Coverage and evidence standard

The search followed the TrackNet/WASB citation chain, basketball-specific DeepSport work, modern occlusion and blur papers, ball-and-player interaction/physics methods, and 2024–2026 follow-on repositories. It included basketball, tennis, badminton, table tennis, soccer and volleyball. Papers about player tracking or action recognition were not treated as ball-localization benchmarks merely because they used basketball video.

“Code inspected” means the named files were read statically. “Checkpoint linked” means an author repository identifies a file; it does not mean its bytes, embedded architecture, timestamp, training history or inference behavior were verified. “Available” is qualified separately for source code, weights and data. No model's claimed FPS is a prediction for our Windows machine. Search coverage is substantial but cannot establish that every recent paper, private system or inaccessible supplement has been found.

## Candidate comparison

| Family / candidate | Primary evidence and setting | Public artifact position on research date | What is useful here | Main transfer limit / priority |
| --- | --- | --- | --- | --- |
| **WASB, BMVC 2023** | Multi-image HRNet heatmaps; five sports including moving-camera NBA images | MIT code; basketball weights linked; ball annotations linked separately | Direct basketball training; preserves multiple heatmap components before selection | Older CUDA stack, label/metric differences and released tracker mismatch need adaptation; **first comparison** |
| **TrackNet / V2** | Tennis / badminton temporal heatmaps | Original references and several reimplementations; WASB supplies reproducible comparison implementations | Clear simple temporal-image baseline | Shuttle/tennis weights are not basketball evidence; **architecture baseline** |
| **TrackNetV3, MM Asia 2023** | Shuttlecock tracking plus learned trajectory repair | Author code and checkpoints explicitly MIT; training/evaluation code | Temporal appearance, background input, explicit repair mask | Fixed-view median background and inpainting assumptions; **selective components** |
| **TrackNetV4, 2024 preprint / later release** | Motion attention from image differences, tennis/badminton | MIT TensorFlow source; published weight links inspected were placeholders; new data research-only | Lightweight motion conditioning | Pans/zooms also generate motion; pretrained reproducibility unresolved; **second-wave architecture** |
| **TrackNetV5, 2025 preprint** | Signed motion differences and residual spatiotemporal refinement | Official SDK public to read but proprietary; weights/data expressly withheld | Modern design reference | Not a ready open pretrained baseline; **defer** |
| **TOTNet, CVIU 2026** | Temporal 3D convolutions and occlusion-aware training in racket sports | MIT code; TTA access by signed research agreement; no pretrained release established | Direct study of occlusion; visible and hidden states evaluated separately | Hidden targets are inferred, not observed; no basketball experiment; **research/fine-tuning candidate** |
| **BlurBall, CVPRW 2026** | Ball center plus motion-blur orientation/extent, table tennis | MIT code, training code, author-linked weights/data | Blur-aware evidence and annotation conventions | Sport/scale shift, decoding/timing assumptions; **targeted blur candidate** |
| **RacketVision, AAAI 2026** | Multi-racket-sport ball/racket/trajectory benchmark; TrackNetV3 ball module | MIT-labeled code/data; model files listed but no model card/weight license established | Current cross-sport benchmark and clearer artifact organization | No basketball; median background and interpolated trajectory products; **transfer reference** |
| **DeepSportLab / PIFBall / BallSeg** | Basketball-specific ball heatmaps with player pose/segmentation context | DeepSportLab AGPLv3-or-later plus additional license text; separate modern DeepSport repo CC BY-NC-ND | Learned basketball appearance/context alternative | Calibrated arena imagery and crop scale differ; not a broadcast drop-in; **conditional comparator** |
| **FootAndBall / DeepBall** | Specialized small-ball detector, soccer long shots | FootAndBall MIT code and repository checkpoint; DeepBall comparison code also in WASB | High-resolution features and ball-specific training | Fixed soccer-camera split and no occlusion reconstruction; **lower-priority transfer baseline** |
| **TTNet** | Coarse-to-fine ball localization with events and segmentation, 120-fps table tennis | Paper and third-party PyTorch implementations located | Global search plus local crop refinement | Camera/FPS/sport mismatch and reproduction provenance; **design reference** |
| **Physics / joint interaction methods** | Ball flight, possession/contact and player states; often calibrated multiple cameras | Papers and some author code, uneven checkpoint availability | State-dependent constraints rather than unconditional smoothing | Cannot turn one moving 2D view into measured 3D; **later reconstruction layer** |

The rows summarize the dossiers below; none of their reported scores is directly interchangeable with our match/wrong/missing counts.

## WASB: the strongest basketball-specific lead

### Paper, dataset lineage and chronology

Tarashima and colleagues' *Widely Applicable Strong Baseline for Sports Ball Detection and Tracking* is a BMVC 2023 paper, first posted to arXiv on November 9, 2023. It evaluates five sports. For basketball it reports 244,224 training frames from 70 games and 31,104 test frames from 11 games. Reported basketball F1 is 80.6 for step-3 inference and 82.6 for step-1 inference; these are paper-protocol results, not our coverage metric. The work's reimplementations are not all exact reproductions of the original comparator papers. [Paper](https://arxiv.org/html/2311.05237)

The upstream NBA activity dataset's authors describe 181 games collected from 2019. That establishes a chronology distinct from our February 2026 game. It does not by itself authenticate the current remotely hosted WASB weight bytes. [SAM dataset paper, section 3.2](https://www.ecva.net/papers/eccv_2020/papers_ECCV/papers/123530205.pdf)

The inspected WASB basketball config enumerates **30 source test game IDs**, beginning `21800974`, `21801076`, `21801079`, and uses the remaining eligible sources for training. The loader skips games/clips without the needed annotations. Therefore the config's 30 IDs must not be described as 30 actually evaluated annotated games: the paper reports 11. The exact 70/11 annotated membership and acquisition dates require an annotation inventory audit; they were not reconstructed by downloading data during this research. [Pinned basketball config](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/configs/dataset/basketball.yaml), [loader](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/datasets/basketball.py)

### Actual input/output behavior

At inspected commit `923462cacdeb3353b84ddebdedb3f4b7a8553b0f`, the WASB model config uses three RGB input images, three output heatmaps, and a 512×288 working resolution. Its high-resolution branches preserve spatial detail within that working image; this is not the same as running at original 1920×1080 resolution. The detector configuration permits step-3 or overlapping step-1 inference. [Model config](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/configs/model/wasb.yaml), [detector config](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/configs/detector/tracknetv2.yaml)

The postprocessor thresholds sigmoid heatmaps, extracts connected components, computes heatmap-weighted centers, and scores components by accumulated heatmap values. It maps positions back with the supplied affine transform. Multiple components survive this stage, making it possible to preserve ambiguity rather than retain only the final tracker choice. A heatmap sum is a ranking score, not an established calibrated probability of correctness. [Postprocessor](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/detectors/postprocessor.py)

**Static implementation finding:** `Track.predict()` contains a motion predictor, but `OnlineTracker._select_best()` initializes `xy_pred = None` and never invokes it. The update path instead rejects candidates more than the configured displacement from the previous visible coordinate, then selects the highest score. The default `max_disp` is 300. After a missing frame that gate is skipped. Thus the released path inspected is not an acceleration-predicted association gate. This is a source-level observation, not a claim that the published experiment was invalid. A future comparison should identify whether it uses the released behavior or a separately named modification. [Tracker](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/trackers/online.py), [tracker config](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/configs/tracker/online.yaml)

### Label and metric mismatches that matter

The basketball XML reader marks a point visible from `occluded == '0'`; it parses `outside` but does not use that variable in the shown visibility decision. With multiple points it takes the first. Missing annotation entries become invisible coordinates, and clips with no visible point are excluded. This does **not** directly implement our observed/partially-visible amodal estimate/ambiguous/not-visible distinction. In particular, source flags need examination before constructing an adapter or treating its training negatives as equivalent to ours. [Basketball loader](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/datasets/basketball.py)

The evaluator counts a wrong visible localization as `FP1`, a prediction on an invisible target as `FP2`, and an absent prediction on a visible target as `FN`. Recall is `TP / (TP + FN)`, excluding `FP1` from the denominator. Consequently, a model can localize many visible frames incorrectly without those frames reducing that recall denominator. Its F1/AP should not be renamed “fraction of visible balls correctly tracked.” Export coordinates and rescore them with our evaluator. [Evaluator](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/utils/evaluator.py)

The inspected evaluation path compares transformed-back predictions with original annotation coordinates and takes its tolerance directly from configuration. Its timer excludes later visualization, and its throughput counter adds `batch_size × frames_in`, which can count repeated contributions under overlapping inference. These are reasons to report our own unique decoded frames, timestamps, end-to-end latency and source-pixel tolerance rather than transplant FPS or a “4 pixel” number without its coordinate convention. [Evaluation runner](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/runners/eval.py), [evaluation configuration](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/configs/runner/eval.yaml)

### Reproducibility and terms

The official model zoo lists sport-specific pretrained models, including basketball, plus comparator checkpoints. Its basketball Google Drive link is published, but the browsing tool could not access the file page; no checkpoint was downloaded or hashed. The setup instructions separately link original images and supplemental ball annotations; their training section remains `TBA`. These are materially better starting artifacts than a paper-only architecture, but they are not a verified local installation or complete turnkey training release. [Model zoo](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/MODEL_ZOO.md), [dataset setup](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/GET_STARTED.md)

Code is MIT. No separate explicit grant covering the linked weights and NBA source footage was established in the inspected material; those remain separate questions. The published stack is old: the Dockerfile pins NumPy 1.22.4 and PyTorch 1.11 with CUDA 11.3. The detector explicitly refuses CPU operation and wraps CUDA inference in `DataParallel`. This requires an isolated compatibility assessment for our current Windows/Python/PyTorch environment, not replacement of the project environment. [License](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/LICENSE.md), [Dockerfile](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/Dockerfile), [detector implementation](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/detectors/detector.py)

**Project inference:** compare raw basketball heatmap evidence first, with its native tracker as a separately attributable option. Preserve component candidates and explicit no-ball outputs. This distinguishes learned image evidence from the already-tested graph ranking and avoids crediting a new model for an unrecorded change to association or gap filling.

### Challenge to the recommendation: the minimum honest adapter

WASB is the best-supported *first candidate*, but it is not already compatible with our observation contract. Our labels target the complete ball center, including defensible amodal centers for partial visibility; fully hidden frames have no localization truth. WASB's binary annotation visibility and heatmap centroid cannot be presumed equivalent. A centroid can land on the visible patch or blur rather than the complete ball. The adapter must preserve our labels and score outputs against them, not relabel them to fit the external model. [Our annotation and raw-data contract](../ball_tracking_annotation_protocol.md)

The preprocessing path loads PIL RGB images, applies an affine bilinear warp, then ImageNet channel normalization before concatenating channels. It derives the affine transform from image center and maximum image dimension. Replacing it with a generic resize/letterbox call may change coordinates or appearance. Preserve the forward/inverse transform, source dimensions and color convention in the adapter. [Image loader](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/utils/utils.py), [dataset loader](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/dataloaders/dataset_loader.py), [normalization](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/dataloaders/__init__.py)

Its basketball sequence builder creates only complete three-frame windows, with no explicit edge padding. Step-3 output can omit a trailing remainder; overlapping step-1 can produce several candidate sets for the same source frame. Its loops also assume contiguous zero-based frame indexing. These behaviors need explicit handling rather than accepting a shorter output silently. [Sequence builder](https://github.com/nttcom/WASB-SBDT/blob/923462cacdeb3353b84ddebdedb3f4b7a8553b0f/src/datasets/basketball.py)

For a scored window `[a,b]`, a proposed overlap-complete policy would read context `[a-2,b+2]`: every scored frame can then occur in all three relative positions of a three-frame input. This **four-frame context expansion is a derived proposal**, not a requirement to run or read new footage during research. All context must belong to the permitted development source and same camera shot; it must not cross a holdout, cut or unrelated replay. At real boundaries, explicitly record unavailable context and either score the supported outputs or declare a separately tested padding policy. Do not duplicate border frames without recording that change. A center-output-only policy needs just one neighbor each side, but changes the released all-output inference design.

The minimal implementation should do five concrete things:

1. Bind the exact model/config, original frame IDs/timestamps, temporal context and preprocessing transform.
2. Export all retained component centers and native scores, plus model/processing failures and genuine zero-candidate frames. Avoid importing the native displacement gate in the first model-evidence comparison.
3. Preserve overlapping contributions and a declared merge/selection policy. Any temporal selection is attributed separately.
4. Use an honestly named temporal point/heatmap output adapter. Our closed image-only raw detection schema requires bounding boxes and `[0,1]` confidence; a summed heatmap score is neither a calibrated confidence nor a COCO box. Do not invent boxes, clamp scores or falsely label temporal inference image-only merely to pass the old schema.
5. Route actual emitted records through the intended evaluator and renderer, checking frame completeness and inverse transforms. Retain no-ball decisions separately from any future inferred occlusion positions.

Those are ordinary integration responsibilities. They do not require a new certificate framework. WASB can still fail because its pretrained NBA images differ in scale, visibility semantics, camera treatment or distractors. If its raw evidence is no better, adding its native tracker would not establish that temporal appearance solved the problem.

## TrackNet lineage: useful architecture, substantial domain assumptions

### Original TrackNet and TrackNetV2

TrackNet introduced multi-image heatmap localization for tiny, fast sports objects; the 2019 paper centers tennis. TrackNetV2 develops efficient shuttlecock tracking. These are ball-specific learning designs, unlike applying a general COCO sports-ball classifier to one image. The original source sites and later ports have different dependencies and protocols; a port is not automatically the authors' implementation. [TrackNet paper](https://arxiv.org/abs/1907.03698), [TrackNetV2 publisher record](https://ieeexplore.ieee.org/document/9302757)

WASB offers a common implementation and checkpoint set for several such baselines, but identifies reproduction limitations. Use those artifacts as explicitly named WASB reimplementations, not an exact replication of every original result. Comparing a simple TrackNet-style model to WASB could help identify whether high-resolution branches are worth their extra integration cost. This is a proposed experiment, not a completed finding.

### TrackNetV3: detection and inpainting must remain separate

The author-linked implementation is **`qaz812345/TrackNetV3`**, associated with Chen and Wang's MM Asia 2023 paper, DOI `10.1145/3595916.3626370`. Other repositories use “TrackNetV3” for different architectures; names alone are unsafe identifiers. The author paper introduces background-assisted prediction and trajectory rectification for badminton. Its median-background assumption is a largely fixed broadcast view. [Author paper](https://people.cs.nycu.edu.tw/~yushuen/data/TrackNetV3.pdf)

At commit `6eda442ada1740573f200f836d93edc9a541ee86`, the supplied workflow trains the heatmap model with sequence length 8 and the inpainting model with length 16. Inference supports nonoverlapping or overlapping weighted/average predictions, records `Inpaint_Mask`, and loads detection and repair checkpoints separately. The utility code establishes a 512×288 working coordinate system. These affordances are useful for keeping raw detections and repair provenance separate. [Prediction code](https://github.com/qaz812345/TrackNetV3/blob/6eda442ada1740573f200f836d93edc9a541ee86/predict.py), [utilities](https://github.com/qaz812345/TrackNetV3/blob/6eda442ada1740573f200f836d93edc9a541ee86/utils/general.py)

The README reports F1 98.56% on its shuttlecock test split and explains match/rally median backgrounds, including a camera-angle exception. That score is not evidence of NBA performance. Background estimation and overlapping temporal prediction can use future frames; “offline” is a valid mode, but must not be described as a causal online tracker. [Author README](https://github.com/qaz812345/TrackNetV3/blob/6eda442ada1740573f200f836d93edc9a541ee86/README.md)

The inspected license expressly includes **pretrained model checkpoints** in its MIT-style permission, unlike a repository badge that only establishes source terms. The linked checkpoint page was inaccessible through the browsing tool, so file access and integrity remain unverified. Dataset terms are a separate matter. [License](https://github.com/qaz812345/TrackNetV3/blob/6eda442ada1740573f200f836d93edc9a541ee86/LICENSE)

**Project inference:** a fixed median background can be invalidated by our camera pans and zooms. Any background registration, cut reset or removal of that channel changes the model's input distribution and may require training. A repaired point is an estimated trajectory state, not a newly observed ball. Evaluate detector-only output before enabling repair.

### TrackNetV4: motion attention with unresolved release completeness

The official implementation at `cb7eea7988474771ceac7e880bbffc35bfa87bca` is TensorFlow/Keras. `MotionPromptLayer` computes grayscale inter-frame differences, transforms their magnitudes with trainable parameters, and fuses motion attention with predicted maps. This is image-derived temporal information rather than our coordinate-graph cost. [Model implementation](https://github.com/TrackNetV4/TrackNetV4/blob/cb7eea7988474771ceac7e880bbffc35bfa87bca/src/models/TrackNetV4.py), [paper](https://arxiv.org/abs/2409.14543)

The dataset instructions define both game-level and clip-level tennis splits and acknowledge differing versions of the badminton dataset. Their working setting is three input images, three outputs and 512×288 resolution. This is why a model-family league table that combines unrelated “TrackNet dataset” scores would be misleading. [Dataset protocol](https://github.com/TrackNetV4/TrackNetV4/blob/cb7eea7988474771ceac7e880bbffc35bfa87bca/docs/DATASET.md)

The inspected results document's weight downloads point to `#`, not checkpoint files. Source is MIT; the new tennis dataset's project page requires a research-only access agreement and restricts commercial use and redistribution. No operational pretrained V4 basketball baseline was established. [Results/artifacts](https://github.com/TrackNetV4/TrackNetV4/blob/cb7eea7988474771ceac7e880bbffc35bfa87bca/docs/RESULT.md), [project and data terms](https://tracknetv4.github.io/)

**Project inference:** basketball camera motion can produce much stronger frame differences than the ball. Test motion attention only with explicit camera behavior strata; it is not automatically a cure for the failures of coordinate-motion rules.

### TrackNetV5: frontier reading, not a ready open baseline

The December 2, 2025 preprint introduces motion-direction decoupling and residual spatiotemporal refinement. Its reported TrackNetV2-dataset F1 is 0.9859, not a basketball result. [Paper](https://arxiv.org/abs/2512.02789)

The official SDK at `779d78f487b63cd76076f8deab27f42dcd4d8930` describes itself as proprietary software for technical exchange and academic study; weights and training datasets are explicitly withheld. It recommends Python 3.10 and CUDA 12.6/PyTorch 2.9. A publicly visible repository is therefore not equivalent to an open permissive implementation with a reproducible checkpoint. [SDK](https://github.com/thaonan/TrackNetV5-SDK)

The inspected motion module separates luminance changes rather than simply discarding their sign. That provides an architectural idea to understand, but copying or integrating proprietary source requires a different rights assessment from MIT code. The paper and SDK are enough to track the direction of research, not enough to justify choosing it for our next local run. [MDD source](https://github.com/thaonan/TrackNetV5-SDK/blob/779d78f487b63cd76076f8deab27f42dcd4d8930/models_factory/basic/mdd.py)

## Occlusion, blur and cross-sport learning

### TOTNet: a serious occlusion study, with a different target definition

Use the **2026 CVIU journal version**, not a mixture of its numbers with the 2025 preprint. The journal TTA dataset has 12,414 samples from 17 para table-tennis matches; the earlier preprint had 9,159 from four. Fully occluded centers are inferred from neighboring visible positions, geometry and contact timing. Thus its hidden-ball accuracy measures agreement with an inferred reference. The journal uses 4-pixel visible/partial and 10-pixel fully-occluded thresholds at the resized scale; the preprint specifies 5/10. Neither version evaluates basketball. [Journal paper](https://rbouadjenek.github.io/assets/pdf/YCVIU_104657.pdf), [preprint version](https://arxiv.org/html/2508.09650)

The inspected implementation at `8a757f63391b262c14d18b4095486336852dbeef` combines spatial convolutions with explicit temporal 3D convolutions, typically on five images. Its output is a spatial softmax over the heatmap. That normalizes location mass; it does not itself establish the probability that a ball is visible. It must be paired with an explicit absence/visibility interpretation before entering our observation stream. [Model](https://github.com/AugustRushG/TOTNet/blob/8a757f63391b262c14d18b4095486336852dbeef/src/model/TOTNet.py)

The repository provides training instructions, MIT code, occlusion weighting/augmentation settings, and a separate optical-flow variant. TTA access requires an agreement and approval; its stated terms prohibit commercial use and redistribution. A downloadable pretrained checkpoint was not established in the inspected README/tree. Those costs distinguish this from WASB's linked basketball checkpoint. [Repository and access instructions](https://github.com/AugustRushG/TOTNet)

**Project inference:** visibility-aware training is relevant, but our current `not_visible` references intentionally contain no localization truth. We cannot manufacture hidden training centers from them and then claim ordinary detection accuracy. A separate reconstruction task would need its own reference uncertainty and visible/estimated state.

### BlurBall: motion blur contains information, and annotation position matters

BlurBall is a CVPR 2026 CVSports workshop paper based on a 2025 preprint. It introduces 64,119 table-tennis frames with blur labels, uses a blur-center convention, and learns ball localization together with blur properties. Its paper uses an 80/20 train/test split and studies short-horizon trajectory fitting from blur as well as coordinates. It reports that badminton pretraining did not improve its own training outcome. This is a useful warning against assuming visually related sports transfer automatically. [Paper](https://arxiv.org/html/2509.18387)

At commit `2f0f5496f7ba4b5b1a36790749935121b2ce972d`, the model is a WASB-derived, three-image, three-output HRNet with 512×288 working resolution. The repository supplies training and author-linked weights for BlurBall and comparator models. These are table-tennis weights, not a basketball-specific release. [Model config](https://github.com/cogsys-tuebingen/blurball/blob/2f0f5496f7ba4b5b1a36790749935121b2ce972d/src/configs/model/blurball.yaml), [repository](https://github.com/cogsys-tuebingen/blurball)

Two implementation details merit explicit handling. The inspected table-tennis split config lists training match `13` twice and omits `14`; do not silently translate that to an assumed contiguous split without checking the loader/data. The frame-extraction helper offers similarity filtering and renumbers retained frames; its default is `filter=False`. Therefore a future invocation must preserve a source-frame/time mapping if filtering is enabled, rather than assuming README discussion of duplicate removal determines the actual behavior. [Split config](https://github.com/cogsys-tuebingen/blurball/blob/2f0f5496f7ba4b5b1a36790749935121b2ce972d/src/configs/dataset/tabletennis.yaml), [frame helper](https://github.com/cogsys-tuebingen/blurball/blob/2f0f5496f7ba4b5b1a36790749935121b2ce972d/src/utils/preprocess.py)

The blur tracker retains the same previous-coordinate displacement gate and inactive `xy_pred` path noted in WASB. Blur outputs are useful evidence, not proof that a sophisticated ballistic tracker is already present. [Tracker](https://github.com/cogsys-tuebingen/blurball/blob/2f0f5496f7ba4b5b1a36790749935121b2ce972d/src/trackers/online_blur.py)

Code is MIT. Author Nextcloud links for data/weights were identified but inaccessible to the browsing tool; separate data/weight licensing and actual files were not verified. **Project inference:** first resolve whether our center annotation means physical/amodal ball center, blur midpoint or another convention. Changing that target silently could create apparent improvement without better tracking.

### RacketVision: modern artifacts, different sports

The official AAAI 2026 repository reports code/data release in April 2026. It combines ball tracking, racket pose and trajectory prediction for tennis, badminton and table tennis. Its ball module is based on TrackNetV3 and takes a median-background image. [Official project](https://github.com/OrcustD/RacketVision), [BallTrack module](https://github.com/OrcustD/RacketVision/blob/c44af2a08524d3cb54d818f19686f4cdea4d2793/source/BallTrack/README.md)

The actual checkpoint downloader identifies `linfeng302/RacketVision-Models` and `checkpoints/balltrack_best.pth`, separate racket models and sport-specific trajectory models. The model-host metadata lists these files at revision `a3760773233a0988c9605259743fbdd87c59d3a3`, but has no model card or established weight-license metadata; no bytes were fetched. Dataset documentation distinguishes raw ball annotations, interpolated ball trajectories and prediction datasets. Its MIT metadata is a stated publisher grant, not independent verification of underlying broadcast rights. [Downloader](https://github.com/OrcustD/RacketVision/blob/c44af2a08524d3cb54d818f19686f4cdea4d2793/source/download_checkpoints.py), [model host](https://huggingface.co/linfeng302/RacketVision-Models), [dataset card](https://huggingface.co/datasets/linfeng302/RacketVision)

**Project inference:** this is useful for testing whether multi-sport learning is robust, and for studying learned contact context. A racket is a different interaction cue from a basketball player's hands; its accuracy does not establish that nearest-player proximity solves our persistent false balls.

## Basketball alternatives beyond TrackNet

### DeepSportLab, BallSeg, PIFBall and single-image 3D localization

DeepSportLab is a BMVC 2021 basketball-focused framework combining ball detection, player instance masks and pose with shared learned representations. Its evidence is useful because it studies ball appearance and human context jointly, rather than requiring independent detectors to agree. It is a different task mix and capture setting from one moving NBA broadcast camera. [Paper](https://arxiv.org/html/2112.00627)

The inspected `ball_metrics.py` contains dedicated heatmap/local-peak evaluation and a separate ball dataset input; this is not a generic player-MOT score. The file also carries crop/scale assumptions that require tracing before comparing reported ball accuracy with full-frame tiny-ball performance. The source is an OpenPifPaf fork with AGPLv3-or-later licensing, an additional no-deliberate-harm clause, and a commercial-license route. No basketball pretrained-weight artifact was verified during this inspection. [Metric code](https://github.com/ispgroupucl/DeepSportLab/blob/67b03dd7e8b012de6309adf3fce2694046ccbdad/ball_metrics.py), [license](https://github.com/ispgroupucl/DeepSportLab/blob/67b03dd7e8b012de6309adf3fce2694046ccbdad/LICENSE)

The separate, actively documented `gabriel-vanzandycke/deepsport` repository exposes BallSeg, PIFBall and BallSize tasks and links basketball-instants and ballistic-sequence data. Its source terms are **CC BY-NC-ND 4.0**, not the DeepSportLab license. Its BallSize evaluation deliberately withholds arenas such as Caen, Limoges and Roanne. It also mentions an optional private dependency index. These are concrete provenance, access and integration considerations, not reasons to conflate all DeepSport code into one package. [Inspected repository revision](https://github.com/gabriel-vanzandycke/deepsport/tree/eb902209fcbb5c4ea06332b95f71bb8ef0a46b72)

The associated 2022 3D-localization paper estimates depth from apparent ball diameter, known physical size and a calibrated camera. It needs a localized ball and camera geometry; it is not a substitute for first detecting the correct ball in an occluded broadcast frame. [3D localization paper](https://arxiv.org/html/2204.00003)

**Project inference:** DeepSport offers a credible basketball appearance-training direction if its data and terms fit the intended use. Importing a shared pose/ball system wholesale would be a large architectural change to our already-reviewed player pipeline. A ball-only comparison is a more attributable first step.

### HMMATrack and recent basketball-specific detector/tracker papers

Han, Wang and Wang's 2024 HMMATrack paper studies multiscale feature enhancement and cooperative association on a hand-annotated SportsTrack set. The publisher's indexed table lists 3,660 basketball frames, split 2,196 train /1,464 test, at 1280×720 and 30 fps. A complete accessible code/checkpoint/data package was not established; direct article access was blocked in this session. Therefore it is a relevant paper lead, not a verified deployable baseline. [Publisher record](https://www.mdpi.com/2076-3417/14/4/1376)

Recent papers also use “basketball tracking” for narrower tasks. A 2025 IoT score-tracking system uses an overhead camera and a Raspberry Pi accelerator to recognize rim crossings; that is not a full-possession broadcast-ball benchmark. [Primary paper](https://www.mdpi.com/2073-431X/14/11/469)

A 2026 DeCon-Net paper reports ball metrics while referencing SportsMOT subsets. Before using that claim, the exact ball annotation source and protocol must be reconciled with the upstream dataset; this review did not establish that lineage. It is not included in the actionable shortlist. [Primary paper](https://www.nature.com/articles/s41598-026-39084-4)

These examples are reasons to inspect labels, capture geometry and artifact availability rather than equating “newer paper” with “stronger basketball tracker.”

## Detection, association and physics: what transfers and what does not

### Specialized detection and coarse-to-fine search

DeepBall and FootAndBall demonstrate small-ball-specific feature design on soccer long shots. FootAndBall's official implementation includes `model_20201019_1416_final.pth`, with training on ISSIA cameras 1–4 and validation cameras 5–6, plus a player-detection dataset. That split tests camera transfer within a capture setup; it does not establish unseen-game NBA generalization. Code is MIT; separately documented weight/data terms still need checking. [DeepBall paper](https://arxiv.org/abs/1902.07304), [FootAndBall repository](https://github.com/jac99/FootAndBall), [exact configuration](https://github.com/jac99/FootAndBall/blob/01261092a93de55026745e532a2e12188ad86801/config.txt)

TTNet jointly models ball location, table-tennis events and segmentation and uses global/local stages. Its 120-fps table-tennis capture is very different from our lower-frame-rate broadcast. Repositories by later implementers must be labeled as such, rather than presented as author replication. [TTNet paper](https://arxiv.org/html/2004.09927), [third-party PyTorch implementation](https://github.com/maudzung/TTNet-Real-time-Analysis-System-for-Table-Tennis-Pytorch)

**Project inference:** coarse-to-fine search and learned candidate appearance remain worthwhile ideas. We have already retained high-resolution crop candidates; the new information would come from a better learned discriminator or temporal images, not merely cropping again. Reacquisition must include a wider search after a gap, otherwise a wrong prior can trap the search on a false object.

### Joint ball/player state and physical constraints

Maksai, Wang and Fua's CVPR 2016 work explicitly models ball states such as flight and possession, physical constraints and player interaction through mixed-integer optimization. It evaluates basketball, volleyball and soccer using calibrated overlapping multiple cameras. It includes a not-present state. The lesson is state-dependent reasoning: a ball held by a player, bouncing and flying should not obey one universal motion model. The published system's 3D multi-camera evidence is unavailable from our broadcast alone. [Primary paper](https://arxiv.org/html/1511.06181)

Parisot and De Vleeschouwer's graph-based ballistic work is another historical basketball lead: fit candidate observations into plausible flight segments instead of treating every frame independently. It is not evidence that a parabola should be imposed across dribbles, hand contact, rebounds or camera cuts. [Primary paper](https://projet.liris.cnrs.fr/imagine/pub/proceedings/ICME2011/HTML/Papers/MainConference/paper_1011.pdf)

MonoTrack's CVPRW 2022 pipeline combines badminton court geometry, shuttle tracking, player pose, shot segmentation and nonlinear 3D reconstruction. The author repository includes a modified TrackNet and separate court/pose/trajectory components. This is a useful example of making geometry and contact events explicit. Shuttle aerodynamic assumptions and court constraints cannot be copied into basketball. [Paper](https://arxiv.org/html/2204.01899), [author code](https://github.com/jhwang7628/monotrack)

*Where Is The Ball* (CVPRW 2025) estimates 3D trajectories from a 2D track using simulation-trained recurrent networks and a representation designed for reprojection consistency. The paper studies a fixed monocular camera. The project page still labels code, simulation and dataset links “coming soon”; we did not verify a complete release. It is a later reconstruction option once reliable 2D evidence exists. [Paper](https://arxiv.org/html/2506.05763), [project](https://where-is-the-ball.github.io/)

**Project inference:** a calibrated floor homography is sufficient for points on the court plane, not for an airborne ball. A projected image parabola also need not remain a parabola while the camera pans or zooms. Physical priors can constrain hypotheses and expose impossible jumps; they do not make a hidden center directly observed. Keep 2D detection, estimated 2D continuation and inferred 3D trajectory as separate products with uncertainty.

### Learned graph association and segmentation prompts

Zou and colleagues' 2024 graph-neural-network table-tennis paper learns node/edge scores from candidate features and optimizes trajectories. That is different from hand-set graph costs, but still depends on candidate quality and its capture/domain assumptions. Code, trained weights and an independent basketball result were not established in this review. [Primary article](https://www.nature.com/articles/s41598-024-80056-3)

SAM-style video segmentation is a possible prompted tracking tool, but a mask propagator does not solve initial ball discovery or certify its identity after occlusion. The team-wide systems chapter covers foundation-model trackers. For this ball chapter, no quantitatively validated basketball SAM baseline was established; attractive overlays alone would not resolve our false-ball selection problem.

TSFMO (ACCV 2022) broadens the comparison beyond one sport: it contains 250 small/fast-object sequences, roughly 50,000 bounding-box-annotated frames, and evaluates generic trackers alongside S-KeepTrack. It is relevant to initialization, abrupt motion and search-region failure. Bounding-box tracking after initialization remains a different contract from finding the correct basketball and declaring absence on every frame; its benchmark is supporting evidence, not a substitute for our basketball test. The publisher abstract and linked project were identified; complete code/checkpoint inspection was not performed. [Publisher record](https://openaccess.thecvf.com/content/ACCV2022/html/Zhang_Tracking_Small_and_Fast_Moving_Objects_A_Benchmark_ACCV_2022_paper.html)

## Terms, availability and compatibility must be checked independently

| Artifact | Source code terms verified | Weights | Data / footage |
| --- | --- | --- | --- |
| WASB | MIT license file | Basketball file linked; bytes/access/independent terms unverified | Original NBA images and added annotations separate; rights not established here |
| Author TrackNetV3 | MIT-style license explicitly includes checkpoints | Author link; browser access failed | Shuttlecock dataset is a separate upstream asset |
| TrackNetV4 | MIT repository | Inspected links are placeholders | New tennis set has research-only access conditions |
| TrackNetV5 SDK | Explicit proprietary notice | Withheld by publisher | Withheld by publisher |
| TOTNet | MIT repository | No release established | TTA by agreement; research only, no redistribution/commercial use |
| BlurBall | MIT repository | Author Nextcloud link; bytes and separate terms unverified | Separate author Nextcloud link; terms unverified |
| RacketVision | MIT repository | Checkpoint filenames verified by host metadata; no model card/weight terms established | MIT-labeled dataset card; upstream video rights not independently audited |
| DeepSportLab | AGPLv3-or-later plus additional text | No checkpoint verified | DeepSport assets separate |
| Modern DeepSport repository | CC BY-NC-ND 4.0 | Not verified | Kaggle assets separate; inspect their own terms |
| FootAndBall | MIT | Named file in repository; not downloaded | ISSIA and player dataset terms separate |

This table records observed notices rather than providing a legal conclusion. A future acquisition should retain the exact notice and artifact revision. Do not interpret a code license, a paper's open-access license or a dataset-host badge as proof that every included broadcast can be redistributed.

For Windows integration, the material compatibility issues are Python/PyTorch/TensorFlow versions, CUDA requirements, old NumPy APIs, Linux paths and shell scripts, dataloader process behavior, serialization format, and frame/color/resize conventions. Static reading identifies these risks but cannot determine their runtime impact. Use an isolated environment and a focused check of real model output through the actual consumer, with synthetic shape/transform checks where useful; changing the main environment simply to match an old research Dockerfile is unnecessary. No such check was run during this research.

## Actionable shortlist and decision boundaries

1. **WASB basketball heatmaps:** first establish artifact access, exact checkpoint/config compatibility, label semantics and source-frame mapping. Then propose a direct development comparison with RF crop evidence under the existing evaluator. Preserve raw components and distinguish model-only from model-plus-tracker output.
2. **Learned basketball candidate appearance / temporal image baseline:** use the RF raw availability result to motivate a discriminator that sees crop appearance, potentially adjacent images. Compare against our completed graph/context baselines; do not call the same heuristic graph a novel temporal model. Training data volume, diverse negatives and game-disjoint evaluation determine feasibility.
3. **TOTNet-style occlusion learning:** appropriate if occlusion remains the dominant failure after visual evidence improves. Separate observed localization from inferred continuation; acquire/clarify data and pretrained artifacts first. No immediate claim of basketball transfer.
4. **BlurBall-inspired blur evidence:** a targeted branch if blur explains reviewed failures. Preserve the annotation target convention and frame cadence. Do not replace missing coordinates with confident extrapolations merely to obtain smoother tracks.
5. **DeepSport ball models:** conditional basketball comparator if data rights, artifact access and camera/scale transfer are workable. It should not require reopening the reviewed player pipeline as its first integration step.

Lower priority or deferred: proprietary TrackNetV5 without weights; V4 until release completeness improves; direct shuttle inpainting on unregistered moving NBA footage; additional generic COCO agreement filters without a new evidence hypothesis; multi-camera 3D systems requiring cameras we do not have; player-MOT or action datasets without verified ball labels; hobby overlays without a documented evaluation protocol.

The next scientific decision should answer a concrete uncertainty: **can learned temporal appearance select or recover the real ball without increasing false-ball or hidden-frame alarms?** It should not be an indiscriminate tournament of every repository in this review. The proposed evaluation design remains subordinate to the existing reviewed split and holdout contract; these six development windows remain development evidence. A new method's final visual judgment and any quality-gate decision require its actual synchronized outputs, while numerical rejection of the completed agreement rule does not reopen old reviews.

## Open questions before choosing an implementation

- Which exact WASB checkpoint bytes, annotation version and annotated game IDs are available, and what terms cover each artifact?
- How much of our error is wrong-candidate selection, insufficient spatial evidence, blur, full occlusion, camera movement, or label uncertainty? The pooled 140/145 availability figure does not answer each category.
- Does 512×288 temporal input discard important basketball detail, and would multiscale/crop temporal input help without losing reacquisition coverage?
- How should overlapping-image predictions be combined while retaining one output per original frame and correct boundary behavior?
- Can a learned model distinguish held/partially visible ball appearance from hands, shoes and player-adjacent distractors with the development data we can legitimately obtain?
- Which models provide an actual no-ball/visibility decision, rather than only the most likely position conditional on a ball being present?
- What independent games/camera conditions are needed for training and validation without opening or tuning on the preserved holdouts?
- Which reconstruction estimates would be useful downstream without overstating observation certainty or projecting airborne balls onto the floor?

These questions are not new administrative gates. They identify the unresolved scientific and integration choices that would make the next experiment informative.
