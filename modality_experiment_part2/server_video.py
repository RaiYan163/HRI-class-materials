import math
import os
import sys
import threading
import time
from datetime import datetime

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request, send_file

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
FRAME_PATH = os.path.join(TEMP_DIR, "frame.jpg")

FPS_OPTIONS = {"1": 5, "2": 10, "3": 15, "4": 24}
MAX_CAMERA_INDEX = 4
PORT = 5010

VALID_SHAPES = ("circle", "triangle", "rectangle", "pentagon", "hexagon")
# BGR values, since OpenCV uses BGR order
COLORS = {
  "green": (0, 255, 0),
  "red": (0, 0, 255),
  "blue": (255, 0, 0),
  "yellow": (0, 255, 255),
  "cyan": (255, 255, 0),
  "magenta": (255, 0, 255),
  "orange": (0, 165, 255),
  "white": (255, 255, 255),
  "black": (0, 0, 0),
}
DEFAULT_COLOR = "green"
FONT = cv2.FONT_HERSHEY_SIMPLEX
# Font size is given in pixels; cv2 scale = size / FONT_PX_PER_SCALE
FONT_PX_PER_SCALE = 30
DEFAULT_FONT_SIZE = 24
MIN_FONT_SIZE = 10
MAX_FONT_SIZE = 100
MIN_SHAPE_SIZE = 50
MAX_SHAPE_SIZE = 500
DEFAULT_THICKNESS = 2
MIN_THICKNESS = 1
MAX_THICKNESS = 20
TIMESTAMP_MARGIN_RIGHT = 10
TIMESTAMP_MARGIN_TOP = 30

# Polygon shapes: (vertex count, starting angle in degrees)
POLYGONS = {
  "triangle": (3, 90),
  "pentagon": (5, 90),
  "hexagon": (6, 0),
}

app = Flask(__name__)

# Shared between Flask request threads and the capture thread, so every
# access goes through state_lock.
annotations = []
show_timestamp = False
timestamp_color = DEFAULT_COLOR
current_color = DEFAULT_COLOR
timestamp_font_size = DEFAULT_FONT_SIZE
frame_width = None
frame_height = None
state_lock = threading.Lock()


def discover_cameras():
  available = []
  for index in range(MAX_CAMERA_INDEX + 1):
    cap = cv2.VideoCapture(index)
    if cap.isOpened():
      available.append(index)
    cap.release()
  return available


def choose_camera(available):
  print("Available cameras:")
  for index in available:
    print(f"  [{index}] Camera {index}")
  while True:
    choice = input("\nSelect camera index: ").strip()
    if choice.isdigit() and int(choice) in available:
      return int(choice)
    print("Invalid choice. Please pick one of the listed camera indices.")


def choose_fps():
  print("\nSelect FPS:")
  for key, fps in FPS_OPTIONS.items():
    print(f"  [{key}] {fps} FPS")
  while True:
    choice = input("\nEnter choice (1-4): ").strip()
    if choice in FPS_OPTIONS:
      return FPS_OPTIONS[choice]
    print("Invalid choice. Please enter 1, 2, 3, or 4.")


def polygon_points(x, y, size, vertex_count, start_deg):
  step = 360 / vertex_count
  points = []
  for i in range(vertex_count):
    angle = math.radians(start_deg + i * step)
    # Image y grows downward, so subtract sin to make 90 degrees point up
    px = x + size * math.cos(angle)
    py = y - size * math.sin(angle)
    points.append([round(px), round(py)])
  return np.array(points, dtype=np.int32)


def font_scale(font_size):
  return font_size / FONT_PX_PER_SCALE


def text_thickness(font_size):
  return max(1, round(font_scale(font_size) * 2.5))


