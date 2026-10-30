# Crop motion factorial: proposed next experiment

Status: concrete proposal; not executable or authorized. No operating point,
method, quality gate, or holdout release is selected.

The completed ranking experiment used one parameter both to permit movement
between candidates and to normalize its score penalty. This proposal separates
those effects. It asks whether an observed change comes from allowing a link,
charging less for an allowed link, or their interaction.

The evidence and remaining limitations are summarized in
`docs/ball_crop_candidate_ranking_results.md`. The saved-result diagnostic is
`data/outputs/ball_tracking/crop_ranking_diagnosis/3c4894656fd5/diagnostic.json`.
The companion machine-readable proposal is
`configs/ball_tracking/proposals/rfdetr_medium_crop_motion_factorial_v0_1.json`.
Approval must bind the final bytes of this design and that proposal.

## Why this bounded comparison

At P002 representative frame 258, tight and wide history admit the same ball
path, but its motion penalty differs ninefold. At P002 challenge frames 44-46,
some ball steps exceed the tight edge limit. These are different mechanisms.
The four graph arms below form the smallest complete comparison of both.

This is not a claimed cure for persistent false detections. At representative
frame 262, a correct, gap-free path already exists under both edge limits but
loses to false candidates with a larger accumulated score. The proposed arms
also retain singleton starts during hidden-ball frames and cannot create a
missing candidate. Results remain descriptive on the same development data.

## Frozen inputs and scope

Use exactly the six saved crop candidate files bound by the completed ranking
experiment at `3c4894656fd5da11708a54089444d41f0a6f7773`. Their detector/crop
execution provenance remains `1a9479f83a1766d8979fad07c604bc686d3c52c6`.
Bind their exact paths, SHA-256 hashes, source geometry, original candidate
indices, and existing reviewed annotation bindings in the new proposal.

| Possession | Pool | Inclusive source frames |
| --- | --- | --- |
| P001 | Representative | 50-74 |
| P001 | Challenge | 200-224 |
| P002 | Representative | 250-274 |
| P002 | Challenge | 25-49 |
| P003 | Representative | 300-324 |
| P003 | Challenge | 150-174 |

There are 150 source frames. No detector inference, training, new labels,
window expansion, player/court inputs, or media-based selection is proposed.
All nine original prediction embargoes and three sealed holdouts remain intact.
Selection reads saved candidates and source metadata only; annotations are
available solely to scoring and synchronized review, never to the selector.

## Seven arms

| Arm | Edge step | Cost step | Existing control mapping |
| --- | ---: | ---: | --- |
| `crop_raw` | None | None | `crop_raw` |
| `crop_top_one` | None | None | `crop_top_one` |
| `crop_top_twenty` | None | None | `crop_top_twenty` |
| `history_edge_tight_cost_tight` | 0.01 | 0.01 | `recent_history_tight` |
| `history_edge_tight_cost_wide` | 0.01 | 0.03 | New |
| `history_edge_wide_cost_tight` | 0.03 | 0.01 | New |
| `history_edge_wide_cost_wide` | 0.03 | 0.03 | `recent_history_wide` |

For each arm, use all nine existing inclusive confidence thresholds:
`0.01, 0.03, 0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 0.50`.
Preserve original global candidate order after filtering. Raw retains all
accepted candidates; top one retains the first; top twenty and graph arms
retain at most the first 20. Retain duplicate candidates without suppression.

## Exact graph and score contract

Let `D` be the source image diagonal, `d` candidate-center distance, and `dt`
elapsed source frames. An edge is admissible exactly when `dt` is 1, 2, or 3
and `d <= edge_step * D * dt`. Independently define its normalized motion as
`d / (cost_step * D * dt)`. Do not clip that value: a wide-edge/tight-cost link
can reach normalized motion 3 and motion penalty 2.25.

Preserve the existing algorithm and all other rules:

- Rebuild an exact directed acyclic graph over the current and four preceding
  frames, truncated at the window start. No future access or cross-window state.
