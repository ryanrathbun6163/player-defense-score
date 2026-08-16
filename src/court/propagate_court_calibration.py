import argparse
import json
from collections import Counter
from pathlib import Path

try:
    import cv2
except ModuleNotFoundError:
    cv2 = None

try:
    import numpy as np
except ModuleNotFoundError:
    np = None

try:
    from scipy.signal import savgol_filter
except ModuleNotFoundError:
    savgol_filter = None


DEFAULT_VIDEO_PATH = Path("data/clips/possession_001.mp4")
DEFAULT_CALIBRATION_PATH = Path(
    "configs/possession_001_court_calibration_final.json"
)
DEFAULT_COURT_CONFIG_PATH = Path("configs/possession_001_court.json")
DEFAULT_OUTPUT_DIR = Path(
    "data/outputs/court/possession_001_motion_review"
)
DEFAULT_OUTPUT_VIDEO_PATH = (
    DEFAULT_OUTPUT_DIR / "possession_001_court_motion_review.mp4"
)
DEFAULT_HOMOGRAPHIES_PATH = (
    DEFAULT_OUTPUT_DIR / "possession_001_camera_homographies.npz"
)
DEFAULT_REPORT_PATH = (
    DEFAULT_OUTPUT_DIR / "possession_001_court_motion_review.json"
)

DEFAULT_SAMPLE_COUNT = 7
DEFAULT_MAX_FEATURES = 6000
DEFAULT_REVIEW_WIDTH = 1280
DEFAULT_SMOOTHING_WINDOW = 11
DEFAULT_EXTRA_CHECKPOINT_FRAMES = [
    244,
    291,
    294,
    339,
    469,
    470,
    475,
    479,
    494,
    498,
]

LOWE_RATIO = 0.75
RANSAC_THRESHOLD_PX = 4.0
MIN_RATIO_MATCHES = 20
MIN_INLIERS = 15
MIN_INLIER_RATIO = 0.25
MAX_MEDIAN_REPROJECTION_ERROR_PX = 4.0
MAX_FALLBACK_CHAIN = 12
ROBUST_BASELINE_RADIUS = 30
ROBUST_REFIT_RADIUS = 35
MAX_ROBUST_MEDIAN_RESIDUAL_PX = 12.0
MAX_ROBUST_POINT_RESIDUAL_PX = 50.0
GEOMETRY_FALLBACK_MEDIAN_WINDOW = 21
GEOMETRY_FALLBACK_SAVGOL_WINDOW = 31
MIN_NORMALIZED_PROJECTION_DENOMINATOR = 0.01
MAX_ABSOLUTE_CONTROL_COORDINATE_FRAME_MULTIPLIER = 4.0
MIN_CONTROL_SPAN_FRAME_FRACTION = 0.02
MAX_CONTROL_SPAN_FRAME_MULTIPLIER = 4.0
MAX_CONTROL_STEP_DIAGONAL_FRACTION = 0.35
MAX_CONTROL_ACCELERATION_DIAGONAL_FRACTION = 0.50
MAX_REFERENCE_ANCHOR_ERROR_PX = 0.5
TERMINAL_SEARCH_FRAME_COUNT = 60
TERMINAL_REJECTED_RUN_TRIGGER = 5
TERMINAL_MIN_REJECTED_SUFFIX_FRACTION = 0.70

COURT_MODEL_COLOR = (0, 235, 255)
FIT_REGION_COLOR = (70, 230, 70)
WARNING_COLOR = (0, 165, 255)
ERROR_COLOR = (30, 30, 230)
TEXT_COLOR = (255, 255, 255)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Propagate a reviewed reference court homography "
            "through a moving-camera possession and render a "
            "visual validation video."
        )
    )
    parser.add_argument(
        "--video",
        type=Path,
        default=DEFAULT_VIDEO_PATH,
        help="Source possession video.",
    )
    parser.add_argument(
        "--calibration",
        type=Path,
        default=DEFAULT_CALIBRATION_PATH,
        help="Final reviewed reference-frame calibration JSON.",
    )
    parser.add_argument(
        "--court-config",
        type=Path,
        default=DEFAULT_COURT_CONFIG_PATH,
        help="Playable-court polygon configuration.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for motion-review outputs.",
    )
    parser.add_argument(
        "--output-video",
        type=Path,
        default=DEFAULT_OUTPUT_VIDEO_PATH,
        help="Moving-court validation MP4 path.",
    )
    parser.add_argument(
        "--output-homographies",
        type=Path,
        default=DEFAULT_HOMOGRAPHIES_PATH,
        help="Per-frame camera homography NPZ path.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Camera-motion validation JSON path.",
    )
    parser.add_argument(
        "--sample-count",
        type=int,
        default=DEFAULT_SAMPLE_COUNT,
        help="Number of full-resolution checkpoint overlays.",
    )
    parser.add_argument(
        "--max-features",
        type=int,
        default=DEFAULT_MAX_FEATURES,
        help="Maximum ORB features detected per frame.",
    )
    parser.add_argument(
        "--review-width",
        type=int,
        default=DEFAULT_REVIEW_WIDTH,
        help="Width of the motion-review MP4.",
    )
    parser.add_argument(
        "--smoothing-window",
        type=int,
        default=DEFAULT_SMOOTHING_WINDOW,
        help="Odd Savitzky-Golay camera-trajectory window.",
    )
    parser.add_argument(
        "--extra-checkpoint-frames",
        type=int,
        nargs="*",
        default=DEFAULT_EXTRA_CHECKPOINT_FRAMES,
        help=(
            "Additional frame indices to save as full-resolution "
            "checkpoint overlays."
        ),
    )
    args = parser.parse_args(argv)

    if args.sample_count < 3:
        parser.error("--sample-count must be at least 3")

    if args.max_features < 1000:
        parser.error("--max-features must be at least 1000")

    if args.review_width < 640:
        parser.error("--review-width must be at least 640")

    if args.smoothing_window < 3 or args.smoothing_window % 2 == 0:
        parser.error("--smoothing-window must be an odd integer >= 3")

    return args


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Required JSON file not found: {path}")

    with path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def open_video(path):
    if not path.exists():
        raise FileNotFoundError(f"Source video not found: {path}")

    capture = cv2.VideoCapture(str(path))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open source video: {path}")

    metadata = {
        "fps": float(capture.get(cv2.CAP_PROP_FPS)),
        "frame_count": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }

    if (
        metadata["fps"] <= 0
        or metadata["frame_count"] <= 0
        or metadata["width"] <= 0
        or metadata["height"] <= 0
    ):
        capture.release()
        raise ValueError(f"Invalid video metadata: {metadata}")

    return capture, metadata


def validate_inputs(metadata, calibration, court_config):
    calibration_metadata = calibration["video_metadata"]
    expected = (
        int(calibration_metadata["width"]),
        int(calibration_metadata["height"]),
        int(calibration_metadata["frame_count"]),
    )
    actual = (
        metadata["width"],
        metadata["height"],
        metadata["frame_count"],
    )

    if expected != actual:
        raise ValueError(
            "Final calibration video metadata does not match the "
            f"source video: calibration={expected}, video={actual}"
        )

    polygon_size = (
        int(court_config["video_width"]),
        int(court_config["video_height"]),
    )

    if polygon_size != actual[:2]:
        raise ValueError(
            "Court polygon dimensions do not match the video: "
            f"polygon={polygon_size}, video={actual[:2]}"
        )

    if calibration.get("status") != "reference_fit_reviewed":
        raise ValueError(
            "Calibration must have status 'reference_fit_reviewed' "
            "before camera-motion propagation."
        )


def parse_polygon(court_config):
    points = []

    for index, point in enumerate(court_config["polygon"]):
        try:
            points.append([int(point["x"]), int(point["y"])])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                f"Invalid court polygon point {index}: {point!r}"
            ) from error

    if len(points) < 3:
        raise ValueError("Court polygon needs at least three points")

    return np.asarray(points, dtype=np.int32)


def build_feature_mask(height, width, polygon):
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(mask, [polygon], 255)

    # Ignore a thin border, where broadcast graphics and partial
    # features are more likely to create unstable correspondences.
    border = 12
    mask[:border, :] = 0
    mask[-border:, :] = 0
    mask[:, :border] = 0
    mask[:, -border:] = 0
    return mask


