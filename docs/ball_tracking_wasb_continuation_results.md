# Matched WASB continuation results

October 26, 2026, America/Phoenix. Both training/comparison arms and the two
targeted diagnostics are complete. **The sequence is complete; the ball phase
has not passed.**

## Outcome

Both independently initialized continuations completed absolute epochs 6–10,
adding **7,760 optimizer updates each** to the same completed 768 epoch-five
state. Constant learning rate 0.0001 and cosine reduction from 0.0001 to 0.00001
were compared on identical examples and augmentation draws. This is cumulative
refinement within each branch, not a fresh optimizer or one model trained through
both branches sequentially.

**No new checkpoint improves DET correct coverage beyond the parent's 219/241
(90.9%), and none passes the unchanged quality criteria. No model is adopted.**
All ten still miss every eligible frame in DET 11075–11093: 19 frames / 317ms.
The target remains at least 229/241 correct plus every other numerical and visual
requirement. All checkpoints also retain certain-hidden HOU emissions.

Training loss decreases every epoch in both arms, while development results
fluctuate. This establishes that fitting the training objective better did not
produce the required detection improvement in these continuations. It does not
establish parameter convergence, an architecture ceiling, or that every future
training intervention would fail. This is one seed and two particular schedules.

The [frozen plan](ball_tracking_wasb_continuation_sequence.md) and
[recipe](../configs/ball_tracking/proposals/wasb_continuation_v0_1.json) remain
unchanged. The original parent, failed attempts, accepted references, frozen
code, checkpoints, reviews and recovery history remain preserved.

## All checkpoints

Count cells are **correct / wrong / missing**. HOU totals cover 882 eligible
positions in six episodes; DET has 241 and SAC 270. HOU totals are descriptive:
each episode retains its own gates. SAC is training-exposed, HOU repeatedly used
for validation, and DET inspected development footage excluded from fitting.
These are not independent test results or full-game certification.

| Arm | Absolute epoch | HOU /882 | HOU certain-hidden emissions | DET /241 | SAC /270 |
|---|---:|---:|---:|---:|---:|
| Parent 768 | 5 | 841 / 20 / 21 | 18 | 219 / 1 / 21 | 269 / 1 / 0 |
| Constant | 6 | 837 / 25 / 20 | 20 | 219 / 1 / 21 | 269 / 1 / 0 |
| Constant | 7 | 842 / 20 / 20 | 20 | 218 / 1 / 22 | 269 / 1 / 0 |
| Constant | 8 | 840 / 24 / 18 | 21 | 217 / 2 / 22 | 270 / 0 / 0 |
| Constant | 9 | 828 / 35 / 19 | 20 | 218 / 2 / 21 | 270 / 0 / 0 |
| Constant | 10 | 840 / 22 / 20 | 19 | 214 / 0 / 27 | 270 / 0 / 0 |
| Cosine | 6 | 835 / 27 / 20 | 20 | 218 / 1 / 22 | 269 / 1 / 0 |
| Cosine | 7 | 842 / 19 / 21 | 17 | 217 / 2 / 22 | 269 / 1 / 0 |
| Cosine | 8 | 840 / 23 / 19 | 19 | 219 / 0 / 22 | 270 / 0 / 0 |
| Cosine | 9 | 842 / 19 / 21 | 19 | 219 / 1 / 21 | 270 / 0 / 0 |
| Cosine | 10 | 838 / 25 / 19 | 21 | 219 / 0 / 22 | 270 / 0 / 0 |

Cosine epochs eight and ten eliminate the parent's remaining wrong DET output
by abstaining; they do not add a correct position. Constant epoch ten also has
zero wrong DET outputs, but loses five correct positions. Zero wrong outputs
alone is therefore not evidence of passing tracking quality.

