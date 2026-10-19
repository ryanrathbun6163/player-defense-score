# NBA native-frame annotation pilot

Ryan approved the two-source, 120-frame pilot and game allocation on October 18,
2026. The [approval record](../configs/ball_tracking/reviews/nba_development_selection_approval_v0_1.json)
binds the preserved [selection proposal](nba_development_selection_plan.md).
Sacramento is eligible for future training data; Detroit remains target-case
development. Neither this pilot nor its completion authorizes a model fit.

## Accepted pilot status

Ryan accepted both presented AI proposal packages with “looks great chat. move
forward.” The [acceptance record](../configs/ball_tracking/reviews/nba_assisted_label_acceptance_v0_1.json)
binds the two full short reviews, priority cases and actual final frames. The
separate accepted reference bundle is
`data/outputs/ball_tracking/nba/reviewed_pilot_v0_1/reference.json`. Its 120 labels
remain AI-authored, human-accepted estimates with their original uncertainty;
they are not independent human annotations.

The original proposals and videos retain their historical “pending review”
status/captions. This later acceptance supersedes that status without rewriting
the evidence. The blank manual editor drafts are also unchanged. The first-pass
description below documents how this accepted batch was prepared; it is not a
request to repeat the completed review.

The [next prepared diagnostic](nba_wasb_native_pilot_diagnostic.md) uses one
existing checkpoint on these native frames. Its new cadence choice is awaiting
approval; no actual model execution or training is implied by label acceptance.

## What to label

| Pilot | Original source frames, inclusive | Original source timestamps | Purpose |
| --- | --- | --- | --- |
| Sacramento opening action | 660–719 | 11.070689–12.054689 s | Future-training-eligible protocol pilot |
| Detroit half-court action | 10788–10847 | 180.022689–181.006689 s | Target-case development protocol pilot |

Each block contains 60 consecutive original frames. The source timestamp is an
integer number of 1/90000-second ticks, retained for every frame. The first-to-last
span is about 0.984 seconds. No 25 fps conversion or nominal-fps timestamp
calculation is used. The Detroit opening inbound remains unseen; labeling this
block does not certify a complete possession or a primary defender.

The authoritative images are full-resolution RGB PNGs decoded directly from
the original recordings. The source-only review MP4s remain useful context,
but their lossy pixels are not the annotation authority. Source image geometry
is unchanged; the PNGs preserve the exact RGB pixels from the recorded FFmpeg
software decode/conversion.

## Default workflow: assistant first pass, Ryan reviews

Ryan's October 18 workflow clarification replaces the all-manual starting plan.
The assistant inspects every approved native frame, proposes labels with
uncertainty, checks the records and prepares short source-plus-zoom overlays.
Ryan reviews the complete short clips and highlighted difficult cases, including
each actual final frame. Corrections can be requested by source frame number;
the assistant carries them out and preserves the previous proposal.

These are explicitly AI-authored proposals, separate from the original human
editor drafts. They are not accepted reference labels and must not be reported
as independently human-labeled data. A completed first pass is followed by
explicit human acceptance; a plausible-looking overlay alone does not establish
accuracy. Hidden or indefensible centers stay missing. The existing editor is
still available for direct manual annotation when useful.

The first assisted batch is ready in
`data/outputs/ball_tracking/nba/assisted_pilot_v0_1/index.html`. Its two candidate
directories each contain `review.mp4`, `index.html`, `proposal.json`, all 60
source-plus-zoom overlays, a frame manifest and a preparation receipt. Each
video shows the 60 source frames at six frames per second followed by a
one-second final-frame hold. This deliberate slow playback is not evidence of
the original temporal cadence. The underlying original PTS remain intact.

SAC proposals contain 57 fully visible and three partly covered balls, with
priority frames 660–662 and 674–675. DET proposals contain 14 fully visible and
46 partly covered balls, with priority frames 10788, 10791, 10833–10835, 10840
and 10846–10847. The 13 priority frames are a navigation aid; the remaining
frames are not automatically accepted. All 120 have proposed centers, with
uncertainty expressing estimated placement ambiguity rather than calibrated
statistical confidence. No hidden-ball position was filled.

The combined review page is open locally. In a later session the assistant can
serve this existing directory on loopback again without regenerating labels or
videos. Give corrections by game and original source-frame number. Preserve
the current proposal and review package when creating a corrected version.
The [compact preparation record](../configs/ball_tracking/reviews/nba_assisted_annotation_pilot_v0_1.json)
binds the actual proposals, renderer checks and independent output audit.

The separate `nba_assisted_annotation_proposal/v0.1` wrapper records AI origin,
the original draft hash and per-frame inspection evidence. Its existing row
semantics include the legacy geometry token `human_amodal_estimate`; inside
this wrapper that names a partial-ball geometry convention, not a human author.
Do not load these proposals into the original editor under Ryan's name or
silently treat them as an independent human-labeled evaluation set.

