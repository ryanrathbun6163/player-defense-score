import argparse
import csv
import json
from pathlib import Path


DEFAULT_DETECTOR_THRESHOLD = 0.15
DEFAULT_TRACK_ACTIVATION_THRESHOLD = 0.35
DEFAULT_HIGH_CONFIDENCE_THRESHOLD = 0.35
DEFAULT_LOST_TRACK_BUFFER = 30
DEFAULT_MINIMUM_CONSECUTIVE_FRAMES = 2
DEFAULT_MINIMUM_IOU_THRESHOLD = 0.1


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Run RF-DETR Medium and ByteTrack on people inside a configured "
            "playable-court polygon."
        )
    )
    parser.add_argument(
        "--video",
        type=Path,
        required=True,
        help="Source possession video.",
    )
    parser.add_argument(
        "--court-config",
        type=Path,
        required=True,
        help="Playable-court polygon JSON.",
    )
    parser.add_argument(
        "--output-video",
        type=Path,
        required=True,
        help="Annotated tracking MP4.",
    )
    parser.add_argument(
        "--output-tracks",
        type=Path,
        required=True,
        help="Court-filtered tracking CSV.",
    )
    parser.add_argument(
        "--detector-threshold",
        type=float,
        default=DEFAULT_DETECTOR_THRESHOLD,
        help="RF-DETR person-detection threshold.",
    )
    parser.add_argument(
        "--track-activation-threshold",
        type=float,
        default=DEFAULT_TRACK_ACTIVATION_THRESHOLD,
        help="Confidence required to establish a new ByteTrack track.",
    )
    parser.add_argument(
        "--high-confidence-threshold",
        type=float,
        default=DEFAULT_HIGH_CONFIDENCE_THRESHOLD,
        help="ByteTrack strong/weak detection threshold.",
    )
    parser.add_argument(
        "--lost-track-buffer",
        type=int,
        default=DEFAULT_LOST_TRACK_BUFFER,
        help="Frames for which ByteTrack retains a lost track.",
    )
    parser.add_argument(
        "--minimum-consecutive-frames",
        type=int,
        default=DEFAULT_MINIMUM_CONSECUTIVE_FRAMES,
        help="Consecutive observations required to confirm a track.",
    )
    parser.add_argument(
        "--minimum-iou-threshold",
        type=float,
        default=DEFAULT_MINIMUM_IOU_THRESHOLD,
        help="Minimum ByteTrack association IoU.",
    )
    args = parser.parse_args(argv)

    for name in (
        "detector_threshold",
        "track_activation_threshold",
        "high_confidence_threshold",
        "minimum_iou_threshold",
    ):
        value = getattr(args, name)

        if not 0.0 <= value <= 1.0:
            parser.error(f"--{name.replace('_', '-')} must be in [0, 1]")

    if args.lost_track_buffer < 1:
        parser.error("--lost-track-buffer must be positive")

    if args.minimum_consecutive_frames < 1:
        parser.error("--minimum-consecutive-frames must be positive")

    return args


def load_court_config(path):
    import numpy as np

    if not path.exists():
        raise FileNotFoundError(f"Court configuration not found: {path}")

    with path.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    required_fields = {"video_width", "video_height", "polygon"}
    missing_fields = sorted(required_fields - set(config))

    if missing_fields:
        raise ValueError(
            f"Court configuration is missing fields: {missing_fields}"
        )

    polygon = np.array(
        [
            [point["x"], point["y"]]
            for point in config["polygon"]
        ],
        dtype=np.int32,
    )

    if len(polygon) < 3:
        raise ValueError("Court polygon must contain at least three points")

    return config, polygon


