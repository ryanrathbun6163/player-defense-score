# Accepted gap and anchor reference evaluation

Ryan accepted the presented reference package with “ok great chat they have been
reviewed. move forward”. The separate
[acceptance record](../configs/ball_tracking/reviews/nba_gap_anchor_reference_acceptance_v0_1.json)
records this decision without changing the sealed AI draft or its historical
pending-review receipts. The 27 new judgments retain AI authorship and the
seven previously accepted controls remain exact. This is human acceptance of
assisted references, not independent human annotation or a separate adjudication
of every categorical object finding.

The [compact result](../configs/ball_tracking/reviews/nba_gap_anchor_reference_evaluation_result_v0_1.json)
binds the separate accepted reference, saved-output report and completion audit.
Implementation and acceptance were committed at
`9ee85aee0d468674efae855bb8da6893e183a2b8` before one successful 2.156-second
publication/evaluation run. No prediction, model, source pixel or candidate
array was recomputed. The original 790-frame report remains unchanged.

## New references, separate from the original baseline

The unchanged metric requires an in-image point within an inclusive ten source
pixels of the accepted center. Placement uncertainty is diagnostic only; it
does not enlarge that radius. Unknown centers receive no geometric outcome or
distance and are not silently treated as hidden-ball negatives.

| New reference subset | Frames | Original matched / wrong / missing / unscored | Repaired matched / wrong / missing / unscored |
| --- | ---: | --- | --- |
| Original anchors | 16 | 14 / 0 / 0 / 2 | 14 / 0 / 0 / 2 |
| Added positions | 11 | 0 / 0 / 8 / 3 | 8 / 0 / 0 / 3 |
| All new references | 27 | 14 / 0 / 8 / 5 | 22 / 0 / 0 / 5 |

| Source | Original matches | Repaired matches | Eligible references | Unknown references |
| --- | ---: | ---: | ---: | ---: |
| SAC | 0 | 0 | 0 | 3 |
| DET | 2 | 4 | 4 | 0 |
| Possession 001 | 4 | 6 | 6 | 0 |
| Possession 003 | 8 | 12 | 12 | 2 |

The eight newly measured recoveries are DET 11723–11724, P001 19/91 and
P003 194/205/362/363. Among all 22 emitted eligible positions, mean raw error
is 4.881 pixels and maximum error is 9.788 pixels. All seven reused controls
reproduce their complete original score records exactly; they contribute
nothing to the new denominator. These controls include the three previously
accepted additions, which remain accepted.

## Geometry does not settle object identity

The separate, previously sealed AI object assessment remains a second axis:

| New reference subset | Geometric match, object judged ball | Geometric match, object unresolved | Geometrically unscored, other object | Geometrically unscored, unresolved |
| --- | ---: | ---: | ---: | ---: |
| Original anchors | 10 | 4 | 2 | 0 |
| Added positions | 6 | 2 | 1 | 2 |
| All new references | 16 | 6 | 3 | 2 |

All six P001 references have approximate complete-ball centers, but the exact
emitted points remain visually ambiguous at a blurred ball/sleeve boundary.
They qualify geometrically under the existing metric; they are not six
confirmed visual identifications. Some placement uncertainties are as large
as or larger than the ten-pixel radius, so the result is sensitive to the
accepted approximate labels. No uncertainty subtraction or post-result label
correction was used to obtain these matches.

SAC 1419–1421 remain unknown ball locations. Separate source/object inspection
places both original anchors and the new 1420 fill on the same head. These
points therefore remain unscored geometrically while retaining adverse visual
evidence. The evaluation's zero new geometric errors does not clear this
failure. P003 333–334 remain unscored and unresolved. The categorical findings
retain AI authorship; reference acceptance does not invent separate human
verdicts about them.

This is a small, correlated, failure-selected development set, annotated after
earlier model/footage exposure. It is not an independent benchmark, full-clip
accuracy estimate, confidence calibration, broader-rule acceptance or a
ball-tracking phase pass. Saved candidate-availability fields describe only
each row's recorded pool, not an exhaustive search for the ball.

## Verification and preserved evidence

Four focused evaluator tests pass in 6.428 seconds. They cover actual producer
record transport, metadata-only publication/scoring, exact control reproduction,
inclusive ten-pixel scoring, unknown semantics, retained drafts, write-once
outputs and tamper rejection. No full suite was repeated for this isolated
consumer. An independent audit passes 1,901 checks: all 34 source/annotation
joins, all 68 score records, every aggregate and all seven unchanged controls.
It uses standard-library math without calling the project scorer and verifies
27 artifact bindings. The compact record binds this audit and the test log.
Earlier preparation/media checks and their preserved codec-tolerance test
failure remain in the [preparation result](nba_gap_anchor_reference_results.md).

The retained `09da1214e94f` checkpoint, rejected NBA continuation, original
790-frame results, protected holdouts, DET exclusion from fitting, completed
continuous-video reviews and three older pending motion reviews remain intact.
Generated references, reports and media remain ignored. No new fit, inference,
threshold search, prediction change or remote Git publication occurred.

## Recommended next bounded step

Prepare an appearance-verification dataset and evaluation design for both the
original anchors and proposed gap candidates. SAC demonstrates that smooth,
consistent endpoints can belong to the wrong object. Tightening temporal
smoothness alone cannot establish ball identity. A blanket head-proximity veto
would also reject valid DET ball positions near a shooter's head.

Before choosing or fitting an appearance rule:

1. Inventory candidate-centered examples from already permitted SAC and NFHS
   training contexts, with explicit ball / other-object / unresolved judgments.
   A geometric miss is not automatically a non-ball example. Keep source frame,
   candidate provenance and surrounding unmarked context available for review.
2. Split complete temporal contexts before labeling or fitting. Seek distinct
   wrong-object episodes for development and checking; the three neighboring
   SAC head frames are one episode, not three independent negatives. If enough
   distinct examples do not exist, report that limitation instead of tuning to
   this single failure. Keep DET excluded from fitting and all sealed holdouts
   untouched; DET remains development evidence, not an unseen final test.
3. Freeze one future rule after reference review. Preserve original predictions;
   use verified anchor/candidate appearance to allow or abstain from new fills.
   Keep these 34 already-exposed targets as a regression set, and report rejected
   head fills, retained ball fills, unresolved abstentions and lost valid fills
   separately, alongside the unchanged 790-frame comparison and synchronized
   visual review.

This section is a proposed next scientific increment, not an executed
appearance experiment or authorization for training. It specifies the evidence
needed before a model or threshold choice. The current accepted-reference
publication and saved-output evaluation are complete.
