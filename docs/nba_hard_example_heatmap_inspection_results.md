# NBA saved-heatmap inspection results

The approved inspection found weak ball-region responses on missing frames and
nearby component-center errors on most wrong locations. This supports preparing
a bounded NBA adaptation/data experiment emphasizing held and overlapped balls.
It does not establish one cause for every failure or approve a new fit.

Ryan approved the inspection with “Let’s do it. Move forward chat”. The
[recorded scope](../configs/ball_tracking/selections/nba_hard_example_heatmap_inspection_v0_1.json)
fixed the 640 rows and descriptive comparisons before inspecting the heatmaps. The
[compact result](../configs/ball_tracking/reviews/nba_hard_example_heatmap_inspection_result_v0_1.json)
binds the completed evidence. The [run receipt](../data/outputs/ball_tracking/nba/hard_example_heatmap_inspection_v0_1/completion.json)
records one completed 19.937-second inspection: 652 existing cache files,
1,037,888,584 compressed bytes, and 640 original float32 means reproduced exactly.
Every original candidate inventory and selection also agrees.

The inspection made no model calls, checkpoint loads, training runs or source
image/video decodes. It reconstructed the existing aggregation without changing
labels, predictions, thresholds or scores. Peak rolling cache storage was three
triplet arrays, 5,308,416 bytes; this is not total process RAM. The 640 rows keep
the 82 failures separate from 305 matched difficult frames, 120 pilot controls,
86 hidden references and 47 other unsupported references.

## What explains the recorded failures

“Local” means heatmap pixels whose mapped source locations lie within the fixed
ten-pixel disk around an accepted center. Response values are sigmoid outputs,
not calibrated probabilities. Null-center references receive no local region or
localization judgment. The [response comparison plot](../data/outputs/ball_tracking/nba/hard_example_heatmap_inspection_v0_1/visuals/response_comparison.png)
shows the eligible missing/wrong measurements alongside matched difficult frames
and pilot controls. Hidden-frame measurements are described separately below.
The [source-frame examples](../data/outputs/ball_tracking/nba/hard_example_heatmap_inspection_v0_1/visuals/heatmap_examples_v2.png)
show SAC 1294 from the 58 misses without above-threshold contributor support,
and SAC 1269 from the 11 with support lost during averaging. These illustrate
two measured patterns without claiming that two images explain every failure.

| Recorded group | Finding | Implication |
| --- | --- | --- |
| 69 missing outputs | Local response median 0.117843, maximum 0.293772; no local support exceeds 0.3. The global strongest pixel is within ten pixels of the label on only 21/69 frames. | The missing ball signal is usually weak and often not the strongest response anywhere in the image. |
| Contributors to those 69 misses | 11 have local support above 0.3 in at least one original contributor, lost in the mean; 58 have none. | Averaging removes some above-cutoff local support, but does not explain most misses by itself. |
| 13 wrong locations | 11 selected components have above-threshold pixels inside the label disk, although their weighted centers are outside; only three component peaks are inside. | Most are marginal center/shape errors rather than a complete absence of nearby response. |
| 305 matched difficult frames | Six component peaks are outside ten pixels even though the existing weighted centers match. | Replacing centers with peaks would gain three wrong frames and lose six current matches; it is not a justified promotion. |

The 13 hidden-ball alarms have a global-response median of 0.459021. The 73
hidden quiet frames have a median of 0.109686 and values that overlap the missing
frames. The matched difficult-frame local median is 0.845677; the separate pilot
control median is 0.892521. These descriptive comparisons do not provide a safe
new threshold. No threshold sweep or alternative prediction policy was run.

The original saved score remains **305/387 difficult-center matches, 13 wrong
locations and 69 missing**, with 13/86 hidden alarms and 47 other unscored frames.
Separate longer-context controls remain 120/120. All 133 null geometries, the
original short-pilot score and the eight longer-context pilot edges are preserved.
No component or peak location shown here has replaced a saved prediction.

## Validation and limits

Seven new focused tests passed. The initial test command passed 15 checks because
an imported class also exposed eight existing tests; the import was corrected
and the final command passed the seven intended new checks. Both logs are
retained. There were no failed tests or scientific runs in this increment, and
the full suite was not repeated.

The independent [actual-output audit](../data/outputs/ball_tracking/nba/hard_example_heatmap_inspection_v0_1/independent_audit_01/audit.json)
passed on its first attempt in 3.297 seconds. It checked all 640 rows and summaries
structurally and all 652 cache metadata records. Independent numeric reconstruction
covered **126 rows: all 82 failures plus 44 context rows**, using 237 caches
(377,272,217 compressed bytes). The other 514 rows were not independently
recomputed numerically; the producing diagnostic verified their original mean
hashes and candidate/selection agreement.

The [preservation receipt](../data/outputs/ball_tracking/nba/hard_example_heatmap_inspection_v0_1/preservation.json)
confirms nine authority/source bindings and five tracked prior code/result files
are unchanged. Separate visual delivery used 12 cache reads (19,097,646 bytes)
and four PNG decode events across two unique source images. Both final figures
were visually checked. The [visual receipt](../data/outputs/ball_tracking/nba/hard_example_heatmap_inspection_v0_1/visuals/visual_check.json)
retains an initial clipped-colorbar layout and the corrected second version;
these presentation attempts did not change the diagnostic or predictions.

These labels were chosen after failures were observed, adjacent frames are
correlated, and AI authorship remains explicit despite human acceptance. The
measurements diagnose this development sample, not representative NBA accuracy.
Weak response, contributor disagreement and marginal geometry support several
mechanisms; they do not prove a single causal explanation.

The recommended next step is an exact, bounded NBA adaptation/data proposal
focused on held and partially overlapped balls, with appropriate hidden-ball
context. The design should use SAC training examples alongside eligible NFHS
training examples to retain earlier learned behavior; DET remains excluded from
fitting. An exact next scope and explicit approval are required before any fit.
No new experiment, fit, threshold search or model-output promotion is approved
by this result. TOR, protected holdouts, the NFHS finish line and the negative
motion result are unchanged; its three human reviews remain pending.
