# Proposed point-conditioned image-feature feasibility test

## Completed comparison, 2026-10-26

Implementation, the approved CPU pass, scoring and independent audits are now
complete. See [results](ball_tracking_point_feature_comparison_results.md).
The original proposal and authorization checkpoints below remain unchanged as
history. Useful spatial ordering gains coexist with failed visibility separation;
no tracker, threshold or new training is adopted.

## Execution authorized, 2026-10-26

Ryan approved implementation and the single CPU inference comparison after the
explicit history/research reconciliation. The earlier proposed/not-authorized
status below is preserved as the pre-approval checkpoint. No training, new labels,
tracking policy or protected access is included. The execution recipe is
`configs/ball_tracking/proposals/point_feature_comparison_v0_1.json`; implementation
and analysis are frozen before the first new descriptor is computed.

The [saved research reconciliation](../data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/history/research_reconciliation/review.txt)
records the additional reading performed after the proposal, its limits and open
alternatives. The historical review covers Sessions 1–16 through their available
timelines, plus Session 17's complete handoff and relevant primary results; it
does not imply a fresh reread of every transcript or external URL. Existing
research supports investigating candidate-specific image information without
establishing that DINO point tokens are superior. Basketball MonoTrack, specialist
RF-DETR adaptation, learned basketball context and materially changed temporal
tracking remain open alternatives. Each new direction must explicitly reconcile
this research and accumulated project evidence before it is proposed.

**Status: proposed inference design; model comparison not implemented or authorized. CPU input/geometry preparation is complete. No new inference or training has run.**

The next information test should compare the existing DINOv2 global crop
descriptor with a descriptor sampled at the actual candidate point from the
same model output. Keep the model, crop, preprocessing, reference bank and
comparison rule fixed. This isolates spatial readout as the change; it does not
repeat the old fitted veto or simultaneously change the crop scale and model.

This proposal follows the completed
[response-structure diagnosis](ball_tracking_candidate_response_feasibility.md).
Across 882 eligible HOU frames, peak places a matching candidate strictly first
in 837 frames; the five shape descriptors do so in 80–625. Cutoffs retaining
every original native-correct point still leave a known surviving candidate on
all 34 certain-hidden frames for every shape descriptor. These are scalar
diagnostic results, not proof that joint, temporal or conditional use of saved
responses cannot help. The demonstrated motion correction and weak recoveries
remain useful evidence.

## The single controlled change

Use the already specified DINOv2 ViT-S/14 without registers, revision
`150c8e7bb7cef2d30ec31b13a517af14840ee3f7`, with its frozen pretrained weights.
For each distinct input image, obtain two representations in the same forward
pass:

1. **Global control:** the final layer-normalized CLS vector, exactly the old
   `pooler_output` descriptor.
2. **Point readout:** bilinear interpolation of the four neighboring final
   layer-normalized spatial patch tokens at the saved candidate coordinate,
   followed by the same float64 L2 normalization used for CLS comparisons.

The installed `Dinov2Model` source exposes the final normalized sequence as
`last_hidden_state`, with CLS first, and exposes that same first token as
`pooler_output`. For a 224 by 224 input the remaining sequence is a 16 by 16
grid of 384-dimensional tokens. The eventual implementation must verify that
contract and row-major ordering against the pinned local library, rather than
infer it from an array shape alone.

Both representations use the identical fixed cosine-similarity comparison to
the same accepted bank: maximum similarity to an accepted ball minus maximum
similarity to an accepted other object. No logistic head, learned feature
combination, HOU prototype, threshold sweep, crop-size grid or tracking policy
is part of this test. Compare the point readout with a newly computed CLS
control on the same current HOU crops. The old fitted logistic head is adverse
historical evidence, not a fair head for a different descriptor.
CLS queries compare only with CLS bank vectors; point queries compare only with
point bank vectors from those same ten case identities. Bank self-matches are
excluded from check metrics.

Spatial patch tokens are **not isolated local pixels**. Self-attention mixes
context throughout the crop, so the point representation may still reflect a
nearby hand, head, jersey or background. A favorable result would show that the
spatial readout preserves useful information lost by global pooling. A failure
would not establish that all image representations fail.

## Exact source-pixel and crop geometry

Reuse `nba_appearance_feature_screen.crop_and_preprocess` semantics without
editing that frozen function. For a saved floating candidate center `(cx, cy)`:

- Crop the original RGB PNG at
  `[floor(cx)-32, floor(cy)-32, floor(cx)+32, floor(cy)+32)`, right and bottom
  exclusive. This is a 64 by 64 native-pixel crop, with the old black-padding
  behavior retained and explicitly recorded when it touches the source border.
