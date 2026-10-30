# Local input plus wider context: completed information screen

October 30, 2026. **A limited positive information result, not a new model or
tracking-accuracy result.** The fixed wider view supplies useful clues for a few
ambiguous candidates while preserving the original close-up. This supports
designing one bounded representation pilot. It does not establish that a model
will learn those clues, solve the remaining errors, or reach the 95% goal.

## Completed comparison

Ryan's "Ok chat move forward" authorized this previously recommended CPU screen.
The original recommendation, frozen membership, all images, four sealed reviews,
joined analysis and readable viewer are under
`data/outputs/ball_tracking/input_context_screen_v0_1/`.

The finite population contains **100 candidate points on 69 saved frames**:

- 82 points on the complete 53-frame fresh BKN union: 24 failure-related frames
  and 30 source-time controls, overlapping at frame 122/72. Membership is the
  union of existing native choices, original-Q-top choices and all already
  matching candidates. This reference-assisted diagnostic sampling is not an
  accuracy evaluation or a new selection policy.
- 18 points on 16 historical frames: all ten HOU e01/194–203 recoveries, both
  candidate choices on e05/8–9, the first chronological HOU native-hidden case
  e05/3, and three exposed SAC1419–1421 illustrations. Ten fresh missing-choice
  slots and ten legacy missing-native slots remain explicit; no point is invented.
- BKN references remain AI-authored and human-accepted. HOU retains its stronger
  historical descriptive/regression-veto role; its benefits cannot justify
  choosing features. SAC semantics remain unaccepted prior-AI observations and
  cannot qualify the decision. DET imagery was not opened.

An additive role clarification corrected an overbroad initial HOU eligibility
flag **before authorizing paired review**. The original flag, initial audit and
frozen manifest remain intact alongside the effective per-case mask. This is a
narrower interpretation of the existing role, not a new permission or label.

The local image is the exact existing floor-centered 64-source-pixel crop,
bicubic-resized 256 and center-cropped 224 (about 56 source pixels of effective
view). The treatment keeps those 224x224 pixels unchanged and adds one fixed
192-source-pixel current-frame crop centered on the **same candidate**, displayed
at 224x224. No accepted-reference-centered crop, temporal context, enhancement,
new source acquisition or image/model generation was used. Source padding and
fractional point positions are retained; cyan markers occupy margins only.

Two independent AI reviewer agents, without inherited case history, first sealed
all 100 local-only judgments. Only then did each inspect all 100 paired views.
Scores, candidate origins, source identities and reference classes were hidden.
Each rated identity, visible support at the candidate point, confidence and the
specific new cue. These are 400 qualitative ratings, not human validation or new
training truth. Reviewers share a model family; memory, expectation and correlated
errors remain limitations. Anonymous IDs and sheet order were fixed before review.

## What the additional view contributed

Both reviewers reported concrete added clues and reached supported-ball agreement
on **four points across three frames**, in two frozen failure intervals:

| Cases | Existing accepted outcome | Additional visible clue |
|---|---|---|
| C016, BKN122/7 | Matching weak recovery point | The full forearm and lower body separate the round object beside the thigh from an elbow or uniform patch. |
| C006, BKN122/71 | Matching point | The head and arm outlines separate the orange ball surface from the adjacent dark head. |
| C052/C065, BKN122/72 | Two matching points on one frame | The same head/hand distinction becomes clearer with the surrounding body visible. |

C016 changed from nonball/uncertain to supported ball across the two reviewers;
the other three changed from uncertain to supported ball in both. These are
**three frames, not four recovered detections**. Intervals7–9 and71–72 were named
before review, but both are inside the same two-second clip and are not independent
plays. No new strict qualifying benefit was demonstrated in clips237 or365.

The source-time control C014 (BKN122/96) also changed from uncertain to nonball in
both reviews: the wider view reveals the continuous head, neck and blue-clad body.
It is useful supporting evidence, but does not count as a frozen failure interval.
Some other cases helped one reviewer while merely reinforcing the other's local
judgment; they remain in the complete joined table and do not inflate this count.

All **46 reference-matched points that both reviewers already supported locally
remained supported** with context. No reviewer withdrew a previously supported
ball judgment on a matched point, including the source-time and historical
controls. This is preservation of visual judgments, **not measured model retention**.
Identity agreement rose 93/100 to 97/100; agreement is not accuracy.

