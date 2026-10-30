# Compare the saved winner with one retained localization match

Status: proposed, not authorized for implementation or execution. Ryan's
"move forward chat" authorizes preparing this concrete follow-up. The companion
scope is `configs/ball_tracking/proposals/rfdetr_medium_crop_saved_decision_contrast_v0_1.json`.
Prepared at `7a2e660a38877e2000fa997e675c86b97d55e9ac`; no Git step is included.

## Question and reason for this step

For the same eight P003 representative TT/cap20 frames, what recorded numerical
terms favored the emitted candidate over one retained candidate that satisfied
the existing raw 10-source-pixel localization rule?

Ryan's completed review found seven emissions on players or hands and one on
the ball's outer edge. The selected frames are 300, 301, 302, 304, 308, 319, 320
and 324. They are correlated failures from one window, not a performance sample.
Their saved S memberships already establish retained localization-compatible
candidates. Repeating availability, cap counts or the completed image review
would not answer a new question.

This comparison reads recorded decisions. It does not change the detector,
selector, thresholds, matching rule, annotations or original results. It may
explain a numerical preference over the named comparison candidate; it cannot
prove a physical cause or show what would happen after changing the algorithm.

## Exact scientific inputs: two existing files

Let `M` be `data/outputs/ball_tracking/crop_motion_factorial/rfdetr_medium_crop_motion_factorial_v0_1/`.
Only a future owned, monitored worker may read/hash these bodies:

| Input relative to M | Bytes | SHA-256 |
| --- | ---: | --- |
| `evaluation/representative_evaluation.json` | 22583132 | `d70e2c4abafdd943a5f1add2e4f15748f04f5f2c2a240c2a5f867c81f03c7c9b` |
| `possession_003_frames_0300_0324_representative_evaluation_development_v0_2/history_edge_tight_cost_tight_6faf84c6b3f6ca9d.json` | 5522898 | `731eb6e538e43d4412762b5aab276ed250f57cc8f1ea19a34ee4e62b722fe26f` |

The 28,106,030-byte pair is smaller than the 44,676,525-byte retention window
scoring file alone. Sizes were obtained through filesystem metadata only;
expected hashes came from the committed retention proposal, not fresh body reads.

In the pool, interpret only header/provenance metadata and reports
`/evaluation_reports/641` (crop_top_twenty, .01, cap20, raw10) and
`/evaluation_reports/646` (TT, .01, cap20, raw10), with the exact content digests
frozen in the companion scope. Interpret their frame results only for the eight
specified indices. Whole-file parsing/hashing is permitted inside the worker;
other embedded reports are not additional analytical scope.

In the observation wrapper, validate its metadata and embedded observations
content digest, then interpret only those eight observation frames. Read their
two named current-endpoint records, saved competing-endpoint entries, candidate
dispositions, winner and global margin. Numeric path references and their
stored totals may include earlier frames within each saved horizon
`max(300, frame-4)..frame`. This does not authorize earlier images or semantic
labels for historical nodes. No raw candidates, annotation files, edge lists,
other settings/windows, path shards, scientific manifests, images or video
are additional inputs. Every embedded file pointer stays inert.

The parent keeps scientific bodies opaque. It may use source, committed
authority, administrative human-review records/receipts and filesystem metadata,
then receive the bounded verified summary after successful execution. It may
not directly open/hash either input or the new scientific output bodies.

## Fixed comparison and explicitly permitted operations

For each frame, use the existing top-twenty report's `matched_candidate_index`
as the comparison candidate. The evaluator chooses the highest-confidence
candidate within the raw radius, breaking equal-confidence ties by original
candidate index. This is not necessarily the nearest candidate, the best-scoring
compatible endpoint, or a visually confirmed ball. Do not search for a different
comparison candidate or assign it a semantic identity.

Require a single current emitted endpoint in the TT observations, a saved TT
nonmatch, and a distinct retained comparison index from the top-twenty report.
Copy both current endpoint confidences, saved scores and paths, confidence
sums, internal skipped-frame counts and normalized squared-motion sums from
the saved records. Copy the comparison candidate's saved raw center error.
Join Ryan's existing identity/center judgments to the emitted endpoint only;
do not fill previously null human-record candidate numbers retroactively.

Permit these new within-frame arithmetic operations, explicitly labelled as
derived from saved values. For each endpoint with confidence `c`, path
confidence sum `C`, internal skip count `G`, and squared-motion sum `N`:

