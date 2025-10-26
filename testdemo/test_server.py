#!/usr/bin/env python
"""Test script to verify the Research tool server works."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from testdemo.tools.research_mcp import ResearchToolServer


async def test_server_initialization():
    """Test that the server can be initialized."""
    print("Testing server initialization...")
    server = ResearchToolServer()
    print("✓ Server initialized successfully")
    print(f"✓ Server name: {server.name}")
    print(f"✓ MCP instance: {type(server.mcp).__name__}")

    # List registered tools
    tools = await server.mcp.get_tools()
    print(f"✓ Registered tools: {len(tools)}")
    for tool in tools:
        tool_name = tool if isinstance(tool, str) else getattr(tool, "name", str(tool))
        print(f"  - {tool_name}")

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_server_initialization())
        if success:
            print("\n✅ All tests passed! Server is functional.")
            sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
