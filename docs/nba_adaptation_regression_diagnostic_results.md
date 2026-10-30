# NBA continuation regression diagnostic: three distinct failure mechanisms

Ryan explicitly authorized: “Ok move forward chat. Run the 37-frame diagnostic.”
The [bound scope](../configs/ball_tracking/selections/nba_adaptation_regression_diagnostic_v0_1.json)
compares saved outputs from the retained expanded checkpoint `09da1214e94f`
and the unsuccessful continuation `da44ce06cdf7`. One **2.375-second** run
completed all 37 frames and 74 old/new means. Independent audit passed after
one audit-helper correction. The six lost matches have three distinct mechanisms:
one competing component wins, one weighted center barely crosses the fixed
distance boundary, and four NFHS outputs lose above-threshold support when
their original contributors are averaged. No model or prediction was changed.

## What changed in the saved outputs

At DET frame **11107**, the ball is still represented by a candidate only
5.682 pixels from the label, but it ranks second. The ball component's total
response decreases from 11.953 to 11.161, while the off-ball hand component
increases from 9.237 to 13.747 and wins the unchanged selection rule. At the
same fixed hand location, peak response rises from 0.516856 to 0.647093; the
ball-region peak falls only from 0.560917 to 0.539540. This is a stronger
competitor overtaking an existing correct candidate, not disappearance of the
ball response. The selected output is 305.575 pixels from the reference.

At DET frame **11501**, the selected ball component remains supported and its
peak lies 4.809 pixels from the reference. Its weighted center moves from
9.272 to 10.014 pixels away, just beyond the inclusive ten-pixel boundary.
There is no alternate matching component. This is a marginal center-placement
failure, distinct from frame 11107's large distractor switch.

The four newly missing NFHS frames retain an above-0.3 response near the ball
in at least one original contributor, but their averaged maps fall below the
unchanged threshold:

| New missing frame | Old mean ball-region peak | New mean peak | Strongest new contributor |
| --- | ---: | ---: | ---: |
| P001/206 | 0.435629 | 0.279458 | 0.509464 |
| P001/207 | 0.315976 | 0.187125 | 0.486735 |
| P001/209 | 0.382789 | 0.216723 | 0.441645 |
| P003/304 | 0.346241 | 0.264340 | 0.555945 |

The averaging algorithm did not change. The individual responses changed,
leaving weaker support after the same averaging step. These numbers describe
model responses, not calibrated probabilities.

All four recovered matches cross the same mean-response threshold in the other
direction:

| Recovered frame | Old mean ball-region peak | New mean peak |
| --- | ---: | ---: |
| DET/11013 | 0.211950 | 0.324713 |
| P001/221 | 0.206515 | 0.307730 |
| P001/223 | 0.188371 | 0.327344 |
| P002/49 | 0.247495 | 0.307082 |

DET/11013 and P001/221 already had individual above-threshold support that did
not survive the old mean. P001/223 and P002/49 did not have that old individual
support: their strongest old contributor responses were 0.294096 and 0.247495.
The original window edges are retained: P001/223 has two contributors
and P002/49 has one, rather than an invented three-frame context.

Across the complete 37-frame selection, transitions are 16 matched→matched,
four missing→matched, two matched→wrong, four matched→missing, seven
missing→missing, two hidden-alarm→hidden-alarm and two unscored→unscored.
These are selected-event context counts, not a replacement accuracy benchmark.

The [ball-response comparison](../data/outputs/ball_tracking/nba/adaptation_regression_diagnostic_v0_1/delivery/ball_response_changes.png)
shows the ten anchor changes, and the [three regression heatmaps](../data/outputs/ball_tracking/nba/adaptation_regression_diagnostic_v0_1/delivery/three_regression_heatmaps.png)
illustrate the distinct loss mechanisms. The figures were checked in a separate
[AI inspection record](../data/outputs/ball_tracking/nba/adaptation_regression_diagnostic_v0_1/delivery/figure_inspection.json);
the original render receipt retains its pending-inspection snapshot.

## Exact comparison scope

Six lost matches and four recovered matches supply ten anchors. Take exactly
±2 native source frames around each, clip to the original review window and
deduplicate:

| Existing development context | Anchor source frames | Unique frames |
| --- | --- | ---: |
| DET | 11107, 11501, 11013 | 15 |
| P001 challenge | 206, 207, 209, 221, 223 | 14 |
| P002 challenge | 49 | 3 |
| P003 representative | 304 | 5 |
| Total | Six losses and four recoveries | 37 |

The 74 old/new means use their original complete cached contributor contexts.
The diagnostic compares true-ball response, averaging across overlapping
triplets, component center/mass and competing distractors at the unchanged
strict `>0.3` response threshold and inclusive ten-source-pixel match boundary.
It preserved source labels, uncertainty, predictions and scores. There were no
model calls, checkpoint loads, source-PNG/video decodes, training runs, threshold
changes or holdout access.

Before numerical cache reads, the scope added paired response measurements at
the existing old/new selected centers, using the same 74 means. Those fixed
locations are diagnostic probes, not new ball labels. The initial scope copy
and the addendum history are preserved.

## Execution and validation

