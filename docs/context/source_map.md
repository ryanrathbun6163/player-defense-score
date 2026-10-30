# Source Map

## Wider-input pilot completed; ranking gain, no replacement, 2026-10-30

Ryan authorized implementation and execution of the reviewed dual-view experiment.
All eight six-epoch fits, final scores, CPU analysis and independent audits are
complete. See [the results](../ball_tracking_dual_view_context_results.md) and
configs/ball_tracking/reviews/dual_view_context_result_v0_1.json. Reuse these
outputs; the earlier design/unrun status is superseded. No model, selector,
threshold or replacement of saved J is adopted.

Held-NBA full-pool strict-first ranking is LC 2609/2811 (92.81%), Q 2542, LL 2551:
LC gains 69/loses 2 versus Q and gains 61/loses 3 versus LL. This is diagnostic
ordering, not emitted tracking accuracy. Both fixed-zero gates FAIL: LC loses
23 LL-kept correct policy identities; protected Q losses are 14 policy identities
and 1 weak candidate, with 0 HOU stress losses. Protection sets overlap. Saved J
remains stronger: fixed original-Q-top 2541/2811, versus LC 2317. Its fixed-choice
ceiling is 2542; acceptance alone cannot reach 95% on those original choices.

Of net 67 ranking gains versus Q, 66 occur on already-native-correct frames.
The sole native-missing gain remains LC-negative; no native-wrong case improves.
LC has no newly correct J-rejected fixed choice on held NBA or BKN. All LC fitting
targets have correct signs, so the model learned its fitting objective; the
remaining failure mechanism is not uniquely identified. BKN stays exposed
diagnostic/nonfitting, HOU veto/descriptive only, NFHS secondary, DET metadata-only.
Scorer-held NBA games were already seen by the detector; no global 95% claim.

The initial run stopped because a copied event watcher retained the old 30-minute
deadline, not because of a reported GPU fault. The failed attempt is preserved.
Shared-deadline repair and exact SAC-LC epoch 3 continuation reused five completed
fits and all captures. All 67 necessarily replayed loss/gradient-norm values match
exactly. Actual work: 28149 calls/899618 presentations/19807 updates, published
separately from logical 28082/897474/19740. Both launch charges total 48m03.516s,
within the original 90-minute allowance; CPU repair downtime is separate. Final
cleanup is clean, no qualifying fault, peaks 64 C/63 C, no GPU setting change.
True Color remains permitted; standing Debug Mode ON and other guards remain.

Next: CPU-only source/annotation feasibility and design for diverse actual
current-detector failures on additional permitted NBA games, correct controls
and separate evaluation. The old coverage census, 461-point Q+ addition, rank
overlap and curves are already complete; do not repeat or blindly tweak them.
More support is a justified priority, not a proven cure. No new fit, labels,
protected access or source-role reassignment follows automatically.

All 174 inherited working-file contents remain preserved through 165 unchanged
files and 9 reversible history additions. Both final audits pass; original
failure/auditor-correction evidence remains. Branch/HEAD and empty index remain
unchanged. This entry is the current completion and next-step state.


## Controlled wider-input pilot designed, 2026-10-30

Ryan requested an exceptionally critical, informative design. The concrete
[protocol](../ball_tracking_dual_view_context_protocol.md) and its machine-readable proposal are ready; three independent reviews
passed. Implementation, feature capture, fitting and scoring remain unrun.

Two matched arms compare duplicate-local LL with local-plus-192px-context LC.
Both retain frozen fold-specific Q local features, use the same generic DINO
auxiliary final-two-block adaptation, and learn a fresh point+CLS fusion head.
Saved Q/J remain separate controls. Extra capacity/training is controlled; field
of view and auxiliary scale still change together. Frozen features do not promise
preserved predictions. Saved-logit saturation ruled out a zero-residual primary
test; 7,426 existing distant negatives contain the reference center in the wider
crop, supporting explicit checks against accepting the wrong nearby point.

Eight fixed six-epoch fits are proposed: 19,740 updates; total future capture,
training/scoring/parity budget 28,082 backbone calls / 897,474 presentations.
Final fitting-health scores, full-pool ranking, fixed-zero policy gains/losses,
all protected Q successes and comparison to saved J are required. Fixed Q-top
choices have a 2,542/2,811 ceiling; filtering alone cannot reach 95% there.
No result may silently become a new threshold, selector, J substitution or fit.

Next is implementation of this exact protocol, CPU checks and executable freeze;
new neural execution is not authorized by design alone. BKN remains exposed
diagnostic/nonfitting; HOU remains veto/descriptive, never positive feature choice.
DET is metadata-only with no new query. Existing labels/results/hardware policy
and all 172 inherited contents remain preserved. See the design evidence under
data/outputs/ball_tracking/dual_view_context_design_v0_1/ and its design_freeze.json.
Every subsequent recommendation must state useful outcomes and limits before
running; failure need not uniquely identify a cause to supply bounded evidence.


## Input-context information screen completed, 2026-10-30

The authorized CPU screen is complete: 100 candidate points on 69 saved frames,
exact original local input versus unchanged local plus fixed 192px context.
See [the completed report](../ball_tracking_input_context_screen_results.md) and configs/ball_tracking/reviews/input_context_screen_result_v0_1.json.
Two score/reference-blind AI reviewers supplied 400 sealed qualitative ratings.
Four qualifying points on three frames in two frozen failure intervals gained
concrete cues; all are within one two-second BKN clip. All 46 jointly recognized
matched balls retained visual support. Eleven cases remain jointly unresolved.
This is limited input-information evidence, not model accuracy or a gain toward 95%.

Next: design one bounded close-up-plus-context representation pilot; preserve
the existing model/control and exact-success/hidden/weak-recovery protections.
No recipe, fit, new score or selector has run. BKN remains nonfitting; HOU can
only provide descriptive/regression-veto evidence, never positive feature choice.
SAC prior-AI illustrations are nondecision; DET was not opened. The stronger HOU
role was clarified additively before paired review; earlier flags stay archived.
Two focused tests and independent 3243/5464-check audits passed. Existing results,
references, checkpoints, original handoff and GPU operating policy stay intact.
This entry supersedes the unrun context recommendation; do not repeat the screen.


## Fresh-game diagnostic completed; True Color may remain running, 2026-10-30

Ryan clarified that closing True Color was only a temporary GPU troubleshooting
trial. History confirms no causal attribution. Retire that blanket absence
requirement; do not ask him to close it simply to run this experiment. Record
its actual presence and retain other hardware, worker, temperature and fault
checks. Five prior post-cable workloads completed cleanly over 55 minutes; that
does not prove a single hardware cause. Debug Mode remains required ON.

The approved fresh-game run and CPU analysis are COMPLETE. See the
[results](../ball_tracking_fresh_game_diagnostic_results.md) and
[all360-frame source/exact-input viewer](../../data/outputs/ball_tracking/fresh_game_diagnostic_v0_1/diagnostic_review/index.html).
True Color PID 20968 was observed before and after the clean 67.843-second run:
peak 54 C, no qualifying faults, no retry and zero remaining owned workers.
All 354 detector forwards,109 Q batches and 3480 J predictions completed once.
No fitting, new labels, thresholds, selectors, protected access or adoption.

Accepted population:310 eligible/32 certain-hidden/18 unknown. Correct/wrong/hidden
counts: native 298/6/2; native+Q 289/1/1; native+J 298/4/2; fixedQ-top 294/16/32;
Q-top+Q 290/10/2; Q-top+J 293/2/2. J retains every correct native point but still
emits wrong/hidden points. The 96.13% native result is conditional on three short
clips from one game, not attainment of the global 95% goal. Old reported results,
failed Q+ decisions and game roles remain unchanged.

The complete pool supports 305/310 eligible frames. Of 12 native failures, five lack
a matching proposal and seven have one. Six are weak-only;237/47 also has matching
unselected native components. RawQ-top gains 4 correct identities but loses 8.
Actual crops show spectator-head ranking errors, hand/ball confusion and hidden
emissions. Use these exact current-model cases alongside historical failures to
design the next discriminating comparison; no automatic unchanged fit/max-J/
native-first adoption follows. Reuse all saved outputs; do not rerun this study.

Independent neural/output and analysis audits passed 58452 and 321647 checks;
all 360 illustrations are saved and 974 exact-Q-input comparisons passed. A
corrected auditor cache-shape assumption is preserved without any scientific
rerun. All prior 166 contents are retained via 157 unchanged files and 9 reversible
documentation additions. Branch/HEAD and empty index remain unchanged. This
entry supersedes earlier pending-label, unrun and TrueColor-blocker statements.

## Fresh-game references accepted; implementation ready, 2026-10-30

Ryan accepted all three new reference sets and authorized continuing: "ok I've
reviewed them. Move forweard chat". See the [execution preparation state](../ball_tracking_fresh_game_execution_preparation.md).
The separate accepted publication contains 360 AI-authored, human-accepted
frames: 310 eligible centers, 32 certain hidden and 18 unknown. Original proposals
and review media remain unchanged. No repeat reference or experiment approval
is needed. The whole game remains diagnostic development, ineligible for fitting
or checkpoint selection.

Frozen saved-model inference and CPU analysis are implemented; 27 focused tests
and independent implementation review passed. Source-only caches are complete.
No model has run on this sample and no new accuracy result exists. Fresh readiness
stopped before launch: Lively was closed, but protected MSI True Color PID 20968
returned Access is denied and still needs Ryan to quit it. Debug Mode was restored
from OFF to ON under the standing instruction; preserve the truthful setting-change
receipt. Additive readiness v4 narrowly recognizes the observed X-VPN desktop GPU
child; 18 fixture checks passed, with original helper/freeze/rejection preserved.

Next: verify True Color is closed, obtain fresh Debug-ON and readiness evidence,
then run the existing supervisor once. Reuse accepted/reference.json,
inference_preparation/prepared.json, execution_freeze.json and the completed
readiness amendment under fresh_game_diagnostic_v0_1. Do not repeat preparation,
fit models, change selectors, reopen protected sets or claim progress toward 95%.
After clean execution, finish saved-output audits, full analysis and visual review.
All prior 160 file contents remain preserved through reversible additions; Git
branch/HEAD and empty index are unchanged. This entry supersedes the pending-label
and not-yet-implemented state below while retaining it as history.

## Fresh-game diagnostic: new reference review ready, 2026-10-30

Ryan approved moving forward with the bounded fresh-game diagnostic. See the
[preparation result](../ball_tracking_fresh_game_reference_preparation.md) and
[fixed protocol](../ball_tracking_fresh_game_diagnostic_protocol.md). Three
source-first BKN-DET clips (122/237/365, game 0022400861) supply 360 native frames:
310 AI-proposed centers and 50 null centers. All new labels remain pending human
acceptance; no detector/scorer inference, training or adoption occurred.

Complete native/slow overlays, original-frame viewers, exceptions and actual
finals are ready under data/outputs/ball_tracking/fresh_game_diagnostic_v0_1/review/.
All 360 source PNGs match alternate RGB decoding; 12 focused tests and all 720
encoded-frame checks passed. Prior 155 file contents/results remain preserved.
The actual next step is Ryan's review of this concrete new reference set, then a
separate accepted publication and implementation/run of the frozen diagnostic.
The experiment itself is already authorized; do not request its approval again.
The new whole-game role is diagnostic_development, ineligible for fitting or
checkpoint selection. Existing game roles and the failed Q+ result stay unchanged.


## Producer-transfer experiment completed; criterion failed, 2026-10-29

Ryan explicitly authorized implementing and running the designed experiment,
building on saved work and preserving all results. See the
[completed result](../../docs/ball_tracking_candidate_producer_transfer_results.md) and [result ledger](../../configs/ball_tracking/reviews/candidate_producer_transfer_result_v0_1.json). This supersedes
the earlier unrun progress statements below; original design and results remain.

One Q+ treatment added the 461 audited compatible points to the original NBA
population, retaining the original model, objective function and matched budget.
All four fits completed once: 9,870 updates / 315,432 training presentations;
1,014 scoring forwards / 32,341 presentations; four parity calls / 128 points.
Total 10,888 neural forwards / 347,901 presentations. Saved Q controls were
reused; no detector calls, J fits, new labels, protected access or adoption.
The supervised launch took 1,181.296 seconds, peaked at 63C, and ended with no
faults, settings changes, retry or surviving owned process. Debug Mode was ON.

The prespecified fixed-zero criterion FAILS. NBA native correct retention fell
2,309 -> 2,238, with wrong/hidden remaining 0/0. Fixed original-Q-top correct
retention fell 2,275 -> 2,215, wrong 99 -> 90 and hidden 28 -> 27. Correct retention
fell in every held NBA game; CHI and DEN gained wrong acceptances. HOU native
correct rose 798 -> 808 (0/0 errors/hidden), but quality-top rose 825 -> 836 with
wrong 6 -> 8 and hidden 3 -> 4. Net gains cannot conceal exact-success losses.
The protected sets lost 189 fixed-policy rows (182 NBA, seven HOU), 20 weak
candidate rows and four HOU stress probes. These views overlap; do not add them.

Source-held added challenges showed only positive 44 -> 45 (four gains, three
losses); distant-negative acceptances stayed 35 and hidden acceptances stayed 38.
Diagnostic strict-match-first frames fell NBA 2,542 -> 2,534 and HOU 862 -> 855;
NFHS rose 115 -> 118. Full curves contain crossing tradeoffs, so this is not a
claim that every operating point or every aspect of discrimination worsened.
No threshold is selected and no curve rescues the failed fixed-zero criterion.
The exact 21/6 named recovery-query Q signs remain unchanged (13/21 and 2/6
positive), while broader cases include regressions. All missing and historical
roles, complete contrasts and successful/failed evidence remain preserved.

All 45 focused checks passed. Independent neural and analysis audits passed
271,004 and 7,072,931 checks. Two audit-tool representation corrections and their
failed receipts are retained; no scientific output changed or neural work repeated.
The old caches remain unchanged; only 452 new crops were made from 385 PNGs,
and nine additions reuse old pixels with different fractional point inputs.

Keep Q/J controls and the prior reported J quality-top 90.39% result unchanged;
this run adds no gain toward 95%. Do not substitute Q+ into frozen J or launch an
automatic threshold/seed/weight/pool/epoch tweak. Failure is specific to this
population/weight/exposure intervention, not proof that all augmentation or image
representations fail. Any subsequent direction must reconcile this result with
the full prior history and research and identify new information before another fit.

All 147 inherited file contents are preserved: 138 unchanged, nine reversible
history additions, eight new source/test/report/ledger files = 155 current paths.
See data/outputs/ball_tracking/candidate_producer_transfer_v0_1/ for the run,
analysis, independent reviews and documentation_update preservation receipt.
Original handoff/Session 17 chain, branch/HEAD and empty index remain intact.



## Producer-transfer experiment designed, 2026-10-29

Ryan's latest "ok chat move forward" continued the bounded design recommended
after the completed alternate-producer coverage study. See the
[producer-transfer protocol](../../docs/ball_tracking_candidate_producer_transfer_protocol.md) and
[machine-readable proposal](../../configs/ball_tracking/proposals/candidate_producer_transfer_v0_1.json). Design and saved-metadata preparation
are complete; implementation, training and new scoring remain unrun.

Compare the original image-quality model Q with one Q+ treatment: retain all
18,813 original NBA candidate records and add the 461 audited compatible points
(304 distant negatives, 81 certain-hidden negatives, 76 weak positives).
All 3,179 frames, 3,433 original positive candidates and 610 weak positives remain.
No new scenes or labels; the million-point alternate pool is not a fitting pool.
Four future fits use the original representation, weighted objective function,
initialization and optimizer. Six frozen sampled cycles exactly match the old
9,870 updates / 315,432 training presentations; every eligible old/new example
appears. Reuse saved Q controls without refitting. Added all-NBA objective mass
is 8.46924%; weights, exposure, concentration and displaced old presentations
are explicit. Scoring and four parity calls bring the future total to 10,888
neural forwards / 347,901 candidate presentations; this is a budget, not a run.

Freeze original native and original-Q-top identities. Require per-game NBA
nonregression in correct, wrong and hidden outcomes, zero lost protected correct
identities, and a strict primary gain. Keep HOU as an exposed regression veto,
not fitting or threshold selection. A newly declared stricter veto also protects
every old-Q-positive known-correct weak point, including unchosen alternatives.
Retain all 21 HOU recovery cases, the six below-.01 cases, missing slots and
historical semantic roles. No threshold rescue, reranking, fallback or trajectory
claim. Saved acceptance model J is contextual only: changing Q would also change
J's input distribution, so integration requires a later valid design.

This isolates training-population transfer, not detector replacement. Of the 76
alternate recovery frames, 75 already have correct current native choices; the
other lacks original positive support but is not the current missing-native case.
The older producer natively recovers none of the four current wrong/missing cases.
CHI supplies 56/76 positives; DEN has one added hidden point; dense proposals can
produce chance geometric matches. No improvement toward 95% has been measured.

The accumulated history/research review was reused with targeted original
reports/code and primary research on decoupled classification, failure-directed
training and nested stacking. Independent population, workload, evaluation and
design reviews passed. Next is implementation of this fixed comparison with
focused checks and fresh supervised execution readiness; no extra arm, automatic
retry, settings change, new protected access or Git integration is included.

All 145 inherited file contents remain preserved: 136 unchanged and nine exact
reversible documentation additions; the new protocol and proposal make 147.
See data/outputs/ball_tracking/candidate_producer_transfer_design_v0_1/ for the
finite manifests, reviews and documentation_update preservation receipt.
Original handoff/Session 17 chain, branch/HEAD and empty index remain intact.



## Alternate-producer coverage capture completed, 2026-10-29

Ryan's "ok chat move forward my man" authorized implementing and running the
fixed capture from the completed coverage review. See the
[audited result](../ball_tracking_candidate_proposal_coverage_report.md) and
configs/ball_tracking/reviews/candidate_proposal_coverage_v0_1.json.
This supersedes the earlier proposed/unrun progress statements retained below;
the original protocol and all prior scientific results remain unchanged.

The expanded-NFHS checkpoint completed exactly 3,137 canonical 768x432 forwards
on all 3,179 accepted NBA training frames / 21 blocks. Zero imports, extra parity
forwards, fits, optimizer updates, new labels, selectors or protected evaluation.
Full means and uncapped pools were sealed before joining accepted references.
Capture 236.36s; charged supervised launch 288.75s; maximum 59C; no faults, settings
changes, retry or surviving owned processes. Debug Mode was freshly observed ON.

Both predeclared raw and conservative role/input-screened coverage gates PASS.
Raw chosen known-distant errors 305 -> screened 304; native-hidden 81; weak positive
with that producer wrong/missing 76 (67 wrong, 9 missing). Each combined required
category spans all 3 games and survives every intended outer training fold.
The usable exact-new union is 461 points on 394 existing frames, 18 blocks, 70 physical
consecutive runs: 452 new floor-centered crops and 9 existing crops with different
point readouts. One historical-frame role conflict is excluded; old roles and
unknown targets remain unchanged. Runs do not establish independent plays.
DEN contributes only 1 native-hidden frame; CHI supplies 56/76 weak recoveries.

