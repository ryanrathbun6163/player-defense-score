# Ball-detector baseline window selection v0.1

## Status and purpose

Ryan approved the nine windows in this record on 2026-08-23 America/Phoenix,
before any selected-window detector prediction was generated or viewed. The
machine-readable experiment contract is
`configs/ball_tracking/experiments/rfdetr_medium_image_only_baseline_v0_1.json`.

This record makes the label-blind selection reproducible. It freezes which raw
video measurements were used, how candidates were ranked, which separation
guards applied, and how ties were resolved. The measurements below inspect only
source pixels and source metadata. They do not load ball annotations, detector
outputs, player tracks, or manually supplied ball locations.

The nine windows are still annotation-pending and under prediction embargo.
They are not detector results, a selected operating point, or a quality gate.

## Candidate grid, guards, and selection order

Each verified source is decoded sequentially. A candidate is the inclusive
25-frame block `[25k, 25k + 24]`.

A candidate must leave at least 25 source frames before and after itself. It
must also leave at least 25 intervening, unselected frames between itself and:

- the reviewed protocol-adjudication pilot in the same possession;
- every evaluation split already selected in that possession; and
- any known frame on which historical detector output had already been viewed.

For Possession 001, historical detector evidence is bound to source frame 150.
The separation rule therefore excludes starts 125, 150, and 175. Metrics and
normalization are computed from the complete eligible set after all fixed
source, edge, pilot, and historical-evidence guards:

| Possession | Eligible candidate starts |
| --- | --- |
| `possession_001` | `25, 50, 75, 100, 200, 225, 250, 275, 300, 325, 425` |
| `possession_002` | `25, 50, 75, 100, 125, 150, 175, 200, 225, 250, 375, 400, 425` |
| `possession_003` | `25, 50, 75, 100, 125, 150, 175, 200, 225, 250, 275, 300, 325, 350` |

The selection order is fixed: **holdout, representative, challenge**. After a
split is selected, its 25-intervening-frame guard is applied before choosing
the next split. Descriptor values and population normalization are not
recomputed on the shrinking candidate set.

## Holdout rule

The holdout is chosen without a visual difficulty judgment. For every eligible
candidate, compute SHA-256 over this exact UTF-8 string with no trailing newline:

```text
ball_tracking_test_holdout_v0_1|<lowercase source_sha256>|<start>|<end>
```

Sort the lowercase hexadecimal digests lexicographically and select the first.
A theoretical digest tie is resolved by the lower start frame.

| Possession | Holdout | SHA-256 ordering digest |
| --- | ---: | --- |
| `possession_001` | `300..324` | `0d20d0ad64ffb73c63e0c82c84fee30b265daa3f33a8dedc453e7dae13502d32` |
| `possession_002` | `200..224` | `379d2207206e13f1754614ce77c825e487f274ac4b5d20123815bfc6c6e06a73` |
| `possession_003` | `250..274` | `06f80419653d714d972992993d6be2c3d3fe58a1414f8b0c12a9714cf36d5105` |

These windows receive structural review only until the detector and operating
point are frozen. They are not swapped based on perceived difficulty.

## Representative rule

Resize each raw frame to 320 by 180 pixels with OpenCV `INTER_AREA`, then
convert it to grayscale. For each frame, measure:

- mean grayscale brightness;
- grayscale standard deviation, used as contrast; and
- Laplacian variance, used as a sharpness measure.

For each of the 24 internal frame transitions, measure:

- mean absolute grayscale difference; and
- the 90th percentile of dense optical-flow magnitude using Farneback flow with
  `pyr_scale=0.5`, `levels=3`, `winsize=15`, `iterations=3`, `poly_n=5`,
  `poly_sigma=1.2`, and `flags=0`.

The five-component block vector is:

```text
[
  median brightness,
  median contrast,
  ln(median Laplacian variance),
  mean internal absolute difference,
  mean internal p90 optical flow
]
```

Within each possession's complete eligible candidate set, normalize every
component as `(value - component_median) / component_IQR`; use `1` when a
component IQR is zero. A block's representative distance is the mean absolute
value of its five normalized components. After applying the holdout separation
guard, select the minimum distance. A score tie goes to the lower start frame.

| Possession | Representative | Distance |
| --- | ---: | ---: |
| `possession_001` | `50..74` | `0.322132` |
| `possession_002` | `250..274` | about `0.389` |
| `possession_003` | `300..324` | about `0.136` |

Leading remaining candidates, shown at audit-report precision, were:

- P001: `100 .411`, `225 .530`, `425 .539`, `75 .577`, `200 .601`,
  `25 .611`, `250 .657`;
- P002: `75 .449`, `100 .475`, `425 .503`, `150 .571`;
- P003: `350 .310`, `325 .429`, `75 .617`, `200 .622`.