def run_tracking(args):
    import cv2
    import numpy as np
    import torch
    from rfdetr import RFDETRMedium
    from trackers import ByteTrackTracker
    from tqdm import tqdm

    court_config, court_polygon = load_court_config(args.court_config)
    capture = cv2.VideoCapture(str(args.video))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {args.video}")

    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
        capture.release()
        raise ValueError(
            "Invalid source-video metadata: "
            f"fps={fps}, frames={frame_count}, resolution={width}x{height}"
        )

    config_width = int(court_config["video_width"])
    config_height = int(court_config["video_height"])

    if width != config_width or height != config_height:
        capture.release()
        raise ValueError(
            "Court configuration resolution does not match video: "
            f"config={config_width}x{config_height}, "
            f"video={width}x{height}"
        )

    args.output_video.parent.mkdir(parents=True, exist_ok=True)
    args.output_tracks.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(args.output_video),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    if not writer.isOpened():
        capture.release()
        raise RuntimeError(f"Could not create output video: {args.output_video}")

    print(f"Video: {args.video}")
    print(f"Resolution: {width}x{height}")
    print(f"FPS: {fps:.2f}")
    print(f"Frames: {frame_count}")
    print(f"Court configuration: {args.court_config}")
    print(f"Court polygon points: {len(court_polygon)}")

    processed_frames = 0
    total_people_detected = 0
    total_people_inside_court = 0
    total_confirmed_tracks = 0
    unique_track_ids = set()

    try:
        print("\nLoading RF-DETR Medium...")
        model = RFDETRMedium()
        print("Optimizing RF-DETR for GPU inference...")
        model.inference(dtype=torch.float16)
        tracker = ByteTrackTracker(
            frame_rate=fps,
            lost_track_buffer=args.lost_track_buffer,
            track_activation_threshold=args.track_activation_threshold,
            minimum_consecutive_frames=args.minimum_consecutive_frames,
            minimum_iou_threshold=args.minimum_iou_threshold,
            high_conf_det_threshold=args.high_confidence_threshold,
        )

        with args.output_tracks.open(
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

            for frame_index in tqdm(
                range(frame_count),
                desc="Tracking video",
            ):
                success, frame_bgr = capture.read()

                if not success:
                    break

                processed_frames += 1
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                detections = model.predict(
                    frame_rgb,
                    threshold=args.detector_threshold,
                )
                class_names = np.array(detections.data["class_name"])
                person_detections = detections[class_names == "person"]
                detected_people_count = len(person_detections)
                total_people_detected += detected_people_count
                court_mask = []

                for box in person_detections.xyxy:
                    x1, _y1, x2, y2 = box
                    floor_x = float((x1 + x2) / 2)
                    floor_y = float(y2)
                    court_mask.append(
                        cv2.pointPolygonTest(
                            court_polygon,
                            (floor_x, floor_y),
                            False,
                        )
                        >= 0
                    )

                court_detections = person_detections[
                    np.array(court_mask, dtype=bool)
                ]
                inside_court_count = len(court_detections)
                total_people_inside_court += inside_court_count
                tracked_detections = tracker.update(court_detections)

                if tracked_detections.tracker_id is not None:
                    confirmed = tracked_detections[
                        tracked_detections.tracker_id != -1
                    ]
                else:
                    confirmed = tracked_detections

                annotated_frame = frame_bgr.copy()
                polygon_overlay = annotated_frame.copy()
                cv2.fillPoly(
                    polygon_overlay,
                    [court_polygon],
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
                    [court_polygon],
                    isClosed=True,
                    color=(0, 255, 255),
                    thickness=3,
                )

                if confirmed.tracker_id is not None and len(confirmed) > 0:
                    total_confirmed_tracks += len(confirmed)

                    for box, confidence, track_id in zip(
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
                        cv2.putText(
                            annotated_frame,
                            f"ID {track_id} {confidence:.2f}",
                            (int(x1), max(int(y1) - 8, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            (0, 255, 0),
                            2,
                        )
                        floor_x = (x1 + x2) / 2
                        floor_y = y2
                        cv2.circle(
                            annotated_frame,
                            (int(floor_x), int(floor_y)),
                            4,
                            (0, 0, 255),
                            -1,
                        )
                        csv_writer.writerow(
                            [
                                frame_index,
                                frame_index / fps,
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

                count_label = (
                    f"People detected: {detected_people_count} | "
                    f"Inside court: {inside_court_count} | "
                    f"Confirmed tracks: {len(confirmed)}"
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
                writer.write(annotated_frame)
    finally:
        capture.release()
        writer.release()

    if processed_frames > 0:
        average_people_detected = total_people_detected / processed_frames
        average_people_inside_court = (
            total_people_inside_court / processed_frames
        )
        average_confirmed_tracks = total_confirmed_tracks / processed_frames
    else:
        average_people_detected = 0.0
        average_people_inside_court = 0.0
        average_confirmed_tracks = 0.0

    summary = {
        "processed_frames": processed_frames,
        "average_people_detected": average_people_detected,
        "average_people_inside_court": average_people_inside_court,
        "average_confirmed_tracks": average_confirmed_tracks,
        "unique_track_ids": len(unique_track_ids),
    }
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
    print(f"Unique court-filtered track IDs: {len(unique_track_ids)}")
    print(f"Video saved to: {args.output_video}")
    print(f"CSV saved to:   {args.output_tracks}")
    return summary


def main(argv=None):
    args = parse_args(argv)
    run_tracking(args)


if __name__ == "__main__":
    main()
