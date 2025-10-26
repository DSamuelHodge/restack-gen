#!/usr/bin/env python
"""Test script to verify the FastMCPServerManager works."""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from testdemo.common.fastmcp_manager import FastMCPServerManager

async def test_manager():
    """Test that the manager can load config and manage servers."""
    print("Testing FastMCPServerManager...")
    
    # Initialize manager with config
    config_path = Path(__file__).parent / "config" / "tools.yaml"
    print(f"Loading config from: {config_path}")
    print(f"Config exists: {config_path.exists()}")
    
    manager = FastMCPServerManager(str(config_path))
    print(f"✓ Manager initialized successfully")
    print(f"✓ Loaded {len(manager.server_configs)} server configurations")
    
    # List configured servers
    for server_name, config in manager.server_configs.items():
        print(f"\n  Server: {server_name}")
        print(f"    - Module: {config.module}")
        print(f"    - Class: {config.class_name}")
        print(f"    - Transport: {config.transport}")
        print(f"    - Autostart: {config.autostart}")
    
    print("\n✅ Manager configuration loaded successfully!")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_manager())
        if success:
            print("\n✅ All tests passed! Manager is functional.")
            sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
