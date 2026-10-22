# Decisions and Invariants

These are durable project decisions, not incidental properties of one possession.

## Product and analytical decisions

1. **The output must be interpretable.** The end goal is a transparent possession-level defender score that can be explained in interviews and audited basketball-wise; it is not a black-box ranking exercise.
2. **Build reliable measurement layers before scoring.** Player and ball trajectories, possession state, matchup assignment, and outcomes must be trustworthy before defensive weights are finalized.
3. **Start with a narrow case study, then generalize.** The initial matchup is Stephon Castle defending Cade Cunningham on 2026-02-23, but the architecture must ultimately support other players, possessions, and games.
4. **Full-game scale is a later phase.** Curated possessions are the development and validation unit until each layer passes a multi-possession gate.

## Data and uncertainty decisions

1. **Missingness beats fabrication.** If evidence is insufficient, leave a coordinate, identity, ball state, or assignment unknown.
2. **Every correction must be auditable.** Preserve the original observation, correction/interpolation method, anchors, thresholds, and reports.
3. **Only bracketed internal gaps are interpolated.** Leading observations without a left anchor remain missing; this was explicitly preserved in the Possession 001 baseline.
4. **Outside-court observations are not silently clamped.** They are retained and audited unless a separately justified correction applies.
5. **Generated artifacts are reproducible evidence, not source.** Videos, crops, embeddings, CSV/NPZ outputs, ZIP review packages, and copyrighted footage stay ignored by Git.
6. **Ball-label review defaults to honest single-annotator visual review.** A second person or duplicate labeling pass is not a routine gate. Small point-placement variation is represented by annotation uncertainty and later scoring tolerances. Independent or same-person repeats are optional reproducibility studies, must be described accurately, and must never use a fabricated reviewer identity.

## Pipeline architecture decisions

1. **One possession manifest is the configuration contract.** It supplies the possession ID, video path, reference frame, expected counts, court geometry, and reviewed overrides.
2. **Paths are possession-scoped.** `PipelinePaths` derives config, state, and generated-output locations from the possession ID.
3. **No source edits per possession.** A new clip may require manifest values and review decisions, but not custom Python changes.
4. **The workflow is resumable.** Completed stages are skipped when commands, inputs, and manifest signatures are unchanged; failed stages resume; deliberate upstream changes use `--rerun-from`.
5. **There are two required human-review gates.** Identity reconciliation and calibration remain explicit pauses.
6. **The reviewed baseline is protected.** Possession 001 cannot be executed destructively by default.
7. **Final-frame review matters.** Camera motion, identities, and coordinate visualizations must be checked through the actual last frame, not merely at sparse checkpoints.

## Generalization gate decisions

The empirical player-coordinate gate requires:

- all 21 stages and both review gates completed;
- no possession-specific source edits;
- one homography per decoded frame;
- at least 95% coordinate coverage;
- at least 85% complete expected-player frames;
- zero unresolved reviews;
- zero coordinate-key violations;
- outside-court positions audited;
- synchronized visual review through the final frame;
- generated outputs left uncommitted.

Possession 003 passed this gate. Do not relax these thresholds retroactively.

## Ball-phase exit contract accepted on 2026-10-21

Ryan approved the [completion plan](../ball_tracking_completion_plan.md) and its
new numerical criteria in the bound
[approval record](../../configs/ball_tracking/reviews/ball_tracking_completion_campaign_approval_v0_1.json).
This is the three-curated-possession finish line: at least 95% correct automatic
positions within the existing inclusive ten-source-pixel radius; at most 1%
wrong eligible outputs; zero certain-hidden/out-of-view emissions; no eligible
missing run over 200 ms or wrong-object run lasting 120 ms or longer; recovery
within 120 ms with the first correct and next two eligible frames correct;
complete synchronized review of all 1,498 frames. Apply each criterion per
possession and retain the plan's exact timing, eligibility, censoring and
inconclusive-evidence rules. Inferred/manual points count as absent for automatic
metrics. This does not revise historical player or experiment gates.

The approved campaign allows one primary WASB fit and one conditional resolution
fit after reference acceptance, with existing NFHS development evidence used
for checkpoint selection as specified. It does not release the 225 protected
holdout/buffer positions, replace human final review, or authorize an indefinite
experiment loop. Execution was deferred to the next session by Ryan.

## Rejected or superseded approaches

- **Forcing team balance to 5/5 before resolving track contamination:** rejected because it hid raw tracker/identity switches.
- **Trusting visually plausible tracking alone:** superseded by quantitative audits and synchronized review artifacts.
- **Applying a global coordinate clamp:** rejected in favor of audited geometry and explicit boundary state.
- **Filling every missing coordinate:** rejected in favor of conservative bracketed interpolation.
- **Treating each new possession as a custom script:** rejected by the configuration-driven generalization work.
- **Beginning ball tracking before player-coordinate generalization:** intentionally blocked until Possession 003 passed.
- **Treating transient assistant ZIP links as source of truth:** rejected; use current Git, manifests, reviewed data, and hashes.

## Traceability

- Initial project purpose: Chat 01, message `29214222-c0f2-4448-bf20-7ade7be4c86a`.
- Workflow rules and ball-tracking blocker: Chat 05, message `a0b4f63f-838f-49f5-a825-e4f2bfb1f971`.
- Final clean PR #5 checkpoint: Chat 06, message `c761f593-2f9c-52d8-8bbd-5520ffa8b2c4`.
- Current committed technical authority: `docs/pipeline_generalization.md`, `src/pipeline/planner.py`, and `configs/possession_003_generalization_evidence.json`.
