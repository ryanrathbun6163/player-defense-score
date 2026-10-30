# Saved candidate-change comparison results

October 28, 2026, America/Phoenix. **Completed CPU diagnosis, independently
recounted. No new selector, trajectory or trained model is adopted.**

The saved point features contain useful information for choosing between two
existing points. The complete comparison also exposes a hard limit: much of the
remaining problem is deciding whether to emit at all, where one side is missing
and no relative image comparison exists. The useful signal is concentrated;
this result does not establish a safe change-acceptance rule or justify training
by itself.

## What was run

Ryan said, "Ok chat move forward. Let's make some good progress today", after
the [specified protocol](ball_tracking_candidate_change_comparison_protocol.md).
One CPU analysis executed that fixed design: all 960 HOU frames, native plus
all six completed selector arms, 6,720 existing choice slots and 6,720 rows in
seven directed comparisons. The three primary contrasts and four historical
contrasts were fixed before outcome analysis. No extra pairing, fitted weight,
threshold, bank change or trajectory was introduced.

The earlier preparation exactly linked 6,421 emitted choice slots to cached
point/CLS outputs and retained 299 missing slots. This execution rechecked actual
producer choices, source/candidate/PTS/PNG joins, accepted-reference authority,
saved margins and prior scored outcomes. It reused the original point numerical
audits and cache inventory rather than repeating inference or token arithmetic.
The 34 certain-hidden, eight uncertain-hidden, 14 indeterminate and 22
visible-unlocalizable frames remain separate from 882 eligible frames.

Analysis took **1.817 seconds**. The process reported a peak working set of
294,924,288 bytes before completion serialization and 1.75 process CPU seconds.
That wall time excludes prior inventory, implementation, tests and recount.
There was one successful analysis attempt and no retry. No model was imported
or run, no pixels were decoded, and no selector or training updates occurred.

## Complete primary comparison accounting

"Same point" means exact coordinate agreement. Candidate identities and their
pool provenance are separately retained. Counts below include all reference
categories, not just scored or favorable frames.

| Source to target | Same observed point | Different observed points | Source point, target missing | Source missing, target point | Both missing | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Native to corrected strong | 874 | 35 | 6 | 0 | 45 | 960 |
| Native to narrow weak | 871 | 39 | 5 | 37 | 8 | 960 |
| Corrected strong to narrow weak | 906 | 2 | 1 | 39 | 12 | 960 |

On eligible frames, the full outcome transitions are:

| Source to target | Correct to correct | Correct to wrong | Correct to missing | Wrong to correct | Wrong to wrong | Wrong to missing | Missing to correct | Missing to wrong | Missing to missing |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Native to corrected strong | 815 | 25 | 2 | 6 | 11 | 2 | 0 | 0 | 21 |
| Native to narrow weak | 813 | 27 | 2 | 7 | 11 | 1 | 11 | 9 | 1 |
| Corrected strong to narrow weak | 819 | 2 | 0 | 0 | 36 | 0 | 12 | 9 | 4 |

Each row totals 882 eligible frames. No primary contrast has a different-point
correct/correct revision; its correct/correct rows are agreements. Wrong/wrong
agreements remain failures, and neither agreement nor a missing choice is
discarded from the population.

## Point ordering helps, with specific counterexamples

The table counts distinct, observed match/wrong pairs with exactly one correct
point under the unchanged inclusive ten-pixel criterion. It asks which point
has the higher saved score. It is **not tracking accuracy** or a new output
policy. Every observed image/peak pair in these comparisons has known features.
Weak-extraction mass is explicitly incomparable.

| Contrast | Comparable match/wrong pairs | Point correct / wrong preference | CLS correct / wrong | Peak correct / wrong | Native mass correct / wrong / incomparable |
| --- | ---: | ---: | ---: | ---: | ---: |
| Native to corrected strong | 31 | 26 / 5 | 14 / 17 | 23 / 8 | 25 / 6 / 0 |
| Native to narrow weak | 34 | 27 / 7 | 17 / 17 | 25 / 9 | 25 / 6 / 3 |
| Corrected strong to narrow weak | 2 | 0 / 2 | 2 / 0 | 2 / 0 | 0 / 0 / 2 |

There are no ties in these informative primary pairs. Complete point/CLS/peak
observed-pair denominators, including agreements and unscored references, are
909, 910 and 908 respectively; their different-coordinate denominators are 35,
39 and two. The remaining 51, 50 and 52 rows involve a missing choice. The main
31/34/two denominators must not be substituted for all 960 frames or all 882
eligible frames.

For corrected strong, this recovers the already inspected six useful revisions
and 25 emitted harmful revisions: point favors five of six useful changes and
the correct native point in 21/25 harmful pairs. Two further correct-to-missing
losses remain unpaired. The complete census establishes that those 31 were all
eligible match/wrong point pairs in this contrast; it does not manufacture a
new validation set out of them.

