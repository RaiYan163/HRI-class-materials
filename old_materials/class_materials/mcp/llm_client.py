# llm_client.py

import asyncio
from llm_wrapper import MCPWrapper
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_llm_cli():
    server_params = StdioServerParameters(command="python", args=["server.py"])

    async with stdio_client(server_params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            wrapper = MCPWrapper(session)

            print("LLM CLI Started. Type 'exit' to quit.\n")
            while True:
                user_input = input("You: ")
                if user_input.lower() in ["exit", "quit"]:
                    break
                response = await wrapper.handle(user_input)
                print("Bot:", response)

if __name__ == "__main__":
    asyncio.run(run_llm_cli())
