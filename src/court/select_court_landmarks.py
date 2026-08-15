import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np


DEFAULT_VIDEO_PATH = Path("data/clips/possession_001.mp4")
DEFAULT_COURT_CONFIG_PATH = Path("configs/possession_001_court.json")
DEFAULT_OUTPUT_CONFIG_PATH = Path(
    "configs/possession_001_court_calibration.json"
)
DEFAULT_REVIEW_DIR = Path(
    "data/outputs/court/possession_001_landmark_review"
)

VIDEO_WINDOW = "Select Reference Court Landmarks"
GUIDE_WINDOW = "NFHS Half-Court Landmark Guide"
MAX_VIDEO_DISPLAY_WIDTH = 1400
MAX_VIDEO_DISPLAY_HEIGHT = 800

COURT_WIDTH_FT = 50.0
IDEAL_COURT_LENGTH_FT = 84.0
HALF_COURT_LENGTH_FT = IDEAL_COURT_LENGTH_FT / 2.0
LANE_WIDTH_FT = 12.0
LANE_FAR_Y_FT = (COURT_WIDTH_FT - LANE_WIDTH_FT) / 2.0
LANE_NEAR_Y_FT = (COURT_WIDTH_FT + LANE_WIDTH_FT) / 2.0
FREE_THROW_LINE_X_FT = 19.0
FREE_THROW_CIRCLE_RADIUS_FT = 6.0
BASKET_CENTER_X_FT = 5.25
BASKET_CENTER_Y_FT = COURT_WIDTH_FT / 2.0
NFHS_THREE_POINT_RADIUS_FT = 19.75

THREE_POINT_BASELINE_OFFSET_FT = math.sqrt(
    NFHS_THREE_POINT_RADIUS_FT**2 - BASKET_CENTER_X_FT**2
)

LANDMARKS = [
    {
        "key": "1",
        "id": "free_throw_far_lane_corner",
        "label": (
            "Free-throw line x FAR lane edge "
            "(upper/bench side in video)"
        ),
        "court_xy_ft": [FREE_THROW_LINE_X_FT, LANE_FAR_Y_FT],
        "recommended": True,
    },
    {
        "key": "2",
        "id": "free_throw_near_lane_corner",
        "label": (
            "Free-throw line x NEAR lane edge "
            "(lower/camera side in video)"
        ),
        "court_xy_ft": [FREE_THROW_LINE_X_FT, LANE_NEAR_Y_FT],
        "recommended": True,
    },
    {
        "key": "3",
        "id": "baseline_far_lane_corner",
        "label": (
            "Baseline x FAR lane edge "
            "(upper/bench side in video)"
        ),
        "court_xy_ft": [0.0, LANE_FAR_Y_FT],
        "recommended": True,
    },
    {
        "key": "4",
        "id": "baseline_near_lane_corner",
        "label": (
            "Baseline x NEAR lane edge "
            "(lower/camera side in video)"
        ),
        "court_xy_ft": [0.0, LANE_NEAR_Y_FT],
        "recommended": False,
    },
    {
        "key": "5",
        "id": "arc_tangent_toward_midcourt",
        "label": "FT-circle/3-point-arc tangent toward midcourt",
        "court_xy_ft": [
            FREE_THROW_LINE_X_FT + FREE_THROW_CIRCLE_RADIUS_FT,
            BASKET_CENTER_Y_FT,
        ],
        "recommended": True,
    },
    {
        "key": "6",
        "id": "baseline_far_three_point_intersection",
        "label": (
            "Baseline x FAR three-point arc "
            "(upper/bench side in video)"
        ),
        "court_xy_ft": [
            0.0,
            BASKET_CENTER_Y_FT - THREE_POINT_BASELINE_OFFSET_FT,
        ],
        "recommended": False,
    },
    {
        "key": "7",
        "id": "baseline_near_three_point_intersection",
        "label": (
            "Baseline x NEAR three-point arc "
            "(lower/camera side in video)"
        ),
        "court_xy_ft": [
            0.0,
            BASKET_CENTER_Y_FT + THREE_POINT_BASELINE_OFFSET_FT,
        ],
        "recommended": False,
    },
]

