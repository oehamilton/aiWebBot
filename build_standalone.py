#!/usr/bin/env python3
"""Build script for creating a standalone Windows executable."""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_dependencies():
    """Check and install required dependencies."""
    print("Checking dependencies...")
    
    try:
        import PyInstaller
        print("  ✓ PyInstaller found")
    except ImportError:
        print("  Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("  ✓ PyInstaller installed")
    
    # Check if all required packages are installed
    required = ['playwright', 'pydantic', 'loguru', 'aiohttp']
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
            print(f"  ✓ {pkg} found")
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"  Installing missing packages: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("  ✓ All dependencies installed")

def create_launcher_script():
    """Create a launcher script for the executable."""
    launcher_content = '''"""Launcher script for standalone AI Web Bot."""
import sys
import os
from pathlib import Path

# Determine base path
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    base_path = Path(sys.executable).parent
    os.environ['AIWEBOT_BUNDLED'] = '1'
else:
    # Running as script
    base_path = Path(__file__).parent / "src"

# Add to path if not frozen
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(base_path))

# Import and run
if __name__ == "__main__":
    from aiwebbot.main import run
    run()
'''
    
    launcher_path = Path("launcher_standalone.py")
    launcher_path.write_text(launcher_content)
    return launcher_path

def create_spec_file():
    """Create PyInstaller spec file."""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
# AI Web Bot Standalone Build Configuration

block_cipher = None

a = Analysis(
    ['launcher_standalone.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config', 'config'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'playwright',
        'playwright.async_api',
        'aiohttp',
        'pydantic',
        'loguru',
        'asyncio',
        'json',
        'pathlib',
        'datetime',
        'threading',
        'random',
        're',
        'time',
        'os',
        'sys',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AIWebBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI mode)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Can add icon file path here if you have one
)
'''
    
    spec_path = Path("AIWebBot.spec")
    spec_path.write_text(spec_content)
    return spec_path

def build_executable():
    """Build the standalone executable."""
    print("\n" + "="*60)
    print("Building Standalone Windows Executable")
    print("="*60 + "\n")
    
    # Check dependencies
    check_dependencies()
    
    # Clean previous builds
    print("\nCleaning previous builds...")
    for dir_name in ["build", "dist"]:
        if Path(dir_name).exists():
            print(f"  Removing {dir_name}/")
            shutil.rmtree(dir_name)
    
    # Remove old spec file if exists
    spec_file = Path("AIWebBot.spec")
    if spec_file.exists():
        spec_file.unlink()
    
    # Create launcher script
    print("\nCreating launcher script...")
    launcher_path = create_launcher_script()
    print(f"  ✓ Created {launcher_path}")
    
    # Create spec file
    print("\nCreating PyInstaller spec file...")
    spec_path = create_spec_file()
    print(f"  ✓ Created {spec_path}")
    
    # Build with PyInstaller
    print("\nBuilding executable with PyInstaller...")
    print("  This may take several minutes...")
    cmd = ["pyinstaller", "--clean", "--noconfirm", "AIWebBot.spec"]
    
    try:
        subprocess.check_call(cmd)
        print("\n  ✓ Build successful!")
    except subprocess.CalledProcessError as e:
        print(f"\n  ✗ Build failed: {e}")
        return False
    
    # Verify executable exists
    exe_path = Path("dist/AIWebBot.exe")
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n  ✓ Executable created: {exe_path}")
        print(f"  ✓ Size: {size_mb:.1f} MB")
    else:
        print("\n  ✗ Executable not found!")
        return False
    
    # Copy config folder to dist
    print("\nCopying configuration files...")
    config_src = Path("config")
    config_dst = Path("dist/config")
    
    if config_src.exists():
        if config_dst.exists():
            shutil.rmtree(config_dst)
        shutil.copytree(config_src, config_dst)
        print(f"  ✓ Copied config folder to dist/config")
    else:
        print("  ⚠ Config folder not found - you may need to create it manually")
    
    # Create README for distribution
    readme_content = """AI Web Bot - Standalone Windows Application

QUICK START:
1. Run AIWebBot.exe
2. On first run, you may need to install Playwright browsers:
   - Open Command Prompt in this folder
   - Run: playwright install chromium
3. Edit config\\my_config.json with your settings
4. Set GROK_API_KEY environment variable (optional)

NOTES:
- This is a standalone executable - Python is NOT required
- The config folder contains configuration files
- Logs will be created in a logs folder
- Browser data is stored in %USERPROFILE%\\.aiwebbot\\

For detailed instructions, see INSTALL_WINDOWS.md
"""
    
    readme_path = Path("dist/README.txt")
    readme_path.write_text(readme_content)
    print(f"  ✓ Created README.txt")
    
    print("\n" + "="*60)
    print("Build Complete!")
    print("="*60)
    print(f"\nExecutable location: {exe_path.absolute()}")
    print(f"\nNext steps:")
    print("  1. Test the executable: Run dist\\AIWebBot.exe")
    print("  2. Create distribution package:")
    print("     - Copy dist\\AIWebBot.exe")
    print("     - Copy dist\\config folder")
    print("     - Copy README.txt and INSTALL_WINDOWS.md")
    print("     - Zip everything together")
    print("\n  ⚠ IMPORTANT: Users will still need to run:")
    print("     playwright install chromium")
    print("     (This installs the browser engine)")
    
    return True

if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)
