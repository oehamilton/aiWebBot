#!/usr/bin/env python3
"""Build script for creating a standalone Windows executable with GUI launcher."""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def build_standalone():
    """Build standalone executable using PyInstaller."""
    print("Building standalone Windows application with GUI...")
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Clean previous builds
    for dir_name in ["build", "dist"]:
        if Path(dir_name).exists():
            print(f"Cleaning {dir_name}...")
            shutil.rmtree(dir_name)
    
    # Create launcher script
    launcher_content = '''import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set environment variable for bundled app
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    os.environ['AIWEBOT_BUNDLED'] = '1'
    base_path = Path(sys._MEIPASS)
else:
    base_path = Path(__file__).parent

# Run the main application
if __name__ == "__main__":
    from aiwebbot.main import run
    run()
'''
    
    launcher_path = Path("launcher.py")
    launcher_path.write_text(launcher_content)
    
    # Create PyInstaller spec file
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config', 'config'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'playwright',
        'aiohttp',
        'pydantic',
        'loguru',
        'asyncio',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
    
    spec_path = Path("AIWebBot.spec")
    spec_path.write_text(spec_content)
    
    # Build with PyInstaller
    cmd = ["pyinstaller", "--clean", "AIWebBot.spec"]
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd)
    
    print("\nBuild complete!")
    print(f"Executable location: dist/AIWebBot.exe")
    print("\nNext steps:")
    print("1. Copy the 'config' folder to the dist directory")
    print("2. On target machine, run: playwright install chromium")
    print("3. Set GROK_API_KEY environment variable (optional)")

if __name__ == "__main__":
    build_standalone()

