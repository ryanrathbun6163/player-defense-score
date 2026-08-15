import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import least_squares


DEFAULT_VIDEO_PATH = Path("data/clips/possession_001.mp4")
DEFAULT_INPUT_PATH = Path(
    "configs/possession_001_court_calibration_final.json"
)
DEFAULT_OUTPUT_PATH = Path(
    "configs/possession_001_court_calibration_refined.json"
)
DEFAULT_REVIEW_DIR = Path(
    "data/outputs/court/possession_001_boundary_refinement"
)

WINDOW_NAME = "Refine Camera-Side Court Boundary"
MAX_DISPLAY_WIDTH = 1400
MAX_DISPLAY_HEIGHT = 800
NEAR_SIDELINE_Y_FT = 50.0
BOUNDARY_WEIGHT = 2.0

ORIGINAL_MODEL_COLOR = (150, 150, 150)
REFINED_MODEL_COLOR = (0, 235, 255)
CLICK_COLOR = (60, 230, 60)
TEXT_COLOR = (255, 255, 255)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Refine a reviewed reference homography with two "
            "camera-side sideline points."
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
        help="Reviewed reference calibration JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Boundary-refined calibration JSON.",
    )
    parser.add_argument(
        "--review-dir",
        type=Path,
        default=DEFAULT_REVIEW_DIR,
        help="Directory for boundary-refinement review images.",
    )
    return parser.parse_args()


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Required JSON file not found: {path}")

    with path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def normalize_homography(homography):
    array = np.asarray(homography, dtype=np.float64)

    if array.shape != (3, 3):
        raise ValueError(
            f"Homography must be 3x3, received {array.shape}"
        )

    scale = float(array[2, 2])

    if abs(scale) < 1e-12:
        raise ValueError("Homography has an invalid scale")

    array = array / scale

    if not np.all(np.isfinite(array)):
        raise ValueError("Homography contains non-finite values")

    return array


def project_points(points, homography):
    array = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(
        array,
        np.asarray(homography, dtype=np.float64),
    )
    return projected.reshape(-1, 2)


