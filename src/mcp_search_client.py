# from asyncio import tools
import asyncio
from mcp.client.stdio import stdio_client
from langchain_openai import ChatOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from utils.logger import create_logger
import os
import json

class MCPManager:
    def __init__(self):
        self.custom_session = None
        self.gh_session = None
        self.all_tools = {}
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0
        )
    
    def textcontent_to_string(self,content):
        if isinstance(content, list):
            return [self.textcontent_to_string(c) for c in content]

        if hasattr(content, "text"):
            return content.text

        return content


    async def startup(self):
        server_params = StdioServerParameters(
            command="python",
            args=["src/custom_mcp_server.py"],
        )

        github_params = StdioServerParameters(
            command="mcp-server-github",
            args=[],
            env={
                "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
            }
        )

        # Start stdio clients
        self.custom_client_ctx = stdio_client(server_params)
        self.github_client_ctx = stdio_client(github_params)

        custom_read, custom_write = await self.custom_client_ctx.__aenter__()
        gh_read, gh_write = await self.github_client_ctx.__aenter__()

        self.custom_session_ctx = ClientSession(custom_read, custom_write)
        self.gh_session_ctx = ClientSession(gh_read, gh_write)

        self.custom_session = await self.custom_session_ctx.__aenter__()
        self.gh_session = await self.gh_session_ctx.__aenter__()

        await self.custom_session.initialize()
        await self.gh_session.initialize()

        custom_tools = (await self.custom_session.list_tools()).tools
        gh_tools = (await self.gh_session.list_tools()).tools

        self.all_tools = {t.name: ("custom", t) for t in custom_tools}
        self.all_tools.update({t.name: ("github", t) for t in gh_tools})

        self.openai_tools = [
            self.convert_mcp_tool_to_openai_schema(t)
            for _, t in self.all_tools.values()
        ]

    async def shutdown(self):
        await self.custom_client_ctx.__aexit__(None, None, None)
        await self.github_client_ctx.__aexit__(None, None, None)

    def convert_mcp_tool_to_openai_schema(self, tool):
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        }

    async def mcp_search(self, query: str):

        response = await self.llm.ainvoke(
            query,
            tools=self.openai_tools,
            tool_choice="auto"
        )
        # If model wants to call tool
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            source, _ = self.all_tools[tool_name]

            try:
                if source == "custom":
                    tool_response = await asyncio.wait_for(
                        self.custom_session.call_tool(tool_name, tool_args),
                        timeout=15
                    )
                else:
                    tool_response = await asyncio.wait_for(
                        self.gh_session.call_tool(
                            tool_name,
                            {
                                "query": tool_args.get("query"),
                                "per_page": tool_args.get("max_results", 5),
                            }
                        ),
                        timeout=15
                    )

            except asyncio.TimeoutError:
                return f"Tool '{tool_name}' timed out after 15 seconds."

            except Exception as e:
                return f"Tool '{tool_name}' failed with error: {str(e)}"

            tool_output = self.textcontent_to_string(tool_response.content)

            # Normalize
            if isinstance(tool_output, list):
                tool_output = json.dumps(tool_output)

            tool_output = str(tool_output)

            # Hard safety cap
            MAX_TOOL_CHARS = 8000
            if len(tool_output) > MAX_TOOL_CHARS:
                tool_output = tool_output[:MAX_TOOL_CHARS] + "\n\n[TRUNCATED]"

            # Send tool result back to model
            final = await self.llm.ainvoke(
                [
                    {"role": "user", "content": query},
                    response,
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": str(tool_output),
                    },
                ]
            )

            return final.content

        return response.content