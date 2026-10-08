# WASB basketball checkpoint: development transfer results

Recorded 2026-10-08. Execution commit: `96907dfdf77fd29474357c6ee7845c2be49fc9dc`.

Subsequent [cached calibration](ball_wasb_calibration_results.md) is now complete.
It doubles error-free observed matches to 62 at threshold 0.2, still leaving 83
eligible frames missing. Equal-count RF gives 61 matches and one wrong point;
at the original 31-output count RF can also achieve zero observed errors. The
original fixed-policy results below remain unchanged. See the
[next adaptation plan](ball_wasb_adaptation_plan.md); training has not run.

The fixed WASB policy produced 31 geometrically matched observations among 145 localization-eligible frames, with no wrong observations and 114 eligible frames missing. The saved RF-DETR crop-union top-one control matched 111 frames and was wrong on 34. WASB emitted nothing on the five hidden-ball frames; RF emitted on all five. Every WASB match was already an RF match: WASB recovered zero RF failures and lost 80 RF matches.

This is a sparse, clean development result under one fixed policy, not evidence that WASB is a replacement for RF or meets the ball-tracking quality gate. Human synchronized visual review remains pending. The saved result retains `selected_operating_point: null` and `quality_gate: null`.

## Evidence and fixed comparison

All local generated evidence is under `data/outputs/ball_tracking/wasb/wasb_basketball_transfer_v0_1/`. Its `experiment.json` binds the released development manifest, source clips, reviewed annotations, saved RF candidates, saved RF reports and WASB checkpoint. `summary.json` supplies the descriptive totals; each window has its own `evaluation.json`, `points.json`, inference/cache receipts and `review.json`. This audit read those records without rerunning inference or rendering.

The model source is NTT Communications' WASB-SBDT at revision `923462cacdeb3353b84ddebdedb3f4b7a8553b0f`. `model_runtime.json` records the actual source files and loaded basketball checkpoint, SHA-256 `8d1ba9870d0a6ab37b06ab82bed593c6c09133e713810bac475d0c000bb7e948`, 6,102,633 bytes. Loading used `torch.load(weights_only=True)` and a strict state-dictionary match. This records an actual checkpoint load, not merely an available download link.

The comparison used these fixed choices:

- Three chronological RGB frames produce three aligned heatmaps. Every 25-frame window supplies exactly 23 complete, overlapping triplets, all inside that window. Each target frame takes the mean of its available aligned heatmaps: contribution counts are `1, 2, 3, ..., 3, 2, 1`. There is no external context, padding or endpoint exclusion.
- Components use a strict heatmap value `> 0.5`, weighted centers and eight-neighbor connectivity. The selected point has the greatest native component mass, with candidate order breaking ties. Native mass sums sigmoid heatmap values; it is not a calibrated probability or an RF box-confidence equivalent.
- WASB runs with CUDA, float32 and batch size one. No native tracker, interpolation, training, player coordinates, court coordinates, RF output or annotation is an inference input. Existing reviewed player identity is displayed only in review videos.
- The saved RF control is `four_crop_union`, confidence threshold `0.01`, using its raw candidates and highest-confidence top-one selection. No new RF inference was performed.
- The primary geometric match radius is 10 source pixels. Reports also preserve radii 5, 15, 20 and 30 pixels. The point evaluator reproduced the saved RF control in all 60 declared cells: six windows × two selectors (raw and top-one) × five radii. These are actual recorded comparisons, not a proposed validation count.

## Results by pool

Matched, wrong-present and missing partition eligible frames. Hidden alarms are reported separately on reviewed not-visible frames. The two pools remain separate because they were selected for different purposes.

| Pool | Eligible / hidden frames | RF matched | RF wrong | RF missing | RF hidden alarms | WASB matched | WASB wrong | WASB missing | WASB hidden alarms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Representative | 75 / 0 | 51 | 24 | 0 | 0 | 17 | 0 | 58 | 0 |
| Challenge | 70 / 5 | 60 | 10 | 0 | 5 | 14 | 0 | 56 | 0 |

Across these two development pools, descriptive matched coverage is 31/145 (21.4%) for WASB and 111/145 (76.6%) for RF. Zero wrong WASB outputs is an observation about 31 emitted points on these repeatedly inspected clips; it is not an established population accuracy of 100%.

Raw candidate availability was 70/75 representative and 70/70 challenge for RF, versus 17/75 and 14/70 for WASB. At this fixed heatmap policy, WASB's raw availability and selected match count are identical. The low coverage therefore already appears at candidate emission; the final top-one selection did not discard a larger set of correct emitted candidates.

## Results by window

Frame numbers are inclusive, zero-based source-video indices. In the table, each method's triple is **matched / wrong-present / missing**; hidden alarms are separate.

