# Eight-frame P003 candidate identity review — proposed

Status: planning only; no new scientific access or human judgments authorized.
Prepared at `efeefd58f6801ffe5de106a48f8dad1e835b9647` on
`codex/ball-detector-baseline`.

## Question and fixed scope

Does the emitted candidate visibly depict the game ball, another object, or
something that cannot be resolved from the saved frame? If it depicts the ball,
does its marked center look plausible, clearly displaced, or indeterminate?

Use exactly P003 representative frames **300, 301, 302, 304, 308, 319, 320, 324**,
with the existing TT/cap20 setting (tight edge/tight cost, confidence floor .01).
These eight present-nonmatching frames come from the already returned
output-presence summary, source row `/pools/0/rows/16`. The four missing-output
frames 310, 311, 322 and 323 answer a different question and are excluded.
The saved raw 10-source-pixel localization result remains unchanged.

This is a case study of selected, correlated failures from one window and
setting. It cannot establish frequency, rank methods, demonstrate tracking
quality, or support generalization. Qualitative center placement cannot prove
the cause of the numerical mismatch. No training labels or method selection
are proposed.

## Existing images and exact access boundary

The companion metadata scope is
`configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_identity_review_v0_1.json`.
It names exactly sixteen existing PNGs: the unmarked source and native
TT/cap20 `view_0` overlay for each of the eight frames. Expected hashes are
copied from the committed retention proposal and its bound administrative
preservation audit. No PNG was read, hashed or decoded while preparing this
proposal; current image bytes have not been reverified.

Source inspection establishes `view_0` as the first arm's cap20 view. Its header
identifies the emitted candidate by `#candidate_index`; amber `alt #` markers
are alternatives, not emissions. The saved overlay also contains reference
geometry and localization outcomes. The `confidence_0.2` directory in the
unmarked source's path records earlier image provenance; it does not change
this case study's .01 setting. Original scientific manifests are provenance
pointers only and are not inputs to be reopened.

After approval and release, one owned, monitored worker may read/hash only
these sixteen scientific files, solely to verify their expected bytes. It must
not decode pixels, open scientific manifests, observations, candidates,
annotations, traces, reports or videos, or invoke broad review loaders.
It returns a bounded administrative receipt, preserving each expected/actual
binding and success or failure. No new inference, scoring or rendering runs.

Only after successful verification may the exact sixteen images be presented
to Ryan through file links or the image viewer. The parent does not read/hash
scientific bodies or inspect pixels. Ordinary viewer display and zoom are
within the requested human-review scope; no neighboring frames, video, new
crops, all-arm collages or broader closeups are included.

## Human review and record

For each frame, show the unmarked source first and its existing overlay second.
Disclose the overlay's prior reference markings. This is source-first review,
not blind or independent review. Ryan supplies:

1. Candidate identity: **ball / another object / uncertain**.
2. If ball: center **plausible / clearly displaced / cannot judge**; otherwise
   not applicable.
3. Optional note, including ambiguity or occlusion. Record the displayed
   candidate index only if it can be read confidently; otherwise leave it null.

If the emission cannot be distinguished from contextual markings, or the
existing presentation is insufficient, retain uncertainty. Do not broaden
access or create a new rendering automatically. Do not infer these decisions
from the completed six-clip package approval.

Keep an eight-row ledger with exact image bindings, frame/setting identity,
reviewer attribution, actual response and time, and the unchanged prior
localization outcome. Unanswered rows remain pending; no automatic pass or
invented reviewer statement. Preserve corrections as new records. Save review
records under a new ignored `candidate_identity_review_v0_1` directory within
the existing retention output root; do not overwrite reviewed artifacts.

## Proposed resource and release conditions

Request one new verification attempt, at most **120 charged seconds**, bounded
also by the existing cumulative remaining `11037.211000000018` seconds. This
limit is not an estimate. Human viewing time is separate from worker time.
It renews neither consumed diagnostic attempt and permits no scientific retry.

Reuse the validated responsive monitor: requested .25-second polling,
one-second maximum completed safety interval, ten seconds per full scan
request, next request within five seconds of accepted completion, maximum
measurement age thirty seconds, and one accounting helper. Preserve 8 GiB
combined sampled RAM, worker/helper committed-memory limits of 8 GiB/512 MiB,
50 GiB minimum free disk, the 32 GiB whole-root bound, 8 KiB scan records,
1 MiB receipts and 64 KiB publication reserve. Initial and distinct final
accounting, process cleanup and separate wall/charged times remain required.

Preserve the closed 3,121-event prefix and its tip
`7a990a3fd2b86502dd6245d6d08d2d17c75abe4534bad8d6cc323aa9c43ba701`,
all four historical failures, nine embargoes, three sealed holdouts, previous
reviews, budgets and outputs. Freeze current allowed metadata before dispatch;
reject an unexpected suffix or pre-existing target directory. Hash mismatch,
scope, evidence or resource failures require investigation. Routine tooling
problems follow Ryan's current failure policy; preserve failed evidence.

Approval would authorize the minimal verification integration, artificial
validation, and this one conditional verification plus human review. Reuse
existing infrastructure without repeating its completed benchmarks. Relevant
new code receives focused then full tests and `git diff --check`; no tests are
needed merely to prepare this proposal. Release requires the validated scope
to be separately staged and committed, with a clean checkpoint before the real
attempt. Every Git mutation still needs its own explicit approval. No push,
PR or merge is requested.

## Next boundary

Approve this exact sixteen-image access and eight-frame human-review scope
before implementation or scientific access. This proposal grants no approval
by itself. The next scientific conclusion depends on Ryan's actual judgments.
