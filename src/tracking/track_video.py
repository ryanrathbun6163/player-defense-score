import csv
import json
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
COURT_CONFIG_PATH = Path("configs/possession_001_court.json")

OUTPUT_DIR = Path("data/outputs/tracking")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_OUTPUT_PATH = (
    OUTPUT_DIR / "possession_001_court_filtered.mp4"
)

CSV_OUTPUT_PATH = (
    OUTPUT_DIR / "possession_001_court_filtered_tracks.csv"
)


# ---------------------------------------------------------
# Detection and tracking settings
# ---------------------------------------------------------

# RF-DETR returns lower-confidence people so ByteTrack can
# use them to recover existing tracks.

DETECTOR_THRESHOLD = 0.15

# A detection must reach this confidence to establish a new
# track.

TRACK_ACTIVATION_THRESHOLD = 0.35

# Separates ByteTrack's strong and weak detections.

HIGH_CONF_THRESHOLD = 0.35


# ---------------------------------------------------------
# Load court polygon configuration
# ---------------------------------------------------------

if not COURT_CONFIG_PATH.exists():
    raise FileNotFoundError(
        f"Court configuration not found: {COURT_CONFIG_PATH}"
    )

with COURT_CONFIG_PATH.open(
    "r",
    encoding="utf-8",
) as config_file:
    court_config = json.load(config_file)

COURT_POLYGON = np.array(
    [
        [point["x"], point["y"]]
        for point in court_config["polygon"]
    ],
    dtype=np.int32,
)

if len(COURT_POLYGON) < 3:
    raise ValueError(
        "Court polygon must contain at least three points"
    )


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

config_width = int(court_config["video_width"])
config_height = int(court_config["video_height"])

if width != config_width or height != config_height:
    cap.release()

    raise ValueError(
        "Court configuration resolution does not match video: "
        f"config={config_width}x{config_height}, "
        f"video={width}x{height}"
    )

print(f"Video: {VIDEO_PATH}")
print(f"Resolution: {width}x{height}")
print(f"FPS: {fps:.2f}")
print(f"Frames: {frame_count}")
print(f"Court configuration: {COURT_CONFIG_PATH}")
print(f"Court polygon points: {len(COURT_POLYGON)}")


# ---------------------------------------------------------
# Create output video writer
# ---------------------------------------------------------

fourcc = cv2.VideoWriter_fourcc(*"mp4v")

writer = cv2.VideoWriter(
    str(VIDEO_OUTPUT_PATH),
    fourcc,
    fps,
    (width, height),
)

if not writer.isOpened():
    cap.release()
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
    track_activation_threshold=(
        TRACK_ACTIVATION_THRESHOLD
    ),
    minimum_consecutive_frames=2,
    minimum_iou_threshold=0.1,
    high_conf_det_threshold=HIGH_CONF_THRESHOLD,
)


# ---------------------------------------------------------
# Tracking summary counters
# ---------------------------------------------------------

processed_frames = 0
total_people_detected = 0
total_people_inside_court = 0
total_confirmed_tracks = 0
unique_track_ids = set()


# ---------------------------------------------------------
# CSV output and frame processing
# ---------------------------------------------------------

