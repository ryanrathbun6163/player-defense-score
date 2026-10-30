# Fixed appearance-feature screen: failed feasibility gate

Ryan's “Ok move forward chat” approved the frozen 60-crop experiment. The
[approval](../configs/ball_tracking/reviews/nba_appearance_feature_screen_approval_v0_1.json)
supersedes the historical pending status of the unchanged
[plan](nba_appearance_feature_screen_plan.md) and
[proposal](../configs/ball_tracking/proposals/nba_appearance_feature_screen_v0_1.json).
The [compact result](../configs/ball_tracking/reviews/nba_appearance_feature_screen_result_v0_1.json)
binds the actual implementation, sources, model, report, tests, audit and review.

**The fixed setup failed: eight of ten accepted checks correct, with two real
balls preferring other objects.** It also preferred ball at all three saved
points in the known SAC head episode. Do not adopt it as a ball verifier or
modify trajectories from these results. The failure completes the experiment;
no encoder, crop, bank or threshold was changed in response.

## Exact result

| Population | Result |
| --- | --- |
| Ten accepted excluded checks | 4/6 balls and 4/4 hands correct; two errors, no ties; required 10/10 gate fails |
| Six accepted unknowns | Preferences reported, correctness unscored; labels unchanged |
| 34 exposed older points | Eleven disagreements with resolved prior AI judgments; eight unresolved remain unscored; zero ties |
| SAC 1419–1421 head episode | All three points prefer ball; supplemental flag fails (one episode) |
| DET 11722–11725 near-head balls | All four points prefer ball; this supplemental check has no adverse flag |

The older 34 judgments remain qualitative AI assessments, not newly accepted
classification truth and not pooled with the ten checks. Their 20 mean and
14 contributor provenance records remain distinct from anchor/fill roles.

| Source / frame / candidate | Accepted class | Preference | Ball-minus-other margin | Check |
| --- | --- | --- | ---: | --- |
| sas_det_q1_c02 / 11008 / mean:0 | other_object | other_preferred | -0.041035 | correct |
| sas_det_q1_c02 / 11008 / mean:1 | ball | ball_preferred | +0.077336 | correct |
| sas_det_q1_c02 / 11059 / mean:0 | ball | other_preferred | -0.011298 | incorrect |
| sas_det_q1_c02 / 11107 / mean:0 | other_object | other_preferred | -0.039996 | correct |
| sas_det_q1_c02 / 11107 / mean:1 | ball | ball_preferred | +0.048317 | correct |
| sas_det_q1_c02 / 11431 / mean:0 | ball | other_preferred | -0.087911 | incorrect |
| sas_det_q1_c02 / 11431 / mean:1 | other_object | other_preferred | -0.065694 | correct |
| sas_det_q1_c02 / 11444 / mean:0 | ball | ball_preferred | +0.037597 | correct |
| sas_det_q1_c02 / 11444 / mean:1 | other_object | other_preferred | -0.194185 | correct |
| possession_003 / 428 / mean:0 | ball | ball_preferred | +0.095956 | correct |

The false rejections are DET11059 and DET11431. Their nearest other references
are the SAC961 and SAC1299 hands respectively. The SAC head margins are
+0.103272, +0.134865 and +0.100668; every correctly classified accepted ball has
a smaller margin (largest +0.095956). Therefore increasing a positive-margin
cutoff cannot reject these heads while preserving those balls. This conclusion
uses the ordering of the saved results, not another threshold experiment.
Both wrong-head anchors also pass the original positive-margin rule.

## Review and verification

The [complete crop/neighbor review](../data/outputs/ball_tracking/nba/appearance_feature_screen_v0_1/review/attempts/f57fda8a29804bb6a6379d447796b681/review.html) shows all 50 queries beside their
nearest ball and other reference, with scores, source frames, roles and label
status. Ten sheets and the actual final query were inspected by the assistant;
all 150 displayed crop panels match their bound native crops exactly. No new
human playback, object-label acceptance or trajectory acceptance is claimed.
A new review is not needed to establish the already-failed numerical gate;
all earlier completed human reviews remain completed.

Six focused tests passed on their first run in 4.826 seconds. After clarifying
only the renderer header, the affected review test passed in 1.942 seconds.
Tests cover the actual captured registry, floor/black-padding preprocessing,
CLS extraction, float64 normalization, all 500 synthetic comparisons, ties,
unknown separation, interrupted cache resume, tampering and emitted media
transport. Synthetic intentional failures are preserved as test evidence.
There were no unexpected test failures and no full-suite repeat.

An independent audit passed 3,914 checks in 3.078 seconds. It verified all
49 source PNG byte/RGB hashes, 60 native crops, 60 model inputs, exact scalar
float32 preprocessing, 60 descriptors and all 500 similarities. Independent
float64 sums differed by at most 2.22e-16. Exact joins and the earlier selected
outputs, original 790-frame report and accepted 27-reference report are intact.

## Execution and limits

One weight download verified the pinned 88,249,960-byte safetensors file in
8.200 seconds. One production attempt completed in 12.594 seconds: one CPU
model load, 60 encodings, 49 cached PNG decodes and zero operational failures.
There were no source-video decodes, candidate-array reads, training updates,
parameter variations or trajectory changes. All features are saved for reuse.
The locally tested implementation was bound before execution and integrated
into Git afterward; the run does not claim a pre-execution implementation commit.

Model: DINOv2 ViT-S/14, revision `150c8e7bb7cef2d30ec31b13a517af14840ee3f7`,
final-normalized CLS vector with 384 dimensions, CPU float32, batch one, four Torch threads and eager
attention. The fixed 64-pixel native crop / bicubic resize to 256 / center crop to 224 transform and float64
feature normalization match the plan. Actual versions: Torch 2.13.0+cu130,
Transformers 5.14.1, safetensors 0.8.0, NumPy 2.4.6 and Pillow 12.3.0.

The bank still has only ten resolved SAC objects. It has no resolved NFHS
example; excluded negatives are hands, with no head/clothing episode. Repeated
objects, overlapping crops, previous development exposure and mixed candidate
provenance prevent any independent accuracy claim. The one known head episode
cannot establish broad head rejection. A failed setup does not prove that all
appearance methods fail.

## Next direction

Close this exact nearest-reference setup. The current experiment produced no
new tracking improvement and does not change the ball-phase finish line.
The next design should combine a bounded supervised candidate-verifier test
with the reference coverage it needs: resolved NFHS balls, head/clothing
objects from distinct fit and excluded episodes, valid balls near heads, and
contributor candidates. Specify one finite sampling budget and one fixed
fit/evaluation before starting new data or model work; keep unknowns unknown.
This is a recommendation for the next scientific proposal, not execution
approval. No further fitting, inference or label collection has started.
