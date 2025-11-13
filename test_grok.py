#!/usr/bin/env python3
"""Test script for Grok API integration"""

import asyncio
import os
import aiohttp
from aiwebbot.bot import call_grok_api, SYSTEM_PROMPT, GROK_API_KEY

async def test_grok_api():
    """Test the Grok API integration"""
    if not GROK_API_KEY:
        print("❌ GROK_API_KEY environment variable not set")
        return

    print("🔑 Grok API Key found")
    print(f"📡 System Prompt: {SYSTEM_PROMPT}")

    test_posts = [
        "I just launched a new startup!",
        "Climate change is getting worse every day",
        "What's the meaning of life?",
        "AI will take over the world",
    ]

    async with aiohttp.ClientSession() as session:
        for i, post in enumerate(test_posts, 1):
            print(f"\n🧪 Test {i}: '{post}'")
            user_prompt = f"Generate a reply to this post: '{post}'"

            try:
                reply = await call_grok_api(
                    session=session,
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt
                )
                print(f"✅ Reply: '{reply}' (len: {len(reply)})")
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_grok_api())
