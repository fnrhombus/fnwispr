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

# Collect Whisper's asset files (mel filters, tokenizers, etc.)
# These are .npz and .tiktoken files that whisper.load_model() needs at runtime.
whisper_datas = collect_data_files("whisper")

# Collect tiktoken data files (used by Whisper's tokenizer)
tiktoken_datas = collect_data_files("tiktoken")

# Hidden imports that PyInstaller's analysis misses
hidden_imports = (
    collect_submodules("whisper")
    + collect_submodules("tiktoken")
    + collect_submodules("tiktoken_ext")
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
        # Torch backends (PyInstaller often misses these)
        "torch",
        "torch.nn",
        "torch.nn.functional",
        # Numba (used by some whisper features)
        "numba",
    ]
)

a = Analysis(
    ["../client/main.py"],
    pathex=["../client"],
    binaries=[],
    datas=whisper_datas
    + tiktoken_datas
    + [
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
