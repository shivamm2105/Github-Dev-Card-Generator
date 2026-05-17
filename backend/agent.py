import os
from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from dotenv import load_dotenv

load_dotenv()

from mcp import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_toolset import StdioConnectionParams

# Configure the MCP Toolset using stdio transport to the mcp_server.py
mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python",
            args=[os.path.join(os.path.dirname(__file__), "mcp_server.py")],
            env=dict(os.environ)
        ),
        timeout=60.0
    )
)

# Define the ADK Agent
github_card_agent = Agent(
    name="GitHubCardAgent",
    model="gemini-flash-latest",
    instruction="""You are a GitHub profile analyst and dev card generator. 
    When a user gives you a GitHub username, you ALWAYS follow this exact sequence: 
    1. Call scrape_github.
    2. Call analyze_profile with the result of scrape_github.
    3. Call generate_card_html with the username, scrape_github result, and analyze_profile result.
    4. Call save_card with the username and the generated HTML.
    
    Never skip steps. Be enthusiastic about developers' work. 
    If the profile is private or doesn't exist, say so clearly.""",
    tools=[mcp_toolset]
)
