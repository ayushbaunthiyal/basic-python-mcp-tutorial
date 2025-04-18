# basic-python-mcp-tutorial

got to 

https://docs.astral.sh/uv/getting-started/installation/#__tabbed_1_2

execute this first in windows powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

create virtual envi

python -m venv .venv

uv init .

add below code

# server.py
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Demo")


# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"
	
	
uv add "mcp[cli]"

Install claude desktop

uv run mcp install main.py