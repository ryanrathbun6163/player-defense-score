# Fresh-game diagnostic: reference review ready

October 30, 2026, America/Phoenix. The approved diagnostic has reached its
concrete new-reference review step. **Source selection, acquisition, AI first-
pass labels, validation and review media are complete. Human acceptance and
detector/scorer inference are pending.** No accuracy gain or failure-study
outcome is claimed from these proposals.

The [protocol](ball_tracking_fresh_game_diagnostic_protocol.md) builds on the
failed producer-transfer experiment and prior failure/acceptance/coverage work.
The saved cosine-nine detector and original all-NBA Q/J controls remain unchanged.
No new model was run, fitted or adopted. No old experiment or accepted review
was repeated. All inherited file contents and game roles are preserved.

## Delivered sample and proposals

BKN–DET game `0022400861` is outside the project's local fitting games. Its
opening-tip clip was previously previewed for source-acquisition usability;
that clip is excluded. This is a new diagnostic-development source, not a
pristine holdout or a claim of globally unseen pretraining footage.

The saved BARD catalog's numeric clip quartiles fixed **122, 237 and 365** before
new pixel inspection or predictions. Every native frame in [0,2) seconds is
retained: **120 frames per clip, 360 total**, at actual 60 fps. The sampled
plays occur in the second, third and fourth quarters. No clip was replaced or
selected because a model failed. Three event-clipped starts from one game do
not establish full-game prevalence or cross-game reliability.

| Clip | Proposed centers | Null centers | Main review focus |
| --- | ---: | ---: | --- |
| 122 | 84 | 36 | Moving pass/reception; hand, player and referee occlusions |
| 237 | 106 | 14 | Pass/receiver occlusion, reappearance and raised/held ball |
| 365 | 120 | 0 | Dribble/held ball, hand overlap and brief brightness flash |
| Total | 310 | 50 | Every original frame included |

Visibility states are **40 fully visible, 282 partially visible, 32 not visible,
and six indeterminate**. The 50 null centers comprise 32 not-visible, six
indeterminate and 12 partially visible frames without a defensible center.
All 360 are explicitly AI-authored proposals. Zero new references are accepted;
training and checkpoint-selection eligibility remain false. Hidden coordinates
were not interpolated. Current-frame visual estimates, uncertainty and source
inspection evidence remain bound to each proposal.

## Review package and checks

The complete local review is
`data/outputs/ball_tracking/fresh_game_diagnostic_v0_1/review/index.html`.
It contains three native two-second videos and three slow twelve-second videos,
all 360 marked overlays, original-pixel/overlay frame controls, label notes,
uncertainty/null listings and each actual encoded final frame. Corrections can
be identified by clip and original frame number. Source attribution is included.

All 360 PNGs match an alternate FFmpeg CLI RGB conversion byte for byte.
Both paths use the FFmpeg codec family; this is alternate transport/conversion
evidence, not an independent codec claim. Actual native PTS, source hashes,
dimensions and next-frame durations are checked without resampling.

All **12 focused validator/renderer tests passed** using unittest. They cover
pending/reference-role protection, hidden geometry, source/PTS/hash changes,
frame completeness and real synthetic encoding. An initial pytest invocation
found that pytest was unavailable; no test failure or scientific rerun followed.
All **720 emitted review frames** (360 at each rate) were decoded and checked,
including markers, color metadata and actual final frames. Every selected frame
was visually inspected for its first-pass label; independent AI reviews checked
all clip-365 closeups and focused difficult/final frames in clips 122 and 237.
Those reviews recommended no label changes and do not substitute for Ryan's
acceptance. Two clip-365 viewer-audit harness setup failures are retained and
corrected; they did not change scientific artifacts or labels.

HTTP checks found the review and media assets available. A read-only review
server is intentionally left on loopback; its current URL/PID are recorded in
`review_server.json`. The panel-open request was queued by the app; that response
is not evidence of user playback. No GPU or model process was launched.

## Exact next step and authority

Ryan should review all three complete short overlays, their unknown intervals
and actual final frames, then accept or correct this concrete reference set.
The standing [working agreement](context/working_agreement.md) says:
"They are not independent human annotations or accepted reference labels."
It assigns first-pass preparation to the assistant and reserves acceptance of
the new proposals to Ryan. This is a new-label review, not renewed permission
for the already approved experiment or a repeat of prior accepted labels.

After acceptance, publish a separate accepted-reference receipt without
rewriting the original proposals. Then implement the diagnostic capture/scoring
wrapper around the saved arithmetic and execute the already-approved frozen
comparison with current GPU readiness/supervision. At confirmed timing, the
detector budget is **354 forwards**; Q's complete candidate count is determined
and saved after capture, before scoring. J uses saved CPU weights. No training,
cutoff selection or new selector is included. The inference wrapper and
scientific result analysis have **not** been implemented/run in this increment.

Primary records live under
`data/outputs/ball_tracking/fresh_game_diagnostic_v0_1/`: `baseline155.json`,
`source_selection/selection.json`, `source_preparation.json`,
`source_pixel_audit.json`, three `sources/<clip>/proposal.json` files,
`reference_render_recipe.json`, three `review/<clip>/manifest.json` files,
`reference_package.json`, independent visual receipts and the final preservation
receipt. The maintained review ledger is
`configs/ball_tracking/reviews/fresh_game_reference_preparation_v0_1.json`.
