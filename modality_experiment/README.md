# Modality Experiment — Live Video Stream Demo

A real-time webcam streaming demo built with Python (Flask) and vanilla JavaScript.  
Designed for the HRI class at Kent State University — ATR Lab.

---

## What This Does

When you run the server, it:
1. Scans your machine for available cameras and lets you pick one
2. Asks you to choose a capture frame rate from 4 preset options
3. Starts continuously capturing frames from your webcam and saving them to a local `temp/` folder (one file, constantly overwritten)
4. Serves a web frontend at `http://localhost:5001`

The frontend connects to the server and polls for the latest frame every 80ms — displaying it in real time, creating the appearance of a live video stream.

---

## Architecture

```
┌─────────────────────────────────┐        ┌──────────────────────────────┐
│           SERVER (Python)       │        │       CLIENT (Browser)       │
│                                 │        │                              │
│  ┌──────────────────────────┐   │        │  ┌────────────────────────┐  │
│  │  Background Thread       │   │        │  │  index.html            │  │
│  │  cv2.VideoCapture(cam)   │   │        │  │                        │  │
│  │  └─ cap.read() loop      │   │        │  │  setInterval(80ms)     │  │
│  │     └─ saves frame.jpg   │   │        │  │  └─ GET /frame         │  │
│  └──────────────────────────┘   │        │  │     └─ img.src = url   │  │
│                                 │        │  └────────────────────────┘  │
│  Flask Routes:                  │        └──────────────────────────────┘
│  GET /        → index.html      │  HTTP
│  GET /frame   → temp/frame.jpg  │◄───────────────────────────────────────
└─────────────────────────────────┘
```

**Key design choice:** There is no video encoding, no WebSockets, and no multipart streaming. The client simply fetches a fresh JPEG every 80ms. This keeps the implementation simple, dependency-free on the frontend, and easy to debug.

---

## Folder Structure

```
modality_experiment/
├── server.py            # Flask server + webcam capture logic
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── templates/
│   └── index.html       # Frontend (HTML + CSS + JS, self-contained)
├── static/              # Reserved for future static assets
└── temp/
    ├── .gitkeep         # Keeps the folder tracked by git
    └── frame.jpg        # ← auto-generated at runtime, not committed
```

---

## Setup

### Prerequisites

- Python 3.8 or higher
- A webcam connected to your machine
- pip

### Install Dependencies

```bash
cd modality_experiment
pip install -r requirements.txt
```

---

## Running the Server

```bash
cd modality_experiment
python server.py
```

You will see a terminal prompt like this:

```
Scanning for available cameras...

Available cameras:
  [0] Camera 0
  [1] Camera 1

Select camera index: 0

Select FPS:
  [1] 5 FPS
  [2] 10 FPS
  [3] 15 FPS
  [4] 24 FPS

Enter choice (1-4): 3

Starting stream from Camera 0 at 15 FPS...
Server running at http://localhost:5001
```

Open your browser and go to: **http://localhost:5001**

---

## Using the Frontend

1. Click **"Watch Video Stream"** — the live feed from your webcam will appear instantly
2. Click **"Stop Stream"** to pause the feed
3. The status indicator (bottom of the panel) shows whether the stream is active
4. The live clock in the header updates every second

---

## How the Streaming Works

```
Server thread          temp/frame.jpg          Browser
─────────────          ──────────────          ───────
cap.read()    ──────►  overwrite file  ◄──────  GET /frame (every 80ms)
(every 1/fps s)                                 img.src = /frame?t=<timestamp>
```

- The server writes one JPEG file, constantly replacing it
- The browser fetches that file 12–13 times per second
- The `?t=<timestamp>` query parameter is a cache buster — it forces the browser to always fetch a fresh copy instead of using a cached version
- The result looks like a live video stream

---

## Stopping the Server

Press `Ctrl+C` in the terminal. The background camera thread is a daemon thread, so it stops automatically when the main process exits.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| No cameras found | Camera not connected or in use | Close other apps using the camera |
| No cameras found on macOS (`not authorized to capture video`) | Terminal or VS Code has no camera permission | Click Allow on the prompt, or enable it in System Settings > Privacy & Security > Camera, restart the app, and run again |
| Black/frozen frame | Camera index mismatch | Try a different camera index |
| `ModuleNotFoundError: cv2` | OpenCV not installed | Run `pip install -r requirements.txt` |
| Port 5001 already in use | Another process on port 5001 (port 5000 is avoided because macOS AirPlay Receiver uses it) | Change `port=5001` in `server.py` to another free port |
| Stream looks choppy | Low FPS selected | Re-run and choose a higher FPS option |

---

## Extending This Demo

This demo is intentionally minimal. Possible extensions:
- **LLM frame analysis**: Send `temp/frame.jpg` to Claude or GPT-4o on each capture and overlay the response on the frontend
- **Multiple modalities**: Add microphone input alongside the video stream
- **Robot control**: Wire the stream into the existing robot control dashboard in `intro_claude_code/`

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| flask | 3.0.3 | Web server and routing |
| opencv-python | 4.10.0.84 | Webcam capture and JPEG writing |
| waitress | 3.0.0 | Production WSGI server |

---

## Author

Raiyan — ATR Lab, Kent State University  
HRI Class Demo · 2026

---

## Running Individual Modality Servers (Option B)

Each modality can be run as a standalone server for focused demos:

### Video Stream Only
```bash
cd modality_experiment
python server_video.py
```
Opens at: http://localhost:5001

### Speech to Text Only
```bash
cd modality_experiment
python server_stt.py
```
Opens at: http://localhost:5002

The STT server loads the Whisper `base` model on startup (~74MB download on first run).
Click **Start**, speak, then click **Stop & Transcribe**.
Each transcription appears as a chat bubble in the log.

### STT Parameters
| Parameter | Value | Reason |
|---|---|---|
| Model | `base` | Best balance of speed and accuracy on CPU |
| Language | `en` (English, fixed) | Avoids language detection overhead |
| VAD filter | `on` | Skips silence — cleaner output |
| Beam size | `5` | Standard decoding quality |
| Device | CPU | No GPU required |
| Precision | int8 | Quantized for faster CPU inference |

### Combined Demo (coming soon)
`server_full.py` on port `5003` — video stream + STT + TTS in one dashboard.
