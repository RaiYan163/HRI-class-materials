# class_materials

An MCP (Model Context Protocol) practice project from the HRI class (2025). A Python MCP server exposes tools, resources and a prompt. An LLM client (Google Gemini) reads what the user types, decides which MCP capability to use, and calls it. On top of that there are five switchable personality modes (for example Santa or Pirate) and a live camera feed analysed by YOLO and Gemini Vision.

For the original write-up, including bugs fixed during development, see `PROJECT_DOCUMENTATION.txt`.

## How it fits together

```
yolo_background_server.py ──writes──> temp/current_frame.jpg
   (webcam + YOLOv8n)                 temp/current_metadata.json
                                                │ read by
llm_client.py ──> llm_wrapper.py ──(MCP, stdio)──> server.py ──> OpenAI DALL-E, Gemini Vision, Arduino
   (CLI)         (Gemini decides      server.py is launched                (serial, COM3)
                  what to call)       by the client as a subprocess
                       │
                  mode_manager.py (personality, kept on the client side)
```

- The client starts `server.py` as a subprocess and talks to it over stdio.
- Gemini (`gemini-2.5-flash`) is given the list of capabilities and the user's message. The wrapper then runs the choice it makes.
- **Mode switching happens on the client.** The client and server are separate processes, so each has its own copy of `mode_manager`. The server's copy would never affect the client's prompts. `llm_wrapper.py` therefore handles `set_mode`, `get_current_mode` and `list_modes` locally, even though `server.py` also defines tools with those names.
- The YOLO server runs on its own and only writes files. When the user asks about the camera, `server.py` copies `temp/` to `latest_frame.jpg` and `latest_metadata.json`, then sends the frame and detection counts to Gemini Vision.

## What the MCP server provides (`server.py`)

| Type | Name | What it does |
|------|------|--------------|
| Tool | `add(a, b)` | Adds two integers. |
| Tool | `control_light(state)` | Sends `on` or `off` to an Arduino over serial (`COM3`, 9600 baud). If the port is missing it falls back to a dummy serial object and just tracks the state. |
| Tool | `create_image(prompt)` | Generates a 1024x1024 image with OpenAI `dall-e-2` and returns a markdown link. |
| Tool | `set_mode`, `get_current_mode`, `list_modes` | Personality mode controls (see the note above on where they really run). |
| Tool | `get_current_inference()` | Copies the latest YOLO snapshot and returns Gemini's 2-3 sentence description of the scene. |
| Tool | `get_current_frame()` | Returns the path and capture time of the latest saved frame. |
| Tool | `get_current_metadata()` | Returns the YOLO detections as JSON (adds a warning if the data is over 10 seconds old). |
| Tool | `get_everything()` | Returns a JSON report: frame path, metadata and Gemini description. |
| Resource | `greeting://{name}` | Returns `Hello, {name}!`. |
| Resource | `light://state` | Returns the current light state. |
| Prompt | `check_fact(sentence)` | A fact-checking prompt, prefixed with the current personality. |

## Personality modes (`mode_manager.py`)

`normal` (default), `santa`, `engineer`, `teacher`, `pirate`. The active mode's description is placed at the top of every Gemini prompt. To add a mode, add an entry to the `MODES` dictionary. To leave a mode, switch back to `normal`.

## Files

**Core**

| File | Purpose |
|------|---------|
| `server.py` | The MCP server (tools, resources and prompt above). |
| `llm_wrapper.py` | Version 1 client logic. Gemini replies with text commands such as `CALL add a=5 b=3`, and the wrapper parses them. This version knows about all the tools, including the camera ones. |
| `llm_wrapper_v2.py` | Version 2. Gemini replies with JSON (`call_tool`, `read_resource`, `get_prompt` or `direct_response`), which is more robust to parse. **Its prompt does not list the camera tools**, and it sends `set_mode` to the server instead of handling it on the client, so personality switching does not persist in v2. Use v1 for the full feature set. |
| `llm_client.py` / `llm_client_v2.py` | Interactive CLI using v1 or v2. They start `server.py` and loop on `You:` input. Type `exit` or `quit` to leave. |
| `mode_manager.py` | Personality definitions and the get/set functions. |
| `yolo_background_server.py` | Reads the webcam (`CAMERA_INDEX = 1`, the external camera), runs YOLOv8n at up to 10 FPS with confidence 0.5, and writes the annotated frame and detection JSON to `temp/`. Shows a preview window. Press `q` or Ctrl+C to quit. |

