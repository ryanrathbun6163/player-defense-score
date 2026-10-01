# Saved crop candidate ranking: results and mechanism diagnosis

The recent-history experiment is complete at commit
`3c4894656fd5da11708a54089444d41f0a6f7773`. Ryan's response, "looks good to me",
is recorded in
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_ranking_visual_review_record_v0_1.json`.
It is package-level feedback; it does not invent itemized final-frame attestations.

The wide rule improves many saved outcomes, but it is not a selected method.
The next useful question is why it improves them: the original tight/wide
comparison changes both the allowed displacement and the motion penalty.

## Evidence and scope

All six finalized development windows remain fixed: P001 representative 50-74
and challenge 200-224; P002 representative 250-274 and challenge 25-49; P003
representative 300-324 and challenge 150-174. There are 145 eligible frames
and five hidden frames. The experiment produced 270 derived outputs, 1,350
per-window reports and 225 aggregate cells in each separate pool, with all
540 saved crop raw/top-one control cells matching prior outcomes.

The saved execution record is
`data/outputs/ball_tracking/crop_ranking_execution/3c4894656fd5/execution_record.json`
(SHA-256 `95c0b8f92c8af1fde8a842bf7e4bd6993b87880cfbc2a690ae758bf267a14b5d`).
The same directory's `review_guide.md` links the 12 completed clips and final
frames; `results_summary.md` contains the complete displayed outcome tables.
Their historical pending-review text is superseded by the separate receipt.

The create-only diagnosis is
`data/outputs/ball_tracking/crop_ranking_diagnosis/3c4894656fd5/diagnostic.json`
(SHA-256 `b5fc30f8dd8e5bd4b8a7c1bf98bf9e51108cdd3cc45397dd6a12fe614a84014d`).
Its adjacent `diagnose_saved.py` reads saved JSON only and binds its own bytes,
inputs and code checkpoint. It verifies 540 history/window/radius cells,
summarizes 180 aggregate cells, and records 600 displayed frame outcomes plus
88 detailed endpoint traces. It invokes no inference, selector, scorer or
renderer. Label distances are posthoc explanations, never selection inputs.

All 270 derived output hashes and 71 protected non-context files matched.
The three intentional context edits and review receipt matched the previous
closeout before these notes were added. All nine original embargo paths were
absent. No holdout media, labels or predictions were inspected.

## What the saved counts show

At confidence 0.20 and raw-center radius 10 source pixels:

| Pool | Arm | Matched frames | False candidates | Missed eligible frames |
| --- | --- | ---: | ---: | ---: |
| Representative | Crop raw | 62 | 278 | 13 |
| Representative | Crop top one | 51 | 23 | 24 |
| Representative | Tight history | 29 | 37 | 46 |
| Representative | Wide history | 54 | 19 | 21 |
| Challenge | Crop raw | 63 | 81 | 7 |
| Challenge | Crop top one | 59 | 13 | 11 |
| Challenge | Tight history | 53 | 13 | 17 |
| Challenge | Wide history | 63 | 6 | 7 |

Raw retains multiple candidates, so its false-candidate count can exceed the
number of frames. At confidence 0.35/radius 10, wide history has 51 matches
and 17 false candidates representative, and 58 matches and two false candidates
challenge. Top one has 50/19 and 55/6 respectively.

Across the 45 threshold/radius cells, wide history has more/equal/fewer
representative matches than top one in 37/3/5 cells. It has more challenge
matches and fewer false candidates in all 45 cells. Tight history has fewer
matches in every cell of both pools. These cells reuse the same frames and
are correlated descriptive comparisons, not independent trials.

Every history miss can be partitioned without overlap:

| Pool | Confidence | Arm | No match at export floor | Threshold loss | Cap loss | Ranking loss | Total misses |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| Representative | .01 | Tight | 5 | 0 | 6 | 32 | 43 |
| Representative | .01 | Wide | 5 | 0 | 6 | 9 | 20 |
| Representative | .20 | Tight | 5 | 8 | 0 | 33 | 46 |
| Representative | .20 | Wide | 5 | 8 | 0 | 8 | 21 |
| Representative | .35 | Tight | 5 | 11 | 0 | 30 | 46 |
| Representative | .35 | Wide | 5 | 11 | 0 | 8 | 24 |
| Challenge | .01 | Tight | 0 | 0 | 2 | 15 | 17 |
| Challenge | .01 | Wide | 0 | 0 | 2 | 3 | 5 |
| Challenge | .20 | Tight | 0 | 7 | 0 | 10 | 17 |
| Challenge | .20 | Wide | 0 | 7 | 0 | 0 | 7 |
| Challenge | .35 | Tight | 0 | 12 | 0 | 8 | 20 |
| Challenge | .35 | Wide | 0 | 12 | 0 | 0 | 12 |

"No match at export floor" means no saved candidate center falls within the
fixed radius at confidence >=0.01; it is not proof of no ball detection.
Conversely, a low-confidence candidate near a label does not establish reliable
identity among dense predictions. Threshold loss removes such an available
candidate. Cap loss removes it from the top twenty. Ranking loss means the
cap retained a qualifying candidate but the history output failed to match.

No cap loss occurs at .20/.35 in any of the 120 history/window/radius cells.
The full grid has cap losses in 36 cells, confined to .01/.03/.05. At .20/.35,
all eight additional representative wide-rule misses are wrong current
choices, not null output. The saved JSON further separates wrong emissions
from withheld observations for every cell. An independent read-only check
reproduced all 540 partitions and their saved false-negative totals.

## Why P002 gains and losses happen

At representative frame 262, wide history selects original global candidate
2, about 391.67 pixels from the annotation, over candidate 0, about 5.46
pixels away. The latter is the correct top-one observation at both displays.

| Saved wide path at frame 262 | Confidence sum | Motion cost | Gap cost | Final score |
| --- | ---: | ---: | ---: | ---: |
| Selected false path 258#1,259#0,260#0,261#0,262#2 | 2.861809 | .069614 | 0 | 2.792195 |
| Best path ending within 10px: 258#4,259#4,260#4,261#2,262#0 | 2.546685 | .003950 | 0 | 2.542735 |

Here `frame#index` uses immutable global candidate indices. The correct path
is gap-free and all its movements fit both link limits. There is no missing
candidate, cap loss, or broken correct edge. Persistent false evidence wins
by about .24946 score units. Tight history also chooses a false path. Merely
separating the two motion parameters is not an established cure for this case.

