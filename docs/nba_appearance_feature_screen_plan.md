# Frozen appearance feature feasibility screen

**Status: `proposed_not_approved`. No feature inference or weight download has
run.** Ryan accepted all 26 appearance proposals with “I accept the proposals.
Move forward chat”. That acceptance authorizes publication of the references
and assessment of the next step, as recorded in the
[acceptance](../configs/ball_tracking/reviews/nba_appearance_reference_acceptance_v0_1.json).
This plan proposes one finite experiment with a new visual representation.
The executable scope and bindings belong to the
[proposal configuration](../configs/ball_tracking/proposals/nba_appearance_feature_screen_v0_1.json).

The question is narrow: can one fixed pretrained image representation retrieve
the correct object class from our small accepted reference bank, while exposing
the known wrong-head failure and retaining valid balls near heads? This is a
feasibility screen, not an integrated ball verifier or an accuracy benchmark.

## Why this experiment

The accepted batch contains ten resolved potential-fit examples, all from SAC:
four balls and six other objects across five targets in two historical training
blocks. P002 contributes five unresolved examples and no resolved reference.
The excluded development checks contain six balls and four hands: DET supplies
five balls and all four hands; P003 supplies one ball. DET 11499 is the sixth
unresolved example. There is no new excluded-check head or clothing negative.