def draw_annotation(frame, annotation):
  x = annotation["x"]
  y = annotation["y"]
  if annotation["type"] == "text":
    font_size = annotation["font_size"]
    cv2.putText(frame, annotation["content"], (x, y), FONT,
                font_scale(font_size), COLORS[annotation["color"]],
                text_thickness(font_size))
    return

  shape = annotation["shape"]
  size = annotation["size"]
  thickness = annotation["thickness"]
  color = COLORS[annotation["color"]]
  if shape == "circle":
    cv2.circle(frame, (x, y), size, color, thickness)
  elif shape == "rectangle":
    half = size // 2
    cv2.rectangle(frame, (x - half, y - half), (x + half, y + half),
                  color, thickness)
  elif shape in POLYGONS:
    vertex_count, start_deg = POLYGONS[shape]
    points = polygon_points(x, y, size, vertex_count, start_deg)
    cv2.polylines(frame, [points], isClosed=True, color=color,
                  thickness=thickness)


def draw_timestamp(frame, font_size, color_name):
  text = datetime.now().strftime("%H:%M:%S")
  scale = font_scale(font_size)
  thickness = text_thickness(font_size)
  (text_width, text_height), baseline = cv2.getTextSize(
    text, FONT, scale, thickness)
  x = frame.shape[1] - text_width - TIMESTAMP_MARGIN_RIGHT
  # Offset by the text height so larger text never clips off the top
  y = TIMESTAMP_MARGIN_TOP + text_height - baseline
  cv2.putText(frame, text, (x, y), FONT, scale, COLORS[color_name],
              thickness)


def capture_loop(camera_index, fps):
  global frame_width, frame_height
  os.makedirs(TEMP_DIR, exist_ok=True)
  cap = cv2.VideoCapture(camera_index)
  delay = 1.0 / fps
  tmp_path = FRAME_PATH + ".tmp"
  while True:
    ok, frame = cap.read()
    if ok:
      # Copy under the lock, draw outside it, so requests never wait on
      # OpenCV drawing.
      with state_lock:
        if frame_width is None:
          frame_height, frame_width = frame.shape[:2]
        annotations_copy = list(annotations)
        timestamp_on = show_timestamp
        timestamp_size = timestamp_font_size
        timestamp_color_name = timestamp_color
      for annotation in annotations_copy:
        draw_annotation(frame, annotation)
      if timestamp_on:
        draw_timestamp(frame, timestamp_size, timestamp_color_name)
      ok, buffer = cv2.imencode(".jpg", frame)
      if ok:
        with open(tmp_path, "wb") as f:
          f.write(buffer.tobytes())
        os.replace(tmp_path, FRAME_PATH)
    else:
      print("[WARNING] Failed to read frame from camera")
    time.sleep(delay)


def is_int(value):
  # bool is a subclass of int, but True/False are not valid coordinates
  return isinstance(value, int) and not isinstance(value, bool)


def in_range(value, low, high):
  return is_int(value) and low <= value <= high


@app.route("/")
def index():
  return render_template("video.html")


@app.route("/frame")
def frame():
  if os.path.exists(FRAME_PATH):
    response = send_file(FRAME_PATH, mimetype="image/jpeg")
    response.headers["Cache-Control"] = "no-store"
    return response
  return jsonify({"error": "No frame available yet"}), 404


@app.route("/frame_size")
def get_frame_size():
  with state_lock:
    width, height = frame_width, frame_height
  if width is None:
    return jsonify({"error": "No frame available yet"}), 404
  return jsonify({"width": int(width), "height": int(height)})


@app.route("/add_text", methods=["POST"])
def add_text():
  data = request.get_json(silent=True) or {}
  content = data.get("content")
  x = data.get("x")
  y = data.get("y")
  font_size = data.get("font_size", DEFAULT_FONT_SIZE)
  if not isinstance(content, str) or not content.strip():
    return jsonify({"error": "content must not be empty"}), 400
  if not is_int(x) or not is_int(y):
    return jsonify({"error": "x and y must be integers"}), 400
  if not in_range(font_size, MIN_FONT_SIZE, MAX_FONT_SIZE):
    return jsonify({"error": f"font size must be {MIN_FONT_SIZE}-"
                             f"{MAX_FONT_SIZE}"}), 400
  with state_lock:
    annotations.append({"type": "text", "content": content, "x": x, "y": y,
                        "font_size": font_size, "color": current_color})
    count = len(annotations)
  return jsonify({"status": "ok", "count": count})


