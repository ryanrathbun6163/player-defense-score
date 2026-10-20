# NBA action observation: results and review

The approved longer observation pass is complete and its saved outputs passed
verification. **The videos expose distractor selections and visible-ball gaps;
this is not a reliable-tracking or ball-phase pass.** Ryan's review of both new
videos is pending. His accepted short-pilot predictions remain unchanged.

Ryan approved the exact [two-core plan](nba_wasb_action_observation_plan.md):
“I approve. Move forward chat”. The separate
[approval record](../configs/ball_tracking/reviews/nba_wasb_action_observation_approval_v0_1.json)
binds the immutable proposal. Inference and rendering used committed
`4b67d0850897d539ab2994afc6349c0b6af11667`, the frozen expanded WASB checkpoint,
strict `>0.3` selection and native 16–17 ms inputs. No training, labels,
threshold search, interpolation or new accuracy scoring were added.
The [compact result record](../configs/ball_tracking/reviews/nba_wasb_action_observation_result_v0_1.json)
binds the completed outputs, audits, AI inspections and retained provenance.

## Actual execution

| Game and original source frames | Native frames | Observed | Missing | Withheld | Prior imports | New calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SAC–MEM, 540–2010 | 1,471 | 1,310 | 161 | 0 | 58 | 1,411 |
| SAS–DET, 10668–11898 | 1,231 | 1,070 | 161 | 0 | 58 | 1,171 |
| Total | 2,702 | 2,380 | 322 | 0 | 116 | 2,582 |

All 2,582 new model calls completed with zero failed or unresolved attempts.
The 116 prior pilot triplets were imported with their original identities,
bytes and attempt records; they were not reinferred. The complete 2,698-triplet
inventory stayed inside the two approved cores. Source continuity inspection
found no cut or replay requiring a split, so the full planned inventory was
used. This does not certify complete possessions or live-ball state throughout;
Detroit's opening inbound is unseen and its terminal stoppage remains included.

The [process receipt](../data/outputs/t/nba_action_implementation_2026-10-19/run_001_exit.json)
records exit 0 and **1,238.416 seconds** of wall time, about 20 minutes 38 seconds.
The runner's internal receipt records 1,237.234 seconds. Earlier bounded input
preparation took 162.884 seconds separately; the independent audit took another
27.172 seconds. The original 15–30-minute planning estimate was not a cap;
implementation and complete source/output AI review made the overall work
longer. The 20-minute-38-second figure describes the run, not that entire effort.
At 01:50 UTC, a storage snapshot counted 9.971 GiB under the new
run directory, including review diagnostics but excluding reused old PNG/cache
locations; later audit/review additions were still in progress. A sampled worker
peak working set was about 1.14 GiB and a GPU-memory snapshot was 2,053 MiB;
these are sampled resource evidence, not a continuously measured GPU peak.

**Observed/missing counts are availability, not accuracy.** A selected point
can land on a spectator or player instead of the ball, and a missing point can
occur while the ball is visible. The longer pass has no new reference labels
and no independently measured error rate.

All **112 pilot interior observations** remain identical to their original
output. Eight edge frames receive longer context: SAC 660, 661, 718, 719 and
DET 10788, 10789, 10846, 10847. Their new observations are recorded separately;
the original accepted 120/120 short-window score was not recomputed or replaced.

## Review both complete videos

- [Both videos with seekable AI review cues](../data/outputs/ball_tracking/nba/wasb_action_observation_v0_1/review_guide.html)
- [SAC–MEM: 25.541-second review, through original frame 2010](../data/outputs/ball_tracking/nba/wasb_action_observation_v0_1/sac_mem_q1_c01/review_attempts/15c8e702a51642199f6d453f369679b2/review.mp4)
- [SAS–DET: 21.537-second review, through original frame 11898](../data/outputs/ball_tracking/nba/wasb_action_observation_v0_1/sas_det_q1_c02/review_attempts/f22f738e7379465aa58223d667918219/review.mp4)
- [Combined native-paced playback and speed controls](../data/outputs/ball_tracking/nba/wasb_action_observation_v0_1/review.html)

Pink is the selected point; gold marks candidates. Missing/withheld intervals
stay explicit. The source timelines are 24.541 and 20.537 seconds; each actual
final frame receives an additional one-second hold. Watch both complete clips,
using slower playback for the flagged intervals. Report corrections or
observations by game and original frame number.

The assistant inspected all 1,471 SAC frames, including its actual decoded
final frame, and preserved [14 review cues](../data/outputs/ball_tracking/nba/wasb_action_observation_v0_1/diagnostics/model_visual_sac_01/inspection.json).
Long stretches follow the apparent ball, but recurrent switches select heads,
shoulders, arms or legs. Important examples include:

| SAC source frames | Approximate review time | AI inspection cue |
| --- | --- | --- |
| 967–998 | 7.12–7.64 s | Spectator-head and off-ball arm/shoulder selections, gaps, then apparent recovery at 998. |
| 1259–1324 | 12.00–13.08 s | Repeated held-ball gaps; the ball is visibly present in several missing-frame examples. |
| 1410–1489 | 14.51–15.83 s | Defender-head selections and repeated loss/recovery during congested action. |
| 1978–1991 | 23.99–24.21 s | Off-ball head/knee selections, then missing frames and apparent recovery before the final advance. |

