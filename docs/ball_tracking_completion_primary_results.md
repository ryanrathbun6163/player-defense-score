# Completion primary result: baseline retained; permitted screen failed

Recorded October 25, 2026, America/Phoenix.

[Open the consolidated scorecard, GPU trace and all five review videos](../data/outputs/ball_tracking/completion_campaign_v0_1/primary_result_review_v0_1/index.html).
The [compact committed result](../configs/ball_tracking/reviews/ball_completion_primary_result_v0_1.json)
binds the actual training, comparison, monitoring and validation evidence.

The approved primary fit completed **five epochs and 7,760 scheduled updates**.
Every trained checkpoint failed the frozen per-cohort selection rule, so the
retained epoch-zero model remains selected. Its complete permitted-reference
comparison fails the ball-quality criteria in all three curated possessions.
Certain-hidden emissions in P001 and P002 independently block the conditional
higher-resolution fit under the approved plan. No second fit, threshold change,
protected evaluation or ball-phase acceptance followed.

## Training and selection

Ryan explicitly lifted the diagnostic pause and requested GPU monitoring.
Attempt `b898cdd299724f1b97a492cc77648462` resumed the same frozen recipe from
update 500, replaying the 22 previously completed but unsaved updates. It finished
in **1,060.663 seconds**; the external supervisor ran **1,065.360 seconds**.
Both original failed attempts, update-zero and update-500 states, all validation
reports and the final update-7,760 state remain preserved. No frozen fitting
dependency or recipe changed.

The [actual completion record](../data/outputs/ball_tracking/completion_campaign_v0_1/primary_fit_v0_1/completed.json)
passed the real `bind_selected_result` consumer and an additive completion audit.
Stopping after five epochs without an eligible rank improvement was the frozen
rule, not a resource abort. The selected checkpoint remains
`09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`.
The final trained checkpoint, preserved but not adopted, is
`de3e4c1c3b57b3b7ae21401231db7bd54a66781dda06d38bc1b3e3c63707439c`.

| Epoch | P001 correct / 50 | P002 correct / 50 | P003 correct / 45 | NBA correct / 882 | NBA wrong | NBA certain-hidden emissions | Eligible |
|---|---:|---:|---:|---:|---:|---:|---|
| 0, retained | 41 | 49 | 40 | 845 | 29 | 25 | Yes |
| 1 | 44 | 49 | 38 | 837 | 34 | 19 | No |
| 2 | 39 | 49 | 38 | 850 | 9 | 16 | No |
| 3 | 37 | 49 | 38 | 842 | 4 | 15 | No |
| 4 | 39 | 49 | 38 | 850 | 8 | 11 | No |
| 5 | 42 | 50 | 38 | 848 | 9 | 17 | No |

Epoch 5 improves P001, P002 and NBA validation counts, but loses two P003 matches.
The agreed rule protects each possession separately; an aggregate gain cannot
erase that loss. These are fixed checkpoint-selection results. No rejected
epoch was evaluated on the complete post-selection census.

## Complete permitted-reference result

The [fixed evaluation](../data/outputs/ball_tracking/completion_campaign_v0_1/selected_comparison_v0_1/evaluation.json)
uses the selected retained model's **3,975 existing outputs** across eight exact
contexts. All outputs are unchanged; there were **zero new model calls**.
The strict `>0.3` heatmap policy and inclusive ten-source-pixel match radius stay
unchanged.
All 16 named cohorts reproduce their original counts, including both 60/60 NBA
pilot controls. The three SAC training-exposed cohorts remain descriptive.
Unchanged regression results do not establish improved tracking.

| Possession | Permitted frames | Eligible | Correct | Wrong | Missing | Certain-hidden emissions | Worst known eligible gap |
|---|---:|---:|---:|---:|---:|---:|---:|
| P001 | 424 | 355 | 300 (84.51%) | 12 (3.38%) | 43 | 5 | 480 ms |
| P002 | 424 | 360 | 291 (80.83%) | 8 (2.22%) | 61 | 4 | 400 ms |
| P003 | 425 | 402 | 333 (82.84%) | 8 (1.99%) | 61 | 0 | 640 ms |

