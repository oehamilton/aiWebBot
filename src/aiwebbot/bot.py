"""Main AI Web Bot implementation."""

import asyncio
import os
import random
import re
import time
from dataclasses import dataclass
from typing import Optional

import aiohttp
from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from .config import Config
from .prompts import PromptManager

# Grok API Configuration
GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_API_ENDPOINT = "https://api.x.ai/v1/chat/completions"

# System prompt for generating replies
#SYSTEM_PROMPT = "You are an AI assistant focused on advancing humanity toward a Type 1 civilization on the Kardashev scale. Generate concise, insightful replies (128 characters or less) that promote scientific progress, technological advancement, critical thinking, profit focused on early stage investing in energy, robotics, AI, or positive societal mind set change. Replies should be thought-provoking and actionable."
# SYSTEM_PROMPT = "You are an AI assistant focused on advancing humanity toward a Type 1 civilization on the Kardashev scale. Generate concise, insightful replies (128 characters or less) that promote scientific progress, technological advancement, critical thinking, and profit through early-stage investing in energy, robotics, AI, or positive societal change. Replies must be thought-provoking, actionable, and responsive to the post's sentiment: offer condolences for death or injury; provide reassurances for AI fears, relating to the post and emphasizing AI's benefits to humanity. Always suggest solutions propelling humanity forward, incorporating changes to people, processes, and technology. For mindset shifts, include thought-provoking, actionable suggestions. Replies may be questions or as short as 2-3 words, but never exceed 128 characters."
SYSTEM_PROMPT = "You are a highly intelligent man with vast knowledge and experience in business, investing, and technology. You have advanced degrees in engineering, theoritical physics, chemistry and computer science. You care about the well being of humanity. You are focused on advancing humanity toward a Type 1 civilization on the Kardashev scale. Generate concise, insightful replies (128 characters or less) that promote scientific progress, technological advancement, critical thinking, energy, robotics, AI, or positive societal mind set change. Replies should be thought-provoking, actionable, a little technical and relevant to the post."

# System prompt for generating new posts
#POST_SYSTEM_PROMPT = "You are a highly intelligent and whitty man with vast knowledge and experience in business, investing, and technology. You have advanced degrees in engineering, theoretical physics, chemistry and computer science. You care about the well being of humanity. You are focused on advancing humanity toward a Type 1 civilization on the Kardashev scale. Generate unique, engaging posts (280 characters or less) that promote scientific progress, technological advancement, critical thinking, profit focused on early stage investing in energy, robotics, AI, or positive societal mindset change. Posts should be thought-provoking, actionable, a little technical, and original. Create standalone content that doesn't require context from other posts."
POST_SYSTEM_PROMPT = "You are a staunch, unapologetically right-wing, heterosexual Christian male patriot in his 40s–50s. Your core values and posting order of priority are always: God first, then Country, then Family. You are bold, assertive, masculine, and optimistic in tone. You speak plain truths confidently and directly, without sugarcoating, hedging, or fear of offending. You never apologize for your beliefs. You refuse performative neutrality or people-pleasing. Keep every post short, punchy, and under 200 characters (ideally 100–150 for maximum impact). Use strong, declarative language. Hashtags only when they add punch (#MAGA, #AmericaFirst, #2A, #ProLife, etc.). End many posts with rhetorical questions, calls to action, or emphatic statements when it fits."

def clean_generated_text(text: str) -> str:
    """Remove character count annotations from generated text."""
    # Remove patterns like "(87 chars)", "(87 characters)", "(87 char)", etc.
    # Matches parentheses with numbers followed by "char" or "chars" or "characters"
    text = re.sub(r'\s*\(\d+\s*(?:char|chars|character|characters)\)\s*$', '', text, flags=re.IGNORECASE)
    # Also remove patterns without parentheses like "87 chars", "87 characters" at the end
    text = re.sub(r'\s+\d+\s*(?:char|chars|character|characters)\s*$', '', text, flags=re.IGNORECASE)
    return text.strip()


