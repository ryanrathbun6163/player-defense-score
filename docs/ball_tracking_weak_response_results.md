# NBA weak-response feasibility and candidate selection

## Decision and scope

The cosine-nine model contains useful weak ball responses. Both automatic weak
comparisons recover ten missing Houston positions, but neither selector passes.
A bounded correction improves the strong sequence from 764 to 821 correct HOU
positions; the native model still has 842/882. Narrow weak selection reaches
831, with 47 wrong positions and 27 certain-hidden emissions. DET remains
219/241 correct. Preserve the successful recoveries and corrected selection
errors without adopting either method or starting new training automatically.

This is the authorized continuation of the
[sixteen-session reassessment](research/ball_tracking_full_history_reassessment_2026-10-26.md)
and [prospective method](ball_tracking_weak_response_experiment.md). The completed
historical review was reused, with relevant primary reports and saved records
inspected; this session did not reread every original transcript. Earlier
selection, look-ahead, verifier, resolution, continuation and spatial results,
including successful increments and failures, remain evidence. This variation
adds observed weak components and local maxima, allows revising original choices,
and keeps an explicit missing state. It does not infer unobserved coordinates.

The saved cosine epoch-nine checkpoint remains the declared research control:
SHA-256 `f4b721662ec3d8b546563feffcf5ce0d6319ed8ddc83f398830a0aac5d29c7b9`.
HOU is repeatedly inspected development/checkpoint-validation data; DET is
excluded post-selection development, not fitting or checkpoint-selection data;
SAC is training-exposed. None supplies a fresh independent test. Existing labels,
source roles, all quality criteria and original human reviews are unchanged.
Nine source-uncertain recovery events remain independently inconclusive.
Protected evaluation stays closed; no new training or labeling occurred.

Each context still requires at least 95% correct automatic positions, at most
1% wrong positions, zero certain-hidden emissions, no eligible missing run over
200 ms, no confirmed wrong-object run of 120 ms or longer, and recovery within
120 ms followed by two more eligible correct positions. Native timing,
uncertainty, censoring and manual/inferred-as-absent rules remain unchanged.
The uncertain recoveries are HOU e03 returns 146/190 and DET returns
11047/11075/11098/11107/11476/11497/11557. They cannot become certified through
better numerical tracking alone.

All eight complete contexts were processed: 1,231 DET frames, six HOU episodes
totaling 960 frames, and 1,471 SAC frames. Outputs are ignored under
`data/outputs/ball_tracking/weak_response_v0_1/`. The original native selections
and scores reproduce their saved producer records exactly.

## What the saved responses can support

These are **reference-assisted availability ceilings**, not automatic accuracy.
Every extraction was saved before reference-distance diagnosis. A point counts
only if an actual extracted center is within the unchanged inclusive ten-source-
pixel tolerance; no reference point becomes a candidate.

| Context | Eligible | Native >.3 candidate ceiling | Expanded selection-pool ceiling |
|---|---:|---:|---:|
| DET | 241 | 219 | 240 |
| HOU, six episodes | 882 | 857 | 882 |
| SAC | 270 | 270 | 270 |

All nineteen DET gap frames have a matching observed weak candidate. At frame
11087 a local maximum is needed; threshold-component centers alone miss. At
11093 a threshold component succeeds where local maxima miss. Some late-gap
peaks are approximately .00026–.0007. This is evidence against treating the
entire gap as absent model response.

DET's raw extraction ceiling is actually 241/241. The fixed two-pixel duplicate
merge removes a local-maximum center at frame 11561 that is 9.585 pixels from the
reference in favor of a retained native center at 10.193 pixels. This is a pool
construction loss, preserved in the raw records, not evidence of no signal.

The expanded pool is extremely ambiguous: thousands of candidates per frame,
with maxima of 4,749 DET, 5,347 HOU and 5,529 SAC. Every certain-hidden HOU/SAC
frame also has weak candidates (34 and 17 frames respectively). All 69
source-uncertain hidden DET frames have them, versus two with native candidates.
The pool's large reference ceiling cannot distinguish a ball from clutter.

## First fixed automatic comparison

Each cell is **correct / wrong / missing; certain-hidden emissions**. HOU totals
are descriptive; acceptance remains per episode, including temporal gates and
human object/trajectory review. Native is the unchanged cosine-nine selection.