with CSV_OUTPUT_PATH.open(
    "w",
    newline="",
    encoding="utf-8",
) as csv_file:
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

    try:
        for frame_index in tqdm(
            range(frame_count),
            desc="Tracking video",
        ):
            success, frame_bgr = cap.read()

            if not success:
                break

            processed_frames += 1

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

            detected_people_count = len(
                person_detections
            )

            total_people_detected += (
                detected_people_count
            )

            # ---------------------------------------------
            # 3. Keep people whose floor point is inside
            #    the configured playable-court polygon
            # ---------------------------------------------

            court_mask = []

            for box in person_detections.xyxy:
                x1, y1, x2, y2 = box

                floor_x = float((x1 + x2) / 2)
                floor_y = float(y2)

                inside_court = (
                    cv2.pointPolygonTest(
                        COURT_POLYGON,
                        (floor_x, floor_y),
                        False,
                    )
                    >= 0
                )

                court_mask.append(inside_court)

            court_mask = np.array(
                court_mask,
                dtype=bool,
            )

            court_detections = person_detections[
                court_mask
            ]

            inside_court_count = len(
                court_detections
            )

            total_people_inside_court += (
                inside_court_count
            )

            # ---------------------------------------------
            # 4. Give only court detections to ByteTrack
            # ---------------------------------------------

            tracked_detections = tracker.update(
                court_detections
            )

            # ByteTrack uses -1 for detections that do not
            # yet belong to a confirmed track.

            if (
                tracked_detections.tracker_id
                is not None
            ):
                confirmed_mask = (
                    tracked_detections.tracker_id
                    != -1
                )

                confirmed = tracked_detections[
                    confirmed_mask
                ]

            else:
                confirmed = tracked_detections

            # ---------------------------------------------
            # 5. Draw court polygon and tracking results
            # ---------------------------------------------

            annotated_frame = frame_bgr.copy()

            polygon_overlay = annotated_frame.copy()

            cv2.fillPoly(
                polygon_overlay,
                [COURT_POLYGON],
                color=(0, 255, 255),
            )

            cv2.addWeighted(
                polygon_overlay,
                0.08,
                annotated_frame,
                0.92,
                0,
                annotated_frame,
            )

            cv2.polylines(
                annotated_frame,
                [COURT_POLYGON],
                isClosed=True,
                color=(0, 255, 255),
                thickness=3,
            )

            if (
                confirmed.tracker_id is not None
                and len(confirmed) > 0
            ):
                total_confirmed_tracks += len(
                    confirmed
                )

                for (
                    box,
                    confidence,
                    track_id,
                ) in zip(
                    confirmed.xyxy,
                    confirmed.confidence,
                    confirmed.tracker_id,
                ):
                    x1, y1, x2, y2 = box

                    track_id = int(track_id)
                    unique_track_ids.add(track_id)

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
            # 6. Draw per-frame detection counts
            # ---------------------------------------------

            count_label = (
                f"People detected: "
                f"{detected_people_count} | "
                f"Inside court: "
                f"{inside_court_count} | "
                f"Confirmed tracks: "
                f"{len(confirmed)}"
            )

            cv2.rectangle(
                annotated_frame,
                (15, 15),
                (760, 58),
                (0, 0, 0),
                -1,
            )

            cv2.putText(
                annotated_frame,
                count_label,
                (25, 45),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )

            # ---------------------------------------------
            # 7. Save annotated frame
            # ---------------------------------------------

            writer.write(annotated_frame)

    finally:
        cap.release()
        writer.release()


# ---------------------------------------------------------
# Print run summary
# ---------------------------------------------------------

if processed_frames > 0:
    average_people_detected = (
        total_people_detected / processed_frames
    )

    average_people_inside_court = (
        total_people_inside_court / processed_frames
    )

    average_confirmed_tracks = (
        total_confirmed_tracks / processed_frames
    )

else:
    average_people_detected = 0.0
    average_people_inside_court = 0.0
    average_confirmed_tracks = 0.0

print("\nTracking complete.")
print(f"Frames processed: {processed_frames}")
print(
    "Average people detected per frame: "
    f"{average_people_detected:.2f}"
)
print(
    "Average people inside court per frame: "
    f"{average_people_inside_court:.2f}"
)
print(
    "Average confirmed tracks per frame: "
    f"{average_confirmed_tracks:.2f}"
)
print(
    f"Unique court-filtered track IDs: "
    f"{len(unique_track_ids)}"
)
print(f"Video saved to: {VIDEO_OUTPUT_PATH}")
print(f"CSV saved to:   {CSV_OUTPUT_PATH}")