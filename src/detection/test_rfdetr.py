import csv
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from rfdetr import RFDETRMedium


image_path = Path("data/outputs/frame_candidates/frame_06s.jpg")
output_dir = Path("data/outputs/rfdetr_test")
output_dir.mkdir(parents=True, exist_ok=True)

all_output_path = output_dir / "frame_06s_all_detections.jpg"
filtered_output_path = output_dir / "frame_06s_person_ball_only.jpg"
csv_output_path = output_dir / "frame_06s_detections.csv"

image = cv2.imread(str(image_path))
if image is None:
    raise FileNotFoundError(f"Could not load image: {image_path}")

print("Loading RF-DETR model...")
model = RFDETRMedium()

print("Running inference...")
detections = model.predict(str(image_path), threshold=0.35)

class_names = np.array(detections.data["class_name"])
confidences = detections.confidence
xyxy = detections.xyxy

# Save raw detections to CSV so you can inspect the actual structured output
with open(csv_output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["class_name", "confidence", "x1", "y1", "x2", "y2"])

    for cls_name, conf, box in zip(class_names, confidences, xyxy):
        x1, y1, x2, y2 = box
        writer.writerow([cls_name, float(conf), float(x1), float(y1), float(x2), float(y2)])

# Annotate ALL detections
box_annotator = sv.BoxAnnotator(thickness=2)
label_annotator = sv.LabelAnnotator(text_scale=0.4, text_thickness=1)

all_labels = [
    f"{cls_name} {conf:.2f}"
    for cls_name, conf in zip(class_names, confidences)
]

annotated_all = image.copy()
annotated_all = box_annotator.annotate(scene=annotated_all, detections=detections)
annotated_all = label_annotator.annotate(
    scene=annotated_all,
    detections=detections,
    labels=all_labels,
)

cv2.imwrite(str(all_output_path), annotated_all)

# Filter to just the classes we care about right now
keep_mask = np.isin(class_names, ["person", "sports ball"])
filtered_detections = detections[keep_mask]
filtered_names = class_names[keep_mask]

filtered_labels = [
    f"{cls_name} {conf:.2f}"
    for cls_name, conf in zip(filtered_names, filtered_detections.confidence)
]

annotated_filtered = image.copy()
annotated_filtered = box_annotator.annotate(scene=annotated_filtered, detections=filtered_detections)
annotated_filtered = label_annotator.annotate(
    scene=annotated_filtered,
    detections=filtered_detections,
    labels=filtered_labels,
)

cv2.imwrite(str(filtered_output_path), annotated_filtered)

# Print a quick summary
unique_classes, counts = np.unique(class_names, return_counts=True)

print("\nDetection summary:")
for cls_name, count in zip(unique_classes, counts):
    print(f"  {cls_name}: {count}")

print(f"\nTotal detections: {len(detections)}")
print(f"Person/ball detections kept: {len(filtered_detections)}")

print(f"\nSaved:")
print(f"  All detections image: {all_output_path}")
print(f"  Person/ball image:    {filtered_output_path}")
print(f"  CSV output:           {csv_output_path}")