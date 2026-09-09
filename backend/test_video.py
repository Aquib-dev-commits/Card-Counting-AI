import cv2
from video_processor import read_video


for frame_number, frame in read_video():

    print(f"Frame: {frame_number}")

    cv2.imshow("Sample Video", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cv2.destroyAllWindows()