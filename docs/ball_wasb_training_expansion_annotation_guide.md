# Approved additional training labels

Ryan approved 75 additional training frames and one 200-update fit on 2026-10-08.
The [approval record](../configs/ball_tracking/reviews/wasb_training_data_expansion_approval_v0_1.json)
supersedes the prepared proposal's historical pending status. The new fit is
authorized after these labels are completed and visually reviewed. The six model
output clips already reviewed remain complete.

## Open the three prepared drafts

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

All 75 rows begin unlabeled. No predicted locations or invented visibility labels
have been inserted. The helper seeks directly to each approved source window and
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

After all three are labeled, return to the chat. Codex will prepare the label
overlays and playback for the required visual review, then freeze the reviewed
label bindings and run the already-approved single fit. The original annotations,
evaluation windows, holdouts, checkpoint and previous results stay separate.

The source-only previews remain linked from the
[prepared data proposal](ball_wasb_training_data_expansion.md). Watching those
previews does not substitute for placing and reviewing the new frame labels.
