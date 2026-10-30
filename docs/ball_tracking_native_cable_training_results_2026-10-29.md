# Candidate-quality pilot completed: useful ordering, unresolved rejection and transfer

October 29, 2026. **All four fixed fits and all declared scoring completed.**
Ryan's “ok chat move forward” authorized the prepared continuation once. Debug
Mode was observed ON immediately before launch and remained the required setting;
no driver, clock, power, RAM or other setting was changed. This is a completed
scientific pilot and saved-score diagnosis, **not an adopted model or tracker**.

The learned candidate score contains substantially more useful location evidence
than the earlier frozen point/CLS comparisons. On exposed HOU development it
ranks a matching candidate strictly first on **862/882 eligible frames**, versus
527 for point and 259 for CLS. The peak control has 837 strict-first rankings
among available features; its 17 incomplete-feature rankings require the paired
comparison below. Useful e01 recoveries and previously harmful e05 substitutions
are better distinguished. However, correct-point rejection, game transfer,
certain-hidden candidates and historical failures remain material. More unchanged
training or an automatic score veto is not supported by these results.

## Execution, stability and retained work

The exact [prepared continuation](ball_tracking_native_cable_training_continuation_2026-10-29.md)
ran from approximately **15:26:02 to 15:44:47 Phoenix**. Inclusive charged launcher
time was **1,125.984 seconds (18m46s)**; the narrower supervisor timer was
1,123.406 seconds. Both are retained rather than treated as the same clock.
The fixed workload ended normally, well inside its 90-minute operational watchdog.

All 547 saved GPU samples were readable. Sampled maxima were **63°C, 151.21 W and
3,537 MiB**. There was no detected device, thermal, power-brake or Windows graphics
fault, no STOP or forced job termination, and no cleanup error. Supervisor and
event jobs each report zero remaining owned processes. The independent postrun
Windows query inspected both new events since the launch watermarks, found no
qualifying fault, found no owned training/watcher process and reported 44.515 GiB
free memory. Both 32 GB modules still report 5200 MT/s. Debug ON was directly
observed before launch; this is not a continuous UI recording of that setting.

This longer successful exposure after the reported native-cable change is
encouraging. It does not identify a faulty cable/component, exclude unsampled
transients or certify permanent stability. The cable replacement also involved
reseating, adapter removal and a reboot. Previous 0x116/141 failures, corrupted
receipts and cleanup failures remain recorded; they have not been reclassified.

| Fit | New optimizer updates | Imported logical updates | Scored presentations |
| --- | ---: | ---: | ---: |
| Leave CHI out | 0 | 2,244 | 5,935 |
| Leave DEN out | 2,238 | 0 | 5,790 |
| Leave SAC out | 2,100 | 0 | 7,088 |
| All three NBA games | 3,288 | 0 | 31,419 |
| Total | **7,626** | **2,244** | **50,232** |

The new attempt returned all 7,626 training forwards/updates, 1,572 scoring
forwards and three fresh-fit parity forwards: 9,201 new neural forwards and
294,036 presentations, including 243,708 fitting presentations. Logical four-fit
training is 9,870 updates / 315,432 presentations. Cumulative physical history,
including failures and replay, is at least **11,710 training starts, 11,709
training returns, 11,708 optimizer updates and 374,206 fitting presentations**.
The distinctions matter: an earlier forward returned without an optimizer update,
and another never returned. None of those costs is erased.

The audited diagnostic epoch-six checkpoint supplied the unchanged first fit
through an explicit provenance bridge. An independent CPU comparison confirms
all 42 trainable tensors / 3,600,641 parameters in its new final checkpoint are
exactly equal to that diagnostic endpoint. It was not retrained. The original
epoch-four scientific checkpoint, diagnostic checkpoints and unsaved historical
suffixes remain intact. There are 18 new recovery checkpoints and four final
trainable checkpoints. No alternate epoch was scored or chosen.

The original hour's 1,574 charged seconds and old 2,026-second balance remain
historical; Ryan removed that cap. New inclusive exposure adds 1,125.984 seconds,
for 2,699.984 historical-plus-new seconds under those recorded accounting rules.
There is no automatic retry, renewed time allowance or further GPU run.

