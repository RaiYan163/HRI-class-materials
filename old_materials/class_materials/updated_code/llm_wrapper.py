import os
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai
import re
import traceback
from mcp import ClientSession
import mode_manager  # Import mode manager for personality control

genai.configure(api_key=os.environ["GEMINI_API_KEY"])  # Replace with your Gemini key
gemini_llm = genai.GenerativeModel("gemini-2.5-flash")

class MCPWrapper:
    def __init__(self, session: ClientSession):
        self.session = session

    async def handle(self, user_input: str) -> str:
        # Get current mode context for personality-aware responses
        mode_context = mode_manager.get_mode_context()
        
        # LLM prompt to decide which action to take
        full_prompt = f"""
=== YOUR PERSONALITY (ALWAYS MAINTAIN THIS) ===
{mode_context}
=== END PERSONALITY ===

You are connected to an MCP server.
The available capabilities are:

1. Tool: add(a: int, b: int)
2. Tool: control_light(state: str)  → control light (state: 'on' or 'off')
3. Tool: create_image(prompt: str)  → generates an image using OpenAI
4. Tool: set_mode(mode: str)  → switch personality mode (normal, santa, engineer, teacher, pirate)
5. Tool: get_current_mode()  → get the current active mode
6. Tool: list_modes()  → list all available personality modes
7. Resource: greeting://{{name}}  → returns a personalized greeting
8. Resource: light://state  → returns current light state
9. Prompt: check_fact(sentence: str)  → checks if a sentence is factually correct

Response rules:
- For math like "Add 5 and 3", reply: CALL add a=5 b=3
- For light control like "Turn the light on", reply: CALL control_light state=on
- For image generation like "Create an image of a cat", reply: CALL create_image prompt=an image of a cat
- For mode switching like "Switch to santa mode", reply: CALL set_mode mode=santa
- For ending/exiting a mode like "End pirate mode" or "Exit santa mode", reply: CALL set_mode mode=normal
- For mode query like "What mode are you in?", reply: CALL get_current_mode
- For listing modes like "What modes are available?", reply: CALL list_modes
- For light state query like "What is the current light state?", reply: CALL resource light://state
- For greeting like "Greet Alice", reply: CALL resource greeting://Alice
- For fact checking like "Check if cows fly", reply: CALL prompt check_fact sentence=Cows fly in the sky
- Otherwise, reply: NO TOOL NEEDED <your direct reply IN CHARACTER based on your personality above>

IMPORTANT: When giving direct responses (NO TOOL NEEDED), you MUST stay fully in character according to your personality context at the top. This is critical!

USER: {user_input}
"""
        
        # Send prompt to LLM
        response = gemini_llm.generate_content(full_prompt)

        # Extract command from LLM response
        try:
            command = response.candidates[0].content.parts[0].text.strip()
        except:
            command = str(response.text).strip()

        # 1. Tool: Add
        if command.startswith("CALL add"):
            try:
                parts = command.split()
                a = int(parts[2].split("=")[1])
                b = int(parts[3].split("=")[1])
                result = await self.session.call_tool("add", arguments={"a": a, "b": b})
                # Extract only the actual result value (similar to resource handler)
                # Old version: result_text = result["result"] if isinstance(result, dict) and "result" in result else str(result)
                # print(f"[DEBUG] Raw response from MCP server: {result}")
                # print(f"[DEBUG] Response type: {type(result)}")
                if hasattr(result, "structuredContent") and isinstance(result.structuredContent, dict) and "result" in result.structuredContent:
                    result_text = result.structuredContent["result"]
                elif isinstance(result, dict) and "result" in result:
                    result_text = result["result"]
                else:
                    result_text = result
                return f"The result is {result_text}."
            except Exception as e:
                return f"Error parsing tool call: {e}"

        # 1b. Tool: control_light
        elif command.startswith("CALL control_light"):
            try:
                parts = command.split()
                state = parts[2].split("=")[1] if len(parts) > 2 and "=" in parts[2] else parts[2]
                result = await self.session.call_tool("control_light", arguments={"state": state})
                # Extract only the actual result value (similar to add tool)
                # print(f"[DEBUG] Raw response from MCP server (control_light): {result}")
                # print(f"[DEBUG] Response type: {type(result)}")
                if hasattr(result, "structuredContent") and isinstance(result.structuredContent, dict) and "result" in result.structuredContent:
                    result_text = result.structuredContent["result"]
                elif isinstance(result, dict) and "result" in result:
                    result_text = result["result"]
                else:
                    result_text = result
                return str(result_text)
            except Exception as e:
                return f"Error controlling light: {e}"

        # 1c. Tool: create_image
        elif command.startswith("CALL create_image"):
            try:
                # Extract prompt (handle values with spaces)
                if "prompt=" in command:
                    prompt = command.split("prompt=", 1)[1].strip()
                else:
                    # Fallback: get everything after "create_image"
                    prompt = command.split("CALL create_image", 1)[1].strip()
                result = await self.session.call_tool("create_image", arguments={"prompt": prompt})
                # Extract only the actual result value (similar to other tools)
                # print(f"[DEBUG] Raw response from MCP server (create_image): {result}")
                # print(f"[DEBUG] Response type: {type(result)}")
                if hasattr(result, "structuredContent") and isinstance(result.structuredContent, dict) and "result" in result.structuredContent:
                    result_text = result.structuredContent["result"]
                elif isinstance(result, dict) and "result" in result:
                    result_text = result["result"]
                else:
                    result_text = result
                return str(result_text)
            except Exception as e:
                return f"Error creating image: {e}"

        # 1d. Tool: set_mode (CLIENT-SIDE - updates local mode_manager)
        elif command.startswith("CALL set_mode"):
            try:
                parts = command.split()
                mode = parts[2].split("=")[1] if len(parts) > 2 and "=" in parts[2] else parts[2]
                
                # Update the CLIENT's mode_manager directly
                success = mode_manager.set_mode(mode)
                
                if success:
                    return f"Mode switched to '{mode.upper()}'. All future interactions will use this personality."
                else:
                    available = ", ".join(mode_manager.list_available_modes())
                    return f"Unknown mode '{mode}'. Available modes: {available}"
            except Exception as e:
                return f"Error setting mode: {e}"

        # 1e. Tool: get_current_mode (CLIENT-SIDE - reads local mode_manager)
        elif command.startswith("CALL get_current_mode"):
            try:
                current = mode_manager.get_mode()
                description = mode_manager.get_mode_description(current)
                return f"Current mode: {current.upper()}\nDescription: {description}"
            except Exception as e:
                return f"Error getting current mode: {e}"

        # 1f. Tool: list_modes (CLIENT-SIDE - reads local mode_manager)
        elif command.startswith("CALL list_modes"):
            try:
                modes = mode_manager.list_available_modes()
                result = "Available Modes:\n\n"
                for mode in modes:
                    desc = mode_manager.get_mode_description(mode)
                    result += f"• {mode.upper()}: {desc}\n\n"
                result += f"Current mode: {mode_manager.get_mode().upper()}"
                return result
            except Exception as e:
                return f"Error listing modes: {e}"

        # 2. Resource: greeting://{name} or light://state
        elif command.startswith("CALL resource"):
            try:
                uri = command.split("CALL resource")[1].strip()
                result = await self.session.read_resource(uri)
                # Extract only the text content from the resource
                # print(f"[DEBUG] Raw response from MCP server (read_resource): {result}")
                # print(f"[DEBUG] Response type: {type(result)}")
                if result.contents and hasattr(result.contents[0], "text"):
                    return result.contents[0].text.strip()
                else:
                    return str(result)
            except Exception as e:
                return f"Error retrieving resource: {e}"

        # 3. Prompt: check_fact
        elif command.startswith("CALL prompt"):
            try:
                ##print("[DEBUG] Inside CALL prompt block")
                ##print(f"[DEBUG] Raw command: {command}")
                
                # Extract prompt name and arguments
                # Format: "CALL prompt check_fact sentence=Some sentence here"
                parts = command.split()
                prompt_name = parts[2] if len(parts) > 2 else None
                
                ##print(f"[DEBUG] Extracted prompt_name: {prompt_name}")
                
                if not prompt_name:
                    return "Error: No prompt name specified"

                # Extract arguments dynamically - handle values with spaces
                args = {}
                remaining = " ".join(parts[3:]) if len(parts) > 3 else ""
                
                if remaining:
                    # Parse key=value pairs, handling values with spaces
                    # Match pattern: key=value (value can contain spaces until next key= or end)
                    matches = re.findall(r'(\w+)=(.+?)(?=\s+\w+=|$)', remaining)
                    for key, val in matches:
                        args[key.strip()] = val.strip()
                    
                    # If no matches found, treat entire remaining as sentence (fallback)
                    if not args and remaining:
                        args["sentence"] = remaining.strip()
                
                #print(f"[DEBUG] Extracted args: {args}")

                # Call MCP prompt with arguments (MCP will render the prompt)
                #print(f"[DEBUG] Calling get_prompt('{prompt_name}', arguments={args})")
                prompt_template = await self.session.get_prompt(prompt_name, arguments=args)
                # print(f"[DEBUG] Raw response from MCP server (get_prompt): {prompt_template}")
                # print(f"[DEBUG] Response type: {type(prompt_template)}")
                
                # Extract text message from the returned prompt (already rendered by MCP)
                raw_text = prompt_template.messages[0].content.text
                #print(f"[DEBUG] Rendered prompt from MCP:\n{raw_text}")

                # Send the rendered prompt to Gemini for contextual reasoning
                llm_response = gemini_llm.generate_content(raw_text)

                try:
                    result = llm_response.candidates[0].content.parts[0].text.strip()
                    #print(f"[DEBUG] Gemini response: {result}")
                    return result
                except:
                    result = str(llm_response.text).strip()
                    #print(f"[DEBUG] Gemini response (fallback): {result}")
                    return result

            except Exception as e:
                print(f"[ERROR] Exception occurred: {e}")
                traceback.print_exc()
                return f"Error processing prompt: {e}"

        # 4. No tool needed
        elif command.startswith("NO TOOL NEEDED"):
            return command.replace("NO TOOL NEEDED", "").strip()

        # 5. Fallback
        else:
            return f"Unrecognized LLM response: {command}"