The [complete paired summary](../data/outputs/t/wasb_continuation_20261026/paired_summary_completed_001.json)
retains all per-episode gates, uncertain/probable-hidden emissions, exact gains
and losses, NFHS secondary regression cohorts, loss histories and original 512
controls. The [learning curves](../data/outputs/ball_tracking/wasb_continuation_v0_1/paired_plot_v0_2/paired_training_curves.png)
show the shared parent and two independent continuation branches. The first plot
and its source remain preserved; version two only clarifies that a diagnostic
review choice is separate from model adoption, with identical plotted values.

## Diagnostic review choice

After both comparisons, cosine epoch nine was chosen for diagnosis, not adoption.
It ties the best new DET coverage and the best new HOU correct count, with 19 HOU
wrong outputs, while matching all 270 scored SAC positions. This is an explicit
post-comparison development choice, not a frozen qualifying selection or an
independent validation claim. The frozen earliest-qualifying rule returns null.

Relative to parent 768 epoch five:

- HOU gains four correct positions and loses three: net +1. It resolves two
  wrong outputs and introduces one: net −1. Certain-hidden emissions worsen
  from 18 to 19.
- DET eligible outcome sets are identical. Five probable-hidden emissions are
  removed at 11016, 11017, 11026, 11027 and 11064; these remain uncertain
  references and are not reclassified as certain-hidden violations.
- SAC resolves its remaining wrong output, adding one correct position.

The paired review uses parent 768 epoch five on the left and cosine epoch nine
on the right. Complete human trajectory/object-identity acceptance remains
pending; reviewed labels do not imply reviewed model predictions.

## Persistent gap: saved-output evidence

The [ten-model saved-mean analysis](../data/outputs/t/wasb_continuation_20261026/saved_det_gap_both_continuations_20261026T192713431016Z.json)
verifies 230 sampled map hashes. All ten checkpoints have zero components above
the unchanged 0.3 threshold on all 19 gap frames. The largest peak inside any
accepted ten-source-pixel reference circle is only 0.046856. Ranking cannot
recover a candidate that is absent under this method.

All four nearby eligible frames 11098–11101 match in every checkpoint. The
unscored surrounding frames remain unscored; this does not establish a certain
recovery immediately after 11093. For eight checkpoints, three times the largest
mean-map peak is below 0.3 everywhere, ruling out an individually strong
nonnegative contributor being diluted by averaging. That global bound is
inconclusive for both epoch-six checkpoints. No threshold was changed.

## Evidence-limited acceptance gates

This study exposed a separate planning limitation that should have been made
explicit earlier: **with the current reference evidence, training alone cannot
make the automatic qualifying selector return a checkpoint.**

The [structural evidence audit](../data/outputs/t/wasb_continuation_20261026/structural_gate_evidence_20261026T174939286422Z.json)
identifies nine recovery events whose status is forced to `inconclusive` by
source uncertainty, independently of predictions: HOU e03 returns at 146 and
190, and DET returns at 11047, 11075, 11098, 11107, 11476, 11497 and 11557.
The parent already supplies immediate stable correct HOU returns, yet the
accepted probable-hidden evidence still prevents a recovery pass. The frozen
selector requires all automatic gates to be pass or not applicable.

This is distinct from actual detection failures and prediction-dependent
uncertainty, such as the missed HOU e05 return at frame eight. It does not excuse
the DET gap or false detections. The
[nine-event navigation](../data/outputs/ball_tracking/wasb_continuation_v0_1/recovery_evidence_review_v0_1/index.html)
links exact unchanged source/review intervals and reference decisions. It makes
no claim that those events are visually resolvable and proposes no label upgrade.

Final wrong-object review alone cannot clear source uncertainty: the current
scorer has no recovery-adjudication input. Any evidence-supported reference
adjudication would need its own reviewed version while preserving the original.
Insufficient evidence must remain inconclusive. No criteria, labels or frozen
scoring code were changed to remove this blocker. Protected evaluation remains
closed pending a frozen method and separate explicit authorization.

## Actual current-model training fit