## Training learned the fitting targets; low loss is not validation

| Fit | Epoch-one weighted online loss | Epoch-six loss | Updates with preclip norm >1 |
| --- | ---: | ---: | ---: |
| Leave CHI out, inherited logical branch | 0.177355 | 0.00009234 | 600/2,244 |
| Leave DEN out | 0.224693 | 0.00114866 | 819/2,238 |
| Leave SAC out | 0.161304 | 0.00006022 | 422/2,100 |
| All NBA | 0.161547 | 0.00245281 | 962/3,288 |

All trainable backbone/head fingerprints changed and all frozen-prefix
fingerprints remained identical. Losses and gradients were finite. Maximum
preclip norms were 105.50, 119.60, 116.37 and 239.68 respectively; clipping at 1.0
was part of the original recipe, not a response to these observations. The logs
retain each epoch's positive, distant-miss and hidden loss contributions. These
are changing-model online training losses, not held-out losses or checkpoint
selection evidence. They support successful fitting, not adequate transfer.

## Complete populations and unchanged roles

All **3,329 package frames and 19,632 candidates** were scored where candidates
exist. All 21 empty frames and all 241 masked frames / 1,228 masked candidates
remain in the inventory. The all-NBA model fits 17,524 candidates: 3,433 accepted
matches, 13,776 clearly distant misses and 315 certain-hidden points. The 65 NBA
near-boundary candidates and 1,224 masked candidates remain unknown for fitting.
Across NBA and NFHS there are 70 boundary-unknown candidates. Unknowns are never
counted as negatives merely because their scores are low.

The complete HOU evaluation has **960 frames**: 882 eligible, 34 certain-hidden,
14 indeterminate, eight uncertain-hidden and 22 visible-unlocalizable. All
10,778 main candidates, 960 broad-choice stress slots and 60 historical queries
are retained: 11,798 query records, 11,787 emitted scores and 11 image-less missing
slots. All seven existing arms / 6,720 choice slots and all **6,720 directed
contrast rows** remain, including agreements, unchanged errors and missing cases.

HOU remains exposed development, excluded from fitting and threshold selection.
The original 18 DET appearance queries are fixed historical diagnostics only;
they select no method, checkpoint or cutoff. NFHS is secondary scoring evidence.
Cosine nine already saw the three NBA fitting sources and NFHS upstream, so the
held-game tests exclude a game only from the **new scorer**. This is not an
end-to-end unseen-game test. Adjacent frames, candidates and folds are correlated;
no independent-frame significance claim or pooled validation accuracy is made.

The target remains geometric usable-location quality under the original
inclusive ten-pixel rule, not object identity or a calibrated probability.
Throughout this report, “kept at zero” means the predeclared strict logit >0
reference; exact zero is a tie. It is a diagnostic, not a selected operating rule.

## Fitted games versus held-game results

“Fitted” uses the all-NBA fit on the game. “Held” uses the fixed fit excluding
that game from the new scorer. Each pair has the same evaluation population,
but the models have different fitting populations; the gap does not isolate a
single cause such as scenery, ball size, training amount or calibration.

| Game/context | Eligible | Native-correct kept / total | Weak-match frames kept / total | Hidden frames with any survivor / total | Match strictly first |
| --- | ---: | ---: | ---: | ---: | ---: |
| CHI fitted | 836 | 832/832 | 250/250 | 0/50 | 831/836 |
| CHI held | 836 | 637/832 | 106/250 | 2/50 | 730/836 |
| DEN fitted | 920 | 920/920 | 183/183 | 0/10 | 920/920 |
| DEN held | 920 | 808/920 | 155/183 | 0/10 | 899/920 |
| SAC fitted | 1,055 | 1,055/1,055 | 177/177 | 0/68 | 1,054/1,055 |
| SAC held | 1,055 | 864/1,055 | 141/177 | 26/68 | 913/1,055 |
| NBA fitted, descriptive total | 2,811 | 2,807/2,807 | 610/610 | 0/128 | 2,805/2,811 |
| NBA held, descriptive total | 2,811 | 2,309/2,807 | 402/610 | 28/128 | 2,542/2,811 |
| NFHS secondary | 130 | 59/130 | 30/64 | 0/19 | 115/130 |

