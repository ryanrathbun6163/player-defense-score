# Ball-tracking annotation protocol v0.1

## Status and purpose

Ryan approved the three pilot windows and the complete-ball-center rule on
2026-08-23. This document freezes the first annotation and raw-detection
evaluation contract for the ball-tracking phase.

The 75 approved frames are a **protocol-adjudication pilot**. They are for
testing whether the vocabulary, missingness rules, point target, and review
workflow are usable. They are not yet a detector benchmark, a model-selection
result, or a ball-tracking quality gate.

`protocol_adjudication` is retained as the v0.1 window-selection identifier for
schema compatibility. It does not require a second annotator. The default pilot
workflow is one honest annotator followed by explicit visual self-review.

## Approved pilot windows and source contract

All annotations must be made against the original possession clips, not the
resized synchronized-review composites. All three source clips are 1920 x 1080
at 25 frames per second. Frame indices are zero-based, window endpoints are
inclusive, and the timestamp is derived as `frame_index / fps`.

| Possession | Source clip | Total frames | Approved window | Time range | Pilot coverage | Source SHA-256 |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `possession_001` | `data/clips/possession_001.mp4` | 499 (`0..498`) | `375..399` (25) | 15.00-15.96 s | Pass release, airborne flight, catch, and low dribble | `5c42dad097a27873852d1555a71de36b890eb7bf287cf53ee1cdc693c31fcae6` |
| `possession_002` | `data/clips/possession_002.mp4` | 499 (`0..498`) | `318..342` (25) | 12.72-13.68 s | Dribble, self-occlusion, leg-level reappearance, and defender overlap | `e76e9805c390054d7fda9ca4413612d1f22cdb2f64bc58526a193bd8fdecb224` |
| `possession_003` | `data/clips/possession_003.mp4` | 500 (`0..499`) | `416..440` (25) | 16.64-17.60 s | Overhead release, flight, torso overlap, and catch | `6b0088df4434ebcd9de84997f871f26698544ebdd237f46d1f4a39937cf40531` |

An annotation file is valid only for the exact source bytes named by its
relative path and SHA-256. Possession ID, source hash, source dimensions, frame
count, frame index, and window form the join contract. Ball annotations must
not be inner-joined to the existing player-coordinate CSV rows because those
CSVs can legitimately omit a frame that the source video contains.

## Complete-ball-center rule

The only v0.1 geometry target is the center of the complete game ball in the
original source image:

- A fully visible ball uses `observed_complete_ball_center`.
- A partially visible ball may use `human_amodal_estimate` when the annotator
  can defensibly estimate the center of the complete ball behind the
  occlusion. Here, *amodal* means the whole object rather than only the visible
  orange fragment.
- The centroid of the visible fragment is never substituted for the complete
  ball center.
- If the complete-ball center is not defensible, geometry remains null. The
  visibility and identity decisions are still recorded.
- Neighboring frames may help identify the game ball, but a point must be
  supported by the current frame. No tracker output, interpolation, or
  inferred point through a fully hidden interval is ground truth.

Every geometry record includes an `uncertainty_radius_px`. It is the
annotator's non-statistical estimate of the maximum plausible point-placement
error in source pixels; it is not detector confidence and does not assert a
calibrated probability.

The v0.1 target is image-space only. A ball center is normally above the court
plane, including during most of a dribble, so player/court homographies must
not be applied to it. A future, separately defined ball-floor contact point
could be projected only with explicit contact or height assumptions.

## Annotation JSON schema

The schema is closed: every object must contain its exact fields. Missing,
unknown, and duplicate JSON object keys are rejected. The top-level object
contains:

| Field | Contract |
| --- | --- |
| `schema_version` | Exact string `"0.1"`. |
| `annotation_set_id` | Lowercase identifier beginning with a letter or digit and containing only letters, digits, `_`, or `-`. |
| `possession_id` | Identifier under the same rule; it must name the source possession. |
| `source_video` | Exact source path, SHA-256, width, height, fps, and frame count. |
| `window` | Inclusive start/end frame indices and a declared `selection_purpose`. Pilot files use `protocol_adjudication`. |
| `coordinate_system` | The fixed image/frame convention below. |
| `review` | Draft/reviewed state and human annotation provenance. |
| `annotations` | Exactly one sorted frame record for every inclusive window frame. |

`source_video` has exactly these fields:

```json
{
  "path": "data/clips/possession_001.mp4",
  "sha256": "5c42dad097a27873852d1555a71de36b890eb7bf287cf53ee1cdc693c31fcae6",
  "width_px": 1920,
  "height_px": 1080,
  "fps": 25.0,
  "frame_count": 499
}
```

The path must be repository-relative, use forward slashes, and contain no
parent traversal. The hash is exactly 64 lowercase hexadecimal characters.
Dimensions and frame count are positive integers; fps is finite and positive.
Declaring these values is not source verification by itself. Reviewed files
must also pass the hash-and-metadata verification described below.

`window` has exactly these fields:

```json
{
  "start_frame_index": 375,
  "end_frame_index": 399,
  "selection_purpose": "protocol_adjudication"
}
```

Both frame indices must be within the source. The end must not precede the
start. The allowed purposes are `protocol_adjudication`,
`representative_evaluation`, `challenge_evaluation`, `training`,
`validation_calibration`, and `test_holdout`.

`coordinate_system` is constant in v0.1:

```json
{
  "frame_index_origin": 0,
  "pixel_origin": "top_left",
  "x_axis_direction": "right",
  "y_axis_direction": "down",
  "center_definition": "complete_ball_center",
  "timestamp_rule": "frame_index_divided_by_fps"
}
```

`frame_index_origin` must be the JSON integer `0`; boolean `false` and numeric
`0.0` are rejected even though they can compare equal to zero in Python. The
other five fields must exactly match the strings shown above.

`review` has exactly these fields:

```json
{
  "status": "draft",
  "annotator_id": "annotator-id",
  "reviewer_id": null,
  "created_at_utc": "2026-08-23T00:00:00Z",
  "reviewed_at_utc": null
}
```

The allowed review states are `draft` and `reviewed`. A draft requires null
`reviewer_id` and `reviewed_at_utc`. A reviewed set requires both values and
cannot contain an `unlabeled` frame. Timestamps must be ISO-8601 timestamps
with an explicit UTC offset. `annotator_id` and, when present, `reviewer_id`
must be nonblank. The reviewed timestamp cannot precede the created
timestamp.

`reviewer_id` identifies the person who actually performs final sign-off. It
may identify the same human who placed the annotations. The field does not
assert that an independent second annotator participated, and a fictitious
identity must never be supplied merely to satisfy the schema.

### Per-frame fields

Every annotation row has exactly these fields:

| Field | Allowed value |
| --- | --- |
| `frame_index` | Zero-based integer within the declared window. |
| `annotation_status` | `labeled`, `unlabeled`, or `excluded`. |
| `visibility` | `fully_visible`, `partially_visible`, `not_visible`, `indeterminate`, or null when status is not labeled. |
| `absence_reason` | `occluded`, `out_of_frame`, `unknown`, or null. It describes why no ball pixels are visible, not why a point was withheld. |
| `game_ball_identity_certainty` | `certain`, `probable`, `ambiguous`, or null when status is not labeled. |
| `geometry` | Null, or the complete-ball-center object defined below. |
| `localization_eligible` | Boolean controlling point-localization scoring. |
| `difficulty_tags` | Lexicographically sorted, duplicate-free array of allowed tags. |
| `notes` | Null or a nonblank audit note. |

The geometry object has exactly these fields:

```json
{
  "center_xy_px": [1040.5, 612.0],
  "source": "human_amodal_estimate",
  "uncertainty_radius_px": 4.0
}
```