Every possession fails the 95% correct, at-most-1% wrong and maximum-200-ms
eligible-missing-run requirements. P001/P002 also fail the zero-certain-hidden
emission requirement. Their recovery judgments remain inconclusive; P003's
three scored recovery events pass. Wrong-object judgments remain inconclusive:
geometric distance does not establish object identity. Unknown and censored
intervals are retained in the full report.

The exact integer deficits are **38 / 51 / 49 additional correct matches** and
**9 / 5 / 4 fewer wrong outputs**, respectively. These deficits alone do not
authorize a resolution fit. The independent hidden-emission failures occur at
P001 **185, 424–427** and P002 **340–342, 438**. The approved contract explicitly
excludes the resolution fallback when certain-hidden emissions independently
block acceptance. That necessary condition fails, so no small-ball error
classification or additional fit is needed to decide this branch.

The 225 protected positions remain metadata-only. These are permitted-segment
development results, including disclosed training/selection exposure, not a
full-clip pass or an unseen-game benchmark. All accepted references, original
reviews and earlier bounded-gap results remain unchanged.

## Monitoring and validation

The [monitoring summary](../data/outputs/ball_tracking/completion_campaign_v0_1/primary_fit_v0_1/monitoring/20261025T221007Z/summary.json)
contains **518 samples**, temperature **44–60 C**, peak reported power
**133.27 W**, and peak total-device memory **4,253 MiB**. No sampled thermal or
power-brake flag, telemetry error, device loss or matching queried Windows
graphics/crash/WHEA event appeared. The Python descendant exited normally;
neither supervisor forced a stop. The temporary chat follow-up was removed.
NVIDIA Overlay, Lively and MSI True Color remain stopped. No driver, BIOS,
clock, fan or startup setting was changed.

This is one completed monitored workload, not proof of a stability cure or
causation. Two-second sampling cannot capture every transient.

![Recorded GPU temperature and power](../data/outputs/ball_tracking/completion_campaign_v0_1/primary_fit_v0_1/monitoring/20261025T221007Z/gpu_telemetry.png)

The additive evaluator passed **12 focused CPU tests**; the separate NBA renderer
passed **7**. Tests exercise actual annotation, observation, validation and
completion producers, JSON transport, interrupted-output recovery, baseline
reuse, protected withholding and exact native video timing. The original 28
helper checks were not repeated. The NBA renderer's first six-test fixture run
had seven errors because synthetic source metadata omitted its SHA; that log is
preserved, and the corrected final seven-test run passes. The final evaluator
test output is retained in the agent execution record, not a separate local log.

The [independent actual-result audit](../data/outputs/t/completion_actual_result_audit_20261025_01/audit.json)
passes with zero discrepancies. It re-derives all six validation reports and
checkpoint selection, all cohort and curated counts, integer deficits and
original-output equality, and verifies 118 reference/acceptance bindings.
It does not load models, rerun the scientific scorer or read protected content.
The real trained-checkpoint inference branch remains unexercised in this run;
its implementation checks use synthetic CPU inputs because epoch zero won.

## Review delivery and next boundary

The [three curated comparisons](../data/outputs/ball_tracking/completion_campaign_v0_1/selected_comparison_v0_1/attempts/42d80059dbfd44cd845fcf31b9bf6db0/review/index.html)
contain all **1,498 timeline slots**, with **225 black protected panels**.
Every encoded frame is compared against its source/overlay canvas and the actual
final frames are saved. Root inspected all three encoded finals. Player context
is display-only; missing points are not filled.

The [two NBA comparisons](../data/outputs/ball_tracking/completion_campaign_v0_1/selected_nba_comparison_review_v0_1/attempts/6429fb38c01d43649062cc143fb2b452/index.html)
also completed on their first actual rendering attempt, in **330.250 seconds**.
All **2,702 frames** pass source/overlay, native packet, decoded-frame PTS and
display-interval checks, including the actual final durations. Root inspected
both encoded finals (SAC 2010 and DET 11898). Unlabeled context is explicit and
does not enter accuracy denominators. All five videos preserve original timing;
no complete human playback or new acceptance is asserted by these checks.

These comparisons show unchanged retained predictions alongside the newly
complete accepted reference census. They do not revoke earlier reviews or
require relabeling accepted references. No new trajectory acceptance or phase
pass is claimed. The primary route is rejected for adoption and the conditional
route is blocked; further fitting or a different scientific approach requires a
new scope decision. Protected evaluation stays closed.