Held-game zero rejection loses **498 correct native points (17.7%)** and 208
weak-match frames. CHI has the largest weak loss (144/250); SAC accounts for
26/28 held-game hidden frames with survivors. DEN has only ten hidden frames;
zero survivors there is limited support, not broad absence validation.

The fitted NBA score retains all 3,433 positive candidates, with 25/13,841
eligible-miss candidates above zero and zero certain-hidden candidates above
zero. Held-game scores retain 2,711/3,433 positive candidates and 351/13,841 misses;
38/315 hidden candidates survive across the 28 hidden frames. The three old
native-wrong eligible choices are all below zero when held out, versus one
survivor in-sample. One native-missing eligible frame stays explicitly missing;
its weak match is positive in-sample and negative out of fold. Two eligible
package frames lack any matching candidate in the pool in either context.

NBA masked/empty denominators are 240/19; NFHS adds one/two. Of 1,289 fitting-unknown
NBA candidates, 94 are above zero in-sample and 96 out of fold. The nine NFHS
fitting-unknown candidates are below zero. These are score descriptions only.
The full per-block, origin, visibility, target and uncertainty tables remain in
the linked output; native and weak origin counters keep their distinct schemas.

## HOU ranking gains and their regressions

| Episode | Eligible | New strict-first | Old point | Old CLS | Old peak, available features | Peak incomplete |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| e01 | 120 | 120 | 90 | 54 | 115 | 0 |
| e02 | 120 | 120 | 77 | 34 | 120 | 8 |
| e03 | 98 | 96 | 52 | 13 | 88 | 2 |
| e04 | 120 | 120 | 84 | 49 | 120 | 0 |
| e05 | 212 | 200 | 88 | 48 | 196 | 7 |
| e06 | 212 | 206 | 136 | 61 | 198 | 0 |
| Total | **882** | **862** | **527** | **259** | **837** | **17** |

The new score has 14 beaten rankings and six frames with no matching main-pool
candidate; there are no top ties. The six missing matches are the previously
identified below-.01 e05 cases, not six newly fabricated or negative examples.
The 78 localization-ineligible frames are retained outside this rank denominator.

The paired strict-first transition counts expose regressions beside gains:

| Saved control | Comparable eligible frames | New strict-first where old failed | Old strict-first where new failed |
| --- | ---: | ---: | ---: |
| Point | 882 | 338 | 3 |
| CLS | 882 | 605 | 2 |
| Peak, complete-feature rankings only | 865 | 36 | 11 |

All 17 excluded incomplete-peak frames have new strict-first rankings and remain
separately recorded. These counts measure ranking transitions only. They do not
create a new emitted location, certify ball identity, or measure trajectory
gaps, wrong-object duration or recovery acceptance.

## Rejection improves, but cannot preserve every correct point

| HOU episode | Native-correct kept at zero | Weak matching candidates kept at zero | Hidden frames with any survivor | Missing stress slots |
| --- | ---: | ---: | ---: | ---: |
| e01 | 107/110 | 13/15 | 0/0 | 0 |
| e02 | 120/120 | 19/19 | 0/0 | 0 |
| e03 | 87/90 | 10/13 | 0/0 | 3 |
| e04 | 108/120 | 41/48 | 0/0 | 1 |
| e05 | 180/195 | 19/31 | 2/16 | 6 |
| e06 | 196/207 | 30/36 | 1/18 | 1 |
| Total | **798/842** | **132/162** | **3/34** | **11** |

Zero retains 943/1,019 matching main candidates, 91/8,814 eligible misses,
3/410 hidden candidates and 9/535 unknown candidates. Candidate counts differ
from frame counts and can include multiple points in the same frame. The losses
of 44 native-correct points and 30 weak matches are not automatically 74 lost
tracking frames: categories can overlap and no new choice was made.

