# Modality Experiment Part 2 — Interactive Video Annotation

A small Flask + vanilla JavaScript demo of server-side video annotation with OpenCV. Type text, pick a shape or toggle a timestamp in the browser, and the server draws it onto the live webcam frames.  
Designed for the HRI class at Kent State University — ATR Lab.

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
├── server_video.py      # Capture loop, annotation drawing, Flask routes
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── templates/
│   └── video.html       # Frontend: stream + controls panel
└── temp/
    ├── .gitkeep         # Keeps the folder tracked by git
    └── frame.jpg        # ← annotated frame, auto-generated, not committed
```

---

## Setup

### Prerequisites

- Python 3.10 or higher
- A webcam
- pip

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

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| flask | 3.0.3 | Web server and routing |
| opencv-python | 4.10.0.84 | Webcam capture and drawing |
| numpy | latest | Polygon vertex arrays |

---

## Author

Raiyan — ATR Lab, Kent State University  
HRI Class Demo · 2026
