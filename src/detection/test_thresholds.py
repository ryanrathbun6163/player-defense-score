from pathlib import Path

import numpy as np
from rfdetr import RFDETRMedium


image_path = Path("data/outputs/frame_candidates/frame_06s.jpg")

print("Loading model...")
model = RFDETRMedium()

thresholds = [0.35, 0.25, 0.15, 0.10]

for threshold in thresholds:
    print(f"\n--- Threshold: {threshold} ---")

    detections = model.predict(
        str(image_path),
        threshold=threshold,
    )

    class_names = np.array(detections.data["class_name"])
    confidences = detections.confidence

    unique_classes, counts = np.unique(
        class_names,
        return_counts=True,
    )

    for cls_name, count in zip(unique_classes, counts):
        print(f"{cls_name}: {count}")

    print("\nSports ball detections:")

    ball_mask = class_names == "sports ball"

    if not ball_mask.any():
        print("  None")
    else:
        for conf, box in zip(
            confidences[ball_mask],
            detections.xyxy[ball_mask],
        ):
            print(
                f"  confidence={conf:.3f}, "
                f"box={box}"
            )