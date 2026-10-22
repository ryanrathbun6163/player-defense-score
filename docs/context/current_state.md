# Current State

## Latest increment: third reference batch accepted

The [third reference batch](../ball_tracking_completion_reference_batch_03.md)
contains 131 new P002 proposals, frames 368–498 through the actual clip final.
Selection used uncovered permitted coverage before inspecting new source pixels.
The complete native and slow overlays include uncertainty, frame controls and
unmarked source crops for null-center exceptions. Ryan explicitly answered
“Accept all 131 proposals.” A separate acceptance publication preserves the
reviewed annotations, nulls, native-frame records and AI authorship.

All 560 prior accepted rows and both earlier acceptance receipts remain unchanged.
Current coverage is 691/1,273 with 582 uncovered. The new batch includes 114
eligible centers and 17 nulls and remains evaluation-only. The original review,
config and preparation result retain their pending-era status; the later
acceptance receipt is the current authority. No repeat review is needed.
Source extraction and its independent comparison use only permitted packets
250–498, starting at a verified keyframe after the protected band. All 131 PNGs
match the comparison decode, with native timing and actual final 498 retained.

No implementation changes or repeated test suite were needed. Actual source,
proposal and emitted-media records were checked. Original AI drafts and reader
differences remain preserved, including conservative null geometry for severe
net overlap. No fitting, inference, scoring or protected evaluation ran.
Next: continue the fixed reference package with all three accepted campaign
publications in duplicate guards. New labels still need acceptance; campaign
approval remains in force and protected evaluation remains separately gated.

## Earlier increment: second reference batch accepted

The [second reference batch](../ball_tracking_completion_reference_batch_02.md)
contains 120 new P002 judgments for frames 50–169, selected from uncovered
permitted coverage before source inspection. Complete native and slow overlays
include every frame through 169, proposed centers and uncertainty, and an
exception list for null geometry. Ryan explicitly answered “Accept all 120
proposals” after the complete overlay and exceptions were delivered. A separate
acceptance publication preserves the original pending-era review artifacts.

The accepted P003 batch remains byte-identical. Current accepted coverage is
560/1,273, leaving 713 uncovered. The new batch has 98 eligible centers and 22
null centers; accepted unknown judgments remain unknown. The loader now includes explicitly bound accepted
campaign publications in duplicate guards while preserving historical replay.
Ten focused tests pass; all 120 new source PNGs match an independent decode.

Next: continue the fixed reference package with both accepted campaign batches
included in duplicate guards. No repeat review of either batch is needed. No fitting or inference
ran. Protected evaluation remains closed pending a frozen method and separate
explicit authorization. Campaign approval does not need to be repeated.

## Earlier increment: retained baseline, fixed sources and first reference batch

The approved [completion campaign](../ball_tracking_completion_plan.md) has
started from the exact clean handoff at `b1dbf027ee14`. Its
[first increment](../ball_tracking_completion_first_increment.md) packages
1,498 retained-baseline records: 979 observations, 294 missing permitted
frames and 225 protected positions. Three exact previously reviewed player/ball
videos are reused; all records and encoded frames were checked through finals.
Availability is not accuracy. No model output or reviewed player decision changed.

Four NBA parent-game roles and 24 source-only episode windows are fixed: existing
SAC, new CHI–IND and DEN–BOS for training; fresh local HOU–OKC for validation.
DET remains excluded from fitting/selection and TOR remains exposed development.
The first new reference batch is P003 frames 0–119, evaluation-only. Ryan
explicitly accepted all 120 proposals after the complete overlay was delivered.
The separate accepted publication brings curated coverage to 440/1,273 and
leaves 833 uncovered. Initial drafts, corrections and AI reader differences
remain preserved; no repeat review of this batch is needed.

Next: continue the fixed reference package: 833 uncovered curated frames and
3,839 selected NBA frame judgments. Fitting waits for accepted references and the frozen
executable recipe. No inference, new fit, protected pixel inspection, push, PR
or merge occurred. The campaign approval is already supplied; no repeat approval
is needed. Prior failed experiments and completed reviews retain their status.

## Earlier decision: completion campaign and ball-quality criteria approved

Ryan explicitly approved the completion plan and proposed ball-quality criteria,
then requested a complete handoff and execution in a new session. The
[approval record](../../configs/ball_tracking/reviews/ball_tracking_completion_campaign_approval_v0_1.json)
binds his exact statement and the approved plan at `faa2804`. The campaign is
authorized; do not request the same approval again. It has not started.
New reference acceptance and final trajectory review remain human decisions.
The 225 protected holdout/buffer positions still require a frozen candidate and
separate explicit evaluation authorization. No push, PR or merge is authorized.

Next session: confirm exact Git state and required reading, then assemble the
retained-baseline player/ball development package, select fixed source/episode
roles, and prepare the first 120–240 reference proposals. The approval event
has already been recorded. No extra diagnostic-only gate is a prerequisite.

## Earlier planning increment: completion campaign designed

Ryan requested a critical review of the full research and a concrete route out
of the ball phase. The [completion plan](../ball_tracking_completion_plan.md)
recommends retaining WASB, one broader multi-game training/validation package,
validation-selected training and at most one conditional higher-resolution fit.
It proposes an explicit numerical exit contract for the existing three-possession
finish line. They were new proposals at design time; the approval above now
accepts them. No improved model result is claimed.

Planning started from clean `codex/ball-detector-baseline` at
`759f43db37ba810ccf6516b2cdfd37a542dc5619`. No new source acquisition, pixel
inspection, labels, inference, training or protected evaluation ran. The rejected
verifier and retained `09da1214` baseline remain unchanged. Campaign/exit-gate
approval was pending at design time; reference and final-motion reviews remain human decisions,
and protected evaluation requires a frozen candidate and explicit authorization.
After campaign approval, the first increment is an integrated retained-baseline
development package plus fixed source/role selection and a first reference batch.
Earlier entries below are historical increments, not competing next actions.

## Latest increment: one trained verifier; protection checks fail

Ryan explicitly requested fixing the execution block and training. The
[execution amendment](../../configs/ball_tracking/reviews/nba_ball_distractor_execution_amendment_v0_1.json)
records one provisional fit using the unchanged AI-proposed label package;
new human label/grouping acceptance remains pending. Missing excluded clothing
and newly emitted excluded head examples still fail the original coverage gates.
The additional source search found arm errors, not the required categories.

The [trained model and result](../nba_ball_distractor_training_results.md)
use 90 fit object groups / 109 distinct crops and one fixed 385-parameter
logistic head over frozen DINOv2 features. The 33.125-second feature/fit run
converged in 17 iterations with no optimizer warning or retry. Accepted old
checks are only 5/10 correct (2/6 balls, 3/4 distractors). Proposed combined
checks are 24/46 ball crops and 19/20 distractor crops, or 19/39 ball and 17/18
distractor object groups when every member must classify correctly.

This exact recipe is rejected for adoption. The saved fit is real; it is not
an improved tracker. The full 3,373-point veto comparison retains 1,847 points and loses 207/581
protected geometric matches; all 14 fills are revoked. Four newly proposed
emitted distractors are removed, but the ball-loss gate fails. Missingness rises
from 602 to 2,128 positions. Comparison media belong to this same bounded
experiment, with no refit or changed cutoff. All five comparison videos are
complete; the result report links the saved model, media and compact evidence.
Twenty-six focused tests pass; new human motion review remains pending.
Unknown reference labels remain unresolved. The experimental arm can remove
points at unscored or unknown locations; original baseline trajectories,
protected spans and prior reviews remain intact.
Ball tracking is unfinished; downstream possession and defensive scoring remain ahead.

## Earlier increment: approved bounded reference batch; insufficient check coverage

The approved [bounded test](../nba_ball_distractor_reference_results.md) has a
complete 184-row AI label package: 106 ball, 51 other-object and 27 unresolved.
All 105 targets / 525 native context frames were inspected; the 26 previously
accepted classes are unchanged. Same-frame aliases reduce the combined resolved
census to 90 fit groups (52 ball / 38 other) and 57 excluded check groups
(39 ball / 18 other). New human label/grouping acceptance remains pending.

Two frozen adequacy conditions fail provisionally: no excluded clothing group,
and no newly sampled actually emitted head distractor. The two new check heads
were unselected; the four emitted negatives are hands/arms in two DET blocks.
No feature extraction, fitting or trajectory change ran. This is an
insufficient-data result, not classifier performance or improved tracking.

The [complete results and review links](../nba_ball_distractor_reference_results.md)
and [bound result](../../configs/ball_tracking/reviews/nba_ball_distractor_reference_result_v0_1.json)
record all unknowns, groups, unchanged evidence, focused validation and the full
review video through every context final. Ryan may accept/correct the new
package. If these labels stand, this exact test stops before fitting. The same
approval covers one fixed fit/comparison only if accepted labels satisfy all
frozen conditions; no second fit proposal is required, and no replacement
sampling or relaxed gate is authorized. Prior reviews remain unchanged.

## Earlier increment: bounded ball-versus-distractor test designed

Ryan requested the [concrete bounded design](../nba_ball_distractor_verifier_plan.md).
The [proposal](../../configs/ball_tracking/proposals/nba_ball_distractor_verifier_v0_1.json)
fixes 160 new detector-candidate judgments (96 fit/64 excluded check) plus 24
fit-only source-selected head/hand/clothing slots. All use 105 targets and 525
native context frames outside the old 149 context keys. P001 historical training
blocks explicitly join SAC/P002 fitting; DET/P003 remain excluded. Existing 26
accepted labels retain their roles, and the old 34 remain qualitative regressions.

Read-only reconstruction used 426 existing retained-checkpoint triplets in
11.765 seconds; all 142 reconstructed means matched saved originals, yielding
490 coordinate groups. These are not independent objects or new semantic
labels. Same-object grouping, class/block coverage and human label acceptance
must precede the single proposed 385-parameter logistic fit on frozen features.

The proposal covers one complete evaluation of all 3,373 saved emissions in
the five permitted clips, using a separate veto arm. It must remove actual
emitted excluded distractors across two blocks, preserve every verified match
and valid near-head ball, and remove the known SAC head episode. Unknowns stay
unscored; all changed episodes and actual finals require new human review.
The candidate-only inventory was too repetitive, hence the explicit 24 contrast
slots and capped training influence. Their centers/labels are still unassigned.

**Next action:** after explicit scope approval, implement and prepare the single
new label package. Human acceptance then releases one fit and complete comparison
if frozen coverage passes; no second fitting proposal is needed. Inadequate
coverage stops before fitting, with no replacement loop or relaxed gates.
This turn completed design and metadata/cache inventory only: no source-pixel
inspection, labels, feature inference, training or trajectory changes. Earlier
failed setups, accepted references, completed reviews and three older pending
motion reviews retain their status. Ball tracking is unfinished.

## Earlier increment: fixed appearance-feature screen completed and rejected

Ryan approved the fixed screen with “Ok move forward chat”. The
[results and complete crop review](../nba_appearance_feature_screen_results.md)
and [bound result](../../configs/ball_tracking/reviews/nba_appearance_feature_screen_result_v0_1.json)
record one 12.594-second run: 60 crops from 49 cached frames, 500 similarities,
no training, no operational failure and no trajectory changes.

The strict gate failed: **8/10 accepted checks**, comprising 4/6 balls and
4/4 hands. DET11059 and DET11431 balls preferred other objects. All three
SAC1419–1421 head points still preferred ball; all four valid DET11722–11725
near-head ball points remained ball-preferred. The six accepted unknowns stay
unscored. The 34 older points have eleven qualitative disagreements and eight
unresolved judgments; they are not newly accepted class truth or pooled checks.

Six focused tests passed; the later affected renderer check passed after a
header-only change. Independent audit verified all 500 similarities, all source
and crop/input pixels, provenance and unchanged earlier evidence. All 50 query
rows and the actual final were AI-inspected; all 150 displayed crop panels
match their saved crops. New human review is not claimed, and no prior review
must be repeated to close this failed setup.

**Next direction:** close this exact nearest-reference setup. A subsequent
bounded supervised-verifier proposal must specify necessary NFHS, distinct
head/clothing and contributor-candidate coverage together with one fixed test.
It is not yet an execution proposal or approval. No cutoff or crop/encoder sweep
follows from this failure. The saved trajectories, retained 09da checkpoint,
rejected continuation, accepted references, protected holdouts and three older
pending motion reviews retain their status. Ball tracking remains unfinished.

## Earlier increment: all 26 appearance references accepted and published

Ryan explicitly said “I accept the proposals. Move forward chat”. The
[acceptance results](../nba_appearance_reference_acceptance_results.md),
[acceptance record](../../configs/ball_tracking/reviews/nba_appearance_reference_acceptance_v0_1.json)
and [publication result](../../configs/ball_tracking/reviews/nba_appearance_reference_publication_result_v0_1.json)
record a separate human-accepted AI artifact containing all 26 exact object
judgments: ten ball, ten other-object and six unresolved. It retains all fifteen
targets, 75 context frames, candidate provenance, source roles and AI authorship.
DET11499 stays unresolved with its original reader disagreement preserved.
The draft, seal, review media and pending-era receipts remain unchanged; this
appearance-label review is complete and need not be repeated.

One publication attempt completed in 0.696 seconds without decoding source
pixels, loading candidate arrays, fitting, inference or geometric scoring.
Six focused tests initially passed in 10.845 seconds and passed again in 10.971
seconds after correcting only the local-evidence availability guard. The
publisher and actual publication remained unchanged. An independent standard-library
audit passed 380 checks on exact labels/candidates, source/PTS joins, roles,
acceptance, original evidence and unchanged prior artifacts. The original
790-frame report, accepted 27-reference extension and seven controls are intact.

**Pending approval:** the [fixed feature-screen plan](../nba_appearance_feature_screen_plan.md)
and [proposal](../../configs/ball_tracking/proposals/nba_appearance_feature_screen_v0_1.json)
would use pretrained DINOv2 ViT-S/14 features and one nearest-reference comparison.
Its exact census is 60 crops from 49 existing cached target frames: ten resolved
SAC reference-bank objects, ten resolved excluded checks, six unknown objects
and 34 previously exposed gap/anchor regression objects. All ten resolved checks
must classify correctly; unknowns remain unscored and never become negatives.
No training, parameter grid, trajectory update or label-driven replacement is
proposed. The screen has not run and this publication does not authorize it.

The ten bank labels all come from SAC; all five P002 fit-side examples remain
unknown. Excluded checks contain six balls and four hands, with no head/clothing
negative. Repeated objects and prior inspection prevent an independent accuracy
claim. The older 34 objects mix original means and contributor-derived fills;
they are a separate exposed regression challenge, not evidence of contributor
generalization or a held-out head test. A successful screen would justify
considering one later bounded abstention rule, preserving every original point
and supporting both anchors and every proposed fill. A blanket head-proximity
veto remains unsuitable. Protected holdouts, earlier completed reviews and the
three older pending motion reviews retain their existing status.

## Earlier increment: appearance references prepared; new human label review pending

Ryan's later “Move forward chat” authorized the
[appearance-reference plan](../nba_appearance_reference_preparation.md), recorded
in the [preparation approval](../../configs/ball_tracking/reviews/nba_appearance_reference_preparation_approval_v0_1.json).
The [results](../nba_appearance_reference_results.md) and
[compact result](../../configs/ball_tracking/reviews/nba_appearance_reference_result_v0_1.json)
cover **15 targets, 26 saved mean candidates and 75 native context frames**.
All original mean components at each target are retained in their saved order;
expanded/pruned gap pools are not substituted. The metadata census and source
roles were fixed before new source inspection.

SAC and P002 supply eight potential-fit targets/fifteen objects. DET and P003
supply seven excluded-check targets/eleven objects. Roles separate whole sources;
all supports stay inside the original permitted blocks. SAC was used by the
rejected continuation, NFHS by the retained detector, and DET was repeatedly
inspected in development. These checks are excluded from a future appearance
verifier's fitting, not previously unseen data. All 34 earlier gap/anchor targets
and their 74 context frames are excluded from this new census and remain linked
regression evidence. Protected frames and holdouts remain untouched.

Actual source preparation completed in 14.968 seconds, reading 55 existing NBA
PNGs and decoding exactly twenty approved NFHS frames. AI proposals classify
candidate objects as ball, other-object or unresolved from unmarked source
context; ambiguous occlusion boundaries remain unresolved. These are object
judgments, not new ball centers, geometric scores or automatically inferred
negatives. The drafts contain ten ball, ten other-object and six unresolved
judgments: potential-fit objects split 4/6/5 and excluded checks 6/4/1 in that
order. No new excluded-check candidate supplies a confirmed head negative;
the known SAC head regression remains a single previously reviewed episode.

The complete 48-second review rendered on its first attempt in 20.359 seconds.
Transport checks verify all 75 encoded source frames; independent audit passes
1,649 checks. AI inspection covers 31 encoded stills: fifteen targets, fifteen
context finals and the actual final frame. This does not claim continuous human
playback. Ten distinct focused tests pass (five preparation, five review), with
fixture/regex failures and corrected checks preserved.

**Next action:** Ryan accepts or corrects the completed appearance-label review
package. Human acceptance remains pending;
prior center-reference acceptance does not accept this new batch. Then use the
observed diversity and uncertainty to decide whether one bounded appearance
rule has enough evidence. No new fitting, inference, evaluation, threshold
selection or prediction change is authorized or run. The original 790-frame
report, accepted 27-reference scores, seven exact controls and earlier completed
reviews remain unchanged.

## Earlier increment: gap/anchor references accepted; saved-output scoring complete

After the explicit request to accept or correct the completed reference review,
Ryan said “ok great chat they have been reviewed. move forward”. The
[acceptance record](../../configs/ball_tracking/reviews/nba_gap_anchor_reference_acceptance_v0_1.json)
accepts all 27 new AI judgments, including 22 approximate centers and five
indeterminate/null cases (SAC 1419–1421; P003 333–334). This is human acceptance
of assisted references, not independent human annotation or separate semantic
object adjudication. A separate accepted artifact preserves AI authorship;
the sealed pending-era proposal, media and seven accepted controls remain exact.

The [completed evaluation](../nba_gap_anchor_reference_evaluation_results.md) and
[compact result](../../configs/ball_tracking/reviews/nba_gap_anchor_reference_evaluation_result_v0_1.json)
score only saved coordinates at the unchanged inclusive ten-pixel radius.

| New reference group | Original matched / wrong / missing / unscored | Selected matched / wrong / missing / unscored |
| --- | --- | --- |
| All 27 new references | 14 / 0 / 8 / 5 | 22 / 0 / 0 / 5 |
| Eleven new fills | 0 / 0 / 8 / 3 | 8 / 0 / 0 / 3 |
| Sixteen new anchors | 14 / 0 / 0 / 2 | 14 / 0 / 0 / 2 |

All seven reused controls reproduce their original scores exactly and are not
included in these new denominators. The original 790-frame report is unchanged.
Five unknowns remain unscored even when a point is emitted; uncertainty-adjusted
distance is diagnostic only. These selected, correlated cases are development
evidence, not an independent estimate of continuous tracking accuracy.

Geometric matches do not settle object identity. All six P001 points at
18–20/90–92 match their accepted approximate centers but remain unresolved in
the separate AI object inspection because of blurred ball/sleeve boundaries.
The SAC head anchors 1419/1421 and fill 1420 remain adverse visual evidence,
with unknown true centers and no geometric score. P003 333/334 also stay unknown.
Human reference acceptance does not turn unresolved object judgments into
confirmed ball recoveries or endorse broader adoption of the unchanged rule.

Publication and evaluation completed in 2.156 seconds without model calls,
arrays, pixel reads or decoding. Four focused tests and 1,901 independent audit
checks pass, covering all 34 targets, both arms and exact controls. Earlier
preparation/media checks, the retained codec-test failure, complete 24.8-second
review and its 74 permitted native
context frames remain documented in the
[preparation result](../nba_gap_anchor_reference_results.md). No full suite was repeated.

**Recommended next work:** prepare a bounded appearance-verification proposal
for original anchors and fill candidates, able to abstain when identity is
uncertain. Define distinct source-context candidate examples and excluded
evaluation roles before selecting one rule. A blanket head-proximity veto is
unsuitable because real DET ball observations also lie near heads. No new trial,
fit, threshold tuning, holdout access or broader adoption is authorized or run.
The retained checkpoint, rejected continuation, three accepted bounded gains,
completed five-video review and three older pending motion reviews are unchanged.

## Earlier increment: continuous videos reviewed; adverse visual evidence retained

Ryan separately authorized the [continuous-context plan](../nba_temporal_gap_continuous_validation_plan.md)
with “Move forward chat”. The earlier resume request did not authorize execution;
the bounded three-frame trial remains accepted separately. The new
[results report](../nba_temporal_gap_continuous_validation_results.md) and
[compact result](../../configs/ball_tracking/reviews/nba_temporal_gap_continuous_validation_result_v0_1.json)
record a completed saved-evidence comparison with all **24 numerical conditions
passing**. Five full comparisons are rendered and verified through every native
frame and timestamp. Ryan subsequently said “Ok videos reviewed. What’s next
chat”. The [later review record](../../configs/ball_tracking/reviews/nba_temporal_gap_continuous_visual_review_v0_1.json)
records completion of all five presented video reviews, without playback
telemetry, an explicit quality endorsement or per-frame adjudication. Original
pending-era receipts remain unchanged; these five reviews need not be repeated.

**Adverse visual evidence:** separate AI inspection of the encoded changed frame
and bound unmarked source frames 1418–1422 finds the added SAC point at frame
1420 (14.681 seconds into the comparison) on the foreground light-blue defender's
head/face. The original anchors at 1419 and 1421 also follow that head. The rule
bridges a consistent distractor trajectory. Frame 1420 is outside the 790 scored
references; no label, visibility annotation, center-error value or score changed.
The true ball center/visibility remains uncertain in this context. This finding
does not support broader adoption of the unchanged rule despite the numerical
pass. Ryan reported video review but did not explicitly adjudicate this finding.
Exact source, encoded-frame and crop
bindings are preserved in ignored `review/ai_sac_context_inspection.json` beneath
`data/outputs/ball_tracking/nba/temporal_gap_continuous_v0_1/`.

The unchanged rule processes 3,975 allowed frames in eight segments, excluding
225 protected NFHS positions. All **3,359 original points remain exact**.
Ten gaps supply 14 additional points: three labeled matches and eleven unlabeled,
unscored positions. The 3,373 selected points and 602 remaining missing positions
are availability counts, not full-clip accuracy.

| Group | Same-context original matched / wrong / missing | Selected matched / wrong / missing | Hidden alarms |
| --- | --- | --- | --- |
| SAC training fit | 218 / 5 / 47 | 218 / 5 / 47 | 0 unchanged |
| DET development | 207 / 8 / 22 | 209 / 8 / 20 | 13 unchanged |
| NFHS development | 131 / 1 / 13 | 132 / 1 / 12 | 0 unchanged |

Both included NBA controls remain 60/60. Scoring uses the same 790 labels, with
no new wrong frame, hidden alarm or lost correct position. All three accepted
additions (DET 11437–11438 and P001 208) retain their exact coordinates and match.
The older short-window NFHS control remains 130/1/14/0; its longer-context
131/1/13/0 control already includes the P002/49 recovery. That context benefit
is not attributed to gap repair. DET/NFHS still have 32 labeled misses, nine
wrong positions and thirteen hidden alarms.

The first attempt `890e7ac8d160491eb76f6d89d70c31be` failed before selections
were saved because imported NFHS identities lack a source-video field. Its
1.391 seconds and 48 cache reads remain consumed evidence. The routine source-
window identity correction at `ad82b03d2dbad115d188e83f62e99faf3ca1c88b`
uses a separate recovery configuration and preserves the original scope.
Attempt `c4c9e3e80c5b4beaaa49147f0e0ad3b5` completed in 4.031 seconds using
83 cached triplets, 132,172,876 compressed bytes and at most three retained
triplet arrays. Selections and their receipt were sealed before label scoring.
No inference, fitting, checkpoint load, threshold search or source-pixel decoding
occurred in selection/scoring; rendering is a separate step.

Twenty-one distinct focused tests pass; prior fixture failures and corrections
are preserved and no full suite was repeated. Independent audit passed 42,844
checks, reconstructing all 3,975 decisions without the producer selector,
all 790 outcomes/errors, protected slots and missing intervals, plus every added
component from fourteen original caches. NFHS actual container timestamps are
retained alongside the historical clip-relative reference clock.

The five videos cover all 4,200 timeline slots, including 225 black protected
slots, eight segment finals and five actual-final holds. Rendering and complete
pixel/timing verification took 676.688 seconds with no failed render attempts.
Independent media audit passed 12,832 checks without repeating video decoding.
AI inspection covered all fourteen additions and eight segment finals, with
adjacent context for SAC 1420 and P003 333/334. P001 19/91 and P003 333/334 remain
visually uncertain due to occlusion/blur. This was not manual review of all 4,200 slots.

**Next proposal:** [27 new source-first frame judgments](../nba_gap_anchor_reference_plan.md)
and seven unchanged accepted controls cover all ten repaired gaps and both
original anchors: 34 targets, with 74 permitted native context frames. The
assistant prepares one compact review, retaining unknown centers and separately
assessing whether saved predictions mark the ball, another object or remain
unresolved. After acceptance, score saved outputs separately from the original
790-frame report. This closes the unlabeled-failure blind spot before choosing
a detector/selector change. Preparation and execution are not yet authorized
by the video-review completion. No new labels, model calls or threshold search
have occurred.
Do not recommend broader unchanged-rule adoption from the numerical pass. The
three previously accepted labeled additions remain accepted; this new case is
separate adverse evidence from a previously unscored part of the longer clips.
The retained checkpoint, failed NBA continuation, sealed holdouts, DET fitting
exclusion and three older pending motion reviews remain unchanged. No broader
adoption, ball-phase completion or downstream possession/matchup work is approved
by this numerical result.

## Earlier increment (historical): fixed temporal gap trial accepted; continuous-context validation proposed