Counterevidence must remain prominent. The pool has 1,091,879 candidates versus
18,813 current (~58x); only 0.0422% meet the combined required-case/novelty/role
screen. Alternate native choices are 2425 correct / 308 wrong / 81 hidden versus current
2807 / 3 / 2 before J; 382 current-native successes are lost, 180 current-positive pool
frames are lost and only 1 is added. It natively recovers none of the 4 current
wrong/missing cases. Of 76 producer-relative recovery frames, 75 already have a
correct current-cosine choice. The current-policy failure population remains
4 CHI frames, with no fresh-scene or cross-game current-policy coverage claim.
All 610 original weak positives and all 21 HOU external recovery cases, including
6 below-.01 cases, remain preserved regression evidence. No HOU fitting/evaluation
was added. No tracking gain or progress toward 95% is claimed by this data test.

Next is a bounded producer-transfer DESIGN: isolate added role-compatible
examples while retaining successful controls, original representation/objective,
downstream policies and per-source retention/hidden/recovery vetoes. Do not feed
the million-point pool wholesale, swap detectors, fit automatically or sweep
thresholds/checkpoints. New permitted footage remains the direct alternative for
current-detector failures on fresh scenes; representation/visibility diagnostics
require a specific new information hypothesis. Existing context/temporal/point
and origin-ablation evidence plus freshly checked primary research constrain
the recommendation. Ryan's standing due-diligence requirement continues.

All 23 focused checks and independent implementation/capture/analysis audits
passed. Saved means/extraction and all contributor identities are audited;
discarded raw forward channels cannot be numerically reaveraged postrun.
Float32/order reduction is supported by meaningful synthetic tests of the
unchanged reducer. An initial metadata-only source race was preserved and fixed
before successful CPU compatibility/freeze; no neural attempt was repeated.

The inherited 138-file worktree is preserved: 129 files unchanged, 9 maintained
documents receive exact reversible additions, and 7 new source/test/config/report/
ledger paths make 145. Original handoff/Session17 history, branch/HEAD and empty
index persist. No Git integration. Continue from the new result/ledger and the
documentation_update preservation receipt; do not restart completed studies.


## Coverage review completed; due diligence reaffirmed, 2026-10-29

Ryan directed the coverage/design check and reaffirmed critical due diligence
for every recommendation. See [the coverage decision review](../ball_tracking_candidate_training_coverage_review.md) and
configs/ball_tracking/reviews/candidate_training_coverage_review_v0_1.json.
This is a completed saved-metadata review, not another training/capture run.

All 3,179 accepted NBA training frames are already used. The 70 known native
distant-negative candidates are all unchosen alternatives; all three actual
wrong native choices remain boundary-unknown for fitting. Native-hidden support
is one adjacent CHI two-frame interval. Of 610 weak positives, 609 accompany
native success; one accompanies native missing and none native wrong. Actual
leave-CHI-out fitting lacks each of these decision-relevant cases despite real
weak-hidden training support. Existing broad objective balancing is preserved.
This is a conditional support gap, not proof that visual coverage causes errors.

Saved older locally NBA-untrained SAC proposals were checked against the same
accepted 300 frames. They add 23 unchosen negative coordinates on 19 used frames,
but zero selected known wrong/hidden points; 17 coordinates lie outside both
compared current/historical crop registries. Different coordinates are not new
scenes. A SAC-trained older checkpoint adds two adjacent selected wrong points
with same-source exposure. No unused accepted hard-case scene bank was found.
All 21 HOU external weak recoveries remain, including six below-.01 cases;
HOU is an exposed regression veto, not a fitting/sampling repair source.

Next proposed experiment is one alternate-producer coverage capture using the
existing expanded-NFHS checkpoint, on the 21 accepted NBA training blocks only:
3,179 frames, 3,137 canonical768x432 forwards, zero assumed imports, zero fits.
The old512x288 SAC caches remain diagnostic evidence and cannot be imported by
PNG identity. Local NBA nonexposure does not certify global pretraining history.
The separate protocol fixes producer-relative coverage checks before outcomes;
new proposals cannot manufacture cross-game current-cosine recovery failures on
these fixed frames. Passing permits only a later producer-transfer design.
The capture is proposed, unimplemented and unrun; no launch readiness is claimed.

For every recommendation, carry forward the maintained session history and
decision-relevant primary evidence; disclose what was freshly read versus reused.
Check relevant primary research when it can affect the decision. State what
actually changes, meaningful alternatives and counterevidence, assumptions and
limits, the question answered, and proportionate stop/continue criteria before
costly execution. Establish genuine novelty; do not repeat completed experiments
or rename an existing recipe. Challenge important recommendations independently
when useful. A negative experiment can be informative, but audit counts and
activity are not tracking progress. Do not turn this into an endless review or
duplicate-permission loop; existing authorization and routine autonomy persist.

No model load, inference, optimizer update, GPU query, image decoding, new label,
protected access, selector/threshold adoption or Git integration occurred.
The nine maintained files receive exact reversible additions; 126 other prior
files remain unchanged. Three new report/protocol/ledger files make 138 current
worktree paths. The documentation_update receipt preserves all135 prior contents
and the original handoff/Session17 chain. Branch/HEAD/index remain unchanged.
Existing NBA roles, accepted uncertainty, 95%/1%/zero-hidden, temporal/recovery
and human-review gates stand. Quality-top's90.43% ceiling remains a separate
selection problem; this review does not claim a tracking accuracy gain.



## CPU origin ablation completed and audited, 2026-10-29

Ryan authorized the recommended one-change CPU comparison. Four new fits remove
the two explicit origin indicators while reusing all saved detector scores,
feature registries, splits, targets, weights and fixed candidate choices.
The first attempt completed in 19.735 seconds; no neural call or GPU query.
See [the origin-ablation results](../ball_tracking_candidate_acceptance_origin_ablation_results.md) and the ledger
configs/ball_tracking/reviews/candidate_acceptance_origin_ablation_result_v0_1.json.

Removing these indicators does not improve this recipe. At zero, held NBA native
J -> A is 2,806 -> 2,798 correct with the same three wrong/two hidden emissions;
quality-top is 2,541 -> 2,539 correct, 34 -> 48 wrong and eight -> nine hidden.
There is no strict NBA fixed-zero gain; ten exact J-kept correct policy points
on eight distinct frames are lost. The full unselected curves also mostly favor
J for NBA quality-top.
HOU is mixed: native 841/18/18 -> 840/17/16 and quality-top 855/4/14 -> 858/5/16
(correct/wrong/hidden). e01 quality-top recovery improves six -> nine of ten,
and exact stress six -> eight of ten, still below original Q's ten. Three frozen
HOU policy identities and six stress identities are lost; overlapping views
are not additive. Both predeclared criteria fail. No arm, cutoff or selector
is adopted; original J also remains an unadopted experimental comparison.

25 focused tests pass. Independent audits pass 3,072,793 output checks and
2,773,690 saved-model checks. All 31,430 slots, 11 missing scores, 4,289 context
frames, 8,578 fixed-policy rows, 6,720 choices/contrasts and 60 historical rows
remain; A adds 3,270 zero tables and 143 complete unselected curves. Retained
scalers and fitting arrays reconcile with J. No old experiment was rerun.

This rejects removing the two indicators as the repair for this recipe, not all
origin-aware methods or a causal hypothesis. Correlated cues and sparse native
negative/hidden support remain. Quality-top's 2,542/2,811 ceiling is unchanged;
this experiment does not move the 95% milestone. Next is a separate bounded
design addressing native-negative support/objective balance from NBA fitting
evidence, with retained J as a comparison; no weighting, schema, routing or
training follow-up has been run. Exposed HOU cannot choose a repair. Existing
roles, accepted labels, numerical/temporal/human gates and protected closure stand.

All 125 prior worktree contents are preserved through 116 unchanged files and
nine reversible insertions; ten new files make 135 current worktree paths.
The preparation/documentation_update receipt continues the original handoff and
Session17 chain. Branch/HEAD/index remain unchanged. The authorized comparison
is complete. No new labels, settings change, protected access or Git integration.



## Candidate acceptance experiment completed and audited, 2026-10-29

Ryan authorized moving forward with the reviewed acceptance experiment.
Implementation, the fixed new workload and independent audits are complete.
See [the acceptance experiment results](../ball_tracking_candidate_acceptance_gate_results.md) and the ledger
configs/ball_tracking/reviews/candidate_acceptance_gate_result_v0_1.json.

The joint acceptance score J adds useful separation on held NBA quality-top
points: correct kept 2,275 -> 2,541, wrong eligible 99 -> 34, and hidden-frame
emissions 28 -> 8 at the fixed zero reference. Each of the three NBA games
improves or matches both raw Q and score-only S on all three measures for this
policy. Complete unselected curves show added separation; positive-slope S
preserves Q's per-source curve ordering. No evaluation cutoff was selected.

The full predeclared component criterion nevertheless FAILS. Held NBA native
retention rises 2,309 -> 2,806, but CHI adds three wrong and two hidden emissions.
HOU native J keeps 841 correct yet accepts 18 wrong and emits in 18 hidden frames;
HOU quality-top keeps 855 correct with four wrong but 14 hidden frames, versus
Q's 825 correct, six wrong and three hidden. Five protected quality-top choices
and seven exact protected stress probes are newly rejected; four of ten e01
recoveries are lost in each respective view. These overlapping views are not
additive failures. No model, threshold or selector is adopted.

All three single-game quality fits ran from the pinned fresh initialization:
3,300 updates, 37,626 cross-game scores, 4,481 total neural forwards. Supervised
execution took 448.906 seconds, peaked at 63 C, and finished with no qualifying
fault or remaining owned job. Eight CPU gate fits and analysis took 28.297
seconds. Original caches, four-fit quality models and completed studies were
reused; no old experiment was rerun. An initial readiness classifier mistook
ordinary WDDM desktop contexts for training workers; its unused freeze and
rejected evidence were preserved, then a reviewed version distinguished exact
desktop identities from conflicting/unknown runtimes before the only launch.
Debug Mode remained visibly ON; no system settings changed.

54 focused tests, 13 synthetic supervision checks and 12 readiness-correction
tests pass. Independent audits passed 152,617 neural transport/supervision,
16,520 saved tensor/optimizer and 3,328,460 acceptance-output checks. All 31,430
evaluation slots per arm, 11 missing scores, 4,289 context frames, 6,720 old
choices and contrasts, unknown roles and 60 historical rows remain represented.
There are 13,080 zero-reference tables and 578 complete unselected curves.

Next is a controlled follow-up design addressing incorrect/hidden native points
and protected recovery losses while preserving the demonstrated separation.
HOU remains exposed regression evidence and cannot choose a repair. Base-training
size changes across nesting and sparse native-negative support remain limits.
Quality-top's 2,542/2,811 ranking ceiling still prevents a rejection-only route
to 95% correctness; native and quality-top must remain separate. The existing
95%-correct / 1%-wrong / zero-hidden, temporal and human trajectory gates stand.

The current execution request is fulfilled. Outputs are under
data/outputs/ball_tracking/candidate_acceptance_gate_v0_1/attempt_001/.
The implementation_preparation/documentation_update receipt preserves all 113
prior worktree contents through exact unchanged bytes or reversible insertions,
retaining the Session17 and original handoff chain. Branch/HEAD/index remain
unchanged. No new labels, protected access, Git integration or future experiment
is implied. Existing NBA/cosine-nine roles and accepted annotations stand.



## Candidate acceptance experiment designed; unrun, 2026-10-29

Ryan requested a next experiment to preserve correct detections while rejecting
wrong ones, building on the CPU study and earlier work, with online research.
The independently reviewed design is [the candidate acceptance protocol](../ball_tracking_candidate_acceptance_gate_protocol.md), with specification
configs/ball_tracking/proposals/candidate_acceptance_gate_v0_1.json.

Keep original native and quality-top policies fixed: retain their point or
abstain, without fallback, reranking or trajectory changes. Compare reused raw
quality, a score-only adjustment, one 16-feature joint acceptance head, and a
fixed spatial-competition control. Only observable quality/response/pool inputs
are allowed; the target is useful coordinates, not semantic crop presence.

Honest source nesting needs three new single-game quality fits, each scoring
the other two games: 3,300 updates, 37,626 cross-game scores, 4,481 total neural
forwards. Existing models/results/caches are reused; eight small CPU gate fits
follow. None of that work ran. Metadata preparation verified 74 input bindings,
actual counts and feature availability; independent design review passes.
Targeted primary online research and material earlier reports were reconciled
with the completed history review, without claiming an exhaustive reread.

New gate evaluation has 31,430 slots per head (31,419 observed / 11 missing)
and 4,289 context frames. Old NBA fitted controls stay separate. Fixed zero and
complete unselected curves distinguish added information from a moved cutoff.
HOU native/recovery/stress successes and hidden emissions have explicit
regression checks; HOU chooses no weights, feature, cutoff or repair.

Quality-top's held ceiling is 2,542/2,811 (90.43%): rejection alone cannot finish
the 95% tracker gate. Native preservation is a separate primary question.
The existing 95%-correct / 1%-wrong / zero-hidden, temporal and human gates
remain. Mixed outcomes remain mixed; no model, threshold or selector is adopted.

Next: implement this exact bounded design and focused checks, then independent
review and concrete launch readiness before new neural execution. The current
design request is fulfilled; implementation and execution remain unrun.
Evidence is under data/outputs/ball_tracking/candidate_acceptance_gate_v0_1/preparation/.
All 111 prior worktree contents and the Session17 chain remain preserved through
exact additive records. Branch/HEAD/index are unchanged. No labels, protected
access, GPU query, settings change, old experiment rerun or Git integration.
Debug Mode ON remains the standing instruction.


## Saved-score CPU failure study completed and audited, 2026-10-29

Ryan explicitly authorized implementation and execution using saved results.
Accepted output is `data/outputs/ball_tracking/saved_score_failure_study_v0_1/attempt_003/`:
47.722 seconds of CPU consumer work; 25 focused tests and 1,615,156 independent
output checks pass. All 7,468 context frames, 50,243 score slots (11 missing),
18,813 NBA candidate pairs, 3,179 frame pairs, 6,720 contrasts and 60 historical
rows remain. The four-fit pilot and original consumers were reused.

New diagnosis separates rejection from ordering: 267 held-game frames still
rank a match first but contain no positive matching score; 264 paired frames
lose correct first-place ordering versus one gain. Matching native/weak
candidate median held-minus-fitted logits are -4.529/-6.751; full-pool margin
change is -8.310 on 2,694 defined pairs, with 485 named nulls. Source/visibility
patterns differ by game. Actual fitting support is narrow for native negatives
and hidden native candidates, but some zero-support metadata cells succeed and
some supported cells fail. No causal explanation, cutoff or model is selected.

See [the complete results](../ball_tracking_saved_score_failure_study_results.md) and the project ledger
`configs/ball_tracking/reviews/saved_score_failure_study_result_v0_1.json`.
Full source/support tables, successful/adverse controls, e01/e05 cases, weak/native,
unknown/missing/hidden populations and historical roles remain in the accepted
attempt. The next recommendation is a bounded design addressing presence/rejection
and cross-source comparability while retaining ordering and coverage constraints;
it is not a new training or selector authorization.

Attempts 001/002 are preserved but not accepted: a doubled summary counter,
numeric-radius category splitting and unavailable threshold metadata were fixed
with regression checks before attempt003. Original scores/labels/design files
never changed. Use the final freeze, audits and additive documentation receipt
under `implementation_preparation/documentation_update/`, rather than treating
the old pre-design handoff verifier as the current file-hash baseline.

All 102 preimplementation worktree contents and the Session17 preservation chain
remain recoverable. Branch/HEAD and empty index stay unchanged. Reuse prior
history/research reconciliation with its stated limits; no fresh full reread is
claimed. NBA/cosine-nine roles, accepted labels, pending human trajectory review,
Debug ON and protected closure stand. No model call, GPU query, new label,
trajectory, protected access, completed-old-study rerun or Git integration.


## CPU saved-score study specified; endpoints unrun, 2026-10-29

Session 19 resume verification passed: branch/HEAD and empty index match, all
100 intentional worktree files and 91 evidence bindings preserved. The complete
handoff and maintained history/research were reconciled using prior completed
reviews plus targeted primary records; no full-transcript reread is claimed.
The [new protocol](../ball_tracking_saved_score_failure_study_protocol.md) and
[bound specification](../../configs/ball_tracking/proposals/saved_score_failure_study_v0_1.json)
now specify source/support diagnosis beyond the completed rank-versus-zero
cross-tab. All gains/losses, agreements, native/weak, hidden, uncertain, missing,
e01/e05 and historical populations remain. No model/threshold is adopted.

Metadata preparation passes 215,780 identity/membership/transport checks on
35 inputs; the design binds 43 inputs. These are preparation checks, not new
scientific results. NBA fitted/held pairs cover 3,179 frames/18,813 candidates;
NFHS remains separate. Independent design review resolved denominator, rank
margin and cross-source support definitions. The new endpoint consumer is
unimplemented/unrun. Next: implement and focused-test this exact CPU design
before its bounded measurement; reuse all completed consumers and audits.

Evidence: `data/outputs/ball_tracking/saved_score_failure_study_v0_1/preparation/`
contains the metadata helper/receipt, design review and additive preservation
receipt. The old Session 19 verifier describes the pre-design baseline; after
these documented insertions, use the new receipt to distinguish intended changes.
All prior bytes remain preserved beneath reversible additions; the original
Session 17 chain is retained transitively. NBA/cosine-nine roles, accepted labels,
quality/human gates, Debug ON and protected closure stand. No GPU query, model
call, new labels, trajectory, training, completed-study rerun or Git integration.


## Session 19 complete handoff, 2026-10-29

Suggested title: **Ball Tracking 19 — Candidate-Quality Training & GPU Recovery**.
Local thread: `01a1831e-73b0-7532-8b5d-f60486918039`. The app title was retrieved
as `Specify CPU candidate-change comparison`; the title above is generated for
Ryan, not a claim that the app was renamed. Session 18 precedes this continuation.

Read the [complete Session 19 handoff](../../data/outputs/t/handoff_2026-10-29_8c040fca385d_session19/COMPLETE_HANDOFF.txt),
its appended full results report and required reading. The sibling opening prompt,
read-only verifier, exact 100-file snapshots and verification manifest preserve
the current branch/HEAD, empty index, all prior contents and Session 17 chain.
Only these additive handoff pointers changed; no scientific source, run or setting
changed. Current file hashes supersede older context hashes through the recorded
insertion layer; earlier experimental evidence remains frozen.

The four-fit pilot, all scoring, audits, paired/adverse comparisons and posthoc
cross-tab are complete. Reuse them. The next recommendation is to specify the
bounded CPU saved-score failure study; its precise protocol remains unfrozen and
unrun. Preserve useful ranking alongside rejection, weak, hidden, historical and
held-game failures, with full agreement/uncertain/missing coverage. Prior one-run
GPU permission is fulfilled, Debug Mode ON remains the requested configuration,
and no new training, selector, labels, protected access or Git integration follows.
Reuse completed history/research and state new reading limits; no resume reruns.

## Four-fit quality pilot completed; useful ranking, unresolved rejection, 2026-10-29

Ryan authorized the prepared continuation once. All four fixed fits and all
declared scoring completed with Debug Mode observed ON before launch. Inclusive
runtime was 1,125.984 seconds (18m46s); 547 GPU samples peaked at 63C/151.21W/3537MiB.
No qualifying fault or retry occurred; both owned jobs exited cleanly and the
postrun Windows/process query confirms no owned training/watcher remains. This
is encouraging after the native-cable change, not proof of a component cause or
permanent stability. No setting changed.

