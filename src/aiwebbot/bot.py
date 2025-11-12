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

                    # Scroll to next post
                    await self.scroll_to_next_post()

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

    async def read_next_post(self) -> Optional[PostData]:
        """Read the next post in the feed."""
        # TODO: Implement post reading logic
        logger.debug("Reading next post (not yet implemented)")
        return None

    async def reply_to_post(self, post: PostData) -> bool:
        """Reply to a specific post."""
        # TODO: Implement reply logic
        logger.debug(f"Replying to post (not yet implemented): {post.text[:50]}...")
        return False

    async def scroll_to_next_post(self) -> None:
        """Scroll to the next post in the feed."""
        # TODO: Implement scrolling logic
        logger.debug("Scrolling to next post (not yet implemented)")
        await asyncio.sleep(1)
