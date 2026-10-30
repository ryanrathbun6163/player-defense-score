# Candidate acceptance origin ablation v0.1 — 2026-10-29

Removing the two candidate-origin indicators did not improve the gate overall.
The ablation recovered several HOU weak-recovery successes, but lost correct
NBA detections and admitted more NBA quality-top errors. The original joint
gate remains the stronger research baseline; neither version passes the
preservation and hidden-emission requirements. No model or cutoff is adopted.

This was a narrow, useful negative result: it tests the explicit origin fields,
not every possible origin-related shortcut. Response mass, component size,
padding, quality, spatial competition and their missingness indicators remain.
The model was refitted, so the changes are not a causal attribution to individual
coefficients or evidence that the remaining features are origin-independent.

The completed first attempt is
`data/outputs/ball_tracking/candidate_acceptance_origin_ablation_v0_1/attempt_001/`.
Four CPU fits converged in 19.735 seconds. No new neural inference, image
training, GPU query, candidate extraction, or old experiment rerun occurred.
The implementation passed 25 focused tests and 192 preexecution review checks.
The independent output audit passed 3,072,793 checks. The separate model audit
passed 2,773,690 checks in 4.72 seconds and verified the retained projection,
target/weight arrays, fitting-only scaler,
objectives and all 31,419 observed predictions; maximum prediction discrepancy
was zero, and all 11 missing slots remained missing.

**The comparison changed exactly two inputs.** A removes `native_indicator`
and `origin_unavailable` from the accepted 16-feature J model, leaving 14
features in the original order. The same three outer folds and final all-NBA
fit use the same candidate memberships, row order, targets, objective weights,
continuous-feature scaling, ridge penalty and L-BFGS-B settings. The 37,626
nested cross-score feature rows and 18,813 final-training feature rows were
reused. There were 52,572 known-target fitting-row presentations across the
four CPU fits; excluded unknowns remain in the saved inventories and neighbor
pools.

Q, S, J and M remain the original saved controls. A is added to their records.
Both original native and quality-top choices remain fixed: a rejection means
abstention, with no fallback, reranking or trajectory change. The full original
control tables and curves remain bound and available. The prior
[joint-gate report](ball_tracking_candidate_acceptance_gate_results.md) supplies
their interpretation and the earlier
[CPU failure study](ball_tracking_saved_score_failure_study_results.md) supplies
the source-shift/support evidence. This run does not replace either study.

**Fixed zero by source.** Every cell is
`correct kept / wrong eligible kept / certain-hidden emission frames`.
Acceptance is strictly score >0. Correct/wrong counts use the original eligible
frames; hidden counts use distinct certain-hidden frames. Missing choices and
unknown-reference frames remain in the all-frame inventories and saved tables.

| NBA source | All / eligible / hidden frames | Policy | Q0 | S0 | J0 | A0 |
|---|---|---|---|---|---|---|
| CHI | 960 / 836 / 50 | Native | 637 / 0 / 0 | 656 / 0 / 0 | 831 / 3 / 2 | 830 / 3 / 2 |
| CHI | 960 / 836 / 50 | Quality-top | 636 / 17 / 2 | 653 / 27 / 2 | 729 / 9 / 1 | 729 / 10 / 1 |
| DEN | 960 / 920 / 10 | Native | 808 / 0 / 0 | 855 / 0 / 0 | 920 / 0 / 0 | 920 / 0 / 0 |
| DEN | 960 / 920 / 10 | Quality-top | 811 / 0 / 0 | 856 / 2 / 0 | 899 / 0 / 0 | 899 / 0 / 0 |
| SAC | 1,259 / 1,055 / 68 | Native | 864 / 0 / 0 | 892 / 0 / 0 | 1,055 / 0 / 0 | 1,048 / 0 / 0 |
| SAC | 1,259 / 1,055 / 68 | Quality-top | 828 / 82 / 26 | 843 / 96 / 28 | 913 / 25 / 7 | 911 / 38 / 8 |