Representative 258 exposes the coupled parameters. Its useful path
254#0,255#0,256#0,257#4,258#4 is allowed by both limits. Its confidence sum
is 3.176710. The tight motion cost is .556533; the wide cost is .061837,
exactly nine times smaller apart from floating-point rounding. The tight
path loses to false competition, while the wide path wins. This recovery
does not require an additional allowed edge. Its frame-257 ancestor is
10.409 pixels from the label; do not call every ancestor a 10-pixel match.

At challenge 48 and 49, wide history retains gap-free useful paths ending
at candidate 2, despite a higher-confidence false candidate at each current
frame. Current errors are 2.329 and 8.689 pixels. Both displayed settings
recover these matches. The same candidate-history machinery can therefore
recover a ball observation or reinforce a persistent wrong object.

The stored margin is a competing-hypothesis margin: the next alternative can
be a current candidate, an older endpoint, or the empty hypothesis. It is not
object-level confidence. At these P002 recoveries, close alternatives can be
duplicate crop views of the same ball. The diagnostic retains the field name
`saved_candidate_runner_up_margin` for this saved value; interpret it with
these broader endpoint semantics. No ambiguity-margin acceptance threshold
follows from this diagnosis.

## P003: movement limits and hidden-ball starts

The source diagonal is about 2,202.91 pixels; tight and wide limits are
22.03 and 66.09 pixels per elapsed frame. At representative 300-301, the
useful link moves 22.253 pixels, just outside the tight limit. Tight then
prefers a persistent false path at 301-303; wide can retain the unselected
ball alternative from frame 300 and recover. Rebuilding from raw recent
candidates permits recovery after an earlier wrong output.

At challenge final frame 174, the useful 172#0 to 174#0 link spans 99.676
pixels over two frames. Tight rejects that edge; wide permits it. Tight
selects false candidate 2 (124.089-pixel error), while wide emits candidate
0 (3.851-pixel error). Frame 173 stays null; no missing coordinate is filled.

Hidden frames 165-169 expose a different mechanism. At .20, no candidates
qualify on 165-166. The earlier hypothesis survives as null output, then
expires. Frame 167 starts a new false singleton, and frame 168 continues it.
At .35, the false singleton begins at 168. Both rules therefore emit hidden
false alarms on 167/168 at .20 and on 168 at .35. These are fresh candidate
starts, not an extrapolated ball location through occlusion. Frame 169 is
null because an earlier endpoint wins; no hidden truth center is invented.

At radius 10, frames 164 and 170 have no qualifying raw candidate at either
display confidence. Frame 164's selected center is 11.502 pixels from the
label. The next correct matched observation after occlusion is 171, not
170. These boundary misses must not be attributed to ranking alone.

## Next bounded question

Separate edge admissibility (may two candidates connect?) from motion cost
(how much does an allowed movement reduce the score?). The proposed full
2-by-2 comparison keeps both existing settings as controls and adds the two
crossed combinations. See `ball_crop_motion_factorial_proposal.md` and its
machine-readable proposal. It reuses only these saved development candidates.

This tests the source of the present motion-related behavior. It does not
establish an answer to persistent clutter, hidden-frame starts, absent usable
candidates, ball identity or cross-game generalization. No new comparison has
run, no operating point or quality gate is selected, and all holdouts remain
sealed. The production code and its last focused/full test results are
unchanged. New experiment scope and each subsequent Git step retain their
separate authorization boundaries.
