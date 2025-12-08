"""
Multi-Laser Controller Package

A Python-based control system for managing multiple lasers and Thorlabs power meters.
"""

__version__ = "1.1.0"
__author__ = "Kok-Wei Bong, Chris Betters"

from multilaser.laser_controller import (
    MultiLaserController,
    LaserControllerError,
    LaserState,
)

__all__ = [
    "MultiLaserController",
    "LaserControllerError",
    "LaserState",
]