The full saved breakpoint curves show the conflict for a single global cutoff
on these observed scores. At the first descriptive boundary rejecting every HOU hidden
candidate, **770/842 native-correct points and 110/162 weak matches remain**.
At a boundary preserving all 842 native-correct points, candidates survive in
**all 34 hidden frames** (197 hidden candidates), with 160/162 weak matches kept.
Every breakpoint is saved; neither boundary is selected or recommended.
The older point score retained only 47/842 native-correct points when rejecting
all hidden candidates, so the new evidence is a real increment even though the
zero-hidden/full-preservation conflict remains.

A **posthoc descriptive cross-tab**, explicitly separate from the frozen
measurements, preserves all 7,468 package-context/HOU frame rows. Of the 44
rejected native-correct HOU points, 35 occur in strict-first frames and nine in
beaten frames. Of the 498 held-game native losses, 279 occur in match-first
frames and 219 in miss-first frames. Across all 882 eligible HOU frames, 825
strict-first frames have some matching candidate above zero and 37 do not;
three beaten frames have a positive match and 11 do not; six have no pool match.
Across all 2,811 held-game eligible frames, the corresponding counts are
2,275/267 match-first, 47/220 miss-first and two no-match frames. These counts
separate ordering from rejection without proving a calibration cause, fixing a
cutoff or constructing a trajectory. All ineligible, empty and masked rows
remain in the cross-tab under their proper categories.

The broad stress inventory is separate: 949 emitted and 11 missing slots.
At zero it retains **745/780 matching** stress choices, rejects all 97 eligible
misses and all 31 emitted certain-hidden choices, and retains three of 41
unknown choices. Those improvements coexist with **35 correct stress choices
lost**. Its “native correct” curve denominator is zero by construction and must
not be read as a successful native-preservation test. Missing slots have null
image logits; zero is used only as the named reject reference in comparisons.

## All seven contrasts, including agreement and missing states

Every row below includes all 960 HOU frames and the same 882/34/14/8/22 reference
category split. “Correct/wrong side” applies only where exactly one existing
choice succeeds under the declared comparison semantics. The remaining rows
include both-good, both-bad, unknown and agreement cases; they are not silently
counted as successes or failures. Unknown outcomes remain unknown when scores
differ. Both-missing ties do not have invented image evidence.

| Existing comparison | Same coordinate | Both observed, different | Source missing only | Target missing only | Both missing | Correct / wrong side | Not discrimination pair |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Native → motion+speed | 874 | 35 | 0 | 6 | 45 | 33/0 | 927 |
| Native → narrow weak | 871 | 39 | 37 | 5 | 8 | 54/1 | 905 |
| Motion+speed → narrow weak | 906 | 2 | 39 | 1 | 12 | 21/1 | 938 |
| Native → sequence strong | 829 | 70 | 0 | 16 | 45 | 70/8 | 882 |
| Native → sequence weak | 823 | 85 | 41 | 7 | 4 | 103/13 | 844 |
| Native → motion only | 860 | 39 | 0 | 16 | 45 | 44/4 | 912 |
| Native → speed only | 835 | 68 | 0 | 12 | 45 | 65/7 | 888 |

Coordinate and candidate-identity agreements have identical counts in these
actual records. All outcome transitions and overlapping tags are retained in
the full tables; tags are not disjoint samples and must not be summed.

For direct comparison with the previous point study's **two-observed-candidate**
denominators, the new score favors the correct side on **31/31 strong pairs and
34/34 narrow pairs**, versus point's 26/31 and 27/34. The larger 33/33 and 54/55
totals above include missing-reference comparisons, so those totals must not be
presented as if they were the old 31/34 populations.

The required useful and adverse groups remain explicit:

- **Ten e01/194–203 recoveries:** every main pool ranks a match first; every
  narrow recovery has a positive score (approximately 10.97–16.22), and all ten
  relevant old-choice comparisons favor the useful recovery. This improves on
  the earlier point recovery ranking of 3/10 and CLS 6/10. It is not a new
  trajectory/recovery-gate certification.
- **Six below-.01 e05/14–19 broad gains:** absent from the main pool; their saved
  broad stress queries are scored. Two are positive and four negative. The
  full native→sequence-weak broad-gain set has **13 correct-side and eight
  wrong-side preferences among all 21 gains**. Broad coverage is not solved.
