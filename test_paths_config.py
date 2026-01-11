"""
Test script for paths_config module
This script tests the paths configuration without requiring full ComfyUI startup
"""

import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Mock config and folder_paths before importing
class MockConfig:
    extension_uri = os.path.dirname(__file__)
    output_uri = None
    workflows_uri = None
    prompts_uri = None
    thumbnail_cache_uri = None
    ffmpeg_path = "ffmpeg"

    class PromptServer:
        class Instance:
            routes = None
        instance = Instance()

    serverInstance = PromptServer.instance
    routes = None

class MockFolderPaths:
    @staticmethod
    def get_output_directory():
        # Return a mock output directory
        comfyui_base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(comfyui_base, "output")

# Mock the modules
sys.modules['server'] = type(sys)('server')
sys.modules['server'].PromptServer = MockConfig.PromptServer
sys.modules['folder_paths'] = MockFolderPaths

# Now we can import our module
from py import config as real_config
from py import paths_config

# Copy mock values
real_config.extension_uri = MockConfig.extension_uri

print("=" * 60)
print("Testing paths_config module")
print("=" * 60)

# Test 1: Get default paths
print("\n[Test 1] Getting default paths...")
try:
    defaults = paths_config.get_default_paths()
    print("✓ Success!")
    for key, value in defaults.items():
        print(f"  {key}: {value}")
except Exception as e:
    print(f"✗ Failed: {e}")

# Test 2: Validate a valid path
print("\n[Test 2] Validating extension directory (should exist)...")
try:
    validation = paths_config.validate_path(real_config.extension_uri, should_exist=False)
    print(f"✓ Success!")
    print(f"  Valid: {validation.get('valid')}")
    print(f"  Exists: {validation.get('exists')}")
except Exception as e:
    print(f"✗ Failed: {e}")

# Test 3: Validate an invalid path (empty)
print("\n[Test 3] Validating empty path (should fail)...")
try:
    validation = paths_config.validate_path("", should_exist=False)
    if not validation.get('valid'):
        print(f"✓ Success! Correctly rejected empty path")
        print(f"  Error: {validation.get('error')}")
    else:
        print(f"✗ Failed: Should have rejected empty path")
except Exception as e:
    print(f"✗ Failed with exception: {e}")

# Test 4: Validate a relative path (should fail)
print("\n[Test 4] Validating relative path (should fail)...")
try:
    validation = paths_config.validate_path("./cache", should_exist=False)
    if not validation.get('valid'):
        print(f"✓ Success! Correctly rejected relative path")
        print(f"  Error: {validation.get('error')}")
    else:
        print(f"✗ Failed: Should have rejected relative path")
except Exception as e:
    print(f"✗ Failed with exception: {e}")

# Test 5: Load config (should return defaults if no config file exists)
print("\n[Test 5] Loading paths config...")
try:
    paths = paths_config.load_paths_config()
    print("✓ Success!")
    for key, value in paths.items():
        print(f"  {key}: {value}")
except Exception as e:
    print(f"✗ Failed: {e}")

# Test 6: Save config
print("\n[Test 6] Saving test configuration...")
test_config_path = os.path.join(real_config.extension_uri, "test_paths_config.json")
try:
    test_paths = paths_config.get_default_paths()
    test_paths['thumbnail_cache'] = os.path.join(real_config.extension_uri, "test_cache")

    # Temporarily change config file for testing
    original_config_file = paths_config.CONFIG_FILE
    paths_config.CONFIG_FILE = "test_paths_config.json"

    success = paths_config.save_paths_config(test_paths)
    if success and os.path.exists(test_config_path):
        print("✓ Success! Config file created")
        with open(test_config_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        print(f"  Saved data:")
        print(json.dumps(saved_data, indent=4))

        # Cleanup
        os.remove(test_config_path)
        print("  Test file cleaned up")
    else:
        print("✗ Failed: Could not save config")

    # Restore original config file name
    paths_config.CONFIG_FILE = original_config_file
except Exception as e:
    print(f"✗ Failed: {e}")
    # Restore and cleanup
    paths_config.CONFIG_FILE = original_config_file
    if os.path.exists(test_config_path):
        os.remove(test_config_path)

# Test 7: Get all paths with status
print("\n[Test 7] Getting all paths with status...")
try:
    all_paths = paths_config.get_all_paths()
    print("✓ Success!")
    for path_type, info in all_paths.items():
        print(f"\n  {path_type}:")
        print(f"    Current: {info['current']}")
        print(f"    Default: {info['default']}")
        print(f"    Is default: {info['is_default']}")
        print(f"    Exists: {info['exists']}")
        print(f"    Valid: {info['valid']}")
except Exception as e:
    print(f"✗ Failed: {e}")

# Test 8: Set and get individual path
print("\n[Test 8] Setting and getting individual path...")
try:
    original_config_file = paths_config.CONFIG_FILE
    paths_config.CONFIG_FILE = "test_paths_config.json"

    test_path = os.path.join(real_config.extension_uri, "my_custom_cache")

    # Set path
    success = paths_config.set_path('thumbnail_cache', test_path)
    if success:
        # Get path back
        retrieved_path = paths_config.get_path('thumbnail_cache')
        if retrieved_path == test_path:
            print("✓ Success! Path set and retrieved correctly")
            print(f"  Set path: {test_path}")
            print(f"  Retrieved: {retrieved_path}")
        else:
            print(f"✗ Failed: Retrieved path doesn't match")
            print(f"  Expected: {test_path}")
            print(f"  Got: {retrieved_path}")
    else:
        print("✗ Failed: Could not set path")

    # Cleanup
    if os.path.exists(test_config_path):
        os.remove(test_config_path)
    paths_config.CONFIG_FILE = original_config_file
except Exception as e:
    print(f"✗ Failed: {e}")
    paths_config.CONFIG_FILE = original_config_file
    if os.path.exists(test_config_path):
        os.remove(test_config_path)

print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)
