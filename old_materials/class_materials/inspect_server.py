"""
Inspect what capabilities the MCP server exposes.
This shows all tools, resources, and prompts with their descriptions.
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def inspect_mcp_server():
    """Connect to server and list all capabilities"""
    server_params = StdioServerParameters(command="python", args=["server.py"])

    async with stdio_client(server_params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            
            print("=" * 60)
            print("MCP SERVER CAPABILITIES")
            print("=" * 60)
            
            # 1. List all tools
            print("\nTOOLS:")
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"\n  🔧 {tool.name}")
                print(f"     Description: {tool.description}")
                if hasattr(tool, 'inputSchema'):
                    print(f"     Parameters: {tool.inputSchema}")
            
            # 2. List all resources
            print("\nRESOURCES:")
            resources = await session.list_resources()
            for resource in resources.resources:
                print(f"\n  {resource.uri}")
                print(f"     Name: {resource.name}")
                if hasattr(resource, 'description') and resource.description:
                    print(f"     Description: {resource.description}")
            
            # 3. List all prompts
            print("\n PROMPTS:")
            prompts = await session.list_prompts()
            for prompt in prompts.prompts:
                print(f"\n  {prompt.name}")
                if hasattr(prompt, 'description') and prompt.description:
                    print(f"     Description: {prompt.description}")
                if hasattr(prompt, 'arguments'):
                    print(f"     Arguments: {prompt.arguments}")
            
            # 4. Get server info
            print("\nSERVER INFO:")
            capabilities = session.get_server_capabilities()
            print(f"  Server name: {capabilities}")
            
            print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(inspect_mcp_server())

