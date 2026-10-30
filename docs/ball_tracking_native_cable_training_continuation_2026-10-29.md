# CPU-validated checkpoint and next supervised continuation

October 29, 2026. **Preparation only; no GPU workload launched.** Ryan requested
CPU validation of the new checkpoint and preparation of the next supervised
training continuation, keeping Debug Mode ON. He explicitly removed the old
remaining-time constraint and asked for the most useful accuracy and diagnostic
evidence. That changes the operational time policy, not the frozen scientific
recipe, data roles or acceptance criteria.

## Decision and why it is useful

Finish the existing four-fit candidate-quality pilot, using the completed
diagnostic epoch-six checkpoint for the first fit's endpoint. Do not repeat its
2,244 logical updates. Score that first fit on CHI, then complete the other three
fixed fits and the full declared score comparison. A favorable or unfavorable
first-fold score does not change the later fits, their six-epoch endpoints or
the reporting population. There is no adaptive early stop for accuracy, sweep,
additional epoch, new architecture or automatic tracker integration.

This is the best-supported bounded continuation among the reviewed options,
not a claim that this recipe is globally optimal. Earlier WASB adaptation and
motion corrections made real gains; later near-perfect training fit did not
resolve the NBA gaps. The point experiment improved on whole-crop features but
failed weak e01, hidden and historical cases. The first fit of its learned
successor is complete but unscored; the full four-fit comparison remains
unfinished. Completing that comparison resolves a real missing
answer before adding more training or changing methods.

The useful result is not simply a smaller training loss. It is whether learned
candidate-point evidence transfers between the declared games while protecting
good native and weak locations and rejecting unsupported locations. A failed
transfer result can still distinguish scene dependence, poor ranking, weak-ball
losses and an unresolved visibility problem.

## Actual checkpoint validation

The new diagnostic checkpoint is
`data/outputs/t/native_cable_reference_diagnostic_2026-10-29_v0_2/attempt_001/leave_chi_out/diagnostic_epoch_06.pth`:
43,272,491 bytes, SHA-256
`6976594931e696a4f9f5c3e624c1048a95d666f6503b10960a4360f5bb9b9cfc`.

The independent CPU audit passed **12,181 checks**. It constructed the actual
pinned DINOv2/head model on CPU, verified the 42 trainable tensors and 3,600,641
parameters, finite AdamW state and update 2,244 for every optimizer state, exact
named parameter/moment restoration, frozen-prefix identity and final group
fingerprints. CPU random-state restoration and saved CUDA RNG byte structure
were checked. **CUDA remained uninitialized; no neural forward, optimizer step
or GPU query ran.** CPU validation does not exercise CUDA RNG restoration or
prove future hardware stability; the launch worker verifies GPU restoration
only during a separately authorized execution.

The checkpoint's original purpose remains "Separate stability diagnostic only;
no scientific adoption or automatic continuation." The new worker records an
explicit import/provenance bridge to the original unchanged first-fit recipe;
it does not edit that checkpoint or relabel the diagnostic as an already scored
scientific result. The original scientific epoch-four checkpoint, all old
failures, unsaved suffixes and diagnostic checkpoints remain intact. The earlier
1,015 exact loss/gradient overlaps support continuity, without proving identity
of every unsaved historical tensor.

## Exact remaining work

| Fixed fit | Training still needed | Final scoring population |
| --- | ---: | --- |
| Leave CHI out | 0 updates; reuse audited epoch six | All 5,935 CHI candidates |
| Leave DEN out | 2,238 updates, six epochs | All 5,790 DEN candidates |
| Leave SAC out | 2,100 updates, six epochs | All 7,088 SAC candidates |
| All three NBA games | 3,288 updates, six epochs | All 19,632 package candidates plus 11,787 emitted development/historical queries |

New work totals **7,626 optimizer updates**, 243,708 fitting presentations,
1,572 scoring forwards / 50,232 scored presentations, and three new-fit parity
forwards / 96 presentations: **9,201 new neural forwards and 294,036 presentations**.
The first fit inherits its verified original parity evidence; it does not repeat
parity or training. The logical four-fit total remains 9,870 updates. Each fresh
fit uses the same original seed and initialization. Only final epoch six is
scored; earlier online losses and recovery checkpoints are not validation-based
checkpoint selection.