**Utilities and demos**

| File | Purpose |
|------|---------|
| `client.py` | Minimal MCP client that calls `add(3, 4)`. |
| `inspect_server.py` | Connects to the server and lists its tools, resources and prompts. |
| `check_mcp.py`, `check_error.py` | Print the methods of the MCP `ClientSession` class. |
| `check_models.py` | Lists the Gemini models your key can use. |
| `openAI_model_list.py` | Lists the OpenAI image models. |
| `generate_image.py` | Standalone DALL-E script that prompts you for an image description. |

**Other**

| Path | What it is |
|------|------------|
| `PROJECT_DOCUMENTATION.txt` | Full project notes, prompt design, bug history and troubleshooting. |
| `command.txt` | Setup commands from class (Windows virtual environment activation, installs). |
| `requirements.txt` | Python dependencies. |
| `mcp/` | Earliest snapshot (Nov 10, 2025): the basic server and wrapper with no personality modes or camera, plus `explanation.docx` with class notes on async MCP. Its scripts use placeholder keys. |
| `updated_code/` | Mid-way snapshot (Nov 12, 2025) with `server.py`, `llm_wrapper.py`, `llm_client.py` before the camera tools were added. It still imports `mode_manager`, so it needs the top-level `mode_manager.py`. |
| `mcp.zip`, `updated_code.zip` | Zipped copies of those two folders. Not tracked in git. |
| `temp/`, `latest_frame.jpg`, `latest_metadata.json` | Output from a past YOLO run. They are regenerated when you run the camera server. |
| `yolov8n.pt` | YOLOv8 nano weights (about 6.5 MB). Not tracked in git, and `ultralytics` downloads it on first run. |

## Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   ```
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Add your keys to a `.env` file. Copy `../.env.example` into this folder as `.env`, or into the folder you run from, and fill it in:
   ```
   OPENAI_API_KEY=your_openai_api_key
   GEMINI_API_KEY=your_gemini_api_key
   ```
   Get a Gemini key at https://makersuite.google.com/app/apikey and an OpenAI key at https://platform.openai.com/api-keys. `.env` is git-ignored, so never commit it.

## Running

Run everything from this folder, because the scripts use relative paths such as `temp/` and `server.py`.

```bash
python llm_client.py            # chat client, starts server.py itself
python llm_client_v2.py         # same, with JSON routing (no camera tools)
python yolo_background_server.py  # in a second terminal, only for camera questions
python inspect_server.py        # list what the server exposes
```

Example things to type at `You:`:

- `Add 5 and 3`
- `Switch to pirate mode`, then `Hello`
- `Turn the light on`
- `Create an image of a snowman`
- `What do you see?` or `How many people are there?` (needs the YOLO server running)
- `Greet Alice`, `What is the light state?`, `Check if cows can fly`

## Notes and known quirks

- `server.py` and the wrappers need `GEMINI_API_KEY` and `OPENAI_API_KEY` set at startup. Without them they stop with a `KeyError`.
- `PROJECT_DOCUMENTATION.txt` lists only four dependencies. `requirements.txt` is the up-to-date list: it also covers `ultralytics`, `opencv-python`, `pillow` and `python-dotenv`.
- `command.txt` and the docs mention Windows (`COM3`, `venv\Scripts\activate`). On a Mac or Linux the Arduino port will be something like `/dev/tty.usbmodem...`, so change the port in `server.py`. Without an Arduino the light tool still works in simulated mode.
- The camera index is set to `1` (external camera). Change `CAMERA_INDEX` to `0` for a built-in webcam.
- Gemini and DALL-E calls use the free or paid quota of your own keys, and `dall-e-2` may be retired.
- The `latest_frame.jpg` and `temp/current_frame.jpg` files are real webcam captures, so check them for people before sharing.
