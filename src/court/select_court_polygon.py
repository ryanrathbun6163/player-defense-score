import argparse
import json
from pathlib import Path


DEFAULT_MAX_DISPLAY_WIDTH = 1400
DEFAULT_MAX_DISPLAY_HEIGHT = 800
WINDOW_NAME = "Select Court Polygon"


def parse_reference_frame(value):
    if value == "middle":
        return value

    try:
        frame_index = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            'reference frame must be a non-negative integer or "middle"'
        ) from error

    if frame_index < 0:
        raise argparse.ArgumentTypeError(
            "reference frame must be non-negative"
        )

    return frame_index


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Interactively select the playable-court polygon for one "
            "possession."
        )
    )
    parser.add_argument(
        "--video",
        type=Path,
        required=True,
        help="Source possession video.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Destination court-polygon JSON.",
    )
    parser.add_argument(
        "--reference-frame",
        type=parse_reference_frame,
        default="middle",
        help='Frame index to display, or "middle" (default).',
    )
    parser.add_argument(
        "--max-display-width",
        type=int,
        default=DEFAULT_MAX_DISPLAY_WIDTH,
        help="Maximum interactive window width.",
    )
    parser.add_argument(
        "--max-display-height",
        type=int,
        default=DEFAULT_MAX_DISPLAY_HEIGHT,
        help="Maximum interactive window height.",
    )
    args = parser.parse_args(argv)

    if args.max_display_width <= 0 or args.max_display_height <= 0:
        parser.error("Display dimensions must be positive")

    return args


def select_court_polygon(args):
    import cv2
    import numpy as np

    capture = cv2.VideoCapture(str(args.video))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {args.video}")

    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if frame_count <= 0 or width <= 0 or height <= 0:
        capture.release()
        raise ValueError(
            "Invalid source-video metadata: "
            f"frames={frame_count}, resolution={width}x{height}"
        )

    if args.reference_frame == "middle":
        reference_frame_index = frame_count // 2
    else:
        reference_frame_index = args.reference_frame

    if reference_frame_index >= frame_count:
        capture.release()
        raise ValueError(
            f"Reference frame {reference_frame_index} is outside the "
            f"{frame_count}-frame video"
        )

    capture.set(cv2.CAP_PROP_POS_FRAMES, reference_frame_index)
    success, frame = capture.read()
    capture.release()

    if not success:
        raise RuntimeError(
            f"Could not read frame {reference_frame_index} from {args.video}"
        )

    display_scale = min(
        1.0,
        args.max_display_width / width,
        args.max_display_height / height,
    )
    display_width = int(width * display_scale)
    display_height = int(height * display_scale)
    points = []

    def handle_click(event, x, y, _flags, _param):
        original_x = int(round(x / display_scale))
        original_y = int(round(y / display_scale))
        original_x = min(max(original_x, 0), width - 1)
        original_y = min(max(original_y, 0), height - 1)

        if event == cv2.EVENT_LBUTTONDOWN:
            points.append((original_x, original_y))
            print(f"Added point: ({original_x}, {original_y})")
        elif event == cv2.EVENT_RBUTTONDOWN and points:
            removed_point = points.pop()
            print(f"Removed point: {removed_point}")

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, display_width, display_height)
    cv2.setMouseCallback(WINDOW_NAME, handle_click)

    print(f"Video: {args.video}")
    print(f"Resolution: {width}x{height}")
    print(f"Reference frame: {reference_frame_index}")
    print()
    print("Controls:")
    print("  Left-click:  add polygon point")
    print("  Right-click: remove most recent point")
    print("  R:           clear all points")
    print("  Enter:       save polygon")
    print("  Escape:      cancel")

    while True:
        display = cv2.resize(
            frame,
            (display_width, display_height),
            interpolation=cv2.INTER_AREA,
        )
        display_points = np.array(
            [
                [
                    int(round(x * display_scale)),
                    int(round(y * display_scale)),
                ]
                for x, y in points
            ],
            dtype=np.int32,
        )

        for index, point in enumerate(display_points):
            point_tuple = (int(point[0]), int(point[1]))
            cv2.circle(display, point_tuple, 6, (0, 0, 255), -1)
            cv2.putText(
                display,
                str(index),
                (point_tuple[0] + 8, point_tuple[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2,
            )

        if len(display_points) >= 2:
            cv2.polylines(
                display,
                [display_points],
                isClosed=len(display_points) >= 3,
                color=(0, 255, 255),
                thickness=2,
            )

        cv2.putText(
            display,
            "Left: add | Right: undo | R: reset | Enter: save | Esc: cancel",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )
        cv2.imshow(WINDOW_NAME, display)
        key = cv2.waitKey(20) & 0xFF

        if key in (10, 13) and len(points) >= 3:
            break

        if key in (ord("r"), ord("R")):
            points.clear()
            print("Cleared all points")

        if key == 27:
            points.clear()
            break

    cv2.destroyAllWindows()

    if not points:
        print("Selection cancelled. No configuration was saved.")
        return False

    args.output.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "video": str(args.video),
        "video_width": width,
        "video_height": height,
        "reference_frame_index": reference_frame_index,
        "polygon": [
            {"x": x, "y": y}
            for x, y in points
        ],
    }

    with args.output.open("w", encoding="utf-8") as output_file:
        json.dump(config, output_file, indent=2)
        output_file.write("\n")

    print(f"Saved court polygon to: {args.output}")
    return True


def main(argv=None):
    args = parse_args(argv)
    select_court_polygon(args)


if __name__ == "__main__":
    main()
