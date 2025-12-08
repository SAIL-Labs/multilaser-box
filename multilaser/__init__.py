"""
Multi-Laser Controller Package

A Python-based control system for managing multiple lasers and Thorlabs power meters.
"""

__version__ = "1.1.0"
__author__ = "Kok-Wei Bong, Chris Betters"

# Lazy imports to avoid requiring all dependencies at package import time
__all__ = [
    "MultiLaserController",
    "LaserControllerError",
    "LaserState",
    "PowerMeterController",
    "PowerMeterError",
    "PowerMeterRole",
]


def __getattr__(name):
    """Lazy import of submodules"""
    if name in ["MultiLaserController", "LaserControllerError", "LaserState"]:
        from multilaser.laser_controller import (
            MultiLaserController,
            LaserControllerError,
            LaserState,
        )
        return locals()[name]
    elif name in ["PowerMeterController", "PowerMeterError", "PowerMeterRole"]:
        from multilaser.power_meter_controller import (
            PowerMeterController,
            PowerMeterError,
            PowerMeterRole,
        )
        return locals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
