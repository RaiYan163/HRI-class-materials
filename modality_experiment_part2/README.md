# Modality Experiment Part 2 — Video Annotation, Object Detection, Hand Tracking and Voice Control

A small Flask + vanilla JavaScript demo of server-side video annotation with OpenCV. Type text, pick a shape or toggle a timestamp in the browser, and the server draws it onto the live webcam frames.  
Designed for the HRI class at Kent State University — ATR Lab.

## Servers at a Glance

Four standalone servers share this folder. They all use the webcam, so **run only one at a time**.

| Server | Port | What it does |
|---|---|---|
| `server_video.py` | 5010 | Draw text, shapes and a timestamp on the live video using the page controls |
| `server_detect.py` | 5011 | Object detection (YOLOv8 nano) or hand gesture recognition (MediaPipe), switchable in the page |
| `server_hand.py` | 5012 | Hand tracking with live pixel coordinates (Start/Stop Tracking button) |
| `server_voice.py` | 5013 | Same annotations as `server_video.py`, but triggered by your voice (Whisper speech-to-text) |

The sections below describe `server_video.py`. The other three are covered under **Other Servers**.

---

## What This Does

When you run the server, it:
1. Scans your machine for available cameras and lets you pick one
2. Asks you to choose a capture frame rate from 4 preset options
3. Captures frames from your webcam, draws the current annotations onto each frame with OpenCV, and saves the result to `temp/frame.jpg` (one file, constantly overwritten)
4. Serves a web frontend at `http://localhost:5010`

The browser polls for the latest frame every 80ms, so the annotations appear on the stream a moment after you add them. The drawing happens on the server, so the browser only ever receives finished JPEGs.

This is Part 2 of the modality experiment. It uses port 5010 so it can run next to Part 1 (`modality_experiment/`, port 5001).

---

## Coordinate System

`(0, 0)` is the **top-left corner** of the frame. X grows to the right, Y grows **downward**.

The top of the controls panel shows the valid range for your camera, for example `Valid coordinates: 0–640 (X) · 0–480 (Y)`. Values outside that range are accepted but draw off-screen.

---

## Folder Structure

```
modality_experiment_part2/
├── server_video.py      # Capture loop, annotation drawing, Flask routes (5010)
├── server_detect.py     # YOLO + MediaPipe gestures (5011)
├── server_hand.py       # Hand tracking with coordinates (5012)
├── server_voice.py      # Voice-controlled annotations (5013)
├── hand_tracker.py      # Shared MediaPipe hand helper
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── templates/
│   ├── video.html       # Frontend for server_video.py
│   ├── detect.html      # Frontend for server_detect.py
│   ├── hand.html        # Frontend for server_hand.py
│   └── voice.html       # Frontend for server_voice.py
├── temp/
│   ├── .gitkeep         # Keeps the folder tracked by git
│   └── *.jpg            # ← latest frames, auto-generated, not committed
├── yolov8n.pt           # ← YOLO model, auto-downloaded, not committed
└── hand_landmarker.task # ← hand model, auto-downloaded, not committed
```

---

## Setup

### Prerequisites

- Python 3.10 or higher
- A webcam, and a microphone for the voice demo
- pip
- Internet on first use. These download automatically, once:
  - `yolov8n.pt` (~6 MB) for `server_detect.py`
  - `hand_landmarker.task` (~8 MB) for `server_detect.py` and `server_hand.py`
  - Whisper `base` model (~74 MB) for `server_voice.py`

### Install Dependencies

```bash
cd modality_experiment_part2
pip install -r requirements.txt
```

---

## Running the Server

```bash
cd modality_experiment_part2
python server_video.py
```

Pick a camera and FPS at the prompts, then open **http://localhost:5010**.

---

## Using the Frontend

1. Click **Start Stream** to see the live feed
2. Use the controls panel on the right to annotate it

| Control | What it does |
|---|---|
| **Color** | Dropdown of 9 colors (default green). Applies to everything drawn after you change it; existing drawings keep their color |
| **Add Text** | Draws the text with its baseline-left corner at (X, Y), in the selected color |
| **Add Shape** | Draws the chosen shape centered at (X, Y) with the given size (50–500 px) and outline thickness (1–20 px), in the selected color |
| **Show / Hide Timestamp** | Toggles a `HH:MM:SS` clock at the top-right of the frame, in the color selected when it is switched on |
| **Reset All** | Removes every text, shape and the timestamp |

Each action shows a short confirmation under its button that fades after 2 seconds (red if the request failed).

### Available Shapes

| Shape | How Size is used |
|---|---|
| circle | Radius in pixels |
| rectangle | Side length in pixels (a square centered at X, Y) |
| triangle | Distance from the center to each vertex, point facing up |
| pentagon | Distance from the center to each vertex, point facing up |
| hexagon | Distance from the center to each vertex, flat sides on top and bottom |

