import logging
import os
import re
import sys
import tempfile
import threading

from faster_whisper import WhisperModel
from flask import Flask, jsonify, render_template, request

# Reuse the camera prompts, capture loop and annotation drawing from the
# first demo. Its annotation state lives in that module, so the voice
# commands below edit the very lists the capture loop draws from.
import server_video as base

PORT = 5013
DEFAULT_SHAPE_SIZE = 50
TIMESTAMP_FONT_SIZE = 50

SHAPE_ALIASES = {
  "circle": "circle",
  "triangle": "triangle",
  "rectangle": "rectangle",
  "square": "rectangle",
  "pentagon": "pentagon",
  "hexagon": "hexagon",
}

app = Flask(__name__)
whisper_model = None


def clean_text(text):
  return re.sub(r"\s+", " ", text.lower().replace(",", " ")).strip(" .!?")


def parse_command(raw_text):
  """Turn a transcript into an action dict, or None if not a command."""
  words = clean_text(raw_text).split()
  if not words:
    return None
  # The first word is the command, so "text reset the world" writes that
  # sentence instead of resetting.
  first = words[0]
  if first == "text":
    content = " ".join(raw_text.strip(" .!?").split()[1:])
    return {"action": "text", "content": content} if content else None
  if first == "time":
    return {"action": "timestamp"}
  if first in ("reset", "clear"):
    return {"action": "reset"}
  for word in words:
    if word in SHAPE_ALIASES:
      return {"action": "shape", "shape": SHAPE_ALIASES[word]}
  return None


def post_to_base(path, payload=None):
  """Call a server_video.py route, so voice and the manual controls share
  one set of validation rules and one annotation format."""
  response = base.app.test_client().post(path, json=payload or {})
  return response.status_code == 200, response.get_json()


def apply_action(command, settings):
  """Apply a command using the page's settings. Returns (ok, message)."""
  x, y = settings["x"], settings["y"]
  size, font_size = settings["size"], settings["font_size"]
  kind = command["action"]
  if kind == "reset":
    ok, data = post_to_base("/reset")
    return ok, "Cleared everything"
  if kind == "timestamp":
    post_to_base("/timestamp_font_size",
                 {"font_size": TIMESTAMP_FONT_SIZE})
    ok, data = post_to_base("/toggle_timestamp")
    return ok, "Timestamp " + ("on" if data.get("show_timestamp") else "off")
  if kind == "text":
    ok, data = post_to_base(
      "/add_text", {"content": command["content"], "x": x, "y": y,
                    "font_size": font_size})
    return ok, data.get("error") or \
      f"Text \"{command['content']}\" at ({x}, {y}), size {font_size}"
  ok, data = post_to_base(
    "/add_shape",
    {"shape": command["shape"], "x": x, "y": y, "size": size})
  return ok, data.get("error") or \
    f"{command['shape'].capitalize()} at ({x}, {y}), size {size}"


def read_settings(form):
  """Read the page's inputs; empty or invalid fields use the defaults."""
  width, height = current_frame_size()
  defaults = {"x": (width or 0) // 2, "y": (height or 0) // 2,
              "size": DEFAULT_SHAPE_SIZE,
              "font_size": base.DEFAULT_FONT_SIZE}
  values = {}
  for name, default in defaults.items():
    raw = form.get(name, "").strip()
    values[name] = int(raw) if raw.isdigit() and int(raw) > 0 else \
      max(default, 1)
  return values


def current_frame_size():
  with base.state_lock:
    return base.frame_width, base.frame_height


@app.route("/")
def index():
  return render_template("voice.html")


app.add_url_rule("/frame", "frame", base.frame)


@app.route("/frame_size")
def frame_size():
  width, height = current_frame_size()
  if width is None:
    return jsonify({"error": "No frame available yet"}), 404
  return jsonify({"width": int(width), "height": int(height)})


@app.route("/transcribe", methods=["POST"])
def transcribe():
  audio_file = request.files.get("audio")
  if audio_file is None:
    return jsonify({"error": "No audio file received"}), 400

  with tempfile.NamedTemporaryFile(
    delete=False, suffix=".webm", dir=base.TEMP_DIR
  ) as tmp:
    audio_file.save(tmp.name)
    tmp_path = tmp.name

  try:
    segments, _ = whisper_model.transcribe(
      tmp_path, beam_size=5, language="en", vad_filter=True)
    transcript = " ".join(segment.text.strip() for segment in segments)
  except Exception as e:
    return jsonify({"error": str(e)}), 500
  finally:
    if os.path.exists(tmp_path):
      os.remove(tmp_path)

  result = {"transcript": transcript, "result": None, "ok": True}
  if transcript.strip():
    command = parse_command(transcript)
    if command:
      ok, message = apply_action(command, read_settings(request.form))
      result["result"] = message
      result["ok"] = ok
  return jsonify(result)


def main():
  global whisper_model
  os.makedirs(base.TEMP_DIR, exist_ok=True)
  logging.getLogger("werkzeug").setLevel(logging.WARNING)

  print("=== Voice Annotation Server ===\n")
  print("Loading Whisper base model (CPU, int8)...\n")
  whisper_model = WhisperModel("base", device="cpu", compute_type="int8")

  print("Scanning for available cameras...\n")
  available = base.discover_cameras()
  if not available:
    print("Error: no cameras found.")
    sys.exit(1)
  camera_index = base.choose_camera(available)
  fps = base.choose_fps()

  thread = threading.Thread(
    target=base.capture_loop, args=(camera_index, fps))
  thread.daemon = True
  thread.start()

  print(f"\nStarting stream from Camera {camera_index} at {fps} FPS...")
  print(f"Server running at http://localhost:{PORT}\n")
  app.run(host="0.0.0.0", port=PORT, debug=False)


if __name__ == "__main__":
  main()
