# Detectors, learned representations, and model selection

Research date: 2026-10-08. This chapter maps options; it does not install, train, benchmark or promote a new model. Read it with the [ball-specific review](ball_tracking_research.md) and [evaluation design](evaluation_data_and_pipeline_design.md).

## What each technology contributes

| Family | What it learns or computes | What it does not establish by itself |
| --- | --- | --- |
| Closed-vocabulary detector: RF-DETR, YOLO, RT-DETR | Locations and scores for trained classes in an image | Which low-confidence proposal is the same game ball across time |
| Temporal heatmap network: TrackNet/WASB family | Spatial ball likelihood using consecutive images | Correct handling of our hidden labels, camera cuts or every basketball domain |
| Motion filter / association graph | Relationships among observations over time | Physical identity when a distractor is also persistent and plausible |
| Appearance model / candidate verifier | Similarity or ball-versus-distractor evidence | Reliable confidence without suitable training and evaluation data |
| Video segmentation / point tracking | Propagation of masks or queried points | Discovery of every target, roster identity, or guaranteed reacquisition after full occlusion |
| Camera calibration | Relationship between image and known court geometry | The height of an airborne ball from a floor homography |
| Video-language model | Semantic descriptions, event proposals and question answering | A calibrated pixel trajectory or validated defensive value |

These are complementary capabilities. A powerful new model does not eliminate the need to decide what counts as an observation, what can remain missing, and what quantity is being evaluated.

## RF-DETR: retain the measured baseline, consider specialization

Our committed dependency list pins `rfdetr==1.9.1`; the existing ball manifest binds a particular `rf-detr-medium.pth` digest. Those historical model bytes and outputs remain the baseline. The live upstream repository is different evidence: inspected default-branch revision `b6814eaba40e30d779562f999e909d785e146738` on 2026-10-08.

