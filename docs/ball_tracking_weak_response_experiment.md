# NBA weak-response feasibility and paired selection

October 26, 2026. Authorized in session 18 after the complete session 17 handoff.
This experiment uses cosine epoch nine as a **research control**, not an adopted
model. New fitting remains conditional on the findings and a subsequent decision.

## Scientific question and historical basis

Can the current model's weak observed responses supply useful automatic ball
locations when considered with surrounding model evidence? Can a small sequence
chooser correct original wrong choices without comparable losses or hidden
emissions? These are separate questions from whether a pool contains a point
near a known answer.

The [completed sixteen-session reassessment](research/ball_tracking_full_history_reassessment_2026-10-26.md)
is reused, with its documented coverage limits. Relevant primary reports and
producer code were inspected again for this method; the old transcripts were
not reread wholesale. The historical outcomes remain unchanged:

- The [older weak-response diagnosis](ball_wasb_remaining_gap_diagnosis.md)
  found matching components somewhere in its grid for all 46 misses. Blind
  mass selection still chose distractors and lower cutoffs added hidden outputs.
- [WASB motion selection](ball_wasb_motion_selection.md) was past-only and used
  existing strong candidates. It tied the scored control and left empty frames
  empty; that result does not answer the current weak-response question.
- [Candidate preservation](nba_candidate_preservation_experiment.md) recovered
  nine available positions but also increased ambiguity and hidden-frame pools.
- [Two-ended gap repair](nba_temporal_gap_selection_experiment.md) already used
  future context, limited anchor spans to 120 ms and preserved original choices.
  Its continuous extension and [later accepted references](nba_gap_anchor_reference_evaluation_results.md)
  established three initial and eight additional geometric gains, with the
  documented identity caveats and adverse SAC head trajectory still intact.
- The [DINO verifier](nba_ball_distractor_training_results.md) removed 207/581
  previously correct points and remains rejected.
- [Current continuations](ball_tracking_wasb_continuation_results.md) and the
  [spatial pilot](ball_tracking_wasb_spatial_results.md) represent real completed
  training iterations. None removes the 19-frame DET gap. Training successes,
  failures, frozen recipes and recovery history remain preserved.

The substantive variation is observed weak candidates, revisable original
choices and explicit abstention. Future context itself is not a new idea.

## Prospective method

The [parameter file](../configs/ball_tracking/proposals/weak_response_v0_1.json)
was saved before extraction or selection results. The ignored
`data/outputs/ball_tracking/weak_response_v0_1/prospective_freeze_v0_2.json` binds the
final implementation before automatic choices or scores are computed.

All eight complete permitted contexts are retained: six HOU episodes (960
frames), DET (1,231 frames) and SAC (1,471 frames), totaling 3,662 native frames.
The model is the saved cosine-nine checkpoint with SHA-256
`f4b721662ec3d8b546563feffcf5ce0d6319ed8ddc83f398830a0aac5d29c7b9`.

Extraction retains every original strict >0.3 component, then adds weighted
components at 0.1, 0.03, 0.01, 0.003, 0.001, 0.0003, 0.0001, 0.00003 and 0.00001.
A separately recorded 5x5 local-maximum extraction checks whether connected
components merge distinct response lobes. Its patch center uses observed pixels
above half the local peak. Weak duplicates within two source pixels are merged
in the selection pool, while every raw extraction/provenance remains available.
No candidate-count cap is applied. Component mass is not a probability, and
masses from different thresholds are not compared as calibrated confidence.

The three fixed arms are unchanged native selection, sequence selection using
only native strong candidates, and that same rule using the expanded pool.
The offline sequence maximizes an explicitly defined research objective with
an always-available missing state. It uses native presentation timestamps,
source-width-normalized displacement and model response; reference geometry,
eligibility and visibility never enter it. All original selections may change.
Every emitted point is an actual candidate coordinate, never interpolation.

Weak points must be geometrically reachable from strong model candidates before
and after within 0.4 seconds, under the fixed 1.5-source-widths/second bound.
Those supporting candidates need not be the finally selected path: this is a
broad geometric hypothesis, not proof of ball identity. The objective gives
weak points equal reward; path-margin values are diagnostic costs, not calibrated
confidence. A smooth head/hand/background path can therefore still win.

Exact sparse neighbor enumeration and vectorized support tests avoid a dense
quadratic table without removing candidates or changing costs. An independent
exhaustive synthetic oracle checks the objective, alternate-path margins, ties,
abstention and inclusive motion boundaries.

## Data roles and decision boundaries

The [source-role manifest](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json)
is unchanged. HOU is repeatedly inspected checkpoint-validation development
data. This first comparison makes no HOU-based parameter sweep or selection.
DET remains excluded from fitting/checkpoint selection: its accepted references
measure diagnostic ceilings and score the locked rule, never seed or tune it.
SAC is training-exposed and descriptive. None is a fresh independent test.
CHI/DEN and retained NFHS fitting roles are unchanged; no new labels are made.

All per-context quality rules, uncertainty, native timing, boundary censoring
and manual/inferred-as-absent scoring remain unchanged. The nine source-uncertain
recovery events retain their independent evidence limitation. Complete human
trajectory/object review is still required; protected evaluation stays closed.

Useful support plus a bounded automatic gain can justify a reasoned refinement
even while final acceptance fails. Broad near-reference availability amid
indistinguishable clutter is insufficient. If actual observed candidates cannot
cover the deficits or the fixed chooser cannot separate them from persistent
distractors, the next decision should test a specific recognition/preprocessing
hypothesis. No new training starts automatically from this experiment.

## Execution evidence

CPU inventory verified all eight input caches, the checkpoint, original paired
records and all 2,702 saved DET/SAC mean maps. HOU validation had discarded its
raw means, so one scoped supervised pass regenerated 960 means using 948 native
triplet calls. Every mean hash and original native observation reproduced exactly.
The GPU pass completed in 53.593 supervised seconds, peaked at 57 C, exited zero
with no stop/cleanup error and left no owned process. Graphics extras were
checked absent before execution. No settings changed; a clean pass does not
establish that the earlier graphics-reset issue is cured.

An independent CPU audit re-extracted all HOU native components from the saved
maps and verified emitted rows, journal counts and monitor records: 11,544 checks,
zero discrepancies. The six handoff documentation files were still byte-for-byte
unchanged at that audit. All new source/config/test files are additive.

The first saved-map extraction attempt reached an undersized 5 GB transport
limit after 352.935 seconds. Preserve that failure and its partial files. The
recovery uses a practical 30 GB allowance, reuses complete emitted frame pairs
and extracts only remaining frames. Scientific parameters, model responses,
native candidates and data roles are unchanged. This is a tooling interruption,
not a negative scientific result or a reset of consumed work.

The [completed results and review artifacts](ball_tracking_weak_response_results.md)
record the full feasibility scan, failed first selector, and a bounded HOU-informed
follow-up that separates motion cost, speed limit and a narrower weak pool. Useful
recoveries persist, but neither method passes. The follow-up's preparation probes
and parameter-selection basis are disclosed separately from its full-study freeze.
No new training or protected evaluation follows automatically.
