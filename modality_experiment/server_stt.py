import logging
import os
import tempfile
from datetime import datetime

from faster_whisper import WhisperModel
from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")

app = Flask(__name__)
whisper_model = None


@app.route("/")
def index():
    return render_template("stt.html")


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


@app.route("/log", methods=["POST"])
def log_line():
    """Print a line from the page's System log to this console."""
    data = request.get_json(silent=True) or {}
    # Strip control characters so page text can't forge extra console lines
    clean = lambda value, limit: "".join(
        ch if ch.isprintable() else " " for ch in str(value)
    )[:limit]
    stamp = datetime.now().strftime("%H:%M:%S")
    tag = clean(data.get("tag", "LOG"), 12)
    print(f"{stamp}  {tag:<7} {clean(data.get('msg', ''), 500)}", flush=True)
    return "", 204


def main():
    global whisper_model
    os.makedirs(TEMP_DIR, exist_ok=True)
    # Hide Flask's per-request lines so the console shows only the system log
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    print("=== Speech-to-Text Server ===\n")
    print("Loading Whisper base model (CPU, int8)...")
    print("First run will download ~74MB — please wait...\n")
    whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    print("Model loaded. Ready.\n")
    print("Server running at http://localhost:5002\n")
    app.run(host="0.0.0.0", port=5002, debug=False)


if __name__ == "__main__":
    main()
