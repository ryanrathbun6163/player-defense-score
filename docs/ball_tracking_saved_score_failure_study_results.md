# Saved-score CPU failure study results

October 29, 2026. The authorized study is complete. Accepted output is
`data/outputs/ball_tracking/saved_score_failure_study_v0_1/attempt_003/`.
It ran in **47.722 seconds**, using saved records only. The final 25 focused
tests and **1,615,156 independent output checks** pass. Earlier attempts are
preserved and explicitly not accepted, as explained below.

The scorer's useful ranking gains remain real, but its errors are not explained
by a single score offset or an absence of every kind of training support.
Held-game matching candidates lose score while many misses gain score; full-pool
separation narrows and some orderings reverse. Other frames retain correct
ordering while every matching point falls below zero. Source, visibility and
support differ substantially, without establishing their causal contribution.
No threshold, model, selector or trajectory is adopted.

## Scope, reading and reuse

This implements the [frozen protocol](ball_tracking_saved_score_failure_study_protocol.md)
and [bound specification](../configs/ball_tracking/proposals/saved_score_failure_study_v0_1.json).
Ryan explicitly requested implementing and running the CPU study using saved
results. The original design files remain unchanged; additive execution freezes
record that later authorization and the exact implementation used.

We reused the completed Session 19 resume verification, Sessions 1–16 historical
review (398 available turns / 47 pages), Session 17/18/19 handoffs, maintained
context and October 26 reassessment, plus the design's targeted source/research
review. The inherited research ledger covers 56/75 entries with recorded depth
limits. This is not a fresh every-transcript, every-paper or every-historical-
paragraph reread. Implementation review inspected the original target rules,
saved schemas, source roles and original producers. New evidence here consists
of exact saved-record joins, paired differences, fixed metadata/support tables
and their independent audits. No new image or video was adjudicated.

The four-fit pilot, original package/HOU consumers, previous scientific audits,
point/CLS/peak comparisons and 7,468-row rank/zero cross-tab were reused. Their
headline scores below are reconciliation controls, not newly repeated
experiments. The newly measured parts are the source-conditioned joint views,
NBA fitted/held pair transport and differences, and actual per-fit support
correspondences. Historical semantic evidence stays separate from geometric
training targets. HOU is exposed development data, excluded from fitting and
threshold selection; DET remains limited to its original 18 historical queries.

## Complete populations and units

| Population | Retained unit/count |
| --- | ---: |
| Unique package | 3,329 frames; 19,632 candidates; 21 empty frames |
| NBA fitted/held pairs | 3,179 frames; 18,813 candidate pairs |
| NFHS secondary, without fabricated held scores | 150 frames; 819 candidates |
| HOU development | 960 frames; 10,778 main queries; 960 stress slots |
| Historical appendix | 60 rows: 10 bank, 10 accepted checks, 6 unresolved, 34 exposed regression |
| All context frames | 7,468 |
| Candidate-context score slots | 50,243: 50,232 observed, 11 missing stress images |
| Original choices / seven directed contrasts | 6,720 slots / 6,720 rows; 299 choice slots remain missing |

Candidate counts and distinct-frame counts are both reported. Tags, metadata
families and fitting folds overlap and are not additive. Missing scores are
null, never substituted with the contrast's zero reference. All exact-zero and
rank-tie states remain representable; none occurred in the paired NBA scores.

## A. Correct ordering, rejection, absent matches and hidden survivors

These complete-context counts reconcile the existing evidence:

| Context | Eligible frames | Strictly matching first | Native-correct points above zero | Frames with any matching point above zero | Certain-hidden frames with a survivor |
| --- | ---: | ---: | ---: | ---: | ---: |
| NBA fitted | 2,811 | 2,805 | 2,807/2,807 | 2,809 | 0/128 |
| NBA held | 2,811 | 2,542 | 2,309/2,807 | 2,322 | 28/128 |
| HOU | 882 | 862 | 798/842 | 828 | 3/34 |
| NFHS secondary | 130 | 115 | 59/130 | 66 | 0/19 |