| Possession | Pool | Frames | Eligible / hidden | RF triple | WASB triple | RF / WASB hidden alarms | WASB recoveries / losses versus RF |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 001 | Representative | 50–74 | 25 / 0 | 8 / 17 / 0 | 0 / 0 / 25 | 0 / 0 | 0 / 8 |
| 001 | Challenge | 200–224 | 25 / 0 | 20 / 5 / 0 | 1 / 0 / 24 | 0 / 0 | 0 / 19 |
| 002 | Representative | 250–274 | 25 / 0 | 20 / 5 / 0 | 15 / 0 / 10 | 0 / 0 | 0 / 5 |
| 002 | Challenge | 25–49 | 25 / 0 | 23 / 2 / 0 | 13 / 0 / 12 | 0 / 0 | 0 / 10 |
| 003 | Representative | 300–324 | 25 / 0 | 23 / 2 / 0 | 2 / 0 / 23 | 0 / 0 | 0 / 21 |
| 003 | Challenge | 150–174 | 20 / 5 | 17 / 3 / 0 | 0 / 0 / 20 | 5 / 0 | 0 / 17 |

The exact directory IDs are:

```text
possession_001_frames_0050_0074_representative_evaluation_development_v0_2
possession_001_frames_0200_0224_challenge_evaluation_development_v0_2
possession_002_frames_0250_0274_representative_evaluation_development_v0_2
possession_002_frames_0025_0049_challenge_evaluation_development_v0_2
possession_003_frames_0300_0324_representative_evaluation_development_v0_2
possession_003_frames_0150_0174_challenge_evaluation_development_v0_2
```

Each directory's `review.mp4` displays synchronized source-frame observations at five playback frames per second. Its `review.json` records all 25 source indices, 25 decoded review frames and successful final-frame decoding. First- and last-frame review PNGs are also present. All six receipts retain `human_visual_review: pending`; mechanical video coverage is not a completed human review.

Local review videos:

- [Possession 001 representative, frames 50–74](../data/outputs/ball_tracking/wasb/wasb_basketball_transfer_v0_1/possession_001_frames_0050_0074_representative_evaluation_development_v0_2/review.mp4)
- [Possession 001 challenge, frames 200–224](../data/outputs/ball_tracking/wasb/wasb_basketball_transfer_v0_1/possession_001_frames_0200_0224_challenge_evaluation_development_v0_2/review.mp4)
- [Possession 002 representative, frames 250–274](../data/outputs/ball_tracking/wasb/wasb_basketball_transfer_v0_1/possession_002_frames_0250_0274_representative_evaluation_development_v0_2/review.mp4)
- [Possession 002 challenge, frames 25–49](../data/outputs/ball_tracking/wasb/wasb_basketball_transfer_v0_1/possession_002_frames_0025_0049_challenge_evaluation_development_v0_2/review.mp4)
- [Possession 003 representative, frames 300–324](../data/outputs/ball_tracking/wasb/wasb_basketball_transfer_v0_1/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/review.mp4)
- [Possession 003 challenge, frames 150–174](../data/outputs/ball_tracking/wasb/wasb_basketball_transfer_v0_1/possession_003_frames_0150_0174_challenge_evaluation_development_v0_2/review.mp4)

## Runtime and implementation checks

There were 138 unique triplet calls: 23 per window. The first window completed in an initial invocation and its cache was reused when the next invocation completed all six windows. Both invocation receipts record completion with no error, at the execution commit above:

| Invocation receipt under `invocations/` | Scope | Recorded wall seconds |
| --- | --- | ---: |
| `1791495221509146300.json` | Possession 001 representative window | 6.942 |
| `1791495317238349000.json` | Complete six-window request, reusing the first window | 26.490 |

The two invocation durations sum to 33.432 seconds. This includes work beyond model inference and is not a general throughput benchmark. The six timing receipts sum to 2.111 seconds for original triplet inference including adapter processing; that measurement excludes decoding, caching, scoring and rendering. The maximum recorded CUDA allocation was 275,631,104 bytes (262.9 MiB). This is PyTorch's allocated-memory measurement, not total GPU use or process peak RAM.

The recorded environment used Python 3.11.15, NumPy 2.4.6, OpenCV 5.0.0 and PyTorch 2.13.0+cu130, with CUDA 13.0 and cuDNN 92000. Source-function and adapter identities, runtime versions, checkpoint provenance and cached triplet frame mappings are retained in the saved evidence.

Implementation validation passed 29 focused tests: 10 adapter, 11 point-evaluator and eight runner tests. Independent report inspection confirmed the six evaluation reports agree with the summary, the 60 saved-control parity cells are present, and all six inference/video receipts cover their declared endpoints. No full-suite run, holdout experiment or replay of earlier completed model studies was used for this comparison. The read-only result audit did not repeat those focused tests.

