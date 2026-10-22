import os
import sys
import time
import threading
import urllib.request

import cv2
from flask import Flask, jsonify, render_template, request, send_file
from ultralytics import YOLO
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")

PORT = 5011
FRAME_FILE = os.path.join(TEMP_DIR, "detect_frame.jpg")
FRAME_TMP = os.path.join(TEMP_DIR, "detect_frame.tmp")
HAND_MODEL_PATH = os.path.join(BASE_DIR, "hand_landmarker.task")
HAND_MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/"
                  "hand_landmarker/hand_landmarker/float16/1/"
                  "hand_landmarker.task")
JPEG_QUALITY = 85
INFERENCE_INTERVAL = 0.2  # seconds between model runs
YOLO_CONFIDENCE = 0.45
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.65
FONT_THICKNESS = 2
BOX_THICKNESS = 2
LABEL_PADDING = 6
YOLO_COLOR = (34, 197, 94)  # BGR green
MP_COLOR = (255, 100, 0)  # BGR blue
LABEL_BG_COLOR = (0, 0, 0)
LABEL_TEXT_COLOR = (255, 255, 255)
HAND_BOX_PADDING = 15
READ_RETRY_DELAY = 0.05
CONFIDENCE_DECIMALS = 2
PERCENT = 100

FPS_OPTIONS = {"1": 5, "2": 10, "3": 15, "4": 24}
MAX_CAMERA_INDEX = 4

MODE_YOLO = "yolo"
MODE_MEDIAPIPE = "mediapipe"
VALID_MODES = (MODE_YOLO, MODE_MEDIAPIPE)

# Landmark indices: (tip, joint below the tip)
LANDMARK_RADIUS = 4
LANDMARK_COLOR = (0, 0, 255)  # BGR red
CONNECTION_COLOR = (255, 255, 255)
CONNECTION_THICKNESS = 2

# The Tasks API has no drawing helpers, so the hand skeleton is listed here
HAND_CONNECTIONS = (
  (0, 1), (1, 2), (2, 3), (3, 4),
  (0, 5), (5, 6), (6, 7), (7, 8),
  (5, 9), (9, 10), (10, 11), (11, 12),
  (9, 13), (13, 14), (14, 15), (15, 16),
  (13, 17), (17, 18), (18, 19), (19, 20),
  (0, 17),
)

THUMB = (4, 3)
FINGERS = ((8, 6), (12, 10), (16, 14), (20, 18))

app = Flask(__name__)

# Both load at import time so the first request is not slow, and so a
# missing model or package fails before the camera prompts.
yolo_model = YOLO("yolov8n.pt")



def ensure_hand_model():
  if not os.path.exists(HAND_MODEL_PATH):
    print("Downloading hand landmarker model...")
    urllib.request.urlretrieve(HAND_MODEL_URL, HAND_MODEL_PATH)


ensure_hand_model()
hands_detector = mp_vision.HandLandmarker.create_from_options(
  mp_vision.HandLandmarkerOptions(
    base_options=mp_tasks.BaseOptions(model_asset_path=HAND_MODEL_PATH),
    running_mode=mp_vision.RunningMode.VIDEO,
    num_hands=2,
    min_hand_detection_confidence=0.6,
    min_tracking_confidence=0.5,
  ))

lock = threading.Lock()
current_mode = MODE_YOLO
last_detections = []
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


def classify_gesture(landmarks, handedness):
  thumb_tip, thumb_ip = (landmarks[i] for i in THUMB)
  # In image space x grows to the right; the thumb points the opposite
  # way for each hand.
  if handedness == "Right":
    thumb_extended = thumb_tip.x < thumb_ip.x
  else:
    thumb_extended = thumb_tip.x > thumb_ip.x
  # y grows downward, so an extended fingertip sits above its joint
  extended = [thumb_extended] + [
    landmarks[tip].y < landmarks[joint].y for tip, joint in FINGERS
  ]
  thumb, index, middle, ring, pinky = extended

  if all(extended):
    return "Open Palm"
  if not any(extended):
    return "Closed Fist"
  if index and not (thumb or middle or ring or pinky):
    return "Pointing Up"
  if index and middle and not (thumb or ring or pinky):
    return "Peace / Victory"
  if thumb and not (index or middle or ring or pinky):
    return "Thumbs Up"
  return "Unknown Gesture"


def run_yolo_inference(frame):
  results = yolo_model(frame, conf=YOLO_CONFIDENCE, verbose=False)
  detections = []
  for box in results[0].boxes:
    detections.append({
      "label": yolo_model.names[int(box.cls[0])],
      "confidence": round(float(box.conf[0]), CONFIDENCE_DECIMALS),
      "box": [int(v) for v in box.xyxy[0].tolist()],
    })
  return detections


def hand_bounding_box(landmarks, width, height):
  xs = [lm.x * width for lm in landmarks]
  ys = [lm.y * height for lm in landmarks]
  x1 = max(int(min(xs)) - HAND_BOX_PADDING, 0)
  y1 = max(int(min(ys)) - HAND_BOX_PADDING, 0)
  x2 = min(int(max(xs)) + HAND_BOX_PADDING, width - 1)
  y2 = min(int(max(ys)) + HAND_BOX_PADDING, height - 1)
  return [x1, y1, x2, y2]


