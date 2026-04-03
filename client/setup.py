"""
Setup script for fnwispr Windows Client
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent.parent
long_description = ""
readme_file = this_directory / "README.md"
if readme_file.exists():
    long_description = readme_file.read_text(encoding='utf-8')

# Read version from single source of truth
version_file = this_directory / "VERSION"
version = version_file.read_text(encoding='utf-8').strip()

setup(
    name="fnwispr-client",
    version=version,
    description="Windows client for fnwispr speech-to-text service",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="fnwispr",
    python_requires=">=3.8",
    install_requires=[
        "sounddevice>=0.4.6",
        "scipy>=1.11.0",
        "pynput>=1.7.6",
        "pyautogui>=0.9.54",
        "requests>=2.31.0",
        "numpy>=1.24.0",
    ],
    entry_points={
        'console_scripts': [
            'fnwispr=main:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
