# Crop motion factorial: reviewed results and remaining failures

Ryan confirmed: "I have reviewed all of these clips. move forward" after the
12-clip review package. This completes that requested visual review. It does
not supply an itemized frame verdict, choose a method or operating point, or
establish a quantitative quality gate.

The separate review receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_motion_factorial_visual_review_record_v0_1.json`
(SHA-256 `d629f93d4c4081dd89fcbc98c997fff0f5aea7fe9d8555a16d9328f803d6fd40`).
Earlier execution records and guides retain their historical pending-review
status. No completed detector, crop, ranking or motion experiment was rerun.

## Scope and integrity

The experiment ran at `2274ab6097cd841421e2b606f723b047cd7dc62b` on the same
six development windows: 150 source frames, 145 localization-eligible labels
and five hidden frames. Four edge/cost combinations and three crop controls
at nine confidence thresholds produced 378 outputs and 1,890 per-window
reports. Each separate pool has 315 aggregate cells.

All 270 prior control traces, 1,350 report cells and 450 aggregate cells
reproduce saved evidence. The review receipt rechecks 3,012 review assets,
12 playback copies, 378 outputs, both scoring pools, six crop inputs, six
saved whole-frame detections and six finalized annotation files. All nine
original prediction embargo paths remain absent; all three holdouts stay
sealed. Selection never reads annotations.

The execution record is
`data/outputs/ball_tracking/crop_motion_execution/2274ab6097cd/execution_record.json`
(SHA-256 `1e732738669cb3f6c4389a92248cd1435b376b2fb023a2b02abacda9bb4eb40f`).
That directory also holds the immutable saved `score_audit.json`,
`results_summary.md` and `review_guide.md` with all clips and exact frames.
Later read-only closeout evidence is under
`data/outputs/ball_tracking/crop_motion_closeout/2274ab6097cd/`.
`closeout_audit.json` (SHA-256
`2eb17ff8c26237f3009396a5a54f9646fba187db7409d9e87cfe83c678361c5c`)
reconciles all 1,080 saved loss partitions and extracts 4,843 emitted winners
from all 216 graph outputs. `mechanism_diagnostic.json` (SHA-256
`496a2c6cdfa01d46e43ca7dec052bdffbe0329876cc6d9018618b3acee2b203a`)
copies 112 saved case traces and binds 38 input files. Neither diagnostic
invokes a selector, scorer, renderer or model.

## What the factorial establishes

TT, TW, WT and WW name movement allowance first, then motion-cost scale.
Tight is .01 and wide .03 image diagonals per source-frame interval. A wider
cost scale makes an allowed movement less expensive. The comparison changes
one parameter at a time, preserving the other and all remaining rules.

Each row below compares all 45 confidence/radius cells in its pool. These
reuse the same frames; they are correlated development comparisons, not
independent trials or evidence of generalization.

| Pool | Change | More / equal / fewer matched frames | More / equal / fewer false positives |
| --- | --- | --- | --- |
| Representative | TT to WT: more allowed movement | 45 / 0 / 0 | 0 / 0 / 45 |
| Representative | TW to WW: more allowed movement | 45 / 0 / 0 | 0 / 0 / 45 |
| Challenge | TT to WT: more allowed movement | 45 / 0 / 0 | 0 / 5 / 40 |
| Challenge | TW to WW: more allowed movement | 45 / 0 / 0 | 0 / 0 / 45 |
| Representative | TT to TW: gentler penalty | 39 / 5 / 1 | 1 / 4 / 40 |
| Representative | WT to WW: gentler penalty | 40 / 5 / 0 | 0 / 0 / 45 |
| Challenge | TT to TW: gentler penalty | 0 / 0 / 45 | 40 / 5 / 0 |
| Challenge | WT to WW: gentler penalty | 37 / 8 / 0 | 2 / 11 / 32 |

Allowing larger movements consistently helps within this fixed grid. The
penalty effect depends on the allowed links and pool. This identifies a
mechanism; it does not select WW or any other arm as the production method.

At the predeclared 10-pixel display radius:

| Pool | Confidence | Top-one TP / FP | TT TP / FP | TW TP / FP | WT TP / FP | WW TP / FP |
| --- | ---: | --- | --- | --- | --- | --- |
| Representative | .20 | 51 / 23 | 29 / 37 | 33 / 33 | 48 / 26 | 54 / 19 |
| Representative | .35 | 50 / 19 | 29 / 32 | 31 / 29 | 46 / 22 | 51 / 17 |
| Challenge | .20 | 59 / 13 | 53 / 13 | 50 / 15 | 62 / 7 | 63 / 6 |
| Challenge | .35 | 55 / 6 | 50 / 5 | 48 / 7 | 57 / 3 | 58 / 2 |

## Different failures require different evidence

At both display settings, P002 representative 258 is recovered by both
cost-scale .03 arms while both cost-scale .01 arms miss it. At P002
representative 262, all four arms at both displays
choose a sustained five-observation false path even though a correct
five-observation path remains available. The wrong object accumulates more
score. Requiring temporal support alone cannot distinguish these paths.

At P002 challenge 48, TW loses a match that TT, WT and WW retain at .20.
The tight movement limit splits useful fast-moving ball evidence; making
movement cheaper also strengthens a competing persistent distractor. This
explains why gentler penalties with tight allowance lose challenge matches.

At P003 final challenge frame 174, only WW among the four history arms
matches at both display settings. WT permits the useful link but charges it
more heavily. Both allowance and scoring matter in this case.

Hidden P003 frames 165-169 are a separate failure mode. At .20, frame 167
starts a false singleton and 168 continues a two-observation false path. At
.35, frame 168 is a false singleton. The correct reacquisition at frame 171
is itself a singleton in all four arms at both displays. No hidden truth
coordinate is inferred, and none of these outputs is interpolation.

Consequently, simply withholding singleton winners would discard a valid
reacquisition, retain the false two-observation continuation, and leave the
persistent P002 clutter. These statements describe existing path support;
no new emission filter or alternative prediction run is applied.

Across all nine confidences and four history arms, the saved radius-10 audit
contains 313 matched singleton emissions, 71 unmatched emissions on eligible
frames with singleton support, and 19 hidden singleton false alarms. There
are also 1,221 unmatched eligible-frame emissions and 52 hidden false alarms
with at least two nodes of support. These counts repeat the same source
frames under correlated settings; they are not independent examples. A
short path can reflect the five-frame horizon, window startup or filtering,
not necessarily a newly encountered object.

A constant penalty charged once to every nonempty path cannot change the
ordering of those paths. It can only change which beats the empty hypothesis.
Likewise, endpoint-score margins are not calibrated object confidence:
overlapping crop views may represent the same ball, and other competitors
can be older endpoints or the empty hypothesis.

## Existing player context: feasible, incomplete identity evidence

The read-only context feasibility audit joins the 4,843 saved emissions to
215 unique frame/candidate pairs and 1,353 reconciled player-box rows in the
six permitted windows. Every permitted frame has at least one player box,
but coverage is incomplete: neither P002 window has all ten boxes on any
frame, and its challenge window falls to six boxes. These are detector boxes
associated with reviewed identities, not manually certified silhouettes.

`context_feasibility.json` (SHA-256
`cb06d0804bed5ea5f0ca76685696f87dd12bfe7d0e99157ff7735132c0471a0e`)
binds 48 inputs and selected player-row digests. Source paths, dimensions,
frame rates, frame counts and selected timestamps agree. Legacy player
artifacts lack a historical source-video SHA-256 and model provenance; current
file hashes and metadata alignment do not retroactively establish those facts.

The distance below is from the candidate center to the nearest player box in
the same source image. Zero means inside or on a box. Each emitted candidate
is counted once, using its existing radius-10 outcome. This is descriptive
geometry, not a new candidate filter or an independent evaluation sample.

| Pool / saved outcome | Unique candidates | Median nearest-box distance | Maximum distance | Inside/on a box |
| --- | ---: | ---: | ---: | ---: |
| Representative / matched | 57 | 0.00 px | 10.22 px | 48 |
| Representative / unmatched | 62 | 309.10 px | 440.36 px | 16 |
| Challenge / matched | 68 | 0.00 px | 57.90 px | 52 |
| Challenge / unmatched eligible | 23 | 0.00 px | 578.13 px | 12 |
| Challenge / hidden false alarm | 5 | 0.00 px | 167.30 px | 3 |

P002 representative 262's false candidate is 278.367 pixels from the nearest
player box. In contrast, P003's hidden false candidates at 167 and 168 and
correct reacquisition at 171 are all inside a box. Context may help distinguish
some distant distractors, but proximity alone cannot establish ball identity
or possession. The audit also retains candidate box dimensions, crop-border
distances and nearest alternatives from other crops, without selecting a rule.
It inventories court/calibration metadata without reading camera arrays or
projecting ball points onto the floor.

## Next direction

The remaining question is which evidence distinguishes the ball from another
object. More observations of the same wrong object do not establish identity.
Before adding another selection rule, use this candidate geometry and crop-view
inventory with the saved unmarked images to examine appearance. Separate persistent background
distractors, player-adjacent confusion, localization error and absent usable
candidates. Label uncertain physical identity as uncertain.

Any later player-proximity or court-context experiment must account for passes,
airborne balls, camera motion and player-detection errors. A floor homography
does not turn an airborne ball center into a valid court coordinate. A screen
mask fitted to these distractors risks encoding this broadcast. Keep context
as diagnostic evidence until a bounded label-free rule and validation design
are specified; preserve the existing outputs and controls.

Any later abstention comparison must distinguish suppressing an already chosen
winner from reranking supported paths, and two observations from two consecutive
observations. Its declared purpose would be the false-alarm/missingness tradeoff,
not a claimed solution to persistent wrong-object tracking. Only five hidden
frames from one episode are currently labeled in this development pool.

No next experiment or new model run is executed by this closeout. No operating
point, quality gate, winner, holdout release or Git publication is selected.
Production code remains at its tested checkpoint: 23 focused passes and
385 full-suite passes plus one existing Windows symlink skip. This saved-data
analysis and documentation update do not require repeating those code tests.
