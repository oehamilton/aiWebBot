# Building Standalone Windows Executable

This guide explains how to build a standalone `.exe` file that doesn't require Python on the end user's machine.

## Prerequisites

- Python 3.9+ installed on your build machine
- All dependencies installed (`pip install -e .`)
- Internet connection (for downloading PyInstaller if needed)

## Quick Build

1. **Run the build script:**
   ```batch
   python build_standalone.py
   ```

2. **Create distribution package:**
   ```batch
   create_standalone_package.bat
   ```

3. **Result:**
   - `AIWebBot_Standalone_v0.1.0.zip` - Ready to distribute!

## Detailed Build Process

### Step 1: Install PyInstaller
```batch
pip install pyinstaller
```

### Step 2: Build the Executable
```batch
python build_standalone.py
```

This will:
- Check and install dependencies
- Create launcher script
- Create PyInstaller spec file
- Build the executable (takes 5-10 minutes)
- Copy config files
- Create README

**Output:** `dist\AIWebBot.exe` (typically 50-100MB)

### Step 3: Create Distribution Package
```batch
create_standalone_package.bat
```

This creates a ZIP file containing:
- `AIWebBot.exe` - The standalone executable
- `config\` - Configuration folder
- Documentation files

## Testing the Executable

1. **Test locally:**
   ```batch
   cd dist
   AIWebBot.exe
   ```

2. **Install Playwright browsers (one-time):**
   ```batch
   python -m playwright install chromium
   ```
   (Python is only needed for this step)

3. **Run the executable:**
   ```batch
   AIWebBot.exe
   ```

## Distribution

### What to Include
- `AIWebBot.exe`
- `config\` folder (with sample configs)
- `INSTALL_WINDOWS.md`
- `QUICKSTART.txt`
- `install_playwright_browsers.bat` (helper script)

### End User Instructions

1. Extract the ZIP file
2. Run `install_playwright_browsers.bat` (requires Python - one-time setup)
3. Edit `config\my_config.json`
4. Run `AIWebBot.exe`

**Note:** While the `.exe` doesn't require Python, Playwright browsers still need to be installed using Python (one-time setup).

## Troubleshooting

### Build Fails
- Make sure all dependencies are installed: `pip install -e .`
- Check that PyInstaller is installed: `pip install pyinstaller`
- Try cleaning: Delete `build/` and `dist/` folders, then rebuild

### Executable Doesn't Run
- Check that config folder exists in same directory as .exe
- Verify Playwright browsers are installed
- Check Windows Event Viewer for error details

### Missing Modules
- Add to `hiddenimports` in the spec file
- Rebuild the executable

### Large File Size
- This is normal - all Python dependencies are bundled
- Typical size: 50-100MB
- Can be reduced by excluding unused modules in spec file

## Advanced Options

### Custom Icon
1. Create or obtain an `.ico` file
2. Update `AIWebBot.spec`:
   ```python
   icon='path/to/icon.ico',
   ```
3. Rebuild

### Console Window
To show console window (for debugging):
- Update spec file: `console=True`
- Or use: `pyinstaller --console AIWebBot.spec`

### Include Playwright Browsers
Playwright browsers are large (~200MB) and typically not bundled.
If you want to include them:
1. Install browsers: `playwright install chromium`
2. Copy from: `%USERPROFILE%\.cache\ms-playwright\`
3. Include in spec file `datas` section
4. Update code to use bundled browser path

## File Structure After Build

```
dist/
├── AIWebBot.exe          # Standalone executable
└── config/               # Configuration files
    ├── sample_config.json
    ├── system_prompts.txt
    └── ...
```

## Next Steps

After building:
1. Test the executable thoroughly
2. Create the distribution package
3. Test on a clean Windows machine (without Python)
4. Document any additional setup steps needed

