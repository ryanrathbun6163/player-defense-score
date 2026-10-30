# Fresh-game diagnostic completed

October 30, 2026. The frozen detector and saved Q/J scorers completed once on
all three accepted BKN–DET windows. **No model was fitted or adopted.** True Color
remained running; the supervised run completed cleanly. The earlier statement
that it had to be closed was an inherited troubleshooting condition, not a
scientific requirement of this experiment.

## Main finding

The original detector choice was correct on **298/310 eligible frames (96.13%)**.
J retained all 298 while removing two of six wrong eligible choices. Four wrong
choices and two emissions while the ball was certainly hidden remained. This
is encouraging performance on these three short windows, **not achievement of
the project-wide 95% goal** or a reason to adopt a new tracker.

Selecting the highest Q score was not consistently better: it produced only
294 correct choices before rejection. Q sometimes preferred a spectator's head
over the correct ball already selected by the detector. J improved rejection
of those choices but could not repair an identity already fixed by Q-top.

## Fixed sample and complete comparisons

Ryan's explicit acceptance is recorded separately from the preserved original
AI proposals. The 360 native frames comprise **310 eligible centers, 32 certain
hidden, and 18 unknown**. Unknown frames are not errors. The sample is the first
two seconds of each source-first clip 122/237/365 from game 0022400861, not random
possessions, independent games or representative full-broadcast footage. The
whole game remains diagnostic development, ineligible for fitting or checkpoint
selection. Upstream pretraining's complete game inventory remains unknown.

Within each choice policy, its before/Q/J views use identical candidate identities
and the original source-pixel match distance <=10; Q/J acceptance is strictly score >0. There is no threshold
search, new selector, J-argmax choice, fallback or temporal fill.

| Fixed choice / acceptance | Correct / 310 | Wrong eligible | Hidden emissions / 32 | Unknown emissions / 18 |
|---|---:|---:|---:|---:|
| Native / none | 298 | 6 | 2 | 3 |
| Native / Q | 289 | 1 | 1 | 0 |
| Native / J | 298 | 4 | 2 | 3 |
| Original Q-top / none | 294 | 16 | 32 | 18 |
| Original Q-top / Q | 290 | 10 | 2 | 2 |
| Original Q-top / J | 293 | 2 | 2 | 4 |

There were 51 missing native choices across the full population: six eligible,
30 certain-hidden and 15 unknown. Every full candidate pool was nonempty; Q-top
therefore emitted something in every raw frame, including hidden/unknown frames.
The report retains those slots and all abstentions rather than changing the
denominator. All 3,480 candidates were in bounds.

## Which stage failed

**Candidate availability:** a matching candidate existed in 305/310 eligible
frames (98.39%). Five had none: clip 122 frames 8,9,18,19 and clip 237 frame 51.
An acceptance change cannot recover an absent proposal. Frame 237/51 is a
near-boundary geometric miss at 10.746 source pixels; it remains a miss under
the frozen rule, with accepted placement uncertainty retained.

Native-origin candidates supported 299 frames; weak candidates supported 36.
These overlap. Six frames had weak-only matching support; seven native-failure
frames had a matching weak candidate. These are opportunity counts, not a
realized recovery or a trained method. Among all matching candidates, at least
one survived Q in 291 frames and J in 303.

The seventh frame,237/47, has two unchosen matching native components as well as
one matching weak component. Its failure therefore also involves choosing among
native proposals; seven weak-supported failures must not be called weak-only.

**Choice:** native had 12 eligible failures: five without any matching proposal
and seven with matching support available. Q-top had 16 eligible failures: five
without matching support and 11 with it. Its fixed-choice ceiling here is
294/310 (94.84%), so filtering that choice alone cannot reach 95% on this sample.
This is consistent with the earlier saved Q-top ceiling of 2542/2811, rather
than new evidence that another rejection threshold will solve selection.
Raw Q-top gains four correct frame identities relative to native (122/7 and
237/42–44) but loses eight (122/52–54,56–58,71 and 365/41). The net loss of four
does not erase the distinct recovery opportunities or displaced successes.

**Acceptance:** Q rejected nine correct native points, whereas J rejected none.
On Q-top, Q rejected four correct points and J rejected one. J versus Q adds
nine correct native outputs with no correct losses, but accepts three additional
wrong points and one additional hidden output. On Q-top, J adds three correct
outputs with no correct losses and rejects eight additional wrong points. Both
have two hidden emissions, but their identities differ: one gain and one loss
cancel. Net counts must not hide these paired changes.

| Clip | Eligible / hidden / unknown | Native correct / wrong | Native+J correct / wrong | Q-top+J correct / wrong |
|---|---|---|---|---|
|122|84 / 22 / 14|79 / 0|79 / 0|73 / 1|
|237|106 / 10 / 4|99 / 6|99 / 4|101 / 1|
|365|120 / 0 / 0|120 / 0|120 / 0|119 / 0|

The failures cluster in short parts of clips 122 and 237. These are not dozens
of independent failure scenes. Clip 365 supplies an important success control:
the original detector is correct throughout, but Q-top introduces one error.
No temporal recovery metric was measured, and no event beyond the fixed windows
was acquired to fill a quota or establish recovery.

