"""
Setup configuration for Multi-Laser Controller package
"""

from setuptools import setup, find_packages
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / "multilaser"))
from _version import __version__

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="multilaser-controller",
    version=__version__,
    author="Kok-Wei Bong, Chris Betters",
    author_email="",
    description="A Python-based graphical interface for controlling multiple lasers and Thorlabs power meters",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SAIL-Labs/multilaser-box",
    packages=find_packages(exclude=["tests", "dist", "build"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    install_requires=[
        "numpy",
        "pyserial>=3.5",
        "PyQt6>=6.0",
    ],
    extras_require={
        "dev": [
            "pyinstaller",
        ],
        "powermeter": [
            "pyvisa>=1.11.0",
            "pyvisa-py>=0.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "multilaser-gui=multilaser.laser_controller_gui:main",
            "multilaser=multilaser.laser_controller_gui:main",
        ],
    },
    include_package_data=True,
    package_data={
        "multilaser": ["../laser_ttl_controller/*.ino", "../figures/*"],
    },
)