| Context | Native | Strong-candidate sequence | Expanded weak sequence |
|---|---|---|---|
| DET | 219 / 1 / 21; 0 | 219 / 1 / 21; 0 | 219 / 16 / 6; 0 |
| HOU e01 | 110 / 0 / 10; 0 | 110 / 0 / 10; 0 | 120 / 0 / 0; 0 |
| HOU e02 | 120 / 0 / 0; 0 | 119 / 0 / 1; 0 | 119 / 1 / 0; 0 |
| HOU e03 | 90 / 8 / 0; 0 | 67 / 29 / 2; 0 | 67 / 29 / 2; 0 |
| HOU e04 | 120 / 0 / 0; 0 | 116 / 0 / 4; 0 | 116 / 3 / 1; 0 |
| HOU e05 | 195 / 6 / 11; 1 | 180 / 15 / 17; 1 | 186 / 24 / 2; 13 |
| HOU e06 | 207 / 5 / 0; 18 | 172 / 40 / 0; 18 | 172 / 40 / 0; 18 |
| HOU total | 842 / 19 / 21; 19 | 764 / 84 / 34; 19 | 780 / 97 / 5; 31 |
| SAC | 270 / 0 / 0; 0 | 270 / 0 / 0; 0 | 270 / 0 / 0; 14 |

The ten e01 recoveries are a real automatic increment under this fixed rule.
In e05, the weak arm recovers eleven native-missing correct positions, including
six at frames 14–19 that need responses below .01, while losing other correct
positions. Preserve those gains even though the complete method fails. The
extra DET emissions do not improve its correct count. SAC's unchanged eligible
accuracy hides fourteen new certain-hidden
emissions, demonstrating why accuracy alone is insufficient.

All choices for both arms and all eight contexts were sealed before scoring.
The selector sees only candidate geometry, original response mass, candidate
identity/bounds and native timestamps. Reference geometry, eligibility and
visibility never enter the chooser. Weak support uses strong model hypotheses
on both sides within .4 seconds; those need not be the final chosen anchors.
This permissive geometric support does not establish object identity. DET
source-uncertain hidden emissions rise from two to 49; their uncertain status
is retained, not converted into either certain errors or correct detections.

The strong-only sequence loses 78 native-correct HOU positions. Seventeen touch
a correct-to-correct edge above its 1.5-source-widths/second hard limit; the
largest observed correct HOU speed is 2.1435. In e03/e06, 58 losses occur despite
no such correct-edge violations. Wrong selected components retain substantial
mass, and the motion objective can prefer a stable head to the moving ball.
Still-image inspection confirms spectator-head selections in e03 frames
124/147 and e06 frames 224/251/273; e03 frame 183 instead abstains on a partially
visible ball. These AI still judgments do not certify continuous wrong-object
duration or human trajectory acceptance.

DET has no strong candidates from 11064 through 11097. The original .4-second
two-sided support horizon excludes part of the long gap even though matching
weak centers exist. This is a limitation of this declared gate; it is not a
failure of weak-response feasibility. The follow-up does not tune that horizon
using DET.

## Bounded follow-up and its development basis

HOU diagnosis justified one CPU follow-up, with four arms and all other settings
unchanged: motion cost .025 instead of .25; speed limit 3.0 instead of 1.5;
both corrections; and both corrections with a narrowed weak pool. The original
strong sequence is the already-completed factorial control. The combined strong
arm was declared the main research arm before seeing follow-up outcomes.

The narrowed pool retains exact native candidates plus actual >.01 components,
with the original two-pixel duplicate rule, no local maxima and no candidate cap.
This is an explicitly **HOU label-assisted development choice**, not independent
validation. It preserves all ten demonstrated e01 opportunities; >.03 would
miss frames 200–201. The twelve newly emitted certain-hidden e05 selections from
the first weak run all have peaks below .01, so these exact choices disappear;
alternate false choices can still occur. Six correct e05 recoveries at frames
14–19 also require responses below .01 and are knowingly unavailable here.

An earlier .03 preparation draft used the highest grid threshold whose native
union ceiling reached 95% in every HOU episode. That draft was revised before
the full-study freeze, extraction or comparison, and retained as preparation
history. A failed fixture-order comparison is retained separately. Four
preparation-test executions also exercised the fixed combined strong rule and
scorer on real HOU e01 for record transport; saved-map extraction probes also
preceded the freeze. Their assertions concerned census, human-review state and
tamper rejection, and did not report numerical outcomes
or use them for tuning. These probes must not be described as zero selection
invocations. The freeze precedes the full four-arm study, whose complete choices
precede comparison scoring. DET receives the locked method unchanged.