def read_exact_frame(capture, frame_index):
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    success, frame = capture.read()
    decoded_index = int(capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1

    if not success or decoded_index != frame_index:
        raise RuntimeError(
            "Could not decode exact frame: "
            f"requested={frame_index}, decoded={decoded_index}"
        )

    return frame


def create_orb(max_features):
    return cv2.ORB_create(
        nfeatures=max_features,
        scaleFactor=1.2,
        nlevels=8,
        edgeThreshold=19,
        fastThreshold=12,
    )


def detect_features(detector, frame, mask):
    grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    keypoints, descriptors = detector.detectAndCompute(
        grayscale,
        mask,
    )
    return keypoints, descriptors


def ratio_matches(source_descriptors, target_descriptors):
    if source_descriptors is None or target_descriptors is None:
        return []

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    candidates = matcher.knnMatch(
        source_descriptors,
        target_descriptors,
        k=2,
    )
    return [
        first
        for pair in candidates
        if len(pair) == 2
        for first, second in [pair]
        if first.distance < LOWE_RATIO * second.distance
    ]


def normalize_homography(homography):
    if homography is None:
        return None

    scale = float(homography[2, 2])

    if abs(scale) < 1e-12:
        return None

    normalized = homography.astype(np.float64) / scale

    if not np.all(np.isfinite(normalized)):
        return None

    return normalized


def project_points(points, homography):
    array = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    homogeneous = np.column_stack(
        [array, np.ones(len(array), dtype=np.float64)]
    )
    projected = homogeneous @ np.asarray(
        homography,
        dtype=np.float64,
    ).T

    with np.errstate(divide="ignore", invalid="ignore"):
        return projected[:, :2] / projected[:, 2:3]


def polygon_area(points):
    array = np.asarray(points, dtype=np.float32)
    return abs(float(cv2.contourArea(array)))


def estimate_transform(
    source_keypoints,
    source_descriptors,
    target_keypoints,
    target_descriptors,
    source_polygon,
):
    matches = ratio_matches(
        source_descriptors,
        target_descriptors,
    )
    result = {
        "ratio_match_count": len(matches),
        "inlier_count": 0,
        "inlier_ratio": 0.0,
        "median_reprojection_error_px": None,
        "p90_reprojection_error_px": None,
        "projected_polygon_area_ratio": None,
        "valid": False,
        "failure_reason": None,
    }

    if len(matches) < MIN_RATIO_MATCHES:
        result["failure_reason"] = "insufficient_ratio_matches"
        return None, result

    source_points = np.float32(
        [source_keypoints[match.queryIdx].pt for match in matches]
    )
    target_points = np.float32(
        [target_keypoints[match.trainIdx].pt for match in matches]
    )
    homography, inlier_mask = cv2.findHomography(
        source_points,
        target_points,
        cv2.RANSAC,
        RANSAC_THRESHOLD_PX,
        maxIters=4000,
        confidence=0.995,
    )
    homography = normalize_homography(homography)

    if homography is None or inlier_mask is None:
        result["failure_reason"] = "homography_failed"
        return None, result

    inliers = inlier_mask.ravel().astype(bool)
    inlier_count = int(np.count_nonzero(inliers))
    inlier_ratio = inlier_count / len(matches)
    result["inlier_count"] = inlier_count
    result["inlier_ratio"] = round(float(inlier_ratio), 6)

    if inlier_count < MIN_INLIERS:
        result["failure_reason"] = "insufficient_inliers"
        return None, result

    if inlier_ratio < MIN_INLIER_RATIO:
        result["failure_reason"] = "low_inlier_ratio"
        return None, result

    projected_matches = project_points(source_points[inliers], homography)
    errors = np.linalg.norm(
        projected_matches - target_points[inliers],
        axis=1,
    )
    median_error = float(np.median(errors))
    p90_error = float(np.percentile(errors, 90))
    result["median_reprojection_error_px"] = round(median_error, 4)
    result["p90_reprojection_error_px"] = round(p90_error, 4)

    if median_error > MAX_MEDIAN_REPROJECTION_ERROR_PX:
        result["failure_reason"] = "high_reprojection_error"
        return None, result

    projected_polygon = project_points(source_polygon, homography)

    if not np.all(np.isfinite(projected_polygon)):
        result["failure_reason"] = "non_finite_projection"
        return None, result

    source_area = polygon_area(source_polygon)
    projected_area = polygon_area(projected_polygon)

    if source_area <= 0:
        raise ValueError("Court feature polygon has zero area")

    area_ratio = projected_area / source_area
    result["projected_polygon_area_ratio"] = round(area_ratio, 6)

    if not 0.35 <= area_ratio <= 2.8:
        result["failure_reason"] = "implausible_projected_area"
        return None, result

    result["valid"] = True
    return homography, result


def identity_transform_metrics(feature_count):
    return {
        "ratio_match_count": feature_count,
        "inlier_count": feature_count,
        "inlier_ratio": 1.0,
        "median_reprojection_error_px": 0.0,
        "p90_reprojection_error_px": 0.0,
        "projected_polygon_area_ratio": 1.0,
        "valid": True,
        "failure_reason": None,
    }


def estimate_all_camera_transforms(
    video_path,
    metadata,
    reference_frame_index,
    feature_mask,
    polygon,
    max_features,
):
    cv2.setRNGSeed(0)
    detector = create_orb(max_features)
    reference_capture, _ = open_video(video_path)

    try:
        reference_frame = read_exact_frame(
            reference_capture,
            reference_frame_index,
        )
    finally:
        reference_capture.release()

    reference_keypoints, reference_descriptors = detect_features(
        detector,
        reference_frame,
        feature_mask,
    )

    if reference_descriptors is None or len(reference_keypoints) < MIN_INLIERS:
        raise RuntimeError(
            "Reference frame did not produce enough ORB features"
        )

    capture, _ = open_video(video_path)
    transforms = []
    frame_records = []
    previous_keypoints = None
    previous_descriptors = None
    previous_to_reference = None
    previous_fallback_chain = 0

    print("Estimating per-frame camera motion...")

    try:
        for frame_index in range(metadata["frame_count"]):
            success, frame = capture.read()

            if not success:
                break

            keypoints, descriptors = detect_features(
                detector,
                frame,
                feature_mask,
            )
            feature_count = len(keypoints)
            record = {
                "frame_index": frame_index,
                "timestamp_sec": round(
                    frame_index / metadata["fps"],
                    6,
                ),
                "feature_count": feature_count,
                "method": None,
                "fallback_chain_length": 0,
                "direct_match": None,
                "fallback_match": None,
                "raw_transform_valid": False,
            }
            transform = None

            if frame_index == reference_frame_index:
                transform = np.eye(3, dtype=np.float64)
                record["method"] = "reference_identity"
                record["direct_match"] = identity_transform_metrics(
                    feature_count
                )
            else:
                direct_transform, direct_metrics = estimate_transform(
                    keypoints,
                    descriptors,
                    reference_keypoints,
                    reference_descriptors,
                    polygon,
                )
                record["direct_match"] = direct_metrics

                if direct_transform is not None:
                    transform = direct_transform
                    record["method"] = "direct_to_reference"
                elif (
                    previous_keypoints is not None
                    and previous_to_reference is not None
                    and previous_fallback_chain < MAX_FALLBACK_CHAIN
                ):
                    current_to_previous, fallback_metrics = (
                        estimate_transform(
                            keypoints,
                            descriptors,
                            previous_keypoints,
                            previous_descriptors,
                            polygon,
                        )
                    )
                    record["fallback_match"] = fallback_metrics

                    if current_to_previous is not None:
                        transform = normalize_homography(
                            previous_to_reference
                            @ current_to_previous
                        )
                        record["fallback_chain_length"] = (
                            previous_fallback_chain + 1
                        )
                        record["method"] = "sequential_fallback"

            if transform is None:
                record["method"] = "unresolved"
                transforms.append(None)
                previous_to_reference = None
                previous_fallback_chain = 0
            else:
                record["raw_transform_valid"] = True
                transforms.append(transform)
                previous_to_reference = transform
                previous_fallback_chain = record[
                    "fallback_chain_length"
                ]

            frame_records.append(record)
            previous_keypoints = keypoints
            previous_descriptors = descriptors

            if (frame_index + 1) % 50 == 0:
                method_counts = Counter(
                    item["method"] for item in frame_records
                )
                print(
                    f"  Processed {frame_index + 1}/"
                    f"{metadata['frame_count']} frames | "
                    f"direct={method_counts['direct_to_reference']} | "
                    f"fallback={method_counts['sequential_fallback']} | "
                    f"unresolved={method_counts['unresolved']}"
                )
    finally:
        capture.release()

    if len(frame_records) != metadata["frame_count"]:
        raise RuntimeError(
            "Video decode ended early during camera tracking: "
            f"decoded={len(frame_records)}, "
            f"expected={metadata['frame_count']}"
        )

    return transforms, frame_records


def image_corners(width, height):
    return np.asarray(
        [
            [0.0, 0.0],
            [width - 1.0, 0.0],
            [width - 1.0, height - 1.0],
            [0.0, height - 1.0],
        ],
        dtype=np.float32,
    )


def interpolate_missing(values, valid_mask):
    frame_indices = np.arange(len(values), dtype=float)
    valid_indices = frame_indices[valid_mask]

    if len(valid_indices) < 2:
        raise RuntimeError(
            "Fewer than two valid camera transforms are available"
        )

    output = values.copy()

    for column in range(values.shape[1]):
        output[:, column] = np.interp(
            frame_indices,
            valid_indices,
            values[valid_mask, column],
        )

    return output


def centered_median_filter(values, window_length):
    if window_length < 1 or window_length % 2 == 0:
        raise ValueError("Median-filter window must be a positive odd integer")

    radius = window_length // 2
    output = np.empty_like(values)
    padding = [(radius, radius)] + [
        (0, 0) for _ in range(values.ndim - 1)
    ]
    padded = np.pad(values, padding, mode="edge")

    for index in range(len(values)):
        output[index] = np.median(
            padded[index : index + window_length],
            axis=0,
        )

    return output


def effective_odd_window(requested_window, frame_count):
    effective_window = min(requested_window, frame_count)

    if effective_window % 2 == 0:
        effective_window -= 1

    return max(1, effective_window)


def numeric_distribution(values):
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]

    if not len(finite):
        return {
            "minimum": None,
            "median": None,
            "p90": None,
            "p99": None,
            "maximum": None,
        }

    return {
        "minimum": round(float(np.min(finite)), 4),
        "median": round(float(np.median(finite)), 4),
        "p90": round(float(np.percentile(finite, 90)), 4),
        "p99": round(float(np.percentile(finite, 99)), 4),
        "maximum": round(float(np.max(finite)), 4),
    }


