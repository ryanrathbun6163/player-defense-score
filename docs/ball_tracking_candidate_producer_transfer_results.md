# Producer-transfer experiment results v0.1

October 29, 2026. **Execution completed; the prespecified scientific criterion failed. No model adopted.**

Adding the 461 audited alternate-producer examples did not improve the quality
component while preserving its existing successes. On the fixed NBA quality-top
policy, Q+ retained 60 fewer correct points, accepted nine fewer wrong points and
emitted one fewer point on a certainly hidden frame. Correct retention declined
in every held NBA game. HOU gained correct points but also gained errors, and
exact-success protections failed. The saved Q and J results remain unchanged.

This completes Ryan's instruction to implement and run the
[reviewed experiment](ball_tracking_candidate_producer_transfer_protocol.md).
The [design proposal](../configs/ball_tracking/proposals/candidate_producer_transfer_v0_1.json)
remains the original design-only record. The later execution direction and the
[result ledger](../configs/ball_tracking/reviews/candidate_producer_transfer_result_v0_1.json)
record the implementation, run and outcome separately.

## What ran

One treatment, Q+, used all 18,813 original NBA candidate records plus the exact
461 eligible additions: 304 distant negatives, 81 certain-hidden negatives and
76 weak positives. Unknown targets stayed excluded from fitting. All original
3,433 positive candidates, including 610 weak positives, remained available and
were visited by their eligible fits. No new labels, scenes or detector outputs
were introduced. The million-point alternate pool was not used for fitting.

Four fresh fits retained the original pinned DINOv2 crop/point representation,
initialization, trainable parameters, weighted objective function and optimizer.
Three fits held out one NBA game each; the all-NBA fit scored the original
external registries. Six frozen sampled cycles matched the old training budget.
The population intervention changes numeric weights and per-example exposure;
it is not a comparison with every old gradient contribution held constant.
Added examples received 8.46924% of the all-NBA weighted objective.

The implementation reused both old crop caches unchanged. CPU preparation
decoded 385 PNGs to create 452 new crops; nine additions reused old pixels with
distinct fractional point inputs. All 452 new crops matched the original pixel
preprocessor exactly, and all 461 added inputs passed transport checks. Eleven
missing-image slots stayed missing. The original external query order was one
combined physical scoring stream, with cohorts reported separately.

| Completed work | Count |
|---|---:|
| New quality fits | 4 |
| Training updates / presentations | 9,870 / 315,432 |
| Scoring forwards / presentations | 1,014 / 32,341 |
| Producer-parity forwards / presentations | 4 / 128 |
| Total neural forwards / presentations | 10,888 / 347,901 |
| Old control refits / detector calls / J fits | 0 / 0 / 0 |

The only new saved-Q inference was scoring the 461 additions with their three
saved source-held controls. Original Q scores were reused. Treatment checkpoints
were saved before control restoration; all restored control tensor fingerprints
matched their accepted records. All four fresh initializations matched the
original initial fingerprints. Frozen tensors stayed unchanged, and the trained
backbone/head groups changed as required. Only cycle-six endpoints were evaluated.

The worker completed in 1,170.922 seconds; the full supervised launch consumed
1,181.296 seconds, about 19.7 minutes. Peak GPU temperature was 63°C across 571
telemetry samples. Debug Mode was freshly observed ON. No fault, forced stop,
retry, setting change or surviving owned process occurred. The independent
postrun Windows check found zero qualifying faults.

## Fixed-policy outcomes

Both policies retain their original chosen point, accepting it only when the
new score is strictly greater than zero. Quality-top means the **original Q-top
choice**, not a newly ranked Q+ point. There is no fallback after rejection.
The numbers below are counts, not precision percentages. NBA comparisons retain
all 3,179 context frames; HOU retains 960. Hidden and uncertain frames keep their
original roles, and the localization goal's eligible-frame denominator is not
replaced by these complete context totals.

| Context / fixed policy | Correct Q → Q+ | Wrong Q → Q+ | Hidden Q → Q+ |
|---|---:|---:|---:|
| NBA native | 2,309 → 2,238 | 0 → 0 | 0 → 0 |
| NBA quality-top | 2,275 → 2,215 | 99 → 90 | 28 → 27 |
| HOU native | 798 → 808 | 0 → 0 | 0 → 0 |
| HOU quality-top | 825 → 836 | 6 → 8 | 3 → 4 |

The NBA native policy gained 25 previously rejected correct points but lost 96
previously accepted correct points, for a net loss of 71. NBA quality-top gained
26 correct points but lost 86, for a net loss of 60. It rejected 15 previously
accepted wrong points but newly accepted six, yielding the net nine-error decrease.
A pooled total cannot conceal those exact-identity losses.

| Held NBA game | Native correct Q → Q+ | Quality-top correct Q → Q+ | Quality-top wrong Q → Q+ | Quality-top hidden Q → Q+ |
|---|---:|---:|---:|---:|
| CHI | 637 → 630 | 636 → 631 | 17 → 21 | 2 → 2 |
| DEN | 808 → 800 | 811 → 803 | 0 → 2 | 0 → 0 |
| SAC | 864 → 808 | 828 → 781 | 82 → 67 | 26 → 25 |

SAC supplies the pooled error reduction and most of the lost correct points;
CHI and DEN gain wrong quality-top acceptances. HOU native gains 14 correct
points and loses four; quality-top gains 14 and loses three. Its positive net
retention does not satisfy exact-success preservation, and quality-top also
adds two wrong points and one hidden emission.

## Exact protections and retained cases

