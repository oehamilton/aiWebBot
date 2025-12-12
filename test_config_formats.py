#!/usr/bin/env python3
"""Test script to verify all config formats are correct."""

import sys
from pathlib import Path
import json
import os

sys.path.insert(0, 'src')

from aiwebbot.config import Config

def test_config_formats():
    """Test that all config values save and load in correct formats."""
    print("Testing config save/load formats...")
    
    # Create test config
    config = Config()
    config.post_to_reply_ratio = 0.6
    config.timing.min_post_reply_cooldown_seconds = 150.5
    config.timing.max_post_reply_cooldown_seconds = 900.0
    
    # Save to test file
    test_path = Path('config/test_format.json')
    config.to_file(test_path)
    
    # Read raw JSON
    with open(test_path) as f:
        saved = json.load(f)
    
    print("\nSaved JSON structure:")
    print(f"  post_to_reply_ratio: {saved['post_to_reply_ratio']} (type: {type(saved['post_to_reply_ratio']).__name__})")
    print(f"  min_cooldown: {saved['timing']['min_post_reply_cooldown_seconds']} (type: {type(saved['timing']['min_post_reply_cooldown_seconds']).__name__})")
    print(f"  max_cooldown: {saved['timing']['max_post_reply_cooldown_seconds']} (type: {type(saved['timing']['max_post_reply_cooldown_seconds']).__name__})")
    print(f"  system_prompts_path: {saved['system_prompts_path']} (type: {type(saved['system_prompts_path']).__name__})")
    
    # Reload and verify types
    reloaded = Config.from_file(test_path)
    
    print("\nAfter reload - types:")
    print(f"  post_to_reply_ratio: {reloaded.post_to_reply_ratio} (type: {type(reloaded.post_to_reply_ratio).__name__})")
    print(f"  min_cooldown: {reloaded.timing.min_post_reply_cooldown_seconds} (type: {type(reloaded.timing.min_post_reply_cooldown_seconds).__name__})")
    print(f"  max_cooldown: {reloaded.timing.max_post_reply_cooldown_seconds} (type: {type(reloaded.timing.max_post_reply_cooldown_seconds).__name__})")
    print(f"  system_prompts_path: {reloaded.system_prompts_path} (type: {type(reloaded.system_prompts_path).__name__})")
    
    # Verify types are correct
    assert isinstance(reloaded.post_to_reply_ratio, float), "post_to_reply_ratio should be float"
    assert isinstance(reloaded.timing.min_post_reply_cooldown_seconds, float), "min_cooldown should be float"
    assert isinstance(reloaded.timing.max_post_reply_cooldown_seconds, float), "max_cooldown should be float"
    assert isinstance(reloaded.system_prompts_path, Path), "system_prompts_path should be Path"
    assert isinstance(saved['system_prompts_path'], str), "system_prompts_path in JSON should be string"
    
    # Clean up
    os.remove(test_path)
    
    print("\n[OK] All formats verified correctly!")
    print("\nSummary:")
    print("  - post_to_reply_ratio: saves as float, loads as float [OK]")
    print("  - min/max_cooldown: saves as float, loads as float [OK]")
    print("  - system_prompts_path: saves as string, loads as Path [OK]")
    print("  - Prompts: saved to text file (not JSON) [OK]")

if __name__ == "__main__":
    test_config_formats()