An exhaustive native-context pass of cosine epoch nine covers all 26 training
blocks and 3,329 existing frames: 2,941 eligible positives, 147 certain-hidden
frames and 241 masked frames. It performs 3,277 forward calls and zero optimizer
updates. The [assessment](../data/outputs/ball_tracking/wasb_continuation_v0_1/current_training_fit_v0_1/assessment.json)
finds **2,937/2,941 correct (99.864%)**, three wrong and one missing. Of 2,167
eligible partially visible frames, 2,165 are correct. NBA is 2,807/2,811 and NFHS
130/130. This measures the actual current 768 model; the older 512 model's fit
is not substituted for it.

All four localization failures are CHI–IND e02: frames zero and one are partial
ball errors without a correct candidate; frame 70 has a correct secondary
candidate but selects a point 10.56 pixels away; frame 83 has no candidate.
Two certain-hidden emissions remain at CHI–IND e05 frames 490–491. Seven other
hidden emissions have probable/uncertain references and remain separate.

The native loss numerator is 55.292% positive foreground, 44.565% visible-frame
background and 0.143% certain-hidden frames. These are **not gradient shares**.
This exhaustive, unaugmented pass also differs from the balanced, augmented
batch-two optimizer objective. Its 9,114 valid output-channel occurrences and
3,023,806,464 valid pixels are not unique-frame denominators; 717 masked channel
occurrences are excluded. A tiny scalar loss or numerator share does not justify
uniformly increasing a class weight.

The near-perfect training fit alongside unchanged DET failures supports a
generalization-focused next experiment. It does not prove convergence or that
the model cannot learn these scenes. Repeating the same examples for longer,
or emphasizing only four residual training positives, has weaker support now.
The independent 36,780-check CPU audit reconstructs outcomes, transforms,
counts and loss aggregation. Raw logits/mean arrays were not retained for this
diagnostic, so raw loss terms, component extraction and unchanged model tensors
remain bound producer evidence rather than independently repeated inference.

## Temporal-input sensitivity

The [eight-call probe](../data/outputs/ball_tracking/wasb_continuation_v0_1/middle_output_sensitivity_v0_1/completed.json)
compares a real centered triplet with three copies of its middle frame, retaining
all three output channels. Its middle-frame pixels are identical in each pair.

| DET center | Native middle-channel peak near accepted ball | Repeated-center peak |
|---|---:|---:|
| 11075 | 0.041520 | 0.028557 |
| 11084 | 0.001069 | 0.001074 |
| 11093 | 0.000378 | 0.000515 |
| 11099, nearby matched control | 0.888507 | 0.914072 |

The three missed locations remain weak under both inputs; the nearby matched
control remains strong. This supplies no support for repeated-center substitution
as a remedy. It is a limited sensitivity test on synthetic temporal inputs,
not production accuracy, proof that temporal cues are ignored, or a complete
causal explanation. No predictions, thresholds or scoring records were replaced.
An independent CPU audit verifies all eight inputs and 24 raw output channels,
recomputes the paired statistics and passes 234 recorded checks. It performs no
new model calls.

## Visual review

The [complete paired review](../data/outputs/ball_tracking/wasb_continuation_v0_1/paired_review_v0_1/attempts/617eac4110ca45e881207576b3a9bb70/index.html)
contains eight synchronized videos and all 3,662 actual native frames, including
verified final intervals without an added hold. Parent epoch five is left;
cosine epoch nine is right. Legacy canvas headings are comparison roles, not
adoption decisions.

The [AI observations](../data/outputs/t/wasb_continuation_20261026/paired_review_ai_observations.json)
bind the five contact sheets and three individually inspected DET frames. They
include every actual final, new correct/lost positions, probable-hidden removals
and representative false outputs. At HOU e06 frames 210/220/245 both points lie
on a spectator's head; these sparse AI observations do not establish a
human-confirmed continuous wrong-object run. SAC 961 improves through a 0.921px
prediction shift: reference distance changes from 10.867 to 9.948px. It is a
small threshold-boundary gain, not a large distractor correction. DET 11561
remains just outside tolerance at 10.193px; 11557–11558 remain missing.