| Frozen protection set | Protected rows | Newly rejected rows |
|---|---:|---:|
| Correct fixed-policy identities, NBA and HOU | 6,207 | 189 |
| Correct Q-positive weak candidate identities | 547 | 20 |
| Correct Q-positive HOU stress queries | 745 | 4 |

These are overlapping views and must not be added together as distinct lost
detections. The 189 policy rows comprise 182 NBA and seven HOU rows; native and
quality-top can describe the same point. Weak losses comprise eight CHI, three
DEN, eight SAC and one HOU-main point. No weak HOU-stress point in that protected
subset was lost; four other protected correct stress probes were lost.

All 21 named HOU recovery query identities and all six below-.01 query identities
retain their original Q acceptance signs: 13/21 and 2/6 remain positive, with zero
gains or losses within those exact query sets. This does **not** mean Q accepted
all 21 or all six. Their broader frame views still contain adverse changes;
the six-case e05 frame view gains one wrong candidate. All 15 named case groups,
6,720 source choices, 6,720 contrast views and 60 historical queries remain in
the saved analysis, including prior failures and unknown/missing states.

## Transfer and ranking diagnostics

The 461 additions were scored by models that excluded their source game. They
are error-selected challenges from existing scenes, not deployment-prevalence
or new-scene evaluation.

| Added challenge category | Rows | Accepted by Q | Accepted by Q+ |
|---|---:|---:|---:|
| Correct weak points | 76 | 44 | 45 |
| Distant wrong points | 304 | 35 | 35 |
| Certainly hidden points | 81 | 38 | 38 |

The positive total hides four gains and three losses. Distant negatives have
one newly rejected and one newly accepted point; every hidden point retains its
old acceptance sign. The treatment therefore shows no net reduction of accepted
negative examples in this source-held challenge set.

Full old-pool ranking is diagnostic only. Frames with a matching point strictly
above every nonmatching point change from 2,542 to 2,534 on NBA and 862 to 855 on
HOU; NFHS improves from 115 to 118. This is additional adverse evidence on NBA
and HOU, rather than support for a broad ranking improvement. It does not prove
every threshold or subgroup worsened. Complete strict unique-score curves, ties,
endpoints and missingness were retained; no cutoff was selected to rescue failure.
Descriptive review of those curves finds crossing tradeoffs for quality-top:
some retention levels improve and others worsen. Native-policy curves also
include improved or equal regions. Consequently, the fixed-zero failure is not
evidence that every aspect of score separation worsened; score calibration and
discrimination must remain distinct. This outcome-informed reading selects no
operating threshold and changes none of the acceptance or preservation criteria.

NFHS remains a secondary diagnostic: native correct retention changes 59 → 63
with no wrong/hidden emissions; fixed quality-top changes 66 → 65 correct and
0 → 1 wrong, with no hidden emission. Historical queries remain separate semantic
diagnostics. No new protected footage was opened.

## Conclusion, scope and continuity

The fixed-zero component criterion fails both correct-retention and exact-success
conditions, as well as source-specific error and HOU conditions. Removing only
the newly declared strict weak-point veto would not make this result pass.
No Q+ model is adopted, no Q+ score is substituted into frozen J, and no automatic
threshold, weight, seed, pool-size or training-length revision follows.

This result rejects this specific population addition under the existing recipe.
It does not show that all hard-negative training, all alternate-producer data or
all image representations are ineffective. It is one seed, finite correlated
scenes and one weighting/sampling intervention. The dense older proposal pool
can produce chance geometric matches, most alternate recovery frames were already
correct for the current native detector, and no fresh-scene failure coverage was
added. The source-held quality model is not an entirely unseen-game pipeline.

The prior CPU failure study, acceptance results and failed origin ablation remain
part of the evidence. This test supplies a different input population, not a
repeat of those studies. The historical/research reconciliation in the design
was reused; this execution turn does not claim a fresh every-session or
every-paper reread. A subsequent direction needs a specific information gain and
comparison against the open fresh-footage and representation alternatives before
another fit. The saved results, full curves and exact losses support that decision;
an unplanned small tweak is not justified by this result alone.

The earlier reported J quality-top result remains 2,541/2,811 eligible NBA frames
(90.39%), with its existing 34 wrong acceptances and eight hidden emissions.
It was not improved or rerun here, and it is not a deployed or fully accepted
tracker. The 95%/1%/zero-hidden, temporal, recovery and human-review requirements
remain unchanged. This experiment adds evidence, not a new gain toward 95%.

## Verification and saved evidence

All 45 focused checks passed. Baseline-identity transport reproduced the old
registries and original Q counts; an identical treatment correctly had no strict
gain. Independent review checked input routes, original-pixel equivalence,
sampling, source exclusion, control serialization and supervised execution.

The neural-output audit passed 271,004 checks, including all 21,776 ordered
journal events, exact exposures, scoring order and CPU-only final tensor
fingerprints. Two audit-tool corrections were required: recovery ledger entries
also carry timestamps, and established tensor digests sort parameter names.
Both failed audit receipts and earlier helper versions are preserved. They
changed neither scientific artifacts nor neural execution; the final audit passed.

The independent analysis audit passed 7,072,931 checks across all 26 bound
artifacts and 360,087 curve points, including all 31,430 candidate slots, 8,578
fixed-policy rows, 461 paired challenge points and every protection/decision.
All original 147 file contents are preserved through unchanged files or exact
reversible history additions. Branch, HEAD and empty index remain unchanged.

Evidence root: `data/outputs/ball_tracking/candidate_producer_transfer_v0_1/`.
Key records are `launch_v0_1/execution_freeze.json`, `attempt_001/completed.json`,
`analysis/summary.json`, `analysis/decision.json`, `review/neural_output_audit.json`,
`review/analysis_audit.json` and `documentation_update/receipt.json`.
