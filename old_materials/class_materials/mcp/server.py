# server.py
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
import serial
from openai import OpenAI
import traceback

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

client = OpenAI(api_key="your_openai_api_key")


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

    :param sentence: The sentence to be evaluated.
    :return: A natural language prompt asking the LLM to check if the sentence is factually correct.
    """
    return f"Is the following sentence factually correct? Answer Yes or No and explain why.\n\nSentence: \"{sentence}\""


if __name__ == "__main__":
    print("The server is running!")
    mcp.run()  

#notice the change made here, please look into it.