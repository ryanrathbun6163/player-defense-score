# Point-feature comparison results, 2026-10-26

**Completed, independently audited, reference-assisted diagnosis. No tracker or
training recipe is adopted.** The point readout improves HOU candidate ordering
over the whole-crop CLS readout in every episode. A matching candidate ranks
strictly first on 527/882 eligible frames versus 259/882 for CLS. However, peak
response remains better on every episode, and neither image margin adequately
separates visible balls from certain-hidden frames. Preserve the spatial signal
and its failures; this result does not justify either a standalone image veto or
automatic new training.

## What was held fixed

The [approved proposal](ball_tracking_point_feature_feasibility_proposal.md) and
[frozen recipe](../configs/ball_tracking/proposals/point_feature_comparison_v0_1.json)
compare two readouts from the same CPU forward pass of the pinned DINOv2 ViT-S/14:
final CLS and bilinear interpolation of four final spatial tokens at the actual
candidate coordinate. The raw tokens are interpolated in float64 before one L2
normalization. Both readouts use the same 64-source-pixel crop, preprocessing,
ten accepted SAC references (four ball, six other object), and maximum ball
cosine minus maximum other-object cosine. Each query uses references from its
own representation. There is no fitted head or changed crop scale.

The saved cosine-nine WASB model remains the declared research control. All
coordinates are existing observed candidates. HOU remains repeatedly inspected
checkpoint-validation development, excluded from fitting; SAC remains exposed;
the original DET appearance cases remain separate diagnostics and choose no
method or parameters. Protected evaluation stays closed. No new labels, GPU
inference, fitting, selector run or trajectory was produced.

## Execution and verification

The code, recipe, analysis and independent audit adapters were frozen before
inference. The single CPU attempt completed in **754.482 seconds**: 10,883
attempted and returned forwards, one model load, and 1,009 source PNG decodes.
There were no inference failures, retries or resumed calls. The observed peak
process working set was 1,050,554,368 bytes; monitoring was sampled, not a full
machine resource trace. Batch size was one, float32, four Torch threads, eager
attention, evaluation mode and inference mode. No GPU fallback occurred.

The 11,798 query rows comprise 10,778 HOU main candidates, all 960 prior broad
stress choices (949 emitted, eleven explicitly missing), and the original sixty
historical cases. Deduplicating identical source/crop inputs did not merge
different candidate-point interpolation queries. All emitted descriptors are
finite and nonzero; no bank member is missing. The ten bank rows are excluded
from query outcomes. All sixty historical CLS outputs are **byte-identical** to
the old float32 cache, stronger than the frozen tolerance requirement. They
were checked before HOU inference. All descriptors were sealed before scoring.

Fifteen focused producer/consumer tests passed. The independent audit preparation
also passed ten scalar cases, five analysis cases, actual synthetic producer and
consumer transport, and a deliberately corrupted-count check. The completed
witness audit independently reconstructed all 11,787 emitted point queries and
non-bank cosine scores. The analysis audit passed 521,860 checks over provenance,
geometry, roles, shared cutoffs, episode and pooled ranks, padding strata, paired
changes and historical outcomes. Maximum independent cosine difference was
2.22e-16. The audit explicitly reuses the frozen annotation/category kernel and
uses verified published scores for exact-tie recounts; it does not claim a second
independent neural-network forward or independent semantic relabeling.

Primary artifacts, including exact hashes and runtime accounting:

- [Prospective freeze](../data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/point_comparison_v0_1/prospective_freeze.json)
- [Sealed inference](../data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/point_comparison_v0_1/completed.json)
- [Complete scored diagnosis](../data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/point_comparison_v0_1/analysis_v0_1/completed.json)
- [Independent witness audit](../data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/point_comparison_v0_1/validation/independent_witness_audit.json)
- [Independent analysis audit](../data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/point_comparison_v0_1/validation/independent_analysis_audit.json)
- [Compact result ledger](../configs/ball_tracking/reviews/point_feature_comparison_result_v0_1.json)

## Candidate ordering: recurring improvement, substantial remaining errors