The joint states matter. In held NBA, **267 frames rank a match strictly first
but have no positive matching score**; another 220 rank a miss first and have no
positive match. There are 47 miss-first frames that nevertheless contain a
positive match, and two frames lack a matching candidate. HOU has the analogous
37 correctly ranked/all-matches-rejected, 11 miss-first/no-positive-match,
three miss-first/positive-match and six no-match frames. NFHS has 49 correctly
ranked/all-matches-rejected frames. These states are not interchangeable with
loss of one original native point: another matching point can survive.

The newly joined source view retains successes alongside failures:

| Source/context | Strictly matching first / eligible | Native-correct retained / available | Weak-match frames retaining a weak match | Hidden survivor frames / certain hidden |
| --- | ---: | ---: | ---: | ---: |
| DEN held | 899/920 | 808/920 | 155/183 | 0/10 |
| CHI held | 730/836 | 637/832 | 106/250 | 2/50 |
| SAC held | 913/1,055 | 864/1,055 | 141/177 | 26/68 |
| HOU development | 862/882 | 798/842 | 131/159 | 3/34 |

Pooled visibility summaries show more partial-visibility losses, but the
relationship differs by source and is not a complete explanation.
Held NBA retains 643/756 fully visible native-correct points and 1,666/2,051
partially visible ones; HOU retains 326/336 and 472/506 respectively. HOU's six
missing-match pools are partially visible. The full tables also retain
indeterminate identity, uncertain hidden and visible-but-unlocalizable cases;
those are not scored as certain-hidden negatives or localization failures.
For SAC, native-correct losses are 183/817 partial versus 8/238 fully visible;
DEN has 80/694 versus 32/226 and CHI 122/540 versus 73/292. The pooled direction
therefore must not be treated as a uniform visibility effect across games.

Continuous producer metadata does not supply a simple low-response explanation.
Within held NBA native-component extraction at .3, rejected matching candidates
have median saved response mass **40.074** (514 candidates / 499 frames), versus
**39.996** for 2,309 retained matching candidates. For weak-component extraction
at .01, the corresponding medians are **76.922** for 208 rejected candidates and
**62.695** for 402 retained candidates. Their median component counts are 861 and
641 pixels. These are descriptive, source-confounded distributions with overlap,
not selected rules. The response value is component response mass, not a peak
probability; component pixels are not physical ball diameter. HOU's native
matching-candidate component medians are similarly close: 64.5 rejected versus
64 retained. Full min/median/max and inclusive quartiles remain in the fixed
producer-compatible numeric tables.

## B. What changes between fitted and held NBA scores

The 18,813 exact candidate pairs and 3,179 exact frame pairs have no missing
score or identity join. **2,541 frames retain match-first ordering, 264 change
from match-first to miss-first, one improves, and three remain miss-first.**
The remaining 368 are ineligible and two lack a matching pool candidate.

| Candidate population | Paired candidates | Median held-minus-fitted logit | Positive to negative |
| --- | ---: | ---: | ---: |
| Native eligible matches, including unselected alternatives | 2,823 | -4.529 | 514 |
| Weak eligible matches | 610 | -6.751 | 208 |
| All candidates, including misses and masked cases | 18,813 | +1.109 | 775 |

The overall positive median shift is dominated by the much larger miss
population; it is not improved scoring of useful points. Across all candidates,
14,846 stay negative, 2,754 stay positive, 775 cross downward and 438 cross
upward. The 514 native-candidate losses differ from 498 losses of the originally
selected native-correct point because candidate and selection units differ.

The full-pool margin is maximum matching score minus maximum eligible-miss
score, never an origin-restricted reranking. On the 2,694 frames where both
maxima exist, its median held-minus-fitted change is **-8.310** (quartiles
-17.091 and -5.181). The other 485 pair margins stay null: 368 ineligible,
115 without an eligible miss, and two without a match. Candidate-level summaries
carrying parent margins explicitly label their candidate weighting.

This combination supports both rejection/comparability and representation or
coverage questions. A uniform offset alone cannot reverse a within-frame rank
or recover a missing candidate. Fitted versus held model composition and
training amount are confounded; these differences do not isolate a cause.

## C. Actual fitting support, not nominal candidate volume