- **Original six strong gains and 27 losses, including two missing:** the new
  score favors the correct side in all six and all 27 relevant native→strong
  comparisons. These successes do not filter the full analysis population.
- **e05/8–9 harmful weak additions:** both now have the correct relative ordering,
  unlike the old point comparison. However, both the good native and bad weak
  logits are negative. Correct ordering is not preservation under a zero veto.
- **e05/206 useful weak addition:** correct weak logit approximately +13.877,
  wrong native −13.976. Preserve this positive increment with the failures.
- **Nineteen shared old hidden emissions and eight added narrow emissions:** all
  have negative logits. Equal old choices cannot prove pairwise discrimination;
  other main-pool candidates still survive on three hidden frames.
- **All 842 native-correct, 19 native-wrong and 21 native-missing eligible
  frames**, all 78 noneligible frames, all unchanged errors and all missing
  comparisons remain in the full artifacts. No case set was reduced to gains.

## Historical diagnostics remain separate

All 60 original rows are retained: ten reference-bank entries, ten accepted
checks, six unresolved and 34 exposed regressions, including exactly the original
18 DET queries. No new frame or protected evaluation was accessed. Semantic
labels and older unaccepted AI assessments remain distinct from geometric targets.

Among the ten accepted checks, **four of six balls are positive and all four
other objects negative**. All four accepted same-frame ball/other pairs are
ordered correctly. The two negative accepted-ball checks are the original DET
frames 11008 and 11107, with logits approximately −13.234 and −10.620. They remain
failures of this fixed rejection diagnostic, not new fitting examples or a basis
for choosing a DET-specific model/cutoff.

The ten bank references are excluded from independent outcome metrics (four ball
references positive; two of six other-object references positive). All six
unresolved rows are negative, which does not resolve their labels. The 34 exposed
regressions have 18 positive and 16 negative logits with accepted classification
remaining null. Prior AI assessments are not promoted into accepted outcomes.

## What this supports next, and what remains uncertain

The completed result supports **preserving the learned ranking evidence while
diagnosing transfer and rejection failures before changing the model or building
a selector**. Strong fitted-game behavior, weaker held-game results, improved HOU
ranking and residual historical/weak/hidden failures are all present at once.
Neither “learning failed” nor “the ball tracker is fixed” describes this evidence.

The best-supported bounded next direction is a **CPU saved-score failure study**:
join the complete fitted/held/HOU records to existing game, episode, candidate
origin, uncertainty and support metadata; distinguish wrong ordering, a useful
candidate scored below zero, no matching pool candidate, and certain-hidden
survivors. Carry successes and agreements through the same tables. Use the
existing accepted labels and saved scores; do not fit a cutoff or add inference.
The precise follow-up protocol has not been frozen or run. The descriptive
reporting cross-tabs accompanying this result do not constitute a new selector.

If failures concentrate in useful candidates ranked correctly but scored below
zero, that supports investigating score comparability/rejection separately from
recognition. If ordering itself fails by game or support regime, representation,
context or data coverage becomes the stronger hypothesis. Missing pool matches
point upstream. Persistent hidden-positive evidence argues for an explicit
absence/visibility treatment. These are decision branches, not proven causes or
automatic authorizations. A different training amount and different fitting
games are confounded in this pilot; a low loss does not prove overfitting is the
only cause, nor justify adding epochs.

Small CNNs, wider context, separate presence evidence, regularization, joint
temporal evidence and materially different detector candidates remain open.
None was executed or ruled out here. No new threshold, selector, trajectory,
label campaign, architecture, ACB prototype, specialist, protected access or
automatic GPU follow-on is adopted. NBA remains the goal and cosine nine the
research control. Original accuracy/error/hidden/gap/recovery thresholds and
synchronized human identity/trajectory review remain unchanged. The nine
source-uncertain recovery events remain independently inconclusive.

## Actual reading and reuse

