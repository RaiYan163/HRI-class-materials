import os
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Same file server_detect.py uses, so the model is only downloaded once
MODEL_PATH = os.path.join(BASE_DIR, "hand_landmarker.task")
MODEL_URL = (
  "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
  "hand_landmarker/float16/1/hand_landmarker.task"
)

MAX_HANDS = 2
MIN_DETECTION_CONFIDENCE = 0.6
MIN_TRACKING_CONFIDENCE = 0.5
LANDMARK_COLOR = (0, 0, 255)  # BGR red
CONNECTION_COLOR = (255, 255, 255)
LANDMARK_RADIUS = 4
CONNECTION_THICKNESS = 2

# mp.solutions was removed in MediaPipe 1.x, so this module uses the
# Tasks API, which works on both old and new releases.
CONNECTIONS = vision.HandLandmarksConnections.HAND_CONNECTIONS


def ensure_model():
  # Download once; write to a temp name so a failed download is never reused
  if os.path.exists(MODEL_PATH):
    return
  print("Downloading hand_landmarker.task (~8 MB), first run only...")
  tmp_path = MODEL_PATH + ".tmp"
  urllib.request.urlretrieve(MODEL_URL, tmp_path)
  os.replace(tmp_path, MODEL_PATH)


def create_detector():
  ensure_model()
  options = vision.HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=vision.RunningMode.IMAGE,
    num_hands=MAX_HANDS,
    min_hand_detection_confidence=MIN_DETECTION_CONFIDENCE,
    min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
  )
  return vision.HandLandmarker.create_from_options(options)


def detect_hands(detector, frame):
  # Returns [{"label": "Left" | "Right", "landmarks": [21 landmarks]}]
  rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
  image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
  result = detector.detect(image)
  hands = []
  for landmarks, handedness in zip(result.hand_landmarks,
                                   result.handedness):
    hands.append({
      "label": handedness[0].category_name,
      "landmarks": landmarks,
    })
  return hands


def draw_landmarks(frame, landmarks):
  height, width = frame.shape[:2]
  points = [(int(lm.x * width), int(lm.y * height)) for lm in landmarks]
  for connection in CONNECTIONS:
    cv2.line(frame, points[connection.start], points[connection.end],
             CONNECTION_COLOR, CONNECTION_THICKNESS)
  for point in points:
    cv2.circle(frame, point, LANDMARK_RADIUS, LANDMARK_COLOR, cv2.FILLED)
