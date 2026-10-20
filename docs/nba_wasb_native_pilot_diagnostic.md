# Proposed NBA frozen-checkpoint pilot diagnostic

## Latest result: approved and completed on 2026-10-19

Ryan approved this exact native-cadence recipe. One run completed all 116 unique
triplets: each game matched all 60 accepted references at the fixed ten-pixel
radius, with zero wrong or missing observations. No training occurred. See the
[result and two model-output review videos](nba_wasb_native_pilot_diagnostic_results.md).
Human review of these new predictions remains pending. The proposal below is
preserved as the record of what was awaiting approval before this run.

## Historical proposal and preparation

**NOT EXECUTED. Awaiting scientific approval of this exact configuration.**

The runner is implemented. Seven initial focused checks and six affected/new
checks after review corrections passed, using synthetic records and fake model
outputs. The updated actual read-only plan confirms the 120-frame/116-triplet
scope below. Two independent code reviews found no remaining material issue.
The [preparation record](../configs/ball_tracking/reviews/nba_wasb_native_pilot_preparation_v0_1.json)
binds the current source, test evidence, accepted reference and plan; these
checks do not establish real-model performance.
Scoped Git attributes preserve the exact bytes of this increment's bound JSON,
source and test files across checkout; earlier files are not renormalized.

Ryan accepted both 60-frame AI label proposals with “looks great chat. move
forward.” The [acceptance record](../configs/ball_tracking/reviews/nba_assisted_label_acceptance_v0_1.json)
preserves AI authorship and binds the presented artifacts; it does not approve
this new model recipe. Original drafts and proposals remain unchanged.

The [runnable configuration](../configs/ball_tracking/wasb_experiments/nba_wasb_native_pilot_diagnostic_v0_1.json)
proposes one small diagnostic before more labeling or training: apply the
existing expanded WASB checkpoint to the accepted native PNGs, measure its
visible-ball observations and prepare synchronized review overlays. This checks
the new NBA input path and gives a first development result; it cannot establish
reliable NBA tracking.

| Source | Original frames | Role | Complete triplets |
| --- | --- | --- | ---: |
| SAC–MEM, `0022500829` | 660–719 | Future training candidate pool | 58 |
| SAS–DET, `0022500828` | 10788–10847 | Target-case development | 58 |

The frozen checkpoint is `09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`,
bound through its completed training receipt. Its original pretrained checkpoint
is a provenance/runtime dependency, not a second comparison arm. Selection keeps
the existing strict heatmap threshold `>0.3` and greatest native component mass.
Heatmap mass is not a probability. There is no fit, threshold search, motion
selector, tracker, external temporal context or interpolated output.

All **116 unique triplets** use consecutive original frames within their own
60-frame block. Input gaps are measured 1,440 or 1,530 ticks on the 90 kHz source
clock: **16 or 17 ms**, rather than the old NFHS inputs' 40 ms. This is a declared
native-cadence diagnostic, not a claim that the training cadence was preserved.
The source timeline is not resampled or padded, and no synthetic timestamp is assigned.
Each frame averages its aligned outputs from all available complete triplets;
the contribution counts are `1, 2, 3, ..., 3, 2, 1`. Both endpoints remain scored.

Report each game separately: matched, wrong-present and missing observations
under the fixed ten-source-pixel diagnostic radius, together with localization
distances and complete source-plus-prediction reviews. The 120 accepted rows
contain 71 fully visible and 49 partly visible balls, and **no hidden negatives**.
Hidden-ball false alarms, recovery and full trajectories therefore cannot be
measured here. The radius does not turn uncertain AI-authored centers into exact
truth, and these correlated, selected frames are not an independent benchmark.
SAC remains future-training-eligible; DET remains excluded from fitting. No
independent test game, identity/calibration acceptance or ball-phase pass is
created. The completed negative motion study and its three pending new human
reviews remain unchanged.

The runner reads the verified PNGs and bound metadata; it does not read or decode
the original game recordings. Generated caches, points, receipts and review
media stay under the ignored output root in the configuration. Preserve failed
attempts and their actual consumption. Resume compatible completed caches after
a routine delivery failure; do not repeat completed inference or reset history.
Review playback is deliberately slowed to six frames per second with a one-second
hold of the actual final frame, independently of native source timing.

From the repository root, this exact command prints a read-only plan without
loading the model, importing torch, decoding images or writing outputs:

```powershell
.\.venv\Scripts\python.exe -B -m src.ball_tracking.nba_wasb_diagnostic --repository-root . --config configs/ball_tracking/wasb_experiments/nba_wasb_native_pilot_diagnostic_v0_1.json --plan
```

Execution additionally requires `--run --approval` and an actual Ryan-approved
record bound to the exact configuration hash. No execution approval is created
by this proposal, the plan command, implementation tests or prior label acceptance.
