from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from rfdetr import RFDETRMedium


IMAGE_PATH = Path("data/outputs/frame_candidates/frame_06s.jpg")
OUTPUT_PATH = Path("data/outputs/rfdetr_test/frame_06s_clean.jpg")

PERSON_THRESHOLD = 0.35
BALL_THRESHOLD = 0.25


print("Loading RF-DETR...")
model = RFDETRMedium()

print("Running inference...")

# We need 0.25 here so the model returns the basketball.
detections = model.predict(
    str(IMAGE_PATH),
    threshold=BALL_THRESHOLD,
)

class_names = np.array(detections.data["class_name"])
confidences = detections.confidence


# Apply different confidence requirements depending on object type.
person_mask = (
    (class_names == "person")
    & (confidences >= PERSON_THRESHOLD)
)

ball_mask = (
    (class_names == "sports ball")
    & (confidences >= BALL_THRESHOLD)
)

keep_mask = person_mask | ball_mask

filtered_detections = detections[keep_mask]
filtered_names = class_names[keep_mask]


print(
    f"People kept: "
    f"{np.sum(filtered_names == 'person')}"
)

print(
    f"Balls kept: "
    f"{np.sum(filtered_names == 'sports ball')}"
)


image = cv2.imread(str(IMAGE_PATH))

box_annotator = sv.BoxAnnotator(thickness=2)
label_annotator = sv.LabelAnnotator(
    text_scale=0.4,
    text_thickness=1,
)

labels = [
    f"{class_name} {confidence:.2f}"
    for class_name, confidence in zip(
        filtered_names,
        filtered_detections.confidence,
    )
]

annotated = image.copy()

annotated = box_annotator.annotate(
    scene=annotated,
    detections=filtered_detections,
)

annotated = label_annotator.annotate(
    scene=annotated,
    detections=filtered_detections,
    labels=labels,
)

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

cv2.imwrite(
    str(OUTPUT_PATH),
    annotated,
)

print(f"Saved: {OUTPUT_PATH}")