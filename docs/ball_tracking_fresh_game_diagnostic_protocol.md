# Fresh-game current-model diagnostic

October 30, 2026, America/Phoenix. Ryan approved moving forward after the
recommendation to examine actual current-model failures on fresh footage.
This is a finite diagnostic and reference-preparation increment. Prior models,
results, accepted references and failed experiments remain unchanged.

## Decision and evidence

Determine whether actual mistakes from the current detector and saved scorers
provide a specific next intervention: candidate availability, candidate choice,
acceptance, or information missing from the current image input. Do not assume
that another fit, a larger crop, or additional hard examples will fix them.

The producer-transfer treatment failed its frozen criterion: correct retention
fell in all three scorer-held NBA games. Of its 76 alternate-producer recovery
examples, 75 already had a correct current-native choice. That experiment did
not add independent current-producer failure scenes. The earlier training
coverage review explicitly identified new footage as the fallback when the
existing-frame alternative did not supply the required evidence.

Reuse the completed full-history reassessment, CPU failure study, quality,
acceptance, origin-ablation, coverage and producer-transfer studies. This turn
adds targeted reading of those results, source-role/acquisition records and the
annotation workflow; it does not claim another full transcript/paper reread.
Primary DCR research motivates examining base-detector mistakes; JTT cautions
that emphasizing high-loss examples can optimize irrelevant groups. Neither
establishes that this project's current crop or training objective can separate
the required cases. Sources:

- https://arxiv.org/abs/1803.06799
- https://proceedings.mlr.press/v139/liu21f.html

J remains a useful saved control. Its NBA strict-first diagnostic largely
occurs on already-native-correct frames; HOU native-failure ordering and hidden
survivors contradict a simple max-J selection fix. Frozen Q-top choice has a
2,542/2,811 ceiling: acceptance alone cannot reach 95% in that saved view.

## Fixed source sample

The source-first selection is frozen in
`data/outputs/ball_tracking/fresh_game_diagnostic_v0_1/source_selection/selection.json`.
Use BARD's pinned revision `d98a075d42c46518cf5b3c7255cb4c6d207adeef`, reusing
the saved catalog rather than acquiring the dataset again. BKN–DET game
`0022400861` has 246 unique catalog clips. Ascending numeric clip IDs and
zero-based floor((246-1)*q), q=.25,.5,.75, select clips **122, 237, 365**.
Use every original frame with native PTS in **[0,2) seconds** of each clip.
At the cataloged 60 fps, this is 120 frames each, 360 total. Never resample to
force that count; stop and document a cadence/structural mismatch instead.

Selection precedes new pixels, labels and predictions. Clip 0 was previously
previewed only for acquisition usability and is not selected. The new game is
outside local fitting, but upstream pretraining's full game inventory is
unknown. Assign the entire game `diagnostic_development`; both fitting and
checkpoint-selection eligibility remain false. This is not a pristine holdout.
Existing HOU, DET, TOR and NFHS protected roles are unchanged.

These are three event-clipped starts from one game, not random full-game
possessions or a representative broadcast. Retain easy, difficult, hidden,
closeup or replay content. No replacement based on difficulty or results, no
mining until an error quota is met, no extra stress enrichment this stage.
Structural failure/duplicate/wrong-game evidence stops the selected component;
preserve its original selection before any later correction.

## Source-first references and human review

Acquire only the three clips (32 MiB maximum each) and export the fixed native
RGB PNGs, actual PTS/frame map and byte/RGB hashes. No detector or scorer is
used to create labels. The assistant inspects every selected frame, proposes
complete-ball centers and current-frame uncertainty, and retains per-frame
inspection evidence. Neighbor context may identify the ball, but never supply
an interpolated hidden center. Distinguish visible but indefensible geometry,
partial visibility, certain hidden and indeterminate identity.

Use the existing FrameAnnotation semantics. The partial-center legacy field
`human_amodal_estimate` denotes the geometry convention; the wrapper explicitly
records AI authorship. All proposals are pending, with no fitting or selection
eligibility. Render every selected frame in native and slow complete overlays,
plus source/detail views, an exception list and the actual final frames. The
original proposals remain separate from any later human-accepted publication.