## Counterevidence and uncertainty

- Eleven paired cases remain unresolved by both reviewers. Three more retain
  an identity disagreement. Severe blur is not repaired by surrounding pixels.
- BKN122/52's two matching points C045/C081 remain uncertain in both views.
  The accepted ball region was already present locally; this does not establish
  missing context as the cause of the scorer's failure.
- BKN365/41's correct point C010 was already an obvious ball locally. The wrong
  courtside choice C002 was already judged nonball. Its ranking error therefore
  remains a counterexample to a universal missing-context explanation.
- HOU e05/8–9 (C094/C085) changed from confident nonball to uncertain in both
  reviews. The wider view invalidates the local jersey/armhole interpretation,
  but does not establish ball identity. These accepted matching points remain
  unresolved, not recovered, and supply no positive feature-choice evidence.
- The BKN237/51 candidate C067 remains a 10.746px geometric miss with recorded
  reference uncertainty. Reviewers disagree about its visible ball support.
  Neither geometric failure nor disagreement makes it a non-ball training label.
- Confidence decreases are preserved for C016/C085/C094. In each case a previous
  confident nonball judgment was revised; no previously supported matched ball
  lost categorical support. References and previous scientific scores are unchanged.

## Decision and connection to prior work

The finite engineering criterion is met narrowly: agreed concrete benefit in two
predeclared BKN failure intervals and no categorical success-judgment regression.
The justified next step is **designing one close-up-plus-context representation
pilot**, retaining the current model as control and preserving the original local
input. This is permission to consider/design that comparison, not a trained-model
pass, an adopted tracker, a crop-size sweep, or an automatic GPU launch.

The distinction from earlier work matters. The old player-context experiment used
distance to player boxes; hidden guesses inside those boxes had zero penalty.
The point-versus-CLS and Q/Q+ studies retained the same local image. This screen
tests additional pixels, while the failed Q+ transfer result still warns that
more examples alone did not preserve successes. Existing fitting data also lack
diverse current-detector failure situations; this screen does not repair that
support gap. BKN and HOU remain excluded from fitting and checkpoint selection.

A later pilot must isolate the added image information, keep comparison budgets
and fitting roles honest, preserve the successful local signal, evaluate exact
losses as well as gains, and retain hidden/weak-recovery vetoes. Its architecture,
training recipe and execution budget are not frozen here. The local-objective/
current-error-supervision alternative remains open if the learned context branch
does not improve the required tradeoff. No threshold or ranking rule follows from
these visual judgments.

Due diligence reused the accumulated full-history reconciliation and the preceding
recommendation's cross-study review, with fresh reads of relevant code, saved
records, coverage/transfer/gate reports and historical role requirements. It was
not a new reread of every chat or paper. A fresh check of the
[DCR paper](https://arxiv.org/html/1803.06799v3) supports testing difficult false
positives while also warning that excessive context can hurt small-object
classification. That paper does not validate a 192px view or predict this model's
gain. The present result supports a bounded comparison despite, not by ignoring,
the remaining locally clear mistakes and training-support limits.

## Verification and preserved outputs

Two focused geometry tests pass using the project's unittest runner. The initial
pytest invocation executed no tests because pytest is not installed; no dependency
was changed. Every fresh cached raw crop/tensor and every legacy64/224/CHW hash
matches. The independent renderer audit passed 3,243 checks, reconstructing all
100 tiles and all 20 contact sheets, source joins, marker positions and the full
population. The independent analysis audit passed 5,464 checks, verifying all
400 judgments, transitions, seals and effective roles. Unknown references and
all nine points near the geometric boundary remain explicit.

No detector/Q/J inference, fitting, reference change, protected evaluation or Git
integration occurred. Existing checkpoints and results were reused. There is
**no new numerical progress toward 95%**: the previously reported broader
Q-top+J 2541/2811 (90.39%) and the separate short-clip native 298/310 (96.13%) remain
unchanged and are not interchangeable benchmarks.

The machine-readable closeout is
`configs/ball_tracking/reviews/input_context_screen_result_v0_1.json`.
Independent analysis and preservation receipts are linked from it. The complete
local viewer is `data/outputs/ball_tracking/input_context_screen_v0_1/index.html`;
it is a local file, not a running web service.