def run_mediapipe_inference(frame):
  height, width = frame.shape[:2]
  rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
  image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
  # VIDEO mode requires strictly increasing timestamps
  timestamp_ms = int(time.monotonic() * 1000)
  results = hands_detector.detect_for_video(image, timestamp_ms)
  if not results.hand_landmarks:
    return [], None
  detections = []
  for hand_landmarks, handedness in zip(
      results.hand_landmarks, results.handedness):
    label = handedness[0].category_name
    detections.append({
      "hand": label,
      "gesture": classify_gesture(hand_landmarks, label),
      "box": hand_bounding_box(hand_landmarks, width, height),
    })
  return detections, results


def draw_label(frame, text, x1, y1):
  (text_width, text_height), baseline = cv2.getTextSize(
    text, FONT, FONT_SCALE, FONT_THICKNESS)
  # Keep the label on screen when the box touches the top edge
  top = max(y1 - text_height - baseline - 2 * LABEL_PADDING, 0)
  bottom = top + text_height + baseline + 2 * LABEL_PADDING
  right = x1 + text_width + 2 * LABEL_PADDING
  cv2.rectangle(frame, (x1, top), (right, bottom), LABEL_BG_COLOR,
                cv2.FILLED)
  cv2.putText(frame, text, (x1 + LABEL_PADDING,
              bottom - LABEL_PADDING - baseline), FONT, FONT_SCALE,
              LABEL_TEXT_COLOR, FONT_THICKNESS)


def draw_yolo_annotations(frame, detections):
  for det in detections:
    x1, y1, x2, y2 = det["box"]
    cv2.rectangle(frame, (x1, y1), (x2, y2), YOLO_COLOR, BOX_THICKNESS)
    percent = int(det["confidence"] * PERCENT)
    draw_label(frame, f"{det['label']} {percent}%", x1, y1)


def draw_mediapipe_annotations(frame, detections, raw_results):
  if raw_results is None or not raw_results.hand_landmarks:
    return
  height, width = frame.shape[:2]
  for hand_landmarks in raw_results.hand_landmarks:
    points = [(int(lm.x * width), int(lm.y * height))
              for lm in hand_landmarks]
    for start, end in HAND_CONNECTIONS:
      cv2.line(frame, points[start], points[end], CONNECTION_COLOR,
               CONNECTION_THICKNESS)
    for point in points:
      cv2.circle(frame, point, LANDMARK_RADIUS, LANDMARK_COLOR, cv2.FILLED)
  for det in detections:
    x1, y1, x2, y2 = det["box"]
    cv2.rectangle(frame, (x1, y1), (x2, y2), MP_COLOR, BOX_THICKNESS)
    draw_label(frame, f"{det['hand']} — {det['gesture']}", x1, y1)


def write_frame(frame):
  ok, buffer = cv2.imencode(
    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
  if ok:
    with open(FRAME_TMP, "wb") as f:
      f.write(buffer.tobytes())
    os.replace(FRAME_TMP, FRAME_FILE)


def capture_loop(camera_index, fps):
  global last_detections, frame_dimensions
  os.makedirs(TEMP_DIR, exist_ok=True)
  cap = cv2.VideoCapture(camera_index)
  delay = 1.0 / fps
  height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
  width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
  with lock:
    frame_dimensions = {"width": width, "height": height}

  last_inference_time = 0.0
  cached_detections = []
  cached_raw_results = None
  cached_mode = None

  while True:
    ok, frame = cap.read()
    if not ok:
      time.sleep(READ_RETRY_DELAY)
      continue

    with lock:
      mode = current_mode

    # Cached results belong to one mode only; drawing them under the
    # other mode would hit missing keys, so drop them on a switch.
    if mode != cached_mode:
      cached_detections = []
      cached_raw_results = None
      cached_mode = mode
      last_inference_time = 0.0

    now = time.time()
    if now - last_inference_time >= INFERENCE_INTERVAL:
      if mode == MODE_YOLO:
        cached_detections = run_yolo_inference(frame)
        cached_raw_results = None
      else:
        cached_detections, cached_raw_results = run_mediapipe_inference(
          frame)
      # Skip publishing if the mode changed while the model was running
      with lock:
        if current_mode == mode:
          last_detections = list(cached_detections)
      last_inference_time = now

    annotated = frame.copy()
    if mode == MODE_YOLO:
      draw_yolo_annotations(annotated, cached_detections)
    else:
      draw_mediapipe_annotations(
        annotated, cached_detections, cached_raw_results)
    write_frame(annotated)
    time.sleep(delay)


@app.route("/")
def index():
  return render_template("detect.html")


@app.route("/frame")
def frame():
  if os.path.exists(FRAME_FILE):
    response = send_file(FRAME_FILE, mimetype="image/jpeg")
    response.headers["Cache-Control"] = "no-store"
    return response
  return jsonify({"error": "No frame available yet"}), 404


@app.route("/frame_size")
def frame_size():
  with lock:
    dims = dict(frame_dimensions)
  return jsonify(dims)


@app.route("/set_mode", methods=["POST"])
def set_mode():
  global current_mode, last_detections
  data = request.get_json(silent=True) or {}
  mode = data.get("mode", "")
  if mode not in VALID_MODES:
    return jsonify({"error": "invalid mode"}), 400
  with lock:
    current_mode = mode
    last_detections = []
  return jsonify({"mode": mode})


@app.route("/detections")
def detections():
  with lock:
    mode = current_mode
    dets = list(last_detections)
  return jsonify({"mode": mode, "detections": dets})


def main():
  os.makedirs(TEMP_DIR, exist_ok=True)
  print("=== Detection Server ===\n")
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

  print(f"\nStarting detection from Camera {camera_index} at {fps} FPS...")
  print(f"Server running at http://localhost:{PORT}\n")
  app.run(host="0.0.0.0", port=PORT, debug=False)


if __name__ == "__main__":
  main()