No NBA game/policy improves a primary fixed-zero count against J. CHI native
loses one correct point; CHI quality-top rejects two J-kept wrong choices but
accepts three new wrong choices, for a net increase of one. SAC native loses
seven correct points. SAC quality-top loses two correct points, accepts 13 new
wrong choices without rejecting any J-kept wrong choice, and emits one new
hidden frame. DEN's primary outcomes are unchanged. Unknown-role decisions
can differ even when these primary counts agree; those rows are not discarded
or counted as known errors.

After those source results, the pooled NBA totals are:

| Policy, 3,179 total / 2,811 eligible / 128 hidden frames | Q0 | S0 | J0 | A0 |
|---|---|---|---|---|
| Native | 2,309 / 0 / 0 | 2,403 / 0 / 0 | 2,806 / 3 / 2 | 2,798 / 3 / 2 |
| Quality-top | 2,275 / 99 / 28 | 2,352 / 125 / 30 | 2,541 / 34 / 8 | 2,539 / 48 / 9 |

Relative to J, A has no newly accepted correct NBA policy point. It loses ten
protected policy outcomes on eight distinct frames: eight native losses and
two quality-top losses that overlap native losses on the same SAC frames.
The native losses are CHI e05 source frame 391; SAC e01 frames 5145–5148 and
5161; SAC e02 frame 73671; and SAC e06 frame 197812. The latter two also lose
quality-top acceptance. All ten had negative Q scores, so these regressions
erase improvements gained by J rather than Q-kept successes. Overall NBA
quality-top wrong changes are two new rejections versus 16 new acceptances;
hidden changes are zero new rejections versus one new acceptance.

**HOU has real gains and losses.** Its original inventory is 960 frames:
882 eligible, 34 certain-hidden and 44 other unknown/nonlocalizable frames.

| HOU policy | Q0 | S0 | J0 | A0 |
|---|---|---|---|---|
| Native | 798 / 0 / 0 | 807 / 0 / 0 | 841 / 18 / 18 | 840 / 17 / 16 |
| Quality-top | 825 / 6 / 3 | 834 / 7 / 4 | 855 / 4 / 14 | 858 / 5 / 16 |

A rejects one J-kept correct native point, one wrong native point and two
hidden native points. The correct loss is e05 frame 212. Quality-top preserves
all 855 J-kept correct points and restores e01 frames 198, 199 and 200. It also
accepts one new wrong choice and three new hidden choices while rejecting one
J-kept hidden choice, producing the net changes above. Lower native hidden
emission does not offset the quality-top increase or the correct native loss.

The ten e01 recoveries now retain nine quality-top points, up from J's six,
while Q and S retain all ten. Exact e01 stress probes retain eight, up from
six, while Q and S retain all ten. The recovered stress probes are frames 196
and 200; they are not the same coordinate identities as the three recovered
quality-top choices. A still rejects quality-top e01 frame 201 and exact stress
frames 197 and 198.

The protection lists were frozen from original Q/J outcomes before A fitting.
They have different purposes and must not be merged into one denominator:

| Protected identities | Frozen count | A retained | A lost |
|---|---:|---:|---:|
| NBA J-kept correct fixed-policy outcomes | 5,347 | 5,337 | 10 |
| HOU named correct policy outcomes kept by Q or J | 1,701 | 1,698 | 3 |
| HOU named exact correct stress probes kept by Q or J | 772 | 766 | 6 |

HOU's three policy losses are native e05/212, quality-top e01/201 and
quality-top e05/21. Its six protected stress losses are e01/197–198 and
e05/14, /15, /21 and /220. The e05/220 stress loss is new relative to J;
the other five were already J losses relative to Q. Across all known-correct
stress probes, A adds three and loses one relative to J; those gains and losses
remain alongside the protected-set accounting. The e05/14–19 six-frame group
still keeps neither of the two Q-positive correct probes at /14 and /15.
The useful e05/206 quality-top choice remains accepted. All 17 incomplete-peak
control frames retain their correct native, quality-top and exact stress points.
All other named adverse/rank/hidden views remain saved; the overlapping named
groups are not additive.

**The two declared criteria both fail, for separate reasons.**

1. A nonregression versus J fails: there is no strict NBA improvement in any
   primary fixed-zero count; several game/policy counts regress; and protected
   correct identities are lost. HOU's native and quality-top tradeoffs also fail
   the per-policy comparison. Better recovery on three selected HOU frames does
   not establish this criterion.
