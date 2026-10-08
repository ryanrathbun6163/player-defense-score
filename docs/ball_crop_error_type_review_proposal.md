# Identify the remaining error types using existing review images

Status: proposed review scope, not yet accepted. Ryan's "Ok move forward"
authorizes preparing this next proposal. Prepared on `codex/ball-detector-baseline`
at `b71c64d3fd46bb27072efa8644e90c1c222bb65c`.
Companion scope:
`configs/ball_tracking/proposals/rfdetr_medium_crop_error_type_review_v0_1.json`.
No new scientific execution, implementation or Git step is proposed or authorized.

## One question

Do the remaining errors involve a marker on another object, an off-center mark
on the ball, or no current output, and what changes at the boundaries of the
existing hidden interval?

The mean-confidence comparison improved pool match totals over saved TT but
remained mixed. P001 challenge fell from 25 matched frames to 18, while mean
still trailed saved top-one in both pools. Ryan's six qualitative reviews describe
different strengths by clip and remaining misses around a referee passage, but
do not identify exact frames or distinguish wrong-object selection from center
placement. The fixed raw10 metric tests center distance, not physical identity.

Another scoring change would not resolve that distinction. This proposal uses
already verified native overlays for new frame-specific diagnostic judgments.
There is no new selector, scoring, inference, rendering, automated experiment,
test suite, resource reservation or release checkpoint.

## Fixed 16-frame scope

Choose cases from the existing bounded result before opening any review pixels:

| Group | Selection rule | Exact frames |
| --- | --- | --- |
| P001 challenge, 200-224 | Across all six windows, choose the unique largest net loss of matched frames from TT to mean. Include every TT-matched to mean-wrong/missing transition in that window. | 204, 210, 211, 215, 216, 217, 219 |
| P003 challenge, 150-174 | Include the entire sole labeled hidden interval, plus exactly two immediately adjacent frames on each side. | 163-171 inclusive |

This is a deliberately selected diagnostic sample, not a representative accuracy
sample. It includes all seven regressions in the chosen window, not only striking
examples. The hidden interval is 165-169 in the saved evaluation; Ryan did not
assign exact frame numbers to the referee passage, so the two must not be assumed
to coincide without his observation. No range expansion is automatic.

Existing returned facts, not new visual judgments:

- P001 mean is wrong-present on 204, 210, 216, 217 and 219, and missing on 211
  and 215. TT is matched on all seven. Top-one is wrong-present on the same five
  frames and matched on 211 and 215.
- P003 164 and 170 are wrong-present for all three methods. Mean and top-one are
  matched on 163 and 171; TT is missing at 163 and wrong-present at 171.
  During 165-169, TT emits on 165-168, mean on 167-169, and top-one on all five.
  These are saved hidden-frame alarms, not invented ball centers or identities.

Do not repeat the eight completed P003 representative identity reviews or the
six whole-clip reviews. Their raw responses and unknown candidate indices remain
unchanged. P003 representative mean and top-one agree on 24 of 25 emissions,
differing only at 314. The difference in Ryan's impressions of those panels remains
unresolved; this proposal does not add 300-324 to the review or claim mean is better.
Missing explicit final-frame wording is not a reason to replay completed clips.

## Existing evidence and access

Use exactly 48 existing native PNG overlays: saved TT, new mean and saved top-one
for each of the 16 selected frames. They already exist beneath the completed
mean comparison's `review/<window>/native/<arm>/frame_<index>.png` paths.
The companion scope lists each path, copied worker-verified hash and filesystem
metadata. It also binds the existing bounded return, worker receipt, completion,
human submission and presentation approval. No media is hashed in preparation.

The prior post-success presentation exception already permits showing these
verified media to Ryan and inspecting layout. Acceptance here concerns the new
frame-specific diagnostic review, not an extra permission step for opening each
already authorized image. Parent scientific JSON bodies and original source-image
files stay closed. No candidate runs, annotation files, scientific pools, audit
shards or embedded pointers are opened. Review-index JSON remains opaque; only
its existing receipt binding and metadata may be checked.

