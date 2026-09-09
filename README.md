# 🃏 Card Counting AI

### Real-Time Playing Card Detection, Tracking & Counting

An AI-powered computer vision application that detects playing cards from video, tracks cards across frames, identifies card ranks, and maintains a running card-counting state through an interactive web dashboard.

The project combines **YOLO-based object detection**, **IoU-based multi-object tracking**, **temporal smoothing**, and a **card-counting engine** with a React-based visualization dashboard.

---

## 🚀 Features

- 🎯 Real-time playing card detection using YOLO
- 🃏 Recognition of card ranks from **A, 2–10, J, Q, K**
- 🔍 IoU-based card tracking across consecutive frames
- 📉 Temporal smoothing for more stable bounding boxes
- ♻️ Duplicate detection merging for card-corner detections
- 📊 Running Count calculation
- 🃏 Cards Counted and Cards Remaining tracking
- 📈 True Count calculation
- 🎚️ Adjustable confidence threshold
- ⏯️ Play / Pause / Restart controls
- ⏩ Variable playback speed
- ⏪ 5-second backward / forward seeking
- 📱 Support for both portrait and landscape videos
- ⚡ Asynchronous FastAPI backend
- 💻 Interactive React dashboard
- 📡 WebSocket-based frame and detection communication

---

## 🧠 System Architecture

```text
                    ┌─────────────────────┐
                    │     Input Video     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Frame Processing  │
                    │  Resize + Encoding  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    YOLO Detector    │
                    │ Card Detection +    │
                    │ Confidence Filtering│
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Card Tracker     │
                    │ IoU Matching +      │
                    │ Temporal Smoothing  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Counting Engine   │
                    │ Running Count       │
                    │ Cards Remaining     │
                    │ True Count          │
                    └──────────┬──────────┘
                               │
                         WebSocket
                               │
                               ▼
                    ┌─────────────────────┐
                    │   React Dashboard   │
                    │                     │
                    │ Detection Overlay   │
                    │ Deck Status         │
                    │ Count Statistics    │
                    │ Detection Log       │
                    └─────────────────────┘
