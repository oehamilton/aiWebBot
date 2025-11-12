"""Configuration management for AI Web Bot."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class BrowserConfig(BaseModel):
    """Browser automation configuration."""

    headless: bool = Field(default=False, description="Run browser in headless mode")
    slow_mo: int = Field(default=1000, description="Slow down operations by milliseconds")
    timeout: int = Field(default=30000, description="Default timeout for operations in ms")
    viewport_width: int = Field(default=1280, description="Browser viewport width")
    viewport_height: int = Field(default=720, description="Browser viewport height")


class TimingConfig(BaseModel):
    """Timing and rate limiting configuration."""

    min_delay_between_actions: float = Field(
        default=5.0, description="Minimum delay between actions in seconds"
    )
    max_delay_between_actions: float = Field(
        default=15.0, description="Maximum delay between actions in seconds"
    )
    page_load_timeout: float = Field(
        default=10.0, description="Timeout for page loads in seconds"
    )
    reply_timeout: float = Field(
        default=30.0, description="Timeout for reply operations in seconds"
    )


class TwitterConfig(BaseModel):
    """X/Twitter specific configuration."""

    base_url: str = Field(default="https://x.com", description="X/Twitter base URL")
    home_url: str = Field(default="https://x.com/home", description="X/Twitter home URL")

    # CSS selectors for elements (may need updates if X changes their UI)
    post_selector: str = Field(
        default='[data-testid="tweetText"]',
        description="CSS selector for post text content"
    )
    reply_button_selector: str = Field(
        default='[data-testid="reply"]',
        description="CSS selector for reply button"
    )
    reply_textarea_selector: str = Field(
        default='[data-testid="tweetTextarea_0"]',
        description="CSS selector for reply textarea"
    )
    reply_submit_selector: str = Field(
        default='[data-testid="tweetButton"]',
        description="CSS selector for reply submit button"
    )

    @field_validator("base_url", "home_url")
    @classmethod
    def validate_urls(cls, v):
        """Ensure URLs are valid."""
        if not v.startswith("https://"):
            raise ValueError("URL must start with https://")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Logging level")
    file_path: Optional[Path] = Field(default=None, description="Log file path")
    max_file_size: str = Field(default="10 MB", description="Maximum log file size")
    retention: str = Field(default="7 days", description="Log retention period")


class Config(BaseModel):
    """Main configuration for AI Web Bot."""

    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    timing: TimingConfig = Field(default_factory=TimingConfig)
    twitter: TwitterConfig = Field(default_factory=TwitterConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    reply_text: str = Field(default="Why?", description="Text to reply with")

    # Authentication credentials (optional - if not provided, manual login required)
    twitter_username: Optional[str] = Field(default=None, description="X/Twitter username for automatic login")
    twitter_password: Optional[str] = Field(default=None, description="X/Twitter password for automatic login")

    model_config = ConfigDict(validate_assignment=True)

    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """Load configuration from a JSON file."""
        import json

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def to_file(self, config_path: Path) -> None:
        """Save configuration to a JSON file."""
        import json

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)
