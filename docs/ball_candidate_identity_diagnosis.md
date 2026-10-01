# Candidate identity: appearance and crop evidence

Ryan completed the 12-clip motion-factorial review. This follow-up inspects
saved evidence to specify the next comparison. It does not rerun an experiment,
change labels, or choose a tracker, operating point, or quality gate.

The checkpoint is `codex/ball-detector-baseline` at
`2274ab6097cd841421e2b606f723b047cd7dc62b`. The earlier reviewed results and
receipt remain unchanged in `ball_crop_motion_factorial_results.md` and
`configs/ball_tracking/reviews/rfdetr_medium_crop_motion_factorial_visual_review_record_v0_1.json`.

## What was inspected

The saved motion audit has 4,843 emitted winners across correlated settings.
These reduce to 215 distinct source-frame/global-candidate pairs: 125 matched,
85 unmatched on localization-eligible frames, and five hidden false alarms.
They are already selected candidates, not a sample of all detector proposals
or independent trials. An unselected useful alternative can be absent from
this catalog, including the correct P002 representative frame 262 candidate.

The ignored catalog under
`data/outputs/ball_tracking/candidate_identity_diagnosis/2274ab6097cd/`
contains 430 exact native pixel crops from 149 existing unmarked review PNGs
and 12 labeled contact sheets. All 430 crop pixels were checked against their
source rectangles. The agent inspected all 12 sheets; this is an agent
diagnostic, not an additional human review or new semantic annotation set.
The catalog SHA-256 is
`20803ef757b63ffb9126da363b59a8f59d12c3fb3bdd34d5e357be844413f6b4`.
The separate `agent_appearance_inspection.json` binds the inspected sheets.

**The sheet labels MATCH, WRONG and HIDDEN FP are saved radius-10 scoring
outcomes. WRONG does not certify that the depicted object is not a ball.**
For example, P001 representative 51-53, P002 representative 257 and P003
challenge 164 include crops that appear to cover part of the ball or its
hand/ball boundary despite failing that localization comparison. These visual
descriptions preserve uncertainty; they do not overwrite finalized labels.

## Recurring visual patterns

| Evidence | Agent observation | Implication |
| --- | --- | --- |
| P001/P002 representative repeated unmatched proposals; P002 262#2 | Small bright yellow-green/orange spots against blue bleacher rows, far from observed players | Continuity can accumulate strong support for persistent background clutter. |
| P002 challenge late unmatched proposals, including 48#1 | Bright spots in the distant seating/background region | Context may distinguish these from the same-frame ball near a player. |
| P003 representative early unmatched proposals | Several crops center on raised hands/fingers or nearby arm regions | Proximity to a player alone cannot establish ball identity. |
| P003 hidden 167#0 and 168#0 | Skin-colored knee/leg region beside dark/yellow shorts | Both proposals are already inside player rectangles; the proposed context term is zero there. |
| P003 challenge 170#0, 171#7, 172#10, 173#12 | White shoe region near the floor | Appearance confusion also occurs inside player context. |
| P001 challenge 200-201 | A genuine ball separated from observed player boxes during flight | A hard proximity cutoff would risk removing valid passes. |

These are illustrative descriptions of inspected pixels, not certified object
categories or new category-level metrics. Color, size and silhouette vary with
occlusion, camera scale and lighting. No appearance feature or learned model
was fitted or evaluated.

## Why another crop is not sufficient confirmation

The read-only `crop_evidence.json` (SHA-256
`64d9818668e6ebb4e20e76138f20316eaa78cc716bc3d1529c95a4717be891b4`)
checks saved crop provenance and geometry. Of 125 matched candidates, 93 have
centers covered by only their own crop. A second crop cannot confirm those
centers. Missing second-view evidence is therefore often unavailable evidence.

False proposals also repeat across crops. Hidden P003 168#0 has another-view
candidate only 1.110 pixels away with box intersection-over-union .819935.
The useful reacquisition at 171#0 has excellent geometric agreement with its
other-view candidate, but that candidate's confidence .166817 falls below both
predeclared display thresholds. Shared model and source pixels also make these
views correlated, so adding their confidence as independent evidence is unsound.

Duplicate clustering could improve how alternatives and margins are presented.
It would not by itself remove a sustained wrong path: each existing path
already uses at most one candidate per frame. No clustering is performed here.

## Smallest useful next comparison

The prior context audit joined exactly 1,353 observed player-box rows across
the 150 permitted frames. At least one box exists on every frame; coverage is
incomplete, falling to six in P002 challenge. Reviewed identities do not make
the detector rectangles manually certified silhouettes. Legacy player outputs
lack historical source-video hashes and model provenance; current byte hashes
and aligned metadata do not repair that historical gap.

The remote-clutter cases justify testing a single soft distance penalty in
the path score, alongside each unchanged motion setting. The rule should
allow passes, preserve missingness and penalize distant context gradually.
It should neither alter original detector confidence nor invent a ball or
ball-handler identity. The fixed proposal is in
`ball_crop_player_context_proposal.md`.

The hypothesis is deliberately narrow. Of 85 unmatched eligible candidates,
28 are inside a player box, as are three of five hidden false candidates.
Their context penalty would be zero. Appearance evidence remains a separate
future question. These repeatedly inspected development windows cannot
establish generalization; all nine original prediction embargoes and all
three sealed holdouts remain preserved.
