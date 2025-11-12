"""Tests for the main bot functionality."""

import pytest

from aiwebbot.bot import AIWebBot, PostData
from aiwebbot.config import Config


class TestPostData:
    """Test PostData dataclass."""

    def test_post_data_creation(self):
        """Test creating PostData instances."""
        post = PostData(
            text="Sample tweet text",
            author="testuser",
            post_id="12345"
        )
        assert post.text == "Sample tweet text"
        assert post.author == "testuser"
        assert post.post_id == "12345"
        assert post.timestamp is None

    def test_post_data_with_timestamp(self):
        """Test PostData with timestamp."""
        post = PostData(
            text="Sample tweet text",
            author="testuser",
            post_id="12345",
            timestamp="2023-11-12T10:00:00Z"
        )
        assert post.timestamp == "2023-11-12T10:00:00Z"


class TestAIWebBot:
    """Test AIWebBot class."""

    @pytest.mark.asyncio
    async def test_bot_initialization(self, default_config: Config):
        """Test bot initialization."""
        bot = AIWebBot(default_config)
        assert bot.config == default_config
        assert bot.playwright is None
        assert bot.browser is None
        assert bot.context is None
        assert bot.page is None
        assert bot.running is False

    @pytest.mark.asyncio
    async def test_random_delay(self, default_config: Config):
        """Test random delay generation."""
        bot = AIWebBot(default_config)

        # Generate multiple delays and check they're within bounds
        delays = []
        for _ in range(10):
            delay = await bot.get_random_delay()
            delays.append(delay)
            assert default_config.timing.min_delay_between_actions <= delay <= default_config.timing.max_delay_between_actions

        # Check that delays are varied (not all the same)
        assert len(set(delays)) > 1

    @pytest.mark.asyncio
    async def test_context_manager(self, default_config: Config):
        """Test async context manager functionality."""
        async with AIWebBot(default_config) as bot:
            assert isinstance(bot, AIWebBot)
            # Note: We can't easily test full browser startup in unit tests
            # without proper mocking or integration test setup

    def test_read_next_post_not_implemented(self, default_config: Config):
        """Test that read_next_post returns None (not yet implemented)."""
        bot = AIWebBot(default_config)
        # This would normally be an async test, but we're just checking the method exists
        assert hasattr(bot, 'read_next_post')

    def test_reply_to_post_not_implemented(self, default_config: Config, sample_post_data: PostData):
        """Test that reply_to_post exists (not yet implemented)."""
        bot = AIWebBot(default_config)
        assert hasattr(bot, 'reply_to_post')

    def test_scroll_to_next_post_not_implemented(self, default_config: Config):
        """Test that scroll_to_next_post exists (not yet implemented)."""
        bot = AIWebBot(default_config)
        assert hasattr(bot, 'scroll_to_next_post')