2. The original acceptance-component criterion evaluated with A against Q/S
   also fails. CHI native still accepts three wrong and two hidden points where
   Q/S accept none. HOU hidden emissions are 16 for each policy, exceeding Q/S's
   0/0 native and 3/4 quality-top. This original Q-based protection independently
   finds two HOU quality-top losses and five exact stress losses. Its smaller
   loss lists differ from the expanded Q-or-J lists above by construction.

Neither criterion selects a threshold or adopts an arm. A still improves many
counts over Q, but that does not make it a nonregressing replacement for J.

**Complete curves do not rescue the ablation.** The interpretation compares
every shared integer correct-retention floor using the complete saved
tied-score curves. For each floor, the first reachable outcome retaining at
least that many correct points minimizes both wrong and hidden counts along
that curve. No interpolation splits a tie. A/J “better” below means fewer of
one error type without more of the other; equal means the same error counts at
the retention floor. This is descriptive oracle potential, not an operating
point choice, additional pass rule, or independent validation.

| Source and policy | Retention floors | A better | J better | Equal | Wrong/hidden tradeoff |
|---|---:|---:|---:|---:|---:|
| CHI native | 832 | 11 | 23 | 798 | 0 |
| CHI quality-top | 730 | 5 | 502 | 223 | 0 |
| DEN native | 920 | 0 | 0 | 920 | 0 |
| DEN quality-top | 899 | 0 | 0 | 899 | 0 |
| SAC native | 1,055 | 0 | 0 | 1,055 | 0 |
| SAC quality-top | 913 | 0 | 663 | 250 | 0 |
| HOU native | 842 | 2 | 9 | 831 | 0 |
| HOU quality-top | 862 | 9 | 35 | 808 | 10 |

CHI quality-top favors J at floors 50–519 and 699–730, favors A at 644–648,
and is equal elsewhere. SAC quality-top favors J at 32–564 and 784–913 and is
equal elsewhere. DEN's curves agree on these primary tradeoffs. SAC native's
curves agree even though its fixed-zero retention differs, because there are
no known wrong/hidden original native choices in that view; a different cutoff
can recover the seven losses there, but no cutoff is chosen.

At the full quality-top correct-choice ceilings, the oracle outcomes are:

| Source | J curve: correct / wrong / hidden | A curve: correct / wrong / hidden |
|---|---|---|
| CHI | 730 / 44 / 5 | 730 / 77 / 11 |
| DEN | 899 / 0 / 0 | 899 / 0 / 0 |
| SAC | 913 / 23 / 7 | 913 / 45 / 11 |

At SAC's A0 retention floor of 911 correct points, J's curve can reach
911 / 18 / 4 while A's reaches 911 / 38 / 8. Thus the SAC difference is not
explained solely by the position of zero. For HOU quality-top, A has a few
favorable levels: at 855 correct it permits 855 / 4 / 13 versus J's
855 / 4 / 14. But at 825 correct, A requires one wrong point versus J's zero;
at 858 correct A permits 858 / 5 / 16 versus J's 858 / 5 / 15. At the full
HOU ceiling A has 862 / 12 / 26 versus J's 862 / 12 / 27. These mixed local
potentials do not justify choosing a HOU cutoff or ignoring lost identities.

**Secondary and historical controls remain complete.**

| NFHS source, all / eligible / hidden frames | Policy | J0 | A0 |
|---|---|---|---|
| Possession 001, 75 / 74 / 1 | Native | 74 / 0 / 0 | 74 / 0 / 0 |
| Possession 001, 75 / 74 / 1 | Quality-top | 68 / 0 / 0 | 68 / 0 / 0 |
| Possession 002, 50 / 31 / 18 | Native | 31 / 0 / 0 | 31 / 0 / 0 |
| Possession 002, 50 / 31 / 18 | Quality-top | 23 / 1 / 0 | 23 / 1 / 1 |
| Possession 003, 25 / 25 / 0 | Native | 25 / 0 / 0 | 25 / 0 / 0 |
| Possession 003, 25 / 25 / 0 | Quality-top | 24 / 1 / 0 | 24 / 1 / 0 |

