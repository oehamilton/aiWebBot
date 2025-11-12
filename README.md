# AI Web Bot

An automated Python application that interacts with X (formerly Twitter) by reading posts and replying with "Why?". The bot uses browser automation to navigate the web interface and perform actions on behalf of a logged-in user account.

## Features

- **Automated Post Reading**: Extracts text content from X/Twitter posts
- **Automated Replies**: Responds to posts with configurable text (default: "Why?")
- **Continuous Scrolling**: Automatically scrolls through the feed
- **Page Refresh**: Refreshes the page when reaching the bottom
- **Configurable Timing**: Adjustable delays between actions to appear human-like
- **Comprehensive Logging**: Detailed logging with configurable levels
- **Browser Automation**: Uses Playwright for reliable web automation

## Requirements

- Python 3.9+
- Active X/Twitter account (bot uses existing browser session)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd aiwebbot
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e .
   pip install -e ".[dev]"  # For development dependencies
   ```

4. **Install Playwright browsers:**
   ```bash
   playwright install
   ```

## Configuration

Create a configuration file based on the sample:

```bash
python -m aiwebbot.main --generate-config config/my_config.json
```

Or copy and modify the sample configuration:

```bash
cp config/sample_config.json config/my_config.json
```

### Configuration Options

- **Browser Settings**: Control headless mode, viewport size, timeouts
- **Timing**: Configure delays between actions (important for rate limiting)
- **Twitter Selectors**: CSS selectors for X/Twitter elements (may need updates if UI changes)
- **Logging**: Configure log level, file output, retention
- **Reply Text**: Customize the reply message

## Usage

### Basic Usage

Run the bot with default configuration:

```bash
python -m aiwebbot.main
```

### With Custom Configuration

```bash
python -m aiwebbot.main --config config/my_config.json
```

### Generate Configuration Template

```bash
python -m aiwebbot.main --generate-config config/new_config.json
```

## Important Notes

### Authentication
- The bot **requires** you to be already logged into X/Twitter in your browser
- It does **not** handle login credentials or authentication
- Start your browser session and log into X/Twitter before running the bot

### Rate Limiting & Safety
- Configure appropriate delays between actions to avoid account suspension
- Default settings include random delays between 5-15 seconds
- Monitor your account activity and adjust timing as needed

### X/Twitter UI Changes
- The bot uses CSS selectors that may break if X/Twitter changes their interface
- Monitor logs for element selection errors and update selectors as needed
- The current selectors are based on X/Twitter's data-testid attributes

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Project Structure

```
aiwebbot/
├── src/aiwebbot/          # Main package
│   ├── __init__.py
│   ├── bot.py            # Main bot logic
│   ├── config.py         # Configuration models
│   └── main.py           # CLI entry point
├── tests/                # Test suite
├── config/               # Configuration files
├── plan.md              # Development plan
├── prd.md               # Product requirements
└── README.md
```

## Security Considerations

- No credentials are stored or transmitted
- Uses existing browser sessions only
- Configurable delays to avoid detection
- Clear logging without sensitive data exposure
- Respects platform Terms of Service boundaries

## Troubleshooting

### Common Issues

1. **"User not authenticated"**
   - Ensure you're logged into X/Twitter in your browser before starting the bot

2. **"Element not found" errors**
   - X/Twitter may have updated their UI. Check and update CSS selectors in configuration

3. **Rate limiting or account suspension**
   - Increase delays between actions in the configuration
   - Monitor account activity closely

4. **Browser crashes**
   - Ensure Playwright browsers are properly installed
   - Try running in non-headless mode for debugging

### Logs

Check the logs directory for detailed error information:
- Default log file: `logs/aiwebbot.log`
- Console output shows real-time status
- Increase log level to DEBUG for more detailed information

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

See LICENSE file for details.

## Disclaimer

This tool is for educational and personal use only. Users are responsible for complying with X/Twitter's Terms of Service and applicable laws. The authors are not responsible for any account suspension, legal issues, or other consequences resulting from use of this software.