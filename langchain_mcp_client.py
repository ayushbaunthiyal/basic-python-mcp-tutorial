import asyncio
import os

from dotenv import load_dotenv
from langchain_core.messages import ToolMessage, AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

load_dotenv()
model = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv('OPENAI_API_KEY'))

async def main():
    # This is the Langchain MCP adapater for MCP servers
    async with MultiServerMCPClient(
            {
                "arxiv_server": {
                    "transport": "stdio",
                    "command": "python",
                    "args": ["main.py"]  # Separate command and args
                }
            }
    ) as client:
        agent = create_react_agent(model, client.get_tools())
        arxiv_response = await agent.ainvoke({"messages": "I want to know about Neural Network architecture?"})
        messages = arxiv_response["messages"]

        for message in messages:
            if isinstance(message, AIMessage):
                print(message.content)

# now lets execute
asyncio.run(main())