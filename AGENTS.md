# Player Defense Score — Agent Instructions

## Purpose

This repository builds an auditable computer-vision and basketball-analytics pipeline that will ultimately assign transparent possession-level defensive value. The initial case study is Stephon Castle defending Cade Cunningham in the February 23, 2026 Spurs–Pistons game.

The player-coordinate foundation is complete for three curated possessions. Possession 003 passed the multi-possession empirical gate. Ball tracking is the next major phase; possession understanding, NBA roster identity, matchup inference, defensive scoring, and full-game validation are not complete.

## Required reading before substantive work

Read, in order:

1. `README.md`
2. `docs/pipeline_generalization.md`
3. `docs/context/current_state.md`
4. `docs/context/decisions_and_invariants.md`
5. `docs/context/working_agreement.md`

Consult `docs/context/validation_history.md`, `roadmap.md`, and `source_map.md` when the task touches those subjects.

## Source-of-truth order

When sources disagree, prefer:

1. current Git state, code, tests, and committed manifests;
2. committed reviewed evidence and audit reports;
3. current ignored local data and generated outputs;
4. the curated `docs/context/` record;
5. archived browser transcripts and attachment manifests;
6. historical assistant-generated ZIP links.

Never infer that an old command, artifact link, branch, or checkpoint is still current. Verify the actual repository state first.

## Non-negotiable engineering rules

- Preserve uncertainty. Missing data is better than fabricated certainty.
- Keep identity reconciliation and court calibration as explicit human-review gates.
- Keep generated videos, model outputs, CSV/NPZ artifacts, and copyrighted footage uncommitted.
- A new possession should require configuration and review decisions, not possession-specific Python edits.
- Do not weaken the Possession 001 baseline or the empirical generalization thresholds to make a new run pass.
- Preserve possession-scoped paths, resumability, provenance fields, audit trails, and final-frame visual review.
- Before changing an upstream reviewed decision, identify the correct `--rerun-from` stage and downstream effects.
- Do not silently overwrite an existing reviewed config or generated baseline.
- Keep `main` clean. Use a narrowly scoped feature branch for changes.

## Git authorization boundary

Treat editing, validation, staging, committing, pushing, PR creation, and merging as distinct steps. Do not stage, commit, push, create a PR, or merge unless Ryan explicitly asks for that step. Never push directly to `main`.

Before any Git mutation, report the current branch, HEAD, worktree status, and intended file scope. Afterward, verify the exact result.

## How to work with Ryan

Ryan has a software-engineering degree and professional technical experience but is refreshing Python, computer vision, ML, and Git workflows. Explain unfamiliar terms in plain language and connect each command to its purpose. Prefer one copyable PowerShell command when Ryan must run something manually, with guards that confirm the repository, branch, HEAD, inputs, and expected outputs.

Do not assume a command was run merely because it was provided. Confirm terminal output or inspect the resulting files. Visual judgments remain Ryan's decisions; provide the exact frames, videos, or evidence to inspect.

## Validation expectations

For relevant code changes:

- run focused tests first, then the full test suite;
- use `PYTHONDONTWRITEBYTECODE=1` or remove newly generated `__pycache__` directories;
- keep generated test/output artifacts outside Git;
- run `git diff --check` before proposing staging;
- compare quantitative reports with the reviewed baseline;
- require synchronized visual review when geometry, identity, trajectories, or ball tracking changes.

The current full test command is:

```powershell
python -m unittest discover -s tests -v
```

## Immediate next milestone

Build an auditable ball-tracking foundation across multiple curated possessions. Begin with evaluation design and representative labeled clips, then compare detector/tracker approaches, preserve confidence and missingness, render synchronized player/ball review output, and define quantitative plus visual quality gates before building possession or matchup inference.