Keep the [original full recipe](ball_tracking_candidate_quality_pilot.md): pinned
DINOv2 ViT-S/14, unchanged 64-source-pixel crop/point readout, last two blocks and
final normalization plus the 384→128→1 head, original weighted objective, AdamW
rates, batch 32, deterministic precision and six epochs. No augmentation or
rate change is introduced. The target is geometric usable-location quality,
not semantic ball identity or a calibrated probability.

## Full evidence and decision rules

Reuse the original score consumers and all their source-bound inventories:

- All 3,329 package frames / 19,632 candidates, including 21 empty frames and
  all 241 masked frames. Out-of-fold and in-sample scores stay separate; native,
  weak, visibility, uncertainty, game and episode breakdowns remain explicit.
- All 960 HOU frames, 11,798 query records including 11 image-less missing slots,
  all seven existing arms, 6,720 choice slots and 6,720 declared contrasts.
  Agreements, unchanged errors, both-missing, uncertain and unavailable cases
  stay alongside changes.
- All overlapping adverse/useful groups: ten e01 recoveries, six below-.01 e05
  gains, 21 broad gains, 842 native-correct points, the original six-gain/27-loss
  tags, e05/8–9 failures, e05/206 and shared/added hidden emissions. Tags do not
  filter the full population.
- Saved peak, point and CLS controls; strict ranks and ties; fixed zero-logit
  rejection comparisons; all descriptive retention/rejection breakpoints;
  per-game/episode tables. No breakpoint becomes a selected threshold or new
  emitted point. A missing candidate has no invented image score.
- All 60 historical queries, including only the original 18 DET appearance
  queries; accepted geometry and historical semantic/AI judgments retain their
  distinct roles. No new DET frame, label or protected evaluation is opened.

HOU is exposed development and stays excluded from fitting/threshold selection.
The three held-game fits exclude a game only from the **new scorer**: upstream
cosine nine already trained on those games. This is not end-to-end unseen-game
validation. Thousands of adjacent candidates are not thousands of independent
games; per-game outcomes and weak/hidden subsets matter more than a pooled
accuracy number. Class-balanced objective weights also mean sigmoid scores are
not automatically calibrated population probabilities.

| Observed result after the complete comparison | What it would support investigating next |
| --- | --- |
| Useful held-game and HOU separation with native/weak preservation | A separately specified integration experiment, still requiring unchanged quality and visual gates |
| Strong fitted-game scores but poor held-game scores | Scene dependence/generalization; investigate data/context or regularization before extending epochs |
| Better candidate ordering but harmful hidden-frame survival | Recognition has value, while visibility/abstention needs separate evidence |
| Strong-point protection but e01/other weak-ball losses | A weak-evidence tradeoff that must be diagnosed before using the scorer as a veto |
| Poor fitting together with unhealthy gradients or state changes | Implementation/optimization diagnosis; not a rejection of image recognition |
| Healthy fitting but no useful full-population tradeoff | Evidence against this crop/recipe; wider context, presence or joint temporal evidence remain open |

These are interpretation branches, not automatic follow-on executions or
retroactively selected success thresholds. Headline gains must show losses and
adverse groups beside them. Existing NBA accuracy/error/hidden/gap/recovery and
human-review gates stand. The nine source-uncertain recovery events remain
independently inconclusive. No score-only report completes ball tracking.

## Supervision and revised time policy

The prior original-hour ledger remains preserved: 1,574 seconds charged and a
historical 2,026-second balance. **That balance is no longer an execution cap**,
under Ryan's latest instruction. Future actual work and elapsed time are still
logged; nothing is refunded or erased.

The next attempt ends at its fixed workload endpoint. A generous **90-minute
operational watchdog**, with STOP at 89m30s and 30 seconds reserved for cleanup,
guards against an unexpectedly stuck process; it is not the old pilot allowance
or a target runtime. The full remaining workload has not been timed, so no
precise ETA is promised. The successful diagnostic took 4m21s overall, with only
an approximate 2m34s training-journal window, and cannot prove sustained stability.

Reuse the successful diagnostic's two owned Windows process groups, two-second
GPU telemetry, three-second Windows event watcher, five-second NVIDIA-query
timeout, 80°C/device/thermal/power-brake stops, independent 30-second fault/STOP
cleanup guard and hard deadline armed through the final durable receipt. Stop
on any renewed fault; **no automatic retry**, batch-size adjustment or further
training follows. New journal rows include UTC record times for clearer future
timing/fault diagnosis; those are not exact CUDA-kernel timings.

