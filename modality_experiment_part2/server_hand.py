import os
import sys
import time
import threading

import cv2
from flask import Flask, jsonify, render_template, request, send_file

import hand_tracker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
FRAME_FILE = os.path.join(TEMP_DIR, "hand_frame.jpg")
FRAME_TMP = os.path.join(TEMP_DIR, "hand_frame.tmp")

PORT = 5012
JPEG_QUALITY = 85
READ_RETRY_DELAY = 0.05
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.55
FONT_THICKNESS = 2
CROSSHAIR_SIZE = 12
MARKER_RADIUS = 7
MARKER_COLOR = (0, 255, 255)  # BGR yellow
TEXT_COLOR = (255, 255, 255)

# Landmark indices from the MediaPipe hand model
WRIST = 0
INDEX_TIP = 8
PALM_POINTS = (0, 5, 9, 13, 17)  # wrist + base of each finger

FPS_OPTIONS = {"1": 5, "2": 10, "3": 15, "4": 24}
MAX_CAMERA_INDEX = 4

app = Flask(__name__)

hands_detector = hand_tracker.create_detector()

lock = threading.Lock()
latest_hands = []
tracking_enabled = False
frame_dimensions = {"width": 0, "height": 0}


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


def to_pixel(landmark, width, height):
  # Clamp: MediaPipe can report points slightly outside the frame
  x = min(max(int(landmark.x * width), 0), width - 1)
  y = min(max(int(landmark.y * height), 0), height - 1)
  return x, y


def palm_center(landmarks, width, height):
  points = [to_pixel(landmarks[i], width, height) for i in PALM_POINTS]
  x = sum(p[0] for p in points) // len(points)
  y = sum(p[1] for p in points) // len(points)
  return x, y


def extract_hands(detected, width, height):
  hands = []
  for hand in detected:
    lm = hand["landmarks"]
    px, py = palm_center(lm, width, height)
    wx, wy = to_pixel(lm[WRIST], width, height)
    ix, iy = to_pixel(lm[INDEX_TIP], width, height)
    hands.append({
      "hand": hand["label"],
      "palm": {"x": px, "y": py},
      "wrist": {"x": wx, "y": wy},
      "index_tip": {"x": ix, "y": iy},
    })
  return hands


def draw_hand(frame, landmarks, info):
  hand_tracker.draw_landmarks(frame, landmarks)
  x, y = info["palm"]["x"], info["palm"]["y"]
  cv2.line(frame, (x - CROSSHAIR_SIZE, y), (x + CROSSHAIR_SIZE, y),
           MARKER_COLOR, FONT_THICKNESS)
  cv2.line(frame, (x, y - CROSSHAIR_SIZE), (x, y + CROSSHAIR_SIZE),
           MARKER_COLOR, FONT_THICKNESS)
  cv2.circle(frame, (x, y), MARKER_RADIUS, MARKER_COLOR, FONT_THICKNESS)
  # Text below the palm, kept inside the frame
  text_y = min(y + CROSSHAIR_SIZE + 20, frame.shape[0] - 5)
  cv2.putText(frame, f"({x}, {y})", (x + 10, text_y), FONT, FONT_SCALE,
              TEXT_COLOR, FONT_THICKNESS)


def write_frame(frame):
  ok, buffer = cv2.imencode(
    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
  if ok:
    with open(FRAME_TMP, "wb") as f:
      f.write(buffer.tobytes())
    os.replace(FRAME_TMP, FRAME_FILE)


def capture_loop(camera_index, fps):
  global latest_hands, frame_dimensions
  os.makedirs(TEMP_DIR, exist_ok=True)
  cap = cv2.VideoCapture(camera_index)
  delay = 1.0 / fps
  while True:
    ok, frame = cap.read()
    if not ok:
      time.sleep(READ_RETRY_DELAY)
      continue

    height, width = frame.shape[:2]
    with lock:
      enabled = tracking_enabled
    hands = []
    # Skip the model entirely while paused to save CPU
    if enabled:
      detected = hand_tracker.detect_hands(hands_detector, frame)
      hands = extract_hands(detected, width, height)
      for hand, info in zip(detected, hands):
        draw_hand(frame, hand["landmarks"], info)

    with lock:
      latest_hands = hands
      frame_dimensions = {"width": width, "height": height}
    write_frame(frame)
    time.sleep(delay)


@app.route("/")
def index():
  return render_template("hand.html")


@app.route("/frame")
def frame():
  if os.path.exists(FRAME_FILE):
    response = send_file(FRAME_FILE, mimetype="image/jpeg")
    response.headers["Cache-Control"] = "no-store"
    return response
  return jsonify({"error": "No frame available yet"}), 404


@app.route("/hand")
def hand():
  with lock:
    hands = list(latest_hands)
    dims = dict(frame_dimensions)
    enabled = tracking_enabled
  return jsonify({"hands": hands, "tracking": enabled, **dims})


@app.route("/tracking", methods=["POST"])
def set_tracking():
  global tracking_enabled
  data = request.get_json(silent=True) or {}
  enabled = data.get("enabled")
  if not isinstance(enabled, bool):
    return jsonify({"error": "enabled must be true or false"}), 400
  with lock:
    tracking_enabled = enabled
    if not enabled:
      latest_hands.clear()
  return jsonify({"tracking": enabled})


def main():
  os.makedirs(TEMP_DIR, exist_ok=True)
  print("=== Hand Tracking Server ===\n")
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

  print(f"\nStarting hand tracking from Camera {camera_index} at {fps} FPS...")
  print(f"Server running at http://localhost:{PORT}\n")
  app.run(host="0.0.0.0", port=PORT, debug=False)


if __name__ == "__main__":
  main()
