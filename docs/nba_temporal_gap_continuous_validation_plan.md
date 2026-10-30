# Proposed continuous-context validation of the accepted gap rule

Ryan approved the three bounded-trial comparisons with “Ok I approve. What next
chat”. That closes the visual gate for the three-frame development improvement,
recorded in [the later review](../configs/ball_tracking/reviews/nba_temporal_gap_selection_visual_review_v0_1.json).
This document proposes the next execution; it has not run. No new fit, inference,
parameter search, holdout release or full-game claim follows from that approval.

## Decision

Determine whether the unchanged short-gap rule remains useful across complete
available development clips, with natural gaps and recovery transitions instead
of artificial short-window resets. Deliver a repeatable source-scoped comparison
and a concrete inventory of remaining failures before downstream possession or
matchup work. This rule does not repair long gaps or existing wrong positions.

## Exact available context

| Source | Permitted source frames, inclusive | Processed frames | Existing triplets |
| --- | --- | ---: | ---: |
| SAC | 540–2010 | 1,471 | 1,469 |
| DET | 10668–11898 | 1,231 | 1,229 |
| NFHS P001 | 0–274; 350–498 | 424 | 420 |
| NFHS P002 | 0–174; 250–498 | 424 | 420 |
| NFHS P003 | 0–224; 300–499 | 425 | 421 |

This is 3,975 processable frames in eight continuous segments. The NFHS protected
bands (P001 275–349, P002 175–249, P003 225–299) remain excluded from processing
and black in playback. Including those 225 positions gives 4,200 timeline slots.
NBA ranges are continuous live-action camera sequences, not certified complete
possessions or live-ball states.

Authorities are the [NBA action proposal](../configs/ball_tracking/selections/nba_wasb_action_observation_proposal_v0_1.json)
and [NFHS development observation config](../configs/ball_tracking/wasb_experiments/wasb_expanded_development_observation_v0_1.json).
Metadata inspection found all 3,959 expected triplet files at their recorded
sizes, totaling 6,304,753,417 compressed bytes. This is an existing inventory,
not a required read budget; no arrays were read for this proposal.

## Unchanged rule and fair comparison

Keep retained checkpoint `09da1214e94f`, strict `>0.3` components and every fixed
setting of the accepted rule: original points immutable; original in-image
anchors within 0.12 seconds; speed at most one image diagonal/second; candidate
residual and plausible-coordinate diameter at most 0.006 diagonals; exact saved
candidate output; whole-gap abstention and no recursive anchors. Reset only at
the eight permitted segment boundaries. Never connect across protected bands.
Native timestamps govern all timing; future-anchor context remains explicit.

Compare with each source's **same-context original selection**. Score only the
same 790 existing labels, keeping SAC, DET, NFHS and included controls separate.
The saved longer-context NFHS baseline is **131 matched, one wrong, 13 missing,
zero hidden alarms**, whereas the original short-window baseline was 130/1/14/0.
Keep the accepted short-window trial as a separate comparison. Identify changes
caused by model input context separately from changes caused by the selector.
The previously accepted three additions must remain explicit retention checks;
any loss must be explained, not hidden in aggregate gains.

Before execution, bind the exact context/control records and unchanged rule.
Require no added wrong outputs or hidden alarms, no loss of existing correct
positions, both NBA easy controls at 60/60, and the original quantitative gates.
Also require DET to retain at least the accepted 209 matches. Preserve the
same-context NFHS baseline and account explicitly for the accepted P001/208 gain.
Report every changed frame, original/selected errors and full missing intervals.
Unlabeled positions remain unscored; visual plausibility is not an accuracy count.

## Efficient execution and review

Use saved original centers and PTS to reject edge, overlong and excessive-speed
gaps before opening heatmaps. Only potentially fillable gaps need additional
contributor components. Reuse bound pools only where complete contributor context
matches. Verify the necessary cache identities and bodies at consumption; a
missing or mismatched cache must never silently start inference. Test that this
execution optimization preserves the frozen selector's decisions.

Save choices before labels enter scoring. Reuse the current selector, cache
loader and review components; test changed producer/consumer boundaries and
independently verify actual emitted records. Keep original evidence immutable.

Render five synchronized comparisons through their actual final frames.
Existing reconciled-player overlays are available for all three NFHS clips and
may be displayed with the ball. NBA review remains source/ball comparison:
reviewed NBA player identity is not available under this scope. Highlight all
newly filled gaps and preserve unknown intervals and protected black bands.
Ryan reviews the resulting trajectories before broader adoption.

If the unchanged rule holds up, integrate it as an optional auditable ball
postprocessing step and use the remaining-error inventory to choose the next
detection/localization improvement. If it introduces failures, preserve the
negative result and decide from the observed cause; do not tune a parameter grid.
Neither outcome completes the ball phase or establishes independent holdout
performance. No reviewed upstream player-pipeline decision is changed here.
