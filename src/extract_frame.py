import cv2
from pathlib import Path

video_path = Path("data/clips/possession_001.mp4")
output_dir = Path("data/outputs/frame_candidates")
output_dir.mkdir(parents=True, exist_ok=True)

cap = cv2.VideoCapture(str(video_path))

if not cap.isOpened():
    raise RuntimeError(f"Could not open video: {video_path}")

fps = cap.get(cv2.CAP_PROP_FPS)

# Extract a frame every 2 seconds
timestamps = [2, 4, 6, 8, 10, 12, 14, 16, 18]

for timestamp in timestamps:
    target_frame = int(timestamp * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

    success, frame = cap.read()

    if not success:
        print(f"Could not read frame at {timestamp}s")
        continue

    output_path = output_dir / f"frame_{timestamp:02d}s.jpg"
    cv2.imwrite(str(output_path), frame)

    print(f"Saved {timestamp}s -> {output_path}")

cap.release()