Native to narrow weak adds only three distinct informative frame cases beyond
that earlier set. At **e05/206**, the weak choice corrects a native mistake and
point favors the correction; CLS also favors it and peak does not. At
**e05/8–9**, weak points replace correct native/strong choices, and point favors
both wrong replacements. CLS and peak favor the correct original points.
Thus expanding beyond the earlier selected subset adds one favorable point
preference and two adverse ones. Those losses are not explained away by the
useful aggregate.

Per-episode primary discrimination is concentrated:

| Episode | Native to strong: point / CLS / peak correct preferences, denominator | Native to narrow: point / CLS / peak, denominator | Strong to narrow |
| --- | --- | --- | --- |
| e01 | No two-point match/wrong pairs | None | None |
| e02 | None | None | None |
| e03 | 7 / 2 / 9, out of 11 | 7 / 2 / 9, out of 11 | None |
| e04 | None | None | None |
| e05 | 4 / 3 / 0, out of 5 | 5 / 6 / 2, out of 8 | Point 0/2; CLS and peak 2/2 |
| e06 | 15 / 9 / 14, out of 15 | 15 / 9 / 14, out of 15 | None |

Point does not beat every comparator in every episode. Native mass protects
all eleven e03 informative native points; point wrongly favors four revisions
there. For native to narrow, point corrects seven preferences where peak chooses
the wrong side, while peak corrects five where point chooses the wrong side.
Point corrects five comparable native-mass preferences, but mass corrects four
point mistakes; three weak-extraction pairs are excluded from that mass pairing.
These are complementary and adverse signs, not a fitted combination.

## Missing, weak and hidden cases prevent a broader claim

All ten **e01/194–203** recoveries are missing-to-correct in native/strong to
narrow weak. There is no image feature for the missing alternative. This test
therefore cannot claim to validate or reject their recovery choices through a
relative pair score. The old adverse main-pool ordering remains point 3/10,
CLS 6/10 and peak 5/10; it is not erased by this comparison.

The six old **e05/14–19** below-.01 broad recoveries remain preserved in the
stress arm. Native and corrected strong are missing on all six. Narrow weak
instead emits five wrong points and leaves one missing. Across all 21 old broad
gains from native missing, narrow weak has eleven correct, nine wrong and one
missing. The original broad arm has all 21 correct on that subset but has its
other documented losses and hidden emissions. None of those one-sided rows can
supply a pair preference against missing.

All **19 native certain-hidden emissions** are exactly shared with corrected
strong and narrow weak. Native to narrow adds eight more certain-hidden emissions
from missing, yielding 27, while seven hidden frames stay missing. Strong to
narrow has the same nineteen shared false emissions and eight new ones. Relative
point ordering challenges none of those nineteen agreements and cannot score
an image comparison against the eight missing alternatives. All 34 hidden frames
remain in the tables. An emitted point being better than another invalid point
would still not establish that it should be emitted.

The eight uncertain-hidden frames have seven shared emissions and one
native-observed/strong-or-narrow-missing case. They remain uncertain, not eight
certain errors or verified successes. All 14 indeterminate and 22
visible-unlocalizable frames retain their complete state/score accounting,
including different-point choices and one-sided missing cases, without invented
localization or identity outcomes. Per-episode/category/state/outcome cross-tables,
extraction/padding strata and all exception row IDs are in the saved output.

## Historical controls and unchanged scores

The four other declared native contrasts retain every agreement and missing
row. Their observed match/wrong pair counts and correct-side preferences are:

| Target arm | Informative pairs | Point | CLS | Peak | Native mass correct / complete |
| --- | ---: | ---: | ---: | ---: | ---: |
| First strong | 65 | 58 | 33 | 54 | 65 / 65 |
| First broad weak | 78 | 70 | 42 | 67 | 63 / 63; 15 incomparable |
| Motion cost only | 35 | 31 | 17 | 32 | 34 / 35 |
| Speed only | 63 | 56 | 31 | 52 | 63 / 63 |

Most are preservation of native-correct points against harmful revisions. First
strong, broad weak and speed-only have no wrong-to-correct two-point revision;
motion-only has one. Broad weak's 21 missing-to-correct recoveries stay separate.
Better preservation than CLS is useful, but does not establish extra information
beyond native mass where mass already protects every comparable point. These
controls reuse overlapping frames and choices; they are not independent repeats.

All prior arm totals reproduce exactly (correct / wrong / missing on 882 eligible
frames; then certain-hidden emissions):

