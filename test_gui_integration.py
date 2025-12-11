#!/usr/bin/env python3
"""Test script for GUI integration and code changes."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from aiwebbot.config import Config
from aiwebbot.bot import AIWebBot, SYSTEM_PROMPT, POST_SYSTEM_PROMPT
from aiwebbot.prompts import PromptManager

def test_prompt_manager():
    """Test PromptManager with file parsing."""
    print("Testing PromptManager...")
    pm = PromptManager(Path('config/system_prompts.txt'))
    
    # Test file parsing
    general, reply, post = pm._read_prompts_from_file(Path('config/system_prompts.txt'))
    print(f"  Parsed prompts - General: {len(general)}, Reply: {len(reply)}, Post: {len(post)}")
    
    if post:
        print(f"  Post prompt preview: {post[0][:80]}...")
    
    # Test get_random_prompt
    reply_prompt = pm.get_random_prompt(SYSTEM_PROMPT, prompt_type="reply")
    post_prompt = pm.get_random_prompt(POST_SYSTEM_PROMPT, prompt_type="post")
    print(f"  Reply prompt fallback used: {reply_prompt == SYSTEM_PROMPT}")
    print(f"  Post prompt fallback used: {post_prompt == POST_SYSTEM_PROMPT}")
    print("  [OK] PromptManager test passed\n")

def test_bot_initialization():
    """Test bot initialization with tracking variables."""
    print("Testing Bot initialization...")
    config = Config()
    bot = AIWebBot(config)
    
    # Check tracking variables
    assert bot.total_new_posts == 0, "total_new_posts should start at 0"
    assert bot.total_replies == 0, "total_replies should start at 0"
    assert bot.last_new_post_text is None, "last_new_post_text should start as None"
    assert bot.last_reply_text is None, "last_reply_text should start as None"
    assert bot.gui_callback is None, "gui_callback should start as None"
    
    print("  [OK] All tracking variables initialized correctly")
    print("  [OK] Bot initialization test passed\n")

def test_cooldown_methods():
    """Test cooldown-related methods."""
    print("Testing cooldown methods...")
    config = Config()
    bot = AIWebBot(config)
    
    # Test can_post_or_reply when no post/reply has been made
    can_post, seconds = bot.can_post_or_reply()
    assert can_post == True, "Should be able to post when no previous post/reply"
    assert seconds == 0.0, "Seconds remaining should be 0 when can post"
    
    # Test get_random_cooldown
    cooldown = bot.get_random_cooldown()
    assert config.timing.min_post_reply_cooldown_seconds <= cooldown <= config.timing.max_post_reply_cooldown_seconds, \
        "Cooldown should be within min/max range"
    
    print(f"  Random cooldown: {cooldown}s (min: {config.timing.min_post_reply_cooldown_seconds}s, max: {config.timing.max_post_reply_cooldown_seconds}s)")
    print("  [OK] Cooldown methods test passed\n")

def test_gui_imports():
    """Test GUI module imports."""
    print("Testing GUI imports...")
    try:
        from aiwebbot.gui import BotGUI, run_gui
        print("  [OK] GUI module imports successfully")
        print("  [OK] GUI functions available")
        print("  [OK] GUI import test passed\n")
    except ImportError as e:
        print(f"  ✗ GUI import failed: {e}\n")
        raise

def test_config_access():
    """Test config access for GUI."""
    print("Testing config access...")
    config = Config()
    
    print(f"  Min cooldown: {config.timing.min_post_reply_cooldown_seconds}s")
    print(f"  Max cooldown: {config.timing.max_post_reply_cooldown_seconds}s")
    print(f"  Prompts path: {config.system_prompts_path}")
    print("  [OK] Config access test passed\n")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing GUI Integration and Code Changes")
    print("=" * 60 + "\n")
    
    try:
        test_prompt_manager()
        test_bot_initialization()
        test_cooldown_methods()
        test_gui_imports()
        test_config_access()
        
        print("=" * 60)
        print("All tests passed! [OK]")
        print("=" * 60)
        print("\nTo test the GUI, run:")
        print("  python -m aiwebbot.main --gui")
        
    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