The assistant also inspected all 1,231 DET frames across 31 crop/context sheets,
30 larger context panels and the actual decoded final frame. Its
[seven review cues](../data/outputs/ball_tracking/nba/wasb_action_observation_v0_1/diagnostics/model_visual_det_01/review.json)
include four confirmed qualitative distractor episodes:

| DET source frames | Approximate review time | AI inspection cue |
| --- | --- | --- |
| 10951–10953 | 4.72–4.76 s | Hands/arms near the paint selected while the ball is at the far-right recipient; apparent recovery at 10954. |
| 11023–11029 | 5.92–6.02 s | Overlapping hands/arms selected while the ball remains at the right wing; missing 11030–11046, then apparent recovery at 11047. |
| 11102–11106 | 7.24–7.31 s | An off-ball player's hand/arm selected; apparent recovery at 11107. |
| 11829–11834 | 19.37–19.45 s | Upper-right hand/forearm selected while the ball bounces lower-left; apparent recovery at 11835. |

The other DET cues cover its longest missing run, 11063–11096 (34 frames,
0.567 seconds), repeated gaps during the drive/near-rim action at 11437–11557,
and the final visible-ball sequence through frame 11898. Blur and occlusion
leave some near-rim intervals uncertain. Both actual final frames were inspected.
These qualitative notes do not supply human acceptance or turn observations
into reference labels. **Ryan's review of both longer videos remains pending.**

## Saved-output and media verification

The independent [actual saved-output audit](../data/outputs/ball_tracking/nba/wasb_action_observation_v0_1/diagnostics/independent_audit_01/audit.json)
passed on its first attempt in 27.172 seconds, with 687,915 structural/numerical
checks, 8,157 file bindings and zero issues. It independently reconstructed:

- all 2,702 aligned float32 mean heatmaps from the 2,698 actual NPZ caches;
- all 2,711 final components and every selected point or missing state;
- native source-frame/PTS joins, availability counts and timed intervals;
- source/model identity, original start/receipt records, 116 imports and the
  unchanged 112 pilot interiors versus eight longer-context edges.

Both renderers decoded and verified every new video frame against its source
overlay, including encoded source-frame keys, native PTS/durations and final
holds. Maximum whole-image RGB mean absolute errors were 3.323705 for SAC and
3.543898 for DET, below the declared limit of 8. Actual final-frame errors were
2.794446 and 3.451360. The independent audit checked the bound verification
receipts, stored ffprobe records and complete review-manifest joins; it did not
repeat those full media decodes. It made no model calls and scored no labels.
These checks establish artifact integrity and transport, not ball accuracy.

The inherited adapter's provenance describes its unused default `>0.5`
per-triplet components. The actual runner consumes heatmaps, averages aligned
contributions and recomputes final components at strict `>0.3`. The independent
audit verified that final path and retained the original adapter metadata.

## Implementation validation and retained history

Twenty-three distinct focused checks passed: seven native-input, twelve
observation and four review checks. This is a count of distinct checks, not
total invocations. Actual synthetic media checks exercise native-PTS extraction,
rendering and final holds; producer-derived cache fixtures exercise imports,
aggregation, preserved failed attempts/resume and boundary handling. The full
suite and earlier scientific experiments were not repeated.

The [validation record](../data/outputs/t/nba_action_implementation_2026-10-19/validation_receipt.json)
and [later addendum](../data/outputs/t/nba_action_implementation_2026-10-19/validation_addendum.json)
preserve the actual code/test versions. Initial failures were the system Python
missing NumPy, a synthetic reference-publication path outside `data/outputs`,
and an approval consumer comparing full proposal windows instead of their
approved field projection. Corrections passed the affected checks. A separate
DET visual-inspection helper import failed before image reads. These attempts
remain recorded; none was a failed scientific model call.

Preparation loaded an initial `nba_action_inputs.py` snapshot with SHA-256
`ee20bea139aa639806ab79739ec7572066433a04fd8f8a7608e078531c3c2842` after six input
checks. Recovery/pre-decode source-stat safeguards were then edited on disk
while that process ran; a later start receipt therefore hashes the new disk
file rather than the already loaded helper. The exact loaded snapshot and
[provenance explanation](../data/outputs/ball_tracking/nba/wasb_action_observation_v0_1/diagnostics/helper_loaded_provenance_01/provenance.json)
remain preserved, with original receipts unchanged. Fresh extraction commands,
PTS/RGB checks and successful output construction were unchanged. Seven input
checks passed on the later helper. Preparation also used an earlier runner
version; later runner changes concerned post-preparation/inference handling.
Inference and rendering used the committed
`4b67d08` source; the note required no repeated source decode.

## Limits and next action

Ryan reviews both complete new videos and their flagged intervals next. The
current model has useful stretches but unresolved distractor and coverage
failures. Completing this observation does not approve a new experiment, fit
or method promotion. A later change should target these visible weaknesses
with an exact scope and retained uncertainty.

SAC remains future-training-eligible; DET remains target development and
excluded from fitting; TOR is outside this pass. There is no independent test
game, certified complete-possession result, NBA identity/calibration acceptance
or ball-phase pass. The NFHS finish line, protected holdouts, negative motion
result and its three pending new human reviews remain unchanged. Detailed
outputs, media and caches stay ignored and uncommitted.
