# Saved candidate-change comparison protocol

October 28, 2026, America/Phoenix. **Design specified; comparison analysis not
implemented or run.** Metadata/cache preparation is separate from the proposed
outcome analysis. The machine-readable companion is
[candidate_change_comparison_v0_1.json](../configs/ball_tracking/proposals/candidate_change_comparison_v0_1.json).
Neither document authorizes a new selector, trajectory or training run.

## The question, simply

When an existing sequence method changes the native detector's choice, does the
saved point-image evidence favor useful changes and oppose harmful ones?
Compare the actual old and new points on every declared frame, including frames
where the methods agree or leave a point missing. This asks whether the point
information is complementary to response strength. It does not ask the image
score to find the ball everywhere or establish visibility by itself.

The result will be a table of existing choices and evidence, with explicit
limitations. It will publish no revised trajectory. A relative preference
between two points cannot tell us whether either should have been emitted.

## Historical and research reconciliation before this specification

Reuse the completed [full-history reassessment](research/ball_tracking_full_history_reassessment_2026-10-26.md),
the [authority/session map](context/source_map.md), and the
[validation history](context/validation_history.md). The inherited review covers
the available Sessions 1–16 timelines (398 turns/47 pages); earlier foundation
coverage is selected decisions and primary evidence, not six complete raw
transcript rereads. This continuation read both complete Session 17/18 handoffs,
the reassessment, the saved [research reconciliation](../data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/history/research_reconciliation/review.txt)
and the [point-result decision basis](../data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/point_comparison_v0_1/validation/history_reconciled_decision_basis.txt).
It did not retrieve the raw Session 17/18 transcripts anew. The earlier explicit
research check occurred after the original point proposal and before its approval
and inference; this specification does not backdate that check.

New reading also covered the current project entry/decision/agreement records,
current sections and relevant historical entries in the large context records,
the weak-response design/result, response diagnosis, point proposal/recipe/result,
their ledger structures and relevant bound primary artifacts. Numerical ledger
tables and the 43 MB point analysis were parsed locally rather than reproduced
in chat. The exact query/choice producer fields, saved point receipts/witnesses,
score transport and objective-accounting record were inspected. Prior numerical
audits are reused; this is not an independent repeat of their neural-network or
token arithmetic. Required entry documents do not imply a new line-by-line read
of every historical block in the very large context files.

The saved research hub, recommendations, research-method limits, relevant
ball-research and evaluation chapter sections, October 25 next-step review and
selected source-ledger records were consulted. The completed broader review's
56/75 ball-ledger coverage is inherited, not a new every-source inspection.
Source-ledger inspection depths remain unchanged. No external release or new
paper availability was verified here; no current-release claim drives this
cache-only design. No material missing historical/research evidence was found
that changes this bounded question. External model availability would need fresh
primary checking before choosing one of those alternatives.

| Evidence actually used | What it supports here | Adverse evidence and limit |
| --- | --- | --- |
| [Crop/motion factorial](ball_crop_motion_factorial_results.md), inspected mechanism sections | Movement allowance and cost changes can produce real gains. Preserve motion evidence as context. | Persistent false paths and hidden emissions also have temporal support. Smoothness is not identity. |
| [Accepted gap/anchor evaluation](nba_gap_anchor_reference_evaluation_results.md), inspected results/authority | Preserve three earlier accepted gains and eight later geometric gains. | Two later P001 gains remain identity-ambiguous; SAC head anchors/fill remain adverse even with unknown true-ball geometry. |
| [Fitted DINO veto](nba_ball_distractor_training_results.md), inspected fit/protection results | Test preservation explicitly before proposing learning. | Converged fitting removed 207/581 correct points. This was a fitted head, distinct from the present nearest-bank rule. |
| [Successor/TAP result](ball_tracking_successor_results.md), inspected method/results; continuation/spatial evidence reused through the maintained review | Preserve successful training increments and the reasons for testing new information. | Single-seed TAP failed 12/13 guards; repeated WASB continuations/spatial fit left the DET gap. Neither exhausts its method family. |
| [Weak-response/follow-up](ball_tracking_weak_response_results.md), current reports and actual choices | Ten e01 recoveries and motion/speed repairs are useful. Include every completed arm. | Strong 821 and narrow weak 831 correct trail native 842/882; hidden emissions and lost native points remain. |
| [Response diagnosis](ball_tracking_candidate_response_feasibility.md), saved objective accounting and sealed feature transport | Keep peak/native mass controls and explicit missing states. | Five shape rules lose to peak in every episode; broad availability is density-confounded. Positive emission/restart incentives favor false paths. |
| [Point result](ball_tracking_point_feature_comparison_results.md), actual analysis/receipts and prior audits | Point beats CLS in all six episodes, 527 versus 259/882 strict-first; useful relative signal deserves a complete change diagnosis. | Peak is 837. e01 recoveries are point 3/10 versus CLS 6/10. Hidden rejection retains only 47/842 native-correct; native preservation leaves all 34 hidden frames. Historical accepted preference falls 8/10 to 7/10. |