def control_trajectories_from_transforms(transforms, control_points):
    trajectories = np.full(
        (len(transforms), len(control_points), 2),
        np.nan,
        dtype=float,
    )
    normalized_denominators = np.full(
        (len(transforms), len(control_points)),
        np.nan,
        dtype=float,
    )
    valid_mask = np.zeros(len(transforms), dtype=bool)
    homogeneous = np.column_stack(
        [
            np.asarray(control_points, dtype=np.float64),
            np.ones(len(control_points), dtype=np.float64),
        ]
    )

    for index, transform in enumerate(transforms):
        if transform is None:
            continue

        try:
            reference_to_frame = np.linalg.inv(transform)
        except np.linalg.LinAlgError:
            continue

        projected = homogeneous @ reference_to_frame.T
        denominators = projected[:, 2]
        denominator_scale = float(np.max(np.abs(denominators)))

        if denominator_scale < 1e-12:
            continue

        with np.errstate(divide="ignore", invalid="ignore"):
            points = projected[:, :2] / denominators[:, None]

        if not np.all(np.isfinite(points)):
            continue

        trajectories[index] = points
        normalized_denominators[index] = (
            denominators / denominator_scale
        )
        valid_mask[index] = True

    return trajectories, normalized_denominators, valid_mask


def fit_transforms_from_control_trajectory(
    trajectory,
    control_points,
    reference_frame_index,
):
    if cv2 is None:
        raise ModuleNotFoundError(
            "OpenCV is required to fit smoothed camera transforms."
        )

    smoothed_transforms = []

    for index, frame_control_points in enumerate(trajectory):
        transform, _ = cv2.findHomography(
            np.asarray(frame_control_points, dtype=np.float32),
            np.asarray(control_points, dtype=np.float32),
            method=0,
        )
        transform = normalize_homography(transform)

        if transform is None:
            raise RuntimeError(
                f"Smoothed transform invalid at frame {index}"
            )

        smoothed_transforms.append(transform)

    reference_adjustment = normalize_homography(
        np.linalg.inv(smoothed_transforms[reference_frame_index])
    )

    if reference_adjustment is None:
        raise RuntimeError("Could not re-anchor smoothed camera trajectory")

    smoothed_transforms = [
        normalize_homography(reference_adjustment @ transform)
        for transform in smoothed_transforms
    ]

    if any(transform is None for transform in smoothed_transforms):
        raise RuntimeError("Re-anchored camera trajectory is invalid")

    return smoothed_transforms


def _geometry_issue(code, frame_indices, message):
    return {
        "code": code,
        "frame_count": len(frame_indices),
        "sample_frames": [int(value) for value in frame_indices[:20]],
        "message": message,
    }


