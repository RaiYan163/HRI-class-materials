import os
from dotenv import load_dotenv
load_dotenv()

# server.py
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
import serial
from openai import OpenAI
import traceback
import mode_manager  # Import the mode manager
import os
import json
import shutil
import time
import google.generativeai as genai
from PIL import Image

# Adjust COM port and baud rate as needed for your Arduino
try:
    ser = serial.Serial('COM3', 9600)
except Exception as e:
    print(f"[WARNING] Serial port not available: {e}")
    class DummySerial:
        def __init__(self): self.is_open = False
        def write(self, data): pass
    ser = DummySerial()

light_state = "off"

# Create an MCP server instance with a custom name.
mcp = FastMCP("Demo Server")

# OpenAI key
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Configure Gemini API for vision analysis
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
gemini_vision = genai.GenerativeModel("gemini-2.5-flash")  # Latest stable model

# YOLO integration paths
TEMP_FRAME = "temp/current_frame.jpg"
TEMP_METADATA = "temp/current_metadata.json"
FINAL_FRAME = "latest_frame.jpg"
FINAL_METADATA = "latest_metadata.json"


# Add a calculator tool: a simple function to add two numbers.
@mcp.tool()
def add(a: int, b: int) -> int:
    """
    Add two numbers together.
    
    :param a: First number.
    :param b: Second number.
    :return: Sum of the numbers.
    """
    return a + b

@mcp.tool()
def create_image(prompt: str) -> str:
    """
    Generates an image using OpenAI and returns a clickable markdown link.

    :param prompt: Prompt for image generation.
    :return: Markdown-formatted clickable link to the image.
    """
    try:
        result = client.images.generate(
            model="dall-e-2",  # Change to "dall-e-3" if your API access allows
            prompt=prompt,
            size="1024x1024"  # low-res image
        )
        image_url = result.data[0].url
        return f"[Link to your image created using OpenAI]({image_url})"

    except Exception as e:
        print("Exception during image generation:")
        traceback.print_exc()
        return f"Error generating image: {e}"



@mcp.tool()
def control_light(state: str) -> str:
    """
    Control the light by sending 'on' or 'off' to the Arduino.
    Updates light state regardless of serial port status, but notifies user.

    :param state: Desired state ('on' or 'off')
    :return: Status message
    """
    global light_state

    state = state.strip().lower()
    if state not in ["on", "off"]:
        return "Invalid state. Please specify 'on' or 'off'."

    if state == light_state:
        return f"The light is already {state.upper()}."

    light_state = state  # update state regardless

    # Try to send to serial port if available
    try:
        if ser.is_open:
            ser.write(f"{state}\n".encode())  # Send command
            return f"The light has been turned {state.upper()} (sent to Arduino)."
        else:
            return f"The light has been set to {state.upper()}, but serial port is not open."
    except Exception as e:
        return f"The light has been set to {state.upper()}, but failed to send to Arduino. Reason: {e}"


@mcp.tool()
def set_mode(mode: str) -> str:
    """
    Switch the assistant's personality mode (e.g., normal, santa, engineer, teacher, pirate).
    This changes how the assistant communicates while keeping all functionality intact.

    :param mode: The mode to activate (normal, santa, engineer, teacher, pirate)
    :return: Confirmation message or error if mode doesn't exist
    """
    success = mode_manager.set_mode(mode)
    if success:
        return f"Mode switched to '{mode.upper()}'. All future interactions will use this personality."
    else:
        available = ", ".join(mode_manager.list_available_modes())
        return f"Unknown mode '{mode}'. Available modes: {available}"


@mcp.tool()
def get_current_mode() -> str:
    """
    Get the currently active personality mode.

    :return: The name of the current mode
    """
    current = mode_manager.get_mode()
    description = mode_manager.get_mode_description(current)
    return f"Current mode: {current.upper()}\nDescription: {description}"


@mcp.tool()
def list_modes() -> str:
    """
    List all available personality modes.

    :return: List of available modes with descriptions
    """
    modes = mode_manager.list_available_modes()
    result = "Available Modes:\n\n"
    for mode in modes:
        desc = mode_manager.get_mode_description(mode)
        result += f"• {mode.upper()}: {desc}\n\n"
    result += f"Current mode: {mode_manager.get_mode().upper()}"
    return result


# ============================================================================
# YOLO VISION TOOLS
# ============================================================================

@mcp.tool()
def get_current_inference() -> str:
    """
    Get Gemini's intelligent analysis of the current camera scene.
    This captures a fresh snapshot from YOLO background server and analyzes it.
    
    :return: Natural language scene description from Gemini Vision
    """
    try:
        # Check if YOLO background server is running
        if not os.path.exists(TEMP_FRAME) or not os.path.exists(TEMP_METADATA):
            return "ERROR: YOLO background server not running. Please start yolo_background_server.py first."
        
        # Copy fresh snapshot from temp to latest (ONLY this function does this!)
        shutil.copy(TEMP_FRAME, FINAL_FRAME)
        shutil.copy(TEMP_METADATA, FINAL_METADATA)
        
        # Read metadata
        with open(FINAL_METADATA, 'r') as f:
            metadata = json.load(f)
        
        # Load image for Gemini Vision
        image = Image.open(FINAL_FRAME)
        
        # Create prompt with detection context
        prompt = f"""Analyze this camera frame naturally and conversationally.

Detection data shows: {metadata['summary']['total_objects']} objects detected - {', '.join([f"{count} {cls}" for cls, count in metadata['summary']['class_counts'].items()])}

Describe what you see in 2-3 sentences like you're telling a friend. Include:
- What's in the scene
- The environment/setting
- Any notable details

Be natural and concise."""

        # Call Gemini Vision API
        response = gemini_vision.generate_content([prompt, image])
        
        try:
            inference = response.candidates[0].content.parts[0].text.strip()
        except:
            inference = str(response.text).strip()
        
        return inference
        
    except Exception as e:
        print(f"[ERROR] Exception in get_current_inference: {e}")
        traceback.print_exc()
        return f"ERROR: Failed to analyze scene: {e}"


