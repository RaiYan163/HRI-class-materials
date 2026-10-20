import logging
import os
import sys
import tempfile
import threading
import time
import urllib.request
import wave
from datetime import datetime

import cv2
from faster_whisper import WhisperModel
from flask import Flask, jsonify, render_template, request, send_file

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
VOICES_DIR = os.path.join(BASE_DIR, "voices")
FRAME_PATH = os.path.join(TEMP_DIR, "frame.jpg")
AUDIO_PATH = os.path.join(TEMP_DIR, "output.wav")

PORT = 5004
FPS_OPTIONS = {"1": 5, "2": 10, "3": 15, "4": 24}
MAX_CAMERA_INDEX = 4
HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en"
MAX_LOG_ENTRIES = 200

app = Flask(__name__)
whisper_model = None

# ── Logging (one shared log for all three modalities) ──────────────
log_entries = []  # in-memory log served to the frontend at /logs


def log(message, level="info"):
    """Append a timestamped entry to the in-memory log and print it."""
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "message": message,
    }
    log_entries.append(entry)
    del log_entries[:-MAX_LOG_ENTRIES]
    print(f"[{entry['time']}] [{level.upper()}] {message}", flush=True)


# ── Video ──────────────────────────────────────────────────────────
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
    cap = cv2.VideoCapture(camera_index)
    delay = 1.0 / fps
    tmp_path = FRAME_PATH + ".tmp"
    while True:
        ok, frame = cap.read()
        if ok:
            ok, buffer = cv2.imencode(".jpg", frame)
            if ok:
                # Write to a temp file, then swap, so /frame never reads a half-written JPEG
                with open(tmp_path, "wb") as f:
                    f.write(buffer.tobytes())
                os.replace(tmp_path, FRAME_PATH)
        else:
            print("[WARNING] Failed to read frame from camera")
        time.sleep(delay)


# ── Text-to-speech voices (Piper) ──────────────────────────────────
def make_voice(voice_id, label, locale, name):
    """Piper 'medium' voice hosted in the rhasspy/piper-voices repo."""
    stem = f"{locale}-{name}-medium"
    path = f"{HF_BASE}/{locale}/{name}/medium/{stem}.onnx"
    return {
        "id": voice_id,
        "label": label,
        "model": f"{stem}.onnx",
        "config": f"{stem}.onnx.json",
        "url_model": path,
        "url_config": path + ".json",
    }


VOICES = [
    make_voice("lessac", "American English · Female (Lessac)", "en_US", "lessac"),
    make_voice("ryan", "American English · Male (Ryan)", "en_US", "ryan"),
    make_voice("alan", "British English · Male (Alan)", "en_GB", "alan"),
    make_voice("amy", "American English · Female (Amy)", "en_US", "amy"),
]

loaded_voices = {}  # voice id -> PiperVoice, so each model is loaded only once
synth_lock = threading.Lock()


def get_voice_by_id(voice_id):
    for v in VOICES:
        if v["id"] == voice_id:
            return v
    return None


def download(url, dest):
    """Download to a temporary name, then rename, so a partial file is never used."""
    part = dest + ".part"
    urllib.request.urlretrieve(url, part)
    os.replace(part, dest)


def ensure_voice_downloaded(voice):
    """Download the .onnx and .onnx.json files if not already present."""
    model_path = os.path.join(VOICES_DIR, voice["model"])
    config_path = os.path.join(VOICES_DIR, voice["config"])

    if not os.path.exists(model_path):
        log(f"[TTS] Downloading voice model: {voice['model']} (~60MB)...")
        download(voice["url_model"], model_path)
        log(f"[TTS] Downloaded: {voice['model']}")

    if not os.path.exists(config_path):
        log(f"[TTS] Downloading voice config: {voice['config']}...")
        download(voice["url_config"], config_path)
        log(f"[TTS] Downloaded: {voice['config']}")

    return model_path, config_path


def load_voice(voice):
    """Return the loaded PiperVoice for this voice, loading it on first use."""
    if voice["id"] not in loaded_voices:
        from piper import PiperVoice

        model_path, config_path = ensure_voice_downloaded(voice)
        log(f"[TTS] Loading voice into memory: {voice['label']}...")
        loaded_voices[voice["id"]] = PiperVoice.load(model_path, config_path=config_path)
    return loaded_voices[voice["id"]]