The complete follow-up took 22.723 CPU seconds. All 32 context/arm choice series
were saved before comparison scoring; all 3,662 mean hashes and original native
candidates reproduce exactly. There were 3,772 native components and 25,606 raw
>.01 components, yielding 26,371 retained pool entries across the full study.
This substantially reduces clutter, but does not establish candidate identity.

Each cell remains **correct / wrong / missing; certain-hidden emissions**.

| Context | Motion cost only | Speed limit only | Both, strong | Both, narrow weak |
|---|---|---|---|---|
| DET | 219 / 1 / 21; 0 | 219 / 1 / 21; 0 | 219 / 1 / 21; 0 | 219 / 9 / 13; 0 |
| HOU e01 | 110 / 0 / 10; 0 | 110 / 0 / 10; 0 | 110 / 0 / 10; 0 | 120 / 0 / 0; 0 |
| HOU e02 | 119 / 0 / 1; 0 | 119 / 0 / 1; 0 | 120 / 0 / 0; 0 | 120 / 0 / 0; 0 |
| HOU e03 | 77 / 19 / 2; 0 | 67 / 29 / 2; 0 | 77 / 19 / 2; 0 | 77 / 19 / 2; 0 |
| HOU e04 | 116 / 0 / 4; 0 | 120 / 0 / 0; 0 | 120 / 0 / 0; 0 | 120 / 0 / 0; 0 |
| HOU e05 | 180 / 15 / 17; 1 | 182 / 13 / 17; 1 | 200 / 0 / 12; 1 | 200 / 11 / 1; 9 |
| HOU e06 | 194 / 17 / 1; 18 | 172 / 40 / 0; 18 | 194 / 17 / 1; 18 | 194 / 17 / 1; 18 |
| HOU total | 796 / 51 / 35; 19 | 770 / 82 / 30; 19 | 821 / 36 / 25; 19 | 831 / 47 / 4; 27 |
| SAC | 270 / 0 / 0; 0 | 270 / 0 / 0; 0 | 270 / 0 / 0; 0 | 270 / 0 / 0; 8 |

The factorial comparison supports both diagnoses. Speed correction restores e04;
e02 requires both changes; reducing the motion cost helps e03/e06. The combined
strong rule gains six native-incorrect positions (five e05 and one e06), but
loses 27 native-correct positions, all in e03/e06. This is a useful repair of
the first chooser and a failed replacement for the native control. Compared
with the first strong sequence, it gains 57 correct HOU positions without losing
any that first sequence had correct.

The narrow weak arm preserves all ten e01 gains at frames 194–203. In e05 it
adds two correct positions versus corrected strong while losing two others,
leaving the same correct total, eleven new wrong emissions and eight new
certain-hidden emissions. SAC retains all eligible correct points while adding
eight hidden-ball emissions. DET adds eight wrong positions and raises
source-uncertain hidden emissions from two to 46 without any correct gain.
Filling a missing interval with wrong or uncertain points is not successful
recovery. The corrected strong DET gap is still nineteen frames / 317 ms; the
narrow weak arm still has a thirteen-frame / 217 ms eligible missing run. Both
fail the 200 ms limit. The nine original source-uncertain recoveries remain
inconclusive; narrow weak additionally makes an e05 recovery inconclusive, while
corrected strong fails recovery events in e05/e06. No arm passes the unchanged
complete criteria.

## Next decision

Retain cosine nine and both failed selector recipes as research evidence. The
useful increments justify continuing candidate work. The next bounded question
is whether candidate-specific ball identity and visibility evidence can preserve
those gains while choosing absence during occlusion and avoiding replacement of
correct points. It needs a concrete prospective design before execution; this
report neither specifies a passing method nor authorizes new training.

Another motion/threshold sweep or a longer DET-tuned anchor horizon is not the
supported next step. A saved-output HOU diagnosis checks the stricter geometric
condition of support from the **already selected** strong endpoints: all ten
correct e01 weak choices, both correct e05 weak choices, all eleven wrong e05
weak choices and six of eight new e05 hidden emissions still satisfy it. This
is a label-assisted support diagnosis, not a new chooser run. Endpoint support
alone does not separate these objects or establish visibility.