```text
current confidence contribution = c
past confidence contribution    = C - c
internal gap contribution       = -0.25 * G
motion contribution             = -0.25 * N
saved current-endpoint score    = their sum
pair score gap                  = saved winner score - saved comparison score
term contrasts                  = winner contribution - comparison contribution
```

Both endpoints are current, so their trailing-skip penalty must be zero.
Verify score and contrast reconciliation with `math.isclose(rel_tol=1e-9,
abs_tol=1e-9)`. This is a floating-point integrity check, not a quality gate.
Preserve full numeric precision in JSON. Report all four signed contributions
side by side; do not pick a single causal label, tune weights or rank methods.

Keep the saved global `score_margin` separate: it compares the winner with the
global runner-up, not necessarily this comparison candidate. A zero pair gap
is a tie, not a score advantage; retain the source-defined current-endpoint tie
fields (confidence, original index and path). Use exact stored equality to
identify a tie; the arithmetic tolerance must not turn near-ties into ties.

Frame 300 has a one-frame horizon, so it has no past-confidence, gap or motion
contribution. Do not attribute its choice to history. Later paths may have
different histories; term differences describe those saved paths, not controlled
experiments. No dynamic-programming recurrence, alternative-path search,
detector inference, matching, rescoring or selection is rerun.

Record exact source JSON pointers for every copied field and operand pointer
plus operation for every derived field. Preserve all eight rows and human
uncertainty. Mismatched namespaces, duplicate/missing records, incompatible
hashes, absent comparison endpoints or contradictory saved outcomes stop the
unit with evidence; do not substitute or regenerate data.

## Outputs and execution envelope

Create only a new ignored directory under the existing retention root:
`audit/post_review_saved_decision_contrast_v0_1/`, containing `contrast.json`
(at most 128 KiB), `summary.md` (64 KiB) and `provenance.json` (128 KiB).
The summary shows all eight frame pairs, four signed term contrasts, pair gap,
separate global margin, saved raw comparison error and prior human judgments.
No pool totals, rates, method rankings, new semantic labels, causal verdicts or
overall quality conclusions are produced. Fail rather than truncate.

Request one new unit, `post-review-saved-decision-contrast:summary:`, at most
one attempt and 120 charged seconds from the existing remaining cumulative
`10993.273000000017` seconds. The reservation is bounded by both limits.
This is a proposed allocation, not a runtime estimate or renewed old attempt.
All prior attempts remain consumed; there is no automatic scientific retry.

Reuse the validated responsive monitor unchanged: .25-second requested polling,
one-second maximum completed safety interval, ten seconds per full scan request,
next request within five seconds of completion, maximum measurement age thirty
seconds and one accounting helper. Preserve 8 GiB combined sampled RAM,
worker/helper committed-memory limits 8 GiB/512 MiB, at least 50 GiB free disk,
32 GiB whole-root bound, 8 KiB scan records, 1 MiB receipt and 64 KiB publication
reserve. Initial and distinct post-shutdown accounting and owned cleanup are
mandatory; charged time, supervisor wall time and command wall time stay separate.

Preserve the 3,172-event prefix (61 closed attempts, 57 successes, four failures)
and tip `10ce622caf54c06526fa2b0b259889157711adeb35d4185d793e74cf845dad13`.
Freeze new allowed preservation metadata that includes all eight immutable human
response records and their completion record. Do not invoke a consumed runner
or force the old pre-human-review directory validator to accept new records.
Reject an existing target directory, unapproved suffix or partial-output adoption.
Keep all nine prediction embargoes, three sealed holdouts, prior reviews,
original localization outcomes and upstream player/court decisions unchanged.

## Approval and release

Approval would authorize minimal separate implementation, artificial focused
tests followed by the full suite, independent source review, and one conditional
execution within this exact two-input scope. Cover fixed report/endpoint joins,
wrong candidate namespace, unequal paths, confidence-only frame 300, exact and
near ties, sign/reconciliation errors, null human indices, forbidden pointer
following, bounded publication, cleanup, prefix and exhausted-attempt guards.
Reuse completed monitor validation; do not rerun benchmarks or visual reviews.
No tests are needed merely to prepare these documents.

Bind a new implementation certificate to the resulting source and evidence.
Staging and committing each require separate approval. Execution additionally
requires the verified clean commit and a create-only release checkpoint.
Ordinary implementation/tooling failures may be corrected within approved scope;
material evidence/resource/scope issues require investigation. No consumed real
attempt may be automatically retried. No training, model choice, quality gate,
broader visual review, scientific access outside the pair, push, PR or merge
is included. Any follow-up change depends on the returned evidence and its own
concrete scope.
