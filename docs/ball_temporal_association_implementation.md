# Temporal-association implementation checkpoint

The saved-detection experiment now has separate association, evaluation,
manifest/runner, and visual-review support. It compares the existing raw
candidates, a highest-confidence control, and four tracklet settings at each
of nine confidence thresholds: 54 variants per window. Six windows produce
324 observation files; scoring produces 1,620 per-window reports and two
separate pools of 270 aggregate cells each. These are expected output counts;
real association, scoring, and rendering have not run yet.

Ryan's "lets move forward" response to the linked design authorizes this
experiment. The approval receipt binds the concrete specification to that
design and the six immutable development detection files. The design remains
unchanged as the approved historical proposal. Git actions remain separate.

## Behavior and provenance

- A new tracklet needs two consecutive observations. Its first provisional
  observation is never backfilled. Missing frames have no emitted coordinate.
- Associations retain original candidate indices, geometry, and detector
  confidence. The derived contract separately records tracklet decisions,
  links, confirmation, expiry, input hashes, and association code commit.
- The association stage does not open annotation JSON, source videos, player
  tracks, or court geometry. Scoring opens the frozen reviewed labels later.
- Matching uses the existing raw-distance rule. Annotation uncertainty is
  retained in diagnostic error summaries and does not enlarge the match radius.
- Raw-arm TP/FP/FN/precision/recall match the established evaluator in synthetic
  regression tests. Derived report input counts describe emitted observations,
  while every raw candidate disposition remains in the association audit.
- Outputs are created atomically and reused only if their bytes match the
  deterministic result. Changed existing outputs are refused. There is no force
  overwrite option, detector rerun, window expansion, or holdout access.
- Review renders both controls and all four tracklet variants at confidence
  0.20 and 0.35, radius 10. Native overlays and unmarked source closeups accompany
  the six-panel context videos. Every source frame and final frame is retained.
  New temporal evidence will require Ryan's visual judgment after execution.

The implementation is outside the existing player pipeline. It changes no
reviewed upstream decision and needs no player-pipeline `--rerun-from` step.
No operating point, quality gate, detector winner, or complete-trajectory claim
is selected.

## Validation

The focused suite covers confirmation, causal behavior, competing edges and
ties, short/expired gaps, state reset, absent observations, wrong high-confidence
candidates, hidden-frame false alarms, raw scoring compatibility, input/output
tampering, exact window scope, embargo refusal, and resumability. It also runs
all 324 observation outputs and both scoring pools on synthetic candidates,
and renders/decodes a complete synthetic review bundle through its final frame.

The agent inspected synthetic comparison and closeup images. That inspection
prompted larger video-panel headings and offset tracklet labels. It is not a
human review of real temporal output. The first full-suite run was deliberately
stopped after this rendering change; only final-code validation counts below.

Final validation results are recorded in `docs/context/current_state.md` and
the ignored `data/outputs/ball_tracking/temporal_implementation_validation/`
directory. The final focused suite passed 25 tests; the full suite ran 324:
323 passed, one existing directory-symlink capability skip. Formatting, JSON,
Python syntax, and exact staging-scope checks passed. Real-data dry-run passed
for six windows, 150 frames, and 54 variants.
All 59 prior protected files, six saved detection files, and nine absent parent
prediction paths were reverified. Real temporal output remains absent.

## Exact proposed staging scope

Branch: `codex/ball-detector-baseline`.
HEAD: `84bcc8da143e54ff17a28b39db0e70c4b8b299c8`.
Index is empty. Preserve the existing documentation and visual-review work
included here. The following 13 files form one narrowly scoped implementation
checkpoint; no generated media or results are included.

```text
configs/ball_tracking/reviews/rfdetr_medium_development_candidate_comparison_review_record_v0_1.json
configs/ball_tracking/reviews/rfdetr_medium_temporal_association_approval_v0_1.json
configs/ball_tracking/temporal_experiments/rfdetr_medium_temporal_association_v0_1.json
docs/ball_temporal_association_experiment_proposal.md
docs/ball_temporal_association_implementation.md
docs/context/current_state.md
docs/context/roadmap.md
docs/context/validation_history.md
src/ball_tracking/temporal_association.py
src/ball_tracking/temporal_evaluation.py
src/ball_tracking/temporal_experiment.py
src/ball_tracking/temporal_review.py
tests/test_ball_temporal_association.py
```

## Execution after separately authorized staging and commit

The runner requires a clean committed feature-branch checkpoint. The commands
below are documented for that future checkpoint; only the dry-run command has
been executed on the current worktree. Run all three stages at the same new
commit before editing documentation. They preserve the original detector commit
inside the derived evidence rather than rewriting it.

```powershell
.\.venv\Scripts\python.exe -B -m src.ball_tracking.temporal_experiment --manifest configs/ball_tracking/temporal_experiments/rfdetr_medium_temporal_association_v0_1.json --repository-root . --dry-run
.\.venv\Scripts\python.exe -B -m src.ball_tracking.temporal_experiment --manifest configs/ball_tracking/temporal_experiments/rfdetr_medium_temporal_association_v0_1.json --repository-root .
.\.venv\Scripts\python.exe -B -m src.ball_tracking.temporal_review score --manifest configs/ball_tracking/temporal_experiments/rfdetr_medium_temporal_association_v0_1.json --repository-root .
.\.venv\Scripts\python.exe -B -m src.ball_tracking.temporal_review render --manifest configs/ball_tracking/temporal_experiments/rfdetr_medium_temporal_association_v0_1.json --repository-root .
```

Do not repeat the already received experiment or detector-comparison approval.
Do not infer permission to stage, commit, push, select an operating point, set a
quality gate, or release holdouts from the experiment authorization.