LANDMARK_BY_KEY = {landmark["key"]: landmark for landmark in LANDMARKS}
LANDMARK_BY_ID = {landmark["id"]: landmark for landmark in LANDMARKS}
RECOMMENDED_KEYS = [
    landmark["key"] for landmark in LANDMARKS if landmark["recommended"]
]

COLOR_SELECTED = (70, 230, 70)
COLOR_ACTIVE = (0, 220, 255)
COLOR_MODEL = (255, 210, 20)
COLOR_POINTS = (0, 100, 255)
COLOR_TEXT = (255, 255, 255)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Interactively select standardized NFHS court "
            "landmarks on one reference video frame."
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
        help="Existing playable-court polygon configuration.",
    )
    parser.add_argument(
        "--output-config",
        type=Path,
        default=DEFAULT_OUTPUT_CONFIG_PATH,
        help="JSON output for reference-frame calibration.",
    )
    parser.add_argument(
        "--review-dir",
        type=Path,
        default=DEFAULT_REVIEW_DIR,
        help="Directory for the calibration validation images.",
    )
    parser.add_argument(
        "--reference-frame",
        type=int,
        default=None,
        help=(
            "Reference frame override. By default, use the frame "
            "stored in the existing court configuration."
        ),
    )
    return parser.parse_args()


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Configuration not found: {path}")

    with path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def open_reference_frame(video_path, reference_frame):
    if not video_path.exists():
        raise FileNotFoundError(f"Source video not found: {video_path}")

    capture = cv2.VideoCapture(str(video_path))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open source video: {video_path}")

    metadata = {
        "fps": float(capture.get(cv2.CAP_PROP_FPS)),
        "frame_count": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }

    if not 0 <= reference_frame < metadata["frame_count"]:
        capture.release()
        raise ValueError(
            "Reference frame outside the source video: "
            f"{reference_frame} not in "
            f"0..{metadata['frame_count'] - 1}"
        )

    capture.set(cv2.CAP_PROP_POS_FRAMES, reference_frame)
    success, frame = capture.read()
    decoded_frame = int(capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
    capture.release()

    if not success or decoded_frame != reference_frame:
        raise RuntimeError(
            "Could not decode the requested reference frame: "
            f"requested={reference_frame}, decoded={decoded_frame}"
        )

    return frame, metadata


def validate_video_dimensions(metadata, court_config):
    configured = (
        int(court_config["video_width"]),
        int(court_config["video_height"]),
    )
    actual = (metadata["width"], metadata["height"])

    if configured != actual:
        raise ValueError(
            "Court configuration dimensions do not match the "
            f"video: config={configured}, video={actual}"
        )


def player_facing_orientation_text():
    return (
        "Coordinate convention: x=0 at the RIGHT baseline and "
        "increases toward midcourt; y=0 at the FAR bench-side "
        "sideline (upper video edge) and increases toward the "
        "near camera-side sideline (lower video edge)."
    )


def court_to_guide(point, margin, scale):
    court_x, court_y = point
    pixel_x = int(round(margin + court_y * scale))
    pixel_y = int(
        round(margin + (HALF_COURT_LENGTH_FT - court_x) * scale)
    )
    return pixel_x, pixel_y


def build_court_polylines():
    polylines = []
    polylines.append(
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
    polylines.append(
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

    angles = np.linspace(0.0, 2.0 * math.pi, 121)
    free_throw_circle = np.column_stack(
        (
            FREE_THROW_LINE_X_FT
            + FREE_THROW_CIRCLE_RADIUS_FT * np.cos(angles),
            BASKET_CENTER_Y_FT
            + FREE_THROW_CIRCLE_RADIUS_FT * np.sin(angles),
        )
    ).astype(np.float32)
    polylines.append(free_throw_circle)

    three_point_angles = np.linspace(
        -math.acos(-BASKET_CENTER_X_FT / NFHS_THREE_POINT_RADIUS_FT),
        math.acos(-BASKET_CENTER_X_FT / NFHS_THREE_POINT_RADIUS_FT),
        181,
    )
    three_point_arc = np.column_stack(
        (
            BASKET_CENTER_X_FT
            + NFHS_THREE_POINT_RADIUS_FT
            * np.cos(three_point_angles),
            BASKET_CENTER_Y_FT
            + NFHS_THREE_POINT_RADIUS_FT
            * np.sin(three_point_angles),
        )
    ).astype(np.float32)
    three_point_arc = three_point_arc[three_point_arc[:, 0] >= 0.0]
    polylines.append(three_point_arc)

    center_angles = np.linspace(math.pi / 2.0, 3.0 * math.pi / 2.0, 61)
    center_arc = np.column_stack(
        (
            HALF_COURT_LENGTH_FT
            + FREE_THROW_CIRCLE_RADIUS_FT * np.cos(center_angles),
            BASKET_CENTER_Y_FT
            + FREE_THROW_CIRCLE_RADIUS_FT * np.sin(center_angles),
        )
    ).astype(np.float32)
    polylines.append(center_arc)
    return polylines


COURT_POLYLINES = build_court_polylines()


def draw_guide(selected, active_key):
    margin = 50
    scale = 12
    width = int(COURT_WIDTH_FT * scale + 2 * margin)
    height = int(HALF_COURT_LENGTH_FT * scale + 2 * margin)
    guide = np.full((height, width, 3), 28, dtype=np.uint8)

    for polyline in COURT_POLYLINES:
        points = np.asarray(
            [court_to_guide(point, margin, scale) for point in polyline],
            dtype=np.int32,
        )
        cv2.polylines(
            guide,
            [points],
            isClosed=False,
            color=(190, 190, 190),
            thickness=2,
            lineType=cv2.LINE_AA,
        )

    basket = court_to_guide(
        [BASKET_CENTER_X_FT, BASKET_CENTER_Y_FT],
        margin,
        scale,
    )
    cv2.circle(guide, basket, 6, (0, 120, 255), -1, cv2.LINE_AA)
    backboard_first = court_to_guide([4.0, 22.0], margin, scale)
    backboard_second = court_to_guide([4.0, 28.0], margin, scale)
    cv2.line(
        guide,
        backboard_first,
        backboard_second,
        (255, 255, 255),
        3,
        cv2.LINE_AA,
    )

    for landmark in LANDMARKS:
        point = court_to_guide(
            landmark["court_xy_ft"],
            margin,
            scale,
        )
        is_active = landmark["key"] == active_key
        is_selected = landmark["id"] in selected
        color = (
            COLOR_ACTIVE
            if is_active
            else COLOR_SELECTED
            if is_selected
            else COLOR_POINTS
        )
        radius = 10 if is_active else 8
        cv2.circle(guide, point, radius, color, -1, cv2.LINE_AA)
        cv2.circle(guide, point, radius + 2, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(
            guide,
            landmark["key"],
            (point[0] + 12, point[1] - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            2,
            cv2.LINE_AA,
        )

    cv2.putText(
        guide,
        "FAR / BENCH SIDE",
        (margin + 5, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        COLOR_TEXT,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        guide,
        "NEAR / CAMERA SIDE",
        (width - 205, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        COLOR_TEXT,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        guide,
        "RIGHT BASELINE / BASKET END",
        (width // 2 - 155, height - 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        COLOR_TEXT,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        guide,
        "MIDCOURT DIRECTION",
        (width // 2 - 115, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        COLOR_TEXT,
        1,
        cv2.LINE_AA,
    )
    return guide


def next_unselected_key(selected, current_key):
    ordered_keys = RECOMMENDED_KEYS + [
        landmark["key"]
        for landmark in LANDMARKS
        if landmark["key"] not in RECOMMENDED_KEYS
    ]
    start_index = ordered_keys.index(current_key)

    for offset in range(1, len(ordered_keys) + 1):
        key = ordered_keys[(start_index + offset) % len(ordered_keys)]

        if LANDMARK_BY_KEY[key]["id"] not in selected:
            return key

    return current_key


def solve_homography(selected):
    if len(selected) < 4:
        return None, None

    image_points = []
    court_points = []

    for landmark in LANDMARKS:
        if landmark["id"] not in selected:
            continue

        image_points.append(selected[landmark["id"]])
        court_points.append(landmark["court_xy_ft"])

    image_array = np.asarray(image_points, dtype=np.float32)
    court_array = np.asarray(court_points, dtype=np.float32)
    method = cv2.RANSAC if len(image_array) > 4 else 0
    homography, inlier_mask = cv2.findHomography(
        image_array,
        court_array,
        method,
        3.0,
    )

    if homography is None:
        return None, None

    projected = cv2.perspectiveTransform(
        image_array.reshape(-1, 1, 2),
        homography,
    ).reshape(-1, 2)
    errors = np.linalg.norm(projected - court_array, axis=1)
    metrics = {
        "selected_point_count": len(image_points),
        "inlier_count": (
            len(image_points)
            if inlier_mask is None
            else int(np.count_nonzero(inlier_mask))
        ),
        "mean_reprojection_error_ft": float(np.mean(errors)),
        "maximum_reprojection_error_ft": float(np.max(errors)),
    }
    return homography, metrics


def project_court_to_image(points, inverse_homography):
    array = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(array, inverse_homography).reshape(-1, 2)


def draw_projected_model(frame, homography):
    inverse_homography = np.linalg.inv(homography)

    for polyline in COURT_POLYLINES:
        projected = project_court_to_image(polyline, inverse_homography)
        finite = np.all(np.isfinite(projected), axis=1)

        if np.count_nonzero(finite) < 2:
            continue

        points = np.rint(projected[finite]).astype(np.int32)
        cv2.polylines(
            frame,
            [points],
            isClosed=False,
            color=COLOR_MODEL,
            thickness=3,
            lineType=cv2.LINE_AA,
        )

    basket_point = project_court_to_image(
        [[BASKET_CENTER_X_FT, BASKET_CENTER_Y_FT]],
        inverse_homography,
    )[0]

    if np.all(np.isfinite(basket_point)):
        basket = tuple(np.rint(basket_point).astype(int))
        cv2.circle(frame, basket, 8, (0, 100, 255), -1, cv2.LINE_AA)


def draw_selected_points(frame, selected, active_key):
    for landmark in LANDMARKS:
        landmark_id = landmark["id"]

        if landmark_id not in selected:
            continue

        point = tuple(np.rint(selected[landmark_id]).astype(int))
        color = (
            COLOR_ACTIVE
            if landmark["key"] == active_key
            else COLOR_SELECTED
        )
        cv2.circle(frame, point, 8, color, -1, cv2.LINE_AA)
        cv2.circle(frame, point, 11, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(
            frame,
            landmark["key"],
            (point[0] + 12, point[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
            cv2.LINE_AA,
        )


def draw_video_panel(frame, selected, active_key, homography, metrics):
    display = frame.copy()

    if homography is not None:
        draw_projected_model(display, homography)

    draw_selected_points(display, selected, active_key)
    panel_height = 134
    overlay = display.copy()
    cv2.rectangle(
        overlay,
        (0, 0),
        (display.shape[1], panel_height),
        (0, 0, 0),
        -1,
    )
    cv2.addWeighted(overlay, 0.78, display, 0.22, 0, display)
    active_landmark = LANDMARK_BY_KEY[active_key]
    lines = [
        (
            f"ACTIVE {active_key}: {active_landmark['label']} | "
            "click the exact black-line intersection"
        ),
        (
            f"Selected {len(selected)}/4 minimum | number keys: "
            "choose landmark | U: undo | R: reset | V: validate"
        ),
        (
            "Yellow projected court must align with BLACK "
            "basketball markings | Enter: save | Esc: cancel"
        ),
    ]

    if metrics is not None:
        lines.append(
            "Fit: "
            f"{metrics['inlier_count']}/"
            f"{metrics['selected_point_count']} inliers | "
            f"max selected-point error "
            f"{metrics['maximum_reprojection_error_ft']:.3f} ft"
        )

    for index, text in enumerate(lines):
        cv2.putText(
            display,
            text,
            (20, 31 + index * 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.64,
            COLOR_ACTIVE if index == 0 else COLOR_TEXT,
            2,
            cv2.LINE_AA,
        )

    return display


def save_outputs(
    args,
    frame,
    metadata,
    court_config,
    reference_frame,
    selected,
    homography,
    metrics,
):
    args.output_config.parent.mkdir(parents=True, exist_ok=True)
    args.review_dir.mkdir(parents=True, exist_ok=True)
    overlay = frame.copy()
    draw_projected_model(overlay, homography)
    draw_selected_points(overlay, selected, active_key="")
    overlay_path = args.review_dir / "reference_homography_overlay.jpg"
    reference_path = args.review_dir / "reference_frame.jpg"
    guide_path = args.review_dir / "nfhs_landmark_guide.jpg"

    if not cv2.imwrite(str(reference_path), frame):
        raise RuntimeError(f"Could not write: {reference_path}")

    if not cv2.imwrite(str(overlay_path), overlay):
        raise RuntimeError(f"Could not write: {overlay_path}")

    guide = draw_guide(selected, active_key="")

    if not cv2.imwrite(str(guide_path), guide):
        raise RuntimeError(f"Could not write: {guide_path}")

    correspondences = []

    for landmark in LANDMARKS:
        if landmark["id"] not in selected:
            continue

        image_point = selected[landmark["id"]]
        correspondences.append(
            {
                "landmark_id": landmark["id"],
                "label": landmark["label"],
                "image_xy_px": [
                    round(float(image_point[0]), 3),
                    round(float(image_point[1]), 3),
                ],
                "court_xy_ft": [
                    round(float(landmark["court_xy_ft"][0]), 6),
                    round(float(landmark["court_xy_ft"][1]), 6),
                ],
            }
        )

    output = {
        "source_video": str(args.video),
        "source_court_polygon_config": str(args.court_config),
        "video_metadata": metadata,
        "reference_frame_index": reference_frame,
        "reference_timestamp_sec": round(
            reference_frame / metadata["fps"],
            6,
        ),
        "court_model": {
            "ruleset": "NFHS_high_school",
            "coordinate_scope": "right_half_court",
            "ideal_full_court_length_ft": IDEAL_COURT_LENGTH_FT,
            "half_court_length_ft": HALF_COURT_LENGTH_FT,
            "court_width_ft": COURT_WIDTH_FT,
            "lane_width_ft": LANE_WIDTH_FT,
            "baseline_to_free_throw_line_ft": FREE_THROW_LINE_X_FT,
            "basket_center_from_baseline_ft": BASKET_CENTER_X_FT,
            "three_point_radius_ft": NFHS_THREE_POINT_RADIUS_FT,
            "coordinate_convention": player_facing_orientation_text(),
            "note": (
                "The reference transform uses standardized "
                "basket-area markings. Full-court length does not "
                "affect the selected reference correspondences."
            ),
        },
        "correspondences": correspondences,
        "image_to_court_homography": [
            [round(float(value), 12) for value in row]
            for row in homography
        ],
        "fit_metrics": {
            key: round(float(value), 6)
            for key, value in metrics.items()
        },
        "review_outputs": {
            "reference_frame": str(reference_path),
            "projected_model_overlay": str(overlay_path),
            "landmark_guide": str(guide_path),
        },
        "status": "pending_visual_review",
    }

    with args.output_config.open("w", encoding="utf-8") as output_file:
        json.dump(output, output_file, indent=2)
        output_file.write("\n")

    return reference_path, overlay_path, guide_path


def print_landmark_list():
    print("Available landmarks:")

    for landmark in LANDMARKS:
        recommendation = " [recommended]" if landmark["recommended"] else ""
        court_x, court_y = landmark["court_xy_ft"]
        print(
            f"  {landmark['key']}: {landmark['label']} "
            f"-> ({court_x:.3f}, {court_y:.3f}) ft"
            f"{recommendation}"
        )


def main():
    args = parse_args()
    court_config = load_json(args.court_config)
    reference_frame = (
        int(args.reference_frame)
        if args.reference_frame is not None
        else int(court_config["reference_frame_index"])
    )
    frame, metadata = open_reference_frame(
        args.video,
        reference_frame,
    )
    validate_video_dimensions(metadata, court_config)
    display_scale = min(
        1.0,
        MAX_VIDEO_DISPLAY_WIDTH / metadata["width"],
        MAX_VIDEO_DISPLAY_HEIGHT / metadata["height"],
    )
    display_size = (
        int(round(metadata["width"] * display_scale)),
        int(round(metadata["height"] * display_scale)),
    )
    selected = {}
    selection_history = []
    active_key = RECOMMENDED_KEYS[0]
    homography = None
    metrics = None
    saved = False

    def handle_click(event, x, y, flags, param):
        nonlocal active_key, homography, metrics

        if event != cv2.EVENT_LBUTTONDOWN:
            return

        original_x = min(
            metadata["width"] - 1,
            max(0, int(round(x / display_scale))),
        )
        original_y = min(
            metadata["height"] - 1,
            max(0, int(round(y / display_scale))),
        )
        landmark = LANDMARK_BY_KEY[active_key]
        selected[landmark["id"]] = np.asarray(
            [original_x, original_y],
            dtype=np.float32,
        )
        selection_history.append(landmark["id"])
        print(
            f"Selected {active_key}: {landmark['label']} "
            f"at ({original_x}, {original_y}) px"
        )
        active_key = next_unselected_key(selected, active_key)
        homography = None
        metrics = None

    print("NFHS reference-frame court calibration")
    print(f"Video: {args.video}")
    print(
        f"Reference frame: {reference_frame} "
        f"({reference_frame / metadata['fps']:.2f}s)"
    )
    print(player_facing_orientation_text())
    print()
    print_landmark_list()
    print()
    print("Controls:")
    print("  1-7: choose the landmark to place or replace")
    print("  Left click: place active landmark")
    print("  U: undo the most recent selection")
    print("  R: clear all selections")
    print("  V: solve and preview the projected court model")
    print("  Enter: save a validated calibration")
    print("  Escape: cancel without saving")
    print()
    print(
        "Use the BLACK basketball lines. Ignore red and white "
        "volleyball markings."
    )

    cv2.namedWindow(VIDEO_WINDOW, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(VIDEO_WINDOW, handle_click)
    cv2.namedWindow(GUIDE_WINDOW, cv2.WINDOW_AUTOSIZE)

    while True:
        annotated = draw_video_panel(
            frame,
            selected,
            active_key,
            homography,
            metrics,
        )
        display = cv2.resize(
            annotated,
            display_size,
            interpolation=cv2.INTER_AREA,
        )
        guide = draw_guide(selected, active_key)
        cv2.imshow(VIDEO_WINDOW, display)
        cv2.imshow(GUIDE_WINDOW, guide)
        key = cv2.waitKey(20) & 0xFF

        if chr(key) in LANDMARK_BY_KEY if key < 128 else False:
            active_key = chr(key)
            print(
                f"Active landmark {active_key}: "
                f"{LANDMARK_BY_KEY[active_key]['label']}"
            )
            continue

        if key in (ord("u"), ord("U")):
            if selection_history:
                landmark_id = selection_history.pop()
                selected.pop(landmark_id, None)
                active_key = next(
                    landmark["key"]
                    for landmark in LANDMARKS
                    if landmark["id"] == landmark_id
                )
                homography = None
                metrics = None
                print(f"Removed {landmark_id}")
            continue

        if key in (ord("r"), ord("R")):
            selected.clear()
            selection_history.clear()
            active_key = RECOMMENDED_KEYS[0]
            homography = None
            metrics = None
            print("Cleared all landmark selections")
            continue

        if key in (ord("v"), ord("V")):
            homography, metrics = solve_homography(selected)

            if homography is None:
                print(
                    "Need at least four valid, non-collinear "
                    "landmarks before validation."
                )
            else:
                print(
                    "Projected model ready. Check that the yellow "
                    "lane, circles, and three-point arc align with "
                    "the black court markings."
                )
            continue

        if key in (10, 13):
            if homography is None or metrics is None:
                print("Press V and inspect the overlay before saving.")
                continue

            if metrics["inlier_count"] < 4:
                print("Calibration does not have four valid inliers.")
                continue

            saved = True
            break

        if key == 27:
            break

    cv2.destroyAllWindows()

    if not saved:
        print("Calibration cancelled. No output was saved.")
        return

    reference_path, overlay_path, guide_path = save_outputs(
        args,
        frame,
        metadata,
        court_config,
        reference_frame,
        selected,
        homography,
        metrics,
    )
    print("\nReference-frame court calibration saved for review.")
    print(f"Selected landmarks: {len(selected)}")
    print(
        "Inliers: "
        f"{metrics['inlier_count']}/"
        f"{metrics['selected_point_count']}"
    )
    print(
        "Maximum selected-point reprojection error: "
        f"{metrics['maximum_reprojection_error_ft']:.4f} ft"
    )
    print(f"Calibration config saved to: {args.output_config}")
    print(f"Reference frame saved to: {reference_path}")
    print(f"Projected overlay saved to: {overlay_path}")
    print(f"Landmark guide saved to: {guide_path}")
    print(
        "Status: pending visual review. Do not map player "
        "coordinates until the projected overlay is approved."
    )


if __name__ == "__main__":
    main()