def validate_smoothed_camera_geometry(
    transforms,
    width,
    height,
    reference_control_points,
    reference_frame_index,
):
    control_points = np.asarray(
        reference_control_points,
        dtype=np.float64,
    )
    trajectories, denominators, valid_mask = (
        control_trajectories_from_transforms(
            transforms,
            control_points,
        )
    )
    frame_count = len(transforms)
    issues = []
    invalid_frames = np.flatnonzero(~valid_mask).tolist()

    if invalid_frames:
        issues.append(
            _geometry_issue(
                "non_finite_control_projection",
                invalid_frames,
                "One or more reviewed control points could not be projected.",
            )
        )

    valid_denominators = denominators[valid_mask]
    crossing_frames = []
    low_margin_frames = []

    for frame_index in np.flatnonzero(valid_mask):
        row = denominators[frame_index]

        if float(np.min(row)) < 0.0 < float(np.max(row)):
            crossing_frames.append(int(frame_index))

        if (
            float(np.min(np.abs(row)))
            < MIN_NORMALIZED_PROJECTION_DENOMINATOR
        ):
            low_margin_frames.append(int(frame_index))

    if crossing_frames:
        issues.append(
            _geometry_issue(
                "vanishing_line_crosses_control_region",
                crossing_frames,
                "The projective vanishing line crosses the reviewed control region.",
            )
        )

    if low_margin_frames:
        issues.append(
            _geometry_issue(
                "near_singular_control_projection",
                low_margin_frames,
                "A control point approaches a projective singularity.",
            )
        )

    finite_trajectory = trajectories[valid_mask]
    absolute_limit = (
        MAX_ABSOLUTE_CONTROL_COORDINATE_FRAME_MULTIPLIER
        * max(width, height)
    )
    excessive_coordinate_frames = []
    collapsed_span_frames = []
    excessive_span_frames = []
    spans = np.empty((0, 2), dtype=float)

    if len(finite_trajectory):
        per_frame_absolute = np.max(
            np.abs(finite_trajectory),
            axis=(1, 2),
        )
        valid_indices = np.flatnonzero(valid_mask)
        excessive_coordinate_frames = valid_indices[
            per_frame_absolute > absolute_limit
        ].tolist()
        spans = np.ptp(finite_trajectory, axis=1)
        minimum_spans = np.asarray(
            [
                MIN_CONTROL_SPAN_FRAME_FRACTION * width,
                MIN_CONTROL_SPAN_FRAME_FRACTION * height,
            ],
            dtype=float,
        )
        maximum_spans = np.asarray(
            [
                MAX_CONTROL_SPAN_FRAME_MULTIPLIER * width,
                MAX_CONTROL_SPAN_FRAME_MULTIPLIER * height,
            ],
            dtype=float,
        )
        collapsed_span_frames = valid_indices[
            np.any(spans < minimum_spans, axis=1)
        ].tolist()
        excessive_span_frames = valid_indices[
            np.any(spans > maximum_spans, axis=1)
        ].tolist()

    if excessive_coordinate_frames:
        issues.append(
            _geometry_issue(
                "control_region_leaves_safe_image_extent",
                excessive_coordinate_frames,
                "The smoothed control region diverges far beyond the image.",
            )
        )

    if collapsed_span_frames:
        issues.append(
            _geometry_issue(
                "control_region_collapses",
                collapsed_span_frames,
                "The smoothed control region collapses toward a line or point.",
            )
        )

    if excessive_span_frames:
        issues.append(
            _geometry_issue(
                "control_region_expands_excessively",
                excessive_span_frames,
                "The smoothed control region expands beyond a safe image extent.",
            )
        )

    steps = np.full((max(0, frame_count - 1), len(control_points)), np.nan)
    accelerations = np.full(
        (max(0, frame_count - 2), len(control_points)),
        np.nan,
    )

    if frame_count >= 2:
        steps = np.linalg.norm(np.diff(trajectories, axis=0), axis=2)

    if frame_count >= 3:
        accelerations = np.linalg.norm(
            np.diff(trajectories, n=2, axis=0),
            axis=2,
        )

    image_diagonal = float(np.hypot(width, height))
    step_limit = MAX_CONTROL_STEP_DIAGONAL_FRACTION * image_diagonal
    acceleration_limit = (
        MAX_CONTROL_ACCELERATION_DIAGONAL_FRACTION * image_diagonal
    )
    excessive_step_frames = (
        np.flatnonzero(np.any(steps > step_limit, axis=1)) + 1
    ).tolist()
    excessive_acceleration_frames = (
        np.flatnonzero(
            np.any(accelerations > acceleration_limit, axis=1)
        )
        + 2
    ).tolist()

    if excessive_step_frames:
        issues.append(
            _geometry_issue(
                "implausible_control_point_step",
                excessive_step_frames,
                "The smoothed camera path contains an implausible one-frame step.",
            )
        )

    if excessive_acceleration_frames:
        issues.append(
            _geometry_issue(
                "implausible_control_point_acceleration",
                excessive_acceleration_frames,
                "The smoothed camera path contains an implausible acceleration spike.",
            )
        )

    anchor_error = None

    if valid_mask[reference_frame_index]:
        anchor_error = float(
            np.max(
                np.linalg.norm(
                    trajectories[reference_frame_index] - control_points,
                    axis=1,
                )
            )
        )

        if anchor_error > MAX_REFERENCE_ANCHOR_ERROR_PX:
            issues.append(
                _geometry_issue(
                    "reference_frame_not_anchored",
                    [reference_frame_index],
                    "The reviewed reference frame no longer maps to itself.",
                )
            )

    minimum_denominator_margin = (
        np.min(np.abs(valid_denominators), axis=1)
        if len(valid_denominators)
        else np.asarray([], dtype=float)
    )

    return {
        "status": "passed" if not issues else "failed",
        "issue_count": len(issues),
        "issues": issues,
        "thresholds": {
            "minimum_normalized_projection_denominator": (
                MIN_NORMALIZED_PROJECTION_DENOMINATOR
            ),
            "maximum_absolute_control_coordinate_px": round(
                float(absolute_limit),
                4,
            ),
            "minimum_control_span_px": {
                "x": round(MIN_CONTROL_SPAN_FRAME_FRACTION * width, 4),
                "y": round(MIN_CONTROL_SPAN_FRAME_FRACTION * height, 4),
            },
            "maximum_control_span_px": {
                "x": round(MAX_CONTROL_SPAN_FRAME_MULTIPLIER * width, 4),
                "y": round(MAX_CONTROL_SPAN_FRAME_MULTIPLIER * height, 4),
            },
            "maximum_control_point_step_px": round(step_limit, 4),
            "maximum_control_point_acceleration_px": round(
                acceleration_limit,
                4,
            ),
            "maximum_reference_anchor_error_px": (
                MAX_REFERENCE_ANCHOR_ERROR_PX
            ),
        },
        "metrics": {
            "valid_frame_count": int(np.count_nonzero(valid_mask)),
            "invalid_frame_count": int(frame_count - np.count_nonzero(valid_mask)),
            "control_coordinate_absolute_px": numeric_distribution(
                np.abs(finite_trajectory).reshape(-1)
                if len(finite_trajectory)
                else []
            ),
            "control_span_x_px": numeric_distribution(
                spans[:, 0] if len(spans) else []
            ),
            "control_span_y_px": numeric_distribution(
                spans[:, 1] if len(spans) else []
            ),
            "control_point_step_px": numeric_distribution(steps.reshape(-1)),
            "control_point_acceleration_px": numeric_distribution(
                accelerations.reshape(-1)
            ),
            "normalized_projection_denominator_margin": (
                numeric_distribution(minimum_denominator_margin)
            ),
            "vanishing_line_crossing_frame_count": len(crossing_frames),
            "reference_anchor_maximum_error_px": (
                None if anchor_error is None else round(anchor_error, 6)
            ),
        },
    }


def build_geometry_safe_fallback_trajectory(
    trajectories,
    valid_mask,
    requested_smoothing_window,
    reference_frame_index,
):
    flattened = np.asarray(trajectories, dtype=float).reshape(
        len(trajectories),
        -1,
    )
    filled = interpolate_missing(flattened, valid_mask)
    median_window = effective_odd_window(
        GEOMETRY_FALLBACK_MEDIAN_WINDOW,
        len(flattened),
    )
    local_median = centered_median_filter(filled, median_window)
    differences = (flattened - local_median).reshape(
        len(flattened),
        -1,
        2,
    )
    point_residuals = np.linalg.norm(differences, axis=2)
    median_residuals = np.full(len(flattened), np.nan, dtype=float)
    maximum_residuals = np.full(len(flattened), np.nan, dtype=float)
    median_residuals[valid_mask] = np.median(
        point_residuals[valid_mask],
        axis=1,
    )
    maximum_residuals[valid_mask] = np.max(
        point_residuals[valid_mask],
        axis=1,
    )
    accepted_mask = (
        valid_mask
        & (median_residuals <= MAX_ROBUST_MEDIAN_RESIDUAL_PX)
        & (maximum_residuals <= MAX_ROBUST_POINT_RESIDUAL_PX)
    )
    accepted_mask[reference_frame_index] = valid_mask[
        reference_frame_index
    ]
    cleaned = filled.copy()
    cleaned[~accepted_mask] = local_median[~accepted_mask]
    median_filtered = centered_median_filter(cleaned, 3)
    smoothing_window = effective_odd_window(
        max(
            requested_smoothing_window,
            GEOMETRY_FALLBACK_SAVGOL_WINDOW,
        ),
        len(flattened),
    )

    if savgol_filter is not None and smoothing_window >= 3:
        smoothed = savgol_filter(
            median_filtered,
            window_length=smoothing_window,
            polyorder=2,
            axis=0,
            mode="interp",
        )
        method = (
            f"geometry_safe_local_median_{median_window}_"
            f"plus_median_3_plus_savgol_{smoothing_window}"
        )
    else:
        smoothed = centered_median_filter(
            median_filtered,
            smoothing_window,
        )
        method = (
            f"geometry_safe_local_median_{median_window}_"
            f"plus_stacked_centered_median_{smoothing_window}"
        )

    return (
        smoothed.reshape(np.asarray(trajectories).shape),
        accepted_mask,
        median_residuals,
        maximum_residuals,
        {
            "method": method,
            "median_window_length": median_window,
            "smoothing_window_length": smoothing_window,
        },
    )


def transform_quality_weights(frame_records):
    weights = np.zeros(len(frame_records), dtype=float)

    for index, record in enumerate(frame_records):
        if record["method"] == "reference_identity":
            weights[index] = 1.0
            continue

        if record["method"] != "direct_to_reference":
            weights[index] = 0.1
            continue

        metrics = record.get("direct_match") or {}
        inlier_weight = min(
            1.0,
            float(metrics.get("inlier_count", 0)) / 60.0,
        )
        ratio_weight = min(
            1.0,
            float(metrics.get("inlier_ratio", 0.0)) / 0.5,
        )
        weights[index] = max(
            0.02,
            inlier_weight * ratio_weight,
        )

    return weights


