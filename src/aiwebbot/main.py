"""Main entry point for AI Web Bot."""

import asyncio
import signal
import sys
from pathlib import Path

from loguru import logger

from .bot import AIWebBot
from .config import Config
from . import __version__


def setup_logging(config: Config) -> None:
    """Setup logging configuration."""
    logger.remove()  # Remove default handler

    # Console handler
    logger.add(
        sys.stdout,
        level=config.logging.level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # File handler if configured
    if config.logging.file_path:
        logger.add(
            config.logging.file_path,
            level=config.logging.level,
            rotation=config.logging.max_file_size,
            retention=config.logging.retention,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )


def load_config(config_path: Path = None) -> Config:
    """Load configuration from file or use defaults."""
    if config_path and config_path.exists():
        logger.info(f"Loading configuration from {config_path}")
        return Config.from_file(config_path)
    else:
        logger.info("Using default configuration")
        return Config()


async def main() -> None:
    """Main application entry point."""
    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(description="AI Web Bot for X/Twitter automation")
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--generate-config",
        type=Path,
        help="Generate default configuration file at specified path"
    )

    args = parser.parse_args()

    # Generate config if requested
    if args.generate_config:
        config = Config()
        config.to_file(args.generate_config)
        logger.info(f"Generated default configuration at {args.generate_config}")
        return

    # Load configuration
    config = load_config(args.config)

    # Setup logging
    setup_logging(config)

    logger.info("Starting AI Web Bot")
    logger.info(f"Version: {__version__}")
    logger.info(f"Configuration: {config.model_dump(exclude={'twitter': {'post_selector', 'reply_button_selector', 'reply_textarea_selector', 'reply_submit_selector'}})}")

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        nonlocal bot
        if bot:
            asyncio.create_task(bot.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    bot = None
    try:
        # Initialize and run bot
        async with AIWebBot(config) as bot:
            await bot.run()

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        logger.info("AI Web Bot shutdown complete")


def run() -> None:
    """Entry point for console script."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
