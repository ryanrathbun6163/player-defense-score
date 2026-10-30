# Proposed reference batch for repaired gaps and their original anchors

## Decision and current status

Ryan reported reviewing all five continuous comparison videos with “Ok videos
reviewed. What’s next chat”. The [review completion record](../configs/ball_tracking/reviews/nba_temporal_gap_continuous_visual_review_v0_1.json)
preserves that event without inferring broader-rule approval. The
[continuous result](nba_temporal_gap_continuous_validation_results.md) passes its
790-frame numerical screen but adds an apparent head detection at unlabeled SAC
frame 1420. The original anchors at 1419/1421 already follow that head.

The next proposed work is **27 new source-first frame judgments**, plus reuse of
seven existing accepted references, covering all ten repaired gaps and both
original endpoints. It closes a specific evaluation blind spot before changing
the detector or selector. This proposal has not been executed or authorized by
the review-completion statement. No new labels, fit, inference or rule is created
by this document.

## Exact batch

| Source | New source frames, inclusive | New judgments | Accepted references reused unchanged |
| --- | --- | ---: | --- |
| SAC | 1419–1421 | 3 | None |
| DET | 11722–11725 | 4 | 11436–11439 |
| P001 | 18–20; 90–92 | 6 | 207–209 |
| P002 | None | 0 | None; no gap was repaired |
| P003 | 193–195; 204–206; 332–335; 361–364 | 14 | None |
| Total | Ten complete endpoint-to-endpoint groups | **27** | **7** |

The 34 unique target frames comprise fourteen filled positions and twenty
original anchors. All eleven previously unscored additions are included, along
with P001 19/91 and P003 333/334, whose visual interpretations remain uncertain.
The seven accepted frames retain their exact annotation, uncertainty, authorship
and acceptance record; they are controls, not new labels.

Derive this census from the successful continuous selection's ten
`all_frames_have_unambiguous_saved_candidates` gaps, not a hand-picked subset of
favorable examples. The existing result record binds that selection and its
790-frame scored report. Before labeling, freeze those bindings and each source
frame identity. Use existing NBA PNG/native-PTS records and the verified NFHS
source/container clock. Every target is inside a permitted development segment.

For visual context, include two native frames before and after each of the ten
endpoint-to-endpoint groups. These are 74 context frames in ten disjoint spans;
the forty added context-only frames receive no new reference judgment. Preserve
the permitted segment boundaries and never decode protected NFHS bands. These
tiny contexts supplement the already-reviewed full comparisons; they are not
new complete-possession or continuous-tracking evidence.

## Preparation and one compact review

1. Inspect source images without prediction markers for all 27 new targets,
   using adjacent native frames only as context. This is source-first annotation,
   not blind annotation: the footage and known failure have already been seen.
2. Apply the existing [annotation protocol](ball_tracking_annotation_protocol.md).
   Record ball identity certainty, visibility and a center with uncertainty only
   when the image supports one. If the ball's location cannot be established,
   keep it unknown; never infer its center solely from neighboring points.
3. Save AI proposals separately from accepted references, with exact source
   evidence and actual authorship. Preserve the seven existing references.
4. After the source proposals are fixed, separately inspect each saved emitted
   endpoint/fill: ball, another object, or unresolved. Bind this object assessment
   to the exact prediction. A visible head can be identified as a non-ball object
   even when the true ball center remains unknown; that supplies no fabricated
   geometric error or hidden-ball label.
5. Deliver one short compilation of all ten complete source contexts with
   explicit target-frame overlays and an uncertainty list. Show both ordinary
   cases and exceptions, with final-frame holds. Ryan reviews this new reference
   proposal in one batch; the previous model-output videos do not need repeated
   review merely to acknowledge completion.

Use the existing source readers, annotation validation and review components.
Implement only the missing binding/packaging work, with focused checks at changed
boundaries. Keep all source images, generated labels and video under ignored data
paths. No new model calls or cached-array analysis is required for annotation.

## Evaluation after reference acceptance

After Ryan accepts or corrects the proposal, publish a separate human-accepted
AI reference and score the already-saved original and repaired coordinates at
the unchanged inclusive ten-pixel radius. Keep visibility/identity outcomes and
qualitative wrong-object judgments separate from geometric center accuracy.
Unresolved judgments are not matches. Do not overwrite the original 790-frame
report or add the seven overlapping controls twice.

Report the 27 new targets separately, with endpoint and filled-position subsets,
and preserve the original seven control outcomes. Keep the source roles and
correlated, failure-selected nature explicit: this is a development regression
set, not independent validation or a causal generalization study.

A confirmed wrong-object or hidden-ball fill keeps broader adoption of the
unchanged rule unsupported. Determine whether each bad addition follows bad
original anchors, chooses the wrong candidate despite good anchors, or has
unresolved evidence. That outcome must choose the next detection/appearance or
selection intervention; do not launch another generic confidence survey or a
parameter grid. The three accepted bounded additions remain preserved controls.

## Why this precedes another rule or fit

The SAC head trajectory already satisfies every frozen timing and geometry
condition. Its saved component mass is about 8.444, above accepted DET additions
at about 5.549 and 2.991. Native score is summed heatmap response, not a calibrated
probability. A simple minimum-score floor that rejects this head would also lose
accepted gains. These saved facts do not prove every appearance feature useless,
but they do rule out treating stronger response or smoothness as object identity.

This batch cannot solve the remaining 32 DET/NFHS labeled misses, nine wrong
positions or thirteen hidden alarms, and it does not reopen the completed
aggregation diagnosis. It provides the missing accepted failure cases needed to
measure the next correction. No new training, threshold tuning, held-out access,
full-game processing, player-pipeline change or defensive-scoring work is part
of this proposal. The retained checkpoint and rejected NBA continuation remain.
