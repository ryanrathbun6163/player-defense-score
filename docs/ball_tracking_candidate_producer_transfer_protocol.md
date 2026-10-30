# Controlled producer-transfer quality experiment v0.1

October 29, 2026. **Design and metadata preparation; no new model work has run.**
Ryan directed moving forward after the independently audited
[coverage result](ball_tracking_candidate_proposal_coverage_report.md). This
protocol specifies the next comparison, its finite inputs and fixed workload.
It is not an execution freeze or a claim of launch readiness.

## Question and the single treatment

Does adding the 461 predeclared, role-compatible alternate-producer point
examples improve the existing image-quality scorer on the original candidate
pools, under the same training-update and presentation budgets?

Compare saved original quality **Q** with one new quality treatment **Q+**.
The treatment expands the eligible fitting population while retaining the
image representation, target semantics, hierarchical objective formula,
optimizer, initialization, source folds and comparison policies. Preserve every
original candidate and reference. The 1,091,879-point alternate pool is not the
training set; its audited 461-point subset is the entire addition.

This is a quality-component test. Existing detector outputs, weak pools and J
results remain saved controls. Do not substitute Q+ into frozen J: its Q and
Q-dependent neighborhood features would change scale and distribution. Refitting
J would require new source-honest nested quality predictions and an explicit
definition of alternate-point response/pool context. A label-selected 461-point
set cannot silently become an observable neighbor pool. That larger integration
question is deferred.

## Evidence, due diligence and alternatives

We carry forward the complete coverage capture and its two scientific audits,
the saved-score CPU failure study, four-fit quality pilot, acceptance experiment
and failed origin ablation. The completed 398-turn/47-page historical review,
Session17–19 handoffs and original source-authority chain are reused. Fresh
reading inspected the latest maintained state, original quality recipe and
training/weighting code, acceptance nesting/policy contract, saved candidate
schemas and the bounded manifest/workload calculations. This is not a new
every-transcript or every-paper reread. The design's research and independent
challenge records distinguish freshly checked primary material from reuse.

The new information is actual cross-game support for selected distant errors,
selected hidden emissions and weak recoveries relative to another producer:
304 / 81 / 76 compatible points. Earlier weighting already included positive,
distant and hidden strata; the origin-indicator ablation did not repair the
recipe. This test adds different point inputs, rather than changing that loss
or removing the same flags again. Earlier context, temporal/head-fill and frozen
point/CLS results remain material counterevidence against an automatic context
or smoothing solution.

