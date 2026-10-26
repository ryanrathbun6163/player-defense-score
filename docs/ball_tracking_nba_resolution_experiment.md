# Proposed NBA resolution experiment

Proposed October 25, 2026, America/Phoenix. **Not executed or authorized for
fitting by the diagnosis request.** This is a concrete next experiment, not a
claim that one more fit will pass. See the [completed diagnosis](ball_tracking_nba_failure_diagnosis.md).

## Recommendation and question

Run one five-epoch WASB adaptation at **768x432**, comparing with the already
completed 512x288 augmentation experiment. Does retaining 1.5 times the linear
image detail recover weak partial-ball detections, particularly the persistent
DET 11075-11093 gap, without worsening wrong or hidden-ball outputs?

This is the most informative next fit among the examined alternatives, in our
judgment, not an experimentally established best treatment. All thirteen saved
weight sets fail that gap. Original basketball weights add essentially no unique
matches and mainly abstain more, weakening initialization-only as the lead
remedy. Training already fits almost all training centers, partial examples
dominate exposure, and negatives are present. More identical epochs, broad
oversampling or adding a focal loss already in use do not address an established
defect. Candidate ranking can repair only two of the 29 DET errors.

Additional pixels directly test an information bottleneck. They cannot restore
detail absent in the native source. Some missed Houston balls are discernible at
512, and head/hidden-ball false detections are distinct observed failure modes, so resolution
may fail and is not expected to solve every error by itself. Negative weighting,
training-only hard mining, a different initializer or architecture remain later
hypotheses, not automatic follow-on jobs.

The [WASB paper](https://arxiv.org/html/2311.05237v2) motivates spatial detail and
describes a 512x288 heatmap model, but does not establish that this proposed NBA
adaptation will satisfy our criteria. Its hard-example soft-label mining is a
training localization method; the isolated reported ablation covers soccer,
tennis and badminton. It is not proof that applying it to our already well-fitted
training frames would fix held-ball misses or hidden emissions.

## Controlled comparison

| Item | Proposed setting |
|---|---|
| Initial weights | Same retained NFHS-adapted checkpoint `09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`; fresh optimizer, not continuation of epoch five |
| Data and sampling | Same accepted 3,329 training frames, 3,103 usable triplets; first five frozen schedule epochs, 15,515 examples / 7,760 updates; 75% NBA / 25% NFHS |
| Resolution | 768x432 instead of 512x288; native frames resized directly, not enlarged from the old cache |
| Target geometry | Radius 3.75 instead of 2.5 working pixels, preserving nominal source-space footprint; document integer rasterization differences |
| Optimization | Same seed 1234, batch two, fresh Adam at 0.0001, betas (0.9, 0.999), epsilon 1e-8, weight decay zero, no scheduler; float32, masked gamma-two loss, frozen BatchNorm running statistics, same trainable parameters |
| Augmentation | Same synchronized 50% mirror and shared brightness 0.9-1.1, with the same separate RNG and draws |
| Inference | Same native triplets, aligned float32 mean, strict >0.3, largest-component-mass selection, no interpolation or reference-conditioned seeding |
| Control | Reuse the completed augmentation experiment; do not rerun it |
| Stopping | Stop at five epochs; no automatic extension, second fit or threshold search |

Changing resolution necessarily changes rasterized heatmap/target dimensions.
Scaling the target radius is a declared dependent geometry adjustment, not an
independent sharpening experiment or a change to the ten-source-pixel metric.
The binary pixel pattern will not be identical at the two resolutions.

## Preparation and measurement

Preserve all existing frozen files. Implement a separate resolution-aware
adapter/cache/target path, bind its code and recipe before scientific execution,
and check actual 1280x720 and 1920x1080 transforms in both directions. Verify
padding/stride, center mapping, masks, component transport and exact native
time joins. Do not resize the old 512 cache or reinterpret hidden/uncertain rows.

Static inspection of the pinned WASB HRNet configuration shows stride-one stems
and three subsequent downsampling levels; both proposed dimensions divide by
eight. This establishes shape plausibility, not runtime or memory feasibility.
First run a **monitored synthetic batch-two forward/backward check on a disposable
model** to measure memory and confirm shapes. This is a task-specific readiness
check, not a hardware stress test. Preserve the unmodified initialization and
use a fresh model/optimizer for scientific training. If memory or execution fails,
preserve the attempt and report it; do not silently change batch size, numerical
precision or optimizer behavior to force the comparison through.

Save every epoch and resumable optimizer/RNG state. Monitor with the existing
owned-process GPU supervisor and preserve telemetry/failed attempts. Keep
NVIDIA Overlay, Lively Wallpaper and MSI True Color stopped; do not change
hardware settings. Evaluate all five epochs on the same eight NBA contexts:
six HOU episodes, the original DET context and descriptive training-exposed SAC.
Also retain the existing high-school development regression comparison, without
opening protected frames or reinstating the superseded high-school selection veto.

Report each episode separately, every gain/loss, missing runs, recovery and
hidden outputs; include the 19-frame DET gap and the two known ranking failures.
Use the frozen accepted references throughout. HOU and DET remain development
evidence, and SAC remains training-exposed. No fresh-test claim is available.

## Unchanged decision rule and budget

Retain every existing requirement: at least 95% eligible correct points within
inclusive ten source pixels; at most 1% wrong eligible outputs; zero certain-hidden
or out-of-view emissions; no eligible missing run over 200ms; no confirmed
wrong-object run of at least 120ms; recovery within 120ms with its existing
three-correct-frame rule; and complete synchronized human review. Preserve
unknowns, boundary censoring and per-episode continuity. Pooled counts cannot
override an individual failure.

No checkpoint is adopted automatically. Report all five against all gates.
If more than one clears every computable NBA requirement, the earliest qualifying
epoch proceeds to human visual review. Missing or censored evidence cannot be
called a pass. If none qualifies, publish the failure and any partial improvement;
do not extend training. Improved coverage with persistent false detections is
progress on one mechanism, not phase completion. Protected evaluation remains
closed until a frozen method and separate explicit authorization.

The completed 512 augmentation fit took 22.3 monitored minutes. The new input
has 2.25 times as many pixels. **Plan roughly 45-75 minutes for training**, subject
to the readiness measurement. Allow roughly **10-15 additional minutes for five
full NBA comparisons**, estimated from the measured 66.84s eight-context control
and the pixel ratio; reuse HOU outputs already emitted during epoch validation.
High-school regression, implementation, checks and visual review add separate
time. These are planning ranges,
not a measured guarantee or a promise to finish the phase within that time.
There is no new labeling campaign.

The old completion plan's conditional resolution fallback is **not triggered**:
hidden/distractor errors still independently fail. This is a newly recommended
NBA-focused research experiment requiring approval of this concrete changed
scope, not execution under that older conditional authorization. Ryan need not
reapprove the existing campaign, references or quality criteria.
