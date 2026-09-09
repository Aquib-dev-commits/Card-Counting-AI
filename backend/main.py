import asyncio
import base64
import os
import tempfile
import time
import uuid
from pathlib import Path

import cv2

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)

from fastapi.middleware.cors import CORSMiddleware

from ml.detector import CardDetector
from ml.tracker import CardTracker
from ml.counter import CardCounter


app = FastAPI(
    title="Card Counting AI"
)


# ==================================================
# CORS
# ==================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# YOLO
# Load model only once
# ==================================================

detector = CardDetector()


# ==================================================
# UPLOAD DIRECTORY
# ==================================================

UPLOAD_DIR = (
    Path(tempfile.gettempdir())
    / "card_counting_ai"
)

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ==================================================
# PROCESSING SETTINGS
# ==================================================

MAX_PROCESSING_SIZE = 960


# ==================================================
# YOLO INFERENCE INTERVAL
# ==================================================

DETECTION_INTERVAL = 0.20


# ==================================================
# JPEG QUALITY
# ==================================================

JPEG_QUALITY = 75


# ==================================================
# RESIZE FRAME
# ==================================================

def resize_frame(frame):

    height, width = frame.shape[:2]

    largest_dimension = max(
        width,
        height
    )

    if largest_dimension <= MAX_PROCESSING_SIZE:
        return frame

    scale = (
        MAX_PROCESSING_SIZE /
        largest_dimension
    )

    new_width = max(
        1,
        int(width * scale)
    )

    new_height = max(
        1,
        int(height * scale)
    )

    return cv2.resize(
        frame,
        (
            new_width,
            new_height
        ),
        interpolation=cv2.INTER_AREA
    )


# ==================================================
# HEALTH CHECK
# ==================================================

@app.get("/health")
async def health_check():

    return {
        "status": "ok",
        "message":
            "Card Counting AI backend is running"
    }


# ==================================================
# UPLOAD VIDEO
# ==================================================

@app.post("/upload-video")
async def upload_video(
    file: UploadFile = File(...)
):

    extension = Path(
        file.filename or ""
    ).suffix.lower()

    allowed_extensions = {
        ".mp4",
        ".avi",
        ".mov",
        ".mkv",
        ".webm"
    }

    if extension not in allowed_extensions:

        return {
            "status": "error",
            "message":
                "Unsupported video format"
        }

    video_id = str(
        uuid.uuid4()
    )

    video_path = (
        UPLOAD_DIR /
        f"{video_id}{extension}"
    )

    with open(
        video_path,
        "wb"
    ) as buffer:

        while True:

            chunk = await file.read(
                1024 * 1024
            )

            if not chunk:
                break

            buffer.write(
                chunk
            )

    return {
        "status": "ok",
        "video_id": video_id,
        "filename": file.filename
    }


