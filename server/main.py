from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn
import os
import json
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Get environment variables
MILESTONE_API_TOKEN = os.getenv('MILESTONE_API_TOKEN')
MILESTONE_API_BASE_URL = os.getenv('MILESTONE_API_BASE_URL', 'https://t-midgard.milestoneinternet.com')

if not MILESTONE_API_TOKEN:
    raise ValueError("MILESTONE_API_TOKEN not found in environment variables")
if not MILESTONE_API_BASE_URL:
    raise ValueError("MILESTONE_API_BASE_URL not found in environment variables")

# Constants for API endpoints
MILESTONE_API_ENDPOINTS = {
    "find_profiles": "/api/v1.0/profile/findprofiles"
}
# Initialize FastMCP server for Weather tools (SSE)
mcp = FastMCP("weather")

# Constants for NWS (National Weather Service) API
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"


@mcp.tool()
async def search_arxiv(topic, max_results=5):
    """
    Search for arXiv papers related to a topic.

    Parameters:
        topic (str): The topic or keywords to search for.
        max_results (int): Number of results to retrieve.

    Returns:
        List of dictionaries with paper details (title, authors, summary, link).
    """
    base_url = "http://export.arxiv.org/api/query?"
    query = f"search_query=all:{topic}&start=0&max_results={max_results}"
    response = requests.get(base_url + query)

    if response.status_code != 200:
        raise Exception("Failed to fetch results from arXiv API.")

    root = ET.fromstring(response.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}

    papers = []
    for entry in root.findall('atom:entry', ns):
        title = entry.find('atom:title', ns).text.strip()
        summary = entry.find('atom:summary', ns).text.strip()
        link = entry.find('atom:id', ns).text.strip()
        authors = [author.find('atom:name', ns).text for author in entry.findall('atom:author', ns)]
        papers.append({
            'title': title,
            'authors': authors,
            'summary': summary,
            'link': link
        })

    return papers





async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling.
    
    This function handles the HTTP request to the NWS API, setting appropriate
    headers and handling potential errors during the request.
    
    Args:
        url: The complete URL for the NWS API endpoint
        
    Returns:
        A dictionary containing the JSON response if successful, None otherwise
    """
    # Set required headers for the NWS API
    headers = {
        "User-Agent": USER_AGENT,  # NWS API requires a user agent
        "Accept": "application/geo+json"  # Request GeoJSON format
    }
    # Create an async HTTP client
    async with httpx.AsyncClient() as client:
        try:
            # Make the GET request with timeout
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            return response.json()  # Parse and return JSON response
        except Exception:
            # Return None if any error occurs (connection, timeout, parsing, etc.)
            return None


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string.
    
    Extracts relevant information from a weather alert feature and formats it
    into a human-readable string.
    
    Args:
        feature: A dictionary containing a single weather alert feature
        
    Returns:
        A formatted string with key alert information
    """
    # Extract properties from the feature
    props = feature["properties"]
    # Format the alert with important details
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""


@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.
    
    Fetches active weather alerts from the NWS API for a specified US state.
    
    Args:
        state: Two-letter US state code (e.g. CA, NY)
        
    Returns:
        A formatted string containing all active alerts for the state,
        or a message indicating no alerts or an error
    """
    # Construct the URL for the state's active alerts
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    # Make the API request
    data = await make_nws_request(url)

    # Check if the response is valid
    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    # Check if there are any active alerts
    if not data["features"]:
        return "No active alerts for this state."

    # Format each alert and join them with separators
    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.
    
    Fetches the weather forecast from the NWS API for a specified location
    using latitude and longitude coordinates.
    
    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
        
    Returns:
        A formatted string containing the forecast for the next 5 periods,
        or an error message if the forecast couldn't be retrieved
    """
    # First get the forecast grid endpoint using the coordinates
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    # Check if we received valid point data
    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Extract the forecast URL from the points response
    # NWS API requires this two-step process to get the forecast
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    # Check if we received valid forecast data
    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Extract and format the forecast periods
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    # Join all forecast periods with separators
    return "\n---\n".join(forecasts)


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided MCP server with SSE.
    
    Sets up a Starlette web application with routes for SSE (Server-Sent Events)
    communication with the MCP server.
    
    Args:
        mcp_server: The MCP server instance to connect
        debug: Whether to enable debug mode for the Starlette app
        
    Returns:
        A configured Starlette application
    """
    # Create an SSE transport with a base path for messages
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        """Handler for SSE connections.
        
        Establishes an SSE connection and connects it to the MCP server.
        
        Args:
            request: The incoming HTTP request
        """
        # Connect the SSE transport to the request
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            # Run the MCP server with the SSE streams
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    # Create and return the Starlette application with routes
    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),  # Endpoint for SSE connections
            Mount("/messages/", app=sse.handle_post_message),  # Endpoint for posting messages
        ],
    )


@mcp.tool()
async def get_profile(profile_id: int) -> str:
    """Get profile information from Milestone API.
    
    Fetches profile data from the Milestone API for a specified profile ID.
    
    Args:
        profile_id: The ID of the profile to retrieve
        
    Returns:
        A formatted string containing the profile information,
        or an error message if the profile couldn't be retrieved
    """
    url = f"{MILESTONE_API_BASE_URL}{MILESTONE_API_ENDPOINTS['find_profiles']}"
    
    # Prepare the request payload
    payload = {
        "selectors": [
            {
                "profileId": profile_id
            }
        ],
        "showInactiveProfiles": True
    }
    
    # Set up headers with bearer token
    headers = {
        "Authorization": f"Bearer {MILESTONE_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Make the API request
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url, 
                json=payload,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Check if we got valid data
            if not data or not isinstance(data, dict):
                return "Invalid response from the API"
            
            # Format the response - adjust this based on the actual response structure
            return json.dumps(data, indent=2)
            
        except httpx.HTTPStatusError as e:
            return f"API request failed with status code: {e.response.status_code}"
        except Exception as e:
            return f"Failed to fetch profile: {str(e)}"


if __name__ == "__main__":
    # Get the underlying MCP server from the FastMCP instance
    mcp_server = mcp._mcp_server  # noqa: WPS437
    
    import argparse
    
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Run MCP server with configurable transport')
    # Allow choosing between stdio and SSE transport modes
    parser.add_argument('--transport', choices=['stdio', 'sse'], default='stdio', 
                        help='Transport mode (stdio or sse)')
    # Host configuration for SSE mode
    parser.add_argument('--host', default='0.0.0.0', 
                        help='Host to bind to (for SSE mode)')
    # Port configuration for SSE mode
    parser.add_argument('--port', type=int, default=8080, 
                        help='Port to listen on (for SSE mode)')
    args = parser.parse_args()

    # Launch the server with the selected transport mode
    if args.transport == 'stdio':
        # Run with stdio transport (default)
        # This mode communicates through standard input/output
        mcp.run(transport='stdio')
    else:
        # Run with SSE transport (web-based)
        # Create a Starlette app to serve the MCP server
        starlette_app = create_starlette_app(mcp_server, debug=True)
        # Start the web server with the configured host and port
        uvicorn.run(starlette_app, host=args.host, port=args.port)