# Authorized WASB continuation sequence

October 26, 2026, America/Phoenix. Preparation begins on
`codex/ball-detector-baseline` at `11fcc20cf41ef4e17eea5e3d50310009e495e7f3`,
with a clean index/worktree.

Ryan authorized moving forward after discussing a coherent sequence of training
experiments, including bounded continuation and a controlled learning-rate
comparison: "Okay chat, move forward. Let's finish this sequence and phase and
let's make some good progress today, okay?" This authorizes the work below;
the original campaign, accepted references and quality criteria need no renewed
approval. It does not itself certify phase completion or release protected data.

## First paired study

The latest [768 result](ball_tracking_nba_resolution_results.md) is still improving
on DET at its endpoint: correct counts 211, 216, 218, 218, 219 and wrong counts
eight, three, two, two, one across epochs one through five. Mean training loss
also decreases each epoch. HOU fluctuates and regresses relative to the 512
control, while the 19-frame DET gap remains. Five epochs do not demonstrate
convergence or establish that further training cannot help.

Compare two independent continuations of the same saved 768 epoch-five state:

| Item | Constant arm | Cosine arm |
|---|---|---|
| Parent | Same exact epoch-five weights, Adam moments/steps, RNG and frozen BN state | Same parent; never the constant arm's endpoint |
| New epochs | Absolute epochs 6-10 | Absolute epochs 6-10 |
| Learning rate | Constant 0.0001 | Cosine reduction from 0.0001 to 0.00001 |
| New updates | 7,760 | 7,760 |
| Cumulative updates | 15,520, including the inherited 7,760 | 15,520, including the same inherited 7,760 |
| Examples and augmentation | Frozen schedule epochs 6-10; unchanged absolute-epoch augmentation keys | Identical schedule and augmentation draws |

For local update index `j` from 0 through 7,759, the cosine arm uses
`0.00001 + (0.0001 - 0.00001) * (1 + cos(pi*j/7759))/2` before that update.
Thus the first update is exactly the parent learning rate and the last reaches
the declared minimum. Log the actual learning rate for every new update;
derive it from durable progress on resume instead of mutable scheduler state.
Changing the rate does not reset Adam moments or step counters.

This separates duration under the existing rate from this particular reduced-rate
schedule. It does not establish cosine decay as uniquely best. The choice is
consistent with examining duration and scheduling when performance is improving
near the endpoint, as discussed in the
[Google Research tuning playbook](https://github.com/google-research/tuning_playbook#determining-the-number-of-steps-for-each-training-run).
The earlier 99.66% training-fit assessment belongs to another 512 model and is
not evidence that this 768 configuration has exhausted useful training.

## Fixed inputs, evidence and execution

Preserve the original frozen recipe/code, accepted labels, reviews, failed
attempts and all parent checkpoints/recovery history. Use additive code and
new arm-scoped output directories under
`data/outputs/ball_tracking/wasb_continuation_v0_1/`. Neither arm writes into the
parent run. Retain the complete inherited loss history with explicit parent
provenance so absolute schedule and optimizer progress remain auditable.

Reuse the verified 768 native-frame caches. Keep resolution 768x432, target
radius 3.75, float32, batch two, masked loss, 75% NBA / 25% NFHS mixture, all
training examples, augmentation, frozen BatchNorm buffers, strict >0.3 heatmaps,
native triplet means, component selection and inclusive ten-source-pixel metric.
No new labels, validation-frame fitting, interpolation or threshold search.
The existing readiness evidence applies to unchanged geometry/batch/precision;
do not repeat a disposable GPU run just to start another training recipe.

Verify source state against the completed parent model, optimizer and frozen
schedule before execution. Test actual handoff, absolute epoch/index transport,
learning-rate endpoints, interrupted/resumed equivalence, completed consumers
and cache reuse with focused CPU checks. Bind the new code/plan/recipe before
training. Save each new epoch and resumable state every 25 updates; preserve
failed/unsaved/replayed events honestly. Supervise one GPU workload at a time.
NVIDIA Overlay, Lively Wallpaper and MSI True Color remain stopped. No hardware,
driver or power settings change. Another device/telemetry failure stops that
attempt without automatic retry; routine implementation fixes remain autonomous.

## Comparison and decisions

Reuse the audited parent epoch-five validation as an explicit starting anchor.
Evaluate HOU and existing NFHS selection cohorts after every new epoch, with
NFHS reported as secondary regression evidence. Compare all five saved epochs
per arm on the same eight NBA contexts, reusing their exact HOU observations
and running SAC/DET inference. Reuse the full parent 768 epoch-five comparison
and original 512 controls. Preserve absolute epoch and arm names throughout.

Report all per-episode accuracy, wrong outputs, certain/probable-hidden emissions,
missing intervals, recovery, exact gains/losses and the shared DET gap. The
same 95% correct / at most 1% wrong / zero certain-hidden emissions / temporal
and visual criteria apply. Existing unknown/censored evidence stays unknown;
neither pooled counts nor a training-loss decrease constitutes a pass. HOU/DET
remain inspected development evidence; SAC remains training-exposed. One seed
supports a paired development comparison, not a general hyperparameter claim.

No checkpoint is automatically adopted. Any model clearing every computable
criterion proceeds to synchronized human review; prefer the earliest absolute
epoch, with the constant arm first only for an otherwise tied qualifying epoch.
If none clears, report the improvements and regressions and choose the next
research step from the observed mechanisms. A diagnostic review candidate may
be selected transparently after comparison; that development choice is not
held-out performance or adoption. Preserve earlier checkpoints even when a
later checkpoint regresses. Rejection for adoption does not end the authorized
iterative research sequence by itself.

Protected evaluation still requires a frozen method and separate explicit
authorization. Full human trajectory acceptance, NBA player identity/calibration
and the other remaining project phases cannot be inferred from this fit.

## Expected cost

The measured parent fit suggests roughly 80 minutes for the two continuations,
plus 25-30 minutes for ten saved-model NBA comparisons. Preparation, independent
audits and visual review are additional. These are estimates, not a guarantee
of runtime or phase completion. Both arms have the same predeclared five-epoch
budget; no unrecorded extension or unlimited search is implied. Use the results
to determine the next justified training change while retaining the standing
requirement to discuss substantial scientific, architectural or cost tradeoffs.