The unchanged epoch-six diagnostic endpoint was imported exactly for the first
fit, with zero retraining. New work: 7,626 updates, 1,572 score forwards and 3 parity
forwards; 50,232 scored presentations. Independent saved audits pass 246,129/224/
806,799 checks, including exact first-fit CPU tensor equality, complete counters,
score transport and cleanup. All 3,329 package frames/19,632 candidates, 960 HOU
frames, 11,798 query records, 6,720 contrasts and 60 historical rows remain.

HOU ranks a match strictly first on 862/882 eligible frames versus point 527 and
CLS 259. Against peak on 865 complete-feature pairs: 36 gains and 11 regressions;
17 incomplete old rankings remain separate. All ten e01 recovery rankings and
recovery-vs-missing comparisons succeed, but four of six below-.01 e05 gains
score negative. At fixed zero, 798/842 HOU native points survive and 3/34 hidden
frames retain another candidate. Held-game scores keep 2,309/2,807 native-correct
points (498 lost), 402/610 weak-match frames and retain hidden candidates in
28/128 frames. Fitted NBA keeps all native/weak positives.
Correct ordering, zero rejection and missing pool coverage remain distinct.
Historical accepted checks still miss two balls. No threshold or model is adopted.

See [the complete results](../ball_tracking_native_cable_training_results_2026-10-29.md), linked primary outputs and independent
interpretation. Reuse the completed full-history/research reconciliation plus
actual new four-fit evidence; no fresh every-transcript/paper claim. All agreement,
weak/native, hidden, uncertain, missing, adverse and historical cases are retained.
The next recommendation is a bounded CPU saved-score failure study before any
model/selector/training change; its precise follow-up protocol is not frozen or
run. The completed posthoc reporting cross-tab is explicitly descriptive.

All 99 prior worktree contents and the Session 17 chain are preserved beneath
verified additive records; one result report makes 100 paths. Branch/HEAD and
empty index remain unchanged. Earlier failures, checkpoints and physical exposure
11,710 starts/11,709 returns/11,708 updates remain. Historical 1,574 seconds and
the old 2,026-second balance remain but are no longer an active cap; new
1,125.984 seconds are recorded
separately. NBA/cosine-nine roles, accepted labels, quality/human gates and protected
closure stand. No further GPU work, new selector/trajectory, labeling campaign,
outside specialist, ACB prototype, protected access or Git integration occurred.

## Epoch-six checkpoint CPU-validated; continuation prepared, 2026-10-29

Ryan requests CPU validation and preparation of the next supervised continuation,
keeping Debug Mode ON, and explicitly removes the old remaining-time constraint.
The diagnostic epoch-six checkpoint passes 12,181 CPU checks, including actual
pinned model/AdamW restoration at update 2,244 and frozen-prefix identity. CUDA
stayed uninitialized; no neural forward, optimizer step or GPU query occurred.

Prepare completion of the unchanged four-fit pilot: reuse that audited first-fit
endpoint with an explicit diagnostic-origin record, score CHI, then finish the
remaining three six-epoch fits and all fixed scoring. New work is 7,626 updates,
1,572 score forwards and three parity forwards. No first-fit retraining, extra
epochs, outcome-based recipe changes, selected threshold or model adoption.
Full agreement/disagreement, weak/native, hidden, uncertain, missing, e01 and
historical populations remain; HOU stays out of fitting and DET is limited to
the original fixed historical queries.

See [the prepared continuation](../ball_tracking_native_cable_training_continuation_2026-10-29.md) and its linked primary review/audit
records. Reuse the completed full-history/research review plus targeted original
reports, code, primary research and actual new CPU checkpoint evidence; no fresh
all-transcript claim. Source/tests, independent review and supervision checks
pass. Metadata preflight rejects missing new execution approval before Torch.
Nothing has launched; fresh readiness and specific execution direction remain.

Historical 1,574 seconds charged and the old 2,026-second balance are preserved;
that balance is no longer a cap. The fixed workload ends normally when complete,
with a separate 90-minute operational watchdog and 30-second cleanup reserve.
Stop on any renewed fault, with no automatic retry. All 96 prior contents and
the Session 17 chain remain preserved through additive records; three new files
make 99 worktree paths. Original checkpoints/failures, NBA/cosine-nine roles,
accepted labels, all quality/human gates and protected closure remain. No Git
integration or new settings change occurred.

## Native-cable diagnostic completed with Debug Mode ON, 2026-10-29

Ryan approved the revised diagnostic. Fresh readiness passed; Debug Mode was
already observed ON, Lively was closed, and driver 617.42 / RAM 5200 / 250 W
remained unchanged. The fixed epoch-two replay completed all 1,496 updates and
shut down cleanly in 260.781 seconds including startup/cleanup. Peak sampled
62 C; no new matching Windows fault, zero remaining owned GPU/event workers.
The ten-minute value was a cap, not ten full minutes under load.

Independent CPU audit passes 34,315 checks: all 1,015 overlapping updates exactly
match earlier loss/gradient pairs, 481 extend beyond the old recorded range,
and four separate diagnostic checkpoints pass hash/ZIP checks. Their new tensor
semantics are unaudited; no scoring, four-fit comparison or adoption completed.
Original scientific epoch four and all prior unsaved work/failures remain.

See [the completed result](../ball_tracking_native_cable_diagnostic_results_2026-10-29.md). This short pass after the user-reported
native cable change is encouraging, not proof of a component cause or lasting
stability. Reuse completed history/research plus actual readiness, journals,
telemetry, events and independent reviews; no fresh all-transcript claim.
Conservative debit 261 seconds leaves 2,026 seconds (33m46s), with no automatic
continuation. All 95 prior contents and the Session 17 chain remain preserved
through additive records; one new report makes 96 worktree paths. NBA, cosine
nine, full case coverage, labels, uncertainty and protected closure are unchanged.
No new setting, scientific direction or Git integration follows this result.

## Cable replay revised to Debug Mode ON; still unrun, 2026-10-29

Ryan clarified that OFF was only the default and permits configuration choice.
Select Debug Mode ON to match the directly observed failing epoch-two replay
before the native cable change. Keep driver 617.42, RAM 5200, power limit 250 W
and the training recipe unchanged. This is a closer comparison, not a cure or
proof of cable causality. The original OFF preparation remains preserved/unrun.

The separate v0_2 preparation retains the 600-second cap and fault/stop guards.
CPU checks pass; actual ON observation, fresh readiness and explicit workload
execution direction remain required. Configuration selection is not a setting
change or launch: neither occurred. Earlier no-launch instruction still applies.

See [the revised protocol and commands](../ball_tracking_native_cable_reference_diagnostic_2026-10-29.md). Reused completed history and
targeted actual failure evidence; freshly read NVIDIA Debug Mode guidance.
No fresh all-transcript claim, GPU work, additional exposure or Git integration.
Preserve all 92 prior contents, Session 17 chain, scientific checkpoints and
2,287 remaining seconds; no automatic retry or further training follows.


## Native cable diagnostic prepared; do not launch, 2026-10-29

Ryan reports replacing the breakout cable plus ASUS adapter with the original
Corsair RM850e 2025 native 16-pin cable. Keep reported Debug Mode OFF. Photos
were reviewed in the browser chat; no specific cable fault is proven. A separate
ten-minute epoch-two replay is prepared, not authorized or run. The previous
clock diagnostic used Debug Mode ON, so configuration is not identical.

The last directed training retry failed after 83 returned forwards / 82 completed
updates, all replayed; no new checkpoint or scores. This time cleanup certified
zero owned processes. Debit 150 seconds; 2,287 seconds remain. Scientific epoch
four and its original 267 unsaved logical updates remain preserved.

Read-only checks find driver 617.42, both RAM modules at 5200, Lively running and
True Color absent. Apps and settings were left untouched. New owned supervision
has a 600-second hard deadline and a 30-second fault-cleanup guard; CPU checks
pass and missing execution approval is rejected before Torch import. Fresh
isolation/readiness and explicit execution direction are still required.

See [the protocol, commands and evidence](../ball_tracking_native_cable_diagnostic_2026-10-29.md). Reuse completed history and
research with targeted primary reads; no fresh all-transcript claim. All 89
prior contents and Session 17 chain remain preserved through additive records.
No automatic retry, further training, scientific-role change or Git integration.


## Powered-off connection check recommended, 2026-10-28

After the completed Debug Mode crash comparison, recommend photographs of the
existing GPU plug, cable/adapter route and accessible PSU label/ports, with the
PC off and AC unplugged. Keep internal connections untouched. This closes an
unresolved physical-evidence gap after inaccurate original cabling advice;
one native cable can be correct, and normal photos cannot prove electrical
health. See [the recommendation](../ball_tracking_nonphysical_crash_diagnosis_2026-10-28.md). The check is proposed, not performed.

Reused full history/research with original build messages, current primary crash
evidence and manufacturer guidance. No new setting, GPU work, retry or scientific
direction. All 87 prior contents, Session 17 chain and 2,437 seconds remain.

## Debug Mode crash dump comparison complete, 2026-10-28

The copied dump is verified and locally analyzed. It repeats the earlier
0x116/C000009A/4 failed-reset stack and 617.42 module offset. Raw same-build
context plus Windows report fields corroborate timeout-path 9 versus earlier 3,
consistent with an engine timeout escalated to adapter reset versus an earlier
display-flip timeout. Private type symbols are missing; no component cause is
identified. The retained power-cable string is in an identical firmware ROM,
not an active alert. See [the dump comparison](../ball_tracking_nonphysical_crash_diagnosis_2026-10-28.md).

The copy request is fulfilled; no further copy is currently needed. No GPU
query/workload, settings change, retry or new direction occurred. Reused completed
history/research plus relevant original logs and primary Microsoft documentation;
no fresh all-transcript claim. All 87 prior contents and Session 17 preservation,
scientific checkpoints, failures, roles/gates and 2,437 remaining pilot seconds
stand. Physical inspection remains deferred; no automatic GPU continuation.

## Debug Mode test failed; no retry, 2026-10-28

Ryan approved the single-setting diagnostic. Debug Mode was observed enabled,
but NVIDIA telemetry failed and Windows rebooted with another0x116/nvlddmkm
crash. The setting did not prevent recurrence; a faulty component is not yet
identified. Peak sampled63C/2525MiB; worker cleanup failed. Readable final receipts
and the live event watcher preserve this failure. See [the completed diagnostic](../ball_tracking_nonphysical_crash_diagnosis_2026-10-28.md).

Independent CPU recount:441 returned updates, all exactly matching attempt003's
recorded loss/gradient pairs; one unreturned start. Separate epoch3 checkpoint
hash/ZIP passes;67 later diagnostic updates unsaved. Original scientific epoch4,
267 original unsaved updates and all earlier failures remain. Conservative debit
through reboot leaves2437seconds (40m37s), with no reset or retry authorization.
New dump ordinary access is denied; exact local administrator-copy helper is
prepared/unrun. No further GPU/settings action, scoring, adoption, protected
access or Git integration. Post-reboot Debug Mode state is uninspected.

Reuse completed history/research and targeted primary/current-run evidence; no
fresh all-transcript claim. Original85 contents and Session17 chain are preserved
beneath additive documentation; two new worker/test files make87worktree paths.
All scientific roles, full case coverage and review gates remain unchanged.

## Reference-clock diagnostic recommended, not run, 2026-10-28

Ryan requests one change at a time. The actual NVIDIA App shows Debug Mode off;
recommend enabling it as the single setting change for a bounded replay of the
same first fit, from the already audited epoch-two state through epoch six, at
most10 minutes including startup/cleanup. See [the proposed contract](../ball_tracking_nonphysical_crash_diagnosis_2026-10-28.md).
The worker/launch inventory still needs preparation; no setting or GPU workload
changed. Reuse completed history and targeted primary evidence; current off state
does not establish the historical toggle state. A short pass is not a cure.
Preserve all85 prior contents, Session17 chain, latest checkpoint,267 unsaved
updates and2661 seconds remaining. No automatic retry, new scientific recipe,
protected access or Git integration; physical inspection remains deferred.

## Watchdog dump analyzed; cause still unresolved, 2026-10-28

The verified live dump captures graphics-scheduler hang detection at16:21:38.251,
19.296 seconds before the final116, with the same recovery-context address. It
confirms the same incident and earlier failure stage, not a faulty component.
Missing context/process memory and an undecoded retained graphics block limit
causal diagnosis. An embedded firmware power-cable message is not an active alert.
See [the completed follow-up](../ball_tracking_nonphysical_crash_diagnosis_2026-10-28.md). The watchdog-copy request is fulfilled.

Three local debugger passes and independent reviews are complete; no settings
change, GPU query/workload or retry occurred. No further copy is currently needed.
Reuse completed history/research and targeted primary evidence, without a new
all-transcript claim. All 85 prior worktree contents and Session17 preservation,
epoch-four checkpoint,267 unsaved updates and2,661 remaining seconds stand.
Existing diagnostic alternatives remain proposed/unrun; physical inspection is
deferred. No new scientific direction, protected access or Git integration.

## Existing timeout report analyzed, 2026-10-28

The copied Kernel117 report is verified and independently reviewed. It records
an NVIDIA timeout at 16:21:41.478 Phoenix, 16.069 seconds before the final 0x116
crash, with matching boot/bucket evidence. Its repeated AAAA parameters and generic
"Hardware error" label do not identify a faulty component or underlying cause.
The prior report-copy request is fulfilled. See [analysis receipt](../../data/outputs/ball_tracking/candidate_quality_pilot_v0_1/post_driver_recovery_preparation_v0_1/attempt003_interruption_v0_1/nonphysical_diagnosis_v0_1/kernel117_analysis_v0_1/analysis_receipt.json).

The report names WATCHDOG-20261028-1621.dmp; ordinary access is denied, so its
survival/content is not yet verified. An exact-file administrator copy helper is
prepared and unrun. No settings changes or GPU work occurred. Reuse the completed
history/research review and prior dump/event evidence; no fresh full-history claim.
All 85 prior worktree contents and Session 17 preservation remain intact. Physical
inspection is deferred; 2,661 pilot seconds, the epoch-four checkpoint and 267
unsaved updates remain unchanged. No automatic retry or scientific-role change.

## Further nonphysical diagnosis requested and completed, 2026-10-28

Ryan prefers further diagnosis before opening the case; physical inspection is
deferred. The [targeted review](../ball_tracking_nonphysical_crash_diagnosis_2026-10-28.md) identifies an unread protected Kernel117
report near the last crash, MSI/Ryzen helpers loaded in the actual dump, later
exact-board PCIe/graphics firmware fixes and untested NVIDIA reference-clock
mode. Chipset support/version differences are real but no CPU-specific or
NVIDIA-crash cause is established. Runtime/code review finds no obvious mismatch
or defect; that is not a software-health certificate.

Next is copying the existing small117 Report.wer with the prepared administrator
helper, then reading its actual metadata. Windows ordinary access is denied;
the copy is prepared and unrun. No new GPU workload, settings change, installation,
stress test or physical action occurred. One read-only NVIDIA query and one
saved-dump module inspection are recorded. Any later reference-clock or isolation
experiment still needs a concrete protocol and explicit execution direction.

All84 prior worktree contents and Session17 preservation remain intact. Reuse
completed history with targeted primary evidence; no fresh all-transcript claim.
Epoch-four checkpoint,267 unsaved updates, failures and2,661 seconds remaining
stand. No automatic retry, scientific-role change, protected access or Git
integration. Earlier cable-inspection recommendation remains historical.

## New dump analyzed after driver change, 2026-10-28

Ryan's new dump copy is verified and analyzed locally. It repeats 0x116,
C000009A and the Windows failed graphics-reset stack at 16:21:57.547 Phoenix,
now with verified 617.42. The changed NVIDIA offset reflects a different binary;
no identical private-function or specific faulty-component claim is justified.
Configured 5200 and driver replacement did not prevent recurrence. No retry ran.

The [comparison and diagnostic proposal](../ball_tracking_crash_dump_post_driver_2026-10-28.md) reuse completed history plus
actual earlier/new debugger evidence and primary vendor guidance. Next proposed
step is a powered-off photographic check of the GPU power connector/cable route
and accessible PSU label/ports. Earlier build advice was inaccurate; the actual
route is unknown, and one cable alone does not prove incorrect wiring. No
physical inspection, settings change, stress test or new GPU work occurred.

The dump-copy request is fulfilled. All 83 prior worktree contents remain intact
through additive records. Epoch-four checkpoint, 267 unsaved updates, previous
failures and 2,661 seconds (44m21s) remaining stand; no budget refund or automatic
retry. NBA, cosine nine, labels, full case coverage, gates and protected closure
are unchanged. No Git integration or new scientific direction.

## Post-driver continuation crashed; no retry, 2026-10-28

Ryan explicitly approved attempt003 and its remaining 49m6s. Readiness passed,
but NVIDIA telemetry failed and Windows rebooted with confirmed 0x116 naming
nvlddmkm.sys. Verified 617.42 and 5200 MT/s did not prevent recurrence; root cause
remains unresolved. STOP was requested, cleanup failed, and the final receipt
is 494 NUL bytes. Post-reboot snapshot finds no Python worker. No retry ran.

The independent CPU recount passes 3,474 recorded checks: 1,015 new updates,
exact replay of 213 old updates, epoch-four checkpoint retaining 1,496 logical
updates, and 267 later unsaved updates. Hash/ZIP CRC pass; new tensor semantics
are unaudited. No fit/scoring comparison completed. Peak sampled 62 C.
Conservative debit through reboot leaves 2,661 seconds (44m21s), not a new hour.

See [the interruption report](../ball_tracking_candidate_quality_post_driver_interruption.md). Windows denies ordinary access to the
new minidump; an administrator copy is the next local diagnostic step. The
guarded copy script is prepared, not run. All 82 prior worktree contents and
original Session17 preservation remain intact through additive records.
Reuse completed history/research with targeted crash/producer evidence; no fresh
all-transcript claim, new recipe, labels, protected access, adoption or Git
integration. Remaining time does not authorize another GPU attempt.

## Post-driver recovery validated and prepared, 2026-10-28

Ryan authorized CPU checkpoint validation and preparation only. The actual
epoch-two checkpoint passes 5,056 independent CPU checks: 42 finite trainable
tensors, exact parameter/AdamW restore at update 748, and CPU RNG checks. CUDA
remained uninitialized. Nine focused recovery tests and independent code review
pass. Actual frozen metadata preflight verifies original 45, prior 10 and new
22 bindings, and rejects the missing attempt003 execution approval without
importing Torch. No GPU worker or neural call started.

The [prepared continuation](../ball_tracking_candidate_quality_post_driver_recovery.md) resumes epoch three on driver 617.42 with
9,122 updates left, unchanged science and all original case coverage. The
2,946-second limit includes startup and a 30-second cleanup reserve. Preserve
both failures, 213 newly unsaved updates and all 300 replay-overhead updates;
cross-driver bit identity is not promised. All 79 prior worktree contents and
Session 17 preservation remain intact through additive records.

Next launch needs explicit direction for this prepared attempt and fresh
telemetry, event/memory and graphics-isolation checks; Lively was running at the
preparation snapshot and was not closed. Short idle readiness is not a cure.
Reuse completed history/research with targeted producer/crash/recovery evidence.
No automatic retry, new recipe, labels, protected access, adoption or Git integration.

