"""Quick test script to verify username filling on X.com login page."""

import asyncio
from playwright.async_api import async_playwright
import os

async def test_username_fill():
    """Test if username is properly filled and passed to X.com."""
    username = input("Enter your X.com username to test: ").strip()
    
    if not username:
        print("No username provided. Exiting.")
        return
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False, slow_mo=1000)
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    page = await context.new_page()
    
    try:
        print(f"\nNavigating to X.com login page...")
        await page.goto("https://x.com/login", wait_until="domcontentloaded")
        await asyncio.sleep(5)
        
        print("Waiting for page to load...")
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass
        
        # Find username input
        print("Looking for username input field...")
        username_input = None
        selectors = [
            'input[autocomplete="username"]',
            'input[name="text"]',
            'input[name="username"]',
            'input[type="text"]',
        ]
        
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() > 0 and await locator.is_visible():
                    username_input = locator
                    print(f"Found username input with selector: {selector}")
                    break
            except:
                continue
        
        if not username_input:
            print("ERROR: Could not find username input field!")
            await page.screenshot(path="test_error.png")
            print("Screenshot saved to test_error.png")
            return
        
        # Set username using JavaScript with full event triggering
        print(f"\nSetting username: '{username}'")
        escaped_username = username.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
        await username_input.evaluate(f"""
            (el) => {{
                const username = '{escaped_username}';
                el.focus();
                if (el.tagName === 'INPUT') {{
                    el.value = '';
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype,
                        'value'
                    ).set;
                    if (nativeInputValueSetter) {{
                        nativeInputValueSetter.call(el, username);
                    }} else {{
                        el.value = username;
                    }}
                }}
                const events = ['input', 'change', 'keyup', 'keydown', 'blur', 'focus'];
                events.forEach(eventType => {{
                    const event = new Event(eventType, {{ bubbles: true, cancelable: true }});
                    el.dispatchEvent(event);
                }});
            }}
        """)
        await asyncio.sleep(2)
        
        # Verify
        print("\nVerifying username was set...")
        try:
            input_value = await username_input.input_value()
            print(f"  input_value(): '{input_value}'")
        except:
            print("  Could not get input_value()")
        
        try:
            dom_value = await username_input.evaluate("el => el.tagName === 'INPUT' ? el.value : el.textContent")
            print(f"  DOM value: '{dom_value}'")
        except:
            print("  Could not get DOM value")
        
        # Check form data
        print("\nChecking form data...")
        form_data = await page.evaluate("""
            () => {
                const form = document.querySelector('form');
                if (form) {
                    const formData = new FormData(form);
                    const result = {};
                    for (let [key, value] of formData.entries()) {
                        result[key] = value;
                    }
                    return result;
                }
                return null;
            }
        """)
        if form_data:
            print(f"  Form data: {form_data}")
            username_in_form = any(username in str(v) for v in form_data.values())
            if username_in_form:
                print("  ✓ Username found in form data!")
            else:
                print("  ✗ Username NOT found in form data!")
        else:
            print("  No form found on page")
        
        print("\n" + "="*60)
        print("Test complete! Check the browser window.")
        print("The username should be visible in the input field.")
        print("Press Enter in the browser to proceed, or close this window.")
        print("="*60)
        
        # Keep browser open for manual inspection
        input("\nPress Enter to close the browser...")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(test_username_fill())

