import json
from pathlib import Path

import cv2
import numpy as np


VIDEO_PATH = Path("data/clips/possession_001.mp4")
OUTPUT_PATH = Path("configs/possession_001_court.json")

WINDOW_NAME = "Select Court Polygon"
MAX_DISPLAY_WIDTH = 1400
MAX_DISPLAY_HEIGHT = 800


cap = cv2.VideoCapture(str(VIDEO_PATH))

if not cap.isOpened():
    raise RuntimeError(f"Could not open video: {VIDEO_PATH}")

frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Use the middle frame as a representative view of the possession.
reference_frame_index = frame_count // 2
cap.set(cv2.CAP_PROP_POS_FRAMES, reference_frame_index)

success, frame = cap.read()
cap.release()

if not success:
    raise RuntimeError(
        f"Could not read frame {reference_frame_index} from {VIDEO_PATH}"
    )

display_scale = min(
    1.0,
    MAX_DISPLAY_WIDTH / width,
    MAX_DISPLAY_HEIGHT / height,
)

display_width = int(width * display_scale)
display_height = int(height * display_scale)

points = []


def handle_click(event, x, y, flags, param):
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

print(f"Video: {VIDEO_PATH}")
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

        cv2.circle(
            display,
            point_tuple,
            6,
            (0, 0, 255),
            -1,
        )

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

    instructions = (
        "Left: add | Right: undo | R: reset | Enter: save | Esc: cancel"
    )

    cv2.putText(
        display,
        instructions,
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
else:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    config = {
        "video": str(VIDEO_PATH),
        "video_width": width,
        "video_height": height,
        "reference_frame_index": reference_frame_index,
        "polygon": [
            {"x": x, "y": y}
            for x, y in points
        ],
    }

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            config,
            output_file,
            indent=2,
        )

        output_file.write("\n")

    print()
    print(f"Saved {len(points)} polygon points to: {OUTPUT_PATH}")