## Driver 617.42 verified after installation, 2026-10-28

Ryan explicitly approved the Studio 617.42 clean installation, followed the
walkthrough and reported rebooting. Windows now reports signed driver
32.0.16.1742, and NVIDIA telemetry confirms 617.42 at a sampled 42 C. Boot was
15:54:12.5 Phoenix. Both 32 GB modules remain configured at 5200 MT/s. The
clean-install checkbox was not independently observed; EXPO off remains Ryan's
reported BIOS setting.

The successful since-boot queries inspected 147 System and 33 Application
events, with no matching graphics/WHEA/resource-exhaustion/WER reports. No
Python worker was present. This verifies replacement and short idle operation,
not a cure or load stability. No training, stress test or automatic retry ran.

[Observed installation snapshot](../../data/outputs/ball_tracking/candidate_quality_pilot_v0_1/studio_61742_install_v0_1/post_install_snapshot.json). All 79 prior worktree contents and
original 45/recovery 10 execution bindings remain preserved. The interrupted
epoch-two checkpoint retains 748 logical updates; its tensor semantics still
need CPU validation before any future recovery preparation. The 213 unsaved
updates, prior failures and 2,946-second remaining budget stand. Reuse completed
history/research and targeted incident evidence; no method, labels, protected
access, adoption or Git integration changes. Further GPU continuation requires
an explicit direction after concrete recovery/readiness preparation.

## Recovery interrupted again at 5200 MT/s, 2026-10-28

The directed attempt002 ran and failed again: CUDA unknown error and lost NVIDIA
telemetry, with a same-time Windows141 NVIDIA graphics timeout. Ryan restarted;
both RAM modules still report5200, EXPO off remains user-reported. No new0x116
is established for this incident. The memory change alone did not prevent it;
root cause remains unresolved. No further GPU retry follows.

The independent CPU recount preserves587 new updates, exact replay of87 old
updates, an epoch-two checkpoint retaining748 logical updates and213 later
unsaved updates. Hash/ZIP CRC pass; new checkpoint tensor semantics are not yet
audited. Supervisor cleanup certifies zero owned workers; no fit/scoring result
is complete. Peak sampled62 C. Budget remaining2946 seconds (49m6s), no reset.

See [the recovery interruption and evidence limits](../ball_tracking_candidate_quality_pilot_recovery_interruption.md). Original78 worktree
contents, attempts, approvals and scientific roles/gates remain preserved.
Reuse completed history/research with targeted current evidence; latest driver
review precedes any proposed installation. No automatic retry, adoption,
protected access, settings change or Git integration.

## Directed pilot recovery prepared, 2026-10-28

Ryan directed recovery after the verified 5200 MT/s memory change and reported EXPO disablement. The additive worker restores the first fit at epoch two from its 374-update checkpoint, with unchanged scientific recipe. Six actual-checkpoint CPU recovery tests and six original pilot checks pass; independent implementation review and original45/recovery10 metadata bindings pass. No CUDA/model call occurred during preparation.

The remaining supervised budget is 3,126 seconds from policy creation, with 30 seconds reserved for shutdown. New work if complete is 9,496 updates; logical total remains 9,870, while the physical lower bound becomes 9,957 because 87 unsaved recorded updates must be recomputed. No fresh hour or further automatic retry. Attempt001 and all original75 worktree contents remain preserved; attempt002 and monitoring/attempt002 are the continuation locations. Read their current started/completed/failed receipts before asserting execution status.

See [the recovery specification](../ball_tracking_candidate_quality_pilot_recovery.md) and ignored recovery_preparation_v0_1 evidence. Existing pilot approval and this explicit continuation apply; no new method, selector, labels, protected access, adoption or Git integration. The memory change is a diagnostic intervention, not a proven cure. Completed history/research review is reused with targeted recovery/crash evidence reads.


## Memory change verified after reboot, 2026-10-28

Ryan reports setting DRAM speed to 5200 and EXPO Profile 1 to Disabled. Windows independently reports both 32 GB modules configured at 5200 MT/s, with all 64 GB installed. EXPO state is user-reported; exact BIOS timing/voltage controls were not remotely inspected. The separate SMBIOS Speed=5600 field does not contradict ConfiguredClockSpeed=5200.

Boot was 15:09:56.5 Phoenix. The successful read-only query inspected 147 System events since boot and found no matching graphics/WHEA/resource-exhaustion provider events. NVIDIA 616.56 responds at sampled 40-41 C. These are a successful boot and short idle observations, not proof of stability or a confirmed cure. Lively has restarted; no Python worker was found. No GPU model call, training retry, stress test or further system change occurred.

[Verification snapshot](../../data/outputs/ball_tracking/candidate_quality_pilot_v0_1/interruption_v0_1/memory_change_v0_1/readiness_snapshot.json). All 75 prior worktree files and 45 frozen execution bindings pass; additive records preserve earlier contents. The approved pilot checkpoint and 3,126-second remaining budget stand. Next is CPU preparation of exact checkpoint recovery and fresh supervisor/isolation readiness before any explicitly directed GPU continuation; no automatic launch. Reuse the completed history/research review and preserve all scientific roles, gates, uncertainty and prior failures.


## Crash dump analyzed; controlled memory check proposed, 2026-10-28

Ryan supplied the local dump copy; analysis is complete. It repeats the October 26 NVIDIA 0x116 reset-failure signature, with crash time 14:05:31.131 Phoenix. The underlying cause remains unresolved. Earlier crashes predate this pilot and current driver; sampled GPU peak was 61 C with 2,688 MiB used. Ryan confirms the previously proposed lower-memory-speed test was never tried. Current 2x32 GB RAM remains configured at 6000; AMD rates this CPU at 5200 for two DIMMs. Next: inspect and preserve actual BIOS settings before one proposed conservative memory-profile/speed test. No BIOS/driver/settings change, stress test or GPU retry occurred. A supported clean-driver installation remains an alternative, not a proven cure.

See [the completed dump analysis and evidence limits](../ball_tracking_crash_dump_analysis_2026-10-28.md). The older dump-access request below is fulfilled. Same pilot approval/checkpoint/recipe and 3,126 seconds remaining are preserved; no budget reset, automatic retry, new scientific direction, protected access or Git integration. All 74 prior worktree files are preserved through additive documentation.


## Approved quality pilot interrupted, 2026-10-28

Ryan explicitly approved the frozen four-run pilot and one-hour supervised limit. It launched, then NVIDIA telemetry failed and Windows recorded a 0x116 graphics bugcheck naming nvlddmkm.sys. There are 461 durably recorded updates; the valid epoch-one recovery checkpoint retains 374. The 87 later updates are unsaved. No development scoring or completed scientific comparison exists. Sampled peak 61 C; the supervisor final receipt is corrupted (441 NUL bytes), so clean exit/cleanup is not certified. Original failure evidence remains intact.

CPU-only checkpoint audit verifies its original hash/CRC, finite trainable/optimizer state and saved RNG; CUDA stayed uninitialized. All 72 prior worktree bindings and 45 execution bindings pass. Conservative debit through reboot is 474 seconds, leaving 3,126 seconds of the approved hour. Approval persists for the same recipe; no fresh hour, automatic retry, alternate model or unrecorded replay is authorized. Further GPU work is deferred while the repeated graphics fault is unresolved. Windows denies access to the crash dump; an administrator-provided copy into the ignored local interruption folder is needed for deeper diagnosis. No drivers or system settings were changed.

See [the interruption and recovery record](../ball_tracking_candidate_quality_pilot_interruption.md). Earlier prepared/unrun entries remain historical. Preserve the full-history/research reconciliation, all roles and gates; no selector, new labels, protected access, model adoption or Git integration follows.


## Candidate-quality pilot prepared, 2026-10-28

The candidate-point quality pilot is specified and CPU-prepared; training and neural scoring remain unrun. It uses one pinned point-readout recipe, four fixed six-epoch fits, exact game grouping, complete weak/native/hidden/unknown/missing coverage and unchanged acceptance gates. The budget is 9,870 updates plus fixed scoring/parity, with a one-hour supervised attempt limit. New-scorer game splits are not end-to-end unseen-game tests: cosine nine already saw all three NBA sources. HOU stays excluded from fitting; DET has only the original fixed historical diagnostics. No selector, new labels, protected access, Git integration or training execution is authorized. The earlier capture approval is fulfilled, not recurring.

Reused the completed Sessions1-16 review, selected foundation decisions, previously read complete Session17/18 handoffs and subsequent results. Targeted primary artifacts and current records were read; the basketball crop paper was reopened and its pretrained-VGG16 detail corrected in the new rationale. No fresh every-transcript/every-paper claim.

See [the complete protocol](../ball_tracking_candidate_quality_pilot.md) and its frozen proposal.


## Next design recommendation after capture, 2026-10-28

Ryan asked what comes next. The evidence-led recommendation is to specify one
small candidate-point image-learning pilot for usable-location quality and
rejection. It is a direction recommendation; architecture, targets, grouping,
budget and evaluation protocol are not frozen and no training is authorized.
See the [decision and reading limits](../../data/outputs/ball_tracking/training_response_preparation_v0_1/next_step_review_v0_1/recommendation.md).
The design must protect native/weak balls, retain uncertainty and use point
conditioning; geometric misses are not semantic non-ball labels. Internal
source splits isolate only the new scorer, since cosine nine already fitted
CHI/DEN/SAC. HOU remains excluded from fitting and exposed development; DET
cannot choose the method. Other recognition/temporal/model alternatives remain
open. Completed history/research coverage is reused with relevant primary reads.
No new experiment, labels, selector, protected access or Git integration ran.


## Training response capture completed, 2026-10-28

The [approved capture and audited census](../ball_tracking_training_response_capture_results.md)
completed 2,995 forwards, 288 exact imports and3,329 training means with full original
parity and unchanged weights. Weak hidden-frame support is 130/147 frames;674 weak
matching frames comprise 673 already-correct native frames and one missing case.
All 241 masked frames remain unknown. No fit/selector/adoption follows. Prior pending/blocked
entries are historical; GPU capture approval is now fulfilled, not recurring.

Primary outputs: `data/outputs/ball_tracking/training_response_preparation_v0_1/`
contains `capture_attempt_001/`, `monitoring/capture_attempt_001/`, and
`reboot_resume_v0_1/post_capture_audit_v0_1/`. Separate review, source recount,
reassessment, earlier device/version-probe failures and pre-audit bounds fix
are preserved. Research/history coverage is reused with targeted primary reads.


## Post-reboot decision review, 2026-10-28

Ryan reported rebooting and requested a deeper reassessment before proceeding.
The same frozen capture remains supported after history/result reconciliation
and an independent implementation review. This is an in-sample training-support
check, not proof of generalization or authorization to train. All 225 inspected
workspace/input/source/runtime bindings pass; original code and approval stand.
The GPU responds again at 33-35 C with no matching new System graphics events
observed since boot. Reboot does not establish a cure for the prior graphics fault.
Lively was temporarily stopped under the existing isolation authorization. MSI
True Color restarted as PID18064; graceful/ordinary termination was unavailable
and Stop-Process returned Access is denied. Ryan was asked to exit only that app;
no supervisor, capture worker, model or new neural forward has started. No new
capture approval is needed after isolation is restored and freshly verified.

The first version probe matched the runtime pins but unexpectedly initialized
CUDA; its CPU-only guard exited before any model load or forward. Preserve that
failure separately. The corrected metadata preflight passed without importing
Torch. No frozen worker was changed or scientific experiment repeated. The
independent post-capture CPU audit helper is prepared and syntax-checked, unrun.

Evidence: `data/outputs/ball_tracking/training_response_preparation_v0_1/reboot_resume_v0_1/`
contains `decision_reassessment.md`, `independent_review.json`, `cpu_preflight.json`,
`preflight_attempt01_failure.json`, graphics isolation records and `audit_capture.py`.
Existing full-history/research coverage was reused with targeted current reads;
no fresh full-transcript or every-paper reread is claimed. NBA/cosine-nine/data
roles, acceptance gates, uncertainty and all original results remain unchanged.
No training, selector, new labels, protected access or Git integration occurred.


## Approved capture and prelaunch device block, 2026-10-28

- [Prelaunch status](../../data/outputs/ball_tracking/training_response_preparation_v0_1/prelaunch_gpu_unavailable_001/status.md); sibling `telemetry.json` preserves the NVIDIA
  GPU-lost error and `blocked.json` binds it, scope, CPU runtime metadata and
  zero inference/training/selector/label counts.
- Parent `gpu_approval.json` preserves Ryan's exact approval and binds the frozen
  prepared inventory. Original proposal/preparation/freeze remain unchanged as
  historical records; their pending-approval fields are not current authority.
- No worker, model or new inference started. Resume the same approved capture
  after a user-managed reboot and fresh readiness checks; no automatic fit.
- Existing full-history/research reconciliation is reused for this unchanged
  scope. No new experiment or research claim is introduced by the device block.


## Training-source response preparation, 2026-10-28

- [Decision, accumulated-history/research reconciliation and completed CPU work](../ball_tracking_training_response_preparation.md).
- [Proposed capture scope](../../configs/ball_tracking/proposals/training_response_capture_v0_1.json).
- Additive worker/test: `training_response_capture.py` and
  `test_training_response_capture.py`; original187 point-study and later frozen
  candidate-change files remain unchanged.
- Ignored `data/outputs/ball_tracking/training_response_preparation_v0_1/` contains
  `prepared.json`, `execution_freeze.json`, nine-test log, all288 exact saved
  training-import pools sealed before reference diagnosis, support/recount and
  preservation receipts. No new neural inference or training was performed.
- New relevant primary reading includes current training-fit records/caches,
  DeepSport candidate-presence sections/code and SAM3 presence/setup sources.
  Earlier full-history/research coverage is reused with its limits, not reread
  in full. No external model was installed, downloaded or adopted.
- One2,995-forward capture is proposed; GPU approval pending. No fit, labeling,
  selector or protected access follows automatically.

## Completed saved candidate-change comparison, 2026-10-28

- [Result and accumulated-evidence decision](../ball_tracking_candidate_change_comparison_results.md).
- [Result ledger](../../configs/ball_tracking/reviews/candidate_change_comparison_result_v0_1.json).
- Additive code/tests: `src/ball_tracking/candidate_change_analysis.py`,
  `tests/test_candidate_change_analysis.py` and its captured producer fixture.
- Ignored `data/outputs/ball_tracking/candidate_change_comparison_v0_1/` now adds
  `execution_freeze.json` and `analysis_v0_1/` with all choice/comparison rows,
  complete summary strata and the separately implemented standard-library recount.
  The fixed design is now executed; earlier unrun statements retain their time.
  Full history/research reconciliation is inherited from the preceding protocol,
  extended by these full-population results and adverse cases; no fresh all-source
  review is claimed. No method, training or next experiment is adopted/frozen.

## Candidate-change protocol and cache preparation, 2026-10-28

- [Protocol and evidence reconciliation](../ball_tracking_candidate_change_comparison_protocol.md).
- [Fixed design specification](../../configs/ball_tracking/proposals/candidate_change_comparison_v0_1.json).
- Ignored `data/outputs/ball_tracking/candidate_change_comparison_v0_1/` contains
  `inventory.json`, `choice_cache_joins.jsonl`, the metadata preparation helper,
  design binding and documentation preservation receipts. All960 HOU frames,
  seven old arms and seven full contrasts are declared;6,421 exact cached emitted
  choices and299 missing slots are retained. There is no new endpoint analysis,
  selector, inference, fit, label or protected access. Reuse the completed
  Sessions1-16 review plus both handoffs/relevant primary evidence; actual new
  chapter/ledger reading and inherited coverage limits are stated in the protocol.
  No fresh all-transcript/all-paper or external-release verification is claimed.
  The new protocol is specified; its future implementation freeze/execution
  decision remains separate. Prior records and their historical status stand.

## Session 18 handoff, 2026-10-28

Suggested title: **Ball Tracking 18 — NBA Weak Responses & Point-Feature Comparison**.
Chat ID: `01a17a62-ae37-74a3-8c10-1b96e4170c17`.
The [complete handoff](../../data/outputs/t/handoff_2026-10-28_8c040fca385d_session18/COMPLETE_HANDOFF.txt)
connects all completed weak/response/point phases, exact Git and dirty-file
snapshots, the latest continuation readiness, required primary evidence and
remaining human-review/uncertainty boundaries. Its `verification.json` is the
current handoff snapshot; earlier verification receipts retain their original
time and scope. No new experiment was performed to prepare the handoff.
Earlier point-proposal/unrun statements below are superseded execution statuses,
preserved for historical accuracy rather than current instructions.

## Completed point-readout continuation, 2026-10-26

- Result and interpretation: [point-feature comparison](../ball_tracking_point_feature_comparison_results.md).
- Frozen recipe: [point_feature_comparison_v0_1.json](../../configs/ball_tracking/proposals/point_feature_comparison_v0_1.json).
- Compact provenance/result ledger: [point_feature_comparison_result_v0_1.json](../../configs/ball_tracking/reviews/point_feature_comparison_result_v0_1.json).
- Ignored primary output root: `data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/point_comparison_v0_1/`.
  It contains `prospective_freeze.json`, `completed.json`, immutable attempt and
  input receipts, `analysis_v0_1/completed.json`, both `validation/independent_*_audit.json`
  receipts, resource samples and additive documentation preservation receipts.
- Explicit research coverage and timing: [research reconciliation](../../data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/history/research_reconciliation/review.txt).
- Result-grounded historical decision check: [decision basis](../../data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/point_comparison_v0_1/validation/history_reconciled_decision_basis.txt).

This continuation reuses the completed Sessions1-16 available-timeline review,
Session17 complete handoff/relevant primary evidence and stated foundation
coverage. It does not claim a fresh reread of every transcript or external URL.
The point experiment is now completed diagnosis, not merely a proposal and not
an accepted tracking method. Its ordering gains must not erase e01 subgroup,
visibility or historical regressions. No new training or policy is authorized.
Earlier coverage and frozen-result records below remain preserved.

## Authority map

The latest [response-structure diagnosis](../ball_tracking_candidate_response_feasibility.md)
completes the saved-output CPU question after weak-response selection. Its frozen
recipe is `configs/ball_tracking/proposals/candidate_response_feasibility_v0_1.json`;
the result ledger is `configs/ball_tracking/reviews/candidate_response_feasibility_result_v0_1.json`.
Ignored primary evidence is under
`data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/`: historical
pair diagnosis, cache inventory, exact saved objective accounting, frozen
preparation, sealed response features, per-episode ranking/visibility analysis,
fixed translated-location diagnostics and scoped independent audits. The report
maps exact receipts and limitations. The [point-feature proposal](../ball_tracking_point_feature_feasibility_proposal.md)
is a subsequent design, not an executed result. The completed sixteen-session
review was reused with relevant primary inspection, not repeated or represented
as a new full-transcript reread. No training, labels or protected access follows.

