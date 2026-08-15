import argparse
import json
from pathlib import Path

import cv2
import numpy as np


DEFAULT_VIDEO_PATH = Path("data/clips/possession_001.mp4")
DEFAULT_INPUT_PATH = Path(
    "configs/possession_001_court_calibration.json"
)
DEFAULT_REVIEW_PATH = Path(
    "configs/possession_001_court_calibration_review.json"
)
DEFAULT_OUTPUT_PATH = Path(
    "configs/possession_001_court_calibration_final.json"
)
DEFAULT_REVIEW_DIR = Path(
    "data/outputs/court/possession_001_calibration_final_review"
)

COURT_WIDTH_FT = 50.0
HALF_COURT_LENGTH_FT = 42.0
LANE_FAR_Y_FT = 19.0
LANE_NEAR_Y_FT = 31.0
FREE_THROW_LINE_X_FT = 19.0
FREE_THROW_CIRCLE_RADIUS_FT = 6.0
BASKET_CENTER_X_FT = 5.25
BASKET_CENTER_Y_FT = 25.0
THREE_POINT_RADIUS_FT = 19.75
THREE_POINT_BASELINE_OFFSET_FT = float(
    np.sqrt(
        THREE_POINT_RADIUS_FT**2 - BASKET_CENTER_X_FT**2
    )
)

MODEL_COLOR = (0, 235, 255)
FIT_POINT_COLOR = (60, 230, 60)
CHECK_POINT_COLOR = (0, 165, 255)
TEXT_COLOR = (255, 255, 255)