The six useful corrected-strong changes (point favors five) and 27 native-correct
losses (point favors native in 21/25 emitted pairs, with two missing) motivate the
question. They were already inspected and are not a new validation set. The new
variation is the **complete declared choice population**, including the ways a
pair comparison cannot answer absence. It adds no new image encoding, bank,
feature fit, threshold or temporal optimization.

This is the best-supported bounded next diagnostic among the inspected options
because exact image outputs and old choices already exist and their
complementarity remains unresolved. It is not claimed globally optimal.
Basketball MonoTrack, specialist RF-DETR adaptation, learned basketball context,
materially changed temporal/reseeding methods, and joint/temporal response
evidence remain open. Their cost, data and integration questions remain; none
is ruled out by failure of this particular readout/bank or selector recipe.

## Fixed development population and comparisons

Use all six HOU episodes, all **960 frames**, with their existing source ranges,
timestamps and accepted references. HOU remains repeatedly inspected
checkpoint-validation development, excluded from fitting. There is no fresh-test
or frame-independence claim. Every arm contributes one choice slot per frame,
including missing slots; seven arms give **6,720 choice slots**.

| Arm name in producing records | Purpose | Cached emitted / missing slots |
| --- | --- | ---: |
| `native` | Unchanged cosine-nine selection; research control | 915 / 45 |
| `sequence_strong` | First failed strong sequence | 899 / 61 |
| `sequence_weak` | First expanded/broad weak sequence, including its stress choices | 949 / 11 |
| `motion_only` | Completed motion-cost-only follow-up | 899 / 61 |
| `speed_only` | Completed speed-only follow-up | 903 / 57 |
| `motion_and_speed` | Corrected strong sequence | 909 / 51 |
| `motion_and_speed_narrow_weak` | Corrected sequence with native-plus-strict-.01 pool | 947 / 13 |

Three primary directed contrasts are native to corrected strong, native to
narrow weak, and corrected strong to narrow weak. Four historical/context
contrasts compare native to each remaining arm. Every contrast includes all
960 frames: **6,720 contrast-frame rows**, reported separately. This happens to
equal the choice-slot count; the two counts describe different tables. Do not
pool repeated appearances of a choice as independent evidence. Other cross-arm
pairings are outside v0.1; adding them later requires a declared amendment, not
searching for a favorable pair.

Keep the existing partition: 882 eligible, 34 certain-hidden, 14 indeterminate,
eight uncertain-hidden, and 22 visible-unlocalizable. Cross-tabulate every
contrast by episode, reference category, both choice states and each eligible
outcome. Agreements must include correct/correct, wrong/wrong and hidden
emission agreements, as well as both-missing agreements.

Maintain overlapping named diagnostic tags, never summed as disjoint samples:
all 842 native-correct, 19 native-wrong and 21 native-missing eligible frames;
the ten e01 recoveries (194–203); the six below-.01 e05 broad gains (14–19);
all 21 old broad gains from native missing; the six useful/27 harmful corrected-
strong cases, including two missing; every certain-hidden/uncertain/unlocalizable
case; complete-source versus padded crops; native versus weak extraction.
No tag defines inclusion in the main population.

The existing 60 historical appearance cases remain a separate fixed appendix:
ten bank references excluded from query metrics, ten accepted checks, six
unresolved and 34 exposed cases. Reuse their published point/CLS outputs and
role-specific findings, including DET11008/11059/11107/11431/11444 and SAC1419–1421.
No new semantic labels or pooled HOU/DET accuracy result. DET chooses no method,
feature, bank or cutoff. SAC exposure remains explicit. Full DET/SAC point
coverage is not cached and is outside this design; no inference follows from
that gap. NFHS remains secondary evidence, with no new evaluation in this study.

