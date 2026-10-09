# Approved additional training labels

Ryan approved 75 additional training frames and one 200-update fit on 2026-10-08.
The [approval record](../configs/ball_tracking/reviews/wasb_training_data_expansion_approval_v0_1.json)
supersedes the prepared proposal's historical pending status. The new fit is
authorized after these labels are completed and visually reviewed. The six model
output clips already reviewed remain complete.

## Current step: review the completed labels

All 75 frames are now labeled: 64 have ball centers and 11 mark the ball as hidden.
At Ryan's direction, eight `camera_motion` tags were corrected to `motion_blur`;
the original snapshots and changes are preserved in the
[correction record](../configs/ball_tracking/reviews/wasb_training_expansion_tag_correction_v0_1.json).
Older reviewed training and development labels contain no `camera_motion` tags.

Review these three five-second clips, including each final frame:

1. [P001, frames 100–124](../data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/training_expansion_labels_v0_1/visual_review/possession_001_frames_0100_0124_training_expansion_v0_1/label_review_5fps.mp4).
2. [P001, frames 250–274](../data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/training_expansion_labels_v0_1/visual_review/possession_001_frames_0250_0274_training_expansion_v0_1/label_review_5fps.mp4).
3. [P002, frames 343–367](../data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/training_expansion_labels_v0_1/visual_review/possession_002_frames_0343_0367_training_expansion_v0_1/label_review_5fps.mp4).

The cyan mark is the saved ball center; the yellow circle is uncertainty in that
center, not the ball's outline. A partially visible label estimates the complete
ball center. Hidden frames intentionally have no point. Check placement,
visibility and the transitions through occlusion. These are your labels, with
no model predictions. Tell Codex whether all three are acceptable or give the
possession and frame numbers that need corrections.

Each video's adjacent `native` and `zoom` folders contain every frame. The zoom
panels pair raw pixels with the annotation at 4× magnification. Useful closer
checks include [P001/258](../data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/training_expansion_labels_v0_1/visual_review/possession_001_frames_0250_0274_training_expansion_v0_1/zoom/frame_000258.png)
and [P002/355](../data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/training_expansion_labels_v0_1/visual_review/possession_002_frames_0343_0367_training_expansion_v0_1/zoom/frame_000355.png),
where the saved center uncertainty is larger. P001/253 and P002/343–346, 349–354
are labeled hidden; verify their transitions in playback.

All three clips were decoded through their 25 frames and final frame. The
[asset manifest](../data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/training_expansion_labels_v0_1/visual_review/manifest.json)
binds the rendered media to the corrected annotation files. Their `draft` status
is intentional until human visual review is recorded. The approved fit has not
started; its authorization remains valid after this review.

## Original annotation workflow

Run this one command in PowerShell. It opens the existing annotation editor for
each unfinished clip in sequence and checks the repository, branch, saved HEAD,
approval, source files and frame ranges first.

```powershell
& 'C:\Users\Ryan\Projects\player-defense-score\.venv\Scripts\python.exe' -B 'C:\Users\Ryan\Projects\player-defense-score\data\outputs\ball_tracking\wasb\wasb_basketball_adaptation_v0_1\annotation_session_v0_1\annotate_expansion.py'
```

The drafts are:

1. P001 frames 100–124: left-side handling and hand/body overlap.
2. P001 frames 250–274: left-side pass/receive/handling with a different background.
3. P002 frames 343–367: continuation after the old training occlusion.

All 75 rows originally began unlabeled and have now been filled by Ryan. No
predicted locations or invented visibility labels were inserted. The helper seeks
directly to each approved source window and
shows source images only. It reuses the existing editor and does not run a detector.
One input check loaded and decoded all 75 approved frames in the editor's RGB
format, with all draft bytes unchanged. It did not open the GUI or enter labels.

## Labeling and resume

Use the existing visibility, identity certainty and difficulty fields. Left-click
the best complete-ball center where a center is defensible. Right-click the
farthest alternate center you consider plausible to set its uncertainty radius.
For a hidden ball, preserve the missing geometry; uncertainty is preferable to a
guessed point. The existing protocol's ambiguity and exclusion rules still apply.

**Ctrl+S** saves the frame and advances. After saving the last frame, close that
editor window to continue to the next clip. If you close a clip before finishing,
the helper stops; rerun the same command to resume from its first unlabeled frame.
Completed drafts are skipped without resetting them.

The completed label overlays and playback are linked above. After their visual
review, Codex will freeze the reviewed label bindings and run the already-approved
single fit. The original annotations,
evaluation windows, holdouts, checkpoint and previous results stay separate.

The source-only previews remain linked from the
[prepared data proposal](ball_wasb_training_data_expansion.md). Watching those
previews does not substitute for placing and reviewing the new frame labels.