The sole producer attempt passed all 74 original mean, candidate, selection and
score parity checks. It read 94 existing triplet caches containing 149,913,392
compressed bytes. Three original NFHS mean bundles added 39,639,143 compressed
bytes: all 75 stored planes were loaded, while only the 22 selected old NFHS
means were measured. This distinction preserves the actual read scope.

The rolling cache held at most three triplet arrays (5,308,416 bytes). Twenty
anchor planes retained for figures occupied 11,796,480 bytes; one NFHS bundle
at a time occupied 14,745,600 bytes. These array inventories are not total
process-memory measurements.

Eight focused tests passed on their first command in 3.486 seconds. Independent
audit fully recomputed all 74 means, contributor metrics, components, selections
and scores, and verified all source joins, 94 cache bodies, 22 selected old NFHS
planes and 20 exported anchor planes. It passed **20,962 checks in 1.630051
seconds**, using SciPy component labeling independently of the producer's
OpenCV labeling.

The first audit-helper attempt stopped after 1,128 checks because its independent
component record omitted `in_source_bounds`. The correction and failed receipt
are preserved; the producer and diagnostic outputs were not rerun or changed.

## Interpretation boundaries

These ten selected events can describe how saved outputs changed; they cannot
establish causal NBA overfitting or general forgetting. DET remains development
data excluded from fitting, and SAC's continuation score remains training-fit
evidence. No new fit or training-data change is authorized by this diagnostic.

Old NFHS cache provenance binds the original source/window/frame indices and
model identity; those historical caches did not save captured PNG or PTS hashes.
The new manifest supplies source-frame/PTS mapping. The old producer's recorded
0.5 threshold is retained as history; parity here uses the previously published
strict 0.3 calibration. Neither limitation is silently rewritten.

The findings do not support a universal lower threshold, strongest-pixel rule
or causal claim about forgetting. Such changes could alter the two still-active
hidden alarms and other unexamined distractors. The retained baseline and all
full-comparison scores remain unchanged.

## One proposed next experiment

Test whether preserving candidates from individual contributors improves
candidate availability without an excessive increase in distractors. Keep every
original mean-map candidate and add provenance-tagged, in-image components
already supported at strict `>0.3` in each original contributor. Use the same
two checkpoints, labels, original contributor contexts and inclusive ten-pixel
reference radius. Change neither the threshold nor any temporal rule.

On the existing **790 labeled frames** (SAC 300, DET 340 and NFHS 150), compare
whether either pool contains any candidate within ten pixels of an eligible
reference. Report extra candidates per frame and hidden-reference frames that
become newly nonempty. Keep SAC training-fit, DET development and NFHS development
results separate; report the 120 easy NBA control frames separately as subsets
of the NBA totals, not additional frames. Holdouts remain excluded.

This would measure candidate availability, not a deployable prediction or a
new accuracy score. In particular, DET/11107 already has a correct mean-map
candidate, so preserving more candidates does not by itself solve its selection
failure. Above-threshold local support in the four NFHS losses also does not
guarantee that a contributor component's weighted center will match. The proposed
test would resolve those questions before designing a selection rule.

This single cached-output experiment is **proposed, not executed or authorized
by the 37-frame diagnostic request**. It needs no new fit or model inference;
the current selected outputs and failed comparison remain unchanged.

The [failed continuation](nba_wasb_adaptation_results.md) still fails four of nine
conditions, and checkpoint `09da1214e94f` remains the baseline. Ryan's reported
review of the three inline embeds covering both NBA videos and all six NFHS
windows is complete. That review did not promote the model. The original pending
publication receipts, the negative motion result and its three pending human
reviews remain unchanged.

## Evidence

- [Bound diagnostic scope](../configs/ball_tracking/selections/nba_adaptation_regression_diagnostic_v0_1.json).
- [Compact result and evidence bindings](../configs/ball_tracking/reviews/nba_adaptation_regression_diagnostic_result_v0_1.json).
- [Completed diagnostic and exact output bindings](../data/outputs/ball_tracking/nba/adaptation_regression_diagnostic_v0_1/completion.json).
- [Full report](../data/outputs/ball_tracking/nba/adaptation_regression_diagnostic_v0_1/attempts/2697d0dab9fa4afeb6e6f2cf41b67b80/report.json) and [anchor summary](../data/outputs/ball_tracking/nba/adaptation_regression_diagnostic_v0_1/attempts/2697d0dab9fa4afeb6e6f2cf41b67b80/summary.json).
- [Focused-test log](../data/outputs/ball_tracking/nba/adaptation_regression_diagnostic_v0_1/preparation/tests_01.log) and [sole producer run log](../data/outputs/ball_tracking/nba/adaptation_regression_diagnostic_v0_1/preparation/run_01.log).
- [Passed independent audit](../data/outputs/ball_tracking/nba/adaptation_regression_diagnostic_v0_1/independent_audit/audit_02.json) and [preserved first audit attempt](../data/outputs/ball_tracking/nba/adaptation_regression_diagnostic_v0_1/independent_audit/audit_01.json).
- [Continuation comparison](nba_wasb_adaptation_results.md).
- [Completed continuation video review](../configs/ball_tracking/reviews/nba_wasb_adaptation_visual_review_v0_1.json).

Generated diagnostic outputs belong under ignored
`data/outputs/ball_tracking/nba/adaptation_regression_diagnostic_v0_1/`.