- Resize to 256 by 256 using the same Pillow bicubic operation, then take
  `[16,16,240,240)`. Keep the original RGB scaling and ImageNet mean/std
  normalization. The nominal field of view is 56 source pixels across.
- Do not assume the candidate is at the 224-input midpoint. With integer source
  coordinates denoting pixel centers and crop origin `(left, top)`, the image
  resampling coordinate map is
  `u = 4 * (cx - left + 0.5) - 0.5 - 16`, and likewise for `v`.
  Thus an integer candidate center maps to 113.5, not 111.5; fractional source
  coordinates must be retained. The implementation must verify this convention
  with synthetic ramps/impulses and the actual Pillow transform before freezing.
- A patch token's nominal input center is `(6.5 + 14*j, 6.5 + 14*i)`.
  Interpolate the grid at `((u-6.5)/14, (v-6.5)/14)`. Retain the four token
  indices and interpolation weights for an independent geometry audit. A token
  spans 14 model-input pixels, nominally 3.5 source pixels before context mixing.

The source pixels come from the native PNG, rather than the saved WASB mean.
Enlarging them creates no additional image detail. The old CLS experiment
already used these native crops; **only the spatial readout changes here**.
This proposal therefore does not isolate crop resolution as a cause of the old
failure, and does not claim that changing readout supplies pixels missing from
the old crop.

Bind the original PNG bytes/RGB hash, video identity, source frame/PTS/time base,
crop box, exact floating point center, preprocessing version and input tensor
hash. Two candidates with the same floored crop can share one forward pass but
have different point interpolation weights. Never deduplicate their point
descriptors merely because the input crop is identical. Never recenter a crop
on the accepted reference instead of the emitted candidate.

Padding, nonfinite/zero-norm descriptors and invalid point mappings need explicit
status and denominators. Padding must not masquerade as absence evidence.
Within-ten-pixel correctness also does not certify that a candidate lies on the
physical ball: preserve all such correct points and report localization offset
when interpreting a failed point readout. Do not turn localization misses into
new semantic other-object labels.

## Cohorts and permitted reference roles

Use every candidate in the existing native-plus-strict-.01 HOU pools: 10,778
candidates over all 960 frames of the six complete episodes. Retain the exact
native candidate identities, selected native point, old mass/area, map features
and provenance as comparators. No cap or outcome-dependent subset replaces this
main population.

Separately retain every original expanded-weak choice on those same 960 frames:
949 emitted points and eleven missing rows. These are a selected-output stress
cohort, not a sample of all four million broad candidates. Missing rows stay
missing and need no image-model call. Include all native-correct and native-wrong
cases, certain-hidden emissions, uncertain/unscored rows, the ten e01 gains and
the six below-.01 e05 gains. Preserve the six useful strong revisions and 27
native-correct losses as diagnostic subsets, without selecting inputs from those
subsets alone.

The bank must be the **same ten already accepted, resolved, fit-eligible SAC
reference cases** from the original appearance-screen registry: four ball and
six other-object cases. Their established roles permit the reference comparison;
this does not make SAC an independent test. Recompute their point descriptors
under the identical representation and preserve their exact identities. Do not
augment the bank with HOU, DET, pending AI appearance labels, uncertain cases or
newly authored labels. There is no HOU parameter fit or gradient update.

Preserve the original sixty-case appearance-screen registry as a separately
reported historical diagnostic: bank, accepted checks, unresolved audit and
exposed regressions retain their different authority. In particular, the
the original nearest-bank CLS control incorrectly preferred other objects for
the accepted balls at DET11059 and DET11431, and preferred ball for the exposed
SAC1419–1421 head points. It correctly classified the accepted DET11008 and
DET11444 ball/other cases. The later fitted logistic veto had different errors:
DET11008/11444 rank inversions and DET11431's negative but correctly ordered
logits. Preserve those as separately named fitted-veto diagnostics, not failures
of the proposed nearest-bank CLS control. These already inspected DET cases choose no
feature, bank, crop, threshold or model. Do not expand this into fresh DET
validation or promote pending AI judgments into accepted semantic labels.

HOU remains repeatedly inspected checkpoint-validation development, excluded
from model fitting. Existing SAC exposure, NFHS secondary evidence, nine
inconclusive recoveries, protected closure and final human trajectory-review
requirements remain unchanged.

## Cache-only preparation before any model call