Fresh primary research supports a controlled test without promising success.
[DCR](https://arxiv.org/html/1803.06799v3) studies hard false positives with positive
and background examples, and warns that nearby real objects can contaminate a
large receptive field. Our geometric point target and alternate producer differ
from its detector-classification task. [JTT](https://proceedings.mlr.press/v139/liu21f.html)
uses selected errors and a small group-annotated validation set; it does not
establish that these selected producer errors represent deployment failures.
[Stacking guidance](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.StackingClassifier.html)
supports keeping second-stage fitting separate from base training predictions;
the project's source-level nesting remains the authority for any later J study.
No new library, model or dataset is acquired.

Four quality fits are the smallest comparison retaining both whole-source
exclusion and the complete existing external regression registry. A CPU gate-only
addition would test shifted response/origin/pool metadata instead of learned
image evidence. A full nested quality-plus-J experiment is a larger intervention
before this component question is answered. New permitted footage is the direct
alternative for current-detector failures on genuinely new scenes; a different
representation/visibility diagnostic needs a specific omitted-information
hypothesis. Neither alternative is ruled out by this design.

## Finite population, provenance and controls

The fitting registry is the original **18,813 NBA candidates plus 461 additions**:
19,274 rows on the same 3,179 accepted training frames. Keep all 1,289 old unknown
rows for scoring/reporting; they never fit. The all-NBA known-target union is
17,985: 3,509 positive, 14,080 distant negative and 396 certain-hidden points.
The additions comprise 304 selected distant negatives, 81 selected hidden
emissions and 76 weak positives (67 with alternate native wrong, nine missing).
Use the exact audited membership, with no new difficulty cap, seed search,
candidate mining, relabeling or producer threshold change.

The original candidate IDs remain intact. A separate producer-prefixed training
row key disambiguates provenance; the manifest checks raw-ID uniqueness rather
than assuming it. All source video/frame/PTS/PNG identities, accepted reference
bindings, coordinates, targets and uncertainty travel with each row. Source roles
and original human decisions remain authoritative. One historical-frame conflict
already excluded by the capture study stays excluded; no historical semantic
label becomes a fitting target.

There are 461 exact-new point inputs on 394 existing frames and 70 consecutive
source-frame runs. Of these, 452 have new floor-centered crops and nine reuse a
current crop with a different fractional point readout. Reuse those crop pixels
where identities match, while retaining different point weights. Verify the full
input identity and absence of contradictory targets before fitting. Do not drop
the nine as duplicate images or claim 461 new scenes.

The complete old known population supplies ordinary successes and negatives,
including all 610 original weak-positive points. No extra label-selected set of
successful alternate-producer points is needed for this first intervention.
Ordinary controls and the error-enriched additions retain separate reporting
roles; their union is not a deployment-prevalence sample. Adjacent frames and
shared crops do not establish independent objects or plays.

## Same model and objective, with matched training expenditure

Reuse the pinned DINOv2 ViT-S/14 revision
`150c8e7bb7cef2d30ec31b13a517af14840ee3f7`, 64-source-pixel floor-centered RGB crop,
black padding, bicubic resize to 256 and center crop to 224. Retain fractional
point interpolation of four normalized spatial tokens in float64, one final L2
normalization and float32 head input. Freeze embeddings/first ten blocks; adapt
the final two blocks, final LayerNorm and 384→128→1 GELU head: 3,600,641 trainable
parameters. The model sees crop and point only. Producer, origin, response,
selection category, source IDs and reference metadata are not new input features.

Use fresh pinned initialization for each fit, seed 20261028, AdamW backbone/head
rates 1e-5/1e-3, weight decay .01, betas (.9,.999), epsilon 1e-8, clipping norm1,
batch32 and the original deterministic float32/no-AMP/no-TF32/eager-attention
contract. No augmentation, scheduler, warm-start from a fitted model or architecture
change. Original Q checkpoints are controls, not treatment initializations.

Keep weighted binary cross-entropy and the original function: .5 positive,
.25 distant and .25 hidden mass, then equal available game/block/frame/nonempty
native-or-weak origin/candidate. Recompute it only on each fit's eligible union.
Add no producer level, run quota or special multiplier. Numeric weights change
when new child groups/rows enter: the metadata preparation records every old→new
weight and added objective mass by target/game/block/frame/origin. This tests
the population intervention under the original weighting rule, not isolated
visual novelty with every old gradient contribution held constant.

Added rows receive 5.5946%, 10.9310%, 8.8821% and 8.4692% of the total objective
in leave-CHI, leave-DEN, leave-SAC and all-NBA fits respectively. In all-NBA,
2,659 old rows lose weight and 14,865 retain it; none gains weight, and the
smallest new/old ratio is .34375. One DEN hidden addition receives .520833% of
the whole all-NBA objective (.78125% in either applicable two-game fit).
Thus 461 rows are not a negligible perturbation: the inherited hierarchy
concentrates weight on scarce categories. This is an explicit limitation to
test, not grounds for an unplanned weight adjustment.

Six full union epochs would add 264 updates and 8,298 presentations. To avoid
that compute confound, use **six sampled cycles** instead:

1. Preserve the old known-row order, append eligible additions in capture order.
2. For cycle c=1…6, shuffle the complete eligible union with the original
   `random.Random(20261028+c)` rule.
3. Take exactly the original fit's known-row count as the prefix. Split it into
   batches32 with the same final partial-batch size as that original fit.
4. Use `N_union * objective_weight` as the BCE multiplier. Stop at cycle six.

With zero additions this exactly reduces to the original declared six-pass
schedule. The saved control is reused after metadata order/batch parity checks;
no completed control fit is repeated. Every actual prefix, ID exposure count and
weighted exposure total is frozen before execution. Require all old known and
all fit-eligible added points to be seen at least once with these fixed seeds;
otherwise the design fails before training, without reseeding. Some original
presentations are displaced by additions. Six cycles are not six complete union
epochs, and original per-row exposure is not unchanged.

The prepared schedules pass those checks: every addition is presented four to
six times in its eligible fits. Old-row minimum visits are 3 /2 /2 /2 for the
four fits in table order, with maximum six. Added presentations are
1,231 /2,023 /2,151 /2,699 respectively; all other fixed slots retain original
examples. These are exact planned memberships, not observed training outcomes.

At a fixed model, uniform-prefix sampling with the stated multiplier targets
the same weighted objective in expectation. The realized cycle masses are not
exact, adaptive SGD is not claimed conditionally unbiased, and unequal weights,
partial batches and clipping remain optimization limitations. Save actual
exposures and batch normalization effects. Use only the fixed cycle-six endpoint;
intermediate checkpoints are recovery records, never selection candidates.

| Fit | Old draw quota per cycle | Eligible union | Added rows | Fixed updates |
|---|---:|---:|---:|---:|
| Leave CHI out | 11,954 | 12,162 | 208 | 2,244 |
| Leave DEN out | 11,912 | 12,258 | 346 | 2,238 |
| Leave SAC out | 11,182 | 11,550 | 368 | 2,100 |
| All NBA | 17,524 | 17,985 | 461 | 3,288 |
| Total across fits | 52,572 | 53,955 | 1,383 | **9,870** |

Exactly 315,432 training presentations match the saved four-fit control budget.
There is one treatment and one fixed seed, not a sweep or estimate of seed
robustness. Source-held scorer fits do not make the whole pipeline unseen-game:
cosine nine already saw these games; global pretraining exposure is unknown.

## Fixed scoring scope and concrete workload

Score the existing original pools; added points never enter a new inference pool
or alter a policy's candidate identity. Each NBA game's original points use its
source-held treatment model. The all-NBA treatment scores the unchanged NFHS,
HOU main/stress and historical query registries. Missing-image slots stay missing.

| New scoring work | Observed points | Batch32 forwards |
|---|---:|---:|
| Original NBA outer-held pools, batched separately by game | 18,813 | 589 |
| Original NFHS secondary registry | 819 | 26 |
| HOU main 10,778; stress949; historical60, combined original-registry order | 11,787 | 369 |
| Added challenge points with source-held Q+ (253 /115 /93) | 461 | 15 |
| Same added points with saved source-held Q controls | 461 | 15 |
| First-batch producer/readout parity for four fresh fits | 128 | 4 |

Original evaluation retains 31,430 slots /31,419 observed scores, including 11
missing-image slots, on 4,289 context frames. The 461 additions are a separate
error-selected challenge registry with two scores each. There are **10,888 total
new neural forwards and 347,901 candidate presentations**, including training.
Zero new detector calls, gate fits, optimizer updates outside the 9,870 schedule,
or protected-evaluation queries. Do not score the million-point pool.
The external cohorts remain separate reporting views, but share one combined
ordered emitted-query stream for physical batching, exactly as frozen in the
scoring plan. Equal rounded forward totals are not permission to reorder batches.

Reuse all original Q scores. The only new saved-Q inference is 15 forwards on
previously unscored added points; its results choose no design setting. Original
all-NBA in-sample scores remain saved diagnostics; this experiment does not add
another 18,813-point in-sample scoring pass. Distinguish omitted new diagnostics
from missing required outputs. No exact runtime is inferred from prior runs.

## Primary evaluation, protection sets and interpretation

Freeze both policies before any Q+ result: the original native identity and
the original **Q-top** identity, including original tie ordering. Each keeps
its fixed point if score>0 or abstains otherwise; equality rejects. There is
no new top-point selection, fallback or trajectory. Use every original eligible,
hidden, masked and missing frame in its proper denominator. Evaluate wrong
locations at the original inclusive10px rule; fitting-unknown boundary misses
remain errors for eligible-frame evaluation with their uncertainty reported.

Primary comparison is Q+ versus **Q**, not Q+ versus a refitted or substituted J.
For each held NBA game and each fixed policy require correct retained >=Q,
wrong accepted <=Q and certain-hidden emissions <=Q, plus zero loss of an exact
Q>0-kept correct fixed-policy identity. Require at least one strict NBA primary
improvement. A pooled gain cannot hide a source or policy regression.

Apply the same per-policy count nonregression and exact-correct protections on
HOU as an exposed external veto. Additionally require zero newly rejected old
Q>0 known-correct weak candidates in NBA and HOU, and zero newly rejected old
Q>0 known-correct HOU stress probes. These are **separate strict weak-point and
stress-probe vetoes**; weak protection includes unchosen alternatives and is
stronger than selected-policy retention alone. Declare that strength now, rather
than calling it an inherited implicit criterion. Freeze exact identities and
original Q states in the evaluation manifest before implementation. Points
already Q<=0, unknowns and missing images remain fully reported, not invented
successes. Preserve all ten e01 recoveries, six below-.01 e05 cases, all21 broad
gains and all earlier adverse/unchanged contrasts, including their failed signs.
HOU chooses no sampling, model, checkpoint, threshold or repair.

The frozen original-Q protection registries contain 6,207 correct fixed-policy
rows across NBA and HOU; 547 weak rows (402 NBA,132 HOU main,13 HOU stress); and
745 known-correct positive-scoring HOU stress queries. These are overlapping
views, not additive distinct successes. NFHS and historical semantics remain
secondary diagnostics. The evaluation manifest retains all 8,578 original
fixed-policy rows, 6,720 original source-choice slots, all eleven missing-image
slots and the original signed states of the 21/6 recovery cases.

For every source/block/policy, retain complete correct/wrong/hidden tables and
exact paired gains/losses/agreements. Also retain full native/weak target-stratified
candidate results, ties, missing/unknowns, all historical roles, full unique-score
retention/error curves with tied groups and endpoints, and old-pool strict-first
ranking diagnostics. New rankings are diagnostic opportunities, not an emitted
replacement policy. The 461 added-point comparisons are source-held challenge
diagnostics; gains there alone do not establish transfer to the original pools.

The fixed-zero component criterion passes only when all primary and veto
conditions pass. It supports a later integration design, not tracker adoption
or a claimed improvement over J. Report full-curve discrimination separately:
fixed-zero gains can be a scale shift; better rankings/curves with a fixed-zero
failure are a mixed result, not a threshold-selected rescue. No best cutoff,
checkpoint, producer subset, seed or extra epoch is chosen from results.

If results fail or are source-dependent, preserve the exact failure and stop
this bounded recipe. Compare a permitted fresh-footage design with a specific
representation diagnostic using the resulting evidence; no automatic wider
pool, reweighting or training extension. The original 95%/1%/zero-hidden,
recovery, temporal and human trajectory gates remain unchanged.

## Counterevidence and execution boundary

The additions are concentrated: DEN contributes one native-hidden point; CHI
supplies 56/76 alternate recoveries; a selected-error run lasts 73 frames. Of 76
alternate recovery frames, 75 already have correct current native choices. The
alternate native producer loses 382 current successes and recovers no current
native failures. None of this supplies fresh-scene current-policy failures,
proves visual insufficiency, or justifies detector replacement.
The 76 positive additions satisfy the accepted distance rule; a dense proposal
pool can also yield chance geometric matches, so these labels do not prove that
the older producer visually recognized 76 balls.

Metadata preparation hashes/reconciles existing records, constructs finite
manifests, weight changes, schedules and workload. It decodes no images, loads
no model, runs no neural call or fitter and queries no GPU. Preserve all145
inherited worktree contents and the original handoff chain. Original references,
all failed/completed experiments and Git branch/HEAD/index remain untouched.

Implementation must add a new runner/consumer and exclusive output attempt,
bind this protocol, manifests, sources, caches, models, tests and actual execution
direction. Focused checks must cover no-addition schedule parity, exact budgets
and tails, membership and source exclusion, weight scaling/exposure, full crop+
point identity, fitting-unknown handling, no-label inference inputs, fixed-policy
ties/no-fallback, all protection sets and raw-score transport. Verify model,
cache and initialization compatibility; validate the actual first batch without
adding undeclared forwards. Independently audit saved scores, model/accounting
and complete outcomes without repeating completed scientific experiments.

Reuse owned-job supervision, Debug Mode ON, fresh device/process/UI readiness,
two-second telemetry and existing80C/device/fault stops. A later prepared launch
uses a 90-minute operational watchdog (5,370s soft stop,30s cleanup), not a runtime
promise. Preserve partial checkpoints/failures; no automatic retry, fallback,
extension, system-setting change, new labels, protected access or Git integration.
This turn completes the concrete design and metadata preparation. Implementation
and neural execution remain unrun; no launch command or readiness is claimed.
