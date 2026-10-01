# Proposed comparison: soft player context in crop ranking

Status: specified for review; not implemented, authorized or executed.

The next question is whether observed player rectangles can reduce persistent
remote distractors without losing valid passes or reacquisitions. The preceding
appearance diagnosis is `ball_candidate_identity_diagnosis.md`. This proposal
adds one fixed context term to each of the four existing motion settings.
It does not select a motion setting, confidence threshold, quality gate or
production method. A proposal coefficient is a test hypothesis, not an adopted
operating point.

## Scope and frozen inputs

Use only the six finalized development windows and the exact saved crop
candidates, labels and motion outputs already bound at
`2274ab6097cd841421e2b606f723b047cd7dc62b`:

| Possession | Representative frames | Challenge frames |
| --- | --- | --- |
| P001 | 50-74 | 200-224 |
| P002 | 250-274 | 25-49 |
| P003 | 300-324 | 150-174 |

There are 150 frames, 145 localization-eligible labels and five hidden frames.
Keep the representative and challenge pools separate. Reuse completed outputs
and score reports; no detector, crop, ranking or motion experiment is rerun.
No model call, training, annotation change or window expansion is included.

The ignored `context_inputs.json` under
`data/outputs/ball_tracking/candidate_identity_diagnosis/2274ab6097cd/`
freezes the 1,353 reconciled observed player rows in those frames, original
fields/IDs/duplicate provenance, source metadata, selected-row digests and
current source-file hashes. The proposal JSON binds its exact bytes. Use only
source-image rectangles; do not read court projections, homography arrays,
interpolated player coordinates or sealed holdout geometry. Labels are available
only to scoring and review, after selection.

These are frozen offline reviewed player inputs. Their identities may reflect
later human review; this comparison does not establish an online player
pipeline. Historical source-video hashes and detector provenance are absent
from the legacy player artifacts. Current hashes freeze today's evidence,
without claiming that missing historical provenance exists.

## Exactly one new scoring term

For a candidate center `(x, y)` and each observed player rectangle
`(x1, y1, x2, y2)` in that candidate's own frame, calculate:

```text
dx_i = max(x1_i - x, 0, x - x2_i)
dy_i = max(y1_i - y, 0, y - y2_i)
d_i  = hypot(dx_i, dy_i)
h_i  = y2_i - y1_i
z    = min_i(d_i / h_i)
p    = z / (1 + z)
context_cost = 0.25 * p
node_utility = original_detector_confidence - context_cost
```

The normalization uses the minimum ratio over **all** boxes, not the distance
to the nearest pixel-distance box divided by that box's height. A point inside
or on any box has zero cost. At one normalized player height the cost is .125;
it approaches .25 smoothly at very large distances. This bounds the penalty
and avoids a hard distance cutoff. Utility is not a probability and must not
replace the original confidence field.

The coefficient .25 uses the existing path-penalty unit as one predeclared
hypothesis. It has not been optimized or calibrated on these frames. Do not
sweep its strength, replace its functional form after seeing results, or fit
possession-specific constants. The zero-strength case is solely an
implementation-parity test, not another real experiment arm.
Equal coefficients do not imply equal empirical effects to gap or motion costs.
Retain negative node utility; never clamp it or use it for confidence filtering.

Empty player context contributes zero cost and an explicit
`context_unavailable` flag. Incomplete coverage remains visible in the frame's
box count; no boxes are filled or extrapolated. Reject malformed/nonfinite
geometry, nonpositive width/height, duplicate player IDs, out-of-window frame
keys, and mismatched source/timestamps. Preserve legitimate boxes crossing an
image boundary. Do not reject a candidate merely because a box is absent.

For diagnostic attribution, record all minimizing boxes, ordered by player ID
then original track ID; the numeric cost is independent of row order. Do not
interpret a minimizing player as the ball handler or defensive matchup.

Apply the context term after the unchanged inclusive confidence filter and
original global-order cap of 20. Charge it once for each observed node in a
path, using that node's own frame context. Preserve original candidate indices,
coordinates, confidence, view provenance and candidate order.

## Paired design and unchanged rules

Keep all seven saved controls: crop raw, top one, top twenty, and TT/TW/WT/WW.
For the four graph controls add TT-context, TW-context, WT-context and WW-context.
T/W continue to mean edge allowance first and motion-cost scale second, with
values .01/.03 source-image diagonals per source-frame interval. The only new
term is the sum of node context costs:

```text
path_score = existing_confidence_sum
           - existing_missing_frame_cost
           - existing_motion_cost
           - sum(node_context_cost)
```