| Arm | Eligible outcomes | Certain-hidden emissions |
| --- | --- | ---: |
| Native | 842 / 19 / 21 | 19 |
| First strong | 764 / 84 / 34 | 19 |
| First broad weak | 780 / 97 / 5 | 31 |
| Motion only | 796 / 51 / 35 | 19 |
| Speed only | 770 / 82 / 30 | 19 |
| Corrected strong | 821 / 36 / 25 | 19 |
| Narrow weak | 831 / 47 / 4 | 27 |

The 60 historical appearance cases are copied unchanged into a separate appendix:
ten bank references excluded from query metrics, ten accepted checks, six
unresolved and 34 exposed. Point's accepted class preference remains 7/10 versus
CLS 8/10, with DET11008 reversal, DET11059 failure, DET11431 improvement and the
SAC1419–1421 head preferences intact. No DET result chose a method or parameter.
The earlier fitted-logistic veto and nearest-bank failures remain distinct.

## Verification, artifacts and limits

Eleven focused tests passed on the frozen implementation. Four exact captured
producer records cover a native emission, broad weak emission, narrow weak
emission and strong missing choice. Synthetic cases cover strict ties, source/
clock/candidate tampering, same crop with distinct point queries, same coordinates
with different identities, all outcome/state partitions, unknown references,
incomparable mass and corrupted bindings. These captured-record transport checks
ran before the full-study freeze; no complete comparison or preference aggregate
was calculated in those preparation tests. Earlier exposed outcomes remain
disclosed in the protocol.

A separate standard-library recount passed **136,510 checks** in 1.463 seconds.
It checked all actual choices/cache joins, independently derived coordinate
distances and outcomes from accepted reference flags, compared saved margins,
recounted exact preference signs and every published summary partition, and
verified named tag membership and arm censuses. It imports no new analysis
helper. It does not independently rerun neural inference, token/cosine arithmetic
or semantic labeling. The main analysis explicitly reuses the established
annotation parser/category kernel. No full suite was repeated for these additive
modules, and no old test result is claimed to cover new code.

- [Execution freeze and authorization](../data/outputs/ball_tracking/candidate_change_comparison_v0_1/execution_freeze.json)
- [Complete result and all summary strata](../data/outputs/ball_tracking/candidate_change_comparison_v0_1/analysis_v0_1/completed.json)
- [Full comparison rows](../data/outputs/ball_tracking/candidate_change_comparison_v0_1/analysis_v0_1/comparisons.jsonl)
- [Original-choice table](../data/outputs/ball_tracking/candidate_change_comparison_v0_1/analysis_v0_1/choices.jsonl)
- [Separate recount](../data/outputs/ball_tracking/candidate_change_comparison_v0_1/analysis_v0_1/independent_recount.json)
- [Compact result ledger](../configs/ball_tracking/reviews/candidate_change_comparison_result_v0_1.json)

## Decision in the accumulated evidence

Keep the immutable point/CLS cache and its limited complementary signal. The
complete population supports the original useful point increment while showing
that its apparent strength does not extend to a visibility or missing-state
solution. The primary additional informative cases are mixed, not a broad new
set of successful corrections. Do not adopt a point-gated change rule, combine
scores by an unannounced sweep, or train a head to rescue these results.

This interpretation extends the [protocol's full-history/research reconciliation](ball_tracking_candidate_change_comparison_protocol.md#historical-and-research-reconciliation-before-this-specification),
using its actual reading/reuse limits. No fresh all-transcript/all-paper or current
external-release review is claimed. The current results were reconciled with the
old motion/clutter mechanisms, gap gains and head-anchor failure, fitted-veto
preservation losses, response/objective diagnosis and point visibility/e01/
historical failures before this decision. This is the same authorized diagnostic
direction, not a new experiment launched after seeing its outcome.

The next method decision must explicitly address missing/visibility evidence and
protection of weak and native points; relative ordering between emitted points
alone is insufficient. This result supplies exact counterexamples for that
decision rather than authorizing an experiment queue. It does not reject all
image information, learned recognition, joint/temporal maps or materially changed
tracking. Basketball MonoTrack, specialist RF-DETR adaptation, learned basketball
context and materially changed temporal/reseeding methods remain open, with the
same primary-evidence review requirement before choosing one. No new training
decision or next experimental protocol is frozen by this report.

NBA remains the goal and cosine nine remains research control, not an adopted
model. HOU stays exposed development without fitting; SAC exposure and DET's
exclusion from method/parameter selection stand. All numerical gates, accepted
labels, nine inconclusive source recoveries, protected closure and pending human
trajectory reviews remain unchanged. No new trajectory needs acceptance here.
NBA player geometry, roster identity and calibration validation remain future
work with explicit human gates. Original worktree/history and all failed results
remain preserved. No staging, commit, push, PR or merge occurred.
