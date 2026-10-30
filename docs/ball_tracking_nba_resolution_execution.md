# Approved NBA resolution experiment

Ryan approved the [concrete proposed experiment](ball_tracking_nba_resolution_experiment.md)
on October 26, 2026 (America/Phoenix): **"ok move forward with the experiment chat"**.
Base branch `codex/ball-detector-baseline`, HEAD
`70409dd35cbea3cfedfc94287acf005cb2e2c42a`, initially clean.
This approval authorizes preparation, the disposable readiness check, the fixed
five-epoch 768x432 fit, all five NBA comparisons and high-school regression
evidence. It does not authorize new labeling, an extension, method adoption or
protected evaluation. The earlier proposal remains preserved as proposed then.

## Fixed scientific scope

The new recipe binds the original training package, first five schedule epochs,
completed augmentation control and exact implementation bytes. Start from the
same retained `09da1214...` checkpoint with fresh Adam, seed 1234, batch two,
float32 and frozen BatchNorm buffers. Use the same synchronized mirror/brightness
draws, loss, 75% NBA / 25% NFHS mixture and 7,760-update budget. The resolution
is 768x432, with target radius 3.75 working pixels preserving the nominal
source-space footprint. Native PNGs are resized directly into a separate cache.
No existing frozen file or reviewed reference is rewritten.

The disposable readiness check uses three synthetic optimizer steps on a
separate model to verify actual forward/backward shapes, finite gradients,
optimizer-state memory and unchanged BatchNorm buffers. It saves no model and
counts zero scientific updates. The fit subsequently initializes afresh.
All attempts and telemetry remain under ignored experiment paths. If the
approved configuration cannot run, preserve the failure rather than silently
changing batch size or precision.

Recompute epoch zero at the new resolution; a 512 result cannot represent a
768 baseline. Train all five epochs regardless of the superseded NFHS selection
veto. Save each epoch and resumable optimizer/RNG states every 25 updates.
Evaluate the existing validation blocks each epoch, then all five epochs on
the full eight permitted NBA contexts, reusing exact HOU validation observations.
SAC is training-exposed; HOU/DET remain development evidence. Preserve unknowns,
censored intervals and the complete per-episode reports.

All original accuracy, wrong-output, hidden-output, continuity, wrong-object,
recovery and human-review requirements remain unchanged. No checkpoint is
automatically adopted. If every computable NBA gate is satisfied, the earliest
qualifying epoch proceeds to synchronized human review; otherwise publish the
failure and partial progress without another fit. Full accepted trajectories
and protected evaluation remain separate gates.

## Environment and preservation

Lively Wallpaper and MSI True Color had restarted before preparation. Lively
was stopped; Windows denied this session permission to stop elevated MSI True
Color. Ryan closed it and confirmed that action; a subsequent process check
found neither application nor NVIDIA Overlay running. No GPU work preceded that
confirmation. The initial GPU was idle at 27 C. No hardware settings were changed.
The existing supervisor monitors the owned workload and stops on its device,
thermal or telemetry conditions. A successful run is not proof that earlier
PC blackouts have been resolved.

## Completed preparation

Thirty-eight focused tests pass: seven resolution-primitive checks, seven
training/recovery checks, seven NBA producer/consumer checks and seventeen
unchanged scoring checks. The real 4,439-frame training/validation cache is
prepared from accepted native PNGs; 114 first/middle/final triplets match an
independent direct native warp and normalization exactly. An initial audit's
bit-exact comparison of `512/source * 1.5` and `768/source` failed on a float64
rounding difference of 1.11e-16; the preserved second attempt uses the direct
dimension ratio and verifies actual image tensors. No production geometry was
changed to satisfy that check. Earlier corrected synthetic fixture failures are
also preserved, separately from scientific execution.

The disposable readiness check passed all three steps, verified unchanged
BatchNorm buffers and original checkpoint bytes, and saved no model. It took
8.281 supervised seconds, peaking at 42 C / 81.47 W / 6,980 MiB. After the last
step, CUDA reported 5,898,240,000 free device bytes. No batch-size or precision
adjustment was needed. The recipe binds the completed readiness, telemetry and
actual-input parity records as well as exact implementation bytes.

Implementation, readiness, fit, comparison and visual-delivery results will be
recorded separately. The prior proposal's 45-75 minute training and 10-15 minute
NBA-inference ranges are estimates; measured resource consumption supersedes
them. Preserve failed attempts and replayed work rather than resetting history.