@mcp.tool()
def get_current_frame() -> str:
    """
    Returns the path to the latest captured frame.
    Note: Call get_current_inference() first to capture a fresh snapshot.
    
    :return: Path to latest frame image file
    """
    if not os.path.exists(FINAL_FRAME):
        return "ERROR: No snapshot available. Call get_current_inference() first to capture the scene."
    
    # Read metadata to get timestamp
    try:
        with open(FINAL_METADATA, 'r') as f:
            metadata = json.load(f)
        timestamp = metadata.get('datetime', 'unknown')
        return f"Frame available at: {FINAL_FRAME} (captured at {timestamp})"
    except:
        return f"Frame available at: {FINAL_FRAME}"


@mcp.tool()
def get_current_metadata() -> str:
    """
    Returns YOLO detection metadata from the latest snapshot.
    Note: Call get_current_inference() first to capture a fresh snapshot.
    
    :return: JSON string with detection data (objects, bounding boxes, counts)
    """
    if not os.path.exists(FINAL_METADATA):
        return "ERROR: No snapshot available. Call get_current_inference() first to capture the scene."
    
    try:
        with open(FINAL_METADATA, 'r') as f:
            metadata = json.load(f)
        
        # Check if data is stale
        age = time.time() - metadata['timestamp']
        if age > 10:
            metadata['warning'] = f"Data may be stale (captured {age:.1f} seconds ago)"
        
        return json.dumps(metadata, indent=2)
        
    except Exception as e:
        return f"ERROR: Failed to read metadata: {e}"


@mcp.tool()
def get_everything() -> str:
    """
    Returns complete camera report including frame path, metadata, and Gemini analysis.
    This captures a fresh snapshot and provides all available information.
    
    :return: Complete JSON report with all vision data
    """
    try:
        # Check if YOLO background server is running
        if not os.path.exists(TEMP_FRAME) or not os.path.exists(TEMP_METADATA):
            return "ERROR: YOLO background server not running. Please start yolo_background_server.py first."
        
        # Copy fresh snapshot from temp to latest
        shutil.copy(TEMP_FRAME, FINAL_FRAME)
        shutil.copy(TEMP_METADATA, FINAL_METADATA)
        
        # Read metadata
        with open(FINAL_METADATA, 'r') as f:
            metadata = json.load(f)
        
        # Load image for Gemini Vision
        image = Image.open(FINAL_FRAME)
        
        # Create prompt
        prompt = f"""Describe what you see in this camera frame naturally.

Detection: {metadata['summary']['total_objects']} objects - {', '.join([f"{count} {cls}" for cls, count in metadata['summary']['class_counts'].items()])}

Give a brief, natural description of the scene and environment in 2-3 sentences."""

        # Call Gemini Vision API
        response = gemini_vision.generate_content([prompt, image])
        
        try:
            inference = response.candidates[0].content.parts[0].text.strip()
        except:
            inference = str(response.text).strip()
        
        # Combine everything
        result = {
            "frame_path": FINAL_FRAME,
            "capture_time": metadata.get('datetime', 'unknown'),
            "metadata": metadata,
            "inference": inference
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        print(f"[ERROR] Exception in get_everything: {e}")
        traceback.print_exc()
        return f"ERROR: Failed to get complete report: {e}"


# Expose a greeting resource that dynamically constructs a personalized greeting.
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """
    Return a greeting for the given name.
    
    :param name: The name to greet.
    :return: A personalized greeting.
    """
    return f"Hello, {name}!"


@mcp.resource("light://state")
def get_light_state() -> str:
    """
    Expose the current light state as a read-only resource.

    :return: Current light status ("on"/"off")
    """
    return f"The current light state is {light_state.upper()}."

@mcp.prompt()
def check_fact(sentence: str) -> str:
    """
    Prompt to verify factual accuracy of a sentence.
    This prompt is mode-aware and will adapt to the current personality.

    :param sentence: The sentence to be evaluated.
    :return: A natural language prompt asking the LLM to check if the sentence is factually correct.
    """
    # Get current mode context for personality-aware response
    mode_context = mode_manager.get_mode_context()
    
    return f"{mode_context}\n\nIs the following sentence factually correct? Answer Yes or No and explain why.\n\nSentence: \"{sentence}\""


if __name__ == "__main__":
    print("The server is running!")
    mcp.run()  

#notice the change made here, please look into it.