Prior evidence matters to that design. The
[candidate-preservation experiment](nba_candidate_preservation_experiment.md)
recovered candidates for nine of 45 unavailable target positions. The
[look-ahead work](nba_temporal_gap_selection_experiment.md) and
[later reference evaluation](nba_gap_anchor_reference_evaluation_results.md)
retained three accepted additions and eight later geometric gains, with six
AI-supported identities and two ambiguous cases, alongside the SAC
1419–1421 spectator-head counterexample. Those frozen results remain intact.
The [DINO appearance veto](nba_ball_distractor_training_results.md) discarded
207/581 previously correct points; repeating that generic hard filter is not
justified by the current failure. This is adverse evidence about that recipe,
not a rejection of all appearance or identity evidence.

A result that would change the recommendation is a prospectively fixed score
using permitted development inputs that retains the demonstrated correct
increments, avoids native-correct regressions and removes certain-hidden
emissions under the same complete per-context gates. Any new fitting proposal
must explain the discriminating information it is expected to learn and its
data/cost boundaries. Merely extending the failed selector or unchanged spatial
training recipe would not answer that question. Human trajectory review and
the nine uncertain-source recoveries remain separate obligations.

## Execution, failures and verification

The initial CPU inventory verified source caches, accepted records and all
2,702 existing DET/SAC mean maps. HOU means were absent, so one supervised GPU
capture performed 948 triplet forwards to reconstruct 960 means. Every original
mean hash and native observation reproduced exactly. The workload took 53.593
supervised seconds, peaked at 57 C / 104.19 W / 2,684 MiB, exited zero and left
no owned process. Graphics extras were absent before execution, and the post-run
system check found no matching new errors. No settings changed; this does not
establish that the earlier graphics-reset problem is cured. All extraction,
selection, diagnosis, audits and rendering then use CPU and saved outputs.

The first saved-map extraction failed only at an undersized 5 GB output guard,
after 352.935 seconds. The failure and partial files remain. A recovery with a
practical 30 GB allowance reused 1,334 complete emitted frame pairs, including
all DET frames, and finished the remainder in 634.984 seconds. One pool-only SAC
frame had no matching raw record and was recomputed, with the original retained.
HOU extraction took 409.900 seconds. Scientific parameters were unchanged.

The initial sequence comparison completed in 442.180 CPU seconds. Exact sparse
neighbor enumeration replaced a dense implementation before choices were made;
it changes neither candidates nor the objective. An independent exhaustive
synthetic oracle checks the optimum, path margins, stable ties and inclusive
speed boundaries. Complete pool files remain bound to compact choice records;
no candidate cap or duplicated multi-gigabyte pool is hidden in transport.

The independent capture audit passes 11,544 checks. The independent first-
comparison audit passes 96,340 checks, including emitted coordinates, pool
membership, native timing, ten-pixel categories, hidden emissions, missing runs,
gains/losses and source/freeze integrity. Recovery-kernel contracts are verified,
not claimed as an independent reimplementation. Forty distinct focused checks
cover extraction, capture, sequence/oracle, actual producer/consumer transport,
native-score parity and a real encoded/decoded native-timing video fixture.
The full repository suite was not rerun for these additive modules.

The follow-up adds seven focused checks and four render-transport checks,
bringing the total to 51 distinct focused tests across component runs. Its
independent audit passes 388,845 checks, including direct coordinate outcomes,
candidate membership, gain/loss/hidden sets, native missing intervals and chosen
path costs/support. Full report equality explicitly reuses the frozen scoring
kernel. Study choice-before-score ordering is supported by the frozen code and
file evidence, with the preparation-probe limitation above. One audit-helper
import error occurred before reading inputs; the failed helper and receipt are
preserved rather than relabeled as a scientific failure or successful audit.

A post-study static review found three tests that assumed ignored local records
were present. After all rendering finished, a test-only portability correction
added explicit missing-data skips. The original preparation and render-test files
were preserved byte-for-byte in `post_study_test_portability_v0_1/original/`.
The current eleven focused cases have ten passes and one explicit historical-
preflight skip; simulated absent outputs also pass, with eight executed tests
and four skips including the unavailable-data class. This does not claim that
earlier test runs covered the edit. Scientific source, recipes and choices are
unchanged. Historical freezes still name the original test path/hash; the
portability receipt binds its exact archived copy and the new active version.