Possession 002 adds one hidden quality-top emission without a correct gain.
All NFHS native retention-floor comparisons are equal, as are possession 001
quality-top comparisons. J has fewer errors at six of possession 002's 23
quality-top floors and three of possession 003's 24, with all remaining floors
equal. Original Q/S/M values remain unchanged and are recorded alongside A in
all candidate, policy, paired and named-case outputs.

Historical rows retain their four original roles. Positive-score counts remain
diagnostics rather than geometric accuracy:

| Historical role | Rows | Q positive | S positive | J positive | M positive | A positive |
|---|---:|---:|---:|---:|---:|---:|
| Reference bank | 10 | 6 | 6 | 6 | 6 | 6 |
| Resolved check | 10 | 4 | 4 | 4 | 4 | 4 |
| Exposed regression | 34 | 18 | 19 | 16 | 18 | 18 |
| Unresolved audit | 6 | 0 | 0 | 0 | 0 | 0 |

The two accepted historical balls at `sas_det_q1_c02:11008:mean:1` and
`sas_det_q1_c02:11107:mean:1` remain negative under A. Six unresolved cases
remain unresolved. No label, historical role, uncertainty rule or protected
source access changed. All 31,430 candidate slots, 8,578 fixed-policy rows,
6,720 source choices, 6,720 contrasts, 60 historical rows and 11 missing scores
remain. Missing values are not zero; unknown labels remain excluded from
fitting while their candidates remain in the observable pools and reporting.

**What this means for the project.** The simple hypothesis that removing
explicit origin indicators would improve preservation while keeping J's gains
is not supported by this bounded comparison. The origin fields help the
refitted recipe on some cases and hurt it on others; the remaining correlated
inputs prevent treating this as a complete origin-bias diagnosis. The result
also does not show that more general image learning or candidate context will
fail. It rules out this particular two-field removal as the next replacement.

Keep the accepted J result and all its limitations as the research baseline.
Do not automatically proceed to the broader metadata-removal arm, reweighting,
a cutoff sweep, always-native selection, or reranking with A/J. Any follow-up
needs its own bounded design, training-source basis and frozen preservation
checks; HOU remains a veto, not a source for fitting repairs. This report does
not execute or authorize another experiment.

The quality-top choice ceiling remains 2,542/2,811, or 90.43%, below the
unchanged 95% correct-position requirement. A keeps 2,539 at zero and J keeps
2,541; neither can repair an absent candidate or a wrong first choice by
rejection alone. Native's stronger eligible ceiling does not remove its wrong,
hidden, recovery or source-preservation failures. The <=1% wrong, zero-hidden,
temporal/recovery and human-trajectory gates remain unchanged. These are
repeatedly inspected development/source-held views, not a fresh independent
test or a statistical confidence guarantee.

**Evidence and bindings.** All new experiment paths below are under
`data/outputs/ball_tracking/candidate_acceptance_origin_ablation_v0_1/`.
`review/interpretation_bindings.json` binds the exact source files, read-only
interpretation helper, receipt and this report.

- `attempt_001/completed.json`, `summary.json`, `decision.json` and four
  `fits/*_A.json` records establish execution, outcomes and fitted parameters.
- `attempt_001/fixed_policy_rows.jsonl`, `candidate_scores.jsonl`, paired rows,
  zero tables, complete curves, `named_case_views.json`, source choices,
  contrasts and historical rows retain all source and paired evidence.
- `preparation/protection.json`, `execution_freeze.json` and
  `focused_tests.json` bind the prefit identities, scope and tests.
- `review/implementation_review.json`, `output_audit.json` and
  `model_audit/receipt.json` provide independent implementation, full-output
  and model/transport checks.
- `review/interpretation/interpret_saved.py` and `review/interpretation.json`
  retain independent fixed-zero counts, exact change identities, every
  retention-floor comparison range, protected-case scores and historical roles.
- Original Q/S/J/M curves, frame inventory and controls remain in
  `data/outputs/ball_tracking/candidate_acceptance_gate_v0_1/attempt_001/analysis/`;
  the prior result report and its bindings remain unchanged.
