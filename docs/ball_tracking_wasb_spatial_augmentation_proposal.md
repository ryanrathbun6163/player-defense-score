# Next training proposal: coherent spatial augmentation

October 26, 2026. Recommendation following the
[completed paired continuations and diagnostics](ball_tracking_wasb_continuation_results.md).
No new executable recipe is frozen and no fit under this proposal has run.

## Why this change

The actual current 768 model fits 2,937/2,941 training positives, including
2,165/2,167 partial positives, while ten continuation checkpoints retain the
same 19-frame DET gap. Training loss decreases without the needed development
improvement. Only mirror and brightness variation are currently applied; scale
and position variation are not. A coherent spatial augmentation trial tests a
limited generalization hypothesis using accepted labels and completed controls.

Training-only augmentation has primary evidence for improving detection
generalization ([Zoph et al., 2019](https://arxiv.org/abs/1906.11172)).
Scale jitter is an established detector augmentation
([Ghiasi et al., 2021](https://arxiv.org/html/2012.07177v2)). Those studies use
different tasks and schedules. They do not validate this exact two-epoch recipe
or establish that scale/placement causes the DET hand-overlap failure.

## One new factor and a reused control

- Start from the exact completed 768 epoch-five full state used by both previous
  arms, including optimizer/RNG history. Do not initialize from the post-selected
  diagnostic epoch nine.
- Run absolute epochs six and seven only: 3,104 new updates, constant learning
  rate 0.0001. Compare with the already completed constant-arm epochs six and
  seven on the same draws; another control fit is unnecessary.
- Add one augmentation family: isotropic scale and translation, shared across
  all three input frames and supervised geometry. Initial proposed bounds are
  probability 0.5, scale 0.9–1.1, translation at most 3% of width/height. These
  bounds require the preparation checks below before freezing.
- Preserve mirror/brightness draws, training examples, game mixture, sampling,
  architecture, 768x432 inputs, batch size, precision, frozen BatchNorm, loss,
  target meaning, native inference and every quality criterion. Spatial draws
  must be independently keyed so they do not alter other random draws.
- Transform center, target footprint and uncertainty support consistently.
  If supervised support would be clipped, use a logged identity fallback.
  Never wrap or reflect pixels into a second ball. Any padding uses a declared
  constant fill with no invented positive target. Masked channels remain masked;
  hidden channels remain negative. Accepted source labels are immutable;
  transformed targets are derived training examples.

Preparation must settle exact pixel-center mapping, interpolation, padding,
target rasterization and support checks in an additive implementation. Verify
inverse geometry and inspect representative transformed training triplets,
including tiny/partial balls, boundaries, certain-hidden and masked frames.
Use existing training caches; do not inspect protected data or train on HOU/DET
development failures. Native validation inputs and scoring remain unchanged.
Publish implementation, examples and focused checks before freezing a recipe.
There is no new labeling campaign.

## Decision and cost

Report both epochs against the parent and matched constant controls, including
every HOU per-episode gate, DET gaps/correct/wrong counts, SAC training-exposed
results and NFHS secondary regressions. Do not select by pooled accuracy or
call a lower loss a success. A promising outcome needs improvement in an actual
remaining failure family without offsetting coverage/false-emission regressions.
If neither epoch does that, do not extend this pilot automatically; record what
it tested and choose the next hypothesis. Adoption still requires every quality
criterion and complete human review.

Measured continuation timings imply about 18 minutes of fitting and 4–5 minutes
of NBA comparison for two epochs. Allow roughly 25 minutes of monitored compute,
plus implementation, geometry verification, audits and visual review. This is
not an end-to-end or phase-completion promise. Maintain one supervised GPU
workload at a time and the same graphics-app isolation/device-failure response.

This augmentation cannot create genuinely new hand/ball appearances, guarantee
generalization, or resolve reference uncertainty. Four residual training
localization failures and two hidden emissions provide weaker support for broad
hard-example/negative weighting as the next first intervention. Do not combine
loss changes, synthetic occluders, blur, a new architecture or threshold tuning
with this pilot; they would prevent isolating the effect of spatial augmentation.
A later architecture/data tradeoff must be judged separately.

The nine source-uncertain recovery events remain a separate acceptance issue.
Keep their exact evidence and inconclusive status. Human review may establish
whether any uncertainty is resolvable; it must not silently upgrade references
or remove events. Protected evaluation remains closed pending a frozen method
and separate explicit authorization.
