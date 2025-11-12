"""Main AI Web Bot implementation."""

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Optional

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from .config import Config


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

        logger.info("Browser started successfully")

    async def stop(self) -> None:
        """Stop the browser and cleanup resources."""
        logger.info("Stopping AI Web Bot...")

        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        self.running = False
        logger.info("AI Web Bot stopped")

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

    async def login_to_twitter(self) -> bool:
        """Automatically log in to X/Twitter using provided credentials."""
        if not self.page or not self.config.twitter_username or not self.config.twitter_password:
            return False

        try:
            logger.info("Attempting automatic login to X/Twitter...")

            # Navigate directly to login page first
            login_url = "https://x.com/login"
            logger.info(f"Navigating to login page: {login_url}")
            await self.page.goto(login_url, wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # Try multiple selector patterns for username input
            username_selectors = [
                '[data-testid="login-username"]',
                'input[name="username"]',
                'input[autocomplete="username"]',
                'input[type="text"]',
                '[role="textbox"]'
            ]

            username_input = None
            for selector in username_selectors:
                try:
                    username_input = self.page.locator(selector).first
                    await username_input.wait_for(timeout=2000)
                    logger.info(f"Found username input with selector: {selector}")
                    break
                except:
                    continue

            if not username_input:
                logger.warning("Username input field not found with any selector")
                return False

            # Fill username
            await username_input.fill(self.config.twitter_username)
            logger.info(f"Entered username: {self.config.twitter_username}")
            await asyncio.sleep(2)

            # Try multiple patterns for next/submit button
            next_selectors = [
                '[data-testid="login-button"]',
                '[role="button"]:has-text("Next")',
                '[role="button"]:has-text("Submit")',
                'button[type="submit"]',
                '[data-testid*="button"]:has-text("Next")',
                '[data-testid*="button"]:has-text("Submit")'
            ]

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

            # Check for any error messages or unusual elements
            try:
                error_elements = await self.page.locator('[role="alert"], .error, [data-testid*="error"]').all_text_contents()
                if error_elements:
                    logger.warning(f"Found error elements on page: {error_elements}")

                    # Check for rate limiting or temporary block messages
                    rate_limit_messages = [
                        "could not log you in now",
                        "please try again later",
                        "rate limit",
                        "temporary block",
                        "too many attempts"
                    ]

                    error_text = " ".join(error_elements).lower()
                    if any(msg in error_text for msg in rate_limit_messages):
                        logger.warning("Detected rate limiting or temporary block from X/Twitter")
                        logger.info("Falling back to manual login mode due to rate limiting")
                        return False  # Return false to trigger manual login fallback

            except:
                pass

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

                        # Random delay between actions
                        delay = await self.get_random_delay()
                        logger.debug(f"Waiting {delay:.1f} seconds before next action")
                        await asyncio.sleep(delay)
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

                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    await asyncio.sleep(5)  # Brief pause before retry

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, stopping gracefully")
        except Exception as e:
            logger.error(f"Fatal error in bot execution: {e}")
        finally:
            self.running = False

    async def read_next_post(self) -> Optional[PostData]:
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
            while self.current_post_index < len(post_elements):
                try:
                    post_element = post_elements[self.current_post_index]

                    # Try to get post ID or unique identifier
                    post_id = await self._get_post_id(post_element, self.current_post_index)

                    # Skip if already processed
                    if post_id in self.processed_post_ids:
                        logger.debug(f"Skipping already processed post: {post_id}")
                        self.current_post_index += 1
                        continue

                    # Extract post data
                    post_data = await self._extract_post_data(post_element, post_id)
                    if post_data and post_data.text.strip():
                        self.processed_post_ids.add(post_id)
                        self.current_post_index += 1
                        logger.info(f"Successfully read post: '{post_data.text[:50]}...' by {post_data.author}")
                        return post_data
                    else:
                        logger.debug(f"Post at index {self.current_post_index} had no extractable text, skipping")

                    self.current_post_index += 1

                except Exception as e:
                    logger.warning(f"Error reading post at index {self.current_post_index}: {e}")
                    self.current_post_index += 1
                    continue

            # If we've processed all visible posts, try scrolling to load more
            logger.info("Reached end of visible posts, need to scroll for more")
            return None

        except Exception as e:
            logger.error(f"Error reading next post: {e}")
            return None

    async def _get_post_id(self, post_element, index: int) -> str:
        """Generate a unique identifier for a post."""
        try:
            # Try to get the post ID from various attributes
            post_id = await post_element.get_attribute('data-testid')
            if post_id and 'tweet' in post_id.lower():
                return f"{post_id}_{index}"

            # Try to get href or other identifying attributes
            href = await post_element.get_attribute('href')
            if href:
                return f"href_{href}_{index}"

            # Fallback to index-based ID
            return f"post_{index}_{int(time.time())}"

        except:
            # Final fallback
            return f"fallback_{index}_{int(time.time())}"

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
            logger.warning(f"Error extracting post data: {e}")
            return None

    async def reply_to_post(self, post: PostData) -> bool:
        """Reply to a specific post."""
        if not self.page:
            logger.error("Browser page not initialized")
            return False

        try:
            logger.info(f"Attempting to reply to post: '{post.text[:50]}...' by {post.author}")

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

                # Clear any existing text
                await reply_input.clear()

                # Try different methods to enter text
                await reply_input.fill(self.config.reply_text)
                await asyncio.sleep(0.5)

                # Verify text was entered
                entered_text = await reply_input.input_value()
                if entered_text != self.config.reply_text:
                    logger.warning(f"Text entry failed. Expected: '{self.config.reply_text}', Got: '{entered_text}'")
                    # Try typing instead of filling
                    await reply_input.clear()
                    await reply_input.type(self.config.reply_text, delay=100)
                    await asyncio.sleep(0.5)

                final_text = await reply_input.input_value()
                logger.info(f"Final reply text in input: '{final_text}'")
                await asyncio.sleep(1)
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
                await asyncio.sleep(2)  # Wait for submission to complete
                return True
            except Exception as e:
                logger.warning(f"Failed to submit reply: {e}")
                return False

        except Exception as e:
            logger.error(f"Error replying to post: {e}")
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
            new_scroll = current_scroll + viewport_height * 0.8  # Scroll 80% of viewport height

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