## Optional manual editor

The local editor opens both pilots. Choose a pilot, enter your actual annotator
name, and work through all 60 frames. Every initial row is explicitly unlabeled.
Loading a frame, entering a name or navigating does not place a ball label.

1. Inspect the frame, using zoom for the small ball. Click the defensible center
   of the **complete ball**, not the center of a visible orange fragment.
2. Set visibility and game-ball identity certainty. For a visible center, enter
   a positive uncertainty radius in original source pixels. This is your estimate
   of placement uncertainty, not model confidence.
3. Record relevant difficulty tags and notes. Save the frame explicitly, then
   continue. The next frame does not inherit a point from the previous frame.
4. Inspect the actual last frame of each block. Completing draft labels is
   followed by source-faithful visual review and explicit human acceptance.

Use `fully_visible` for a directly observed complete-ball center. Use
`partially_visible` with an amodal estimate only when the whole-ball center can
be defended from the current frame. Neighboring frames can help identify the
ball, but cannot supply an invented point while it is fully hidden.

Use `not_visible` when no game-ball pixels are visible, with `occluded`,
`out_of_frame` or `unknown` as the absence reason. These rows have no geometry.
Use `indeterminate`, ambiguous identity and an explanatory note when the image
does not support a reliable visibility/identity decision. Visible frames with
an indefensible center retain their visibility and a note, with no geometry.
Use `excluded` only for a stated source/protocol reason; difficulty alone is not
a reason to discard a frame. All these semantics reuse the established
[complete-ball-center protocol](ball_tracking_annotation_protocol.md).

The editor records a human annotator only when a valid save occurs. Every save
checks the current revision and original provenance, validates the complete
document, retains the exact previous bytes in an adjacent history directory,
and replaces the draft atomically. A stale browser tab must reload instead of
overwriting a newer save. The editor cannot mark a set human-reviewed.

The workspace is already open for this session. To restart it later, run this
from the repository root; it prints the complete local URL to open. Keep the
printed `#token=...` fragment. Stop a terminal-launched server with Ctrl+C;
saved labels remain on disk.

```powershell
& .\.venv\Scripts\python.exe -B -m src.ball_tracking.annotate_nba_frames --annotations data/outputs/ball_tracking/nba/annotation_pilot_v0_1/sac_mem_q1_c01/annotations.json data/outputs/ball_tracking/nba/annotation_pilot_v0_1/sas_det_q1_c02/annotations.json --repository-root . --port 0
```

Source images and each frame's provenance are checked before use. The editor
listens only on this computer's loopback address and serves only its configured
drafts and bound images. PNG loading is bounded to one displayed frame; labels
and metadata for both small pilots remain in memory.

## Files and implementation boundary

Generated PNGs, drafts and receipts live under ignored
`data/outputs/ball_tracking/nba/annotation_pilot_v0_1/`, in a separate directory
for each candidate. `annotations.json` is the authoritative editable draft;
`annotations.history/` retains earlier saves. Keep these files local and backed
up with the other project data. They are intentionally absent from Git.

The separate `nba_ball_annotations/v0.1` schema records parent game/source,
candidate, approved role, approval hash, original frame indices and integer PTS,
PNG hashes and decoded-RGB hashes. It does not claim compatibility with old
NFHS experiment runners or choose a model's temporal input cadence. Identity,
court calibration, ball-label acceptance and trajectory review remain explicit
human decisions. Existing NFHS results, protected holdouts and completed
reviews remain unchanged; three motion-comparison human reviews remain pending.

## Preparation and checks

Both extractions completed on their first invocation, in 6.921 and 6.922 seconds,
with empty FFmpeg warning/error logs. The 120 PNGs total 273,738,677 bytes. Each
PNG's decoded RGB pixels and original PTS match the source decode and audited
frame map. A separate earlier-seek decode independently checked all 120 PNGs,
with 26 seconds of bounded input in total and 4.656 seconds of FFmpeg elapsed
time. The original full recordings were neither rehashed nor decoded in full.
Completed source hashes were reused with unchanged size and modification time.

Focused checks passed: 12 schema/save checks, three actual synthetic FFmpeg
producer checks, and 12 current editor/HTTP checks. An earlier 11-check editor
run is retained separately; the later run covers the additional fixed session
provenance guard. No full suite or old scientific experiment was repeated.

Browser verification saved and reloaded a synthetic test label, confirmed that
the next frame stayed blank, and observed the unsaved-change confirmation.
Browser-control timeouts after that confirmation are preserved as tooling
failures; cancellation behavior was not fully observed. A fresh real workspace
loaded both pilots' first and final frames without changing their drafts.
The synthetic server was stopped; the real editor remains available for Ryan.
The [compact preparation record](../configs/ball_tracking/reviews/nba_annotation_pilot_preparation_v0_1.json)
binds the receipts, audits, initial drafts and implementation versions.