def fit_local_robust_baseline(
    trajectories,
    quality_weights,
    radius,
    accepted_mask=None,
):
    frame_count = len(trajectories)
    baseline = np.full_like(trajectories, np.nan, dtype=float)

    for target_index in range(frame_count):
        start = max(0, target_index - radius)
        end = min(frame_count, target_index + radius + 1)
        indices = np.arange(start, end)
        valid = np.all(np.isfinite(trajectories[indices]), axis=1)

        if accepted_mask is not None:
            valid &= accepted_mask[indices]

        indices = indices[valid]

        if len(indices) < 3:
            continue

        relative_time = (indices - target_index) / float(radius)
        degree = min(2, len(indices) - 1)
        design = np.column_stack(
            [relative_time**power for power in range(degree + 1)]
        )
        observations = trajectories[indices]
        weights = np.maximum(
            0.03,
            quality_weights[indices],
        )
        coefficients = None

        for _ in range(10):
            sqrt_weights = np.sqrt(weights)
            coefficients = np.linalg.lstsq(
                design * sqrt_weights[:, None],
                observations * sqrt_weights[:, None],
                rcond=None,
            )[0]
            predicted = design @ coefficients
            residual_vectors = (
                observations - predicted
            ).reshape(len(indices), -1, 2)
            residuals = np.median(
                np.linalg.norm(residual_vectors, axis=2),
                axis=1,
            )
            residual_median = float(np.median(residuals))
            residual_mad = 1.4826 * float(
                np.median(np.abs(residuals - residual_median))
            )
            cutoff = max(
                5.0,
                residual_median
                + 2.5 * max(residual_mad, 0.5),
            )
            normalized = residuals / cutoff
            robust_weights = np.where(
                normalized < 1.0,
                (1.0 - normalized**2) ** 2,
                0.005,
            )
            weights = (
                np.maximum(0.02, quality_weights[indices])
                * robust_weights
            )

        baseline[target_index] = coefficients[0]

    return baseline


def contiguous_false_runs(mask):
    runs = []
    start = None

    for index, accepted in enumerate(mask):
        if not accepted and start is None:
            start = index

        if start is not None and (
            accepted or index == len(mask) - 1
        ):
            end = index if not accepted else index - 1
            runs.append(
                {
                    "start_frame": int(start),
                    "end_frame": int(end),
                    "frame_count": int(end - start + 1),
                }
            )
            start = None

    return runs


def stabilize_terminal_trajectory(
    smoothed,
    accepted_mask,
    reference_frame_index,
):
    """Prevent unreliable end-of-clip samples from bending the trajectory.

    A centered smoother has no future observations at the right edge. When a
    sustained run of rejected raw transforms begins near the end, later small
    islands of falsely accepted transforms can bend the fitted homography well
    before the final frame. Search the tail for the first sufficiently long
    rejected run whose remaining suffix is dominated by rejected transforms,
    then hold the last reliable pre-run transform through the end of the clip.
    """
    frame_count = len(smoothed)
    search_start = max(
        reference_frame_index + 1,
        frame_count - TERMINAL_SEARCH_FRAME_COUNT,
    )
    summary = {
        "applied": False,
        "method": "last_reliable_anchor_hold",
        "start_frame": None,
        "end_frame": None,
        "search_start_frame": int(search_start),
        "search_frame_count": int(frame_count - search_start),
        "required_consecutive_rejected_frames": (
            TERMINAL_REJECTED_RUN_TRIGGER
        ),
        "required_rejected_suffix_fraction": (
            TERMINAL_MIN_REJECTED_SUFFIX_FRACTION
        ),
        "trigger_run_frame_count": None,
        "trigger_suffix_frame_count": None,
        "trigger_suffix_rejected_frame_count": None,
        "trigger_suffix_rejected_fraction": None,
    }

    run_start = None
    terminal_start = None

    for frame_index in range(search_start, frame_count):
        if accepted_mask[frame_index]:
            run_start = None
            continue

        if run_start is None:
            run_start = frame_index

        run_length = frame_index - run_start + 1

        if run_length < TERMINAL_REJECTED_RUN_TRIGGER:
            continue

        suffix = accepted_mask[run_start:]
        suffix_frame_count = len(suffix)
        suffix_rejected_count = int(np.count_nonzero(~suffix))
        suffix_rejected_fraction = (
            suffix_rejected_count / float(suffix_frame_count)
        )

        if (
            suffix_rejected_fraction
            < TERMINAL_MIN_REJECTED_SUFFIX_FRACTION
        ):
            continue

        terminal_start = run_start
        summary.update(
            {
                "trigger_run_frame_count": int(run_length),
                "trigger_suffix_frame_count": int(suffix_frame_count),
                "trigger_suffix_rejected_frame_count": int(
                    suffix_rejected_count
                ),
                "trigger_suffix_rejected_fraction": round(
                    float(suffix_rejected_fraction),
                    4,
                ),
            }
        )
        break

    if terminal_start is None:
        return smoothed, summary

    anchor_index = terminal_start - 1
    stabilized = smoothed.copy()
    stabilized[terminal_start:] = stabilized[anchor_index]

    summary.update(
        {
            "applied": True,
            "start_frame": int(terminal_start),
            "end_frame": int(frame_count - 1),
            "anchor_frame": int(anchor_index),
        }
    )
    return stabilized, summary


