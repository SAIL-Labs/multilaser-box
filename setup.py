"""
Setup configuration for Multi-Laser Controller package
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="multilaser-controller",
    version="1.0.0",
    author="Kok-Wei Bong, Chris Betters",
    author_email="",
    description="A Python-based graphical interface for controlling multiple lasers through Arduino",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/multilaser-box",
    packages=find_packages(),
    py_modules=["laser_controller", "laser_controller_gui"],
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
    },
    entry_points={
        "console_scripts": [
            "multilaser-gui=laser_controller_gui:main",
            "multilaser=laser_controller_gui:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["laser_ttl_controller/*.ino", "figures/*"],
    },
)
