import os
import sys
import threading
import time

import cv2
from flask import Flask, jsonify, render_template, send_file

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
FRAME_PATH = os.path.join(TEMP_DIR, "frame.jpg")

FPS_OPTIONS = {"1": 5, "2": 10, "3": 15, "4": 24}
MAX_CAMERA_INDEX = 4

app = Flask(__name__)


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


def capture_loop(camera_index, fps):
    os.makedirs(TEMP_DIR, exist_ok=True)
    cap = cv2.VideoCapture(camera_index)
    delay = 1.0 / fps
    tmp_path = FRAME_PATH + ".tmp"
    while True:
        ok, frame = cap.read()
        if ok:
            ok, buffer = cv2.imencode(".jpg", frame)
            if ok:
                with open(tmp_path, "wb") as f:
                    f.write(buffer.tobytes())
                os.replace(tmp_path, FRAME_PATH)
        else:
            print("[WARNING] Failed to read frame from camera")
        time.sleep(delay)


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


def main():
    os.makedirs(TEMP_DIR, exist_ok=True)
    print("=== Video Stream Server ===\n")
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
    print("Server running at http://localhost:5001\n")
    app.run(host="0.0.0.0", port=5001, debug=False)


if __name__ == "__main__":
    main()