A hand-crafted color or roundness cutoff would revisit cues shared by balls,
heads, skin and clothing, with blur weakening shape evidence. A frozen learned
representation is a distinct, bounded hypothesis. DINOv2's authors document
using frozen class-token features for nearest-neighbor classification and image
retrieval. They do not establish performance on our tiny basketball crops.
[Meta model card](https://github.com/facebookresearch/dinov2/blob/main/MODEL_CARD.md)

The reference bank is supervised by accepted labels, but there is no backbone
fine-tuning, classifier-head training, optimization or threshold selection.
The screen can reject this particular setup before a larger labeling or fitting
effort. Passing cannot remedy the missing domain and distractor coverage.

## Exact finite inputs

The metadata-only registry is
`data/outputs/ball_tracking/nba/appearance_reference_v0_1/feature_screen_scope.json`
(112,596 bytes; SHA256
`b4c662d273155ac7dc0dfab8293b3992cfb82657052fab46e2eafc7b58978806`).
It fixes 60 crop records at 49 distinct already-cached source frames, including
source PNG bindings, native PTS, exact saved points, provenance and crop boxes.

| Role | Crop records | Permitted use |
| --- | ---: | --- |
| Accepted resolved SAC bank | 10 | Four ball and six other-object references |
| Accepted resolved excluded checks | 10 | Six ball and four hand classification checks |
| Accepted unresolved new examples | 6 | Unscored retrieval audit; never negatives or bank entries |
| Prior exposed gap/anchor regression points | 34 | Qualitative supplement only; never bank entries |
| Total | 60 | One encoding per fixed crop record |

All 26 new records use the original mean-component candidate census. The old
34 use the exact saved **selected points**, not reference centers or newly
chosen alternatives. Their selected provenance contains 20 mean and 14
contributor records. Those provenance counts must not be equated with the
anchor/fill counts. Report the two candidate populations separately.

SAC/P002 remain the potential-fit sources, restricted to existing training
authorities. DET/P003 remain excluded from the new reference bank. DET has
already been inspected during development, and P003 trained the retained
detector; these checks are not unseen data. The old 34 points are known
regression examples. Neither neighboring frames nor overlapping candidate
patches become independent observations merely because they have separate IDs.

Use only the registry's hash-verified PNGs. There is no source-video decode,
new target selection, new label, candidate-array read, temporal input expansion
or holdout access. Existing coordinates, selected outputs and geometric scores
remain unchanged.

## One model and one preprocessing path

Use DINOv2 **ViT-S/14 without registers**, through the installed Transformers
`Dinov2Model`, with no classification head. The author card specifies a
384-dimensional class token and 14-pixel patches, and lists Apache 2.0 terms.
[Meta model card](https://github.com/facebookresearch/dinov2/blob/main/MODEL_CARD.md)

Pin the Hugging Face model repository `facebook/dinov2-small` to revision
`150c8e7bb7cef2d30ec31b13a517af14840ee3f7`. The proposed single weight download is
`model.safetensors`, exactly **88,249,960 bytes**, SHA256
`ae1e99fcefd534ed978cdeb8326f08030c96e28b7a81ffcbc98a857c84d14be1`.
These are the published pointer's size and digest; locally downloaded weights
have not yet been verified because no weight download has occurred.
[Pinned weight record](https://huggingface.co/facebook/dinov2-small/commit/150c8e7bb7cef2d30ec31b13a517af14840ee3f7)

Only two small design-source files have been downloaded and verified under
`data/outputs/ball_tracking/nba/appearance_reference_v0_1/design_sources/`:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `config.json` | 547 | `1809f83e3bdb1609a501a610ad4a742f4fd8ae44d72ca4aa0df52d1f2ac8628d` |
| `preprocessor_config.json` | 436 | `14e780d86fa1861f8751f868d7f45425b5feb55c38ca26f152ca5097ab30f828` |

The model configuration fixes the small backbone; the processor configuration
specifies RGB conversion, bicubic resizing, a 224-pixel center crop and the
normalization below.
[Pinned model configuration](https://huggingface.co/facebook/dinov2-small/raw/150c8e7bb7cef2d30ec31b13a517af14840ee3f7/config.json),
[pinned processor configuration](https://huggingface.co/facebook/dinov2-small/raw/150c8e7bb7cef2d30ec31b13a517af14840ee3f7/preprocessor_config.json)

For every saved point `(x, y)`, use the same transform:

1. Start from the bound original RGB PNG. Set `x0 = floor(x) - 32` and
   `y0 = floor(y) - 32`; take `[x0, y0, x0 + 64, y0 + 64)`, with black padding
   outside the source. This is a 64-by-64 native crop; do not recenter on a
   visible ball, reference annotation or alternative candidate.
2. Resize that square to 256-by-256 using PIL bicubic, then take its centered
   224-by-224 crop, `[16, 16, 240, 240)`. The effective native field is the
   central 56-by-56 pixels. This is a deliberate focus on the saved point;
   the earlier 128-by-128 review crops remain unchanged review artifacts.
3. Convert to float32, divide by 255, subtract RGB means
   `[0.485, 0.456, 0.406]`, and divide by RGB standard deviations
   `[0.229, 0.224, 0.225]`. Use channels-first input.
4. Run CPU float32, batch size one, four Torch CPU threads, evaluation mode,
   inference mode and eager attention. Use no autocast, augmentation,
   compilation, remote code or new package installation. Record actual
   library versions. Loading/inference compatibility is still untested.
5. Extract the final-normalized 384-dimensional CLS token, exposed locally as
   `pooler_output`. Save that float32 vector. Convert it to float64, verify
   finite nonzero norm, and L2-normalize for float64 cosine dot products.

There is one encoder, crop, layer, pooling choice and normalization path.
There is no alternative-encoder comparison, multiscale crop, prompt, temporal
average, feature concatenation or hyperparameter grid.

## Retrieval and fixed decision gates

For each of the 50 query records, calculate its cosine similarity to each of
the ten SAC bank vectors. Save all ten similarities and their reference IDs.
Let `s_ball` and `s_other` be the largest similarities within the two classes,
and save `margin = s_ball - s_other`.

Positive margin means `ball_preferred`; negative means `other_preferred`;
an exactly zero margin means `abstain_tie`. These are retrieval preferences,
not calibrated probabilities or accepted output labels. Preserve all tied
nearest IDs within a class. No similarity cutoff is fitted or tuned. Bank
self-matches are not evaluated, and no leave-one-out or alternative bank run
is added.

The **main feasibility gate** passes only if all six accepted excluded-check
balls prefer ball and all four accepted excluded-check hands prefer other.
Any wrong class or tie fails it. Report the ten individual outcomes and their
source/target grouping, together with exact counts. Do not present 10/10 as a
generalization estimate, calibrated operating point or deployment approval.

The six unresolved new examples have no correctness gate. Report their
preferences, margins and nearest references without relabeling them or using
them for adjustment. In particular, preserve the accepted conservative
DET 11499 judgment and its original reader disagreement.

For all 34 old points, report retrieval preferences alongside the saved AI
object assessments, visibly marked **qualitative and previously exposed**.
Those assessments comprise 23 ball, three other-object and eight unresolved
judgments; their separate semantic acceptance was not established by the
earlier geometric-reference acceptance. They are not additional accepted
classification test labels. Flag every disagreement with a resolved AI
assessment and every tie; leave unresolved assessments unscored.

Two supplemental checks directly address the motivating failure:

- `sac_mem_q1_c01` frames **1419, 1420, 1421**: original anchor, fill, original
  anchor on the same wrong head. A ball preference or tie at any of these
  points flags an unresolved failure. Count this as one episode, not three
  independent negative examples.
- `sas_det_q1_c02` frames **11722, 11723, 11724, 11725**: original anchor, two
  fills, original anchor on the ball near the shooter's head. An other-object
  preference or tie flags a possible loss of a useful ball observation.

Keep the main accepted-label gate and these qualitative flags separate. A
main-gate pass with either highlighted regression flag is not a clean result
supporting a follow-on policy proposal. It requires an explicit explanation
and review of the conflict; do not silently promote the old assessments to
accepted truth or change the new rule to remove the flag.

## Evidence, completion and the next decision

Before execution, bind the implementation, proposal, registry, accepted
reference, downloaded model/config/processor bytes and existing source PNGs.
Use focused tests for the actual registry/consumer transport, native crop
edges, normalization, CLS selection, class maxima, ties and resume behavior.
An independent calculation should reproduce every reported similarity and
gate from saved vectors and labels. No full-suite rerun is implied.

Persist per-crop source identity, PTS, saved point/provenance, crop/input hashes,
raw descriptor and retrieval results. Record the real model/download/runtime
resources and preserve failures. Reuse completed, hash-bound encodings after
an operational interruption rather than resetting completed scientific work.
Produce one compact report and a review sheet showing each query with its
nearest ball and other-object references, including the actual final query.
Keep the original source/reference media and all pending-era receipts intact.

A scientific gate failure still completes the report. Do not respond by
swapping the encoder, changing crop sizes, dropping hard examples, moving
source roles, adding labels or tuning thresholds within this experiment.
Failure rejects this fixed encoder/crop/bank setup; it does not prove that
appearance models cannot help. A clean pass supports a later bounded policy
design proposal only. It does not change original anchors, accept new fills,
rerun the selector, certify ball identity or authorize broader use.

The remaining limits must accompany any result: only ten resolved SAC bank
records; correlated episodes and overlapping patches; no resolved NFHS bank
example; no excluded-check head/clothing negatives; no independent head-error
episode; prior development exposure; and a mean-component bank tested against
a mixed-provenance qualitative supplement. Any later validation must address
those gaps rather than treating this screen as their replacement.

Execution needs explicit approval because selecting and running a new learned
representation is a substantive scientific choice. The current
[working agreement](context/working_agreement.md#current-standing-policy-ryans-2026-10-08-instruction)
says: “Bring substantial scientific, architectural, evidence-integrity,
safety, or cost tradeoffs to Ryan for approval rather than escalating routine
fixes.” Routine implementation, publication and metadata inspection are
already authorized; this proposed inference experiment is the specific new
decision. No download of weights, model load, feature inference or scientific
trial is authorized by the reference acceptance alone.
