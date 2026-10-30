# Evaluation, data, and pipeline design for broadcast basketball

Research date: 2026-10-08. This is an engineering synthesis and proposed evaluation design, not a new experimental result. External methods were researched, not executed. Existing reviewed labels, holdouts and results are unchanged.

## The problem we actually need to solve

Our immediate output is a usable, reviewed ball trajectory synchronized with the three curated player trajectories. A trajectory can contain honest gaps. The eventual defensive score additionally needs identities, possession, actions, matchups, geometry, and a defensible attribution model. A better detector does not automatically solve those later tasks.

The sports literature provides a useful separation between perception, understanding events, and making decisions. We use that taxonomy to organize work, rather than treating a language model, object detector, tracker and defensive-value model as interchangeable. The [Zhao et al. survey](https://arxiv.org/html/2307.03353v1) is a discovery map; original papers and implementations support the method-specific findings in the other chapters.

| Layer | Concrete output | Typical failure | Evidence needed |
| --- | --- | --- | --- |
| Decode and timeline | Source frame, presentation timestamp, shot/clip identity | Wrong offset, repeated/dropped frame, replay mixed with live action | Decode/timestamp alignment and explicit shot boundaries |
| Image observation | Ball point/heatmap or player box in source coordinates | Shoe, hand, logo or spectator mistaken for target | Labeled positive and negative frames; error types |
| Temporal association | Track with observed, missing and inferred states | Persistent wrong target, lost reacquisition, over-smoothing | Whole temporal episodes, gap behavior and paired errors |
| Identity and geometry | Reviewed person identity and ground-plane player position | ID switch, wrong court transform, airborne point projected to floor | Identity continuity and independent landmark/reprojection review |
| Basketball state | Possession, handler, pass, shot, help/switch state | Nearest player assumed to possess ball | Event/relationship annotations and uncertainty |
| Defensive attribution | Transparent contribution under stated assumptions | Confusing correlation or team outcome with individual causal value | Basketball validity, sensitivity analysis and broader data |

This table is our proposed decomposition. It is not a claim that any one reviewed repository solves all six layers.

## What our existing experiments already establish

Read the [corroboration result](../ball_crop_cross_detector_corroboration_results.md), [candidate ranking](../ball_crop_candidate_ranking_results.md), [motion factorial](../ball_crop_motion_factorial_results.md), and [player-context result](../ball_crop_player_context_results.md) before proposing another tracker rule.

- Saved RF crop candidates at the .01 export floor have a center within ten source pixels on 140/145 eligible development frames. This is candidate availability under that geometric criterion, not 140 verified basketball identities or an achievable production accuracy guarantee.
- RF top-one matches 51/75 representative and 60/70 challenge frames at that floor. The tested YOLO agreement filter reduces those counts to 41/75 and 37/70. It supplies no recovery or hidden-alarm suppression.
- Wider motion allowance and some player-context costs already helped certain selections. We have therefore tested more than single-frame detection. Persistent distractors can form plausible paths; player-adjacent false objects have zero nearest-box distance just like the ball.
- A ten-pixel miss can be an on-ball center offset. A ten-pixel match does not by itself establish physical object identity. Completed human/AI diagnostic reviews already exposed both distinctions.
- The five hidden labels are one short episode. They do not support a reliable estimate of hidden-ball behavior across games.

The practical inference is to prioritize **new image evidence and useful missing-state decisions**, rather than another large grid of confidence/motion/proximity constants. A temporal image model is new evidence; reranking the same saved boxes with another similar formula is less novel. Existing development windows remain useful regression examples, but repeated inspection has made them unsuitable as an unseen-game claim.

## A compact scorecard that answers useful questions

The following is a proposed reporting contract. It adds interpretation around existing measurements; it does not silently change established thresholds or label definitions.

| Question | Report | Main caution |
| --- | --- | --- |
| Did a detector offer a usable point? | Candidate recall at the existing radius; candidates/frame; recall after threshold and cap | More proposals can raise recall by guessing widely |
| Did selection choose correctly? | Matched, wrong-present and missing counts with fixed denominators | A confidence score is not an identity label |
| Does abstention help? | Wrong-present versus coverage curve; paired suppressed-wrong and lost-correct counts | An always-missing method must not look successful |
| Does it behave during occlusion? | False emissions per hidden episode; fraction of hidden frames with emissions; reacquisition delay | Five neighboring frames are not five independent episodes |
| Is localization precise? | Error distribution on eligible observations plus recall-versus-radius curve | Conditional error on only successful predictions hides misses |
| Is the trajectory usable? | Longest wrong run, longest visible gap, switches to distractors, reacquisition cases | Smoothness alone can reward a smoothly tracked shoe |
| What does it cost? | Wall time, decode/model/postprocessing/render times, peak memory, review minutes | Model-only FPS omits important work |

For a single emitted observation per eligible frame, use the complete partition:

`eligible = matched + wrong_present + missing`.

If defining accepted-observation precision under the geometric matching criterion as `matched / (matched + wrong_present)`, print its denominator and mark it undefined when there are no accepted observations. This is not independently reviewed object-identity precision. Report coverage `(matched + wrong_present) / eligible` alongside it. Hidden-frame emissions belong in a separate false-alarm measure because a hidden reference does not provide a known center. These definitions are our suggested diagnostics; they are not replacements for existing evaluator conventions.

The general idea of choosing when to abstain is studied in [SelectiveNet](https://proceedings.mlr.press/v97/geifman19a.html). Its image-classification experiments do not establish calibrated risk guarantees for our correlated basketball video. Borrow the risk/coverage question, not an unearned guarantee or an unnecessary neural architecture.

For player tracking, [HOTA](https://arxiv.org/abs/2009.07736) balances detection and association. The inspected [TrackEval implementation](https://github.com/JonathonLuiten/TrackEval/blob/12c8791b303e0a0b50f753af204249e622d0281a/trackeval/metrics/hota.py) combines DetA and AssA, evaluates matching thresholds, and aggregates sequence statistics. HOTA/IDF1 are useful player diagnostics. One-ball coordinate quality, false-target runs and hidden emissions still need explicit evaluation. Do not install this old snapshot into our current NumPy environment without checking compatibility: this inspected file uses the removed `np.float` alias.

[TIDE](https://dbolya.com/tide/) separates object-detection errors such as localization, classification, duplicate, background and missed detections. Its lesson is valuable: choose a correction based on the error type. Our current ball labels are points with visibility states, so using its box-based implementation unchanged would not create an equivalent diagnostic. Reuse the principle and existing local error review before building another evaluator.

## Compare papers without creating a false leaderboard

A numerical result is comparable only after checking the target, footage, split, available temporal context, annotation policy, matching rule and compute conditions.

| Difference | Why it changes the meaning |
| --- | --- |
| Basketball versus tennis/badminton | Different ball appearance, number of occluders, motion, court/background and camera behavior |
| Fixed camera versus edited broadcast | Camera pan/zoom/cuts can resemble object motion; objects leave the view |
| Boxes versus centers versus masks | AP, center-distance F1 and mask IoU measure different things |
| Original pixels versus resized network pixels | A five-pixel tolerance on a small heatmap is not five source pixels |
| Visible-only labels versus inferred hidden positions | A model can be rewarded for estimating through occlusion under one protocol and penalized under another |
| Future frames versus strictly causal prediction | Offline interpolation/temporal windows can use evidence unavailable in live deployment |
| Player IDs versus roster identity | Track continuity is not knowing which NBA player it is |
| Model-only FPS versus full pipeline throughput | Decode, crops, transfer, association and rendering can dominate |
| Selected clips versus complete broadcasts | Easy gameplay excerpts omit cuts, graphics, replay and non-gameplay failure modes |

The basketball checkpoint in WASB is more directly relevant than a large F1 figure on shuttlecock footage. It still needs evaluation under our source-coordinate and visibility definitions. The [ball chapter](ball_tracking_research.md) records the actual preprocessing, outputs and metric differences.

Do not pool external benchmark percentages with ours. Do not claim that RF-DETR beats all YOLO versions because a particular generic YOLO11x checkpoint failed on our six windows. Conversely, a newer model's COCO AP cannot overturn the actual local result without local evidence.

## Labels and data: buy information, not redundant frames

The immediate label inventory is small and heavily reused. Before any fine-tuning, identify which existing data can serve as development/training and which remains untouched evaluation. Keep the original reviewed references unchanged; corrections, if needed, receive an explicit new annotation version.

A useful expansion samples **episodes**, not thousands of adjacent near-duplicates: dribble, pass, catch, shot, rebound, player crossing, referee occlusion, motion blur, camera pan/zoom, out-of-view ball, reacquisition and distracting hands/shoes/logos. Include both common gameplay and hard cases; report their results separately. New sports footage or a public dataset also needs clear access/usage terms before collection or publication.

The minimum annotation fields for a future ball dataset should distinguish source frame/time, visible/partly visible/hidden/out-of-view/uncertain, center when actually supportable, optional extent, and reviewer/version. A visible center should not be invented on a fully occluded frame. A model-generated proposal must retain its origin until a human checks it.

[CVAT's native format](https://github.com/cvat-ai/cvat/blob/b52288c2b7f07184a0ddc6fb9b096ea7cebde9d4/site/content/en/docs/dataset_management/formats/format-cvat.md) supports tracked points/shapes, attributes and video track states. This is a plausible annotation tool, not an obligation to migrate the current JSON annotations. A round-trip check would be needed so that export/import preserves visibility and frame indexing. Linear interpolation can assist drawing but should not automatically label ball bounces, occlusion or cuts as observed truth.

The [FiftyOne uniqueness tutorial](https://docs.voxel51.com/tutorials/uniqueness.html) discusses selecting diverse images and detecting near-duplicates. Its documentation was discoverable, but direct page opening failed during this pass; treat this as a tooling lead, not inspected implementation. The original [temporal active-learning paper](https://openaccess.thecvf.com/content_ICCVW_2019/html/CVRSUAD/Bengar_Temporal_Coherence_for_Active_Learning_in_Videos_ICCVW_2019_paper.html) uses temporal coherence in road-scene video. Our transfer proposal is modest: select diverse basketball error episodes for annotation and keep representative coverage, rather than copying its road-scene results.

For a learned candidate verifier, sample candidates broadly, including true balls, on-ball offsets, high-confidence distractors, duplicates and uncertain examples. A ten-pixel localization miss must not automatically become a negative object-identity label. Do not train solely on previous winners: that excludes the alternatives we need the verifier to distinguish.

## Splits and uncertainty without procedural overhead

Random neighboring-frame splits can put almost the same image in training and testing. Keep an episode together; group by source game for a cross-game claim, and record broadcast/camera context. The official [scikit-learn cross-validation guide](https://scikit-learn.org/stable/modules/cross_validation.html) explains dependent groups and why repeated test-set tuning compromises evaluation. Our specific application is a game/episode manifest and temporal separation; it does not require expensive repeated cross-validation of every large model.

For a temporal model, split before constructing windows. A training input must not reach across a held-out boundary through past or future context. Decode timestamps and source frame indices must remain aligned. Replays of the same action also belong to the same underlying-event group when estimating unseen-action performance.

Report per-episode outcomes and paired changes. When enough independent games exist, a game-level or episode-level resampling analysis may help quantify uncertainty. With only three possessions, a highly precise frame-level confidence interval would exaggerate the evidence. More parameter cells over the same six windows do not increase the independent sample size.

Detector confidence is a ranking score until calibrated for a specified event. [Kuppers et al.](https://arxiv.org/abs/2004.13546) explicitly study object-detection calibration conditional on box scale and location. Our immediate requirement is to name what a score means and compare errors versus thresholds. Fitting an elaborate calibrator to 150 repeatedly used frames would be premature.

Holdouts are useful because they answer whether a choice works beyond the examples that shaped it. This is a scientific reason to preserve them, not a blanket ban on reading development results. Ryan's current policy already permits necessary development-data reads and routine fixes.

## Training choices and stopping decisions

Proposed order:

1. Evaluate a relevant released basketball temporal checkpoint before funding a custom model. Keep raw heatmaps/candidates and final emitted points separable.
2. If its representation helps but domain errors remain, fine-tune using diverse, independent basketball episodes with explicit negatives/visibility. Compare the same architecture before and after training.
3. If RF candidates remain competitive but ranking is weak, consider a learned candidate verifier with a defensible candidate-level dataset. This is a different task from tuning motion constants.
4. If both representations fail on the same tiny/blurred ball, inspect resolution and labeling limits before adding a larger model or another dependency.

A training plan should identify target labels, pretrained weights, split unit, image transform, temporal context, negative sampling, checkpoint selection rule and the measured failure it intends to reduce. It need not create another elaborate approval/certificate framework. Use the smallest useful implementation, and stop adding variants once the current result makes the next decision clear.

Augmentations must preserve the physical target: synchronized spatial transforms across temporal frames, corresponding coordinate changes, realistic brightness/compression/blur, and no assumption that arbitrary temporal reversal preserves event labels. Synthetic balls pasted into images or generative super-resolution can be training/diagnostic hypotheses, but they do not create measured truth about an invisible ball in source footage. Their value requires real-data evaluation.

## Pipeline implementation that avoids repeating expensive work

The key architectural recommendation is a thin adapter around a chosen external model, feeding the existing source-coordinate observation/evaluation interface. Do not import a whole research repository's orchestration stack to get one network.

Proposed observation fields include `source_frame`, `source_timestamp`, `shot_id`, source dimensions, raw model coordinates/score, reversible transform metadata, source-coordinate output, output state, method/config/checkpoint identity and optional reason for missingness. Preserve distinct `observed`, `inferred` and `missing` meanings. This is a design sketch, not a new enforced schema.

Cache stages according to actual inputs: decode -> model observations -> association -> evaluation -> rendering/reporting. A report formatting change should regenerate the report from saved results. A selector change should reuse unchanged observations. A detector or preprocessing change invalidates its observations and their consumers. Failed publication should not erase already computed numerical evidence.

[DVC's pipeline documentation](https://doc.dvc.org/user-guide/pipelines/running-pipelines) demonstrates dependency-aware stage caching. It also documents replacement of stage outputs during reruns, so adopting it blindly would not preserve our reviewed baselines. [MLflow Tracking](https://www.mlflow.org/docs/latest/tracking/) records parameters, metrics, code references and artifacts. These are optional tools; the repository already has substantial provenance machinery. First simplify its existing data flow. Do not add both platforms merely because they are standard names.

The original [Hidden Technical Debt in Machine Learning Systems](https://papers.nips.cc/paper_files/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf) identifies coupled data dependencies, hidden consumers and configuration problems. Our practical response is to make dependency boundaries visible and reduce duplicate machinery—not build more wrappers around every routine operation.

Profile the full useful path before optimizing. [PyTorch Profiler](https://docs.pytorch.org/tutorials/recipes/recipes/profiler_recipe.html) can attribute CPU/CUDA work. Record the hardware, precision, batch size, resolution and temporal context; do not transfer another paper's FPS to this Windows machine. Keep a research dependency environment isolated until the adapter works, then integrate only the needed components.

## Proportionate checks and a usable completion definition

For a new adapter, the high-value checks are: one real output through the existing consumer, RGB/BGR and coordinate scaling, temporal target-frame alignment, first/last-frame policy, explicit absent output, and a compact synchronized review. A source-to-source round trip should catch an offset or resizing bug before a long run. Use the producing component's real fields; avoid another fixture that merely duplicates an incorrect assumption.

Run focused tests on the changed boundary. Broaden to the full suite when shared pipeline behavior or unresolved risk warrants it. Documentation, report formatting and a routine path correction do not justify repeating an already completed full run. Research in this directory did not run the full suite.

Proposed ball-phase exit evidence is one selected implementation with an explicit operating point, per-possession quantitative results, reviewed synchronized player/ball output through final frames, honest missing states, and a concise limitations page. Exact acceptance thresholds remain a project decision; this research does not weaken any existing reviewed gate. Broader unseen-game validation is a later claim requiring broader data, not a reason to leave every useful curated increment unintegrated.

The result should let Ryan say what works, what fails, how to reproduce it, and what the next improvement would test. That is a stronger engineering portfolio story than a large test count or a smooth but unmeasured video.
