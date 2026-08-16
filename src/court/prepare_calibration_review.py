import argparse
import json
import math
from pathlib import Path

try:
    import cv2
    import numpy as np
except ModuleNotFoundError:
    cv2 = None
    np = None


DEFAULT_VIDEO_PATH = Path("data/clips/possession_001.mp4")
DEFAULT_COURT_CONFIG_PATH = Path("configs/possession_001_court.json")
DEFAULT_OUTPUT_DIR = Path(
    "data/outputs/court/possession_001_calibration_review"
)
DEFAULT_REPORT_PATH = (
    DEFAULT_OUTPUT_DIR / "possession_001_calibration_review.json"
)

DEFAULT_SAMPLE_COUNT = 7
DEFAULT_MAX_FEATURES = 5000
MIN_HOMOGRAPHY_MATCHES = 12
LOWE_RATIO = 0.75

THUMBNAIL_WIDTH = 640
THUMBNAIL_HEIGHT = 360
CONTACT_SHEET_COLUMNS = 2


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Extract clean court-calibration frames and measure "
            "camera motion across a possession."
        )
    )
    parser.add_argument(
        "--video",
        type=Path,
        default=DEFAULT_VIDEO_PATH,
        help="Source possession video.",
    )
    parser.add_argument(
        "--court-config",
        type=Path,
        default=DEFAULT_COURT_CONFIG_PATH,
        help=(
            "Existing playable-court polygon configuration. "
            "The polygon is used as a feature-matching mask."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for review frames and the JSON report.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Calibration-preparation JSON report path.",
    )
    parser.add_argument(
        "--sample-count",
        type=int,
        default=DEFAULT_SAMPLE_COUNT,
        help=(
            "Number of evenly spaced frames to sample. The "
            "configured reference frame is always included."
        ),
    )
    parser.add_argument(
        "--max-features",
        type=int,
        default=DEFAULT_MAX_FEATURES,
        help="Maximum ORB features detected per sampled frame.",
    )
    args = parser.parse_args(argv)

    if args.sample_count < 3:
        parser.error("--sample-count must be at least 3")

    if args.max_features < 500:
        parser.error("--max-features must be at least 500")

    return args


def load_court_config(path):
    if not path.exists():
        raise FileNotFoundError(f"Court configuration not found: {path}")

    with path.open("r", encoding="utf-8") as input_file:
        config = json.load(input_file)

    required_fields = {
        "video_width",
        "video_height",
        "reference_frame_index",
        "polygon",
    }
    missing_fields = sorted(required_fields - set(config))

    if missing_fields:
        raise ValueError(
            "Court configuration is missing required fields: "
            f"{missing_fields}"
        )

    polygon = config["polygon"]

    if not isinstance(polygon, list) or len(polygon) < 3:
        raise ValueError(
            "Court configuration polygon must contain at least "
            "three points."
        )

    parsed_polygon = []

    for index, point in enumerate(polygon):
        try:
            x = int(point["x"])
            y = int(point["y"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                f"Invalid polygon point at index {index}: {point!r}"
            ) from error

        parsed_polygon.append([x, y])

    config["video_width"] = int(config["video_width"])
    config["video_height"] = int(config["video_height"])
    config["reference_frame_index"] = int(
        config["reference_frame_index"]
    )
    config["polygon_array"] = np.asarray(
        parsed_polygon,
        dtype=np.int32,
    )
    return config


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
        raise ValueError(
            "Source video has invalid metadata: "
            f"{metadata}"
        )

    return capture, metadata


def validate_dimensions(metadata, court_config):
    configured_size = (
        court_config["video_width"],
        court_config["video_height"],
    )
    video_size = (metadata["width"], metadata["height"])

    if configured_size != video_size:
        raise ValueError(
            "Court polygon dimensions do not match the source "
            f"video: config={configured_size}, video={video_size}"
        )


def build_sample_indices(frame_count, sample_count, reference_frame):
    last_frame = frame_count - 1
    evenly_spaced = {
        int(round(index * last_frame / (sample_count - 1)))
        for index in range(sample_count)
    }

    if 0 <= reference_frame <= last_frame:
        evenly_spaced.add(reference_frame)
    else:
        raise ValueError(
            "Configured reference frame is outside the video: "
            f"frame={reference_frame}, video frames=0..{last_frame}"
        )

    return sorted(evenly_spaced)


def read_frame(capture, frame_index):
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    success, frame = capture.read()

    if not success:
        raise RuntimeError(
            f"Could not decode source frame {frame_index}"
        )

    decoded_index = int(capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1

    if decoded_index != frame_index:
        raise RuntimeError(
            "Video seek returned the wrong frame: "
            f"requested={frame_index}, decoded={decoded_index}"
        )

    return frame


def polygon_mask(frame_shape, polygon):
    mask = np.zeros(frame_shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [polygon], 255)
    return mask


def draw_polygon_overlay(frame, polygon, frame_index, timestamp_sec):
    overlay = frame.copy()
    shaded = frame.copy()
    cv2.fillPoly(shaded, [polygon], (0, 180, 255))
    cv2.addWeighted(shaded, 0.18, overlay, 0.82, 0, overlay)
    cv2.polylines(
        overlay,
        [polygon],
        isClosed=True,
        color=(0, 255, 255),
        thickness=4,
        lineType=cv2.LINE_AA,
    )

    for index, point in enumerate(polygon):
        point_tuple = (int(point[0]), int(point[1]))
        cv2.circle(overlay, point_tuple, 7, (0, 0, 255), -1)
        cv2.putText(
            overlay,
            str(index),
            (point_tuple[0] + 10, point_tuple[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    label = f"frame {frame_index} | {timestamp_sec:.2f}s"
    cv2.rectangle(overlay, (12, 12), (430, 58), (0, 0, 0), -1)
    cv2.putText(
        overlay,
        label,
        (25, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return overlay


def add_thumbnail_label(image, label):
    cv2.rectangle(
        image,
        (0, THUMBNAIL_HEIGHT - 38),
        (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT),
        (0, 0, 0),
        -1,
    )
    cv2.putText(
        image,
        label,
        (12, THUMBNAIL_HEIGHT - 11),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 255, 255),
        2,
        cv2.LINE_AA,
    )


def build_contact_sheet(frame_records, output_path):
    thumbnails = []

    for record in frame_records:
        image = cv2.imread(str(record["clean_path"]))

        if image is None:
            raise RuntimeError(
                f"Could not reopen review frame: {record['clean_path']}"
            )

        thumbnail = cv2.resize(
            image,
            (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT),
            interpolation=cv2.INTER_AREA,
        )
        add_thumbnail_label(
            thumbnail,
            (
                f"frame {record['frame_index']} | "
                f"{record['timestamp_sec']:.2f}s"
            ),
        )
        thumbnails.append(thumbnail)

    row_count = math.ceil(
        len(thumbnails) / CONTACT_SHEET_COLUMNS
    )
    blank = np.zeros(
        (THUMBNAIL_HEIGHT, THUMBNAIL_WIDTH, 3),
        dtype=np.uint8,
    )

    while len(thumbnails) < row_count * CONTACT_SHEET_COLUMNS:
        thumbnails.append(blank.copy())

    rows = []

    for start in range(0, len(thumbnails), CONTACT_SHEET_COLUMNS):
        rows.append(
            np.hstack(
                thumbnails[start : start + CONTACT_SHEET_COLUMNS]
            )
        )

    contact_sheet = np.vstack(rows)

    if not cv2.imwrite(str(output_path), contact_sheet):
        raise RuntimeError(f"Could not write contact sheet: {output_path}")


def detect_features(frame, mask, max_features):
    detector = cv2.ORB_create(
        nfeatures=max_features,
        scaleFactor=1.2,
        nlevels=8,
        edgeThreshold=19,
        fastThreshold=12,
    )
    grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    keypoints, descriptors = detector.detectAndCompute(
        grayscale,
        mask,
    )
    return keypoints, descriptors


def project_points(points, homography):
    source = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(source, homography)
    return projected.reshape(-1, 2)


def estimate_pair_motion(
    first_record,
    second_record,
    mask,
    polygon,
    max_features,
):
    first_frame = cv2.imread(str(first_record["clean_path"]))
    second_frame = cv2.imread(str(second_record["clean_path"]))

    first_keypoints, first_descriptors = detect_features(
        first_frame,
        mask,
        max_features,
    )
    second_keypoints, second_descriptors = detect_features(
        second_frame,
        mask,
        max_features,
    )

    result = {
        "from_frame": first_record["frame_index"],
        "to_frame": second_record["frame_index"],
        "frame_gap": (
            second_record["frame_index"]
            - first_record["frame_index"]
        ),
        "from_feature_count": len(first_keypoints),
        "to_feature_count": len(second_keypoints),
        "ratio_test_match_count": 0,
        "inlier_count": 0,
        "inlier_ratio": None,
        "median_inlier_displacement_px": None,
        "p90_inlier_displacement_px": None,
        "polygon_motion_median_px": None,
        "polygon_motion_max_px": None,
        "status": "insufficient_features",
    }

    if first_descriptors is None or second_descriptors is None:
        return result

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    candidate_matches = matcher.knnMatch(
        first_descriptors,
        second_descriptors,
        k=2,
    )
    good_matches = [
        first
        for pair in candidate_matches
        if len(pair) == 2
        for first, second in [pair]
        if first.distance < LOWE_RATIO * second.distance
    ]
    result["ratio_test_match_count"] = len(good_matches)

    if len(good_matches) < MIN_HOMOGRAPHY_MATCHES:
        result["status"] = "insufficient_matches"
        return result

    source_points = np.float32(
        [first_keypoints[match.queryIdx].pt for match in good_matches]
    )
    destination_points = np.float32(
        [second_keypoints[match.trainIdx].pt for match in good_matches]
    )
    homography, inlier_mask = cv2.findHomography(
        source_points,
        destination_points,
        cv2.RANSAC,
        4.0,
    )

    if homography is None or inlier_mask is None:
        result["status"] = "homography_failed"
        return result

    inlier_flags = inlier_mask.ravel().astype(bool)
    inlier_count = int(np.count_nonzero(inlier_flags))
    result["inlier_count"] = inlier_count
    result["inlier_ratio"] = round(
        inlier_count / len(good_matches),
        4,
    )

    if inlier_count < MIN_HOMOGRAPHY_MATCHES:
        result["status"] = "insufficient_inliers"
        return result

    inlier_displacements = np.linalg.norm(
        destination_points[inlier_flags]
        - source_points[inlier_flags],
        axis=1,
    )
    projected_polygon = project_points(polygon, homography)
    polygon_displacements = np.linalg.norm(
        projected_polygon - polygon.astype(np.float32),
        axis=1,
    )
    result.update(
        {
            "median_inlier_displacement_px": round(
                float(np.median(inlier_displacements)),
                2,
            ),
            "p90_inlier_displacement_px": round(
                float(np.percentile(inlier_displacements, 90)),
                2,
            ),
            "polygon_motion_median_px": round(
                float(np.median(polygon_displacements)),
                2,
            ),
            "polygon_motion_max_px": round(
                float(np.max(polygon_displacements)),
                2,
            ),
            "status": "ok",
        }
    )
    return result


def summarize_motion(pair_records):
    successful = [
        record for record in pair_records if record["status"] == "ok"
    ]

    if not successful:
        return {
            "successful_pair_count": 0,
            "failed_pair_count": len(pair_records),
            "maximum_polygon_motion_px": None,
            "motion_classification": "undetermined",
            "recommended_calibration_model": (
                "manual review required because automatic motion "
                "estimation did not produce a reliable result"
            ),
        }

    maximum_motion = max(
        record["polygon_motion_max_px"] for record in successful
    )

    if maximum_motion <= 8:
        classification = "approximately_static"
        recommendation = (
            "a single homography may be sufficient, subject to "
            "landmark reprojection validation"
        )
    elif maximum_motion <= 35:
        classification = "mild_camera_motion"
        recommendation = (
            "use a reference homography plus per-frame camera "
            "motion compensation"
        )
    else:
        classification = "material_camera_motion"
        recommendation = (
            "use a reference homography plus per-frame camera "
            "motion compensation; validate multiple keyframes"
        )

    return {
        "successful_pair_count": len(successful),
        "failed_pair_count": len(pair_records) - len(successful),
        "maximum_polygon_motion_px": round(maximum_motion, 2),
        "motion_classification": classification,
        "recommended_calibration_model": recommendation,
    }


def relative_path(path, root):
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def write_report(
    output_path,
    video_path,
    court_config_path,
    metadata,
    court_config,
    frame_records,
    pair_records,
    motion_summary,
    output_dir,
):
    report = {
        "source_video": str(video_path),
        "court_polygon_config": str(court_config_path),
        "video_metadata": metadata,
        "reference_frame_index": court_config["reference_frame_index"],
        "sampled_frames": [
            {
                "frame_index": record["frame_index"],
                "timestamp_sec": record["timestamp_sec"],
                "clean_image": relative_path(
                    record["clean_path"],
                    output_dir,
                ),
                "polygon_overlay": relative_path(
                    record["overlay_path"],
                    output_dir,
                ),
            }
            for record in frame_records
        ],
        "pairwise_camera_motion": pair_records,
        "motion_summary": motion_summary,
        "next_step": (
            "Review the sampled clean frames, choose visible "
            "court landmarks, and solve the reference image-to-"
            "court homography before transforming player floor "
            "points."
        ),
    }

    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)
        output_file.write("\n")


def main():
    args = parse_args()

    if cv2 is None or np is None:
        raise ModuleNotFoundError(
            "OpenCV and NumPy are required for calibration preparation."
        )
    court_config = load_court_config(args.court_config)
    capture, metadata = open_video(args.video)
    validate_dimensions(metadata, court_config)
    sample_indices = build_sample_indices(
        metadata["frame_count"],
        args.sample_count,
        court_config["reference_frame_index"],
    )

    frames_dir = args.output_dir / "frames"
    overlays_dir = args.output_dir / "polygon_overlays"
    frames_dir.mkdir(parents=True, exist_ok=True)
    overlays_dir.mkdir(parents=True, exist_ok=True)
    frame_records = []

    print("Preparing clean court-calibration review frames...")

    try:
        for frame_index in sample_indices:
            frame = read_frame(capture, frame_index)
            timestamp_sec = frame_index / metadata["fps"]
            clean_path = frames_dir / f"frame_{frame_index:06d}.jpg"
            overlay_path = (
                overlays_dir
                / f"frame_{frame_index:06d}_polygon.jpg"
            )
            overlay = draw_polygon_overlay(
                frame,
                court_config["polygon_array"],
                frame_index,
                timestamp_sec,
            )

            if not cv2.imwrite(str(clean_path), frame):
                raise RuntimeError(
                    f"Could not write calibration frame: {clean_path}"
                )

            if not cv2.imwrite(str(overlay_path), overlay):
                raise RuntimeError(
                    f"Could not write polygon overlay: {overlay_path}"
                )

            frame_records.append(
                {
                    "frame_index": frame_index,
                    "timestamp_sec": round(timestamp_sec, 4),
                    "clean_path": clean_path,
                    "overlay_path": overlay_path,
                }
            )
            print(f"  Saved frame {frame_index} ({timestamp_sec:.2f}s)")
    finally:
        capture.release()

    contact_sheet_path = args.output_dir / "calibration_frames.jpg"
    build_contact_sheet(frame_records, contact_sheet_path)
    mask = polygon_mask(
        (metadata["height"], metadata["width"]),
        court_config["polygon_array"],
    )
    pair_records = []

    print("Measuring pairwise camera motion inside the court mask...")

    for first_record, second_record in zip(
        frame_records,
        frame_records[1:],
    ):
        pair_record = estimate_pair_motion(
            first_record,
            second_record,
            mask,
            court_config["polygon_array"],
            args.max_features,
        )
        pair_records.append(pair_record)
        motion_text = (
            "unavailable"
            if pair_record["polygon_motion_max_px"] is None
            else f"{pair_record['polygon_motion_max_px']:.1f}px"
        )
        print(
            f"  {pair_record['from_frame']} -> "
            f"{pair_record['to_frame']} | "
            f"status={pair_record['status']} | "
            f"max polygon motion={motion_text}"
        )

    motion_summary = summarize_motion(pair_records)
    report_path = args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_report(
        report_path,
        args.video,
        args.court_config,
        metadata,
        court_config,
        frame_records,
        pair_records,
        motion_summary,
        args.output_dir,
    )

    print("\nCourt-calibration review preparation complete.")
    print(f"Sampled frames: {len(frame_records)}")
    print(
        "Motion classification: "
        f"{motion_summary['motion_classification']}"
    )
    print(
        "Recommended model: "
        f"{motion_summary['recommended_calibration_model']}"
    )
    print(f"Contact sheet saved to: {contact_sheet_path}")
    print(f"Review report saved to: {report_path}")


if __name__ == "__main__":
    main()
