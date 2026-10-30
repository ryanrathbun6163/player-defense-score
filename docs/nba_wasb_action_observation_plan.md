# NBA action observation plan

**Current status: approved pass completed; both video reviews reported complete.** Ryan
approved the exact longer plan: “I approve. Move forward chat”. The separate
[approval record](../configs/ball_tracking/reviews/nba_wasb_action_observation_approval_v0_1.json)
binds the unchanged proposal and authorizes implementation, focused validation
and one resumable pass. Implementation was committed as
`4b67d0850897d539ab2994afc6349c0b6af11667`; 23 distinct focused checks passed.
The full suite was not repeated. One run completed 2,582 new model calls and
imported all 116 prior triplets, with zero failed or unresolved calls. The
[result and review report](nba_wasb_action_observation_results.md) records the
2,380 observations, 322 missing frames, passed saved-output/media checks and
qualitative concerns. This does not establish reliable longer ball tracking.
After both complete videos were delivered in chat for phone viewing, Ryan
reported: “Ok reviewed. What’s the next step”. The later
[visual-review record](../configs/ball_tracking/reviews/nba_wasb_action_observation_visual_review_v0_1.json)
records completion without playback telemetry, explicit quality endorsement or
new experiment authorization. Original result records and media are preserved.

Ryan accepted both complete [native pilot prediction videos](nba_wasb_native_pilot_diagnostic_results.md)
on October 19. The model matched all 120 accepted reference points, but each
pilot covers only about one source second with the ball visible. The next
useful question is whether the same frozen model remains useful through a
longer action: a shot, rebound, player overlap and recovery after a gap.

The [exact proposal record](../configs/ball_tracking/selections/nba_wasb_action_observation_proposal_v0_1.json)
retains its historical design-only, pending status. The later approval above
supersedes that status without rewriting the original decision artifact. Its
scope remains the two already selected action cores. Approval covers routine
implementation work together with the run; mechanical fixes do not need an
additional permission step.

## Exact footage and workload

| Game | Original source frames, inclusive | Native frames | Playback duration | Maximum complete triplets | Prior triplets reused | Maximum new calls |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Kings–Grizzlies | 540–2010 | 1,471 | 24.541 s | 1,469 | 58 | 1,411 |
| Spurs–Pistons | 10668–11898 | 1,231 | 20.537 s | 1,229 | 58 | 1,171 |
| Total | Two fixed cores | 2,702 | 45.078 s | 2,698 | 116 | 2,582 |

Playback durations include the last frame's native display interval. The
first-to-last timestamp spans are 24.524 and 20.520 seconds respectively.
The count maxima assume no internal scene split. Inspect source continuity
before inference and explicitly split at any confirmed cut or replay boundary.
No three-frame input may cross such a boundary. Withhold frames that cannot
receive a complete input within their segment, record the reduced counts and
reasons, and do not extend these source ranges to replace them.

These are selected action cores, not certified complete possessions. The
Detroit opening inbound is hidden by a closeup, and Sacramento's exact
possession boundaries have not been accepted. This pass does not certify
possession ownership, player identity, court calibration or defensive roles.

## Frozen model and honest missingness

Use the same expanded WASB checkpoint as the accepted pilot, with strict
heatmap threshold `>0.3`, largest-component-mass selection and the same stable
tie rule. Each input contains three consecutive original RGB frames at native
16–17 ms spacing. Average aligned outputs from every available complete
triplet for each frame. Retain candidates, confidence semantics, contribution
counts and explicit missing or withheld states.

There is no new training, threshold search, motion selector, interpolation,
padding, resampling or model context outside the two cores. No new labels or
accuracy scoring are proposed. A point's presence means the model emitted an
observation; it does not establish that the point is on the ball.

