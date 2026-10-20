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

#OpenAI key.

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


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