Ryan approved the [single temporal gap-selection trial](../nba_temporal_gap_selection_experiment.md#completed-single-run-result)
with “Ok awesome move forward chat”. One 0.391-second saved-output run fixed all
790 choices before scoring. It preserves every original point and fills only
two bounded gaps: DET frames 11437–11438 and P001 frame 208. All three additions
match the accepted references. DET improves **207→209/237**, missing 22→20;
NFHS improves **130→131/145**, missing 14→13. Wrong outputs stay eight/one and
hidden alarms 13/zero respectively. SAC stays 218 matches, five wrong and 47
missing; the included easy controls remain 60/60 in each NBA game.

All sixteen fixed numeric conditions pass, including the nine original
adaptation conditions and no added wrong points or hidden alarms in any group.
All thirteen focused checks (eight selector, five renderer) passed first time.
Independent audit passed 165,219 checks, recomputing all 790 decisions and
1,580 before/after scores, and confirming all 597 original emitted points are
unchanged. All three videos passed verification for every source frame, timestamp,
duration and paired image, including twelve actual window finals. AI inspection
covered the three encoded changed frames and all twelve encoded finals, not
continuous manual review of all 790 frames. The [compact result](../../configs/ball_tracking/reviews/nba_temporal_gap_selection_result_v0_1.json)
binds the evidence. Ryan subsequently said “Ok I approve. What next chat”. The
[later review record](../../configs/ball_tracking/reviews/nba_temporal_gap_selection_visual_review_v0_1.json)
closes the visual gate and accepts this bounded increment, without claiming
playback telemetry or changing the original pending-era receipts.

This offline rule uses original past/future anchors, native timestamps and
saved candidate coordinates; interpolated expectations are never emitted.
No fit, inference, heatmap processing, threshold sweep or baseline overwrite
occurred. The failed NBA continuation, uncertainty, protected holdouts, DET
fitting exclusion, NFHS finish line and three earlier pending motion reviews
remain unchanged. Twelve short windows do not establish continuous tracking.

**Next proposal:** [one continuous-context validation](../nba_temporal_gap_continuous_validation_plan.md)
of the unchanged rule on the two existing NBA cores and three permitted NFHS
timelines: 3,975 frames in eight segments, with 225 protected positions withheld.
Use saved model evidence and the same 790 labels; compare against each source’s
same-context control. The longer-context NFHS control is 131/1/13 matched/wrong/missing,
so context effects must be separated from selector gains. This broader run has
not executed. No new fit, parameter sweep or full-game run is proposed.

## Earlier increment (historical): candidate preservation supports one bounded selector trial

The approved [candidate-preservation experiment](../nba_candidate_preservation_experiment.md#completed-comparison)
completed once in 22.094 seconds across 790 frames, 1,580 means and 4,668
contributor planes. For retained checkpoint `09da1214e94f`, matching-candidate
availability improves from 207 to 213/237 in DET and 130 to 133/145 in NFHS.
Five DET and two NFHS gains are outside the ten prior anchors; five and one,
respectively, are outside the full 37-frame diagnostic context.

The nine gains cover 20% of 45 previously unavailable development frames.
**Thirty-six still have no matching candidate and cannot be repaired by selecting
from this pool.** Costs are 51 additional ambiguous development frames, DET
hidden nonempty frames rising 13→18/69, and median raw candidates rising one→four.
NFHS hidden frames stay 0/5. Easy-control availability remains 120/120 while
ambiguity rises seven→20. Candidate availability is not selected accuracy.

Seven distinct focused tests pass after one preserved missing-`game_id` fixture
failure and a single corrected-case rerun; production source did not change.
Independent audit passed 181,673 checks on its first attempt, checking all
1,580 frame-arm evaluations and numerically reconstructing 141 selected rows,
including every gain/newly nonempty hidden case. No fit, inference, media decode,
prediction or score change occurred. The failed continuation, baseline, completed
reviews, uncertainty and holdouts remain unchanged.

**Next:** define one fixed, label-blind temporal selector trial using the retained baseline's
saved candidates, permitting missing/uncertain output and preserving strict
`>0.3` and inclusive ten-pixel evaluation. Compare with original selected outputs
under existing gates, including no additional wrong outputs/alarms and retained
easy controls, and review new trajectories. This is not yet executed or authorized. The aggregation
question is resolved; do not restart a heatmap diagnosis or threshold sweep.

## Earlier increment (historical): 37-frame saved-output diagnostic complete

Ryan said: “Ok move forward chat. Run the 37-frame diagnostic.” The
[bound scope](../../configs/ball_tracking/selections/nba_adaptation_regression_diagnostic_v0_1.json)
and [results record](../nba_adaptation_regression_diagnostic_results.md) cover
exactly 37 source frames and 74 old/new means around six lost matches and four
recoveries. Means retain their original complete cached contributor contexts.
One 2.375-second run reproduced all 74 original means, candidates, selections
and scores. Eight focused tests passed. Independent audit fully recomputed all
74 means and passed 20,962 checks in 1.630051 seconds. Its first helper omitted
`in_source_bounds` and stopped after 1,128 checks; the failed receipt is preserved
and the producer was not rerun.

DET/11107 still has a correct 5.682-pixel candidate, but its response mass loses
to a stronger off-ball hand component (ball 11.953→11.161; hand 9.237→13.747).
DET/11501 retains a ball peak 4.809 pixels from the reference while its weighted
center crosses 9.272→10.014 pixels. Four NFHS losses retain individual `>0.3`
ball support, but their means fall to 0.279458, 0.187125, 0.216723 and 0.264340.
The four recoveries cross the same mean threshold in the opposite direction.
The unchanged averaging rule acts on changed individual responses; no single
universal fix or causal forgetting conclusion follows.

The run read 94 triplet bodies (149,913,392 compressed bytes) plus three original
NFHS mean bundles (39,639,143 bytes; 75 planes loaded, 22 selected planes measured).
Old NFHS source/window/frame/model provenance is preserved, without inventing
historical captured PNG/PTS hashes. The report records array memory separately
from total process RAM.

This compares saved true-ball response, overlapping-triplet averaging, component
center/mass and competing distractors at strict `>0.3` and inclusive ten pixels.
It made no model calls, fit, threshold change, label/score change or holdout
access. The unsuccessful continuation and retained `09da1214e94f` baseline remain
unchanged. Its video review is already complete; no repeat review is requested.

**Next proposal, not executed or authorized:** one cached candidate-preservation
experiment. Retain original mean-map candidates and add provenance-tagged,
in-image strict-`>0.3` components from original contributors, with both checkpoints,
original contexts, labels and ten-pixel radius unchanged. On the existing 790
frames (SAC 300, DET 340, NFHS 150), compare the presence of any matching candidate,
extra candidates per frame and newly nonempty hidden-reference frames. Report
SAC training fit, DET/NFHS development and the included 120 easy controls separately.
This is candidate availability, not a usable prediction or model promotion;
DET/11107's correct mean candidate already exists. No threshold or temporal rule
would change, and no fit, inference or holdout access is proposed.

## Earlier increment (historical): NBA continuation review recorded; failed screen and baseline retained

Ryan reported: “Ok I reviewed these chat. What’s the next step?” The
[later review record](../../configs/ball_tracking/reviews/nba_wasb_adaptation_visual_review_v0_1.json)
covers the three inline embeds: two complete NBA comparisons and the verified
31-second compilation of all six NFHS windows. This is user-reported review
completion, without playback telemetry or an explicit quality endorsement.
The original generated pending-review receipts remain unchanged as publication
history. This comparison no longer needs a repeated review request.

Ryan approved the [bounded NBA experiment](../nba_wasb_adaptation_plan.md) with
“Ok I like this chat. Move forward”. The bound config and approval were fixed
before execution. One continuation from expanded checkpoint `09da1214e94f`
completed 200 updates in 50.328 seconds, producing `da44ce06cdf7`. No retry or
intermediate-checkpoint selection occurred. The [fixed comparison](../nba_wasb_adaptation_results.md)
fails four of nine predeclared conditions. The expanded checkpoint `09da1214e94f`
remains the baseline; no second fit or threshold tuning has occurred.

SAC training-fit matches rise from 218 to 265 of 270, with five wrong locations
and no missing outputs. DET, excluded from fitting, changes from 207/8/22 to
206/10/21 matched/wrong/missing among 237 eligible centers. Hidden alarms fall
from 13 to nine of 69 probable-hidden references. Both easy NBA controls remain
60/60. NFHS changes from 130/1/14 to 129/1/15 among 145 eligible centers; hidden
alarms remain zero of five. DET's frame 11107 is a large new wrong-location
error (305.575 pixels); frame 11501 is a marginal failure (10.014 pixels). Fewer
misses or hidden alarms do not offset the failed screen.

Training uses 300 accepted SAC frames plus 150 prior NFHS training frames:
400 positive, 36 certain-hidden and 14 masked. Ten entirely masked triplets were
excluded, leaving 424 usable; 400 samples comprise 269 NBA and 131 NFHS triplets.
Twenty-four triplets were unsampled. The samples touch 440 frames; eight masked
frames and positive frames P001/375 and SAC/1059 have zero input exposure.
Native cadence and block boundaries are preserved. DET remains excluded from
fitting; TOR and protected holdouts remain untouched. SAC's subsequent scores
are training-fit evidence.

Seventeen distinct focused trainer/comparison checks passed. Independent training audit passed 3,469
checks, including checkpoint/state equality, unchanged BatchNorm buffers and
200 optimizer steps. Its initial missing-PyTorch environment failure is preserved;
the unchanged helper passed under the project environment without another fit.
The single comparison/media execution completed in 1,425.922 seconds with
2,836 new calls and no failed or uncertain calls. All eight videos cover 2,852
source frames with every-frame key/pixel verification and actual-final holds.
Independent comparison audit passed 48,264 checks, deriving all 790 scores and
checking every source join/cache record; numeric means/components were sampled
on 56 rows from 72 caches. It checked media receipts without duplicate decoding.
AI inspected 56 sampled source frames and all eight actual encoded finals.
The six NFHS clips also form a verified 31-second phone compilation, preserving
all 150 decoded frames and timing. Its initial packet-byte check failed; exact
decoded-pixel/timing verification passed without re-encoding or inference.
No model or phase gate is promoted. The negative motion result and three pending
motion reviews remain unchanged.

**Next concrete action (planned, not run):** compare saved old/new heatmaps around
the six lost matches and four recovered matches. Use exactly ±2 native frames
around DET/11107, DET/11501, DET/11013, P001/206, P001/207, P001/209, P001/221,
P001/223, P002/49 and P003/304, clipped to each original review window and
deduplicated. This gives 37 unique source frames: DET 15, P001 14, P002 three
and P003 five, or 74 old/new mean heatmaps. Reconstruct each mean from its
original complete cached contributor context, not a shortened context.

Compare true-ball response, averaging across overlapping triplets, component
center/mass and competing distractors at the unchanged strict `>0.3` and inclusive
ten-pixel match boundary. Preserve labels and scores. This routine inspection of
existing development outputs needs no new permission gate. Use it to select one
justified follow-up proposal; no new fit, data change or threshold tuning has been
approved. These ten selected events cannot establish causal NBA overfitting or
general forgetting, and the failed screen remains in force.

## Earlier increment (historical): approved saved-heatmap inspection completed

Ryan approved the inspection with “Let’s do it. Move forward chat”. The
[recorded scope](../../configs/ball_tracking/selections/nba_hard_example_heatmap_inspection_v0_1.json)
fixed 640 rows and comparisons before reading the heatmaps. One 19.937-second
run read 652 existing
cache files (1,037,888,584 compressed bytes) and reconstructed all 640 original
means exactly, including the original candidates and selections. No model calls,
checkpoint loads, training, source image/video decoding or prediction changes
occurred. Three rolling triplet arrays used at most 5,308,416 bytes; this is not
total process RAM. Seven intended new focused tests passed. Independent audit
passed in 3.297 seconds: all 640 rows/summaries and 652 cache records checked
structurally, with 126 rows independently recomputed numerically (all 82 failures
and 44 context rows). The other 514 were not independently recomputed numerically.

The [inspection report](../nba_hard_example_heatmap_inspection_results.md) explains
why reranking the saved candidates is insufficient. On 69 missing frames, the
local response median is 0.117843 and maximum 0.293772, below strict 0.3 support.
Only 11/69 had an original contributor with local support above 0.3 that vanished
in the mean; 58 had none. The global peak lies within ten pixels of the label on
only 21/69. Eleven of 13 wrong-location components overlap the label disk, but
only three component peaks match. Replacing weighted centers with peaks would
lose six of the 305 currently matched difficult frames while gaining three wrong
ones. No new selector or threshold was promoted.

The 73 hidden quiet frames have a global-response median of 0.109686, overlapping
missing-frame values; 13 hidden alarms have a median of 0.459021. These are
uncalibrated responses, not probabilities or a basis for an assumed safe lower
threshold. The original 305/387 score, 13/86 hidden alarms, 133 null geometries,
120/120 separate controls and original short-pilot score remain unchanged.

**Next concrete action:** prepare an exact bounded NBA adaptation/data proposal
emphasizing held and overlapped balls, using SAC alongside eligible NFHS training
examples to retain prior behavior, with DET excluded from fitting. Improving
model responses to these ball appearances
is a principal hypothesis; the findings do not prove one cause or approve a fit.
Failure-selected,
correlated human-accepted AI labels remain development evidence, not independent
NBA accuracy. TOR, protected holdouts, the NFHS finish line and the negative
motion result remain unchanged; its three human reviews are pending.

## Earlier increment (historical): difficult-scene labels accepted and saved predictions scored

Ryan accepted all four complete label-overlay videos without corrections. The
[acceptance record](../../configs/ball_tracking/reviews/nba_hard_example_label_acceptance_v0_1.json)
preserves his statement and binds the centers, uncertainty, unknown intervals
and actual final frames. User-reported acceptance remains distinct from AI
label authorship; no playback telemetry is claimed. A separate accepted
reference retains all 520 labels, including 387 defensible centers and 133 null
centers. Original proposals, media and prior results are unchanged.

The [saved-output diagnostic](../nba_hard_example_reference_results.md) completed
in 1.094 seconds: **305 matches, 13 wrong locations and 69 missing outputs** among
387 eligible centers. All 13 wrong locations are just beyond ten pixels and no
farther than 14.755 pixels. Separately, 13/86 hidden-ball frames emit an alarm;
47 other frames remain unscored. The 133 null centers are not assigned invented
geometry. The 120 easy controls remain 120/120 against longer-context outputs,
with eight changed-context edges kept separate from the original pilot score.

None of the 82 localization failures has another saved strict `>0.3` candidate
within ten pixels. Reordering those existing candidates cannot recover these
failures; this does not rule out subthreshold ball evidence. The scoring step used no new inference,
training, threshold change, image/video decoding or heatmap reaggregation.
Publication separately verified all 520 native PNGs.
Publication passed 21 distinct focused checks and the scorer passed nine. The
independent actual-report audit passed with zero issues, checking all 2,702
producer records and 640 scored rows, summaries and native-time intervals.
Earlier preparation failures and the scorer's corrected fixture attempt remain
preserved.

**Next concrete action:** prepare a bounded saved-heatmap inspection to explain
the 69 misses and 13 marginal localization errors before choosing fitting or
threshold changes. This is a recommendation, not approval of a new experiment.
These correlated, failure-selected human-accepted AI labels are a development
diagnostic, not an independent NBA benchmark. The six-fps label overlays do not
measure model trajectory improvement or comparative NBA/high-school accuracy.

SAC remains future-training-eligible, DET excluded from fitting and TOR outside
scope. Prior pilot acceptance, protected holdouts, the NFHS finish line and the
negative motion result remain unchanged; its three human reviews are pending.

## Earlier increment (historical): 520 NBA label proposals prepared for human review

Ryan approved the exact four-window scope: “Ok move forward”. The separate
[approval](../../configs/ball_tracking/reviews/nba_hard_example_reference_approval_v0_1.json)
preserves the original pending proposal. The [preparation record](../../configs/ball_tracking/reviews/nba_hard_example_reference_preparation_v0_1.json)
binds four complete review packages: **520 AI-proposed labels, 387 defensible
centers and 133 null centers**, with visibility and uncertainty retained. Every
native source frame was visually inspected; predictions did not supply label
coordinates. Prior model exposure and source/model-informed selection remain
disclosed, so this is a biased development diagnostic.

Twenty-six focused tests passed. The existing review renderer was reused with
approval/manifest verification for the new source windows. Independent transport
checks passed for all 520 review PNGs and four MP4 timelines (544 encoded frames
including final holds). Actual final frames 1059, 1359, 11119 and 11579 were
visually inspected. Playback is deliberately slowed to six source frames per
second, retaining native source timestamps; total review time is about 91 seconds.
Draft corrections and failed helper attempts remain preserved.

**Next concrete action:** Ryan reviews the four complete videos delivered in
chat and the [label-review guide](../nba_hard_example_reference_review.md), then
explicitly accepts the labels or requests corrections. Human label acceptance
is pending; no accepted new reference or new scores exist. Only after acceptance
will separate accepted AI references be published and saved outputs scored for
up to 640 frames, keeping the 120 existing pilot controls separate and the
original short-pilot score unchanged. No new inference or training has run.

Earlier pilot acceptance, the NFHS finish line, protected holdouts and the
negative motion result remain unchanged; three motion reviews remain pending.
SAC remains future-training-eligible, DET excluded from fitting and TOR outside
scope. Transport correctness does not establish label or tracking accuracy.

## Earlier increment: longer NBA videos reviewed; reference batch proposed

After both complete longer videos were delivered in chat for phone viewing,
Ryan reported: “Ok reviewed. What’s the next step”. The separate
[visual-review record](../../configs/ball_tracking/reviews/nba_wasb_action_observation_visual_review_v0_1.json)
records that later user-reported event. No playback telemetry, explicit quality
endorsement or new experiment authorization is inferred. Distractor selections
and visible-ball gaps remain unresolved; original result records and media stay
unchanged. The earlier short-pilot acceptance remains complete, and the three
motion-comparison reviews remain pending.

**Next concrete action:** decide on the [design-only hard-example reference
proposal](../nba_hard_example_reference_plan.md). Its four bounded windows cover
520 new frames: SAC 940–1059 and 1240–1359; DET 11000–11119 and 11420–11579.
The assistant would propose labels from existing native PNGs, preserving AI
authorship and uncertainty, then present complete short overlays for Ryan's
acceptance. Only after acceptance would saved frozen predictions be scored on
the new references and 120 existing pilot references, at most 640 frames.
The latter are longer-context easy controls, separate from the unchanged
original short-window score. Indefensible centers remain unscored.

These source/model-selected windows are a biased development diagnostic, not
an independent or representative NBA benchmark. No new inference, training,
threshold or motion change is proposed. SAC remains future-training-eligible,
DET excluded from fitting, TOR outside scope, and protected holdouts and the
NFHS finish line unchanged. No new labels or scores have been produced.

## Earlier increment: 2026-10-19 longer NBA action pass completed and audited

Ryan explicitly approved the exact longer plan: “I approve. Move forward chat”.
The [approval](../../configs/ball_tracking/reviews/nba_wasb_action_observation_approval_v0_1.json)
binds the immutable proposal; its original design-only/pending status remains
historical. The implementation is committed at
`4b67d0850897d539ab2994afc6349c0b6af11667`. Twenty-three distinct focused checks
passed: seven native-input, twelve observation and four review checks. The full
suite was not repeated; failed setup attempts and subsequent corrections remain
recorded.

The approved run completed in 1,238.416 seconds of process wall time: all
2,582 new model calls and 116 prior imports, with zero failed or unresolved
calls. SAC has 1,310 observed/161 missing/0 withheld frames; DET has
1,070 observed/161 missing/0 withheld. These 2,380/322 totals describe
availability, not accuracy. All 112 original pilot interior observations are
identical; eight edge frames receive longer context, while the original
120/120 short-window score stays unchanged.

The independent saved-output audit passed in 27.172 seconds with zero issues:
all 2,698 cached triplets, 2,702 mean heatmaps and 2,711 final components were
reconstructed, along with frame/PTS joins, selected points, availability
intervals and provenance. Both videos passed every-frame renderer checks;
the independent audit checked the bound receipts and saved ffprobe records
without another media decode. Actual final frames 2010 and 11898 have an
additional one-second hold. AI inspection covered all 2,702 frames and both
actual final frames, preserving 14 SAC and seven DET cues. It finds distractors
and visible-ball gaps; completion and correct artifact transport do not
establish tracking quality. The [compact result record](../../configs/ball_tracking/reviews/nba_wasb_action_observation_result_v0_1.json)
binds these outputs and checks.

**Next concrete action:** Ryan reviews both complete longer videos with the
exact cues in the [result and review report](../nba_wasb_action_observation_results.md).
Ryan's acceptance of the original short pilots is complete and unchanged;
human review of the two longer videos is pending. The frozen checkpoint,
strict `>0.3`, native timing, game roles, protected holdouts and NFHS finish
line remain intact. No training or new label scoring was added. The negative
motion result and its three pending new human reviews also remain unchanged.

Preparation took 162.884 seconds separately. Its loaded initial input-helper
snapshot is preserved: on-disk recovery/predecode-stat safeguards changed while
preparation was running, so a later start receipt hashes newer disk bytes.
Original receipts remain unchanged; fresh extraction commands and PTS/RGB
checks were unchanged. Preparation also used an earlier runner version; later
runner changes concerned post-preparation/inference handling. Inference and
rendering used committed `4b67d08` code.
The result report links the exact provenance note and retained setup failures.

## Earlier increment: 2026-10-19 NBA predictions accepted; longer action pass proposed

Ryan reported: “I reviewed both videos and the predictions look good. Move
forward chat.” The separate [visual acceptance record](../../configs/ball_tracking/reviews/nba_wasb_native_pilot_visual_review_v0_1.json)
records acceptance of both complete native pilot model-output videos through
their presented final frames. No corrections were requested. Both new reviews
are complete; original result/completion records, accepted references and
pending-era media/page remain unchanged. The later
[accepted-status page](../../data/outputs/ball_tracking/nba/wasb_native_pilot_diagnostic_v0_1/accepted.html)
uses the same videos. This is user-reported review, not claimed playback telemetry.

The [next proposed action observation](../nba_wasb_action_observation_plan.md)
has an exact [non-runnable scope record](../../configs/ball_tracking/selections/nba_wasb_action_observation_proposal_v0_1.json):
SAC–MEM source frames 540–2010 (1,471 frames, 24.541 seconds) and SAS–DET
10668–11898 (1,231 frames, 20.537 seconds). Together, 2,702 frames permit at
most 2,698 complete native triplets: reuse 116 completed pilot caches and make
at most 2,582 new model calls. Explicit scene boundaries may reduce these
counts; no triplet crosses a confirmed cut/replay boundary and the scope cannot
expand to replace withheld inputs.

This broader pass is **design-only, not implemented, approved or run**. It
keeps the expanded checkpoint, strict `>0.3`, native 16–17 ms input spacing and
complete-triplet averaging. It would expose shot/rebound/overlap and recovery
behavior, with two complete source-synchronized videos and availability counts,
not new-label accuracy scoring. No training, threshold search, interpolation or
motion selector is proposed. The original accepted 120/120 pilot score stays
unchanged: longer context may change eight pilot-edge means; the 112 interiors
should remain identical unless a newly declared scene boundary changes their
input context. Estimated new PNG/cache storage is 9.28 GiB plus
videos/receipts; 15–30 minutes is a working estimate, not a hard limit.

**Next concrete action:** Ryan decides on this exact broader scope. Approval
would cover implementation, proportionate validation and one resumable run;
routine implementation does not need another approval ceremony. Afterwards,
the assistant inspects the complete new timelines and Ryan reviews the actual
new videos. No new model calls, raw-video decodes, labels or tests occurred in
preparing this proposal. A read-only import-feasibility check repeated existing
hash/metadata/array checks on all 116 completed cache records, with zero issues;
it did not rerun inference, source decoding or scoring.

SAC remains future-training-eligible; DET remains target development and
excluded from fitting; TOR is outside this pass. No independent test game,
complete-possession certification, NBA identity/calibration acceptance or
ball-phase pass is inferred. The NFHS finish line, protected holdouts and
negative motion result stand; the motion study's three new human reviews remain
pending.

## Earlier increment: 2026-10-19 approved NBA diagnostic completed

Ryan approved the exact native-cadence diagnostic: “yes I do. move forward
chat”. One run completed all 116 unique three-frame inputs in 49.766 seconds,
with no failed or unresolved model calls, training or original-game decoding.
The frozen expanded checkpoint at strict `>0.3` matched **60/60 frames in each
game**, with zero wrong or missing outputs at the fixed inclusive ten-pixel
radius. Mean center distances from the accepted AI references are 2.779 pixels
for SAC–MEM and 2.894 for SAS–DET. See the [results and exact review videos](../nba_wasb_native_pilot_diagnostic_results.md)
and [bound result record](../../configs/ball_tracking/reviews/nba_wasb_native_pilot_diagnostic_result_v0_1.json).

**Next concrete action:** Ryan reviews both complete 11-second model-output
overlays through final frames 719 and 10847. These new human reviews are
pending; completed reference-label acceptance remains intact. Independent
saved-output/media verification passed: all 116 cached triplets, 120 outcomes
and 132 encoded review frames agree with the recorded computation and overlays.
The assistant inspected all 120 overlays and found no obvious switch/dropout;
this does not replace Ryan's visual judgment. No source/tests changed or earlier
suite/experiment was repeated.
Native 16–17 ms spacing was approved, but was not compared against 40 ms.
These two one-second scenes contain no hidden negatives and are not an
independent benchmark, complete trajectories or a ball-phase pass. SAC remains
future-training-eligible and DET remains excluded from fitting. Existing
holdouts, completed reviews and the negative motion result stand; its three
new human reviews remain pending.

## Earlier increment: 2026-10-18 NBA pilot labels accepted; diagnostic prepared

Ryan accepted both presented 60-frame AI proposal packages: “looks great chat.
move forward.” The [acceptance record](../../configs/ball_tracking/reviews/nba_assisted_label_acceptance_v0_1.json)
binds both clips, actual final frames and priority cases. All 120 labels retain
AI authorship and placement uncertainty; human acceptance is a separate event,
not a claim of independent human annotation or measured labeling accuracy.
Original proposals, pre-acceptance review videos and blank editor drafts remain
unchanged. A separate accepted reference bundle now exists at
`data/outputs/ball_tracking/nba/reviewed_pilot_v0_1/reference.json`.

The acceptance loader passed six focused checks and published that bundle once,
verifying all 120 native PNGs without reading the original game recordings.
The separate [frozen-checkpoint NBA diagnostic](../nba_wasb_native_pilot_diagnostic.md)
is implemented and its read-only plan confirms 116 distinct three-frame inputs
across the same 120 frames. Its seven initial focused checks use synthetic
records/fake model output; no actual model inference or NBA evaluation has run.
Six affected/new checks passed after provenance, locking and code-binding
corrections; two independent reviews found no remaining material issue. The
[preparation record](../../configs/ball_tracking/reviews/nba_wasb_native_pilot_preparation_v0_1.json)
binds the exact validated code, receipts and final read-only plan.

**Next concrete action:** decide on the exact proposed native-cadence diagnostic,
then run it once and review the resulting two overlays. It keeps the existing
expanded checkpoint and strict >0.3 threshold, with no fitting, threshold search,
interpolation or external context. Native input spacing is 16–17 ms rather than
the earlier NFHS 40 ms; this scientific choice is declared and awaiting approval.
The recipe reports each game separately against the accepted AI references.
These short visible-ball scenes cannot establish hidden-ball behavior, full
trajectories or general NBA accuracy. SAC remains future-training-eligible;
DET remains target development and excluded from fitting. Holdouts, completed
experiments and reviews stand. The negative motion comparison is unchanged,
and its three new human reviews remain pending.

## Earlier increment: 2026-10-18 assistant first-pass NBA labels ready for review

Ryan asked the assistant to take on more ball-tracking work and streamline the
process. The assistant has now visually inspected all 120 approved native PNGs
and saved separate, explicitly AI-authored proposals. SAC has 57 fully visible
and three partially visible balls; DET has 14 fully visible and 46 partially
visible balls. All 120 proposals contain a center with placement uncertainty;
none uses detector predictions or interpolated hidden positions. These counts
describe proposed labels, not measured accuracy or human acceptance.

Two 11-second source-plus-zoom review videos, every-frame overlays and a combined
review page are prepared under ignored
`data/outputs/ball_tracking/nba/assisted_pilot_v0_1/`. Thirteen priority frames
highlight contact boundaries, blur and a bounce; the full short clips still
need review. Actual final frames 719 and 10847 are included and held for one
second. Original editor drafts remain revision zero, genuinely unlabeled and
byte-for-byte unchanged. The AI proposal wrapper retains the actual authorship,
source-image evidence, uncertainty and pending human review.

Five new focused renderer checks passed on their first run, including an actual
encoded-video tail check. An independent audit of the actual packages passed
all 120 mappings, image/proposal/receipt hashes and displayed marker coordinates;
both videos report 66 encoded frames at 6 fps and their sampled tails match the
final overlays within lossy tolerance. See the [guide](../nba_native_annotation_guide.md)
and [bound preparation record](../../configs/ball_tracking/reviews/nba_assisted_annotation_pilot_v0_1.json).
No original recording was decoded again and no detector inference, training,
evaluation, holdout access or earlier review was repeated.

**Next concrete action:** Ryan watches both complete short overlays and checks
the priority frames, then accepts the proposals or identifies corrections by
game/frame number. The assistant performs corrections and preserves versions;
Ryan need not enter every point manually. Human acceptance remains separate
from AI proposal creation. This pilot is about one source second per game,
not a completed tracker or full-possession result. Existing game roles, NFHS
finish line, holdouts and completed reviews stand; the negative motion result
and its three pending new human reviews remain unchanged.

## Earlier increment: 2026-10-18 approved NBA pilot ready for annotation

Ryan explicitly approved the proposed game allocation and two-clip, 120-frame
pilot: “Yes I approve. Move forward chat.” The new [approval record](../../configs/ball_tracking/reviews/nba_development_selection_approval_v0_1.json)
binds the preserved proposal. SAC–MEM is the future-training candidate pool;
SAS–DET is target-case development; SAS–TOR is additional development. No
independent test game or new fit/evaluation is authorized.

The separate native-timestamp annotation workflow is implemented. Original
source frames 660–719 (SAC) and 10788–10847 (DET) now exist as 120 lossless RGB
PNGs with exact integer PTS and genuinely unlabeled drafts. Extraction and an
independent bounded decode agree on every frame's source PTS and RGB pixels.
No full recording hash/decode was repeated. Frozen NFHS helpers are unchanged.

The local browser editor loads one image at a time, supports zoom and original-
pixel placement, validates uncertainty/missingness, saves atomically with prior
snapshots, and rejects stale revisions or changed provenance. Twelve schema,
three synthetic extraction and twelve current editor checks passed. Synthetic
browser save/reload and real first/final-frame loading were checked. A browser
automation timeout after a synthetic unsaved-change dialog remains recorded.

**Next concrete action:** Ryan labels the two pilots in the open editor using
the [native annotation guide](../nba_native_annotation_guide.md), then reviews
the completed labels and actual final frames. The 120 real rows were still
unlabeled at preparation verification; no model, training or evaluation ran.
Source-use approval does not accept labels, complete possession boundaries,
NBA identity, defensive responsibility or calibration. The Detroit opening
inbound remains unseen. Existing NFHS holdouts and completed reviews remain
unchanged; the negative motion comparison stands and its three new human
reviews remain pending.

## Latest preparation: 2026-10-18 NBA candidates inspected; split/pilot proposed

Six source-only review clips are prepared with exact original-frame and PTS
mappings: three early SAS–DET candidates and three SAC–MEM quarter-opening
candidates. Independent checks passed for 12,466 frames, 422 sampled images,
21 contact sheets and all six review-video hashes. These are muted, lossy
review derivatives, not label truth. No full-game acquisition/decode, old
scientific experiment or completed review was repeated.

The proposed first pair is SAC–MEM's opening episode (source frames 540–2010)
and SAS–DET's partial half-court action (10668–11898). The latter's opening
inbound is not shown. Other candidates retain camera-cut, overlay or obscured-
start limitations; no complete-possession or primary-defender certainty is
invented. See the [selection plan and two primary review clips](../nba_development_selection_plan.md)
and [non-runnable proposal](../../configs/ball_tracking/selections/nba_development_selection_proposal_v0_1.json).

**Pending scientific decision:** use SAC–MEM as a future training source,
SAS–DET as target-case development and SAS–TOR as additional development;
prepare an initial 60-frame native-source annotation pilot from each primary
clip (120 total) after a timestamp-aware annotation path is implemented.
All three games remain development-visible; there is no independent test game.
The roles, source-selection acceptance and pilot are proposed, not approved.
No labels, model calls, evaluations or training occurred. Native PTS must not
be silently replaced with the old 25 fps/frame-index timing contract.

**Next concrete action:** Ryan reviews the two primary candidates and decides
on the proposed allocation/pilot. Then implement and verify a separate NBA
timing/source-mapping annotation path before creating genuinely unlabeled
pilot records. No fit or model comparison is authorized by this proposal.
Existing NFHS holdouts, ball-phase finish line, completed negative motion
comparison and earlier reviews remain unchanged; three new motion human
reviews remain pending.

## Latest access result: 2026-10-18 repeated complete recordings verified

The public replay-to-file route has now produced three specific local NBA
recordings. In addition to the chosen Spurs–Pistons game, Kings–Grizzlies
(`0022500829`, February 23) and Spurs–Raptors (`0022500843`, February 25)
were acquired at 1920×1080/nominal 60000/1001 fps. Each passed an independent
assembled-range/full-hash audit and one complete audio/video decode:
357,233 and 423,838 video frames respectively. Sampled visuals establish the
correct matchups, all four quarters, opening tips and final results of
123–114 and 110–107. See the [repeatability report and bound evidence](../research/nba_footage_repeatability.md).

This establishes practical repeated acquisition on these examples, not an
entire-season supply or every-possession continuity. The files share one
hosting route. Exact quarter-start coverage remains unproven; Toronto's Q2
zero/end graphic was not isolated. The chosen game's Q4 opening limitation
below remains unresolved. The Kings original receipt-writing failure remains
failed; recovery used existing parts with no redownload. Toronto's full decode
exited 0 with one preserved output-timing warning and a qualified rounding
explanation. Cleanup removed only verified duplicate download pieces.

**Next concrete step:** prepare the NBA development-possession selection and
split plan using the acquired files, then inspect the exact selected intervals
for complete actions, cuts, replays and useful court views before labeling or
training. These three inspected games are development-visible; no independent
game holdout or accepted split has been designated. Existing NFHS holdouts
remain untouched. Earlier training, evaluations, observations and completed
reviews remain complete; the negative motion result is unchanged and its
three new human reviews remain pending. No method or phase gate is promoted.

## Earlier access result: 2026-10-18 chosen NBA recording acquired and decoded

Ryan authorized moving forward after the footage-access research. The selected
Spurs–Pistons recording is now local at
`data/raw/nba/0022500828/0022500828_ok_12326019402326_1080p.mp4`:
6,081,103,430 bytes, 1920×1080, nominal 60000/1001 fps, 1:55:39.509,
415,953 video frames. SHA-256:
`27b5143105f5bf3276a2cc51945133c9fdcd2b82d4247d8365110428062ec21f`.
An independent prefix/range/full-hash audit passed. One complete video/audio
decode passed with an empty warning/error log. Original transfer interruption,
failed preflights, consumed resources and their receipts remain preserved.

All four quarters are present. Opening/closing and selected clock/quarter
checks support practical development-clip selection; **every-possession
continuity remains unproven**. At the Q4 opening, the broadcast returns from
a coach interview with play already underway; its opening inbound is not
visually established and must be excluded from uninterrupted-possession claims.
The saved scoreboard OCR has substantial
missingness. Its three clock flags resolve to one actual apparent dead-ball
clock correction and one OCR mistake that produced two flags. Long OCR gaps
inspected in the fourth quarter contain visible broadcast content, stoppages
and live play. These observations are not a claim that all 48 live minutes
were continuously shown. See the [acquisition report and evidence](../research/nba_game_0022500828_acquisition.md).

**Next access step:** verify additional complete game files before describing
this route as repeatable. This chosen game, short research clips and repeatable
full-game access remain separate requirements. Before labeling NBA footage,
specify the development/split plan and inspect the exact selected possessions
for cuts, replays and suitable court views. This acquisition used no ball model,
added no ball labels and repeated no earlier science or completed review.
Existing holdouts remain untouched; the three new motion-comparison human
reviews remain pending. No method or phase gate is promoted.

## Earlier access result: 2026-10-18 exact NBA game samples verified

The full handoff and expected clean starting state were confirmed on
`codex/ball-detector-baseline` at `10f3d4cfd0ce2f3fce2be898e8f498fc2cb1d4d6`.
Ryan then requested a broad, in-depth footage-access investigation, explicitly
including unofficial sources. The [decision report](../research/nba_footage_access.md),
three detailed chapters and source ledger preserve that investigation.

An exact-game replay page leads to public OK video `12326019402326`. Eight
downloaded segments decode at 1920×1080 and 60000/1001 fps, showing the opening
tip through the final Spurs 114–Pistons 103 scoreboard. These samples and their
playlist consumed 52,881,180 payload bytes. The full MP4 endpoint declares
6,081,103,430 bytes, but **the complete file has not been downloaded and
continuous game coverage is unverified**. A separate MEGA candidate has live
metadata and a 5,289,752,196-byte binary endpoint; its media is unverified.
Two additional games have live replay-to-MP4 endpoints, which is promising
access evidence, not completed repeatable full-game acquisition.

A separate BARD Brooklyn–Detroit event clip was completely acquired and decoded:
5,867,901 bytes, 1280×720, 60 fps, 473 frames including the final frame. It is a
short research clip, not a full possession or the chosen game. Inf-Stream also
exposes historical game-length NBA files with verified public headers; sampled
containers are 720p/24 fps. This fixed corpus does not establish current-game
availability. Public availability does not establish underlying footage rights.

Ryan recalled that the assistant supplied the original `playon_full_game.mp4`.
The migrated first transcript confirms the public PlayOn NFHS sample HLS and
FFmpeg download command; no PlayOn Home/Cloud recording product was involved.
The historical user terminal records the same 4,849,555,188-byte size as the
current raw file. No old source pixels or protected ranges were inspected.

**Next access step:** acquire the selected 6.08 GB source into a new ignored,
game-scoped raw directory, verify bytes/hash and full decoding, then audit all
quarter boundaries and game-clock coverage. Verify additional complete games
before claiming repeatability. Do this before further labeling or training.
The three requirements—research clips, this exact game and repeatable complete
games—remain separate. No source or dataset was accepted as a new benchmark.

The prior OBS failure remains failed. A new sample-thumbnail helper failure
and its local recovery are both preserved in the ignored research evidence.
No scientific run, prior review, holdout or full test suite was repeated.
The motion comparison below stays complete and negative; **its three new
human reviews remain pending**, and all earlier completed reviews stay complete.

## Latest result: 2026-10-08 fixed motion comparison completed; do not promote

Ryan approved one candidate-only comparison with "Yes move forward". The fixed
rule at implementation commit `915ba13c2910efa7f875cb251b7bc049790d1df3`
completed once in 175.5554 seconds, with zero model calls. Selection took 0.2004
seconds; selection plus scoring took 0.3083 seconds. Training, inference,
thresholds, original observations and completed reviews were not repeated.

Both arms select exactly the same candidates on all 150 released development
frames: **131 matched / 1 wrong-present / 13 missing / zero hidden alarms**.
The historical short-window result remains 130 / 1 / 14 / zero; P002/49 is now
4.531 pixels from its reviewed center in both longer-context arms. That is a
context difference, not a motion-selection gain. No training or withheld frame
enters scoring, and the existing ten-pixel radius is unchanged.

Across the longer timelines, motion changes 13 frames: nine in P001, two each
in P002/P003; three candidate switches and ten abstentions. It leaves 969 points,
304 missing positions and 225 withheld positions. All 294 originally empty
visible frames stay empty. These are training-inclusive availability counts,
not accuracy rates. P001/256 is a training frame and remains unscored.

AI inspection covered all 13 changes. P001/247 appears to recover the ball, but
P001/441-443 and /462-463 discard visible-ball observations and damage recovery.
P001/230 appears to switch between wrong objects; training frame /256 appears
to switch from a possible ball observation to an elbow. P001/185, P002/454-455
and P003/19 and /64 appear to suppress distractors. These are visual inspection
notes, not new labels or Ryan's judgments. With no labeled improvement and
visible recovery losses, this setting should not be promoted.

All three new comparison videos decode all 1,498 frames through their final
frames; all 225 protected frame pairs are black. **Ryan's review of these new
videos is pending.** His previous three longer-video reviews and all other
completed reviews remain complete. Holdouts, the quality bar and phase acceptance
are unchanged. See [comparison, evidence and new review videos](../ball_wasb_motion_selection.md).

Outputs are under `data/outputs/ball_tracking/wasb/wasb_motion_selection_v0_1/`.
The independent saved-output audit in `diagnostics/independent_saved_output_audit_01/`
verified original candidate transport, training exclusion, geometric distances,
paired reports and aggregate arithmetic without rerunning selection or scoring.
Three inspection-note files are under `diagnostics/visual/`. Validation is 19
focused passes before the final renderer bounds correction, then four affected
renderer passes afterward; no full suite ran. Initial import/TEMP validation
failures and the partial inspection-helper failure remain preserved. The actual
scientific invocation succeeded without retry.

Next recommendation: improve the visual evidence needed for missing positions,
using a separately specified development comparison. No new trial or blind motion
parameter search is approved; candidate-only motion cannot fill empty frames.
The older checkpoints below retain their historical approval and review states.

## Latest result: 2026-10-08 longer development observations completed

Ryan directed "Review. Move forward". Technical review and longer development
inspection proceeded under standing runtime/data/local-integration authorization.
Ryan subsequently confirmed "Ok what’s the next move. I reviewed the possessions".
All three longer videos are now reviewed, recorded in
`configs/ball_tracking/reviews/wasb_expanded_development_observation_visual_review_v0_1.json`.
This is review completion, not acceptance of every prediction or the phase gate.
The earlier six short candidate clips were not separately named; retain their
historical status without requesting that review again as a planning blocker.
Completed older reviews remain complete. No operating point is promoted.

Implementation commit `23fc90876458068ca422708bef92a35357bfa201` adds an isolated,
configuration-driven longer observation runner. Nine focused checks passed in
1.808 seconds, including actual old-producer/cache-consumer compatibility and
real synthetic video exclusion/final-frame checks. No full suite was run.

The fixed expanded checkpoint at 0.3 processed 1,273 visible frames once. It
reused 138 raw triplets and computed 1,123 new triplets; no training or threshold
search occurred. Runtime including rendering was 212.761 seconds, with 17.832
seconds of new inference and 263 MiB peak allocated GPU memory. Three 25fps
timelines contain 499/499/500 frames; each has 75 black positions preserving the
sealed holdout plus its surrounding 25-frame buffers. Temporal inputs never
cross those bands. All final frames decode and all protected display areas
are verified black.

Counts are P001 324 observed/100 missing, P002 308/116, P003 347/78, plus 75
withheld each. These are unlabeled, training-inclusive availability counts,
not correctness metrics. There are no interpolated points or connecting trails.
All 130 old same-context development heatmaps remain bit-for-bit equal; 20
boundary means change with longer context. P001/223 and /224 remain missing;
P002/49 newly emits an unscored point. The frozen six-window metrics are unchanged.

AI spot-review finds a distractor at P003/64: the marker is on white jersey 21's
waist while the ball is visible with white jersey 24. This is a human-review cue,
not a new label or accuracy metric. Motion consistency is a plausible next test
for rejecting such points; recovery of missing positions is still unproven.

See [longer results and three review videos](../ball_wasb_development_observation.md).
Outputs are under
`data/outputs/ball_tracking/wasb/wasb_expanded_development_observation_v0_1/`.
Summary SHA-256 `722a60dab8d34aa7acd3cbc5d1fc1635042050fb8a5d0f65fa96a7e380ae1b9f`.
The independent saved-output audit passed. Next recommendation: one motion-assisted
selection comparison on the existing 0.3 candidates, preserving missingness and
reacquisition. Compare against native-mass selection on the same longer-context
caches at the 150 existing development label frames; do not mix in training frames.
This specific scientific change is proposed, not yet approved or executed. It
cannot fill the 294 frames with no candidate; recovery needs a separate visual-
evidence change. Do not repeat the completed fit, six-window evaluation or this
observation pass merely to resume. Full-possession tracking and phase acceptance
remain unfinished; reserved bands have not been released.

## Earlier result: 2026-10-08 expanded training improves P001 substantially

Ryan approved all three new label clips: "yep these look good. move forward chat".
The review record is
`configs/ball_tracking/reviews/wasb_training_expansion_label_review_v0_1.json`.
Only review metadata changed; all saved points, visibility and corrected blur
tags remain as reviewed. Implementation commit
`3928f7fee7f6e41eb3ffa05b0db062b176442e6e` adds versioned training-block composition
and a comparison against preserved prior adapted results. Seventeen focused
checks passed; no full suite was run. Independent code/config review passed.

The approved expanded fit completed once, without resume: 150 reviewed frames,
140 triplets, 400 sampled examples, 200 updates from the original pretrained
checkpoint. It took 24.3455 seconds and used 1.87 GiB peak allocated GPU memory.
All 213 BatchNorm buffers remained unchanged. Checkpoint SHA-256:
`09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`.
Outputs are under
`data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/`.

At the unchanged primary 0.5 setting, expanded WASB gives **120 matched / 2 wrong /
23 missing**, with zero alarms on five hidden frames. The prior fit gave 98 / 1 /
46. P001 improves from 11 to 34 matches; P002 loses only frame 48, while P003's
match/missing classifications are unchanged. Across all windows, 23 matches are
gained and one is lost. The two geometric errors are P001/52 at 10.368 pixels and
P003/164 at 10.972 pixels, still outside the unchanged ten-pixel radius. These
offsets do not by themselves establish wrong-object selections. Equal-output-count
RF gives 99 / 23 / 23; unrestricted RF gives 111 / 34 / 0 plus five hidden alarms.

The predeclared eight-setting cached comparison is also complete. At 0.3 the
expanded checkpoint gives **130 / 1 / 14**, with zero hidden alarms, retaining all
120 primary matches and adding ten. It corrects P001/52 and restores P002/48 on
these labels. Next: review the cached 0.3 candidate outputs before any additional
training or motion rule. No operating point or phase gate is promoted. The
primary results remain 0.5; candidate selection from inspected development data
does not establish independent generalization. Existing human reviews remain
complete; the new model outputs require their own visual review.

Six cached 0.3 candidate clips are ready under `review_threshold_0_3/`, with
`review_manifest.json` binding their receipts. Each is 25 frames at 5 fps and
decodes through its final frame. Rendering took 9.315 seconds, with no new model
inference, training or scoring. The results document links these six clips for
the next human review, while keeping all primary 0.5 videos separately preserved.

See [expanded results and review material](../ball_wasb_expanded_adaptation_results.md).
Training and evaluation audits reconciled actual saved states and report records.
Evaluation plus cached calibration took 32.714 seconds; primary review rendering
took 12.630 seconds. No old model was rerun and no holdout was released. The
approved single expanded fit is consumed and complete; do not restart it to resume.

## Earlier result: first pilot adaptation helped development localization

Ryan approved the concrete pilot-training plan. Implementation commit
`193319f984e5d150fbb86e9da2c5ec559540d61e` adds an isolated trainer, safely bound
adapted-checkpoint loader, paired evaluator and labeled review renderer. One
uninterrupted 200-update fit completed on the three reviewed pilots: 66 coordinate
targets, eight hidden negatives and one masked ambiguous frame. No development
evaluation frame entered training or checkpoint selection; holdouts stayed sealed.

At the predeclared 0.5 threshold, adapted WASB gives **98 matched / 1 wrong / 46
missing** eligible observations, with zero alarms on five hidden frames. Original
WASB gave 31 / 0 / 114. All 31 original matches remain, with 67 gained. Pool-wise
equal-output-count RF gives 90 / 9 / 46 and no hidden alarms. That comparison is
a post-hoc ranking diagnostic, not a deployable RF threshold. Against unrestricted
RF (111 / 34 / 0, five hidden alarms), adapted WASB recovers nine matches and loses
22 through abstention. This establishes useful development improvement, not
superiority at every coverage level or independent generalization.

The remaining missing frames concentrate in P001: all 25 representative frames
and 14 challenge frames, accounting for 39/46 missing. The sole geometric error
is P003/164 at 11.43 source pixels from the reviewed amodal center; it remains
wrong under the unchanged ten-pixel rule. Do not automatically equate that with
following a different object. Six synchronized adapted review videos cover all
25 frames and their endpoints. Ryan has now reviewed all six and authorized
continued work. His bleacher-ball and dark-uniform/referee-occlusion observations
are preserved in `configs/ball_tracking/reviews/wasb_basketball_adaptation_visual_review_v0_1.json`.
The two supplied screenshots show yellow RF detections while WASB reports missing;
do not treat them as WASB false detections. The original rendering receipts keep
their historical pending state; the new human record supplies completed review.

Training took 23.207 seconds, with 1.87 GiB peak allocated GPU memory. Evaluation
and eight cached thresholds completed in 32.705 seconds; rendering took 12.551
seconds without new inference. Twenty-one unique focused checks passed (nine
trainer, eight adapter, four evaluator); no full suite was run. Independent
training/result audits confirmed the saved weights, 200 updates, frozen BN
buffers, complete outputs, control parity and comparison records. All earlier
evidence and reviews remain intact.

Read [the adaptation results and review links](../ball_wasb_adaptation_results.md).
The final checkpoint is
`data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/training/checkpoint.pth`,
SHA-256 `98912a271791326bcfe2d2f468e94002d0986281f27ff1641c795177d1f94289`.
No production operating point or quality gate is promoted. The subsequent
[gap diagnosis](../ball_wasb_remaining_gap_diagnosis.md) reuses saved results:
all 39 P001 primary missing frames have a nearby raw candidate somewhere in the
existing threshold grid, but 28 are never selected correctly. A forced-peak
diagnostic is correct on only 2/25 P001 representative frames; most strongest
responses are elsewhere. Lowering thresholds or replacing component mass alone
does not resolve the main visual-discrimination weakness.

The [data expansion proposal](../ball_wasb_training_data_expansion.md) now names
75 new training-only frames: P001/100–124, P001/250–274 and P002/343–367. Source-only
previews are ready, and source bytes plus evaluation/holdout separation were
checked. The P002 addition intentionally continues the old training occlusion;
combining it yields five training blocks, 150 frames and 140 complete triplets.
Ryan approved this added labeling work and one original-initialized 200-update
fit after label review. The approval is recorded separately at
`configs/ball_tracking/reviews/wasb_training_data_expansion_approval_v0_1.json`;
the proposal's pending status is its historical preparation snapshot. Ryan has
completed all 75 new labels: 64 eligible centers (four fully visible and 60
partially visible) and 11 hidden frames. At his direction, eight `camera_motion`
tags became `motion_blur`; pre-correction snapshots and exact changes are recorded
in `configs/ball_tracking/reviews/wasb_training_expansion_tag_correction_v0_1.json`.
None of the old three pilots or six released development sets used that tag.
The combined training set has 130 eligible centers, 19 hidden frames and one
masked ambiguous frame. Ryan has since approved all three new label sets, as
recorded in the latest result above.
The [annotation guide](../ball_wasb_training_expansion_annotation_guide.md) links
three label-only clips, native overlays and zoom panels. Each clip decodes through
all 25 frames and its final frame; no predictions were used. Their completed
review and the subsequent expanded fit are recorded above. The six earlier
completed output reviews, full-possession finish line and player foundation
remain unchanged.

## Earlier snapshot: cached calibration, before the completed adaptation above

The eight-setting [calibration screen](../ball_wasb_calibration_results.md) reused
saved heatmaps without model inference, media reads or holdout access. Threshold
0.2 raises WASB matches from 31 to 62/145 with zero observed wrong/hidden outputs,
but leaves 83 eligible frames missing. Representative/challenge matches are
29/75 and 33/70. At equal pool output counts, RF gives 61 matches and one wrong
output; at threshold 0.1, WASB's 70 matches/five wrong outputs trail equal-count
RF's 72/three. The original zero-error 31-output count is also achievable by
selective RF ranking. This ranking comparison is post-hoc, not a deployable gate.

All six original 0.5 point/report comparisons and RF control comparisons agree;
nine focused tests passed. One cached-only invocation completed in 2.851 seconds.
Original evidence remains intact. No full suite, new training, visual acceptance
or method promotion occurred. Outputs are under
`data/outputs/ball_tracking/wasb/wasb_basketball_calibration_v0_1/`.

The [adaptation plan](../ball_wasb_adaptation_plan.md) specifies one 200-update
pretrained trial: train on the three reviewed pilots (66 coordinate targets,
eight hidden negatives, one ambiguous frame masked), then evaluate on the six
disjoint development windows. It is prepared, not executed. This same-game split
can test useful adaptation but cannot establish independent generalization.
The ball-phase finish line, reviewed player foundation and holdouts are unchanged.

## Latest implementation: 2026-10-08 WASB transfer comparison completed

The official WASB basketball checkpoint now loads safely in the existing GPU
environment through a small temporal point adapter. All six released development
windows completed inference, scoring and synchronized player/ball rendering at
source commit `96907dfdf77fd29474357c6ee7845c2be49fc9dc`. No training, holdout
access, native WASB tracker or interpolation was used. Inputs remain inside each
25-frame window; all frames receive aligned outputs, with fewer contributions at
the endpoints. Predictions, heatmaps, timing and review media are cached under
`data/outputs/ball_tracking/wasb/wasb_basketball_transfer_v0_1/`.

At the published strict heatmap threshold above 0.5 and the existing 10-source-
pixel match radius, WASB top-one matches 17/75 representative and 14/70 challenge
frames, compared with saved RF top-one 51/75 and 60/70. WASB makes zero wrong
selections and zero alarms on the five hidden frames, but leaves 114 eligible
frames missing. It recovers no match absent from RF top-one and loses 80. This
fixed setting is insufficient as a replacement. See
`../ball_wasb_transfer_results.md` for results, diagnostics and remaining choices.

The point evaluator agrees with all 60 declared saved-RF raw/top-one control
cells across the six windows. Twenty-nine focused tests passed; no full suite
was needed. Actual real-frame preprocessing also matched the official RGB,
affine and normalization path bit for bit on the checked triplet. All six videos
decode through their final frames; human visual acceptance remains pending.
The comparison is a completed development result, not a failed startup, a new
generalization claim, or ball-phase completion. Prior failures/reviews remain
unchanged, and the existing quality bar remains in force.

## Latest research: 2026-10-08 sports-video implementation review

Ryan requested an extensive external research effort before further implementation.
The durable collection begins at [the research hub](../research/README.md), with
[recommendations](../research/recommendations.md), detailed ball/player/geometry/
pipeline/analytics chapters and source ledgers. It separates author-reported
benchmarks, inspected implementations, unresolved artifact access/terms and local
results. No external model was installed, trained, run or promoted during this
research; no scientific comparison or full test suite was repeated.

The leading recommendation is a small adapter for WASB's linked basketball
temporal checkpoint, comparing its image evidence with saved RF controls under
our current label/evaluation semantics. Actual weight access, compatible loading,
frame/coordinate alignment and local benefit remain unresolved. Existing motion
graphs and player-context rules have already been tested; a new temporal image
representation is a materially different hypothesis. Preserve the reviewed player
foundation and use the broader references when measured failures justify them.

The research does not change the recovered negative corroboration result, failed
attempt history, consumed resources, completed reviews, holdouts or quality gates.
The next implementation should follow the practical October 8 operating policy:
fix routine issues, check real component boundaries proportionally, and deliver a
usable ball/player increment instead of another general release framework.

## Latest checkpoint: 2026-10-08 corroboration result recovered; practical workflow adopted

The tested RF/YOLO agreement rule worsens localization on all six development
windows. Representative matches fall from 51/75 to 41/75; challenge matches fall
from 60/70 to 37/70. It recovers no match and suppresses no wrong output or hidden
alarm. The five hidden alarms remain. See
`../ball_crop_cross_detector_corroboration_results.md` for the separate pools,
per-window counts, evidence, and limitations. This answers the corroboration
question; it does not finish the broader ball-tracking phase.

Attempt `dcdfd95a942c44f3bccb8d41fe8c795c` at `decfcbaf642bcff8d04496f8c1274a1c7a415811`
computed the results and rendered the reviews, then failed on an oversized
Markdown report. Its saved numerical summary passed internal consistency checks
and an independent comparison with all six window and two pool evaluations.
The failed status, 58.562999999994645 charged seconds, and existing outputs remain
preserved. No experimental recomputation or full-suite rerun was needed for recovery.
New human visual reviews have not occurred; no method or quality gate is promoted.

Ryan's current standing instructions in `../../AGENTS.md` and `working_agreement.md`
supersede older arbitrary caps, read bans, mandatory full-suite runs, routine
certificate procedures, and recovery-proposal requirements. Fix routine issues,
read needed development results, and check changes proportionally. Preserve honest
evidence and practical computer safety; bring substantial tradeoffs to Ryan.
Older checkpoints below are historical, including their now-superseded operational
approval boundaries. Next work should advance the usable ball-tracking baseline
and integration of completed increments, not rerun this rejected corroboration rule.

## Prior checkpoint: 2026-10-07 joint 16-frame diagnostic review complete

All 16 fixed frames now have separate Ryan and Codex observations for all three
methods. The completed diagnostic summary and receipt are
`data/outputs/t/error_type_review_b71c64d3fd46/summary.md` (7,208 bytes; SHA-256
`178e899526d686a635a45bb16ebc56dbdbed616bd2dc812fbbd5c05d6f0ed16a`) and
`completion.json` (13,226 bytes; SHA-256
`7996f3c2254649a8e10efaf7fc25ef2f1ceef51d5305b29654f244e1e809adf2`).
These selected cases distinguish other-object marks, on-ball center offsets and
absent predictions. At P003/164 Ryan places all marks on the ball but slightly
left despite their saved wrong-present status; identity and center-distance
criteria remain distinct. At 170 all methods select a foot; at 171 mean/top-one
are on the ball while TT still selects a foot. No method is promoted. Next is a
separately bounded follow-up proposal about object selection and withholding
predictions during occlusion, keeping center placement distinct. No execution or
Git mutation follows automatically from completion.

Ryan accepted the fixed 16-frame review and explicitly requested Codex's own visual
assessments alongside his. The exact request and amendment are recorded in
`configs/ball_tracking/reviews/rfdetr_medium_crop_error_type_review_approval_v0_1.json`
(SHA-256 `ea04de33574ecab244d063fc3f9262ac0d2ce73ed6c0e6318dbae4d51d38a65c`).
This approval supplements the frozen proposal/scope below; their original proposed
status is historical. AI semantic review is limited to the same 48 native overlays.

Record Codex and Ryan separately, sealing each AI batch before requesting new
human frame judgments. This is an unblinded diagnostic review by one human and
an AI assistant, not two humans or independent blinded annotation. Both can err;
preserve disagreements and uncertainty, with Ryan retaining final human review
authority. Prior clip comments, image labels and reference markings are already known.

Codex inspected all three methods at P001 challenge frames 204 and 210 and sealed
the provisional observations in the create-only ignored record
`data/outputs/t/error_type_review_b71c64d3fd46/submission_0001.json` (9,499 bytes;
SHA-256 `531acd9f54613e25fc59f0231b5a040491eba9256e176ae746813c8f677a8c84`).
Ryan's six panel observations for 204 and 210 are now recorded verbatim in
`submission_0002.json` in that same directory (13,769 bytes; SHA-256
`5f820a7f4168a13d1dbd758077d37ede564e9ac310b4e114a15e1e52e810cf66`).
His top/bottom rows map to 204/210 and left/middle/right to TT/mean/top-one.
He reports TT centered in both frames, the other predictions near but not touching
the ball at 204, and far across the court on a player's pants at 210. Preserve his
reported green on-ball markings separately from their reference-marker role in
mean/top-one images. No extra model prediction or confirmed candidate index is inferred.
The 204 non-ball target is unspecified by Ryan; 210 has a preserved pants-versus-
torso/jersey detail disagreement with AI. TT fine-centering remains uncertain in
the original AI record, whereas Ryan judges it centered. His visibility extent is
unspecified, not a contradiction of AI's partly-visible observation.

Codex then inspected and sealed all three methods at 211 and 215 in
`submission_0003.json` (9,761 bytes; SHA-256
`be5dfc0fc9c53484cad35e08f26bb4d04a3b92169051dc7d68cc5e54498e1266`).
Ryan's response for 211 and 215 is now saved verbatim in `submission_0004.json`
(10,933 bytes; SHA-256 `9de235aef38d174e3d34e2bba21ac5c37365a1e73faf3eb6b468974c280a2eee`).
He reports green markers centered on the ball for TT/top-one, no red marks, and a
centered crosshair with no prediction markers for mean. Same-as references remain
explicit. The crosshair does not create an identity or center judgment for absent
mean output. No explicit visibility category or candidate number was supplied;
those fields remain null. Human centering is more specific than AI uncertainty,
with no contradictory ball-identity or prediction-presence claim in this batch.

Codex inspected and sealed all three methods at 216 and 217 in
`submission_0005.json` (9,919 bytes; SHA-256
`fd40775a5cb47d8cad721e97213c1ebe11f8ed9124e8df587cae993cdf6abccd`).
Ryan's 216/217 observations are saved in `submission_0006.json` (12,933 bytes;
SHA-256 `4328de9931a8d0388a6cb8416d965b5e717410f6728020ea902982754d5c7dfb`).
He reports TT centered and mean/top-one off-ball in both frames. Preserve "about
6 feet" at 216 and farther-away at 217 as uncalibrated human descriptions, not
measured court or pixel distances. The off-ball targets, explicit visibility
category and candidate indices are unspecified; AI floor/line and clothing
descriptions are not promoted to human-confirmed object identities.

Codex inspected and sealed P001 challenge 219 and P003 challenge 163 in
`submission_0007.json` (9,981 bytes; SHA-256
`0b258c47c81f47ca5a1b887e66371bbace570f88835649323e01154614f7b018`).
Ryan's P001/219 and P003/163 response is recorded in `submission_0008.json`
(14,198 bytes; SHA-256 `24abe63109ff01debebf03df35089a56ac5fbd83a00d78e5c6eccdedc162924a`).
Five panels agreed on prediction presence and apparent ball identity. His initial
P001/219 mean no-marker report conflicted with the sealed AI red bench-marker
observation. Codex reopened only that bound native image to investigate this new
disagreement, not to repeat a completed checkpoint, and again observed red #1.
Ryan then confirmed seeing it and explained that it blended into the bench.
The exact question and reply are appended in `submission_0009.json` (3,407 bytes;
SHA-256 `ad6fb8e57c05952c064f97c2001fbdd771f5749bf1f3bcba9002f96078ac12d9`).
Presence is now confirmed, while the first response and original AI record remain
unchanged. This prompted clarification is not another independent/blinded review.
Ryan's approximate 15-foot description applies only to P001/219 top-one and remains
unmeasured. No new exact target-object identity or candidate index was assigned.

Codex sealed the next fixed pair, P003/164 and P003/165, in `submission_0010.json`
(11,037 bytes; SHA-256 `193c4610e2f22eb091c49f097074c3cf8cdcd7896d18989ceae8fe8ba1ee061a`).
Ryan's P003/164 and P003/165 observations are recorded in `submission_0011.json`
(14,585 bytes; SHA-256 `3bd99402eac57ddfa6205872ff343c61635cfb0dc2e48a714210ebcc1a3c61f7`).
For 164 he places all red predictions on the ball, a little left of center. This
qualitative offset is retained directly; no threshold-based displacement category
or human uncertainty is invented. Reported green on-ball marks remain reference
geometry. For 165 he explicitly says the referee hides the ball, identifies TT and
top-one marks on a player's shoe, and reports no mean mark or crosshair. The shoe
is more specific than the AI's white-patch observation. His approximate 10-foot
description is unmeasured; no hidden ball center or candidate index is inferred.

Codex sealed P003/166 and P003/167 in `submission_0012.json` (10,667 bytes; SHA-256
`d3b151abda0d16bbd2882165910435117f7cd0a0af278acdcfcaa1b9b4cb1bb3`).
Ryan's P003/166 and P003/167 response is saved in `submission_0013.json`
(13,593 bytes; SHA-256 `3d45593a324160cd28f7716067e17e299bdcedd9048e890c569f522daecd842e`).
He identifies the baseline official for 166 TT/top-one and 167 TT, no prediction
for 166 mean, and a player near the free-throw line for 167 mean/top-one. His
approximate 30-foot and 10-foot descriptions remain uncalibrated; inherited
same-as descriptions are explicit. Exact anatomy is unspecified by Ryan. No
crosshair is reported, but visibility for 166/167 remains null in his record;
the explicit hidden statement for 165 is not silently carried forward.

Codex sealed P003/168 and P003/169 in `submission_0014.json` (10,525 bytes; SHA-256
`77223aa2565a6297d39ea55b6ae8d1d8e95ed320b5ed33a6e2b6716d65b78ca8`).
Ryan's P003/168 and P003/169 response is saved verbatim in `submission_0015.json`
(14,549 bytes; SHA-256 `b1b32709bc160dbf76589ea1e29c57257b7d83ba23ad5bfcb62096e5bba8c499`).
He identifies player-leg targets for all three methods at 168, absent TT output
at 169, and a bench person's head for mean/top-one at 169. The person's role as
coach is his description, not a verified identity. His 10-foot and 35-to-40-foot
estimates remain unmeasured. Both frames are described as covered; the original
169 word "red" is preserved. Ryan confirmed he meant the referee in appended
`submission_0016.json` (3,548 bytes; SHA-256
`46b8c6c56856c0e8a159cd35fe0ecbd10be76947ded305430d59af29e5237e42`).
The clarification applies to all three views and is not another independent review.

Codex sealed the final pair, P003/170 and P003/171, in `submission_0017.json`
(11,426 bytes; SHA-256 `de6b0eea96dda3c44ce3b729a0e2a12ae46ca56d6453832c1ca0efc5e07eb516`).
An appended administrative correction, `submission_0018.json` (2,560 bytes;
SHA-256 `2d270f6750a0e9fc0f18c72b7862a6779fd064a825f92448e6635efe76de2c11`),
removes unsupported inspection chronology and clarifies screen-right versus
anatomical foot side. It adds no image access or changed target judgment.
Ryan's final P003/170 and P003/171 response is preserved in `submission_0019.json`
(15,300 bytes; SHA-256 `7b9b8044f0fa67e78cc77dcf7103bfa9a6057c42acae8a7b0b1e193a3cca9758`).
He reports foot targets at 170 for all methods and at 171 for TT, with centered
reference crosshairs. His approximate 25-foot distance remains unmeasured. In
`submission_0020.json` (10,160 bytes; SHA-256
`72d586c67f0629251c16fafedbec00a3d4ed5810c142eb665d1025bd4daa2efa`), he confirms
"right marker" meant red and confirms green on-ball predictions in 171 mean/top-one.
No red marker is not treated as no prediction. Human on-ball confirmation and
AI centering remain separately attributed. "White player" does not establish race
or uniform color, so no confirmed clothing disagreement is inferred. Human explicit
visibility categories remain unspecified in this batch; AI uncertainty at 170 stays.

Coverage is AI 16/16 and human 16/16, with three method records each per frame.
Twenty submissions plus summary/completion total 232,784 bytes; individual limits
and exact frozen frame/media/state bindings passed administrative consistency
checks. Prior submissions, frozen scope, proposal and approval remain unchanged.
The earlier presence disagreement is resolved by appended clarification; other
uncertainty and the pants-versus-jersey detail remain preserved. No question remains
pending. Review is complete; no method or quality gate is selected.

The original submission count, individual-size and 1 MiB aggregate bounds include
both reviewers. No scientific bodies or original-source images were opened, media
hashed, images derived, annotations changed, tests repeated or new scientific
attempts consumed. All prior evidence, budgets, embargoes and holdouts remain intact.
The proposal, scope, approval and three context records remain unstaged at
`b71c64d3fd46bb27072efa8644e90c1c222bb65c`, with an empty index. This review approval
does not add Git or scientific-execution authority. Any next algorithm or experiment
still requires a separately bounded proposal.

## Prior checkpoint: 2026-10-06 fixed error-type review proposed; no new execution

Ryan's "Ok move forward" authorized the next bounded proposal. It is now
`../ball_crop_error_type_review_proposal.md`, with exact metadata scope
`configs/ball_tracking/proposals/rfdetr_medium_crop_error_type_review_v0_1.json`.
The proposal asks whether remaining errors are wrong-object marks, displaced
ball-center marks or absent outputs, and what happens at hidden-interval boundaries.
It uses existing images instead of another scoring intervention.

The fixed scope is 16 frames: P001 challenge 204, 210, 211, 215, 216, 217, 219
(all TT-matched to mean-wrong/missing transitions in the unique worst net-match-loss
window), plus P003 challenge 163-171 (the entire saved hidden run 165-169 and two
adjacent frames on each side). Exactly 48 existing worker-verified native overlays,
one per arm/frame, are bound by copied receipt hashes and filesystem metadata;
their aggregate existing size is 143,320,299 bytes. No pixels were opened in planning.

This would be a new, unblinded frame-specific diagnostic review, not an accuracy
study or a repeat of the six whole clips or eight completed identity reviews.
Ryan would report ball visibility, object identity of each present marker and
center alignment when identifiable. Missing outputs receive no invented identity;
uncertain/skipped observations remain explicit. The prior P003 300-324 impression
discrepancy remains unresolved, and the referee passage is not assigned a precise
frame range merely from its proximity to the saved hidden interval.

The proposal permits zero new scientific attempts, charged seconds, model calls,
selectors, scoring, rendering, tests, release checkpoints or application-code changes.
The existing post-success exception covers presentation of these verified images;
acceptance is for the new diagnostic scope, with no additional per-image permission.
Original images and scientific JSON stay closed; parent media hashes are forbidden.
New create-only human submissions/completion records would stay under the proposed
ignored `data/outputs/t/error_type_review_b71c64d3fd46/` directory, at most 1 MiB total.
No new judgments have been collected and that output directory has not been created.

Independent design and boundary reviews passed. Preparation used source,
administrative records and metadata only. No old validation, scientific attempt,
render or visual review was repeated. The history remains 3,330 events / 63 closed
attempts, with `10852.476000000015` cumulative seconds remaining; all prior evidence,
nine embargoes and three sealed holdouts stay unchanged. No method or quality gate
is selected. Next is accepting this 16-frame diagnostic scope; any later algorithm
change or scientific execution needs a separate proposal.

The intended five-file preparation is the proposal, scope and these three context
records. They remain unstaged with an empty index at
`b71c64d3fd46bb27072efa8644e90c1c222bb65c` on `codex/ball-detector-baseline`.
No Git mutation is authorized or performed for this new proposal.

## Prior checkpoint: 2026-10-06 Ryan submitted all six mean-confidence clip reviews

Ryan supplied six qualitative responses to the request to review the new clips
through their final frames. All six clip responses are recorded. A separate
explicit final-frame attestation, exact error frames and candidate indices were
not supplied and are not invented. These observations do not replace the fixed
raw10 results or approve a production quality gate.

The panel map is top-left unmarked source, top-right saved TT, bottom-left new
mean and bottom-right saved top-one. The repeatedly noted lack of top-left
markers is the intended source-reference design, not a rendering failure.

| Clip | Ryan's qualitative observations |
| --- | --- |
| P001 representative 50-74 | All three marked panels looked pretty good; no specific miss identified. |
| P001 challenge 200-224 | Saved TT looked amazing; bottom panels had a couple of misses. "Both two" is interpreted as the bottom pair; "although very scarce" is preserved without inferring a rate. |
| P002 representative 250-274 | All three marked panels looked great; Ryan saw no markers miss the ball. This frame range follows the six-clip reply order because the bullet omitted it. |
| P002 challenge 25-49 | All three marked panels looked great; no specific miss identified. |
| P003 representative 300-324 | Saved TT had a couple of incorrect markers close to the ball; top-one had a couple on a player's hand, with its other markers hitting the ball. Mean looked amazing. |
| P003 challenge 150-174 | All three marked panels missed around the referee passage. Mean and top-one kept the center better before that passage than saved TT. |

Verbatim wording, panel mapping, interpretation caveats and null exact-frame/
candidate fields are preserved in the create-only administrative ledger
`data/outputs/t/mean_impl_10e5fcb90f51/human_review_0001.json`, SHA-256
`3fcc37bc7969e99cc294c6a3bd3b56d4d3322e4baec309bac8a22f1494cd8589`.
`human_review_receipt_0001.json` binds the six submitted responses (SHA-256
`47faf088a3057903d3f8888f9a2b82f8fa7172a6a51543b1100f64d7bbc9e6b9`).
Clip/index metadata still matches the successful worker receipt. The original
636 bound artifacts, eight earlier human judgments and old handoff are unchanged.

The quantitative interpretation remains mixed: human impressions neither erase
the P001 regressions nor turn general praise into per-frame localization passes.
They describe different strengths by clip and remaining referee-passage misses.
New identities cannot be assigned to exact frame/candidate pairs from this reply.
No method or operating point is selected. No tests, experiments, media reads or
scientific-body hashes were repeated for recording these reviews. The scientific
journal remains 3,330 events / 63 closed attempts (59 successes, four historical
failures), with `10852.476000000015` seconds remaining; holdouts and embargoes
remain unchanged. Remaining time is not execution authority.

Next is a separately bounded follow-up proposal using this evidence. Any new
scientific access, tuning, execution or holdout release requires its own approved
scope. Do not repeat the six submitted reviews merely to resume. The earlier
handoff and pending-review checkpoint below describe the state before this reply.

## Prior checkpoint: 2026-10-06 mean-confidence comparison executed; six new reviews pending

The 15-file implementation was committed under Ryan's conditional authorization
at `06d3bb96ebb2659005716b7390f40f64e563e44b` on `codex/ball-detector-baseline`.
The clean descendant, exact implementation certificate and new create-only
release checkpoint passed. The single approved worker then completed successfully;
its verified bounded return classified the development result as **mixed**.

Validation remains **55 focused passes** and **1,103 full passes plus one existing
Windows skip**. No tests or prior experiments were repeated for execution. The
worker read only the 176 declared inputs, froze all six new selections before
scoring/rendering, copied the saved controls without rerunning them, and verified
all 636 artifacts (1,457,619,447 published bytes). There were zero new model calls.
Parent scientific JSON bodies remain opaque; only administrative/metadata records
and the bounded return were read. The approved post-success presentation exception
was used to inspect the layout of two new verified composites, without media
hashing, original-image access or human identity judgments.

Pool results at the fixed .01/raw10 operating point are below. Counts are
matched / wrong-present / missing on eligible frames; hidden alarms are separate.

| Pool | Saved TT | New mean | Saved top-one | Hidden alarms TT / mean / top-one |
| --- | --- | --- | --- | --- |
| Representative (75 eligible) | 32 / 39 / 4 | 49 / 24 / 2 | 51 / 24 / 0 | no hidden frames |
| Challenge (70 eligible, 5 hidden) | 53 / 14 / 3 | 57 / 9 / 4 | 60 / 10 / 0 | 4 / 3 / 5 |

The conservative favorable criterion did not pass: challenge missingness increased.
Pool gains also conceal important window regressions, particularly P001.

| Window | Saved TT matched / wrong / missing | New mean | Saved top-one |
| --- | --- | --- | --- |
| P001 representative 50-74 | 11 / 14 / 0 | 9 / 16 / 0 | 8 / 17 / 0 |
| P001 challenge 200-224 | 25 / 0 / 0 | 18 / 5 / 2 | 20 / 5 / 0 |
| P002 representative 250-274 | 8 / 17 / 0 | 18 / 6 / 1 | 20 / 5 / 0 |
| P002 challenge 25-49 | 16 / 7 / 2 | 22 / 2 / 1 | 23 / 2 / 0 |
| P003 representative 300-324 | 13 / 8 / 4 | 22 / 2 / 1 | 23 / 2 / 0 |
| P003 challenge 150-174 | 12 / 7 / 1 | 17 / 2 / 1 | 17 / 3 / 0 |

All window regressions against both controls and exact paired transitions remain
in the bounded administrative return. New-mean singleton emissions per window
in the order above are 16, 16, 19, 24, 22 and 21; current/older/empty endpoint
counts are 25/0/0, 23/2/0, 24/1/0, 24/1/0, 24/1/0 and 22/3/0. The new rule still
trails saved top-one in matched frames in both pools, so these results do not
establish added value from history. Localization does not certify object identity.

Frame 300 stayed candidate 0 at startup; frame 304 also stayed candidate 0.
The other six fixed diagnostic frames (301, 302, 308, 319, 320, 324) switched to
candidate 0, matching the saved top-one choice. Their new semantic identities
remain unknown. The eight prior human judgments apply only to the originally
reviewed saved-TT emissions; null human candidate indices remain null.

Attempt `b36133afc62a4c9fb34547ab6ad2c4ac` consumed 98.719 charged seconds of
its 1,200-second ceiling. Supervisor wall time before publication was 99.516
seconds; full command wall time was 144.468 seconds. Maximum completed safety
interval was 0.282 seconds; all memory/output/disk/cleanup checks passed.
The journal now has **3,330 events, 63 closed attempts, 59 successes and the same
four historical failures**. Consumed cumulative time is `3547.523999999985`
seconds; remaining time is `10852.476000000015`. The new attempt is consumed and
cannot retry. Nine embargoes, three sealed holdouts and prior outputs stay intact.

Administrative evidence lives in `data/outputs/t/mean_impl_10e5fcb90f51/`:
`study_stdout.json` is the allowed bounded parent return;
`path_confidence_mean_completion_06d3bb96ebb2.json` records completion and balances
(SHA-256 `0a83fbcd35079b57738ce32c05c8d31d5c979b8384d84c17a60d20eabc4e2071`).
Journal tip is `4dd2b89f3fea67f3be9e3f409e7b937fc6da8a2a622c9b2a98505041c2a31fd6`.
The release checkpoint binds the execution commit, not a later documentation HEAD.

Next is Ryan's review of **all six new 25-frame clips through their final frames**,
at 5 fps, under the retention root's `audit/path_confidence_mean_v0_1/review/`.
Each window has `comparison.mp4`, `first.png`, `last.png` and native overlays.
No new human review has been completed. No method, operating point or production
quality gate is selected. New execution, tuning, retries and holdout release need
separate bounded approval. Push, PR creation and merge remain unauthorized.

## Prior checkpoint: 2026-10-06 mean-confidence implementation validated for the approved commit

Ryan approved the exact proposal and added: "yes I do an you are approved to stage
and commit if nothing is broken after". The separate immutable approval record is
`configs/ball_tracking/reviews/rfdetr_medium_crop_path_confidence_mean_approval_v0_1.json`.
It authorizes implementation, artificial validation, one conditional scientific
attempt and the six new review packages, plus staging/committing after passing
checks. Push, PR creation and merge remain outside this authorization. The frozen
proposal/scope retain their original planning status; the new approval supplies
authority without rewriting them.

Four separate modules and four artificial test files implement the fixed mean
arm, saved-control comparison, synchronized rendering and guarded execution.
Historical selectors, evaluator semantics and the responsive monitor are unchanged.
All six selections freeze before labels, saved reports or pixels are accessible.
Independent numerical, access-boundary and returned-report reviews passed after
adding report consistency checks. The corrected focused suite passed **55 tests**.
The full suite passed **1,103 tests plus the one existing Windows skip** (1,104
total), with no errors or failures. No scientific attempt has started.

Administrative evidence is in `data/outputs/t/mean_impl_10e5fcb90f51/`.
`focused_01` passed 54 tests; `full_01` was deliberately interrupted after
35.375 supervised seconds to incorporate the final review findings, before any
source edits. Its failed/interrupted receipt and verified owned cleanup remain
preserved with `correction_01.json`. `focused_02` passed 55 tests. All correction
time counts toward the original 4,200-second artificial validation allowance.
Accepted `full_02` used 2,123.766 supervised seconds (2,121.558 unittest seconds).
Total artificial time including the interruption and both focused runs is
2,164.297 seconds. Exact 177-file source bindings stayed unchanged; cleanup and
resource bounds passed. The create-only implementation certificate SHA-256 is
`51384f02cf27f56bd5bfb0b2281fcc62cecd30c2726f528c9671fccb2fc92093`.
The manifest now binds that certificate; the release checkpoint is still absent.

The new preservation snapshot binds the exact 3,221-event prefix, 62 closed
attempts, 58 successes, four historical failures, all eight human judgments,
nine embargoes and three sealed holdouts. Parent scientific bodies/pixels have
not been opened. The existing cumulative scientific balance remains
10951.195000000016 seconds. The one new unit retains its 1,200-second/4-GiB
ceilings and cannot retry automatically.

Next: stage and commit the exact 15-file scope under Ryan's permission, verify a clean
descendant commit and create the new release checkpoint, then execute once.
After a successful bounded return, present the six new clips through their final
frames for Ryan's judgment. No method, operating point or quality gate is selected.
Implementation was prepared from `10e5fcb90f51909891d5df08d0b84ea5932a4033` on
`codex/ball-detector-baseline`; the new checkpoint must bind its clean descendant.
Nothing has been pushed.

## Prior preparation: 2026-10-06 mean-confidence comparison proposed

Ryan's latest "move forward chat" authorized the next bounded proposal only.
The proposal is `../ball_crop_path_confidence_mean_proposal.md`, with scope
`configs/ball_tracking/proposals/rfdetr_medium_crop_path_confidence_mean_v0_1.json`.
It asks whether averaging path confidence instead of summing it improves
current-frame localization or changes the wrong-output/missingness tradeoff.
It proposes one new TT/cap20/.01 arm across all six existing development windows,
using saved TT and top-one controls without rerunning their selection/scoring.

The proposed fixed-terminal-length algorithm preserves movement/gap rules and
defines binary64 arithmetic and tie behavior. Normalization also increases the
relative influence of the unchanged penalties; it is not a proven history-only
fix. All 150 frames are evaluated at raw10, with representative/challenge pools
separate, paired match/wrong/missing transitions, hidden alarms and six new
final-frame review packages. Frame 300 must remain unchanged at startup; all
eight completed human judgments and their null candidate indices are preserved.

The proposed worker-only allowance binds 176 existing candidate/control/label/
pool/PNG files, totaling 558,727,833 bytes from filesystem metadata. All six new
selections must be frozen before labels, saved scoring reports or pixels are
opened. Parent scientific bodies remain opaque; the proposal requests only a
later exception to present the new verified review media to Ryan. No such new
access is authorized yet. One distinct attempt would have a 1,200-second ceiling
and 4 GiB of new output under the unchanged responsive safety policy. The
remaining 10951.195000000016 seconds does not itself authorize this attempt.

Preparation read source, committed metadata and administrative records, and
checked scientific path sizes only. No scientific body/hash/pixel access, tests,
experiments or completed review repetitions occurred. Existing validation stays
at 55 focused passes and 1,048 full passes plus one existing Windows skip.
Independent numerical-design and access-boundary reviews passed after clarifying
window-regression disclosure and temporal-run definitions. JSON inventory/binding
and document whitespace checks passed; these are proposal checks, not code tests.
Preserve all 3,221 events, 62 closed attempts, 58 successes, four failures, the
successful contrast suffix, nine embargoes and three sealed holdouts.

Next is approval of the exact proposal for implementation, artificial validation
and one conditional execution/new review scope. Staging and committing still
require separate permission before a clean release checkpoint. No production
method, operating point or quality gate is selected. The five intended files
are the new proposal/scope and these three context records; they are unstaged,
with an empty index. HEAD remains `10e5fcb90f51909891d5df08d0b84ea5932a4033`
on `codex/ball-detector-baseline`. No Git step has been performed.

## Prior checkpoint: 2026-10-06 saved-decision contrast completed successfully

The eleven-file implementation was staged and committed under Ryan's explicit
conditional permission at `26242d13a5a93043d35fa832c348a44445c1759e` on
`codex/ball-detector-baseline`. The clean descendant commit and its release
checkpoint were verified, then the single authorized comparison succeeded.
Validation remains **55 focused passes** and **1,048 full-suite passes plus the
one existing Windows skip**; no tests were repeated for this execution.

Only the owned worker read and hashed the two fixed saved scientific inputs.
The parent inspected the verified bounded return and administrative records;
no scientific input/output body or pixel was reopened. No inference, selector,
evaluator, rendering, tuning or new human review ran. Existing human judgments,
null human indices and original raw-10 localization outcomes are unchanged.

For the fixed saved winner–comparison pairs in frames 301, 302, 308, 319,
320 and 324, the emitted endpoint had lower current confidence, but its larger
saved past-confidence contribution outweighed that disadvantage and the combined
gap/motion differences. Frame 300 was confidence-only. In frame 304, higher
current confidence and a smaller motion penalty outweighed lower past confidence.
There were no exact score ties. These are descriptive saved-score arithmetic,
not a controlled causal finding or overall performance estimate. The comparator
remains the saved highest-confidence raw-10-qualified retained endpoint; its
visual identity, nearest-point status and best-compatible-objective status are
not established. The saved global margin remains distinct from this pair gap.

The new attempt `9b7ad2e59c67420ea70e0a2be8b7767d` is consumed: **42.078
charged seconds of 120**, 42.625 supervisor wall seconds and
85.313 command wall seconds. The journal now has **3,221 events,
62 closed attempts, 58 successes and four preserved historical failures**.
Remaining cumulative time is `10951.195000000016` seconds; this balance does
not authorize another attempt. All prior diagnostic/recovery/verification roles
remain consumed. No automatic retry is authorized. Nine prediction embargoes
and three sealed holdouts remain intact.

The ignored outputs are `contrast.json`, `summary.md` and `provenance.json`
under `data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit/post_review_saved_decision_contrast_v0_1/`.
The administrative completion is
`data/outputs/t/sdc_impl_7a2e660a3887/saved_decision_contrast_completion_26242d13a5a9.json`;
its verified bounded transport is
`data/outputs/t/sdc_impl_7a2e660a3887/saved_decision_contrast_execution_26242d13a5a9_stdout.json`.
Use those administrative bindings for resumption; do not open the scientific
artifact bodies merely to recover context.

Next is a separately scoped decision about a possible follow-up to the saved
history contribution. Any change to selection/scoring or new experiment needs
a concrete proposal and approval; this diagnostic grants neither. Do not rerun
the consumed comparison, the completed tests, or the eight visual reviews for
resumption. Nothing was pushed. These three completion-context documents are
the only follow-up changes and are covered by the existing associated-documentation
stage/commit permission; verify Git for the later documentation commit.

## Prior checkpoint: 2026-10-06 saved-decision contrast validated; approved commit is next

Ryan explicitly approved the exact saved-decision contrast proposal and added:
"Yes you may, and you also have my permission to stage and commit if nothing is broken after you implement this".
The separate approval record authorizes implementation, artificial validation,
one conditional execution, and staging/committing the passing scope. No further
permission is needed for those approved steps; pushing, PR creation and merging
remain unauthorized.

The new runner and pure formatter are validated with **55 focused passes** and
**1,048 full-suite passes plus the one existing Windows directory-symlink skip**
(1,049 total; no failures or errors). Independent implementation/helper reviews
passed. The certificate in `data/outputs/t/sdc_impl_7a2e660a3887/` binds all 169
source/test/requirements files, unchanged authority and validation evidence.
The original selector, evaluator, monitor and prior tests remain unchanged.


Next stage and commit the exact eleven intended files after reporting branch,
HEAD, status and scope. Then verify the clean descendant commit, create its
release checkpoint and dispatch the one authorized 120-second comparison.
The index is empty; this pre-commit checkpoint remains on
`codex/ball-detector-baseline` at `7a2e660a38877e2000fa997e675c86b97d55e9ac`.
The release checkpoint and new comparison outputs are absent.

The fresh preservation snapshot includes all nine human administrative records,
the sixteen prior image metadata rows, the two declared input metadata rows,
the 3,172-event/61-attempt prefix, nine embargoes and three sealed holdouts.
All old attempts remain consumed; the new role is unspent and the cumulative
balance is `10993.273000000017` seconds. Implementation and validation opened
no real scientific bodies or pixels and repeated no completed human review.
Only the future owned worker may read the two exact saved inputs. It will
return the fixed eight comparisons with unchanged judgments and null indices.

## Prior checkpoint: 2026-10-06 saved-decision contrast proposed; approval is next

Ryan's "move forward chat" authorized planning only. The concrete proposal is
`../ball_crop_saved_decision_contrast_proposal.md`, with companion scope
`configs/ball_tracking/proposals/rfdetr_medium_crop_saved_decision_contrast_v0_1.json`.
For the same eight TT/cap20 frames, it would compare the emitted winner's saved
score/path with one saved highest-confidence top-twenty candidate satisfying
the raw 10-pixel rule. Saved S membership already establishes retained
availability; neither that question nor the completed visual review is repeated.

The proposed worker would read exactly the original motion representative pool
(22,583,132 bytes) and TT observations (5,522,898 bytes), totaling 28,106,030 bytes.
Sizes came from metadata; expected hashes came from committed metadata. It
would report signed current-confidence, past-confidence, gap and motion
contributions and differences from saved values, keeping the pair gap separate
from the saved global margin. Frame 300 has no history contribution. These
comparisons support no global causal conclusion or new semantic identity.

The proposed distinct unit permits one attempt of at most 120 charged seconds,
bounded by the remaining `10993.273000000017` seconds. All old attempts remain
consumed; the 3,172-event prefix, completed human review, original localization
outcomes, nine embargoes and three holdouts remain preserved. Preparation read
or hashed no scientific bodies and accessed no pixels; no tests, experiments
or Git mutations ran. Independent source/document review of the proposal passed;
this is not code validation or a test run.

Next is explicit approval of the exact proposal for implementation, artificial
focused/full validation, independent review and one conditional execution.
Execution still requires separately approved staging and committing, a verified
clean commit, and its release checkpoint. The intended dirty scope is five files:
three context documents plus the new proposal and scope. The index is empty;
HEAD remains `7a2e660a38877e2000fa997e675c86b97d55e9ac` on
`codex/ball-detector-baseline`. Nothing is staged, committed or pushed by this planning.

## Prior checkpoint: 2026-10-06 all eight candidate-identity judgments complete

Ryan's exact response for frame 324 was: "ok this one is the furthest from the ball of all 8 frames. This one is on the white player in the left corner, very far from the ball".
The final `human_review_0008.json` records `another_object`, center
`not_applicable`, and candidate index null. The left-corner-player description
and furthest-of-eight comparison are Ryan's qualitative judgments; no numerical
distance or player identity is inferred. The administrative completion record is
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/review/candidate_identity_review_v0_1/human_review_completion_v0_1.json`.
Administrative checks confirmed the eight-record chain, one new answer per
record, preserved other rows/image bindings/raw outcomes, and unchanged
verification-artifact metadata and resource-journal event count and tip.

All eight frames are reviewed, with none pending or uncertain: seven
`another_object` judgments and one `ball` judgment. Frames 300, 301, 302, 304
and 308 were hands; frame 320 was the dribbling player; frame 324 was the
left-corner player. Frame 319 was ball with `clearly_displaced` center at its
outer edge. These selected, correlated failures do not establish overall rates,
method rankings or causal proof. The original 10-pixel outcomes remain unchanged.

Next is a separately bounded follow-up proposal using these human observations;
no additional experiment or visual review is authorized. Resource journals,
consumed attempts, budgets, existing tests, nine embargoes and three sealed
holdouts are unchanged. HEAD remains `7a2e660a38877e2000fa997e675c86b97d55e9ac`;
the three context documents remain unstaged with an empty index. Staging and
committing still require separate approval. No scientific input/image access,
test rerun or Git mutation accompanied these notes.

## Prior checkpoint: 2026-10-06 frame 320 judgment recorded; frame 324 is next

Ryan's exact response for frame 320 was: "ok this one is off the ball but it is not nearly as far as frames 1-5. This one landed on the player who is actively dribbling the ball".
The immutable administrative `human_review_0007.json` records `another_object`,
center `not_applicable`, and candidate index null. Ryan identified the dribbling
player, without specifying a body part or candidate number. His comparison with
the first five reviewed examples remains qualitative; no distance, cause or
matchup identity is inferred. Record `0006` and all other rows are preserved.

Seven of eight frames are reviewed: five hand cases, frame 319 ball/off-center,
and frame 320 the dribbling player. Only frame 324 remains pending; present its
unmarked source first, then its verified native overlay. Original outcomes,
budgets, test evidence and Git boundaries are unchanged. Recording this response
required no scientific input or image access, experiment/test rerun or Git
mutation. The three context documents remain unstaged with an empty index.

## Prior checkpoint: 2026-10-06 frame 319 judgment recorded; frame 320 is next

Ryan's exact response for frame 319 was: "so this one is on the ball, but it is on the outer edge of the ball and not in the center".
The immutable administrative `human_review_0006.json` records identity `ball`,
center `clearly_displaced`, and candidate index null because no number was
supplied. The marked point's outer-edge placement is a qualitative judgment;
no numerical displacement or causal explanation is inferred. Record `0005`
and all other rows are preserved.

Six of eight frames are reviewed: the first five were another object (player's
hand); frame 319 is ball with an off-center mark. Frames 320 and 324 remain
pending. Present frame 320's unmarked source first, then its verified native overlay.
Original 10-pixel outcomes, budgets, test evidence and Git boundaries are
unchanged. Recording this response required no scientific input or image
access, experiment/test rerun or Git mutation. The three context documents
remain unstaged with an empty index.

## Prior checkpoint: 2026-10-06 frame 308 judgment recorded; frame 319 is next

Ryan's exact response for frame 308 was: "same thing with this one, it is only a players hand".
The immutable administrative `human_review_0005.json` records `another_object`
(player's hand), center `not_applicable`, and candidate index null because no
number was supplied. Record `0004` and all other rows are preserved.

Five of eight frames are reviewed; 319, 320 and 324 remain pending.
Present frame 319's unmarked source first, then its verified native overlay.
Budgets, localization outcomes, test evidence and Git boundaries are unchanged.
Recording this response required no scientific input or image access,
experiment/test rerun or Git mutation. The three context documents remain
unstaged with an empty index.

## Prior checkpoint: 2026-10-06 frame 304 judgment recorded; frame 308 is next

Ryan's exact response for frame 304 was: "same thing with this one, it is on a black players hand".
The immutable administrative `human_review_0004.json` records `another_object`
(player's hand), center `not_applicable`, and candidate index null because no
number was supplied. Record `0003` and all other rows are preserved.

Four of eight frames are reviewed; 308, 319, 320 and 324 remain pending.
Present frame 308's unmarked source first, then its verified native overlay.
Budgets, localization outcomes, test evidence and Git boundaries are unchanged.
Recording this response required no scientific input or image access,
experiment/test rerun or Git mutation. The three context documents remain
unstaged with an empty index.

## Prior checkpoint: 2026-10-06 frame 302 judgment recorded; frame 304 is next

Ryan's exact response for frame 302 was: "same thing with this one, it is on a black players hand".
The immutable `human_review_0003.json` records `another_object` (player's hand),
center `not_applicable`, and candidate index null because no number was supplied.
Record `0002` and all other rows are preserved.

Three of eight frames are reviewed; 304, 308, 319, 320 and 324 remain pending.
Present frame 304's unmarked source first, then its verified native overlay.
Budgets, localization outcomes, test evidence and Git boundaries are unchanged.
The new administrative ledger preserves all earlier records. No scientific
input or image was opened/hashed; no experiment, test or Git mutation occurred.
The three documents remain unstaged with an empty index.

## Prior checkpoint: 2026-10-06 frame 301 judgment recorded; frame 302 is next

Ryan's exact response for frame 301 was: "same thing with this one, the candidate is on a black players hand".
The new immutable `human_review_0002.json` in the candidate-identity review
directory records `another_object` (player's hand), center `not_applicable`,
and candidate index null. Ryan did not state a number for this frame;
frame 300's index 0 is not inherited. Record `0001` and all other rows are preserved.

Two of eight frames are reviewed; 302, 304, 308, 319, 320 and 324 remain pending.
Present frame 302's unmarked source first, then its verified native overlay.
Budgets, original localization outcomes, test evidence and Git boundaries are
unchanged. No scientific artifact or pixel inspection, experiment, test or Git
mutation accompanied these notes. The three context documents remain unstaged
with an empty index.

## Prior checkpoint: 2026-10-06 frame 300 judgment recorded; frame 301 is next

Ryan's exact response for frame 300 was: "That candidate landed on a black
players hand, not very close to the ball". The new immutable administrative
ledger is `data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/review/candidate_identity_review_v0_1/human_review_0001.json`.
It records `another_object`, center `not_applicable`, and candidate index 0
from the preceding marker clarification. Ryan supplied the identity judgment;
the numeral was not separately restated in his answer. No distance was derived.

One frame is reviewed; 301, 302, 304, 308, 319, 320 and 324 remain pending.
Present frame 301's unmarked source first, then its verified native overlay.
The original pending ledger, verification artifacts and localization outcomes
remain unchanged. No image bodies were opened/hashed to record this response,
and no experiment or test was repeated. Budgets and Git boundaries below remain
unchanged. The three context documents remain unstaged with an empty index.

## Prior checkpoint: 2026-10-06 image-byte verification complete; human review is next

Ryan separately approved staging and committing the exact nine validated files.
Commit `7a2e660a38877e2000fa997e675c86b97d55e9ac` on
`codex/ball-detector-baseline` was verified clean before the already conditional
verification ran. Its parent is `efeefd58f6801ffe5de106a48f8dad1e835b9647`.
Nothing was pushed.

The one approved attempt, `89268748193e45b4a598af6bd4747f05`, succeeded.
Its owned worker verified only the sixteen declared PNG byte bindings and
created verification, pending-review, guide and provenance outputs. No pixels
were decoded or inspected by the parent; no inference, scoring, selection or
semantic labels were produced. All eight frames remain pending with zero human
answers: 300, 301, 302, 304, 308, 319, 320 and 324 in P003 representative TT/cap20.
The administrative completion record is
`data/outputs/t/ci_impl_efeefd58f680/identity_review_completion_7a2e660a3887.json`;
it binds the verified summary transport without requiring scientific-body reads.

The attempt used 43.938 charged seconds of 120; supervisor wall time was
44.750 seconds and complete command wall time was 86.094 seconds. Cleanup and
final accounting passed with no resource overshoot. The preserved 3,121-event
prefix is now part of a 3,172-event journal with 61 closed attempts: 57 successes
and the same four historical failures. Its tip is
`10ce622caf54c06526fa2b0b259889157711adeb35d4185d793e74cf845dad13`.
Cumulative allowance remaining is `10993.273000000017` seconds. This attempt,
the output-presence attempt and prior recovery are consumed, with zero
authorized attempts remaining. Unused arithmetic time grants no retry.

Next is Ryan's already approved human judgment, beginning with frame 300:
inspect the unmarked source first, then the native TT/cap20 overlay. Reference
markings are disclosed; this is source-first review, not blind review. Use the
emitted candidate `#`, not the amber `alt #`; record an unreadable identifier as
null. Identity choices are `ball`, `another_object`, or `uncertain`; for `ball`,
center choices are `plausible`, `clearly_displaced`, or `cannot_judge`.
Keep the original 10-pixel outcome separate. These selected eight frames do
not establish general rates, rankings or a tracking-method choice. All nine
embargoes, three sealed holdouts and completed review decisions remain protected.

The existing validation remains 33 focused passes and 993 full-suite passes
plus the existing Windows skip; no tests or completed visual reviews were
repeated. These three post-execution context updates are intentionally unstaged,
with an empty index and HEAD unchanged at `7a2e660a38877e2000fa997e675c86b97d55e9ac`.
Further staging and committing each require separate approval. No new
scientific run, retry or budget renewal is authorized.

## Prior checkpoint: 2026-10-06 candidate-identity implementation validated; staging is next

Ryan's exact approval, "ok I'm back chat. Lets move forwar sir", authorized
implementation, artificial validation and the conditional execution/human-review
scope in `../ball_crop_candidate_identity_review_proposal.md`. The separate
approval is `configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_identity_review_approval_v0_1.json`;
the frozen proposal and exact scope remain unchanged.

One new runner, `src/ball_tracking/crop_candidate_identity_review.py`, and one
test module implement the fixed sixteen-image scope: an existing unmarked PNG
and native TT/cap20 `view_0` overlay for each P003 representative frame 300,
301, 302, 304, 308, 319, 320 and 324. After successful byte verification, Ryan
may inspect each unmarked source first, then its existing overlay, and record
identity and qualitative center-placement judgments. The overlays contain
reference markings, so this is source-first review, not blind review. The
parent may not inspect pixels or read/hash scientific bodies. The saved
10-pixel outcomes remain separate from these pending semantic judgments;
this selected eight-frame case study cannot establish general error rates.

The distinct `post-review-candidate-identity:verify:` unit permits one
conditional attempt with at most 120 charged seconds. It has not run or spent
its allowance. The preserved prefix remains 3,121 events and 60 closed attempts:
56 successes and four historical failures, with tip
`7a990a3fd2b86502dd6245d6d08d2d17c75abe4534bad8d6cc323aa9c43ba701`.
Cumulative time remaining stays `11037.211000000018` seconds. Consumed recovery
and output-presence attempts remain consumed; no old budget or retry is renewed.
All nine embargoes, three sealed holdouts and prior review decisions remain protected.

Focused validation passed all 33 new tests in 10.953 supervised seconds, with
no skips, failures or errors. Full validation completed 994 tests in 2,090.750
supervised seconds: 993 passes and the single existing Windows directory-symlink
skip, with no failures or errors. The 165 source/test/requirements bindings
matched before and after validation; owned cleanup and final accounting passed.
The create-only `implementation_validation.json` certificate is sealed under
`data/outputs/t/ci_impl_efeefd58f680/`, alongside the records, logs, snapshots
and source review. Its manifest binding changed without changing the approved
specification. Existing monitor-design and helper race evidence were reused
without rerunning their checks. Output accounting covers the fresh TEMP tree
and log; legacy fixture paths remain outside that byte subtotal.

No real scientific worker, image inspection, media decoding, inference,
scoring or visual adjudication has occurred for this scope. Branch/HEAD remain
`codex/ball-detector-baseline` / `efeefd58f6801ffe5de106a48f8dad1e835b9647`,
with nine intended unstaged files and an empty index. Next: request separate
approval to stage those nine validated files, then separate commit approval.
The real review target and post-commit checkpoint remain absent.
Only after a verified clean commit and release
checkpoint may the already conditional unit run. Nothing is staged, committed
or pushed by this implementation work.

## Prior checkpoint: eight-frame candidate identity review proposed

The next proposed step is
`../ball_crop_candidate_identity_review_proposal.md`, with exact image bindings
in `configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_identity_review_v0_1.json`.
It fixes P003 representative TT/cap20 frames 300, 301, 302, 304, 308, 319, 320
and 324 from the previously returned present-nonmatching row. Each has an
existing unmarked PNG and native `view_0` overlay; no new rendering is needed.
Source inspection established the setting-to-view mapping. Expected image
bindings were copied from the committed proposal and verified administrative
preservation audit, without opening/hashing images or scientific manifests.

The proposal requests one new monitored, 120-second maximum verification
attempt for those sixteen image byte bindings, followed by Ryan's new
frame-specific identity and qualitative center-placement judgments. The
parent would receive only administrative verification metadata and present
the exact images for Ryan to inspect. Existing overlays contain reference
markings; this would be source-first review, not blind review. The previous
10-pixel outcomes and completed package reviews remain unchanged.

This is a proposal only. No new implementation, tests, scientific execution,
media decoding or visual review ran. No budget or consumed attempt was renewed.
The previous three dirty context files are preserved; the two new proposal
files are untracked, making five intended unstaged files. The index is empty
and HEAD remains `efeefd58f6801ffe5de106a48f8dad1e835b9647` on
`codex/ball-detector-baseline`. Nothing was staged, committed or pushed.
Next: approve the exact new scope before implementation or scientific access;
future staging and committing remain separate approval steps.

## Prior checkpoint: output-presence diagnostic complete; next study needs its own scope

Ryan separately authorized staging and committing the exact ten validated files.
Commit `efeefd58f6801ffe5de106a48f8dad1e835b9647` on
`codex/ball-detector-baseline` was verified clean before the already conditionally
approved output-presence unit ran. Nothing was pushed.

The single worker succeeded, attempt `395c3038fe7440a1b59912df476c3dd7`.
It used only the bound recovered breakdown and preserved all 48 original rows,
with the two pools, settings and original execution roles kept separate. Each
saved S list now has its own missing-current-output and present-nonmatching-
current-output lists and counts. The parent received the verified 11,566-byte
summary through the administrative transport; it did not reopen or hash
scientific input or output bodies.

One example copied from the returned P003 representative TT/cap20 row is
`4: 310, 311, 322, 323` missing current outputs and
`8: 300, 301, 302, 304, 308, 319, 320, 324` present nonmatching current outputs.
This is one saved row, not a cross-row total or a new performance rate.
Present nonmatching output does not establish wrong-object identity or
inaccurate ball-center placement. Those distinctions and missing-output causes
remain unresolved; no semantic labels, method, operating point or quality gate
were selected.

Charged time was 42.734 seconds of the 120-second allocation; supervisor wall
time was 43.265 seconds and complete command wall time was 84.703 seconds.
Cleanup and final accounting passed with no resource overshoots. The journal
now has 3,121 events and 60 closed attempts: 56 successes and the same four
preserved failures. Its tip is
`7a990a3fd2b86502dd6245d6d08d2d17c75abe4534bad8d6cc323aa9c43ba701`.
The remaining cumulative allowance is `11037.211000000018` seconds. Both the
output-presence attempt and prior recovery attempt are consumed, with zero
authorized attempts remaining; arithmetic unused time grants no retry.

The completion record and verified summary transport are
`data/outputs/t/op_impl_de134d942767/output_presence_completion_efeefd58f680.json`
and `output_presence_execution_efeefd58f680_stdout.json` in that same directory.
All scientific outputs remain ignored. No detector inference, scoring,
selection or media decoding ran; no completed tests or visual reviews were
repeated for execution or closeout. All nine embargoes, three sealed holdouts
and prior player/court and clip-review decisions remain preserved.

The three post-execution context updates are intentionally unstaged; the index
is empty. HEAD remains `efeefd58f6801ffe5de106a48f8dad1e835b9647`.
Next: prepare a separately bounded study proposal before any further scientific
access. No new study, real retry, budget allocation, semantic adjudication or
Git step is authorized by this completed execution. Further staging and
committing each require separate approval.

## Prior checkpoint: output-presence implementation validated; staging is next

Ryan's "Yes move forward chat" approved the exact output-presence proposal,
implementation, artificial validation and one conditional scientific unit.
The frozen proposal and separate approval are preserved. A new reader and pure
formatter retain the complete recovered breakdown and derive the two approved
ordered membership lists separately for all 48 rows. They keep semantic causes,
method choice, operating point and quality gate unknown.

Independent review passed. The accepted focused run passed 42 tests; the full
suite passed 960 tests with the one existing Windows directory-symlink skip.
The initial focused run passed 41 tests and failed one invalid exact comparison
of floating-point time. Only that test assertion changed to the existing
seven-decimal precision. Its log, source snapshots, failure and correction are
preserved; no production limit changed. The first full run was stopped by a
validation-helper race while a test renamed a temporary directory. Cleanup
passed. After a reviewed helper correction, fresh focused/full validation
passed; the interrupted run and original helpers remain preserved.
Current validation binds all 163
source/test/requirements files. Validation and certificate evidence are under
`data/outputs/t/op_impl_de134d942767/`.

The new `post-review-output-presence:summary:` role has at most one attempt
and 120 charged seconds, bounded by the unchanged cumulative balance of
`11079.945000000014` seconds. Its 3,071-event predecessor history preserves
59 closed attempts, 55 successes and all four failures. The completed recovery
attempt remains consumed; its unused role time is not renewed. The responsive
monitor and its completed design evidence are reused.

No real output-presence worker ran. No parent scientific body was read or
hashed; no scientific inference, scoring, rendering or visual review occurred.
All validation fixtures were artificial.
The only conditionally authorized scientific input remains the 744,235-byte
recovered breakdown, accessible inside the owned worker after release.
Existing scientific evidence, nine embargoes, three sealed holdouts and prior
review decisions remain preserved.

Branch/HEAD remain `codex/ball-detector-baseline` /
`de134d942767b70dfc6da360745f50405a8b3f8d`. The index is empty and the exact
intended scope is ten unstaged files: two source modules, two test modules,
proposal, approval, manifest and these three context documents.
Next: separately approve staging, then separately approve committing the
validated scope. The new post-commit execution checkpoint remains absent.
No staging, commit, push, PR or merge is authorized by the study approval.

## Prior checkpoint: output-presence study proposed from one saved breakdown

Ryan's "move forward chat" authorized preparing the next concrete study.
The proposal is `../ball_crop_candidate_retention_output_presence_proposal.md`.
It requests one worker-only read of the 744,235-byte recovered breakdown,
without reopening the large evaluation pools, observations, labels or media.
Within every existing row, split S memberships by presence in that same row's
eligible false-observation list: present but nonmatching current output versus
no current emitted output. Preserve both pools, all 48 rows and original roles.

Source reasoning establishes this distinction for both frozen cap policies:
each emits at most one original threshold-qualified current candidate, and an
unmatched eligible frame's false-positive count equals its accepted output
count. All four relevant source blobs match the original scoring commit.
No new scientific memberships or counts were calculated during preparation.
The six-clip review receipt has no individual-frame semantic verdicts, so
wrong-object versus ball-center placement remains unknown. No repeat visual
review or new semantic adjudication is requested by this proposal.

Implementation and the new derivation await explicit approval. The proposed
unit has at most one attempt and 120 charged seconds from the existing
remaining cumulative budget, using the validated responsive monitor. This
neither renews the completed recovery nor repurposes its unused role time.
Source review, focused/full validation and separately approved staging/commit
precede conditional execution. The old scientific body-access boundary remains
effective until the new exact input and operations are approved.

Preparation used only source, reviewed authority and administrative receipts.
No scientific body was read/hashed, no test or experiment ran, and no completed
review was repeated. Planning evidence and source-contract bindings are under
`data/outputs/t/output_presence_plan_de134d942767/`.
Branch/HEAD remain `codex/ball-detector-baseline` /
`de134d942767b70dfc6da360745f50405a8b3f8d`, with an empty index. Intended dirty
scope is now the three existing context files plus the new proposal. All prior
budgets, evidence, embargoes and holdouts remain preserved. Next: Ryan decides
whether to approve the exact proposal; no additional Git step is authorized.

## Prior checkpoint: saved error-breakdown recovery completed successfully

Ryan separately authorized staging and committing the exact validated 34-file
scope. Commit `de134d942767b70dfc6da360745f50405a8b3f8d` on
`codex/ball-detector-baseline` contains those exact staged blobs. Working-file
bytes were preserved, with Git's configured line-ending normalization accounted
for. The worktree and index were clean before execution; nothing was pushed.

After Ryan's "ok lets move forward", the create-only post-commit checkpoint
was bound to that actual HEAD, unchanged manifest and implementation certificate.
All 159 source bindings and 16 validation-evidence bindings matched. The public
recovery command then ran once, including its own metadata preflight. No tests,
old experiments, abandoned scanner benchmarks or visual reviews were repeated.

Recovery attempt `05fe00c14f224c5abfc2cc6008e90f96` succeeded. The public runner
verified completion, preservation and bounded summary transport before returning
the 48 saved rows. Representative and challenge pools remain separate. Only the
owned worker read/hashed the three scientific inputs and its generated outputs;
the parent received the verified summary through administrative transport.
No inference, scoring, media decoding, training or method selection ran.

The supervisor charged `52.54699999999866` seconds; its wall time before final
publication was `53.09300000000076` seconds. The full command, including metadata
preflight and post-run verification, took `106.45300000000134` seconds. Eleven
complete scans succeeded; maximum safety-check interval was about 0.296 seconds.
Peak sampled combined memory was 419,811,328 bytes. Final output bound was
7,415,183,417 bytes, minimum free disk 1,465,797,832,704 bytes. No resource
overshoot, final-accounting error or cleanup error was recorded; owned cleanup
was verified.

The original failed attempt and 3,010-event prefix remain preserved. The new
completion is event `00003070.json`, chain tip
`d800b77b4db2128d1baa09db59538ab6f16d4aad6d96aaa7a9fd84f96c11bf92`.
Remaining role time is `240.18800000001647` seconds and cumulative experiment
time is `11079.945000000014` seconds. The one recovery attempt is consumed.
Arithmetic time remaining does not grant another attempt; do not rerun either
public diagnostic entry point.

The verified summary records, for example, 14 saved misses under both cap20 and
all policies for P001 representative TT. Its cap20 row has six cap-loss and four
final-output-loss memberships; its all row has zero and ten respectively.
Retaining the candidates did not resolve those saved final outputs. This does
not distinguish wrong-object output, center placement or missing output. No new
rates, pool totals, rankings or cross-row unions were calculated.

Execution checkpoint, launch receipts, bounded returned transport and completion
record are under `data/outputs/t/ebri_fa730bcb6d2e/`. Scientific outputs remain
ignored at the existing experiment root's
`audit/post_review_error_breakdown_recovery_v0_1/`. Never follow their pointers
for parent body reads/hashes. Nine prediction embargoes, three sealed holdouts,
six retention reviews and twelve earlier YOLO final-frame reviews remain intact.

Next: specify a separate study of the saved final-output losses that can
distinguish missing output, object identity and center placement. This is a
proposed question, not a new experiment authorization or selected method.
Ball-tracking quality, possession understanding, matchups and defensive scoring
remain unfinished. This post-run continuation changes only three context files;
staging and committing those new documentation changes are not authorized.

## Prior checkpoint: recovery integration validated; staging approval pending

The new `src/ball_tracking/crop_retention_error_breakdown_recovery.py` connects
the saved error-breakdown recovery to the validated responsive monitor. Its
versioned manifest, integration design and approval preserve the original
scientific scope, three worker-only inputs, failed attempt and 3,010-event
prefix. The original 300-second allowance remains shared; the recovery balance
is still 292.73500000001513 seconds. The original runner, formatter, monitor,
resource module and historical approvals/certificates were not edited.

Independent static review passed. All 32 focused synthetic
tests passed, followed by 919 full-suite tests: 918 passes
and the existing Windows directory-symlink capability skip, no failures/errors
on the final validated run. Supervised elapsed times were
8.719 seconds focused and 2241.687
seconds full. Validation binds the exact current source/test inventory and
reuses the monitor's completed design check without rerunning it.

Evidence and the new implementation certificate are under
`data/outputs/t/ebri_fa730bcb6d2e/`. The post-commit execution checkpoint is
deliberately absent. No scientific recovery, parent scientific-body read/hash,
new visual review or Git mutation occurred. The planned 48-row diagnostic is
still pending; this completes its runner integration and validation.

The intended scope is 34 unstaged files, with empty index on
`codex/ball-detector-baseline` at
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`. Next: Ryan may authorize staging the
exact files in `data/outputs/t/ebri_fa730bcb6d2e/staging_scope.json`. Committing
remains a separate approval. After a validated clean commit, the create-only
execution checkpoint must bind its actual HEAD before the conditional recovery.
See `../ball_crop_candidate_retention_error_breakdown_recovery_integration.md`.

## Prior checkpoint: responsive monitor validated; 886 full-suite passes

Ryan approved the monitoring redesign with "ok I like it. Move forward" after
reviewing the difference between computer safety and the arbitrary half-second
accounting target. The new isolated backend is
`src/ball_tracking/crop_retention_monitor.py`; policy and scope are in
`../ball_crop_candidate_retention_monitor_revision.md` and its versioned approval.
The compiled scanner/native timing proposal is set aside; its evidence remains
preserved and no pending native allocation was executed.

Fast resource checks remain at most one second apart, while a separately owned
Python helper gets ten seconds per complete accounting request. The effective
free-disk reserve is 50 GiB. Combined sampled RAM remains bounded at 8 GiB, with
separate Windows committed-memory backstops. Process ownership begins before
execution, and whole-root preflight/final accounting remain mandatory. Original
supervisor, runners, journal limit bindings and consumed budgets are unchanged.

Independent static review passed. All 37 focused checks passed on their first
run (0.978 unittest seconds). The separate fresh 12,000-file/400-directory
design check passed with three complete scans and a maximum safety-check gap
of 0.266 seconds. Its final scan took 0.890 seconds, demonstrating accounting
longer than the former half-second limit while safety checks continued.
The full suite passed on its first run: 887 tests, 886 passes and one existing
Windows directory-symlink capability skip, no failures/errors, in 2197.840
unittest seconds (2199.922 supervised seconds). Source/test bytes stayed frozen
across validation. No scientific execution, old
fixture traversal, parent scientific-body read/hash, Git mutation or visual
re-review is included. The saved error breakdown still requires recovery-runner
integration/authority and a separately authorized validated clean commit.

Administrative evidence is under `data/outputs/t/ebdm_fa730bcb6d2e/`; see
`completion_checkpoint.json`, the three result records and the design receipt.
Starting 25-file dirty state and 181 source/test/configuration/context bindings
were captured. Current intended scope adds four files (monitor, tests, design
and approval), for 29 unstaged files and empty index at unchanged branch
`codex/ball-detector-baseline`, HEAD `fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`.

## Prior checkpoint: compiled prototype built; focused and full validation passed

Ryan authorized the specified installation and isolated prototype with "ok well
lets move forward" and asked to keep usage focused. Microsoft Build Tools
17.14.41 (installed build 17.14.37710.0), MSVC v143 and the selected Windows SDK
are installed and verified, with no reboot required. The fixed bootstrapper's
Microsoft signature and version were checked. Existing newer C++ runtimes remain
registered; setup also added required components. The approval is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_compiled_batch_build_approval_v0_1.json`.

The isolated production/test extensions and Python accounting wrapper are under
`data/outputs/t/ebcb_src_fa730bcb6d2e/`, successful source `revision_02`, build
`build_02`. Public ABI/path, allocation/error and deadline behavior passed
independent source review. Production exposes no artificial provider hooks.
Both binaries compiled with strict warnings and passed architecture/export/
dependency inspection; the build receipt binds 260 dependency inputs.

All **39 focused artificial checks passed** on their first actual test run.
The single full regression run completed **850 tests: 849 passes and the existing
directory-symlink capability skip**, with no failures/errors. It took 2290.353
unittest seconds and 2296.125 supervised seconds. Peak sampled worker-tree memory
was 955,551,744 bytes; cleanup succeeded and no job members remained. All 156
production/test/requirements bindings stayed unchanged.

Two routine setup corrections are preserved: the first build stopped on a
Python-header warning, resolved by a file-scope forward declaration without
weakening warnings; the first validator invocation could not import `psutil`
and stopped before any test/worker launch. Its replacement reuses the frozen
Windows Job/RSS helper and adds no Python dependency. Neither was a scientific
failure. Original revisions, logs and correction records remain intact.

No production query series, performance benchmark, scanner replacement or real
scientific recovery ran. Speed is still unproved. The next reviewed proposal is
`../ball_crop_candidate_retention_compiled_scanner_validation_proposal.md`: one
new conditional native correctness/static/dynamic validation allocation, 120
charged seconds with separate outer command limits totaling 150 seconds. It
requires new approval; no consumed allocation is renewed. The planned 48-row
saved error breakdown still awaits safe accounting and validated integration.

All scientific embargoes, holdouts, completed reviews and evidence remain.
Git state is 25 intended unstaged files, empty index, unchanged branch
`codex/ball-detector-baseline` and HEAD `fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`.
No Git mutation is authorized. See the new ignored completion checkpoint for
exact result/source/binary bindings and final preservation checks.

## Prior checkpoint: compiled-batch plan ready; compiler installation proposed

The read-only toolchain inventory and concrete build/interface plan are complete:
`../ball_crop_candidate_retention_compiled_batch_plan.md`. CPython 3.11.15/x64
already has its extension headers and import library. No usable compiler or
Windows SDK was found in the checked PATH, known locations or registry roots;
installed C++ runtimes and VS Code are not those build tools. No installer was
downloaded or executed, and no prototype was built or tested.

The proposed next block installs specified Microsoft Build Tools/SDK components,
then builds and artificially validates an isolated CPython C extension. Its
128-name batches retain fresh per-file queries, full native identities, the
same Python deadline callback and original error precedence. Discovery and both
complete accounting inventories stay in Python. Speed remains unproved; a later
live correctness/performance series needs a fresh explicit envelope. No consumed
series or leftover arithmetic time grants another attempt.

Installation/implementation approval is pending. Scientific recovery, scanner
integration and Git mutations are outside this plan. All embargoes, holdouts,
completed reviews, evidence, resource limits and readiness gates remain. The
planned 48-row breakdown of saved ball-candidate errors is still pending safe
accounting. Planning records are under `data/outputs/t/ebcb_plan_fa730bcb6d2e/`.
Final planning scope is 23 intended unstaged files, empty index, branch
`codex/ball-detector-baseline`, HEAD `fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`.

## Prior checkpoint: accounting reassessed; compiled-loop build plan preferred

Ryan requested reassessment after the completed negative speed finding. The
saved profile, component evidence, accounting/diagnostic source and official
Windows API documentation were reviewed without new tests, native probes,
benchmarks or scientific reads. The decision note is
`../ball_crop_candidate_retention_accounting_reassessment.md`.

Fresh file metadata occupied about 59.8% of the older profiled scanner call;
that incomplete profiled call is not an unprofiled speed bound. The latest tiny
comparison was order-sensitive: the second method won nine of ten pairs. That
observation does not establish cache causation or invalidate the saved negative
gate result. No timing pass was discarded or repeated.

The source-only write audit found an explicit 65,536-byte limit on readable
summary text, but no complete pre-write byte budget for JSON artifacts, receipts,
journals, logs and temporary/runtime output. Saved receipts do not make history
immutable. Counting only a mutable suffix is therefore not a proved substitute
for whole-root accounting. Directory-entry sizes have a documented hard-link
freshness limitation and are not an equivalent shortcut either.

Preferred next scope: establish a supported build path and review a bounded
compiled sequential loop that still queries every file freshly and preserves
both complete inventories, identities, multiplicity, conservative sizes and
all deadlines. This may reduce language-boundary overhead; its performance is
unproved. The limited local inventory found no common compiler on PATH or the
usual Visual Studio locator. It did not establish that no compiler exists
elsewhere, and no compiler was run or installed.

No implementation or execution allocation was added. All prior gates, budgets,
failures, embargoes, holdouts and completed reviews remain unchanged. The planned
48-row breakdown of saved results and reliable ball-tracking quality remain pending. Git
state is branch `codex/ball-detector-baseline`, HEAD
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`, 22 intended unstaged files and empty
index. Reassessment records are under `data/outputs/t/ebra_plan_fa730bcb6d2e/`.

## Prior checkpoint: identity equivalence passed; component speed gate not met

Ryan approved the reviewed identity-equivalence follow-up with "Ok move forward
now chat". The separate approval is recorded in
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_by_name_identity_equivalence_approval_v0_1.json`.
The implementation and its preserved source revision are under
`data/outputs/t/ebni_src_fa730bcb6d2e/`. The Windows adapter remains unchanged.

Independent source review passed. All 50 relevant artificial checks passed on
their first run: 35 identity/timing checks and 15 adapted supervision regressions,
with zero failures, errors or skips. The unchanged adapter's prior 32 passing
checks were reused; neither those checks nor the full suite were repeated.

The one authorized native series completed as `component_comparison_complete`,
attempt `0148ff4a58d247aa83b1e4758b48902e`, under
`data/outputs/t/ebni_fa730bcb6d2e/`. All 94 comparisons across seven correctness
phases passed. The two backends retained their different complete identifiers
while agreeing on known file groups, sizes and continuity through the controlled
mutations. Opaque 128-bit evidence was preserved and checked separately. Both
backends observed a different identity for the declared replacement. This does
not establish arbitrary concurrent-replacement behavior. The final fabricated
fixture had 64 names, four directories and 2,125 logical bytes counted per name.

All 20 timing batches and ten alternating pairs completed, totaling 1,280 fresh
queries. The median native/reference duration ratio was `0.8992258224480973`.
Native was faster in six pairs and slower in four. The prospective gate required
a median at most `0.80` and every native batch faster; both conditions failed.
This is a valid negative performance finding. `worth_full_scanner_proposal` and
`scanner_readiness_passed` remain false. No pass was discarded or rerun.

The unchanged supervisor sealed a successful execution with `1.5780000000013388`
charged seconds, a 221,061-byte final output bound and no resource violations.
The arithmetic remainder is `28.42199999999866` seconds, with zero native series
remaining. Parent-reported harness/external wall times were respectively
`2.0964757000001555` and `2.2839816` seconds; they are separate from sealed active
time. Independent post-run metadata audit passed in `outcome_audit_01.json`.

Next: reassess the output-accounting design using saved evidence. This result
does not justify integrating the candidate or repeating its series. The saved
48-row scientific error breakdown still awaits safe, sufficiently fast output
accounting. Ball tracking quality and the full scanner readiness gates remain
open; this task produced infrastructure evidence, not improved ball tracks.

All earlier results and allowances remain preserved, including the earlier
numeric-identity finding. No scientific bodies or fixtures were traversed by
the parent; no completed visual reviews were repeated. Embargoes and sealed
holdouts remain unchanged. Git mutations remain unauthorized: branch
`codex/ball-detector-baseline`, HEAD `fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`,
21 intended unstaged files and an empty index. Preservation verification is
recorded in the implementation directory's `completion_checkpoint.json`.

## Prior checkpoint: identity semantics reviewed; follow-up proposal prepared

Ryan asked to continue after the by-name component finding. The next work was
read-only review of identity semantics and preparation of
`../ball_crop_candidate_retention_identity_equivalence_proposal.md`. No new
component code, tests, native probe, benchmark or fixture traversal ran.

The current byte counter uses file identifiers as equality keys, not numeric
quantities. A consistent one-to-one relabeling across both complete inventories
preserves membership, hard-link multiplicity, conservative maximum sizes and
the byte sum. Separate numeric identifiers can therefore support the same
accounting semantics, conditional on correct same-file grouping and continuity.
Per-phase group agreement alone is insufficient: still-live files must retain
their own identity across observations. This is source-based reasoning, not a
new empirical pass or proof for arbitrary concurrent replacements.

The proposal retains the existing full native volume/FileId64 key and complete
Python device/inode key separately. It requires declared and cross-backend
hard-link groups, distinct files, constant per-backend volume, live-file
continuity, known sizes, consistent observed replacement reuse, and opaque
128-bit evidence. No truncation, identity translation or 128-bit key redesign
is proposed. Timing would use separate frozen expectations for the two APIs.

The saved numeric mismatch remains `identity_contract_review_required`; its
native series is still consumed and its 29.21900000000096 arithmetic seconds
are not renewed. Speed and scanner readiness remain unproved. The follow-up
asks for explicit approval of the amended component checks and a fresh bounded
30-second/16 MiB series, with the original supervisor and all existing gates.
Implementation, native execution, full scanner integration, scientific recovery
and Git mutations are not authorized by this preparation.

Preparation records are under `data/outputs/t/ebni_plan_fa730bcb6d2e/`. Eighty
source/authority/context/fabricated-metadata bindings were verified. Only the new
proposal and continuation text in three context files change; 77 other bindings
and all historical context bodies remain protected. The expected dirty scope
is 20 intended unstaged files, index empty, branch `codex/ball-detector-baseline`,
HEAD `fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`. No completed tests or visual reviews
were repeated, no old budget changed, and all scientific boundaries remain.

Next: obtain approval of the concrete identity-equivalence component envelope.
The project remains at ball-tracking diagnostics; the 48-row saved error
breakdown still awaits safe, sufficiently fast output accounting.

## Prior checkpoint: metadata component tested; volume identity differs

Ryan approved the reviewed by-name component proposal on 2026-10-05 and asked
for an honest project status. Approval is recorded separately in
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_by_name_feasibility_approval_v0_1.json`.
The frozen proposal remains historical; its formerly pending approval is now
satisfied for this component only. No Git or real-recovery permission was added.

The ignored adapter, tiny comparison engine, supervision harness and artificial
checks were implemented under `data/outputs/t/ebbn_src_fa730bcb6d2e/`. Combined
independent review passed. All 72 new artificial tests passed on their first
validation run, with zero failures, errors or skips. Old tests and the full
suite were not repeated; the original scanner/supervisor remained unchanged.

The single native series then completed under the original supervisor at
`data/outputs/t/ebbn_fa730bcb6d2e/`, attempt
`d774f180726d47a08a6aead2658a807a`. The API was available and the local fixed
NTFS/ancestor checks passed. The first fabricated-file comparison found the
same file ID (`1125899906873685`) and logical size (64 bytes) but different
volume identifiers: ordinary `os.stat` returned `986718957`, whereas the native
API returned full unsigned value `14572188484234126061`. Raw signed storage and
the complete 128-bit file ID are preserved. No identifier was truncated or
remapped to force equality.

The outcome is `identity_contract_review_required`. This is a completed,
supervisor-bound component finding, not an exception or a passing compatibility
check. It prevents a direct substitution under the current numeric-identity
contract. It does not establish that the native query is wrong or unsafe under
a different reviewed contract. Only the first initial file comparison ran:
later correctness mutations, the 64-entry timing inventory and all timing
passes did not run. Speed benefit and scanner readiness remain unproved.

The supervisor charged `0.7809999999990396` seconds; command wall time was
`1.3705132` seconds. Its five-event journal closed successfully, with no resource
overshoot or final-accounting error, maximum monitor interval 0.25 seconds and
final output bound 34,770 bytes. The final event SHA-256 is
`23af9026d35da59de3d6500b33e8bca498948c3bd9ec7d10e40e1a9c683d400a`.
The arithmetic balance is `29.21900000000096` seconds, but the single native
series has been consumed: no retry or new allocation is implied.

The project has demonstrated player coordinates across three reviewed
possessions and completed the ball-evaluation protocol, 75-frame pilot,
150-frame development baseline and controlled detector/association comparisons.
The retention and YOLO visual reviews are complete. These experiments establish
useful tradeoffs, but no robust end-to-end ball tracker or multi-possession ball
quality gate has been selected. Recent progress concerns the resource monitor;
it is not demonstrated tracking-quality improvement. The saved 48-row error
breakdown remains pending on safe, sufficiently fast output accounting.

Next technical decision: review the identity representation explicitly before
considering another by-name experiment, or select a different accounting design.
Do not silently narrow the native volume ID. Full scanner correctness/static/
dynamic gates, integration/regression, a recovery certificate and separately
authorized clean commit remain prerequisites for real recovery. Possession
understanding, roster identity, matchups and validated defensive scoring follow
the ball-tracking foundation; no completion percentage or ETA is established.

Post-run review/preservation and this checkpoint are documentation work only.
All nine embargoes, three sealed holdouts, six retention reviews, twelve YOLO
final-frame reviews, old balances and completed/failed evidence remain intact.
There was no parent scientific-body access, old stress-fixture traversal, or
real-root execution. Routine command quoting, a metadata-directory lookup and
a bookkeeping path-array expression were corrected without permission stops;
none was an experimental failure.
The worktree has 19 intended unstaged files, an empty index, branch
`codex/ball-detector-baseline` and HEAD `fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`.

## Prior checkpoint: fresh Windows metadata feasibility proposal prepared

Ryan's 2026-10-05 instruction replaces the blanket stop-on-any-failure rule:
resolve ordinary tool/helper problems within approved scope; pause for material
correctness, evidence, resource or scope issues. The updated working agreement
records this. Historical stop instructions below describe their earlier scope;
they do not override Ryan's latest instruction. Git permissions, embargoes,
sealed holdouts and consumed experimental allowances remain separate.

Read-only review of the saved profile and existing source supports investigating
a different fresh metadata interface. The new proposal is
`../ball_crop_candidate_retention_by_name_feasibility_proposal.md`: an isolated
Windows by-name adapter, artificial checks and one conditional tiny correctness/
timing series before any full scanner implementation. Availability, complete
identity compatibility, fresh sizes and useful speed benefit are unproved. The
proposal requests a new cumulative 30-second, 16 MiB feasibility allowance;
it does not consume or renew any old allocation.

The earlier CPython raw-source lookup was blocked by the fetch tool. It was not
a test or diagnostic failure. Its interruption receipt remains unchanged and
the restricted fetch was not retried. Official Microsoft interface declarations
support this proposal without claims about installed CPython internals.

Only documentation changed during preparation: the proposal, this checkpoint,
roadmap, validation history and working agreement. No native API probe, tests,
benchmark, fixture traversal or scientific-body access occurred. Preparation
and final verification records live under `data/outputs/t/ebbn_plan_fa730bcb6d2e/`.
The intended dirty scope is now 18 files, with an empty index, on
`codex/ball-detector-baseline` at `fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`.
No staging or other Git mutation is authorized.

Next: obtain approval of the concrete component envelope, then implement its
reviewed adapter/harness and perform its new checks and conditional bounded
series. Full scanner readiness and the saved 48-row scientific error breakdown
remain pending. Earlier successful/failed evidence, all nine embargoes, three
sealed holdouts and the six plus twelve completed visual reviews stay intact.

## Prior checkpoint: static timing attempt failed on the first call; stopped

Ryan approved the reviewed static timing request with "Yes move forward".
The separate approval is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_scan_prefix_static_timing_approval_v0_1.json`.
New ignored harness, artificial tests and validation are preserved under
`data/outputs/t/ebxt_src_fa730bcb6d2e/`. Independent static review passed, followed
by one run of 29 new helper tests: 29 passes, zero failures, errors or skips.
The candidate's earlier 26 correctness tests were not repeated.

The one approved static attempt was then executed at
`data/outputs/t/ebxt_static_fa730bcb6d2e/`, attempt
`5650139001c240c5bb6c9e243927f0de`. The owned worker verified the preserved
fabricated fixture's metadata before timing. Call 1 raised the unchanged
accounting-deadline `ResourceLimitError` after a measured
`0.4854300000006333` seconds and returned no byte total. This failed the static
gate; no second candidate call ran. The after-series fixture check did not run.
The saved call progress and worker result are failure evidence, not a successful
supervisor-bound completion result. Static and overall readiness remain false.

Read-only failure preservation verified the sole closed attempt, six-event
journal, reservation/completion seals and absent supervisor lock. The final
event SHA-256 is
`3dfa324db2969075accea17ea8485898cc4962a98c277311a54a1cd6dd4a48c1`.
The supervisor charged `2.312999999998283` seconds; the external command took
`2.6772916` seconds. No time, memory or output overshoot or final-accounting error
was recorded; maximum monitor interval was `0.26599999999962165` seconds.
The new allocation has `27.687000000001717` seconds arithmetically unspent but
**zero authorized attempts remaining**. The failure does not authorize a retry,
an alternate root, code repair or a changed threshold.

`failed_execution.json` in the new helper directory preserves the command
outputs, failure-artifact hashes, charged/wall times and unchanged old balances.
Only failure documentation and preservation followed the stop. The candidate,
supervisor, old approvals, successful/failed evidence and timing request remain
unchanged. No parent fixture traversal, scientific body access or real-root
traversal occurred. All embargoes, sealed holdouts and completed visual reviews
remain protected; no full suite or scientific recovery ran.

The new approval brings the intended dirty scope to sixteen files on
`codex/ball-detector-baseline`, HEAD
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`, with an empty index. No Git mutation
is authorized. The next proposed approval is read-only review of existing
profile/source evidence to prepare another concrete optimization proposal;
no new tests, benchmark, profiler or scientific access would be included.
No manual command is pending. Stop remains in effect until Ryan authorizes
the next scope.

## Prior checkpoint: bounded static timing request ready for approval

The amended prefix candidate's 26 focused passes and independent reviews remain
valid. No benchmark or additional test has run. Ryan's "Move forward" authorized
preparation of `../ball_crop_candidate_retention_scan_timing_request.md`.

The request proposes a new static-only allocation: one owned worker, 30 seconds
of recorded unit/cumulative active time, 16 MiB new outputs, 8 GiB combined worker
memory and 10 GiB minimum free disk. Keep 0.25-second polling, the live one-second
monitor limit and the candidate's half-second deadline. The original supervisor
captures charged elapsed before its final accounting/seal publication; those
mandatory checks remain, and total command wall time is reported separately.

The worker would verify the preserved 12,000-file/400-directory fabricated tree
and run exactly 30 candidate calls, each returning 12,259,360 bytes in less than
0.40 seconds. No candidate warmup, extra candidate verification call, profiler
or retry is allowed. First failure stops dispatch. The unchanged supervisor and
original scanner monitor a separate small result root. The existing fixture
remains read-only, and its before/after preservation checks are metadata-only.

Independent request review passed after clarifying the existing time-accounting
semantics. Preparation verified 31 source/authority/synthetic-metadata bindings,
without traversing the fixture or real scientific root. Bindings, before-context
copies and completion evidence are under `data/outputs/t/ebxt_plan_fa730bcb6d2e/`.
The new request brings the intended dirty scope to fifteen files; the branch,
HEAD and empty index remain unchanged. No source, old approval or evidence is
altered by this documentation stage.

Next approval covers a new ignored static harness, its new artificial helper
checks and one conditional static execution if those checks and review pass.
It proposes no reuse/reset of the old profiling balance and no new dynamic
budget. Dynamic readiness, full regression and real recovery remain outstanding;
all scientific/Git boundaries below remain intact. No manual command is pending.
Stop on any new failure; no automatic repair or retry.

## Prior checkpoint: amended prefix candidate passed focused correctness

The separate directory-prefix scanner is implemented, including Ryan's approved
UNC correction: `prefix = os.path.join(folder, "_")[:-1]`. It prepares each
directory prefix once, then uses fresh `os.stat(prefix + name)` queries. The
two-inventory accounting algorithm and all existing deadline checks remain;
one additional check follows prefix preparation. The ordinary supervisor does
not install this candidate.

Both independent source reviews passed. The structural validator confirmed that
only the approved prefix preparation, added deadline check and query expression
differ from the frozen first candidate's executable code. The first and only
focused run passed all 26 tests with zero failures, errors or skips. Coverage
includes bare/extended UNC and drive-relative paths, fresh queries, hard links,
inventory changes, disappearance/errors and deadline enforcement. A small
temporary Windows fixture matched an independent ordinary-stat reference.

The test log reports 0.016 seconds; the helper took 0.24663389999841456 seconds,
with 0.583733 seconds command wall time. These are correctness-test durations,
not a scanner benchmark. The validation SHA-256 is
`416983627262eb332f74af528ad996aed93029ce81bc3f85b3c23d260f56cd73`;
the log SHA-256 is
`2f5e6316d89bbc780f34773507246cf7867d46bf81a5979e4e3d032284cab1bd`.
Evidence is under `data/outputs/t/ebsx_impl_fa730bcb6d2e/`, with the current
continuation in `completion_checkpoint.json` there. Independent result review
confirmed the structured counts, log and source/review bindings.

The blocked empty-prefix version, original proposal/approval and all earlier
failures remain preserved. The UNC amendment has separate authority. A subsequent
JavaScript wrapper syntax error stopped before its PowerShell command started;
Ryan approved correction with "Yes you may". That corrected preparation and
the single focused run succeeded. No test was rerun.

Branch is `codex/ball-detector-baseline`, HEAD
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`, with an empty index and fourteen
intended dirty files. The prior thirteen are joined by the separate amendment
approval. Context updates after validation are reporting changes; the validation
receipt retains its actual pre/post-test context snapshot. Runtime source,
tests, helper, approvals and all protected evidence remain frozen.

Next: prepare a concrete, bounded timing-execution request. Speed and full
regression for this candidate remain unverified. No stress benchmark, new profile,
full-suite run or real recovery is authorized in this stage. The completed
profiling allowance retains `26.560999999998785` seconds and cannot be silently
reused or reset. The saved real balances, nine embargoes, three sealed holdouts
and eighteen completed reviews remain unchanged. Parent scientific-body reads
and hashes remain prohibited. Git steps are separately unapproved. No manual
command is pending. Stop on any new failure; no automatic repair or retry.

## Prior checkpoint: prefix implementation stopped at static review

Ryan approved the directory-prefix implementation and new focused correctness
checks with "Yes you may chat move forward". The separate scanner, approval,
26-test module and ignored structural-result helper were prepared. No test,
benchmark, profile, full suite or real recovery ran.

Independent test-source review found a blocker in the frozen proposal: for a
bare UNC share root such as `\\server\share`, joining an empty string omits
the separator needed before a filename. The proposed prefix concatenation is
therefore not equivalent to the original join for that required case. Read-only
inspection of the installed Python `ntpath.py` confirmed its conditional UNC
separator logic. The earlier proposal review missed this case.

Implementation stopped before validation. There is no validation-start marker,
test log, result or overall passing implementation-review receipt. The candidate,
tests, helper, original proposal and approval remain preserved; no repair or
retry has occurred. The exact review/binding checkpoint is
`data/outputs/t/ebsx_impl_fa730bcb6d2e/blocked_review.json`.

The proposed amendment is `prefix = os.path.join(folder, "_")[:-1]`: join a
nonempty placeholder to obtain the normal separator, then remove that one
character. It is not implemented or approved. Ryan's explicit amendment approval
is needed before changing the candidate, related tests and structural checker,
obtaining fresh review and running the new tests once. Timing remains unproved.

Branch/HEAD remain `codex/ball-detector-baseline` /
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`. The intentional dirty scope is
thirteen files, with an empty index: the prior ten plus the new scanner, test
and approval. Scientific data, all resource balances, nine embargoes, three
holdouts and eighteen completed visual reviews remain unchanged. No manual
command is pending. Stop on any new failure; no automatic repair or retry.

## Prior checkpoint: profile captured; directory-prefix candidate proposed

Branch is `codex/ball-detector-baseline`, HEAD
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`, with an empty index. The approved
single synthetic profile succeeded in capturing the anticipated accounting
deadline. It returned no byte total; readiness remains false. Fresh metadata
queries took 291.710 ms, approximately 60% of recorded scanner time. Path joining
took 71.589 ms cumulative, including nested work. The truncated profile does not
prove a speedup, tree instability or the original real-run cause.

The profile used 2.594 active seconds within the approved limits. Its completed
attempt is `4932f5dc070640e3a96cf094ff86859b`. The exact result checkpoint is
`data/outputs/t/ebsp_src_fa730bcb6d2e/profile_execution_continuity.json`, SHA-256
`bdb79f4f527beb7b3927b5c02dd5779d8a60e45c9deefac21f7416c6727b730b`.
The remaining profiling balance is `26.560999999998785` seconds, with no unused
execution authorization. Earlier helper/ownership failures and successful
corrections remain preserved; the final integrated helper passed 15 new tests.

The next draft is
`../ball_crop_candidate_retention_scan_prefix_proposal.md`: retain fresh ordinary
stat calls and the two-inventory algorithm, but construct the directory prefix
once per directory. Its benefit remains unproved. Ryan authorized documentation
preparation; implementing this new candidate and its focused correctness checks
is the next approval. No benchmark budget, stress run, full-suite rerun or real
recovery is authorized by preparation. All later performance/full-regression
gates and separately authorized staging/clean-commit requirements remain.

Preparation changes only the new proposal and these three existing context
documents, bringing the intentional dirty scope from nine files to ten. Source,
old approvals/proposals and completed/failed evidence remain preserved. Two
preparation interruptions were separately cleared: a wrong source path, then
an unavailable external documentation page. Neither was a failed test or
diagnostic. The proposal uses already retrieved sources; the page was not retried.
Preparation bindings and before-context copies are under
`data/outputs/t/ebsx_plan_fa730bcb6d2e/`.

The real error breakdown remains pending. No real-root traversal or scientific
body read/hash occurs in this preparation. All nine embargoes, three sealed
holdouts and eighteen completed clip reviews remain protected. No manual command
is pending. Stop on any new failure; no automatic repair or retry.

## Prior checkpoint: scanner timing gate failed; synthetic diagnosis proposed

Branch remains `codex/ball-detector-baseline`, HEAD
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`, with an empty index. Ryan approved
the first recovery proposal with "yes I do move forward"; its separate approval
record supersedes its frozen draft wording. The recovery-only ordinary-stat
scanner and 20 focused tests were implemented. All 20 tests passed, zero skipped.
The recorder initially failed to parse Windows CRLF line endings. With separate
permission, `scanner_focused_reconciliation.json` accepted the unchanged saved
log after 13 parser checks; the tests were not rerun. Preserve the original
failed recorder receipt and successful reconciliation.

The approved static readiness benchmark ran once on its fixed 12,000-file,
400-directory fabricated tree. The first call raised the existing accounting-
deadline error, returned no total, and was measured at `0.4908125000074506`
seconds. The requirement was less than 0.40 seconds for each of 30 calls.
Work stopped after that first call. No dynamic gate, full-suite rerun, recovery
runner implementation or real recovery dispatch followed. Correctness passed;
the candidate did not pass performance readiness. No slow phase, speedup or
performance on the real tree was established by this observation.

Evidence is under
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_recovery_implementation/fa730bcb6d2e_2026-10-04/`.
The failed `static_receipt.json` SHA-256 is
`f7f12382fa600f1e05d9aaf160e7aec2e064492865d30fce23c035afe4e9e3f2`.
The scanner uses a monotonic clock for its deadline; the wrapper used a
performance counter. No saved internal readings establish why their observed
values differ. Neither clock nor threshold was changed.

Ryan then authorized inspection of the saved result and a revised proposal
with "yes you may". Independent review confirmed the nine bound files and
the fabricated layout/reference. Metadata preparation verified all 5,774 real
files/189 directories, all 12,000 fabricated files/400 directories, 151 original
source/test/dependency bindings and three helpers. No scientific bodies were
read or hashed, and no scanner was called during that investigation.

The new draft is
`../ball_crop_candidate_retention_error_breakdown_scan_diagnosis_proposal.md`.
It proposes one supervised synthetic profile of the unchanged scanner on the
preserved fabricated tree. Profiling measures function calls and time but adds
overhead; its result cannot pass readiness or unlock real execution. A captured
known deadline would remain an explicit diagnostic observation. Any later
scanner design and execution need their own concrete authority. Pure batched
directory sizes are not accepted as a fresh-stat substitute because documented
NTFS size staleness could understate growing files.

Preparation evidence and before-context copies are under
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_scan_diagnosis_proposal/fa730bcb6d2e_2026-10-04/`.
The preparation receipt SHA-256 is
`e7b8e01b920c25dea4ed3ff7d671aad82f8e46ac1c223e93d5436af57c518ba3`.
The eight intended dirty files comprise the existing proposal, approval, scanner,
test and three context files, plus the new diagnosis proposal. No Git mutation
was performed. The old proposal, approval, scanner/tests and all failure evidence
remain unchanged. The real journal and remaining balances below are preserved.

Next: review the new synthetic diagnosis scope with Ryan before implementing
its helper or running the profile. No command is pending. Do not repeat any of
the eighteen completed clip reviews, old tests or experiments. The original
scientific approval remains valid, all embargoes and sealed holdouts remain in
force, and the saved error breakdown remains unproduced. Stop on any new failure.

## Prior checkpoint: error-breakdown execution stopped; recovery proposal prepared

Ryan separately authorized staging and committing the eleven tested files.
Commit `fa730bcb6d2e6d396391191c0fb3e36a3a338bf1` on
`codex/ball-detector-baseline` has parent
`e71a4d2165623208d624c4839e9321bd9bf779ba`. The exact committed hashes, clean
checkout and empty index were verified before real execution. Nothing was pushed.
The earlier handoff ignore-check and independent-check interpreter errors were
separately corrected with permission; neither was a test or scientific failure.

The approved public error-breakdown command ran once and failed. Attempt
`4adfb390f1f74a1baaec7fb178092218` consumed `7.264999999984866` active seconds;
the command took 41.266 wall seconds. The resource monitor reported
`Output tree did not stabilize for complete byte accounting`. Work stopped
without repair or retry. Its worker log is empty, its result file and diagnostic
output directory are absent, and no verified summary was returned. The records
do not establish the worker's internal interruption point or whether it reached
a scientific input. Parent investigation read no scientific bodies.

Ryan authorized read-only investigation, then preparation of the concrete draft
`../ball_crop_candidate_retention_error_breakdown_recovery_proposal.md` with
"move forward with the recovery proposal". The scanner's one half-second deadline
can fail on slow complete scans as well as membership changes; the exact trigger
is unresolved. The draft proposes a recovery-only ordinary `os.stat` lookup
without repeated `Path` construction, preserving all counting rules and live
limits. Its performance is unproved. Fixed fabricated correctness/timing gates
must pass before one newly authorized recovery attempt at a clean tested commit.
No recovery implementation, benchmark or retry has run or is approved.

The full 3,010-event chain is verified: 58 closed attempts, 54 successes, four
preserved failures and no open attempt. Tip:
`e5f2a832dd961d2615daa30ca77b039ad8dbe68bcbcfa12c2437128fbc83a3b3`.
Cumulative usage is `3267.507999999987` seconds; remaining cumulative allowance
is `11132.492000000013`. The original diagnostic's 300 seconds would cover both
attempts, leaving `292.73500000001513` seconds for recovery, not a fresh budget.
The supervisor lock is absent. Final accounting succeeded after termination;
that does not convert the failed attempt into success.

Execution receipts remain under
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_implementation/e71a4d216562_2026-10-02/`.
Proposal preparation evidence and before-context copies are under
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_recovery_proposal/fa730bcb6d2e_2026-10-04/`.
All 5,762 original evidence files match frozen metadata; the current inventory
has 5,774 files and 189 directories, including the new failure. This is metadata
preservation, not a new scientific-content audit. All 151 source/test/dependency
bindings and three earlier helper bindings are unchanged. The prior 46 focused
passes and 803 full-suite passes plus one Windows skip were not repeated.

The proposal and three context updates are intentionally unstaged; index empty.
HEAD remains `fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`. Next: Ryan reviews the
specific operational recovery proposal. Original scientific approval and all
eighteen completed clip reviews remain valid; no repeat review is requested.
All embargoes, holdouts, original authorities and resource limits are preserved.
Do not invoke the old runner or dry-run: both reject the changed failure prefix.
No manual command is pending. Stop on any new failure; Git steps remain separate.

## Prior checkpoint: saved error-breakdown implementation validated; Git authorization next

Ryan approved the exact new scope with "Yes I permit. Move forward". The separate
approval receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_error_breakdown_approval_v0_1.json`,
SHA-256 `f0eb74cde6077a5741c46ebe1aa1f8633ed2ac031f8b3a5f493d417ca9a2a0cf`.
The frozen proposal SHA-256 is
`f8525927fa5589b7c5a70aef6fee9bcc813365e267503eaa4f6610438802deee`;
its draft wording is superseded by this separate receipt, not edited in place.
Scientific-scope approval need not be requested again.

Two new modules implement a separate supervised reader and pure formatter for
the existing error breakdown. Independent source review passed, including
fabricated child-process supervision, deterministic window mapping, exact
authority guards, per-row saved-list counts, create-only outputs and rejection
of partial or tampered results. All prior implementation files remain unchanged.
The new validation recorder passed twelve fabricated checks and parsed the
exact preserved 758-test log without rerunning that old suite. It handles the
known buffered diagnostic suffix while requiring the exact successful result.

All 46 focused tests (35 runner, 11 formatter) passed in 72.28 unittest seconds
(72.625 seconds of command wall time), with zero skips. Source/helper/recorder
bindings stayed unchanged. The actual metadata-only dry-run passed in 15.047
seconds without scientific-body access, worker dispatch or journal changes.
The full suite completed successfully: 804 run, 803 passed and one existing
Windows directory-symlink capability skip. Unittest time was 2,040.214 seconds;
command wall time was 2,044.594 seconds. All 151 source/test/dependency bindings
and three prior helper bindings remained unchanged. The new manifest binds the
completed `implementation_validation.json` certificate, SHA-256
`c252a3015acd0cc037ac084db8f6a09589f0d41a23d28e2d18312b0be58ca233`.
No real diagnostic worker has started and no scientific bodies have been read
for this implementation and validation. See
`../ball_crop_candidate_retention_error_breakdown_implementation.md` for the
eleven-file scope, approval and validation details. Evidence is under
`data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_implementation/e71a4d216562_2026-10-02/`.

Branch remains `codex/ball-detector-baseline`, HEAD
`e71a4d2165623208d624c4839e9321bd9bf779ba`. The implementation/documentation scope
is intentionally unstaged; the index remains empty. Stop on any new failure.
Obtain separate Git authorization before the approved real
unit can execute at a clean tested checkpoint. Do not request prior clip reviews
or scope approval again. All embargoes, sealed holdouts, completed evidence and
original resource limits remain intact.

## Prior checkpoint: interpretation complete; error-breakdown proposal prepared

Ryan authorized staging and committing the exact thirteen-file interpretation
scope with "Yea move forward chat" in response to the concrete Git request.
The commit is `e71a4d2165623208d624c4839e9321bd9bf779ba` on
`codex/ball-detector-baseline`, parent `a89cd40838b066c1d2fe3cb1f257dda10e80a3bb`.
The exact committed scope, clean worktree and empty index were verified before
the already-approved interpretation ran. Nothing was pushed.

The one `post-review-interpretation:summary:` worker succeeded, attempt
`7bd613d71cef48d38c15a72e9647fc10`, in 40.14 active seconds. Its verified bounded
summary was returned and explained to Ryan. The completion checkpoint is
`data/outputs/ball_tracking/crop_candidate_retention_interpretation_implementation/a89cd40838b0_2026-10-02/interpretation_completion_checkpoint.json`,
SHA-256 `c6e55a921c44bd6dfa29b291dd753fb80b72637ecc86ba035802210f5bb80bf5`.
The readable result is
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit/post_review_interpretation_v0_1/summary.md`,
SHA-256 from the successful result receipt
`590f2ed1ff1159f381bbae078dce5e5850b494aad6cf93d54e59d4af429461e9`.
Do not rerun the finished unit or reopen scientific bodies in the parent.

At the fixed .01/10px comparison, removing the cap gained no localization
matches under any of the four settings in either pool. Some settings lost a
match; all challenge settings produced more false observations. Some looser
radii had gains with extra errors. These are development observations, not a
tracker selection or passed quality gate. Localization is not certified object
identity, and five hidden frames from one episode cannot establish robust
hidden-ball behavior. See the returned summary for the balanced full account.

The original resource journal now has 3,002 events and 57 completed attempts:
54 successes, the same three preserved failures and no active worker. Its final
event digest is `6c0924cc29f4bdf6b7d6e9311b3fc8205baf8ad0ab251a31ae2bb056a45e1f6c`.
Recorded cumulative active time is 3,260.243 seconds, leaving 11,139.757 seconds
(both rounded here). This is available processing allowance, not a completion
estimate or chat-usage balance. All earlier evidence and resource limits remain
preserved; preservation used frozen metadata and receipt bindings, not a fresh
parent content audit. All eighteen requested clip reviews remain complete.

Ryan asked to move forward. The next preparation confirmed from source that
the completed scoring files already contain an ordered error breakdown. The
concrete draft is `../ball_crop_candidate_retention_error_breakdown_proposal.md`:
one bounded reading of two saved pool files and the passed audit, covering all
six windows/four settings/both cap policies at .01/10px. It distinguishes missing
near-reference candidates, filtering, cap removal and path-selection misses
without new scoring or individual object-identity judgments. Window mapping
uses saved companion window IDs, not an assumed possession order.

A read-only preparation command incorrectly requested `resource_events.jsonl`
and returned an error. Work stopped without edits or a new worker. Ryan then
authorized the corrected metadata check and documentation-only proposal with
"You can move forward chat". The corrected `resource_events/` check passed:
3,002 files and the expected successful final event. No experimental failure,
retry, journal mutation or scientific-body access occurred during preparation.

Current changes are limited to the new draft and current-state, roadmap and
validation-history documentation, intentionally unstaged with an empty index.
No implementation or new diagnostic worker has started. No manual command is
pending. First next action: review this concrete new scientific-reading scope
with Ryan for approval before implementation; future Git mutations require
separate authorization. No method, setting, quality gate, training, new clip
review or holdout release is selected. Ball tracking remains the active phase;
possession understanding, matchup inference and defensive scoring come later.

## Prior checkpoint: interpretation validation complete; separate Git authorization next

Ryan approved `../ball_crop_candidate_retention_interpretation_proposal.md` with
"I approve chat, and can you please give me a status update on where we’re at,
and how close we are to finishing this stage". The separate approval record is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_interpretation_approval_v0_1.json`,
SHA-256 `c485620816810e6d035fb019d4a466a0e73038d4a2f1cab4ea049277d6420ca3`.
The exact approved proposal remains frozen at SHA-256
`e01da501500e359fd3f27d27aa6647f9a444022eb7e7eb2a647a473f350013a3`.
Its historical draft wording is superseded by the separate approval receipt.

The new implementation prepares one supervised reading of the already audited
guide and audit, followed by a bounded descriptive summary. It preserves both
pools, all four settings, gains, regressions and missingness without new scoring,
aggregation, model calls or video access. Its tighter 1,800-second reservation
uses the original cumulative journal and unchanged supervisor. See
`../ball_crop_candidate_retention_interpretation_implementation.md`.

All 42 focused fabricated-fixture tests pass, including a genuine supervised
synthetic child and bounded receipt-verified summary return. Independent source
review is clear. The full unittest subprocess exited zero after 758 tests in
1,846.555 seconds: 757 passed and the existing Windows directory-symlink test
was skipped. All 147 source/test/dependency bindings and three preserved helper
sources remained unchanged.

The separate validation recorder stopped with exit one. It expected the last
log line to be the unittest status, but two buffered diagnostic lines appeared
after `OK (skipped=1)`: `Saved context: context.jpg` and
`Saved identities: identities.jpg`. Its `full_suite_receipt.json` therefore
truthfully remains `passed: false`; the original receipt and log are preserved.
Work stopped under Ryan's stop-on-new-failure instruction. Ryan subsequently
approved the narrow correction with "Ok move forward chat". A new ignored
reconciler passed 12 focused synthetic checks and independent review. It verified
the exact original test commands, counts, durations, exit codes, known skip,
two trailing diagnostics and unchanged source bindings. The original failed
receipt, logs, scripts and historical review records remain unchanged. The full
suite was not rerun.

The separate reconciliation SHA-256 is
`d9bf5e6e330f4153657eb1beccdaf58adb85dbcb0afbc684ecf35c7df6bc45a5`.
The completed implementation certificate SHA-256 is
`fd18eb13f5b9d88251b21b47282e82cba3c17226d602482a8faa180c686424cf`.
Both are under the interpretation implementation directory, and the manifest
now binds that certificate. The code is ready for separately authorized staging
and committing of the thirteen files listed in the implementation note.

No real interpretation worker has run, and the completed prefix remains
2,966 events and 56 attempts, including
three preserved failures. The branch remains `codex/ball-detector-baseline` at
`a89cd40838b066c1d2fe3cb1f257dda10e80a3bb`. New implementation and closeout files
are intentionally unstaged; the index is empty. Staging and committing require
separate explicit authorization before execution at a clean tested checkpoint.
All eighteen prior clip reviews remain complete; no repeat review is requested.

Ryan requested fuller explanations after each completed task: explain what
changed, why it mattered, how it was checked and what it means for the project.
Use simple language, define unfamiliar terms and do not assume prior Python,
computer-vision, machine-learning or Git workflow knowledge.

## Prior checkpoint: publication recovery and six-clip human review complete

The approved candidate-retention comparison has completed selection, scoring,
review publication and its independent completion audit. Ryan approved the six
new clips in response to the requested final-frame review: "I approve and have
reviewed everything’s looking pretty good. Move forward chat". The separate
receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_visual_review_record_v0_1.json`,
SHA-256 `9a3089a14747dce7b95670838dd116b2ddaf6cd426837f93435ff6ad6706d46b`.
It records package completion and approval without invented individual frame
verdicts, new identity labels or a selected method or quality gate. Do not
request these six reviews or the twelve earlier YOLO reviews again.

Branch is `codex/ball-detector-baseline`; HEAD is
`a89cd40838b066c1d2fe3cb1f257dda10e80a3bb`. Publication recovery has its own
execution provenance. Preserved selections remain attributed to
`0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41`, scoring to
`f36237247191e726ad7e81bdc6651f9340a9063d`, and original rendering to
`cd51bfc1336bba76e4b118b6cfe55d7f74a3b5a6`. Five windows had successful render
receipts; the sixth had been published before its renderer failed. Ryan approved
the bounded amendment that independently validates that exact sixth publication
and records a new acceptance without rewriting the failed attempt. No selector,
scorer or renderer was replayed.

All six new supervised workers passed: verification, recovery preflight,
sixth-window acceptance, global finalization, independent completion audit and
review-guide creation. The journal now has 2,966 events and 56 completed attempts:
53 successes and the same three preserved failures, with zero active attempts.
Its chain tip is
`018a97a3075f46698e215c3f6e8e95cab7cbab4f926e9bad68dbbd25d6c0640e`.
Recorded active-worker time is 3,220.103 seconds, leaving 11,179.897 seconds under
the original budget. This is an allowance for active work; idle time and human
discussion do not consume it. All original limits and partial evidence remain
preserved. The completion checkpoint is
`data/outputs/ball_tracking/crop_candidate_retention_publication_recovery_implementation/cd51bfc1336b_2026-10-02/recovery_completion_checkpoint.json`,
SHA-256 `03ddbd6151b3827afaf98070a5c8ed745f9ccd05b582b84d0c23ab8f0417e7d0`.
The review receipt binds the acceptance, independent audit, global manifest,
guide and successful resource receipts. Generated review manifests and guides
retain their historical pending-human-review snapshots; the later human receipt
establishes completion.

Validation passed 38 runner tests and 13 helper tests. The full suite ran 716
tests in 1,873.376 seconds: 715 passed and one existing Windows directory-symlink
test was skipped. All 143 source/test/dependency files and three helper sources
remain unchanged. Implementation certificates and scientific outputs are frozen.
This documentation closeout reruns no test, scientific work or media decode and
draws no quantitative cap-retention conclusion from unread results.

See `../ball_crop_candidate_retention_closeout.md` for the completed review record
and `../ball_crop_candidate_retention_interpretation_proposal.md` for the next
concrete draft. Next review that scope for approval: one supervised worker would
read the existing audited guide and audit to explain the saved comparison, with
representative and challenge pools separate. That interpretation has not run.
The project remains in the ball-tracking foundation phase; possession
understanding, matchup inference, defensive scoring and full-game validation
remain later work. No method, operating point, quality gate, training, holdout
release or certified object identity is selected. The nine original prediction
embargoes and three sealed holdouts remain intact.

The closeout documents and review receipt are intentionally unstaged; the index
is empty. No Git mutation is authorized by this review response or has occurred
during the closeout. Staging, committing and subsequent Git steps remain separate
authorization decisions. No manual command is pending and no worker is active.

## Prior checkpoint: rendering recovery approved and implemented; regression validation passed

Ryan approved the bounded rendering recovery with "I approve, move forward chat".
The exact approval is recorded in
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_render_recovery_approval_v0_1.json`,
SHA-256 `133981a85b191e931e739ad0c3030659072282665db0dd5cb234716fb52f71f6`.
It binds `docs/ball_crop_candidate_retention_render_recovery_proposal.md`,
SHA-256 `2d9ea51ca4f93fbc77d902266dcbf1ef496edcb8c320c7a0dbbe6d86bf884b48`.
The earlier proposal remains frozen; its draft wording is superseded by this
approval receipt. Staging, committing, pushing, PR creation and merging remain
separate authorization steps.

The implementation adds a runner restricted to verification and rendering,
an explicit saved-score loader bridge, and the approved monotone-additions
measurement rule. Original selections and completed scores keep their original
commits/specifications. Both failures, all partial files, the 1,170-event history
and existing budget remain preserved. No real recovery worker has run.

Individual focused checks passed: 44 resource tests and 26 rendering-recovery
tests. Independent static reviews passed, including the separately prepared
completion-audit helper. The actual metadata-only dry-run passed. All 145
combined retention tests passed in 198.604 seconds; all 140 source/test/dependency
bindings stayed unchanged. The full suite completed 665 tests in 1,882.854 seconds:
664 passed and one existing Windows directory-symlink test was skipped. Its 140
source/test/dependency bindings also stayed unchanged. Independent certificate
guard review passed. The final certificate SHA-256 is
`652a8bb8926ea21be2e1863e34105b1c737986e46c5615a342e682be497644dc`;
it binds 140 source/test/dependency files and 27 evidence artifacts. Evidence is under
`data/outputs/ball_tracking/crop_candidate_retention_render_recovery_implementation/f36237247191_2026-10-02/`.
The validated source/test bytes remain frozen.

Branch remains `codex/ball-detector-baseline`, HEAD
`f36237247191e726ad7e81bdc6651f9340a9063d`. Changes are unstaged; the index is empty.
The final recovery specification is
`326ba1cec475aa32d172a76a2ea760ceffb3e9188631c16ed2b1af5914fab3cd`;
its metadata-only dry-run passed without worker dispatch. The exact 14-file scope
is listed in `../ball_crop_candidate_retention_render_recovery_implementation.md`.
Next obtain explicit staging authorization for that scope, then separate
commit authorization before the already approved real recovery. Do not request
scientific-scope approval again. All nine embargoes and three sealed holdouts
remain protected; no method, operating point, quality gate or training is chosen.
The twelve prior YOLO reviews remain complete. Six new retention clips and the
full comparison audit remain outstanding.

## Prior checkpoint: scoring complete; rendering interrupted and recovery proposed

Ryan separately authorized staging and committing the exact 15-file recovery
scope at `f36237247191e726ad7e81bdc6651f9340a9063d`. Execution began from that
clean checkpoint on `codex/ball-detector-baseline`. Recovery verification
succeeded, then all eight scoring-stage workers succeeded: six window JSON
files and two separated pool files are complete, with 120 new localization
reports and 630 saved reports. The original 24 selections were reused.

Rendering preflight passed, but the first rendering worker,
`158f51be5ab34cdface57f4e0036b7d2`, failed with
`Output tree did not stabilize for complete byte accounting`. Ten partial PNGs
totaling 32,989,248 bytes remain. No completed clip, global review manifest or
full comparison-completion audit exists. Scoring completion does not establish
tracking quality; all six new clips still need generation and human review.

The supervised read-only forensic audit succeeded. Under
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/`,
its receipt `audit/render_interruption_f362.json` has SHA-256
`f2bece32af228b0f525b07eb060b1671194812b26af7787283c8ecca2aabea8b`,
and checkpoint `audit/render_interruption_checkpoint_f362.json` has SHA-256
`8dce571305282e59dc61e3ceb610e2ea0e5dbd86ce1896beb9e035c8ee12dcac`.
Diagnosis attempt `8e121d23c2494d969df9af94cc45bbeb` consumed 9.812 seconds.
The preserved journal now contains 1,170 events and 41 completed attempts:
39 successful and two failed. Cumulative real time is 1,136.756 seconds, leaving
13,263.244 seconds; both failures and all partial outputs remain charged and
preserved. This forensic verification is not the unexecuted comparison audit.

See `../ball_crop_candidate_retention_render_interruption.md` for the exact
evidence and `../ball_crop_candidate_retention_render_recovery_proposal.md`
for the new draft. Synthetic reproduction showed that creating new files can
prevent the current monitor from finding equal membership in two complete
scans; it supports, but does not prove, that mechanism in the real failure.
The proposal would permit only monotone membership additions within the same
two-complete-scan, half-second contract and unchanged resource budgets. It
would reuse the exact original selections and completed scores, then render
only the six approved clips. No reranking or rescoring is proposed.

This measurement rule and the new renderer-provenance transition require
explicit review of the revised execution contract. The render-only amendment
is a draft; implementation and retry are not approved. The original scientific
scope remains unchanged. All 137 production/test/requirements hashes are
unchanged; the 107 focused passes and full-suite 626 passes plus one existing
Windows skip remain valid for the committed implementation. A later approved
amendment would require its own focused/full validation, independent review,
certificate and clean, separately authorized commit.

HEAD remains `f36237247191e726ad7e81bdc6651f9340a9063d`; this preparation changes
five documentation files only, unstaged with an empty index. Next is review
and explicit approval of the concrete render-only proposal. All nine original
prediction embargoes and three sealed holdouts remain protected. Ryan's prior
twelve YOLO final-frame approvals remain complete. No method, operating point,
quality gate, training or certified identity labels are selected. No manual
command is pending; no rendering retry is running.

## Prior checkpoint: retention recovery validated; staging unapproved

Ryan approved the bounded recovery with "I approve chat. Please move forward".
The separate receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_recovery_approval_v0_1.json`.
The recovery proposal retains its original bytes and historical draft wording;
its SHA-256 is `c066bc43b204a09a05e2912589cbc173614cecbe563431ebbeed75c42db3de48`.
The receipt supplies current scope authorization. The original scientific
comparison approval remains valid and does not need to be requested again.

The implementation permits verification, scoring and rendering using the 24
completed selections. It corrects accounting of continuously growing files,
preserves all resource limits and consumed budgets, and requires exact old
selection receipts while recording new evaluation/rendering provenance.
The ordinary runner remains strict. Selection, candidate coordinates,
confidence, annotations and matching mathematics are unchanged. Published
outputs without successful completion receipts cannot be adopted.
See `../ball_crop_candidate_retention_recovery_implementation.md` for details
and the exact intended 15-file staging scope.

The preserved inventory has SHA-256
`5a05c6644196f7fd0dfb731c538f68077039f74265d62e7b95f3dbbe00b92739` and binds
24 selection manifests, 600 trace hashes and all 697 resource events across
29 completed attempts. A supervised read-only preparation worker consumed
1.75 seconds, making the recorded real-run balance 621.943 seconds consumed
and 13,778.057 seconds remaining. The original failure and partial JSON remain
in place. This balance is historical; the persistent journal is authoritative.

The combined focused run passed all 107 tests in 101.25 seconds. All 137
production/test/requirements hashes were unchanged across focused validation,
the initial full run and the successful retry. Independent static review passed.
The final full suite passed: 627 tests ran, with 626 passes and one existing
Windows directory-symlink capability skip, no failures or errors, in 1,824.921
seconds of command wall time. The first full suite had failed:
627 tests ran, with 621 passes, five errors and one existing skip. All five
errors occurred during initial `git add` in older `ReleaseMetadataTests`
temporary fixture repositories. Independent reproduction confirmed Windows Git
reported `Filename too long` under the deep validation TEMP path. No production
or test code changed. All 14 tests in the affected module then passed in
40.031 seconds using the short ignored TEMP root `data/outputs/t/crr_setup_short`.
The successful full-suite retry used a short TEMP path. Synthetic validation
evidence is under
`data/outputs/ball_tracking/crop_candidate_retention_recovery_implementation/0a7f5bc69be9_2026-10-02/`.
The failed `full_final.log` and receipt remain preserved; `full_short.log` and
`full_short_receipt.json` record the successful retry. The failed run's raw log
records one skip; its original receipt incorrectly says zero because its old
parser handled only `OK` summaries. Neither original evidence file was rewritten.

The final `implementation_validation.json` certificate binds all 137 validated
production/test/requirements files and the validation evidence. Its SHA-256 is
`71f75c979c5c754c7387df859e885b4a48be1b43fcfc62f683d76a7bc14fc8bc`.
The recovery manifest now binds that certificate and has file SHA-256
`2e1a57cfdacfa0359f328d467fd75b513b81fde192f69e4bd2a9919dbb7a6e1f`.
The actual dirty-checkout guard rejected recovery dispatch before a worker
started or the journal changed. The recovery runner has not executed a real
stage: scoring and rendering remain incomplete, and no comparison-quality
conclusion or completed comparison audit is available.

Branch remains `codex/ball-detector-baseline` at
`0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41`; the 15-file scope is unstaged and
the index empty. Next: obtain separate authorization to stage those exact
15 files, then separate commit authorization. Already approved recovery execution
requires that clean tested commit; no repeat scope approval is needed.
All nine original prediction embargoes and three sealed holdouts remain
protected. Ryan's twelve YOLO final-frame approvals remain complete. The six
new retention clips still require generation and final-frame human review.
No method, operating point, quality gate, training or certified identity labels
are selected. No manual command is pending.

## Prior checkpoint: retention selection complete; scoring interrupted

Ryan separately authorized staging and committing the exact 24-file retention
implementation scope. The approved real comparison began from the clean tested
commit `0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41` on
`codex/ball-detector-baseline`. All 24 selection units completed, using 25
successful workers including selection preflight. Scoring preflight also
completed. The first scoring window then failed with
`ResourceLimitError: Output tree did not stabilize for complete byte accounting`.
At the scoring failure there were 26 successful workers and one failed worker.
No retry or rendering followed; no successful scoring reports, aggregate pools or six-clip review
package exist. The prepared completion audit was never executed.

The resource journal records 618.1929999999993 cumulative active seconds,
279,302,144 peak worker-tree resident bytes, 881,741,466 maximum sampled output
bytes and a .469-second maximum monitoring interval, with no recorded
overshoots. The monitor requires two identical size/mtime inventories while
the scorer writes JSON continuously; the saved partial write is consistent
with that stability-check conflict. This is an interrupted comparison, not an
accuracy result or a completed independent audit.

See `../ball_crop_candidate_retention_interruption.md` for the failed attempt,
exact completion-event hash and retained partial file. All completed outputs,
failure evidence and consumed budgets are preserved under
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/`.
The limited forensic audit passed and is bound by
`audit/interruption_receipt.json`, SHA-256
`0f90a59c07dd2436ef8618ffd8d3637695b99ab3e56e08f879866d9d702e40df`.
It verified selection manifests/canonical content, 600 compressed trace hashes,
the failure-prefix resource history, source/input/control bindings and embargo
absence; it read only holdout metadata. It did not decompress traces or rerun
selection/scoring/rendering. Its 2.0-second supervised worker brings the total
to 27 successful workers and one failure, 620.193 active seconds consumed and
13,779.807 seconds remaining. Maximum sampled output is now 882,157,412 bytes;
peak memory and maximum monitoring interval are unchanged. This limited audit
does not substitute for the unexecuted comparison-completion audit. Next is
review and approval of the bounded recovery proposal at
`../ball_crop_candidate_retention_recovery_proposal.md`; no monitor change or
recovery execution has occurred. The original scientific approval remains valid;
the proposed live-write accounting and cross-commit reuse amend the execution
contract under the frozen proposal's revised-explicit-scope boundary.

The following historical checkpoints retain their original statuses. Current
tracked changes are documentation only and remain unstaged; the index is empty.
All nine original prediction embargoes and three sealed holdouts remain in force.
Ryan's twelve prior YOLO final-frame approvals remain complete. The six new
retention clips still require generation and final-frame human review after
successful recovery. No method, operating point, quality gate or training is
selected or authorized; localization outcomes are not certified identity labels.
No manual command is pending. Further Git steps require separate authorization.

## Prior checkpoint: retention implementation validated; staging unapproved

Ryan approved the exact retention comparison on October 2, 2026 with
"I approve. Please move forward chat". The separate receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_approval_v0_1.json`.
The frozen proposal/design keep their historical draft text and exact hashes;
the new receipt authorizes implementation and later execution within that scope.
Training, method/operating-point/quality selection and every Git step remain
unauthorized. The proposal's clean tested commit prerequisite still applies.

Five new modules and five synthetic test files implement cap removal throughout
the causal history, lossless full traces, immutable saved-control reuse,
ordered scoring comparisons, saved-PNG review and persistent resource bounds.
See `../ball_crop_candidate_retention_implementation.md` for the concrete scope.
Read-only candidate preflight passed for six inputs, 126 saved controls and
48 higher-confidence equivalence records. No real selection, scoring, rendering,
model inference or training has run. The real experiment root remains absent.

All 78 focused synthetic tests and both final 400-candidate/25-frame stress
fixtures pass. The dense fixture saved and decoded 31,840,000 edges in 491.578
seconds, peaking at 1,280,413,696 worker-tree resident bytes. The sparse fixture
saved 112,280 edges in 10.266 seconds, peaking at 74,559,488 bytes. Neither
crossed a resource bound; these costs do not consume the future real-run budget.
The full regression suite passed: 598 tests ran, with 597 passes and one
existing Windows directory-symlink capability skip, in 1,638.766 seconds.
All 134 production/test/requirements files were unchanged during validation.
Evidence is under
`data/outputs/ball_tracking/crop_candidate_retention_implementation/9fe6a1ef86d2_2026-10-02/`.
Only fabricated candidates and pixels are used for execution validation.
Independent preservation checks passed for 755 unique files; all eight prior
non-context working files retain their exact hashes. The runner's actual
dirty-checkout guard was exercised without starting a real worker.
The completed certificate binds all production/test Python and requirements
bytes, the full-suite log, and complete benchmark/resource receipts. Its
SHA-256 is `135bb50a461eec662f70ed4c64d15fe15e36826eefe81ee21e7521f36578890f`;
the executable manifest now binds it. All 755 preservation bindings were
reverified after the full suite. Both independent preservation and synthetic
benchmark audits passed. The real experiment root remains absent.

Branch remains `codex/ball-detector-baseline`, HEAD
`9fe6a1ef86d23391c64b7d5b16198ad7bb005c25`; index empty. The implementation is
unstaged in an exact 24-file scope listed in the implementation note. All nine
original embargo paths remain absent and all three holdouts
sealed. Ryan's prior twelve YOLO final-frame approvals remain complete.
Next: obtain separate authorization to stage those 24 files; committing remains
a subsequent, separate authorization. Real execution needs that clean tested
commit, but its scope approval is already recorded and should not be requested
again. No manual command is pending. The final checkpoint receipt records
exact working hashes, validation evidence and the empty index for resumption.

## Prior checkpoint: bounded candidate-retention comparison drafted

On October 2, 2026, Ryan said "Move forward chat" after the completed
saved-evidence diagnostic. This turn prepares the next concrete design:
`../ball_crop_candidate_retention_proposal.md` and
`configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_retention_v0_1.json`.
They are non-executable and await scope review; no implementation, new
selection/scoring, inference, training or rendering occurred in preparation.

The proposed change removes only the twenty-candidate cap from all four
unchanged no-context motion scorers at the existing .01 floor, across all six
development windows. It requires 24 new window outputs and 120 reports if
later approved. At .20/.35, stored candidates never exceed nine/seven per
frame, so the corresponding 48 graph settings are structural-equivalence
references to existing cap20 results; they must not be rerun or relabeled as
new execution. The proposal reuses 126 existing control outputs and 630 reports.
Six new .01 paired clips would need final-frame review after execution;
completed .20/.35 motion review and all twelve YOLO approvals remain complete.

The saved inventory has 47,198 candidates, at most 400/frame and 1,924 in a
five-frame horizon. Explicit resource limits and synthetic stress validation
are required; no silent truncation or partial-comparison claim is allowed.
The design separates confidence filtering, cap retention, final path choice,
uncertified identity and center placement. Candidate burden, false alarms,
missingness, gains and regressions stay explicit, with pools separate.
Player-context and YOLO methods are outside this conditional mechanism test;
no method, operating point, quality gate or training labels are selected.

Preparation evidence and source inventories are under
`data/outputs/ball_tracking/crop_candidate_retention_proposal/9fe6a1ef86d2_2026-10-02/`.
Use `independent_proposal_audit_v2.json` and `final_preparation_receipt.json`
for the final draft. The earlier receipt precedes the explicit aggregate-alias
deduplication clarification; that prior draft is retained as a snapshot.
The prior diagnostic, source/test bytes, approved proposal and receipts remain
unchanged. Its relevant validation remains 28 focused passes and 519 full-suite
passes with one existing Windows skip. Documentation/source-inventory checks
replace any need to repeat that suite for this preparation.

Branch remains `codex/ball-detector-baseline` at
`9fe6a1ef86d23391c64b7d5b16198ad7bb005c25`. Eleven intentional files are now
unstaged; index empty. This turn adds two proposal files and updates only this
checkpoint and `roadmap.md`. All nine embargo paths remain absent and all
three holdouts sealed. No Git mutation occurred. No manual command is pending.
Next: review the exact retention-comparison scope before implementation or
execution; staging, committing, pushing, PR creation and merging each require
separate explicit authorization.

## Prior checkpoint: approved saved-evidence diagnostic complete

On October 2, 2026, Ryan replied "mover forward chat" to the concrete bounded
diagnostic proposal. The separate approval is
`configs/ball_tracking/reviews/saved_candidate_retention_localization_approval_v0_1.json`.
The original proposal and design retain their exact bytes and historical draft
status; the receipt authorizes implementation and execution of this diagnostic.
It does not authorize a new tracking experiment, training or any Git step.

The helper `src/ball_tracking/candidate_retention_diagnostic.py` and its 28
focused synthetic tests are complete. The full suite ran 520 tests: 519 passed
and one existing Windows directory-symlink capability test was skipped.
Exact tested helper/test bytes were unchanged during execution.

The approved diagnostic ran once, successfully, into the fresh ignored
directory `data/outputs/ball_tracking/candidate_retention_localization_diagnostic/v0_1_9fe6a1ef86d2/`.
Its `case_ledger.json`, `summary.md` and `integrity.json` preserve 32 frames,
82 candidates, 640 saved display outcomes and 15 cap records. An independent
audit verified all original payloads, 1,060 same-detector candidate-setting
records, residual arithmetic and hashes. All 231 original assets and 177 input
bindings remain unchanged. All fifteen cap-membership bindings were available
and verified: eight rejected and seven retained the saved floor-match candidate.

Fifteen of twenty persistent display misses have RF floor matches rejected by
both display confidence thresholds. Eight of those fifteen are separately lost
at .01/top-twenty; these counts overlap. Choice, identity and center placement
remain distinct. All 82 certified identities remain null and ineligible for
training. Five hidden frames retain null geometry/residuals. Reference distances
are descriptive arithmetic, not new matches or ball/non-ball labels; 25 of the
27 eligible reference centers are partially visible amodal estimates.

Results and exact evidence links are in
`../ball_candidate_retention_localization_results.md`. Validation, execution
and independent audit receipts are under
`data/outputs/ball_tracking/candidate_retention_localization_implementation/9fe6a1ef86d2_2026-10-02/`.
No model, selector, evaluator, renderer or media decode ran in the real diagnostic.
Ryan's completed twelve-clip final-frame review and the later agent inspection
remain complete. Neither requires repetition for this saved-record diagnostic.

Branch remains `codex/ball-detector-baseline`, HEAD
`9fe6a1ef86d23391c64b7d5b16198ad7bb005c25`. Nine intentional files are unstaged;
index empty. No staging, commit, push, PR or merge occurred. All nine original
prediction embargoes remain absent and all three holdouts sealed. No method,
operating point or quality gate is selected; no upstream player review changes.
No manual command is pending. Next: use the completed diagnostic to prepare a
bounded next comparison with candidate-load, false-alarm and missingness
tradeoffs explicit. New experiment execution/training and each Git step remain
separate authorization boundaries.

## Prior checkpoint: completed inspection; retention/localization diagnostic proposed

Verified October 2, 2026 (America/Phoenix): branch
`codex/ball-detector-baseline`, HEAD
`9fe6a1ef86d23391c64b7d5b16198ad7bb005c25`, initially clean worktree and empty
index. The reviewed YOLO closeout was separately committed at this HEAD. The
later saved-candidate inspection is complete. The older staging and pending
inspection instructions below are historical; neither step should be repeated.

The full preceding handoff is
`data/outputs/ball_tracking/weak_candidate_inspection/9fe6a1ef86d2/handoff_2026-10-02.md`.
Its `findings.md`, `completion.json`, `inspection.json`,
`saved_cap_diagnosis.json` and final `review_native.html` contain the completed
agent diagnosis. All 231 assets and 177 input bindings were rehashed successfully
during this preparation; 79 saved floor/cap report pointers match their sources.
The earlier pixel-exact crop verification was not repeated. This remains agent
diagnosis, not a new human object-identity labeling pass. Ryan's twelve-clip
YOLO review through final frames is complete; do not request it again.

The new draft is `../ball_candidate_retention_localization_proposal.md`, with
non-executable specification
`configs/ball_tracking/proposals/saved_candidate_retention_localization_diagnostic_v0_1.json`.
It freezes 32 frames, 82 candidate identities, 640 saved display outcomes and
15 saved cap records. It proposes a ledger with separate retention, identity,
center-discrepancy and emission fields. Fifteen persistent display misses have
weak RF floor matches; eight lose the match in the separate saved .01 top-twenty
setting as well. Those causes must not be double-counted. MATCH/UNMATCHED does
not certify ball/non-ball identity. Proposed center residuals are descriptive
distances to reviewed references; hidden geometry stays null.

Preparation changes only this file, `roadmap.md`, the new proposal document
and its JSON. These four files are unstaged; the index remains empty and HEAD
is unchanged. No implementation, new diagnostic execution, inference, training,
selector/scorer/renderer rerun or media decode occurred. All nine original
embargo paths remain absent and three holdouts sealed. No method, operating
point or quality gate is selected. No upstream player review or pipeline stage
changes. No staging, commit, push, PR or merge occurred.

The proposal received independent read-only design review. JSON, scope, source
bindings, local links and whitespace are checked in the ignored preparation
receipt under
`data/outputs/ball_tracking/candidate_retention_localization_proposal/9fe6a1ef86d2_2026-10-02/`.
Production code is unchanged, so tests were not rerun; the existing result
remains 27 recovery-focused and 15 adapter passes, plus 491 full-suite passes
and one existing Windows capability skip. No manual command is pending.
Next: Ryan reviews the concrete diagnostic scope. Its implementation/execution
and any later tracking experiment remain unapproved; Git steps each require
separate explicit authorization.

## Prior checkpoint: YOLO recovery executed and visually approved; saved-method closeout

The separately authorized recovery commit is
`3326482e6f7e05527d146f3110c8ec39171cf08d` on `codex/ball-detector-baseline`.
Its exact seventeen tested files were verified after committing. Recovery,
scoring and rendering are complete: 175 original crops preserved, 425 missing
crops completed, zero new failures, six candidates and 162 selectors. Actual
totals are 600 unique crops, 602 project attempts/forwards including two earlier
failures, three predictor preparations and six synthetic forwards. All 561
original partial-run files retain their bytes and actual inference provenance.

There are 810 new and 810 reused RF-DETR scoring reports, 270 aggregate cells
per separate pool, twelve new clips and 1,500 PNGs with 1,200 saved references.
The independent audit checked all asset hashes, every clip through its 25th
frame at 5 fps, and sixty final images. Short playback/final-image copies are
byte-identical support duplicates. Evidence is under
`data/outputs/ball_tracking/yolo11x_recovery_execution/3326482e6f7e/`.

Ryan explicitly approved the requested twelve-clip final-frame review:
"I approve these clips. They have been reviewed and you are good to move forward".
The separate receipt is
`configs/ball_tracking/reviews/yolo11x_crop_recovery_visual_review_record_v0_2.json`
(SHA-256 `365facf28a1e2f05339adea1e04e96a8fe7f33d0b3dea0184d16d1caa4c05433`).
It records package review without invented frame-level correctness verdicts.
Earlier pending snapshots stay unchanged. Do not request this review again.

The results closeout is `../ball_yolo11x_crop_recovery_results.md`. YOLO has
fewer matches in all 270 paired aggregate cells; these are correlated settings
on reused development frames. At radius 10, its .01 exported set covers 87/145
eligible frames versus RF-DETR's 140/145 and adds no matched frame beyond RF.
P002 challenge top one matches 12/25 versus 22/25 at both display thresholds.
A bounded comparison of ten existing single-detection families now reconciles
900 aggregate cells, 2,700 reports and 3,000 displayed frame-setting records,
counting duplicated controls once. At radius 10 it retains eight representative
and seven challenge tradeoff settings without selecting among them. YOLO .50
retains a representative low-FP/low-coverage point; it is not universally dominated.
Twenty frames are missed by all families at both displays: five lack an RF
match at .01 and fifteen lose an available RF match to confidence filtering.
The saved audit SHA-256 is
`9a83a996f4c4772a45530e1050dc9337c8caa3fabaf6095ed96bbc44bc5cfe21`.

All nine original prediction embargoes remain absent and all three holdouts
sealed. No method, operating point or quality gate is selected. No completed
experiment, media decode or model call is rerun in this closeout. Production
code is unchanged; the latest tests remain 27 recovery-focused, 15 adapter,
and 491 full-suite passes with one existing Windows skip.

The index is empty. Current work is three intentional context updates plus a
new review receipt and results document; no Git mutation occurred in this
closeout. Before-context bytes and a 4,750-file evidence preservation inventory
are saved under `data/outputs/ball_tracking/yolo11x_crop_closeout/3326482e6f7e/`.
Next Git step is separate authorization to stage the exact five-file closeout
scope, then separate commit authorization. The next development task is the
bounded 32-frame inspection of weak matching proposals versus emitted
alternatives specified in the results document. It uses saved evidence only;
no further clip approval, detector run, label change or training is pending.
No manual command is pending. Further Git steps require separate authorization.

## Prior checkpoint: approved YOLO recovery implemented and validated; staging next

Ryan approved the exact v0.2 recovery plan with "Yes I approve chat". The
separate record is
`configs/ball_tracking/reviews/yolo11x_crop_recovery_approval_v0_2.json`
(SHA-256 `5d9ec4a2d2d7c310ed304f4ce41e5b5aed9c76dd2829fdeb469201478c773782`).
The original proposal and design remain byte-identical historical snapshots.
The new executable manifest and three recovery modules implement guarded
inference/resume, saved-control scoring, and synchronized review rendering.
Every crop retains its actual inference commit and checkpoint/attempt/preparation
bindings; the typed model commit is explicitly assembly-view provenance only.

Validation: 27 recovery-focused tests and 15
adapter tests passed; the full suite ran 492 tests with
491 passes and one existing Windows directory-symlink skip.
Synthetic tests cover the 175/425 boundary, retry/resume, mixed provenance,
control preservation, complete scoring and twelve final-frame review clips.
Agent visual inspection covers synthetic layouts only. No real new review
clips or complete detector-quality results exist yet.

The actual read-only preflight verified the frozen runtime, all 150 source PNGs
and 175 original crop checkpoints without constructing a model, decoding
pixels or opening labels. The dirty-tree guard rejects execution. All 561
original partial-run files remain unchanged, and the real recovery subtree is
absent. All nine embargo paths and three holdouts remain protected. No method,
operating point or quality gate was selected. Earlier player-context review
is complete; do not request it again or rerun any completed experiment.

Branch remains `codex/ball-detector-baseline` at `116e3ed9cb4113521fa8c93adf4a100fea4dc0ec`.
The index is empty. No staging, commit, push, PR or merge occurred in this
implementation. See `../ball_yolo11x_crop_recovery_implementation.md` for exact
file scope and validation details. Evidence and the latest handoff are under
`data/outputs/ball_tracking/yolo11x_recovery_implementation/116e3ed9cb41/`.
Next is separate authorization to stage that exact scope, then separate commit
authorization. After a clean tested commit, execute only the approved 425
missing crop units, score/render and request Ryan's twelve-clip final-frame
review. No additional experiment approval or manual command is pending.

## Prior checkpoint: YOLO commit saved; partial run preserved; recovery proposed

Ryan separately authorized staging and committing the nineteen-file YOLO
snapshot. Commit `116e3ed9cb4113521fa8c93adf4a100fea4dc0ec` is complete on
`codex/ball-detector-baseline`. The exact staged/committed bytes match the
validated implementation. No push, PR or merge occurred.

Clean preflight passed for the approved six windows. The real new run saved
175 of 600 crop checkpoints, one full window candidate file and 27 selector
files, then failed at P001 challenge frame 218, bottom-right crop. One traced
normal retry preserved all 175 completed units and reproduced the failure.
There are 177 recorded project attempts: 175 completed and two failed; two
predictors performed four synthetic warmup forwards. No scoring or rendering
ran, so there are no new YOLO review clips or complete performance results.

The adapter wrongly rejected a native postprocessor box clipped to zero
height at the crop edge. Its confidence was 8.813966019260988e-7, below the
fixed .01 export floor, and that crop had zero exported candidates. The new
unstaged validator fix preserves finite, bounded, non-reversed native boxes
below the floor; all exported boxes still require positive size. The saved
failure replay preserves all 60 native rows, zero exports and every completed
checkpoint. All 15 focused tests and 464 full-suite tests pass, with one
existing Windows directory-symlink skip. No model call was made for the fix.

The existing v0.1 candidate format has one code commit. It cannot truthfully
describe preserved results from the old code and remaining work from a repair
commit. Do not rewrite old headers, overwrite artifacts, bypass validation or
rerun the 175 completed crops. The concrete versioned recovery proposal is
`docs/ball_yolo11x_crop_recovery_proposal.md`, bound by
`configs/ball_tracking/proposals/yolo11x_crop_recovery_v0_2.json`
(SHA-256 `b0a6a6ee81711d59f35b6360ce6c9595fce80c1625d45ff407683958a65612fe`). It proposes 175 reused plus 425
new crop units, explicit actual inference provenance per unit, a separate
assembly commit and new derived outputs in a fresh recovery subtree. It is
not approved, implemented or executable. Detector settings, development
windows and scoring/display grids remain fixed.

Start the next session with
`data/outputs/ball_tracking/yolo11x_execution/116e3ed9cb41/handoff_failure.md`.
The directory contains commit/preflight/failure receipts, the captured native
prediction, replay proof, tests, partial-run audit and final failure checkpoint.
The old experiment, all nine embargo paths and three sealed holdouts remain
preserved; no method, operating point or quality gate was selected. Ryan's
previous twelve player-context clips are reviewed; do not request them again.

The index is empty. Current unstaged work is the two-file validator fix and
three context updates; two recovery proposal files are untracked. Next is
review of the exact recovery contract, then implementation/validation and
separately authorized Git steps. Do not invoke the original inference helper
again. No manual command is pending.

## Prior checkpoint: approved YOLO11x support validated; staging next

Ryan approved the exact six-window YOLO11x comparison. The separate approval
and executable manifest are saved; the historical proposal remains unchanged.
Implementation details and the exact nineteen-file staging scope are in
`docs/ball_yolo11x_crop_implementation.md`. Prior player-context review is
complete; do not ask Ryan to repeat it or rerun any completed experiment.

The isolated ignored runtime and official weights are verified. Actual GPU
checks used synthetic arrays only: RGB conversion, fixed letterbox, inverse
mapping, FP32 CUDA device 0 and one ordinary forward after synthetic warmup
passed. No basketball frames entered the new detector. Read-only preflight
verified 150 source PNGs and 600 planned crops without constructing a model.
The dirty-tree guard rejects real execution before inspecting the runtime.

All 41 focused tests pass; the full suite has 460 passes and
1 existing Windows directory-symlink skip. Synthetic paired review panels
were visually inspected, and all 12 synthetic test clips decode through their
final frames. Candidate-prefix and same-buffer PNG hash/decode checks were
tightened during independent review. The initial focused invocation had
fixture-import errors; repository-style discovery passed without changing
production behavior. Logs retain both attempts.

Branch remains `codex/ball-detector-baseline` at `119159817df5414f534f133f0954c1f78c7e51de`;
the index is empty. The three intentional context changes are retained with
preceding bytes backed up. The four prior review/design files and 98 protected
non-context files remain unchanged. No staging, commit, push, PR or merge
occurred. All nine original embargoes and three sealed holdouts remain intact.
No method, operating point or gate is selected.

Evidence is in `data/outputs/ball_tracking/yolo11x_implementation/119159817df5/`;
`implementation_checkpoint.json` binds final files, tests, runtime and audits.
The next decision is authorization to stage exactly those nineteen files.
Committing remains a separate step. After a clean tested commit, execute the
already approved new comparison, score it and prepare twelve new review clips.
No manual command is pending and no new experiment approval is needed.

## Prior checkpoint: player-context review complete; next detector comparison proposed

Ryan explicitly answered "Yes, reviewed all 12; proceed" to the question asking
whether he watched all twelve new player-context clips through their final
frames. The separate record
`configs/ball_tracking/reviews/rfdetr_medium_crop_player_context_visual_review_record_v0_1.json`
(SHA-256 `0ebaabad929558d9c07339161f0d37362d6da9477883853146345cc56a848ef6`) binds his exact response,
the guide, all twelve clips/final panels, reports and execution checkpoint.
It records review completion without inventing frame-level correctness claims.
Earlier pending-review artifacts remain unchanged. Do not request this review
again or rerun the completed experiments.

The saved-results closeout is `docs/ball_crop_player_context_results.md`.
Across all 1,080 per-window comparisons with matching motion controls, the
context term causes no new lost matches, false-positive frames or increased
errors on shared matches. Remaining errors include candidate unavailability,
confidence filtering and path-choice losses. At radius 10, candidates at the
.01 export floor cover 140/145 eligible frames; better confidence separation
and fewer false guesses matter as well as candidate recall. P003 hidden false
observations persist with zero node context cost, and some graph settings
still lose top-one-correct reacquisitions. These are correlated development
results, not an operating-point decision or generalization gate.

Next proposed comparison: one fixed official YOLO11x Detect checkpoint on the
same 150 development frames and four fixed crops, with all-exported/top-one/
top-twenty selectors. See `docs/ball_yolo11x_crop_comparison_proposal.md` and
`configs/ball_tracking/proposals/yolo11x_crop_development_comparison_v0_1.json`
(SHA-256 `f891c04464422428dadbcfdf425436d3347464dbcab6d96ae23cac963dca5492`). The proposal binds 150 existing
unmarked PNGs, 162 saved RF-DETR outputs, their 810 report cells and six labels
for later scoring. It specifies 600 unique project-crop inference units, 162 new selector outputs,
810 new reports and twelve future review clips. It is not approved, executable,
implemented or run. No model/package was downloaded, installed or loaded.

The proposed model and package are pinned, including the official weight
digest. Actual local bytes, dependency hashes, environment lock and runtime
compatibility still require implementation/preflight validation in an isolated
environment. The baseline environment remains unchanged. Standard YOLO
letterboxing, best-class assignment and NMS differ from RF-DETR; this is a
complete detector-configuration comparison, not an architecture-only claim.
Model confidence values are not calibrated equivalents. COCO pretraining is
documented; exact footage overlap is unverified. Publisher licensing is recorded.

Branch/HEAD remain `codex/ball-detector-baseline` at
`119159817df5414f534f133f0954c1f78c7e51de`. The index is empty. The three
intentional context files are updated with their previous bytes retained;
four new review/results/proposal files are untracked. No production code
changed, so 34 focused passes and 419 full-suite passes plus one existing skip
remain the latest code validation; tests were not repeated. No staging, commit,
push, PR or merge occurred in this closeout. All nine embargo paths remain
absent and the three holdouts sealed. No method, operating point or quality
gate is selected. Saved evidence and `closeout_checkpoint.json` are under
`data/outputs/ball_tracking/crop_player_context_closeout/119159817df5/`.
No manual command is pending. First next action is Ryan's review of the exact
new experiment proposal; implementation/validation and separately authorized
Git steps must precede any approved real execution.

## Previous checkpoint: player-context execution complete; new visual review pending

Ryan separately authorized staging the exact validated eighteen-file scope
("yes go ahead and stage") and committing it ("yes you may"). Commit
`119159817df5414f534f133f0954c1f78c7e51de` on `codex/ball-detector-baseline`
is `feat(ball-tracking): compare observed player context`, with parent
`2274ab6097cd841421e2b606f723b047cd7dc62b`. Exact scope, blobs and clean checkout
were verified. No push, PR or merge occurred.

The already approved comparison then ran at that clean tested checkpoint on
the same six development windows/150 frames. It produced 216 new context
outputs and 1,080 new reports while reusing all 378 saved motion outputs and
1,890 reports unchanged. Both separate pools contain 495 aggregate cells.
Selection/scoring/rendering took 157.302/420.797/414.968 seconds.
Zero detector calls were made; no completed detector/crop/ranking/motion
experiment was rerun. Source-video decoding was disabled: the renderer used
only frozen development PNGs and its own new clips.

The new review bundle has 2,112 hash-verified assets: 2,100 PNGs and 12 clips,
plus 2,400 unchanged native/source PNG references. All twelve originals and
twelve separate H.264 playback copies fully decode 25 frames at 5 fps.
Agent inspection covers all twelve final closeup panels and targeted real
comparison frames. This is not Ryan's visual judgment; his review of these
new player-context clips through their final frames remains pending.

Start with the saved guide:
`data/outputs/ball_tracking/crop_player_context_execution/119159817df5/review_guide.md`.
It links every playback clip, final panel/closeup, native view and targeted case.
The same directory contains `results_summary.md`, `selection_audit.json`,
`score_audit.json`, all stage/visual/playback receipts and `execution_record.json`
(SHA-256 `300eecaecc8b99c2e44d765ec1757a10f9431a1f2e1c2766ccfddcd86b3c1615`).

No paired aggregate cell loses matches or increases false positives across
the fixed 360-cell grid. These correlated comparisons reuse the same 150
development frames and are not independent trials or a generalization gate.
At radius 10 and confidence .20/.35, representative matches gain 6-11 frames
per variant; challenge gains are 0-4. No matched display frame is lost.
P002 representative 262 recovers in all arms at both displays, and P002
challenge 48 recovers for tight allowance/gentler cost at .20. Hidden P003
false alarms remain two at .20 and one at .35 in every arm. P001 final 74
recovers at .20 but remains wrong at .35; P003 final 174 still matches only
with wide allowance/gentler cost. These exact cases are linked for review.

An independent saved-trace audit verified all 5,400 frame records, 222,888
node-cost records and 684,466 edges without selecting new winners. The saved
score audit reconciles all 2,970 reports, 990 aggregates, 1,080 paired/loss
cells and 360 aggregate contrasts. Neither audit reruns a selector or scorer.
Reviewed player input may use hindsight, historical player video/model
provenance remains incomplete, and proximity does not establish ball identity.
No method, operating point, quality gate or holdout release is selected.

All 101 protected files stayed unchanged through clean execution and
verification. Only the three intentional context documents were then advanced;
the index is empty. All nine original prediction paths remain absent and
all three holdouts sealed. `post_execution_context.json` binds the final
context edits and preservation checks. The tested implementation is unchanged:
34 focused passes and 419 full-suite passes plus one existing Windows skip.
No manual command is pending. Next is Ryan's twelve-clip final-frame review;
do not rerun completed stages or infer that earlier clip approvals cover it.

## Previous checkpoint: approved player-context comparison implemented and validated

Ryan approved the exact player-context proposal with "I approve chat". The
separate receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_player_context_approval_v0_1.json`
(SHA-256 `6e6f0fa4016c2b187593a11af55e45ef5a0d3f87ad26783af05136d9d80c84c1`).
It binds the unchanged proposal and fixed experiment specification. Four new
modules implement its bounded distance cost, guarded runner, separate scoring,
and paired review. Original confidence, candidate geometry/order, missingness,
and all four motion configurations retain their stated semantics. Reviewed
player rectangles remain offline inputs that may use hindsight; no ball-handler
identity, floor projection or end-to-end online player causality is inferred.

All 34 focused tests passed, followed by 419 full-suite passes and one
existing Windows directory-symlink skip. Independent exhaustive path cases
and complete zero-cost trace parity check the new recurrence. Synthetic
integration covers 216 new outputs with 378 saved outputs reused, 2,970 total
reports, 495 aggregate cells per pool, and all 12 complete 25-frame/5-fps clips.
Review tests verify 2,112 new assets and 2,400 existing native PNG references,
without old selectors/scorers/renderers or source-video decoding. Agent visual
inspection covers the synthetic layout; real comparison quality is untested.

The read-only real-input preflight passed on all six windows/150 frames with
selector/scorer/media-decode calls disabled. A separate read-only check verified
all 2,400 existing native PNG bindings without decoding media. The real runner rejects this dirty
checkout. No real context ranking, scoring or rendering has run; its output
root remains absent. The prior model/crop/ranking/motion experiments were not
rerun. All nine original prediction embargoes remain absent and the three
holdouts sealed. No method, operating point or quality gate is selected.

Start with `../ball_crop_player_context_implementation.md` for the exact
eighteen-file staging scope. Branch/HEAD remain `codex/ball-detector-baseline`
at `2274ab6097cd841421e2b606f723b047cd7dc62b`, with an empty index. The worktree
contains the three intentional tracked context edits and fifteen untracked
files. All five prior untracked review/design files and 83 protected existing
files retain their exact bytes. Only the three context documents were advanced;
their previous versions are retained in the ignored implementation evidence.

Evidence is under
`data/outputs/ball_tracking/crop_player_context_implementation/2274ab6097cd/`:
`focused_final.json`/`full_final.json` bind actual logs,
`real_input_preflight.json` records read-only guards,
`saved_native_input_preflight.json` verifies existing review images, and
`implementation_handoff.json` binds the final scope and preservation checks.
Whitespace, JSON and Python parsing are checked. No Git mutation occurred.
Next is explicit authorization to stage exactly those eighteen files, then
verification of the staged diff and separate commit authorization. Real
execution scope is already approved, but requires that clean tested commit.
Ryan's review of the new real clips follows execution. No manual command is
pending, and pushes, PRs, merges and holdout release remain separate decisions.

## Previous checkpoint: candidate appearance diagnosed; player-context proposal specified

Ryan's requested motion-factorial visual review remains complete. The next
saved-evidence diagnosis is `docs/ball_candidate_identity_diagnosis.md`.
The agent inspected all 12 contact sheets covering 215 distinct saved winner
candidates, with 430 exact native crops from 149 existing unmarked PNGs.
Repeated distant seating clutter and near-player body/footwear confusion are
different failure mechanisms. A saved WRONG localization outcome does not
certify non-ball identity; these are agent observations, not new human labels.

The fixed next design is `docs/ball_crop_player_context_proposal.md`, bound by
`configs/ball_tracking/proposals/rfdetr_medium_crop_player_context_v0_1.json`
(SHA-256 `b41dd0094755de726db6de196c28376cdfc2bceb40b645b1ce91fa56a6be80e7`).
It proposes one soft .25 * z/(1+z) cost per observed candidate node, with z the
minimum center-to-box distance divided by box height across all same-frame
observed player boxes. Missing context is explicitly neutral. Original
confidence/geometry, four motion settings and all other graph rules remain
fixed. All seven prior controls are reused by hash; only four context arms
would generate 216 new outputs and 1,080 new reports. The 12 planned new clips
pair each motion control with its context variant through every final frame.
No model call, completed experiment rerun, method/operating-point/quality-gate
selection, or holdout release is included.

The ignored evidence directory is
`data/outputs/ball_tracking/candidate_identity_diagnosis/2274ab6097cd/`.
Start with `catalog_guide.md` for optional diagnostic images. This is not a
replacement requirement for Ryan's completed clip review. `context_inputs.json`
(SHA-256 `272c0f14e86420f4b667a0a24d4723914c87efa31fdc0244b1348573a2a441a0`)
freezes 1,353 observed player rows over exactly 150 permitted frames; all six
window row digests match the prior feasibility audit. Original fields and
duplicate/identity provenance remain. Historical player source hashes/model
provenance remain unavailable; current hashes do not retroactively supply them.
Reviewed player context can use hindsight, so online player causality is not
claimed. Selection would use image-space rectangles only, without projection
to the court or possession/ball-handler inference.

The proposal is not yet approved, implemented or executed. Next is review of
this exact new comparison scope, followed by implementation and focused/full
synthetic validation. Staging, committing, pushing, PR creation and merging
still need separate explicit authorization. Execution requires its approved
scope and clean tested implementation commit. No manual command is pending.

Branch/HEAD remain `codex/ball-detector-baseline` at
`2274ab6097cd841421e2b606f723b047cd7dc62b`; index empty. Preserve the three
intentional context edits, the prior untracked review receipt/results note,
and three new untracked design files (diagnosis, proposal Markdown/JSON).
No production code changed; the last results remain 23 focused and 385 full
passes plus one existing Windows skip. JSON/AST parsing, exact bindings,
scope and whitespace were checked; all 83 protected non-context files are
unchanged, all nine embargo paths absent and all three holdouts sealed.
`diagnosis_handoff.json` records the exact eight-file scope and final hashes.

## Previous checkpoint: motion review completed; saved-evidence closeout complete

Ryan explicitly stated "I have reviewed all of these clips. move forward".
The separate receipt `configs/ball_tracking/reviews/rfdetr_medium_crop_motion_factorial_visual_review_record_v0_1.json`
(SHA-256 `d629f93d4c4081dd89fcbc98c997fff0f5aea7fe9d8555a16d9328f803d6fd40`)
records completion of the requested 12-clip review against the exact execution,
both scoring pools, original/playback clips and final images. It does not invent
individual-frame verdicts, select a method or approve measured accuracy. Earlier
execution and guide snapshots retain their historical pending-review status.

The read-only closeout is `docs/ball_crop_motion_factorial_results.md`.
Increasing movement allowance helps across the fixed grid; movement-cost
effects depend on the allowed links and pool. Persistent incorrect candidates
remain despite long paths. No winner, operating point, quality gate or holdout
release is selected.

New ignored evidence is under
`data/outputs/ball_tracking/crop_motion_closeout/2274ab6097cd/`.
`closeout_audit.json` (SHA-256 `2eb17ff8c26237f3009396a5a54f9646fba187db7409d9e87cfe83c678361c5c`)
reconciles 1,080 loss partitions and inventories 4,843 saved emitted winners
from all 216 history outputs. It preserves path length, span, gaps, boundary
flags, confidence, current/competing candidates and saved radius-10 outcomes.
`mechanism_diagnostic.json` binds 112 copied case traces and 38 input files.
A further read-only `context_feasibility.json` inventories reviewed image-space
player/court inputs and diagnostic candidate context; see its companion note
and results document for provenance limits. No new selection rule is applied.

The support audit has 313 matched singleton emissions versus 71 unmatched
eligible-frame and 19 hidden singleton emissions. Another 1,221 unmatched
eligible-frame and 52 hidden emissions already have two or more nodes. These
counts repeat correlated arms/confidences, not independent source examples.
At both displays, all four arms choose a five-node false path at P002 262.
Hidden P003 168 already has two nodes at .20; correct reacquisition 171 is a
singleton in every arm at both displays. A generic minimum-support rule would
lose correct observations and still retain persistent wrong objects.

The next design question is candidate identity: whether appearance, crop-view
provenance and reviewed image-space player/scene context supply useful evidence.
Keep abstention as a separate false-alarm/missingness tradeoff. Do not project an
airborne ball through the floor homography or infer possession from proximity.
No new model, selector, scorer or renderer was invoked in this closeout; no
prediction, smoothing, interpolation or operating-point selection was performed.

Branch/HEAD remain `codex/ball-detector-baseline` at
`2274ab6097cd841421e2b606f723b047cd7dc62b`. Preserve the three intentional unstaged
context updates and the two new untracked files: review receipt and results note.
The index is empty. All 83 protected non-context files and prior reviewed
outputs are unchanged; all nine embargo paths remain absent and all three
holdouts stay sealed. The final ignored `closeout_handoff.json` binds the exact
five-file worktree scope and evidence. Whitespace and JSON/Python parsing are
checked; production code and its 23 focused/385 full-suite passes plus one
Windows skip are unchanged, so code tests were not repeated. No new staging,
commit, push, PR or merge is authorized or performed. No upstream player review
changed and no manual command was supplied but left unrun.

## Previous checkpoint: motion-factorial execution complete; visual review pending

Branch is `codex/ball-detector-baseline` at
`2274ab6097cd841421e2b606f723b047cd7dc62b`
(`feat(ball-tracking): separate motion allowance and cost`), parent
`3c4894656fd5da11708a54089444d41f0a6f7773`. Ryan separately authorized staging
the exact validated 15-file scope with "yes you may mr chat sir", then the
proposed commit with "yes you may". The commit scope, parent and blobs were
verified. No push, PR or merge occurred or is authorized.

The already approved comparison completed at that clean checkpoint using only
the six saved development crop windows. It separates movement allowance from
movement penalty: four combinations plus three controls, each at nine confidence
thresholds. There are 378 derived outputs, 1,890 per-window scoring reports and
315 aggregate cells in each separate pool. All 270 saved control traces, 1,350
control reports and 450 aggregate parity checks pass. Zero detector calls were
made; neither completed original crop nor ranking experiment was rerun.
Selection/scoring/rendering took 87.632/113.247/418.471 seconds.

All 3,012 review assets were hash-verified: 12 clips and 3,000 PNGs. Every
original and separate H.264 playback copy decoded all 25 frames at 5 fps.
Agent inspection covered all 12 final-frame closeups and targeted comparison
frames; it is not Ryan's visual judgment. His review of the new 12 clips remains
pending. Earlier crop and ranking review responses remain complete.

Start with the ignored guide:
`data/outputs/ball_tracking/crop_motion_execution/2274ab6097cd/review_guide.md`.
It links all playback clips, final panels/closeups, and exact mechanism cases.
The same directory holds `results_summary.md`, `score_audit.json`, stage receipts,
playback verification, and `execution_record.json` (SHA-256
`1e732738669cb3f6c4389a92248cd1435b376b2fb023a2b02abacda9bb4eb40f`). The execution record binds all outputs, inputs,
86 protected files, inspection evidence and the clean execution checkpoint.

Increasing movement allowance at either fixed penalty scale increases matched
frames in all 45 confidence/radius cells in both pools, without increasing false
positives. Changing the penalty has mixed effects: a gentler penalty with tight
allowance loses challenge matches in all 45 cells, while with wide allowance it
gains challenge matches in 37 and ties in eight. These cells reuse the same
development frames and are not independent trials. No winner is selected.

At radius 10/confidence .20, representative TT/TW/WT/WW match counts are
29/33/48/54 versus top one's 51; challenge counts are 53/50/62/63 versus 59.
TT/TW/WT/WW mean tight/wide movement allowance first, then tight/wide cost scale;
a wider cost scale produces a gentler penalty. P002 representative 258 depends
on the penalty; all four history arms still choose incorrectly at 262. P002
challenge 48 regresses under tight allowance/gentler penalty at .20. Only the
wide-allowance/gentler-penalty history arm matches P003 final challenge frame
174 at both displays. Hidden P003 false alarms remain two at .20 and one at
.35 in each history arm. These are inspection targets, not a quality decision.

All nine original prediction embargo paths remain absent, and holdouts P001
300-324, P002 200-224 and P003 250-274 remain sealed. No operating point,
quality gate or holdout release is selected. All original candidate confidence,
coordinate and index provenance and explicit missingness are preserved.

After the clean execution audit, only the three context files were updated;
preserve these intentional unstaged changes. The index is empty. No production
code changed after its 23 focused passes and 385 full-suite passes plus one
existing Windows symlink skip; tests were not repeated. Whitespace and final
scope are checked in the ignored post-execution context receipt. No upstream
player decision changed and no manual command was supplied but left unrun.
Next: Ryan reviews all 12 new clips through their final frames using the guide.
Further staging, commits, pushes, PRs or merges require separate authorization.

## Previous checkpoint: approved motion-factorial implementation validated

Ryan approved the exact factorial comparison with "I approve chat". The new
receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_motion_factorial_approval_v0_1.json`
(SHA-256 `5169aee6b162494bf4650c308728459f499ecd9b280242d6c36a43411e962a5d`).
The executable manifest is
`configs/ball_tracking/crop_motion_experiments/rfdetr_medium_crop_motion_factorial_v0_1.json`;
specification digest excluding authorization:
`51bc58477f5e1273e4ec83588003861f3b095ae46923b46915905ca4600f829f`.
The approved design/proposal bytes and original historical status are unchanged.
Do not request this experiment approval again. Git steps remain separate.

Four new `src/ball_tracking/crop_motion*.py` modules implement independent
edge allowance and cost normalization, guarded resumable selection, strict
saved-control scoring, and a nine-panel review. Original crop/ranking/detector
and player code is unchanged. The implementation and exact proposed 15-file
scope are in `docs/ball_crop_motion_factorial_implementation.md`.

All 23 focused tests pass in 191.201 seconds. Synthetic integration covers
378 outputs, 1,890 reports, two 315-cell pools, 270 complete control traces,
1,350 control report cells and 450 aggregate parity checks. All 12 synthetic
review clips decode all 25 frames at 5 fps; 3,000 supporting PNGs preserve
native overlays, exact unmarked source and source-scale closeups. The agent
inspected the synthetic layout. The full suite runs 386 tests: 385 pass and
one existing Windows directory-symlink test skips (482.413 seconds).
Source/test hashes remained unchanged throughout the run; bytecode was disabled.

Ignored evidence is under
`data/outputs/ball_tracking/crop_motion_implementation_validation/`.
The actual-input read-only preflight confirms six windows, 150 source frames,
63 variants and zero model calls. `checkpoint_audit.json` binds the exact
15-file scope and successful logs, preserved prior hashes and committed
blobs, all saved controls, JSON/Python parsing, whitespace and actual
dirty-checkpoint execution refusal. The new real output root is absent. No
completed experiment was rerun, no operating point/gate is selected, and all
nine original embargoes and three sealed holdouts remain intact.

Branch/HEAD remain `codex/ball-detector-baseline` at
`3c4894656fd5da11708a54089444d41f0a6f7773`. The index is empty; preserve the
three intentional context edits and 12 new scope files. No staging, commit,
push, PR or merge is authorized or performed. Next is separate authorization
to stage the exact validated 15-file scope, then separate commit authorization.
The already approved experiment
may execute only after that clean implementation checkpoint. No upstream player
decision changed and no manual command was supplied but left unrun.

## Previous checkpoint: saved ranking diagnosis and motion-factorial proposal

After Ryan said "move forward", the saved remaining misses were diagnosed
without invoking a selector, scorer, renderer or detector. The results are in
`docs/ball_crop_candidate_ranking_results.md`. All 540 history/window/radius
loss partitions reconcile exactly with saved false-negative counts. At
confidence .20/.35 there is no top-twenty cap loss across either pool or any
radius. Wide history's eight additional representative misses at each display
are wrong current choices; challenge has no additional ranking misses at those
settings. Low-confidence candidate proximity is not established ball identity.

The saved paths distinguish mechanisms: P002 representative 262 has an intact
correct path but accumulated false evidence wins. At representative 258, the
same useful path is admissible under both motion limits, yet wide normalization
charges nine times less motion cost. Other useful edges are actually excluded
by the tight gate, including P003's final challenge observation. Hidden P003
false alarms at 167/168 arise from fresh starts, not gap interpolation.

The concrete next proposal is `docs/ball_crop_motion_factorial_proposal.md`
and `configs/ball_tracking/proposals/rfdetr_medium_crop_motion_factorial_v0_1.json`
(SHA-256 `66e7c9aae8c66747d62a480d00c256f1e196df3044d5284be501a76a1edd1c64`).
It crosses edge limits .01/.03 with independent motion-cost scales .01/.03,
retains both old settings and three crop controls, and keeps all other rules
fixed. Proposed scope: 63 variants, 378 window outputs, 1,890 reports, 315
aggregate cells per pool, 1,350 existing-arm report parity checks and 270 full
control-trace checks, plus 12 review clips. It uses only saved candidates and
requires zero detector calls. It is not executable or authorized; the earlier
45-variant approval does not include these new combinations. No operating
point, method, quality gate or holdout release is selected.

Ignored evidence is under
`data/outputs/ball_tracking/crop_ranking_diagnosis/3c4894656fd5/`.
`diagnostic.json` (SHA-256
`b5fc30f8dd8e5bd4b8a7c1bf98bf9e51108cdd3cc45397dd6a12fe614a84014d`)
binds its generator/inputs and holds 540 partitions, 180 aggregate cells,
600 display frame records and 88 detailed endpoint traces. All 270 derived
output hashes and 71 non-context protected files matched; the previous three
context hashes and review receipt matched before this update. All nine original
embargo paths remain absent and all three holdouts sealed. No completed
experiment was rerun. No production code changed, so code tests were not
repeated; the last result is 21 focused passes and 362 full-suite passes with
one existing Windows skip. Independent read-only review checked the mechanism
claims, partition counts and new design.

Branch/HEAD remain `codex/ball-detector-baseline` at
`3c4894656fd5da11708a54089444d41f0a6f7773`, with an empty index. Preserve the
three intentional unstaged context edits and four untracked files: the ranking
visual-review receipt, ranking results note, factorial design and proposal JSON.
No new staging, commit, push, PR or merge occurred or is authorized. The final
context handoff binds these seven files and the successful whitespace/JSON/hash
checks. No upstream player decision changed or manual command remains unrun.
Next: obtain approval of the exact new experiment scope, then implement and
validate it synthetically before any separately authorized Git steps or real
execution. The current new output root is absent.

## Previous checkpoint: ranking visual-review response recorded

Ryan responded "looks good to me" after the linked 12-clip ranking review
package and first embedded clip. The separate receipt
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_ranking_visual_review_record_v0_1.json`
(SHA-256 `21d896cd6842fc28293f3196ecce3b2e3dc81d6ae65c694a0aaa93fb753054a5`)
binds the exact response to execution commit
`3c4894656fd5da11708a54089444d41f0a6f7773`, the manifest/approval, both scoring
pools, all 12 original/playback clips, and final panels/closeups.

This records package-level review completion in response to the requested
12-clip scope. Ryan's statement does not itemize clips or independently attest
every final frame; no extra frame-level or quantitative correctness claim is
added. The receipt timestamp is creation time, not an invented message time.
Earlier execution, guide, manifest, and handoff snapshots retain their
historical pending-review status. No completed stage was rerun.

Read-only verification rehashed all 2,412 review assets, 12 playback clips,
270 derived outputs, both scoring pools, six crop inputs, six saved detections,
and six finalized labels. All bindings matched. All nine original prediction
embargoes remain intact and all three holdouts stay sealed.

The numerical findings remain unchanged: wider links improve challenge
matches across the grid, but lose P002 representative 262 and have five
representative grid cells with fewer matches than crop top one. Tight links
lose many valid matches. Positive visual feedback does not select a winner,
operating point, quality gate, or authorize a new experiment or Git step.

Branch/HEAD remain `codex/ball-detector-baseline` at `3c4894656fd5`; the index
is empty. Preserve the three intentional unstaged context edits and new
untracked receipt. No production code changed; tests were not repeated, and
the diff received a whitespace check. Next is a read-only diagnosis of saved
remaining misses and path choices, separating missing usable candidates from
ranking losses, before proposing any new experiment. P002 representative 262
and P003 hidden frames 165-169 remain useful cases. No upstream player
decision changed and no manual command was supplied but left unrun.

## Previous checkpoint: crop candidate ranking executed; visual review pending

Branch is `codex/ball-detector-baseline` at
`3c4894656fd5da11708a54089444d41f0a6f7773`
(`feat(ball-tracking): add approved crop candidate ranking`), parent
`1a9479f83a1766d8979fad07c604bc686d3c52c6`. Ryan separately approved the exact
15-file staging scope and then the proposed commit with "I approve". The commit
parent, scope, and all file blobs were verified. Nothing was pushed.

The already approved ranking experiment then ran at that clean checkpoint:
270 derived outputs from the six saved development crop files, 1,350 per-window
scoring reports, and 225 aggregate cells in each separate pool. All 540 crop
raw/top-one control cells reproduce saved reviewed outcomes. There were zero
new detector calls. The completed original crop experiment was not rerun.

All 2,412 new review assets were hash-verified: 12 clips and 2,400 PNGs. Every
original clip and separate H.264 playback copy decoded all 25 frames at 5 fps.
The agent inspected all 12 final-frame closeups, P003 hidden frame 165's six
panels at 0.20, P002 representative regression frame 262, and P002 challenge
recovery frame 48. Ryan's review of the new 12 clips is pending; his previous
crop and temporal reviews remain complete.

Start with the ignored guide:
`data/outputs/ball_tracking/crop_ranking_execution/3c4894656fd5/review_guide.md`.
It links every playback clip, final panels/closeups, and exact gain/loss frames.
The same directory holds `results_summary.md`, `score_audit.json`, stage logs,
playback verification, and `execution_record.json` (SHA-256
`95c0b8f92c8af1fde8a842bf7e4bd6993b87880cfbc2a690ae758bf267a14b5d`).
The review bundle is
`data/outputs/ball_tracking/crop_candidate_ranking/rfdetr_medium_crop_candidate_ranking_v0_1/review/b7e93ff579f3d8d6069109c069a5a56d/`.

At confidence 0.20 and radius 10, representative crop top one has 51 TP/23 FP;
wide history has 54 TP/19 FP, while tight history has 29 TP/37 FP. Challenge
top one has 59 TP/13 FP; wide has 63 TP/6 FP and tight 53 TP/13 FP. At 0.35,
wide has 51 TP/17 FP versus top one's 50/19 representative, and 58/2 versus
55/6 challenge. Wider links recover P002 challenge 48-49 at both displays but
lose P002 representative 262 while recovering 258. Tight links lose many
previous matches, including P003 challenge final 174. At all 45 grid cells,
wide improves challenge match counts; representative counts improve in 37,
tie in three, and worsen in five. Tight has fewer matches in all 45 cells of
both pools. These are correlated descriptive comparisons, not independent
trials or a selected method, operating point, or quality gate.

Selection took 51.13 seconds, scoring 60.65 seconds, and rendering with its
deterministic new-score verification 251.09 seconds. All 74 protected file
bindings matched through the final clean execution audit. All nine original
prediction embargo paths remain absent and all three holdouts sealed.

These three context files were updated only after execution and verification;
they are intentional unstaged changes, and the index is empty. Preserve them.
No production code changed after the 21 focused passes and full-suite 362
passes plus one existing skip. The context update receives `git diff --check`.
Next is Ryan's visual inspection of all 12 new ranking clips through their
final frames. Do not rerun completed stages or select an operating point/gate.
No new staging, commit, push, PR, or merge is authorized. No upstream player
decision changed, and no manual command was supplied but left unrun.

## Previous checkpoint: approved crop candidate-ranking implementation

Ryan approved the bound saved-candidate experiment with "I approve chat".
The separate receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_ranking_approval_v0_1.json`.
The executable manifest is
`configs/ball_tracking/crop_ranking_experiments/rfdetr_medium_crop_candidate_ranking_v0_1.json`;
specification digest, excluding its authorization binding:
`c3541d45fcc4db384d2222a56cd4fe18885c7212ad9f7c77b0e933bdd3eb2fe4`.
The original proposal/design retain their historical status and bound bytes.

Four separate modules implement causal selection, guarded/resumable execution,
unchanged matching with saved-control parity and loss decomposition, and
six-panel synchronized review. Exact behavior and the proposed 15-file Git
scope are in `docs/ball_crop_candidate_ranking_implementation.md`. Existing
detector, crop, tracklet, player-pipeline, and reviewed label files are unchanged.

All 21 focused tests pass with `.venv` Python and bytecode disabled. The full
suite runs 363 tests: 362 pass and one existing Windows symlink test skips.
Synthetic integration covers 270 derived outputs with partial resume,
1,350 scoring reports, two separate 225-cell pools, all 540 saved crop control
outcome cells, and 12 fully decoded 25-frame/5-fps clips plus 2,400 PNGs.
The agent inspected synthetic comparison/closeup layouts; this does not approve
real ranking quality. No user source video or model is opened by the synthetic
ranking tests. Real-input read-only preflight verifies the six bound windows,
150 frames, 45 variants, and zero new model calls.

Branch/HEAD remain `codex/ball-detector-baseline` at
`1a9479f83a1766d8979fad07c604bc686d3c52c6`. Exactly three tracked context files
are modified; 12 new scope files are untracked. The index is empty. Prior
intentional context notes remain preserved. The real ranking output root is
absent; the completed crop inference/scoring/rendering were not rerun.
All nine original prediction embargoes and all three sealed holdouts remain.
No operating point or quality gate is selected.

Next: request separate authorization to stage the exact validated 15-file
scope, then separately commit it. The already approved ranking experiment can
execute after that clean implementation checkpoint; no new experiment approval
is needed for its fixed scope. Staging, committing, pushing, PR creation, and
merging remain separate, currently unauthorized actions. Ryan's review of the
12 real ranking clips is pending execution. No upstream player decision or
player-pipeline `--rerun-from` change is involved. No manual command was supplied
but left unrun. Ignored validation evidence is under
`data/outputs/ball_tracking/crop_ranking_implementation_validation/`.
The final `checkpoint_audit.json` binds the exact scope and successful logs,
verifies all 59 protected Git/SHA-256 bindings, six saved detections, six labels,
frozen crop/proposal/review evidence, all nine absent embargo paths and three
holdouts, source/JSON parsing, whitespace, and the dirty-execution refusal.

## Previous checkpoint: saved crop closeout and candidate-ranking design

After completed visual review, Ryan said "lets move forward chat". The next
design is now concrete in `docs/ball_crop_candidate_ranking_proposal.md` and
`configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_ranking_v0_1.json`
(SHA-256 `f9a3ae162d2227ddffab9a9da68811ea629cf7dfa6ffa48625546ac1ab5ad2ca`).
This is a non-executable proposal awaiting exact experiment-scope approval.
No new selection, inference, scoring, or rendering experiment has run.

A new create-only saved-result diagnostic extracts all 180 same-cell aggregate
comparisons and the displayed per-window outcomes, without rescoring. It also
counts label-blind cross-crop box overlaps. The diagnostic is
`data/outputs/ball_tracking/tiled_closeout/1a9479f83a17/diagnostic.json`, SHA-256
`87a2e57e147da2907d42286bc6d81d333c011eb5609ba3f71c09291265c0cc3d`.
Its generator and inputs are bound; displayed frame counts/decompositions were
checked. The results note is `docs/ball_detector_tiled_comparison_results.md`.

At confidence 0.20/radius 10, crop raw has qualifying matches in 62/75
representative and 63/70 challenge frames, while top one retains 51 and 59.
Removing lower-ranked duplicates cannot change the highest-confidence guess.
The proposed next experiment therefore ranks original candidates using a
five-frame causal history, with raw/top-one/top-twenty controls and two motion
limits. It uses saved crop inputs only, preserves explicit missing output,
and does not smooth or invent ball coordinates. Its fixed scope is 45 variants,
270 derived outputs, 1,350 per-window reports, two separate 225-cell pools,
and 12 review clips. No operating point or quality gate is selected.

Branch and HEAD remain `codex/ball-detector-baseline` at
`1a9479f83a1766d8979fad07c604bc686d3c52c6`. Preserve the three existing context
edits, completed crop review receipt, new results/design notes, and proposal
JSON. The index is empty; no staging, commit, push, PR, or merge is authorized.
All nine original embargo paths remain absent; all three holdouts stay sealed.
No production code changed, so focused/full tests were not repeated. Next is
approval of the concrete new experiment, then synthetic-first implementation
and validation before any separately authorized Git steps and real execution.
No upstream player decision changes or unrun manual commands are involved.

## Previous checkpoint: crop comparison visually reviewed

Ryan completed the requested 12-clip crop comparison review and stated:
"all of them look pretty good to me. even P002 challenge". The separate receipt
`configs/ball_tracking/reviews/rfdetr_medium_tiled_development_comparison_visual_review_record_v0_1.json`
binds his exact feedback to execution commit
`1a9479f83a1766d8979fad07c604bc686d3c52c6`, both scoring pools, the review
manifest, all 12 original/playback clips, and their final-frame closeups.
Receipt SHA-256:
`6e108189b792d505c97adbcfcce5aa635a6e140893a6306e0c08bfe910218adb`.
The timestamp is receipt creation time, not an invented message event time.
Earlier pending-review records and notes remain historical snapshots.

Read-only closeout rehashed all 1,962 bound review assets, all 12 playback
clips and final closeups, two scoring-pool reports, six crop candidate files,
and six saved whole-frame detection files. All bindings matched. The three
intentional context edits matched the handoff hashes before this update.
All nine original embargo paths remain absent; all three holdouts stay sealed.
No inference, scoring, rendering, or test suite was rerun, and no production
code changed. The previous 18 focused passes and full-suite 341 passes plus
one existing skip remain the last code validation.

Branch and HEAD remain unchanged; the index is empty. This review adds one
unstaged receipt and updates the existing three context files while preserving
their prior notes. Nothing was staged, committed, pushed, or submitted as a PR.
No operating point, quality gate, winner, or next experiment is approved.
Ryan's favorable visual assessment does not remove the numerical regressions:
crops recover more matches overall but add false guesses; P002 challenge
frames 48-49 still lose top-one matches at both displayed settings.

Next: summarize the saved gains/losses and prepare a concrete next experiment
design before seeking its separate scope authorization. Do not repeat the
completed crop review or rerun the experiment. No upstream player decision
changed, and no player-pipeline `--rerun-from` action is needed. No manual
command was supplied but left unrun.

## Previous checkpoint: crop comparison executed; visual review pending

Branch is `codex/ball-detector-baseline` at
`1a9479f83a1766d8979fad07c604bc686d3c52c6` (`feat(ball-tracking): add approved
fixed-crop detector comparison`). Ryan separately authorized staging with
"yes stage" and committing with "commit please". The exact 15 validated files
were committed, their Git blobs and parent verified, and the worktree was clean
through inference, scoring, rendering, playback verification, and final audit.
Nothing was pushed. The three context files are the only subsequent uncommitted
changes; the index is empty. Preserve these execution notes.

The already approved fixed-crop experiment is now complete at that checkpoint:
600 new model calls on exactly 150 frames in the six development windows,
600 immutable view checkpoints, six candidate files, 1,080 per-window scoring
reports, and 180 aggregate cells in each separate representative/challenge pool.
All 540 saved whole-frame raw/top-one control cells reproduce the prior reviewed
scoring outcomes and per-frame results. Adapter-stage input/below-threshold
counts are excluded from that parity claim. All 59 protected files, six saved
detection files, and six reviewed annotation bindings remain unchanged.

All 1,962 review assets were hash-verified: 12 videos and 1,950 images. Every
original video and separate H.264 playback copy fully decoded through all
25 frames. The agent directly inspected all 12 final-frame closeups, P003
hidden frame 165's four-panel image at 0.20, and P001 frame 74's crop context.
This is not all-frame visual approval. Ryan's review of the new crop evidence
is pending; his earlier temporal inspection remains complete.

At both predeclared display confidences and the raw 10-pixel radius, cropped
inputs improve pooled match counts but add false guesses. For top-one at 0.20,
representative matches rise from 44 to 51 of 75 eligible frames and false
guesses from 20 to 23; challenge matches rise from 46 to 59 of 70 and false
guesses from 10 to 13. At 0.35, the corresponding match counts are 39 to 50
and 41 to 55, with false guesses 5 to 19 and 4 to 6. These are descriptive
comparisons, not selected settings. P002 challenge frames 48-49 lose top-one
matches at both settings; P002 representative frames 258-259 and P001 challenge
frame 219 also regress at 0.20. Review the losses as well as the gains.

New generated evidence is ignored under
`data/outputs/ball_tracking/tiled_development/rfdetr_medium_tiled_development_comparison_v0_1/`.
The verified review bundle is `review/a007aa4b358587789f7ef1f28b1c66b5/`.
The execution handoff is
`data/outputs/ball_tracking/tiled_execution/1a9479f83a17/review_guide.md`,
with links to all 12 playback clips and final closeups. The same directory has
`results_summary.md`, `score_audit.json`, command logs, and `execution_record.json`
(SHA-256 `4d7977be4e08c9e70df438a007cbe92de4be60bed14eccc4d75a581aff137b52`).
Inference took 136.28 seconds end to end; synchronized model calls totalled
96.02 seconds, including first-call initialization. Median four-crop frame
time was 0.532 seconds. No measured runtime ratio to the saved control exists.

The last execution command completed the final record and preservation audit;
the subsequent context-only handoff received `git diff --check`. No new code
changed after the validated 18 focused tests and 341 full-suite passes plus
one existing skip, so those tests were not repeated. No manual command was
provided but left unrun. The exact next action is for Ryan to watch all 12 new
crop-comparison clips through their final frames and report visual findings.
Do not repeat experiment authorization or the earlier temporal review.
All nine original prediction paths remain absent, all three holdouts remain
sealed, and operating-point and quality-gate fields remain null. No upstream
reviewed player decision changed; no player-pipeline rerun is needed.

## Previous checkpoint: approved crop comparison validated; staging approval pending

Branch remains `codex/ball-detector-baseline` at
`6769e07476da09d858fa42f82aace024d21f7735`. Preserve the intentionally dirty
worktree. Ryan approved the concrete crop comparison with "yes i approve".
The receipt is
`configs/ball_tracking/reviews/rfdetr_medium_tiled_development_comparison_approval_v0_1.json`;
it binds the unchanged proposal (SHA-256
`2732e69b19e746b96af7d76e214b08281b5a8f4a58b8f28b494890973f846535`)
and executable specification
`3384a930d8633b202b689857de2bea4939277a2d2f0c3da483c2c48e9e9ef023`.
Do not ask for this experiment approval or the completed temporal review again.

Four separate `tiled_*.py` modules implement crop-local/global candidate
provenance, fixed-window inference with immutable per-crop resume, separate
scoring, and four-panel review rendering. They reuse the frozen per-call
detector without editing its contract, source, tests, saved predictions, or
labels. The new manifest is outside the old experiment registry:
`configs/ball_tracking/tiled_experiments/rfdetr_medium_tiled_development_comparison_v0_1.json`.
The implementation note documents the exact 15-file staging scope:
`docs/ball_detector_tiled_comparison_implementation.md`.

Final focused validation passed all 18 tests in 74.915 seconds. Synthetic
integration exercised 600 model calls, exact and partial resume, 1,080 report
cells, saved-control scoring parity, separate pools, 12 complete review videos,
1,950 review images, and tamper rejection. The agent inspected the synthetic
comparison and closeup previews. Real-input dry-run passed source, frozen
package/weight, and RTX 5070 CUDA checks; it made no predictions. All commands
used the repository `.venv` with bytecode disabled. The final full suite ran
342 tests in 223.084 seconds: 341 passed, one existing directory-symlink
capability skip. `git diff --check`, new-file syntax/whitespace checks, and
exact 15-file scope verification passed. All 59 prior protected files and six
saved detection/label bindings remain unchanged.

Generated validation logs and synthetic previews stay ignored under
`data/outputs/ball_tracking/tiled_implementation_validation/`: `focused_final.log`,
`full_suite_final.log`, `preflight.log`, synthetic PNGs, and
`validation_record.json` with file hashes and proposed Git blobs. The last
completed work is the final validation and input/scope audit. Real crop outputs
remain absent. The next boundary is separately
authorized staging of the exact 15 files, then separate commit authorization.
The approved runner requires a clean committed checkpoint for real inference;
run inference, scoring, and rendering at that same commit before updating
context. The real execution commands are documented for the future checkpoint
and have not run. No manual command was left for Ryan to execute.

The index is empty; nothing staged, committed, or pushed. The earlier temporal
closeout files are preserved in this implementation scope. All nine original
embargo paths remain absent, all three holdouts remain sealed, and no operating
point or quality gate is selected. This changes no upstream reviewed player
decision and needs no player-pipeline `--rerun-from` stage.

## Previous checkpoint: temporal evidence inspected; crop comparison proposed

Branch `codex/ball-detector-baseline` remains at
`6769e07476da09d858fa42f82aace024d21f7735`. Ryan responded
"inspected. please move forward" to the 12-clip temporal review package.
The new receipt records inspection completion with that exact statement:
`configs/ball_tracking/reviews/rfdetr_medium_temporal_association_visual_review_record_v0_1.json`,
SHA-256 `c90aab1535c359e50069fbff5149d26040fd1bc9d1696a1009edf89993cf63a7`.
Its timestamp is receipt creation time. Earlier runtime records remain
unchanged as historical pending-review snapshots; do not request this review
again or equate its completion with selecting a quality gate.

All 2,412 review assets, 12 playback clips, 324 observation files, two scoring
grids, six labels and raw files, and 59 protected file bindings were reverified.
The read-only closeout compared all 360 tracklet aggregate cells with top-one
at identical confidence/radius settings. Some settings gain correct matches,
but all such gains also increase false guesses. At the two predeclared display
settings, every tracklet variant loses correct matches in both pools.

Candidate availability is also limiting: at the 0.01 export floor and 10-pixel
radius, P001 has qualifying candidates in 10/25 representative and 18/25
challenge frames. These are label-assisted availability counts, not a selected
operating point. The new results note separates detector/threshold misses from
additional association losses without relaxing the scoring radius:
`docs/ball_temporal_association_results.md`.
The ignored diagnostic contains every same-cell comparison and all 270 raw
miss decompositions, with exact frame IDs and a bound generating script:
`data/outputs/ball_tracking/temporal_closeout/6769e07476da/diagnostic.json`
(SHA-256 `845dc1d7e7ead0ec952c27985595878c3e13488af54c1dc1f946ae207d6cce77`).

The next proposed experiment gives the same detector more image detail using
four fixed overlapping crops on each of these same 150 frames: 600 new model
calls, no training or new weights, no window expansion. Its concrete design is
`docs/ball_detector_tiled_comparison_proposal.md`; its non-executable scope is
`configs/ball_tracking/proposals/rfdetr_medium_tiled_development_comparison_v0_1.json`.
The existing temporal permit covers only saved detections. The next boundary
is approval of this new prediction experiment, followed by implementation and
validation before separate Git steps and real execution. No manual command
was supplied but left unrun.

This turn changes review/configuration/documentation only. Production code and
the original approved temporal design/manifest remain unchanged. Existing
uncommitted progress was preserved; the index is empty. The seven-file worktree
scope is the three context documents, the new review receipt, results note,
crop proposal document, and crop proposal JSON. Nothing staged, committed, or
pushed. No operating point, quality gate, or model winner selected; all nine
old embargo output paths remain absent and all three holdouts remain sealed.

## Previous checkpoint: temporal execution awaiting visual review

Verified 2026-09-19 UTC (2026-09-18 America/Phoenix). Branch remains
`codex/ball-detector-baseline`, now at
`6769e07476da09d858fa42f82aace024d21f7735`:
`feat(ball-tracking): add approved temporal association experiment`.
Ryan separately authorized staging with "yes go ahead" and committing with
"yes commit". Exactly the validated 13-file scope was committed, with parent
`84bcc8da143e54ff17a28b39db0e70c4b8b299c8`; the resulting worktree was clean.
Nothing was pushed. This later progress note is intentionally uncommitted;
the index remains empty.

Ryan responded "lets move forward" to the linked temporal-association design.
This authorizes its six-window experiment; the exact statement, design hash,
and concrete specification hash are in
`configs/ball_tracking/reviews/rfdetr_medium_temporal_association_approval_v0_1.json`.
Do not request that experiment approval again. The new manifest is
`configs/ball_tracking/temporal_experiments/rfdetr_medium_temporal_association_v0_1.json`;
its specification SHA-256 is
`ef2f7a2a77f334c94d0efc045311c6fd4a3cc86695aec84934bacbfb06605ab5`.
It binds all six saved development outputs and the completed visual review.

The real dry-run, association, scoring, and rendering all completed at that
clean commit using the repository `.venv`. Association reused the six saved
development detection files: no new detector inference ran. All 54 declared
variants produced 324 observation files across 150 frames. Scoring produced
1,620 per-window reports and 270 aggregate cells per separate representative
and challenge pool. All 270 raw-control reports reproduce the prior detector
metrics and per-frame outcomes (the derived input count differs by design).
Matching uses raw center distance; annotation uncertainty is diagnostic only
and does not enlarge the localization radius.

The bound review bundle contains 12 slow comparison videos, 300 comparison
images, 1,800 native overlays, and 300 closeup sheets. All 2,412 assets passed
integrity verification. All original videos and their 12 separate H.264
playback copies decoded through all 25 frames. Agent visual inspection covered
the 12 final-frame closeup sheets, six windows at both display thresholds;
this does not claim a complete visual review of every video frame. Ryan's
review of the new temporal evidence remains pending. Earlier detector-review
approval does not approve these new temporal outputs.

At both predeclared display thresholds (0.20 and 0.35) and the raw 10-pixel
radius, the highest-confidence control retains more correct matches than
every tracklet variant in both pools. Tracklets remove some false guesses but
also suppress correct observations. P001 challenge frame 224 matches in raw
and top-one views but is missed by all four tracklet variants; P003
representative frame 324 is retained by the wider 0.03-step variants but
dropped by both tighter 0.01-step variants. These are descriptive development
results from short windows, not a selected winner or generalization claim.

Final focused validation passed all 25 new tests. The final full suite ran
324 tests in 147.691 seconds: 323 passed, one existing directory-symlink
capability skip. Both used the repository `.venv` with bytecode writing disabled.
`git diff --check`, new-file JSON/Python syntax and whitespace checks, and exact
13-file scope verification passed. The first full-suite run was deliberately
stopped after the synthetic preview prompted larger headings and moving
tracklet labels away from the ball marker; its partial result is not counted.
No association or scoring rule changed after validation. The exact committed
file hashes and Git blobs match the validated scope.

Generated validation artifacts are under
`data/outputs/ball_tracking/temporal_implementation_validation/` and stay ignored:
`focused_final.log`, `full_suite_final.log`, final synthetic preview PNGs, and
`validation_record.json` with output hashes and proposed file/Git-blob scope.
`staging_authorization.json` and `commit_authorization.json` record the later
Git steps. All 59 prior protected files and six raw detection files remain
unchanged, including the six annotation sets and their approval receipts.

Execution logs, `score_audit.json`, `missed_match_diagnostic.json`,
`review_bundle_verification.json`, playback copies, `results_summary.md`,
`review_guide.md`, and `execution_record.json` are ignored under
`data/outputs/ball_tracking/temporal_execution/6769e07476da/`.
The 324 observations and two scoring grids are under
`data/outputs/ball_tracking/temporal_association/rfdetr_medium_temporal_association_v0_1/`.
The review bundle beneath that directory is
`review/fa093f830294c6a4dd4259d318cdcf78/`.

The next action is Ryan's visual review of all 12 linked clips through their
final frames, using the guide's closeups to inspect dropped matches. Approval
records whether the evidence has been reviewed; it does not select a detector
setting, tracker, or quality gate. All nine old prediction paths remain absent,
all three test holdouts remain sealed, and no operating point or quality gate
is selected. No new staging, commit, push, PR, or merge is authorized by the
completed commit request.

The sections below are historical checkpoints. Their Git state, pending
implementation, annotation, and execution statements predate the work above.

## Current checkpoint: development experiment visually approved

Verified 2026-09-19 UTC (2026-09-18 America/Phoenix).

- Branch: `codex/ball-detector-baseline`.
- Exact HEAD: `84bcc8da143e54ff17a28b39db0e70c4b8b299c8`.
- Latest commit: `feat(ball-tracking): activate approved development evaluation`.
  Ryan separately approved staging the six release-checkpoint files, then
  authorized their commit with "yes you may chat". Exactly those six files
  were committed. Parent evidence commit:
  `9521569cab36c8d289c4a341b5f33273062cabb4`. Nothing was pushed.
- Clean-commit release validation passed against 59 protected file bindings.
  Detector dry-run preflight passed for exactly six development windows.
  The real frozen RF-DETR Medium run completed all 150 frames, with zero
  incomplete frames and 22,931 raw candidates retained at the 0.01 export floor.
  No labels, detector settings, or protected source/test files changed.
- Scoring created two separate 45-cell grids, containing 270 per-window
  evaluation reports in total. Representative labels have 75 eligible centers;
  challenge labels have 70 centers plus five reviewed hidden-ball frames.
- Both visual packages were rendered and passed bundle-integrity verification:
  150 synchronized comparison frames, 150 truth-region panels, 300 full-resolution
  overlays, and six 25-frame videos. Every final frame is present. All six
  videos were fully decoded for validation. H.264 playback copies are provided
  for app playback; original bound MP4V videos and PNGs are unchanged.
- Agent inspection covered all six final-frame closeups and selected P003
  occlusion-boundary images (164, 165, 169, 170). Ryan subsequently approved the
  six linked comparison clips: "the videos look good. they pretty much track
  the whole trajectory of the ball, with small little blips of possible
  detections. overall though it looks pretty solid to start". The new review
  receipt preserves this exact statement and binds both packages and all six
  playback clips. This is approval of the visual evidence as a starting point,
  not a quantitative quality gate or a claim of complete temporal trajectories.
- No operating point, quality gate, model winner, or generalization claim was
  selected. All three test holdouts remain sealed. The unchanged parent v0.1
  manifest retains nine embargoes and all nine of its old prediction paths
  remain absent. The six new versioned development outputs are the only newly
  generated predictions authorized by this release.
- Execution, scoring, and rendering all completed with a clean worktree at the
  exact activation commit. Later context, roadmap, and validation-history edits,
  the new visual-review receipt, and a temporal-association proposal remain
  uncommitted; the index is empty. Generated media/results remain Git-ignored.

### Results at the two predeclared display settings

Both use the protocol's 10-pixel localization tolerance with stored label
uncertainty. These are descriptive views, not selected operating points.

| Pool | Confidence | Correct matches | False guesses | Misses | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Representative | 0.20 | 47 | 105 | 28 | 30.9% | 62.7% |
| Representative | 0.35 | 39 | 12 | 36 | 76.5% | 52.0% |
| Challenge | 0.20 | 48 | 53 | 22 | 47.5% | 68.6% |
| Challenge | 0.35 | 41 | 9 | 29 | 82.0% | 58.6% |

P001 is the weakest possession in both displayed views. In P003's five
hidden-ball frames, the 0.20 view includes four false candidates across three
frames; 0.35 includes one false candidate. Frame 164 has an offset candidate
at 0.20 that still counts as FP plus FN under the displayed localization rule.
The six reviewed annotation sets, all approval receipts, the frozen parent,
and the historical pilot scoring report retain their original hashes.

### Evidence and exact next action

- Review guide: `data/outputs/ball_tracking/development_execution/84bcc8da143e/review_guide.md`.
  It links all six playback clips, every final-frame closeup, all-frame contact
  sheets, both full scoring grids, and their review manifests.
- Audited run record: `data/outputs/ball_tracking/development_execution/84bcc8da143e/execution_record.json`.
  This binds all detection/report/visual files and records the exact scope of
  agent image inspection. Its execution-time pending-review state is preserved;
  the later receipt below records completion. Runtime warnings are retained
  in the inference log; the installed source documents `_kp_active_mask` as a
  deterministic keypoint buffer. No package or model configuration was changed.
- Representative visual bundle:
  `data/outputs/ball_tracking/detection_review/rfdetr_medium_development_evaluation_v0_2_representative_evaluation_comparison/5ca366b16581f0a2156f1b64badd39e1`.
- Challenge visual bundle:
  `data/outputs/ball_tracking/detection_review/rfdetr_medium_development_evaluation_v0_2_challenge_evaluation_comparison/a8e607388bfbb511212b3956a63f55a3`.
- Human review receipt:
  `configs/ball_tracking/reviews/rfdetr_medium_development_candidate_comparison_review_record_v0_1.json`,
  SHA-256 `a60dea646736135620fb97eba9f1985f7b06f0c7bfc7abee38537580c05f4dba`.
  Its timestamp is receipt creation time, not an invented message event time.
  Both bundle-integrity checks, all six original/playback clip hashes, all 59
  protected file hashes/Git blobs, and all nine absent old outputs passed again.
- Candidate-availability diagnostic:
  `data/outputs/ball_tracking/development_execution/84bcc8da143e/candidate_availability_diagnostic.json`,
  SHA-256 `2bf4efc3bf94472c8f5411fd28194c72a308584ece6faab071841cb856cf55b3`.
  At the stored 0.01 floor and 10-pixel scoring radius, P001 has a qualifying
  candidate in only 10/25 representative and 18/25 challenge frames. These are
  label-assisted ceilings for retaining original candidate centers at those
  settings, not achievable tracking results. No inference or scoring was rerun.

Next: review the concrete design in
`docs/ball_temporal_association_experiment_proposal.md` and implement its
synthetic-first support before proposing a new execution manifest. It compares
raw candidates, a highest-confidence control, and causal tracklets using only
the six saved development outputs. No tracker has been implemented or run.
The completed visual review need not be requested again. The new proposal is
not an execution permit, operating-point choice, or quality gate. Keep all
holdouts sealed. Completed detector artifacts remain bound to `84bcc8d`;
inspect them without overwriting them or changing provenance to bypass resume
checks. No unrun manual command was left with Ryan. Staging, further commits,
and pushing need separate authorization. No production code changed this turn;
the existing full-suite result remains 299 run, 298 passed, one capability skip.

The release-preparation and annotation snapshots below are historical. This
section supersedes their old Git states and next-action instructions.

## Earlier release-preparation checkpoint

Verified 2026-09-19 UTC (2026-09-18 America/Phoenix).

- Branch: `codex/ball-detector-baseline`.
- Exact HEAD: `9521569cab36c8d289c4a341b5f33273062cabb4`.
- Commit: `feat(ball-tracking): add approved development evaluation support`.
  Ryan separately authorized staging the 35-file scope and then said
  "yes commit please". The commit contains exactly those 35 files; their
  working-file bytes were preserved. Nothing was pushed.
- The clean evidence commit passed release preparation using the repository
  `.venv` with bytecode disabled: full-suite return code 0, 299 tests recorded,
  all six annotation approval chains and 330 review assets verified. The
  validation report binds 59 protected code, test, label, receipt, and proposal
  files to the evidence commit's Git blobs.
- Ignored validation report:
  `data/outputs/ball_tracking/release_evidence/9521569cab36c8d289c4a341b5f33273062cabb4/validation.json`.
  Its copied evidence file has SHA-256
  `9a47a6c4e48a77cf0e91311faceae085956a61952ae01697064d0bf778ef03b4`.
- The approved preparation command created five new activation files: evidence
  copy, release receipt, v0.2 experiment manifest, and two pool review plans.
  Their hashes, approval/parent bindings, exact six-window scope, and global
  window/run/output uniqueness were verified. This context file is the sixth
  proposed release-checkpoint file.
- Current worktree: five untracked activation JSON files and this modified
  context file; the index is empty. No activation file has been staged or
  committed. Runtime release validation correctly refuses this uncommitted
  state before model construction.
- The parent v0.1 manifest is unchanged with all nine historical embargoes.
  None of its nine embargoed prediction files or the six new development
  prediction files exists. The new manifest names only the approved six
  development windows (150 frames); all three holdouts stay sealed.
  No operating point or quality gate was selected, and no real inference ran.

The next step is separate staging authorization for the six exact files below,
followed by review of their staged contents and separate commit authorization.
Ryan's experiment approval is already recorded; do not request it again.
After that activation commit, run the existing detector's dry-run preflight,
then the approved six-window experiment, separate-pool scoring, and both visual
review plans. Do not modify protected source/labels or relax any gate. Ryan
must review the resulting real visual evidence; push remains unauthorized.

### Proposed release-checkpoint staging scope

```text
configs/ball_tracking/reviews/rfdetr_medium_development_evaluation_v0_2_9521569cab36_evidence.json
configs/ball_tracking/reviews/rfdetr_medium_development_evaluation_v0_2_9521569cab36_release.json
configs/ball_tracking/experiments/rfdetr_medium_development_evaluation_v0_2.json
configs/ball_tracking/reviews/rfdetr_medium_development_evaluation_v0_2_representative_evaluation_comparison.json
configs/ball_tracking/reviews/rfdetr_medium_development_evaluation_v0_2_challenge_evaluation_comparison.json
docs/context/current_state.md
```

The checkpoint below records the earlier annotation/implementation work.
Its old HEAD, uncommitted status, and next-action statements are historical;
this section supersedes them. Always verify current Git state first.

## Earlier annotation and implementation checkpoint

Verified 2026-09-18 America/Phoenix (2026-09-19 UTC). This section supersedes
the historical snapshot below for session continuation.

- Branch: `codex/ball-detector-baseline`.
- Exact HEAD: `b7a887f55705623889625edf60028e2e39d38dc4`.
- Worktree intentionally contains uncommitted work. Preserve the existing
  working-agreement edit, six development annotation files, approval and
  finalization receipts, pilot review record, annotation initializer, and its
  tests. This context update is also uncommitted. Nothing is staged; no commit,
  push, PR, or merge was performed during this annotation continuation.
- All six representative/challenge development windows are labeled, visually
  approved by Ryan through their final frames, and finalized as `reviewed`.
  They use the established single-annotator visual self-review policy.

| Possession | Purpose | Inclusive frames | Labeled | Localization eligible | Not visible |
| --- | --- | ---: | ---: | ---: | ---: |
| P001 | Representative | 50–74 | 25 | 25 | 0 |
| P001 | Challenge | 200–224 | 25 | 25 | 0 |
| P002 | Representative | 250–274 | 25 | 25 | 0 |
| P002 | Challenge | 25–49 | 25 | 25 | 0 |
| P003 | Representative | 300–324 | 25 | 25 | 0 |
| P003 | Challenge | 150–174 | 25 | 20 | 5 |

The development sets total 150 labeled frames: 14 fully visible centers,
131 partially visible amodal center estimates, and five `not_visible`
occlusions. All 145 geometry points are localization eligible. There are no
unlabeled or excluded rows. P003 challenge frames 165–169 remain explicitly
occluded by the referee with null geometry; no interpolation crosses this gap.

### Evidence and validation at this checkpoint

- Annotation authority: the six `*_representative_evaluation_v0_1.json` and
  `*_challenge_evaluation_v0_1.json` files in
  `configs/ball_tracking/annotations/`.
- Approval authority: the matching frame-scoped `*_visual_review_approval_v0_1.json`
  and `*_single_annotator_finalization_v0_1.json` receipts in
  `configs/ball_tracking/reviews/`. Receipts bind the source, approved draft,
  visual bundle, and finalized file hashes to Ryan's actual approval statements.
- Finalization changed only `/review/status`, `/review/reviewer_id`, and
  `/review/reviewed_at_utc`. Every frame-level decision is unchanged.
- P003 representative final annotation SHA-256:
  `2b35475e715e9a4b816ad997b58be3201370695a2f420a35a6947696bbe3637e`.
- P003 challenge final annotation SHA-256:
  `ab77e6c8570ee8fc536632e43ee71d978e72cd16188f7564c77ae256873994ee`.
- Generated visual packages remain ignored beneath
  `data/outputs/ball_tracking/annotation_visual_review/`. P003 bundle IDs are
  `82e049e3ea6d16f944f1a64345ef7f692e285864edbf47ce3c27161cf35353bf`
  for frames 300–324 and
  `0c6b7ea0d768643f6f4b36d0151a40001d2b2b88f3dc2db5a091ec5b981fa35b`
  for frames 150–174. Their immutable snapshots correctly retain draft status;
  the receipts document the subsequent metadata-only finalization.
- The repository `.venv` with bytecode writing disabled passed strict schema
  and source-video verification for all six sets, the existing finalization
  receipt assertions for all six, and hash/size verification of all 330 review
  assets. This six-window audit completed; it was not merely proposed. At that
  annotation-only checkpoint, runtime code was unchanged and the full suite
  had not been rerun; the implementation checkpoint below supersedes this.
- The existing local pilot candidate-comparison review record reports Ryan's
  approval at `2026-08-24T05:05:09Z`. Its bound review plan, scoring report, and
  visual manifest still match their recorded hashes. The old snapshot's
  instruction to run the first pilot baseline is historical, not a current
  request to regenerate those artifacts.

### Prediction boundary and next action

All nine evaluation windows still have
`annotation_pending_prediction_embargo` in the unchanged v0.1 experiment
manifest. None of their nine declared prediction output files exists.
Completed annotation does not release predictions. No operating point or
quality gate was selected; no inference ran in this continuation.

Ryan approved the development experiment with "lets move forward I approve
of this experiment". The statement and immutable proposal-inventory hash are
recorded in
`configs/ball_tracking/reviews/rfdetr_medium_development_experiment_approval_v0_1.json`.
This authorizes implementation and the proposed six-window experiment once
its clean-checkpoint release conditions pass; it does not authorize staging,
committing, pushing, a holdout release, an operating point, or a quality gate.

Versioned support is implemented in `development_experiments.py`,
`development_release.py`, and `development_scoring.py`, with explicit v0.2
handling in the existing loader, runner, scorer, and visual renderer. The
strict six-window parent binding retains frozen detector settings and all
45 grid cells. Scoring produces two separate pools and 270 per-window results;
visual review produces one complete three-window package for each pool.
Synthetic tests use artificial frames and injected adapters only.

The release verifier checks approved labels and assets during evidence
preparation. At runtime it checks the release receipt and committed Git blob
identities without opening annotation JSON or review images. Evidence belongs
to a future clean commit; activation artifacts belong to a later separately
authorized commit. The new executable manifest and its six prediction outputs
remain absent. All nine original embargoed outputs remain absent. Existing
uncommitted files and the old manifest are preserved.

Implementation validation completed using the repository `.venv` with bytecode
writing disabled. The 14 new development tests, 10 existing detector visual
review tests, and 27 independent-review tests passed. The final full suite ran
299 tests: 298 passed, one existing directory-symlink capability test skipped.
`git diff --check` passed; new untracked Python syntax and whitespace checks
also passed. The ignored full-suite log is
`data/outputs/ball_tracking/development_implementation_validation/full_suite_20260919_retry.log`.
The first full run exposed an old independent-review test fixture with a fixed
August review timestamp earlier than its newly generated September creation
time. The fixture now derives its timestamp from creation; production review
rules and annotation data are unchanged. The full suite then passed.

The audit reverified all 24 approved inventory bindings, the frozen parent
hash, all nine original absent prediction outputs, and the six absent new
outputs. The existing working-agreement edit retains SHA-256
`55eb9c73c29c3f6f8c8e6c30d8caa1e9506adbded15a57e813b76f4c6fe13be3`.
No operating point or quality gate was selected; no real model inference ran.
The new source code remains uncommitted, so this successful implementation
validation is not a clean-commit release receipt.

The next external boundary is separate staging authorization for the exact
35-file list in the proposal document, then separate commit authorization. The approved experiment does not need approval again.
See `docs/ball_detector_development_release_proposal.md` for the checkpoint
procedure. Keep all three test holdouts sealed.
No development-window visual approvals remain unresolved, and no manual
commands were supplied but left unrun. The existing annotation editors may
still be open; their now-reviewed files must not be edited as drafts.

## Historical snapshot retained for provenance

The sections below describe the earlier checkpoint. In particular, their
inference and annotation to-do lists predate the local evidence above.

Snapshot date: 2026-08-23 (America/Phoenix)

## Repository checkpoint

At the current ball-detector precommit checkpoint:

- branch: `codex/ball-detector-baseline`;
- development base: `51c084c6dc8a11df883db6780a9a024d9506e5bf`
  (`feat(ball-tracking): add reviewed annotation foundation`);
- the strict RF-DETR Medium image-only adapter, resumable inference runner,
  experiment-manifest contract, source verification refactor, and regression
  coverage are implemented;
- Ryan approved nine prediction-blind evaluation windows across the same three
  possessions, and their reproducible selection record is frozen in
  `docs/ball_detector_baseline_selection.md`;
- only the three reviewed protocol pilots are marked `ready_for_inference`;
  all nine new windows remain `annotation_pending_prediction_embargo`;
- focused ball source/detector tests: 129 passed, with one Windows
  symlink-capability skip;
- full test suite: 264 passed, with the same one skip and bytecode writing
  disabled;
- no manifest-authorized baseline run or prediction on any of the nine approved
  evaluation windows has been generated; the quarantined historical exploratory
  prediction at Possession 001 frame 150 remains explicitly excluded.
- the real installed RF-DETR class mapping and a non-inference construction of
  the frozen CUDA model both pass the adapter contract; no video frame was
  supplied.

The preceding durable migration checkpoint was:

- branch: `main`;
- local HEAD and `origin/main`: `1f086ba` (merged PR #7, **Add durable desktop project context**);
- PR #6's thorough README update is included;
- the local and remote `docs/desktop-context-migration` feature refs are deleted;
- worktree: clean;
- all eight durable context files match the reviewed migration proposal;
- full test suite: 56 tests passed using the desktop app's bundled Python, with bytecode writing disabled.

Future work should still begin by checking the current branch, HEAD, worktree, and remote state rather than assuming this snapshot remains current.

## Completed technical foundation

- RF-DETR Medium person detection and ByteTrack multi-object tracking.
- Playable-court filtering and tracking audits.
- Uniform-feature team classification.
- OSNet-AIN ReID embeddings, temporal segmentation, segment reconciliation, and reviewed consolidation.
- Exactly ten persistent player identities, with five white and five dark players in validated possessions.
- Reference court calibration and one homography per decoded frame.
- Player floor-point projection to court coordinates.
- Conservative trajectory refinement and bracketed internal-gap interpolation with provenance.
- Configuration-driven, possession-scoped, resumable 21-stage orchestration.
- Explicit identity and calibration review gates.
- Multi-possession empirical generalization gate passed on Possession 003.
- Reviewed ball-center annotations for three 25-frame protocol pilots, plus a
  strict raw-detection and evaluation data contract.
- A precommitted, label-blind RF-DETR Medium ball-detector baseline contract with
  exact runtime provenance, raw-candidate preservation, resumability, and
  prediction embargoes.

## Not complete

- real ball-detector inference, scoring, temporal tracking, and their quality
  gates;
- automatic possession segmentation and broadcast-cut handling;
- ball-handler and event inference;
- mapping visual identities to NBA rosters;
- primary-defender, switch, help, and contest inference;
- the defensive scoring model;
- complete-game NBA validation and reporting.

## Immediate next task

The annotation contract, detector adapter/runner, experiment contract, scoring
grid, and prediction-blind window selection are complete. The next operational
sequence is:

1. from a clean committed snapshot, run the runner's read-only preflight and
   confirm the exact source clips,
   RF-DETR package, official weight bytes, CUDA runtime, ignored outputs, and
   three authorized pilot windows;
2. run the first descriptive baseline over only the three reviewed pilot
   windows, preserving every exported COCO `sports ball` candidate at or above
   the frozen `0.01` export floor;
3. inspect and score the fixed confidence/localization grid on those pilots;
4. annotate and review the six representative/challenge windows, then use a
   reviewed, versioned schema/manifest release instead of toggling v0.1 in
   place; freeze an operating point before separately releasing the three test
   holdouts;
5. render candidate-versus-truth evidence before proposing a temporal tracker
   experiment or any detector quality gate.

No ball-tracking implementation was started in chats 01–06. The prior blocker was intentionally removed only after Possession 003 passed the generalization gate.

### Ball-tracking annotation checkpoint

- The v0.1 annotation schema, prediction-blind editor, source verification,
  neutral review assets, visual-review renderer, and detection-evaluation
  contract are implemented on `codex/ball-annotation-foundation`.
- Possession 001 frames 375–399, Possession 002 frames 318–342, and Possession
  003 frames 416–440 each contain 25 completed annotations and are
  single-annotator, visually reviewed reference sets. Ryan approved all three
  bound visual-review packages through their final frames.
- Across the three windows, all 75 frames are labeled: 67 contain geometry, 66
  are localization eligible, eight are reviewed `not_visible` negatives, and
  one visible ambiguous frame is intentionally unscored.
- Possession 002 contains 17 geometry estimates, of which 16 are localization
  eligible, plus eight reviewed `not_visible` occlusion frames. Missing geometry
  remains explicit and un-interpolated.
- Possession 003 contains 25 continuous geometry points: five fully visible
  observed centers and 20 partially visible amodal estimates. All 25 are
  localization eligible; no geometry gap or interpolation is present.
- Duplicate or independent annotation is not a prerequisite for review or the
  current milestone. It remains optional for a specifically declared
  inter-rater or intra-rater reproducibility study.
- The protocol-declared synthetic evaluator cases pass. The raw, image-only
  detector export harness and precommitted experiment manifest are implemented.
  The next runtime task is the clean preflight and three-pilot descriptive run,
  not temporal tracking yet.

## Local data checkpoint

At migration time, the ignored `data/` tree contained 856 files totaling
6,710,202,697 bytes, all successfully SHA-256 hashed in the external manifest
`manifests/local-data-files.csv`. The ball-annotation workflow subsequently
added ignored review assets beneath `data/outputs/`; that migration-era count
is therefore historical, not the current tree total. All three source clips
still match their declared hashes, and generated review media remains ignored.