The main population contains all 960 HOU frames: 882 eligible, 34 certain-hidden,
14 indeterminate, eight uncertain-hidden and 22 visible-unlocalizable. A matching
candidate means within the unchanged inclusive ten-source-pixel radius. It is
not a new semantic ball label. Strictly first means the best matching candidate
beats every localization miss. These are ranks, **not tracking accuracy**.

| Episode | Eligible | CLS strictly first | Point strictly first | Peak strictly first | Point gains / losses versus CLS |
|---|---:|---:|---:|---:|---:|
| e01 | 120 | 54 | 90 | 115 | 45 / 9 |
| e02 | 120 | 34 | 77 | 120 | 49 / 6 |
| e03 | 98 | 13 | 52 | 88 | 40 / 1 |
| e04 | 120 | 49 | 84 | 120 | 46 / 11 |
| e05 | 212 | 48 | 88 | 196 | 63 / 23 |
| e06 | 212 | 61 | 136 | 198 | 90 / 15 |
| Pooled, descriptive | 882 | 259 | 527 | 837 | 333 / 65 |

All CLS/point competitor features are available. Six frames have no matching
candidate, leaving 876 comparable frames. Point has fewer strictly higher misses
on 513, more on 123 and the same number on 240. Against peak, the complete paired
comparison yields six strict-first gains and 306 losses; seventeen frames have
incomplete peak competitors and six lack a match, so those are excluded from the
paired comparison. The pooled 527-versus-837 totals and that paired denominator
must not be conflated.

On the same native-only population, point ranks a match strictly first on 818
frames, CLS on 755, and native component mass on 842. Twenty-five frames have no
native matching candidate. Point gains nine and loses 33 strict-first cases
against mass over the remaining 857 frames. Broad-extraction component masses
are never treated as interchangeable with native masses.

## Visibility bounds: the main failure remains

These are diagnostic bounds derived using the existing HOU references, not
deployment thresholds. Each feature uses one HOU-wide cutoff for every episode.

| Diagnostic measurement | CLS | Point | Peak | Native mass |
|---|---:|---:|---:|---:|
| Native-correct points retained when rejecting all observed hidden candidates | 48/842 | 47/842 | 701/842 | 735/842 |
| Hidden frames with a survivor when retaining all 842 native-correct points | 34/34 | 34/34 | 19/34 | 19/34 |
| Hidden candidates surviving that native-preserving bound | 403/410 | 337/410 | 23/410, two unknown | 21/22 native candidates |

The strict hidden-rejection cutoffs are CLS >0.1259579502551295 and point
>0.18937830466606315. They leave a matching main candidate on only 51 and fifty
eligible frames respectively. Both reject all 21 useful broad weak gains from
native missing, including the ten e01 recoveries and six below-.01 e05 gains.
Peak has two unknown hidden candidate features; rejecting its known hidden
scores does not establish complete hidden rejection.

The inclusive native-preserving cutoffs are CLS >=-0.325797180761281 and point
>=-0.19871419016656533. Both retain all 21 weak gains, including those ten plus
six subsets, and all 780 matched stress emissions. Point rejects six of the 97
wrong stress emissions; CLS rejects none. Point also rejects one unscored
visible-unlocalizable row, which is not counted as a success. Both retain all
31 certain-hidden stress emissions. The eleven missing stress rows remain
explicitly missing. Thus the improved candidate filtering is real but does not
solve the required absence behavior.

The ten e01 native-missing recovery frames expose an additional limitation:
within the narrowed main pool, strict-first counts are three for point, six for
CLS and five for peak. Thus point's episode-wide gain does not improve ordering
on this useful weak-recovery subset. The six below-.01 e05 stress gains are not
in that main pool; their retained stress scores do not establish broad-pool ranks.

Padding does not explain this failure. All 842 native-correct points have complete
source crops. The 41 padded main candidates contain no eligible matches. Within
complete-source candidates alone, strict-first counts are 530 point and 260 CLS;
the full-pool counts remain 527 and 259. These stratum ranks exclude other-stratum
competitors and are not alternative accepted results. Padding retains its own
denominators under the same global cutoffs; it is never treated as absence evidence.

## Useful changes and regressions from the earlier strong arm