## Challenge rule

The challenge score has exactly five raw-video descriptor families: frame
difference, optical flow, sharpness/blur, brightness variability, and histogram
change. Player or hand overlap is not a numeric input.

For each eligible block, compute:

- `MAD`: mean of the 24 internal mean absolute grayscale differences;
- `flow90`: mean of the 24 internal p90 Farneback-flow magnitudes;
- `lap`: median per-frame Laplacian variance;
- `lap_iqr`: IQR of per-frame Laplacian variance;
- `brightness_iqr`: IQR of per-frame grayscale brightness; and
- `histmax`: maximum internal Bhattacharyya distance between adjacent normalized
  64-bin grayscale histograms.

Within the complete eligible candidate set for the possession, convert each
ascending descriptor value to an empirical rank from 0 through 1, ordering
equal values by lower start frame. For `N` candidates, the zero-based sorted
position `i` has rank `i / (N - 1)`. Define
`inverse_sharpness = 1 - rank(lap)`, then compute:

```text
challenge_score =
    0.20 * rank(MAD)
  + 0.25 * rank(flow90)
  + 0.20 * inverse_sharpness
  + 0.10 * rank(lap_iqr)
  + 0.10 * rank(brightness_iqr)
  + 0.15 * rank(histmax)
```

After applying holdout and representative separation guards, select the maximum
score. A score tie goes to the lower start frame.

| Possession | Challenge | Score |
| --- | ---: | ---: |
| `possession_001` | `200..224` | about `0.805` |
| `possession_002` | `25..49` | about `0.908` |
| `possession_003` | `150..174` | about `0.827` |

Leading remaining candidates, shown at audit-report precision, were:

- P001: `225 .775`, `250 .605`, `425 .540`, `100 .220`;
- P002: `50 .775`, `125 .642`, `150 .588`, `100 .562`;
- P003: `25 .819`, `175 .819`, `50 .669`, `350 .527`.

## Approved windows

| Possession | Representative evaluation | Challenge evaluation | Test holdout |
| --- | ---: | ---: | ---: |
| `possession_001` | `50..74` | `200..224` | `300..324` |
| `possession_002` | `250..274` | `25..49` | `200..224` |
| `possession_003` | `300..324` | `150..174` | `250..274` |

Ryan reviewed prediction-free, source-only 5-by-5 contact sheets labeled only
with frame indices. All nine windows are uninterrupted live half-court play;
none contains a broadcast cut or decode corruption. The representative windows
look like ordinary same-game play. The challenge windows show same-game motion
and blur; post-selection visual review also observed hand/player proximity or
congestion. Possession 002 is the strongest pan/blur case and Possession 003 is
a congestion case. Those observations characterize the selected source pixels;
they did not change the numeric ranking.

This small, same-game design does not claim exhaustive rim interaction, shot,
rebound, transition, replay, or broadcast-cut coverage. A constant scoreboard
overlay is present. Broader coverage remains future work.

## P001 stale temporary-sheet reconciliation

A temporary file named
`possession_001_representative_final_0100_0124.png` was generated during an
intermediate pass that applied edge and pilot guards but had not yet applied the
historical-prediction guard. In that intermediate population, frames 100..124
scored about `0.273` and frames 50..74 scored about `0.293`.

The repository's `src/extract_frame.py` binds
`data/outputs/frame_candidates/frame_06s.jpg` to Possession 001 frame 150. A
fresh OpenCV encoding of decoded source frame 150 matched that artifact
byte-for-byte with SHA-256
`364cad206e0b7c94da91a06918f235fa9daf77d828876da9a22683574c81365e`.
Because historical detector output for that frame had already been viewed, the
25-intervening-frame policy removed blocks 125..149, 150..174, and 175..199.

All population normalization and ranks were then recomputed from scratch. In
the final eligible population, frames 50..74 scored `0.322132`, ahead of frames
100..124 at about `0.411`. The later-looking word `final` in a temporary
filename has no provenance authority. Ryan's approved contact sheet, this
record, and the machine-readable manifest all freeze frames 50..74.

## Leakage and release boundary

- The three reviewed protocol pilots may be used for the first descriptive
  detector run.
- The six representative/challenge windows remain prediction-embargoed until
  their label files are complete and reviewed.
- The three holdouts additionally remain unreleased until the detector and its
  operating point are frozen.
- The v0.1 schema cannot change a non-pilot status in place. Any embargo release
  requires reviewed code and a new versioned schema/manifest that retains this
  record as immutable history.
- No threshold or localization radius has been selected, and no detector
  quality gate has been defined.
- Any departure from these windows or rules requires a new versioned experiment
  manifest and an explicit audit explanation; it must not silently overwrite
  this precommit.
