# NBA-first saved-model comparison

## Authority and purpose

Ryan approved the prospective NBA-first scope on October 25, 2026:

> Ok chat, let's move forward with NBA-first. Keep the high school work and the same quality criteria, and evaluate our saved models on the existing NBA labels before we do more training.

NBA performance now drives the next development decision. The three high-school
possessions, accepted references, player-coordinate reviews, failed experiments,
frozen code/recipes and checkpoint-recovery history remain intact. Existing
experiment rejection decisions are not rewritten. High-school results remain
secondary regression evidence; their old per-possession nonregression veto does
not choose the next NBA research candidate. This is an explicitly narrower NBA
development scope, not a claim that the previous phase passed.

This comparison performs no fitting, optimizer updates, threshold tuning,
relabeling, interpolation, protected evaluation or automatic model promotion.
It does not change the training mixture. Whether removing high-school training
examples helps NBA performance remains untested.

## Fixed comparison scope

Compare twelve existing WASB weight files: the retained expanded baseline,
epochs one through five of the original completion fit, epochs one through five
of the augmentation fit, and the earlier 200-update NBA continuation. Reuse the
eleven existing HOU-OKC validation outputs and both historical NBA models'
complete saved SAC/DET outputs. Only missing model/context pairs require new
inference. Superseded detector architectures and the rejected TAP pilot retain
their historical results; this is a comparison of the saved WASB fitting
candidates, not a new architecture tournament.

| Existing evidence | Scope | Interpretation |
|---|---|---|
| HOU-OKC, game 0022400879 | Six labeled episodes, 960 frames, 882 eligible centers | Excluded from all gradient fitting; repeatedly used checkpoint validation, not a fresh test game |
| SAS-DET, game 0022500828 | Original 1,231-frame context, including hard examples, easy control and later accepted gap labels | Excluded from gradient fitting; already inspected development data, not an independent test |
| SAC-MEM, game 0022500829 | Original 1,471-frame context, including hard examples, easy control and later accepted gap labels | Training-exposed for the NBA continuation and both completion fits; descriptive only |

The additional 2,879 newly accepted NBA training judgments remain training data
and do not enter a held-out accuracy claim. All original exposure assignments
remain recorded. Baseline weights were trained on NFHS examples; SAC exposure
begins with the later NBA fits. The new model manifest records this distinction.

There are 3,662 context frames per model. New work is 27,928 native three-frame
forward calls: ten models on both historical contexts (26,980 calls) and the
older NBA continuation on the six HOU episodes (948 calls). Reuse covers 15,964
model/frame observations. Every model sees identical context for each scored
block, preserving native timing, boundary contributors, strict >0.3 heatmap
threshold, 512x288 inputs, ascending float32 contributor means and largest
component-mass selection. No extra epoch is run.

## Unchanged quality criteria

Apply criteria separately to each episode/context; aggregate scores are
descriptive and cannot conceal a failing episode. Keep at least 95% correct
automatic locations within inclusive ten source pixels, at most 1% wrong
eligible locations, zero certain-hidden/out-of-view emissions, no eligible
missing run longer than 200ms, no confirmed wrong-object run of 120ms or longer,
and recovery within 120ms with the first correct and next two eligible frames
correct. Complete synchronized human visual review remains required.

Sparse historical labels, clipped episode boundaries, uncertain hidden labels
and missing object-identity judgments remain explicitly unscored or censored.
Correct counts do not establish complete trajectories. HOU is one development
game and DET is a target development context; neither establishes full-game or
cross-game completion. Protected evaluation remains closed until a method is
frozen and Ryan separately authorizes it.

## Execution, review and next decision

The additive runner verifies original reference/code/model bindings, builds an
exact existing-preprocessing disk cache, verifies actual first/middle/final
triplets against the original input producer, and publishes immutable per-block
records. Completed blocks can be reused after interruption. Failures and partial
attempts are preserved. Generated images, heatmaps and reports stay ignored.

Use the existing owned-process supervisor with two-second GPU telemetry. Stop on
device/telemetry failure, temperature at 80 C or active thermal slowdown. Keep
NVIDIA Overlay, Lively Wallpaper and MSI True Color stopped; change no hardware
settings. The execution record states this turn's authority; the unchanged
supervisor also retains its historical monitoring-authorization text.

After numerical evaluation, report every candidate and every episode. Choose a
candidate for a complete baseline/candidate review based on its NBA tradeoffs;
this does not adopt that model. Include difficult target-game context and actual
final frames. Identify the remaining failure types before proposing any further
training. Do not infer that more epochs or the NBA-first scope itself closes
the quality gap.