The available inventory supports preparation from existing permitted PNGs and
saved records. It establishes all 960 original HOU PNGs and exact current pool
and choice bindings; there are no saved HOU DINO descriptors or spatial patch
tokens. Nearby cached crops cannot substitute for an exact input.

Preparation can create a bound registry, join source/candidate identities,
deduplicate exact source/crop/tensor inputs while retaining all point queries,
verify native parity, record border padding, and test crop/point geometry on
synthetic images. It can generate review contact sheets from already permitted
pixels with the actual candidate point overlaid. This is geometry inspection,
not a new labeling campaign. Seal the input inventory and source/tests before
descriptors; seal all descriptors before outcome-assisted analysis.

The existing local weight path is
`data/outputs/ball_tracking/nba/appearance_feature_screen_v0_1/model/model.safetensors`.
The historical protocol records 88,249,960 bytes and SHA256
`ae1e99fcefd534ed978cdeb8326f08030c96e28b7a81ffcbc98a857c84d14be1`.
**Verify the actual file, config, processor and installed implementation before
any proposed model run.** The completed CPU preparation below rehashed the
current files and matched these historical identities. Execution must still
check that they remain unchanged. No download, model load, new encoding or fit
follows from this preparation.

## Cost basis and remaining execution decision

One forward pass provides both readouts. The present census gives a conservative
pre-deduplication ceiling of 11,787 input requests: 10,778 main candidates, 949
emitted stress points and sixty historical cases including the ten bank cases.
This is an upper bound, not the unique-input or model-call count; preparation
must establish the exact count. Repeated points and crops should share model
work without losing their separate identities. Preserve an immutable output
cache and actual call/time counters so interruptions do not erase work.

The original screen completed sixty CPU encodings and 49 PNG decodes in
12.594 seconds. The later emission pass completed 3,225 new encodings plus cache
reuse and image/video reads in 569.860 seconds. Linear extrapolation to the
upper census suggests roughly 35–42 minutes at the historical CPU throughput,
before new audit/storage overhead. This is a planning estimate, not a benchmark
or guaranteed limit: the new environment, input grouping, library behavior and
output retention can change it. Exact deduplication should reduce calls; token
readout itself does not require a second model pass. Store the two descriptors
and the necessary token/weight witnesses instead of automatically duplicating
every full token grid for every query.

The concrete outstanding decision is whether to authorize this single frozen
pretrained-model inference pass, preferably using the already established CPU
configuration (float32, batch one, four Torch threads, eager attention). CPU
execution still constitutes new inference and is not authorized by the saved-
output study. Any GPU alternative needs its own explicit device/resource choice,
graphics-app isolation check and established monitoring safeguards. Neither
inference choice authorizes training or adoption. A different crop, backbone,
head or fitting dataset would be another subsequent decision.

## Completed CPU preparation, without inference

The ignored `point_preparation_v0_1/completed.json` receipt records all 11,798
queries: 10,778 main candidates, 960 stress rows and sixty historical cases.
There are 11,787 emitted point queries and eleven explicit missing stress rows.
From 1,009 verified source PNGs, preparation produced **10,883 distinct
source/crop/tensor input identities**. All point queries remain separate. There
are 10,584 distinct tensor hashes; identical tensors across different source
identities are reported without discarding source/clock provenance.

The full crop pass completed in 54.640 seconds. Every one of the 10,883 unique
crop/tensor inputs exactly matched the original producer, and all sixty old
saved crop/input/tensor/CLS bindings verified. Current local weights, config,
processor, library source and package versions matched their historical pins.
No Torch import, model load, model call, feature extraction, fit, selector run,
source-video replay or protected-pixel access occurred. Forty-one main-candidate
crops include black padding; all 949 emitted stress crops and sixty historical
crops are complete. Padding and missingness remain explicit, not inferred
absence or silently omitted evidence.

The final preparation geometry was sealed in `geometry_freeze_003.json` before
the full crop pass. Seven focused tests passed: six synthetic checks, including
actual Pillow half-pixel ramp/impulse behavior and old-producer crop/tensor
parity, plus one full real-registry metadata transport check without source PNG
decoding. Two earlier metadata-only attempts are preserved with their exact
source, tests, freezes and failure logs. The first incorrectly passed an image
binding containing an additional RGB hash to a three-field file-binding checker;
the second assumed historical NFHS timing used the NBA `source_manifest` field
instead of its actual `native_timestamps` field. Neither reached source PNG
decoding, and neither involved a geometry failure. Their corrections preserved
the original geometry/preprocessing function text exactly.

