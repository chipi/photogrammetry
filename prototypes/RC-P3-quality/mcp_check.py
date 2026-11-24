"""Start mcp_server.py over stdio with the MCP SDK's client, list its tools, call each once.
No LLM involved.

    uv run python mcp_check.py kicker/heldout
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).with_name("mcp_server.py")


async def main(run: str):
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        names = [t.name for t in (await session.list_tools()).tools]
        print("tools:", names)
        calls = [
            ("get_summary", {"run": run}),
            ("list_regions", {"run": run, "limit": 3}),
        ]
        first = None
        for name, args in calls:
            res = await session.call_tool(name, args)
            doc = json.loads(res.content[0].text)
            print(name, "isError:", res.is_error, "->", json.dumps(doc)[:160])
            if name == "list_regions":
                first = doc["regions"][0]["id"]
        res = await session.call_tool("get_region", {"run": run, "region_id": first})
        print("get_region", first, "isError:", res.is_error, "->", res.content[0].text[:160])
        if set(names) != {"get_summary", "list_regions", "get_region"}:
            raise SystemExit(f"unexpected tools {names}")
        if res.is_error:
            raise SystemExit("get_region failed")


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "kicker/heldout"))
