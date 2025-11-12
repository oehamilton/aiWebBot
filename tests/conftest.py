"""Pytest configuration and fixtures for AI Web Bot tests."""

import asyncio
import pytest
from pathlib import Path

from aiwebbot.config import Config


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def default_config() -> Config:
    """Provide a default configuration for testing."""
    return Config()


@pytest.fixture
def test_config_file(tmp_path: Path) -> Path:
    """Create a temporary config file for testing."""
    config = Config()
    config_path = tmp_path / "test_config.json"
    config.to_file(config_path)
    return config_path


@pytest.fixture
def sample_post_data():
    """Provide sample post data for testing."""
    from aiwebbot.bot import PostData

    return PostData(
        text="This is a sample tweet for testing purposes.",
        author="testuser",
        post_id="1234567890",
        timestamp="2023-11-12T10:00:00Z"
    )