def smooth_camera_transforms(
    transforms,
    width,
    height,
    smoothing_window,
    reference_frame_index,
    reference_control_points,
    frame_records,
):
    control_points = np.asarray(
        reference_control_points,
        dtype=np.float32,
    )

    if len(control_points) < 4:
        raise ValueError(
            "At least four reviewed reference control points are "
            "required for robust camera smoothing"
        )

    control_trajectories, _, valid_mask = (
        control_trajectories_from_transforms(
            transforms,
            control_points,
        )
    )
    trajectories = control_trajectories.reshape(len(transforms), -1)

    quality_weights = transform_quality_weights(frame_records)
    first_baseline = fit_local_robust_baseline(
        trajectories,
        quality_weights,
        ROBUST_BASELINE_RADIUS,
    )
    baseline_differences = (
        trajectories - first_baseline
    ).reshape(len(transforms), -1, 2)
    point_residuals = np.linalg.norm(
        baseline_differences,
        axis=2,
    )
    median_residuals = np.full(len(transforms), np.nan, dtype=float)
    maximum_residuals = np.full(len(transforms), np.nan, dtype=float)
    finite_residual_rows = np.all(np.isfinite(point_residuals), axis=1)
    median_residuals[finite_residual_rows] = np.median(
        point_residuals[finite_residual_rows],
        axis=1,
    )
    maximum_residuals[finite_residual_rows] = np.max(
        point_residuals[finite_residual_rows],
        axis=1,
    )
    accepted_mask = (
        valid_mask
        & (median_residuals <= MAX_ROBUST_MEDIAN_RESIDUAL_PX)
        & (maximum_residuals <= MAX_ROBUST_POINT_RESIDUAL_PX)
    )
    accepted_mask[reference_frame_index] = valid_mask[
        reference_frame_index
    ]
    second_baseline = fit_local_robust_baseline(
        trajectories,
        quality_weights,
        ROBUST_REFIT_RADIUS,
        accepted_mask=accepted_mask,
    )
    cleaned = trajectories.copy()
    cleaned[~accepted_mask] = second_baseline[~accepted_mask]

    if not np.all(np.isfinite(cleaned)):
        cleaned = interpolate_missing(
            cleaned,
            np.all(np.isfinite(cleaned), axis=1),
        )

    median_filtered = centered_median_filter(cleaned, 3)
    effective_window = effective_odd_window(
        smoothing_window,
        len(transforms),
    )

    if savgol_filter is not None and effective_window >= 3:
        smoothed = savgol_filter(
            median_filtered,
            window_length=effective_window,
            polyorder=2,
            axis=0,
            mode="interp",
        )
        smoothing_method = (
            "bidirectional_robust_quadratic_"
            "plus_median_3_plus_savgol"
        )
    else:
        smoothed = centered_median_filter(
            median_filtered,
            effective_window,
        )
        smoothing_method = "stacked_centered_median"

    smoothed, terminal_stabilization = stabilize_terminal_trajectory(
        smoothed,
        accepted_mask,
        reference_frame_index,
    )

    if terminal_stabilization["applied"]:
        smoothing_method += "_plus_terminal_anchor_hold"

    primary_trajectory = smoothed.reshape(control_trajectories.shape)

    try:
        smoothed_transforms = fit_transforms_from_control_trajectory(
            primary_trajectory,
            control_points,
            reference_frame_index,
        )
        primary_geometry_validation = (
            validate_smoothed_camera_geometry(
                smoothed_transforms,
                width,
                height,
                control_points,
                reference_frame_index,
            )
        )
    except (RuntimeError, ValueError, np.linalg.LinAlgError) as error:
        smoothed_transforms = None
        primary_geometry_validation = {
            "status": "failed",
            "issue_count": 1,
            "issues": [
                {
                    "code": "smoothed_homography_fit_failed",
                    "frame_count": None,
                    "sample_frames": [],
                    "message": str(error),
                }
            ],
            "thresholds": {},
            "metrics": {},
        }

    geometry_fallback = {
        "applied": False,
        "triggered_by_issue_codes": [],
        "method": None,
        "median_window_length": None,
        "smoothing_window_length": None,
    }
    geometry_validation = primary_geometry_validation
    residual_reference = "bidirectional_robust_quadratic"

    if primary_geometry_validation["status"] != "passed":
        (
            fallback_trajectory,
            accepted_mask,
            median_residuals,
            maximum_residuals,
            fallback_summary,
        ) = build_geometry_safe_fallback_trajectory(
            control_trajectories,
            valid_mask,
            smoothing_window,
            reference_frame_index,
        )
        fallback_trajectory, terminal_stabilization = (
            stabilize_terminal_trajectory(
                fallback_trajectory,
                accepted_mask,
                reference_frame_index,
            )
        )

        if terminal_stabilization["applied"]:
            fallback_summary["method"] += (
                "_plus_terminal_anchor_hold"
            )

        smoothed_transforms = fit_transforms_from_control_trajectory(
            fallback_trajectory,
            control_points,
            reference_frame_index,
        )
        geometry_validation = validate_smoothed_camera_geometry(
            smoothed_transforms,
            width,
            height,
            control_points,
            reference_frame_index,
        )
        geometry_fallback = {
            "applied": True,
            "triggered_by_issue_codes": [
                issue["code"]
                for issue in primary_geometry_validation["issues"]
            ],
            **fallback_summary,
        }
        smoothing_method = fallback_summary["method"]
        effective_window = fallback_summary[
            "smoothing_window_length"
        ]
        residual_reference = (
            f"local_median_{fallback_summary['median_window_length']}"
        )

    if geometry_validation["status"] != "passed":
        issue_codes = [
            issue["code"] for issue in geometry_validation["issues"]
        ]
        raise RuntimeError(
            "Camera smoothing failed geometry validation after the "
            "geometry-safe fallback; coordinate export is blocked. "
            f"Issues: {issue_codes}"
        )

    center = np.asarray(
        [[width / 2.0, height / 2.0]],
        dtype=np.float32,
    )
    raw_to_smoothed_center_delta = []

    for index, transform in enumerate(smoothed_transforms):
        if transforms[index] is None:
            raw_to_smoothed_center_delta.append(None)
        else:
            raw_center = project_points(center, transforms[index])[0]
            smooth_center = project_points(center, transform)[0]
            raw_to_smoothed_center_delta.append(
                round(
                    float(np.linalg.norm(raw_center - smooth_center)),
                    4,
                )
            )

    smoothing_summary = {
        "method": smoothing_method,
        "window_length": effective_window,
        "raw_valid_frame_count": int(np.count_nonzero(valid_mask)),
        "raw_unresolved_frame_count": int(
            len(valid_mask) - np.count_nonzero(valid_mask)
        ),
        "robust_accepted_frame_count": int(
            np.count_nonzero(accepted_mask)
        ),
        "robust_replaced_frame_count": int(
            len(accepted_mask) - np.count_nonzero(accepted_mask)
        ),
        "robust_replaced_frame_runs": contiguous_false_runs(
            accepted_mask
        ),
        "robust_residual_thresholds_px": {
            "median_control_point": (
                MAX_ROBUST_MEDIAN_RESIDUAL_PX
            ),
            "maximum_control_point": (
                MAX_ROBUST_POINT_RESIDUAL_PX
            ),
        },
        "robust_residual_reference": residual_reference,
        "terminal_stabilization": terminal_stabilization,
        "primary_geometry_validation": primary_geometry_validation,
        "geometry_fallback": geometry_fallback,
        "geometry_validation": geometry_validation,
        "raw_to_robust_baseline_residual_px": {
            "median": round(float(np.nanmedian(median_residuals)), 4),
            "p90": round(
                float(np.nanpercentile(median_residuals, 90)),
                4,
            ),
            "maximum": round(float(np.nanmax(median_residuals)), 4),
        },
        "raw_to_smoothed_center_delta_px": {
            "median": None,
            "p90": None,
            "maximum": None,
        },
    }
    finite_deltas = np.asarray(
        [
            value
            for value in raw_to_smoothed_center_delta
            if value is not None
        ],
        dtype=float,
    )

    if len(finite_deltas):
        smoothing_summary["raw_to_smoothed_center_delta_px"] = {
            "median": round(float(np.median(finite_deltas)), 4),
            "p90": round(float(np.percentile(finite_deltas, 90)), 4),
            "maximum": round(float(np.max(finite_deltas)), 4),
        }

    return (
        smoothed_transforms,
        valid_mask,
        accepted_mask,
        [
            (
                None
                if not np.isfinite(value)
                else round(float(value), 4)
            )
            for value in median_residuals
        ],
        raw_to_smoothed_center_delta,
        smoothing_summary,
    )


def build_court_polylines(court_model):
    width = float(court_model["court_width_ft"])
    half_length = float(court_model["half_court_length_ft"])
    lane_width = float(court_model["lane_width_ft"])
    free_throw_x = float(
        court_model["baseline_to_free_throw_line_ft"]
    )
    basket_x = float(court_model["basket_center_from_baseline_ft"])
    three_radius = float(court_model["three_point_radius_ft"])
    center_y = width / 2.0
    lane_far = (width - lane_width) / 2.0
    lane_near = (width + lane_width) / 2.0
    circle_radius = 6.0
    lines = []
    lines.append(
        np.asarray(
            [
                [0.0, 0.0],
                [half_length, 0.0],
                [half_length, width],
                [0.0, width],
                [0.0, 0.0],
            ],
            dtype=np.float32,
        )
    )
    lines.append(
        np.asarray(
            [
                [0.0, lane_far],
                [free_throw_x, lane_far],
                [free_throw_x, lane_near],
                [0.0, lane_near],
            ],
            dtype=np.float32,
        )
    )
    circle_angles = np.linspace(0.0, 2.0 * np.pi, 181)
    lines.append(
        np.column_stack(
            (
                free_throw_x
                + circle_radius * np.cos(circle_angles),
                center_y + circle_radius * np.sin(circle_angles),
            )
        ).astype(np.float32)
    )
    endpoint_angle = np.arccos(-basket_x / three_radius)
    arc_angles = np.linspace(-endpoint_angle, endpoint_angle, 241)
    lines.append(
        np.column_stack(
            (
                basket_x + three_radius * np.cos(arc_angles),
                center_y + three_radius * np.sin(arc_angles),
            )
        ).astype(np.float32)
    )
    return lines


def transform_status_color(method):
    if method in ("reference_identity", "direct_to_reference"):
        return FIT_REGION_COLOR

    if method == "sequential_fallback":
        return WARNING_COLOR

    return ERROR_COLOR


