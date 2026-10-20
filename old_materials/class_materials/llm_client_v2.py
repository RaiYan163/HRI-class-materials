# llm_client_v2.py
# Client that uses the improved MCPWrapperV2

import asyncio
from llm_wrapper_v2 import MCPWrapperV2
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_llm_cli():
    """Run the interactive CLI using MCPWrapperV2"""
    server_params = StdioServerParameters(command="python", args=["server.py"])

    async with stdio_client(server_params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            wrapper = MCPWrapperV2(session)

            print("=== LLM CLI v2 Started (Using JSON-based routing) ===")
            print("Type 'exit' to quit.\n")
            
            while True:
                user_input = input("You: ")
                if user_input.lower() in ["exit", "quit"]:
                    break
                response = await wrapper.handle(user_input)
                print("Bot:", response)
                print()  # Extra line for readability

if __name__ == "__main__":
    asyncio.run(run_llm_cli())

