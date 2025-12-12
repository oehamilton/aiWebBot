# AI Web Bot - Standalone Windows Application

This is a standalone version of AI Web Bot that can be installed and run on Windows without requiring Python knowledge.

## Quick Start

### For End Users

1. **Extract the ZIP file** to a folder (e.g., `C:\AIWebBot`)

2. **Run Setup:**
   - Double-click `setup_windows.bat`
   - Wait for installation to complete

3. **Configure:**
   - Edit `config\my_config.json` with your settings
   - (Optional) Set `GROK_API_KEY` environment variable

4. **Run:**
   - Double-click `launcher.bat` (with GUI)
   - Or `launcher_no_gui.bat` (without GUI)

## What's Included

- **Application Code**: All source files
- **Configuration**: Sample config files
- **Launchers**: Easy-to-use batch files
- **Setup Script**: Automated installation
- **Documentation**: Installation and usage guides

## Requirements

### Option 1: Simple Distribution (Requires Python)
- Windows 10 or later
- **Python 3.9+ must be installed** ([Download Python](https://www.python.org/downloads/))
- Internet connection (for initial setup)

### Option 2: Standalone Executable (No Python Required)
- Windows 10 or later
- Internet connection (for initial setup)
- **Python is NOT required** - everything is bundled in the .exe

## Features

- **GUI Interface**: Monitor and control the bot through a graphical interface
- **Persistent Settings**: All settings save automatically
- **Easy Configuration**: Edit JSON files or use the GUI
- **No Python Knowledge Required**: Just run the batch files

## Configuration

### Using the GUI
1. Run `launcher.bat`
2. Use the GUI to adjust:
   - Post-to-reply ratio
   - Cooldown settings
   - System prompts

### Manual Configuration
Edit `config\my_config.json`:
```json
{
  "post_to_reply_ratio": 0.4,
  "timing": {
    "min_post_reply_cooldown_seconds": 200.0,
    "max_post_reply_cooldown_seconds": 1800.0
  },
  "twitter_username": "your_username",
  "twitter_password": "your_password"
}
```

## Troubleshooting

### Setup fails
- Make sure you have internet connection
- Check that Python 3.9+ is installed
- Run Command Prompt as Administrator

### Application won't start
- Check that setup completed successfully
- Verify Python is in PATH: `python --version`
- Check logs in `logs\` folder

### GUI doesn't appear
- Make sure you're using `launcher.bat` (not `launcher_no_gui.bat`)
- Check that tkinter is available: `python -c "import tkinter"`

## Uninstallation

Simply delete the application folder. No system changes are made during installation.

## Support

For detailed instructions, see `INSTALL_WINDOWS.md`