Preserve the five-frame graph horizon, maximum two internal/trailing missing
frames, no leading-missing cost, existing edge rules and arithmetic, empty
hypothesis score zero, empty-wins-zero-tie rule and all path/endpoint tie breaks.
For the context arm, use binary64 arithmetic in existing traversal order:
singleton score is node utility; extension score is
`((parent_score + node_utility) - gap_cost) - motion_cost`; endpoint score is
`path_score - trailing_cost`. When context cost is zero, use original confidence
directly as utility. Accumulate the unpenalized confidence sum and the context
cost sum separately in path order for auditing, without recomputing the score
from those sums. Retain original-confidence endpoint tie breaks. Test zero-cost
parity exactly. Selection
may change path identity, support length or abstention, and must report those
separately. Emit an original candidate only when the winning endpoint is the
current frame; otherwise emit null. No smoothing, interpolation, extrapolation,
future ball-frame access, retrospective output revision or state across windows.

Do not combine deduplication, color/size/border filters, appearance models,
startup confirmation, hard court/player masks or new motion changes with this
comparison. The context term cannot distinguish false proposals already inside
a player box, including hidden P003 167#0/168#0.

Use the unchanged confidence grid `.01, .03, .05, .10, .15, .20, .25, .35, .50`
and localization radii `5, 10, 15, 20, 30` pixels. Matching remains raw center
distance with annotation uncertainty diagnostic only. Retain saved metrics,
candidate-availability/filter/cap/ranking loss partitions, false observations,
hidden false alarms, missing frames, longest missed runs and localization error.
Add exact paired gains/losses, changed endpoints, path support and abstention
changes, player-context availability and every context score component.
Do not claim independent samples across arms, thresholds, radii or crop views.

| Artifact | Reused controls | New context arms | Combined |
| --- | ---: | ---: | ---: |
| Arms | 7 | 4 | 11 |
| Arm/confidence variants | 63 | 36 | 99 |
| Window outputs | 378 | 216 | 594 |
| Window/radius reports | 1,890 | 1,080 | 2,970 |
| Aggregate cells per separate pool | 315 | 180 | 495 |

Each new arm is compared only with its corresponding saved graph control,
yielding 1,080 per-window paired cells and 180 aggregate contrasts per pool.
Load reused reports without rescoring old outputs. Bind their exact bytes and
configuration/threshold/window keys. Preserve their original execution provenance
when composing a new comparison report; do not relabel them as new runs.

## Validation and visual review

Before any real comparison, require focused tests then the full suite with
bytecode disabled. Test the geometry independently, minimum normalized distance
versus nearest pixel-distance, monotonic bounded cost, inside/boundary zero,
missing context, invalid inputs, row-order invariance and own-frame attribution.
Use independent exhaustive synthetic path enumeration to check all four
settings, positive-cost reranking and abstention, negative node utility, ties,
gaps, window reset and future-frame isolation. A zero-strength adapter must
reproduce old arithmetic and traces exactly on synthetic cases. All real saved
control bytes must remain unchanged; do not rerun their pipelines for parity.
Tests must prove annotations cannot enter the selector.

Prepare 12 new synchronized comparison clips: all six windows at confidence
.20/.35 and radius 10, all 25 frames at 5 fps. These are display settings only.
Use four rows and three columns:

| Existing graph control | Corresponding context arm | Reference panel |
| --- | --- | --- |
| TT | TT-context | Unmarked source |
| TW | TW-context | Observed player rectangles/context availability |
| WT | WT-context | Crop top one |
| WW | WW-context | Legend |

Reuse existing control and source PNGs. Keep exact native views available for
all 11 arms, including saved crop raw/top twenty; create new context overlays,
player-box views, mosaics and source-scale closeups in a distinct output root.
Crop raw/top twenty are native-only references, absent from the composite.
The player-box panel is independent of selected ball outputs and shows the
number of observed boxes and any missing context.
Panel labels must show both motion parameters and context strength. Distinguish
detector confidence, context cost and final path score. Preserve uncertainty
and null output, and identify observed boxes as context rather than ball truth.

Review all frames through each final frame. Highlight P001 challenge 200-201
passes, P002 representative 258/262, P002 challenge 44-49, P003 representative
300-308, and P003 challenge 164-174 including hidden 165-169 and reacquisition
171. Compare both improvements and lost observations. Ryan makes final visual
judgments; diagnostics or a completed run do not imply approval.

## Execution boundary

The companion `configs/ball_tracking/proposals/rfdetr_medium_crop_player_context_v0_1.json`
is a reviewable specification, not an executable manifest. Exact-scope approval
must be recorded before real comparison. Implementation and validation can be
prepared separately; staging and committing require their own explicit approval
under the working agreement. Execution then requires the clean, tested commit,
an evidence-bound approval/manifest, all frozen input checks and a fresh ignored
output root `data/outputs/ball_tracking/crop_player_context/rfdetr_medium_crop_player_context_v0_1`.

No upstream player review is changed; no upstream `--rerun-from` is needed.
If a bound source or reviewed input changes, stop and identify its upstream
stage and downstream invalidation before proposing a revision. Never overwrite
old reviewed evidence. All nine original prediction paths must remain absent;
P001 300-324, P002 200-224 and P003 250-274 stay sealed. No holdout release,
operating-point choice, quality gate, push, PR or merge is included.
