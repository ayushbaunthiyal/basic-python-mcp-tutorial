import asyncio
import os

from dotenv import load_dotenv
from langchain_core.messages import ToolMessage, AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from pathlib import Path

load_dotenv()
model = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv('OPENAI_API_KEY'))

async def main():
     # Get the project root directory and server path
    project_root = Path(__file__).parent.parent
    server_script = project_root / "server" / "main.py"

    # Get user input
    user_query = input("What would you like to know about? ")

    # This is the Langchain MCP adapater for MCP servers
    async with MultiServerMCPClient(
            {
               "arxiv_server": {
                    # you need run the server.py to have the mcp server run on 8000
                    "url": "http://127.0.0.1:8080/sse",
                    "transport": "sse",
                }
                # "arxiv_server": {
                #     "transport": "stdio",
                #     "command": "python",
                #     "args": [str(server_script)]  # Use the full path to main.py
                # }
            }
    ) as client:
        agent = create_react_agent(model, client.get_tools())
        arxiv_response = await agent.ainvoke({"messages": user_query})
        messages = arxiv_response["messages"]

        for message in messages:
            if isinstance(message, AIMessage):
                print(message.content)

        # Optional: Add continuous conversation
        while True:
            follow_up = input("\nAsk another question (or 'quit' to exit): ")
            if follow_up.lower() in ['quit', 'exit', 'q']:
                break
            
            arxiv_response = await agent.ainvoke({"messages": follow_up})
            messages = arxiv_response["messages"]
            
            for message in messages:
                if isinstance(message, AIMessage):
                    print(message.content)

if __name__ == "__main__":
    asyncio.run(main())