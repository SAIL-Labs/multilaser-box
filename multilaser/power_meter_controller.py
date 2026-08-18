"""
Thorlabs PM100USB Power Meter Controller
Provides interface for controlling Thorlabs PM100USB power meters using PyVISA

Requirements:
- pyvisa: pip install pyvisa
- pyvisa-py: pip install pyvisa-py (for pure Python backend)

Author: Based on Thorlabs PMxxx_SCPI examples
Date: 2025-12-08
"""

from __future__ import annotations

import logging
import math
import os
import random
import time
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
    PYVISA_AVAILABLE = True
except ImportError:
    pyvisa = None
    PYVISA_AVAILABLE = False


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
            self.instrument.write(f"SENS:AVER:COUN {self._averaging}")
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
            self.instrument.write(f"SENS:AVER:COUN {samples}")
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


SIM_RESOURCE_PREFIX = "SIM::"


class SimulatedPowerMeter(PowerMeter):
    """Simulated power meter for testing the GUI without hardware.

    Produces a slowly drifting power reading with measurement noise;
    averaging reduces the noise as it would on a real meter. Meter 1
    simulates ~2 mW and meter 2 ~1.5 mW so the default ratio/throughput
    displays read 75%.
    """

    BASE_POWERS_W = [2.0e-3, 1.5e-3]

    def __init__(self, resource_name: str, index: int = 0):
        super().__init__(resource_name, rm=None)
        self._base_power = self.BASE_POWERS_W[index % len(self.BASE_POWERS_W)]
        self._serial = f"SIM{index + 1:04d}"

    def connect(self):
        self.device_info = f"Thorlabs,PM100USB,{self._serial},1.0 (simulated)"
        self.connected = True
        logging.info(f"Connected to simulated power meter: {self.device_info}")

    def disconnect(self):
        self.connected = False
        logging.info(f"Disconnected from simulated power meter: {self.device_info}")

    def configure_default_settings(self):
        pass  # nothing to configure

    def set_wavelength(self, wavelength_nm: int):
        self._wavelength = wavelength_nm

    def set_averaging(self, samples: int):
        self._averaging = samples

    def read_power(self) -> float:
        if not self.connected:
            raise PowerMeterError("Not connected to power meter")
        # ±2% sinusoidal drift (30 s period) so the display visibly changes
        drift = 1.0 + 0.02 * math.sin(2.0 * math.pi * time.time() / 30.0)
        # 1% Gaussian noise, reduced by averaging like a real meter
        noise = random.gauss(0.0, 0.01) / math.sqrt(max(1, self._averaging))
        return self._base_power * drift * (1.0 + noise)