---

## How It Works

```
Browser                    Server                     Capture thread
───────                    ──────                     ──────────────
POST /add_text    ──────►  append to annotations
POST /add_shape            (guarded by state_lock)
                                                      cap.read()
                                                      copy annotations
GET /frame (80ms) ◄──────  temp/frame.jpg  ◄────────  draw + os.replace
```

The capture thread copies the annotation list under a lock, then draws outside the lock, so a request never waits on OpenCV. Annotations live in server memory and are lost when the server stops.

Routes: `GET /`, `GET /frame`, `GET /frame_size`, `POST /add_text` (with `font_size` 10–100), `POST /add_shape` (with `size` 50–500, `thickness` 1–20), `POST /set_color`, `POST /toggle_timestamp`, `POST /timestamp_font_size`, `POST /reset`.

---

## Other Servers

All of them ask for a camera and an FPS in the terminal first, like `server_video.py`.

### Detection — `server_detect.py` (port 5011)

```bash
python server_detect.py
```

Open http://localhost:5011. Two cards on the right switch the mode:
- **YOLOv8 Nano**: draws boxes and labels for 80 object classes
- **MediaPipe Hands**: draws the hand skeleton and names the gesture (Open Palm, Closed Fist, Pointing Up, Peace / Victory, Thumbs Up)

### Hand tracking — `server_hand.py` (port 5012)

```bash
python server_hand.py
```

Open http://localhost:5012 and click **Start Tracking**. The side panel shows live pixel coordinates (`(0, 0)` is the top-left) of the palm center, wrist and index fingertip for each hand. **Stop Tracking** pauses the model and clears the overlay.

### Voice control — `server_voice.py` (port 5013)

```bash
python server_voice.py
```

Open http://localhost:5013, allow the microphone, and click **Enable Voice**. Fill in the page's inputs first: **X** and **Y** (where shapes and text go), **Shape size** (50–500) and **Text size** (10–100). Empty fields use the center, shape size 50 and text size 24. Then say:

| Say | Result |
|---|---|
| `circle` (or `draw a circle`) | Draws that shape: circle, square, triangle, pentagon, hexagon |
| `text hello world` | Draws the words after `text` |
| `time` | Toggles the timestamp (always font size 50) |
| `reset` (or `clear`) | Removes everything |

The microphone only records while voice is enabled. It works in 4-second segments, so pause briefly between commands. The **Heard** panel shows what Whisper understood and what it did.

---

## Stopping the Server

Press `Ctrl+C` in the terminal. The capture thread is a daemon thread, so it stops with the main process.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| No cameras found | Camera not connected or in use | Close other apps using the camera |
| No cameras found on macOS (`not authorized to capture video`) | Terminal or VS Code has no camera permission | Enable it in System Settings > Privacy & Security > Camera, restart the app, and run again |
| `ModuleNotFoundError: cv2` | OpenCV not installed | Run `pip install -r requirements.txt` |
| Port 5010 already in use | Another process on port 5010 | Change `PORT` in `server_video.py` |
| Coordinates panel says "Frame size not available yet" | The first frame has not been captured | Wait a second and reload the page |
| A shape or text does not appear | Coordinates are outside the frame | Check the valid range at the top of the controls panel |
| Annotations show up with a short delay | Low FPS selected | Re-run and choose a higher FPS option |
| `module 'mediapipe' has no attribute 'solutions'` | Old code using the removed `mp.solutions` API | Not an issue with these files, which use the Tasks API. Make sure you have the latest copy of this folder |
| A server seems stuck on startup | First run is downloading a model (YOLO, hand model or Whisper) | Wait a minute or two. It only happens once |
| `address already in use` or the camera is busy | Another server from this folder is still running | Stop it with `Ctrl+C` first. Only one can use the camera |
| Voice: nothing happens | Voice is not enabled, or microphone permission is blocked | Click **Enable Voice** and allow the microphone for `localhost` |
| Voice: "Not a command — ignored" | Whisper heard something that is not one of the four commands | Say it more plainly, e.g. `circle`, `text hello`, `time`, `reset` |
| `pip install` fails on `mediapipe` or `av` | Very new Python (3.13+) without wheels | Use a Python 3.12 virtual environment |

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| flask | 3.0.3 | Web server and routing |
| opencv-python | 4.10.0.84 | Webcam capture and drawing |
| numpy | latest | Polygon vertex arrays |
| ultralytics | latest | YOLOv8 object detection |
| mediapipe | latest | Hand tracking and gestures (Tasks API) |
| faster-whisper | 1.1.1 | Speech-to-text for `server_voice.py` |
| av | 16.1.0 | Audio decoding for faster-whisper. Pinned because newer PyAV breaks it |

---

## Author

Raiyan — ATR Lab, Kent State University  
HRI Class Demo · 2026