# ── Routes ─────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("full.html")


@app.route("/frame")
def frame():
    if os.path.exists(FRAME_PATH):
        response = send_file(FRAME_PATH, mimetype="image/jpeg")
        response.headers["Cache-Control"] = "no-store"
        return response
    return jsonify({"error": "No frame available yet"}), 404


@app.route("/transcribe", methods=["POST"])
def transcribe():
    audio_file = request.files.get("audio")
    if audio_file is None:
        return jsonify({"error": "No audio file received"}), 400

    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".webm", dir=TEMP_DIR
    ) as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        segments, _ = whisper_model.transcribe(
            tmp_path,
            beam_size=5,
            language="en",
            vad_filter=True,
        )
        transcript = " ".join(segment.text.strip() for segment in segments)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return jsonify({"transcript": transcript})


@app.route("/voices")
def list_voices():
    return jsonify([{"id": v["id"], "label": v["label"]} for v in VOICES])


@app.route("/synthesize", methods=["POST"])
def synthesize():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    voice_id = (data.get("voice_id") or "lessac").strip()

    if not text:
        return jsonify({"error": "No text provided"}), 400

    voice = get_voice_by_id(voice_id)
    if voice is None:
        return jsonify({"error": f"Unknown voice: {voice_id}"}), 400

    preview = " ".join(text.split())  # one line, so the log stays readable
    log(f"[TTS] Received text: \"{preview[:60]}{'...' if len(preview) > 60 else ''}\"")
    log(f"[TTS] Selected voice: {voice['label']}")

    try:
        with synth_lock:  # one synthesis at a time, so output.wav is never mixed up
            piper_voice = load_voice(voice)
            log("[TTS] Synthesizing audio...")
            started = time.time()

            tmp_path = AUDIO_PATH + ".tmp"
            with wave.open(tmp_path, "wb") as wav:
                piper_voice.synthesize_wav(text, wav)
            os.replace(tmp_path, AUDIO_PATH)  # /audio never sees a half-written file

        log(f"[TTS] Audio ready in {time.time() - started:.1f}s", "success")
        return jsonify({"status": "ok"})

    except Exception as e:
        log(f"[TTS] Synthesis error: {e}", "error")
        return jsonify({"error": str(e)}), 500


@app.route("/audio")
def audio():
    if os.path.exists(AUDIO_PATH):
        response = send_file(AUDIO_PATH, mimetype="audio/wav")
        response.headers["Cache-Control"] = "no-store"
        return response
    return jsonify({"error": "No audio available yet"}), 404


@app.route("/log", methods=["POST"])
def log_line():
    """Add a line from the page (video / STT events) to the shared log."""
    data = request.get_json(silent=True) or {}
    # Strip control characters so page text can't forge extra console lines
    clean = lambda value, limit: "".join(
        ch if ch.isprintable() else " " for ch in str(value)
    )[:limit]
    level = data.get("level")
    if level not in ("info", "success", "error"):
        level = "info"
    log(f"[{clean(data.get('tag', 'LOG'), 12)}] {clean(data.get('msg', ''), 500)}", level)
    return "", 204


@app.route("/logs")
def get_logs():
    return jsonify(log_entries)


def main():
    global whisper_model
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(VOICES_DIR, exist_ok=True)
    # The page polls /logs; hide Flask's per-request lines so the console stays readable
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    print("=== Central Modality Server (video + speech-to-text + text-to-speech) ===\n")
    print("Scanning for available cameras...\n")
    available = discover_cameras()
    if not available:
        print("Error: no cameras found. Connect a camera or close apps that are using it.")
        sys.exit(1)

    camera_index = choose_camera(available)
    fps = choose_fps()

    print("\nLoading Whisper base model (CPU, int8)...")
    print("First run will download ~74MB — please wait...\n")
    whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    print("Model loaded. Piper voices load on first use.\n")

    thread = threading.Thread(target=capture_loop, args=(camera_index, fps))
    thread.daemon = True
    thread.start()

    log(f"[VIDEO] Streaming Camera {camera_index} at {fps} FPS")
    log(f"=== Central server running at http://localhost:{PORT} ===", "success")
    app.run(host="0.0.0.0", port=PORT, debug=False)


if __name__ == "__main__":
    main()
