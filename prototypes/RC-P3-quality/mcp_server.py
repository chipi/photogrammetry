"""RC-P3: stdio MCP server exposing the three quality read tools from tools.py.

uv run python mcp_server.py        # speaks MCP on stdio; runs are read from RECCE_P3_RUNS
"""

import tools
from mcp.server.mcpserver import MCPServer

server = MCPServer(
    "recce-quality",
    instructions=(
        "Read-only quality state of photogrammetry reconstructions. Call get_summary first, "
        "then list_regions (weakest first), then get_region for the regions you want to explain. "
        "`run` is a run id such as 'kicker/full'."
    ),
)

server.tool()(tools.get_summary)
server.tool()(tools.list_regions)
server.tool()(tools.get_region)

if __name__ == "__main__":
    server.run("stdio")
