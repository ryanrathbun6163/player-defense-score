# Bounded ball-versus-distractor reference result

**The approved test stops before fitting because the proposed labels lack two
required kinds of check evidence.** All 184 planned judgments are complete as
AI proposals. New human acceptance is pending. This is an insufficient-data
result, not a failed classifier fit or an improvement in ball tracking.

Ryan approved the [frozen plan](nba_ball_distractor_verifier_plan.md) with
“I approve the bounded test proposal. Move forward chat.” The separate
[approval record](../configs/ball_tracking/reviews/nba_ball_distractor_verifier_approval_v0_1.json)
binds that plan and the exact inventory at starting HEAD
`74053434f26646f1165e1c319a24943eb2c7d11b`. The historical plan's unapproved
wording remains frozen; the later approval supersedes that status.

## Result and decision

The complete proposed reference package passes the size, class, domain, block
and contributor minima, but fails these two requirements:

| Required check evidence | Proposed result | Consequence |
| --- | --- | --- |
| At least one clothing distractor among excluded checks | Zero; check negatives are heads, hands, arms and legs | Clothing rejection cannot be evaluated under the fixed gate. |
| Newly sampled, actually emitted excluded errors including a head and a non-head | Four emitted hand/arm errors across two blocks; zero emitted head errors | The sample cannot establish actual selected-head removal. |

The two newly sampled check heads, DET11512 and P003322, were **unselected
contributor candidates**. Classifying them correctly would remove no saved
tracking output. The four emitted negatives are DET11027 and DET11102 hands,
plus DET11097 and DET11552 arms. The known SAC1419–1421 head remains a separate,
already exposed qualitative challenge; it cannot be promoted into new excluded
class truth to satisfy the gate.

Several sampled geometric errors still lie on a basketball. Their proposed
object label is ball, even when the saved center misses the geometric threshold.
Object classification and ball-center accuracy therefore remain separate.

No feature extraction, classifier fitting, model inference, new selection or
trajectory comparison ran. The baseline and its 602 missing positions are
unchanged. This result does not establish that the proposed classifier would
succeed or fail; the fixed sample cannot support the intended decision.

## Complete proposed census

| New records | Ball | Other object | Unresolved / unused | Total |
| --- | ---: | ---: | ---: | ---: |
| Saved detector candidates | 106 | 31 | 23 | 160 |
| Source-authored fit-only contrasts | 0 | 20 | 4 | 24 |
| Total | 106 | 51 | 27 | 184 |

The four unused contrast requests are hands at SAC677, SAC947, SAC1317 and
P002355. Their visible boundaries or nearest-object assignment were ambiguous;
no replacement object or frame was sought. All 160 candidate centers retain
their exact original coordinates. Authored contrast centers are appearance
examples, not detector errors or geometric ball truth.

The 26 previously accepted labels retain their classes and roles. Their
supplement adds object/episode grouping without reopening the completed class
review. Two same-frame clothing coordinates at SAC1346 share one object, so
20 resolved old rows become 19 groups. Six old unknowns remain unscored.

After grouping aliases, the combined old/new proposed census is:

| Role and domain | Ball groups | Other groups | Total |
| --- | ---: | ---: | ---: |
| Fit NBA | 40 | 23 | 63 |
| Fit NFHS | 12 | 15 | 27 |
| **All fit** | **52** | **38** | **90** |
| Excluded NBA check | 30 | 14 | 44 |
| Excluded NFHS check | 9 | 4 | 13 |
| **All excluded check** | **39** | **18** | **57** |

There are 147 resolved source/frame/object groups and 33 unresolved rows
including old controls. No contrast duplicates another sampled same-frame
object. Repeated frames of an object remain correlated; these counts are not
independent sample sizes or accuracy estimates. All 27 configured adequacy
conditions are recorded; 25 pass provisionally and the two above fail.

## Review package and acceptance boundary

Open the [complete label guide](../data/outputs/ball_tracking/nba/ball_distractor_verifier_v0_1/reference/proposal_review/attempts/7696d457b7c442148c038fc70b89a523/review.html)
or the [5-minute 36-second review video](../data/outputs/ball_tracking/nba/ball_distractor_verifier_v0_1/reference/proposal_review/attempts/7696d457b7c442148c038fc70b89a523/reference_review.mp4).
The guide includes every judgment, original/authored point, rationale,
object/episode assignment, unknown and old grouping supplement. The video shows
all 105 targets with their five native context frames and actual finals.
Classes and point markers appear only on target frames; context frames are
not new labels. The actual video final is included separately.

Three AI readers inspected the complete source census using full-frame evidence
and clean crops: root handled NBA, one reader handled P001/P002, and another
handled P003. Authorship is explicit and not blind. These are human-reviewable
AI proposals, not independently human-annotated truth. Pixel/transport audits
do not establish semantic correctness.

Ryan can accept or correct the new judgments and grouping. If they stand,
this exact bounded test ends with insufficient data. Acceptance alone would
not release fitting while either adequacy requirement fails. The existing
approval already covers one fixed fit and complete comparison if legitimately
accepted labels satisfy every frozen condition; another fitting proposal is
not needed in that case. Adding examples, relaxing gates or changing the
experiment is outside this fixed test. Earlier completed reviews stay complete.

## Execution and validation

Source preparation completed on its first attempt in 104.085 seconds: 360
verified existing NBA PNGs and 165 NFHS frames decoded in 33 approved five-frame
spans. All 525 keys remain outside the 149 old context keys and protected ranges.
Source-sheet rendering completed in 61.359 seconds. Successful label merging
took 1.808 seconds. The complete review render took 196.640 seconds; its
independent audit checked all 525 encoded frames and 210 stills. These are
recorded stage timings, not total annotation time.

Four preparation tests, four grouping/adequacy tests and six rendering tests
pass. They cover actual producer records, exact native clocks and centers,
protected-context exclusion, immutable controls, aliases, unknowns, changed
bindings, actual video encode/decode, markers and final holds. The full suite
was not repeated for these isolated tools.

Independent audits checked all 525 source bindings/RGB identities, source-sheet
pixels, exact merged judgments and physical-group counts. The final media audit
checks every encoded context frame, target point and context final. The
[compact result](../configs/ball_tracking/reviews/nba_ball_distractor_reference_result_v0_1.json)
binds the completed artifacts, audit receipts, test logs and implementation.

Preserved routine failures include the renderer's initial absolute-path guard
test failure, an overstrict audit comparison that rejected prose-only cleanup,
and the first label-merge attempt rejecting NFHS origin/role synonyms. Those
metadata names were corrected in a separate input file without changing any
judgment, center, extent, grouping or evidence. No failed attempt was erased.
No scientific fitting attempt was consumed.

The retained checkpoint, rejected NBA continuation, original selection,
accepted references, prior quantitative evidence and three older pending motion
reviews retain their status. Ball tracking and downstream defensive scoring
remain unfinished.
