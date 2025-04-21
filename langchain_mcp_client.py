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
    # Get user input
    user_query = input("What would you like to know about? ")

    # This is the Langchain MCP adapater for MCP servers
    async with MultiServerMCPClient(
            {
                "arxiv_server": {
                    "transport": "stdio",
                    "command": "python",
                    "args": ["main.py"]
                }
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