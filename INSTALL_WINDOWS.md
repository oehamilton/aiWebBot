# AI Web Bot - Windows Installation Guide

This guide will help you install and run AI Web Bot on a Windows machine.

## Option 1: Quick Install (Requires Python)

**Note:** This option requires Python 3.9+ to be installed on the system.

### Prerequisites
- Windows 10 or later
- **Python 3.9 or later** ([Download Python](https://www.python.org/downloads/))
  - During installation, check "Add Python to PATH"

### Installation Steps

1. **Extract the application** to a folder (e.g., `C:\AIWebBot`)

2. **Run the setup script:**
   - Double-click `setup_windows.bat`
   - This will install all dependencies and set up the application

3. **Configure the application:**
   - Edit `config\my_config.json` with your settings
   - (Optional) Set `GROK_API_KEY` environment variable

4. **Run the application:**
   - Double-click `launcher.bat` to run with GUI
   - Or double-click `launcher_no_gui.bat` to run without GUI

## Option 2: Manual Installation

### Step 1: Install Python
1. Download Python 3.9+ from [python.org](https://www.python.org/downloads/)
2. During installation, check "Add Python to PATH"
3. Verify installation: Open Command Prompt and run `python --version`

### Step 2: Install Dependencies
Open Command Prompt in the application folder and run:
```batch
python -m pip install --upgrade pip
python -m pip install -e .
python -m playwright install chromium
```

### Step 3: Create Configuration
```batch
python -m aiwebbot.main --generate-config config\my_config.json
```

### Step 4: Run the Application
```batch
REM With GUI
python -m aiwebbot.main --gui

REM Without GUI
python -m aiwebbot.main
```

## Option 3: Standalone Executable (No Python Required)

**Note:** This option creates a standalone `.exe` file that does NOT require Python to be installed on the end user's machine.

### Building the Standalone Executable

1. **Install PyInstaller (one-time setup):**
   ```batch
   pip install pyinstaller
   ```

2. **Build the executable:**
   ```batch
   python build_standalone.py
   ```

3. **Create distribution package:**
   ```batch
   create_standalone_package.bat
   ```

4. **Find the package:**
   - Location: `AIWebBot_Standalone_v0.1.0.zip`
   - Contains: `AIWebBot.exe`, `config` folder, and documentation

### Installing on Target Machine

1. **Extract the ZIP file** to a folder

2. **Install Playwright browsers (one-time):**
   - **Option A:** If Python is available:
     ```batch
     install_playwright_browsers.bat
     ```
   - **Option B:** Manual installation:
     ```batch
     python -m playwright install chromium
     ```
   - **Note:** Python is only needed for this one-time browser installation step

3. **Configure:**
   - Edit `config\my_config.json` with your settings

4. **Run:**
   - Double-click `AIWebBot.exe`
   - No Python required to run the application!

## Configuration

### Basic Configuration
Edit `config\my_config.json`:
- `twitter_username`: Your X/Twitter username
- `twitter_password`: Your X/Twitter password
- `post_to_reply_ratio`: Probability of creating new posts (0.0 to 1.0)
- `min_post_reply_cooldown_seconds`: Minimum wait time between actions
- `max_post_reply_cooldown_seconds`: Maximum wait time between actions

### Environment Variables
- `GROK_API_KEY`: Your Grok API key (optional, for AI-powered replies)

To set environment variable in Windows:
1. Open System Properties → Environment Variables
2. Add new variable: `GROK_API_KEY` = `your-key-here`

## Troubleshooting

### Python not found
- Make sure Python is installed and added to PATH
- Reinstall Python and check "Add Python to PATH" option

### Playwright browser not found
- Run: `python -m playwright install chromium`

### Import errors
- Make sure all dependencies are installed: `pip install -e .`

### GUI doesn't appear
- Make sure tkinter is installed (usually included with Python)
- On some systems: `pip install tk`

## Uninstallation

To uninstall:
1. Delete the application folder
2. (Optional) Remove environment variables
3. (Optional) Remove browser data: `%USERPROFILE%\.aiwebbot\`

## Support

For issues or questions, check the README.md file or the project repository.

