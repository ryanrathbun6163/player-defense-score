# Completion campaign: first development package and references

The approved campaign began from clean `codex/ball-detector-baseline` at
`b1dbf027ee140a15b03509a1dfa0ba88e367a6c3`. The exact approved plan blob,
retained checkpoint and rejected-verifier result matched the handoff hashes.
The [existing approval](../configs/ball_tracking/reviews/ball_tracking_completion_campaign_approval_v0_1.json)
was applied without another campaign approval request.

The [delivery index](../data/outputs/ball_tracking/completion_campaign_v0_1/index.html)
links the three packages. The [integration result](../configs/ball_tracking/reviews/ball_completion_first_increment_result_v0_1.json)
binds their exact files and validation evidence.

## Retained baseline is usable now

The [indexed development package](../data/outputs/ball_tracking/completion_campaign_v0_1/baseline/index.html)
reuses the three exact previously reviewed synchronized player/ball videos and
exports every timeline frame with source/model provenance, native presentation
time, player identity context, heatmap component mass and explicit missingness.
Component mass is not a calibrated probability. Ball centers remain in source
image coordinates; no court homography is applied to the airborne ball.

| Possession | Observed | Missing | Protected | Longest output gap |
| --- | ---: | ---: | ---: | ---: |
| P001 | 324 | 100 | 75 | 0.60 s |
| P002 | 308 | 116 | 75 | 0.68 s |
| P003 | 347 | 78 | 75 | 0.64 s |
| Total | 979 | 294 | 225 | — |

These are availability counts across 1,273 permitted frames, not localization
accuracy. Gap durations do not assert continuous reference visibility and
therefore do not decide the new continuity gate. The separate historical
longer-context development result remains 131/145 matches, one geometric error,
13 missing eligible frames and zero alarms on five hidden frames. It is not
accuracy over the complete permitted census.

All 1,498 serialized records retain the original producer fields. Fresh video
verification decoded all 1,498 review frames, checked 225 blacked-out source
areas and reached all actual finals. Native timestamp origins are preserved:
P001 and P002 start at 0.04 s; P003 starts at zero. Clip-relative playback time
is separate, and old accepted annotation timestamps are unchanged.

Ryan's completed review of these exact videos remains complete. Their original
headers retain the historical pending status; the package binds the later review
record. This does not accept the ball phase or every point. The separately
accepted three-point gap increment remains linked and unapplied to this retained
baseline; the broader fourteen-fill rule is not adopted.

## Reference coverage before this batch

An independent inventory joins the twelve reviewed curated annotation sets and
twenty additional accepted gap/anchor judgments by possession and source frame.
Appearance classes and duplicate controls are not counted as new center labels.

| Possession | Accepted permitted frames | Of these eligible | Still uncovered |
| --- | ---: | ---: | ---: |
| P001 | 131 | 130 | 293 |
| P002 | 100 | 81 | 324 |
| P003 | 89 | 82 | 336 |
| Total | 320 | 293 | 953 |

The accepted records comprise 150 historical training frames, 150 development
frames available for checkpoint selection, and twenty later post-selection
references. The historical P003 training block at 416–440 is retained. New
curated reference coverage is evaluation-only; it does not expand fitting.
Unknown and ambiguous accepted judgments remain unchanged.

The first batch covers 120 new, consecutive P003 frames, 0–119, selected as the
earliest uncovered permitted interval before source inspection. Ryan reviewed
the complete overlay and explicitly answered **“Accept all 120 proposals.”**
The [later acceptance record](../configs/ball_tracking/reviews/ball_completion_reference_batch_01_acceptance_v0_1.json)
records that event; a separate accepted publication preserves every proposed
judgment and AI authorship. The [accepted reference](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_01/accepted/reference.json)
contains those exact records. Accepted coverage is now **440/1,273**, leaving
**833** permitted frames uncovered. This is a held-ball sequence with changing hand overlap,
not a representative sample of all ball motions.

The [complete label review](../data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_01/review_v2/index.html)
contains native 4.8-second and slow 24-second overlays, every proposed frame,
magnified current-frame crops, uncertainty rings, exception notes and actual
finals. All 120 proposals are partially visible complete-ball estimates with
7–9-source-pixel uncertainty; zero centers were marked unknown. The original
pending-era headers and proposals remain unchanged. The later acceptance applies
to the assisted references, including their stated uncertainty; it does not
accept model trajectories or protected evaluation. No repeat review is needed.

All 120 source frames were visually inspected before proposal delivery. The
initial placement draft and corrected draft are preserved, including 81 manual
placement revisions. A complete overlay pass corrected crop-boundary placement
errors; a separate source-first AI
spot check covered frames 19, 20, 59, 60, 69, 70 and 119. All revised points
were within their stated nine-pixel uncertainty of that reader's estimates.
Remaining reader differences at 59, 60, 70 and 119 are review cues, not a forced
consensus or independent ground truth. An independent sequential decode of
source frames 0–119 found every saved native PNG pixel-identical. It stopped
after 119 without decoding a protected frame.

