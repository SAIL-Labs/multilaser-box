"""
Thorlabs PM100USB Power Meter Controller
Provides interface for controlling Thorlabs PM100USB power meters using PyVISA

Requirements:
- pyvisa: pip install pyvisa
- pyvisa-py: pip install pyvisa-py (for pure Python backend)

Author: Based on Thorlabs PMxxx_SCPI examples
Date: 2025-12-08
"""

import logging
from typing import Optional, List, Tuple
from enum import Enum


def format_power_auto_scale(power_watts: float) -> str:
    """
    Format power value with automatic unit scaling.

    Selects the most appropriate unit (W, mW, µW, nW) to display
    values in the 1-999 range before the decimal point.

    Args:
        power_watts: Power value in Watts

    Returns:
        Formatted string with value and unit (e.g., "125.3 mW")
    """
    if power_watts is None:
        return "--- W"

    abs_power = abs(power_watts)

    # Select appropriate unit based on magnitude
    if abs_power >= 1.0:
        # Display in Watts
        return f"{power_watts:.3f} W"
    elif abs_power >= 1e-3:
        # Display in milliwatts
        return f"{power_watts * 1e3:.3f} mW"
    elif abs_power >= 1e-6:
        # Display in microwatts
        return f"{power_watts * 1e6:.3f} µW"
    else:
        # Display in nanowatts
        return f"{power_watts * 1e9:.3f} nW"

try:
    import pyvisa
except ImportError:
    pyvisa = None


class PowerMeterRole(Enum):
    """Role assignment for power meters"""
    REFERENCE = "Reference"
    TARGET = "Target"
    UNASSIGNED = "Unassigned"


class PowerMeterError(Exception):
    """Custom exception for power meter errors"""
    pass


class PowerMeter:
    """Individual power meter instance"""

    def __init__(self, resource_name: str, rm: pyvisa.ResourceManager):
        """
        Initialize a power meter instance

        Args:
            resource_name: VISA resource name (e.g., 'USB0::0x1313::0x8078::P0007837::INSTR')
            rm: PyVISA resource manager
        """
        self.resource_name = resource_name
        self.rm = rm
        self.instrument = None
        self.connected = False
        self.role = PowerMeterRole.UNASSIGNED
        self.device_info = ""
        self._wavelength = 1310  # Default wavelength in nm
        self._power_unit = "W"   # Default unit: Watts
        self._averaging = 1   # Default averaging samples

    def connect(self):
        """Connect to the power meter"""
        try:
            self.instrument = self.rm.open_resource(self.resource_name)
            self.device_info = self.instrument.query("SYST:SENS:IDN?").strip()
            self.connected = True

            # Apply default settings
            self.configure_default_settings()

            logging.info(f"Connected to power meter: {self.device_info}")
        except Exception as e:
            raise PowerMeterError(f"Failed to connect to {self.resource_name}: {str(e)}")

    def disconnect(self):
        """Disconnect from the power meter"""
        if self.instrument:
            try:
                self.instrument.close()
                self.connected = False
                logging.info(f"Disconnected from power meter: {self.device_info}")
            except Exception as e:
                logging.error(f"Error disconnecting: {str(e)}")

    def configure_default_settings(self):
        """Configure default measurement settings"""
        if not self.connected:
            raise PowerMeterError("Not connected to power meter")

        try:
            # Enable auto-ranging
            self.instrument.write("SENS:RANGE:AUTO ON")
            # Set wavelength
            self.instrument.write(f"SENS:CORR:WAV {self._wavelength}")
            # Set power unit
            self.instrument.write(f"SENS:POW:UNIT {self._power_unit}")
            # Set averaging
            self.instrument.write(f"SENS:AVER:{self._averaging}")
        except Exception as e:
            raise PowerMeterError(f"Failed to configure settings: {str(e)}")

    def set_wavelength(self, wavelength_nm: int):
        """
        Set the wavelength calibration

        Args:
            wavelength_nm: Wavelength in nanometers
        """
        if not self.connected:
            raise PowerMeterError("Not connected to power meter")

        try:
            self._wavelength = wavelength_nm
            self.instrument.write(f"SENS:CORR:WAV {wavelength_nm}")
        except Exception as e:
            raise PowerMeterError(f"Failed to set wavelength: {str(e)}")

    def set_averaging(self, samples: int):
        """
        Set the number of averaging samples

        Args:
            samples: Number of samples to average
        """
        if not self.connected:
            raise PowerMeterError("Not connected to power meter")

        try:
            self._averaging = samples
            self.instrument.write(f"SENS:AVER:{samples}")
        except Exception as e:
            raise PowerMeterError(f"Failed to set averaging: {str(e)}")

    def read_power(self) -> float:
        """
        Read current power measurement

        Returns:
            Power reading in Watts
        """
        if not self.connected:
            raise PowerMeterError("Not connected to power meter")

        try:
            power_str = self.instrument.query("MEAS:POW?").strip()
            return float(power_str)
        except Exception as e:
            raise PowerMeterError(f"Failed to read power: {str(e)}")

    def set_role(self, role: PowerMeterRole):
        """Set the role of this power meter"""
        self.role = role

    def get_short_name(self) -> str:
        """Get a short name for display purposes"""
        if self.device_info:
            # Extract serial number from device info if available
            parts = self.device_info.split(',')
            if len(parts) > 2:
                return f"PM ({parts[2].strip()})"
        return self.resource_name.split('::')[-2] if '::' in self.resource_name else self.resource_name


