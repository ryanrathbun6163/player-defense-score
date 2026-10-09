# WASB motion-assisted candidate comparison

Ryan approved one comparison after the complete `5606615` handoff with "Yes
move forward". The three longer video reviews and all previous training,
evaluation and checks remain complete. This document freezes the new rule
before its evaluation; it does not announce a result.

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
