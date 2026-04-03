# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for fnwispr.

Builds a one-directory bundle containing the fnwispr application
and all its dependencies (including PyTorch and Whisper).

Usage:
    pyinstaller packaging/fnwispr.spec
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect faster-whisper and ctranslate2 data files
faster_whisper_datas = collect_data_files("faster_whisper")
ctranslate2_datas = collect_data_files("ctranslate2")

# Hidden imports that PyInstaller's analysis misses
hidden_imports = (
    collect_submodules("faster_whisper")
    + collect_submodules("ctranslate2")
    + collect_submodules("huggingface_hub")
    + collect_submodules("tokenizers")
    + [
        # Platform-specific backends
        "pystray._win32",
        "pynput.keyboard._win32",
        "pynput.mouse._win32",
        # Scipy submodules used for WAV I/O
        "scipy.io",
        "scipy.io.wavfile",
        # PIL/Pillow backends
        "PIL._tkinter_finder",
    ]
)

a = Analysis(
    ["../client/main.py"],
    pathex=["../client"],
    binaries=[],
    datas=faster_whisper_datas
    + ctranslate2_datas
    + [
        ("../VERSION", "."),
        ("../client/icons/app_icon.svg", "icons"),
        ("../client/icons/app_icon.ico", "icons"),
        ("../client/alerts.py", "."),
        ("../client/gui.py", "."),
        ("../client/tray.py", "."),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unused large packages to reduce bundle size
        "matplotlib",
        "notebook",
        "jupyter",
        "IPython",
        "pandas",
        "pytest",
        "black",
        "flake8",
        "mypy",
        "sphinx",
        # torch is no longer needed (replaced by ctranslate2 via faster-whisper)
        "torch",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="fnwispr",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed app (no console window)
    disable_windowed_traceback=False,
    icon="../client/icons/app_icon.ico",
    # Windows version info
    version_info={
        "FileDescription": "fnwispr - Speech to Text",
        "ProductName": "fnwispr",
        "CompanyName": "fnrhombus",
        "LegalCopyright": "MIT License",
        "OriginalFilename": "fnwispr.exe",
    },
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="fnwispr",
)
