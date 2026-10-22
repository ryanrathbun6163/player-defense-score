# Completion campaign: NBA reference batch 01

This batch delivers **120 new NBA reference proposals** for
`chi-vs-ind-0022400868_e01`, frames **0–119** of the fixed CHI–IND training
episode. It contains **96 proposed whole-ball centers and 24 null centers**.
Ryan's acceptance is pending. A training-game role does not make unaccepted
labels eligible for fitting or checkpoint selection.

The [fixed source manifest](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json)
selected this episode before new-model predictions. Its
[batch configuration](../configs/ball_tracking/completion_campaign/nba_reference_batch_01_v0_1.json)
retains that role and native timing. This is the first 120 proposals among
**3,839 selected new NBA judgments**; **3,719 remain to be proposed** across
the fixed package. These counts are separate from curated coverage, which
remains **868/1,273 accepted**, with **760 eligible centers and 405 uncovered**.
Ryan's grouped acceptance of the 102 curated judgments in batches 05–07 does
not accept this new NBA batch.

## Source and reference judgments

The native source is 1280×720 at 60 frames per second. Its timebase is
**1/60000 second**, with frame `f` at PTS `f × 1000` and duration 1000 ticks.
The selected interval is **[0,120000) ticks**, or **[0,2) seconds**. Frame 119
is the episode and batch final; the underlying 663-frame source clip continues
through frame 662. The [complete review page](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_01/review_v2/index.html)
retains all 120 frames in a [two-second native overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_01/review_v2/review_native.mp4)
and a [twelve-second slow overlay](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_01/review_v2/review_slow.mp4)
at 10 fps, with frame controls and unmarked source crops for every null center.

Source inspection shows two perimeter passes, a catch and overhead handling
between them, followed by receiver-body occlusion. Visibility counts are **50 fully visible,
48 partially visible, two indeterminate and 20 not visible**. Proposed centers
carry **3–7-source-pixel uncertainty**, an AI placement estimate rather than a
calibrated confidence interval. Every point describes the whole ball; partial
arcs are not relabeled as complete-ball silhouettes.

The nulls preserve specific uncertainty:

- Frames 96–97 contain visible fragments without a defensible whole-ball center.
- Frames 98–99 are ambiguous hand/ball regions with indeterminate visibility.
- Frames 100–119 have no visible ball boundary after reception behind the body
  and arms; hidden coordinates remain unknown.

Each assigned source frame was inspected before proposing its label. No model
predictions, optical flow or temporal interpolation supplied centers. AI
authorship remains explicit, including where the legacy geometry field uses
`human_amodal_estimate`. Original part proposals, inspection images and receipts
are preserved; human acceptance remains a separate decision.

## Source validation and implementation

The initial source comparison failed because OpenCV's RGB conversion matched
BT.601 for this source, whose declared color space is BT.709. The failure,
elapsed time, diagnosis and original PNGs remain preserved. A separate FFmpeg
comparison with explicit BT.709 conversion matched **all 120 original PyAV
PNGs exactly**, including native PTS. Both paths use FFmpeg components; this is
an alternate conversion/transport check, not independent codec evidence.

The new `src/ball_tracking/completion_nba_references.py` consumer preserves the
fixed parent-game role, episode frame list and actual native PTS. It requires
completed source preparation and the successful per-frame RGB audit, preserves
failed-attempt evidence, validates pending-label metadata and joins each
annotation to its native source PNG. It consumes saved PNGs without decoding
the source video. The rendering path currently supports **constant cadence**;
variable-cadence SAC episodes need explicit support before their delivery.

The [independent metadata audit](../data/outputs/ball_tracking/completion_campaign_v0_1/nba_reference_batch_01/inspection/independent_metadata_audit.json)
verifies 185 file bindings and all 120 source/timing joins, and parses both
proposal parts through the annotation consumer. It also confirms all seven
accepted curated campaign publications through production readers: 868 accepted
rows, 760 eligible centers, 20 authorities and seven acceptance receipts.
The original grouped-acceptance preservation snapshots agree on 330 files.
These checks establish record integrity and role separation, not label truth.
This metadata audit preceded the render-only color fix; its exact consumer is
preserved in the failed-render snapshot. Final focused tests bind the updated
consumer separately.

One part's detail-sheet helper had a syntax error before creating any detail
images or specifications. Its failure and correction are recorded separately;
the source PNGs and proposals were unchanged.

The first encoded native review also failed its metadata guard: it had the
correct 120 frames and 60 fps, but omitted BT.709 color primaries and transfer
metadata despite the encoder options. The failed `review_v1` output and the
exact executed module, tests and helper are preserved in `render_attempt_01/`.
This failure did not change the source PNGs or proposals. Explicit color
conversion and frame properties resolved the metadata loss; `review_v2` passes
the emitted color, timing and frame-census checks. The original failure remains
failed and its output is retained.

## Final validation and next step

The [preparation result](../configs/ball_tracking/reviews/nba_completion_reference_batch_01_result_v0_1.json)
records the completed review and its pending human acceptance. All source
frames, encoded center crops, all 24 null-center context crops and the complete
actual encoded final frame 119 were visually inspected. Automated delivery
checks cover **317 file bindings, 120 native source/annotation joins, 240 encoded
frames and 192 localized markers**, all review links and preservation of the
868 accepted curated rows.

All **13 focused tests pass**, with zero failures, errors or skips. The saved
test result binds the final implementation, test file and actual combined
proposal. It covers native timing and role guards, completed source-audit
requirements, actual emitted records and color metadata. Earlier source and
render failures, part proposals and inspection receipts remain preserved.
Generated labels, source PNGs and review media stay ignored by Git.

No fitting, checkpoint selection, model inference or protected evaluation ran
for this reference preparation. Continue the approved reference package and
record Ryan's acceptance of new labels before fitting. Accepted source, label
and role manifests plus the executable recipe must be frozen before training.
The retained model and prior failures remain intact. Protected evaluation still
requires a frozen method and separate explicit authorization; no ball-phase
completion or trajectory acceptance is claimed.
