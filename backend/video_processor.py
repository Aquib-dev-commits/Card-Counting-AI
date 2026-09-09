import cv2
from pathlib import Path


VIDEO_PATH = Path(__file__).parent / "sample.mp4"


def read_video():

    cap = cv2.VideoCapture(str(VIDEO_PATH))

    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {VIDEO_PATH}")

    frame_number = 0

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        frame_number += 1

        # Resize for processing
        frame = cv2.resize(frame, (640, 360))

        yield frame_number, frame

    cap.release()