The current [weak-response result](../ball_tracking_weak_response_results.md)
completes the next experiment proposed by the Session 17 reassessment below.
Frozen recipes are `configs/ball_tracking/proposals/weak_response_v0_1.json` and
`weak_response_followup_v0_1.json`; the compact result ledger is
`configs/ball_tracking/reviews/weak_response_result_v0_1.json`. The original
cosine-nine checkpoint, accepted references and source-role manifest are unchanged.
Ignored primary evidence is under `data/outputs/ball_tracking/weak_response_v0_1/`:
inventory/capture, complete feasibility pools, both comparison records, independent
audits, preparation/failure history and full paired review sets. See the result's
artifact map for exact locations and hash-bound receipts. The prospective-history
clarification discloses preparation probes separately from the full frozen study.

This continuation reused the completed sixteen-session coverage map and inspected
relevant primary evidence; it did not reread every original transcript. No model
passes or is adopted, no training occurred, and no protected evaluation opened.
Original Session 17 documentation remains intact beneath additive current updates.
The earlier "no new selector/inference" statement below is its historical state.

The [October 26 full-history reassessment](../research/ball_tracking_full_history_reassessment_2026-10-26.md)
reviews all sixteen Ball Tracking timelines (398 turns/47 pages), relevant
primary reports, and earlier foundation evidence, with explicit reading limits.
Its ignored coverage notes and current candidate recount are under
`data/outputs/t/full_history_review_20261026/`. All sixteen saved producer files
agree with the 7,324 recounted observation rows. The revised next recommendation
is weak-response feasibility first with a small paired selection control using
cosine nine; no new selector, inference or fitting ran. Existing >.3 candidate
ceilings cannot reach 95% in DET and HOU e01/e05. This completed historical review
supersedes the access-inventory-only status below without claiming a reread of
every raw log or a new validation of every historical result.

The latest [spatial result](../ball_tracking_wasb_spatial_results.md) records the
completed two-epoch fit, both NBA comparisons and same-epoch diagnostic review.
Frozen source/recipe were committed at `297938e0088f71901c8f93c5d3592a97044b763c`;
the recipe is `configs/ball_tracking/proposals/wasb_spatial_v0_1.json`.
Generated outputs are under `data/outputs/ball_tracking/wasb_spatial_v0_1/`,
audits/diagnosis/geometry AI review and preserved preparation failure under
`data/outputs/t/wasb_spatial_20261026/`. The committed result ledger is
`configs/ball_tracking/reviews/wasb_spatial_result_v0_1.json`. Neither checkpoint
passes or is adopted. No automatic extension follows; human review remains
pending and protected evaluation remains closed.

The latest [continuation result](../ball_tracking_wasb_continuation_results.md)
records both completed five-epoch arms, ten comparisons, current-model training
fit and the eight-call temporal probe. The unchanged recipe is
`configs/ball_tracking/proposals/wasb_continuation_v0_1.json`; actual outputs are
under `data/outputs/ball_tracking/wasb_continuation_v0_1/`. Independent audits,
paired summary, source-uncertainty recovery audit, AI inspection and preserved
diagnostic guard failures are under `data/outputs/t/wasb_continuation_20261026/`.
The committed result ledger is
`configs/ball_tracking/reviews/wasb_continuation_result_v0_1.json`.
No model passes or is adopted. Protected evaluation remains closed. Historical
proposed, paused and prepared states below do not override these completed runs.

The latest [resolution result](../ball_tracking_nba_resolution_results.md)
records the completed five-epoch fit and all-five NBA comparison. The original
frozen recipe remains `configs/ball_tracking/proposals/wasb_resolution_v0_1.json`;
completed outputs are under `data/outputs/ball_tracking/wasb_resolution_v0_1/`.
Independent fit/NBA receipts are under
`data/outputs/t/nba_resolution_resume_20261026/`, including the preserved first
audit failure and corrected passed audit. No model qualifies or is adopted.
This completion supersedes earlier proposed/stopped operating states below,
without rewriting their evidence, the failed crash attempt or its unresolved
underlying cause. Protected evaluation and human visual acceptance remain closed
and pending respectively.

The [local crash-dump analysis](../ball_tracking_crash_dump_analysis_2026-10-26.md)
resolves the prior access blocker and identifies the NVIDIA 616.56 module in
the failed reset path, without establishing the underlying cause. Its ignored
`crash_dump_analysis_v0_1.json` receipt binds the dump, debugger logs and driver
metadata under `data/outputs/t/nba_resolution_restart_20261026/`. GPU work remains
stopped; the original inaccessible-dump observations below are historical.

The latest [resolution crash/interruption record](../ball_tracking_nba_resolution_restart_2026-10-26.md)
supersedes the proposed-only operating state. The approved preparation and
frozen recipe are committed at `3605648`; its first fit attempt made zero
updates and no completed epoch. Current evidence is under
`data/outputs/ball_tracking/wasb_resolution_v0_1/` and
`data/outputs/t/nba_resolution_restart_20261026/`. Preserve the corrupt monitor
summary; do not infer completion from its filename or resume GPU work automatically.

The latest [NBA failure diagnosis](../ball_tracking_nba_failure_diagnosis.md)
and [proposed resolution experiment](../ball_tracking_nba_resolution_experiment.md)
record the completed read-only diagnosis and unexecuted recommendation.
The frozen original-weight control is
`configs/ball_tracking/proposals/nba_original_weight_control_v0_1.json`; generated
records/review are under `data/outputs/ball_tracking/nba_diagnosis_v0_1/`.
Its evidence ledger links the error, training, visual and independent audits.
The next fit is not authorized by the diagnosis request; all quality criteria
and protected-evaluation boundaries remain unchanged.

The October 25 [NBA-first result](../ball_tracking_nba_first_results.md),
[approved comparison scope](../ball_tracking_nba_first_evaluation.md) and
[frozen model manifest](../../configs/ball_tracking/proposals/nba_first_saved_models_v0_1.json)
are current. The comparison evaluates twelve existing models, makes no training
updates and claims no pass. Its generated evidence is under
`data/outputs/ball_tracking/nba_first_v0_1/`; the independent audit is
`data/outputs/t/nba_first_inventory_20261026/final_audit_20261026T023210817446Z.json`.
Earlier preparation, recovery
and reference-publication entries retain the states recorded at those checkpoints;
their pending or paused wording does not supersede the later completion.