## Actual source and model-input review

[The complete diagnostic viewer](../data/outputs/ball_tracking/fresh_game_diagnostic_v0_1/diagnostic_review/index.html)
contains all 360 frames with the accepted reference, both fixed choices and exact
Q image inputs. All 974 displayed input tensors match the saved crop-preprocessing
path exactly. The matching-option panel uses the accepted reference solely to
illustrate availability; it is not a new prediction.

Root inspected 10 representative rendered frames, spanning all three clips,
failures and successful controls. These support specific observations:

- 122/52: the correct, blurred ball is present in the native crop; Q rejects it
  and instead prefers a spectator's head. J keeps both on this frame. Nearby
  raw Q-top losses also occur at 53–54,56–58 and 71.
- 365/41: even a clear ball in a successful native detection loses Q ranking to
  a spectator above the court. J rejects the wrong Q-top choice; it does not
  substitute the available correct ball.
- 237/44: the native choice lands on hands away from the accepted ball. The
  matching Q-top crop shows the partially obscured ball at the receiver's torso,
  but J rejects that correct alternative and retains the wrong native choice.
- 122/92: both fixed choices emit on an occluded-ball frame near the carrier and
  foreground referee. The apparent local shape does not establish visible ball
  identity. The accepted hidden reference is unchanged.
- 122/7 and 237/42: a matching weak candidate exists despite a missing native
  choice; Q rejects it and J accepts it.237/40 supplies a nearby correct partial
  ball rejected by Q but preserved by J.365/119 is a preserved correct control.

These observations do not prove that a bigger crop, temporal model or additional
hard-example fit is the cure. The prior full-history reassessment documented
greedy motion losses, smooth tracks following heads, and crop-verifier rejection
of correct points. The producer-transfer treatment also failed retention in
all three held NBA games. Those results and the original Q/J controls stand.

The next design should explain a concrete distinction between the real ball
and the observed head/hand distractors, while protecting existing native
successes and testing weak alternatives on actual native failures. First compare
the available image evidence on these exact cases and the earlier failure cases;
do not jump from this small sample to another unchanged fit, a max-J selector
or a blanket native-first policy. The present diagnostic identifies targets for
that design; it does not establish a validated next algorithm.

## Execution, operating-policy correction and validation

The absence check for True Color originated in an explicitly temporary October 25
graphics-extra isolation trial without causal attribution. Ryan clarified that
scope and reported stability after replacing the GPU cable. Five saved post-cable
workloads completed cleanly over 3305.717 seconds (about 55 minutes), generally
with the earlier absence check. That history supports ending an unnecessary
blanket launch blocker; it does not isolate the cause of the old failures.

Only the exact `MSI.True Color.exe` Windows process-name condition was relaxed.
Its actual presence (PID20968, protected executable path unavailable) remains
in the readiness and postrun inventory. Unknown GPU executables, competing
model workers, remaining graphics isolation checks, hardware checks and live
fault stops stayed active. No True Color mode or Windows security setting changed.
MSI describes its software as display color management, with laptop-specific
scope in its [usage guide](https://www.msi.com/faq/2578). The experiment itself
reads verified source-image files/caches, not desktop display output.

Debug Mode had earlier been restored from OFF to ON under the standing project
instruction; that actual change is recorded. Fresh NVIDIA accessibility reported
ON before launch. The final screenshot was occluded by other apps; no new
unobscured-toggle screenshot is claimed. Driver 617.42, both RAM modules 5200 MT/s
and the 250 W limit remained unchanged. Prior blocked checks, original helpers,
freezes and authorization records remain preserved with additive amendments.

The completed workload was 354 detector forwards/360 means,109 Q forwards over
3480 candidates, and 3480 CPU J predictions. There were zero fitting updates,
parity forwards, new labels or protected-data accesses. Worker time was 58.688 s;
inclusive supervised launch time was 67.843 s. Across 32 samples, peaks were 54°C,
98.28 W and 2166 MiB. No stop/fault/retry/cleanup error occurred, no owned process
remained, and the event watcher plus postrun check found zero qualifying faults.
This successful run with True Color present does not certify permanent stability.

The 27 scientific implementation checks passed before launch. The narrow
operating-policy correction passed 37 metadata checks and independent review.
The independent neural audit passed 58,452 checks, including exact reproduction
of all J scores; the independent outcome recount passed 321,647 checks. An auditor
initially assumed a preprocessed float cache instead of the actual native uint 8
64×64×3 cache. Its failure and corrected auditor are preserved; no scientific
output changed and no model run was repeated.

Primary records are under
`data/outputs/ball_tracking/fresh_game_diagnostic_v0_1/`: `attempt_001/`,
`analysis/`, `diagnostic_review/`, `launch_v0_1/` and `review/`. The
[result ledger](../configs/ball_tracking/reviews/fresh_game_diagnostic_result_v0_1.json)
binds the main records. All prior scientific results and file contents are
preserved. No Git staging, commit, push, protected evaluation or model adoption
occurred. This completed result supersedes the earlier unrun preparation state.