Both center coordinates and the uncertainty radius must be finite numbers.
The center must satisfy `0 <= x < width_px` and
`0 <= y < height_px`; the uncertainty radius must be positive and no greater
than the source-image diagonal `hypot(width_px, height_px)`. The two
geometry-source values are:

- `observed_complete_ball_center`, permitted for `fully_visible`;
- `human_amodal_estimate`, permitted for `partially_visible`.

The identity-certainty field describes whether the marked or asserted object
is the game ball:

- `certain`: no credible competing game-ball interpretation;
- `probable`: the game-ball interpretation is best supported, with residual
  ambiguity;
- `ambiguous`: the evidence does not support a scored identity decision.

The allowed visual difficulty tags are:

```text
background_clutter
camera_motion
compression_artifact
defocus
hand_overlap
motion_blur
overlay_or_cut
player_overlap
rim_net_backboard_overlap
tiny_apparent_size
```

These tags describe visual conditions in the current frame. They deliberately
do not label basketball events such as pass, shot, or rebound; event inference
is a later phase.

### Cross-field invariants

1. `annotations` contains every integer frame from `start_frame_index` through
   `end_frame_index`, exactly once and in ascending order. Thus each pilot file
   contains exactly 25 records.
2. `unlabeled` is workflow incompleteness, not a ball state. Its visibility,
   absence reason, identity certainty, and geometry are null;
   `localization_eligible` is false and `difficulty_tags` is empty.
3. `excluded` means an intentional protocol or source-validity exclusion, not
   an easy way to remove a hard example. It follows the same null/false/empty
   semantic contract as `unlabeled` and requires a nonblank explanation in
   `notes`.
4. Every `labeled` row has a non-null game-ball identity certainty.
5. `not_visible` means no game-ball pixels are visible. It requires exactly
   one absence reason and forbids geometry and localization eligibility.
   `occluded` means the ball is believed to be inside the image but completely
   blocked; `out_of_frame` means it is wholly outside the image; `unknown`
   means those explanations cannot be distinguished.
6. Every visibility state other than `not_visible` requires a null absence
   reason. A ball cut by the image boundary but still partly visible is
   `partially_visible`, not `out_of_frame`.
7. `indeterminate` is distinct from `not_visible`: the reviewer cannot make a
   reliable visibility/identity claim. It requires `ambiguous` identity,
   null geometry, and false localization eligibility. A note explaining the
   ambiguity is required.
8. Geometry is permitted only for `fully_visible` or `partially_visible`, with
   the source corresponding to that state as defined above.
9. True localization eligibility requires geometry and `certain` or
   `probable` game-ball identity. `ambiguous` annotations are never scored for
   localization.
10. If the complete-ball center itself is not defensible, geometry is null. A
    defensible point may be retained with false localization eligibility only
    when a separate review concern excludes it; that concern must be stated in
    `notes`.
11. Any visible row with missing or ineligible geometry requires a nonblank
    note. Such a row is not silently converted into a negative example.
12. Difficulty tags are empty for `unlabeled` and `excluded` rows. For labeled
    rows they may be empty or contain only the allowed, sorted, unique values.

## Annotation and review procedure

1. Verify the source path, SHA-256, dimensions, fps, frame count, and approved
   window before placing a point.
2. Create all 25 explicit frame records as `unlabeled`; do not omit difficult
   frames.
3. Annotate from the original frames without detector boxes, scores, tracker
   paths, or model suggestions visible.
4. Playback may be used to identify the game ball and understand an occlusion,
   but point geometry must be justified by the current frame.
5. Record uncertainty rather than forcing geometry. Use `indeterminate` or an
   unscored visible label where appropriate; use `excluded` only for a stated
   protocol/source reason.
6. After completing every frame, the annotator performs a source-faithful
   visual review of the full-frame overlays, native/magnified panels, ordered
   playback, trajectory gaps, difficult cases, and the final frame. Corrections
   are made in the authoritative JSON, and the visual package is regenerated
   until the annotator signs off.