class PowerMeterController:
    """Controller for managing two Thorlabs PM100USB power meters"""

    def __init__(self):
        """Initialize the power meter controller"""
        if pyvisa is None:
            raise PowerMeterError("PyVISA is not installed. Install with: pip install pyvisa pyvisa-py")

        self.rm = None
        self.power_meters: List[PowerMeter] = []
        self.reference_meter: Optional[PowerMeter] = None
        self.target_meter: Optional[PowerMeter] = None

        logging.basicConfig(level=logging.INFO)

    def find_power_meters(self) -> List[str]:
        """
        Find all available Thorlabs power meters

        Returns:
            List of VISA resource names for found power meters
        """
        try:
            if self.rm is None:
                self.rm = pyvisa.ResourceManager()

            # Find all USB VISA instruments
            resources = self.rm.list_resources("USB?*::INSTR")

            # Filter for Thorlabs devices (VID: 0x1313)
            # thorlabs_resources = []
            # for resource in resources:
            #     if "0x1313" in resource:
            #         thorlabs_resources.append(resource)
            thorlabs_resources=resources
            logging.info(f"Found {len(thorlabs_resources)} Thorlabs power meter(s)")
            return thorlabs_resources

        except Exception as e:
            raise PowerMeterError(f"Failed to find power meters: {str(e)}")

    def connect_power_meters(self, resource_names: List[str]):
        """
        Connect to specified power meters

        Args:
            resource_names: List of VISA resource names to connect to
        """
        if len(resource_names) != 2:
            raise PowerMeterError("Exactly 2 power meters are required")

        self.power_meters.clear()

        for resource_name in resource_names:
            pm = PowerMeter(resource_name, self.rm)
            pm.connect()
            self.power_meters.append(pm)

    def disconnect_all(self):
        """Disconnect from all power meters"""
        for pm in self.power_meters:
            pm.disconnect()
        self.power_meters.clear()
        self.reference_meter = None
        self.target_meter = None

        if self.rm:
            self.rm.close()
            self.rm = None

    def assign_roles(self, reference_index: int, target_index: int):
        """
        Assign reference and target roles to power meters

        Args:
            reference_index: Index of power meter to use as reference (0 or 1)
            target_index: Index of power meter to use as target (0 or 1)
        """
        if len(self.power_meters) != 2:
            raise PowerMeterError("Must have 2 connected power meters")

        if reference_index == target_index:
            raise PowerMeterError("Reference and target must be different power meters")

        if reference_index not in [0, 1] or target_index not in [0, 1]:
            raise PowerMeterError("Index must be 0 or 1")

        # Reset all roles
        for pm in self.power_meters:
            pm.set_role(PowerMeterRole.UNASSIGNED)

        # Assign new roles
        self.power_meters[reference_index].set_role(PowerMeterRole.REFERENCE)
        self.power_meters[target_index].set_role(PowerMeterRole.TARGET)

        self.reference_meter = self.power_meters[reference_index]
        self.target_meter = self.power_meters[target_index]

        logging.info(f"Assigned Reference: {self.reference_meter.get_short_name()}")
        logging.info(f"Assigned Target: {self.target_meter.get_short_name()}")

    def read_both_meters(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Read power from both meters

        Returns:
            Tuple of (reference_power, target_power) in Watts
        """
        ref_power = None
        target_power = None

        if self.reference_meter and self.reference_meter.connected:
            try:
                ref_power = self.reference_meter.read_power()
            except PowerMeterError as e:
                logging.error(f"Error reading reference meter: {str(e)}")

        if self.target_meter and self.target_meter.connected:
            try:
                target_power = self.target_meter.read_power()
            except PowerMeterError as e:
                logging.error(f"Error reading target meter: {str(e)}")

        return ref_power, target_power

    def calculate_ratio(self) -> Optional[float]:
        """
        Calculate the ratio of target/reference power

        Returns:
            Ratio of target to reference power, or None if not available
        """
        ref_power, target_power = self.read_both_meters()

        if ref_power is not None and target_power is not None:
            if ref_power > 0:
                return target_power / ref_power

        return None

    def get_power_meters(self) -> List[PowerMeter]:
        """Get list of all connected power meters"""
        return self.power_meters

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup"""
        self.disconnect_all()
