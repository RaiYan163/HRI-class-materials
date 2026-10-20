# Modality Experiment — Video, Speech-to-Text and Text-to-Speech Demos

Small Flask + vanilla JavaScript demos of three modalities: a live webcam stream, speech-to-text (Whisper) and text-to-speech (Piper).  
Designed for the HRI class at Kent State University — ATR Lab.

## Servers at a Glance

Each modality is its own standalone server. They share no state.

| Server | Port | What it does |
|---|---|---|
| `server.py` | 5001 | Original video stream (asks for camera + FPS in the terminal) |
| `server_video.py` | 5001 | Video stream only (same port as `server.py`, so run one or the other) |
| `server_stt.py` | 5002 | Speech to text, live in the browser |
| `server_tts.py` | 5003 | Text to speech with selectable voices |

The first sections below describe the video stream. The speech sections start at **Running Individual Modality Servers**.

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
├── server.py            # Original video server (webcam capture + Flask)
├── server_video.py      # Video stream only (port 5001)
├── server_stt.py        # Speech to text (port 5002)
├── server_tts.py        # Text to speech (port 5003)
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── templates/
│   ├── index.html       # Frontend for server.py
│   ├── video.html       # Frontend for server_video.py
│   ├── stt.html         # Frontend for server_stt.py
│   └── tts.html         # Frontend for server_tts.py
├── static/              # Reserved for future static assets
├── voices/
│   ├── .gitkeep         # Keeps the folder tracked by git
│   └── *.onnx, *.onnx.json   # ← Piper voices, downloaded on first use, not committed
└── temp/
    ├── .gitkeep         # Keeps the folder tracked by git
    ├── frame.jpg        # ← video frame, auto-generated, not committed
    └── output.wav       # ← last synthesized speech, auto-generated, not committed
```

---

## Setup

### Prerequisites

- Python 3.10 or higher (tested on 3.13). `av==16.1.0` needs 3.10+.
- A webcam (video demo) and a microphone (speech-to-text demo)
- Internet on first use: Whisper downloads its model (~74MB) and Piper downloads each voice (~60MB)
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
| STT page shows `open() got an unexpected keyword argument 'metadata_errors'` | PyAV newer than 16.x (19.0.1 tested) is installed | `pip install -r requirements.txt` (pins `av==16.1.0`) |
| STT page shows a microphone error | Browser has no microphone permission | Allow the microphone for `localhost` in the browser's site settings |
| `pip install` fails on `piper-phonemize` | An old `piper-tts` (1.2.0 or older) on Python 3.13 | Use the pinned `piper-tts==1.3.0` |
| TTS: `Synthesis error` while downloading a voice | No internet, or HuggingFace is unreachable | Check your connection and Send again. A partial download is never reused |

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
| waitress | 3.0.0 | Production WSGI server (listed, but the servers use Flask's built-in server) |
| faster-whisper | 1.1.1 | Speech-to-text (Whisper) for `server_stt.py` |
| av | 16.1.0 | Audio decoding used by faster-whisper. Pinned because newer PyAV breaks it |
| piper-tts | 1.3.0 | Text-to-speech for `server_tts.py` |

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
Click **Start** and speak. The page records in 4-second segments and transcribes each one as soon as it is ready, so the text appears in the chat bubble while you are still talking. Click **Stop** to flush the last segment.
The **System log** panel under the transcript shows every step (recording, sending, transcribed text, errors) with timestamps, and the same lines are printed in the server console.

The segment length is `SEGMENT_MS` in `templates/stt.html`. Longer segments are more accurate (a word is less likely to be cut at a boundary) but update less often.

### STT Parameters
| Parameter | Value | Reason |
|---|---|---|
| Model | `base` | Best balance of speed and accuracy on CPU |
| Language | `en` (English, fixed) | Avoids language detection overhead |
| VAD filter | `on` | Skips silence — cleaner output |
| Beam size | `5` | Standard decoding quality |
| Device | CPU | No GPU required |
| Precision | int8 | Quantized for faster CPU inference |
| Segment length | 4 s | How often live text appears |

### Text to Speech Only
```bash
cd modality_experiment
python server_tts.py
```
Opens at: http://localhost:5003

1. Select a voice from the dropdown
2. Type text in the input box
3. Hit **Send** (or Cmd/Ctrl + Enter) — the text appears as a chat bubble and the server generates audio in the background with Piper TTS
4. Hit **Convert** — the browser plays the generated audio

**Convert** is disabled until a synthesis has succeeded. **Send** is disabled while a synthesis is running. The **Log** panel shows timestamped `info`, `success` and `error` entries (it polls the server every 2 seconds), and the same lines are printed in the server console.

Voice models (~60MB each) download automatically from HuggingFace on first use and are cached in `voices/`. A voice is loaded into memory once, so only the first Send with each voice is slow.

### Available Voices

| Voice ID | Description |
|---|---|
| `lessac` | American English · Female |
| `ryan` | American English · Male |
| `alan` | British English · Male |
| `amy` | American English · Female |

### TTS Parameters

| Setting | Value |
|---|---|
| Engine | Piper TTS 1.3.0 |
| Model size | Medium |
| Device | CPU |
| Output format | WAV (16-bit, mono) at the voice's sample rate (22050 Hz for these voices) |
| Output file | `temp/output.wav`, overwritten on every Send |
| Voice download | Automatic (HuggingFace) |

### Combined Demo (not built yet)
A single dashboard with video, STT and TTS together is planned. It has no server yet, and its port is not decided (5001–5003 are taken).