This decision reuses the completed Sessions 1–16 historical review (398 available
turns/47 pages), selected foundation evidence, previously read complete Session
17/18 handoffs and maintained subsequent scientific/crash/cable continuations.
The preparation reconciled the current source/authority map, validation history,
decisions and agreements with the full frozen pilot, capture census, actual
point/change outputs, failed fitted veto, relevant research chapters/ledgers and
targeted primary research. The saved scientific review documents its exact
reading and bindings. It is not a fresh reread of every transcript or paper.

Relevant historical evidence includes real WASB training gains, the later
training-fit versus NBA gap, the old veto's 207/581 correct-point losses, useful
weak e01 points, point's gains over CLS and its e01/hidden/historical failures,
and the complete candidate-change comparison. This result extends those records
without erasing successes or generalizing one failed setting to all learning.

The prior primary-source reading of the
[basketball crop study](https://arxiv.org/html/2204.00003),
[risk/coverage research](https://proceedings.mlr.press/v97/geifman19a.html), and
[grouped evaluation guidance](https://scikit-learn.org/stable/modules/cross_validation.html)
is reused here. The crop study's VGG16, ball sizes and capture conditions do not
validate this DINO recipe; risk/coverage motivates showing preservation alongside
rejection; grouped evaluation does not remove the upstream cosine-nine exposure.
No new external model or dataset was acquired. The new evidence is the actual
completed run, all scores, independent audits and full saved-record comparisons.
No video was newly adjudicated, and no completed experiment was repeated merely
to resume.

## Evidence, validation and preservation

Preparation/run base: `data/outputs/t/native_cable_training_continuation_2026-10-29_v0_1/`.
Scientific output base: `data/outputs/ball_tracking/candidate_quality_pilot_v0_1/attempt_005/`.

- `execution_approval.json`, `launch_readiness.json`, `ui_launch_observed.json`
  and `review/launch_review.json` bind the authorized scope and fresh readiness.
- `launcher_finished.json`, `monitoring/attempt_001/finished.json`, saved telemetry,
  `events_attempt_001/finished.json` and `postrun_windows_snapshot.json` establish
  observed runtime and cleanup; they do not prove hardware health.
- `postrun_audit/attempt005_complete_audit_001.json` records **246,129 saved checks**
  covering populations, updates, state provenance, checkpoints and supervision.
  The console's additional self-binding check is explained separately in
  `postrun_audit/count_scope_clarification.json`; the saved count is cited here.
- `postrun_audit/firstfit_tensor_equality_001.json` records **224 CPU checks**,
  finite exact endpoint equality, no CUDA initialization and no model forward.
- `postrun_analysis_audit/completed_score_audit.json` records **806,799 independent
  saved-score checks** across all package records/groups/frontiers, all HOU rows,
  all contrasts and all historical roles. This does not replace human review.
- `postrun_audit/completed_training_health_summary.json` retains exact loss,
  gradient and timing scope. `postrun_analysis_audit/paired_and_adverse_case_interpretation.json`
  retains the paired control and difficult-case diagnosis.
- `postrun_analysis_audit/rank_zero_crosstab.json` and its complete frame rows
  retain the explicitly posthoc ordering/rejection cross-tab;
  `complete_pilot_interpretation.json` records the independent full-result
  interpretation and reused history/research reconciliation.
- `postrun_report/completed_tables_001.json` and its extraction receipt retain
  every table, all overlapping tags and all breakpoint references. The original
  `package_analysis/frames.jsonl`, `summary.json`, and
  `all_nba/quality_evaluation/{frames,contrasts,historical}.jsonl`, `completed.json`
  and curve files remain the detailed score evidence. CPU consumers and reporting
  added no neural calls, labels, thresholds or emitted choices.

The frozen scientific sources, tests, proposal and original preparation report
remain unchanged. The new report and additive maintained-context entries preserve
all 99 prior worktree contents and the original Session 17 preservation chain.
The outcome verification records exact reconstruction of inserted documentation
and current hashes. Branch remains `codex/ball-detector-baseline`, HEAD
`8c040fca385dd8fffa0d7a13c45c53e79950bae1`; index remains empty. No staging,
commit, push or merge occurred. Generated models, images, logs and data remain
uncommitted. Focused saved-record checks and `git diff --check` are the relevant
validation; no claim is made that an old full suite covers later changes.