Complete human trajectory/object review remains pending. Automated opening of
the local HTML was rejected by the browser URL security policy. No workaround
was used; filesystem/link checks and actual exported-image inspection are
separate evidence, not a claim of interactive browser playback verification.

## Operational verification

The first training-fit diagnostic attempt stopped before model execution on an
overly strict launcher-PID check. Its failed receipt and supervisor history are
preserved. The additive corrected guard verifies the real Windows Python
redirector/worker ancestry, exact supervisor/module/arguments and live policy.
It relies on the pinned supervisor's suspended-launch/no-breakaway job contract;
it does not claim independent inspection of the outer job handle. CPU probes
verify the real process chain and reject four mismatched ownership cases. Six
prior guard versions and failed probes remain preserved. This was not another
GPU/device failure or a failed training run.

Both training arms and both complete NBA comparisons passed independent CPU
audits. Handoff verification covers exact parent model/Adam/RNG/history,
unchanged BatchNorm buffers, absolute schedule, every update/LR, all saved
checkpoints and native validation records. NBA audits reconstruct saved-map
components and verify HOU reuse, all controls, native temporal gates and every
published record. No frozen experiment code changed during execution.

| Supervised workload | Seconds | Peak observed temperature | Peak power | Peak GPU memory |
|---|---:|---:|---:|---:|
| Constant continuation | 2,736.844 | 61 C | 135.17 W | 7,118 MiB |
| Constant NBA comparison | 683.532 | 59 C | 106.25 W | 2,879 MiB |
| Cosine continuation | 2,766.516 | 62 C | 135.07 W | 7,416 MiB |
| Cosine NBA comparison | 663.391 | 60 C | 108.19 W | 2,714 MiB |
| Current-model training-fit diagnostic | 185.375 | 59 C | 105.08 W | 2,718 MiB |
| Eight-call temporal probe | 6.218 | 43 C | 11.13 W | 2,084 MiB |

Each exits zero with no stop condition, cleanup error or remaining owned
process. These are measured supervised workload times, excluding preparation,
CPU audits, rendering and diagnostics. Earlier failed runs remain part of the
project's history. A clean sequence does not establish a fix for the prior
graphics crash. NVIDIA Overlay, Lively Wallpaper and MSI True Color were checked
stopped before the workloads; no driver, clock or power settings changed.
The preserved rejected diagnostic attempt additionally consumed 10.375 seconds,
peaking at 43 C with zero model calls. Short probe telemetry is sampled and may
miss a transient peak. The final system query at 19:49 UTC finds no matching
Display/NVIDIA/WHEA/Kernel-Power/bugcheck/unexpected-shutdown events since 17:29
UTC, with no query errors; the three graphics extras are absent and GPU is 43 C.

## Next intervention

Recommend a [two-epoch spatial-augmentation pilot](ball_tracking_wasb_spatial_augmentation_proposal.md)
from the same parent epoch-five state, compared with the already completed
constant epochs six/seven. The single new factor is modest synchronized
scale/translation of existing training triplets and their supervised geometry.
Current augmentation only mirrors and changes brightness. Preserve all other
training and evaluation choices, source labels and quality gates. First verify
target alignment and actual transformed examples, then freeze a separate recipe;
this proposal has not been executed.

This targets the measured training/development gap, without claiming spatial
variation is the proven cause of the DET misses. It cannot manufacture new
hand/ball appearances. Four residual training errors and two certain-hidden
emissions provide weaker grounds for emphasizing hard examples/negatives first.
The proposed compute is about 25 minutes plus preparation, verification and
review, using measured timings and reusing controls. Do not automatically extend
it if the two epochs fail to improve a remaining failure family without
offsetting regressions. The separate reference-uncertainty issue must remain
explicit throughout. Iteration continues through a tested hypothesis; passing
the phase is not promised.