- Permit a path to start at any retained node; leading missing frames cost
  zero. The candidate cap, five-frame horizon, and singleton starts are fixed.
- Score each path as the sum of original confidences, minus `0.25` for each
  internal or trailing skipped frame, minus `0.25` times the sum of squared
  normalized motion. Internal gaps and trailing gaps remain at most two frames.
- Use exact dynamic programming over this graph. Preserve arithmetic and
  traversal order for existing controls; do not round before comparisons.
- Break equal path scores by the lexicographically smallest sequence of
  original `(frame_index, candidate_index)` pairs. Break equal endpoint scores
  by latest endpoint frame, higher endpoint confidence, lower global candidate
  index, then lexicographic path. The empty hypothesis has score zero and wins
  every zero-score tie.
- Emit only the original candidate when the winning endpoint is current.
  An older or empty winning endpoint produces null. Never revise past outputs,
  shift centers, alter confidences, interpolate, smooth, or extrapolate.

Retain every candidate disposition, admissible edge and component cost, best
path per endpoint, competing endpoint, winner, score margin, and null reason.
Scores and margins are not probabilities. No margin acceptance rule is added.

## Scoring, counts, and control parity

Keep raw center-distance matching and the radii `5, 10, 15, 20, 30` source
pixels. Annotation uncertainty remains diagnostic; hidden frames retain null
truth geometry. Preserve separate representative and challenge pools.

The fixed scope is 63 variants, 378 derived window outputs, 1,890 per-window
scoring reports, and 315 aggregate cells per pool. Five mapped existing arms
provide 1,350 saved per-window scoring parity cells; the other two arms are new.
No setting is chosen from these correlated comparisons.

Control parity must compare full saved observation traces as well as reports:
original emitted indices, dispositions, paths, edges, score components,
winners, margins, null reasons, frame outcomes, and aggregate metrics. Map
legacy `step_limit` to both new step fields for diagonal controls. Explicitly
account for renamed arms and new schema/run metadata; never mask behavioral
differences as metadata. Verify all 270 mapped control output traces.

## Review package

Render 12 complete 25-frame clips at 5 fps: six windows at confidence 0.20 and
0.35, using the predeclared radius 10. Use a 3-by-3 mosaic in this order:
raw, top one, top twenty; tight/tight, tight/wide, wide/tight; wide/wide,
unmarked source, legend. Label both parameters on every graph panel.

Preserve native-resolution evidence, source-scale unmarked/marked closeups,
original candidate references, alternative hypotheses, and explicit missing
output. Verify every clip through frame 25 and provide final-frame panels and
closeups. Ryan reviews all 12 clips through their final source frames. The
earlier saved whole-frame context panel remains in the previous package and
need not be repeated here. Agent structural checks do not replace his review.

## Implementation and authorization boundary

Use separate experiment/observation schemas and provenance containing both
`edge_step` and `cost_step`, including variant IDs, specification digests,
reports, and review labels. Create immutable, resumable outputs under
`data/outputs/ball_tracking/crop_motion_factorial/rfdetr_medium_crop_motion_factorial_v0_1/`.
Preserve every existing reviewed proposal, manifest, output, and receipt.

Synthetic validation must independently exercise inclusive edge boundaries,
different gate/cost combinations, normalization above one without clipping,
exact path/endpoint ties, empty ties, gaps, horizon expiry, cap behavior,
window resets, future-data isolation, and label-free selection. Require an
independent exhaustive small-graph reference, full mapped-control parity,
partial-resume and tamper checks, scoring partitions, and decoded review clips.
Run focused tests before the full repository suite with bytecode disabled.

The next step is explicit approval of this exact experiment scope. Then
implement and validate against synthetic fixtures and read-only input checks.
Staging and committing each require separate authorization before execution
from a clean implementation checkpoint. Execution remains unauthorized until
the new scope is approved and those conditions pass. Pushes, PRs, merges,
operating-point selection, quality gates, and holdout release require their
own explicit decisions; this proposal authorizes none of them.
