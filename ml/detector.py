from pathlib import Path
from ultralytics import YOLO


MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "card_detector.pt"
)


class CardDetector:
    def __init__(self):
        self.model = YOLO(str(MODEL_PATH))

    def detect(self, frame):
        results = self.model.predict(
            source=frame,
            imgsz=416,
            conf=0.25,
            verbose=False,
            device="cpu"
        )

        detections = []

        result = results[0]

        if result.boxes is None:
            return detections

        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])

            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0].tolist()
            )

            detections.append({
    "card": self.model.names[class_id],
    "class_id": class_id,
    "confidence": confidence,
    "box": [x1, y1, x2, y2],
    "frame_width": frame.shape[1],
    "frame_height": frame.shape[0]
})

        return detections