# Candidate acceptance origin ablation v0.1

October 29, 2026. This protocol is fixed before new fits or outcomes. Ryan's
"Ok chat move forward" authorizes the specific recommended CPU comparison:
remove the two explicit origin indicators from the acceptance gate, preserving
the saved detector scores, candidate choices and all other fitting settings.
Implementation, focused checks, independent review, execution and reporting are
in scope. Weighting, missing-schema repair, candidate routing, new image models,
new labels, protected data, threshold selection and adoption are later questions.

## Question and inherited evidence

Does the current gate's useful separation and its false-acceptance behavior
depend on the explicit native/weak origin indicators? Compare a newly fitted
14-feature arm A with the completed 16-feature J, using the same rows, source
nesting, targets, weights, normalization procedure and optimization recipe.
This is a refitted feature ablation; it does not identify a causal shortcut or
remove every origin-correlated proxy. Response and pool metadata remain.

The accepted [gate results](ball_tracking_candidate_acceptance_gate_results.md)
show quality-top NBA gains at zero: 2,275 -> 2,541 correct, 99 -> 34 wrong,
28 -> 8 hidden frames. Native J retains 2,806/2,811 correct but emits three wrong
and two hidden points; HOU native has 841 correct, 18 wrong and 18 hidden.
Protected HOU choices and stress probes also regress. The earlier
[CPU failure study](ball_tracking_saved_score_failure_study_results.md) found
only two native-hidden fitting candidates in one game and no such candidates
in leave-CHI-out. Reweighting cannot create missing support; no weighting change
is bundled into this experiment.

The completed Session1-19/history reconciliation, accepted original labels,
NBA/cosine-nine roles, protected closure and pending human trajectory review
carry forward. This is not a new exhaustive historical or literature reread.
Previously consulted selective-prediction research motivates explicit
abstention; it does not establish that this ablation will help. No external
method, package or current recommendation is added to the implementation.

## Frozen inputs and one change

Reuse accepted gate attempt001 analysis files under
data/outputs/ball_tracking/candidate_acceptance_gate_v0_1/attempt_001/analysis/.
Bind its completion manifest, independent output audit, all consumed data,
the original four J models, the original protocol/specification, source modules
and the final 125-file preservation receipt before execution. Existing files
are read-only. The new baseline125 receipt verifies all prior current bindings.

Original Q/S/J/M predictions and tables/curves are reused controls, never refit.
The feature registries and original fit-membership rows are also reused:

| Saved population | Rows |
|---|---:|
| New single-game cross-score feature rows | 37,626 |
| Original out-of-fold final-fit feature rows | 18,813 |
| Complete gate membership, including excluded unknowns | 56,439 |
| Evaluation slots per arm | 31,430 |
| Observed / missing evaluation scores | 31,419 / 11 |
| Evaluation context frames / fixed-policy rows | 4,289 / 8,578 |
| Original source choices / contrast rows / historical rows | 6,720 / 6,720 / 60 |

Arm A removes exactly native_indicator and origin_unavailable (old positions
4 and 5, zero based). Its ordered features are:

1. quality_logit
2. log1p_response_mass
3. log1p_component_pixels
4. padding_fraction
5. response_missing
6. component_missing
7. padding_missing
8. quality_minus_far_max
9. quality_minus_near_max
10. log1p_near_count
11. log1p_far_count
12. far_max_missing
13. near_max_missing
14. pool_unavailable

All original16 fields are retained and validated in the saved inputs; only the
14 declared columns enter A's numerical matrix. Origin metadata remains in
reporting strata. No coordinate, label, reference distance, case tag, source ID
or outcome becomes an input. The existing geometric usefulness target remains;
this is not semantic crop-presence classification.

## Four CPU fits, same recipe

| Gate | Known fitting rows | Base-score sources |
|---|---:|---|
| outer_CHI | 11,954 | DEN from SAC_only; SAC from DEN_only |
| outer_DEN | 11,912 | CHI from SAC_only; SAC from CHI_only |
| outer_SAC | 11,182 | CHI from DEN_only; DEN from CHI_only |
| final_all_NBA | 17,524 | Existing leave-game-out scores for CHI/DEN/SAC |

Each outer evaluation uses the original scorer fitted without that game; final
evaluation uses original all-NBA scores on HOU/NFHS/history. Reuse exact original
J training_row_keys order, targets and objective weights. Unknown targets stay
outside fitting and inside all applicable registries/pools/evaluation views.
Validate membership and base-source exclusions rather than accepting row counts
alone. No held game enters its gate's fitting rows or their base scorer.

Fit the weighted logistic objective in float64:
sum(weight * BCEWithLogits) + 0.01/2 * sum(beta squared). The intercept is
unpenalized. Weights retain the original .5 positive/.25 distant-miss/.25 hidden
hierarchy; no resampling or reweighting. Weighted fitting-only observed means
and standard deviations, mean imputation, unscaled binary indicators and
degenerate-feature conventions remain identical. The14 retained scaler columns
must exactly match the corresponding completed J scaler columns.