The [RF-DETR paper](https://arxiv.org/html/2511.09554v1) studies lightweight specialist detection, a pretrained visual backbone, and weight-sharing architecture search with target-dataset fine-tuning. It evaluates COCO and RF100-VL, not our ball trajectories. The paper also explains why latency measurements depend on hardware and measurement conditions. Its generalization claim is a reason to investigate fine-tuning, not proof that the generic sports-ball category is sufficient here.

The [official repository](https://github.com/roboflow/rf-detr/tree/b6814eaba40e30d779562f999e909d785e146738) provides model families, training and inference entry points. The inspected [license](https://github.com/roboflow/rf-detr/blob/b6814eaba40e30d779562f999e909d785e146738/LICENSE) is Apache-2.0 for the package; the README separates Apache-designated checkpoints from Plus components under PML. Do not generalize the package license to every model variant. Current upstream documentation also evolves independently of our installed version.

**Project judgment:** keep RF as the comparison control. It already provides useful candidates. Fine-tuning a ball-specific model or learning to reject distractors is more directly tied to known errors than replacing it because a new generic detector has a higher COCO score. Training is still a hypothesis until evaluated on separate basketball episodes.

## YOLO: an ecosystem, not one universal result

Our measured comparison used a specific YOLO11x checkpoint, fixed crop geometry and saved .01 candidate floor. It contributed no additional radius-ten matched frame beyond RF, and its tested agreement filter regressed every window. That is a concrete reason to stop that branch of work. It does not imply that basketball-trained YOLO, another resolution or another architecture must fail.

The current [official YOLO26 documentation](https://docs.ultralytics.com/models/yolo26/) describes newer training/deployment changes, small-object label-assignment changes and optional NMS-free inference. The documentation inspected here distinguishes a default one-to-many head from an optional one-to-one path; changing that path changes outputs. Code/models are offered under AGPL-3.0 or an Enterprise license. These are upstream statements, not a measured improvement on our basketball footage.

**Project judgment:** a sports-trained YOLO model remains a reasonable future control if it has a relevant released checkpoint or a fair fine-tuning comparison. Running every newer generic YOLO version is not the highest-value next step. Keep class mapping, resizing, NMS/head choice and confidence semantics explicit so that a model comparison does not accidentally become a preprocessing comparison.

## Other specialist detectors: alternatives, not immediate priorities

| Candidate | Verified source-level availability | Why it might matter | Current depth and reason to defer |
| --- | --- | --- | --- |
| [RT-DETR / RT-DETRv2](https://github.com/lyuwenyu/RT-DETR) | Official Paddle/PyTorch implementations and checkpoint links; custom-data training documented | Efficient DETR alternative and export references | Repository/documentation inspected; no basketball checkpoint or local advantage established |
| [D-FINE](https://github.com/Peterande/D-FINE) | Official ICLR2025 implementation and model resources | Box-regression refinement; possible localization control | Repository entry and stated scope inspected, not a source-level reproduction |
| [DEIM](https://github.com/Intellindust-AI-Lab/DEIM) | Official CVPR2025 implementation | Matching/training convergence improvements | Repository entry inspected; does not specifically answer ball identity/occlusion |

These sources keep the candidate pool wider than RF-versus-YOLO. They are deliberately not ranked by external AP: different training, benchmark and inference conditions make a single mixed leaderboard misleading. Detailed dependency/weight/data licensing for these deferred alternatives has not been cleared in this pass; inspect it if one enters implementation scope.

## Slicing: useful image detail, already locally explored

[SAHI](https://arxiv.org/html/2202.06934v1) proposes slicing high-resolution images for small-object detection and slicing-assisted fine-tuning. Its original experiments concern aerial datasets, not basketball. It supports the rationale for giving a tiny target more network pixels, not a guarantee of selecting the correct ball.

The inspected [prediction code](https://github.com/obss/sahi/blob/80ebdb699851facf87def03c0597e1aeb87a9a2d/sahi/predict.py) exposes slice sizes/overlap, optional whole-image prediction and merging choices. These can change both recall and duplicate/clutter behavior. Its [source license](https://github.com/obss/sahi/blob/80ebdb699851facf87def03c0597e1aeb87a9a2d/LICENSE) is MIT; the underlying detector and weights retain their own terms.

Our [fixed-crop experiment](../ball_detector_tiled_comparison_results.md) already demonstrated local improvements in candidate availability and some selected matches, with regressions and additional clutter. Replacing custom crop plumbing with SAHI might reduce maintenance later, but it is not new evidence that cropping works. Nor can suppressing lower-ranked duplicates recover a wrong top-ranked selection when the highest-ranked box is unchanged.

**Implementation lesson:** preserve transform metadata, include edge/overlap cases, and keep raw versus merged candidates separable. Avoid increasing crop count merely to inflate candidate recall.

## Open-vocabulary detection and foundation models

[Grounding DINO](https://arxiv.org/abs/2303.05499) conditions detection on language. The official [repository](https://github.com/IDEA-Research/GroundingDINO) supplies original model checkpoints and an Apache-2.0 code license. Do not confuse those open releases with later API-branded versions or third-party fine-tuning ports.

The inspected [inference implementation](https://github.com/IDEA-Research/GroundingDINO/blob/856dde20aee659246248e20734ef9ba5214f5e44/groundingdino/util/inference.py) lowercases/normalizes the caption, applies image transforms, and uses separate box/text thresholds. A prompt like “basketball” changes the model's query, not the amount of visual detail present in a blurred few-pixel object. It is a potential annotation proposal tool or challenger, not a verified identity oracle.

Video segmentation and point trackers deserve their own comparison because their initialization and occlusion assumptions differ. The [player/geometry chapter](player_tracking_and_geometry.md) covers SAM2/SAM3, Cutie, XMem, CoTracker and TAPIR with their licensing and initialization limits. Prompts or corrected points can make them helpful for assisted review while changing the amount of human input relative to automatic detection.

**Project judgment:** do not make a general VLM the authority for exact ball coordinates. It can propose clips/events, explain a failure, or assist annotation; source-frame measurements and reviewed labels still establish tracking accuracy. The [complete-project chapter](sports_projects_and_analytics.md) includes the new BasketballBench work and separates semantic understanding from metric tracking.

## How to choose the next implementation efficiently

The order should reflect our bottleneck and integration burden:

1. **Highest information value:** a released basketball temporal heatmap model, compared with saved RF controls. It adds learned image-and-motion evidence we have not tested.
2. **If the pretrained model is promising but mismatched:** target-domain fine-tuning on independent episodes. Compare before/after without simultaneously changing every downstream rule.
3. **If candidate availability remains strong and identity selection remains weak:** a ball appearance verifier or learned association supported by appropriate labels.
4. **Only after a measured need:** new player association, segmentation, court calibration or general orchestration infrastructure.

A useful comparison can stop with a negative finding. A failed reporting step can be repaired from saved data. A model that emits fewer wrong observations but also loses many correct ones requires an explicit tradeoff; smooth visual output alone cannot settle it. These are operating principles for learning faster, not another mandatory ceremony.

## Source and compatibility limits

No external checkpoint was loaded, no dependency was upgraded, and no external repository was executed for this review. Source inspection establishes that code paths/resources exist and reveals assumptions; it does not establish installation success, current weight accessibility, identical benchmark reproduction or local performance.

The local requirements include Python-era packages much newer than several research baselines, including NumPy 2.x and current PyTorch/CUDA. A thin isolated adapter is preferable to downgrading the entire working player pipeline. The eventual implementation should pin the external revision and actual weight bytes after obtaining them, verify image/frame transformations, and record the exact output policy. No paper or license summary here overrides the original component terms.
