import logging
import os
import threading
import time
import urllib.request
import wave
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_file

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
VOICES_DIR = os.path.join(BASE_DIR, "voices")
AUDIO_PATH = os.path.join(TEMP_DIR, "output.wav")

HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en"
MAX_LOG_ENTRIES = 200

app = Flask(__name__)

# ── Logging ────────────────────────────────────────────────────────
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


# ── Available voices ───────────────────────────────────────────────
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
        log(f"Downloading voice model: {voice['model']} (~60MB)...", "info")
        download(voice["url_model"], model_path)
        log(f"Downloaded: {voice['model']}", "info")

    if not os.path.exists(config_path):
        log(f"Downloading voice config: {voice['config']}...", "info")
        download(voice["url_config"], config_path)
        log(f"Downloaded: {voice['config']}", "info")

    return model_path, config_path


def load_voice(voice):
    """Return the loaded PiperVoice for this voice, loading it on first use."""
    if voice["id"] not in loaded_voices:
        from piper import PiperVoice

        model_path, config_path = ensure_voice_downloaded(voice)
        log(f"Loading voice into memory: {voice['label']}...", "info")
        loaded_voices[voice["id"]] = PiperVoice.load(model_path, config_path=config_path)
    return loaded_voices[voice["id"]]


# ── Flask routes ───────────────────────────────────────────────────
@app.route("/")
def index():
    voices_for_template = [{"id": v["id"], "label": v["label"]} for v in VOICES]
    return render_template("tts.html", voices=voices_for_template)


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
    log(f"Received text: \"{preview[:60]}{'...' if len(preview) > 60 else ''}\"", "info")
    log(f"Selected voice: {voice['label']}", "info")

    try:
        with synth_lock:  # one synthesis at a time, so output.wav is never mixed up
            piper_voice = load_voice(voice)
            log("Synthesizing audio...", "info")
            started = time.time()

            tmp_path = AUDIO_PATH + ".tmp"
            with wave.open(tmp_path, "wb") as wav:
                piper_voice.synthesize_wav(text, wav)
            os.replace(tmp_path, AUDIO_PATH)  # /audio never sees a half-written file

        log(f"Audio ready in {time.time() - started:.1f}s. Hit Convert to play.", "success")
        return jsonify({"status": "ok"})

    except Exception as e:
        log(f"Synthesis error: {e}", "error")
        return jsonify({"error": str(e)}), 500


@app.route("/audio")
def audio():
    if os.path.exists(AUDIO_PATH):
        response = send_file(AUDIO_PATH, mimetype="audio/wav")
        response.headers["Cache-Control"] = "no-store"
        return response
    return jsonify({"error": "No audio available yet"}), 404


@app.route("/logs")
def get_logs():
    return jsonify(log_entries)


def main():
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(VOICES_DIR, exist_ok=True)
    # The page polls /logs every 2s; hide Flask's per-request lines so the console stays readable
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    log("=== TTS Server starting ===", "info")
    log("Server running at http://localhost:5003", "info")
    log("Select a voice and type text to begin.", "info")
    app.run(host="0.0.0.0", port=5003, debug=False)


if __name__ == "__main__":
    main()
