# Approved additional training labels

Ryan approved 75 additional training frames and one 200-update fit on 2026-10-08.
The [approval record](../configs/ball_tracking/reviews/wasb_training_data_expansion_approval_v0_1.json)
supersedes the prepared proposal's historical pending status. The new fit is
authorized after these labels are completed and visually reviewed. The six model
output clips already reviewed remain complete.

## Completed label review

Ryan approved all three clips on 2026-10-08: "yep these look good. move forward chat".
The [human review record](../configs/ball_tracking/reviews/wasb_training_expansion_label_review_v0_1.json)
preserves the exact reviewed drafts, video bindings and reviewed annotation
files. Only review metadata changed. The approved fit and comparison have now
completed; see [expanded model results](ball_wasb_expanded_adaptation_results.md).
No repeat of this completed label review is needed.

All 75 frames are now labeled: 64 have ball centers and 11 mark the ball as hidden.
At Ryan's direction, eight `camera_motion` tags were corrected to `motion_blur`;
the original snapshots and changes are preserved in the
[correction record](../configs/ball_tracking/reviews/wasb_training_expansion_tag_correction_v0_1.json).
Older reviewed training and development labels contain no `camera_motion` tags.

The three reviewed five-second clips, including their final frames, remain here:

1. [P001, frames 100–124](../data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/training_expansion_labels_v0_1/visual_review/possession_001_frames_0100_0124_training_expansion_v0_1/label_review_5fps.mp4).
2. [P001, frames 250–274](../data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/training_expansion_labels_v0_1/visual_review/possession_001_frames_0250_0274_training_expansion_v0_1/label_review_5fps.mp4).
3. [P002, frames 343–367](../data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/training_expansion_labels_v0_1/visual_review/possession_002_frames_0343_0367_training_expansion_v0_1/label_review_5fps.mp4).

The cyan mark is the saved ball center; the yellow circle is uncertainty in that
center, not the ball's outline. A partially visible label estimates the complete
ball center. Hidden frames intentionally have no point. Check placement,
visibility and the transitions through occlusion. These are your labels, with
no model predictions. These labels were accepted by Ryan without further corrections.

Each video's adjacent `native` and `zoom` folders contain every frame. The zoom
panels pair raw pixels with the annotation at 4× magnification. Useful closer
checks include [P001/258](../data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/training_expansion_labels_v0_1/visual_review/possession_001_frames_0250_0274_training_expansion_v0_1/zoom/frame_000258.png)
and [P002/355](../data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/training_expansion_labels_v0_1/visual_review/possession_002_frames_0343_0367_training_expansion_v0_1/zoom/frame_000355.png),
where the saved center uncertainty is larger. P001/253 and P002/343–346, 349–354
are labeled hidden; verify their transitions in playback.

All three clips were decoded through their 25 frames and final frame. The
[asset manifest](../data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/training_expansion_labels_v0_1/visual_review/manifest.json)
binds the rendered media to the corrected annotation snapshots. Their on-video
`draft` status records creation time; the separate completed human review record
supersedes it. The current annotation files have reviewed status, and the single
approved expanded fit is complete.

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

The completed label overlays and playback are linked above. Their visual review,
reviewed label bindings and the approved single fit are now complete. Original
annotations, evaluation windows, holdouts, checkpoint and previous results remain
separate and preserved.

The source-only previews remain linked from the
[prepared data proposal](ball_wasb_training_data_expansion.md). Watching those
previews does not substitute for placing and reviewing the new frame labels.