Ryan's standing first-pass workflow delegates preparation to the assistant;
the working agreement still reserves final reference acceptance to Ryan.
Complete this concrete review package before asking for that acceptance.
Accepting this experiment did not already accept unseen labels.

## Frozen inference and diagnostic comparisons after reference acceptance

Reuse the all-NBA controls, without fitting or changing thresholds:

- cosine-nine `wasb_continuation_v0_1/cosine/fit_v0_1/checkpoints/epoch_009.pth`;
- original Q `candidate_quality_pilot_v0_1/attempt_005/all_nba/final_trainable.pth`;
- J `candidate_acceptance_gate_v0_1/attempt_001/analysis/fits/final_all_NBA_J.json`.

All paths are under `data/outputs/ball_tracking/`. Keep Q+ out of J. Verify
saved checkpoint and implementation bindings before a later inference launch.
Reuse canonical 768x432 affine input, original normalization and consecutive
native triplets independently inside each fixed block. No outside temporal
context: 3*(120-2)=**354 detector forwards** if source timing confirms the plan.
Preserve exact float32 contributor means and counts, including boundaries.

Retain all native >.3 components, plus >.01 weak components under established
2-source-pixel deduplication, with no candidate cap. Score every in-bounds
candidate with original Q, original 64-pixel source crop/fractional point input,
batch 32. Its finite workload becomes ceil(K/32) after candidate capture, with
K saved before Q execution; no silent truncation. J uses saved CPU weights and
the complete same-frame Q pool. A new diagnostic wrapper must preserve the
new role instead of pretending these frames belong to old fitting registries.
Inference remains subject to the existing supervised GPU readiness safeguards.

Report original native and fixed original-Q-top choices before and after Q/J
zero acceptance, with identical candidate identities across acceptance views.
Retain every missing/empty/out-of-bounds/unknown slot. No new J-argmax selector,
fallback, threshold sweep, temporal fill, training, or model adoption occurs.

After human reference acceptance, use the existing <=10 original-source-pixel
match rule on eligible centers. Wrong eligible choices remain >10 px; do not
confuse training boundary-unknown exclusions with evaluation correctness.
Certain-hidden emissions and unknown reference states are separate. Report:

1. eligible frames with no matching candidate anywhere in the retained pool;
2. available matching candidates but a wrong/missing fixed choice;
3. correct fixed choices rejected by Q or J;
4. accepted wrong choices and emissions on certain-hidden frames;
5. preserved correct choices, exact gains/losses, weak recovery and boundary cases.

Break these down by clip, original native success/failure and visibility;
retain exact frame identities, full denominators and overlaps. Illustrate each
observed failure alongside successful controls using current-frame source and
the exact model crop. Additional context must be shown as diagnostic evidence,
never assumed to cure the error. No event within a two-second window means
recovery is unmeasured; a censored return is not a successful recovery.

## Decision and stopping rules

Stop at the frozen three windows, including if no useful failures occur.
Sparse/ambiguous events mean insufficient evidence for an intervention, not a
pass. Report conditional counts without claiming cross-game accuracy or
progress to 95% from unaccepted labels or selected hard cases.

If repeated reviewed mistakes have a discriminating cue already in the input,
consider one current-error training/selection hypothesis with explicit old-
success retention controls. If the required cue lies outside the input, first
specify that concrete representation contrast. If matching proposals are
absent, an acceptance change cannot recover them. No subsequent fit is automatic.

## Preservation and current artifact state

`baseline155.json` verifies every inherited worktree path against the completed
producer-transfer receipt, branch `codex/ball-detector-baseline`, HEAD
`8c040fca385dd8fffa0d7a13c45c53e79950bae1`, and empty index. New artifacts live
under `data/outputs/ball_tracking/fresh_game_diagnostic_v0_1/`; acquisition bytes
live under the matching new `data/raw/nba/` directory. Existing source roles,
accepted labels, caches and scientific results are preserved. No Git integration
is included. Later preparation results and pending review are recorded separately.