CANONICAL_LANDMARKS = {
    "free_throw_far_lane_corner": {
        "label": "Free-throw line x FAR bench-side lane edge",
        "court_xy_ft": [FREE_THROW_LINE_X_FT, LANE_FAR_Y_FT],
    },
    "free_throw_near_lane_corner": {
        "label": "Free-throw line x NEAR camera-side lane edge",
        "court_xy_ft": [FREE_THROW_LINE_X_FT, LANE_NEAR_Y_FT],
    },
    "baseline_far_lane_corner": {
        "label": "Baseline x FAR bench-side lane edge",
        "court_xy_ft": [0.0, LANE_FAR_Y_FT],
    },
    "baseline_near_lane_corner": {
        "label": "Baseline x NEAR camera-side lane edge",
        "court_xy_ft": [0.0, LANE_NEAR_Y_FT],
    },
    "arc_tangent_toward_midcourt": {
        "label": "FT-circle/3-point-arc tangent toward midcourt",
        "court_xy_ft": [25.0, 25.0],
    },
    "baseline_far_three_point_intersection": {
        "label": "Baseline x FAR bench-side three-point arc",
        "court_xy_ft": [
            0.0,
            BASKET_CENTER_Y_FT - THREE_POINT_BASELINE_OFFSET_FT,
        ],
    },
    "baseline_near_three_point_intersection": {
        "label": "Baseline x NEAR camera-side three-point arc",
        "court_xy_ft": [
            0.0,
            BASKET_CENTER_Y_FT + THREE_POINT_BASELINE_OFFSET_FT,
        ],
    },
}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Apply reviewed landmark corrections and produce the "
            "final reference-frame court homography."
        )
    )
    parser.add_argument(
        "--video",
        type=Path,
        default=DEFAULT_VIDEO_PATH,
        help="Source possession video.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Pending landmark calibration JSON.",
    )
    parser.add_argument(
        "--review",
        type=Path,
        default=DEFAULT_REVIEW_PATH,
        help="Reviewed calibration decisions JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Final reviewed calibration JSON.",
    )
    parser.add_argument(
        "--review-dir",
        type=Path,
        default=DEFAULT_REVIEW_DIR,
        help="Directory for final reference validation images.",
    )
    return parser.parse_args()


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Required JSON file not found: {path}")

    with path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def load_reference_frame(video_path, frame_index):
    if not video_path.exists():
        raise FileNotFoundError(f"Source video not found: {video_path}")

    capture = cv2.VideoCapture(str(video_path))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open source video: {video_path}")

    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

    if not 0 <= frame_index < frame_count:
        capture.release()
        raise ValueError(
            f"Reference frame {frame_index} outside video range "
            f"0..{frame_count - 1}"
        )

    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    success, frame = capture.read()
    decoded_index = int(capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
    capture.release()

    if not success or decoded_index != frame_index:
        raise RuntimeError(
            "Could not decode reference frame: "
            f"requested={frame_index}, decoded={decoded_index}"
        )

    return frame


def normalize_correspondences(raw_calibration, review):
    reassignments = review.get("landmark_reassignments", {})
    fit_ids = set(review["fit_landmark_ids"])
    excluded_reasons = review.get("excluded_landmarks", {})
    normalized = []
    seen_final_ids = set()

    for source in raw_calibration["correspondences"]:
        source_id = source["landmark_id"]
        final_id = reassignments.get(source_id, source_id)

        if final_id not in CANONICAL_LANDMARKS:
            raise ValueError(
                f"Unknown reviewed landmark identity: {final_id}"
            )

        if final_id in seen_final_ids:
            raise ValueError(
                f"Reviewed landmark is assigned more than once: {final_id}"
            )

        seen_final_ids.add(final_id)
        canonical = CANONICAL_LANDMARKS[final_id]
        used_for_fit = final_id in fit_ids
        normalized.append(
            {
                "landmark_id": final_id,
                "label": canonical["label"],
                "image_xy_px": [
                    float(source["image_xy_px"][0]),
                    float(source["image_xy_px"][1]),
                ],
                "court_xy_ft": [
                    float(canonical["court_xy_ft"][0]),
                    float(canonical["court_xy_ft"][1]),
                ],
                "used_for_fit": used_for_fit,
                "selection_confidence": (
                    "reviewed_visible" if used_for_fit else "estimated"
                ),
                "review_note": (
                    None
                    if used_for_fit
                    else excluded_reasons.get(final_id)
                ),
                "source_landmark_id": source_id,
            }
        )

    available_ids = {item["landmark_id"] for item in normalized}
    missing_fit_ids = sorted(fit_ids - available_ids)

    if missing_fit_ids:
        raise ValueError(
            "Reviewed fit landmarks are missing from the input: "
            f"{missing_fit_ids}"
        )

    if len(fit_ids) < 4:
        raise ValueError("At least four reviewed landmarks are required")

    return normalized


def solve_reviewed_homography(correspondences):
    fit_items = [
        item for item in correspondences if item["used_for_fit"]
    ]
    image_points = np.asarray(
        [item["image_xy_px"] for item in fit_items],
        dtype=np.float32,
    )
    court_points = np.asarray(
        [item["court_xy_ft"] for item in fit_items],
        dtype=np.float32,
    )
    homography, _ = cv2.findHomography(
        image_points,
        court_points,
        method=0,
    )

    if homography is None:
        raise RuntimeError("Reviewed landmark homography solve failed")

    projected = cv2.perspectiveTransform(
        image_points.reshape(-1, 1, 2),
        homography,
    ).reshape(-1, 2)
    errors = np.linalg.norm(projected - court_points, axis=1)
    metrics = {
        "fit_landmark_count": len(fit_items),
        "mean_fit_reprojection_error_ft": float(np.mean(errors)),
        "maximum_fit_reprojection_error_ft": float(np.max(errors)),
    }
    return homography, metrics


def project_points(points, homography):
    array = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(array, homography)
    return projected.reshape(-1, 2)


def add_validation_metrics(correspondences, homography):
    inverse_homography = np.linalg.inv(homography)

    for item in correspondences:
        predicted_court = project_points(
            [item["image_xy_px"]],
            homography,
        )[0]
        selected_court = np.asarray(item["court_xy_ft"], dtype=float)
        item["court_reprojection_error_ft"] = round(
            float(np.linalg.norm(predicted_court - selected_court)),
            6,
        )

        if item["used_for_fit"]:
            item["model_predicted_image_xy_px"] = None
            item["image_validation_delta_px"] = None
            continue

        predicted_image = project_points(
            [item["court_xy_ft"]],
            inverse_homography,
        )[0]
        selected_image = np.asarray(item["image_xy_px"], dtype=float)
        item["model_predicted_image_xy_px"] = [
            round(float(predicted_image[0]), 3),
            round(float(predicted_image[1]), 3),
        ]
        item["image_validation_delta_px"] = round(
            float(np.linalg.norm(predicted_image - selected_image)),
            3,
        )


def build_court_polylines():
    lines = []
    lines.append(
        np.asarray(
            [
                [0.0, 0.0],
                [HALF_COURT_LENGTH_FT, 0.0],
                [HALF_COURT_LENGTH_FT, COURT_WIDTH_FT],
                [0.0, COURT_WIDTH_FT],
                [0.0, 0.0],
            ],
            dtype=np.float32,
        )
    )
    lines.append(
        np.asarray(
            [
                [0.0, LANE_FAR_Y_FT],
                [FREE_THROW_LINE_X_FT, LANE_FAR_Y_FT],
                [FREE_THROW_LINE_X_FT, LANE_NEAR_Y_FT],
                [0.0, LANE_NEAR_Y_FT],
            ],
            dtype=np.float32,
        )
    )
    full_circle_angles = np.linspace(0.0, 2.0 * np.pi, 181)
    lines.append(
        np.column_stack(
            (
                FREE_THROW_LINE_X_FT
                + FREE_THROW_CIRCLE_RADIUS_FT
                * np.cos(full_circle_angles),
                BASKET_CENTER_Y_FT
                + FREE_THROW_CIRCLE_RADIUS_FT
                * np.sin(full_circle_angles),
            )
        ).astype(np.float32)
    )
    endpoint_angle = np.arccos(
        -BASKET_CENTER_X_FT / THREE_POINT_RADIUS_FT
    )
    three_point_angles = np.linspace(
        -endpoint_angle,
        endpoint_angle,
        241,
    )
    lines.append(
        np.column_stack(
            (
                BASKET_CENTER_X_FT
                + THREE_POINT_RADIUS_FT
                * np.cos(three_point_angles),
                BASKET_CENTER_Y_FT
                + THREE_POINT_RADIUS_FT
                * np.sin(three_point_angles),
            )
        ).astype(np.float32)
    )
    return lines


def draw_review_overlay(frame, correspondences, homography):
    overlay = frame.copy()
    inverse_homography = np.linalg.inv(homography)

    for court_line in build_court_polylines():
        image_line = project_points(court_line, inverse_homography)
        finite = np.all(np.isfinite(image_line), axis=1)

        if np.count_nonzero(finite) < 2:
            continue

        points = np.rint(image_line[finite]).astype(np.int32)
        cv2.polylines(
            overlay,
            [points],
            isClosed=False,
            color=MODEL_COLOR,
            thickness=3,
            lineType=cv2.LINE_AA,
        )

    for item in correspondences:
        point = tuple(
            np.rint(item["image_xy_px"]).astype(int)
        )
        color = (
            FIT_POINT_COLOR
            if item["used_for_fit"]
            else CHECK_POINT_COLOR
        )
        cv2.circle(overlay, point, 8, color, -1, cv2.LINE_AA)
        cv2.circle(overlay, point, 11, (0, 0, 0), 2, cv2.LINE_AA)
        short_label = item["landmark_id"].replace(
            "_intersection",
            "",
        )
        short_label = short_label.replace("_corner", "")
        cv2.putText(
            overlay,
            short_label,
            (point[0] + 12, point[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            color,
            2,
            cv2.LINE_AA,
        )

    panel = overlay.copy()
    cv2.rectangle(panel, (0, 0), (960, 86), (0, 0, 0), -1)
    cv2.addWeighted(panel, 0.76, overlay, 0.24, 0, overlay)
    cv2.putText(
        overlay,
        "REVIEWED REFERENCE HOMOGRAPHY",
        (22, 34),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.78,
        TEXT_COLOR,
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        overlay,
        "green = fitted visible point | orange = estimated check only",
        (22, 68),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        TEXT_COLOR,
        2,
        cv2.LINE_AA,
    )
    return overlay


def build_final_output(
    args,
    raw_calibration,
    review,
    correspondences,
    homography,
    metrics,
    overlay_path,
    reference_path,
):
    result = dict(raw_calibration)
    result["source_pending_calibration"] = str(args.input)
    result["source_review_decisions"] = str(args.review)
    result["correspondences"] = correspondences
    result["image_to_court_homography"] = [
        [round(float(value), 12) for value in row]
        for row in homography
    ]
    result["fit_metrics"] = {
        key: (
            int(value)
            if key.endswith("_count")
            else round(float(value), 6)
        )
        for key, value in metrics.items()
    }
    result["review_summary"] = {
        "review_status": review["review_status"],
        "coordinate_interpretation": review[
            "coordinate_interpretation"
        ],
        "visual_review": review["visual_review"],
        "fit_landmark_ids": review["fit_landmark_ids"],
        "excluded_landmarks": review["excluded_landmarks"],
        "next_validation": review["next_validation"],
    }
    result["review_outputs"] = {
        "reference_frame": str(reference_path),
        "reviewed_projected_model_overlay": str(overlay_path),
    }
    result["status"] = "reference_fit_reviewed"
    return result


def print_summary(correspondences, metrics, output_path, overlay_path):
    print("\nReviewed reference court calibration finalized.")
    print(
        "Visible landmarks used for fit: "
        f"{metrics['fit_landmark_count']}"
    )
    print(
        "Mean fit reprojection error: "
        f"{metrics['mean_fit_reprojection_error_ft']:.3f} ft"
    )
    print(
        "Maximum fit reprojection error: "
        f"{metrics['maximum_fit_reprojection_error_ft']:.3f} ft"
    )

    for item in correspondences:
        if item["used_for_fit"]:
            continue

        print(
            f"Validation only: {item['landmark_id']} | "
            f"selected-to-model delta="
            f"{item['image_validation_delta_px']:.1f}px"
        )

    print(f"Final calibration saved to: {output_path}")
    print(f"Reviewed overlay saved to: {overlay_path}")
    print(
        "Next step: validate camera-motion propagation across "
        "the full possession before mapping player coordinates."
    )


def main():
    args = parse_args()
    raw_calibration = load_json(args.input)
    review = load_json(args.review)
    correspondences = normalize_correspondences(
        raw_calibration,
        review,
    )
    homography, metrics = solve_reviewed_homography(
        correspondences
    )
    add_validation_metrics(correspondences, homography)
    reference_frame_index = int(
        raw_calibration["reference_frame_index"]
    )
    frame = load_reference_frame(
        args.video,
        reference_frame_index,
    )
    args.review_dir.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    reference_path = args.review_dir / "reference_frame.jpg"
    overlay_path = (
        args.review_dir / "reviewed_reference_homography_overlay.jpg"
    )
    overlay = draw_review_overlay(
        frame,
        correspondences,
        homography,
    )

    if not cv2.imwrite(str(reference_path), frame):
        raise RuntimeError(f"Could not write: {reference_path}")

    if not cv2.imwrite(str(overlay_path), overlay):
        raise RuntimeError(f"Could not write: {overlay_path}")

    final_output = build_final_output(
        args,
        raw_calibration,
        review,
        correspondences,
        homography,
        metrics,
        overlay_path,
        reference_path,
    )

    with args.output.open("w", encoding="utf-8") as output_file:
        json.dump(final_output, output_file, indent=2)
        output_file.write("\n")

    print_summary(
        correspondences,
        metrics,
        args.output,
        overlay_path,
    )


if __name__ == "__main__":
    main()