Use current receipt bindings and filesystem metadata to check that displayed
files are the existing artifacts. Do not rehash or modify PNGs. Show full native
images with ordinary viewer zoom; do not create crops, composites, videos, copies
or new renders. If the available view is insufficient, record uncertain rather
than silently expanding access. A missing or changed artifact requires an
integrity investigation; do not regenerate it or consume another attempt.

## Review protocol and uncertainty

Present the three labeled methods at the same exact source frame. Proceed in
ascending order within P001's seven cases, then P003's nine contiguous cases.
Use small batches at Ryan's pace. There is no need to reopen whole clips.
The images reveal method names, saved scoring status and reference markings;
describe this honestly as an unblinded diagnostic review, not an independent
annotation-quality or reproducibility study.

For each selected frame, record Ryan's words and ask only for distinctions that
are visible:

1. Can he see the ball: visible, partly visible, hidden, or uncertain?
2. For each present mark: ball, another object, or uncertain?
3. If he identifies the ball: centered, clearly displaced, or uncertain?

Saved absent-output status comes from the bounded result. An absent mark receives
no object identity or center judgment. Do not mistake a reference cross or radius
ring for a model's emitted marker. A point on a hand near the ball is not
automatically a ball detection. A plausible-looking point is not automatically a
raw10 pass. Human ambiguity stays unknown; no exact coordinates, distances,
candidate indices, error counts or revised visibility labels are invented.

Persist new responses separately from the old six clip comments and eight
identity judgments. A scientific candidate index visible in an image is not a
human-confirmed index unless Ryan identifies it explicitly. Any apparent reference
or visibility disagreement is a diagnostic flag for a later proposal, not authority
to amend reviewed annotations, ground truth, scores or thresholds.

## Completion and possible next decisions

A completed review has a response or explicit uncertain/skipped entry for all 16
frames and three method records per frame. Every response retains its media
binding, source frame, saved state, verbatim wording and any unspecified fields
as null. An uncertain response is valid evidence; it does not mean a method passed.
Clarifications append new records without overwriting the original response.

Summarize the observed error types within these selected cases only. Any descriptive
count must keep its diagnostic denominator and unknowns explicit; it is not a new
accuracy estimate, significance test or production quality gate. Do not pool these
judgments with old frame labels or redefine the quantitative matched/wrong/missing
counts. No method or operating point is selected by completion.

The result should inform a later bounded proposal: for example, investigate object
selection if marks lie on other objects, center placement if they lie on the ball
but are displaced, or visibility/missingness behavior if those dominate. These are
conditional directions, not authorization to implement, tune, relabel or execute.

## Limits and approval boundary

- New scientific attempts, charged scientific seconds and model calls: **zero**.
- New selector/evaluator runs, renders, tests and release checkpoints: **zero**.
- Allowed existing media: exactly the 48 bound native overlays; no added frames.
- New output: create-only administrative review submissions and completion records
  under `data/outputs/t/error_type_review_b71c64d3fd46/`, at most 1 MiB in total.
  Each submission is at most 16 KiB, at most 32 submissions including clarifications;
  summary and completion records are at most 64 KiB each. Check the aggregate before
  writes; do not silently truncate or overwrite responses.
- Preserve 3,330 resource events, 63 closed attempts, 59 successes, four historic
  failures and tip `4dd2b89f3fea67f3be9e3f409e7b937fc6da8a2a622c9b2a98505041c2a31fd6`.
  Consumed seconds remain `3547.523999999985`; remaining remains
  `10852.476000000015`. No journal events or budget resets belong to this review.
- Preserve all 636 mean artifacts, prior evidence and ledgers, nine embargoes,
  three sealed holdouts and the earlier release checkpoint. No player-pipeline
  rerun stage applies to this administrative human-review follow-up.

Accepting this proposal authorizes the 16-frame diagnostic review, presentation
of the listed existing media under the existing exception, and append-only human
responses within these limits. It does not authorize code changes, new scientific
execution, staging, committing, pushing, PR creation or merging. Ryan may begin
the review directly as acceptance; no additional approval is needed per image.
Preparation performs metadata/binding/document checks only, with no pixel access,
human-review replay, scientific-body hash, test or experiment.