The 116 compatible completed pilot triplets are imported with their original
identities, bytes and attempt records. Do not recompute them. A missing or
incompatible old cache requires investigation, not silent replacement. Reuse
the 120 original pilot PNGs unchanged and extract the other 2,582 native frames
to new ignored paths. Original recordings are read only through bounded
seeks/decodes for these cores and necessary decoder preroll, without another
full-game decode or full-source rehash. Existing full-source audits and
unchanged source size/timestamps, exact frame maps, extracted PTS and RGB
hashes provide the source bindings.

Longer context adds neighboring triplets at each short pilot's edges. Eight
pilot frames may therefore have different averaged outputs: SAC 660, 661, 718,
719 and DET 10788, 10789, 10846, 10847. The 112 pilot interior means should
remain identical if no new scene boundary changes their input context. Preserve
excluded old triplets without reinference and report boundary-related context
differences separately. Preserve the original accepted 120/120 short-context result
and its videos; any longer-context changes belong to the new observation.

## Reviewable result

Produce two complete source-plus-model videos paced by the original timestamps,
with a declared one-second final-frame hold and slower-playback controls on a
combined review page. Preserve each frame's original number and timestamp.
Show gaps plainly, without an invented trail through them or fabricated
reference points outside the accepted pilots.

The assistant inspects the complete timelines and identifies exact source
frames for missing intervals, distractor switches and recoveries. Ryan then
reviews both actual new videos through their final frames. Summaries describe
observed, missing and withheld frames and intervals; they are availability
counts, not an accuracy benchmark. New trajectories are not accepted merely
because the earlier pilot predictions were accepted.

## Implementation, validation and resources

Before a real run, verify native frame extraction and rendering with synthetic
timestamped media. Derive cache-import checks from the actual producer's
record format, verify old source/model bindings, and check that streaming
averages preserve the original float32 accumulation order, endpoint behavior
and scene boundaries. Focused checks must cover scope changes, resume behavior,
preservation of failed attempts, and refusal to reinfer completed old inputs.
Run tests in proportion to the changed components; this plan does not require
a repeat of the full suite by default.

Use a rolling image buffer and unfinished output sums, one owned model worker,
atomic completed caches and streamed video encoding. Check current disk, RAM,
GPU and process ownership before starting. Preserve every actual attempt and
consumed resource; resume compatible completed work without resetting history.

Based on the existing PNG/cache sizes, new frames and compressed caches are
estimated at **9.28 GiB**, plus videos and receipts. Extrapolated model-call time
is about 62 seconds; extraction, verification and review preparation make
**15–30 minutes** a working end-to-end estimate. These are estimates, not
measured longer-run results or hard caps. Keep detailed outputs ignored beneath
`data/outputs/ball_tracking/nba/wasb_action_observation_v0_1/`; commit only
source, tests, configuration and compact evidence.

The completed inference/render run took 20 minutes 38 seconds, with earlier
input preparation and later audit measured separately. Implementation and
complete source/output AI review made the overall effort longer than the
15–30-minute planning estimate. The estimate was not a resource cap.

The original proposal preparation made no model calls, raw-video decodes,
labels or tests. One
additional read-only feasibility check repeated existing hash, metadata and
array-validity checks on the 116 completed cache records, with zero issues.
It did not rerun inference, source decoding or scoring; its duration was not
measured.

## Boundaries retained

SAC remains the future-training candidate pool; DET remains target-case
development and excluded from fitting. TOR is outside this pass. No game is
reclassified as an independent test. The original NFHS finish line—reviewed
trajectories across the three curated possessions, synchronized player/ball
playback, explicit gaps, quantitative error summaries and a repeatable run—
remains unchanged. Protected holdouts, the negative motion-selection result
and its three pending new human reviews remain intact.

Approval, execution, saved-output/media verification and user-reported video
review of this exact scope are complete. The next decision is the separate
[hard-example reference proposal](nba_hard_example_reference_plan.md): 520 new
AI-proposed labels, human reference-overlay acceptance, then scoring of saved
observations with 120 existing pilot references as separate longer-context easy
controls. This proposal is design-only and leaves the original pilot score
unchanged. Review completion does not authorize new labels, scoring or a fit,
and does not establish ball-phase completion.
