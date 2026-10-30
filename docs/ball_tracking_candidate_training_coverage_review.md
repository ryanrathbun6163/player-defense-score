# Candidate training coverage: decision review, 2026-10-29

The authorized coverage/design check is complete. Another training run on the
unchanged data is not justified as a coverage repair. All 3,179 accepted NBA
training frames are already represented. The important gap concerns the actual
chosen mistakes and needed recoveries, rather than a lack of negative examples
in general. Saved older proposals add some different coordinates, but the
locally NBA-untrained producer supplies no selected known-negative or hidden
point on its accepted SAC intersection.

The next proposed experiment is therefore a bounded **proposal-generation
capture**, using an existing locally NBA-untrained checkpoint on those already
accepted NBA training frames. It tests an alternative source of supervision
before any scorer training or new labeling. The [separate protocol](ball_tracking_candidate_proposal_coverage_protocol.md)
fixes the question, inputs, workload and coverage decision. It is proposed and
unrun, not a trained improvement or a verified root-cause repair.

## Due diligence and inherited evidence

Ryan reaffirmed the standing requirement to perform critical due diligence for
every recommendation. This strengthens the October 26 instruction already in
the working agreement; it is not a newly invented approval requirement.
Recommendations must reconcile relevant prior work and research, identify what
actually changes, challenge alternatives, state counterevidence and uncertainty,
and give a bounded question and stop/continue conditions. Reuse completed
reviews and results; do not rerun experiments or create a large administrative
framework merely to claim diligence. Verification counts are not tracking gains.

This review reused the maintained Sessions 1–19 reconciliation, original source
roles and accepted references, then directly rechecked the [quality pilot](ball_tracking_candidate_quality_pilot.md),
[training capture](ball_tracking_training_response_capture_results.md),
[CPU failure study](ball_tracking_saved_score_failure_study_results.md),
[acceptance gate](ball_tracking_candidate_acceptance_gate_results.md),
[origin ablation](ball_tracking_candidate_acceptance_origin_ablation_results.md),
original producers and saved metadata. It is not a fresh reread of every chat,
paper, raw command or video. Earlier geometry/smoothing failures, the head-fill
counterexample, generic appearance-veto losses, useful weak recoveries and the
266 quality-top correct-retention gains remain evidence.

Targeted primary research was reused from the immediately preceding recommendation
review and challenged against the actual recipe:

- [OHEM](https://arxiv.org/abs/1604.03540) supports learning from difficult detector
  examples. Its proposal-selection procedure also addresses correlated overlaps;
  many neighboring candidates are not independent training situations.
- [DCR, sections 4.3 and 5.2](https://arxiv.org/html/1803.06799v3) studies hard false
  positives together with foreground and background examples. Its sampling result
  is not a prescription for equal native/weak quotas, and its box-classification
  benchmarks do not establish tiny NBA point-quality performance.
- [JTT, discussion](https://proceedings.mlr.press/v139/liu21f/liu21f.pdf) explicitly
  relies on representative/group-aware validation and leaves important transfer
  questions open. It does not justify choosing a repair on exposed HOU outcomes.

These sources motivate testable questions, not a guarantee that additional
examples, wider context or a particular weighting rule will help this project.

## New conditional-support result

All original targets and uncertainty rules remain unchanged. A geometric miss
is not automatically a semantic non-ball crop. A point outside ten pixels can
remain excluded from fitting when it lies within the recorded uncertainty band.

| NBA fitting population | Candidates | Frames | Games | Blocks | Consecutive-index runs |
|---|---:|---:|---:|---:|---:|
| Native positives | 2,823 | 2,808 | 3 | 21 | 50 |
| Native known distant negatives | 70 | 53 | 2 | 4 | 25 |
| Native certainly-hidden negatives | 2 | 2 | 1 | 1 | 1 |
| Weak positives | 610 | 610 | 3 | 21 | 233 |
| Weak known distant negatives | 13,706 | 2,694 | 3 | 21 | 137 |
| Weak certainly-hidden negatives | 313 | 113 | 3 | 9 | 14 |

Runs are descriptive adjacency groups, not independent plays or sample-size
certification. Saved analysis preserves exact block/source/frame identities.

**All 70 known native distant negatives are unchosen alternatives.** The three
actual wrong native choices are CHI e02 frames 0, 1 and 70. Their distances are
15.643, 16.251 and 10.560 source pixels, with accepted uncertainty radii 7, 7
and 5. All are boundary-unknown for fitting, while remaining errors under the
unchanged evaluation rule. They cannot be converted into safe negative labels
to fill this gap. Frame 70 has a correct native alternative, not a weak positive.

The two native-hidden examples are adjacent CHI e05 frames 490–491: one interval
in one game. Of the 610 weak positives, 609 accompany an already correct native
choice; only CHI e02 frame 83 accompanies a native-missing choice. None occurs
on a native-wrong frame. Thus 610 weak positives are not 610 recovery examples.

The actual leave-CHI-out gate fitting set has no known wrong chosen-native
target, no native-hidden example and no needed weak-recovery example. It still
has 186 weak-hidden candidates on 70 frames in two games, with objective mass
0.25. General hidden-negative training is present. The existing half-positive,
quarter-distant, quarter-hidden objective and game/block/frame/origin hierarchy
already address broad imbalance; the missing conditional cases are different.

The exposed HOU contrast demonstrates why these distinctions matter. Its 19
wrong native choices are known distant negatives in three blocks/eight runs;
19 hidden native emissions occupy two blocks/three runs. The main pool supplies
weak positives on 12 native-wrong and 15 native-missing frames. Separately, the
saved external stress probes contain correct weak points on all 21 native-missing
frames, including the six e05/14–19 below-.01 successes. These external probes
are preserved; they are not silently added to the current pool or fitting set.
HOU remains a descriptive/regression veto, not an example-selection source.

## Accepted assets and the older-proposal lead

The canonical package has 26 blocks/3,329 frames: 21 NBA blocks/3,179 frames
(CHI 960, DEN 960, SAC 1,259) and 150 secondary NFHS frames. The accepted NBA
campaign's 2,879 training frames plus retained SAC 300 exactly exhaust the NBA
package. No unused accepted training scenes emerged from this inventory.
Additional positions exist in the raw source files, but are not automatically
accepted labels, distinct situations or new fitting permission.

The older expanded-NFHS detector was fitted locally on NFHS 150 and no project
NBA frames. Its cached SAC action observations span 1,471 source frames, of
which 300 have the applicable accepted training references. The pilot shares
60 of those frames. Exact joins verify source frame, PTS, PNG hash and the
recorded heatmap-to-source coordinate conversion.

| Saved selected proposals on accepted SAC frames | Positive | Known distant | Boundary unknown | Masked unknown | Empty | Known hidden |
|---|---:|---:|---:|---:|---:|---:|
| Expanded NFHS, action 300 | 218 | 0 | 5 | 9 | 68 | 0 |
| Expanded NFHS, pilot 60 (overlapping subset) | 60 | 0 | 0 | 0 | 0 | 0 |
| Later SAC-adapted, same 300 | 265 | 2 | 3 | 1 | 29 | 0 |

The SAC-adapted errors are frames 1278–1279. They add two distinct point/crop
inputs, but come from one adjacent interval on a generator's own training source.
They do not establish diverse source-excluded failures.

The expanded-NFHS action/pilot union has 23 distinct known-negative component
coordinates on 19 already-used SAC frames; the pilot's seven are duplicates.
All are unchosen alternatives, and all those frames have correct current native
choices. Twenty-two differ from every current floor-centered crop; 17 also lie
outside the compared historical semantic crop registry. Exact point, crop and
historical overlap are different notions and their counts must not be added.
Historical overlaps retain their original roles; no semantic reference becomes
a new fitting target. New coordinates do not establish new objects or scenes.

Consequently, this cache supplies a small, different alternative-candidate
population, but does not fill the selected-negative/hidden/recovery gap. It is
not evidence for launching another quality fit on a supposedly new hard-case bank.

## What is established, and what remains a hypothesis

The support gap is conditional on the generator, selected policy and target
rules. Cosine nine already saw all three NBA fitting games; holding a game out
of the later quality/gate fits does not undo upstream exposure. Generator
familiarity may contribute to its near-perfect training choices. Counts do not
prove that the appearances of later mistakes are absent from existing weak
negative crops, nor that more data rather than representation or target design
would solve them. No new pixels were inspected in this review.

Upstream WASB pretraining's complete game inventory is unavailable. The older
checkpoint is locally NBA-untrained, not certified globally NBA-unseen. It was
adapted at 512×288; current canonical captures use 768×432. Different weights,
training history and resolution history prevent a causal attribution solely
to NBA familiarity.

Another constraint is fixed: the current cosine-nine wrong/missing native
training frames are confined to CHI. Generating different proposals on the same
frames cannot manufacture cross-game recoveries relative to that current policy.
Recoveries relative to an older producer test a producer-transfer hypothesis;
they are not new examples of current cosine-nine failure on fresh scenes.

## Decision and alternatives

| Direction | Decision from this review |
|---|---|
| Another generic class-balance or cutoff sweep | Low priority: broad balancing is already present; it cannot create absent target cases. This does not prove every weighting method would fail. |
| Immediately refit on saved older SAC mistakes | Not supported as the intended coverage repair: no selected known negatives from the locally NBA-untrained producer, and same-source/adjacent limitations elsewhere. |
| One fixed older-producer capture on accepted NBA frames | Preferred bounded information test: existing checkpoint and labels, explicit new proposal population, no scorer fit. It may return no useful support. |
| New footage/labels | The direct route to genuinely new current-detector failure situations; larger work. Design it if the existing-frame alternative fails or actual-current-policy recovery diversity is required. Do not reopen completed labels. |
| Wider image context or frame-level visibility | Plausible if the existing evidence/target cannot separate cases; no proof of that limitation from metadata alone. Earlier point/CLS, context and temporal work remain comparisons. |
| Immediate routing/always-native | Not established: native's high retention coexists with hidden errors, while weak recovery and the quality-top 90.43% ceiling remain separate constraints. |

The next capture holds canonical input resolution, cadence, contributor means
and extraction fixed while changing the checkpoint. It covers all accepted NBA
training blocks, seals predictions before reference-assisted analysis, and tests
producer-relative known selected errors, hidden emissions and useful weak
alternatives separately. Its prospective diversity screen is a design choice,
not proof of statistical independence or future tracking performance. Passing
would justify designing a later controlled producer-transfer comparison only.
Failure stops this particular capture branch without a threshold/checkpoint sweep.

## Execution, verification and preservation

This review used saved metadata and CPU arithmetic only. No model load, neural
forward, optimizer update, GPU query, image decoding, new label, new selector,
protected access or completed scientific-consumer rerun occurred. All current
annotations, unknowns, previous results and data roles remain unchanged.

Reproducible evidence is under
`data/outputs/ball_tracking/candidate_training_coverage_review_v0_1/`:

- `baseline135_and_direction.json` binds the inherited 135-file worktree and
  Ryan's exact instruction.
- `support/` retains group/frame/run identities, actual fold objective masses,
  external stress preservation, original source bindings and consistency checks.
- `asset_inventory/` retains the complete accepted-frame reconciliation, old
  selected/component joins, crop/history overlap, checkpoint lineage and bindings.
- `support/proposal_capture_feasibility.json` records the metadata-only next-work
  census and exact reuse limitations; it is not a capture result.
- `review/` retains the independent challenges, source checks and final report
  review. The result ledger is
  `configs/ball_tracking/reviews/candidate_training_coverage_review_v0_1.json`.
- `documentation_update/receipt.json` records reversible maintained-document
  additions, unchanged prior contents and the continued Session17/handoff chain.

The proposed capture is not implemented, frozen for launch or executed by this
review. No quality/gate training follows automatically. The unchanged 95%-correct,
1%-wrong, zero-hidden, temporal/recovery and human trajectory gates still apply.
