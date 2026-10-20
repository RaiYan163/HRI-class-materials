import os
from dotenv import load_dotenv
load_dotenv()

"""
MCPWrapper v2 - Improved version using structured JSON output
This version follows best practices:
- Uses JSON for structured LLM responses (more robust parsing)
- Clear separation between decision layer (LLM) and execution layer (MCP)
- Better error handling and response extraction
- Cleaner code structure
"""

import google.generativeai as genai
import json
import traceback
from mcp import ClientSession
import mode_manager  # Import mode manager for personality control

# Configure Gemini API
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
gemini_llm = genai.GenerativeModel("gemini-2.5-flash")


class MCPWrapperV2:
    """
    Agent wrapper that uses LLM to interpret natural language
    and route to appropriate MCP capabilities.
    """
    
    def __init__(self, session: ClientSession):
        """
        Initialize the wrapper with an MCP session.
        
        Args:
            session: Active MCP ClientSession for server communication
        """
        self.session = session
    
    async def handle(self, user_input: str) -> str:
        """
        Main entry point: interpret user input and execute appropriate MCP action.
        
        Args:
            user_input: Natural language user request
            
        Returns:
            User-friendly response string
        """
        try:
            # Step 1: Get LLM decision (structured JSON)
            action_data = await self._get_llm_decision(user_input)
            print(f"[DEBUG] LLM Decision: {json.dumps(action_data, indent=2)}")
            
            # Step 2: Execute the appropriate MCP action
            result = await self._execute_action(action_data)
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Exception in handle(): {e}")
            traceback.print_exc()
            return f"I encountered an error: {str(e)}"
    
    async def _get_llm_decision(self, user_input: str) -> dict:
        """
        Use LLM to decide which MCP action to take.
        Returns structured JSON instead of plain text.
        
        Args:
            user_input: User's natural language input
            
        Returns:
            Dictionary with action details
        """
        # Get current mode context for personality-aware responses
        mode_context = mode_manager.get_mode_context()
        
        prompt = f"""
=== YOUR PERSONALITY (ALWAYS MAINTAIN THIS) ===
{mode_context}
=== END PERSONALITY ===

You are connected to an MCP server.

Available MCP capabilities:

TOOLS (call_tool):
- add(a: int, b: int) → adds two numbers
- control_light(state: str) → controls light ('on' or 'off')
- create_image(prompt: str) → generates an image using OpenAI DALL-E
- set_mode(mode: str) → switch personality mode (normal, santa, engineer, teacher, pirate)
- get_current_mode() → get the current active mode
- list_modes() → list all available personality modes

RESOURCES (read_resource):
- greeting://{{name}} → personalized greeting
- light://state → current light state

PROMPTS (get_prompt):
- check_fact(sentence: str) → fact-checking prompt template

Instructions:
Respond with ONLY valid JSON in this exact format:

For tools:
{{"action": "call_tool", "tool": "add", "args": {{"a": 5, "b": 3}}}}
{{"action": "call_tool", "tool": "set_mode", "args": {{"mode": "santa"}}}}
{{"action": "call_tool", "tool": "get_current_mode", "args": {{}}}}
{{"action": "call_tool", "tool": "list_modes", "args": {{}}}}

For resources:
{{"action": "read_resource", "uri": "greeting://Alice"}}

For prompts:
{{"action": "get_prompt", "prompt": "check_fact", "args": {{"sentence": "Cows can fly"}}}}

For direct response (no MCP needed):
{{"action": "direct_response", "message": "Your answer here"}}

CRITICAL: When using "direct_response", your message MUST be fully in character according to your personality context at the top. This is non-negotiable!

USER INPUT: {user_input}

Respond with JSON only:"""

        # Get LLM response
        response = gemini_llm.generate_content(prompt)
        
        # Extract text from response
        try:
            response_text = response.candidates[0].content.parts[0].text.strip()
        except:
            response_text = str(response.text).strip()
        
        print(f"[DEBUG] Raw LLM Response:\n{response_text}")
        
        # Parse JSON (handle markdown code blocks if present)
        json_text = self._extract_json(response_text)
        action_data = json.loads(json_text)
        
        return action_data
    
    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from text, handling markdown code blocks.
        
        Args:
            text: Text potentially containing JSON
            
        Returns:
            Clean JSON string
        """
        # Remove markdown code blocks if present
        text = text.strip()
        if text.startswith("```"):
            # Find the content between ``` markers
            lines = text.split("\n")
            # Skip first line (```json or ```)
            json_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_block = not in_block
                    continue
                if in_block or not line.strip().startswith("```"):
                    json_lines.append(line)
            text = "\n".join(json_lines).strip()
        
        return text
    
    async def _execute_action(self, action_data: dict) -> str:
        """
        Execute the MCP action based on LLM decision.
        
        Args:
            action_data: Structured action from LLM
            
        Returns:
            User-friendly result string
        """
        action = action_data.get("action")
        
        if action == "call_tool":
            return await self._handle_tool_call(action_data)
        
        elif action == "read_resource":
            return await self._handle_resource_read(action_data)
        
        elif action == "get_prompt":
            return await self._handle_prompt_call(action_data)
        
        elif action == "direct_response":
            return action_data.get("message", "No response provided.")
        
        else:
            return f"Unknown action type: {action}"
    
    async def _handle_tool_call(self, action_data: dict) -> str:
        """
        Handle MCP tool calls.
        
        Args:
            action_data: Contains tool name and arguments
            
        Returns:
            Formatted result
        """
        tool_name = action_data.get("tool")
        args = action_data.get("args", {})
        
        print(f"[DEBUG] Calling tool: {tool_name} with args: {args}")
        
        # Call the MCP tool
        result = await self.session.call_tool(tool_name, arguments=args)
        
        print(f"[DEBUG] Raw MCP response: {result}")
        print(f"[DEBUG] Response type: {type(result)}")
        
        # Extract the actual result value
        result_value = self._extract_result(result)
        
        # Format user-friendly response based on tool
        if tool_name == "add":
            return f"The result is {result_value}."
        elif tool_name == "control_light":
            return str(result_value)
        elif tool_name == "create_image":
            return str(result_value)
        else:
            return str(result_value)
    
    async def _handle_resource_read(self, action_data: dict) -> str:
        """
        Handle MCP resource reads.
        
        Args:
            action_data: Contains resource URI
            
        Returns:
            Resource content
        """
        uri = action_data.get("uri")
        
        print(f"[DEBUG] Reading resource: {uri}")
        
        # Read the MCP resource
        result = await self.session.read_resource(uri)
        
        print(f"[DEBUG] Raw MCP response: {result}")
        print(f"[DEBUG] Response type: {type(result)}")
        
        # Extract text content from resource
        if result.contents and hasattr(result.contents[0], "text"):
            return result.contents[0].text.strip()
        else:
            return str(result)
    
    async def _handle_prompt_call(self, action_data: dict) -> str:
        """
        Handle MCP prompt calls.
        Prompts are templates that get rendered and then sent to LLM for reasoning.
        
        Args:
            action_data: Contains prompt name and arguments
            
        Returns:
            LLM's response to the rendered prompt
        """
        prompt_name = action_data.get("prompt")
        args = action_data.get("args", {})
        
        print(f"[DEBUG] Getting prompt: {prompt_name} with args: {args}")
        
        # Get the rendered prompt template from MCP server
        prompt_template = await self.session.get_prompt(prompt_name, arguments=args)
        
        print(f"[DEBUG] Raw MCP response: {prompt_template}")
        print(f"[DEBUG] Response type: {type(prompt_template)}")
        
        # Extract the rendered prompt text
        rendered_text = prompt_template.messages[0].content.text
        print(f"[DEBUG] Rendered prompt:\n{rendered_text}")
        
        # Send the rendered prompt to LLM for reasoning
        llm_response = gemini_llm.generate_content(rendered_text)
        
        # Extract LLM's answer
        try:
            result = llm_response.candidates[0].content.parts[0].text.strip()
        except:
            result = str(llm_response.text).strip()
        
        return result
    
    def _extract_result(self, result) -> any:
        """
        Extract the actual result value from MCP response.
        Handles different response formats.
        
        Args:
            result: Raw MCP response
            
        Returns:
            Extracted result value
        """
        # Check for structuredContent format
        if hasattr(result, "structuredContent") and isinstance(result.structuredContent, dict):
            if "result" in result.structuredContent:
                return result.structuredContent["result"]
        
        # Check for dictionary format
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        
        # Return as-is
        return result