Six fixed contact sheets show the first, middle and last frame of every HOU
episode, with native-selected, first weak and stress points. Red marks the exact
point and cyan marks the four token centers. Missing categories are labeled;
padding is marked. These are crop/coordinate review aids, not new semantic
labels or acceptance of a tracker. The agent inspected all six for readable
layout and point/token overlays; human trajectory acceptance is not claimed.

The completed census revises the historical CPU extrapolation to roughly
**32–38 minutes** for one pass over 10,883 source-specific inputs, before new
audit/storage overhead. This remains an estimate, not an executed benchmark.
If inference is subsequently authorized, both representations must come from
the same pass. The sixty historical raw CLS vectors must match their existing
cache with the prospectively recorded `atol=1e-5, rtol=1e-5`, before outcome
analysis. A mismatch must remain a recorded failure requiring diagnosis, not
silently redefine the control. No inference was run to choose this tolerance.

The complete query/input registries, tensor hashes, old-feature links, native
clock fields and contact sheets are ignored under
`data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/point_preparation_v0_1/`.
The completion receipt is 5,005 bytes, SHA256
`e6e86d402ba22c43404c17861035a88bcbe7dea32c5e302f4761882329bd6850`.
This preparation does not freeze or authorize the proposed model comparison.

The independent `independent_source_transport_audit.json` passes 147,319 checks
over every query/input and all 1,009 source PNG byte hashes. It independently
joins the emitted clocks and source identities to original HOU timing/preparation,
historical NBA source manifests and NFHS native-timestamp records, and verifies
all candidate choices, ten bank identities and original historical roles. It
imports no preparation helper. Video identity is checked through bound emitting
metadata; videos are not rehashed or decoded, and RGB/tensor arithmetic is not
repeated. Historical CLS byte bindings are verified; newly computed CLS parity
remains a requirement of the future inference comparison. The receipt SHA256 is
`13dc14fee44c9f301da93db055b4e0d182fcd0ed1ef72334a0ccbcc18048c311`.

## Results that would change the recommendation

Compare CLS and point margins on identical HOU candidates, episode by episode.
Keep peak, native-only mass and the completed map-feature results as comparators.
Report strict ordering/ties, same-frame matching-versus-competing locations,
native-correct preservation and the two already used shared-HOU diagnostic
visibility bounds. Unknowns cannot count as successful rejections. Do not apply
the old zero-logit veto or report new tracking accuracy from descriptor scores.

A useful increment is point readout improving paired ordering beyond CLS in the
troublesome alternatives, with fewer native-wrong/hidden preferences while
preserving native-correct points and the e01/e05 weak successes. Improvement
should recur across relevant episodes rather than depend on one favorable
pooled count. It need not pass every final tracking gate to justify a separately
frozen scoring/abstention comparison. The actual gains and losses, including any
partial-ball losses, are the decision evidence; this design does not invent a
new numerical acceptance threshold after seeing them.

If point readout mostly agrees with CLS, improves heads only by rejecting valid
partial/weak balls, or retains overlapping hidden responses, do not fit a new
head merely to rescue this run. Distinguish failed ranking from failed scalar
calibration and inadequate bank coverage. That outcome would reject this
specific frozen readout/reference rule and motivate a separately specified
pixel-detail, spatial representation or target-supervision test. It would not
prove that all DINO features, native crops, appearance, temporal combinations or
evidence-conditioned objectives are exhausted. Training remains conditional on
a concrete later design and decision.

## Evidence used for this proposal

This proposal reuses the completed sixteen-session historical review and reads
the relevant primary source/report paths; it does not claim another complete
transcript review or independent rerun. Relevant evidence includes the
[old feature screen](nba_appearance_feature_screen_results.md),
[fitted veto results](nba_ball_distractor_training_results.md),
[weak-response results](ball_tracking_weak_response_results.md), the frozen
`nba_appearance_feature_screen.py` producer and installed `modeling_dinov2.py`,
and these ignored current records:

- `candidate_identity_feasibility_v0_1/history/hypothesis_review.txt` and
  `history/saved_dino_diagnosis_v02.json` preserve the adverse same-frame cases,
  optimizer evidence and limits on causal attribution.
- `candidate_identity_feasibility_v0_1/inventory/saved_availability.json` binds
  the saved native PNG/map/pool inventory and exact old-feature overlap.
- `candidate_identity_feasibility_v0_1/study_v0_1/analysis_v0_1/completed.json`
  contains the sealed response-descriptor outcome analysis.

All these ignored paths are relative to `data/outputs/ball_tracking/`.
No frozen scientific source, configuration or prior artifact is changed by this
proposal. No Git staging, commit, push, PR or merge is performed.