Keep Debug Mode ON, driver 617.42, both RAM modules at 5200 MT/s and the 250 W
power limit. No driver, BIOS, power, clock or startup change occurred during this
CPU preparation. Debug Mode's last observed state was ON during the successful
diagnostic; it must be checked again immediately before launch. Also recheck
Windows events, available memory, expected GPU, no existing worker and graphics
isolation. A past readiness snapshot cannot authorize a later launch.

## Execution and output paths

Preparation, approval, monitoring and reviews:
`data/outputs/t/native_cable_training_continuation_2026-10-29_v0_1/`.
Scientific outputs: `data/outputs/ball_tracking/candidate_quality_pilot_v0_1/attempt_005/`.
GPU telemetry: preparation `monitoring/attempt_001/`; Windows events:
`events_attempt_001/`. The differing attempt numbers refer to separate scoped
namespaces, not a restart of the scientific pilot.

Prepared launch command, **not run**:

```powershell
& 'C:\Users\Ryan\Projects\player-defense-score\.venv\Scripts\python.exe' -B -u 'C:\Users\Ryan\Projects\player-defense-score\data\outputs\t\native_cable_training_continuation_2026-10-29_v0_1\run_supervised.py'
```

Stop only this future supervised continuation from another PowerShell window:

```powershell
& 'C:\Users\Ryan\Projects\player-defense-score\.venv\Scripts\python.exe' -B 'C:\Users\Ryan\Projects\player-defense-score\data\outputs\t\native_cable_training_continuation_2026-10-29_v0_1\request_stop.py'
```

The stop helper handles startup and rejects the wrong worker module. Verify
actual final cleanup receipts before any further action. No blanket Python kill
or system restart is performed. Existing attempt directories are rejected,
never overwritten. The launcher requires a new approval bound to this concrete
freeze plus fresh readiness before GPU work. Ryan asked to prepare this turn;
the earlier diagnostic approval is fulfilled.

The CPU `analyze_completed.py` adapter reuses both unchanged score consumers for
attempt005 after all four fits and clean supervision complete. It retains full
package, HOU, contrast, frontier and historical output files. An independent
saved-record audit and interpretation follow actual execution; preparation
does not invent scores or guarantee useful results.

## Reading, reuse and validation limits

Reused the completed Sessions 1–16 review (398 available turns/47 pages), selected
foundation evidence, Session 17/18 handoffs and subsequent maintained records.
Read current entries and relevant sections of the required context and
source-map/validation/roadmap, the full historical reassessment, fixed pilot and primary capture,
point/change-comparison and failed-verifier evidence. The independent scientific
review revisits the relevant research and primary crop-study, grouped-evaluation
and rejection-tradeoff sources. This is not a fresh reread of every transcript,
paper, old raw output or video, and no completed experiment was rerun.

The material new question was whether a stability-diagnostic checkpoint could
be reused without losing recipe, state or provenance. The actual producer,
CPU model/optimizer audit and exact saved bindings resolve that technical reuse
question. The previous crash cause and sustained stability remain uncertain;
the cable route/photos remain user/browser-reported.

Current preparation test, supervision review, scientific review, metadata
preflight and preservation receipts live in the preparation directory. Historical
test counts retain their own code scope. The original frozen source/configuration
and all 96 prior worktree contents remain unchanged or preserved beneath verified
additive context entries. NBA remains the goal, cosine nine the research control,
and no model adoption, selector/trajectory, label campaign, protected access,
outside specialist, ACB prototype or Git integration occurred.

Exact preparation records are `checkpoint_audit/checkpoint_audit.json`,
`worker_preparation/test_receipt.json` and `test_receipt_v2.json`,
`supervision_review/supervision_checks.json`, `review/scientific_decision_review.json`,
`review/code_review.json`, `analysis_preflight_v2.json`, `execution_freeze.json`,
`metadata_preflight.json` and `verification.json`. The first seven worker tests
and later two focused metadata/arithmetic checks have separate versioned receipts;
73 CPU supervision checks verify the changed policy and stop/cleanup control flow.
They are not a real GPU run or a guarantee of kernel recovery.