## Exact cache and provenance joins

First use the ignored [preparation inventory](../data/outputs/ball_tracking/candidate_change_comparison_v0_1/inventory.json)
and [choice-to-cache joins](../data/outputs/ball_tracking/candidate_change_comparison_v0_1/choice_cache_joins.jsonl).
These contain metadata/cache availability, not newly computed pair preferences.
All 6,421 emitted choice slots have exact cached descriptors; 299 slots are
explicitly missing. All 10,883 input receipts and their raw witness byte hashes
were checked. These repeated arm slots are not distinct ball observations.
The original point analysis supplies sealed `query_margin_rows`; raw CLS/four-token
witnesses and `input_records` remain immutable verification evidence.

Join by source video SHA256, block ID, source frame, exact PTS/time base and
duration, PNG byte/RGB identity, mean-map hash, producing pool identity and
selected candidate index. Verify exact coordinates and native-prefix membership
against the actual producing records. Native/strong/follow-up choices use their
exact main query; first broad weak uses its own stress query. Different pools'
candidate index zero is not a global identity. Never join by proximity, rounded
coordinates, nearest crop, or a descriptor from the same frame alone.

The prepared main registry has 10,778 native-plus-.01 candidates. The stress
registry has only the 960 old **selected** broad choices, not all 4,020,880 broad
candidates. Identical image inputs can share a forward, but their point queries
retain exact interpolation weights. Same coordinates with different producing
identities retain both provenance links; coordinate agreement and identity
agreement are recorded separately. Padding is never evidence for absence.

Verify role/acceptance receipts, rather than treating inherited annotation-note
text saying "pending" as a reversal of subsequent acceptance. Preserve original
notes and labels. Validate the existing 10,883 input-receipt/witness byte bindings;
reuse prior numerical audits without running DINO or reconstructing all cosines.
An emitted candidate without an exact cache link remains `cache_unavailable`
with a reason. A missing choice is `missing_selection`, with no coordinate,
input, margin, synthetic zero or imputed image evidence. Never drop either kind.
Any unexpected integrity mismatch blocks the affected analysis pending diagnosis;
do not silently shrink the frozen population or refill caches with inference.

## Measurements fixed before new outcome analysis

1. **Complete accounting.** For each contrast/episode, partition states into
   both observed with identical coordinates, both observed with different
   coordinates, source observed/target missing, source missing/target observed,
   and both missing. Record candidate identity agreement separately. Partition
   eligible rows by the full 3 by 3 matched/wrong/missing transition matrix.
   Reproduce the old per-arm outcome and hidden-emission totals from saved
   scores; do not call these results new tracking improvements.
2. **Relative ordering for observed pairs.** For point, CLS and saved peak,
   compute target score minus source score. Positive favors target; negative
   favors source; exact zero is a tie. Use saved float64 numbers, no rounding
   or fitted near-tie tolerance for decisions. Print raw differences and explicit
   unavailable-feature reasons. Native mass is compared only when both choices
   are native components of the same frame/threshold; weak/broad mass differences
   are incomparable. Original mass, extraction, support and path margins stay
   visible as provenance, not calibrated correctness probabilities.
3. **Discrimination and preservation together.** On eligible distinct-point
   pairs with exactly one match and one wrong output, report correct-side,
   wrong-side, tie and unavailable counts for every feature. Keep beneficial
   wrong-to-match revisions separate from harmful match-to-wrong revisions.
   Compare point and CLS on their common complete pairs; show point's favorable,
   adverse and tied differences versus peak and comparable native mass. Publish
   full feature-sign cross-tables, including peak/mass opposition, without
   learning a combination or selecting a sign pattern as a rule. Both-correct
   and both-wrong revisions remain separate; distance differences are descriptive,
   and neither makes a pair semantically ball/non-ball.
4. **Missing and visibility limits.** Source-missing/target-matched recovery,
   source-matched/target-missing loss, wrong-to-missing, and missing-to-wrong each
   retain their complete counts. No pair preference is available against missing.
   For certain-hidden rows print both emissions/missing states and, for two
   emitted points, score ordering marked "neither emission valid". Uncertain-
   hidden, indeterminate and visible-unlocalizable rows receive state/feature
   availability summaries and separate descriptive ordering, never correct-side
   success or negative labels. No new absolute cutoff/visibility bound is fitted.