7. Change the top-level review status to `reviewed` only after every frame is
   either labeled or explicitly excluded, the visual review is approved, and
   the actual sign-off identity and timestamp are recorded. Self-review is
   allowed; inventing a second reviewer is not.
8. Run the strict validator from the repository root and retain its summary
   with the annotation review evidence. For a reviewed file,
   `--verify-source` is mandatory: the command recomputes SHA-256 and uses
   OpenCV to verify width, height, fps, and frame count against the actual
   repository clip.

```powershell
& .\.venv\Scripts\python.exe -m src.ball_tracking.validate_annotations `
  --annotations <path> --verify-source --repository-root . --json
```

The v0.1 annotation JSON stores annotator/reviewer IDs and timestamps, while a
separate approval/finalization receipt binds the reviewed JSON to the visual
evidence and records the review method. For the default workflow, that receipt
must say plainly that this is a single-annotator reference set and makes no
inter-rater reproducibility claim.

Repeated annotation is optional. Use it only when a concrete reproducibility
or ambiguity question justifies the extra work. A genuine second-person study
is **inter-rater** annotation; a later repeat by the same person is
**intra-rater** annotation. Preserve both label sets and a disagreement record
when reporting either study, and never describe an intra-rater repeat or AI
assistance as independent human review. Ordinary visual approval, detector
evaluation, and this milestone do not require either study.

## Representative, challenge, and holdout pools

The three approved windows intentionally combine ordinary ball motion and
difficult conditions so the schema can be adjudicated quickly. They must not
be presented later as an unbiased benchmark sample.

After v0.1 survives the pilot:

- select a **representative pool** of contiguous windows from all three
  possessions using a predeclared coverage rule;
- select a separate **challenge pool** enriched for tiny apparent size, blur,
  defocus, hand/player/rim overlap, clutter, camera motion, compression, and
  overlay/cut conditions;
- reserve contiguous holdout windows before inspecting model predictions;
- keep all frames from a contiguous sequence in one split to prevent temporal
  leakage;
- annotate without predictions visible and report representative, challenge,
  holdout, and per-possession results separately.

All three current possessions come from one game. Success across them is
narrow same-game evidence, not broad NBA, arena, camera, or broadcast
generalization.

## Persisted raw-detection and evaluation contract

`BallDetectionRun` schema v0.1 is the persisted input to
`evaluate_detections`. The loader rejects missing, unknown, and duplicate JSON
object keys. The run is image-only evidence: it contains no track IDs,
temporal interpolation, latent occlusion positions, or one-ball
post-selection.

### Detection-run identity and provenance

The top-level run object has exactly:

| Field | Contract |
| --- | --- |
| `schema_version` | Exact string `"0.1"`. |
| `detection_run_id` | Unique lowercase identifier. |
| `annotation_set_id` | Exact annotation set the run will be scored against. |
| `possession_id` | Exact annotated possession. |
| `source_video` | The annotation contract's exact path, hash, width, height, fps, and frame count. |
| `window` | Exact inclusive `start_frame_index` and `end_frame_index`. |
| `model_provenance` | Complete model, weights, runtime, preprocessing, class, and export-floor contract. |
| `frames` | Exactly one sorted record for every inclusive window frame. |

Evaluation rejects a run unless `annotation_set_id`, `possession_id`, the
entire `source_video` object, and both window endpoints exactly match the
reviewed annotation set.

`model_provenance` has all of the following fields:

| Field | Contract |
| --- | --- |
| `model_name` | Nonblank model name. |
| `package_name` | Nonblank implementation package. |
| `package_version` | Exact nonblank package version. |
| `weights_identifier` | Nonblank human-readable weights identifier. |
| `weights_sha256` | Exactly 64 lowercase hexadecimal characters. |
| `code_commit` | Exactly 40 lowercase hexadecimal characters naming the source commit. |
| `device` | Nonblank inference-device description. |
| `precision` | Nonblank arithmetic-precision description. |
| `input_width_px`, `input_height_px` | Positive integer model-input dimensions. |
| `resize_mode` | Nonblank resize/letterbox/crop description. |
| `tiling_enabled` | Boolean. |
| `target_class_id` | Nonnegative integer target-class ID. |
| `target_class_name` | Nonblank target-class name. |
| `export_confidence_floor` | Finite value in `[0, 1]`; every persisted candidate must meet it. |
| `postprocessing_description` | Nonblank declaration of NMS, top-k, class filtering, clipping, coordinate remapping, and other postprocessing. |

This makes resolution, tiling, class mapping, candidate export, NMS, weights,
code, device, and precision part of the auditable operating point rather than
implicit model defaults.

### Explicit frame status and candidates

Every frame record has exactly `frame_index`, `inference_status`,
`failure_reason`, and `detections`. Allowed inference states are `completed`,
`decode_failed`, `inference_failed`, and `not_run`.

A completed zero-candidate frame is explicit:

```json
{
  "frame_index": 375,
  "inference_status": "completed",
  "failure_reason": null,
  "detections": []
}
```

`completed` requires a null failure reason and a detections array, which may be
empty. Every other status requires a nonblank failure reason and null
`detections`. An omitted frame, a failed frame encoded as an empty list, and an
extra or out-of-order frame are invalid. `evaluate_detections` rejects the
entire run if any frame is not `completed`; operational missingness never
silently becomes a detector miss.

Each detection has exactly:

```json
{
  "candidate_index": 0,
  "class_id": 32,
  "class_name": "sports ball",
  "confidence": 0.73,
  "bbox_xyxy_px": [1020.0, 590.0, 1062.0, 633.0],
  "center_xy_px": [1041.0, 611.5]
}
```

`candidate_index` must equal the candidate's zero-based list position. Class
ID and name must exactly match the target class in `model_provenance`.
Confidence must lie in `[0, 1]` and be at least the declared export floor. Box
coordinates are finite original-source pixels satisfying
`0 <= x1 < x2 <= width_px` and `0 <= y1 < y2 <= height_px`. The center is also
in source pixels and must equal the box midpoint within `1e-6` pixels.

Every candidate at or above the declared export floor remains in the ordered
list. Overlapping and even identical boxes are valid separate candidates with
different indices. The contract does not authorize basketball-specific
deduplication or temporal selection.

### Scoring

The evaluator rejects draft annotation sets, non-`BallDetectionRun` inputs,
binding mismatches, incomplete frames, and a requested confidence threshold
below the run's export floor. Drafts produce no evaluation report.

For caller-supplied confidence and localization-radius values, evaluation is:

1. Keep candidates whose confidence is greater than or equal to the supplied
   confidence value. Sort them by descending confidence and then
   `candidate_index`.
2. On a localization-eligible frame, compute raw Euclidean source-pixel center
   distance to the reviewed point. A candidate qualifies only when this **raw
   distance** is less than or equal to the supplied localization radius.
3. Also report diagnostic effective error as
   `max(0, raw_center_distance - annotation_uncertainty_radius_px)`. Effective
   error never changes true-positive matching.
4. The first qualifying candidate is the one true positive. Every additional
   accepted candidate remains a false positive; additional qualifying
   candidates are also counted as duplicate false positives.
5. If no candidate qualifies on an eligible frame, record one false negative
   and count every accepted candidate as a false positive.
6. A labeled `not_visible` frame with `certain` or `probable` game-ball
   identity is a reviewed negative: every accepted candidate is a false alarm.
   An `ambiguous` not-visible frame is unscored.
7. Unlabeled, excluded, indeterminate, ambiguous, visible-but-ineligible, and
   otherwise unscored rows do not affect precision or recall. Their accepted
   prediction counts remain visible in the report.

The report exposes true positives, false positives, false negatives, duplicate
false positives, non-visible false alarms, false-alarm frames, precision,
recall, raw/effective matched-center error summaries, below-threshold counts,
unscored prediction counts, and per-frame decisions. It also binds results to:

- `evaluation_schema_version`, exactly
  `ball_detection_evaluation/v0.1`;
- `annotation_content_sha256`, a canonical digest of the complete validated
  annotation content;
- `detection_run_id`, plus `detection_run_content_sha256`, a canonical digest
  of the complete validated `BallDetectionRun.to_dict()` payload;
- `model_run_signature`, a canonical digest of the complete
  `model_provenance` object;
- full model provenance, possession, source path/hash, window endpoints,
  selection purpose, and the caller-supplied scoring settings.

The detection-content digest binds the exact candidate payload used when the
report was created, so two runs with the same model configuration but different
outputs have different content hashes. A report by itself does not prove that
its declared hash matches an unavailable detection payload. Archive the
validated detection-run JSON with the report so the canonical digest can be
recomputed independently; retain the annotation JSON for the same reason.

Aggregation accepts only comparable, non-overlapping reports. It requires:

- the exact v0.1 evaluation-report field set and schema-version value;
- unique annotation-set IDs, annotation-content hashes, detection-run IDs,
  and detection-run-content hashes;
- one source SHA-256 per possession and one possession per source SHA-256;
- non-overlapping inclusive windows on each source clip;
- the same model-run signature, selection purpose, confidence threshold, and
  localization radius for every report;
- valid annotation-content, detection-content, model-signature, and source
  SHA-256 fields.

Before summing anything, aggregation parses the full `model_provenance`
object, recomputes its canonical signature, and requires it to equal the
declared `model_run_signature`. It also requires `confidence_threshold` to be
at least `model_provenance.export_confidence_floor`. It then validates the
exact per-frame result schema and ordered, gap-free frame coverage from the
inclusive window start through end. Every claimed match must reference an
existing input candidate through `matched_candidate_index`, and its raw
`matched_center_error_px` must be no greater than `localization_radius_px`.
From `frame_results` it re-derives scoring-category counts,
accepted/below-threshold counts, true/false positives, false negatives,
duplicate and non-visible false alarms, unscored predictions, precision,
recall, false-alarm rates, and raw/effective error summaries. Every declared
report count, metric, and summary must equal that reconstruction before the
report can contribute to an aggregate.

The aggregate provides micro totals, possession-level macro precision and
recall, per-possession source hashes/counts, and explicit
`macro_precision_possession_count` and `macro_recall_possession_count` values
so undefined possessions are not hidden from the denominator.

This protocol deliberately sets no detector confidence threshold,
localization radius, pass/fail boundary, or model winner. Any later score/radius
sweep and quality gate must be predeclared after the pilot schema and labels
are reviewed, then applied identically across candidates.

## Explicit non-goals of this checkpoint

This checkpoint does not:

- claim that the 75 frames are a benchmark or quality gate;
- select RF-DETR, YOLO, or another detector;
- define benchmark thresholds or tune a model;
- add temporal association, interpolation, or hidden-ball hallucination;
- project the ball center through the player/court homography;
- infer dribbles, passes, shots, rebounds, handlers, or possession state;
- integrate ball tracking into the resumable 21-stage player pipeline;
- establish cross-game or full-game generalization.

## Milestone progression

1. **Complete:** instantiate one draft v0.1 annotation JSON for each approved
   window with the exact source metadata and 25 explicit `unlabeled` rows.
2. **Complete:** finish prediction-blind annotation, single-annotator visual
   review, and source-verified validation for all three sets; retain the reviewed summaries.
   Run a repeated-annotation study only if a later reproducibility question
   makes it useful.
3. **Complete:** exercise the evaluator with synthetic positive, negative,
   duplicate, uncertain, and missing-frame cases before using model output.
4. **Next:** precommit the representative, challenge, and holdout sampling plan
   and the detector operating-point comparison.
5. **Pending:** run the first image-only detector baseline, preserve every raw
   candidate, render synchronized review evidence, and only then propose
   empirical thresholds or a temporal-association experiment.
