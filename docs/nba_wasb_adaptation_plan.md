# Bounded NBA adaptation experiment

Ryan approved the explained experiment with “Ok I like this chat. Move forward”.
The [experiment config](../configs/ball_tracking/wasb_experiments/nba_wasb_adaptation_v0_1.json)
and [approval record](../configs/ball_tracking/reviews/nba_wasb_adaptation_approval_v0_1.json)
were fixed before any new fit or inference. The approval records the actual
conversation; implementation details and the conservative numerical screen below
are assistant-specified, not separately user-selected values.

The question is whether a short continuation fit using accepted NBA examples
improves a different, development-visible game while retaining earlier NFHS
performance. This follows the [saved-heatmap diagnosis](nba_hard_example_heatmap_inspection_results.md):
58 of 69 missing outputs lack above-cutoff local support in every original
contributor. Training better ball responses is a hypothesis, not an established
fix or a demonstrated single cause.

## Data roles

| Source | Frames | Positive centers | Hidden references | Other unsupported | Role |
| --- | ---: | ---: | ---: | ---: | --- |
| SAC–MEM accepted references | 300 | 270 | 17 | 13 | Training |
| Existing reviewed NFHS training | 150 | 130 | 19 | 1 | Training |
| SAS–DET accepted references | 340 | 237 | 69 | 34 | Out-of-fit development comparison |
| Six existing NFHS development windows | 150 | 145 | 5 | 0 | Regression comparison |

SAC blocks are native source frames 660–719, 940–1059 and 1240–1359. NFHS blocks
remain P001 100–124, 250–274 and 375–399; P002 318–367; P003 416–440.
Native NBA 16/17 ms and NFHS 40 ms spacing remain separate. No context crosses
a block boundary, and no padding, temporal interpolation or resampling is used.

The combined set yields 434 triplets; ten entirely masked SAC triplets are
excluded, leaving 424 usable triplets. A deterministic shuffle samples 400 for
200 batches of two. Actual triplet and frame exposures are recorded; including
a frame in the accepted pool does not imply its channel contributes a loss.
Only certain-hidden frames are negatives; ambiguous geometry is loss-masked.
NBA references retain AI authorship and Ryan's later acceptance.
The training hidden references above are certain and contribute negative targets.
DET's 69 hidden references have probable confidence and are used only by the
unchanged evaluation rule; they do not become certain training negatives.

## One fit and one fixed comparison

Initialize from a copy of the expanded checkpoint with SHA-256
`09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`.
Use a fresh Adam optimizer, 200 updates, batch two, seed 1234, learning rate
0.0001, float32, trainable weights with frozen BatchNorm running buffers, target
disk radius 2.5 heatmap pixels and the established masked weighted loss. No
augmentation, mining or checkpoint search. Evaluate final update 200 only.
This continuation changes both data composition and optimization exposure;
it does not isolate the causal benefit of NBA data alone.

New predictions cover the two existing NBA action cores: SAC 540–2010 and DET
10668–11898, totaling 2,702 frames / 2,698 complete triplets. The six original
25-frame NFHS development contexts add 150 frames / 138 triplets. Fixed policy:
strict heatmap response >0.3, original float32 averaging of overlapping complete
triplets, largest component mass with stable tie order, inclusive ten-source-pixel
localization radius. No threshold screen, motion selector or interpolation.
The original model's saved observations are the comparison arm and remain intact.

Before model execution, the following conservative screen is fixed:

| Comparison | Baseline | Required new result |
| --- | --- | --- |
| DET correct / missing / wrong | 207 / 22 / 8 of 237 | At least 208 / at most 21 / at most 8 |
| DET hidden alarms | 13 of 69 | At most 13 |
| DET easy controls | 60 of 60 correct | All 60 correct |
| NFHS correct / missing / wrong | 130 / 14 / 1 of 145 | At least 130 / at most 14 / at most 1 |
| NFHS hidden alarms | 0 of 5 | Zero |

All conditions must hold to pass this numerical screen. It is not statistical
significance, independent NBA validation, automatic model promotion or a replacement
for the existing ball-phase finish line. SAC results describe training fit only.
DET was already repeatedly inspected and is not an independent test game.

## Evidence and review

Keep immutable training attempts, sample schedule/exposures, final checkpoint,
inference caches, per-frame outcomes and baseline bindings in the new ignored
`data/outputs/ball_tracking/nba/wasb_adaptation_v0_1/` tree. Preserve failures and
consumed calls. A reporting/rendering repair reuses completed predictions.

Produce two complete paired NBA videos at 30 source frames per playback second
(about half-speed), plus six short NFHS videos at six frames per second. These
playback speeds do not change model inputs. Each includes every source frame,
source index/time, clear old/new legends and an actual final-frame hold. Check
the emitted records and encoded video transport, then inspect final frames.
Ryan's new model-output visual review remains a separate acceptance decision,
including if the numerical result is negative.

TOR, sealed NFHS holdouts and their buffers remain outside scope. No new labels,
source intervals, second fit, operating-point promotion, push, PR or merge is
authorized by this experiment. Original player-coordinate baselines, prior fits,
the negative motion result and its three pending human reviews are unchanged.