Support is joined to the fit that produced each score, using only its included
training games. A held game's ID is not required to match a fitting-game ID.
Each key uses target group and native/weak origin plus exactly one fixed metadata
family. The 794 support cells and 6,054 diagnostic associations preserve both
successful and failed cases, actual membership, objective mass and unique
fitting frames/blocks/games.

The all-NBA fit's complete target/origin support is:

| Target / origin | Fitting candidates | Distinct fitting frames | Games | Objective mass |
| --- | ---: | ---: | ---: | ---: |
| Positive native | 2,823 | 2,808 | 3 | 0.443928 |
| Positive weak | 610 | 610 | 3 | 0.056072 |
| Eligible distant miss, native | 70 | 53 | 2 | 0.002786 |
| Eligible distant miss, weak | 13,706 | 2,694 | 3 | 0.247214 |
| Certain hidden, native | 2 | 2 | 1 | 0.001984 |
| Certain hidden, weak | 313 | 113 | 3 | 0.248016 |

The six masses sum to the original .5 positive / .25 eligible distant miss /
.25 certain-hidden objective. They are not population probabilities. Unknown
or boundary targets remain excluded, with null objective mass. Native negatives
and certain-hidden native examples have especially limited support; the
leave-CHI-out fit has **zero native certain-hidden fitting candidates**. Weak
hidden support remains available there, so this is a specific origin/target
gap, not absence of all hidden examples. SAC's 26 hidden-survivor frames occur
despite available marginal weak-hidden support: matching metadata alone does
not establish useful visual coverage.

Zero-support metadata cells also contain successes: held DEN retains 16/18
padded native-positive candidates despite no padded native-positive fitting
examples, and held CHI retains all 34 native-positive candidates tagged defocus
despite no corresponding fitting tag. Held SAC's unsupported tiny-tag native
cell has 74 retained and 46 rejected candidates, while its weak cell retains
20 of 40 (20 rejected). These are separate marginal correspondences, not a
causal test or a license to combine tags into an outcome-selected rule.

The earlier 674 package weak-match frames include 64 NFHS frames. The actual
all-NBA fit has 610 weak-positive fitting frames. The established weak-support
pattern remains: almost all weak matches accompany an already successful native
point, rather than supplying diverse native-wrong repairs. A large weak-miss
population or a matching visibility/radius label therefore cannot prove support
for the intended recovery task.

Exact numeric radii such as 4 and 4.0 share a grouping key while all original
row values are preserved. Distinct fractional radii are never rounded or binned.
The 92 zero-fitting-support cells concern fully specified categories; 14 cells
instead identify unavailable metadata, and 286 identify excluded/inapplicable
targets or origins. These are overlapping marginal cells, not independent
failure counts. In particular, saved stress choices supply origin/extraction
but omit thresholds: those extraction correspondences have null mass and are
unavailable, not evidence of absent training. Hidden radius=null is structural
absence of geometry; its counts remain, but no measured-radius similarity is
claimed. Other families still report actual hidden fitting mass.

## D. Recovery, adverse, agreement and historical controls remain

The complete seven directed contrasts and original agreements remain linked to
source metadata and full-pool state. This study does not create a new choice.
The inherited successes and adverse results are retained together:

- All ten e01 recoveries rank first, score positive and beat the missing
  comparison reference. All 21 broad gains remain, alongside six e05/14–19
  below-.01 cases, four of which score negative.
- All 842 native-correct, 19 native-wrong and 21 native-missing eligible HOU
  frames remain. The original six strong gains and 27 losses, including two
  missing cases, are retained with e05/8–9 and /206.
- The old point/CLS/peak controls retain all three point, two CLS and eleven
  complete-peak rank regressions, with all 17 incomplete-peak cases separate.
  The inherited peak comparison remains 36 gains / 11 losses on 865 complete
  pairs; point and CLS strict-first counts remain 527 and 259 versus quality 862.
- The original hidden choices retain 19 shared and eight added narrow
  emissions, plus the other seven certain-hidden cases. All 78 noneligible HOU
  frames remain. Equal old choices do not demonstrate discrimination.
- The 60 historical rows retain their four roles. Bank rows are not independent
  tests; six unresolved cases stay unresolved. Two accepted historical balls
  remain negative. No semantic label is changed by geometric reporting.

