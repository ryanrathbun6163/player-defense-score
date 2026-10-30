# WASB motion-assisted candidate comparison: completed negative result

Ryan approved one comparison after the complete `5606615` handoff with "Yes
move forward". The three longer video reviews and all previous training,
evaluation and checks remain complete. The rule below was frozen in implementation
commit `915ba13c2910efa7f875cb251b7bc049790d1df3` before evaluation.

The fixed rule does **not** establish a usable improvement. It changes no choices
on the 150 labeled development frames. Outside those windows it removes some
apparent distractors and fixes one visible selection, but also suppresses clearly
visible ball observations during recovery. Retain native-mass selection as the
development control; do not promote this motion rule or start another parameter
grid. Reliable continuous tracking remains unfinished.

## Paired labeled result

Both arms use the exact same longer-context cached candidates, with the existing
inclusive ten-source-pixel radius. These counts are matched / wrong-present /
missing / hidden alarms; the five hidden frames are separate from the 145
eligible centers.

| Scope | Native mass | Motion |
| --- | --- | --- |
| Representative: 75 eligible | 71 / 0 / 4 / 0 | 71 / 0 / 4 / 0 |
| Challenge: 70 eligible, five hidden | 60 / 1 / 9 / 0 | 60 / 1 / 9 / 0 |
| Combined | **131 / 1 / 13 / 0** | **131 / 1 / 13 / 0** |

Every scored candidate choice and center is unchanged: zero matches gained or
lost, and no hidden alarms added or removed. P003/164 remains a geometric error;
that classification alone does not prove it marks another object.

The original short-window **130 / 1 / 14 / 0** result remains intact. P002/49,
previously missing, matches at 4.531 pixels with the longer context in **both**
arms. This extra match is a context effect, not a gain from motion selection.
No training frame enters scoring. These repeatedly inspected same-game results
do not establish independent generalization.

## All changed outputs and qualitative review

Across the 1,273 visible frames, the rule makes three candidate switches and ten
new abstentions: nine changed frames in P001, two in P002, two in P003. All 13
changes are outside the scoring windows; P001/256 is a training frame. Model
points fall from 979 to 969 and missing frames rise from 294 to 304. These longer
timeline counts measure availability, not accuracy. All 294 originally empty
frames remain empty.

Fresh AI inspection covered every changed output and the named context cues:

| Frames | Observed change | Qualitative interpretation |
| --- | --- | --- |
| P001/185 | Point to missing | Removes a mark on a dark-uniform player's arm. |
| P001/230 | Candidate switch | Knee to elbow; visible ball is elsewhere. Wrong-looking to wrong-looking. |
| P001/247 | Candidate switch | Moves from overlapping players to the visible sideline ball; adjacent 246/248 corroborate its location. |
| P001/256 | Candidate switch | Possible regression from partly obscured ball near chest/hand to elbow. Training frame, unscored; partial visibility limits certainty. |
| P001/441–443 | Points to missing | Suppresses visible ball at white jersey 24's hand/hip after a false point at 440. |
| P001/462–463 | Points to missing | Again suppresses visible ball held by white jersey 24. |
| P002/454–455 | Points to missing | Removes hand/forearm distractors; airborne ball elsewhere still has no output. |
| P003/19,64 | Points to missing | Removes marks on white jersey 21's side/arm; visible ball with 24 remains untracked. |

The legitimate dribble at P002/2–3 is retained. P003/63 retains its plausible
ball point; 65 stays missing despite a partly visible ball. These are qualified
AI observations, not new reviewed annotations, error-rate estimates or human
acceptance. The lost visible-ball recovery is sufficient reason not to replace
the control with this rule, even though the short labeled windows show a tie.

## New comparison videos

Left is native mass; right is motion. Both panels retain the source scale,
synchronized player display and explicit missingness. The three videos decode
through all 499/499/500 frames, with all 225 protected frame pairs verified black.
AI inspected the decoded final images. Human review of these **new comparisons**
is pending; earlier reviews remain complete.

| Video | Useful review locations |
| --- | --- |
| [P001 comparison](../data/outputs/ball_tracking/wasb/wasb_motion_selection_v0_1/possession_001/render_attempts/0f8785fce36d465e877be937aa1ee442/comparison.mp4) | 9.88s: useful switch at 247; **17.64–17.72s and 18.48–18.52s: lost ball points**. |
| [P002 comparison](../data/outputs/ball_tracking/wasb/wasb_motion_selection_v0_1/possession_002/render_attempts/f7f6ad5e84934083b4ef8c0fc5645561/comparison.mp4) | 0.08–0.12s: retained dribble; 18.16–18.20s: removed distractors. |
| [P003 comparison](../data/outputs/ball_tracking/wasb/wasb_motion_selection_v0_1/possession_003/render_attempts/5366efc8bc4249aeaf3c9c45215373fc/comparison.mp4) | 0.76s and 2.56s: removed distractors; ball remains missing. |

The clearest recovery regression is also available as a
[three-frame detail](../data/outputs/ball_tracking/wasb/wasb_motion_selection_v0_1/diagnostics/visual/p001_root_detail_1.png).
Each possession's `review.json` binds all changed-frame stills and its final
decoded frame. Separate AI notes under `diagnostics/visual/` preserve reviewer
attribution, exact images and uncertainty; they do not rewrite render receipts.