def load_reference_frame(video_path, calibration):
    if not video_path.exists():
        raise FileNotFoundError(f"Source video not found: {video_path}")

    capture = cv2.VideoCapture(str(video_path))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open source video: {video_path}")

    frame_index = int(calibration["reference_frame_index"])
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

    if not 0 <= frame_index < frame_count:
        capture.release()
        raise ValueError(
            f"Reference frame {frame_index} outside 0..{frame_count - 1}"
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

    expected = calibration["video_metadata"]
    actual_size = (frame.shape[1], frame.shape[0])
    expected_size = (int(expected["width"]), int(expected["height"]))

    if actual_size != expected_size:
        raise ValueError(
            "Reference calibration dimensions do not match video: "
            f"calibration={expected_size}, video={actual_size}"
        )

    return frame


def build_court_polylines(court_model):
    width = float(court_model["court_width_ft"])
    half_length = float(court_model["half_court_length_ft"])
    lane_width = float(court_model["lane_width_ft"])
    free_throw_x = float(
        court_model["baseline_to_free_throw_line_ft"]
    )
    basket_x = float(
        court_model["basket_center_from_baseline_ft"]
    )
    three_radius = float(court_model["three_point_radius_ft"])
    center_y = width / 2.0
    lane_far = (width - lane_width) / 2.0
    lane_near = (width + lane_width) / 2.0
    lines = [
        np.asarray(
            [
                [0.0, 0.0],
                [half_length, 0.0],
                [half_length, width],
                [0.0, width],
                [0.0, 0.0],
            ],
            dtype=np.float32,
        ),
        np.asarray(
            [
                [0.0, lane_far],
                [free_throw_x, lane_far],
                [free_throw_x, lane_near],
                [0.0, lane_near],
            ],
            dtype=np.float32,
        ),
    ]
    circle_angles = np.linspace(0.0, 2.0 * np.pi, 181)
    lines.append(
        np.column_stack(
            (
                free_throw_x + 6.0 * np.cos(circle_angles),
                center_y + 6.0 * np.sin(circle_angles),
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


def draw_model(frame, court_polylines, image_to_court, color, thickness):
    output = frame
    court_to_image = np.linalg.inv(image_to_court)

    for court_line in court_polylines:
        image_line = project_points(court_line, court_to_image)
        finite = np.all(np.isfinite(image_line), axis=1)

        if np.count_nonzero(finite) < 2:
            continue

        points = np.rint(image_line[finite]).astype(np.int32)
        cv2.polylines(
            output,
            [points],
            isClosed=False,
            color=color,
            thickness=thickness,
            lineType=cv2.LINE_AA,
        )

    return output


def compute_display_scale(frame):
    height, width = frame.shape[:2]
    return min(
        1.0,
        MAX_DISPLAY_WIDTH / width,
        MAX_DISPLAY_HEIGHT / height,
    )


def select_boundary_points(frame, court_polylines, homography):
    scale = compute_display_scale(frame)
    display_size = (
        int(round(frame.shape[1] * scale)),
        int(round(frame.shape[0] * scale)),
    )
    selected = []

    def mouse_callback(event, x, y, _flags, _parameter):
        if event == cv2.EVENT_LBUTTONDOWN and len(selected) < 2:
            selected.append((x / scale, y / scale))
        elif event == cv2.EVENT_RBUTTONDOWN and selected:
            selected.pop()

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, *display_size)
    cv2.setMouseCallback(WINDOW_NAME, mouse_callback)

    try:
        while True:
            canvas = frame.copy()
            draw_model(
                canvas,
                court_polylines,
                homography,
                ORIGINAL_MODEL_COLOR,
                2,
            )

            for index, point in enumerate(selected, start=1):
                center = tuple(np.rint(point).astype(int))
                cv2.circle(
                    canvas,
                    center,
                    9,
                    CLICK_COLOR,
                    -1,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    canvas,
                    str(index),
                    (center[0] + 12, center[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    CLICK_COLOR,
                    2,
                    cv2.LINE_AA,
                )

            panel = canvas.copy()
            cv2.rectangle(panel, (0, 0), (1510, 126), (0, 0, 0), -1)
            cv2.addWeighted(panel, 0.76, canvas, 0.24, 0, canvas)
            cv2.putText(
                canvas,
                "CAMERA-SIDE SIDELINE REFINEMENT",
                (22, 34),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.78,
                TEXT_COLOR,
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                canvas,
                "Click 2 widely separated points where hardwood meets the dark camera-side border.",
                (22, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.58,
                TEXT_COLOR,
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                canvas,
                "Left click=add | right click=undo | R=reset | Enter=accept | Esc=cancel",
                (22, 104),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.54,
                TEXT_COLOR,
                2,
                cv2.LINE_AA,
            )
            display = cv2.resize(
                canvas,
                display_size,
                interpolation=cv2.INTER_AREA,
            )
            cv2.imshow(WINDOW_NAME, display)
            key = cv2.waitKeyEx(20)

            if key in (13, 10) and len(selected) == 2:
                break

            if key in (ord("r"), ord("R")):
                selected.clear()

            if key == 27:
                raise RuntimeError(
                    "Boundary refinement cancelled before acceptance"
                )
    finally:
        cv2.destroyWindow(WINDOW_NAME)

    return np.asarray(selected, dtype=np.float64)


def homography_to_parameters(homography):
    normalized = normalize_homography(homography)
    return np.asarray(
        [
            normalized[0, 0],
            normalized[0, 1],
            normalized[0, 2],
            normalized[1, 0],
            normalized[1, 1],
            normalized[1, 2],
            normalized[2, 0],
            normalized[2, 1],
        ],
        dtype=np.float64,
    )


def parameters_to_homography(parameters):
    values = np.asarray(parameters, dtype=np.float64)
    return np.asarray(
        [
            values[0:3],
            values[3:6],
            [values[6], values[7], 1.0],
        ],
        dtype=np.float64,
    )


def transform_points_numpy(points, homography):
    points = np.asarray(points, dtype=np.float64)
    homogeneous = np.column_stack(
        (points, np.ones(len(points), dtype=np.float64))
    )
    projected = homogeneous @ homography.T
    denominators = projected[:, 2:3]
    denominators = np.where(
        np.abs(denominators) < 1e-9,
        np.sign(denominators) * 1e-9 + (denominators == 0) * 1e-9,
        denominators,
    )
    return projected[:, :2] / denominators


def fit_boundary_refined_homography(calibration, boundary_points):
    fit_items = [
        item
        for item in calibration["correspondences"]
        if item["used_for_fit"]
    ]
    image_points = np.asarray(
        [item["image_xy_px"] for item in fit_items],
        dtype=np.float64,
    )
    court_points = np.asarray(
        [item["court_xy_ft"] for item in fit_items],
        dtype=np.float64,
    )
    original = normalize_homography(
        calibration["image_to_court_homography"]
    )

    def residuals(parameters):
        homography = parameters_to_homography(parameters)
        landmark_projection = transform_points_numpy(
            image_points,
            homography,
        )
        boundary_projection = transform_points_numpy(
            boundary_points,
            homography,
        )
        landmark_residuals = (
            landmark_projection - court_points
        ).reshape(-1)
        boundary_residuals = (
            boundary_projection[:, 1] - NEAR_SIDELINE_Y_FT
        ) * BOUNDARY_WEIGHT
        return np.concatenate(
            (landmark_residuals, boundary_residuals)
        )

    result = least_squares(
        residuals,
        homography_to_parameters(original),
        method="trf",
        loss="linear",
        max_nfev=5000,
        xtol=1e-13,
        ftol=1e-13,
        gtol=1e-13,
    )

    if not result.success:
        raise RuntimeError(
            f"Boundary-constrained homography solve failed: {result.message}"
        )

    refined = normalize_homography(
        parameters_to_homography(result.x)
    )
    original_landmarks = transform_points_numpy(image_points, original)
    refined_landmarks = transform_points_numpy(image_points, refined)
    original_boundary = transform_points_numpy(
        boundary_points,
        original,
    )
    refined_boundary = transform_points_numpy(
        boundary_points,
        refined,
    )
    original_errors = np.linalg.norm(
        original_landmarks - court_points,
        axis=1,
    )
    refined_errors = np.linalg.norm(
        refined_landmarks - court_points,
        axis=1,
    )
    original_boundary_errors = np.abs(
        original_boundary[:, 1] - NEAR_SIDELINE_Y_FT
    )
    refined_boundary_errors = np.abs(
        refined_boundary[:, 1] - NEAR_SIDELINE_Y_FT
    )
    metrics = {
        "fit_landmark_count": len(fit_items),
        "boundary_point_count": len(boundary_points),
        "original_mean_landmark_error_ft": round(
            float(np.mean(original_errors)),
            6,
        ),
        "refined_mean_landmark_error_ft": round(
            float(np.mean(refined_errors)),
            6,
        ),
        "refined_maximum_landmark_error_ft": round(
            float(np.max(refined_errors)),
            6,
        ),
        "original_mean_boundary_error_ft": round(
            float(np.mean(original_boundary_errors)),
            6,
        ),
        "refined_mean_boundary_error_ft": round(
            float(np.mean(refined_boundary_errors)),
            6,
        ),
        "optimizer_cost": round(float(result.cost), 8),
    }

    if metrics["refined_maximum_landmark_error_ft"] > 1.0:
        raise RuntimeError(
            "Boundary refinement degraded an existing fitted landmark "
            "beyond 1.0 ft; reset and choose the hardwood/border line "
            "more carefully."
        )

    return refined, metrics


def refresh_correspondence_metrics(correspondences, homography):
    inverse = np.linalg.inv(homography)
    output = []

    for source in correspondences:
        item = dict(source)
        projected_court = project_points(
            [item["image_xy_px"]],
            homography,
        )[0]
        expected_court = np.asarray(item["court_xy_ft"], dtype=float)
        item["court_reprojection_error_ft"] = round(
            float(np.linalg.norm(projected_court - expected_court)),
            6,
        )

        if not item["used_for_fit"]:
            predicted_image = project_points(
                [item["court_xy_ft"]],
                inverse,
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

        output.append(item)

    return output


def draw_review_overlay(
    frame,
    court_polylines,
    original_homography,
    refined_homography,
    boundary_points,
):
    overlay = frame.copy()
    draw_model(
        overlay,
        court_polylines,
        original_homography,
        ORIGINAL_MODEL_COLOR,
        2,
    )
    draw_model(
        overlay,
        court_polylines,
        refined_homography,
        REFINED_MODEL_COLOR,
        3,
    )

    for point in boundary_points:
        center = tuple(np.rint(point).astype(int))
        cv2.circle(
            overlay,
            center,
            9,
            CLICK_COLOR,
            -1,
            cv2.LINE_AA,
        )
        cv2.circle(
            overlay,
            center,
            12,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )

    panel = overlay.copy()
    cv2.rectangle(panel, (0, 0), (1260, 88), (0, 0, 0), -1)
    cv2.addWeighted(panel, 0.76, overlay, 0.24, 0, overlay)
    cv2.putText(
        overlay,
        "CAMERA-SIDE BOUNDARY REFINEMENT",
        (22, 34),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.78,
        TEXT_COLOR,
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        overlay,
        "gray=original | yellow=refined | green=selected boundary points",
        (22, 68),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        TEXT_COLOR,
        2,
        cv2.LINE_AA,
    )
    return overlay


def confirm_review_overlay(overlay):
    scale = compute_display_scale(overlay)
    display_size = (
        int(round(overlay.shape[1] * scale)),
        int(round(overlay.shape[0] * scale)),
    )
    display = cv2.resize(
        overlay,
        display_size,
        interpolation=cv2.INTER_AREA,
    )
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, *display_size)

    try:
        while True:
            canvas = display.copy()
            cv2.rectangle(
                canvas,
                (0, canvas.shape[0] - 44),
                (canvas.shape[1], canvas.shape[0]),
                (0, 0, 0),
                -1,
            )
            cv2.putText(
                canvas,
                "Enter=accept refined yellow model | R=reselect points | Esc=cancel",
                (18, canvas.shape[0] - 14),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.54,
                TEXT_COLOR,
                2,
                cv2.LINE_AA,
            )
            cv2.imshow(WINDOW_NAME, canvas)
            key = cv2.waitKeyEx(20)

            if key in (13, 10):
                return True

            if key in (ord("r"), ord("R")):
                return False

            if key == 27:
                raise RuntimeError(
                    "Boundary refinement cancelled before acceptance"
                )
    finally:
        cv2.destroyWindow(WINDOW_NAME)


def build_output(
    args,
    calibration,
    refined_homography,
    boundary_points,
    metrics,
    reference_path,
    overlay_path,
):
    output = dict(calibration)
    output["source_reference_calibration"] = str(args.input)
    output["image_to_court_homography"] = [
        [round(float(value), 12) for value in row]
        for row in refined_homography
    ]
    output["correspondences"] = refresh_correspondence_metrics(
        calibration["correspondences"],
        refined_homography,
    )
    output["fit_metrics"] = {
        "fit_landmark_count": metrics["fit_landmark_count"],
        "mean_fit_reprojection_error_ft": metrics[
            "refined_mean_landmark_error_ft"
        ],
        "maximum_fit_reprojection_error_ft": metrics[
            "refined_maximum_landmark_error_ft"
        ],
    }
    output["boundary_refinement"] = {
        "boundary_id": "near_camera_side_sideline",
        "court_constraint": "y=50.0 ft",
        "selected_image_points_px": [
            [round(float(value), 3) for value in point]
            for point in boundary_points
        ],
        "constraint_weight": BOUNDARY_WEIGHT,
        "metrics": metrics,
        "interpretation": (
            "The two selected image points constrain only the "
            "camera-side sideline equation. Their along-line court "
            "coordinates are intentionally not assumed."
        ),
    }
    review_outputs = dict(output.get("review_outputs", {}))
    review_outputs.update(
        {
            "boundary_reference_frame": str(reference_path),
            "boundary_refinement_overlay": str(overlay_path),
        }
    )
    output["review_outputs"] = review_outputs
    review_summary = dict(output.get("review_summary", {}))
    visual_review = dict(review_summary.get("visual_review", {}))
    visual_review["near_camera_side_sideline_alignment"] = (
        "refined_with_reviewed_line_constraint"
    )
    review_summary["visual_review"] = visual_review
    review_summary["next_validation"] = (
        "Re-run temporally guarded camera-motion propagation and "
        "inspect the complete overlay video."
    )
    output["review_summary"] = review_summary
    output["status"] = "reference_fit_reviewed"
    return output


def print_summary(metrics, output_path, overlay_path):
    print("\nCamera-side boundary refinement complete.")
    print(
        "Mean fitted-landmark error: "
        f"{metrics['original_mean_landmark_error_ft']:.3f} -> "
        f"{metrics['refined_mean_landmark_error_ft']:.3f} ft"
    )
    print(
        "Mean selected-boundary error: "
        f"{metrics['original_mean_boundary_error_ft']:.3f} -> "
        f"{metrics['refined_mean_boundary_error_ft']:.3f} ft"
    )
    print(f"Refined calibration saved to: {output_path}")
    print(f"Boundary comparison overlay saved to: {overlay_path}")


def main():
    args = parse_args()
    calibration = load_json(args.input)

    if calibration.get("status") != "reference_fit_reviewed":
        raise ValueError(
            "Input calibration must have status "
            "'reference_fit_reviewed'"
        )

    original_homography = normalize_homography(
        calibration["image_to_court_homography"]
    )
    frame = load_reference_frame(args.video, calibration)
    court_polylines = build_court_polylines(
        calibration["court_model"]
    )
    while True:
        boundary_points = select_boundary_points(
            frame,
            court_polylines,
            original_homography,
        )
        refined_homography, metrics = fit_boundary_refined_homography(
            calibration,
            boundary_points,
        )
        overlay = draw_review_overlay(
            frame,
            court_polylines,
            original_homography,
            refined_homography,
            boundary_points,
        )

        if confirm_review_overlay(overlay):
            break
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.review_dir.mkdir(parents=True, exist_ok=True)
    reference_path = args.review_dir / "reference_frame.jpg"
    overlay_path = args.review_dir / "boundary_refinement_overlay.jpg"

    if not cv2.imwrite(str(reference_path), frame):
        raise RuntimeError(f"Could not write: {reference_path}")

    if not cv2.imwrite(str(overlay_path), overlay):
        raise RuntimeError(f"Could not write: {overlay_path}")

    output = build_output(
        args,
        calibration,
        refined_homography,
        boundary_points,
        metrics,
        reference_path,
        overlay_path,
    )

    with args.output.open("w", encoding="utf-8") as output_file:
        json.dump(output, output_file, indent=2)
        output_file.write("\n")

    print_summary(metrics, args.output, overlay_path)


if __name__ == "__main__":
    main()