| Subject | Primary authority | Supporting archive |
|---|---|---|
| P003 occlusion-exit diagnosis, 2026-10-25 | [Diagnosis](../ball_tracking_p003_reacquisition_diagnosis.md), [fixed probe scope](../../configs/ball_tracking/proposals/wasb_p003_validation_probe_v0_1.json), [exact replay](../../data/outputs/ball_tracking/wasb_p003_diagnosis_v0_1/attempt_001/completed.json), [independent raw-map audit](../../data/outputs/t/wasb_p003_diagnosis_20261026/independent_probe_audit.json) | All ten trained checkpoints miss 170 then match 171-174. Thirty read-only calls / 16 frames reproduce 15 outputs exactly; trained weak response plus misplaced surviving component. Seven focused checks/6,681 independent checks pass, peak 48 C. No fitting, label/threshold change, protected evaluation or adoption. |
| Five-epoch WASB augmentation completed, 2026-10-25 | [Result report](../ball_tracking_wasb_augmentation_results.md), [frozen plan](../ball_tracking_wasb_augmentation_experiment.md), [recipe](../../configs/ball_tracking/proposals/wasb_augmentation_v0_1.json), [completed producer](../../data/outputs/ball_tracking/wasb_augmentation_v0_1/fit_v0_1/completed.json), [independent audit](../../data/outputs/t/wasb_augmentation_20261026/actual_run_audit.json) | Existing labels, synchronized mirror/brightness, original first-five schedule and unchanged quality rules. All 7,760 updates complete; only epoch zero qualifies. Epoch three fails selection solely because P003 loses frame 170. Fourteen focused checks and 171,615 actual-record checks pass. One 22.3-minute monitored run peaks at 60 C; no new full census/render for baseline retention. All original evidence and protected boundary preserved. |
| Approved successor assessment and rejected TAPNext++ pilot, 2026-10-25 | [Result report](../ball_tracking_successor_results.md), [approved scope](../ball_tracking_successor_execution_plan.md), [training assessment](../../data/outputs/ball_tracking/completion_next_step_v0_1/training_assessment_epoch005/assessment.json), [pilot evaluation](../../data/outputs/ball_tracking/successor_campaign_v0_1/tapnextpp512_pilot_v0_1/evaluation.json), [retention decision](../../data/outputs/ball_tracking/successor_campaign_v0_1/tapnextpp512_pilot_v0_1/retention_decision.json) | Training-only epoch five matches 2,931/2,941, including 130/130 NFHS; conditional extra epochs skipped. Fixed TAP pilot completes 3,975 frames/3,947 calls, scores 356/1,117 curated matches versus 924 baseline, and fails 12/13 guards. Independent assessment/pilot audits pass 30,322/124,853 checks; 38 focused checks mapped with honest source coverage. Peak pilot GPU 64 C; failed acquisition and namespace compatibility attempt preserved. No new labels, thresholds, protected reads or method adoption. |
| Primary fit completed; retained baseline selected, 2026-10-25 | [Result and review report](../ball_tracking_completion_primary_results.md), [actual training completion](../../data/outputs/ball_tracking/completion_campaign_v0_1/primary_fit_v0_1/completed.json), [fixed comparison](../../data/outputs/ball_tracking/completion_campaign_v0_1/selected_comparison_v0_1/evaluation.json), [independent audit](../../data/outputs/t/completion_actual_result_audit_20261025_01/audit.json); `completion_evaluation.py`, `completion_nba_comparison_render.py` and focused tests | Ryan explicitly lifted the pause. Third attempt completes five epochs/7,760 updates in 1,060.663s after update-500 recovery and 22-update replay. Only epoch zero is eligible; primary model rejected. The 3,975-frame/16-cohort comparison preserves baseline predictions with zero new inference. All permitted curated screens fail; P001 five/P002 four certain-hidden emissions block the resolution fallback. Nineteen new CPU checks and 104,212 independent audit checks pass. Three curated renders cover 1,498 slots/225 black protected slots; see result report for all review artifacts. Protected evaluation closed; monitored success does not prove PC stability. |
| Historical CPU preparation and explicit training pause | [Training/preparation report](../ball_tracking_completion_primary_training.md#cpu-only-preparation-completed-before-handoff), [combined checks](../../data/outputs/ball_tracking/completion_campaign_v0_1/training_implementation/evaluation_focused_validation.json), [integrity check](../../data/outputs/ball_tracking/completion_campaign_v0_1/training_implementation/resume_integrity_before_handoff.json); `completion_evaluation_package.py`, `completion_scoring.py`, `completion_comparison_render.py` and focused tests | 28 checks pass; real annotation/observation/scoring transport and synthetic CPU video tested. All 25 frozen training dependencies and update-500 state unchanged. At this pre-handoff checkpoint, real post-selection evaluation and completed selection remained future work, and GPU training was explicitly paused. Protected evaluation remained closed. |
| Historical primary run recovery after repeated GPU loss | [Execution report](../ball_tracking_completion_primary_training.md#execution-interrupted-by-gpu-loss), [recovery audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/primary_fit_v0_1/gpu_recovery_after_attempt_02.json) | Two failed attempts preserved: zero updates, then 522 completed/523 attempted. Update 500 was durable and verified; 22 completed updates required replay. Baseline validation was complete, with no trained epoch selected. GPU was inaccessible to NVIDIA tooling; cause unknown. Protected evaluation closed. |
| Frozen primary completion training | [Training report](../ball_tracking_completion_primary_training.md), [recipe](../../configs/ball_tracking/completion_campaign/primary_recipe_v0_1.json), [focused checks](../../data/outputs/ball_tracking/completion_campaign_v0_1/training_implementation/focused_validation.json) | 32 tests and real runner preflight pass. Final accepted package: 3,329 training/1,110 selection frames, 3,103 usable triplets, 174 all-masked exclusions. Recipe binds 25 implementation dependencies and the fixed 20-epoch schedule. Pre-fit checkpoint; protected evaluation closed. |
| Final curated group 17–23 accepted; permitted census complete | [Acceptance report](../ball_tracking_completion_reference_group_17_23.md#human-acceptance-published-2026-10-25), [publication audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batches_17_23_acceptance/publication_audit.json), [final inventory](../../data/outputs/ball_tracking/completion_campaign_v0_1/accepted_reference_inventory_after_batch_23.json), [primary training increment](../ball_tracking_completion_primary_training.md) | Ryan accepted all 269 proposals. First publication passes in 5.101s, preserving 1,004 prior rows and 854 originals. All 1,273 permitted references accepted: 1,117 eligible centers, 155 null geometries and one unchanged noneligible geometry (P002335). All 3,839 NBA references unchanged. Training implementation/freezing follows; no fit or protected evaluation. |
| Curated completion group 12–16, accepted 2026-10-25 | [Acceptance report and receipts](../ball_tracking_completion_reference_group_12_16.md#human-acceptance-published-2026-10-25), [actual-reader audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batches_12_16_acceptance/publication_audit.json), [inventory after batch 16](../../data/outputs/ball_tracking/completion_campaign_v0_1/accepted_reference_inventory_after_batch_16.json) | Ryan's structured “Accept all 71 proposals” accepts 71 centers, zero nulls, 51 partial/20 full visibility judgments and 5–9px uncertainty. First publication passes in 2.170s, preserving all 933 earlier rows and 350 originals. Curated totals: 1,004/1,273 accepted, 896 eligible centers, 107 null geometries and one unchanged geometry excluded from localization scoring (P002 frame 335); 269 remain. New references stay evaluation-only, both eligibility flags false. |
| Historical preparation: final curated group 17–23 before acceptance | [Complete report/review](../ball_tracking_completion_reference_group_17_23.md), [source audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_17_23/source_preparation_and_pixel_audit.json), [integration audit](../../data/outputs/ball_tracking/completion_campaign_v0_1/reference_group_17_23/integration_audit.json) | 269 proposals: 221 centers/48 nulls, 5–10px uncertainty. Seven complete overlays total 53.8s slow. Source preparation 269 exact matches in 60.625s; integration 538 encoded frames/finals passes. All 1,004 accepted curated rows remain unchanged; acceptance would complete 1,273 permitted references. Failed source comparison/unverified first-output identity and sorted-tag repairs are preserved. Evaluation-only; no fit or protected evaluation. |
| Fixed NBA selection complete through accepted NBA24 | [NBA24 acceptance](../ball_tracking_completion_nba_reference_batch_24.md#human-acceptance-published-2026-10-25), [accepted NBA inventory](../../data/outputs/ball_tracking/completion_campaign_v0_1/accepted_nba_reference_inventory_after_batch_24.json) | All 3,839 selected judgments remain accepted: 3,423 centers/416 nulls, with 2,879 training and 960 checkpoint validation. Validation stays excluded from gradient fitting. Curated completion is now separately published; the full package and executable recipe are being prepared. No completion-campaign fit or protected evaluation has run. |
| NBA completion reference batch 18, accepted | [Acceptance and complete overlays](../ball_tracking_completion_nba_reference_batch_18.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_18_acceptance_v0_1.json), [original result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_18_result_v0_1.json) | Ryan accepted all 240 HOU–OKC e06 judgments, frames 210–449: 212 centers/28 nulls, 128 full/94 partial/18 not visible, 5–9px uncertainty. Publication preserves 5,882 originals and passes actual readers/duplicate guard. NBA totals 2,880 accepted/2,638 centers/242 nulls, split 1,920 training/all 960 validation. One game remains: six fixed SAC–MEM training episodes totaling 959 judgments. Curated 868 accepted/760 centers/405 uncovered remains separate. Original review and all failure/inspection history remain unchanged; validation references stay excluded from gradient fitting. No new batch preparation, scoring, fit or protected evaluation. |
| NBA completion reference batch 17, accepted | [Report and complete overlays](../ball_tracking_completion_nba_reference_batch_17.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_17_acceptance_v0_1.json), [original result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_17_result_v0_1.json) | Ryan accepted all 240 HOU–OKC e05 judgments, frames 0–239: 212 centers/28 nulls, 200 partial/20 full/16 not visible/four indeterminate, 5–9px uncertainty. Publication preserves 5,406 originals and passes actual readers/duplicate guard. NBA totals 2,640 accepted/2,426 centers/214 nulls, split 1,920 training/720 validation; 1,199 unaccepted. Validation labels remain excluded from gradient fitting. Original review evidence, failed writer/tag correction, source crops, second-AI scope and curated 868 references remain unchanged. No checkpoint scoring, fit or protected evaluation. |
| NBA completion reference batch 16, accepted | [Report and complete overlays](../ball_tracking_completion_nba_reference_batch_16.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_16_acceptance_v0_1.json), [original result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_16_result_v0_1.json) | Ryan accepted all 120 HOU–OKC e04 judgments, frames 150–269: 120 centers, zero nulls, 70 full/50 partial, 5–8px uncertainty. Publication preserves 4,936 originals and passes actual readers/duplicate guard. NBA totals 2,400 accepted/2,214 centers/186 nulls, split 1,920 training/480 validation; 1,439 unaccepted. Validation labels remain excluded from gradient fitting. Original review evidence, six center refinements, crop adjustments, lookup/restart history and curated 868 references remain unchanged. No checkpoint scoring, fit or protected evaluation. |
| NBA completion reference batch 15, accepted | [Report and complete overlays](../ball_tracking_completion_nba_reference_batch_15.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_15_acceptance_v0_1.json), [original result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_15_result_v0_1.json) | Ryan accepted all 120 HOU–OKC e03 judgments, frames 120–239: 98 centers/22 nulls, 32 full/70 partial/ten indeterminate/eight not visible, 5–9px uncertainty. Publication preserves 4,673 originals and passes actual readers/duplicate guard. NBA totals 2,280 accepted/2,094 centers/186 nulls, split 1,920 training/360 validation; 1,559 unaccepted. Validation labels remain excluded from gradient fitting. Original evidence, lookup incidents and curated 868 references unchanged. No scoring, fit or protected evaluation. |
| NBA completion reference batch 14, accepted | [Report and complete overlays](../ball_tracking_completion_nba_reference_batch_14.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_14_acceptance_v0_1.json), [original result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_14_result_v0_1.json) | Ryan accepted all 120 HOU–OKC e02 judgments, frames 0–119: 120 centers, zero nulls, 71 partial/49 full, 5–7px uncertainty. Publication preserves 4,401 originals and passes actual readers/duplicate guard. NBA totals 2,160 accepted/1,996 centers/164 nulls, split 1,920 training/240 validation; 1,679 unaccepted. Validation labels remain excluded from gradient fitting. Original evidence, collective reviewer attribution, helper failure and curated 868 references unchanged. No checkpoint scoring, fit or protected evaluation. |
| NBA completion reference batch 13, accepted | [Report and complete overlays](../ball_tracking_completion_nba_reference_batch_13.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_13_acceptance_v0_1.json), [original result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_13_result_v0_1.json) | Ryan accepted all 120 HOU–OKC e01 judgments, frames 120–239: 120 centers, zero nulls, 80 partial/40 full, 5–6px uncertainty. Publication preserves 4,156 originals and passes actual readers/duplicate guard. NBA totals 2,040 accepted/1,876 centers/164 nulls, split 1,920 training/120 validation; 1,799 unaccepted. Validation labels are excluded from gradient fitting. Original review evidence and curated 868 references unchanged. No checkpoint scoring, fit or protected evaluation. |
| NBA completion reference batch 12, accepted | [Report and complete overlays](../ball_tracking_completion_nba_reference_batch_12.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_12_acceptance_v0_1.json), [original result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_12_result_v0_1.json) | Ryan accepted all 240 DEN–BOS e06 judgments, frames 150–389: 220 centers/20 nulls, 5–8px uncertainty. Publication preserves 3,911 originals and passes actual readers/duplicate guard. NBA totals 1,920 accepted/1,756 centers/164 nulls; 1,919 unaccepted, curated 868 unchanged. Original overlays, metadata corrections and helper failure remain preserved. No fit or protected evaluation. |
| NBA completion reference batch 11, accepted | [Report and complete overlays](../ball_tracking_completion_nba_reference_batch_11.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_11_acceptance_v0_1.json), [original result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_11_result_v0_1.json); ignored inventory after batch 11 | Ryan accepted all 240 DEN–BOS e05 judgments, frames 210–449: 240 centers, zero nulls, 172 partial/68 full, 5–8px uncertainty. Publication preserves 3,455 originals; actual readers and duplicate guard pass. NBA totals 1,680 accepted/1,536 centers/144 nulls, with 2,159 unaccepted; curated 868 unchanged. Original 4s/24s media and receipt sequence correction are preserved. No fit or protected evaluation. |
| NBA completion reference batch 10, accepted | [Acceptance and complete overlays](../ball_tracking_completion_nba_reference_batch_10.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_10_acceptance_v0_1.json), [preparation result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_10_result_v0_1.json); ignored `accepted_nba_reference_inventory_after_batch_10.json` | Ryan accepted all 120 judgments: 100 centers, 20 nulls at 270–289, uncertainty 5–8px; visibility 68 full/40 partial/two indeterminate/ten not visible. Separate publication preserves 3,015 originals and passes actual readers/duplicate guard. Combined coverage is 1,440/3,839 NBA labels, with 1,296 centers/144 nulls and 2,399 unaccepted; curated 868 unchanged. Original 2s/12s review passed 3,049 bindings, 120 native joins, 240 encoded frames and 200 markers. Native selected 240–359 differs from source final 578. Original pending-era records/media and prior 13/12-test evidence remain unchanged. Reference preparation continues; no completion-campaign fit or next prepared batch claimed. |
| NBA completion reference batch 09, accepted | [Acceptance and complete overlays](../ball_tracking_completion_nba_reference_batch_09.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_09_acceptance_v0_1.json), [preparation result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_09_result_v0_1.json); ignored `accepted_nba_reference_inventory_after_batch_09.json` | Ryan accepted all 120 judgments: 112 partial/eight full centers, zero nulls and 5–8px uncertainty. Separate publication preserves 2,742 originals and passes actual readers/duplicate guard. Combined coverage is 1,320/3,839 NBA labels, with 1,196 centers/124 nulls; curated 868 unchanged. Original 2s/12s review passed 2,768 bindings, 120 native joins, 240 encoded frames and 240 markers. Source final 474 differs from batch final 119. Original pending-era records/media, retained config/capacity failures and prior 13/12-test evidence remain unchanged; no fitting or protected evaluation. |
| NBA completion reference batch 08, accepted | [Acceptance and complete overlays](../ball_tracking_completion_nba_reference_batch_08.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_08_acceptance_v0_1.json), [preparation result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_08_result_v0_1.json); ignored `accepted_nba_reference_inventory_after_batch_08.json` | Ryan accepted all 120 judgments: 92 partial/28 full centers, zero nulls and 4–6px uncertainty. Separate publication preserves 2,490 originals and passes actual readers/duplicate guard. Combined coverage is 1,200/3,839 NBA labels, with 1,076 centers/124 nulls; curated 868 unchanged. Original 2s/12s review passed 2,514 bindings, 120 native joins, 240 encoded frames and 240 markers. Source final 398 differs from batch final 119. Original pending-era records/media and prior 13/12-test evidence remain unchanged; no fitting or protected evaluation. |
| NBA completion reference batch 07, accepted | [Acceptance and complete overlays](../ball_tracking_completion_nba_reference_batch_07.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_07_acceptance_v0_1.json), [preparation result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_07_result_v0_1.json); ignored `accepted_nba_reference_inventory_after_batch_07.json` | Ryan accepted all 120 judgments: 120 partial-visible centers, zero nulls and 5–6px uncertainty. Separate publication preserves 2,245 originals and passes actual readers/duplicate guard. Combined coverage is 1,080/3,839 NBA labels, with 956 centers/124 nulls; curated 868 unchanged. Original 2s/12s review passed 2,264 bindings, 120 native joins, 240 encoded frames and 240 markers. Source final 602 differs from batch final 119. Original pending-era records/media and prior 13/12-test evidence remain unchanged; no fitting or protected evaluation. |
| NBA completion reference batch 06, accepted | [Acceptance and complete overlays](../ball_tracking_completion_nba_reference_batch_06.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_06_acceptance_v0_1.json), [preparation result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_06_result_v0_1.json); ignored `accepted_nba_reference_inventory_after_batch_06.json` | Ryan accepted all 240 judgments: 224 centers, 16 nulls and 5–8px uncertainty. Separate publication preserves 2,000 originals and passes actual readers/duplicate guard. Combined coverage is 960/3,839 NBA labels, with 836 centers/124 nulls; all six CHI–IND episodes are accepted. Curated 868 unchanged. Original complete 4s/24s review passed 2,014 bindings, 240 native joins, 480 encoded frames and 448 markers. Batch final 479 differs from source final 718. Original pending-era records/media and prior 13/12-test evidence remain unchanged; no fitting or protected evaluation. |
| NBA completion reference batch 05, accepted | [Acceptance and complete overlays](../ball_tracking_completion_nba_reference_batch_05.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_05_acceptance_v0_1.json), [preparation result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_05_result_v0_1.json); ignored `accepted_nba_reference_inventory_after_batch_05.json` | Ryan accepted all 240 judgments: 178 centers, 62 nulls and 4–9px uncertainty. Separate publication preserves 1,549 originals and passes actual readers/duplicate guard. Combined NBA coverage is 720/3,839, with 612 centers/108 nulls; curated 868 unchanged. Original 4s/24s review passed 1,558 bindings, 240 native joins, 480 encoded frames and 356 markers. Source final 756 differs from batch final 509. Original pending-era preparation records/media and prior 13/12-test evidence remain unchanged; no fitting or protected evaluation. |
| NBA completion reference batch 04, accepted | [Acceptance and complete overlays](../ball_tracking_completion_nba_reference_batch_04.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_04_acceptance_v0_1.json), [preparation result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_04_result_v0_1.json); ignored `accepted_nba_reference_inventory_after_batch_04.json` | Ryan accepted all 120 judgments: 118 centers, two indeterminate nulls at 300–301 and 5–7px uncertainty. Separate publication preserves 1,050 originals and passes actual readers/duplicate guard. Combined NBA coverage is 480/3,839, with 434 centers/46 nulls; curated 868 unchanged. Original 2s/12s review passed 1,054 bindings, 120 native joins, 240 encoded frames and 236 markers. Source final 552 differs from batch final 419. Original media and prior 13/12-test evidence retained; no fitting or protected evaluation. |
| NBA completion reference batch 03, accepted | [Acceptance and original review](../ball_tracking_completion_nba_reference_batch_03.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_03_acceptance_v0_1.json), [preparation result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_03_result_v0_1.json); ignored `accepted_nba_reference_inventory_after_batch_03.json` | Ryan accepted all 120 judgments: 100 centers, 20 nulls and 4–8px uncertainty. Separate publication preserves 809 originals and passes actual readers/duplicate guard. Combined NBA coverage is 360/3,839, with 316 centers/44 nulls; curated 868 unchanged. Original complete review passed 808 bindings, 120 native joins, 240 encoded frames and 200 markers. Source final 508 differs from batch final 239. Drafts, revisions, failures and prior 13/12-test evidence remain unchanged; no fitting or protected evaluation. |
| NBA completion reference batch 02, accepted | [Acceptance and original review](../ball_tracking_completion_nba_reference_batch_02.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_02_acceptance_v0_1.json), [preparation result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_02_result_v0_1.json); ignored `accepted_nba_reference_inventory_after_batch_02.json` | Ryan accepted all 120 centers, including 68 full/52 partial judgments and 4–7px uncertainty. Original 2s/12s overlays, revisions and failures remain unchanged; 543 files preserved. Actual publication/inventory readers and duplicate guard pass. Coverage after NBA02 was 240/3,839, with 216 centers/24 nulls; curated 868 unchanged. Prior 12 acceptance and 13 renderer tests retained without rerun. Label eligibility does not authorize package readiness, fitting or protected evaluation. |
| NBA completion reference batch 01, accepted | [Acceptance and original review](../ball_tracking_completion_nba_reference_batch_01.md), [acceptance receipt](../../configs/ball_tracking/reviews/nba_completion_reference_batch_01_acceptance_v0_1.json), [preparation result](../../configs/ball_tracking/reviews/nba_completion_reference_batch_01_result_v0_1.json), `src/ball_tracking/completion_nba_acceptance.py` and `completion_nba_references.py` | Ryan accepted 120 labels: 96 centers/24 nulls. All 286 original files, native/slow review_v2, source-color/render-metadata failures and eight-test history remain preserved. Delivery passed 13 focused tests, 317 bindings, 240 encoded frames and 192 markers. Later acceptance-reader scope revision passed 12 tests; historical preparation status remains unchanged. Source final 662 differs from batch final 119. |
| Grouped acceptance of completion batches 05–07 | [Batch 05 acceptance](../../configs/ball_tracking/reviews/ball_completion_reference_batch_05_acceptance_v0_1.json), [batch 06 acceptance](../../configs/ball_tracking/reviews/ball_completion_reference_batch_06_acceptance_v0_1.json), [batch 07 acceptance](../../configs/ball_tracking/reviews/ball_completion_reference_batch_07_acceptance_v0_1.json); ignored `accepted_reference_inventory_after_batch_07.json` | Ryan explicitly accepted all 102 judgments together: 77 centers and 25 nulls. Current curated coverage 868/1,273 with 760 eligible centers and 405 uncovered. All 766 prior rows and 330 bound original files preserved; actual production consumers and duplicate guards pass. Original preparation rows below retain their pending-era evidence; later receipts supply current status. No source decode, fitting or protected evaluation. |
| Completion reference batch 07, acceptance pending | [Report and complete overlays](../ball_tracking_completion_reference_batch_07.md), [preparation result](../../configs/ball_tracking/reviews/ball_completion_reference_batch_07_result_v0_1.json), `configs/ball_tracking/completion_campaign/reference_batch_07_v0_1.json` | 29 evaluation-only P001 21–49 proposals: 10 centers, 19 nulls, 7–10px uncertainty. Batches 05/06 remain pending. All 766 accepted rows and 1,011 prior files preserved. Native PTS has a 512-tick origin; permitted packet context 0–52; 29 exact PNG comparisons, 58 encoded frames and 20 markers checked. Pre-execution helper corrections preserved. No fitting or protected evaluation. |
| Completion reference batch 06, acceptance pending | [Report and complete overlays](../ball_tracking_completion_reference_batch_06.md), [preparation result](../../configs/ball_tracking/reviews/ball_completion_reference_batch_06_result_v0_1.json), `configs/ball_tracking/completion_campaign/reference_batch_06_v0_1.json` | 30 evaluation-only P003 120–149 proposals: 30 centers, no nulls, 5–8px uncertainty. Batch 05 remains separately pending. All 766 accepted rows and 935 prior files preserved. Zero-origin native PTS; permitted packet context 0–153; 30 exact PNG comparisons, 60 encoded frames/markers checked. One helper field error preserved. No fitting or protected evaluation. |
| Completion reference batch 05, acceptance pending | [Report and complete overlays](../ball_tracking_completion_reference_batch_05.md), [preparation result](../../configs/ball_tracking/reviews/ball_completion_reference_batch_05_result_v0_1.json), `configs/ball_tracking/completion_campaign/reference_batch_05_v0_1.json` | 43 evaluation-only P002 275–317 proposals: 37 centers, six nulls. Complete review delivered; all 766 accepted rows and 829 prior campaign files preserved. Permitted packet context 250–322; all 43 PNGs match bounded comparison. All 86 encoded frames/74 markers checked. Metadata assertion failures and corrections retained. No fitting or protected evaluation. |
| Completion reference batch 04, accepted | [Report and complete overlays](../ball_tracking_completion_reference_batch_04.md), [preparation result](../../configs/ball_tracking/reviews/ball_completion_reference_batch_04_result_v0_1.json), [later acceptance](../../configs/ball_tracking/reviews/ball_completion_reference_batch_04_acceptance_v0_1.json), `configs/ball_tracking/completion_campaign/reference_batch_04_v0_1.json` | Ryan accepted all 75 evaluation-only P001 125–199 judgments: 58 centers, 17 nulls. All 691 previous rows preserved; current coverage 766/1,273, 507 remaining. Native PNGs match bounded independent decoding with permitted packet context 0–204. Unchanged implementation; 150 emitted frames/116 markers checked. No fitting, inference or protected evaluation. |
| Completion reference batch 03, accepted | [Report and complete overlays](../ball_tracking_completion_reference_batch_03.md), [preparation result](../../configs/ball_tracking/reviews/ball_completion_reference_batch_03_result_v0_1.json), [later acceptance](../../configs/ball_tracking/reviews/ball_completion_reference_batch_03_acceptance_v0_1.json), `configs/ball_tracking/completion_campaign/reference_batch_03_v0_1.json` | Ryan accepted all 131 evaluation-only P002 368–498 judgments through the actual clip final: 114 centers, 17 nulls. All 560 prior rows preserved; current 691/1,273 accepted, 582 remaining. Every native PNG matches a bounded independent decode using only permitted packets 250–498. Source implementation unchanged; actual-record/media validation. No fitting, inference or protected evaluation. |
| Completion reference batch 02, accepted | [Report and complete overlays](../ball_tracking_completion_reference_batch_02.md), [preparation result](../../configs/ball_tracking/reviews/ball_completion_reference_batch_02_result_v0_1.json), [later acceptance](../../configs/ball_tracking/reviews/ball_completion_reference_batch_02_acceptance_v0_1.json), `configs/ball_tracking/completion_campaign/reference_batch_02_v0_1.json` | Ryan accepted all 120 evaluation-only P002 50–169 judgments, including uncertainty/nulls: 98 centers, 22 null. Earlier 440 accepted rows and batch-01 media unchanged; current 560/1,273 accepted, 713 remaining. Ten focused tests; 120 native PNGs pixel-identical; complete overlays through 169. No fitting, inference or protected evaluation. |
| First completion-campaign increment | [Results and review links](../ball_tracking_completion_first_increment.md), [first-batch acceptance](../../configs/ball_tracking/reviews/ball_completion_reference_batch_01_acceptance_v0_1.json), `configs/ball_tracking/completion_campaign/`, `completion_baseline.py`, `completion_references.py`; ignored `completion_campaign_v0_1/` | Reuses exact retained observations and three reviewed videos; 1,498 records, 979 points, 294 missing, 225 protected. Four fixed NBA roles/24 source-first episodes and 3,839 pending NBA slots. Ryan accepted 120 new P003 AI labels, evaluation-only: accepted curated coverage 440/1,273, 833 uncovered. No fit, protected evaluation or phase promotion. Supersedes deferred-execution status below. |
| Approved ball-phase completion campaign and numerical exit contract | [Approval record](../../configs/ball_tracking/reviews/ball_tracking_completion_campaign_approval_v0_1.json), [completion plan](../ball_tracking_completion_plan.md) | Ryan approved the exact plan at `faa2804` and requested execution in a new session. Supersedes pending approval below; no campaign execution yet. New labels/final trajectories still require human review, and 225 protected positions require frozen-method plus separate evaluation authorization. |
| Proposed ball-phase completion campaign | [Completion plan](../ball_tracking_completion_plan.md); current state and working agreement | Research/result review at `759f43d`; proposed new numerical gate for three complete curated possessions, one multi-game reference package, one primary WASB fit and at most one conditional higher-resolution fit. No new scientific execution; approval pending. Retained baseline, failed experiments, accepted reviews and protected evaluation boundaries preserved. |
| Single provisional trained ball-versus-distractor model | [Training results and media](../nba_ball_distractor_training_results.md), [execution amendment](../../configs/ball_tracking/reviews/nba_ball_distractor_execution_amendment_v0_1.json), [compact result](../../configs/ball_tracking/reviews/nba_ball_distractor_training_result_v0_1.json); classifier, training, emission-feature, policy, evaluation and review modules | One converged 385-parameter fit on 90 objects / 109 crops; full 3,373-emission comparison loses 207/581 protected matches. Rejected for adoption; no tuning. New AI labels and new motion review pending human judgment; prior insufficient-coverage result and original baselines preserved. |
| Approved bounded reference batch; provisional insufficient-data result | [Results/review](../nba_ball_distractor_reference_results.md), [approval](../../configs/ball_tracking/reviews/nba_ball_distractor_verifier_approval_v0_1.json), [bound result](../../configs/ball_tracking/reviews/nba_ball_distractor_reference_result_v0_1.json); three `nba_ball_distractor_reference*` modules and focused tests | All184 proposed rows / 105targets / 525frames;106ball51other27unknown;26 accepted classes unchanged.147resolved physical groups (90fit57check); fails excluded clothing and actually-emitted head coverage.14focused tests and independent source/label/media audits; no features/fit/trajectory change. New human labels/grouping pending; full review through finals. Supersedes historical pending execution status below. |
| Bounded ball-versus-distractor test design; execution pending | [Plan](../nba_ball_distractor_verifier_plan.md), [proposal](../../configs/ball_tracking/proposals/nba_ball_distractor_verifier_v0_1.json); bound ignored inventory under `data/outputs/t/ball_distractor_full_pool_design_2026-10-21/` | 426 existing triplets reconstructed at 142 targets, all original means exact; no new pixels/labels/model calls. Fixed 160 candidate judgments plus 24 fit-only contrast slots, 105 targets/525 context frames. One conditional 385-parameter fit and full 3,373-emission veto comparison proposed. Requires diverse accepted labels, actual emitted-error removal, zero verified-ball loss and new human trajectory acceptance. P001 fit expansion explicit; DET/P003 excluded, unknowns/old qualitative cases separate, no replacement/tuning loop. |
| Completed fixed appearance-feature screen; scientific gate failed | [Results and crop review](../nba_appearance_feature_screen_results.md), [approval](../../configs/ball_tracking/reviews/nba_appearance_feature_screen_approval_v0_1.json), [compact result](../../configs/ball_tracking/reviews/nba_appearance_feature_screen_result_v0_1.json); `nba_appearance_feature_screen.py`, `nba_appearance_feature_screen_review.py` and six focused tests | Supersedes historical pending proposal below. One 12.594s run, 60 encodings/49 PNGs/500 similarities; 8/10 accepted checks, two real balls rejected; all three SAC heads still ball-preferred, all four DET near-head balls retained. Six unknowns unscored; 34 exposed AI judgments separate. Audit 3,914 checks; all 50 query rows/final AI-inspected and 150 crop panels exact. Fixed setup rejected; no tuning, labels or trajectory changes. |
| All 26 appearance references accepted; separate publication complete | [Acceptance results](../nba_appearance_reference_acceptance_results.md), [acceptance](../../configs/ball_tracking/reviews/nba_appearance_reference_acceptance_v0_1.json), [publication result](../../configs/ball_tracking/reviews/nba_appearance_reference_publication_result_v0_1.json); `nba_appearance_reference_acceptance.py` and six focused tests; ignored `appearance_reference_v0_1/accepted/` | Supersedes the pending appearance-label status below. Ryan: “I accept the proposals. Move forward chat”. All26 exact labels/candidates,15 targets/75 frames; ten ball/ten other/six unresolved, AI authorship/source roles and DET11499 disagreement preserved. Separate artifact published in0.696s; six focused tests10.845s and380 independent audit checks pass. Original draft/media/pending receipts and prior27/790 results remain unchanged. No source decode, inference, fitting or score change; completed review need not repeat. |
| Proposed fixed appearance-feature feasibility screen; approval pending | [Fixed screen plan](../nba_appearance_feature_screen_plan.md), [proposal](../../configs/ball_tracking/proposals/nba_appearance_feature_screen_v0_1.json) | Not approved or run. DINOv2 ViT-S/14, one nearest-reference comparison:60 crops/49 cached target frames, comprising10 resolved SAC bank objects,10 resolved excluded checks,six unknowns and34 old exposed regression objects. Strict10/10 resolved-check gate; unknowns unscored, no training/grid/trajectory changes. Bank is SAC-only; excluded negatives are hands, without head/clothing examples. Old regression points have mixed mean/contributor provenance and are not an unseen head test or contributor-generalization evidence. |
| Earlier preparation snapshot: candidate appearance references awaiting human acceptance | [Fixed plan](../nba_appearance_reference_preparation.md), [approval](../../configs/ball_tracking/reviews/nba_appearance_reference_preparation_approval_v0_1.json), [scope](../../configs/ball_tracking/selections/nba_appearance_reference_v0_1.json), [results and review links](../nba_appearance_reference_results.md), [compact result](../../configs/ball_tracking/reviews/nba_appearance_reference_result_v0_1.json); `nba_appearance_reference.py`, `nba_appearance_reference_review.py` and ten distinct focused tests | Fifteen targets, all 26 original mean candidates and 75 native context frames, fixed before new source inspection. AI proposals: ten ball, ten other-object, six unresolved; one recorded reader disagreement remains unresolved. SAC/P002 potential-fit 4/6/5; DET/P003 excluded-check 6/4/1. No new excluded-check head negative; correlated and previously seen development evidence. One 14.968s preparation reads 55 existing NBA PNGs and decodes twenty permitted NFHS frames; first render 20.359s produces a complete 48-second review. Scope audit86, independent media audit1,649, all75 encoded-frame transport checks and all31 target/context/final still inspections pass. Fixture and test-regex failures preserved. No fitting, inference, new centers, geometric scoring or prediction changes. Prior accepted references, original790 report, protected holdouts and earlier reviews unchanged. Ryan must accept or correct this new appearance batch before use. |
| Accepted gap/anchor references and completed saved-output evaluation | [Evaluation results](../nba_gap_anchor_reference_evaluation_results.md), [acceptance](../../configs/ball_tracking/reviews/nba_gap_anchor_reference_acceptance_v0_1.json), [compact evaluation result](../../configs/ball_tracking/reviews/nba_gap_anchor_reference_evaluation_result_v0_1.json); `nba_gap_anchor_reference_evaluation.py` and four focused tests; ignored `gap_anchor_reference_v0_1/accepted/` and `evaluation/` | Supersedes pending reference acceptance below. Ryan accepted the presented package; assisted authorship and non-blind development status remain. New27: 14 matched/8 missing/5 unscored becomes 22 matched/0 missing/5 unscored, zero geometric errors; seven exact controls excluded from new totals. Eight added geometric matches comprise six AI ball judgments and two unresolved P001 boundaries. SAC head anchors/fill stay unscored and adverse; P003333/334 remain unknown. Original790/draft/media unchanged. One 2.156s metadata-only run at `9ee85aee0d468674efae855bb8da6893e183a2b8`; audit bound by compact result. Next proposal: appearance evidence for anchors and fill candidates, distinct temporal examples and abstention; no new fit or broader adoption. |
| Gap/anchor AI references ready for human review | [Results and review links](../nba_gap_anchor_reference_results.md), [approval](../../configs/ball_tracking/reviews/nba_gap_anchor_reference_approval_v0_1.json), [frozen scope](../../configs/ball_tracking/selections/nba_gap_anchor_reference_v0_1.json), [compact result](../../configs/ball_tracking/reviews/nba_gap_anchor_reference_result_v0_1.json); preparation/renderer modules and focused tests | Supersedes unexecuted reference status below. Later “Move forward chat” approved preparation. 27 new AI judgments (22 centers, five unknowns), seven exact accepted controls, 74 native source frames, ten complete contexts. Proposal sealed before separate 34-object inspection: 23 ball/three head/eight unresolved; no new geometric scores. One verified 24.8-second review; all 34 targets, ten finals and actual final inspected. Eleven distinct focused tests, 792 source-audit checks and 1,232 media-audit checks pass; renderer-test tolerance failure retained. New references pending human acceptance; all old reviews/evidence and broader non-adoption remain. |
| Latest continuous video review and next reference proposal | [Later review completion](../../configs/ball_tracking/reviews/nba_temporal_gap_continuous_visual_review_v0_1.json), [current results](../nba_temporal_gap_continuous_validation_results.md), [27-frame reference proposal](../nba_gap_anchor_reference_plan.md) | Supersedes pending render/review descriptions below: all five comparisons passed full media checks and Ryan said “Ok videos reviewed. What’s next chat”. User-reported completion, no playback telemetry, explicit quality endorsement or per-frame adjudication. Original pending-era receipts and AI head-fill/uncertainty findings remain; no broader adoption. Proposed, not run: 27 new judgments + seven accepted controls across all ten gaps/20 anchors, 74 permitted context frames, one compact review followed by separate accepted-reference scoring. No new fit, inference or threshold tuning. |
| Public purpose, current pipeline, roadmap | Current Git-state `README.md`, `docs/context/current_state.md`, and `docs/context/roadmap.md` | PR #6 and Chat 06 are historical rationale only |
| Stage order and modes | `src/pipeline/planner.py` | Chats 05–06 |
| Manifest/path contract | `src/pipeline/possession.py`, `configs/*_pipeline.json` | Chat 05 |
| Execution/resume behavior | `src/pipeline/execution.py`, tests | Chats 05–06 |
| Gate rules | `src/pipeline/generalization_gate.py`, `docs/pipeline_generalization.md` | Chats 05–06 |
| Possession 003 result | `configs/possession_003_generalization_evidence.json` | Chat 06 |
| Ball annotation semantics and review contract | `docs/ball_tracking_annotation_protocol.md`, `src/ball_tracking/annotations.py`, `src/ball_tracking/detections.py`, reviewed files under `configs/ball_tracking/annotations/` | Current desktop ball-tracking work |
| Ball-detector window selection | `docs/ball_detector_baseline_selection.md`, `configs/ball_tracking/experiments/rfdetr_medium_image_only_baseline_v0_1.json` | Prediction-free source contact sheets are temporary supporting evidence only |
| Ball-detector execution contract | `src/ball_tracking/detector_experiments.py`, `src/ball_tracking/rfdetr_adapter.py`, `src/ball_tracking/run_detector_experiment.py`, tests | Current desktop ball-tracking work |
| RF/YOLO corroboration outcome | `docs/ball_crop_cross_detector_corroboration_results.md`, saved six-window/two-pool outputs and recovery record | October 8 recovered negative result; original reporting attempt remains failed |
| WASB temporal ball transfer | `docs/ball_wasb_transfer_results.md`, `configs/ball_tracking/wasb_experiments/wasb_basketball_transfer_v0_1.json`, new adapter/point evaluator/runner and ignored cached outputs | October 8 completed six-window comparison; fixed setting too sparse, no method/quality gate promoted |
| WASB cached calibration and approved adaptation plan | `docs/ball_wasb_calibration_results.md`, `src/ball_tracking/wasb_calibration.py`, calibration config/tests; `docs/ball_wasb_adaptation_plan.md` | Eight cached thresholds completed; immutable pretraining plan preserved; subsequent training results are in the next row |
| Completed WASB pilot adaptation | `docs/ball_wasb_adaptation_results.md`, adaptation experiment config, `configs/ball_tracking/reviews/wasb_basketball_adaptation_visual_review_v0_1.json`, trainer/derived adapter/evaluator/review modules and tests | Approved single 200-update fit and six-window comparison; 98 matches/one wrong at 0.5; all six clips reviewed by Ryan with observations |
| Remaining WASB gaps and reviewed training data | `docs/ball_wasb_remaining_gap_diagnosis.md`, prepared data proposal, `configs/ball_tracking/reviews/wasb_training_data_expansion_approval_v0_1.json`, tag-correction and label-review records, `docs/ball_wasb_training_expansion_annotation_guide.md` | All 75 new labels completed and visually approved; original labels and corrected-tag history preserved |
| Completed expanded WASB adaptation | `docs/ball_wasb_expanded_adaptation_results.md`, `configs/ball_tracking/wasb_experiments/wasb_basketball_expanded_adaptation_v0_1.json`, versioned trainer and paired evaluator | One original-initialized 200-update fit; primary120 matches/2 errors/23 missing; cached0.3 candidate130/1/14; new-output visual review pending |
| Longer WASB development observations | `docs/ball_wasb_development_observation.md`, `src/ball_tracking/wasb_development_observation.py`, observation config/tests, ignored summary and audit; `configs/ball_tracking/reviews/wasb_expanded_development_observation_visual_review_v0_1.json` | Frozen checkpoint/0.3; 1,273 visible frames, 225 protected timeline positions; 979 points/294 missing are unlabeled availability counts; Ryan reviewed all three videos; motion selection is a proposed next comparison |
| Completed fixed WASB motion comparison | [Comparison and new review videos](../ball_wasb_motion_selection.md), `configs/ball_tracking/wasb_experiments/wasb_motion_selection_v0_1.json`, `wasb_motion_selection.py`, `wasb_motion_evaluation.py`, `wasb_motion_review.py`, focused tests; ignored `wasb_motion_selection_v0_1/` summary, independent audit and visual notes | Implementation `915ba13c2910efa7f875cb251b7bc049790d1df3`; one completed invocation, zero model calls; both same-context arms 131/1/13 with zero hidden alarms and all 150 scored choices unchanged; 13 other changes include visible recovery losses, so do not promote; three new human video reviews pending; supersedes the earlier proposed-motion status |
| External sports tracking research and implementation choices | `docs/research/README.md`, `docs/research/recommendations.md`, detailed chapters and four source ledgers | October 8 primary-source research; source inspection is not local reproduction or runtime authority |
| NBA footage access and original NFHS acquisition provenance | [October 18 decision report](../research/nba_footage_access.md), unofficial/platform/dataset chapters and `nba_footage_access_sources.json`; ignored `data/outputs/t/nba_footage_access_research_2026-10-18/` receipts | Initial exact-game samples, separate complete BARD clip, repeated endpoints and historical full-game alternatives; Chat 01 actual command/terminal evidence resolves original NFHS source, without rescanning old footage |
| Chosen NBA recording acquisition and continuity limits | [Full acquisition report](../research/nba_game_0022500828_acquisition.md), sanitized evidence JSON and ignored `data/outputs/t/nba_full_game_acquisition_2026-10-18/` receipts | Complete 6.08 GB target, independent range/hash audit and one full 415,953-frame video/audio decode; four quarters present, Q4 opening inbound not established after interview transition; every-possession continuity unproven. This acquisition alone did not establish repeatability; the subsequent result is in the next row. No new ball experiments or old holdout access |
| Repeated NBA recording acquisition | [Repeatability report](../research/nba_footage_repeatability.md), sanitized evidence JSON and ignored `data/outputs/t/nba_repeatable_access_2026-10-18/` receipts | Two more complete 1080p recordings, independent assembled-range/hash audits and single full A/V decodes; all four quarters and final results observed. Three specific recordings establish practical repeated access, not catalog-wide or every-possession coverage. Original Kings receipt-writing failure/recovery and Toronto output-timing warning preserved; chosen-game Q4 limitation unresolved; no scientific gate or human review promoted |
| NBA source candidates and proposed split | [Selection plan and primary review clips](../nba_development_selection_plan.md), `configs/ball_tracking/selections/nba_development_selection_proposal_v0_1.json`; ignored `data/outputs/t/nba_possession_selection_2026-10-18/` | Six verified source-only review derivatives, exact frame/PTS mappings, retained cut/overlay/partial-start limitations; proposed SAC training / SAS–DET target development / SAS–TOR additional development roles and 120-frame annotation pilot. Decision and human source review pending; no labels or model work, no independent test designation, no change to NFHS gates |
| Approved NBA native-frame pilot and editor | [Annotation guide](../nba_native_annotation_guide.md), `configs/ball_tracking/reviews/nba_development_selection_approval_v0_1.json`, `nba_annotation_pilot_preparation_v0_1.json`; separate `nba_annotations.py`, `prepare_nba_annotation_pilot.py`, `annotate_nba_frames.py` and editor HTML | Supersedes the proposal's pending allocation/pilot status. 120 original-frame PNGs and unlabeled drafts, exact PTS/RGB checks plus independent bounded decode; 12 schema, 3 synthetic extraction and 12 current editor checks. Draft labels and later visual acceptance remain pending; ignored data retains receipts, initial bindings, UI verification and browser-control timeout history |
| Assistant-first NBA ball proposals | [Current guide](../nba_native_annotation_guide.md), [working agreement](working_agreement.md), `configs/ball_tracking/reviews/nba_assisted_annotation_pilot_v0_1.json`, `prepare_nba_assisted_review.py` and five focused tests | Supersedes the all-manual starting plan. 120 separately authored AI proposals, two 11-second review videos, 13 priority frames and independent actual-output audit; original drafts untouched. Human acceptance remains pending; no tracker accuracy, training or phase-completion claim |
| Human-accepted AI NBA pilot reference | `configs/ball_tracking/reviews/nba_assisted_label_acceptance_v0_1.json`, `nba_reviewed_reference.py`, six focused checks; ignored `reviewed_pilot_v0_1/reference.json` | Supersedes pending human label acceptance above. Ryan accepted both presented packages; 120 original native PNGs checked at separate publication. AI authorship/uncertainty retained; original proposals and blank drafts unchanged. Not independent human labeling or a fit/evaluation approval |
| Prepared native-cadence NBA diagnostic | [Exact proposed recipe](../nba_wasb_native_pilot_diagnostic.md), `configs/ball_tracking/wasb_experiments/nba_wasb_native_pilot_diagnostic_v0_1.json`, `nba_wasb_diagnostic.py` and focused tests | Read-only plan: 120 frames, 116 distinct triplets, native 16–17 ms spacing, frozen expanded checkpoint/0.3. Synthetic execution/resume/render checks only; scientific execution pending approval. No actual inference, training, hidden-negative measurement or phase promotion |
| Completed approved NBA native-cadence diagnostic | [Result and new review videos](../nba_wasb_native_pilot_diagnostic_results.md), `configs/ball_tracking/reviews/nba_wasb_native_pilot_diagnostic_approval_v0_1.json`, `nba_wasb_native_pilot_diagnostic_result_v0_1.json`; ignored `data/outputs/ball_tracking/nba/wasb_native_pilot_diagnostic_v0_1/` | Supersedes pending execution above. One 49.766-second run, 116 unique calls, zero failures; each game 60 matches/0 wrong/0 missing at inclusive 10 px. No training or original-game decode. Independent saved-output/media audit passed; all 120 overlays inspected by AI; new model-output human reviews pending and AI-reference acceptance unchanged. Two selected visible-ball scenes, no hidden negatives, cadence comparison, independent benchmark or phase pass |
| Human-accepted NBA native pilot model outputs | `configs/ball_tracking/reviews/nba_wasb_native_pilot_visual_review_v0_1.json`, [current result status](../nba_wasb_native_pilot_diagnostic_results.md); ignored `wasb_native_pilot_diagnostic_v0_1/accepted.html` | Supersedes the pending model-output human reviews above. Ryan accepted both presented complete videos on October 19, including their actual final frames, with no corrections. User-reported review; no playback telemetry claimed. Original pending-era records, media and page stay unchanged; reference acceptance remains separate. No broader recipe, phase pass or motion-review acceptance inferred |
| Proposed longer NBA action observation | [Exact plan](../nba_wasb_action_observation_plan.md), `configs/ball_tracking/selections/nba_wasb_action_observation_proposal_v0_1.json` | Design-only and non-runnable, pending scope approval to implement, validate and run once. SAC 540–2010 and DET 10668–11898: 2,702 native frames, at most 2,698 triplets with 116 planned cache imports and 2,582 new calls. Frozen checkpoint/strict >0.3, no training or new-label scoring. Complete videos and availability summaries proposed; original pilot result and game roles preserved. Additional read-only check of 116 existing caches found zero issues; no new model/source/scoring run. NFHS finish line, holdouts and three pending motion reviews unchanged |
| Completed longer NBA action observation | [Results and new review videos](../nba_wasb_action_observation_results.md), `configs/ball_tracking/reviews/nba_wasb_action_observation_approval_v0_1.json`, [compact result record](../../configs/ball_tracking/reviews/nba_wasb_action_observation_result_v0_1.json); `nba_action_inputs.py`, `nba_action_observation.py`, `nba_action_review.py` and focused tests; ignored completion, independent audit and visual-inspection receipts | Supersedes pending approval/implementation above without changing the proposal. Implementation `4b67d0850897d539ab2994afc6349c0b6af11667`, 23 distinct focused checks (7 input/12 observation/4 review); full suite not repeated. One 1,238.416-second run, 2,582 new calls + 116 imports, zero call failures. SAC 1,310/161/0 and DET 1,070/161/0 observed/missing/withheld; availability, not accuracy. Independent 27.172-second audit passed: all 2,698 caches/2,702 means/2,711 components, 112 identical pilot interiors and eight changed contexts. Both videos fully verified through final frames; AI inspection covered all 2,702 frames and both actual final frames, with 14 SAC and seven DET cues. Distractors/gaps remain, both new human reviews pending. Loaded preparation-helper snapshot/on-disk-change nuance, setup failures, original short-pilot acceptance and scientific boundaries preserved |
| User-reported longer NBA video review | `configs/ball_tracking/reviews/nba_wasb_action_observation_visual_review_v0_1.json`, [current result status](../nba_wasb_action_observation_results.md) | Supersedes pending human review of the two longer videos above. Both complete videos were delivered in chat for phone viewing; Ryan said “Ok reviewed. What’s the next step”. User-reported completion only, without playback telemetry, explicit quality endorsement or new experiment authorization. Distractor/gap findings, original result/media, prior short-pilot acceptance and three pending motion reviews remain unchanged |
| Proposed NBA hard-example references and saved-output diagnostic | [Exact plan](../nba_hard_example_reference_plan.md), `configs/ball_tracking/selections/nba_hard_example_reference_proposal_v0_1.json` | Design-only, pending approval: 520 new AI-proposed labels in SAC 940–1059/1240–1359 and DET 11000–11119/11420–11579, followed by human reference-overlay acceptance before saved-output scoring. Up to 640 scored frames includes 120 existing pilot references as separate longer-context easy controls; original short-pilot score unchanged. Preserve uncertainty/unscored indefensible centers; source/model-selected hard examples are a biased development diagnostic, not independent NBA accuracy. No new labels, scoring, inference, training, threshold or motion change; SAC future-training-eligible, DET excluded from fitting, TOR outside scope |
| Approved NBA hard-example label preparation | [Review guide](../nba_hard_example_reference_review.md), [scope approval](../../configs/ball_tracking/reviews/nba_hard_example_reference_approval_v0_1.json), [bound preparation record](../../configs/ball_tracking/reviews/nba_hard_example_reference_preparation_v0_1.json), `src/ball_tracking/nba_annotations.py`, `tests/test_nba_hard_example_assets.py` | Historical preparation status: four complete packages prepared after “Ok move forward”; 520 AI labels, 387 proposed centers and 133 null centers. Human label acceptance pending; no new reference publication, scoring, inference or training. All 520 PNG transport checks, four video timelines and final-frame inspections passed; 26 focused tests passed. Generated evidence remains under ignored `data/outputs/ball_tracking/nba/hard_example_reference_v0_1/`. Original proposal/history, pilot score, game roles, holdouts, NFHS finish line and three pending motion reviews remain unchanged |
| Accepted NBA hard-example reference and saved-output diagnostic | [Results](../nba_hard_example_reference_results.md), [label acceptance](../../configs/ball_tracking/reviews/nba_hard_example_label_acceptance_v0_1.json), [compact result](../../configs/ball_tracking/reviews/nba_hard_example_saved_diagnostic_result_v0_1.json); `src/ball_tracking/nba_hard_example_reference.py`, `nba_hard_example_diagnostic.py` and focused tests; ignored accepted reference and saved-score completion | Supersedes pending label acceptance/scoring above. Ryan accepted all four complete packages without corrections; AI authorship and 133 null centers remain. Saved outputs: 305/387 matches, 13 wrong, 69 missing; 13/86 hidden alarms and 47 other unscored. No alternative saved component within ten pixels for any of 82 failures. Separate longer controls 120/120 including eight context edges; original pilot score unchanged. Thirty distinct current focused checks passed; independent actual-report audit passed with zero issues over 20 bound files, all 2,702 producer records and 640 scored rows. No new inference, training, threshold change or heatmap reaggregation. Biased, correlated development diagnostic; slowed label overlays are not model improvement. Roles, holdouts, NFHS gates and three pending motion reviews preserved |
| Completed approved NBA saved-heatmap inspection | [Results](../nba_hard_example_heatmap_inspection_results.md), [frozen scope](../../configs/ball_tracking/selections/nba_hard_example_heatmap_inspection_v0_1.json), [compact result](../../configs/ball_tracking/reviews/nba_hard_example_heatmap_inspection_result_v0_1.json); `src/ball_tracking/nba_saved_heatmap_diagnostic.py` and focused tests; ignored `hard_example_heatmap_inspection_v0_1/` | One 19.937-second run reconstructs all 640 original means/candidates/selections from 652 caches, 1,037,888,584 compressed bytes. Missing local median 0.117843; 11/69 have individual support lost in averaging, 58 have none. Of 13 wrong components, 11 overlap the reference disk and three peaks match; peaks lose six current difficult matches. Seven new focused checks pass; 3.297-second independent audit passes all 640 structural/summary and 652 cache-metadata checks, with numeric reconstruction of 126 rows (all 82 failures + 44 context) from 237 caches; other 514 not independently numerically recomputed. Responses are uncalibrated, no labels/predictions/scores changed, no inference/fit/threshold sweep. Bounded SAC adaptation/data design with eligible NFHS training examples recommended, unapproved; all roles, holdouts, NFHS gates and pending motion reviews preserved |
| Approved mixed NBA/NFHS continuation — numerical screen failed | [Plan](../nba_wasb_adaptation_plan.md), [results and eight videos](../nba_wasb_adaptation_results.md), [bound result](../../configs/ball_tracking/reviews/nba_wasb_adaptation_result_v0_1.json), [later review completion](../../configs/ball_tracking/reviews/nba_wasb_adaptation_visual_review_v0_1.json); frozen config/approval; `src/ball_tracking/nba_wasb_adaptation.py`, `nba_adaptation_comparison.py` and focused tests; ignored `wasb_adaptation_v0_1/` | Supersedes unapproved adaptation status above. One 200-update fit in 50.328s; checkpoint da44ce06cdf7. SAC 300 + NFHS 150 pool; 424 usable triplets, 400 samples (269 NBA / 131 NFHS) touching 440 frames. One 1,425.922s comparison/media run, 2,836 new calls, no failed/uncertain calls. SAC training matches 218→265/270, DET development 207→206/237 with wrong locations 8→10, NFHS 130→129/145. Four of nine conditions fail; expanded baseline 09da retained. Seventeen distinct tests, 3,469 training-audit and 48,264 comparison-audit checks pass; 56 numeric means independently reconstructed, all 790 scores derived. Eight complete videos/2,852 source frames pass transport; AI inspects 56 source samples and all eight encoded finals. NFHS phone compilation preserves all 150 decoded frames/timing across 31s. Preflight/audit/packaging-check failures remain recorded; no second fit/tuning. Ryan reports reviewing three inline embeds covering both NBA videos and all six NFHS windows via the verified compilation; no playback telemetry or explicit quality endorsement. Original pending-review receipts preserved; failed gates/baseline unchanged. Planned, not run: 37 context frames/74 old-new means around six lost and four recovered matches, preserving original cached contributors; no new fit/tuning authorized. DET fitting exclusion, TOR/holdouts/NFHS gates and three pending motion reviews unchanged |
| Completed 37-frame continuation regression diagnostic | [Results](../nba_adaptation_regression_diagnostic_results.md), [bound scope](../../configs/ball_tracking/selections/nba_adaptation_regression_diagnostic_v0_1.json), [compact result](../../configs/ball_tracking/reviews/nba_adaptation_regression_diagnostic_result_v0_1.json); `nba_adaptation_regression_diagnostic.py` and focused tests; ignored `adaptation_regression_diagnostic_v0_1/` | Supersedes planned diagnosis above. One 2.375s run reproduces all 74 means/candidates/selections/scores across 37 frames. Eight tests pass; independent audit fully recomputes all 74 means and passes 20,962 checks after a preserved helper-only omission. Reads 94 triplet caches (149,913,392B) plus three NFHS mean bundles (39,639,143B; 75 planes loaded/22 measured). DET11107 correct candidate loses mass ranking to hand; DET11501 centroid crosses 9.272→10.014px while peak remains 4.809px away; four NFHS means lose >0.3 support despite individual contributors, while four gains cross threshold. No universal fix/causal forgetting claim. Next proposal only: preserve mean candidates plus provenance-tagged original-contributor components at unchanged >0.3 across existing 790 frames; compare candidate availability/extra candidates/newly nonempty hidden frames, not selected predictions; unexecuted and not authorized by this request. No model/inference/fit/source decoding or prediction/label/score change; failed continuation, 09da baseline, completed video review and protected holdouts unchanged |
| Completed candidate-preservation experiment | [Frozen design and appended results](../nba_candidate_preservation_experiment.md), [compact result](../../configs/ball_tracking/reviews/nba_candidate_preservation_result_v0_1.json); `nba_candidate_preservation.py` and focused tests; ignored `candidate_preservation_v0_1/` | Supersedes proposed status above. One 22.094s run: 790 frames, 1,580 means, 4,668 contributors. Old baseline DET availability 207→213/237, NFHS 130→133/145: nine of 45 prior unavailable frames gained; 36 remain unavailable. Costs: 51 extra ambiguous development frames, DET hidden nonempty 13→18/69, median raw candidates 1→4; controls 120/120 with ambiguity 7→20. Seven distinct tests pass after one preserved fixture-only correction; audit passes 181,673 checks on first attempt, with all 1,580 arm evaluations checked and 141 rows numerically reconstructed including every gain/new hidden case. Minimal screen supports one fixed label-blind selector trial, not executed/authorized or a quality pass. No fit/inference/media/score change; baseline, failed continuation, reviews and holdouts preserved |
| Accepted temporal-gap development increment and next proposal | [Later visual approval](../../configs/ball_tracking/reviews/nba_temporal_gap_selection_visual_review_v0_1.json), [continuous-context plan](../nba_temporal_gap_continuous_validation_plan.md) | Ryan explicitly approved all three presented comparisons. Supersedes pending human-review status in the completed trial record; original receipts and baseline stay unchanged. Next proposal uses 3,975 allowed frames across two NBA cores/three NFHS clips, same-context controls, existing caches and unchanged rule; no execution, new fit, inference or holdout access. Longer NFHS control 131/1/13/0 remains distinct from short-window 130/1/14/0. Three older motion reviews remain pending |
| Completed continuous-context numerical validation; visual review pending | [Results](../nba_temporal_gap_continuous_validation_results.md), [approval](../../configs/ball_tracking/reviews/nba_temporal_gap_continuous_validation_approval_v0_1.json), [recovery scope](../../configs/ball_tracking/selections/nba_temporal_gap_continuous_recovery_01_v0_1.json), [compact result](../../configs/ball_tracking/reviews/nba_temporal_gap_continuous_validation_result_v0_1.json); `nba_temporal_gap_continuous.py`, renderer and focused tests; ignored `temporal_gap_continuous_v0_1/` and `data/outputs/t/continuous_gap_audit_2026-10-20/audit_01.json` | Supersedes the unexecuted broader proposal above. Ryan later authorized “Move forward chat”; initial resume alone did not. First attempt `890e7ac8` failed on imported NFHS model-only identity; source-window correction `ad82b03` and separate recovery preserve it. Successful `c4c9e3e8` run: 3,975 allowed frames/eight segments, 225 protected positions, all 3,359 original points exact, fourteen additions/ten gaps (three labeled matches, eleven unscored). Same-context DET 207/8/22→209/8/20; NFHS 131/1/13→132/1/12; hidden alarms thirteen/zero unchanged, SAC unchanged, both controls 60/60, exact three-addition retention. All 24 gates, 21 distinct focused tests and 42,844 independent audit checks pass. Five new renders and human trajectory review remain incomplete. No inference/fit/threshold search, baseline overwrite, holdout access or phase promotion. Historical short-window NFHS 130/1/14 remains separate; three older motion reviews pending |
| Adverse continuous-context visual evidence: SAC head fill | [Current results](../nba_temporal_gap_continuous_validation_results.md); ignored `data/outputs/ball_tracking/nba/temporal_gap_continuous_v0_1/review/ai_sac_context_inspection.json`, bound encoded frame and unmarked native crops 1418–1422 | AI inspection places the new SAC frame 1420 point (14.681 seconds into the comparison) on a foreground light-blue defender's head/face, between original anchors on that head at 1419/1421. All five PNG/RGB bindings match. This frame is outside the 790 scored references; no new label, visibility decision, center error or score change. True ball center/visibility uncertain. The 24 numerical gates and three accepted additions stand, but broader adoption of the unchanged rule is not recommended. Completion of all five renders and Ryan's new trajectory review/adjudication remain pending |
| Git history | repository commits and merged PRs | transcripts only for rationale |
| Completed fixed temporal gap-selection trial | [Prospective design and appended result](../nba_temporal_gap_selection_experiment.md), [frozen scope](../../configs/ball_tracking/selections/nba_temporal_gap_selection_v0_1.json), [compact result](../../configs/ball_tracking/reviews/nba_temporal_gap_selection_result_v0_1.json); `nba_temporal_gap_selection.py` and focused tests; ignored `temporal_gap_selection_v0_1/` | Supersedes the unapproved selector proposal above. Ryan approved “Ok awesome move forward chat”; one 0.391s run saved all 790 decisions before scoring. DET matches 207→209/237 and NFHS 130→131/145; three missing→matched changes, no new wrong outputs/hidden alarms; SAC and 120 easy controls unchanged. All sixteen numeric conditions and thirteen focused checks pass. Independent audit passes 165,219 checks, covering all 790 decisions/1,580 scores and preserving 597 original points. All three videos/790 frames and twelve encoded finals pass complete transport checks; AI inspects three encoded changed frames plus twelve finals. Human review pending. One fixed offline rule, no sweep, model work, heatmap read or original baseline overwrite; no phase promotion. |
| Generated local evidence | ignored `data/` tree plus hash manifest | attachment/archive manifests |
| Collaboration and Git rules | `AGENTS.md`, `working_agreement.md` | Chat 05 opening checkpoint |

## Foundation conversation map and migration bridge

| Chat | Durable contribution |
|---|---|
| 01 — Project Setup, Video Prep & RF-DETR Detection | Project goal, learning context, environment setup, first clip, RF-DETR detection, ByteTrack tracking. |
| 02 — Tracking, Team Classification & Player ReID | Tracking audit, court filtering, uniform features, team classification, OSNet embeddings, early ReID segmentation. |
| 03 — ReID Validation & Final Player Track Consolidation | ReID decisions, ten-player identity consolidation, visualization, calibration development, terminal camera-motion failure analysis. |
| 04 — Court Calibration, Player Coordinates & Trajectory Refinement | Stable court motion, coordinate export, visualization, audited trajectory correction/interpolation, Possession 001 baseline. |
| 05 — Pipeline Generalization & Multi-Possession Validation | Hardcoding audit, manifest/runner design, review gates, Possession 002 failures, explicit workflow rules. |
| 06 — Possession 003 Validation & Generalization Gate Completion | Possession 002 completion, Possession 003 full run, empirical gate pass, PR #5 closeout, README PR #6 post-export delta. |
| Desktop continuation — Ball annotation and detector precommit | Complete-ball-center protocol, three reviewed pilot sets, detection/evaluation contracts, nine prediction-blind evaluation windows, and the frozen RF-DETR baseline harness. |

## Ball-tracking session coverage, 2026-10-26

These sixteen numbered Ball Tracking chats are a different series from the six
foundation chats above. The current continuation is local thread
`01a17517-bef8-7813-bdaf-bc85772fd97e`, titled
`Ball Tracking 17 — NBA Training & Full-History Reassessment`. Include it and future continuations;
sixteen is not a permanent cutoff for historical consideration.

All sixteen IDs below were confirmed through local app thread reads on October
26. Their latest turns were retrieved with older history still available through
pagination. Titles are copied verbatim from the app; ellipses are part of the
stored titles. This inventory verifies access, not comprehensive transcript
review or independent revalidation of every historical result.

| Session | App title (verbatim) | Local thread ID |
|---|---|---|
| 01 | Ball Tracking 01 — Annotations, Detector Baseline & Pilot T… | `01a02bfa-34d0-7bc2-86fd-61a11cc9e768` |
| 02 | Ball Tracking 02 — Pilot Scoring, Visual Review & Tracker D… | `01a03216-d888-79b1-a144-c7bf41eb2671` |
| 03 | Ball Tracking 03 — Development Annotations, Detector Compar… | `01a0b7ec-3f48-7043-98db-ff51d9787a85` |
| 04 | Ball Tracking 04 — Crop Experiments, YOLO Recovery & Candid… | `01a0f529-e4fb-7c40-96e9-a9fbb5b96a83` |
| 05 | Ball Tracking 05 — Candidate Retention, Scoring & Render Re… | `01a0fd35-66a1-7472-90cc-3ea9f09fa1f7` |
| 06 | Ball Tracking 06 — Render Recovery, Audit & Visual Review | `01a0fec3-cc9d-7160-b305-8aa9ee7715f2` |
| 07 | Ball Tracking 07 — Monitor Redesign, Recovery Integration &… | `01a109d2-ba34-7e80-b043-f2e15b1c6068` |
| 08 | Ball Tracking 08 — Recovery, Candidate Review & Score Analy… | `01a10ef2-0554-7a81-a8b6-e957397e952b` |
| 09 | Ball Tracking 09 — Mean Confidence & Joint Error Review | `01a1139a-f3f8-7e10-9ac5-5f0ec7bfcd70` |
| 10 | Ball Tracking 10 — Cross-Detector Corroboration & Superviso… | `01a11927-7ea4-7211-a52f-94af1ecd21e1` |
| 11 | Ball Tracking 11 — WASB Adaptation, Expanded Training & Pos… | `01a11c26-bed0-7ec3-ade9-372c333fb0b9` |
| 12 | Ball Tracking 12 — Motion Selection & NBA Footage Access | `01a11e9f-5632-7ee0-b77d-8f7dbbb5fec3` |
| 13 | Ball Tracking 13 — NBA Footage Acquisition & Accepted Pilot… | `01a15184-8f71-7851-9b47-a6b05432143a` |
| 14 | Ball Tracking 14 — NBA Diagnostics & Accepted Gap Repair | `01a156c4-4647-7fd0-b600-1921249cd369` |
| 15 | Ball Tracking 15 — Verifier Results & Approved Completion P… | `01a15b1f-6768-78e2-93c2-8272c7829f75` |
| 16 | Ball Tracking 16 — Accepted References, Primary Training &… | `01a160f9-cf20-76d1-90cd-27416256d699` |

Use `read_thread` with the exact ID and host `local`, and its returned cursors
to retrieve older turns. `C:/Users/Ryan/.codex/session_index.jsonl` is a fallback
locator, not evidence that a scientific result occurred. A bounded recent-chat
listing can omit early sessions; omission there does not mean they are missing.

The foundation archive exists at
`C:/Users/Ryan/Documents/Codex/2026-08-18/he/outputs/player-defense-score-context-migration/`.
Its `manifests/conversations.csv`, six `transcripts/01-active-transcript.md`
through `06-active-transcript.md`, raw conversation objects and chat-06 delta
provide the older history. Keep these archives outside Git.

Before the next consequential scientific recommendation, reconcile the sixteen
session handoffs with this document's authority map and `validation_history.md`,
then open the relevant primary records. Record any missing or only-summary
coverage and whether it could change the recommendation. The existing authority
map is organized by experiment and is not yet a verified one-to-one mapping of
all findings to session numbers. Do not infer completion of that reconciliation
from this access inventory.

Current-session discussion also identified a distinction to preserve: older
lower-cutoff-only trials and motion selection restricted to candidates above
0.3 do not establish the outcome of combining weak responses with motion on
the current NBA models. Before designing that comparison, verify both histories
against `../ball_wasb_calibration_results.md`,
`../ball_wasb_expanded_adaptation_results.md`,
`../nba_candidate_preservation_experiment.md`,
`../nba_temporal_gap_selection_experiment.md`, and
`../nba_temporal_gap_continuous_validation_results.md`. The current model's
candidate-availability discussion is diagnostic evidence, not an executed new
selector or a phase pass. Keep the current spatial/continuation results above
and the original human-review outcomes as their actual authorities.

## Migration archive

The external migration package contains:

- six raw exported conversation objects plus the chat-06 live delta;
- six readable active-path transcripts;
- a manifest for 119 exported user attachments;
- a manifest for 38 historical `sandbox:/...` artifact links;
- proof that the browser Sources tab was empty;
- a SHA-256 manifest for all 856 files in the local ignored `data/` tree;
- generated-package checksums.

Original account-export ZIP SHA-256:

`BBB7BCC3E7F0C0B01229B8DE2C3522AA87259DD5456165050766F3B61B245C97`

The original ZIP remains the binary source of truth and should not be modified or discarded.

## Historical artifact rule

The transcripts contain 38 assistant-generated download links. They are evidence that an artifact once existed, not proof that it remains current or complete. Reconcile any needed artifact against current source files, Git commits, configs, local outputs, and hashes. Do not rebuild the repository by replaying old ZIP commands.