def draw_model_overlay(
    frame,
    frame_index,
    fps,
    frame_record,
    frame_to_court,
    court_polylines,
    raw_transform_accepted,
    robust_residual,
    smoothing_delta,
):
    overlay = frame.copy()
    court_to_frame = np.linalg.inv(frame_to_court)

    for court_line in court_polylines:
        projected = project_points(court_line, court_to_frame)
        finite = np.all(np.isfinite(projected), axis=1)

        if np.count_nonzero(finite) < 2:
            continue

        points = np.rint(projected[finite]).astype(np.int32)
        cv2.polylines(
            overlay,
            [points],
            isClosed=False,
            color=COURT_MODEL_COLOR,
            thickness=3,
            lineType=cv2.LINE_AA,
        )

    panel = overlay.copy()
    cv2.rectangle(panel, (12, 12), (1370, 112), (0, 0, 0), -1)
    cv2.addWeighted(panel, 0.75, overlay, 0.25, 0, overlay)
    method = frame_record["method"]
    status_color = (
        transform_status_color(method)
        if raw_transform_accepted
        else WARNING_COLOR
    )
    direct = frame_record.get("direct_match") or {}
    robust_text = (
        "n/a" if robust_residual is None else f"{robust_residual:.1f}px"
    )
    raw_status = "kept" if raw_transform_accepted else "replaced"
    cv2.putText(
        overlay,
        (
            f"Frame {frame_index} | {frame_index / fps:.2f}s | "
            "MOVING COURT CALIBRATION"
        ),
        (28, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        TEXT_COLOR,
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        overlay,
        (
            f"camera={method} | direct inliers="
            f"{direct.get('inlier_count', 0)}/"
            f"{direct.get('ratio_match_count', 0)} | "
            f"raw={raw_status} | robust residual={robust_text} | "
            f"smooth delta="
            f"{0.0 if smoothing_delta is None else smoothing_delta:.1f}px"
        ),
        (28, 82),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        status_color,
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        overlay,
        "Judge lane/circles first; bench-side outer boundary is extrapolated",
        (28, 104),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        TEXT_COLOR,
        1,
        cv2.LINE_AA,
    )
    return overlay


def build_sample_indices(frame_count, sample_count, reference_frame):
    last_frame = frame_count - 1
    indices = {
        int(round(index * last_frame / (sample_count - 1)))
        for index in range(sample_count)
    }
    indices.add(reference_frame)
    return sorted(indices)


def render_motion_review(
    video_path,
    output_dir,
    output_video,
    metadata,
    reference_to_court,
    smoothed_frame_to_reference,
    frame_records,
    robust_accepted_mask,
    robust_residuals,
    smoothing_deltas,
    court_polylines,
    sample_indices,
    review_width,
):
    frames_dir = output_dir / "checkpoint_overlays"
    frames_dir.mkdir(parents=True, exist_ok=True)
    output_video.parent.mkdir(parents=True, exist_ok=True)
    review_height = int(
        round(metadata["height"] * review_width / metadata["width"])
    )

    if review_height % 2:
        review_height += 1

    writer = cv2.VideoWriter(
        str(output_video),
        cv2.VideoWriter_fourcc(*"mp4v"),
        metadata["fps"],
        (review_width, review_height),
    )

    if not writer.isOpened():
        raise RuntimeError(
            f"Could not create motion-review video: {output_video}"
        )

    capture, _ = open_video(video_path)
    sample_paths = []
    sample_set = set(sample_indices)
    processed = 0

    print("Rendering moving court-model review...")

    try:
        for frame_index in range(metadata["frame_count"]):
            success, frame = capture.read()

            if not success:
                break

            frame_to_court = normalize_homography(
                reference_to_court
                @ smoothed_frame_to_reference[frame_index]
            )

            if frame_to_court is None:
                raise RuntimeError(
                    f"Frame-to-court composition failed at {frame_index}"
                )

            annotated = draw_model_overlay(
                frame,
                frame_index,
                metadata["fps"],
                frame_records[frame_index],
                frame_to_court,
                court_polylines,
                robust_accepted_mask[frame_index],
                robust_residuals[frame_index],
                smoothing_deltas[frame_index],
            )
            review_frame = cv2.resize(
                annotated,
                (review_width, review_height),
                interpolation=cv2.INTER_AREA,
            )
            writer.write(review_frame)

            if frame_index in sample_set:
                sample_path = (
                    frames_dir
                    / f"frame_{frame_index:06d}_court_overlay.jpg"
                )

                if not cv2.imwrite(str(sample_path), annotated):
                    raise RuntimeError(
                        f"Could not write checkpoint: {sample_path}"
                    )

                sample_paths.append(sample_path)

            processed += 1

            if processed % 100 == 0:
                print(
                    f"  Rendered {processed}/"
                    f"{metadata['frame_count']} frames"
                )
    finally:
        capture.release()
        writer.release()

    if processed != metadata["frame_count"]:
        raise RuntimeError(
            "Video decode ended early during review rendering: "
            f"rendered={processed}, expected={metadata['frame_count']}"
        )

    return output_video, sample_paths


def summarize_tracking(frame_records, smoothing_summary):
    method_counts = Counter(record["method"] for record in frame_records)
    direct_records = [
        record["direct_match"]
        for record in frame_records
        if record["method"] == "direct_to_reference"
    ]
    inliers = np.asarray(
        [record["inlier_count"] for record in direct_records],
        dtype=float,
    )
    inlier_ratios = np.asarray(
        [record["inlier_ratio"] for record in direct_records],
        dtype=float,
    )
    errors = np.asarray(
        [
            record["median_reprojection_error_px"]
            for record in direct_records
            if record["median_reprojection_error_px"] is not None
        ],
        dtype=float,
    )

    def distribution(values):
        if not len(values):
            return {"minimum": None, "median": None, "p90": None}

        return {
            "minimum": round(float(np.min(values)), 4),
            "median": round(float(np.median(values)), 4),
            "p90": round(float(np.percentile(values, 90)), 4),
        }

    unresolved = method_counts.get("unresolved", 0)
    fallback = method_counts.get("sequential_fallback", 0)
    direct = method_counts.get("direct_to_reference", 0)
    non_reference_frames = len(frame_records) - 1
    direct_fraction = (
        direct / non_reference_frames if non_reference_frames else 1.0
    )

    geometry_validation = smoothing_summary.get(
        "geometry_validation",
        {},
    )
    geometry_fallback = smoothing_summary.get(
        "geometry_fallback",
        {},
    )

    if geometry_validation.get("status") != "passed":
        quality = "invalid_smoothed_camera_geometry"
    elif geometry_fallback.get("applied"):
        quality = "usable_with_geometry_safe_fallback_review"
    elif unresolved:
        quality = "needs_review_unresolved_frames"
    elif direct_fraction >= 0.95 and fallback <= 10:
        quality = "strong_direct_registration"
    elif direct_fraction >= 0.80:
        quality = "usable_with_fallback_review"
    else:
        quality = "weak_reference_registration"

    return {
        "quality_classification": quality,
        "frame_method_counts": dict(sorted(method_counts.items())),
        "direct_registration_fraction": round(direct_fraction, 6),
        "direct_inlier_count_distribution": distribution(inliers),
        "direct_inlier_ratio_distribution": distribution(inlier_ratios),
        "direct_median_reprojection_error_px_distribution": (
            distribution(errors)
        ),
        "smoothing": smoothing_summary,
        "interpretation": {
            "direct_to_reference": (
                "Frame registered independently to reference frame 249."
            ),
            "sequential_fallback": (
                "Direct registration failed, so the frame was "
                "composed through the immediately previous frame."
            ),
            "unresolved": (
                "Neither direct nor bounded sequential registration "
                "produced a valid raw transform; the bidirectional "
                "robust trajectory supplied the replacement."
            ),
        },
    }


def save_transform_artifact(
    output_path,
    raw_transforms,
    smoothed_transforms,
    raw_valid_mask,
    robust_accepted_mask,
    robust_residuals,
    reference_frame_index,
):
    raw_array = np.full(
        (len(raw_transforms), 3, 3),
        np.nan,
        dtype=np.float64,
    )

    for index, transform in enumerate(raw_transforms):
        if transform is not None:
            raw_array[index] = transform

    smoothed_array = np.stack(smoothed_transforms).astype(np.float64)
    np.savez_compressed(
        output_path,
        raw_frame_to_reference=raw_array,
        smoothed_frame_to_reference=smoothed_array,
        raw_valid_mask=np.asarray(raw_valid_mask, dtype=bool),
        robust_accepted_mask=np.asarray(
            robust_accepted_mask,
            dtype=bool,
        ),
        raw_to_robust_baseline_median_residual_px=np.asarray(
            [np.nan if value is None else value for value in robust_residuals],
            dtype=np.float64,
        ),
        reference_frame_index=np.asarray(
            [reference_frame_index],
            dtype=np.int32,
        ),
    )


def serialize_frame_record(
    record,
    smoothing_delta,
    raw_valid,
    robust_accepted,
    robust_residual,
):
    output = dict(record)
    output["raw_transform_available_for_smoothing"] = bool(raw_valid)
    output["raw_transform_accepted_by_robust_filter"] = bool(
        robust_accepted
    )
    output[
        "raw_to_robust_baseline_median_residual_px"
    ] = robust_residual
    output["raw_to_smoothed_center_delta_px"] = smoothing_delta
    return output


def write_report(
    output_path,
    args,
    metadata,
    calibration,
    tracking_summary,
    frame_records,
    smoothing_deltas,
    raw_valid_mask,
    robust_accepted_mask,
    robust_residuals,
    output_video,
    sample_paths,
    transform_artifact_path,
):
    report = {
        "source_video": str(args.video),
        "source_calibration": str(args.calibration),
        "source_court_polygon": str(args.court_config),
        "video_metadata": metadata,
        "reference_frame_index": int(
            calibration["reference_frame_index"]
        ),
        "settings": {
            "max_features": args.max_features,
            "lowe_ratio": LOWE_RATIO,
            "ransac_threshold_px": RANSAC_THRESHOLD_PX,
            "minimum_ratio_matches": MIN_RATIO_MATCHES,
            "minimum_inliers": MIN_INLIERS,
            "minimum_inlier_ratio": MIN_INLIER_RATIO,
            "maximum_median_reprojection_error_px": (
                MAX_MEDIAN_REPROJECTION_ERROR_PX
            ),
            "maximum_fallback_chain": MAX_FALLBACK_CHAIN,
            "robust_baseline_radius": ROBUST_BASELINE_RADIUS,
            "robust_refit_radius": ROBUST_REFIT_RADIUS,
            "maximum_robust_median_residual_px": (
                MAX_ROBUST_MEDIAN_RESIDUAL_PX
            ),
            "maximum_robust_point_residual_px": (
                MAX_ROBUST_POINT_RESIDUAL_PX
            ),
            "terminal_search_frame_count": (
                TERMINAL_SEARCH_FRAME_COUNT
            ),
            "terminal_rejected_run_trigger": (
                TERMINAL_REJECTED_RUN_TRIGGER
            ),
            "terminal_minimum_rejected_suffix_fraction": (
                TERMINAL_MIN_REJECTED_SUFFIX_FRACTION
            ),
            "extra_checkpoint_frames": args.extra_checkpoint_frames,
        },
        "tracking_summary": tracking_summary,
        "review_outputs": {
            "motion_review_video": str(output_video),
            "checkpoint_overlays": [str(path) for path in sample_paths],
            "camera_homographies": str(transform_artifact_path),
        },
        "frames": [
            serialize_frame_record(
                record,
                smoothing_deltas[index],
                raw_valid_mask[index],
                robust_accepted_mask[index],
                robust_residuals[index],
            )
            for index, record in enumerate(frame_records)
        ],
        "status": "pending_motion_overlay_review",
        "next_step": (
            "Approve camera-motion propagation only if the yellow "
            "lane, free-throw circle, and three-point arc remain "
            "attached to their black markings through the complete "
            "review video and checkpoint frames."
        ),
    }

    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)
        output_file.write("\n")


