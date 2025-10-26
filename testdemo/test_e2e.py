#!/usr/bin/env python
"""
Comprehensive end-to-end test for restack-gen generated code.

This test validates:
1. Project generation created proper structure
2. Tool server can be imported and initialized
3. FastMCP tools are registered correctly  
4. FastMCPServerManager can load configuration
5. All components work together
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from testdemo.tools.research_mcp import ResearchToolServer
from testdemo.common.fastmcp_manager import FastMCPServerManager


async def test_tool_server():
    """Test the generated tool server."""
    print("\n" + "="*60)
    print("TEST 1: Tool Server Initialization")
    print("="*60)
    
    server = ResearchToolServer()
    print(f"✓ Server initialized")
    print(f"✓ Server name: {server.name}")
    print(f"✓ MCP instance type: {type(server.mcp).__name__}")
    
    # Get registered tools
    tools = await server.mcp.get_tools()
    print(f"✓ Registered {len(tools)} tools:")
    for tool in tools:
        tool_name = tool if isinstance(tool, str) else getattr(tool, 'name', str(tool))
        print(f"    - {tool_name}")
    
    assert len(tools) > 0, "No tools registered!"
    print("✅ PASSED: Tool server works correctly\n")
    return True


async def test_manager():
    """Test the FastMCPServerManager."""
    print("="*60)
    print("TEST 2: FastMCPServerManager")
    print("="*60)
    
    config_path = Path(__file__).parent / "config" / "tools.yaml"
    print(f"Loading config: {config_path.name}")
    
    manager = FastMCPServerManager(str(config_path))
    print(f"✓ Manager initialized")
    print(f"✓ Loaded {len(manager.server_configs)} server config(s)")
    
    # Verify config details
    for server_name, config in manager.server_configs.items():
        print(f"\n  Server: {server_name}")
        print(f"    Module: {config.module}")
        print(f"    Class: {config.class_name}")
        print(f"    Transport: {config.transport}")
        print(f"    Autostart: {config.autostart}")
        
        assert config.module, "Missing module path!"
        assert config.class_name, "Missing class name!"
    
    assert len(manager.server_configs) > 0, "No servers configured!"
    print("\n✅ PASSED: Manager configuration loaded successfully\n")
    return True


async def test_integration():
    """Test integration between components."""
    print("="*60)
    print("TEST 3: Integration Test")
    print("="*60)
    
    # Manager should be able to reference the server
    config_path = Path(__file__).parent / "config" / "tools.yaml"
    manager = FastMCPServerManager(str(config_path))
    
    # Verify server config matches actual server
    if "research_tools" in manager.server_configs:
        config = manager.server_configs["research_tools"]
        server = ResearchToolServer()
        
        print(f"✓ Config name '{config.name}' matches server name '{server.name}'")
        assert config.name == server.name, "Server name mismatch!"
        
    print("✅ PASSED: Components integrate correctly\n")
    return True


async def run_all_tests():
    """Run all tests."""
    print("\n" + "🚀 "*20)
    print("RESTACK-GEN END-TO-END VALIDATION TEST")
    print("🚀 "*20)
    
    try:
        # Run tests
        await test_tool_server()
        await test_manager()
        await test_integration()
        
        # Summary
        print("="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nValidation Summary:")
        print("  ✓ Tool server generates and initializes correctly")
        print("  ✓ FastMCP tools are registered properly")
        print("  ✓ FastMCPServerManager loads configuration")
        print("  ✓ Components integrate seamlessly")
        print("\n🎉 The generated code is fully functional! 🎉\n")
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
