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

## Current operating policy — Ryan's 2026-10-08 instruction

This standing policy supersedes conflicting older operational instructions in this repository, including mandatory full-suite runs, stop-on-failure rules, recovery proposals, certificate procedures, arbitrary resource caps, and blanket scientific-body read bans. Historical records remain evidence of what was authorized and done at that time; they do not impose new approval gates on routine work now.

- Complete routine path, formatting, report-size, tooling, and implementation fixes autonomously. Read and compute the development results needed to answer Ryan's question, including recovering existing results after a delivery failure. Do not require a new recovery proposal or routine RED/GREEN certificate sequence.
- Use the computer and data resources reasonably needed for the work, with practical memory, disk, process-ownership, and cleanup safeguards. Adjust arbitrary operational limits when needed; do not spend repeated runs or complex release machinery merely satisfying an obsolete cap.
- Test in proportion to risk. Use focused checks for local changes; run the full suite when the change's reach or unresolved risk justifies it. Do not repeat a completed full run for a routine fix or merely to resume.
- Preserve failed attempts, consumed resources, original evidence, uncertainty, and completed reviews. Never reset history, turn a failed run into a successful one, or imply that an earlier test run covered later code. Keep holdouts separate from development decisions and retain human visual-review gates.
- Simplify delivery and integrate completed increments into the active project. Bring substantial scientific, architectural, evidence-integrity, safety, or cost tradeoffs to Ryan for approval; explain routine corrections briefly and continue.

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

Treat editing, validation, staging, committing, pushing, PR creation, and merging as distinct steps. Apply Ryan's existing session or standing authorization to local integration without repeatedly asking for the same permission. If local staging or committing has not been authorized, obtain that authorization. Pushing, PR creation, and merging require explicit authorization; never push directly to `main`.

Before any Git mutation, report the current branch, HEAD, worktree status, and intended file scope. Afterward, verify the exact result.

## How to work with Ryan

Ryan has a software-engineering degree and professional technical experience but is refreshing Python, computer vision, ML, and Git workflows. Explain unfamiliar terms in plain language and connect each command to its purpose. Prefer one copyable PowerShell command when Ryan must run something manually, with guards that confirm the repository, branch, HEAD, inputs, and expected outputs.

Do not assume a command was run merely because it was provided. Confirm terminal output or inspect the resulting files. Visual judgments remain Ryan's decisions; provide the exact frames, videos, or evidence to inspect.

## Validation expectations

For relevant code changes:

- run focused checks appropriate to the change; run the full suite only when broader risk warrants it;
- for changes that consume another component's records, derive critical fixtures from the producing code or an explicitly authorized captured record; verify producer and consumer fields independently;
- add a useful regression check when the failure merits one; a mandatory pre-fix RED run, certificate chain, or separate validation proposal is not required for routine corrections;
- when record transport is the risk, check the actual emitted record against its consumer instead of relying only on a fixture that mirrors the implementation;
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

Ryan's October 25 instruction makes NBA footage the primary ball-tracking milestone, preserving all high-school evidence and the same numerical and visual quality criteria. Existing accepted labels are complete; do not restart labeling or request those approvals again. The October 26 paired continuation sequence, diagnostics and authorized two-epoch spatial pilot are complete; see `docs/ball_tracking_wasb_spatial_results.md` for the latest result. Neither spatial checkpoint passes; both retain the 19-frame DET gap. Spatial seven has 218/241 DET correct and two wrong, HOU 842/882 correct with 20 certain-hidden emissions. SAC and secondary NFHS gains do not offset NBA failures. Do not extend the unchanged spatial recipe automatically. Same-epoch paired review is diagnostic, not adoption. Nine source-uncertain recovery events remain inconclusive independently of training; preserve this evidence limitation and pending human trajectory review. High-school results remain secondary regression evidence, and original rejection decisions, frozen code, failures and reviewed baselines remain unchanged. Protected evaluation stays closed pending a frozen method and separate explicit authorization. NBA player-coordinate, identity and calibration validation remain future work; the high-school player-coordinate gate does not certify NBA footage.