## Execution and verification

One actual invocation completed without retry in **175.555 seconds**, including
the three comparison renders. Selection took 0.200 seconds; selection plus
scoring took 0.308 seconds. Model calls: **zero**. No weights were loaded, no
training or threshold search ran, and no old experiment was repeated.

Nineteen unique focused checks passed. The combined run passed in 2.568 seconds;
after the routine renderer correction retaining out-of-image coordinates, the
four affected renderer checks passed in 0.764 seconds. Tests cover actual
producer records, training/holdout exclusion, unchanged point-scoring semantics,
source synchronization, final/protected frames and reuse after a render failure.
No full suite ran. An initial focused-module command failed on sibling fixture
imports; discovery used the repository's expected layout. Sandbox TEMP setup
failures were preserved and the authorized outside-sandbox retries passed.

An independent saved-output audit verified all 1,498 candidate inventories,
original centers/masses/control choices, training membership, 225 protected
positions, 294 originally empty frames, 300 arm/frame geometric classifications,
and window/pool/overall arithmetic. It did not call either scientific runner or
decode media. A separate saved-history check confirms the old short-window result.

Evidence under `data/outputs/ball_tracking/wasb/wasb_motion_selection_v0_1/`:

- `invocations/20261009T035306Z_8fb1d37931dd4aef871290665d4cc97a.json`:
  successful execution, with its separate original started record.
- `summary.json`: SHA-256 `661d5084e0a709fbabfa003425e3afd0416f0f8f310904613b44226c6d63f72d`.
- `comparison.json`: SHA-256 `00b7363e636626ea4fb67f61348491c912389416753987043d9b90b1111458af`.
- `selection_completion.json` and `evaluation_completion.json`: bound source,
  configuration and outputs, saved before rendering; resumable without replaying
  completed selection/scoring.
- `diagnostics/independent_saved_output_audit_01/audit.json`: SHA-256
  `abdf1e4899de52224c887be48bfffb0e76db92873b574690fb62c90a9b0cf53e`.
- `diagnostics/visual/p001_selection_notes.json`, `p001_recovery_notes.json`, and
  `p002_p003_notes.json`: all 13 changed frames plus context cues inspected.

A crop-inspection helper initially stopped at a missing point in frame 439
after saving two crop sheets; those sheets remain, and its partial failure and
subsequent limited completion are recorded in `p001_root_detail_manifest.json`.
The actual scientific invocation was successful and was not repeated.

The next useful scientific question concerns better visual evidence for missing
balls and distractor discrimination. This comparison supplies no approval for a
new fit, weaker-candidate expansion, holdout release or another motion grid.

## Fixed rule and its limits

Use only the existing expanded-model 0.3 candidates. At each frame, predict
from the last two accepted points using constant image velocity, capped at
0.06 image diagonals per frame. With one accepted point, predict its position.
Keep candidates within 0.06 diagonals times the elapsed frames (about 132
pixels for one frame at 1920x1080), with native mass at least half the current
maximum. Choose minimum prediction distance, then greater current mass, then
lower original candidate index. These constants are engineering hypotheses,
not calibrated confidence, measured ball-speed limits or tuned results.

If no candidate qualifies, retain an explicit missing output. After three
consecutive missing outputs, discard history; the next available frame selects
maximum native mass immediately, even when it is a singleton. Every visible
segment resets history. The selector itself uses past observations only; the
unchanged WASB image evidence already contains its original future context.
No coordinates move, no gaps are interpolated, and no candidates are added.
Player context is display-only.

This can fail: a persistent nearby false point can retain the track and delay
real-ball recovery. No special exception is added for the known P001/440–441
case. Earlier RF motion and support-length studies already showed that
continuity alone cannot establish ball identity. The one fixed setting will
be reported honestly, including any lost correct points.

## Comparison and review

Preserve all source candidates, original centers/masses, native-mass choices,
new choices and per-frame decision reasons. Save all selections before reading
labels. Score both arms on the same longer-context caches at the six released
development windows: 150 frames, 145 eligible centers and five hidden frames,
with the unchanged inclusive ten-pixel radius. Independently verify that no
scored frame belongs to training. Preserve the original short-window results
separately. This is repeatedly inspected same-game development evidence.

Render three synchronized native-mass/motion comparisons with player display,
black protected bands and final-frame verification. Provide stills for every
changed frame and the previously identified distractor/recovery cues. Human
review of this new output remains necessary; old reviews remain complete.

The selector cannot fill the 294 originally empty frames. A positive result
would reduce false choices without losing correct positions, adding hidden
alarms or suppressing recovery. A negative result ends this comparison rather
than starting a parameter grid. Holdouts and their buffers remain protected.

Configuration: `configs/ball_tracking/wasb_experiments/wasb_motion_selection_v0_1.json`.
New ignored evidence: `data/outputs/ball_tracking/wasb/wasb_motion_selection_v0_1/`.
No training, model inference, checkpoint search, threshold screen, holdout
release or production operating-point promotion is part of this comparison.
