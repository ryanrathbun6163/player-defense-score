# Gap and anchor reference review

**Later status:** Ryan accepted this package with “ok great chat they have been
reviewed. move forward”. Separate [accepted-reference evaluation results](nba_gap_anchor_reference_evaluation_results.md)
now supersede the pending acceptance/scoring status below. The historical
preparation record and sealed draft remain unchanged.

Ryan's later “Move forward chat” authorized the
[27-frame reference plan](nba_gap_anchor_reference_plan.md). This is separate
from his completed review of the five continuous comparison videos. The
[approval](../configs/ball_tracking/reviews/nba_gap_anchor_reference_approval_v0_1.json)
and [frozen scope](../configs/ball_tracking/selections/nba_gap_anchor_reference_v0_1.json)
bind the source census before annotation. Preparation code and its tests were
integrated at `dc4687780af407c1ae6b3a4c7e12376e7f4e5ffb`, starting from
`c30567a98a556755e2d794b1581909fe95e06818`.

## Source-first proposals

The batch contains every repaired gap and both original endpoints: 34 targets
across ten contexts, comprising 27 new AI judgments and seven accepted controls
reused exactly. Two neighboring frames on each side give 74 native context
frames; forty context-only frames receive no annotations. P002 has no repaired
gap and contributes no new reference. All frames remain inside permitted
development segments, outside protected NFHS bands.

One preparation attempt completed in 22.016 seconds, reading 23 existing NBA
PNGs and decoding 51 permitted NFHS frames. Native source/container clocks,
PNG bytes and RGB hashes remain bound. No model calls, candidate-array reads,
training or prediction changes occurred. The preparation and ready receipt
were saved before any new labels.

The proposed new references contain 22 approximate complete-ball centers and
five indeterminate judgments with null geometry: SAC 1419–1421 and P003
333–334. Unknown means the source pixels do not establish the ball location;
it is not a hidden-ball negative or an interpolated center. The visible P001
18–20 and 90–92 ball portions support approximate centers with ten-pixel
placement uncertainty. DET 11722–11725 has substantial head/hand overlap and
blur, with twelve-pixel uncertainty. Those radii express annotator judgment,
not calibrated probabilities or a widened scoring threshold.

All new judgments retain AI authorship and pending human acceptance. The
inherited `human_amodal_estimate` geometry enum describes the complete-object
estimation method; it does not claim a human authored these rows. This is
source-first, not blind annotation: earlier footage/model reviews were already
seen. A second AI reader checked the ten DET/P001 centers after seeing the
first reader's proposed coordinates; that check is not independent annotation.

## Saved-object assessment and delivery

The source proposals were sealed at 2026-10-21 03:31:12 UTC before a separate
categorical inspection of all 34 exact saved emitted points. The
[compact result](../configs/ball_tracking/reviews/nba_gap_anchor_reference_result_v0_1.json)
binds the proposal, object judgments, checks and review media. These are AI
judgments pending Ryan's review, not new center-accuracy scores:

| Saved target role | Ball | Other object | Unresolved |
| --- | ---: | ---: | ---: |
| Twenty original anchors | 14 | 2 | 4 |
| Fourteen repaired positions | 9 | 1 | 4 |
| All targets | 23 | 3 | 8 |

All three other-object judgments concern the same SAC head at 1419–1421:
the new fill bridges already-wrong original anchors. The eight unresolved
objects are P001 18–20/90–92 and P003 333–334. P001's exact points lie at blurred
ball/sleeve boundaries. An amodal ball center can lie on an occluding arm, so
these are not confirmed arm errors or geometric rejections. P003 335 has a
probable ball identity. The seven reused controls remain separate and unchanged.

One [24.8-second compilation](../data/outputs/ball_tracking/nba/gap_anchor_reference_v0_1/review/attempts/281e8692da094388aadb39391605f82a/reference_compilation.mp4)
shows all ten contexts at five frames per second with an extra one-second
hold on each context final. Cyan marks reference centers and uncertainty;
there are no model markers in this primary reference review. The
[review guide](../data/outputs/ball_tracking/nba/gap_anchor_reference_v0_1/review/attempts/281e8692da094388aadb39391605f82a/review.html)
provides all 34 target stills, unknown-case notes, all ten context finals and
the actual compilation final, P003 frame 366. Because SAC has no defensible
reference center, that group's two panes retain the full source image; its
unmarked [source close-ups](../data/outputs/ball_tracking/nba/gap_anchor_reference_v0_1/annotations/sac_source_context.png)
remain available separately. Review all new targets, including apparently
ordinary cases; the seven accepted controls do not require renewed acceptance.

## Validation and next decision

Six preparation checks pass, including consumption of actual producer-shaped
records, exact accepted-control preservation, changed-source/protected-frame
rejection, failed extraction retention and resume integrity. The independent
actual preparation audit passes 792 checks, rehashing 89 bindings including
all 74 prepared PNGs. It independently checks PNG bytes and clocks; NFHS RGB
generation is covered by the producer checks rather than a second decoder.

Five renderer checks cover actual preparation-to-proposal transport, all
74 encoded keys/timestamps/pixels, reference markers, final holds and resumed
artifact integrity. An initially too-strict local marker tolerance failed
because the phone-compatible codec subsamples cyan strokes. That failed test
and its logs remain preserved; the corrected tolerance still rejects erased
markers. The affected checks passed afterward. Eleven distinct focused checks
pass on the final code; no full suite was repeated. Test logs remain under
the ignored preparation folder and `data/outputs/t/gap_anchor_reference_review_tests_*.log`.

The actual render completed on its first attempt in 21.437 seconds. All 74
encoded frames passed exact timing, source/reference/crop keys, paired-pixel
and local-marker checks; maximum panel mean absolute errors were 2.412/1.559
RGB levels. An independent media audit passed 1,232 checks, including fresh
artifact bindings and all 45 retained still keys, without an extra decode.
Across the assistant's readers, visual inspection covered all 34 encoded
targets, ten context-final stills and the actual final. This is still inspection
plus complete programmatic video checks, not a claim of human review or
continuous manual playback. No material rendering defect was found.

Ryan reviews the new reference package and accepts or corrects the proposed
labels, unknowns, uncertainty and actual context finals. Under the
[working agreement](context/working_agreement.md#assistant-first-pass-ryans-2026-10-18-clarification),
AI drafts remain separate until that decision. Only afterward publish a
separate human-accepted AI reference and score the saved original/repaired
outputs at the unchanged inclusive ten-pixel radius. Report 27 new targets
separately from the original 790; do not count the seven controls twice.

The unchanged rule is not promoted. Original evidence, the three accepted
bounded additions, retained `09da` checkpoint, rejected NBA continuation,
DET fitting exclusion, protected holdouts and three older pending motion
reviews remain preserved. No new fit, generic confidence survey or threshold
grid is authorized. These correlated, failure-selected development frames
are not independent validation or ball-phase completion.
