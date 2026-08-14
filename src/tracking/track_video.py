import csv
from pathlib import Path

import cv2
import numpy as np
import torch
from rfdetr import RFDETRMedium
from trackers import ByteTrackTracker
from tqdm import tqdm


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

VIDEO_PATH = Path("data/clips/possession_001.mp4")

OUTPUT_DIR = Path("data/outputs/tracking")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_OUTPUT_PATH = OUTPUT_DIR / "possession_001_tracked.mp4"
CSV_OUTPUT_PATH = OUTPUT_DIR / "possession_001_tracks.csv"


# ---------------------------------------------------------
# Detection / tracking settings
# ---------------------------------------------------------

# Ask RF-DETR for lower-confidence people too.
# ByteTrack can use these to recover an existing track.
DETECTOR_THRESHOLD = 0.15

# A detection must be at least this confident to establish
# a new track.
TRACK_ACTIVATION_THRESHOLD = 0.35

# Separates ByteTrack's strong and weak detections.
HIGH_CONF_THRESHOLD = 0.35


# ---------------------------------------------------------
# Open input video
# ---------------------------------------------------------

cap = cv2.VideoCapture(str(VIDEO_PATH))

if not cap.isOpened():
    raise RuntimeError(f"Could not open video: {VIDEO_PATH}")

fps = cap.get(cv2.CAP_PROP_FPS)
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"Video: {VIDEO_PATH}")
print(f"Resolution: {width}x{height}")
print(f"FPS: {fps:.2f}")
print(f"Frames: {frame_count}")


# ---------------------------------------------------------
# Output video writer
# ---------------------------------------------------------

fourcc = cv2.VideoWriter_fourcc(*"mp4v")

writer = cv2.VideoWriter(
    str(VIDEO_OUTPUT_PATH),
    fourcc,
    fps,
    (width, height),
)

if not writer.isOpened():
    raise RuntimeError("Could not create output video")


# ---------------------------------------------------------
# Load RF-DETR
# ---------------------------------------------------------

print("\nLoading RF-DETR Medium...")

model = RFDETRMedium()

print("Optimizing RF-DETR for GPU inference...")

model.inference(
    dtype=torch.float16,
)


# ---------------------------------------------------------
# Create ByteTrack tracker
# ---------------------------------------------------------

tracker = ByteTrackTracker(
    frame_rate=fps,
    lost_track_buffer=30,
    track_activation_threshold=TRACK_ACTIVATION_THRESHOLD,
    minimum_consecutive_frames=2,
    minimum_iou_threshold=0.1,
    high_conf_det_threshold=HIGH_CONF_THRESHOLD,
)


# ---------------------------------------------------------
# CSV output
# ---------------------------------------------------------

csv_file = open(
    CSV_OUTPUT_PATH,
    "w",
    newline="",
    encoding="utf-8",
)

csv_writer = csv.writer(csv_file)

csv_writer.writerow(
    [
        "frame_index",
        "timestamp_sec",
        "track_id",
        "confidence",
        "x1",
        "y1",
        "x2",
        "y2",
        "floor_x",
        "floor_y",
    ]
)


# ---------------------------------------------------------
# Process every frame
# ---------------------------------------------------------

for frame_index in tqdm(
    range(frame_count),
    desc="Tracking video",
):

    success, frame_bgr = cap.read()

    if not success:
        break

    # RF-DETR expects RGB input.
    frame_rgb = cv2.cvtColor(
        frame_bgr,
        cv2.COLOR_BGR2RGB,
    )

    # ---------------------------------------------
    # 1. Detect objects
    # ---------------------------------------------

    detections = model.predict(
        frame_rgb,
        threshold=DETECTOR_THRESHOLD,
    )

    class_names = np.array(
        detections.data["class_name"]
    )

    # ---------------------------------------------
    # 2. Keep only people
    # ---------------------------------------------

    person_mask = class_names == "person"

    person_detections = detections[
        person_mask
    ]

    # ---------------------------------------------
    # 3. Give detections to ByteTrack
    # ---------------------------------------------

    tracked_detections = tracker.update(
        person_detections
    )

    # ByteTrack uses -1 for detections that do not
    # yet belong to a confirmed track.
    if tracked_detections.tracker_id is not None:

        confirmed_mask = (
            tracked_detections.tracker_id != -1
        )

        confirmed = tracked_detections[
            confirmed_mask
        ]

    else:
        confirmed = tracked_detections

    # ---------------------------------------------
    # 4. Draw tracked people
    # ---------------------------------------------

    annotated_frame = frame_bgr.copy()

    if (
        confirmed.tracker_id is not None
        and len(confirmed) > 0
    ):

        for box, confidence, track_id in zip(
            confirmed.xyxy,
            confirmed.confidence,
            confirmed.tracker_id,
        ):

            x1, y1, x2, y2 = box

            track_id = int(track_id)

            # Bounding box
            cv2.rectangle(
                annotated_frame,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                (0, 255, 0),
                2,
            )

            label = (
                f"ID {track_id} "
                f"{confidence:.2f}"
            )

            cv2.putText(
                annotated_frame,
                label,
                (
                    int(x1),
                    max(int(y1) - 8, 20),
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 0),
                2,
            )

            # -------------------------------------
            # Approximate player's floor position
            # -------------------------------------

            floor_x = (x1 + x2) / 2
            floor_y = y2

            cv2.circle(
                annotated_frame,
                (
                    int(floor_x),
                    int(floor_y),
                ),
                4,
                (0, 0, 255),
                -1,
            )

            # -------------------------------------
            # Write structured tracking data
            # -------------------------------------

            timestamp_sec = (
                frame_index / fps
            )

            csv_writer.writerow(
                [
                    frame_index,
                    timestamp_sec,
                    track_id,
                    float(confidence),
                    float(x1),
                    float(y1),
                    float(x2),
                    float(y2),
                    float(floor_x),
                    float(floor_y),
                ]
            )

    # ---------------------------------------------
    # 5. Save annotated frame to output video
    # ---------------------------------------------

    writer.write(
        annotated_frame
    )


# ---------------------------------------------------------
# Cleanup
# ---------------------------------------------------------

cap.release()
writer.release()
csv_file.close()

print("\nTracking complete.")
print(f"Video saved to: {VIDEO_OUTPUT_PATH}")
print(f"CSV saved to:   {CSV_OUTPUT_PATH}")