The six gains and 27 losses are joined to the original corrected-strong choices,
not used to select the new inference population. Among the six useful revisions,
point prefers the correct revised candidate over the wrong native candidate on
five; CLS does so on three; peak and mass on none. Among the 25 emitted wrong
revisions that displaced correct native points, point prefers the correct native
candidate on 21, CLS on eleven, peak on 23, and mass on 25. Two additional strong
losses are missing choices and remain separately unpaired.

This is evidence of complementary ordering information. It is not an executed
rule for accepting or rejecting path revisions. Point still prefers the wrong
revision on four of those 25 frames and ranks one useful revision below the wrong
native candidate. Those errors
cannot simply be excused by candidates lying near the ten-pixel correctness
boundary: the four native points are approximately 0.48–1.46 pixels from the
reference, and the lower-ranked useful revision is approximately 0.94 pixels away.
These are descriptive checks of the already sealed coordinates, not new labels.

## Historical cases retain their separate authority

The ten accepted checks change from 8/10 class preferences for CLS to 7/10 for
point. Point repairs the accepted DET11431 ball/other ordering, but reverses the
previously correct DET11008 ordering. DET11107 and DET11444 remain correctly
ordered; the accepted DET11059 ball remains other-preferred. The three exposed
SAC1419–1421 head points remain ball-preferred. These exposed AI assessments are
not promoted to accepted semantic labels. The six unresolved and 34 exposed
cases remain separate from the ten accepted checks and ten excluded bank cases.

The [original nearest-bank screen](nba_appearance_feature_screen_results.md)
failed on the DET11059 and DET11431 accepted balls. The later
[fitted-logistic veto](nba_ball_distractor_training_results.md) had different
DET11008/11444 inversions and lost 207/581 prior correct positions. This test
does not rerun that fitted head or attribute its failures to CLS pooling.
No DET result here chooses a feature, reference bank, model or threshold.

## Decision in the accumulated evidence

The completed [weak-response study](ball_tracking_weak_response_results.md)
showed useful improvements from correcting the motion/speed settings and
preserved ten localized e01 weak recoveries, while its proposed tracks failed
the final criteria. The [response diagnosis](ball_tracking_candidate_response_feasibility.md)
found five scalar shape descriptors worse than peak in every episode and exposed
the path objective's reward for false emissions. Those results did not exhaust
joint or temporal evidence. This comparison now establishes that spatial image
readout adds ordering information, while its fixed ten-reference cosine margin
still has severe visible/hidden overlap and remains weaker than peak overall.

Keep the point cache and successful increments. Do not adopt a standalone image
selector, absence veto or fitted-head rescue, and do not start more training on
the strength of this result. The research question narrows to whether this
complementary information can help assess proposed candidate changes while
preserving strong detections and explicit missing states. Any subsequent test
requires a concrete prospectively specified scope and decision; none was run
or authorized by this result. NBA footage remains the target.

This decision reuses the [full-history authority map](context/source_map.md),
[validation history](context/validation_history.md), and the documented
[research reconciliation](../data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/history/research_reconciliation/review.txt).
Coverage remains Sessions 1–16 through the completed available-timeline review,
Session 17's complete handoff and relevant primary results, plus the stated
foundation coverage. It does not claim a fresh reread of all transcripts or
external URLs. The research cross-check occurred after the initial proposal and
before execution approval; that timing is preserved. MonoTrack basketball,
specialist RF-DETR adaptation, learned basketball context and materially changed
temporal tracking remain open alternatives, not methods disproved by this test.

Before every new experiment, pivot or other substantive direction, reconcile
the accumulated history, relevant research and primary evidence, name adverse
and favorable results, and disclose actual reading coverage and unresolved gaps.
No blanket rejection of image methods follows from this failed standalone rule.

The unchanged gates remain >=95% correct within ten pixels, <=1% wrong, zero
certain-hidden emissions, missing gaps <=200 ms, wrong-object runs <120 ms,
recovery <=120 ms with two subsequent correct frames, and complete human visual
review. No new trajectory was produced, so this study cannot certify those
gates. Nine original source-uncertain recoveries remain inconclusive. Original
reviews, failed attempts, frozen recipes, checkpoint recovery history and human
review requirements remain intact. NBA player identity, calibration and player
coordinate validation remain future work.