@app.route("/add_shape", methods=["POST"])
def add_shape():
  data = request.get_json(silent=True) or {}
  shape = data.get("shape")
  x = data.get("x")
  y = data.get("y")
  size = data.get("size")
  thickness = data.get("thickness", DEFAULT_THICKNESS)
  if shape not in VALID_SHAPES:
    return jsonify({"error": "unknown shape"}), 400
  if not all(is_int(v) and v > 0 for v in (x, y)):
    return jsonify({"error": "x and y must be positive integers"}), 400
  if not in_range(size, MIN_SHAPE_SIZE, MAX_SHAPE_SIZE):
    return jsonify({"error": f"size must be {MIN_SHAPE_SIZE}-"
                             f"{MAX_SHAPE_SIZE}"}), 400
  if not in_range(thickness, MIN_THICKNESS, MAX_THICKNESS):
    return jsonify({"error": f"thickness must be {MIN_THICKNESS}-"
                             f"{MAX_THICKNESS}"}), 400
  with state_lock:
    annotations.append({"type": "shape", "shape": shape, "x": x, "y": y,
                        "size": size, "thickness": thickness,
                        "color": current_color})
    count = len(annotations)
  return jsonify({"status": "ok", "count": count})


@app.route("/toggle_timestamp", methods=["POST"])
def toggle_timestamp():
  global show_timestamp, timestamp_color
  with state_lock:
    show_timestamp = not show_timestamp
    # The clock takes whatever color is selected when it is switched on
    if show_timestamp:
      timestamp_color = current_color
    current = show_timestamp
  return jsonify({"show_timestamp": current})


@app.route("/set_color", methods=["POST"])
def set_color():
  global current_color
  data = request.get_json(silent=True) or {}
  color = data.get("color")
  if color not in COLORS:
    return jsonify({"error": "unknown color"}), 400
  with state_lock:
    current_color = color
  return jsonify({"color": color})


@app.route("/timestamp_font_size", methods=["POST"])
def set_timestamp_font_size():
  global timestamp_font_size
  data = request.get_json(silent=True) or {}
  font_size = data.get("font_size")
  if not in_range(font_size, MIN_FONT_SIZE, MAX_FONT_SIZE):
    return jsonify({"error": f"font size must be {MIN_FONT_SIZE}-"
                             f"{MAX_FONT_SIZE}"}), 400
  with state_lock:
    timestamp_font_size = font_size
  return jsonify({"font_size": font_size})


@app.route("/reset", methods=["POST"])
def reset():
  global annotations, show_timestamp, timestamp_font_size
  global current_color, timestamp_color
  with state_lock:
    annotations = []
    show_timestamp = False
    current_color = DEFAULT_COLOR
    timestamp_color = DEFAULT_COLOR
    timestamp_font_size = DEFAULT_FONT_SIZE
  return jsonify({"status": "ok"})


def main():
  os.makedirs(TEMP_DIR, exist_ok=True)
  print("=== Video Annotation Server ===\n")
  print("Scanning for available cameras...\n")
  available = discover_cameras()
  if not available:
    print("Error: no cameras found.")
    sys.exit(1)

  camera_index = choose_camera(available)
  fps = choose_fps()

  thread = threading.Thread(target=capture_loop, args=(camera_index, fps))
  thread.daemon = True
  thread.start()

  print(f"\nStarting stream from Camera {camera_index} at {fps} FPS...")
  print(f"Server running at http://localhost:{PORT}\n")
  app.run(host="0.0.0.0", port=PORT, debug=False)


if __name__ == "__main__":
  main()