NumPy2.4.6/SciPy1.17.1; L-BFGS-B with analytic gradient, zero initialization,
maxiter10000, ftol1e-12, gtol1e-9. A is unconstrained like J. Require finite
parameters/objective/gradient/predictions and solver success; preserve failures,
do not change the solver after seeing results. Four fits only, no alternative
regularization, radius, feature combinations or cutoff sweep. Full threshold
curves are descriptive outputs, not a hyperparameter search.

No image loading, feature extraction, neural inference/training, Torch import,
GPU query, system setting change or Windows UI action is needed. Debug Mode ON
remains the standing instruction without a new hardware-readiness inspection.

## Fixed policies and complete outputs

Reuse the original native and quality-top chosen-row identities, ties, empty
pools and missing-choice states. Add A's score to each existing choice; rejection
means abstention. No alternate surviving point is substituted, no argmax(A),
no routing and no trajectory change. Missing-image A remains null.

Publish A's full candidate and fixed-policy scores, zero-reference tables with
the original context/game/block/metadata families, and every unique-score curve
breakpoint plus accept-all/reject-all endpoints. Equal scores move together;
acceptance is strictly score>0 at the fixed reference. Preserve candidate versus
distinct-frame units, unknown/reference states, missingness and denominators.
Original Q/S/J/M records remain bound comparisons rather than new model results.

Publish exact A-versus-Q/S/J/M paired accept/reject changes by original row ID,
including gained/lost correct choices, wrong choices and certain-hidden frames.
Extend all6,720 saved source choices and6,720 contrasts with A scores, nulls,
acceptance and observed-side differences. Historical roles remain semantic
diagnostics only; all60 rows survive. All previous recovery, adverse, hidden,
incomplete-peak and e01/e05 groups stay present, not just the desired cases.

## Predeclared interpretation

Freeze protection lists using original Q/J scores and accepted labels before
fitting A. Protection lists are evaluation checks, never features or fitting
weights. Candidate alternatives not selected by a fixed policy remain complete
diagnostics rather than extra undeclared vetoes.

Two judgments remain separate:

1. **Nonregression relative to J at zero.** For every NBA game and both fixed
   policies, A must retain at least J's correct count, accept no more wrong
   eligible points and emit in no more certainly hidden frames. Require at
   least one strict NBA improvement. Also require no individual J0-kept correct
   NBA point lost. In HOU, require correct>=J, wrong<=J and hidden<=J separately
   per policy. Protect the union of Q0- and J0-kept known-correct fixed-policy
   points and exact stress queries in all previously named HOU views. No new
   loss of those frozen identities is allowed. This stronger comparative rule
   protects J's gains as well as the original recovery successes.
2. **Original component criterion applied to A.** Evaluate the exact prior
   Q0/S0 NBA per-game/both-policy comparisons, at least one strict improvement,
   original Q0-kept HOU named policy/stress protection and HOU per-policy
   hidden<=Q/S checks, substituting A solely as the candidate head. Preserve
   original J and its failed decision record; no original criterion is loosened.

If A fails either judgment, report the losses and tradeoffs. Complete curves
can show better or worse separation at fixed retention floors, but no curve
cutoff or arm is selected. A change in fixed-zero counts without improved
curves is not described as new information. Removing origin may improve one
policy/source and harm another; pooled gains cannot erase that result.

Any improvement is conditional evidence about explicit features under this
fixed refitting recipe, not proof that origin was a spurious cause. A decline
does not prove origin is universally reliable. Remaining correlated cues,
limited native-negative support and out-of-schema probes constrain inference.
Do not choose a weighting/schema/image repair from HOU case outcomes.

The repeatedly inspected games and HOU are exposed development evidence.
Nested source exclusions remain useful but do not restore pristine test status.
No 95% generalization claim, threshold/model/selector adoption, or full-tracker
acceptance follows. Existing >=95%-correct, <=1%-wrong, zero-hidden, temporal,
recovery and human gates remain. Quality-top's2,542/2,811 ceiling is unchanged;
native's larger eligible ceiling does not remove false/hidden-source failures.

## Execution and preservation

New study root: data/outputs/ball_tracking/candidate_acceptance_origin_ablation_v0_1/.
Before fits, bind this protocol, machine specification, inputs, implementation,
focused test receipt, independent review, frozen protection IDs and exact user
direction in a new execution freeze. Output attempt001 is exclusive; preserve
partial/failed runs and never silently overwrite or repeat a completed fit.
Independent audit recomputes matrix projection, scaler/objective/gradients,
predictions, fixed choices, paired comparisons, full tables/curves/protections,
and verifies no old content was changed. It performs no optimizer fit.

Write a result report and machine ledger, then add reversible latest-status
insertions to the maintained project documents. Preserve all125 prior worktree
contents and the complete previous handoff chain; branch/HEAD/index stay fixed.
This authorizes this one comparison only. Later weighting, schema handling,
calibration, ranking or model experiments require their own concrete design.