async def call_grok_api(session, system_prompt, user_prompt, model="grok-4-1-fast-reasoning", max_tokens=50, retries=3):
    """Async call to Grok API with retry and debug. Falls back to grok-2 if grok-4-1-fast-reasoning fails."""
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }

    # Model fallback list: try latest first, then fall back to older versions
    model_fallbacks = [model, "grok-beta", "grok-2", "grok-3"] if model not in ["grok-beta", "grok-2", "grok-3"] else [model]
    
    for model_to_try in model_fallbacks:
        data = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "model": model_to_try,
            "max_tokens": max_tokens,
            "temperature": 0.80,  # Slightly higher for creativity while maintaining relevance
            "stream": False
        }

        model_not_found = False
        for attempt in range(retries):
            try:
                logger.debug(f"Grok API call attempt {attempt + 1}/{retries} with model '{model_to_try}'")
                async with session.post(GROK_API_ENDPOINT, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        reply = result["choices"][0]["message"]["content"].strip()
                        # Remove character count annotations
                        reply = clean_generated_text(reply)
                        ai_hyphen = '—'
                        reply = reply.replace(ai_hyphen, ", ")
                        reply = reply + " "
                        # Ensure reply is 500 characters or less
                        if len(reply) > 500:
                            reply = reply[:497] + "..."

                        logger.info(f"Grok generated reply using model '{model_to_try}': '{reply}' (len: {len(reply)})")
                        return reply
                    else:
                        error_text = await response.text()
                        logger.warning(f"Grok API error {response.status} with model '{model_to_try}': {error_text}")
                        
                        # If model doesn't exist (404), try next fallback immediately
                        if response.status == 404 and model_to_try != model_fallbacks[-1]:
                            logger.info(f"Model '{model_to_try}' not available, trying fallback...")
                            model_not_found = True
                            break  # Break out of retry loop to try next model

            except Exception as e:
                logger.warning(f"Grok API call failed (attempt {attempt + 1} with model '{model_to_try}'): {e}")

            if attempt < retries - 1 and not model_not_found:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # If model was not found (404), continue to next fallback
        if model_not_found:
            continue

    logger.error(f"Grok API call failed after trying all models: {model_fallbacks}")
    return "Why?"  # Fallback to default reply


@dataclass
class PostData:
    """Data structure for a Twitter post."""

    text: str
    author: str
    post_id: str
    timestamp: Optional[str] = None


class AIWebBot:
    """Main AI Web Bot class for automated X/Twitter interactions."""

    def __init__(self, config: Config):
        """Initialize the bot with configuration."""
        self.config = config
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.running = False
        self.processed_post_ids = set()  # Track processed posts to avoid duplicates
        self.current_post_index = 0  # Track which post we're currently processing
        self.http_session: Optional[aiohttp.ClientSession] = None  # For Grok API calls
        self.recent_replies = []  # Track recent replies to avoid replying to our own posts
        self.prompt_manager = PromptManager(
            file_path=self.config.system_prompts_path,
            reload_interval_seconds=self.config.prompts_reload_interval_seconds,
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def start(self) -> None:
        """Start the browser and initialize the bot."""
        logger.info("Starting AI Web Bot...")

        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=self.config.browser.headless,
            slow_mo=self.config.browser.slow_mo,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
            ]
        )

        # Create a regular browser context with user agent to appear more legitimate
        self.context = await self.browser.new_context(
            viewport={
                "width": self.config.browser.viewport_width,
                "height": self.config.browser.viewport_height,
            },
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        self.page = await self.context.new_page()

        # Initialize HTTP session for Grok API calls
        self.http_session = aiohttp.ClientSession()

        # Load system prompts and start periodic reload
        await self.prompt_manager.start()

        logger.info("Browser and HTTP session started successfully")

    async def stop(self) -> None:
        """Stop the browser and cleanup resources."""
        logger.info("Stopping AI Web Bot...")

        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.http_session:
            await self.http_session.close()

        # Stop prompt manager
        await self.prompt_manager.stop()

        if self.playwright:
            await self.playwright.stop()

        self.running = False
        logger.info("AI Web Bot stopped")

    async def refresh_feed(self, reason: str = "") -> None:
        """Refresh the feed to load new posts."""
        if not self.page:
            logger.error("Cannot refresh feed: page not initialized")
            return

        message = "Refreshing feed"
        if reason:
            message += f" ({reason})"
        logger.info(message)

        try:
            await self.page.reload()
            await asyncio.sleep(3)
            self.current_post_index = 0
        except Exception as e:
            logger.warning(f"Failed to refresh feed: {e}")

    async def navigate_to_twitter(self) -> bool:
        """Navigate to X/Twitter home page."""
        if not self.page:
            logger.error("Browser page not initialized")
            return False

        try:
            logger.info(f"Navigating to {self.config.twitter.home_url}")
            await self.page.goto(
                self.config.twitter.home_url,
                timeout=self.config.timing.page_load_timeout * 1000,
                wait_until="domcontentloaded"
            )

            # Wait for page to load more robustly
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(3)  # Additional wait for dynamic content

            logger.info("Successfully navigated to X/Twitter")
            return True

        except Exception as e:
            logger.error(f"Failed to navigate to X/Twitter: {e}")
            return False

    async def _check_for_login_errors(self) -> bool:
        """Check for error messages on the login page indicating rate limiting or blocks."""
        try:
            # Check for error messages in various locations
            error_selectors = [
                '[role="alert"]',
                '.error',
                '[data-testid*="error"]',
                '[data-testid*="Error"]',
                '[class*="error"]',
                '[class*="Error"]',
                'div[dir="ltr"]',  # X.com often shows errors in divs with dir="ltr"
            ]
            
            all_error_texts = []
            for selector in error_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for element in elements:
                        if await element.is_visible():
                            text = await element.inner_text()
                            if text and text.strip():
                                all_error_texts.append(text.strip())
                except:
                    continue
            
            # Also check page content directly for error messages
            try:
                page_text = await self.page.evaluate("() => document.body.innerText")
                all_error_texts.append(page_text)
            except:
                pass
            
            if all_error_texts:
                error_text_combined = " ".join(all_error_texts).lower()
                logger.debug(f"Checking page content for errors. Found text: {error_text_combined[:200]}...")
                
                # Check for rate limiting or temporary block messages (expanded list)
                rate_limit_messages = [
                    "could not log you in now",
                    "please try again later",
                    "rate limit",
                    "temporary block",
                    "too many attempts",
                    "something went wrong",
                    "try again later",
                    "unusual activity",
                    "suspicious activity",
                    "verify your account",
                    "temporarily locked",
                    "account locked"
                ]
                
                for msg in rate_limit_messages:
                    if msg in error_text_combined:
                        logger.error(f"Detected login error from X/Twitter: '{msg}'")
                        logger.error("X/Twitter is blocking automated login attempts.")
                        logger.error("This is likely due to:")
                        logger.error("  1. Rate limiting from too many login attempts")
                        logger.error("  2. Anti-bot detection systems")
                        logger.error("  3. Suspicious activity detection")
                        logger.warning("Falling back to manual login mode. Please log in manually in the browser window.")
                        return True  # Error detected
            
            # Check for specific error patterns in the page HTML
            try:
                page_html = await self.page.content()
                if "could not log you in" in page_html.lower() or "try again later" in page_html.lower():
                    logger.error("Detected login error message in page HTML")
                    logger.warning("Falling back to manual login mode due to X/Twitter blocking")
                    return True
            except:
                pass
                
        except Exception as e:
            logger.debug(f"Error checking for login errors: {e}")
        
        return False  # No errors detected

    async def login_to_twitter(self) -> bool:
        """Automatically log in to X/Twitter using provided credentials."""
        if not self.page:
            logger.error("Browser page not initialized for login")
            return False
        
        # Log config values for debugging (without exposing password)
        logger.info(f"Login attempt - Username configured: {bool(self.config.twitter_username)}, Password configured: {bool(self.config.twitter_password)}")
        
        # Validate username is present and not empty/whitespace
        if not self.config.twitter_username or not self.config.twitter_username.strip():
            logger.error("Username is not set or is empty in configuration.")
            logger.error("Please check your JSON config file and ensure 'twitter_username' field has a valid value (not null or empty string).")
            logger.error("Example: \"twitter_username\": \"your_username\"")
            return False
        
        username = self.config.twitter_username.strip()
        logger.info(f"Username value: '{username}' (length: {len(username)})")
        
        # Validate password is present and not empty/whitespace
        if not self.config.twitter_password or not self.config.twitter_password.strip():
            logger.error("Password is not set or is empty in configuration.")
            logger.error("Please check your JSON config file and ensure 'twitter_password' field has a valid value (not null or empty string).")
            return False
        
        logger.info("Password configured (hidden)")

        try:
            logger.info("Attempting automatic login to X/Twitter...")

            # Navigate directly to login page first
            login_url = "https://x.com/login"
            logger.info(f"Navigating to login page: {login_url}")
            await self.page.goto(login_url, wait_until="domcontentloaded")
            await asyncio.sleep(5)  # Wait longer for page to fully load

            # Wait for page to be interactive
            try:
                await self.page.wait_for_load_state("networkidle", timeout=10000)
            except:
                logger.debug("Network idle timeout, continuing anyway...")
            
            # Check for errors immediately after page load (X.com might show errors right away)
            if await self._check_for_login_errors():
                logger.error("Login page shows error message immediately after loading")
                return False

            # Debug: Log what input fields are actually on the page
            try:
                all_inputs = await self.page.evaluate("""
                    () => {
                        const inputs = Array.from(document.querySelectorAll('input, [contenteditable="true"], [role="textbox"]'));
                        return inputs.map(input => ({
                            tag: input.tagName,
                            type: input.type || 'N/A',
                            name: input.name || 'N/A',
                            id: input.id || 'N/A',
                            placeholder: input.placeholder || 'N/A',
                            autocomplete: input.autocomplete || 'N/A',
                            testid: input.getAttribute('data-testid') || 'N/A',
                            role: input.getAttribute('role') || 'N/A',
                            visible: input.offsetWidth > 0 && input.offsetHeight > 0
                        })).filter(input => input.visible);
                    }
                """)
                logger.info(f"Found {len(all_inputs)} visible input fields on login page:")
                for inp in all_inputs[:5]:  # Log first 5
                    logger.info(f"  - {inp}")
            except Exception as e:
                logger.debug(f"Could not inspect page inputs: {e}")

            # Try multiple selector patterns for username input (expanded list)
            username_selectors = [
                'input[autocomplete="username"]',
                'input[name="text"]',  # X.com uses name="text" for username
                'input[name="username"]',
                'input[type="text"]',
                '[data-testid="ocfEnterTextTextInput"]',  # X.com OCF (One Click Flow) input
                '[data-testid="login-username"]',
                'input[placeholder*="phone"]',
                'input[placeholder*="email"]',
                'input[placeholder*="username"]',
                '[role="textbox"][contenteditable="true"]',
                '[role="textbox"]',
                'input:not([type="password"]):not([type="hidden"])'  # Any visible text input
            ]

            username_input = None
            used_selector = None
            for selector in username_selectors:
                try:
                    locator = self.page.locator(selector).first
                    # Check if element exists and is visible
                    count = await locator.count()
                    if count > 0:
                        is_visible = await locator.is_visible()
                        if is_visible:
                            await locator.wait_for(state="visible", timeout=3000)
                            username_input = locator
                            used_selector = selector
                            logger.info(f"Found username input with selector: {selector}")
                            break
                except Exception as e:
                    logger.debug(f"Selector '{selector}' failed: {e}")
                    continue

            if not username_input:
                logger.error("Username input field not found with any selector")
                # Take a screenshot for debugging
                try:
                    await self.page.screenshot(path="debug_login_page.png")
                    logger.info("Saved debug screenshot: debug_login_page.png")
                except:
                    pass
                return False

            # Focus and clear any existing text first
            try:
                await username_input.click()
                await asyncio.sleep(0.5)
                # Try multiple methods to clear
                try:
                    await username_input.press("Control+a")
                    await username_input.press("Backspace")
                except:
                    # If that doesn't work, try select all and delete
                    await username_input.evaluate("el => { el.select(); el.value = ''; }")
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.debug(f"Could not clear username field first: {e}")

            # Try multiple methods to fill username with proper event triggering
            logger.info(f"Attempting to fill username field with: '{username}'")
            fill_success = False
            
            # Method 1: Use JavaScript to set value and trigger all necessary events
            # This ensures X.com's JavaScript recognizes the value
            try:
                logger.info("Setting username via JavaScript with full event triggering...")
                # Escape username for JavaScript
                escaped_username = username.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
                await username_input.evaluate(f"""
                    (el) => {{
                        const username = '{escaped_username}';
                        
                        // Focus the element first
                        el.focus();
                        
                        // Clear any existing value
                        if (el.tagName === 'INPUT') {{
                            el.value = '';
                        }} else {{
                            el.textContent = '';
                            el.innerText = '';
                        }}
                        
                        // Set the username value using multiple methods to ensure it sticks
                        if (el.tagName === 'INPUT') {{
                            // Method 1: Direct value assignment
                            el.value = username;
                            
                            // Method 2: Use native setter to bypass React/other frameworks
                            try {{
                                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                                    window.HTMLInputElement.prototype,
                                    'value'
                                ).set;
                                if (nativeInputValueSetter) {{
                                    nativeInputValueSetter.call(el, username);
                                }}
                            }} catch (e) {{
                                // Fallback if native setter not available
                            }}
                            
                            // Method 3: Set value property directly
                            try {{
                                Object.defineProperty(el, 'value', {{
                                    value: username,
                                    writable: true,
                                    configurable: true
                                }});
                            }} catch (e) {{
                                // Ignore if can't set property
                            }}
                        }} else {{
                            el.textContent = username;
                            el.innerText = username;
                        }}
                        
                        // Trigger all possible events that X.com might be listening to
                        const events = ['input', 'change', 'keyup', 'keydown', 'blur', 'focus'];
                        events.forEach(eventType => {{
                            const event = new Event(eventType, {{ bubbles: true, cancelable: true }});
                            el.dispatchEvent(event);
                        }});
                        
                        // Also try InputEvent for modern browsers
                        try {{
                            const inputEvent = new InputEvent('input', {{
                                bubbles: true,
                                cancelable: true,
                                inputType: 'insertText',
                                data: username
                            }});
                            el.dispatchEvent(inputEvent);
                        }} catch (e) {{
                            // InputEvent might not be available
                        }}
                        
                        // Trigger one more input event after a tiny delay to ensure React picks it up
                        setTimeout(() => {{
                            const event = new Event('input', {{ bubbles: true }});
                            el.dispatchEvent(event);
                        }}, 10);
                    }}
                """)
                await asyncio.sleep(1)  # Wait for X.com's JS to process
                
                # Verify the value is actually set in the DOM
                try:
                    entered_value = await username_input.input_value()
                    logger.info(f"Username set via JS - input_value(): '{entered_value}'")
                    if entered_value == username or username in entered_value:
                        fill_success = True
                except:
                    pass
                
                # Also check via evaluate to see actual DOM value
                try:
                    dom_value = await username_input.evaluate("el => el.tagName === 'INPUT' ? el.value : el.textContent")
                    logger.info(f"Username set via JS - DOM value: '{dom_value}'")
                    if dom_value == username or username in dom_value:
                        fill_success = True
                except:
                    pass
                    
            except Exception as e:
                logger.debug(f"JavaScript method failed: {e}")
            
            # Method 2: Use fill() method if JS didn't work
            if not fill_success:
                try:
                    logger.info("Trying fill() method...")
                    await username_input.fill(username)
                    await asyncio.sleep(0.5)
                    # Trigger events after fill
                    await username_input.evaluate("""
                        (el) => {
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    """)
                    await asyncio.sleep(0.5)
                    # Verify
                    try:
                        entered_value = await username_input.input_value()
                        if entered_value == username or username in entered_value:
                            logger.info(f"Username filled successfully using fill() method: '{entered_value}'")
                            fill_success = True
                    except:
                        pass
                except Exception as e:
                    logger.debug(f"fill() method failed: {e}")
            
            # Method 3: Use type() if other methods didn't work
            if not fill_success:
                try:
                    logger.info("Trying type() method as fallback...")
                    await username_input.click()
                    await asyncio.sleep(0.3)
                    await username_input.press("Control+a")
                    await asyncio.sleep(0.2)
                    await username_input.type(username, delay=30)
                    await asyncio.sleep(0.5)
                    # Verify
                    try:
                        entered_value = await username_input.input_value()
                        if entered_value == username or username in entered_value:
                            logger.info(f"Username typed successfully: '{entered_value}'")
                            fill_success = True
                    except:
                        pass
                except Exception as e:
                    logger.debug(f"type() method failed: {e}")
            
            if not fill_success:
                logger.error(f"Failed to enter username using all methods. Username: '{username}'")
                # Final verification attempt
                try:
                    final_value = await username_input.input_value()
                    logger.error(f"Final field value (input_value): '{final_value}'")
                except:
                    try:
                        final_value = await username_input.evaluate("el => el.tagName === 'INPUT' ? el.value : el.textContent")
                        logger.error(f"Final field value (DOM): '{final_value}'")
                    except:
                        logger.error("Could not read final field value")
                return False
            
            # Final verification: Check that the value is actually in the DOM and form
            try:
                # Wait a bit for X.com's JavaScript to process
                await asyncio.sleep(1)
                
                # Get the actual DOM value
                actual_dom_value = await username_input.evaluate("el => el.tagName === 'INPUT' ? el.value : el.textContent")
                logger.info(f"Final verification - Username in DOM: '{actual_dom_value}'")
                
                if actual_dom_value != username and username not in actual_dom_value:
                    logger.warning(f"Username mismatch! Expected: '{username}', Got in DOM: '{actual_dom_value}'")
                    # Try one more time with direct DOM manipulation
                    # Escape username before using in f-string (can't use backslash in f-string expression)
                    escaped_username_final = username.replace("'", "\\'").replace("\\", "\\\\")
                    await username_input.evaluate(f"""
                        (el) => {{
                            if (el.tagName === 'INPUT') {{
                                el.value = '{escaped_username_final}';
                                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                        }}
                    """)
                    await asyncio.sleep(1)
            except Exception as e:
                logger.debug(f"Final verification failed: {e}")
            
            await asyncio.sleep(2)

            # Check for errors before proceeding (X.com might show errors immediately)
            if await self._check_for_login_errors():
                return False

            # Try multiple patterns for next/submit button
            next_selectors = [
                '[data-testid="login-button"]',
                '[role="button"]:has-text("Next")',
                '[role="button"]:has-text("Submit")',
                'button[type="submit"]',
                '[data-testid*="button"]:has-text("Next")',
                '[data-testid*="button"]:has-text("Submit")'
            ]

            # Verify username is in the form before clicking Next
            try:
                # Check the actual form data to ensure username will be submitted
                form_data = await self.page.evaluate("""
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
                    logger.info(f"Form data before Next click: {form_data}")
                    # Check if username is in form data
                    username_in_form = any(username in str(v) for v in form_data.values())
                    if not username_in_form:
                        logger.warning("Username not found in form data! Attempting to set it again...")
                        # Try to find the input by name and set it
                        # Escape username before using in f-string
                        escaped_username_form = username.replace("'", "\\'").replace("\\", "\\\\")
                        await self.page.evaluate(f"""
                            () => {{
                                const inputs = document.querySelectorAll('input[name="text"], input[name="username"], input[autocomplete="username"]');
                                for (let input of inputs) {{
                                    if (input.offsetWidth > 0 && input.offsetHeight > 0) {{
                                        input.value = '{escaped_username_form}';
                                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                }}
                            }}
                        """)
                        await asyncio.sleep(1)
            except Exception as e:
                logger.debug(f"Could not check form data: {e}")
            
            # Double-check the input value one more time
            try:
                final_check = await username_input.evaluate("el => el.tagName === 'INPUT' ? el.value : el.textContent")
                logger.info(f"Final check before Next - Username in input: '{final_check}'")
                if final_check != username and username not in final_check:
                    logger.error(f"CRITICAL: Username not properly set! Expected: '{username}', Got: '{final_check}'")
                    logger.error("The username will not be submitted to X.com. Please check the browser manually.")
            except Exception as e:
                logger.debug(f"Final check failed: {e}")

            next_button = None
            for selector in next_selectors:
                try:
                    next_button = self.page.locator(selector).first
                    await next_button.wait_for(timeout=2000)
                    logger.info(f"Found next button with selector: {selector}")
                    break
                except:
                    continue

            if next_button:
                await next_button.click()
                logger.info("Clicked next button")
                await asyncio.sleep(3)
            else:
                # Try pressing Enter on username field
                await username_input.press("Enter")
                logger.info("Pressed Enter on username field")
                await asyncio.sleep(3)

            # Check for errors after clicking next/submit
            if await self._check_for_login_errors():
                return False

            # Log current URL after username submission
            current_url = self.page.url
            logger.info(f"Current URL after username submission: {current_url}")

            # Check if we're still on login page or redirected elsewhere
            if "login" not in current_url.lower() and "checkpoint" not in current_url.lower():
                logger.info("Redirected away from login page - possibly successful or additional verification needed")

            # Fill password - try multiple selectors
            password_selectors = [
                '[data-testid="login-password"]',
                'input[name="password"]',
                'input[type="password"]',
                'input[autocomplete="current-password"]'
            ]

            password_input = None
            for selector in password_selectors:
                try:
                    password_input = self.page.locator(selector).first
                    await password_input.wait_for(timeout=3000)
                    logger.info(f"Found password input with selector: {selector}")
                    break
                except:
                    continue

            if not password_input:
                logger.warning("Password input field not found")
                return False

            await password_input.fill(self.config.twitter_password)
            await asyncio.sleep(1)
            
            # Check for errors after password entry
            if await self._check_for_login_errors():
                return False

            # Submit login - try multiple selectors
            login_selectors = [
                '[data-testid="login-button"]',
                '[role="button"]:has-text("Log in")',
                '[role="button"]:has-text("Sign in")',
                'button[type="submit"]',
                '[data-testid*="button"]:has-text("Log in")'
            ]

            login_button = None
            for selector in login_selectors:
                try:
                    login_button = self.page.locator(selector).first
                    await login_button.wait_for(timeout=1000)
                    break
                except:
                    continue

            if login_button:
                await login_button.click()
                logger.info("Clicked login button")
            else:
                # Try pressing Enter on password field
                await password_input.press("Enter")
                logger.info("Pressed Enter on password field")

            await asyncio.sleep(5)
            
            # Check for errors after login attempt
            if await self._check_for_login_errors():
                return False

            # Wait for successful login (check for home timeline or profile elements)
            success_selectors = [
                '[data-testid="primaryColumn"]',
                '[data-testid="User-Name"]',
                '[data-testid="AppTabBar_Home_Link"]',
                'nav[role="navigation"]'
            ]

            for selector in success_selectors:
                try:
                    element = self.page.locator(selector).first
                    await element.wait_for(timeout=5000)
                    logger.info("Login successful!")
                    return True
                except:
                    continue

            logger.error("Login appeared to succeed but couldn't verify authentication")
            return False

        except Exception as e:
            logger.error(f"Automatic login failed: {e}")
            return False

    async def check_authentication(self) -> bool:
        """Check if user is authenticated on X/Twitter."""
        if not self.page:
            return False

        try:
            # Look for indicators that user is logged in
            # This is a basic check - may need refinement based on actual X UI
            home_indicator = self.page.locator('[data-testid="primaryColumn"]').first
            await home_indicator.wait_for(timeout=5000)
            logger.info("User appears to be authenticated")
            return True

        except Exception as e:
            logger.warning(f"Authentication check failed: {e}")

            # Try automatic login if credentials are provided
            if self.config.twitter_username and self.config.twitter_password:
                logger.info("Credentials provided, attempting automatic login...")
                login_result = await self.login_to_twitter()
                if login_result:
                    return True
                else:
                    logger.warning("Automatic login failed - possibly due to rate limiting or additional verification")
                    logger.info("Falling back to manual login mode")
                    # Continue to manual login flow below

            # Manual login mode (fallback or when no credentials provided)
            logger.info("Please log in manually to X.com in the browser window")
            logger.info("Waiting for authentication... (you have 5 minutes for MFA/password)")

            # Give user time to log in manually (5 minutes = 300 seconds)
            total_timeout = 300
            check_interval = 10

            for i in range(total_timeout, 0, -check_interval):
                await asyncio.sleep(check_interval)
                try:
                    # Check again for authentication
                    home_indicator = self.page.locator('[data-testid="primaryColumn"]').first
                    await home_indicator.wait_for(timeout=1000)
                    logger.info("Authentication successful!")
                    return True
                except:
                    remaining_minutes = i // 60
                    remaining_seconds = i % 60
                    if remaining_seconds == 0:
                        logger.info(f"Still waiting for authentication... ({remaining_minutes} minutes remaining)")
                    elif i <= 60:
                        logger.info(f"Still waiting for authentication... ({remaining_seconds} seconds remaining)")

            logger.error("Authentication timeout - please restart and log in within 5 minutes")
            return False

    async def get_random_delay(self) -> float:
        """Get a random delay between actions to appear more human-like."""
        return random.uniform(
            self.config.timing.min_delay_between_actions,
            self.config.timing.max_delay_between_actions,
        )

    async def run(self) -> None:
        """Main bot execution loop."""
        logger.info("Starting main bot execution loop")
        self.running = True

        try:
            # Navigate to Twitter
            if not await self.navigate_to_twitter():
                logger.error("Failed to navigate to Twitter, stopping")
                return

            # Check authentication
            if not await self.check_authentication():
                logger.error("User not authenticated, stopping")
                return

            logger.info("Bot initialization complete, entering main loop")

            while self.running:
                try:
                    # Randomly decide: 1/3 create new post, 2/3 reply to post
                    action_choice = random.random()
                    
                    if action_choice < 0.333:  # 1/3 probability - create new post
                        logger.info("Action: Creating new post")
                        success = await self.create_new_post()
                        if success:
                            logger.info("Successfully created new post")
                        else:
                            logger.warning("Failed to create new post")
                    else:  # 2/3 probability - reply to post
                        logger.info("Action: Replying to post")
                        # Read next post
                        post = await self.read_next_post()
                        if post:
                            logger.info(f"Read post: {post.text[:50]}...")

                            # Reply to post
                            success = await self.reply_to_post(post)
                            if success:
                                logger.info("Successfully replied to post")
                            else:
                                logger.warning("Failed to reply to post")

                            # Scroll to load new posts after successful reply
                            logger.info("Scrolling to load new posts...")
                            await self.scroll_to_next_post()

                            # Reset post index to start fresh from newly loaded content
                            self.current_post_index = 0
                        else:
                            # No post found, try scrolling to load more
                            logger.info("No new post found, scrolling to load more...")
                            await self.scroll_to_next_post()

                            # Wait a bit for posts to load
                            await asyncio.sleep(2)

                            # Check again for posts after scrolling
                            post = await self.read_next_post()
                            if not post:
                                # Still no posts, wait longer and try again
                                logger.info("Still no posts after scrolling, waiting before retry...")
                                await asyncio.sleep(5)

                    # Random delay between actions
                    delay = await self.get_random_delay()
                    logger.debug(f"Waiting {delay:.1f} seconds before next action")
                    await asyncio.sleep(delay)

                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    await asyncio.sleep(5)  # Brief pause before retry

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, stopping gracefully")
        except Exception as e:
            logger.error(f"Fatal error in bot execution: {e}")
        finally:
            self.running = False

    async def read_next_post(self, depth: int = 0) -> Optional[PostData]:
        """Read the next post in the feed."""
        if not self.page:
            logger.error("Browser page not initialized")
            return None

        try:
            # Wait for posts to load - look for timeline or feed indicators
            await self.page.wait_for_selector('[data-testid="primaryColumn"], [role="main"], article, [data-testid*="reply"]', timeout=10000)

            # Find all visible posts on the timeline - look for articles or posts with reply buttons
            post_selectors = [
                'article[data-testid*="tweet"]',
                'article[role="article"]',
                '[data-testid*="tweet"]:has([data-testid*="reply"])',
                'article:has([data-testid*="reply"])',
                'article:has(button[aria-label*="Reply"])',
                'article:has(button[aria-label*="Reply to"])'
            ]

            posts_found = False
            post_elements = []
            for selector in post_selectors:
                try:
                    post_elements = await self.page.query_selector_all(selector)
                    if post_elements and len(post_elements) > 0:
                        logger.info(f"Found {len(post_elements)} posts using selector: {selector}")
                        posts_found = True
                        break
                except Exception as e:
                    logger.debug(f"Selector '{selector}' failed: {e}")
                    continue

            if not posts_found or not post_elements:
                logger.warning("No posts found on the page with any selector")
                # Let's debug what elements are actually on the page
                try:
                    all_articles = await self.page.query_selector_all('article')
                    all_divs = await self.page.query_selector_all('div[data-testid*="tweet"]')

                    # More comprehensive debugging - inspect current X interface
                    debug_info = await self.page.evaluate("""
                        () => {
                            const results = {
                                articles: document.querySelectorAll('article').length,
                                dataTestIds: [],
                                roles: [],
                                replyButtons: document.querySelectorAll('[data-testid*="reply"]').length,
                                tweetElements: document.querySelectorAll('[data-testid*="tweet"]').length
                            };

                            // Get unique data-testid values
                            const testidElements = document.querySelectorAll('[data-testid]');
                            const testids = new Set();
                            for (let el of testidElements) {
                                testids.add(el.getAttribute('data-testid'));
                            }
                            results.dataTestIds = Array.from(testids).slice(0, 15); // First 15 unique

                            // Get unique role values
                            const roleElements = document.querySelectorAll('[role]');
                            const roles = new Set();
                            for (let el of roleElements) {
                                roles.add(el.getAttribute('role'));
                            }
                            results.roles = Array.from(roles).slice(0, 10); // First 10 unique

                            return results;
                        }
                    """)

                    logger.info(f"Debug: Found {debug_info['articles']} article elements")
                    logger.info(f"Debug: Found {debug_info['replyButtons']} reply button elements")
                    logger.info(f"Debug: Found {debug_info['tweetElements']} tweet-related elements")
                    logger.info(f"Debug: Available data-testid attributes: {debug_info['dataTestIds']}")
                    logger.info(f"Debug: Available role attributes: {debug_info['roles']}")

                except Exception as e:
                    logger.warning(f"Debug inspection failed: {e}")
                return None

            # Get the post at current index (skip already processed ones)
            # Re-query elements each time to avoid stale handles after long-running sessions
            while True:
                try:
                    # Re-query elements to avoid stale handles (prevents "object has been collected" error)
                    current_post_elements = []
                    for selector in post_selectors:
                        try:
                            current_post_elements = await self.page.query_selector_all(selector)
                            if current_post_elements and len(current_post_elements) > 0:
                                break
                        except Exception as e:
                            logger.debug(f"Re-query selector '{selector}' failed: {e}")
                            continue
                    
                    if not current_post_elements or self.current_post_index >= len(current_post_elements):
                        # No more posts available
                        break
                    
                    post_element = current_post_elements[self.current_post_index]

                    # Try to get post ID or unique identifier
                    post_id = await self._get_post_id(post_element, self.current_post_index)

                    # Skip if we already replied to this post
                    if post_id in self.processed_post_ids:
                        logger.info(f"SKIPPING already replied-to post: {post_id}")
                        self.current_post_index += 1
                        continue

                    logger.debug(f"Processing new post with ID: {post_id}")

                    # Extract post data
                    post_data = await self._extract_post_data(post_element, post_id)
                    if post_data and post_data.text.strip():
                        # Skip posts that are our own recent replies
                        post_text_clean = post_data.text.strip()
                        if post_text_clean in self.recent_replies:
                            logger.info(f"Detected our own recent reply in feed: '{post_text_clean}' by {post_data.author}")
                            if depth < 3:
                                await self.refresh_feed("detected own reply in feed")
                                return await self.read_next_post(depth=depth + 1)
                            logger.warning("Maximum refresh attempts reached while avoiding own replies")
                            self.current_post_index += 1
                            continue

                        # Skip posts that are likely AI-generated replies (very short, philosophical, or common reply patterns)
                        text_lower = post_data.text.lower().strip()

                        # Skip obvious fallback replies
                        if "why?" in text_lower and len(post_data.text.strip()) <= 10:
                            logger.info(f"SKIPPING fallback reply 'Why?': '{post_data.text}' by {post_data.author}")
                            self.current_post_index += 1
                            continue

                        # Skip very short posts that look like AI replies (under 50 chars and no links/media)
                        if len(post_data.text.strip()) <= 50 and not any(word in text_lower for word in ['http', 'www', '@', '#']):
                            # Check for common AI reply patterns
                            ai_patterns = [
                                'think about', 'consider', 'what if', 'perhaps', 'maybe',
                                'innovate', 'advance', 'progress', 'future', 'change',
                                'explore', 'discover', 'learn', 'grow', 'evolve'
                            ]
                            if any(pattern in text_lower for pattern in ai_patterns):
                                logger.info(f"SKIPPING likely AI-generated reply: '{post_data.text}' by {post_data.author}")
                                self.current_post_index += 1
                                continue

                        self.current_post_index += 1
                        logger.info(f"Successfully read post: '{post_data.text[:50]}...' by {post_data.author}")
                        return post_data
                    else:
                        logger.debug(f"Post at index {self.current_post_index} had no extractable text, skipping")

                    self.current_post_index += 1

                except Exception as e:
                    error_msg = str(e)
                    # Check if this is the "object has been collected" error
                    if "collected to prevent unbounded heap growth" in error_msg or "has been collected" in error_msg:
                        logger.warning(f"Element handle became stale (garbage collected) at index {self.current_post_index}: {e}")
                        logger.info("Refreshing page to reset element handles...")
                        try:
                            await self.refresh_feed("element handle garbage collected")
                            # Reset index and retry
                            self.current_post_index = 0
                            # Recursively retry reading post
                            if depth < 2:
                                return await self.read_next_post(depth=depth + 1)
                            else:
                                logger.error("Max depth reached after element collection error")
                                return None
                        except Exception as refresh_error:
                            logger.error(f"Failed to refresh feed after element collection error: {refresh_error}")
                            return None
                    else:
                        logger.warning(f"Error reading post at index {self.current_post_index}: {e}")
                        self.current_post_index += 1
                        continue

            # If we've processed all visible posts, try scrolling to load more
            logger.info("Reached end of visible posts, need to scroll for more")
            return None

        except Exception as e:
            error_msg = str(e)
            # Check if this is the "object has been collected" error
            if "collected to prevent unbounded heap growth" in error_msg or "has been collected" in error_msg:
                logger.warning(f"Element handle became stale (garbage collected) in read_next_post: {e}")
                logger.info("Refreshing page to reset element handles...")
                try:
                    await self.refresh_feed("element handle garbage collected")
                    # Reset index and retry
                    self.current_post_index = 0
                    # Recursively retry reading post
                    if depth < 2:
                        return await self.read_next_post(depth=depth + 1)
                    else:
                        logger.error("Max depth reached after element collection error")
                        return None
                except Exception as refresh_error:
                    logger.error(f"Failed to refresh feed after element collection error: {refresh_error}")
                    return None
            else:
                logger.error(f"Error reading next post: {e}")
                return None

    async def _get_post_id(self, post_element, index: int) -> str:
        """Generate a unique identifier for a post using author and content."""
        try:
            # Get author and content for stable identification
            author = ""
            content_hash = 0

            try:
                # Try to get author name
                author_element = await post_element.query_selector('[data-testid="User-Name"]')
                if author_element:
                    author = await author_element.inner_text()
                else:
                    # Try role="link" for author
                    author_links = await post_element.query_selector_all('[role="link"]')
                    for link in author_links:
                        link_text = await link.inner_text()
                        if '@' in link_text:
                            author = link_text
                            break
            except:
                pass

            try:
                # Get post content
                text_element = await post_element.query_selector('[data-testid="tweetText"]')
                if text_element:
                    post_text = await text_element.inner_text()
                    # Clean and hash first 100 characters for stability
                    content_part = post_text[:100].strip().replace('\n', ' ').replace('\t', ' ')
                    content_hash = hash(content_part) if content_part else 0
            except:
                pass

            # Try to get timestamp for additional uniqueness
            timestamp = ""
            try:
                time_element = await post_element.query_selector('time')
                if time_element:
                    timestamp = await time_element.get_attribute('datetime') or ""
            except:
                pass

            # Create stable ID using author + content + timestamp
            if author and content_hash != 0:
                stable_id = f"{author}_{content_hash}_{timestamp[:19] if timestamp else ''}"
                logger.debug(f"Stable post ID: {stable_id[:60]}...")
                return stable_id

            # Fallback using just content if available
            if content_hash != 0:
                content_id = f"content_{content_hash}_{index}"
                logger.debug(f"Content-based post ID: {content_id}")
                return content_id

            # Final fallback
            fallback_id = f"fallback_{index}_{int(time.time())}"
            logger.debug(f"Fallback post ID: {fallback_id}")
            return fallback_id

        except Exception as e:
            error_msg = str(e)
            # Re-raise if this is the "object has been collected" error so caller can handle it
            if "collected to prevent unbounded heap growth" in error_msg or "has been collected" in error_msg:
                logger.warning(f"Element handle became stale in _get_post_id: {e}")
                raise  # Re-raise so caller can refresh and retry
            logger.debug(f"Error generating post ID: {e}")
            return f"error_{index}_{int(time.time())}"

    async def _extract_post_data(self, post_element, post_id: str) -> Optional[PostData]:
        """Extract text, author, and other data from a post element."""
        try:
            # Get the text content from the article
            text_content = ""
            try:
                # Look for text content within the article - try multiple approaches
                text_selectors = [
                    '[data-testid="tweetText"]',
                    '[data-testid="Tweet-User-Text"]',
                    'div[data-testid*="tweet"] [lang]',
                    '[role="group"] [lang]',
                    'article [lang]',
                    'span[dir="ltr"]',
                    'div[dir="ltr"]'
                ]

                for selector in text_selectors:
                    try:
                        text_element = await post_element.query_selector(selector)
                        if text_element:
                            text_content = await text_element.inner_text()
                            if text_content and text_content.strip():
                                # Clean up the text (remove extra whitespace, newlines)
                                text_content = ' '.join(text_content.split())
                                break
                    except:
                        continue

            except:
                pass

            # Get author information
            author = "Unknown"
            try:
                # Try to find author name within the article
                author_selectors = [
                    '[data-testid="User-Name"]',
                    '[role="link"] [dir="ltr"]',
                    '[data-testid*="user"] [dir="ltr"]',
                    'article [role="link"] [dir="ltr"]',
                    'article [role="link"] span',
                    '[data-testid="Tweet-User-Name"]',
                    'article [data-testid*="user"]'
                ]

                for selector in author_selectors:
                    try:
                        author_element = await post_element.query_selector(selector)
                        if author_element:
                            author_text = await author_element.inner_text()
                            if author_text and author_text.strip() and len(author_text.strip()) > 1:
                                author = author_text.strip()
                                break
                    except:
                        continue

            except:
                pass

            # Get timestamp if available
            timestamp = None
            try:
                time_element = await post_element.query_selector('time')
                if time_element:
                    timestamp = await time_element.get_attribute('datetime')
            except:
                pass

            if not text_content.strip():
                return None

            return PostData(
                text=text_content.strip(),
                author=author,
                post_id=post_id,
                timestamp=timestamp
            )

        except Exception as e:
            error_msg = str(e)
            # Re-raise if this is the "object has been collected" error so caller can handle it
            if "collected to prevent unbounded heap growth" in error_msg or "has been collected" in error_msg:
                logger.warning(f"Element handle became stale in _extract_post_data: {e}")
                raise  # Re-raise so caller can refresh and retry
            logger.warning(f"Error extracting post data: {e}")
            return None

    async def reply_to_post(self, post: PostData) -> bool:
        """Reply to a specific post."""
        if not self.page or not self.http_session:
            logger.error("Browser page or HTTP session not initialized")
            return False

        try:
            logger.info(f"Attempting to reply to post: '{post.text[:50]}...' by {post.author}")

            # Generate reply using Grok API
            if not GROK_API_KEY:
                logger.warning("GROK_API_KEY not found, using fallback reply")
                reply_text = "Why?"
            else:
                # Create user prompt from post content
                user_prompt = f"Generate a reply to this post: '{post.text[:200]}...'"
                logger.debug(f"Calling Grok API with prompt: {user_prompt}")

                reply_text = await call_grok_api(
                    session=self.http_session,
                    system_prompt=self.prompt_manager.get_random_prompt(SYSTEM_PROMPT),
                    user_prompt=user_prompt
                )

            logger.info(f"Using reply: '{reply_text}'")

            # Find the reply button within this specific post
            # We need to find the post element again and locate its reply button
            reply_selectors = [
                '[data-testid="reply"]',
                '[role="button"][aria-label*="Reply"]',
                '[role="button"][aria-label*="Reply to"]',
                'button[aria-label*="Reply"]',
                '[data-testid*="reply"]:not([aria-disabled="true"])'
            ]

            reply_button = None
            for selector in reply_selectors:
                try:
                    # Try to find reply buttons and click the first one that's visible and enabled
                    reply_buttons = await self.page.query_selector_all(selector)
                    for button in reply_buttons:
                        # Check if button is visible and not disabled
                        is_visible = await button.is_visible()
                        if is_visible:
                            reply_button = button
                            break
                    if reply_button:
                        break
                except Exception as e:
                    logger.debug(f"Reply selector '{selector}' failed: {e}")
                    continue

            if not reply_button:
                logger.warning("Could not find reply button on the page")
                return False

            # Click the reply button
            try:
                await reply_button.click()
                logger.info("Clicked reply button")
                await asyncio.sleep(2)  # Wait for modal to appear
            except Exception as e:
                logger.warning(f"Failed to click reply button: {e}")
                return False

            # Wait for the reply modal to appear
            try:
                # Look for modal indicators
                modal_selectors = [
                    '[role="dialog"]',
                    '[data-testid*="modal"]',
                    '[data-testid*="reply"]',
                    '.modal-content',
                    '[aria-modal="true"]',
                    '[data-testid="Tweet-User-Reply"]',
                    '[data-testid="tweetTextarea_0"]'
                ]

                modal_found = False
                for selector in modal_selectors:
                    try:
                        modal = await self.page.wait_for_selector(selector, timeout=5000)
                        if modal:
                            logger.info(f"Found reply modal with selector: {selector}")
                            modal_found = True
                            break
                    except:
                        continue

                if not modal_found:
                    logger.warning("Reply modal did not appear - checking page state")
                    # Debug: take a screenshot and log current page elements
                    try:
                        await self.page.screenshot(path="debug_modal.png")
                        logger.info("Saved debug screenshot: debug_modal.png")

                        # Log all visible elements that might be related to replies
                        debug_elements = await self.page.evaluate("""
                            () => {
                                const elements = document.querySelectorAll('[data-testid], [role], textarea, input');
                                const results = [];
                                for (let el of elements) {
                                    if (el.offsetWidth > 0 && el.offsetHeight > 0) {  // Only visible elements
                                        const attrs = {};
                                        for (let attr of el.attributes) {
                                            attrs[attr.name] = attr.value;
                                        }
                                        results.push({
                                            tag: el.tagName,
                                            attrs: attrs,
                                            text: el.textContent?.substring(0, 50) || ''
                                        });
                                    }
                                }
                                return results.slice(0, 20); // First 20 visible elements
                            }
                        """)
                        logger.info(f"Visible elements on page: {debug_elements}")
                    except Exception as debug_e:
                        logger.warning(f"Debug logging failed: {debug_e}")

            except Exception as e:
                logger.warning(f"Error waiting for reply modal: {e}")

            # Wait for the reply input to appear (in the modal)
            reply_input_selectors = [
                '[data-testid="tweetTextarea_0"]',
                '[data-testid="tweetTextarea_1"]',
                '[role="textbox"][contenteditable="true"]',
                '[data-testid*="tweet"] [role="textbox"]',
                'textarea[placeholder*="reply"]',
                'textarea[placeholder*="Reply"]',
                '[role="dialog"] [role="textbox"]',
                '[aria-modal="true"] [role="textbox"]',
                '[data-testid="Tweet-User-Reply"] textarea',
                '[data-testid="Tweet-User-Reply"] [contenteditable="true"]',
                'div[data-testid*="tweet"][contenteditable="true"]',
                '[data-testid*="reply"] textarea',
                '[data-testid*="reply"] [contenteditable="true"]'
            ]

            reply_input = None
            for selector in reply_input_selectors:
                try:
                    reply_input = await self.page.wait_for_selector(selector, timeout=5000)
                    if reply_input:
                        logger.info(f"Found reply input with selector: {selector}")
                        # Check if it's actually visible and enabled
                        is_visible = await reply_input.is_visible()
                        logger.info(f"Reply input visible: {is_visible}")
                        if is_visible:
                            break
                        else:
                            reply_input = None
                except:
                    continue

            if not reply_input:
                logger.warning("Could not find reply text input in modal")
                # Additional debugging for reply input
                try:
                    all_text_inputs = await self.page.evaluate("""
                        () => {
                            const inputs = document.querySelectorAll('textarea, [contenteditable="true"], input[type="text"]');
                            return Array.from(inputs).map(input => ({
                                tag: input.tagName,
                                id: input.id,
                                class: input.className,
                                placeholder: input.placeholder,
                                visible: input.offsetWidth > 0 && input.offsetHeight > 0
                            })).filter(input => input.visible);
                        }
                    """)
                    logger.info(f"All visible text inputs: {all_text_inputs}")
                except Exception as debug_e:
                    logger.warning(f"Text input debugging failed: {debug_e}")
                return False

            # Clear any existing text and enter our reply
            try:
                # First click on the input to focus it
                await reply_input.click()
                await asyncio.sleep(0.5)

                # Clear any existing text by selecting all and deleting
                await reply_input.press("Control+a")
                await reply_input.press("Backspace")
                await asyncio.sleep(0.5)

                # Enter our reply text by typing (more reliable than fill for contenteditable)
                await reply_input.type(reply_text, delay=50)
                await asyncio.sleep(1)

                # Verify text was entered by checking the element's text content
                try:
                    entered_text = await reply_input.inner_text()
                    if not entered_text or entered_text.strip() != reply_text:
                        logger.warning(f"Text entry verification failed. Expected: '{reply_text}', Got: '{entered_text}'")
                        # Try fill method as fallback
                        await reply_input.fill("")
                        await reply_input.fill(reply_text)
                        await asyncio.sleep(0.5)
                    else:
                        logger.info(f"Successfully entered reply text: '{entered_text}'")
                except:
                    logger.info("Could not verify text entry, proceeding...")

                await asyncio.sleep(2)  # Give time for UI to update and button to become enabled
            except Exception as e:
                logger.warning(f"Failed to enter reply text: {e}")
                return False

            # Find and click the submit button (in the modal)
            submit_selectors = [
                '[role="dialog"] [data-testid="tweetButton"]',
                '[aria-modal="true"] [data-testid="tweetButton"]',
                '[data-testid="tweetButtonInline"]',
                '[role="dialog"] [role="button"]:has-text("Reply")',
                '[aria-modal="true"] [role="button"]:has-text("Reply")',
                '[role="dialog"] [role="button"]:has-text("Post")',
                '[aria-modal="true"] [role="button"]:has-text("Post")',
                '[role="dialog"] button[type="submit"]',
                '[aria-modal="true"] button[type="submit"]',
                '[data-testid*="button"]:has-text("Reply")',
                '[data-testid="Tweet-User-Reply"] button',
                '[data-testid*="reply"] button',
                'button[data-testid*="tweet"]:not([disabled])'
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = await self.page.query_selector(selector)
                    if submit_button:
                        # Check if button is visible and enabled
                        is_visible = await submit_button.is_visible()
                        is_disabled = await submit_button.get_attribute('aria-disabled')
                        button_text = await submit_button.inner_text()
                        logger.info(f"Found button with selector '{selector}': visible={is_visible}, disabled={is_disabled}, text='{button_text}'")

                        if is_visible and is_disabled != 'true' and ('Reply' in button_text or 'Post' in button_text):
                            logger.info(f"Using submit button with selector: {selector}")
                            break
                        else:
                            submit_button = None
                except:
                    continue

            if not submit_button:
                logger.warning("Could not find submit button or it's disabled")
                # Additional debugging for buttons
                try:
                    all_buttons = await self.page.evaluate("""
                        () => {
                            const buttons = document.querySelectorAll('button, [role="button"]');
                            return Array.from(buttons).map(button => ({
                                tag: button.tagName,
                                text: button.textContent?.trim(),
                                disabled: button.disabled,
                                visible: button.offsetWidth > 0 && button.offsetHeight > 0,
                                attrs: Array.from(button.attributes).reduce((acc, attr) => {
                                    acc[attr.name] = attr.value;
                                    return acc;
                                }, {})
                            })).filter(button => button.visible).slice(0, 10); // First 10 visible buttons
                        }
                    """)
                    logger.info(f"All visible buttons: {all_buttons}")
                except Exception as debug_e:
                    logger.warning(f"Button debugging failed: {debug_e}")
                return False

            # Submit the reply
            try:
                await submit_button.click()
                logger.info("Clicked submit button - reply posted!")

                # Mark this post as replied to
                self.processed_post_ids.add(post.post_id)
                logger.debug(f"Marked post {post.post_id} as replied to")

                # Track this reply to avoid replying to our own posts
                self.recent_replies.append(reply_text)
                # Keep only the last 20 replies to avoid memory issues
                if len(self.recent_replies) > 20:
                    self.recent_replies.pop(0)
                logger.debug(f"Added reply to tracking: '{reply_text}' (total tracked: {len(self.recent_replies)})")

                await asyncio.sleep(2)  # Wait for submission to complete

                # Ensure the reply modal has closed; if not, close it and refresh the feed
                modal_visibility_selectors = [
                    '[role="dialog"]',
                    '[aria-modal="true"]',
                    '[data-testid*="modal"]',
                    '[data-testid="Tweet-User-Reply"]',
                    '[data-testid="tweetTextarea_0"]'
                ]

                modal_still_open = False
                for selector in modal_visibility_selectors:
                    try:
                        element = await self.page.query_selector(selector)
                        if element and await element.is_visible():
                            modal_still_open = True
                            logger.warning(f"Reply modal still visible after submit (selector: {selector})")
                            break
                    except Exception as modal_check_error:
                        logger.debug(f"Modal visibility check failed for selector '{selector}': {modal_check_error}")

                if modal_still_open:
                    logger.info("Attempting to close lingering reply modal")
                    close_button_selectors = [
                        '[data-testid="app-bar-close"]',
                        '[data-testid="modalClose"]',
                        '[role="button"][aria-label="Close"]',
                        '[role="button"][aria-label="close"]',
                        '[role="button"][aria-label*="Close"]',
                        '[data-testid*="close"]'
                    ]

                    for selector in close_button_selectors:
                        try:
                            close_button = await self.page.query_selector(selector)
                            if close_button and await close_button.is_visible():
                                await close_button.click()
                                logger.info(f"Clicked close button selector: {selector}")
                                await asyncio.sleep(1)
                                break
                        except Exception as close_error:
                            logger.debug(f"Close selector '{selector}' failed: {close_error}")

                    # Re-check modal visibility after attempting to click close
                    modal_still_open = False
                    for selector in modal_visibility_selectors:
                        try:
                            element = await self.page.query_selector(selector)
                            if element and await element.is_visible():
                                modal_still_open = True
                                break
                        except Exception:
                            continue

                    if modal_still_open:
                        try:
                            await self.page.keyboard.press("Escape")
                            logger.info("Pressed Escape key to dismiss reply modal")
                            await asyncio.sleep(1)
                        except Exception as escape_error:
                            logger.debug(f"Escape key press failed: {escape_error}")

                        # Final visibility check
                        modal_still_open = False
                        for selector in modal_visibility_selectors:
                            try:
                                element = await self.page.query_selector(selector)
                                if element and await element.is_visible():
                                    modal_still_open = True
                                    break
                            except Exception:
                                continue

                    if modal_still_open:
                        logger.warning("Reply modal remained open after manual close attempts")
                    else:
                        logger.info("Reply modal closed successfully after manual intervention")

                    try:
                        await self.refresh_feed("modal stuck after replying")
                    except Exception as refresh_error:
                        logger.warning(f"Failed to refresh feed after closing modal: {refresh_error}")

                return True
            except Exception as e:
                logger.warning(f"Failed to submit reply: {e}")
                return False

        except Exception as e:
            logger.error(f"Error replying to post: {e}")
            return False

    async def create_new_post(self) -> bool:
        """Create a new post based on prompts."""
        if not self.page or not self.http_session:
            logger.error("Browser page or HTTP session not initialized")
            return False

        try:
            logger.info("Attempting to create a new post")

            # Generate post content using Grok API
            if not GROK_API_KEY:
                logger.warning("GROK_API_KEY not found, using fallback post")
                post_text = "Exploring the future of technology and humanity's path to Type 1 civilization."
            else:
                # Create user prompt for generating a new post
                user_prompt = "Generate a unique, engaging post about scientific progress, technological advancement, early-stage investing in energy/robotics/AI, or positive societal change. Make it thought-provoking and actionable."
                logger.debug(f"Calling Grok API to generate new post with prompt: {user_prompt}")

                post_text = await call_grok_api(
                    session=self.http_session,
                    system_prompt=self.prompt_manager.get_random_prompt(POST_SYSTEM_PROMPT),
                    user_prompt=user_prompt,
                    max_tokens=100  # Allow more tokens for posts (280 chars max)
                )

            # Ensure post is 280 characters or less (Twitter/X limit)
            if len(post_text) > 280:
                post_text = post_text[:277] + "..."
                logger.info(f"Truncated post to 280 characters")

            logger.info(f"Generated post: '{post_text}' (len: {len(post_text)})")

            # Find the compose button (usually in the sidebar or top navigation)
            compose_selectors = [
                '[data-testid="SideNav_NewTweet_Button"]',
                '[data-testid="tweetButtonInline"]',
                'a[href="/compose/tweet"]',
                '[aria-label="Post"]',
                '[aria-label="Tweet"]',
                '[role="button"]:has-text("Post")',
                '[role="button"]:has-text("Tweet")',
                'a[href*="compose"]',
                '[data-testid*="compose"]',
                '[data-testid*="tweet"] button'
            ]

            compose_button = None
            for selector in compose_selectors:
                try:
                    compose_button = await self.page.query_selector(selector)
                    if compose_button:
                        is_visible = await compose_button.is_visible()
                        if is_visible:
                            logger.info(f"Found compose button with selector: {selector}")
                            break
                        else:
                            compose_button = None
                except Exception as e:
                    logger.debug(f"Compose selector '{selector}' failed: {e}")
                    continue

            if not compose_button:
                logger.warning("Could not find compose button on the page")
                return False

            # Click the compose button
            try:
                await compose_button.click()
                logger.info("Clicked compose button")
                await asyncio.sleep(2)  # Wait for compose modal to appear
            except Exception as e:
                logger.warning(f"Failed to click compose button: {e}")
                return False

            # Wait for the compose modal/textarea to appear
            compose_input_selectors = [
                '[data-testid="tweetTextarea_0"]',
                '[data-testid="tweetTextarea_1"]',
                '[role="textbox"][contenteditable="true"]',
                '[data-testid*="tweet"] [role="textbox"]',
                'textarea[placeholder*="What is happening"]',
                '[role="dialog"] [role="textbox"]',
                '[aria-modal="true"] [role="textbox"]',
                'div[data-testid*="tweet"][contenteditable="true"]',
                '[data-testid*="compose"] [contenteditable="true"]'
            ]

            compose_input = None
            for selector in compose_input_selectors:
                try:
                    compose_input = await self.page.wait_for_selector(selector, timeout=5000)
                    if compose_input:
                        is_visible = await compose_input.is_visible()
                        logger.info(f"Found compose input with selector: {selector}, visible: {is_visible}")
                        if is_visible:
                            break
                        else:
                            compose_input = None
                except:
                    continue

            if not compose_input:
                logger.warning("Could not find compose text input")
                return False

            # Enter the post text
            try:
                # Click on the input to focus it
                await compose_input.click()
                await asyncio.sleep(0.5)

                # Clear any existing text
                await compose_input.press("Control+a")
                await compose_input.press("Backspace")
                await asyncio.sleep(0.5)

                # Type the post text
                await compose_input.type(post_text, delay=50)
                await asyncio.sleep(1)

                # Verify text was entered
                try:
                    entered_text = await compose_input.inner_text()
                    if not entered_text or entered_text.strip() != post_text:
                        logger.warning(f"Text entry verification failed. Expected: '{post_text}', Got: '{entered_text}'")
                        # Try fill method as fallback
                        await compose_input.fill("")
                        await compose_input.fill(post_text)
                        await asyncio.sleep(0.5)
                    else:
                        logger.info(f"Successfully entered post text: '{entered_text}'")
                except:
                    logger.info("Could not verify text entry, proceeding...")

                await asyncio.sleep(2)  # Give time for UI to update and button to become enabled
            except Exception as e:
                logger.warning(f"Failed to enter post text: {e}")
                return False

            # Find and click the submit button
            submit_selectors = [
                '[data-testid="tweetButton"]',
                '[data-testid="tweetButtonInline"]',
                '[role="dialog"] [data-testid="tweetButton"]',
                '[aria-modal="true"] [data-testid="tweetButton"]',
                '[role="button"]:has-text("Post")',
                '[role="button"]:has-text("Tweet")',
                '[data-testid*="button"]:has-text("Post")',
                'button[data-testid*="tweet"]:not([disabled])'
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = await self.page.query_selector(selector)
                    if submit_button:
                        is_visible = await submit_button.is_visible()
                        is_disabled = await submit_button.get_attribute('aria-disabled')
                        button_text = await submit_button.inner_text()
                        logger.info(f"Found button with selector '{selector}': visible={is_visible}, disabled={is_disabled}, text='{button_text}'")

                        if is_visible and is_disabled != 'true' and ('Post' in button_text or 'Tweet' in button_text):
                            logger.info(f"Using submit button with selector: {selector}")
                            break
                        else:
                            submit_button = None
                except:
                    continue

            if not submit_button:
                logger.warning("Could not find submit button or it's disabled")
                return False

            # Submit the post
            try:
                await submit_button.click()
                logger.info("Clicked submit button - post created!")

                # Track this post to avoid replying to our own posts
                self.recent_replies.append(post_text)
                # Keep only the last 20 posts to avoid memory issues
                if len(self.recent_replies) > 20:
                    self.recent_replies.pop(0)
                logger.debug(f"Added new post to tracking: '{post_text}' (total tracked: {len(self.recent_replies)})")

                await asyncio.sleep(2)  # Wait for submission to complete

                # Ensure the compose modal has closed
                modal_visibility_selectors = [
                    '[role="dialog"]',
                    '[aria-modal="true"]',
                    '[data-testid*="modal"]',
                    '[data-testid="tweetTextarea_0"]'
                ]

                modal_still_open = False
                for selector in modal_visibility_selectors:
                    try:
                        element = await self.page.query_selector(selector)
                        if element and await element.is_visible():
                            modal_still_open = True
                            logger.warning(f"Compose modal still visible after submit (selector: {selector})")
                            break
                    except:
                        continue

                if modal_still_open:
                    logger.info("Attempting to close lingering compose modal")
                    close_button_selectors = [
                        '[data-testid="app-bar-close"]',
                        '[data-testid="modalClose"]',
                        '[role="button"][aria-label="Close"]',
                        '[data-testid*="close"]'
                    ]

                    for selector in close_button_selectors:
                        try:
                            close_button = await self.page.query_selector(selector)
                            if close_button and await close_button.is_visible():
                                await close_button.click()
                                logger.info(f"Clicked close button selector: {selector}")
                                await asyncio.sleep(1)
                                break
                        except:
                            continue

                    # Try Escape key as fallback
                    try:
                        await self.page.keyboard.press("Escape")
                        logger.info("Pressed Escape key to dismiss compose modal")
                        await asyncio.sleep(1)
                    except:
                        pass

                # Refresh the feed to avoid replying to our own post
                try:
                    await self.refresh_feed("post created - refreshing to avoid replying to own post")
                except Exception as refresh_error:
                    logger.warning(f"Failed to refresh feed after creating post: {refresh_error}")

                return True
            except Exception as e:
                logger.warning(f"Failed to submit post: {e}")
                return False

        except Exception as e:
            logger.error(f"Error creating new post: {e}")
            return False

    async def scroll_to_next_post(self) -> None:
        """Scroll to the next post in the feed."""
        if not self.page:
            logger.error("Browser page not initialized")
            return

        try:
            # Get current scroll position
            current_scroll = await self.page.evaluate("window.scrollY")

            # Calculate new scroll position (scroll down by viewport height)
            viewport_height = await self.page.evaluate("window.innerHeight")
            new_scroll = current_scroll + viewport_height * 1.2  # Scroll 120% of viewport height for better content loading

            # Smooth scroll to new position
            await self.page.evaluate(f"""
                window.scrollTo({{
                    top: {new_scroll},
                    behavior: 'smooth'
                }});
            """)

            # Wait for new content to load
            await asyncio.sleep(2)

            # Check if we actually scrolled (to detect end of feed)
            actual_scroll = await self.page.evaluate("window.scrollY")
            if abs(actual_scroll - current_scroll) < 10:  # Less than 10px movement
                logger.info("Reached end of feed, no more posts to load")
                # Could implement page refresh here if needed
                # await self.page.reload()
                # await asyncio.sleep(3)
            else:
                logger.debug(f"Scrolled from {current_scroll} to {actual_scroll}")

        except Exception as e:
            logger.error(f"Error scrolling to next post: {e}")
            await asyncio.sleep(1)