## Fixed NBA source roles

The [source/episode manifest](../configs/ball_tracking/completion_campaign/source_roles_v0_1.json)
fixes four games and 24 distinct-play windows before new model predictions.
Each game contributes four half-open two-second windows and two four-second
recovery windows, with exact native presentation timestamps and frame lists.

| Role | Parent game | New episode duration |
| --- | --- | ---: |
| Training | Existing Sacramento–Memphis | 16 s |
| Training | Chicago–Indiana, BARD `0022400868` | 16 s |
| Training | Denver–Boston, BARD `0022400866` | 16 s |
| Checkpoint-selection validation | Houston–Oklahoma City, BARD `0022400879` | 16 s |

Eighteen individual BARD clips were acquired and fully decoded at native
1280×720, 60 fps, totaling 129,196,031 bytes. Selected SAC windows reuse its
existing source. The half-open windows contain 3,839 new reference slots:
959 SAC and 960 from each BARD game, within the approved 3,840 ceiling. These
NBA slots are not yet labeled. The
[source-only episode index](../data/outputs/ball_tracking/completion_campaign_v0_1/source_selection/index.html)
provides short navigation previews; future labels use original source pixels.
Source-only
inspection covers ordinary movement, held balls, passes/shots, overlap and
reappearance. Exact occlusion-frame eligibility remains a later label decision.
A screened SAC replay/timeout interval was excluded in favor of a live play;
screening evidence remains preserved.

Whole NBA parent games, replays and alternate encodes retain one role. DET
remains excluded from fitting and checkpoint selection; development-visible
TOR is not substituted for fresh validation. Houston–Oklahoma City is fresh
relative to this project's local work; overlap with upstream pretraining is
not established. Existing 300 accepted SAC and 150 NFHS training rows remain
separate, deduplicated authorities. New NBA labels and triplets are not yet
prepared or accepted by source selection alone.

## Verification and repeatability

Four focused baseline tests and five reference-delivery tests pass. Critical
baseline fixtures come from the existing observation producer, and actual saved
producer records were independently compared with every emitted frame record.
All 240 encoded label-review frames and their marker regions were checked;
the existing annotation parser validated all 120 proposals. Source identity,
native timestamps, role isolation and existing-reference preservation are
checked against actual records rather than a mirrored fixture.
The final integration audit checked 316 file hashes, all 3,839 selected source
timestamps, and unchanged accepted annotations/native frame records. The
[current coverage inventory](../data/outputs/ball_tracking/completion_campaign_v0_1/accepted_reference_inventory_after_batch_01.json)
records 216 remaining P003 frames and 833 across all three possessions. Future
batch selection must include the newly accepted authority in its duplicate
guards; the first-batch validator retains the original pre-batch inventory.

The baseline command can be repeated without inference or rewriting existing
outputs:

```powershell
& .\.venv\Scripts\python.exe -B -m src.ball_tracking.completion_baseline --config configs/ball_tracking/completion_campaign/baseline_v0_1.json
```

The reference renderer also has a validation-only command, with no output
directory argument and no label acceptance:

```powershell
& .\.venv\Scripts\python.exe -B -m src.ball_tracking.completion_references --config configs/ball_tracking/completion_campaign/reference_batch_01_v0_1.json --proposal data/outputs/ball_tracking/completion_campaign_v0_1/reference_batch_01/proposal_revised.json
```

The first reference delivery encoded its native video, then failed to bind a
relative path. That attempt remains in `review_v1/failure.json`; the path fix
has a regression check and the complete delivery is separate in `review_v2`.
A pre-execution baseline test import indentation error was corrected before
package generation. Neither correction consumed a fit or changed a scientific
result. The full test suite was not repeated for this bounded delivery work.
Metadata publication initially failed on a helper import path and was corrected
before writing accepted records. The integration helper first used the wrong
container for native frame records; a later draft inventory retained an outdated
duplicate P003 count. Corrected checks derive and verify that count from its
frame list. These helper attempts and intermediate records remain preserved;
the final audit passes without changing any label or scientific result.

## Execution boundaries

No inference, fitting, threshold search, player-pipeline rerun or protected
source-pixel inspection is part of this increment. The DINO verifier remains
rejected. This first batch is accepted; future new labels still require Ryan's
acceptance, and fitting follows the complete accepted package and frozen executable recipe.
Final trajectories still need human review. All 225 protected positions remain
closed pending a frozen method and separate explicit authorization.

The remaining campaign follows the [approved completion plan](ball_tracking_completion_plan.md):
finish and accept the reference package, run the fixed primary fit and selection,
consider the single conditional resolution fallback only under its declared
trigger, then freeze before separately authorized protected evaluation.