Complete native-timing paired videos preserve every source frame, its original
presentation interval and the actual final frame without an artificial end hold.
Independent decoding checks binary frame keys, timing and image agreement.
AI still inspection and those checks remain separate from Ryan's pending complete
trajectory/object review. The nine source-uncertain recoveries remain unresolved
independently of selector or training outcomes.

All four review sets complete without failures or reused blocks: first strong
698.83 seconds, first weak 865.04 seconds, corrected strong 421.18 seconds and
corrected narrow weak 420.95 seconds. Each contains all eight contexts / 3,662
decoded native frames. First-run workers peaked around 2.84 GB; narrower-pool
follow-up workers stayed far smaller. No CUDA or NVIDIA encode modules were
loaded in the observed CPU render workers. The original failed selectors' review
sets remain alongside the corrected comparison.

The twelve follow-up stills independently inspected by AI include the recovered
held ball in e01, two corrected e05 native mistakes, remaining spectator-head
choices in e03/e06, an e03 abstention on a partially visible ball, and e05 weak
points on another player or during certain occlusion. These observations preserve
the accepted references and their certainty, without asserting full-trajectory
human acceptance.

For human review, open the corrected
[strong index](../data/outputs/ball_tracking/weak_response_v0_1/followup_v0_1/review_motion_and_speed_v0_1/index.html)
and [narrow weak index](../data/outputs/ball_tracking/weak_response_v0_1/followup_v0_1/review_motion_and_speed_narrow_weak_v0_1/index.html).
Each pairs native cosine nine with the named research arm and links the exact
full-context video, final frame and receipt. Start with e01 194–203 (gains),
e03 124–147 and e06 224–237 (remaining native regressions), e05 184–187/205
(corrected selections), e05 4–27 and SAC 986–993 (weak hidden emissions), and
DET's full gap context. Sparse examples guide review; all eight full trajectories
remain the required scope for acceptance.

## Artifact map

All paths below are relative to the ignored output root stated above.

- `inventory.json`, `capture_v0_1/completed.json`,
  `monitoring/capture_attempt_001/`, `independent_capture_audit.json`.
- `feasibility_saved_v0_1/` (failed attempt),
  `feasibility_saved_recovery_v0_2/`, `feasibility_hou_v0_1/`:
  complete pools/raw extraction, reference-assisted diagnostics and union ceilings.
- `prospective_freeze_v0_2.json`, `comparison_v0_1/completed.json`,
  `independent_comparison_audit.json`: first fixed comparison and audit.
- `diagnostics/hou_v1_losses.json`, `hou_v1_reference_run_objectives.json`,
  `hou_v1_weak_selected_sources.json`: HOU-only follow-up evidence.
- `ai_review_v0_1/`: selected native/candidate stills and explicit AI observations.
- `review_sequence_strong_v0_1/`, `review_sequence_weak_v0_1/`: first-comparison
  full-context reviews and actual final images.
- `followup_v0_1/`: prospectively frozen bounded correction, all four choices
  and complete per-context scores.
- `followup_v0_1/prospective_freeze_clarification.json`,
  `preparation_history/threshold_003_draft/`: exact preparation history.
- `diagnostics/followup_independent_audit.json`,
  `diagnostics/followup_anchor_diagnostic.json`: independent verification and
  reference-assisted endpoint-support diagnosis, with no additional chooser run.
- `ai_review_followup_v0_1/`: twelve inspected gain/loss/hidden-emission stills.
- `followup_v0_1/review_motion_and_speed_v0_1/` and
  `followup_v0_1/review_motion_and_speed_narrow_weak_v0_1/`: complete corrected
  full-context review sets, using the prospectively declared actual arm names.
- `post_study_test_portability_v0_1/`: original test copies, new bindings and
  separately recorded post-edit verification.
- `documentation_update_v0_1/`: proof that additive context updates preserve
  the original handoff documentation bytes.

No staging, commit, push, PR or merge was performed. The branch remains
`codex/ball-detector-baseline` at
`8c040fca385dd8fffa0d7a13c45c53e79950bae1`, with an empty index. The six
intentional handoff documentation changes were preserved, not reset to an older
checkpoint or clean checkout.