def print_summary(
    tracking_summary,
    output_video,
    sample_paths,
    report_path,
    transform_artifact_path,
):
    print("\nMoving-camera court calibration review complete.")
    print(
        "Quality classification: "
        f"{tracking_summary['quality_classification']}"
    )
    print(
        "Frame methods: "
        f"{tracking_summary['frame_method_counts']}"
    )
    print(
        "Direct registration fraction: "
        f"{tracking_summary['direct_registration_fraction']:.1%}"
    )
    print(
        "Median direct inliers: "
        f"{tracking_summary['direct_inlier_count_distribution']['median']}"
    )
    print(
        "Median direct reprojection error: "
        f"{tracking_summary['direct_median_reprojection_error_px_distribution']['median']}px"
    )
    smoothing = tracking_summary["smoothing"]
    print(
        "Robust raw transforms kept/replaced: "
        f"{smoothing['robust_accepted_frame_count']}/"
        f"{smoothing['robust_replaced_frame_count']}"
    )
    geometry = smoothing["geometry_validation"]
    print(
        "Smoothed camera geometry validation: "
        f"{geometry['status']} ({geometry['issue_count']} issue(s))"
    )
    geometry_fallback = smoothing["geometry_fallback"]

    if geometry_fallback["applied"]:
        print(
            "Geometry-safe smoothing fallback: applied using "
            f"{geometry_fallback['method']}"
        )
    else:
        print("Geometry-safe smoothing fallback: not required")

    terminal = smoothing["terminal_stabilization"]

    if terminal["applied"]:
        print(
            "Terminal trajectory stabilization: applied to frames "
            f"{terminal['start_frame']} -> {terminal['end_frame']} "
            f"from anchor frame {terminal['anchor_frame']}"
        )
        print(
            "Terminal instability trigger: "
            f"{terminal['trigger_run_frame_count']} consecutive rejected; "
            f"suffix rejected="
            f"{terminal['trigger_suffix_rejected_frame_count']}/"
            f"{terminal['trigger_suffix_frame_count']} "
            f"({terminal['trigger_suffix_rejected_fraction']:.1%})"
        )
    else:
        print("Terminal trajectory stabilization: not required")

    print(f"Motion-review video saved to: {output_video}")
    print(f"Checkpoint overlays saved: {len(sample_paths)}")
    print(f"Camera homographies saved to: {transform_artifact_path}")
    print(f"Motion report saved to: {report_path}")
    print(
        "Status: pending visual review. Player court coordinates "
        "have not been exported."
    )


def main():
    args = parse_args()

    if cv2 is None or np is None:
        raise ModuleNotFoundError(
            "OpenCV and NumPy are required for camera-motion propagation."
        )
    calibration = load_json(args.calibration)
    court_config = load_json(args.court_config)
    capture, metadata = open_video(args.video)
    capture.release()
    validate_inputs(metadata, calibration, court_config)
    polygon = parse_polygon(court_config)
    feature_mask = build_feature_mask(
        metadata["height"],
        metadata["width"],
        polygon,
    )
    reference_frame_index = int(calibration["reference_frame_index"])
    raw_transforms, frame_records = estimate_all_camera_transforms(
        args.video,
        metadata,
        reference_frame_index,
        feature_mask,
        polygon.astype(np.float32),
        args.max_features,
    )
    reference_control_points = [
        correspondence["image_xy_px"]
        for correspondence in calibration["correspondences"]
        if correspondence.get("used_for_fit")
    ]
    (
        smoothed_transforms,
        raw_valid_mask,
        robust_accepted_mask,
        robust_residuals,
        smoothing_deltas,
        smoothing_summary,
    ) = smooth_camera_transforms(
        raw_transforms,
        metadata["width"],
        metadata["height"],
        args.smoothing_window,
        reference_frame_index,
        reference_control_points,
        frame_records,
    )
    reference_to_court = normalize_homography(
        np.asarray(
            calibration["image_to_court_homography"],
            dtype=np.float64,
        )
    )

    if reference_to_court is None:
        raise ValueError("Final reference homography is invalid")

    court_polylines = build_court_polylines(
        calibration["court_model"]
    )
    sample_indices = build_sample_indices(
        metadata["frame_count"],
        args.sample_count,
        reference_frame_index,
    )
    invalid_extra_frames = [
        frame_index
        for frame_index in args.extra_checkpoint_frames
        if not 0 <= frame_index < metadata["frame_count"]
    ]

    if invalid_extra_frames:
        raise ValueError(
            "Extra checkpoint frame indices are outside the video: "
            f"{invalid_extra_frames}"
        )

    sample_indices = sorted(
        set(sample_indices).union(args.extra_checkpoint_frames)
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.output_homographies.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    output_video, sample_paths = render_motion_review(
        args.video,
        args.output_dir,
        args.output_video,
        metadata,
        reference_to_court,
        smoothed_transforms,
        frame_records,
        robust_accepted_mask,
        robust_residuals,
        smoothing_deltas,
        court_polylines,
        sample_indices,
        args.review_width,
    )
    tracking_summary = summarize_tracking(
        frame_records,
        smoothing_summary,
    )
    transform_artifact_path = args.output_homographies
    save_transform_artifact(
        transform_artifact_path,
        raw_transforms,
        smoothed_transforms,
        raw_valid_mask,
        robust_accepted_mask,
        robust_residuals,
        reference_frame_index,
    )
    report_path = args.report
    write_report(
        report_path,
        args,
        metadata,
        calibration,
        tracking_summary,
        frame_records,
        smoothing_deltas,
        raw_valid_mask,
        robust_accepted_mask,
        robust_residuals,
        output_video,
        sample_paths,
        transform_artifact_path,
    )
    print_summary(
        tracking_summary,
        output_video,
        sample_paths,
        report_path,
        transform_artifact_path,
    )


if __name__ == "__main__":
    main()