`case_views.json`, `contrast_views.jsonl`, `source_choices.jsonl` and
`historical_appendix.jsonl` provide every row and original case tag. These views
retain inherited results rather than turning selected motivating cases into
new denominator populations.

## Interpretation and next question

The completed study supports designing a bounded comparison of explicit
presence/rejection evidence and cross-source score comparability, with
preservation of correct native points and weak recoveries as co-primary
constraints alongside hidden emissions. Ordering and proposal coverage must
remain separate constraints: the 264 paired ordering regressions and missing
matches prevent treating this as threshold adjustment alone. Representation,
context, regularization and recovery-support coverage remain plausible avenues;
these descriptive associations do not choose a new architecture or recipe.

Any next design should reuse the existing curves and case lists, retain source
held-out reporting and all successes/adverse cases, and specify its question
before execution. This report does not fit a calibration model, optimize a
cutoff, label new data, load a model, or claim an independent evaluation result.
NBA remains the goal and cosine nine remains the research control. Upstream
cosine nine already saw these package games; scorer-held results are not
end-to-end unseen-game tests. HOU is exposed, frames/candidates/folds are
correlated, and frozen post-exposure endpoints are not pristine preregistration.
Accepted labels, pending human trajectory review, protected closure and the
standing Debug Mode ON instruction remain unchanged.

## Implementation, corrections and reproducibility

New modules are `src/ball_tracking/saved_score_failure_data.py`,
`saved_score_failure_analysis.py` and `saved_score_failure_study.py`, with three
focused test modules and one bounded captured-schema fixture. The runner checks
the exact 43 inputs, protocol, metadata preparation and execution bindings,
rejects an existing output directory, and uses only standard-library JSON and
CPU arithmetic. No neural forward/training, GPU query, pixel decode, new DET
query, label, model adoption or protected access occurred.

Three new-consumer attempts are preserved. Attempt 001 completed in 37.223s
but was not accepted: a positive-retention summary counter collided with a
generic sign counter and doubled that aggregate. Attempt 002 completed in
36.028s after that correction but was also not accepted: exact numeric category
serialization split equivalent integral radii, and incomplete stress extraction
metadata was misclassified as zero support. Regression checks cover all three
defects. Attempt 003 completed in 47.722s after corrected code was independently
reviewed and frozen. The source records and earlier experiment outputs were
unchanged throughout; no rejected attempt was overwritten. The roughly 121s
sum is new-consumer runtime, not total project work or GPU time.

Within `data/outputs/ball_tracking/saved_score_failure_study_v0_1/`:

- `implementation_preparation/baseline_and_authorization.json` binds the prior
  102-file worktree and the user's execution request. `execution_freeze_003.json`
  binds final source/tests/dependencies, the 25-test receipt, final code review
  and both earlier nonacceptance notes. Original freezes/tests remain.
- `attempt_003/completed.json` binds all 19 output artifacts. These include full
  joined frame/candidate rows, choices, paired rows and tables, frame/candidate
  metadata tables, compatible numeric summaries, support cells/associations,
  contrasts, historical appendix, cases, missingness and source controls.
  The design's generic paired/support output categories are split by unit;
  the freeze records the mapping without changing populations or endpoints.
- `implementation_review/output_audit_003.json` passes **1,571,724** independent
  source/identity/state/count/support checks. `numeric_tables_audit_003.json`
  adds **43,432** independent numeric-table and missingness checks. Neither
  invokes the consumer. Earlier audit 001's narrower scope and rejection are
  explicit; its initial pass is not acceptance of that attempt.
- The compact project review ledger is
  `configs/ball_tracking/reviews/saved_score_failure_study_result_v0_1.json`.
  Additive documentation preservation and final review are recorded beneath
  `implementation_preparation/documentation_update/` and `implementation_review/`.

All 102 preimplementation worktree contents and the original Session 17 chain
remain recoverable through exact prior hashes and reversible insertions.
Branch `codex/ball-detector-baseline`, HEAD
`8c040fca385dd8fffa0d7a13c45c53e79950bae1` and the empty index are unchanged.
No staging, commit, push, merge, reset or cleanup was performed.