# ==================================================
# WEBSOCKET
# ==================================================

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket
):

    await websocket.accept()

    print(
        "WebSocket client connected"
    )

    video_path = None
    cap = None

    command_task = None
    detection_task = None

    # ==================================================
    # TRACKER
    # ==================================================

    tracker = CardTracker(
        iou_threshold=0.35,
        max_missed=3,
        smoothing_alpha=0.6
    )

    tracker_lock = asyncio.Lock()


    # ==================================================
    # COUNTER
    # ==================================================

    counter = CardCounter(
        deck_size=52
    )

    counter_lock = asyncio.Lock()


    try:

        # ==================================================
        # WAIT FOR LOAD
        # ==================================================

        first_message = (
            await websocket.receive_json()
        )

        if (
            first_message.get("action")
            != "load"
        ):

            await websocket.send_json({

                "type": "error",

                "message":
                    "Send a load command first"

            })

            return


        video_id = (
            first_message.get(
                "video_id"
            )
        )


        if not video_id:

            await websocket.send_json({

                "type": "error",

                "message":
                    "video_id missing"

            })

            return


        # ==================================================
        # FIND VIDEO
        # ==================================================

        matches = list(
            UPLOAD_DIR.glob(
                f"{video_id}.*"
            )
        )


        if not matches:

            await websocket.send_json({

                "type": "error",

                "message":
                    "Video not found"

            })

            return


        video_path = matches[0]


        # ==================================================
        # OPEN VIDEO
        # ==================================================

        cap = cv2.VideoCapture(
            str(video_path)
        )


        if not cap.isOpened():

            await websocket.send_json({

                "type": "error",

                "message":
                    "Could not open uploaded video"

            })

            return


        # ==================================================
        # VIDEO INFORMATION
        # ==================================================

        source_fps = cap.get(
            cv2.CAP_PROP_FPS
        )


        if source_fps <= 0:

            source_fps = 30.0


        total_frames = int(
            cap.get(
                cv2.CAP_PROP_FRAME_COUNT
            )
        )


        duration = (

            total_frames /
            source_fps

            if total_frames > 0

            else 0

        )


        frame_number = 0


        # ==================================================
        # PLAYBACK STATE
        # ==================================================

        state = {

            "paused": True,

            "ended": False,

            "speed": 1.0,

            "confidence": 0.70,

        }


        # ==================================================
        # LATEST DETECTIONS
        # ==================================================

        latest_detections = []

        latest_detection_lock = (
            asyncio.Lock()
        )


        # ==================================================
        # LATEST FRAME
        # ==================================================

        latest_frame = None

        latest_frame_lock = (
            asyncio.Lock()
        )


        # ==================================================
        # RESET EVERYTHING
        # ==================================================

        async def reset_processing():

            nonlocal latest_detections
            nonlocal latest_frame

            async with (
                latest_detection_lock
            ):

                latest_detections = []


            async with (
                latest_frame_lock
            ):

                latest_frame = None


            async with tracker_lock:

                tracker.reset()


            async with counter_lock:

                counter.reset()


        # ==================================================
        # COMMAND LISTENER
        # ==================================================

        async def command_listener():

            nonlocal frame_number

            try:

                while True:

                    command = (
                        await websocket.receive_json()
                    )

                    action = command.get(
                        "action"
                    )


                    # ==========================================
                    # PLAY
                    # ==========================================

                    if action == "play":

                        if state["ended"]:

                            cap.set(
                                cv2.CAP_PROP_POS_FRAMES,
                                0
                            )

                            frame_number = 0

                            state["ended"] = False

                            await reset_processing()


                        state["paused"] = False


                    # ==========================================
                    # PAUSE
                    # ==========================================

                    elif action == "pause":

                        state["paused"] = True


                    # ==========================================
                    # CONFIDENCE
                    # ==========================================

                    elif action == "threshold":

                        value = float(
                            command.get(
                                "value",
                                0.70
                            )
                        )

                        state["confidence"] = max(
                            0.10,
                            min(
                                value,
                                0.95
                            )
                        )


                    # ==========================================
                    # SPEED
                    # ==========================================

                    elif action == "speed":

                        value = float(
                            command.get(
                                "value",
                                1.0
                            )
                        )

                        state["speed"] = max(
                            0.25,
                            min(
                                value,
                                4.0
                            )
                        )


                    # ==========================================
                    # SEEK
                    # ==========================================

                    elif action == "seek":

                        position = float(
                            command.get(
                                "position",
                                0
                            )
                        )

                        position = max(
                            0,
                            min(
                                position,
                                duration
                            )
                        )


                        target_frame = int(
                            position *
                            source_fps
                        )


                        target_frame = max(
                            0,
                            min(
                                target_frame,
                                max(
                                    0,
                                    total_frames - 1
                                )
                            )
                        )


                        cap.set(
                            cv2.CAP_PROP_POS_FRAMES,
                            target_frame
                        )


                        frame_number = (
                            target_frame
                        )


                        state["ended"] = (

                            total_frames > 0

                            and

                            target_frame
                            >=
                            total_frames - 1

                        )


                        await reset_processing()


                    # ==========================================
                    # BACKWARD 5 SEC
                    # ==========================================

                    elif action == "backward":

                        target = max(

                            0,

                            frame_number -

                            int(
                                source_fps * 5
                            )

                        )


                        cap.set(
                            cv2.CAP_PROP_POS_FRAMES,
                            target
                        )


                        frame_number = target

                        state["ended"] = False


                        await reset_processing()


                    # ==========================================
                    # FORWARD 5 SEC
                    # ==========================================

                    elif action == "forward":

                        target = min(

                            max(
                                0,
                                total_frames - 1
                            ),

                            frame_number +

                            int(
                                source_fps * 5
                            )

                        )


                        cap.set(
                            cv2.CAP_PROP_POS_FRAMES,
                            target
                        )


                        frame_number = target


                        state["ended"] = (

                            total_frames > 0

                            and

                            target
                            >=
                            total_frames - 1

                        )


                        await reset_processing()


            except (
                WebSocketDisconnect,
                asyncio.CancelledError,
            ):

                pass


        # ==================================================
        # YOLO + TRACKER + COUNTER WORKER
        # ==================================================

        async def detection_worker():

            nonlocal latest_frame
            nonlocal latest_detections

            last_inference_time = 0.0


            try:

                while True:

                    # ==========================================
                    # GET LATEST FRAME
                    # ==========================================

                    async with (
                        latest_frame_lock
                    ):

                        frame_for_detection = (
                            latest_frame
                        )

                        latest_frame = None


                    if (
                        frame_for_detection
                        is None
                    ):

                        await asyncio.sleep(
                            0.01
                        )

                        continue


                    # ==========================================
                    # LIMIT YOLO RATE
                    # ==========================================

                    current_time = (
                        time.perf_counter()
                    )


                    if (
                        current_time -
                        last_inference_time
                        <
                        DETECTION_INTERVAL
                    ):

                        await asyncio.sleep(
                            0.01
                        )

                        continue


                    # ==========================================
                    # YOLO
                    # ==========================================

                    raw_detections = (

                        await asyncio.to_thread(

                            detector.detect,

                            frame_for_detection

                        )

                    )


                    # ==========================================
                    # CONFIDENCE FILTER
                    # ==========================================

                    threshold = (
                        state["confidence"]
                    )


                    filtered_detections = [

                        detection

                        for detection
                        in raw_detections

                        if detection[
                            "confidence"
                        ] >= threshold

                    ]


                    # ==========================================
                    # TRACKER
                    # ==========================================

                    async with tracker_lock:

                        stable_detections = (
                            tracker.update(
                                filtered_detections
                            )
                        )


                    # ==========================================
                    # COUNTER
                    # ==========================================

                    async with counter_lock:

                        count_stats = (
                            counter.update(
                                stable_detections
                            )
                        )


                    # ==========================================
                    # STORE DETECTIONS
                    # ==========================================

                    async with (
                        latest_detection_lock
                    ):

                        latest_detections = (
                            stable_detections
                        )


                    last_inference_time = (
                        time.perf_counter()
                    )


            except asyncio.CancelledError:

                pass


        # ==================================================
        # START BACKGROUND TASKS
        # ==================================================

        command_task = asyncio.create_task(
            command_listener()
        )


        detection_task = asyncio.create_task(
            detection_worker()
        )


        # ==================================================
        # MAIN PLAYBACK LOOP
        # ==================================================

        while True:

            # ==============================================
            # PAUSED
            # ==============================================

            if state["paused"]:

                await asyncio.sleep(
                    0.02
                )

                continue


            # ==============================================
            # ENDED
            # ==============================================

            if state["ended"]:

                await asyncio.sleep(
                    0.05
                )

                continue


            # ==============================================
            # READ FRAME
            # ==============================================

            ret, frame = cap.read()


            if not ret:

                state["ended"] = True

                state["paused"] = True


                async with (
                    latest_detection_lock
                ):

                    detections_to_send = list(
                        latest_detections
                    )


                async with counter_lock:

                    count_stats = (
                        counter.get_stats()
                    )


                await websocket.send_json({

                    "type":
                        "frame",

                    "ended":
                        True,

                    "playing":
                        False,

                    "position":
                        duration,

                    "duration":
                        duration,

                    "cards":
                        detections_to_send,

                    "confidence_threshold":
                        state["confidence"],

                    "running_count":
                        count_stats[
                            "running_count"
                        ],

                    "cards_counted":
                        count_stats[
                            "cards_counted"
                        ],

                    "cards_remaining":
                        count_stats[
                            "cards_remaining"
                        ],

                    "decks_remaining":
                        count_stats[
                            "decks_remaining"
                        ],

                    "true_count":
                        count_stats[
                            "true_count"
                        ],

                    "counted_cards":
                        count_stats[
                            "counted_cards"
                        ],

                })


                continue


            frame_number += 1


            # ==============================================
            # RESIZE
            # ==============================================

            processed_frame = (
                resize_frame(frame)
            )


            # ==============================================
            # FRAME SIZE
            # ==============================================

            processed_height, processed_width = (
                processed_frame.shape[:2]
            )


            # ==============================================
            # SEND LATEST FRAME TO YOLO
            # ==============================================

            async with (
                latest_frame_lock
            ):

                latest_frame = (
                    processed_frame.copy()
                )


            # ==============================================
            # GET DETECTIONS
            # ==============================================

            async with (
                latest_detection_lock
            ):

                detections_to_send = list(
                    latest_detections
                )


            # ==============================================
            # GET COUNTING STATS
            # ==============================================

            async with counter_lock:

                count_stats = (
                    counter.get_stats()
                )


            # ==============================================
            # JPEG ENCODE
            # ==============================================

            success, encoded = cv2.imencode(

                ".jpg",

                processed_frame,

                [
                    cv2.IMWRITE_JPEG_QUALITY,
                    JPEG_QUALITY
                ]

            )


            if not success:
                continue


            frame_base64 = (

                base64.b64encode(

                    encoded.tobytes()

                )
                .decode("utf-8")

            )


            # ==============================================
            # POSITION
            # ==============================================

            elapsed = (
                frame_number /
                source_fps
            )


            # ==============================================
            # SEND TO FRONTEND
            # ==============================================

            await websocket.send_json({

                "type":
                    "frame",

                "frame_number":
                    frame_number,

                "frame":
                    frame_base64,

                "fps":
                    source_fps,

                "position":
                    min(
                        elapsed,
                        duration
                    ),

                "duration":
                    duration,

                "cards":
                    detections_to_send,

                "confidence_threshold":
                    state["confidence"],

                "frame_width":
                    processed_width,

                "frame_height":
                    processed_height,

                "running_count":
                    count_stats[
                        "running_count"
                    ],

                "cards_counted":
                    count_stats[
                        "cards_counted"
                    ],

                "cards_remaining":
                    count_stats[
                        "cards_remaining"
                    ],

                "decks_remaining":
                    count_stats[
                        "decks_remaining"
                    ],

                "true_count":
                    count_stats[
                        "true_count"
                    ],

                "counted_cards":
                    count_stats[
                        "counted_cards"
                    ],

                "playing":
                    True,

                "ended":
                    False,

            })


            # ==============================================
            # PLAYBACK TIMING
            # ==============================================

            delay = (

                1.0 /
                source_fps /
                state["speed"]

            )


            await asyncio.sleep(

                max(
                    0.001,
                    delay
                )

            )


    # ==================================================
    # DISCONNECT
    # ==================================================

    except WebSocketDisconnect:

        print(
            "WebSocket client disconnected"
        )


    # ==================================================
    # OTHER ERROR
    # ==================================================

    except Exception as e:

        print(
            f"WebSocket error: {e}"
        )


        try:

            await websocket.send_json({

                "type":
                    "error",

                "message":
                    str(e)

            })

        except Exception:

            pass


    # ==================================================
    # CLEANUP
    # ==================================================

    finally:

        if command_task:

            command_task.cancel()

            try:
                await command_task

            except BaseException:
                pass


        if detection_task:

            detection_task.cancel()

            try:
                await detection_task

            except BaseException:
                pass


        if cap:

            cap.release()


        if (
            video_path
            and
            video_path.exists()
        ):

            try:

                os.remove(
                    video_path
                )

            except OSError:

                pass


        print(
            "WebSocket connection closed"
        )