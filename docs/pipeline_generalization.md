# Player-coordinate pipeline generalization

## Scope and baseline

The `possession_001` player-coordinate foundation is the reviewed behavioral
baseline. Its final coordinate coverage is 4,948/4,990 observations, with
473/499 complete ten-player frames. The 42 remaining gaps are leading
observations without a left anchor. All 22 observed outside-court positions,
including three audited interpolations, remain unchanged.

The initial source audit found 120 `possession_001` references across 26 Python
files. Sixteen runtime modules used possession-specific paths or assumptions.
Some remaining references are safe compatibility defaults in legacy tools;
critical pipeline commands now pass every possession path explicitly. The
legacy `src.identity.review_track_phases` diagnostic remains intentionally
possession-specific and is not part of the 21-stage workflow.

## Smallest configuration contract

One JSON manifest supplies the only values that should vary by possession:

- possession ID and repository-relative source video;
- reference frame (`middle` or an explicit zero-based frame index);
- expected player and team counts;
- court geometry;
- reviewed algorithm overrides for tracking, classification, ReID, identity,
  camera motion, trajectory refinement, gap interpolation, and rendering.

`PipelinePaths` derives all config and generated-output paths from the
possession ID. Generated data and media stay under `data/outputs` and remain
uncommitted. A dry run validates the manifest and displays every command:

```powershell
python -m src.pipeline.run_player_coordinates --config configs/possession_002_pipeline.json --dry-run --check-inputs
```

The plan contains 19 CLI-ready stages and two explicit human review gates:

1. identity review cycle;
2. calibration review gate.

The identity gate exposes five manifest-derived review commands. The
calibration gate records reviewed landmark corrections and fit choices. No
source-code edit is part of either review cycle.

## Resumable one-command execution

Run a new possession with one command:

```powershell
python -m src.pipeline.run_player_coordinates --config configs/possession_002_pipeline.json --run
```

The command executes stages in order and writes an ignored state file under
`data/outputs/pipeline`. Rerunning the same command skips stages whose command,
manifest, and inputs are unchanged. A failed stage is retried on the next run.
The runner stops normally at identity or calibration review and prints the
reason plus any manifest-derived review commands; after recording the human
decisions, the same `--run` command resumes the pipeline.

If a reviewed upstream decision requires deliberate regeneration, invalidate
that stage and everything downstream without deleting outputs:

```powershell
python -m src.pipeline.run_player_coordinates --config configs/possession_002_pipeline.json --run --rerun-from reid_segmentation
```

Missing ReID, identity, and sequential-review JSON files are initialized once
as possession-scoped templates. Existing review files are never overwritten.
The reviewed `possession_001` baseline is protected from execution by default.

## Generalization gate

The structural gate passes only when:

- no stage still needs a source refactor;
- every automatic or interactive stage has a manifest-derived command;
- identity and calibration are the only human review gates;
- all five identity-review helpers are config-driven;
- stage outputs are unique and possession-scoped;
- execution protects the reviewed baseline, records resumable state, and
  pauses at both human review gates.

The empirical gate remains pending until a different possession completes the
entire player-coordinate workflow without source edits. Reviewed evidence must
show:

- all stages and both review gates completed;
- exactly one homography per decoded frame;
- at least 95% player-coordinate coverage;
- at least 85% complete expected-player frames;
- zero unresolved reviews and zero coordinate-key violations;
- all outside-court positions audited;
- synchronized visual review through the final frame;
- generated outputs left uncommitted.

Evidence is a JSON object with the fields printed in the dry-run plan. Evaluate
it against the reviewed baseline with:

```powershell
python -m src.pipeline.run_player_coordinates --config configs/possession_001_pipeline.json --dry-run --gate-evidence configs/possession_002_generalization_evidence.json
```

The executor and structural gate do not by themselves unlock ball tracking.
Ball tracking begins only after the empirical gate passes.

## Baseline regression

The CPU regression checker regenerates segmentation, segment matching, and
player identity construction in the operating system's temporary directory.
It compares semantic JSON, every prototype array, and both output CSVs with the
reviewed possession outputs. It does not overwrite or retain generated files:

```powershell
python -m src.pipeline.verify_existing_player_identity --config configs/possession_001_pipeline.json
```

The GPU embedding extraction is deliberately not rerun by this check; the
reviewed existing embedding archive is its input.


## Possession 003 empirical validation

Possession 003 completed all 21 stages against frozen source commit 8bd9486. The reviewed evidence records:

- 500/500 decoded frames with a camera homography (100.00%);
- 4,921/5,000 player-frame coordinates (98.42%);
- 431/500 complete ten-player frames (86.20%);
- 10 final identities with five white and five dark players;
- zero unresolved reviews, coordinate-key violations, motion jumps, or final outside-court positions;
- synchronized visual review through the final frame;
- generated data and media remaining uncommitted.

Evidence: configs/possession_003_generalization_evidence.json.

The empirical multi-possession gate passed, so ball tracking is unlocked.