class PowerMeterController:
    """Controller for managing one or two Thorlabs PM100USB power meters"""

    def __init__(self):
        """Initialize the power meter controller"""
        # PyVISA is only required for real hardware; simulated meters
        # (see simulated_resources) work without it.
        self.rm = None
        self.power_meters: List[PowerMeter] = []
        self.reference_meter: Optional[PowerMeter] = None
        self.target_meter: Optional[PowerMeter] = None
        self.calibration_factor: float = 1.0
        # (raw_reference_w, target_w) from the last calibrate_from_measurements
        self.last_calibration: Optional[Tuple[float, float]] = None

        logging.basicConfig(level=logging.INFO)

    @staticmethod
    def simulated_resources(count: int = 2) -> List[str]:
        """Return resource names for simulated power meters (for testing)"""
        return [
            f"{SIM_RESOURCE_PREFIX}0x1313::0x8078::SIM{i + 1:04d}::INSTR"
            for i in range(count)
        ]

    @staticmethod
    def is_simulated_resource(resource_name: str) -> bool:
        """Check whether a resource name refers to a simulated meter"""
        return resource_name.startswith(SIM_RESOURCE_PREFIX)

    def find_power_meters(self) -> List[str]:
        """
        Find all available Thorlabs power meters

        Set the MULTILASER_SIM_METERS environment variable to 1 or 2 to skip
        the hardware scan and return that many simulated meters instead.

        Returns:
            List of VISA resource names for found power meters
        """
        sim_env = os.environ.get("MULTILASER_SIM_METERS", "").strip()
        if sim_env and sim_env != "0":
            count = int(sim_env) if sim_env in ("1", "2") else 2
            logging.info(f"MULTILASER_SIM_METERS set: using {count} simulated meter(s)")
            return self.simulated_resources(count)

        if pyvisa is None:
            raise PowerMeterError(
                "PyVISA is not installed. Install with: pip install pyvisa pyvisa-py"
            )

        try:
            if self.rm is None:
                self.rm = pyvisa.ResourceManager()

            # Find all USB VISA instruments
            resources = self.rm.list_resources("USB?*::INSTR")

            # Filter for Thorlabs devices (VID 0x1313). The VID field is
            # formatted as hex by NI-VISA ("0x1313") but as decimal by
            # pyvisa-py ("4883"), so accept both forms.
            thorlabs_resources = []
            for resource in resources:
                parts = resource.split("::")
                vid = parts[1].lower() if len(parts) > 1 else ""
                if vid in ("0x1313", "4883"):
                    thorlabs_resources.append(resource)
                else:
                    logging.info(f"Ignoring non-Thorlabs USB instrument: {resource}")
            logging.info(f"Found {len(thorlabs_resources)} Thorlabs power meter(s)")
            return thorlabs_resources

        except Exception as e:
            raise PowerMeterError(f"Failed to find power meters: {str(e)}")

    def connect_power_meters(self, resource_names: List[str]):
        """
        Connect to specified power meters

        Args:
            resource_names: List of VISA resource names to connect to (1 or 2)
        """
        if len(resource_names) not in [1, 2]:
            raise PowerMeterError("1 or 2 power meters are required")

        self.power_meters.clear()

        for i, resource_name in enumerate(resource_names):
            if self.is_simulated_resource(resource_name):
                pm = SimulatedPowerMeter(resource_name, index=i)
            else:
                if pyvisa is None:
                    raise PowerMeterError(
                        "PyVISA is not installed. Install with: pip install pyvisa pyvisa-py"
                    )
                if self.rm is None:
                    self.rm = pyvisa.ResourceManager()
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

    def assign_roles(self, reference_index: Optional[int], target_index: Optional[int]):
        """
        Assign reference and target roles to power meters

        Args:
            reference_index: Index of power meter to use as reference, or None
            target_index: Index of power meter to use as target, or None
        """
        if not self.power_meters:
            raise PowerMeterError("No connected power meters")

        if reference_index is not None and target_index is not None:
            if reference_index == target_index:
                raise PowerMeterError("Reference and target must be different power meters")

        # Reset all roles
        for pm in self.power_meters:
            pm.set_role(PowerMeterRole.UNASSIGNED)

        self.reference_meter = None
        self.target_meter = None

        if reference_index is not None:
            self.power_meters[reference_index].set_role(PowerMeterRole.REFERENCE)
            self.reference_meter = self.power_meters[reference_index]
            logging.info(f"Assigned Reference: {self.reference_meter.get_short_name()}")

        if target_index is not None:
            self.power_meters[target_index].set_role(PowerMeterRole.TARGET)
            self.target_meter = self.power_meters[target_index]
            logging.info(f"Assigned Target: {self.target_meter.get_short_name()}")

    def set_calibration_factor(self, factor: float):
        """
        Set the calibration factor for the reference meter.

        The corrected reference reading = raw_reading * calibration_factor.
        For a 90:10 fibre splitter where 10% goes to the reference meter,
        the calibration factor would be ~10 so that the corrected reference
        matches the target power.

        Args:
            factor: Calibration factor (default 1.0 = no correction)
        """
        if factor <= 0:
            raise PowerMeterError("Calibration factor must be positive")
        self.calibration_factor = factor
        logging.info(f"Calibration factor set to {factor:.6f}")

    def calibrate_from_measurements(self) -> float:
        """
        Auto-calibrate by reading both meters and computing the factor.

        Sets calibration_factor = target_power / reference_power so that
        corrected_reference ≈ target_power after calibration.

        Returns:
            The computed calibration factor

        Raises:
            PowerMeterError: If both meters are not available or reference reads zero
        """
        raw_ref, _, target = self.read_meters()

        if raw_ref is None or target is None:
            raise PowerMeterError("Both meters must be connected to calibrate")
        if raw_ref <= 0:
            raise PowerMeterError("Reference power must be positive to calibrate")

        factor = target / raw_ref
        self.calibration_factor = factor
        self.last_calibration = (raw_ref, target)
        logging.info(f"Calibrated: factor = {factor:.6f} (target={target:.6e}, ref={raw_ref:.6e})")
        return factor

    def read_meters(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Read power from both meters with calibration applied to reference.

        Returns:
            Tuple of (raw_reference_power, corrected_reference_power, target_power) in Watts.
            corrected_reference = raw_reference * calibration_factor.
        """
        raw_ref = None
        corrected_ref = None
        target_power = None

        if self.reference_meter and self.reference_meter.connected:
            try:
                raw_ref = self.reference_meter.read_power()
                corrected_ref = raw_ref * self.calibration_factor
            except PowerMeterError as e:
                logging.error(f"Error reading reference meter: {str(e)}")

        if self.target_meter and self.target_meter.connected:
            try:
                target_power = self.target_meter.read_power()
            except PowerMeterError as e:
                logging.error(f"Error reading target meter: {str(e)}")

        return raw_ref, corrected_ref, target_power

    def read_both_meters(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Read power from both meters (corrected reference, target).

        Returns:
            Tuple of (corrected_reference_power, target_power) in Watts
        """
        _, corrected_ref, target_power = self.read_meters()
        return corrected_ref, target_power

    def calculate_ratio(self) -> Optional[float]:
        """
        Calculate the ratio of target/corrected_reference power

        Returns:
            Ratio of target to corrected reference power, or None if not available
        """
        corrected_ref, target_power = self.read_both_meters()

        if corrected_ref is not None and target_power is not None:
            if corrected_ref > 0:
                return target_power / corrected_ref

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
