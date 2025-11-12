"""Tests for configuration management."""

import json
from pathlib import Path

import pytest

from aiwebbot.config import Config, BrowserConfig, TimingConfig, TwitterConfig, LoggingConfig


class TestBrowserConfig:
    """Test BrowserConfig model."""

    def test_default_values(self):
        """Test default browser configuration values."""
        config = BrowserConfig()
        assert config.headless is False
        assert config.slow_mo == 1000
        assert config.timeout == 30000
        assert config.viewport_width == 1280
        assert config.viewport_height == 720

    def test_custom_values(self):
        """Test custom browser configuration values."""
        config = BrowserConfig(
            headless=True,
            slow_mo=500,
            timeout=60000,
            viewport_width=1920,
            viewport_height=1080
        )
        assert config.headless is True
        assert config.slow_mo == 500
        assert config.timeout == 60000
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080


class TestTimingConfig:
    """Test TimingConfig model."""

    def test_default_values(self):
        """Test default timing configuration values."""
        config = TimingConfig()
        assert config.min_delay_between_actions == 5.0
        assert config.max_delay_between_actions == 15.0
        assert config.page_load_timeout == 10.0
        assert config.reply_timeout == 30.0

    def test_custom_values(self):
        """Test custom timing configuration values."""
        config = TimingConfig(
            min_delay_between_actions=2.0,
            max_delay_between_actions=10.0,
            page_load_timeout=15.0,
            reply_timeout=45.0
        )
        assert config.min_delay_between_actions == 2.0
        assert config.max_delay_between_actions == 10.0
        assert config.page_load_timeout == 15.0
        assert config.reply_timeout == 45.0


class TestTwitterConfig:
    """Test TwitterConfig model."""

    def test_default_values(self):
        """Test default Twitter configuration values."""
        config = TwitterConfig()
        assert config.base_url == "https://x.com"
        assert config.home_url == "https://x.com/home"
        assert config.post_selector == '[data-testid="tweetText"]'
        assert config.reply_button_selector == '[data-testid="reply"]'

    def test_url_validation(self):
        """Test URL validation."""
        # Valid URLs
        config = TwitterConfig(base_url="https://x.com", home_url="https://x.com/home")
        assert config.base_url == "https://x.com"

        # Invalid URLs should raise validation error
        with pytest.raises(ValueError, match="URL must start with https://"):
            TwitterConfig(base_url="http://x.com")


class TestLoggingConfig:
    """Test LoggingConfig model."""

    def test_default_values(self):
        """Test default logging configuration values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.file_path is None
        assert config.max_file_size == "10 MB"
        assert config.retention == "7 days"


class TestConfig:
    """Test main Config model."""

    def test_default_config(self):
        """Test default configuration creation."""
        config = Config()
        assert isinstance(config.browser, BrowserConfig)
        assert isinstance(config.timing, TimingConfig)
        assert isinstance(config.twitter, TwitterConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert config.reply_text == "Why?"

    def test_config_file_operations(self, tmp_path: Path):
        """Test saving and loading configuration from file."""
        # Create a config with custom values
        original_config = Config(reply_text="Test reply")

        # Save to file
        config_path = tmp_path / "test_config.json"
        original_config.to_file(config_path)

        # Verify file exists and contains expected data
        assert config_path.exists()
        with open(config_path, "r") as f:
            data = json.load(f)
        assert data["reply_text"] == "Test reply"

        # Load from file
        loaded_config = Config.from_file(config_path)
        assert loaded_config.reply_text == "Test reply"
        assert loaded_config.browser.headless is False  # Default value

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = Config(reply_text="Custom reply")
        assert config.reply_text == "Custom reply"

        # Test that assignment validation works
        config.reply_text = "Another reply"
        assert config.reply_text == "Another reply"
