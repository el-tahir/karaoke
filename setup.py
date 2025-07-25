#!/usr/bin/env python3
"""Setup script for Karaoke Creator."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
with open('requirements.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            requirements.append(line)

setup(
    name="karaoke-creator",
    version="1.0.0",
    author="Eltah",
    author_email="",
    description="Generate karaoke videos from YouTube songs with AI-powered vocal separation and synchronized lyrics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/eltahhan/karaoke-creator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Multimedia :: Video",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "karaoke-creator=main:main",
        ],
    },
    keywords="karaoke, youtube, video, audio, separation, lyrics, music",
    project_urls={
        "Bug Reports": "https://github.com/eltahhan/karaoke-creator/issues",
        "Source": "https://github.com/eltahhan/karaoke-creator",
    },
)