5. **Recurrence and exceptions.** Report the same tables per episode and named
   tag, then pooled descriptive totals with denominators. List every harmful
   preference, missing/cache exclusion, hidden-emission agreement and counterexample
   by exact frame/query, together with beneficial cases. Preserve same-point
   agreements as the frame-level denominator, not evidence of discrimination.
   Include full machine-readable rows so favorable examples cannot replace the
   population. Do not publish frame-level significance tests or confidence claims.

Report denominators as total declared rows, two observed, distinct-coordinate
pairs, exactly-one-correct pairs, feature-complete pairs, ties and unknowns. A
complete-pair rate must print excluded missing/unscored/incomplete counts beside
it. Overlapping contrasts and tags are not additional observations. The adverse
e01 3/10 result and all old visibility/historical failures accompany the new table.

The study computes no new trajectories, fills, switches, recoveries or final
quality scores. Existing objective-accounting results, path-margin/support
metadata and old failed temporal gates remain context. No new counterfactual
path optimization, motion threshold or objective-weight sweep is included.

## Implementation, validation and freeze boundary

Use separately named additive CPU analysis code; do not edit any of the 187
source/test/audit files bound by the completed point-study freeze. Read saved
JSON/JSONL and stream witnesses for binding checks. No Torch/model import, PNG
decode, video rendering, package installation or GPU work is necessary. The
bounded workload is 960 frames, seven old choice series, 11,798 cached score
rows and 6,720 contrast rows. Do not promise runtime from inference timings:
metadata inventory and filesystem verification are different work. Record actual
time/resources; keep intermediates ignored and avoid copying the broad pools.

Before running the proposed endpoint analysis, bind this protocol/config,
inventory, exact score/choice/reference inputs and new analysis source/tests in
one small prospective execution receipt. The design is specified now; the
implementation freeze and its execution decision remain outstanding. Preserve
the fact that earlier results and metadata were already inspected. This is a
follow-up on exposed development data, not a blinded discovery study.

Focused validation should exercise actual captured producer rows plus synthetic
counterexamples: different pool index with same coordinate; same crop/different
point query; source/frame/PTS/PNG mismatch; present/missing and both missing;
ties; all outcome transitions; certain-hidden versus uncertain; incomparable
mass; incomplete peak; duplicate or dropped rows; and per-episode totals.
Independently recount emitted table partitions and exact coordinate distances
from accepted references, explicitly naming any category/parser reuse. Verify
actual transport instead of only fixtures that mirror the consumer. No full-suite
or repeated old experiment is needed for this documentation/preparation increment.

## What the result can change

Recurring useful point preference across the complete primary contrasts and
relevant episodes, with its harmful preferences and native/weak losses fully
exposed, can justify specifying one later selective-change test. The critical
evidence is complementary correct-side preference when response strength prefers
the other point, alongside preservation of correct native and weak choices.
A pooled gain driven only by the old six cases, or preservation that merely
repeats mass/native preference, is insufficient evidence of that complementarity.
No new numerical adoption gate is invented for a diagnostic with no output policy.

If signal is mixed, retain the useful strata and the exact adverse cases without
selecting episode-specific exceptions. If it is absent outside the already
inspected subset, do not rescue it through a threshold/weight search or fitted
head. Reconcile the live alternatives and primary evidence before the next
direction. Even strong observed-pair discrimination leaves one-sided missing,
hidden visibility, wrong anchors and no-candidate failures unresolved. It cannot
by itself justify training, adoption, or a claim of NBA tracking completion.

NBA remains the goal; cosine nine remains research control. Keep all accepted
labels and roles, original failures/checkpoints, and the nine inconclusive
source recoveries (HOU e03 146/190; DET 11047/11075/11098/11107/11476/11497/11557).
Unchanged final gates are at least 95% correct within inclusive ten source pixels,
at most 1% wrong, zero certain-hidden emissions, eligible missing gaps at most
200 ms, confirmed wrong-object runs below 120 ms, recovery within 120 ms plus
two subsequent correct eligible frames, and complete synchronized human review.
Existing human trajectory reviews remain pending; this document creates no new
human acceptance. Identity/calibration remain human gates, and NBA player geometry
is not certified by the high-school result. Protected evaluation remains closed.
No new training, selector/trajectory, inference, labels, ACB prototype or outside
specialist follows automatically. Staging, committing and publication remain
separate authorization steps.