After the unexpectedly weak first-window response, an independent check decoded only source frames 50–52 and compared the adapter input with the official RGB loader, affine warp and torchvision normalization. The resulting `[1,9,288,512]` tensors were bit-identical: maximum absolute difference zero and zero differing values. Checkpoint/config mapping and single-sigmoid activation also agreed with the inspected upstream path. The three cached raw heatmap peaks were 0.03260, 0.05251 and 0.08275, already below 0.5 before averaging. No additional model inference was used for this check. These checks found no discrepancy at those boundaries; they do not prove exact equivalence to the authors' legacy runtime or identify the cause of weak responses.

## Post-hoc saved-heatmap diagnostic

After the fixed-policy result, a separate diagnostic examined existing mean heatmaps without new inference. It always emits each heatmap's strongest pixel, maps it through the saved affine transform and evaluates the same 10-pixel radius. It does not run the component detector at a lower threshold. Its record is `diagnostics/post_hoc_forced_peak_v0_1.json`, SHA-256 `6043cc1b1ca5440b55d55b9f82e5a356b0833b79aad85dadfda1fef25624ddac`.

Forced peaks match 76/145 eligible frames, are wrong on 69/145, and emit on all five hidden frames. They retain all 31 default-policy matches and find 45 additional matches among the 114 default-policy missing frames, while introducing 69 wrong locations. Matches in the window order above are 0, 4, 21, 21, 16 and 14. A method forced to emit cannot demonstrate hidden-ball abstention.

Compared directly with RF top-one, forced peaks share 75 matches, recover one RF miss (possession 002 representative frame 257), and lose 36 RF matches; neither matches on 33 eligible frames. The separate pool counts are 37/75 representative and 39/70 challenge. This paired comparison is preserved in `diagnostics/post_hoc_forced_peak_rf_overlap_v0_1.json`, SHA-256 `19e9a516a7f3eb5fb89cfefca657d047eb4bed6848a7cabe75b67396ee3d216c`.

Possession 001 representative is a particularly clear localization problem: its global peaks are 910–1,242 source pixels from the reviewed centers, while the maximum heatmap response within ten pixels of truth never exceeds 0.0086. Some other windows retain useful peaks below the default threshold. Weak emission and wrong peak location therefore both need attention; the evidence does not support treating every missing output as just a threshold problem.

This shows some useful localization signal below the fixed emission threshold and substantial distracting signal. It neither establishes that threshold calibration cannot help nor selects a threshold. Label-assisted truth-neighborhood statistics in the diagnostic are explanatory measurements, not an available prediction rule. No operating point or quality gate changed.

For context, the already-saved RF grid also trades coverage for fewer errors. At its largest saved confidence threshold, 0.50, RF has 96 matches, 18 wrong observations, 31 eligible missing frames and zero hidden alarms. None of its saved thresholds produces zero wrong observations across both pools. That grid does not include a demonstrated RF operating point at WASB's 31-observation coverage; a fair equal-coverage comparison remains unresolved. These numbers reuse the original saved RF grid rather than new RF inference or a newly selected threshold.

## Limits and review boundary

These are six short, repeatedly inspected development windows from three NFHS possessions, not six independent games or an untouched test set. Transfer from the authors' reported NBA basketball training setting to these clips is a plausible concern, not a demonstrated cause of the weak response. The fixed overlapping-window mean policy is part of this local experiment and must accompany any comparison to upstream results.

Ten-pixel proximity to a reviewed annotation measures geometric agreement. It does not independently establish physical ball identity, continuous trajectories, possession understanding or downstream defensive value. The five hidden frames (possession 003, frames 165–169) comprise one episode; they do not supply five independent occlusion trials. Endpoints have fewer temporal contributions than interior frames.

The completed run establishes the behavior of this checkpoint and policy on the released development windows. It leaves synchronized human visual review, the explanation for weak heatmap response, any useful calibrated operating point, and independent generalization unresolved. Holdouts remain sealed; reviewed labels, earlier failures, earlier model results and existing quality gates remain preserved.

## Implementation decision and continuation

Retain RF as the working baseline. Do not adopt the fixed WASB setting or the post-hoc forced-peak decoder. Keep the operational adapter and cached outputs: they allow any targeted calibration question to be answered without another model run. A further comparison must address visual discrimination and the coverage/error tradeoff explicitly; training or fine-tuning requires a concrete development-data and split plan. This result does not reject all temporal models or all possible WASB adaptation.

The current ball-phase finish line and quality bar remain unchanged. Human acceptance of a new trajectory is still required before promoting it. Numerical rejection of these inadequate settings does not require Ryan to repeat old reviews or review every newly generated clip.

The completed comparison can be inspected or resumed with:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.\.venv\Scripts\python.exe -m src.ball_tracking.wasb_experiment --stage score
```

This checks and scores the saved observations; it does not invoke the model. The default `--stage all` also reuses complete validated model caches and existing review receipts. Source/checkpoint assets and outputs remain ignored local files, with pinned identities recorded in the committed configuration and adapter.
